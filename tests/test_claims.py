"""Jede Zahl im README (und in den Preset-Hilfetexten) ist hier belegt — aus dem echten Code neu berechnet."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ndu_constants import DEFAULT_D, DEFAULT_DENSITY, DEFAULT_FIX, DEFAULT_P, DEFAULT_S, DEFAULT_SEED, DEFAULT_SPREAD_LANE, N_REPR, N_SAMPLE
from ndu_evaluation import compare_designs


def _run(spread, load):
    return compare_designs(DEFAULT_P, DEFAULT_D, DEFAULT_S, DEFAULT_DENSITY, DEFAULT_SPREAD_LANE, DEFAULT_FIX, DEFAULT_SEED, spread, load, N_REPR, N_SAMPLE)


def test_standard_preset_65_80():
    r = _run(65, 80)
    assert r.gap_pct == pytest.approx(4.4208873690429105, abs=1e-6)
    assert r.worst_gap_pct == pytest.approx(9.753555664541443, abs=1e-6)
    assert len(r.topology_diff) == 2
    assert r.fixed_det == 930
    assert r.fixed_stoch == 990
    assert 100 * r.det_eval["expected_unmet_share"] == pytest.approx(2.1739638219478272, abs=1e-6)
    assert 100 * r.stoch_eval["expected_unmet_share"] == pytest.approx(0.06895871502613075, abs=1e-6)


def test_moderate_streuung_preset_35_80():
    r = _run(35, 80)
    assert r.gap_pct == 0.0
    assert r.topology_diff == []


def test_mehr_reserve_preset_65_70():
    r = _run(65, 70)
    assert r.gap_pct == pytest.approx(1.2299483440603163, abs=1e-6)
    assert len(r.topology_diff) == 2


def test_knappere_kapazitaet_preset_65_60():
    r = _run(65, 60)
    assert r.gap_pct == pytest.approx(6.353537723229914, abs=1e-6)
    assert r.worst_gap_pct == pytest.approx(49.95115279406018, abs=1e-6)
    assert len(r.topology_diff) == 3


def test_network_size():
    from ndu_model import generate_design
    d = generate_design(DEFAULT_P, DEFAULT_D, DEFAULT_S, DEFAULT_DENSITY, DEFAULT_SPREAD_LANE, 80, DEFAULT_SEED, 1, DEFAULT_FIX)
    assert d.G == 27
    assert d.m == 38
