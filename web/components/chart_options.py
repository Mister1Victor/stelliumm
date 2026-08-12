"""
Stellium Web - Chart Options Component

Expandable panels for house systems, components, and visualization options.
"""

from config import (
    ASPECT_MODES,
    ASPECT_PALETTES,
    AYANAMSAS,
    CHART_THEMES,
    COLORS,
    HOUSE_SYSTEMS,
    MOON_PHASE_POSITIONS,
    PLANET_GLYPH_PALETTES,
    TABLE_POSITIONS,
    ZODIAC_PALETTES,
)
from i18n import wt
from nicegui import ui
from state import ChartState

# Список астероидов для выбора
ALL_ASTEROIDS = ["Ceres", "Pallas", "Juno", "Vesta", "Hygiea", "Eris"]


def create_chart_options(state: ChartState, on_change=None):
    """
    Create the chart configuration options panels.

    Args:
        state: ChartState instance to bind to
        on_change: Optional callback when any option changes
    """
    _ = wt()

    def update_field(field: str, value):
        setattr(state, field, value)
        if on_change:
            on_change()

    def toggle_house_system(system: str, checked: bool):
        if checked and system not in state.house_systems:
            state.house_systems.append(system)
        elif not checked and system in state.house_systems:
            state.house_systems.remove(system)
        if on_change:
            on_change()

    def toggle_planet(planet: str, checked: bool):
        if checked and planet not in state.include_planets:
            state.include_planets.append(planet)
        elif not checked and planet in state.include_planets:
            state.include_planets.remove(planet)
        if on_change:
            on_change()

    def toggle_asteroid(asteroid: str, checked: bool):
        if checked and asteroid not in state.include_asteroids:
            state.include_asteroids.append(asteroid)
        elif not checked and asteroid in state.include_asteroids:
            state.include_asteroids.remove(asteroid)
        if on_change:
            on_change()

    with ui.element("div").classes("w-full"):
        # ===== ZODIAC SYSTEM =====
        with ui.expansion(_("Zodiac System"), icon="public").classes(
            "w-full"
        ).props('header-class="text-sm font-medium"'):
            with ui.column().classes("gap-4 p-4"):
                ui.radio(
                    {
                        "tropical": _("Tropical (Western)"),
                        "sidereal": _("Sidereal (Vedic)"),
                    },
                    value=state.zodiac_type,
                    on_change=lambda e: update_field("zodiac_type", e.value),
                ).props("dense")

                with ui.element("div").bind_visibility_from(
                    state, "zodiac_type", backward=lambda x: x == "sidereal"
                ):
                    ui.label(_("Ayanamsa:")).classes("text-sm mt-2").style(
                        f"color: {COLORS['text_muted']}"
                    )
                    ui.select(
                        {code: name for name, code in AYANAMSAS},
                        value=state.ayanamsa,
                        on_change=lambda e: update_field("ayanamsa", e.value),
                    ).classes("w-full")

        # ===== HOUSE SYSTEMS =====
        with ui.expansion(_("House Systems"), icon="home").classes(
            "w-full"
        ).props('header-class="text-sm font-medium"'):
            with ui.column().classes("gap-1 p-4"):
                ui.label(_("Select one or more:")).classes("text-xs mb-2").style(
                    f"color: {COLORS['text_muted']}"
                )

                # Popular
                ui.label(_("Popular")).classes("text-xs font-bold mt-2").style(
                    f"color: {COLORS['secondary']}"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-x-2"):
                    for name, _code in HOUSE_SYSTEMS[:4]:
                        ui.checkbox(
                            name,
                            value=name in state.house_systems,
                            on_change=lambda e, n=name: toggle_house_system(
                                n, e.value
                            ),
                        ).props("dense")

                # Traditional
                ui.label(_("Traditional")).classes("text-xs font-bold mt-3").style(
                    f"color: {COLORS['secondary']}"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-x-2"):
                    for name, _code in HOUSE_SYSTEMS[4:8]:
                        ui.checkbox(
                            name,
                            value=name in state.house_systems,
                            on_change=lambda e, n=name: toggle_house_system(
                                n, e.value
                            ),
                        ).props("dense")

                # Modern & Specialized
                ui.label(_("Modern & Specialized")).classes(
                    "text-xs font-bold mt-3"
                ).style(f"color: {COLORS['secondary']}")
                with ui.element("div").classes("grid grid-cols-2 gap-x-2"):
                    for name, _code in HOUSE_SYSTEMS[8:]:
                        ui.checkbox(
                            name,
                            value=name in state.house_systems,
                            on_change=lambda e, n=name: toggle_house_system(
                                n, e.value
                            ),
                        ).props("dense")

        # ===== CELESTIAL OBJECTS =====
        with ui.expansion(_("Celestial Objects"), icon="star").classes(
            "w-full"
        ).props('header-class="text-sm font-medium"'):
            with ui.column().classes("gap-2 p-4"):
                # Planets
                ui.label(_("Planets")).classes("text-xs font-bold").style(
                    f"color: {COLORS['secondary']}"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-x-2"):
                    for planet in [
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
                    ]:
                        ui.checkbox(
                            _(planet),
                            value=planet in state.include_planets,
                            on_change=lambda e, p=planet: toggle_planet(
                                p, e.value),
                        ).props("dense")

                # Nodes & Points
                ui.label(_("Nodes & Points")).classes("text-xs font-bold mt-3").style(
                    f"color: {COLORS['secondary']}"
                )
                ui.checkbox(
                    _("North & South Nodes"),
                    value=state.include_nodes,
                    on_change=lambda e: update_field("include_nodes", e.value),
                ).props("dense")
                ui.checkbox(
                    _("Chiron"),
                    value=state.include_chiron,
                    on_change=lambda e: update_field(
                        "include_chiron", e.value),
                ).props("dense")
                ui.checkbox(
                    _("Lilith (Mean)"),
                    value=state.include_lilith_mean,
                    on_change=lambda e: update_field(
                        "include_lilith_mean", e.value
                    ),
                ).props("dense")
                ui.checkbox(
                    _("Lilith (True)"),
                    value=state.include_lilith_true,
                    on_change=lambda e: update_field(
                        "include_lilith_true", e.value
                    ),
                ).props("dense")
                ui.checkbox(
                    _("Vertex"),
                    value=state.show_vertex,
                    on_change=lambda e: update_field("show_vertex", e.value),
                ).props("dense")

                # Asteroids
                ui.label(_("Asteroids")).classes("text-xs font-bold mt-3").style(
                    f"color: {COLORS['secondary']}"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-x-2"):
                    for asteroid in ALL_ASTEROIDS:
                        ui.checkbox(
                            _(asteroid),
                            value=asteroid in state.include_asteroids,
                            on_change=lambda e, a=asteroid: toggle_asteroid(
                                a, e.value
                            ),
                        ).props("dense")

        # ===== ASPECTS =====
        with ui.expansion(_("Aspects"), icon="hub").classes(
            "w-full"
        ).props('header-class="text-sm font-medium"'):
            with ui.column().classes("gap-3 p-4"):
                ui.checkbox(
                    _("Calculate Aspects"),
                    value=state.include_aspects,
                    on_change=lambda e: update_field(
                        "include_aspects", e.value),
                ).props("dense")

                with ui.element("div").bind_visibility_from(
                    state, "include_aspects", backward=lambda x: x
                ):
                    ui.label(_("Aspect Set:")).classes("text-sm mt-2").style(
                        f"color: {COLORS['text_muted']}"
                    )
                    ui.select(
                        {code: name for name, code in ASPECT_MODES},
                        value=state.aspect_mode,
                        on_change=lambda e: update_field(
                            "aspect_mode", e.value),
                    ).classes("w-full")

                    ui.label(
                        _("Major: Conjunction, Opposition, Trine, Square, Sextile")
                    ).classes("text-xs mt-1").style(f"color: {COLORS['accent']}")
                    ui.label(
                        _("Minor: Semi-sextile, Semi-square, Sesquiquadrate, Quincunx")
                    ).classes("text-xs").style(f"color: {COLORS['accent']}")
                    ui.label(
                        _("Harmonic: Quintile, Bi-quintile, Septile, Novile")
                    ).classes("text-xs").style(f"color: {COLORS['accent']}")

        # ===== CALCULATIONS / COMPONENTS =====
        with ui.expansion(_("Calculations"), icon="calculate").classes(
            "w-full"
        ).props('header-class="text-sm font-medium"'):
            with ui.column().classes("gap-2 p-4"):
                ui.checkbox(
                    _("Essential Dignities"),
                    value=state.include_dignities,
                    on_change=lambda e: update_field(
                        "include_dignities", e.value),
                ).props("dense")
                ui.label(
                    _("Rulerships, exaltations, triplicities, terms, faces")
                ).classes("text-xs ml-6 -mt-1").style(f"color: {COLORS['accent']}")

                ui.checkbox(
                    _("Declinations"),
                    value=state.include_declinations,
                    on_change=lambda e: update_field(
                        "include_declinations", e.value),
                ).props("dense")
                ui.label(_("Equatorial coordinates, out-of-bounds detection")).classes(
                    "text-xs ml-6 -mt-1"
                ).style(f"color: {COLORS['accent']}")

                ui.checkbox(
                    _("Aspect Patterns"),
                    value=state.include_patterns,
                    on_change=lambda e: update_field(
                        "include_patterns", e.value),
                ).props("dense")
                ui.label(_("Grand Trines, T-Squares, Yods, Stelliums")).classes(
                    "text-xs ml-6 -mt-1"
                ).style(f"color: {COLORS['accent']}")

                ui.checkbox(
                    _("Midpoints"),
                    value=state.include_midpoints,
                    on_change=lambda e: update_field(
                        "include_midpoints", e.value),
                ).props("dense")
                ui.label(_("Direct midpoints for all planet pairs")).classes(
                    "text-xs ml-6 -mt-1"
                ).style(f"color: {COLORS['accent']}")

                ui.checkbox(
                    _("Arabic Parts"),
                    value=state.include_arabic_parts,
                    on_change=lambda e: update_field(
                        "include_arabic_parts", e.value),
                ).props("dense")
                ui.label(
                    _("25+ lots: Fortune, Spirit, Love, etc. (sect-aware)")
                ).classes("text-xs ml-6 -mt-1").style(f"color: {COLORS['accent']}")

                ui.checkbox(
                    _("Fixed Stars"),
                    value=state.include_fixed_stars,
                    on_change=lambda e: update_field(
                        "include_fixed_stars", e.value),
                ).props("dense")

                with ui.element("div").bind_visibility_from(
                    state, "include_fixed_stars", backward=lambda x: x
                ):
                    ui.select(
                        {
                            "royal": _("Royal Stars (4)"),
                            "major": _("Major Stars (15)"),
                            "all": _("All Stars (26)"),
                        },
                        value=state.fixed_stars_mode,
                        on_change=lambda e: update_field(
                            "fixed_stars_mode", e.value
                        ),
                    ).classes("w-full ml-6")

        # ===== VISUALIZATION - THEME & PALETTES =====
        with ui.expansion(_("Theme & Palettes"), icon="palette").classes(
            "w-full"
        ).props('header-class="text-sm font-medium"'):
            with ui.column().classes("gap-3 p-4"):
                ui.label(_("Chart Theme")).classes("text-sm").style(
                    f"color: {COLORS['text_muted']}"
                )
                ui.select(
                    CHART_THEMES,
                    value=state.theme,
                    on_change=lambda e: update_field("theme", e.value),
                ).classes("w-full")

                ui.label(_("Color Palettes")).classes("text-sm mt-3").style(
                    f"color: {COLORS['text_muted']}"
                )
                with ui.element("div").classes("grid grid-cols-2 gap-x-4 gap-y-2"):
                    with ui.column().classes("gap-1"):
                        ui.label(_("Zodiac Ring")).classes("text-xs").style(
                            f"color: {COLORS['accent']}"
                        )
                        ui.select(
                            ZODIAC_PALETTES,
                            value=state.zodiac_palette,
                            on_change=lambda e: update_field(
                                "zodiac_palette", e.value
                            ),
                        ).classes("w-full")

                    with ui.column().classes("gap-1"):
                        ui.label(_("Aspect Lines")).classes("text-xs").style(
                            f"color: {COLORS['accent']}"
                        )
                        ui.select(
                            ASPECT_PALETTES,
                            value=state.aspect_palette,
                            on_change=lambda e: update_field(
                                "aspect_palette", e.value
                            ),
                        ).classes("w-full")

                    with ui.column().classes("gap-1"):
                        ui.label(_("Planet Glyphs")).classes("text-xs").style(
                            f"color: {COLORS['accent']}"
                        )
                        ui.select(
                            {code: name for name, code in PLANET_GLYPH_PALETTES},
                            value=state.planet_glyph_palette,
                            on_change=lambda e: update_field(
                                "planet_glyph_palette", e.value
                            ),
                        ).classes("w-full")

                    with ui.column().classes("gap-1"):
                        ui.label(_("Sign Info Colors")).classes("text-xs").style(
                            f"color: {COLORS['accent']}"
                        )
                        ui.checkbox(
                            _("Color sign glyphs"),
                            value=state.color_sign_info,
                            on_change=lambda e: update_field(
                                "color_sign_info", e.value
                            ),
                        ).props("dense")

        # ===== VISUALIZATION - DISPLAY =====
        with ui.expansion(_("Display Options"), icon="visibility").classes(
            "w-full"
        ).props('header-class="text-sm font-medium"'):
            with ui.column().classes("gap-3 p-4"):
                ui.checkbox(
                    _("Show Header Band"),
                    value=state.show_header,
                    on_change=lambda e: update_field("show_header", e.value),
                ).props("dense")
                ui.label(_("Name, location, coordinates, datetime")).classes(
                    "text-xs ml-6 -mt-1"
                ).style(f"color: {COLORS['accent']}")

                ui.checkbox(
                    _("Show Moon Phase"),
                    value=state.show_moon_phase,
                    on_change=lambda e: update_field(
                        "show_moon_phase", e.value),
                ).props("dense")

                with ui.element("div").bind_visibility_from(
                    state, "show_moon_phase", backward=lambda x: x
                ):
                    with ui.row().classes("ml-6 gap-4 items-center"):
                        ui.select(
                            {code: name for name, code in MOON_PHASE_POSITIONS},
                            value=state.moon_phase_position,
                            on_change=lambda e: update_field(
                                "moon_phase_position", e.value
                            ),
                        ).classes("w-32")
                        ui.checkbox(
                            _("Label"),
                            value=state.moon_phase_show_label,
                            on_change=lambda e: update_field(
                                "moon_phase_show_label", e.value
                            ),
                        ).props("dense")

                ui.label(_("Info Corners")).classes("text-sm mt-3").style(
                    f"color: {COLORS['text_muted']}"
                )
                ui.checkbox(
                    _("Chart Info (house system, ephemeris)"),
                    value=state.show_chart_info,
                    on_change=lambda e: update_field(
                        "show_chart_info", e.value),
                ).props("dense")
                ui.checkbox(
                    _("Aspect Counts"),
                    value=state.show_aspect_counts,
                    on_change=lambda e: update_field(
                        "show_aspect_counts", e.value),
                ).props("dense")
                ui.checkbox(
                    _("Element/Modality Balance"),
                    value=state.show_element_modality,
                    on_change=lambda e: update_field(
                        "show_element_modality", e.value),
                ).props("dense")

        # ===== TABLES (EXTENDED VIEW) =====
        with ui.expansion(_("Tables (Extended View)"), icon="table_chart").classes(
            "w-full"
        ).props('header-class="text-sm font-medium"'):
            with ui.column().classes("gap-3 p-4"):
                ui.checkbox(
                    _("Show Extended Tables"),
                    value=state.show_tables,
                    on_change=lambda e: update_field("show_tables", e.value),
                ).props("dense")

                with ui.element("div").bind_visibility_from(
                    state, "show_tables", backward=lambda x: x
                ):
                    ui.label(_("Table Position:")).classes("text-sm mt-2").style(
                        f"color: {COLORS['text_muted']}"
                    )
                    ui.select(
                        {code: name for name, code in TABLE_POSITIONS},
                        value=state.table_position,
                        on_change=lambda e: update_field(
                            "table_position", e.value),
                    ).classes("w-full")

                    ui.label(_("Include:")).classes("text-sm mt-3").style(
                        f"color: {COLORS['text_muted']}"
                    )
                    ui.checkbox(
                        _("Planet Positions Table"),
                        value=state.table_show_positions,
                        on_change=lambda e: update_field(
                            "table_show_positions", e.value
                        ),
                    ).props("dense")
                    ui.checkbox(
                        _("House Cusps Table"),
                        value=state.table_show_houses,
                        on_change=lambda e: update_field(
                            "table_show_houses", e.value
                        ),
                    ).props("dense")
                    ui.checkbox(
                        _("Aspectarian Grid"),
                        value=state.table_show_aspectarian,
                        on_change=lambda e: update_field(
                            "table_show_aspectarian", e.value
                        ),
                    ).props("dense")
