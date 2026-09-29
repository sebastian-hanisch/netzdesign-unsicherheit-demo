"""Zusammenspiel: deterministisches Design (Nominalnachfrage) gegen stochastisches Design (mehrere repräsentative
Szenarien), beide über dieselben Out-of-Sample-Szenarien ausgewertet — der zentrale Vergleich dieser Demo.

WICHTIG (per Vormessung gefunden, siehe test_evaluation.py/test_uncertainty.py): das deterministische Design darf
NICHT mit `ndu_formulation.solve_mip` (das Vorbild ohne jede Notfallkapazität) berechnet werden — dessen Lösung
kennt den Recourse-Mechanismus gar nicht, während das stochastische Design ihn nutzt. Verglichen mit demselben
Recourse aber ohne Streuung (`stochastic_master_solve` mit genau EINEM Szenario, der Nominalnachfrage) baut
`solve_mip` systematisch zu viel Kapazität und ist deshalb sogar bei Streuung 0 % teurer (ein Bug-ähnlicher Fund
beim Testen: 1,3 % „Lücke" bei Streuung 0, obwohl der einzige Unterschied Recourse-Bewusstsein war, nicht
Nachfrage-Unsicherheit). Deterministisch heißt hier deshalb: derselbe Recourse-Mechanismus, aber nur EIN
Szenario (die Nominalnachfrage) statt mehrerer — damit die gemessene Lücke wirklich nur die Streuung isoliert."""

from dataclasses import dataclass

from ndu_model import generate_design
from ndu_uncertainty import (
    evaluate_design_over_scenarios,
    nominal_demand,
    representative_scenarios,
    sample_scenarios,
    stochastic_master_solve,
)


@dataclass(frozen=True)
class ComparisonResult:
    design: object
    open_det: frozenset
    open_stoch: frozenset
    fixed_det: float
    fixed_stoch: float
    det_eval: dict
    stoch_eval: dict
    n_groups: int
    n_edges: int

    @property
    def gap_pct(self):
        return 100.0 * (self.det_eval["expected_total"] - self.stoch_eval["expected_total"]) / self.stoch_eval["expected_total"]

    @property
    def worst_gap_pct(self):
        return 100.0 * (self.det_eval["worst_total"] - self.stoch_eval["worst_total"]) / self.stoch_eval["worst_total"]

    @property
    def topology_diff(self):
        return sorted(self.open_stoch.symmetric_difference(self.open_det))


def compare_designs(plants, dcs, stores, density, spread_lane, fix, seed, demand_spread_pct, load, n_repr, n_sample):
    """Baut das Netz, löst das deterministische Design (Nominalnachfrage) und das stochastische Master-Design
    (`n_repr` repräsentative Szenarien), wertet beide über dieselben `n_sample` Out-of-Sample-Szenarien aus."""
    design = generate_design(plants, dcs, stores, density, spread_lane, load, seed, 1, fix)
    open_det, _obj_det = stochastic_master_solve(design, (nominal_demand(design),))

    repr_scenarios = representative_scenarios(design, demand_spread_pct, n_repr, seed)
    open_stoch, _obj = stochastic_master_solve(design, repr_scenarios)

    samples = sample_scenarios(design, demand_spread_pct, n_sample, seed)
    det_eval = evaluate_design_over_scenarios(design, open_det, samples)
    stoch_eval = evaluate_design_over_scenarios(design, open_stoch, samples)

    return ComparisonResult(design, open_det, open_stoch, det_eval["fixed_cost"], stoch_eval["fixed_cost"],
                             det_eval, stoch_eval, design.G, design.m)
