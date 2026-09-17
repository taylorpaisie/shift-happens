# Shift Happens

**See where selection changes.**

A local browser tool for exploring inferred evolutionary selective pressures. This first working increment imports a deliberately narrow, fixture-validated subset of native HyPhy JSON, keeps method-specific evidence separate, and includes an explicitly synthetic linked-track example. No backend, build step, runtime dependencies, telemetry, or external assets.

## Run locally

From this directory, with Python 3 installed:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open **http://127.0.0.1:8000**. Use a modern Chromium, Firefox, or Safari browser with JavaScript modules enabled. Only Chromium has been smoke-tested in this increment. Serve over localhost; opening `index.html` with `file://` is not supported.

Uploaded files are read into browser memory and are never posted to the local server or a remote service. Reloading clears the workspace. Export original JSON before discarding your own source if needed. The local server only serves static files; it does not run analyses.

## Supported imports

| Method | `analysis.version` verified | Scope | Fixture |
| --- | --- | --- | --- |
| FEL | `2.00` | Pervasive site selection in the reported test branches | Official mammalian CD2 output, 187 codons |
| MEME | `2.1.1` | Episodic site diversification in the reported test branches | Official mammalian CD2 output, 187 codons |
| Contrast-FEL | **No native import yet** | Synthetic branch-group difference illustration only | No adapter validation completed |

These are **analysis method versions, not HyPhy executable versions**. The fixtures do not report a verified executable version. Newer or different method versions are rejected even if they look similar. Supporting an entire HyPhy release family is not claimed.

Only single-partition outputs with documented `MLE.headers`, `MLE.content`, `data partitions.0.coverage`, input tree, counts, and tested-branch labels are accepted. The limit is 25 MiB per file and 100,000 alignment codons; large-file responsiveness is not benchmarked. No native FUBAR, aBSREL, RELAX, GARD, or normalized project-JSON importer is included. There was no starter project or legacy importer to preserve.

See [format provenance and field mapping](docs/imports.md) for pinned official references, header mapping, coordinate conventions, fixture hashes, expected values, and rejection rules.

## Example workflow

1. Open the app. The amber banner and source names label the built-in example as **SYNTHETIC**. It is hand-authored illustrative evidence, not a HyPhy analysis or a biological simulation.
2. Click a codon to compare the synthetic FEL, MEME, and Contrast-FEL evidence. Arrow keys move along codons; Home/End select the first/last alignment codon. Choose a window or start coordinate to navigate.
3. Import `fixtures/CD2.FEL.json` and `fixtures/CD2.MEME.json` together. Both remain in the analysis list; selecting either shows its native track and source-specific inspector. FEL codon 11 illustrates supported purifying selection at p ≤ 0.05; MEME codon 43 illustrates episodic diversification.
4. Change the explicitly **unadjusted exploratory threshold**. Raw p-values remain unchanged. Inspect original row values, column descriptions, branch scope, partition mapping, input metadata, and available fits.
5. Export **Evidence CSV** for all alignment codons of the active analysis or synthetic group; export **Figure SVG** for its chosen coordinate window, with legend, settings, and scientific interpretation notes. Source JSON can be downloaded as the original decoded text; the app does not rewrite its fields.

Importing `fixtures/partitioned.FEL.json` demonstrates an actionable rejection of recombination-partitioned data. All fixtures are nonpathogenic mammalian CD2 or explicitly simulated data.

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

## Tests

With Node.js 20 or later, no package installation is needed:

```sh
npm test
# or
node tests/run.mjs
```

The same module suite runs at **http://127.0.0.1:8000/tests/** without Node. It checks pinned fixture hashes and known estimates, header reordering, sparse/reordered coordinates, invalid/missing values, unsupported inputs, partition rejection, branch scope, scientific classification, compatibility, and export escaping.

Real browser smoke tests use installed Chrome/Chromium or Edge and Python's development-only WebSocket client:

```sh
python -m pip install websocket-client
python scripts/browser_smoke.py
# Optional: python scripts/browser_smoke.py --browser /path/to/chrome
```

The script starts a temporary localhost server and an isolated headless browser, runs the module suite, then checks actual uploads, native isolation, synchronized synthetic selection, keyboard navigation, thresholds, pagination, malicious metadata rendering, partition rejection, removal, CSV/SVG downloads, and mobile layout. Screenshots and exports go into ignored `.artifacts/`. It does not alter the normal browser profile.

GitHub Actions runs the Node suite and Chromium smoke script. See [validation record](docs/validation.md) for what was executed locally and what remains unverified.

## Structure

- `src/hyphy.js`: size limits and JSON decoding.
- `src/validation.js`: native schema validation, normalization, and provenance retention.
- `src/model.js`: evidence classification and conservative coordinate compatibility.
- `src/demo.js`: clearly separated, hand-authored synthetic data.
- `src/app.js`: browser state, file management, safe DOM rendering, linked demo controls.
- `src/export.js`: method-specific evidence CSV and standalone SVG.
- `tests/`, `fixtures/`: shared Node/browser regression suite and pinned native outputs.
- `scripts/browser_smoke.py`: real-browser integration checks.

See [ROADMAP.md](ROADMAP.md) for alignment provenance, newer formats, Contrast-FEL, FUBAR, aBSREL, RELAX, and recombination-aware views. No deployment or license selection is part of this increment.
