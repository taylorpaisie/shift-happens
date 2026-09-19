"""Normalized evidence and conservative compatibility, independent of Dash."""
from dataclasses import dataclass, field
import math

STATES = {
    "purifying": ("FEL · purifying", "#2868a5", "−"),
    "pervasive": ("FEL · diversifying", "#b24d20", "+"),
    "episodic": ("MEME · episodic diversification", "#99601a", "E"),
    "difference": ("Contrast-FEL · difference (demo)", "#76549b", "Δ"),
    "nonsignificant": ("Nonsignificant", "#cbd2d9", "·"),
    "untested": ("Untested / outside coverage", "#ffffff", "—"),
    "insufficient": ("Insufficient information", "#eef0f3", "?"),
}


def finite_number(value):
    # bool is a subclass of int in Python; it must not become a rate or p-value.
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


@dataclass
class Site:
    codon: int
    row: int
    values: dict
    issues: list[str] = field(default_factory=list)
    native: list | None = None
    partition: str = "0"


@dataclass
class Analysis:
    method: str
    version: str
    length: int
    filename: str
    sites: dict[int, Site]
    raw: dict
    original_text: str | None = None
    synthetic: bool = False
    identity: str | None = None

    @property
    def input_format(self):
        return "Built-in synthetic illustration" if self.synthetic else "Native HyPhy / Datamonkey results JSON"

    @property
    def scope(self):
        return {
            "FEL": "Pervasive site evidence over tested branches",
            "MEME": "Episodic site evidence over tested branches",
            "Contrast-FEL": "Difference between branch groups A and B; does not establish positive selection",
        }[self.method]

    @property
    def correction(self):
        return ("Hand-authored unadjusted illustrative p-values" if self.synthetic else
                "None reported in validated schema; unadjusted exploratory threshold")

    @property
    def scope_summary(self):
        labels = list(self.raw["tested"]["0"].values())
        return f"{labels.count('test')} test / {labels.count('background')} background branches"


def classify(analysis, site, threshold=0.05):
    if not finite_number(threshold) or not 0 < threshold <= 1:
        raise ValueError("Threshold must be greater than 0 and at most 1.")
    if site is None:
        return "untested"
    v = site.values
    if site.issues or v.get("p") is None:
        return "insufficient"
    if v["p"] > threshold:
        return "nonsignificant"
    if analysis.method == "FEL":
        return "purifying" if v["beta"] < v["alpha"] else "pervasive" if v["beta"] > v["alpha"] else "insufficient"
    if analysis.method == "MEME":
        return "episodic" if v["betaPlus"] > v["alpha"] and v["weightPlus"] > 0 else "insufficient"
    return "difference" if analysis.synthetic and analysis.method == "Contrast-FEL" else "insufficient"


def can_link(a, b):
    return (a.synthetic and b.synthetic and a.identity == b.identity == "builtin-demo-v1"
            and a.length == b.length)


def native_comparison_key(analysis):
    """Conservative coordinate-metadata match; never claims alignment identity."""
    if analysis.synthetic:
        return None
    raw = analysis.raw
    export = raw.get("exportMetadata")
    source = raw.get("input")
    partitions = raw.get("data partitions")
    branches = raw.get("branch attributes")
    tested = raw.get("tested")
    if not all(isinstance(value, dict) for value in (export, source, partitions, branches, tested)):
        return None
    export_name, input_name = export.get("filename"), source.get("file name")
    partition = partitions.get("0")
    branch_data, tested_data = branches.get("0"), tested.get("0")
    if not (isinstance(export_name, str) and export_name and isinstance(input_name, str) and input_name
            and isinstance(partition, dict) and isinstance(branch_data, dict) and isinstance(tested_data, dict)):
        return None
    coverage = partition.get("coverage")
    if not (isinstance(coverage, list) and len(coverage) == 1 and isinstance(coverage[0], list)):
        return None
    leaf_scope = []
    for branch, attributes in branch_data.items():
        if isinstance(attributes, dict) and isinstance(attributes.get("original name"), str):
            label = tested_data.get(branch)
            if label not in ("test", "background"):
                return None
            leaf_scope.append((attributes["original name"], label))
    sequences = source.get("number of sequences")
    if type(sequences) is not int or len(leaf_scope) != sequences or len({name for name, _ in leaf_scope}) != sequences:
        return None
    return (export_name, input_name, sequences, source.get("number of sites"), tuple(coverage[0]), tuple(sorted(leaf_scope)))


def can_compare_native(a, b):
    key = native_comparison_key(a)
    return (key is not None and key == native_comparison_key(b) and a.method != b.method
            and {a.method, b.method} == {"FEL", "MEME"} and a.length == b.length)
