"""Configuration models for chart calculation."""

from dataclasses import dataclass, field

from stellium.core.ayanamsa import ZodiacType


@dataclass
class AspectConfig:
    """Configuration for aspect calculations.

    Will be passed directly into the AspectEngine.
    """

    # Which aspects to calculate (by name - angles are looked up from registry)
    aspects: list[str] = field(
        default_factory=lambda: [
            "Conjunction",
            "Sextile",
            "Square",
            "Trine",
            "Opposition",
        ]
    )

    # Which object types to include in aspect calculations
    # (The AspectEngine will use this to filter pairs)
    include_angles: bool = True
    include_nodes: bool = True
    include_asteroids: bool = True


@dataclass
class CalculationConfig:
    """Overall configuration for chart calculations.

    Passed to the ChartBuilder.
    """

    # Which objects to calculate
    include_planets: list[str] = field(
        default_factory=lambda: [
            "Sun",
            "Moon",
            "Mercury",
            "Venus",
            "Mars",
            "Jupiter",
            "Saturn",
            "Uranus",
            "Neptune",
            "Pluto",
        ]
    )
    include_nodes: bool = False  # North & South Nodes excluded by default
    include_chiron: bool = False  # Chiron excluded by default
    include_points: list[str] = field(
        default_factory=list
    )  # No Lilith (Mean Apogee) by default
    include_asteroids: list[str] = field(
        default_factory=lambda: ["Ceres", "Eris"]
    )  # Ceres and Eris included by default

    # Zodiac system configuration
    zodiac_type: ZodiacType = ZodiacType.TROPICAL
    ayanamsa: str | None = None  # Only used if zodiac_type is SIDEREAL

    # Coordinate system
    heliocentric: bool = False  # Sun-centered instead of Earth-centered

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Set default ayanamsa if sidereal but none specified
        if self.zodiac_type == ZodiacType.SIDEREAL and self.ayanamsa is None:
            object.__setattr__(self, "ayanamsa", "lahiri")  # Default to Lahiri

    @classmethod
    def minimal(cls) -> "CalculationConfig":
        """Minimal calculation - planets only."""
        return cls(
            include_nodes=False,
            include_chiron=False,
            include_points=[],
            include_asteroids=["Eris"],  # Keep Eris in minimal as well
        )

    @classmethod
    def comprehensive(cls) -> "CalculationConfig":
        """Comprehensive calculation -- a well-rounded set."""
        return cls(
            include_nodes=False,
            include_chiron=["Mean Apogee", "True Apogee"],  # Both Liliths
            include_points=False,
            # The big-four asteroids plus Hygiea (the fourth-largest, and the fifth of the
            # classical "big five"); Hygiea was silently absent until its Swiss Ephemeris
            # id was corrected. Chiron/Pholus are the centaurs.
            include_asteroids=[
                "Chiron",
                "Pholus",
                "Ceres",
                "Pallas",
                "Juno",
                "Vesta",
                "Hygiea",
                "Eris",
            ],
        )
