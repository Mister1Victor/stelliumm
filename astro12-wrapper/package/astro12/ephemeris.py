"""Standalone Swiss Ephemeris access for the 12 governing bodies.

Why this exists: astro12 must work *without* modifying stellium, and a chart
built by stellium may be missing Ceres/Eris if the caller forgot
``with_tnos()`` or the Eris .se1 file was absent at build time. This module
computes any of the 12 bodies directly from pyswisseph (a MIT-licensed
binding), with graceful degradation:

- If the Eris asteroid file is missing, we fall back to Moshier
  (analytical) ephemeris mode — no data files required at all.
- Missing bodies are reported in ``TwelveChart.missing`` instead of raising,
  so the program never breaks; callers decide how strict to be.

pyswisseph is imported lazily so pure-data consumers (constants, rulers,
prompt formatting on an existing chart) never need it installed.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from .constants import TWELVE_PLANETS, PlanetInfo

# Cached init state
_initialized_paths: set[str] = set()


def _import_swe():
    try:
        import swisseph as swe  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "astro12 direct calculation requires 'pyswisseph' "
            "(bundled with stellium). Install stellium or run: pip install pyswisseph"
        ) from exc
    return swe


def init_ephemeris(ephe_path: str | None = None) -> Any:
    """Point Swiss Ephemeris at a data directory (default ~/.stellium/ephe)."""
    swe = _import_swe()
    import os
    from pathlib import Path

    if ephe_path is None:
        ephe_path = os.environ.get("STELLIUM_EPHE_PATH") or str(
            Path.home() / ".stellium" / "ephe"
        )
    Path(ephe_path).mkdir(parents=True, exist_ok=True)
    if ephe_path not in _initialized_paths:
        swe.set_ephe_path(ephe_path)
        _initialized_paths.add(ephe_path)
    return swe


def jd_from_utc(when: dt.datetime) -> float:
    """Julian Day UT from a timezone-aware (or naive=UTC) datetime."""
    swe = _import_swe()
    if when.tzinfo is not None:
        when = when.astimezone(dt.timezone.utc)
    return swe.julday(when.year, when.month, when.day,
                      when.hour + when.minute / 60.0 + when.second / 3600.0)


def _calc_body(swe, jd: float, planet: PlanetInfo, flags_base: int):
    """Calculate one body; try high-precision first, then Moshier fallback.

    Note on return codes: pyswisseph's ``swe.calc_ut`` returns the *result
    flags* of the computation (bitmask, e.g. RET_STOPEPH|RET_MOSEPH), not a
    0-on-success code as in the C docs. Success must be judged by the values
    themselves: we require a finite longitude and — when FLG_SPEED was asked
    for — a finite speed in xx[3].
    """
    import math

    last_err: Exception | None = None
    want_speed = bool(flags_base & swe.FLG_SPEED)
    for flags in (flags_base, flags_base | swe.FLG_MOSEPH):
        try:
            xx, ret = swe.calc_ut(jd, planet.swiss_id, flags)
            if math.isfinite(xx[0]) and (not want_speed or math.isfinite(xx[3])):
                return xx
            last_err = RuntimeError(
                f"swe.calc_ut returned non-finite values for {planet.en} "
                f"(ret={ret})")
        except Exception as exc:  # swe raises on missing .se1 files
            last_err = exc
    raise LookupError(str(last_err))


def calculate_twelve(
    when: dt.datetime,
    *,
    ephe_path: str | None = None,
    heliocentric: bool = False,
    sidereal: bool = False,
    ayanamsa: int | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Geographic-free calculation of all 12 bodies at an instant.

    Returns (rows, missing): each row is a plain dict with longitude, sign,
    sign_degree, speed, retrograde, distance, plus the planet key. ``missing``
    lists keys that could not be computed even in Moshier mode.
    """
    swe = init_ephemeris(ephe_path)
    jd = jd_from_utc(when)

    flags = swe.FLG_SPEED
    if heliocentric:
        flags |= swe.FLG_HELCTR
    if sidereal:
        flags |= swe.FLG_SIDEREAL
        if ayanamsa is not None:
            swe.set_sid_mode(ayanamsa)
        # In sidereal mode force Moshier for planets (no reliance on files)
        flags |= swe.FLG_MOSEPH

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for p in TWELVE_PLANETS:
        try:
            xx = _calc_body(swe, jd, p, flags)
        except Exception:
            missing.append(p.key)
            continue
        lon = xx[0] % 360.0
        rows.append({
            "key": p.key,
            "order": p.order,
            "longitude": round(lon, 6),
            "sign_index": int(lon // 30),
            "sign_degree": round(lon % 30.0, 6),
            "speed": round(xx[3], 8),
            "retrograde": xx[3] < 0,
            "distance": round(xx[2], 6),
            "latitude": round(xx[1], 6),
        })
    return rows, missing
