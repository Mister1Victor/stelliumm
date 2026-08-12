#!/usr/bin/env python3
"""
REST API сервер для Flutter клиента.
Запускается на порту 8000.

Usage:
    python api_server.py
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from stellium import ChartBuilder
from stellium.engines import KochHouses, PlacidusHouses, WholeSignHouses, EqualHouses
import tempfile
from pathlib import Path

app = FastAPI(
    title="Astro Pro API",
    description="REST API для расчёта натальных карт через stellium",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChartRequest(BaseModel):
    birth_date: str
    latitude: float
    longitude: float
    house_system: str = "koch"
    theme: str = "midnight"  # ← Новый параметр


def get_house_system(system_name: str):
    systems = {
        "koch": KochHouses(),
        "placidus": PlacidusHouses(),
        "equal": EqualHouses(),
        "whole_sign": WholeSignHouses(),
    }
    return systems.get(system_name.lower(), KochHouses())


@app.get("/")
async def root():
    return {"message": "Astro Pro API is running", "docs": "/docs"}


@app.post("/calculate-chart-svg")
async def calculate_chart_svg(request: ChartRequest):
    """Возвращает SVG натальной карты с выбранной темой."""
    try:
        chart = (
            ChartBuilder.from_details(
                request.birth_date, (request.latitude, request.longitude)
            )
            .with_house_systems([get_house_system(request.house_system)])
            .with_aspects()
            .calculate()
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False, encoding='utf-8') as tmp:
            tmp_path = tmp.name

        # Применяем выбранную тему
        chart.draw(tmp_path) \
            .with_theme(request.theme) \
            .with_chart_info(position="top-left") \
            .save()

        svg_content = Path(tmp_path).read_text(encoding='utf-8')
        Path(tmp_path).unlink()

        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={"Access-Control-Allow-Origin": "*"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calculate-houses")
async def calculate_houses(request: ChartRequest):
    """Пересчёт только куспидов домов."""
    try:
        chart = (
            ChartBuilder.from_details(
                request.birth_date, (request.latitude, request.longitude)
            )
            .with_house_systems([get_house_system(request.house_system)])
            .calculate()
        )
        return {"cusps": [float(cusp) for cusp in chart.get_houses().cusps]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print()
    print("  ✦════════════════════════════════════════════════✦")
    print("  ║         ★  ASTRO PRO API  ★                ║")
    print("  ✦════════════════════════════════════════════════✦")
    print("  ║  API:      http://localhost:8000              ║")
    print("  ║  Docs:     http://localhost:8000/docs         ║")
    print("  ✦════════════════════════════════════════════════✦")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
