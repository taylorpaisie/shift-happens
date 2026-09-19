# Shift Happens

**See where selection changes.**

A **Python + Dash** tool for exploring inferred evolutionary selective pressures. It imports a deliberately narrow, fixture-validated subset of native HyPhy JSON, keeps method-specific evidence separate, and includes an explicitly synthetic linked-track example. Plotly renders linked codon tracks; Python handles validation, inspection, and exports. No database, Node build step, or external data service is required.

## Run locally

From this directory, with Python 3.11 installed (a virtual environment is recommended):

```sh
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:8050**. `python app.py --port 8051` selects another port. Assets are located relative to `app.py`, so starting the script from another working directory still serves the app. Only Chromium has been smoke-tested. **Do not use `python -m http.server` for the Dash app**; that serves the earlier static version instead.

In local mode, uploads are sent to the Python server bound to `127.0.0.1` and processed on your computer. A browser-memory `dcc.Store` holds that browser's source files; callbacks are stateless and do not share uploaded datasets through server globals. The app does not write uploads to disk, use a database, or send application telemetry. Reloading clears the workspace. It does not run HyPhy analyses.

## Render hosting

The repo includes [render.yaml](render.yaml), a Gunicorn WSGI entry point, health checks, and hosted-mode limits. Follow [docs/render.md](docs/render.md) for Blueprint and manual setup. This configuration has **not** been deployed.

Hosted mode explicitly tells users that uploaded data goes to the hosting server. The Blueprint uses a Free preview instance with manual deploys, 5 MiB/file, 10 MiB/workspace, and 10,000 codons/analysis. No account system or persistent storage is included. Local mode remains available for datasets that must stay on a user's own computer.

## Supported imports

| Method | `analysis.version` verified | Scope | Fixture |
| --- | --- | --- | --- |
| FEL | `2.00`, `2.6` | Pervasive site selection in the reported test branches | Official mammalian CD2 output, 187 codons; representative Datamonkey 2.6 output, 42 codons |
| MEME | `2.00`, `2.1.1` | Episodic site diversification in the reported test branches | Official lysin and mammalian CD2 outputs |
| Contrast-FEL | **No native import yet** | Synthetic branch-group difference illustration only | No adapter validation completed |

These are **analysis method versions, not HyPhy executable versions**. The fixtures do not report a verified executable version. Newer or different method versions are rejected even if they look similar. Supporting an entire HyPhy release family is not claimed.

Only single-partition outputs with documented `MLE.headers`, `MLE.content`, `data partitions.0.coverage`, input tree, counts, and tested-branch labels are accepted. Local limits are 25 MiB/file, 50 MiB/workspace, 20 files, and 100,000 alignment codons; hosted limits are smaller. Large-file responsiveness and concurrency are not benchmarked. No native FUBAR, aBSREL, RELAX, GARD, or normalized project-JSON importer is included.

See [format provenance and field mapping](docs/imports.md) for pinned official references, header mapping, coordinate conventions, fixture hashes, expected values, and rejection rules.

**Datamonkey:** use the same import button with the full results JSON downloaded from a completed FEL/MEME job. Datamonkey uses the native HyPhy results schema; supplied publication metadata is preserved in inspection and exports. CSV tables, job-status JSON, saved webpages, and live URLs are not full analysis results. Current Datamonkey jobs can use newer method versions than those validated above. See [Datamonkey import instructions and verification](docs/datamonkey.md).

## Example workflow

1. Open the app. The amber banner and source names label the built-in example as **SYNTHETIC**. It is hand-authored illustrative evidence, not a HyPhy analysis or a biological simulation.
2. Click a codon to compare the synthetic FEL, MEME, and Contrast-FEL evidence, or enter a number in **Inspect codon** and press Enter. Choose a window, start coordinate, or Previous/Next to navigate. Numeric controls provide a keyboard alternative to chart clicks.
3. Import `fixtures/CD2.FEL.json` and `fixtures/CD2.MEME.json` together. Both remain in the analysis list; selecting either shows its native track and source-specific inspector. FEL codon 11 illustrates supported purifying selection at p ≤ 0.05; MEME codon 43 illustrates episodic diversification.
4. Change the explicitly **unadjusted exploratory threshold**. Raw p-values remain unchanged. Inspect original row values, column descriptions, branch scope, partition mapping, input metadata, and available fits.
5. Export **Evidence CSV** for all alignment codons of the active analysis or synthetic group; export **Figure SVG** for its chosen coordinate window, with legend, settings, and scientific interpretation notes. Source JSON can be downloaded as the original decoded text; the app does not rewrite its fields.

Importing `fixtures/partitioned.FEL.json` demonstrates an actionable rejection of recombination-partitioned data. All fixtures are nonpathogenic mammalian CD2, abalone lysin, or explicitly simulated data.

## Scientific boundaries

- FEL's purifying and diversifying site evidence is pervasive over the test branches. MEME evidence is episodic diversification. They are not interchangeable and are never combined into a confidence score.
- Nonsignificance is not proof of neutrality. Uncovered sites are marked untested/outside coverage; missing or invalid numerical fields, zero inferred branch length, or zero-rate rows are marked insufficient information. A zero-rate row does not prove that HyPhy skipped a test.
- The validated native schemas report unadjusted site p-values. The viewer adds no multiple-testing correction. Recognized correction-bearing header metadata outside those schemas is rejected for adapter review, never relabeled as raw p-values. All original metadata remains in the source.
- A Contrast-FEL group difference does not establish positive selection or locate a change in time. The synthetic illustration is not an implemented Contrast-FEL statistical test.
- No selected branch–site intersections are inferred by joining evidence from different methods. MEME's native approximate branch-count column, if present, remains in the original-row inspector without being promoted into branch-specific calls.
- No dN/dS ratios are computed or plotted. Individual rates are retained, including zero synonymous rates. Unreported uncertainty or convergence information is not inferred from model fit statistics.
- This is visualization of inferred pressures, not measured fitness, a fitness landscape, or a new statistical test.

## Alignment compatibility and known limitations

**Native cross-file linking is disabled in this increment.** The supported JSON outputs supply alignment filenames, counts, trees, and coverage, but not an independently verifiable alignment-content identity. Matching lengths, tree labels, or filenames cannot establish that two analyses used the same alignment, taxon ordering, masking, or coordinate transform. Even the two CD2 fixtures are not assumed identical. Native analyses can be loaded together and inspected independently; only built-in synthetic tracks are linked by construction.

This is a deliberate safety boundary and a remaining Priority 2 limitation. A future analysis-time provenance adapter must bind result files to alignment-content hashes and explicit coordinate maps, validate those hashes against supplied content, and define its provenance trust boundary before enabling native linking. A manually supplied shared label or attaching an arbitrary FASTA after analysis will not suffice.

Recombination-partitioned files are rejected rather than flattened. Partition data in accepted single-partition files is preserved. Contrast-FEL native import is deferred: an upstream example exists, but its version, provenance, group contrasts, and native correction semantics have not been validated here; absence of a fixture is **not** claimed as the blocker. The next releases should broaden the validated FEL/MEME version coverage before adding further methods.

SVG figures use system fonts and do not embed fonts. Browser state is not persisted; there is no project save/restore yet. The app does not recompute likelihoods, validate a tree against an alignment, assess convergence, or rerun HyPhy. Accessibility was checked through keyboard behavior, text labels, symbols, and narrow-screen layout; no formal screen-reader audit was performed.

## Python and Dash tests

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_python.py tests/test_hosting.py tests/test_datamonkey.py
python scripts/dash_smoke.py
```

