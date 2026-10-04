"""Konstanten, Regler-Grenzen und feste Seed-Mengen der Demo "Netzdesign unter Nachfrageunsicherheit"."""

# --- Regler Distributionsnetz (wie fixkosten-netzdesign-demo) ----------------------------------------------------
P_MIN, P_MAX, DEFAULT_P = 2, 5, 3
D_MIN, D_MAX, DEFAULT_D = 2, 5, 3
S_MIN, S_MAX, DEFAULT_S = 4, 12, 8
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 30, 100, 60
SPREAD_LANE_MIN, SPREAD_LANE_MAX, DEFAULT_SPREAD_LANE = 0, 100, 50    # Streuung der Lane-Breiten (Netzaufbau, nicht die Nachfrage-Unsicherheit)
FIX_MIN, FIX_MAX, DEFAULT_FIX = 10, 80, 30
DEFAULT_SEED = 155
SEED_MAX = 2_000_000_000

# --- die zwei Kern-Regler: Nachfrage-Streuung und Netzauslastung --------------------------------------------------
# Gemessen (siehe README "Was nicht funktioniert hat"): der faire, Recourse-bewusste Vergleich zeigt eine Lücke
# erst ab grober Streuung (~50 %+); darunter ist sie praktisch null. Default deshalb bei 65 %, nicht in der Mitte
# des Reglers, damit die Standardansicht den echten Effekt zeigt statt einer Null.
DEMAND_SPREAD_MIN, DEMAND_SPREAD_MAX, DEFAULT_DEMAND_SPREAD, DEMAND_SPREAD_STEP = 0, 65, 65, 5   # Prozent
LOAD_MIN, LOAD_MAX, DEFAULT_LOAD, LOAD_STEP = 50, 90, 80, 5    # Gesamtnachfrage in % der Werkskapazität

N_REPR = 15          # repräsentative Szenarien im Master-MILP (gemessen: S=7 generalisiert out-of-sample zu unruhig, ab ~15 stabil positiv)
N_SAMPLE = 120        # Out-of-Sample-Szenarien für die angezeigte erwartete Kostenlücke

COLORS = {"det": "#1f77b4", "stoch": "#2ca02c", "unmet_det": "#d62728", "unmet_stoch": "#2ca02c", "opt": "#111111"}

# --- Presets -------------------------------------------------------------------------------------------------------
_BASE = dict(plants=DEFAULT_P, dcs=DEFAULT_D, stores=DEFAULT_S, density=DEFAULT_DENSITY, spread_lane=DEFAULT_SPREAD_LANE,
             fix=DEFAULT_FIX, seed=DEFAULT_SEED, demand_spread=DEFAULT_DEMAND_SPREAD, load=DEFAULT_LOAD)
PRESETS = {
    "🗺️ Standardnetz": {**_BASE},
    "🔎 Moderate Streuung": {**_BASE, "demand_spread": 35},
    "📦 Mehr Reserve": {**_BASE, "load": 70},
    "⚠️ Noch mehr Reserve": {**_BASE, "load": 60},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py belegt (aus dem echten Code neu berechnet).
PRESET_HELP = {
    "🗺️ Standardnetz": "3 Werke, 3 Verteilzentren, 8 Filialen, Auslastung 80 %, ±65 % Nachfrage-Streuung: das deterministische Design (recourse-bewusst, aber nur für die Nominalnachfrage geplant) kostet im Erwartungswert 4,4 % mehr als das für mehrere Szenarien geplante — und deckt im Mittel seltener die volle Nachfrage (2,2 % gegen 0,1 % Fehlmenge).",
    "🔎 Moderate Streuung": "Nur ±35 % statt ±65 % Streuung: die Lücke verschwindet vollständig (0,0 %, identische Topologie) — sobald beide Designs den Notfall-Mechanismus kennen, lohnt sich Szenario-Planung erst bei grober Unsicherheit.",
    "📦 Mehr Reserve": "70 % statt 80 % Auslastung, weiter ±65 % Streuung: die Lücke schrumpft auf 1,2 % — mehr Kapazitätsreserve dämpft den Effekt, aber die Beziehung ist nicht glatt (diskrete Kapazitätsstufen).",
    "⚠️ Noch mehr Reserve": "60 % statt 80 % Auslastung, ±65 % Streuung: die Lücke wächst auf 6,4 % (Worst Case 50,0 %) — die größte gemessene Lücke in dieser Demo, obwohl hier die Auslastung niedriger und die Reserve größer ist als beim Standardnetz (nicht monoton).",
}
