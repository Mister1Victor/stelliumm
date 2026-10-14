"""Integration tests: real ephemeris + stellium adapter.

Skipped automatically if pyswisseph/stellium or the Eris .se1 file are absent,
so CI on machines without ephemeris data never breaks.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

swe = pytest.importorskip("swisseph")

import astro12  # noqa: E402


@pytest.fixture(scope="module")
def direct_chart():
    when = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    return astro12.calculate(when)


def test_direct_calc_all_twelve_present(direct_chart):
    assert direct_chart.missing == []
    assert len(direct_chart.placements) == 12
    eris = direct_chart.get("eris")
    # J2000-era reality check: Eris was ~18-19° Aries on 2000-01-01
    assert eris.sign == "Aries"
    assert 15 < eris.sign_degree < 22


def test_rulership_consistency(direct_chart):
    for sign_en, ruler_key in astro12.SIGN_RULERS.items():
        pl = direct_chart.get(ruler_key)
        assert pl is not None
        assert pl.ruler_of == sign_en
        # dispositor of a body in sign X must be that sign's ruler
        other = direct_chart.placements[0]
        assert other.dispositor_key == astro12.SIGN_RULERS[other.sign]


def test_prompt_generation_from_real_chart(direct_chart):
    pr = astro12.chart_to_prompt(direct_chart)
    assert "Эрида ERa" in pr
    assert "Церера ⚳" in pr
    assert pr.count("\n- ") > 20  # placements + rulerships + aspects


STELLIUM_AVAILABLE = True
try:
    import stellium  # noqa: F401
except ImportError:
    STELLIUM_AVAILABLE = False

needs_stellium = pytest.mark.skipif(not STELLIUM_AVAILABLE,
                                    reason="stellium not installed")


@needs_stellium
def test_build_chart_via_stellium_and_adapter():
    when = dt.datetime(1990, 6, 15, 12, 0, tzinfo=dt.timezone.utc)
    schart, tc = astro12.build_chart(when, (55.75, 37.62), name="Тест")
    assert schart is not None
    assert len(tc.placements) == 12, f"missing={tc.missing}"
    d = tc.to_dict()
    assert d["meta"]["chart_name"] == "Тест"
    # houses carried over from stellium
    assert isinstance(d["meta"]["houses"], dict)


@needs_stellium
def test_from_stellium_chart_duck_typed():
    """Adapter must work on any object with stellium-like surface."""
    class FakePos:
        def __init__(self, name, lon):
            self.name, self.longitude = name, lon
            self.sign = astro12.SIGNS_EN[int(lon // 30)]
            self.sign_degree = lon % 30
            self.speed_longitude = 0.05
            self.is_retrograde = False
            self.distance = 1.0

    class FakeChart:
        positions = [FakePos("Sun", 20), FakePos("Eris", 18.6),
                     FakePos("Chiron", 100)]  # unknown -> ignored
        aspects = ()
        house_placements = {}
        class _DT:
            utc_datetime = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
        datetime = _DT()
        location = None
        metadata = {}

    tc = astro12.from_stellium_chart(FakeChart())
    assert {p.key for p in tc.placements} == {"sun", "eris"}
    assert "ceres" in tc.missing  # gracefully reported, no exception