The Python suite verifies the same pinned official fixtures and expected values, plus upload isolation, deployment settings, hosted privacy wording, health checks, and WSGI routes. The Chrome/Chromium smoke test exercises actual Plotly clicks, threshold controls, numeric codon navigation, switching files, invalid-file recovery, mobile layout, and CSV/SVG/original downloads. It records screenshots under ignored `.artifacts/`. Supply `--browser /path/to/chrome` if auto-detection fails.

Linux CI additionally starts the real production server with `python scripts/gunicorn_smoke.py`. Gunicorn cannot run on Windows; that production check has not been verified locally here. GitHub Actions now includes both Python/Dash and legacy browser checks. See [validation record](docs/validation.md).

## Preserved static prototype

The earlier JavaScript app (`index.html`, `src/`, `style.css`) is retained and can still be served with `python -m http.server 8000 --bind 127.0.0.1`. This is separate from the Dash server on port 8050 and has browser-only file processing. Its regression tests remain available:

With Node.js 20 or later, no package installation is needed:

```sh
npm test
# or
node tests/run.mjs
```

The same JavaScript module suite runs at **http://127.0.0.1:8000/tests/** without Node. It checks pinned fixture hashes and known estimates, header reordering, sparse/reordered coordinates, invalid/missing values, unsupported inputs, partition rejection, branch scope, scientific classification, compatibility, and export escaping.

Real browser smoke tests use installed Chrome/Chromium or Edge and Python's development-only WebSocket client:

```sh
python -m pip install websocket-client
python scripts/browser_smoke.py
# Optional: python scripts/browser_smoke.py --browser /path/to/chrome
```

The script starts a temporary localhost server and an isolated headless browser, runs the module suite, then checks actual uploads, native isolation, synchronized synthetic selection, keyboard navigation, thresholds, pagination, malicious metadata rendering, partition rejection, removal, CSV/SVG downloads, and mobile layout. Screenshots and exports go into ignored `.artifacts/`. It does not alter the normal browser profile.

GitHub Actions runs the Node suite and Chromium smoke script. See [validation record](docs/validation.md) for what was executed locally and what remains unverified.

## Structure

- `app.py`: Dash layout and callbacks; local entry point on port 8050.
- `shift_happens/imports.py`, `validation.py`: UTF-8 decoding, schema validation, normalization.
- `shift_happens/model.py`, `demo.py`: method-specific evidence and isolated synthetic data.
- `shift_happens/views.py`, `exports.py`: Plotly/Dash rendering and portable CSV/SVG output.
- `shift_happens/workspace.py`, `config.py`: per-browser workspace operations and instance limits.
- `wsgi.py`, `gunicorn.conf.py`, `render.yaml`: production entry point and Render Blueprint.
- `assets/dash.css`: Dash interface styles.

Preserved static app:

- `src/hyphy.js`: size limits and JSON decoding.
- `src/validation.js`: native schema validation, normalization, and provenance retention.
- `src/model.js`: evidence classification and conservative coordinate compatibility.
- `src/demo.js`: clearly separated, hand-authored synthetic data.
- `src/app.js`: browser state, file management, safe DOM rendering, linked demo controls.
- `src/export.js`: method-specific evidence CSV and standalone SVG.
- `tests/`, `fixtures/`: shared Node/browser regression suite and pinned native outputs.
- `scripts/browser_smoke.py`: real-browser integration checks.

See [ROADMAP.md](ROADMAP.md) for alignment provenance, newer formats, Contrast-FEL, FUBAR, aBSREL, RELAX, and recombination-aware views. No deployment or license selection is part of this increment.
