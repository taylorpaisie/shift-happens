# Validation record

Local verification for the first working increment (2026-09-17):

- **26 shared JavaScript regression tests passed in installed Chrome 153 on Windows.** This is the same ES-module suite used by `tests/run.mjs`, including pinned fixture SHA-256 checks, independently read expected numerical values, reordering, coordinate mapping, missing data, incompatible inputs, scientific interpretation and exports.
- **Real-browser smoke tests passed:** multi-file uploads, independent native analyses, synchronized synthetic tracks, per-codon inspection, keyboard navigation, exploratory thresholds, pagination, malicious uploaded metadata, partition rejection without removing working files, file removal, CSV download and parseable SVG download.
- **Desktop (1440px) and mobile (390px) layouts checked.** Browser testing caught and fixed a mobile grid overflow. Desktop and mobile screenshots were generated and visually inspected. Source changes also reset horizontal track scroll when switching an analysis or coordinate window.
- **No uncaught application JavaScript exceptions** in the passing smoke run.
- Fixture files were downloaded from the pinned official `veg/hyphy-vision` commit documented in [imports.md](imports.md). No biological analyses were rerun; tests validate extraction and interpretation of existing outputs.

The host has no Node on PATH. A portable official Node 22.14.0 runtime was downloaded to a temporary directory, but Windows denied execution. Consequently, the **Node command itself was not verified locally**. Its shared suite was executed in the browser instead. GitHub Actions is configured to run both Node and Chrome checks, but remote CI has not been run or claimed as passing.

Firefox, Safari, screen-reader behavior, very large-file responsiveness, newest HyPhy formats, native cross-file alignment identity, Contrast-FEL import, and recombination-aware interpretation remain unverified or intentionally unsupported. No deployment was performed.
