"""LLM prompt generation for the Astro12AI interpretation engine.

Produces compact, deterministic markdown describing a TwelveChart in the
vocabulary of the School of 12 Planets: governors, their signs, rulerships,
dispositor links and aspects. Designed to be pasted straight into an LLM
system/user prompt (see github.com/Mister1Victor/Astro12AI).

Pure string formatting — no heavy deps, safe on any request path.
"""

from __future__ import annotations

from .constants import (
    PLANETS_BY_KEY,
    RULER_TO_SIGN,
    SIGNS_EN,
    SIGN_RU,
    SIGN_RULERS,
    TWELVE_PLANETS,
)
from .model import TwelveChart

SYSTEM_BRIEF_RU = (
    "Ты — интерпретатор авторской системы «Школа 12 Планет». 12 планет-"
    "управителей по порядку реальной скорости обращения вокруг Солнца "
    "(от самой медленной к быстрой): Эрида → Плутон → Нептун → Уран → "
    "Сатурн → Юпитер → Церера → Марс → Венера → Меркурий → Солнце → Луна. "
    "Управители знаков: Овен—Марс, Телец—Венера, Близнецы—Меркурий, Рак—Луна, "
    "Лев—Солнце, Дева—Эрида, Весы—Плутон, Скорпион—Нептун, Стрелец—Уран, "
    "Козерог—Сатурн, Водолей—Юпитер, Рыбы—Церера. Отвечай на русском, "
    "опирайся только на данные карты."
)


def _fmt_deg(x: float) -> str:
    d = int(x)
    m = int(round((x - d) * 60))
    if m == 60:
        d, m = d + 1, 0
    return f"{d}°{m:02d}"


def chart_to_prompt(chart: TwelveChart, *, lang: str = "ru",
                    include_aspects: bool = True,
                    max_orb: float | None = None) -> str:
    """Render a TwelveChart as LLM-ready markdown."""
    lines: list[str] = []
    when = chart.when_utc.strftime("%Y-%m-%d %H:%M UTC") if chart.when_utc else "—"
    name = chart.meta.get("chart_name") or ""
    title = f"# Карта 12 планет {name}".strip()
    lines.append(title)
    lines.append(f"Дата расчёта: {when}")
    loc = chart.meta.get("location") or {}
    if loc.get("name"):
        lines.append(f"Место: {loc['name']}")
    houses = chart.meta.get("houses") or {}

    lines.append("\n## Планеты-управители (по скорости: медленная → быстрая)")
    for p in TWELVE_PLANETS:
        pl = chart.get(p.key)
        if pl is None:
            continue
        own = " *(в своём знаке)*" if pl.house_of_own_ruler else ""
        ret = " R" if pl.retrograde else ""
        ru_sign = SIGN_RU[pl.sign]
        extra = f", дом {houses[p.key]}" if p.key in houses else ""
        lines.append(
            f"- {p.order}. {p.ru} {p.symbol}: {SIGN_RU[pl.sign]} "
            f"{_fmt_deg(pl.sign_degree)}{ret}{extra}{own}"
        )

    if chart.missing:
        miss = ", ".join(PLANETS_BY_KEY[k].ru for k in chart.missing)
        lines.append(f"- НЕ рассчитаны: {miss}")

    lines.append("\n## Управители знаков в этой карте")
    for sign_en in SIGNS_EN:
        ruler_key = SIGN_RULERS[sign_en]
        pl = chart.get(ruler_key)
        where = SIGN_RU[pl.sign] + " " + _fmt_deg(pl.sign_degree) if pl else "н/д"
        lines.append(
            f"- {SIGN_RU[sign_en]} ({sign_en}) → управитель "
            f"{PLANETS_BY_KEY[ruler_key].ru} {PLANETS_BY_KEY[ruler_key].symbol} "
            f"в {where}"
        )

    if include_aspects:
        lines.append("\n## Аспекты между 12 управителями")
        shown = 0
        for a in sorted(chart.aspects, key=lambda x: x.orb):
            if max_orb is not None and a.orb > max_orb:
                continue
            p1, p2 = PLANETS_BY_KEY[a.p1], PLANETS_BY_KEY[a.p2]
            app = "" if a.applying is None else (" (сходящийся)" if a.applying
                                                 else " (расходящийся)")
            lines.append(
                f"- {p1.ru} {p1.symbol} {a.name} {p2.ru} {p2.symbol} "
                f"(орб {a.orb:.1f}°{app})"
            )
            shown += 1
        if shown == 0:
            lines.append("- крупных аспектов в орбитах не найдено")

    lines.append("\n## Задание")
    lines.append(
        "Дай целостную интерпретацию: где живут управители знаков, какие "
        "аспекты формируют ведущие темы, что усилено ретроградностью и "
        "нахождением планеты в собственном знаке."
    )
    return "\n".join(lines)


def aspect_prompt(chart: TwelveChart, p1_key: str, p2_key: str,
                  aspect_name: str) -> str:
    """Single-aspect micro-prompt for granular LLM interpretation."""
    a1, a2 = PLANETS_BY_KEY[p1_key], PLANETS_BY_KEY[p2_key]
    pl1, pl2 = chart.get(p1_key), chart.get(p2_key)
    if pl1 is None or pl2 is None:
        raise KeyError("Both planets must be present in the chart")
    asp = next((x for x in chart.aspects if x.p1 == p1_key and x.p2 == p2_key
                and x.name == aspect_name), None)
    orb = f", орбител {asp.orb:.1f}°" if asp else ""
    return (
        f"Интерпретируй аспект в системе Школы 12 Планет: {a1.ru} {a1.symbol} "
        f"({SIGN_RU[pl1.sign]} {_fmt_deg(pl1.sign_degree)}, управитель знака "
        f"{SIGN_RU[RULER_TO_SIGN[a1.key]] if a1.key in RULER_TO_SIGN else '—'}) "
        f"{aspect_name} {a2.ru} {a2.symbol} "
        f"({SIGN_RU[pl2.sign]} {_fmt_deg(pl2.sign_degree)}){orb}."
    )
