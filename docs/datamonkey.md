# Importing Datamonkey results

In the Dash app, choose **Import HyPhy / Datamonkey JSON** and select the **full results JSON** downloaded from a completed Datamonkey FEL or MEME analysis. Multiple files can be selected. Do not use a CSV table export, a job-status response, a results-page URL, or the browser's Save Page As command.

| Method | Verified method versions | Scope |
| --- | --- | --- |
| FEL | `2.00`, `2.6` | Pervasive site evidence |
| MEME | `2.00`, `2.1.1`, `4.1` | Episodic site evidence |

These are `analysis.version` values, not Datamonkey website releases or HyPhy executable versions. **Current Datamonkey jobs may use newer method versions.** Those remain rejected until representative nonpathogenic/synthetic outputs have been validated. Do not edit a version string to bypass validation. FUBAR, aBSREL, RELAX and other Datamonkey methods are not supported yet. Contrast-FEL remains an explicitly synthetic demonstration.

MEME 4.1 is accepted only when `analysis.settings` reports `rates: 2`, `multihit: "None"`, and `Imputed States: 0`. Version 4.1 outputs with additional rate classes, multiple hits, or imputed states remain rejected because those configurations have not been validated against the current two-component evidence model.

## What the download contains

Datamonkey's [official MEME instructions](https://help.datamonkey.org/methods/meme) describe downloading detailed JSON results. Its [general help](https://www.datamonkey.org/help) points to the HyPhy JSON field documentation.

The verified server contract is pinned to `veg/datamonkey-js` commit **ee78cd35743179c5686dde6090918558c3c9f2b7**:

- [Result handler](https://github.com/veg/datamonkey-js/blob/ee78cd35743179c5686dde6090918558c3c9f2b7/app/routes/analysis.js): reads the native results JSON, adds a top-level `PMID`, and returns the resulting object. It does not wrap the output in a guessed `results` array or dictionary.
- [Route declarations](https://github.com/veg/datamonkey-js/blob/ee78cd35743179c5686dde6090918558c3c9f2b7/config/routes.js): FEL/MEME results routes use the shared result handler. Job-info routes are different responses and contain no site-level evidence.
- [FEL model](https://github.com/veg/datamonkey-js/blob/ee78cd35743179c5686dde6090918558c3c9f2b7/app/models/fel.js) and [MEME model](https://github.com/veg/datamonkey-js/blob/ee78cd35743179c5686dde6090918558c3c9f2b7/app/models/meme.js): supply publication metadata. It is retained **as supplied**, not treated as an independently verified citation or used to identify the analysis method.

Consequently, a separate statistical parser is unnecessary for this download contract. The same header-driven schema validator handles full results from either source. The UI calls the format **Native HyPhy / Datamonkey results JSON**; this describes compatibility, not proof that a particular file came from Datamonkey. A filename or `PMID` cannot establish origin or alignment identity.

Original text and all original fields are retained. Publication metadata appears in the inspector, evidence CSV and SVG metadata; the Original JSON download preserves the original decoded text. A complete, exact metadata match can create a two-track FEL + MEME comparison, but it is not labeled as verified alignment identity. Single-partition, missing-data, correction, and hosted/local size-limit rules are unchanged.

CSV tables are not sufficient substitutes: the importer needs version, tested-branch scope, native headers, and coordinate mapping to interpret evidence safely. Archives and live result URLs are not fetched or unpacked by this increment.

## Fixture evidence

The existing official CD2 fixtures cover FEL 2.00 and MEME 2.1.1. Datamonkey contract tests add exactly the `PMID` field shown in the pinned server source to these fixtures and compare all normalized estimates with the unmodified originals. These are labeled **contract transformations**, not live Datamonkey downloads. No analysis job was submitted to Datamonkey.

FEL 2.6 support is verified against the representative completed Datamonkey export supplied for this project:

- Local fixture: `fixtures/FEL-2.6.Datamonkey.json` (content preserved; final newline normalized for the repository).
- Repository fixture SHA-256: `87ca1554628aef7d94f3f06afc273c79bbcc1ff5ba47832afcfca17882730cd4`.
- 10 sequences, 42 codons, one partition; zero-based coverage 0–41 maps to displayed codons 1–42.
- The six header-driven MLE columns match the validated FEL contract. Codon 9 has α = `18.00931351361862`, β = `0.00006425039486038318`, and p = `0.0095325979984765`.
- FEL 2.6 substitution mapping is retained in the original result object and original-JSON export. It does not alter the existing site-evidence interpretation.

MEME 4.1 support is verified against the representative completed Datamonkey export supplied for this project:

- Local fixture: `fixtures/MEME-4.1.Datamonkey.json` (content preserved; final newline normalized for the repository).
- Repository fixture SHA-256: `f5958329a27eab0af03ee7f2591349ada5b5f6ecdf5addac87b91724560aae51`.
- 10 sequences, 42 codons, one partition, and exactly two ω-rate classes.
- The renamed `&alpha;`, `&beta;<sup>1</sup>`, and `p<sup>1</sup>` headers are mapped by name to the existing synonymous and negative/neutral component fields. The five additional native columns remain preserved.
- Substitution mapping and export metadata remain preserved. All 42 native `Total branch length` values in this particular result are zero, so the viewer correctly marks its sites as insufficient information rather than inventing evidence.

MEME 2.00 support is verified against the official nonpathogenic lysin tutorial output:

- Source: [lysin.fna.MEME.json](https://github.com/veg/hyphy-site/blob/f2786c52efb57bdb79bf3dfe05b0e55bfec831f5/docs/tutorials/files/tutorial_data/lysin.fna.MEME.json), pinned commit **f2786c52efb57bdb79bf3dfe05b0e55bfec831f5**.
- Local fixture: `fixtures/lysin.MEME.json` (unmodified).
- SHA-256: `a17acd9e8dbe8f33cd1c3a7f3d291c09ad1db5f639292338e826a30a19d130e8`.
- 25 sequences, 134 codons, one partition; zero-based coverage 0–133 maps to displayed codons 1–134.
- Independently read anchors: codon 6 β+ = `23.81442994266141`, mixture weight = `0.2097491392006071`, p = `0.005166111870549717`; codon 134 α = `380.97244794148`.
- Tests also reverse headers and rows to verify the adapter does not rely on fixed column positions.

No claim is made to support all current Datamonkey versions, API envelopes, export formats, or methods. The preserved static JavaScript prototype keeps its original narrower version support; this increment targets the Python/Dash app.
