import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ndu_scenario as sc
from ndu_model import Design, Mcf, generate_design
from ndu_formulation import solve_fixed_design, solve_mip
from ndu_uncertainty import (
    EMERGENCY_FRAC,
    EMERGENCY_MULT,
    PENALTY_MULT,
    draw_demand_scenario,
    evaluate_design_over_scenarios,
    mean_unit_cost,
    nominal_demand,
    recourse_solve,
    representative_scenarios,
    sample_scenarios,
    stochastic_master_solve,
)


def _toy_design():
    """S(0) -> A(2) [Werk, Kapazität 10] -> B(3) [Entwurfskante, Kapazität 5, Kosten 1, Gruppe 0] -> T(1) [Filiale]."""
    names = ("S", "T", "A", "B")
    pos = ((50, 100), (50, 0), (50, 66), (50, 33))
    arcs = ((0, 2, 10, 0, sc.K_SUPPLY), (2, 3, 5, 1, sc.K_THROUGHPUT), (3, 1, 999, 0, sc.K_DEMAND))
    net = sc.Net(names, names, pos, arcs, 0, 1, False)
    ub = (tuple([10 ** 6] * 3),)
    reward = tuple(a[1] == 1 for a in arcs)
    joint = tuple(a[4] != sc.K_DEMAND for a in arcs)
    mcf = Mcf(net, ("G1",), (1,), ub, joint, reward, 1000)
    return Design(mcf, (-1, 0, -1), (100,))


def test_recourse_matches_hand_calculation_normal_only():
    design = _toy_design()
    r = recourse_solve(design, frozenset({0}), (5,))
    assert r.flow_cost == pytest.approx(5.0)
    assert r.unmet_total == pytest.approx(0.0)


def test_recourse_matches_hand_calculation_with_emergency():
    design = _toy_design()
    # D=6: 5 normal (Kosten 5) + 1 Notfall (Kosten 4) = 9
    r = recourse_solve(design, frozenset({0}), (6,))
    assert r.flow_cost == pytest.approx(9.0)
    assert r.unmet_total == pytest.approx(0.0)


def test_recourse_matches_hand_calculation_with_shortfall():
    design = _toy_design()
    # D=8: 5 normal + 2,5 Notfall (Kapazitätsgrenze) = 7,5 geliefert, 0,5 Fehlmenge
    r = recourse_solve(design, frozenset({0}), (8,))
    assert r.flow_cost == pytest.approx(5.0 * 1 + 2.5 * 4)
    assert r.unmet_total == pytest.approx(0.5)
    penalty = PENALTY_MULT * mean_unit_cost(design)
    assert r.unmet_cost == pytest.approx(0.5 * penalty)


def test_recourse_closed_group_means_everything_unmet():
    design = _toy_design()
    r = recourse_solve(design, frozenset(), (5,))
    assert r.flow_cost == pytest.approx(0.0)
    assert r.unmet_total == pytest.approx(5.0)


def test_recourse_never_infeasible_even_with_zero_capacity():
    design = _toy_design()
    r = recourse_solve(design, frozenset(), (10 ** 6,))
    assert r.unmet_total == pytest.approx(10 ** 6)


def test_recourse_matches_solve_fixed_design_at_zero_variance():
    """Grenzfall ohne Streuung: das Recourse-Ergebnis auf der Nominalnachfrage mit dem Optimum-Open-Set muss
    genau dem Ergebnis von `solve_fixed_design`/`solve_mip` entsprechen (dieselben Kosten, keine Fehlmenge)."""
    design = generate_design(3, 3, 8, 60, 50, 80, 155, 1, 30)
    sol = solve_mip(design)
    open_set = frozenset(g for g in range(design.G) if sol.y[g] > 0.5)
    nominal = nominal_demand(design)
    r = recourse_solve(design, open_set, nominal)
    fixed_cost = sum(design.fixed[g] for g in open_set)
    assert r.total + fixed_cost == pytest.approx(sol.objective)
    assert r.unmet_total == pytest.approx(0.0)


def test_draw_demand_scenario_reproducible_and_bounded():
    design = generate_design(3, 3, 8, 60, 50, 80, 155, 1, 30)
    nominal = nominal_demand(design)
    a = draw_demand_scenario(design, 35, 42)
    b = draw_demand_scenario(design, 35, 42)
    assert a == b
    for d, n in zip(a, nominal):
        assert 0.65 * n - 1 <= d <= 1.35 * n + 1
        assert d >= 1


def test_representative_and_sample_scenarios_use_different_seeds():
    design = generate_design(3, 3, 8, 60, 50, 80, 155, 1, 30)
    repr_s = representative_scenarios(design, 35, 5, 155)
    samp_s = sample_scenarios(design, 35, 5, 155)
    assert repr_s != samp_s
    assert len(set(repr_s)) > 1


def test_stochastic_master_solve_is_at_least_as_good_in_sample():
    """Auf GENAU den Szenarien, für die das Master-MILP löst, darf keine schlechter Design-Auswahl (z.B. die
    deterministische) im Mittel günstiger sein - das Master-MILP optimiert exakt diesen Erwartungswert."""
    design = generate_design(3, 3, 8, 60, 50, 80, 155, 1, 30)
    scenarios = representative_scenarios(design, 35, 5, 1)
    open_stoch, obj = stochastic_master_solve(design, scenarios)
    ev_stoch_in_sample = evaluate_design_over_scenarios(design, open_stoch, scenarios)
    det_sol = solve_mip(design)
    open_det = frozenset(g for g in range(design.G) if det_sol.y[g] > 0.5)
    ev_det_in_sample = evaluate_design_over_scenarios(design, open_det, scenarios)
    assert ev_stoch_in_sample["expected_total"] <= ev_det_in_sample["expected_total"] + 1e-6


def test_evaluate_design_over_scenarios_matches_manual_average():
    design = generate_design(3, 3, 8, 60, 50, 80, 155, 1, 30)
    sol = solve_mip(design)
    open_set = frozenset(g for g in range(design.G) if sol.y[g] > 0.5)
    scenarios = representative_scenarios(design, 35, 4, 1)
    ev = evaluate_design_over_scenarios(design, open_set, scenarios)
    fixed_cost = sum(design.fixed[g] for g in open_set)
    manual = sum(fixed_cost + recourse_solve(design, open_set, s).total for s in scenarios) / len(scenarios)
    assert ev["expected_total"] == pytest.approx(manual)
