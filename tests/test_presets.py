import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ndu_constants as C
from ndu_presets import SETTING_SPECS


def test_every_preset_has_all_keys():
    required = {"plants", "dcs", "stores", "density", "spread_lane", "fix", "seed", "demand_spread", "load"}
    for name, p in C.PRESETS.items():
        assert required.issubset(p.keys()), name


def test_preset_values_within_bounds():
    for name, p in C.PRESETS.items():
        assert C.P_MIN <= p["plants"] <= C.P_MAX, name
        assert C.D_MIN <= p["dcs"] <= C.D_MAX, name
        assert C.S_MIN <= p["stores"] <= C.S_MAX, name
        assert C.DENSITY_MIN <= p["density"] <= C.DENSITY_MAX, name
        assert C.DEMAND_SPREAD_MIN <= p["demand_spread"] <= C.DEMAND_SPREAD_MAX, name
        assert C.LOAD_MIN <= p["load"] <= C.LOAD_MAX, name


def test_setting_specs_defaults_within_own_bounds():
    for key, spec in SETTING_SPECS.items():
        assert spec["lo"] <= spec["default"] <= spec["hi"], key
