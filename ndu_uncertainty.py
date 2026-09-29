"""Nachfrage-Unsicherheit auf dem Fixkosten-Netzdesign aus `ndu_model.py`/`ndu_formulation.py` (K=1 Gut, Kopie aus
`fixkosten-netzdesign-demo`): wie teuer ist ein Design, das nur für eine Nachfrage-Punktschätzung geplant wurde,
verglichen mit einem Design, das mehrere Nachfrage-Szenarien gemeinsam einplant (zweistufige Näherung)?

**Recourse bei festem Design (realer Nachfrage):** normale Kapazität der offenen Entwurfsgruppen zu Normalkosten;
zusätzlich bis zu `EMERGENCY_FRAC` der Kapazität zum `EMERGENCY_MULT`-fachen Preis (Spot-/Notfallkapazität);
darüber hinaus ungedeckte Nachfrage kostet `PENALTY_MULT` mal die mittleren Stückkosten je Einheit. Das macht das
Recourse-Problem IMMER lösbar (Fehlmenge ist immer eine zulässige, nur teure Option).

**Stochastisches Master-Design:** ein gemeinsames y über `S` repräsentative Nachfrage-Szenarien (Näherung an eine
vollständige zweistufige stochastische Optimierung, kein vollständiger Szenariobaum) — jedes Szenario bekommt seinen
eigenen Fluss- und Recourse-Block, alle teilen sich dieselbe Entwurfsentscheidung y.
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

import ndu_scenario as sc
from ndu_scenario import SplitMix64

EMERGENCY_FRAC = 0.5
EMERGENCY_MULT = 4.0
PENALTY_MULT = 15.0
SALT_REPR = 0x72657072          # "repr"
SALT_SAMPLE = 0x73616D70        # "samp"


def _design_edges(design):
    """(Kantenindex, u, v, Kapazität, Kosten, Gruppe) je entwurfskontrollierter Kante. Kosten über `mcf.cost(0, e)`
    (nicht das rohe Kantenfeld): Lane-Kanten tragen einen Kostenfaktor (K=1, `design.mcf.factors[0]`), den
    `mcf.cost` bereits anwendet — dieselbe Funktion wie `ndu_formulation._build`, damit die Zahlen übereinstimmen."""
    return [(e, u, v, cap, design.mcf.cost(0, e), design.group[e]) for e, (u, v, cap, cost, kind) in enumerate(design.net.arcs) if design.group[e] >= 0]


def _fixed_edges(design):
    """(Kantenindex, u, v, Kapazität, Kosten) je fest verfügbarer, nicht entwurfskontrollierter Kante (Werkskapazität)."""
    return [(e, u, v, cap, design.mcf.cost(0, e)) for e, (u, v, cap, cost, kind) in enumerate(design.net.arcs) if design.group[e] < 0 and kind != sc.K_DEMAND]


def _demand_edges(design):
    """(Kantenindex, Filialknoten, Nominalnachfrage) je Filiale, in Filial-Reihenfolge."""
    return [(e, u, cap) for e, (u, v, cap, cost, kind) in enumerate(design.net.arcs) if kind == sc.K_DEMAND]


def nominal_demand(design):
    return tuple(cap for _e, _u, cap in _demand_edges(design))


def mean_unit_cost(design):
    costs = [cost for _e, _u, _v, _cap, cost, _g in _design_edges(design)]
    costs += [cost for _e, _u, _v, _cap, cost in _fixed_edges(design)]
    return sum(costs) / len(costs) if costs else 1.0


def draw_demand_scenario(design, spread_pct, seed):
    """Je Filiale unabhängig ein ganzzahliger Faktor in [100-spread_pct, 100+spread_pct] Prozent auf die
    Nominalnachfrage (SplitMix64, fester Seed, plattformstabil), mindestens 1 Einheit."""
    rng = SplitMix64(seed)
    nominal = nominal_demand(design)
    return tuple(max(1, d * (100 + (rng.below(2 * spread_pct + 1) - spread_pct)) // 100) for d in nominal)


def representative_scenarios(design, spread_pct, n_scenarios, base_seed):
    return tuple(draw_demand_scenario(design, spread_pct, base_seed ^ SALT_REPR ^ (i * 0x9E3779B1)) for i in range(n_scenarios))


def sample_scenarios(design, spread_pct, n_samples, base_seed):
    return tuple(draw_demand_scenario(design, spread_pct, base_seed ^ SALT_SAMPLE ^ (i * 0x85EBCA6B)) for i in range(n_samples))


@dataclass(frozen=True)
class RecourseResult:
    flow_cost: float          # Normal- + Notfallkosten
    unmet_cost: float         # Fehlmengen-Strafe
    unmet_total: int          # Summe ungedeckter Einheiten
    demand_total: int

    @property
    def total(self):
        return self.flow_cost + self.unmet_cost

    @property
    def unmet_share(self):
        return self.unmet_total / self.demand_total if self.demand_total else 0.0


def _node_range(design):
    return [v for v in range(design.net.n) if v not in (design.net.s, design.net.t)]


def recourse_solve(design, open_set, demand_realization, emergency_frac=EMERGENCY_FRAC, emergency_mult=EMERGENCY_MULT, penalty_mult=PENALTY_MULT):
    """Bester Fluss bei festem Entwurf `open_set` und realisierter Nachfrage `demand_realization` (ausgerichtet an
    `_demand_edges`): Normalkapazität, Notfallkapazität, Fehlmenge. Immer lösbar."""
    des_edges = _design_edges(design)
    fix_edges = _fixed_edges(design)
    dem_edges = _demand_edges(design)
    penalty = penalty_mult * mean_unit_cost(design)

    nd, nf, ns = len(des_edges), len(fix_edges), len(dem_edges)
    n_cols = 2 * nd + nf + 2 * ns
    cost = np.zeros(n_cols)
    lo = np.zeros(n_cols)
    hi = np.zeros(n_cols)

    def col_normal(i): return i
    def col_emerg(i): return nd + i
    def col_fixed(j): return 2 * nd + j
    def col_delivered(k): return 2 * nd + nf + k
    def col_unmet(k): return 2 * nd + nf + ns + k

    for i, (_e, _u, _v, cap, unit_cost, g) in enumerate(des_edges):
        is_open = g in open_set
        hi[col_normal(i)] = cap if is_open else 0.0
        hi[col_emerg(i)] = emergency_frac * cap if is_open else 0.0
        cost[col_normal(i)] = unit_cost
        cost[col_emerg(i)] = unit_cost * emergency_mult
    for j, (_e, _u, _v, cap, unit_cost) in enumerate(fix_edges):
        hi[col_fixed(j)] = cap
        cost[col_fixed(j)] = unit_cost
    for k, d in enumerate(demand_realization):
        hi[col_delivered(k)] = d
        hi[col_unmet(k)] = d
        cost[col_unmet(k)] = penalty

    nodes = _node_range(design)
    row_of = {v: r for r, v in enumerate(nodes)}
    rows, cols, vals = [], [], []
    for i, (_e, u, v, _cap, _c, _g) in enumerate(des_edges):
        if u in row_of:
            rows.append(row_of[u]); cols.append(col_normal(i)); vals.append(-1.0)
            rows.append(row_of[u]); cols.append(col_emerg(i)); vals.append(-1.0)
        if v in row_of:
            rows.append(row_of[v]); cols.append(col_normal(i)); vals.append(1.0)
            rows.append(row_of[v]); cols.append(col_emerg(i)); vals.append(1.0)
    for j, (_e, u, v, _cap, _c) in enumerate(fix_edges):
        if u in row_of:
            rows.append(row_of[u]); cols.append(col_fixed(j)); vals.append(-1.0)
        if v in row_of:
            rows.append(row_of[v]); cols.append(col_fixed(j)); vals.append(1.0)
    for k, (_e, u, _d) in enumerate(dem_edges):
        if u in row_of:
            rows.append(row_of[u]); cols.append(col_delivered(k)); vals.append(-1.0)
    n_eq_node = len(nodes)
    row_base = n_eq_node
    for k, d in enumerate(demand_realization):
        rows.append(row_base + k); cols.append(col_delivered(k)); vals.append(1.0)
        rows.append(row_base + k); cols.append(col_unmet(k)); vals.append(1.0)
    b_eq = np.zeros(n_eq_node + ns)
    b_eq[n_eq_node:] = demand_realization
    a_eq = coo_matrix((vals, (rows, cols)), shape=(n_eq_node + ns, n_cols)).tocsr()

    res = milp(cost, constraints=[LinearConstraint(a_eq, b_eq, b_eq)], bounds=Bounds(lo, hi), integrality=np.zeros(n_cols))
    if res.status != 0 or res.x is None:
        raise RuntimeError(f"Recourse-LP nicht lösbar: {getattr(res, 'message', res.status)}")
    x = res.x
    flow_cost = float(sum(cost[col_normal(i)] * x[col_normal(i)] + cost[col_emerg(i)] * x[col_emerg(i)] for i in range(nd))
                       + sum(cost[col_fixed(j)] * x[col_fixed(j)] for j in range(nf)))
    unmet_total = float(sum(x[col_unmet(k)] for k in range(ns)))
    unmet_cost = penalty * unmet_total
    return RecourseResult(flow_cost, unmet_cost, unmet_total, float(sum(demand_realization)))


def evaluate_design_over_scenarios(design, open_set, scenarios, **kw):
    """Erwartete und Worst-Case-Gesamtkosten (Fixkosten einmal + mittlere Recourse-Kosten) über mehrere Szenarien."""
    fixed_cost = sum(design.fixed[g] for g in open_set)
    results = [recourse_solve(design, open_set, s, **kw) for s in scenarios]
    totals = [fixed_cost + r.total for r in results]
    return {
        "fixed_cost": fixed_cost,
        "expected_total": sum(totals) / len(totals),
        "worst_total": max(totals),
        "expected_unmet_share": sum(r.unmet_share for r in results) / len(results),
        "results": results,
    }


def stochastic_master_solve(design, demand_scenarios, emergency_frac=EMERGENCY_FRAC, emergency_mult=EMERGENCY_MULT, penalty_mult=PENALTY_MULT, time_limit=60.0):
    """Ein gemeinsames y über alle `demand_scenarios` (Master-MILP, S = len(demand_scenarios) repräsentative
    Szenarien); jedes Szenario bekommt seinen eigenen Fluss-/Recourse-Block. Minimiert Fixkosten + mittlere
    Recourse-Kosten über die Szenarien."""
    des_edges = _design_edges(design)
    fix_edges = _fixed_edges(design)
    dem_edges = _demand_edges(design)
    penalty = penalty_mult * mean_unit_cost(design)
    G = design.G
    nd, nf, ns = len(des_edges), len(fix_edges), len(dem_edges)
    S = len(demand_scenarios)
    block = 2 * nd + nf + 2 * ns
    n_cols = G + S * block

    def y_col(g): return g
    def col_normal(s, i): return G + s * block + i
    def col_emerg(s, i): return G + s * block + nd + i
    def col_fixed(s, j): return G + s * block + 2 * nd + j
    def col_delivered(s, k): return G + s * block + 2 * nd + nf + k
    def col_unmet(s, k): return G + s * block + 2 * nd + nf + ns + k

    cost = np.zeros(n_cols)
    lo = np.zeros(n_cols)
    hi = np.zeros(n_cols)
    hi[:G] = 1.0
    for g in range(G):
        cost[y_col(g)] = design.fixed[g]
    for s in range(S):
        for i, (_e, _u, _v, cap, unit_cost, _g) in enumerate(des_edges):
            hi[col_normal(s, i)] = cap
            hi[col_emerg(s, i)] = emergency_frac * cap
            cost[col_normal(s, i)] = unit_cost / S
            cost[col_emerg(s, i)] = unit_cost * emergency_mult / S
        for j, (_e, _u, _v, cap, unit_cost) in enumerate(fix_edges):
            hi[col_fixed(s, j)] = cap
            cost[col_fixed(s, j)] = unit_cost / S
        for k, d in enumerate(demand_scenarios[s]):
            hi[col_delivered(s, k)] = d
            hi[col_unmet(s, k)] = d
            cost[col_unmet(s, k)] = penalty / S

    nodes = _node_range(design)
    row_of = {v: r for r, v in enumerate(nodes)}
    n_eq_node = len(nodes)
    rows, cols, vals = [], [], []
    ineq_rows, ineq_cols, ineq_vals, ineq_rhs = [], [], [], []
    r_ineq = 0
    for s in range(S):
        base = s * (n_eq_node + ns)
        for i, (_e, u, v, _cap, _c, _g) in enumerate(des_edges):
            if u in row_of:
                rows.append(base + row_of[u]); cols.append(col_normal(s, i)); vals.append(-1.0)
                rows.append(base + row_of[u]); cols.append(col_emerg(s, i)); vals.append(-1.0)
            if v in row_of:
                rows.append(base + row_of[v]); cols.append(col_normal(s, i)); vals.append(1.0)
                rows.append(base + row_of[v]); cols.append(col_emerg(s, i)); vals.append(1.0)
        for j, (_e, u, v, _cap, _c) in enumerate(fix_edges):
            if u in row_of:
                rows.append(base + row_of[u]); cols.append(col_fixed(s, j)); vals.append(-1.0)
            if v in row_of:
                rows.append(base + row_of[v]); cols.append(col_fixed(s, j)); vals.append(1.0)
        for k, (_e, u, _d) in enumerate(dem_edges):
            if u in row_of:
                rows.append(base + row_of[u]); cols.append(col_delivered(s, k)); vals.append(-1.0)
        for k, d in enumerate(demand_scenarios[s]):
            rows.append(base + n_eq_node + k); cols.append(col_delivered(s, k)); vals.append(1.0)
            rows.append(base + n_eq_node + k); cols.append(col_unmet(s, k)); vals.append(1.0)
        # Kopplung an y: normal[s,i] <= cap * y[g], emergency[s,i] <= frac*cap * y[g]
        for i, (_e, _u, _v, cap, _c, g) in enumerate(des_edges):
            ineq_rows.append(r_ineq); ineq_cols.append(col_normal(s, i)); ineq_vals.append(1.0)
            ineq_rows.append(r_ineq); ineq_cols.append(y_col(g)); ineq_vals.append(-float(cap))
            ineq_rhs.append(0.0); r_ineq += 1
            ineq_rows.append(r_ineq); ineq_cols.append(col_emerg(s, i)); ineq_vals.append(1.0)
            ineq_rows.append(r_ineq); ineq_cols.append(y_col(g)); ineq_vals.append(-float(emergency_frac * cap))
            ineq_rhs.append(0.0); r_ineq += 1

    b_eq = np.zeros(S * (n_eq_node + ns))
    for s in range(S):
        base = s * (n_eq_node + ns)
        for k, d in enumerate(demand_scenarios[s]):
            b_eq[base + n_eq_node + k] = d
    a_eq = coo_matrix((vals, (rows, cols)), shape=(S * (n_eq_node + ns), n_cols)).tocsr()
    a_ub = coo_matrix((ineq_vals, (ineq_rows, ineq_cols)), shape=(r_ineq, n_cols)).tocsr()

    integrality = np.zeros(n_cols)
    integrality[:G] = 1
    res = milp(cost, constraints=[LinearConstraint(a_eq, b_eq, b_eq), LinearConstraint(a_ub, -np.inf, np.array(ineq_rhs))],
               bounds=Bounds(lo, hi), integrality=integrality, options={"time_limit": time_limit, "mip_rel_gap": 0.0})
    if res.status != 0 or res.x is None:
        raise RuntimeError(f"Master-MILP nicht optimal gelöst: {getattr(res, 'message', res.status)}")
    open_set = frozenset(g for g in range(G) if res.x[y_col(g)] > 0.5)
    return open_set, float(res.fun)
