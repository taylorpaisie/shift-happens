# Validation record

## Datamonkey import increment

- **79 Python tests passed**, including pinned MEME 2.00 fixture values and coordinates, reordered headers, Datamonkey publication metadata preservation, wrong-download diagnostics, unsupported versions, and independent native analyses.
- **Hosted-mode Chrome smoke passed** with actual uploads of official MEME 2.00 output and a documented Datamonkey-contract transformation, codon inspection, safe metadata rendering, and CSV/SVG/original JSON downloads. Existing navigation, isolation, recovery, memory reset, and mobile layout checks also passed.
- Datamonkey contract transformations follow the pinned official server source; they are not live job downloads. No Datamonkey job or Render deployment was performed. See [provenance and supported versions](datamonkey.md).

## Python/Dash and Render preparation

- **64 Python tests passed** on Python 3.11.9 / Dash 3.4.0 / Plotly 6.9.0: fixture integrity, known estimates, malformed fields and missing values, scientific interpretation, isolated workspaces, exports, hosted limits, privacy wording, health/WSGI routes, transport limits, and Blueprint/Gunicorn configuration contracts.
- **Dash browser smoke passed in Chrome 153:** actual Plotly click events, linked synthetic inspection, multiple native imports, threshold changes, numeric codon navigation, analysis switching, pagination, rejection/recovery, removal, CSV/SVG/original downloads, safe metadata, reload reset, and responsive layout. A chart-container overlap caught by screenshot review was fixed and given an explicit regression assertion.
- Dependency wheels for Dash, Plotly, and Gunicorn were successfully resolved/downloaded with the Render requirements file.
- `render.yaml` passed JSON Schema validation against Render's published `https://render.com/schema/render.yaml.json`. The Dash browser smoke also passed with `SHIFT_HAPPENS_HOSTED=true` on a temporary localhost server; this verifies hosted-mode application behavior, not a live Render deployment.
- Gunicorn configuration and the WSGI application were checked through Python tests. **A live Gunicorn process has not been run locally:** this Windows host cannot run Gunicorn, and WSL access was denied. The real production health/callback check is included in Linux CI.
- No Render service has been created or deployed, and remote CI is not claimed to have passed. Render concurrency, maximum-size upload performance, and end-to-end live hosting remain unverified.

## Original static browser increment

Local verification for the first working increment (2026-09-17):

- **26 shared JavaScript regression tests passed in installed Chrome 153 on Windows.** This is the same ES-module suite used by `tests/run.mjs`, including pinned fixture SHA-256 checks, independently read expected numerical values, reordering, coordinate mapping, missing data, incompatible inputs, scientific interpretation and exports.
- **Real-browser smoke tests passed:** multi-file uploads, independent native analyses, synchronized synthetic tracks, per-codon inspection, keyboard navigation, exploratory thresholds, pagination, malicious uploaded metadata, partition rejection without removing working files, file removal, CSV download and parseable SVG download.
- **Desktop (1440px) and mobile (390px) layouts checked.** Browser testing caught and fixed a mobile grid overflow. Desktop and mobile screenshots were generated and visually inspected. Source changes also reset horizontal track scroll when switching an analysis or coordinate window.
- **No uncaught application JavaScript exceptions** in the passing smoke run.
- Fixture files were downloaded from the pinned official `veg/hyphy-vision` commit documented in [imports.md](imports.md). No biological analyses were rerun; tests validate extraction and interpretation of existing outputs.

The host has no Node on PATH. A portable official Node 22.14.0 runtime was downloaded to a temporary directory, but Windows denied execution. Consequently, the **Node command itself was not verified locally**. Its shared suite was executed in the browser instead. GitHub Actions is configured to run both Node and Chrome checks, but remote CI has not been run or claimed as passing.

Firefox, Safari, screen-reader behavior, very large-file responsiveness, newest HyPhy formats, native cross-file alignment identity, Contrast-FEL import, and recombination-aware interpretation remain unverified or intentionally unsupported. No deployment was performed.
