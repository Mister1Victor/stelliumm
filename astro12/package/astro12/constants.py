"""Authoritative data for the School of 12 Planets system.

Pure-data module: no imports from stellium, no side effects. This keeps the
licensing boundary clean and makes the tables easy to audit against the
school's canon.

Two core tables:

1. TWELVE_PLANETS — the 12 governing bodies ordered by real physical speed of
   revolution around the Sun (slowest -> fastest):
   Eris -> Pluto -> Neptune -> Uranus -> Saturn -> Jupiter -> Ceres -> Mars ->
   Venus -> Mercury -> Sun -> Moon

2. SIGN_RULERS — sign -> ruler in the author's system:
   Aries-Mars, Taurus-Venus, Gemini-Mercury, Cancer-Moon, Leo-Sun,
   Virgo-Eris, Libra-Pluto, Scorpio-Neptune, Sagittarius-Uranus,
   Capricorn-Saturn, Aquarius-Jupiter, Pisces-Ceres
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlanetInfo:
    """Static description of one of the 12 governing bodies."""

    key: str            # canonical English key used throughout astro12
    order: int          # 1..12, slowest orbit -> fastest orbit
    symbol: str         # glyph used by the school ("ERa" for Eris per spec)
    ru: str             # Russian name (UI / LLM prompts for the school)
    en: str             # English name
    sidereal_years: float  # orbital period around the Sun, in Earth years
    swiss_id: int | None   # pyswisseph body id (None = not a native SE id)
    aliases: tuple[str, ...] = ()  # names this body may appear under in a chart


# --- The 12 governors, slowest -> fastest -------------------------------------
TWELVE_PLANETS: tuple[PlanetInfo, ...] = (
    PlanetInfo("eris",      1,  "ERa", "Эрида",   "Eris",      558.0, 136199 + 10000,
             ("Eris",)),
    PlanetInfo("pluto",     2,  "♇",  "Плутон",  "Pluto",     248.0, 9,
             ("Pluto",)),
    PlanetInfo("neptune",   3,  "♆",  "Нептун",  "Neptune",   165.0, 8,
             ("Neptune",)),
    PlanetInfo("uranus",    4,  "♅",  "Уран",    "Uranus",    84.0,  7,
             ("Uranus",)),
    PlanetInfo("saturn",    5,  "♄",  "Сатурн",  "Saturn",    29.5,  6,
             ("Saturn",)),
    PlanetInfo("jupiter",   6,  "♃",  "Юпитер",  "Jupiter",   11.9,  5,
             ("Jupiter",)),
    PlanetInfo("ceres",     7,  "⚳",  "Церера",  "Ceres",     4.6,   17,
             ("Ceres",)),
    PlanetInfo("mars",      8,  "♂",  "Марс",    "Mars",      1.88,  4,
             ("Mars",)),
    PlanetInfo("venus",     9,  "♀",  "Венера",  "Venus",     0.62,  3,
             ("Venus",)),
    PlanetInfo("mercury",  10,  "☿",  "Меркурий","Mercury",   0.24,  2,
             ("Mercury",)),
    PlanetInfo("sun",      11,  "☉",  "Солнце",  "Sun",       0.0,   0,
             ("Sun",)),
    PlanetInfo("moon",     12,  "☽",  "Луна",    "Moon",      0.075, 1,
             ("Moon",)),
)

PLANETS_BY_KEY: dict[str, PlanetInfo] = {p.key: p for p in TWELVE_PLANETS}
PLANET_ORDER: tuple[str, ...] = tuple(p.key for p in TWELVE_PLANETS)

# Reverse lookup: any chart-object name -> planet key
NAME_TO_KEY: dict[str, str] = {}
for _p in TWELVE_PLANETS:
    for _alias in _p.aliases:
        NAME_TO_KEY[_alias.lower()] = _p.key
    NAME_TO_KEY[_p.key] = _p.key
    NAME_TO_KEY[_p.en.lower()] = _p.key


# --- Signs ---------------------------------------------------------------------
SIGNS_EN: tuple[str, ...] = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

SIGN_RU: dict[str, str] = {
    "Aries": "Овен", "Taurus": "Телец", "Gemini": "Близнецы",
    "Cancer": "Рак", "Leo": "Лев", "Virgo": "Дева",
    "Libra": "Весы", "Scorpio": "Скорпион", "Sagittarius": "Стрелец",
    "Capricorn": "Козерог", "Aquarius": "Водолей", "Pisces": "Рыбы",
}

SIGN_SYMBOL: dict[str, str] = {
    "Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
    "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
    "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓",
}

# --- Sign rulers in the School-of-12-Planets system -----------------------------
# sign (EN) -> planet key
SIGN_RULERS: dict[str, str] = {
    "Aries": "mars",
    "Taurus": "venus",
    "Gemini": "mercury",
    "Cancer": "moon",
    "Leo": "sun",
    "Virgo": "eris",
    "Libra": "pluto",
    "Scorpio": "neptune",
    "Sagittarius": "uranus",
    "Capricorn": "saturn",
    "Aquarius": "jupiter",
    "Pisces": "ceres",
}

# Derived: planet key -> the sign it governs
RULER_TO_SIGN: dict[str, str] = {v: k for k, v in SIGN_RULERS.items()}

# Names of the bodies that must be present in a chart for a complete
# 12-planets reading (Swiss Ephemeris object names).
REQUIRED_CHART_OBJECTS: tuple[str, ...] = (
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
    "Uranus", "Neptune", "Pluto", "Ceres", "Eris",
)

# Bodies whose ephemeris needs an extra .se1 file (with hint command).
EPHEMERIS_HINTS: dict[str, str] = {
    "Eris": "stellium ephemeris download-asteroid 136199",
}
