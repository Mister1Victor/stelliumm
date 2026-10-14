"""End-to-end API tests (mock LLM mode, no network).

Run from server/:  PYTHONPATH=../package pytest tests -q
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "package"))

os.environ.setdefault("ASTRO12_LLM_MODE", "mock")

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

BODY = {"when_utc": "1990-05-15T12:00:00Z", "lat": 55.75, "lon": 37.62,
        "name": "Тест"}


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["llm_mode"] == "mock"


def test_chart_returns_twelve_placements(client):
    r = client.post("/v1/chart", json=BODY)
    assert r.status_code == 200
    j = r.json()
    assert len(j["placements"]) == 12
    assert j["missing"] == []
    keys = {p["key"] for p in j["placements"]}
    assert {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
            "uranus", "neptune", "pluto", "ceres", "eris"} <= keys
    # every placement carries the school-system fields
    for p in j["placements"]:
        assert p["sign"] and p["sign_ru"]
        assert "in_own_sign" in p and "dispositor" in p


def test_prompt_endpoint(client):
    r = client.post("/v1/prompt", json=BODY)
    assert r.status_code == 200
    j = r.json()
    assert len(j["prompt"]) > 200
    assert "12" in j["system_brief"] or "планет" in j["system_brief"]
    assert len(j["chart_hash"]) == 64


def test_interpret_mock_and_cache(client):
    r = client.post("/v1/interpret", json={**BODY, "focus": "Карьера"})
    assert r.status_code == 200
    j = r.json()
    assert j["cached"] is False and j["model"] == "mock"
    assert "MOCK" in j["interpretation"]
    chash = j["chart_hash"]

    # identical request -> cache hit
    r2 = client.post("/v1/interpret", json={**BODY, "focus": "Карьера"})
    assert r2.status_code == 200 and r2.json()["cached"] is True

    # hash-only lookup works too
    r3 = client.post("/v1/interpret", json={"chart_hash": chash})
    assert r3.status_code == 200 and r3.json()["cached"] is True


def test_interpret_hash_only_unknown(client):
    r = client.post("/v1/interpret",
                    json={"chart_hash": "0" * 64})
    assert r.status_code == 404


def test_interpret_requires_data(client):
    r = client.post("/v1/interpret", json={})
    assert r.status_code == 422


def test_aspects_pair(client):
    chart = client.post("/v1/chart", json=BODY).json()
    if not chart["aspects"]:
        pytest.skip("no aspects in this chart")
    a = chart["aspects"][0]
    r = client.get(f"/v1/aspects/{a['p1']}/{a['p2']}"
                   f"?when_utc={BODY['when_utc']}")
    assert r.status_code == 200
    j = r.json()
    assert len(j["aspects"]) >= 1
    assert all(p.strip() for p in j["prompts"])


def test_aspects_bad_planet(client):
    r = client.get(f"/v1/aspects/mars/notaplanet?when_utc={BODY['when_utc']}")
    assert r.status_code == 404


def test_invalid_date_rejected(client):
    r = client.post("/v1/chart", json={"when_utc": "garbage"})
    assert r.status_code == 422


def test_heliocentric_sidereal_flags(client):
    r = client.post("/v1/chart",
                    json={**BODY, "heliocentric": True, "sidereal": True})
    assert r.status_code == 200
    assert len(r.json()["placements"]) == 12
