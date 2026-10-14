"""Runtime settings for the astro12 API.

Everything is env-driven so one image can run dev/staging/prod:

    ASTRO12_API_KEYS          comma-separated bearer tokens ("" = open mode)
    ASTRO12_EPHE_PATH         Swiss Ephemeris data dir (default ~/.stellium/ephe)
    ASTRO12_RATE_LIMIT        requests per minute per client (0 = off)
    ASTRO12_LLM_MODE          mock | openai  (openai needs ASTRO12_LLM_API_KEY)
    ASTRO12_LLM_BASE_URL / ASTRO12_LLM_MODEL  OpenAI-compatible endpoint
    ASTRO12_CACHE_MAX         max cached interpretations (LRU, default 512)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _split(v: str) -> list[str]:
    return [s.strip() for s in v.split(",") if s.strip()]


@dataclass
class Settings:
    api_keys: list[str] = field(default_factory=list)
    ephe_path: str | None = None
    rate_limit_per_min: int = 60
    llm_mode: str = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    cache_max: int = 512
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_keys=_split(os.environ.get("ASTRO12_API_KEYS", "")),
            ephe_path=os.environ.get("ASTRO12_EPHE_PATH") or None,
            rate_limit_per_min=int(os.environ.get("ASTRO12_RATE_LIMIT", "60")),
            llm_mode=os.environ.get("ASTRO12_LLM_MODE", "mock"),
            llm_base_url=os.environ.get(
                "ASTRO12_LLM_BASE_URL", "https://api.openai.com/v1"),
            llm_model=os.environ.get("ASTRO12_LLM_MODEL", "gpt-4o-mini"),
            llm_api_key=os.environ.get("ASTRO12_LLM_API_KEY", ""),
            cache_max=int(os.environ.get("ASTRO12_CACHE_MAX", "512")),
            cors_origins=_split(os.environ.get("ASTRO12_CORS_ORIGINS", "*"))
            or ["*"],
        )
