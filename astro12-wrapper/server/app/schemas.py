"""Request/response schemas (pydantic v2).

Kept intentionally permissive: unknown fields are ignored, so adding data to
the astro12 model never breaks older clients.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class ChartRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    when_utc: datetime = Field(
        ..., description="Birth/event moment, ISO 8601. Naive = UTC.")
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    name: str | None = Field(None, max_length=120)
    place: str | None = Field(None, max_length=160)
    heliocentric: bool = False
    sidereal: bool = False

    @field_validator("when_utc")
    @classmethod
    def _ensure_tz(cls, v: datetime) -> datetime:
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)


class AspectOut(BaseModel):
    p1: str
    p2: str
    symbol: str = ""
    aspect: str
    angle: int
    orb: float
    applying: bool | None = None


class PlacementOut(BaseModel):
    key: str
    symbol: str
    name_ru: str
    longitude: float
    sign: str
    sign_ru: str
    sign_symbol: str
    sign_degree: float
    speed: float
    retrograde: bool
    ruler_of: str | None = None
    in_own_sign: bool = False
    dispositor: str | None = None


class ChartOut(BaseModel):
    system: str
    when_utc: str
    source: str
    missing: list[str] = []
    placements: list[PlacementOut]
    aspects: list[AspectOut]
    meta: dict = {}


class PromptOut(BaseModel):
    prompt: str
    system_brief: str
    chart_hash: str


class InterpretRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chart_hash: str | None = Field(
        None, description="Hash from /v1/prompt — reuse cached interpretation.")
    when_utc: datetime | None = None
    name: str | None = Field(None, max_length=120)
    focus: str | None = Field(
        None, max_length=300,
        description="Optional question, e.g. 'какие аспекты у Эриды?'")
    lang: str = Field("ru", pattern="^(ru|en)$")
    refresh: bool = False

    @field_validator("chart_hash")
    @classmethod
    def _check_hash(cls, v: str | None) -> str | None:
        if v is not None and not _HEX_RE.match(v):
            raise ValueError("chart_hash must be a 64-hex digest from /v1/prompt")
        return v

    @field_validator("when_utc")
    @classmethod
    def _ensure_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)


class InterpretOut(BaseModel):
    chart_hash: str
    interpretation: str
    cached: bool
    model: str
    usage: dict | None = None
