"""Chart service: astro12 direct-mode calculations + deterministic hashing.

The hash is the cache/identity key for interpretations: it covers the UTC
minute, heliocentric/sidereal flags and the *rounded* longitudes of all 12
bodies (0.01° — below any meaningful orb), so identical charts always map to
the same LLM answer and billing record.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timezone

from astro12 import calculate
from astro12.model import TwelveChart

from .config import Settings


def build_chart(req, settings: Settings) -> TwelveChart:
    """Compute a TwelveChart from a validated ChartRequest."""
    when = req.when_utc.astimezone(timezone.utc).replace(tzinfo=None)
    chart = calculate(
        when,
        ephe_path=settings.ephe_path,
        heliocentric=req.heliocentric,
        sidereal=req.sidereal,
    )
    # record the mode *before* copying meta so chart_hash() sees it
    if req.heliocentric:
        chart.meta["heliocentric"] = True
    if req.sidereal:
        chart.meta["sidereal"] = True
    meta = dict(chart.meta)
    if req.name:
        meta["chart_name"] = req.name
    loc: dict = {}
    if req.lat is not None:
        loc["lat"] = req.lat
    if req.lon is not None:
        loc["lon"] = req.lon
    if req.place:
        loc["name"] = req.place
    if loc:
        meta["location"] = loc
    chart.meta = meta
    return chart


def chart_hash(chart: TwelveChart) -> str:
    """Stable sha256 over the chart's astronomical content."""
    payload = {
        "minute": chart.when_utc.strftime("%Y-%m-%dT%H:%MZ")
        if chart.when_utc else None,
        "helio": bool(chart.meta.get("heliocentric")),
        "sid": bool(chart.meta.get("sidereal")),
        "placements": sorted(
            (p.key, round(p.longitude, 2)) for p in chart.placements
        ),
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()
