"""SETTING_SPECS-Permalink-Muster, Presets und Zufalls-Seed-Button (nach dem in `linehaul-demo` etablierten Muster)."""

import random

import streamlit as st

import ndu_constants as C

SETTING_SPECS = {
    "plants_slider": {"url": "p", "caster": int, "default": C.DEFAULT_P, "lo": C.P_MIN, "hi": C.P_MAX},
    "dcs_slider": {"url": "d", "caster": int, "default": C.DEFAULT_D, "lo": C.D_MIN, "hi": C.D_MAX},
    "stores_slider": {"url": "s", "caster": int, "default": C.DEFAULT_S, "lo": C.S_MIN, "hi": C.S_MAX},
    "density_slider": {"url": "den", "caster": int, "default": C.DEFAULT_DENSITY, "lo": C.DENSITY_MIN, "hi": C.DENSITY_MAX},
    "spread_lane_slider": {"url": "sl", "caster": int, "default": C.DEFAULT_SPREAD_LANE, "lo": C.SPREAD_LANE_MIN, "hi": C.SPREAD_LANE_MAX},
    "fix_slider": {"url": "f", "caster": int, "default": C.DEFAULT_FIX, "lo": C.FIX_MIN, "hi": C.FIX_MAX},
    "seed_input": {"url": "seed", "caster": int, "default": C.DEFAULT_SEED, "lo": 0, "hi": C.SEED_MAX},
    "demand_spread_slider": {"url": "ds", "caster": int, "default": C.DEFAULT_DEMAND_SPREAD, "lo": C.DEMAND_SPREAD_MIN, "hi": C.DEMAND_SPREAD_MAX},
    "load_slider": {"url": "l", "caster": int, "default": C.DEFAULT_LOAD, "lo": C.LOAD_MIN, "hi": C.LOAD_MAX},
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec["lo"], spec["hi"]


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec["default"]


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec["url"] in qp:
            try:
                value = spec["caster"](qp[spec["url"]])
                value = max(spec["lo"], min(spec["hi"], value))
                st.session_state[state_key] = value
            except (ValueError, TypeError):
                pass
    st.session_state["permalink_loaded"] = True


def sync_query_params(plants, dcs, stores, density, spread_lane, fix, seed, demand_spread, load):
    try:
        st.query_params["p"] = str(int(plants))
        st.query_params["d"] = str(int(dcs))
        st.query_params["s"] = str(int(stores))
        st.query_params["den"] = str(int(density))
        st.query_params["sl"] = str(int(spread_lane))
        st.query_params["f"] = str(int(fix))
        st.query_params["seed"] = str(int(seed))
        st.query_params["ds"] = str(int(demand_spread))
        st.query_params["l"] = str(int(load))
    except Exception:
        pass


def apply_preset(name):
    p = C.PRESETS[name]
    st.session_state["plants_slider"] = p["plants"]
    st.session_state["dcs_slider"] = p["dcs"]
    st.session_state["stores_slider"] = p["stores"]
    st.session_state["density_slider"] = p["density"]
    st.session_state["spread_lane_slider"] = p["spread_lane"]
    st.session_state["fix_slider"] = p["fix"]
    st.session_state["seed_input"] = p["seed"]
    st.session_state["demand_spread_slider"] = p["demand_spread"]
    st.session_state["load_slider"] = p["load"]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
