"""Adapter between stellium charts and astro12.

This is the ONLY astro12 module that touches stellium, and even here the
import is lazy and optional:

- ``from_stellium_chart(chart)`` accepts any object exposing a stellium-like
  duck-typed surface (``positions``, ``aspects``, ``house_placements``,
  ``datetime.utc_datetime``). It never imports stellium itself, so AGPL code
  is only *read via attributes* — no linking of stellium internals into our
  data model.
- ``build_chart(...)`` optionally uses stellium's ChartBuilder when installed
  (a pure *call* of its public API, which is the standard way to use an AGPL
  library from a permissively licensed wrapper; distribution of the wrapper
  alone does not make the wrapper a derivative work, though combined products
  must respect AGPL — see package README "Licensing").

Fails soft everywhere: unknown object names are ignored, missing bodies land
in ``TwelveChart.missing``.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from .constants import NAME_TO_KEY, PLANETS_BY_KEY, SIGNS_EN
from .model import AspectBetween, BodyPlacement, TwelveChart, compute_aspects


def _sign_from_longitude(lon: float) -> str:
    return SIGNS_EN[int(lon // 30) % 12]


def _pos_to_placement(pos: Any) -> BodyPlacement | None:
    key = NAME_TO_KEY.get(str(getattr(pos, "name", "")).lower())
    if key is None:
        return None
    lon = float(pos.longitude) % 360.0
    sign = getattr(pos, "sign", None)
    if not isinstance(sign, str) or sign not in SIGNS_EN:
        sign = _sign_from_longitude(lon)
    return BodyPlacement(
        key=key,
        longitude=lon,
        sign=sign,
        sign_degree=float(getattr(pos, "sign_degree", lon % 30.0)),
        speed=float(getattr(pos, "speed_longitude", 0.0)),
        retrograde=bool(getattr(pos, "is_retrograde", False))
        or float(getattr(pos, "speed_longitude", 0.0)) < 0,
        distance=float(getattr(pos, "distance", 0.0)),
    )


def from_stellium_chart(chart: Any, *, recompute_aspects: bool = True) -> TwelveChart:
    """Build a TwelveChart from an existing stellium CalculatedChart.

    The chart must have been built with Ceres and Eris included
    (e.g. ``ChartBuilder...with_tnos()``); anything missing is reported in
    ``.missing`` rather than raising. House placements and birth metadata are
    carried over best-effort.
    """
    placements: list[BodyPlacement] = []
    seen: set[str] = set()
    for pos in getattr(chart, "positions", ()):
        p = _pos_to_placement(pos)
        if p is not None and p.key not in seen:
            placements.append(p)
            seen.add(p.key)

    # house numbers per planet (first house system)
    houses: dict[str, int] = {}
    try:
        hp = getattr(chart, "house_placements", {}) or {}
        first = next(iter(hp.values()), {})
        for name, num in (first or {}).items():
            key = NAME_TO_KEY.get(str(name).lower())
            if key:
                houses[key] = int(num)
    except Exception:
        pass

    aspects: list[AspectBetween] = []
    if recompute_aspects:
        aspects = compute_aspects(placements)
    else:
        for a in getattr(chart, "aspects", ()):
            k1 = NAME_TO_KEY.get(str(a.object1.name).lower())
            k2 = NAME_TO_KEY.get(str(a.object2.name).lower())
            if k1 and k2:
                aspects.append(AspectBetween(k1, k2, str(a.aspect_name),
                                             int(a.aspect_degree),
                                             float(a.orb),
                                             bool(a.is_applying)
                                             if a.is_applying is not None else None))

    when = None
    cdt = getattr(chart, "datetime", None)
    if cdt is not None:
        when = getattr(cdt, "utc_datetime", None)

    meta: dict[str, Any] = {}
    loc = getattr(chart, "location", None)
    if loc is not None:
        meta["location"] = {"lat": getattr(loc, "latitude", None),
                            "lon": getattr(loc, "longitude", None),
                            "name": getattr(loc, "name", None)}
    meta["houses"] = houses
    name = getattr(chart, "name", None) or (getattr(chart, "metadata", {}) or {}).get("name")
    if name:
        meta["chart_name"] = str(name)

    missing = [k for k in PLANETS_BY_KEY if k not in seen]
    return TwelveChart(when_utc=when, placements=placements, aspects=aspects,
                       missing=missing, source="stellium_chart", meta=meta)


def build_chart(
    when: dt.datetime,
    location: tuple[float, float] | None = None,
    *,
    name: str | None = None,
    house_system: str = "Placidus",
    ephe_path: str | None = None,
    strict: bool = False,
) -> tuple[Any, TwelveChart]:
    """Convenience: stellium natal chart + TwelveChart in one call.

    Requires stellium installed (public-API usage only). If stellium cannot
    supply Eris/Ceres, we top up positions with the direct ephemeris fallback
    so the result is still complete whenever possible.

    Returns (stellium_chart_or_None, twelve_chart). Never raises on missing
    bodies unless ``strict=True``.
    """
    twelve: TwelveChart | None = None
    schart = None
    try:
        from stellium.core import ChartBuilder  # type: ignore

        lat, lon = location if location else (55.75, 37.62)
        b = ChartBuilder.from_details(when, (lat, lon), name=name)
        b = b.with_tnos().with_named_asteroids()
        schart = b.calculate()
        twelve = from_stellium_chart(schart)
    except Exception:
        if strict:
            raise
        twelve = None

    # Fallback / top-up via direct ephemeris
    if twelve is None or twelve.missing:
        from .ephemeris import calculate_twelve

        rows, missing = calculate_twelve(when, ephe_path=ephe_path)
        if twelve is None or len(rows) > len(twelve.placements):
            from .model import TwelveChart as TC

            merged_rows = rows
            merged_missing = missing
            if twelve is not None:
                have = {r["key"] for r in rows}
                extra = [
                    {"key": p.key, "order": PLANETS_BY_KEY[p.key].order,
                     "longitude": p.longitude,
                     "sign_index": SIGNS_EN.index(p.sign),
                     "sign_degree": p.sign_degree, "speed": p.speed,
                     "retrograde": p.retrograde, "distance": p.distance}
                    for p in twelve.placements if p.key not in have
                ]
                merged_rows = rows + extra
                merged_missing = [m for m in missing if m not in have]
            fresh = TC.from_rows(merged_rows, when, merged_missing,
                                 source="direct+stellium" if schart else "direct")
            if schart is not None:
                fresh.meta.update(twelve.meta)
            twelve = fresh

    if strict and twelve and twelve.missing:
        raise RuntimeError(f"Missing bodies: {twelve.missing}")
    return schart, twelve
