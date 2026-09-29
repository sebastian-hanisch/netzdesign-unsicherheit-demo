"""Netzdesign unter Nachfrageunsicherheit - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Wie teuer ist ein Netzwerk-Design, das nur für eine Nachfrage-Punktschätzung geplant wurde, verglichen mit einem
Design, das mehrere Nachfrage-Szenarien von Anfang an einplant? Fall-Demo auf der Themenseite Netzwerkdesign,
aufbauend auf dem Fixed-Charge-Network-Design-Modell aus fixkosten-netzdesign-demo. Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import ndu_constants as C
from ndu_evaluation import compare_designs
from ndu_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from ndu_visualization import build_comparison_bars, build_load_sweep, build_map

st.set_page_config(page_title="Netzdesign unter Nachfrageunsicherheit – Sebastian Hanisch", layout="wide")


def _int(x):
    return f"{int(round(x)):,}".replace(",", " ")


def _pct(x, digits=1):
    return f"{x:.{digits}f} %".replace(".", ",")


@st.cache_resource(show_spinner=False, max_entries=32)
def _compare(plants, dcs, stores, density, spread_lane, fix, seed, demand_spread, load):
    return compare_designs(plants, dcs, stores, density, spread_lane, fix, seed, demand_spread, load, C.N_REPR, C.N_SAMPLE)


@st.cache_resource(show_spinner=False, max_entries=16)
def _load_sweep(plants, dcs, stores, density, spread_lane, fix, seed):
    loads = list(range(C.LOAD_MIN, C.LOAD_MAX + 1, 10))
    spreads = (15, 65)
    rows = []
    for load in loads:
        cell = {}
        for spread in spreads:
            try:
                r = compare_designs(plants, dcs, stores, density, spread_lane, fix, seed, spread, load, C.N_REPR, 60)
                cell[spread] = r.gap_pct
            except RuntimeError:
                continue
        rows.append((load, cell))
    return rows


st.title("📦 Netzdesign unter Nachfrageunsicherheit")
st.markdown(
    """
