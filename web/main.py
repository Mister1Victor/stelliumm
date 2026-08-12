#!/usr/bin/env python3
"""
Stellium Web — Main Entry Point

A beautiful web interface for the Stellium astrology library,
plus REST API for Flutter/mobile clients.

Usage:
    cd web
    python main.py

Then visit http://localhost:8080
API docs: http://localhost:8080/docs
"""

import logging
import os
from pathlib import Path

from config import COLORS, FONTS, GOOGLE_FONTS_URL
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from nicegui import app, ui
from pages.explore import create_explore_page
from pages.home import create_home_page
from pages.natal import create_natal_page
from pages.planner import create_planner_page
from pages.relationships import create_relationships_page
from pages.timing import create_timing_page
from starlette.responses import PlainTextResponse

# REST API для Flutter клиента (должен быть в том же каталоге, что и main.py)
from api import router as api_router


# =============================================================================
# LOGGING
# =============================================================================

logger = logging.getLogger("stellium.web")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Маршрутизируем Python warnings в логгер (включая StelliumWarning)
logging.captureWarnings(True)

# Глушим шумные библиотеки
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("nicegui").setLevel(logging.WARNING)


# =============================================================================
# SEO / META
# =============================================================================

SITE_NAME = "Stellium"
SITE_DESCRIPTION = (
    "Free professional astrology charts, reports, and tools. "
    "Generate natal charts, synastry, transits, progressions, "
    "and PDF planners — powered by Swiss Ephemeris."
)
SITE_URL = "https://stelliumastro.app"


# =============================================================================
# GLOBAL STYLES
# =============================================================================

