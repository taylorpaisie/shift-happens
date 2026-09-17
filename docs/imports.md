# Native import provenance

## Authoritative references consulted

- [Official HyPhy JSON field documentation](https://www.hyphy.org/resources/json-fields/): shared metadata, partition coverage, tested branches, fits, and `MLE.headers` / `MLE.content` association.
- [HyPhy source at commit 646e16eb4243e5e5588ac340483fcb987552751d: FEL](https://github.com/veg/hyphy/blob/646e16eb4243e5e5588ac340483fcb987552751d/res/TemplateBatchFiles/SelectionAnalyses/FEL.bf) and [MEME](https://github.com/veg/hyphy/blob/646e16eb4243e5e5588ac340483fcb987552751d/res/TemplateBatchFiles/SelectionAnalyses/MEME.bf): method-native semantics and report coordinates. In particular, FEL's site reporting uses `1 + coverage[site]`. These source files are newer than the accepted fixture versions and do **not** establish support for their newer formats.
- Official `veg/hyphy-vision` fixtures pinned to **2225f5d8b8b919d3eb6d56cdc77d9ca660dc351d**. Files are retained unmodified; the test suite checks their SHA-256 hashes.

| Local fixture | Upstream file at the pinned commit | SHA-256 |
| --- | --- | --- |
| `CD2.FEL.json` | [fel/CD2.fna.FEL.json](https://github.com/veg/hyphy-vision/blob/2225f5d8b8b919d3eb6d56cdc77d9ca660dc351d/data/json_files/fel/CD2.fna.FEL.json) | `78ce35a9e9e6e2b5c8b6d819b121406fa00d02f913f02b67c4493d78229b3fed` |
| `CD2.MEME.json` | [meme/CD2.fna.MEME.json](https://github.com/veg/hyphy-vision/blob/2225f5d8b8b919d3eb6d56cdc77d9ca660dc351d/data/json_files/meme/CD2.fna.MEME.json) | `1f4e9819cb1fcd8a833bf6ac50bfa4324345c8456c8654348447a4513f0aeb50` |
| `partitioned.FEL.json` | [fel/simulated_data_partitioned.nex.FEL.json](https://github.com/veg/hyphy-vision/blob/2225f5d8b8b919d3eb6d56cdc77d9ca660dc351d/data/json_files/fel/simulated_data_partitioned.nex.FEL.json) | `c826cda4dc13d61d6e5ac2b21ead918f20cdf115cd6a2ffe60bc2d36ce0084b5` |

The CD2 fixtures are mammalian CD2 examples with ten taxa. They are **not** labeled synthetic. The third fixture is explicitly simulated, with two partitions over 40 codons, and is used only to verify rejection. The browser's built-in synthetic example is separate from all these native fixtures. Upstream fixture attribution and rights remain with their respective authors; this project has not selected a license.

## Adapter contract

1. Recognize the method from the `FEL (` or `MEME (` prefix in documented `analysis.info`. The Python/Dash adapter requires exact fixture-covered string versions: FEL `2.00`, MEME `2.00` or `2.1.1`. The additional official lysin fixture and Datamonkey download contract are documented in [datamonkey.md](datamonkey.md); the preserved JavaScript prototype retains MEME `2.1.1` only.
2. Require one partition, keyed `0`, consistently in input counts, partition metadata, trees, tested branches, and MLE results. Reject multiple partitions even if a count was changed to one.
3. Treat `input.number of sites` as the alignment codon count for these formats. Read the ordered, zero-based codon coordinate list from `data partitions.0.coverage[0]`. Each `MLE.content.0` row maps to the corresponding coverage entry. Display `coverage[i] + 1`, retain source row `i` and partition `0`, and reject duplicates, fractional/negative/out-of-range coordinates, malformed matrices, or row-count mismatches. Never divide these codon coordinates by three.
4. Build a column index from header names, retaining each accompanying description and every original column. Reordering the entire header/row table leaves the normalized values unchanged.
5. Require method-specific headers. Missing or non-finite numerical cells become `null` with explicit per-site issues; original cells are untouched. Numeric strings, booleans, empty strings, and missing values do not become zero. Reject malformed row widths. Validate nonnegative rates/LRT/branch length, bounded p-values and mixture weights, and the mixture weight sum.
6. Retain `analysis`, `input`, `tested`, trees, partition metadata, `fits`, `timers`, any `settings`, all native headers and rows, the original parsed object, and the exact decoded source text. Missing optional fits/settings are displayed as not reported.

| Semantic value | FEL header | MEME header |
| --- | --- | --- |
| Synonymous rate | `alpha` | `alpha;` |
| Nonsynonymous rate | `beta` | Separate mixture components below |
| Negative/neutral component | — | `&beta;<sup>-</sup>` |
| Positive/neutral component | — | `&beta;<sup>+</sup>` |
| Component weights | — | `p<sup>-</sup>` and `p<sup>+</sup>` |
| Likelihood-ratio statistic | `LRT` | `LRT` |
| Native site p-value | `p-value` | `p-value` |
| Inferred total branch length | `Total branch length` | `Total branch length` |

Aliases listed above are explicit fixture-observed strings, not arbitrary HTML parsing or guessed column positions. No uploaded header markup is inserted as HTML. Other columns remain in the source inspector and CSV native-row fields. Recognition of correction-bearing headers causes rejection, because their statistical meaning has not been validated in these adapters. The verified fixtures contain no native multiple-testing adjustment.

## Independently checked extraction anchors

Expected literals below were read directly from pinned fixture content with Python independently of the JavaScript adapter. They are hard-coded in tests rather than calculated from the adapter under test.

| Fixture / displayed codon | Expected value |
| --- | --- |
| FEL / 1 | α = `0.0004001600640256103` |
| FEL / 9 | p = `0.04105795180923533`; diversifying at 0.05, nonsignificant at 0.01 |
| FEL / 11 | α = `1.569665853806078`, β = `0`; purifying at 0.05 |
| FEL / 187 | β = `0.8185143783777495`, source row 186 |
| MEME / 43 | β+ = `6.801478770233565`, mixture weight = `0.1297540353909942` |
| MEME / 76 | p = `0.002491251281779738` |
| MEME / 187 | α = `2.937024731663259` |

For both methods, codon 2 has zero inferred rates and branch length: the viewer reports insufficient information rather than neutrality or a proven skipped test. Modified fixture copies exercise sparse/reordered coordinates and missing cells; these are test mutations, not additional claims of verified upstream formats.

## Linking and further methods

The native JSON provides no verified alignment-content hash or embedded original alignment. Native analyses stay isolated. Raw-file equality is also not presented as proof of alignment identity. The linked synthetic dataset's identity and coordinate system are established internally by construction; upload data cannot opt into that identity.

[An upstream Contrast-FEL example exists](https://github.com/veg/hyphy-vision/blob/2225f5d8b8b919d3eb6d56cdc77d9ca660dc351d/data/json_files/contrast-fel/multi.json). It was not used to invent a parser. Its analysis version, biological provenance, branch-group mapping and native correction semantics require a separate verified fixture pass. Native Contrast-FEL remains deferred, not silently approximated with FEL.
