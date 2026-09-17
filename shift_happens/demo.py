"""Hand-authored illustrative evidence; never passed off as HyPhy output."""
from .model import Analysis, Site


def create_demo():
    analyses = []
    for method in ("FEL", "MEME", "Contrast-FEL"):
        sites = {}
        for codon in range(1, 73):
            if codon == 31:
                continue
            supported = (codon % 7 == 0 or codon % 11 == 0) if method == "FEL" else codon % (9 if method == "MEME" else 13) == 0
            values = dict(alpha=1, beta=0.15 if codon % 7 == 0 else 1.7, betaMinus=0.3, betaPlus=3.4,
                          weightMinus=0.8, weightPlus=0.2, p=0.008 if supported else 0.47,
                          lrt=7 if supported else 0.5, branchLength=2)
            if method == "Contrast-FEL":
                values.update(groupA=0.2, groupB=1.2 if supported else 0.25)
            sites[codon] = Site(codon, len(sites), values, ["Synthetic missing estimate"] if codon == 20 else [])
        raw = {
            "analysis": {"info": "SYNTHETIC hand-authored illustration; not a biological analysis", "version": "illustration-v1"},
            "tested": {"0": {"Example A": "test", "Example B": "test"}},
            "data partitions": {"0": {"coverage": [[c - 1 for c in sites]]}},
        }
        analyses.append(Analysis(method, "illustration-v1", 72, f"SYNTHETIC-{method}", sites, raw,
                                 synthetic=True, identity="builtin-demo-v1"))
    return analyses
