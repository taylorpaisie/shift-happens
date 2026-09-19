"""Run with `python app.py`; always binds to localhost, independent of cwd."""
import argparse
from pathlib import Path
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate
from flask import request
from shift_happens.config import Settings
from shift_happens.exports import evidence_csv, figure_svg
from shift_happens.model import finite_number
from shift_happens.views import inspector, legend, track_figure
from shift_happens.workspace import active_analyses, import_files, initial_workspace, options, source_ids_for_selection

ROOT = Path(__file__).resolve().parent


def bounded(value, minimum, maximum, fallback):
    return min(maximum, max(minimum, int(value))) if finite_number(value) else fallback


def create_app(settings=None):
    settings = settings or Settings.from_env()
    app = Dash(__name__, assets_folder=str(ROOT / "assets"), title="Shift Happens · See where selection changes.", update_title=None)
    # Includes base64 transport and Store payload overhead; domain limits are lower.
    app.server.config["MAX_CONTENT_LENGTH"] = settings.max_request_bytes

    @app.server.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.server.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.path in ("/_dash-update-component", "/_dash-layout"):
            response.headers["Cache-Control"] = "no-store"
        return response
    def layout():
        workspace = initial_workspace()
        return html.Div([
            dcc.Store(id="workspace", storage_type="memory", data=workspace), dcc.Download(id="download"),
            html.Header([html.Div("⇄", className="brand-mark"), html.Div([html.H1(["Shift Happens", html.Span("PYTHON / DASH", className="version")]), html.P("See where selection changes.")]), html.Span("● Hosted server processing" if settings.hosted else "● Runs on your computer", className="privacy")], className="masthead"),
            html.Main([
                html.Section([html.Div([html.P("EVOLUTION, IN CONTEXT", className="eyebrow"), html.H2(["Different methods.", html.Br(), "Distinct evidence."]), html.P("Explore conservation and diversification while keeping each statistical question in view.")]),
                              html.Div([dcc.Upload(id="upload", children=html.Button("＋ Import HyPhy / Datamonkey JSON", className="primary"), multiple=True, accept=".json,application/json"), html.P(f"FEL 2.00 / 2.6 · MEME 2.00 / 2.1.1 / 4.1 · {settings.max_file_mib} MiB/file"), html.P("Uploads are sent to this hosted server for processing. Use local mode for data that must stay on your computer." if settings.hosted else "Files are processed by your local Python server."), html.Button("Open synthetic example →", id="demo", className="text-button"), html.Details([html.Summary("Importing Datamonkey results"), html.P("On a completed FEL or MEME results page, download the full results JSON and upload it here. CSV tables, job-status JSON, and saved webpages are not complete analysis results."), html.P("MEME 4.1 is validated for exactly two rate classes, with multiple hits and imputed states disabled."), html.P("Only the method versions and configurations listed above are validated. Newer formats need a representative fixture; do not change a file’s version field.")])], className="import-box")], className="intro"),
                html.Div(id="message", role="status", **{"aria-live": "polite"}),
                html.Div([
                    html.Aside([html.H2("Analyses"), html.P("Compatible Datamonkey FEL and MEME exports receive a metadata-matched comparison view; individual method views remain available.", className="hint"), dcc.RadioItems(id="active", options=options(workspace, settings), value="demo", className="analysis-list"), html.Button("Remove selected file(s)", id="remove", className="remove-button"), html.P(f"Reloading clears this browser’s workspace. Up to 20 files / {settings.max_workspace_mib} MiB total / {settings.max_codons:,} codons per analysis.", className="hint")], className="panel files"),
                    html.Section([
                        html.Div([html.Div([html.P("ALONG THE ALIGNMENT", className="eyebrow"), html.H2("Selection evidence")]), html.Div([html.Button("Evidence CSV", id="csv"), html.Button("Figure SVG", id="svg"), html.Button("Original JSON", id="original")], className="export-buttons")], className="section-heading"),
                        html.Div(id="context", className="context"),
                        html.Div([html.Label(["Exploratory p ≤ ", dcc.Dropdown(id="threshold", options=[{"label": str(p), "value": p} for p in (.01, .05, .1)], value=.05, clearable=False, searchable=False)]),
                                  html.Label(["Start codon", dcc.Input(id="start", type="number", value=1, min=1, step=1, debounce=True)]),
                                  html.Label(["Window", dcc.Dropdown(id="window", options=[36, 72, 144], value=72, clearable=False, searchable=False)]),
                                  html.Label(["Inspect codon", dcc.Input(id="codon", type="number", value=1, min=1, step=1, debounce=True)])], className="controls"),
                        html.Div([html.Button("← Previous", id="previous"), html.Span(id="range"), html.Button("Next →", id="next")], className="navigation"),
                        dcc.Graph(id="tracks", config={"displayModeBar": False}, responsive=True, style={"height": "380px", "width": "100%"}, clear_on_unhover=True),
                        html.Div(legend(), className="legend"), html.P("Click a codon or use Inspect codon to compare evidence. The CSV contains all codons; the SVG contains the selected window. Thresholds are unadjusted and exploratory.", className="hint"),
                    ], className="panel explorer"),
                ], className="workspace-grid"),
                html.Section([html.Div([html.Div([html.P("THE EVIDENCE BEHIND THE MARK", className="eyebrow"), html.H2(id="inspector-title")]), html.Span("Alignment coordinates · 1-based")], className="section-heading"), html.Div(id="inspection", className="inspection")], className="panel inspector"),
                html.Section([html.H2("Read the evidence, preserve the question."), html.Div([
                    html.P([html.Strong("FEL "), "tests pervasive site selection across the tested branches. Purifying and diversifying evidence receive equal visual weight."]),
                    html.P([html.Strong("MEME "), "tests episodic diversification at a site. It does not establish purifying selection or locate a selected branch by itself."]),
                    html.P([html.Strong("Contrast-FEL "), "compares branch groups. A difference does not establish positive selection or pinpoint when a shift occurred. Synthetic illustration only."]),
                ], className="reading-grid"), html.P("Nonsignificance is not proof of neutrality. These are inferred selective pressures, not measured fitness or a new statistical test. Never combine significant sites and branches from different methods to infer selected branch–site intersections.", className="footnote")], className="reading"),
            ]), html.Footer("Shift Happens · Python + Dash · " + ("Hosted processing" if settings.hosted else "Local processing") + " · No application telemetry"),
        ])
    app.layout = layout

    @app.callback(Output("workspace", "data"), Output("active", "options"), Output("active", "value"), Output("message", "children"),
                  Input("upload", "contents"), Input("demo", "n_clicks"), Input("remove", "n_clicks"),
                  State("upload", "filename"), State("workspace", "data"), State("active", "value"), prevent_initial_call=True)
    def manage_workspace(contents, _demo, _remove, filenames, workspace, selected):
        notice = ""
        if ctx.triggered_id == "upload":
            workspace, imported, notice = import_files(workspace, contents, filenames, settings)
            selected = imported or selected
        elif ctx.triggered_id == "demo":
            workspace = {**workspace, "demo": True}
            selected = "demo"
            notice = "SYNTHETIC illustration opened. Native files are retained."
        elif ctx.triggered_id == "remove":
            remove_ids = source_ids_for_selection(workspace, selected, settings)
            workspace = {"demo": workspace["demo"] and selected != "demo", "files": [f for f in workspace["files"] if f["id"] not in remove_ids]}
            choices = options(workspace, settings)
            selected = choices[0]["value"] if choices else None
            notice = ("Synthetic illustration closed." if "demo" in remove_ids else
                      f"Removed {len(remove_ids)} selected source file(s).")
        return workspace, options(workspace, settings), selected, notice

    @app.callback(Output("tracks", "figure"), Output("inspection", "children"), Output("context", "children"), Output("range", "children"),
                  Output("start", "value"), Output("codon", "value"), Output("start", "max"), Output("codon", "max"), Output("inspector-title", "children"),
                  Output("original", "disabled"), Output("csv", "disabled"), Output("svg", "disabled"), Output("previous", "disabled"), Output("next", "disabled"),
                  Input("workspace", "data"), Input("active", "value"), Input("threshold", "value"), Input("window", "value"), Input("start", "value"), Input("codon", "value"),
                  Input("tracks", "clickData"), Input("previous", "n_clicks"), Input("next", "n_clicks"))
    def render(workspace, selected, threshold, window, start, codon, click, _previous, _next):
        analyses = active_analyses(workspace, selected, settings)
        length = analyses[0].length if analyses else 1
        window = bounded(window, 1, 144, 72)
        start, codon = bounded(start, 1, length, 1), bounded(codon, 1, length, 1)
        if ctx.triggered_id in ("active", "workspace"):
            start = codon = 1
        elif ctx.triggered_id in ("previous", "next"):
            start = bounded(start + (-window if ctx.triggered_id == "previous" else window), 1, length, 1)
            codon = start
        elif ctx.triggered_id == "tracks" and click and click.get("points"):
            data = click["points"][0].get("customdata", [])
            if data:
                codon = bounded(data[0], 1, length, codon)
        elif ctx.triggered_id == "start":
            codon = start
        if codon < start or codon >= start + window:
            start = codon
        end = min(length, start + window - 1)
        threshold = threshold if finite_number(threshold) and 0 < threshold <= 1 else .05
        notice = ("SYNTHETIC EXAMPLE · Hand-authored illustration, not biological results. These tracks share synthetic coordinates." if selected == "demo" and analyses else
                  f"{analyses[0].filename} + {analyses[1].filename} · Metadata-matched comparison: source filenames, sequence/site counts, coverage, taxa, and leaf scope agree. Alignment content is not embedded or verified." if len(analyses) > 1 else
                  f"{analyses[0].filename} · Independent native analysis. Alignment identity is unverified; cross-file linking is disabled." if analyses else
                  "Import an analysis or open the synthetic example to begin.")
        return (track_figure(analyses, threshold, start, end, codon), inspector(analyses, codon, threshold), notice,
                f"Codons {start}–{end} of {length}" if analyses else "No analysis", start, codon, length, length,
                f"Codon {codon}" if analyses else "Choose an analysis", not analyses or analyses[0].synthetic or len(analyses) != 1, not analyses, not analyses, not analyses or start == 1, not analyses or end == length)

    @app.callback(Output("download", "data"), Input("csv", "n_clicks"), Input("svg", "n_clicks"), Input("original", "n_clicks"),
                  State("workspace", "data"), State("active", "value"), State("threshold", "value"), State("start", "value"), State("window", "value"), prevent_initial_call=True)
    def download(_csv, _svg, _original, workspace, selected, threshold, start, window):
        analyses = active_analyses(workspace, selected, settings)
        if not analyses:
            raise PreventUpdate
        name = "shift-happens-SYNTHETIC" if analyses[0].synthetic else "shift-happens-evidence"
        if ctx.triggered_id == "csv":
            return dict(content=evidence_csv(analyses, threshold), filename=name + ".csv", type="text/csv;charset=utf-8")
        if ctx.triggered_id == "svg":
            start = bounded(start, 1, analyses[0].length, 1)
            end = min(analyses[0].length, start + bounded(window, 1, 144, 72) - 1)
            return dict(content=figure_svg(analyses, threshold, start, end), filename=name + ".svg", type="image/svg+xml")
        if analyses[0].original_text is not None:
            return dict(content=analyses[0].original_text, filename=analyses[0].filename, type="application/json")
        return no_update

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shift Happens local Dash viewer")
    parser.add_argument("--port", type=int, default=8050)
    args = parser.parse_args()
    create_app().run(host="127.0.0.1", port=args.port, debug=False)
