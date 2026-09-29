"""Die aus `fixkosten-netzdesign-demo` kopierten Bausteine (SplitMix64-Strom, Netzgenerator, Entwurfsmodell,
Formulierung) sind bewacht: dieselben Zahlen wie im Vorgänger für K=1."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ndu_model import generate_design
from ndu_formulation import solve_mip
from ndu_scenario import SplitMix64


def test_splitmix64_stream_is_the_portfolio_standard():
    rng = SplitMix64(1)
    assert [rng.next() for _ in range(3)] == [10451216379200822465, 13757245211066428519, 17911839290282890590]


def test_standard_design_matches_fixkosten_netzdesign_demo_family():
    """Dasselbe Netz/Modell wie die Vorgänger-Linie (3/3/8, Dichte 60, Streuung 50, K=1), Seed 155, Fixkosten-Basis 30, Auslastung 80 %."""
    d = generate_design(3, 3, 8, 60, 50, 80, 155, 1, 30)
    assert d.G == 27
    assert d.m == 38
    sol = solve_mip(d)
    assert sol.objective == 2609.0
    assert sol.flow_cost == 1679.0
    assert sol.fixed_cost == 930.0
