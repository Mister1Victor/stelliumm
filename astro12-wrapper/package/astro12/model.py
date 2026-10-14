"""The TwelveChart model — pure data, zero dependency on stellium.

A TwelveChart holds the 12 governing bodies with their sign placements and
the aspects between them (computed here with plain math, so this module is
importable even where pyswisseph/stellium are not).

Everything degrades gracefully: if a body is missing it appears in
``missing``; aspects involving absent bodies simply don't exist.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from .constants import (
    PLANETS_BY_KEY,
    RULER_TO_SIGN,
    SIGNS_EN,
    SIGN_RU,
    SIGN_RULERS,
    SIGN_SYMBOL,
)

# Aspect definitions used by the school (name, exact angle, default orb)
ASPECTS: tuple[tuple[str, int, float], ...] = (
    ("Conjunction", 0, 8.0),
    ("Opposition", 180, 8.0),
    ("Trine", 120, 7.0),
    ("Square", 90, 7.0),
    ("Sextile", 60, 5.0),
)

ASPECT_SYMBOL = {"Conjunction": "☌", "Opposition": "☍", "Trine": "△",
                 "Square": "□", "Sextile": "⚹"}


@dataclass(frozen=True)
class BodyPlacement:
    key: str
    longitude: float
    sign: str              # English sign name
    sign_degree: float     # 0..30 within sign
    speed: float
    retrograde: bool
    distance: float = 0.0

    @property
    def symbol(self) -> str:
        return PLANETS_BY_KEY[self.key].symbol

    @property
    def ru(self) -> str:
        return PLANETS_BY_KEY[self.key].ru

    @property
    def ruler_of(self) -> str | None:
        """Sign this body governs in the 12-planets system (if any)."""
        return RULER_TO_SIGN.get(self.key)

    @property
    def house_of_own_ruler(self) -> bool:
        """True when the body sits in the sign it governs ('в своих правах')."""
        return self.sign == RULER_TO_SIGN.get(self.key)

    @property
    def dispositor_key(self) -> str:
        """Key of the planet that rules the sign this body occupies."""
        return SIGN_RULERS[self.sign]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key, "symbol": self.symbol, "name_ru": self.ru,
            "longitude": round(self.longitude, 4), "sign": self.sign,
            "sign_ru": SIGN_RU[self.sign], "sign_symbol": SIGN_SYMBOL[self.sign],
            "sign_degree": round(self.sign_degree, 4),
            "speed": round(self.speed, 5), "retrograde": self.retrograde,
            "distance": round(self.distance, 4),
            "ruler_of": self.ruler_of, "in_own_sign": self.house_of_own_ruler,
            "dispositor": self.dispositor_key,
        }


@dataclass(frozen=True)
class AspectBetween:
    p1: str                # planet key
    p2: str                # planet key
    name: str
    angle: int
    orb: float
    applying: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"p1": self.p1, "p2": self.p2, "aspect": self.name,
                "symbol": ASPECT_SYMBOL.get(self.name, ""), "angle": self.angle,
                "orb": round(self.orb, 3), "applying": self.applying}


def _norm(a: float) -> float:
    a %= 360.0
    return a if a <= 180 else 360 - a


def compute_aspects(placements: list[BodyPlacement]) -> list[AspectBetween]:
    """All pairwise aspects among the given bodies (pure math)."""
    by_key = {p.key: p for p in placements}
    out: list[AspectBetween] = []
    keys = [p.key for p in placements]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = by_key[keys[i]], by_key[keys[j]]
            diff = _norm(a.longitude - b.longitude)
            for name, angle, orb_max in ASPECTS:
                orb = abs(diff - angle)
                if orb <= orb_max:
                    # applying? faster body moving toward exactness
                    applying: bool | None = None
                    try:
                        da = _norm(a.longitude - b.longitude)
                        rel_speed = a.speed - b.speed
                        if angle == 0:
                            pass
                        approaching = (da > angle and rel_speed < 0) or \
                                      (da < angle and rel_speed > 0)
                        applying = bool(approaching)
                    except Exception:
                        applying = None
                    out.append(AspectBetween(keys[i], keys[j], name, angle,
                                             round(orb, 4), applying))
                    break
    return out


@dataclass
class TwelveChart:
    """Snapshot of the 12 governors at one instant."""

    when_utc: dt.datetime | None = None
    placements: list[BodyPlacement] = field(default_factory=list)
    aspects: list[AspectBetween] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)   # planet keys not computed
    source: str = "direct"          # "direct" | "stellium_chart"
    meta: dict[str, Any] = field(default_factory=dict)

    # -- convenience ---------------------------------------------------------
    def get(self, key: str) -> BodyPlacement | None:
        return next((p for p in self.placements if p.key == key), None)

    @property
    def by_sign(self) -> dict[str, list[BodyPlacement]]:
        d: dict[str, list[BodyPlacement]] = {s: [] for s in SIGNS_EN}
        for p in self.placements:
            d[p.sign].append(p)
        return d

    @property
    def rulers_positioned(self) -> dict[str, str]:
        """sign -> placement sign of that sign's ruler (dispositor chain)."""
        return {sign: p.sign for sign, p in
                ((SIGN_RULERS[k], self.get(k)) for k in SIGN_RULERS.values())
                if p is not None}

    def aspects_for(self, key: str) -> list[AspectBetween]:
        return [a for a in self.aspects if key in (a.p1, a.p2)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": "School of 12 Planets",
            "when_utc": self.when_utc.isoformat() if self.when_utc else None,
            "source": self.source,
            "missing": list(self.missing),
            "placements": [p.to_dict() for p in self.placements],
            "aspects": [a.to_dict() for a in self.aspects],
            "meta": dict(self.meta),
        }

    @classmethod
    def from_rows(cls, rows: list[dict[str, Any]], when_utc: dt.datetime,
                  missing: list[str] | None = None, source: str = "direct",
                  compute: bool = True) -> "TwelveChart":
        placements = [
            BodyPlacement(
                key=r["key"], longitude=r["longitude"],
                sign=SIGNS_EN[r["sign_index"]], sign_degree=r["sign_degree"],
                speed=r["speed"], retrograde=r["retrograde"],
                distance=r.get("distance", 0.0),
            )
            for r in rows if r["key"] in PLANETS_BY_KEY
        ]
        aspects = compute_aspects(placements) if compute else []
        return cls(when_utc=when_utc, placements=placements, aspects=aspects,
                   missing=list(missing or []), source=source)
