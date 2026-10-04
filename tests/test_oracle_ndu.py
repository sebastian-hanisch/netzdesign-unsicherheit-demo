"""Unabhängiges Orakel für Recourse-LP und stochastisches Master-MILP: Recourse als Min-Cost-Flow mit networkx
(Netzwerk-Simplex auf ganzzahlig skalierten Kosten, Fehlmenge als Direktkante S -> T), Master per Vollenumeration
aller Entwurfsmengen, SplitMix64 gegen die veröffentlichten Referenzwerte."""

import itertools
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

nx = pytest.importorskip("networkx")

import ndu_scenario as sc
from ndu_model import generate_design
from ndu_uncertainty import draw_demand_scenario, recourse_solve, representative_scenarios, stochastic_master_solve

LANES = (sc.K_LANE_IN, sc.K_LANE_OUT)


def _oracle_recourse_total(design, open_set, demand):
    design_edges, fixed_edges, demand_edges = [], [], []
    for e, (u, v, cap, cost, kind) in enumerate(design.net.arcs):
        c = cost * 2 if kind in LANES else cost   # Kostenfaktor des Guts auf Lanes
        if design.group[e] >= 0:
            design_edges.append((u, v, cap, c, design.group[e]))
        elif kind == sc.K_DEMAND:
            demand_edges.append(u)
        else:
            fixed_edges.append((u, v, cap, c))
    costs = [c for *_rest, c, _g in design_edges] + [c for _u, _v, _cap, c in fixed_edges]
    n_costs, cost_sum = len(costs), sum(costs)
    total_demand = int(sum(demand))
    graph = nx.MultiDiGraph()
    graph.add_nodes_from((v, {"demand": 0}) for v in range(design.net.n))
    graph.nodes[design.net.s]["demand"] = -2 * total_demand      # Kapazitäten verdoppelt: Notfall = 0,5 * cap ganzzahlig
    graph.nodes[design.net.t]["demand"] = 2 * total_demand
    for u, v, cap, c, g in design_edges:
        if g in open_set:
            graph.add_edge(u, v, capacity=2 * cap, weight=c * n_costs)
            graph.add_edge(u, v, capacity=cap, weight=4 * c * n_costs)
    for u, v, cap, c in fixed_edges:
        graph.add_edge(u, v, capacity=2 * cap, weight=c * n_costs)
    for u, d in zip(demand_edges, demand):
        graph.add_edge(u, design.net.t, capacity=2 * int(d), weight=0)
    graph.add_edge(design.net.s, design.net.t, weight=15 * cost_sum)   # Fehlmenge: 15 x mittlere Stückkosten
    scaled_cost, _flow = nx.network_simplex(graph)
    return scaled_cost / (2 * n_costs)


def test_splitmix64_matches_reference_vectors():
    rng = sc.SplitMix64(0)
    assert [rng.next() for _ in range(3)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F]


def test_recourse_matches_min_cost_flow_oracle():
    rng = random.Random(99)
    for _ in range(80):
        design = generate_design(rng.randint(2, 5), rng.randint(2, 5), rng.randint(4, 12), rng.randint(30, 100),
                                 rng.randint(0, 100), rng.choice([50, 70, 90]), rng.randint(0, 10 ** 6), 1, rng.randint(10, 80))
        open_set = frozenset(g for g in range(design.G) if rng.random() < rng.choice([0.3, 0.6, 0.9, 1.0]))
        scenario = draw_demand_scenario(design, rng.choice([0, 20, 65]), rng.randint(0, 10 ** 6))
        assert recourse_solve(design, open_set, scenario).total == pytest.approx(
            _oracle_recourse_total(design, open_set, scenario), rel=1e-6, abs=1e-6)


def test_stochastic_master_matches_enumeration_of_all_open_sets():
    rng = random.Random(777)
    checked = 0
    while checked < 8:
        design = generate_design(2, 2, rng.randint(3, 4), rng.randint(30, 70), rng.randint(0, 100),
                                 rng.choice([50, 60, 70, 80, 90]), rng.randint(0, 10 ** 6), 1, rng.randint(10, 80))
        if design.G > 8:
            continue
        scenarios = representative_scenarios(design, rng.choice([20, 35, 65]), rng.choice([2, 3]), rng.randint(0, 10 ** 6))

        def value(open_set):
            return (sum(design.fixed[g] for g in open_set)
                    + sum(_oracle_recourse_total(design, open_set, s) for s in scenarios) / len(scenarios))

        best = min(value(frozenset(sub)) for r in range(design.G + 1) for sub in itertools.combinations(range(design.G), r))
        open_set, objective = stochastic_master_solve(design, scenarios)
        assert objective == pytest.approx(best, rel=1e-6)
        assert value(open_set) == pytest.approx(best, rel=1e-6)
        checked += 1
