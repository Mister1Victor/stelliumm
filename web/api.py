"""REST API endpoints для Flutter клиента."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from stellium import ChartBuilder
from stellium.engines import KochHouses, PlacidusHouses, WholeSignHouses, EqualHouses

router = APIRouter(prefix="/api", tags=["astro"])


class ChartRequest(BaseModel):
    birth_date: str
    latitude: float
    longitude: float
    house_system: str = "koch"


def get_house_system(system_name: str):
    return {
        "koch": KochHouses(),
        "placidus": PlacidusHouses(),
        "equal": EqualHouses(),
        "whole_sign": WholeSignHouses(),
    }.get(system_name.lower(), KochHouses())


@router.post("/calculate-chart")
async def calculate_chart(request: ChartRequest):
    try:
        chart = (
            ChartBuilder.from_details(
                request.birth_date, (request.latitude, request.longitude))
            .with_house_systems([get_house_system(request.house_system)])
            .with_aspects()
            .calculate()
        )
        planets_data = {}
        for planet in chart.get_planets():
            planets_data[planet.name] = {
                "longitude": planet.longitude,
                "is_retrograde": getattr(planet, "is_retrograde", False),
                "sign": getattr(planet, "sign", ""),
            }
        houses = chart.get_houses()
        house_cusps = [float(c) for c in houses.cusps]
        aspects_data = [
            {"point1": a.object1.name, "point2": a.object2.name,
             "type": a.aspect_name, "orb": float(a.orb)}
            for a in chart.aspects
        ]
        return {
            "ascendant": house_cusps[0] if house_cusps else 0.0,
            "mc": house_cusps[9] if len(house_cusps) > 9 else 0.0,
            "planets": planets_data,
            "houses": house_cusps,
            "aspects": aspects_data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-houses")
async def calculate_houses(request: ChartRequest):
    try:
        chart = (
            ChartBuilder.from_details(
                request.birth_date, (request.latitude, request.longitude))
            .with_house_systems([get_house_system(request.house_system)])
            .calculate()
        )
        return {"cusps": [float(c) for c in chart.get_houses().cusps]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
