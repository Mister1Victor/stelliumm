"""Offline-safe tests for astro12 (no ephemeris files required)."""

from __future__ import annotations

import datetime as dt

import pytest

import astro12
from astro12.constants import (
    PLANET_ORDER,
    RULER_TO_SIGN,
    SIGN_RULERS,
    TWELVE_PLANETS,
)
from astro12.model import BodyPlacement, TwelveChart, compute_aspects


def test_twelve_order_slowest_to_fastest():
    assert PLANET_ORDER == (
        "eris", "pluto", "neptune", "uranus", "saturn", "jupiter",
        "ceres", "mars", "venus", "mercury", "sun", "moon",
    )
    periods = [p.sidereal_years for p in TWELVE_PLANETS]
    # strictly decreasing orbital period (slowest -> fastest), Sun/Moon are
    # special-cased as reference bodies at the end
    assert periods[:10] == sorted(periods[:10], reverse=True)


def test_sign_rulers_table_matches_school_spec():
    expected = {
        "Aries": "mars", "Taurus": "venus", "Gemini": "mercury",
        "Cancer": "moon", "Leo": "sun", "Virgo": "eris", "Libra": "pluto",
        "Scorpio": "neptune", "Sagittarius": "uranus", "Capricorn": "saturn",
        "Aquarius": "jupiter", "Pisces": "ceres",
    }
    assert SIGN_RULERS == expected
    # bijection: 12 distinct rulers
    assert len(set(SIGN_RULERS.values())) == 12
    assert RULER_TO_SIGN["eris"] == "Virgo"
    assert RULER_TO_SIGN["ceres"] == "Pisces"


def _mk(key, lon):
    sign = astro12.SIGNS_EN[int(lon // 30)]
    return BodyPlacement(key=key, longitude=lon % 360, sign=sign,
                         sign_degree=lon % 30, speed=0.1, retrograde=False)


def test_compute_aspects_conjunction_and_opposition():
    ps = [_mk("sun", 10), _mk("moon", 12), _mk("mars", 190)]
    asp = compute_aspects(ps)
    names = {(a.p1, a.p2, a.name) for a in asp}
    assert ("sun", "moon", "Conjunction") in names
    assert any(a.name == "Opposition" for a in asp if {a.p1, a.p2} == {"sun", "mars"})


def test_orb_boundaries_no_aspect():
    ps = [_mk("sun", 0), _mk("moon", 45)]  # octile not used by school
    assert compute_aspects(ps) == []


def test_own_sign_and_dispositor_logic():
    # Mars in Aries -> in own sign; Venus in Virgo -> dispositor Eris
    mars = _mk("mars", 15)
    venus = _mk("venus", 165)  # 15 Virgo
    assert mars.house_of_own_ruler and mars.ruler_of == "Aries"
    assert not venus.house_of_own_ruler
    assert venus.dispositor_key == "eris"


def test_missing_bodies_do_not_raise():
    when = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    tc = TwelveChart(when_utc=when, placements=[_mk("sun", 0)], missing=["eris"])
    d = tc.to_dict()
    assert d["missing"] == ["eris"]
    assert len(d["placements"]) == 1
    prompt = astro12.chart_to_prompt(tc)
    assert "Эрида" in prompt  # mentioned as not calculated
    assert "НЕ рассчитаны" in prompt


def test_chart_to_prompt_contains_all_sections():
    when = dt.datetime(2026, 10, 11, tzinfo=dt.timezone.utc)
    ps = [_mk(k, i * 30.0 + 5) for i, k in enumerate(PLANET_ORDER)]
    tc = TwelveChart(when_utc=when, placements=ps,
                     aspects=compute_aspects(ps))
    pr = astro12.chart_to_prompt(tc)
    for needle in ("Планеты-управители", "Управители знаков", "Аспекты"):
        assert needle in pr
    assert "ERa" in pr and "⚳" in pr


def test_aspect_prompt_requires_present_planets():
    when = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    tc = TwelveChart(when_utc=when, placements=[_mk("venus", 10)])
    with pytest.raises(KeyError):
        astro12.aspect_prompt(tc, "venus", "saturn", "Trine")


def test_json_round_trip_is_serializable():
    import json

    when = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    ps = [_mk(k, i * 30.0 + 5) for i, k in enumerate(PLANET_ORDER)]
    tc = TwelveChart(when_utc=when, placements=ps, aspects=compute_aspects(ps))
    s = json.dumps(tc.to_dict(), ensure_ascii=False)
    back = json.loads(s)
    assert back["system"] == "School of 12 Planets"
    assert len(back["placements"]) == 12
