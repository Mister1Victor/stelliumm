"""astro12 — School of 12 Planets toolkit (wrapper around stellium).

Public API:
    calculate(when)            -> TwelveChart (direct pyswisseph, no stellium needed)
    build_chart(when, loc)     -> (stellium_chart | None, TwelveChart)
    from_stellium_chart(chart) -> TwelveChart
    chart_to_prompt(chart)     -> markdown for the Astro12AI LLM engine
    constants.*                -> pure data tables (rulers, order, glyphs)

License: MIT. Depends on stellium (AGPL-3.0) only *optionally* and only via
its public API; core functionality works with pyswisseph alone.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

__version__ = "0.1.0"

from .constants import (  # noqa: E402
    PLANET_ORDER,
    PLANETS_BY_KEY,
    RULER_TO_SIGN,
    SIGNS_EN,
    SIGN_RU,
    SIGN_RULERS,
    SIGN_SYMBOL,
    TWELVE_PLANETS,
)
from .model import (  # noqa: E402
    ASPECTS,
    AspectBetween,
    BodyPlacement,
    TwelveChart,
    compute_aspects,
)
from .prompt import SYSTEM_BRIEF_RU, aspect_prompt, chart_to_prompt  # noqa: E402


def calculate(when: dt.datetime, *, ephe_path: str | None = None,
              heliocentric: bool = False) -> TwelveChart:
    """Compute the 12 governors directly with Swiss Ephemeris (no stellium)."""
    from .ephemeris import calculate_twelve

    rows, missing = calculate_twelve(when, ephe_path=ephe_path,
                                     heliocentric=heliocentric)
    return TwelveChart.from_rows(rows, when, missing, source="direct")


def from_stellium_chart(chart: Any, **kw) -> TwelveChart:
    from .stellium_adapter import from_stellium_chart as _f

    return _f(chart, **kw)


def build_chart(when: dt.datetime, location: tuple[float, float] | None = None,
                 **kw) -> tuple[Any, TwelveChart]:
    from .stellium_adapter import build_chart as _b

    return _b(when, location, **kw)


__all__ = [
    "__version__",
    "TWELVE_PLANETS", "PLANETS_BY_KEY", "PLANET_ORDER",
    "SIGN_RULERS", "RULER_TO_SIGN", "SIGNS_EN", "SIGN_RU", "SIGN_SYMBOL",
    "ASPECTS", "TwelveChart", "BodyPlacement", "AspectBetween",
    "compute_aspects", "calculate", "build_chart", "from_stellium_chart",
    "chart_to_prompt", "aspect_prompt", "SYSTEM_BRIEF_RU",
]
