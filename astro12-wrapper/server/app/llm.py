"""LLM interpretation client with cache and graceful degradation.

Modes (ASTRO12_LLM_MODE):
- "mock":   deterministic offline stub — lets Flutter/web integrate the full
            API contract before any LLM keys exist. Never fails.
- "openai": real calls to any OpenAI-compatible endpoint (the Astro12AI
            engine's provider). Failures fall back to a 502 that the route
            turns into a clear message; cached answers still work offline.

The cache is keyed by chart_hash + lang + focus, so repeated requests are
free for us and instant for the user (monetization: paid quota only counts
cache misses).
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections import OrderedDict

from astro12 import SYSTEM_BRIEF_RU, aspect_prompt, chart_to_prompt
from astro12.constants import SIGN_RU
from astro12.model import TwelveChart

from .config import Settings


class LLMError(RuntimeError):
    pass


class InterpretationCache:
    """Tiny thread-safe LRU; values are (text, model, usage)."""

    def __init__(self, max_items: int = 512) -> None:
        self._max = max(16, max_items)
        self._data: OrderedDict[str, tuple[str, str, dict | None]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
        return None

    def put(self, key: str, value: tuple[str, str, dict | None]) -> None:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def prefix_lookup(self, prefix: str):
        """Find any entry whose key starts with prefix (hash-only reuse)."""
        with self._lock:
            for key, value in self._data.items():
                if key.startswith(prefix):
                    self._data.move_to_end(key)
                    return value
        return None

    def __len__(self) -> int:
        return len(self._data)


def _user_prompt(chart: TwelveChart, focus: str | None, lang: str) -> str:
    base = chart_to_prompt(chart, lang=lang)
    if focus:
        base += f"\n\n## Вопрос клиента\n{focus}\n"
    return base


def _mock_interpretation(chart: TwelveChart, focus: str | None) -> str:
    """Deterministic offline 'interpretation' built from the school's data."""
    lines = ["[MOCK — режим ASTRO12_LLM_MODE=mock, реальный LLM не вызывался]", ""]
    own = [p for p in chart.placements if p.house_of_own_ruler]
    if own:
        s = ", ".join(f"{p.ru} в {SIGN_RU[p.sign]}" for p in own)
        lines.append(f"Управители «в своих правах»: {s}.")
    else:
        lines.append("Ни один управитель не стоит в собственном знаке.")
    rets = [p for p in chart.placements if p.retrograde]
    if rets:
        lines.append("Ретроградны: " + ", ".join(p.ru for p in rets) + ".")
    hard = [a for a in chart.aspects if a.name in ("Square", "Opposition", "Conjunction")]
    names = {p.key: p.ru for p in chart.placements}
    if hard:
        lines.append("Напряжённые/соединительные аспекты:")
        for a in hard[:8]:
            arrow = "→" if a.applying else "←" if a.applying is False else "·"
            lines.append(f"  {names.get(a.p1, a.p1)} {a.name} {names.get(a.p2, a.p2)} (орб {a.orb:.1f}° {arrow})")
    if focus:
        lines.append(f"\nФокус вопроса: {focus}")
    return "\n".join(lines)


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache = InterpretationCache(settings.cache_max)

    # -- public ---------------------------------------------------------------
    def interpret(self, chart: TwelveChart, *, chash: str,
                  focus: str | None = None, lang: str = "ru",
                  refresh: bool = False) -> dict:
        key = f"{chash}|{lang}|{(focus or '').strip().lower()}"
        if not refresh:
            hit = self.cache.get(key)
            if hit:
                text, model, usage = hit
                return {"interpretation": text, "cached": True,
                        "model": model, "usage": usage}

        if self.settings.llm_mode == "openai":
            text, model, usage = self._call_openai(chart, focus, lang)
        else:
            text, model, usage = _mock_interpretation(chart, focus), "mock", None

        self.cache.put(key, (text, model, usage))
        return {"interpretation": text, "cached": False,
                "model": model, "usage": usage}

    @staticmethod
    def build_prompt(chart: TwelveChart, lang: str = "ru") -> str:
        return _user_prompt(chart, None, lang)

    @staticmethod
    def aspect_prompt(chart: TwelveChart, p1: str, p2: str,
                      aspect_name: str) -> str:
        # package-level aspect_prompt(chart, p1_key, p2_key, aspect_name)
        return aspect_prompt(chart, p1, p2, aspect_name)

    # -- openai-compatible transport (stdlib only, no extra deps) ------------
    def _call_openai(self, chart: TwelveChart, focus: str | None,
                     lang: str) -> tuple[str, str, dict | None]:
        s = self.settings
        if not s.llm_api_key:
            raise LLMError("ASTRO12_LLM_API_KEY is not set")
        body = json.dumps({
            "model": s.llm_model,
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": SYSTEM_BRIEF_RU},
                {"role": "user", "content": _user_prompt(chart, focus, lang)},
            ],
        }).encode()
        req = urllib.request.Request(
            s.llm_base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {s.llm_api_key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise LLMError(f"LLM provider HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise LLMError(f"LLM provider unreachable: {e}") from e
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError("Unexpected LLM response shape") from e
        return text, s.llm_model, data.get("usage")
