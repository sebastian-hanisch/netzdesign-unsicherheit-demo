"""Plotly-Abbildungen: Netzkarte mit Entwurfs-Status je Gruppe (deterministisch/stochastisch/beide/keins), Balken
det. gegen stoch. (erwartete Kosten, Fehlmenge), Linien der Lücke über Auslastung je Streuungsstufe."""

import plotly.graph_objects as go

import ndu_constants as C
import ndu_scenario as sc


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_map(design, open_det, open_stoch, height=460):
    """Netzkarte: Knoten nach Schicht positioniert (wie im Vorbild), Kanten eingefärbt nach Entwurfs-Status.
    Nur entwurfskontrollierte Kanten (Lanes, DC-Durchsatz) tragen eine Statusfarbe; feste Kanten (Werk, Nachfrage) grau."""
    net = design.net
    fig = go.Figure()

    def status(e):
        g = design.group[e]
        if g < 0:
            return "fix"
        in_det, in_stoch = g in open_det, g in open_stoch
        if in_det and in_stoch:
            return "both"
        if in_stoch:
            return "stoch_only"
        if in_det:
            return "det_only"
        return "neither"

    groups = {"both": ("beide offen", "#6a3d9a"), "stoch_only": ("nur stochastisch offen", "#2ca02c"),
              "det_only": ("nur deterministisch offen", "#1f77b4"), "neither": ("beide zu", "#9aa0a6"), "fix": ("fest (Werk/Nachfrage)", "#c7c7c7")}
    for key, (label, color) in groups.items():
        xs, ys = [], []
        for e, (u, v, _cap, _cost, kind) in enumerate(net.arcs):
            if kind == sc.K_DEMAND or status(e) != key:
                continue
            xs += [net.pos[u][0], net.pos[v][0], None]
            ys += [net.pos[u][1], net.pos[v][1], None]
        if xs:
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=3 if key != "fix" else 1), name=label, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[p[0] for p in net.pos], y=[p[1] for p in net.pos], mode="markers+text", text=list(net.labels),
                             textposition="middle center", marker=dict(size=22, color="#f0f0f0", line=dict(color="#333333", width=1)),
                             textfont=dict(size=9), showlegend=False, hovertext=list(net.names), hoverinfo="text"))
    fig.update_xaxes(visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False)
    return _base(fig, height)


def build_comparison_bars(det_eval, stoch_eval, height=340):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["Deterministisch", "Stochastisch"], y=[det_eval["expected_total"], stoch_eval["expected_total"]],
                         marker=dict(color=[C.COLORS["det"], C.COLORS["stoch"]]),
                         text=[f"{v:,.0f}".replace(",", " ") for v in (det_eval["expected_total"], stoch_eval["expected_total"])], textposition="outside"))
    fig.update_yaxes(title="Erwartete Gesamtkosten")
    return _base(fig, height)


def build_load_sweep(rows, height=380):
    """`rows`: Liste von (load, {spread: gap_pct})."""
    fig = go.Figure()
    spreads = sorted({s for _l, d in rows for s in d})
    colors = {spreads[0]: "#1f77b4", spreads[-1]: "#d62728"} if len(spreads) > 1 else {}
    for s in spreads:
        fig.add_trace(go.Scatter(x=[l for l, d in rows if s in d], y=[d[s] for _l, d in rows if s in d], mode="lines+markers",
                                 name=f"±{s} % Streuung", line=dict(color=colors.get(s))))
    fig.add_hline(y=0, line=dict(color="#111111", dash="dash"))
    fig.update_xaxes(title="Netzauslastung [%]")
    fig.update_yaxes(title="Lücke deterministisch − stochastisch [%]")
    return _base(fig, height)
