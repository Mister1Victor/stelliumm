"""astro12 REST API — the contract for Flutter and web clients.

Endpoints (v1):
    GET  /health                     liveness + ephemeris readiness
    POST /v1/chart                   TwelveChart JSON (positions + aspects)
    POST /v1/prompt                  LLM-ready markdown prompt + chart_hash
    POST /v1/interpret               interpretation (cached; mock or real LLM)
    GET  /v1/aspects/{p1}/{p2}       micro-prompts for one planet pair

Run locally:
    uvicorn app.main:app --reload --port 8100   (from server/)

Security model (MVP, honest about limits):
- Bearer tokens via ASTRO12_API_KEYS when set; open mode when unset (dev).
- Per-client sliding-window rate limit in memory. For multi-instance prod
  move both to Redis — the seams are isolated in this module on purpose.
"""

from __future__ import annotations

import threading
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from astro12 import TWELVE_PLANETS

from .config import Settings
from .llm import LLMClient, LLMError
from .schemas import (
    ChartOut,
    ChartRequest,
    InterpretOut,
    InterpretRequest,
    PromptOut,
)
from .services import build_chart, chart_hash

# --------------------------------------------------------------------------
# App factory (testable without env side effects)
# --------------------------------------------------------------------------


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    llm = LLMClient(settings)

    app = FastAPI(
        title="Astro12 API",
        description="School of 12 Planets — charts, prompts, interpretations.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.llm = llm

    # ---- auth -------------------------------------------------------------
    def require_auth(authorization: str | None = Header(default=None)) -> None:
        if not settings.api_keys:      # dev/open mode
            return
        token = (authorization or "").removeprefix("Bearer").strip()
        if token not in settings.api_keys:
            raise HTTPException(status_code=401,
                                detail="Missing or invalid bearer token")

    # ---- rate limit (per client IP, sliding window) ------------------------
    _hits: dict[str, list[float]] = {}
    _hits_lock = threading.Lock()

    def check_rate(request: Request) -> None:
        limit = settings.rate_limit_per_min
        if limit <= 0:
            return
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with _hits_lock:
            window = [t for t in _hits.get(ip, []) if now - t < 60.0]
            if len(window) >= limit:
                _hits[ip] = window
                raise HTTPException(status_code=429,
                                    detail="Rate limit exceeded, retry soon")
            window.append(now)
            _hits[ip] = window

    dep = [Depends(require_auth), Depends(check_rate)]

    # ---- routes -----------------------------------------------------------
    @app.get("/health")
    def health() -> dict:
        probe = {"ok": True, "ephemeris_ready": None, "llm_mode": settings.llm_mode}
        try:  # cheap probe: compute today's chart
            from datetime import datetime, timezone

            c = build_chart(
                ChartRequest(when_utc=datetime.now(timezone.utc)), settings)
            probe["placements"] = len(c.placements)
            probe["missing"] = c.missing
            probe["ephemeris_ready"] = len(c.placements) == 12
        except Exception as exc:  # never leak internals, but flag loudly
            probe["ok"] = False
            probe["error"] = type(exc).__name__
        return probe

    @app.post("/v1/chart", response_model=ChartOut, dependencies=dep)
    def chart(req: ChartRequest) -> dict:
        return build_chart(req, settings).to_dict()

    @app.post("/v1/prompt", response_model=PromptOut, dependencies=dep)
    def prompt(req: ChartRequest) -> dict:
        chart = build_chart(req, settings)
        return {
            "prompt": llm.build_prompt(chart),
            "system_brief": llm_cache_brief(),
            "chart_hash": chart_hash(chart),
        }

    @app.post("/v1/interpret", response_model=InterpretOut, dependencies=dep)
    def interpret(req: InterpretRequest) -> dict:
        if req.when_utc is None:
            # hash-only lookup: cheap for us, counts as cached for the client
            if req.chart_hash is None:
                raise HTTPException(
                    status_code=422,
                    detail="Provide when_utc (to compute) or chart_hash (to reuse)")
            hit = llm.cache.prefix_lookup(f"{req.chart_hash}|{req.lang}|")
            if hit:
                text, model, usage = hit
                return {"chart_hash": req.chart_hash,
                        "interpretation": text,
                        "cached": True, "model": model, "usage": usage}
            raise HTTPException(
                status_code=404,
                detail="Unknown chart_hash or expired cache; resend when_utc")

        chart = build_chart(
            ChartRequest(when_utc=req.when_utc, name=req.name), settings)
        chash = chart_hash(chart)
        try:
            res = llm.interpret(chart, chash=chash, focus=req.focus,
                                 lang=req.lang, refresh=req.refresh)
        except LLMError as exc:
            raise HTTPException(status_code=502,
                                detail=f"LLM provider error: {exc}") from exc
        return {"chart_hash": chash, **res}

    @app.get("/v1/aspects/{p1}/{p2}", dependencies=dep)
    def aspect_pair(p1: str, p2: str, when_utc: str,
                    aspect: str | None = None) -> dict:
        keys = {p.key for p in TWELVE_PLANETS}
        if p1 not in keys or p2 not in keys:
            raise HTTPException(status_code=404,
                                detail=f"unknown planet key; valid: {sorted(keys)}")
        from datetime import datetime

        try:
            when = datetime.fromisoformat(when_utc)
        except ValueError as exc:
            raise HTTPException(status_code=422,
                                detail="when_utc must be ISO 8601") from exc
        chart = build_chart(ChartRequest(when_utc=when), settings)
        wanted = [a for a in chart.aspects_for(p1)
                  if p2 in (a.p1, a.p2) and (aspect is None or a.name == aspect)]
        prompts = []
        for a in wanted:
            try:
                prompts.append(llm.aspect_prompt(chart, a.p1, a.p2, a.name))
            except KeyError:
                continue
        return {"aspects": [a.to_dict() for a in wanted], "prompts": prompts}

    def llm_cache_brief() -> str:
        from .llm import SYSTEM_BRIEF_RU

        return SYSTEM_BRIEF_RU

    return app


app = create_app()
