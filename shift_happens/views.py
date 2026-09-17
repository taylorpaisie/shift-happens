"""Dash components and Plotly tracks; no import or statistical logic."""
import json
from dash import html
import plotly.graph_objects as go
from .model import STATES, classify


def track_figure(analyses, threshold, start, end, selected):
    figure = go.Figure()
    for row, a in enumerate(analyses):
        codons = list(range(start, end + 1))
        states = [STATES[classify(a, a.sites.get(c), threshold)] for c in codons]
        figure.add_trace(go.Bar(
            x=codons, y=[0.54] * len(codons), base=row - 0.27, width=0.86,
            marker=dict(color=[s[1] for s in states], line=dict(color="#8192a0", width=0.6)),
            text=[s[2] for s in states], textposition="inside", insidetextanchor="middle",
            textfont=dict(color=["white" if s[2] in ("−", "+", "E", "Δ") else "#26394b" for s in states], size=12),
            customdata=[[c, s[0], a.sites[c].values.get("p") if c in a.sites else None] for c, s in zip(codons, states)],
            hovertemplate="Codon %{customdata[0]}<br>%{customdata[1]}<br>Unadjusted p: %{customdata[2]}<extra></extra>",
            name=a.method, showlegend=False,
        ))
    if analyses:
        figure.add_vrect(x0=selected - 0.49, x1=selected + 0.49, fillcolor="rgba(0,0,0,0)", line_color="#172e43", line_width=2)
    figure.update_layout(
        template="plotly_white", barmode="overlay", height=160 + 70 * max(1, len(analyses)),
        margin=dict(l=105, r=16, t=22, b=52), font=dict(family="Arial, sans-serif", color="#203345"),
        paper_bgcolor="white", plot_bgcolor="white", clickmode="event", uniformtext=dict(minsize=9, mode="hide"),
        xaxis=dict(title="Alignment codon (1-based)", range=[start - 0.6, end + 0.6], fixedrange=True, showgrid=False, dtick=max(1, (end-start+1)//12)),
        yaxis=dict(tickvals=list(range(len(analyses))), ticktext=[a.method for a in analyses], range=[len(analyses)-0.4, -0.6], fixedrange=True, showgrid=False, zeroline=False),
    )
    return figure


def disclosure(title, value):
    return html.Details([html.Summary(title), html.Pre("Not reported" if value is None else json.dumps(value, ensure_ascii=False, indent=2))])


def inspector(analyses, codon, threshold):
    cards = []
    for a in analyses:
        site = a.sites.get(codon)
        v = site.values if site else {}
        state = classify(a, site, threshold)
        pairs = [("p-value (unadjusted)", v.get("p")), ("Synonymous rate α", v.get("alpha"))]
        if a.method == "FEL":
            pairs.append(("Nonsynonymous rate β", v.get("beta")))
        elif a.method == "MEME":
            pairs.extend((label, v.get(key)) for label, key in [("Nonsynonymous rate β−", "betaMinus"), ("Nonsynonymous rate β+", "betaPlus"), ("Mixture weight p+", "weightPlus")])
        else:
            pairs.extend((label, v.get(key)) for label, key in [("Group A rate (synthetic)", "groupA"), ("Group B rate (synthetic)", "groupB")])
        pairs.extend([("Likelihood ratio statistic", v.get("lrt")), ("Inferred branch length", v.get("branchLength")),
                      ("Tested scope", a.scope_summary), ("Source", a.filename), ("Method version", a.version),
                      ("Mapping", f"Partition 0, source row {site.row} → codon {codon}" if site else "Outside this file’s covered sites")])
        definition = [item for name, value in pairs for item in (html.Dt(name), html.Dd("Not available" if value is None else str(value)))]
        cards.append(html.Article([
            html.H3(a.method), html.P(STATES[state][0], className=f"state-label {state}"), html.P(a.scope, className="hint"),
            html.Dl(definition), html.P(a.correction, className="hint"),
            html.P("Rate ratios are omitted: zero or poorly estimated synonymous rates can make dN/dS misleading.", className="hint"),
            html.P("; ".join(site.issues) if site else "Not covered by this analysis.", className="warning"),
            disclosure("Tested branches & input tree", dict(tested=a.raw["tested"], trees=a.raw.get("input", {}).get("trees"))),
            disclosure("Source metadata & analysis settings", {k: a.raw.get(k) for k in ("analysis", "input", "settings", "data partitions")}),
            disclosure("Available model fits & timings", {k: a.raw.get(k) for k in ("fits", "timers")}),
            disclosure("Original site values & column definitions", dict(headers=a.raw.get("MLE", {}).get("headers"), row=site.native if site else None)),
        ], className="evidence-card"))
    return cards


def legend():
    return [html.Span([html.Span(symbol, className="swatch", style={"backgroundColor": color, "color": "white" if symbol in ("−", "+", "E", "Δ") else "#203345"}), label]) for label, color, symbol in STATES.values()]
