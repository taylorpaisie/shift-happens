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
