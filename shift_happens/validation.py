"""Fixture-covered native schema validation. No positional column guesses."""
import re
from .model import finite_number

SUPPORTED = {"FEL": ("2.00",), "MEME": ("2.1.1",)}
ALIASES = {
    "alpha": "alpha", "alpha;": "alpha", "beta": "beta",
    "&beta;<sup>-</sup>": "betaMinus", "&beta;<sup>+</sup>": "betaPlus",
    "p<sup>-</sup>": "weightMinus", "p<sup>+</sup>": "weightPlus",
    "LRT": "lrt", "p-value": "p", "Total branch length": "branchLength",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def single_partition(value):
    return isinstance(value, dict) and list(value) == ["0"]


def validate_document(raw):
    require(isinstance(raw, dict) and isinstance(raw.get("analysis"), dict),
            "Missing analysis metadata. Native HyPhy JSON is required; normalized project JSON is a different format.")
    info = raw["analysis"].get("info")
    match = re.match(r"^(FEL|MEME)\s*\(", info.strip()) if isinstance(info, str) else None
    require(match, "Unsupported analysis. Import native FEL 2.00 or MEME 2.1.1 JSON. Contrast-FEL is demo-only.")
    method = match.group(1)
    version = raw["analysis"].get("version")
    require(version in SUPPORTED[method], f"Unsupported {method} method version {version!r}. Verified: {', '.join(SUPPORTED[method])}. A new version needs fixture validation.")
    source = raw.get("input")
    require(isinstance(source, dict), "Missing input metadata. Export the complete HyPhy output.")
    length = source.get("number of sites")
    require(type(length) is int and 0 < length <= 100000, "input.number of sites must be an integer from 1 to 100000 codons.")
    sequences = source.get("number of sequences")
    require(type(sequences) is int and sequences > 0, "Missing or invalid input.number of sequences.")
    require(type(source.get("partition count")) is int and source["partition count"] == 1 and single_partition(raw.get("data partitions")),
            "Only a single partition (0) is supported. Recombination partitions require separate trees and coordinate interpretation; this viewer will not flatten them.")
    partition = raw["data partitions"]["0"]
    coverage = partition.get("coverage") if isinstance(partition, dict) else None
    require(isinstance(coverage, list) and len(coverage) == 1 and isinstance(coverage[0], list),
            "Expected data partitions.0.coverage as one row of zero-based codon coordinates.")
    coordinates = coverage[0]
    require(bool(coordinates) and all(type(c) is int and 0 <= c < length for c in coordinates),
            "Coverage contains invalid or out-of-range codon coordinates.")
    require(len(set(coordinates)) == len(coordinates), "Coverage contains duplicate codon coordinates.")
    tested = raw.get("tested")
    require(single_partition(tested) and isinstance(tested["0"], dict) and bool(tested["0"]),
            "Missing tested.0 branch scope. Export the complete analysis; scope cannot be inferred from a filename.")
    require(all(v in ("test", "background") for v in tested["0"].values()) and "test" in tested["0"].values(),
            "Unsupported tested-branch labels or no test branches. Expected test/background labels.")
    trees = source.get("trees")
    require(single_partition(trees) and isinstance(trees["0"], str) and bool(trees["0"]),
            "Missing single-partition input tree. Export the complete HyPhy JSON.")
    mle = raw.get("MLE")
    require(isinstance(mle, dict) and isinstance(mle.get("headers"), list) and single_partition(mle.get("content")),
            "Missing MLE.headers or single-partition MLE.content.0.")
    headers = mle["headers"]
    require(bool(headers) and all(isinstance(h, list) and len(h) == 2 and all(isinstance(v, str) and v for v in h) for h in headers),
            "Each MLE header must contain a name and description.")
    require(len({h[0] for h in headers}) == len(headers), "Duplicate MLE header names make columns ambiguous.")
    require(not any(re.search(r"adjusted|corrected|q-value|false discovery|holm|bonferroni", " ".join(h), re.I) for h in headers),
            "This file contains correction metadata not covered by the validated adapter. Native corrections require interpretation before this format can be supported.")
    indexes = {}
    for i, (name, _) in enumerate(headers):
        key = ALIASES.get(name)
        if key:
            require(key not in indexes, f"Ambiguous aliases for {key} in MLE.headers.")
            indexes[key] = i
    required = (["alpha", "beta"] if method == "FEL" else ["alpha", "betaMinus", "betaPlus", "weightMinus", "weightPlus"]) + ["lrt", "p", "branchLength"]
    for key in required:
        require(key in indexes, f"Missing required {method} MLE header: {key}. Column positions are never assumed.")
    rows = mle["content"]["0"]
    require(isinstance(rows, list) and len(rows) == len(coordinates), "MLE row count does not match partition coverage.")
    for i, row in enumerate(rows):
        require(isinstance(row, list) and len(row) == len(headers), f"MLE row {i + 1} has the wrong number of columns. Expected {len(headers)}.")
    return method, version, length, coordinates, rows, indexes, required


def validate_values(row, indexes, required, method):
    values, issues = {}, []
    for key in required:
        value = row[indexes[key]]
        valid = finite_number(value) and value >= 0 and (key not in ("p", "weightMinus", "weightPlus") or value <= 1)
        values[key] = value if valid else None
        if not valid:
            issues.append(f"{key}: missing or invalid value (original retained)")
    if method == "MEME" and all(values[k] is not None for k in ("weightMinus", "weightPlus")):
        if abs(values["weightMinus"] + values["weightPlus"] - 1) > 1e-6:
            issues.append("MEME mixture weights do not sum to one")
    if values["branchLength"] == 0:
        issues.append("Zero inferred branch length: insufficient information")
    rate_keys = ["alpha", "beta"] if method == "FEL" else ["alpha", "betaMinus", "betaPlus"]
    if all(values[k] == 0 for k in rate_keys):
        issues.append("All estimated rates are zero: insufficient information")
    return values, issues