def setup_styles(page_title: str = "", page_description: str = ""):
    """Добавляет глобальные CSS стили, шрифты и мета-теги."""
    full_title = f"{page_title} | {SITE_NAME}" if page_title else SITE_NAME
    description = page_description or SITE_DESCRIPTION

    ui.colors(
        primary=COLORS["primary"],
        secondary=COLORS["secondary"],
        accent=COLORS["accent"],
        positive=COLORS["primary"],
        warning=COLORS["gold"],
    )

    from analytics import tracking_script
    ui.add_head_html(tracking_script())

    ui.add_head_html(f"""
    <title>{full_title}</title>
    <meta name="description" content="{description}">
    <meta property="og:title" content="{full_title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{SITE_URL}">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{full_title}">
    <meta name="twitter:description" content="{description}">
    """)

    ui.add_head_html(f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{GOOGLE_FONTS_URL}" rel="stylesheet">
    <style>
        body {{
            font-family: 'Crimson Pro', serif;
            background-color: {COLORS["cream"]};
            color: {COLORS["text"]};
        }}
        .font-display {{ font-family: '{FONTS["display"]}', serif; }}
        a {{ color: {COLORS["gold"]}; }}
        a:hover {{ color: {COLORS["primary"]}; }}
        .nav-link {{
            color: {COLORS["text_muted"]} !important;
            transition: color 0.2s ease !important;
        }}
        .nav-link:hover {{ color: {COLORS["gold"]} !important; }}
        .nicegui-content {{ padding: 0 !important; }}
        .minimal-input .q-field__control {{ background: transparent !important; }}
        .minimal-input .q-field__control:before,
        .minimal-input .q-field__control:after {{ display: none !important; }}
        .minimal-input .q-field__native {{
            border: none !important;
            border-bottom: 1px solid {COLORS["text"]} !important;
            border-radius: 0 !important;
            padding: 8px 0 !important;
            font-family: 'Crimson Pro', serif !important;
            font-size: 1.1rem !important;
            color: {COLORS["text"]} !important;
        }}
        .minimal-input .q-field__native:focus {{
            border-bottom-color: {COLORS["secondary"]} !important;
        }}
        .minimal-input .q-field__native::placeholder {{
            color: {COLORS["accent"]} !important;
        }}
        .q-checkbox__inner--truthy, .q-radio__inner--truthy {{
            color: {COLORS["secondary"]} !important;
        }}
        .q-btn-toggle {{
            border: none !important;
            border-radius: 0.25rem !important;
            background: transparent !important;
            box-shadow: none !important;
        }}
        .q-btn-toggle .q-btn {{
            font-family: 'Crimson Pro', serif !important;
            font-size: 0.75rem !important;
            letter-spacing: 0.05em !important;
            padding: 2px 8px !important;
            min-height: 24px !important;
            box-shadow: none !important;
        }}
        .q-btn-toggle .q-btn:not(.q-btn--active) {{
            color: {COLORS["text_muted"]} !important;
            background-color: transparent !important;
        }}
        .q-btn-toggle .q-btn:not(.q-btn--active):hover {{
            color: {COLORS["text"]} !important;
            background-color: {COLORS["cream_dark"]} !important;
        }}
        .q-btn-toggle .q-btn.q-btn--active {{
            color: {COLORS["primary"]} !important;
            background-color: {COLORS["cream_dark"]} !important;
            font-weight: 600 !important;
        }}
        .q-btn-toggle .q-btn + .q-btn {{ border-left: none !important; }}
        .q-btn {{
            font-family: 'Crimson Pro', serif !important;
            letter-spacing: 0.05em;
        }}
        .q-btn--standard:not(.q-btn--outline) {{
            background-color: {COLORS["primary"]} !important;
            color: white !important;
        }}
        .q-btn--standard:not(.q-btn--outline):hover {{
            background-color: {COLORS["secondary"]} !important;
        }}
        .q-btn--outline {{
            color: {COLORS["primary"]} !important;
            border-color: {COLORS["primary"]} !important;
        }}
        .q-btn--outline:hover {{ background-color: {COLORS["cream_dark"]} !important; }}
        .q-btn--flat {{ color: {COLORS["text"]} !important; }}
        .q-btn--flat:hover {{ background-color: {COLORS["cream_dark"]} !important; }}
        .btn-gold.q-btn--outline {{
            color: {COLORS["gold"]} !important;
            border-color: {COLORS["gold"]} !important;
        }}
        .btn-gold.q-btn--outline:hover {{
            background-color: rgba(184, 149, 61, 0.1) !important;
        }}
        .q-expansion-item__container {{
            border: 1px solid {COLORS["border"]} !important;
            border-radius: 0.25rem !important;
            margin-bottom: 0.5rem !important;
        }}
        ::selection {{ background-color: {COLORS["accent"]}; color: white; }}
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: {COLORS["cream_dark"]}; }}
        ::-webkit-scrollbar-thumb {{
            background: {COLORS["accent"]};
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{ background: {COLORS["secondary"]}; }}
    </style>
    """)


# =============================================================================
# NICEGUI PAGES (HTML UI)
# =============================================================================

@ui.page("/")
async def home():
    """Главная страница."""
    setup_styles()
    create_home_page()


@ui.page("/natal")
async def natal():
    """Натальная карта."""
    setup_styles(
        "Natal Chart",
        "Generate a professional natal birth chart with aspects, houses, and dignities.",
    )
    create_natal_page()


@ui.page("/relationships")
async def relationships():
    """Синастрия, композит, Дэвисон."""
    setup_styles(
        "Relationships",
        "Synastry, composite, and Davison relationship charts.",
    )
    create_relationships_page()


@ui.page("/timing")
async def timing():
    """Транзиты, прогрессии, соляры."""
    setup_styles(
        "Timing",
        "Transits, progressions, solar returns, and timing analysis.",
    )
    create_timing_page()


@ui.page("/planner")
async def planner():
    """Астрологический планировщик."""
    setup_styles(
        "Planner",
        "Generate a personalized astrological PDF planner with transits and Moon phases.",
    )
    create_planner_page()


@ui.page("/explore")
async def explore():
    """Известные личности."""
    setup_styles(
        "Explore Notable Charts",
        "Browse birth charts of famous historical figures — scientists, artists, leaders, and more.",
    )
    create_explore_page()


# =============================================================================
# SERVICE ENDPOINTS (FastAPI)
# =============================================================================

ROBOTS_TXT = """\
# stelliumastro.app — interactive astrology chart tool
User-agent: *
Allow: /
Allow: /explore
Disallow: /wp-admin/
Disallow: /wp-login.php
Disallow: /.env

User-agent: AhrefsBot
Disallow: /

User-agent: SemrushBot
Disallow: /

User-agent: MJ12bot
Disallow: /

Sitemap: https://stelliumastro.app/sitemap.xml
"""


@ui.page("/robots.txt", dark=False)
async def robots_txt():
    """Отдаём robots.txt для поисковых ботов."""
    return PlainTextResponse(ROBOTS_TXT, media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap():
    """Отдаём sitemap.xml для поисковиков."""
    sitemap_path = Path(__file__).parent / "static" / "sitemap.xml"
    content = sitemap_path.read_text(encoding="utf-8")
    return PlainTextResponse(content, media_type="application/xml")


@app.get("/health")
async def health_check():
    """Health-check endpoint для Railway и мониторинга."""
    return {"status": "ok", "service": "stellium-web"}


# =============================================================================
# MIDDLEWARE
# =============================================================================

# Middleware в FastAPI применяются в обратном порядке добавления (LIFO).
# То есть последний добавленный выполняется первым.
# Порядок снизу вверх:
#   1. request_middleware — фильтрация ботов, логирование
#   2. CORSMiddleware — заголовки CORS для Flutter Web (должен быть самым внешним)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Фильтрация ботов и логирование запросов."""
    import time

    path = request.url.path.lower()

    # Тихо отклоняем известные probe-пути
    bot_extensions = (".php", ".asp", ".aspx", ".jsp", ".cgi")
    bot_probes = (
        "/wp-admin", "/wp-login", "/wp-content", "/wp-includes",
        "/.env", "/xmlrpc", "/admin/", "/phpmyadmin",
    )
    if any(path.endswith(ext) for ext in bot_extensions) or \
       any(probe in path for probe in bot_probes):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start

    if (
        not path.startswith("/_nicegui")
        and not path.startswith("/static")
        and not path.startswith("/_event")
        and not path.startswith("/api/")  # API логируем отдельно
        and path != "/health"
        and request.method == "GET"
        and "websocket" not in request.headers.get("upgrade", "")
    ):
        logger.info(
            "%s %s → %s (%.2fs)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )

    return response


# =============================================================================
# MAIN
# =============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    # Порт из переменной окружения (Railway) или 8080 для локальной разработки
    port = int(os.environ.get("PORT", 8080))
    is_production = os.environ.get("RAILWAY_ENVIRONMENT") is not None

    # Секрет для подписи session cookies.
    # В production дефолтный секрет недопустим — иначе любой сможет подделать сессию.
    DEV_STORAGE_SECRET = "stellium-dev-secret"
    storage_secret = os.environ.get("STORAGE_SECRET", DEV_STORAGE_SECRET)
    if is_production and storage_secret == DEV_STORAGE_SECRET:
        raise RuntimeError(
            "STORAGE_SECRET must be set to a unique secret in production "
            "(the default dev secret is public and would allow session forgery)."
        )

    # ─── Startup banner (только в main process) ─────────────────────────────
    if __name__ == "__main__":
        print()
        print("  ✦" + "═" * 48 + "✦")
        print("  ║         ★  STELLIUM WEB + API  ★          ║")
        print("  ✦" + "═" * 48 + "✦")
        print(f"  ║  Web UI:    http://localhost:{port}              ║")
        print(f"  ║  API docs:  http://localhost:{port}/docs         ║")
        print(f"  ║  Health:    http://localhost:{port}/health       ║")
        print("  ✦" + "═" * 48 + "✦")
        print()

    # ─── Регистрация API роутера ────────────────────────────────────────────
    # Эндпоинты из api.py: /api/calculate-chart, /api/calculate-houses
    app.include_router(api_router)

    # ─── CORS middleware (должен быть добавлен ПОСЛЕДНИМ, чтобы применяться ПЕРВЫМ) ─
    # Нужен, чтобы Flutter Web (Chrome) мог обращаться к API на другом порту.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Запуск NiceGUI ─────────────────────────────────────────────────────
    ui.run(
        title="Stellium",
        favicon="★",
        # Привязка ко всем интерфейсам (нужно для Railway)
        host="0.0.0.0",
        port=port,
        reload=not is_production,  # Hot reload только в dev
        show=False,                # Не открывать браузер автоматически
        storage_secret=storage_secret,
    )