Ein Fixkosten-Netzwerkdesign (welche Lanes und Verteilzentren gebaut werden) lässt sich für **eine** Nachfrage-
Punktschätzung planen (deterministisch) — oder für **mehrere** Nachfrage-Szenarien gleichzeitig (zweistufig
stochastisch, ein gemeinsames Design, das über alle Szenarien hinweg gut abschneidet). Dieselbe Ja/Nein-Entscheidung
wie in `fixkosten-netzdesign-demo`, hier unter Nachfrage-Unsicherheit zum Planungszeitpunkt statt mit bekannter
Nachfrage.
"""
)
st.caption(
    "Zwei gleichberechtigte Regler: die **Nachfrage-Streuung** (der inhaltliche Aufhänger) und die **Netzauslastung** "
    "(der versteckte Hebel, der entscheidet, ob sich Vorausschau überhaupt lohnt). Anders als die vier "
    "„starr vs. reaktiv“-Fall-Demos in diesem Portfolio: hier ist die Entscheidung einmalig und vorgelagert "
    "(welche Kapazität überhaupt gebaut wird, vor der Nachfragerealisierung eingefroren), nicht operatives Nachplanen."
)

st.caption("🎯 Schnellstart – ein Beispiel laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name) or None)

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Die zwei Kern-Regler**")
    demand_spread = st.slider("Nachfrage-Streuung [±%]", *bounds("demand_spread_slider"), key="demand_spread_slider", step=C.DEMAND_SPREAD_STEP,
                              help="Jede Filiale zieht ihre reale Nachfrage unabhängig gleichverteilt um ±X% der Nominalnachfrage.")
    load = st.slider("Netzauslastung [%]", *bounds("load_slider"), key="load_slider", step=C.LOAD_STEP,
                     help="Gesamtnachfrage in Prozent der Werkskapazität. Bei viel Reserve ist Unsicherheit fast irrelevant, bei knapper Kapazität zählt sie.")
    st.markdown("---")
    st.markdown("**Netzstruktur**")
    plants = st.slider("Werke", *bounds("plants_slider"), key="plants_slider")
    dcs = st.slider("Verteilzentren", *bounds("dcs_slider"), key="dcs_slider")
    stores = st.slider("Filialen", *bounds("stores_slider"), key="stores_slider")
    density = st.slider("Netzdichte [%]", *bounds("density_slider"), key="density_slider")
    spread_lane = st.slider("Streuung der Lane-Breiten [%]", *bounds("spread_lane_slider"), key="spread_lane_slider")
    fix = st.slider("Fixkosten-Basis", *bounds("fix_slider"), key="fix_slider")
    seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed)

sync_query_params(plants, dcs, stores, density, spread_lane, fix, seed, demand_spread, load)

try:
    with st.spinner("Rechne..."):
        r = _compare(int(plants), int(dcs), int(stores), int(density), int(spread_lane), int(fix), int(seed), int(demand_spread), int(load))
except RuntimeError:
    st.error("Der Löser kam bei dieser Kombination nicht zu einem Ergebnis. Bitte einen anderen Seed oder andere Regler-Werte wählen.")
    st.stop()

st.markdown(
    f"Das Netz hat **{r.n_groups} Entwurfsgruppen** ({r.n_edges} Kanten). Deterministisches Design: **{len(r.open_det)}** offene Gruppen, "
    f"Fixkosten **{_int(r.fixed_det)}**. Stochastisches Design ({C.N_REPR} Szenarien): **{len(r.open_stoch)}** offene Gruppen, Fixkosten **{_int(r.fixed_stoch)}**."
)

st.markdown("---")

st.markdown("## 🎯 Deterministisch gegen stochastisch")
st.caption(f"Beide Designs über {C.N_SAMPLE} identische Out-of-Sample-Nachfrage-Szenarien ausgewertet (Normalkosten bis Nominalkapazität, Notfallkapazität zum 4-fachen Preis, Fehlmenge bestraft).")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Erwartungswert deterministisch", _int(r.det_eval["expected_total"]))
c2.metric("Erwartungswert stochastisch", _int(r.stoch_eval["expected_total"]), delta=f"{_pct(r.gap_pct)} günstiger" if r.gap_pct > 0 else None, delta_color="off")
c3.metric("Fehlmenge (Mittel) deterministisch", _pct(100 * r.det_eval["expected_unmet_share"], 2))
c4.metric("Fehlmenge (Mittel) stochastisch", _pct(100 * r.stoch_eval["expected_unmet_share"], 2))

if r.gap_pct > 0.5:
    st.success(f"✅ Das deterministische Design kostet im Erwartungswert {_pct(r.gap_pct)} mehr als das stochastische (Worst Case: {_pct(r.worst_gap_pct)}). Die Topologie unterscheidet sich in {len(r.topology_diff)} von {r.n_groups} Gruppen.")
elif r.gap_pct < -0.5:
    st.warning(f"Bei dieser Konfiguration schneidet das deterministische Design out-of-sample sogar {_pct(-r.gap_pct)} besser ab — mit nur {C.N_REPR} repräsentativen Szenarien ist das Master-Design eine Näherung, kein Beweis des stochastischen Optimums.")
else:
    st.info("Die Lücke ist bei dieser Konfiguration praktisch null — Streuung oder Auslastung erhöhen, um den Effekt zu sehen.")

st.plotly_chart(build_comparison_bars(r.det_eval, r.stoch_eval), width="stretch", key="bars_chart")

st.markdown("## 🗺️ Netzkarte: wo unterscheiden sich die Designs?")
st.plotly_chart(build_map(r.design, r.open_det, r.open_stoch), width="stretch", key="map_chart")
st.caption("Lila: in beiden Designs offen. Grün: nur im stochastischen Design offen (Absicherung gegen Nachfragespitzen). Blau: nur im deterministischen Design offen. Grau: in beiden zu.")

st.markdown("---")

st.subheader("🔬 Wann lohnt sich Vorausschau? Auslastung als versteckter Hebel")
st.caption("Lücke deterministisch − stochastisch über die Netzauslastung, bei geringer und großer Streuung (dasselbe Netz, nur Auslastung und Streuung variiert).")
if st.button("Auslastungsreihe durchrechnen (dauert einige Sekunden)", key="sweep_start"):
    st.session_state["sweep_on"] = True
if st.session_state.get("sweep_on"):
    with st.spinner(f"Rechne {(C.LOAD_MAX - C.LOAD_MIN) // 10 + 1} Auslastungsstufen × 2 Streuungen..."):
        rows = _load_sweep(int(plants), int(dcs), int(stores), int(density), int(spread_lane), int(fix), int(seed))
    st.plotly_chart(build_load_sweep(rows), width="stretch", key="sweep_chart")
    st.caption("Bei viel Reserve (niedrige Auslastung) ist die Lücke klein oder null; erst bei knapper Kapazität wird Vorausschau spürbar wertvoll — und die Beziehung ist nicht perfekt monoton (diskrete Kapazitätsstufen), wie ehrlich gezeigt.")

st.markdown("---")

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist |
|---|---|
| **Notfallkapazität/Fehlmengenstrafe als feste Annahme** | Die genauen Faktoren (50 % Notfallkapazität, 4-facher Preis, 15-fache Strafe) sind plausibel gewählt, nicht aus echten Vertragsdaten. |
| **S repräsentative Szenarien statt vollem Szenariobaum** | Das Master-Design ist eine Näherung an die zweistufige stochastische Optimierung, kein Beweis des wahren Optimums — mit zu wenigen Szenarien generalisiert es schlechter (siehe Warnhinweis oben). |
| **Unabhängige Nachfrage je Filiale** | Korrelierte Nachfrageschocks (z. B. eine ganze Region) sind nicht abgebildet. |
| **Eine Güterart** | Das Mehrgütermodell des Vorbilds ist auf K=1 reduziert. |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Deterministisches Design.** Wie `fixkosten-netzdesign-demo`: $\min \sum_g f_g y_g + \sum_e c_e x_e$ mit
$x_e \le u_e y_{group(e)}$, Nachfrage exakt gedeckt, $y_g\in\{0,1\}$ — hier gelöst für die Nominalnachfrage.

**Recourse bei festem $y$ und realisierter Nachfrage $d$:** normaler Fluss $x_e\in[0,u_e]$ zu Kosten $c_e$,
Notfallfluss $x_e^{emg}\in[0,\,0{,}5\,u_e]$ zu Kosten $4c_e$ (nur auf offenen Kanten), je Filiale
$\text{geliefert}_j+\text{fehlmenge}_j=d_j$ mit Strafe $15\bar c$ je Fehlmengen-Einheit ($\bar c$ = mittlere
Stückkosten) — immer lösbar, da Fehlmenge nicht an Netzkapazität gebunden ist.

**Stochastisches Master-Design:** ein gemeinsames $y$ über $S=15$ repräsentative Szenarien, jedes mit eigenem
Recourse-Block:
$$\min \sum_g f_g y_g + \frac1S\sum_{s=1}^S\Big(\sum_e c_e x_e^s + 4c_e x_e^{emg,s} + 15\bar c\!\sum_j \text{fehlmenge}_j^s\Big)$$
mit $x_e^s, x_e^{emg,s} \le u_e y_{group(e)}$ (bzw. $0{,}5\,u_e$) je Szenario — dieselbe Entwurfsentscheidung $y$ für
alle Szenarien, aber ein eigener Fluss je Szenario.

Implementiert in `ndu_scenario.py`/`ndu_model.py`/`ndu_formulation.py` (Kopie aus `fixkosten-netzdesign-demo`, K=1),
`ndu_uncertainty.py` (Szenarien, Recourse-LP, Master-MILP), `ndu_evaluation.py` (der zentrale Vergleich).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
