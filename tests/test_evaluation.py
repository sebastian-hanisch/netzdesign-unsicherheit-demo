import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ndu_constants import DEFAULT_D, DEFAULT_DENSITY, DEFAULT_FIX, DEFAULT_P, DEFAULT_S, DEFAULT_SEED, DEFAULT_SPREAD_LANE
from ndu_evaluation import compare_designs


def _standard(demand_spread, load, n_repr=5, n_sample=20):
    return compare_designs(DEFAULT_P, DEFAULT_D, DEFAULT_S, DEFAULT_DENSITY, DEFAULT_SPREAD_LANE, DEFAULT_FIX, DEFAULT_SEED, demand_spread, load, n_repr, n_sample)


def test_compare_designs_zero_spread_gives_exactly_zero_gap():
    """Bei Streuung 0 sind alle Szenarien identisch zur Nominalnachfrage; das Master-MILP mit S Kopien desselben
    Szenarios muss exakt dieselbe Entwurfsentscheidung treffen wie mit S=1 (derselbe Recourse-Mechanismus, kein
    Unterschied durch Streuung)."""
    r = _standard(0, 80)
    assert r.gap_pct == 0.0
    assert r.topology_diff == []


def test_compare_designs_topology_diff_matches_symmetric_difference():
    r = _standard(35, 80)
    manual = sorted(r.open_det.symmetric_difference(r.open_stoch))
    assert r.topology_diff == manual


def test_compare_designs_fixed_costs_match_open_sets():
    r = _standard(35, 80)
    assert r.fixed_det == sum(r.design.fixed[g] for g in r.open_det)
    assert r.fixed_stoch == sum(r.design.fixed[g] for g in r.open_stoch)


def test_compare_designs_gap_pct_matches_formula():
    r = _standard(35, 80)
    expected = 100.0 * (r.det_eval["expected_total"] - r.stoch_eval["expected_total"]) / r.stoch_eval["expected_total"]
    assert r.gap_pct == expected


def test_deterministic_baseline_is_recourse_aware_not_plain_solve_mip():
    """Regressionstest für einen echten Fund beim Bauen: das deterministische Design MUSS mit demselben
    Recourse-Mechanismus (nur S=1 Szenario) berechnet werden wie das stochastische - sonst entsteht eine
    Schein-Lücke allein daraus, dass das (naive) `solve_mip` keine Notfallkapazität kennt, selbst bei Streuung 0
    (gemessen: 1,3 % Schein-Lücke). `compare_designs` darf `ndu_formulation.solve_mip` NICHT für das
    deterministische Design verwenden."""
    from ndu_formulation import solve_mip
    from ndu_model import generate_design
    from ndu_uncertainty import nominal_demand, stochastic_master_solve

    design = generate_design(DEFAULT_P, DEFAULT_D, DEFAULT_S, DEFAULT_DENSITY, DEFAULT_SPREAD_LANE, 80, DEFAULT_SEED, 1, DEFAULT_FIX)
    naive_sol = solve_mip(design)
    open_naive = frozenset(g for g in range(design.G) if naive_sol.y[g] > 0.5)
    open_fair, _obj = stochastic_master_solve(design, (nominal_demand(design),))
    assert open_naive != open_fair  # der gemessene Unterschied, der die Korrektur nötig machte

    r = _standard(0, 80)
    assert r.open_det == open_fair
    assert r.open_det != open_naive
