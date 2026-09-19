"""Portable evidence exports. SVG needs neither Kaleido nor a browser binary."""
import csv
import io
import json
import re
from xml.sax.saxutils import escape
from .model import STATES, classify


def csv_cell(value):
    if value is None:
        return ""
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return "'" + text if re.match(r"^\s*[=+@-]", text) else text


def evidence_csv(analyses, threshold):
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["source", "method", "method_version", "synthetic", "codon_1based", "partition", "source_row_0based", "state",
                     "alpha", "beta", "beta_minus", "beta_plus", "weight_plus", "group_A_rate_demo", "group_B_rate_demo", "LRT", "p_value",
                     "threshold", "correction", "scope", "tested_branches", "issues", "native_headers", "native_row", "input_format", "publication_metadata"])
    for a in analyses:
        for codon in range(1, a.length + 1):
            site = a.sites.get(codon)
            v = site.values if site else {}
            row = [a.filename, a.method, a.version, a.synthetic, codon, site.partition if site else None, site.row if site else None,
                   STATES[classify(a, site, threshold)][0], *[v.get(k) for k in ("alpha", "beta", "betaMinus", "betaPlus", "weightPlus", "groupA", "groupB", "lrt", "p")],
                   threshold, a.correction, a.scope, a.raw["tested"], site.issues if site else None, a.raw.get("MLE", {}).get("headers"), site.native if site else None, a.input_format, a.raw.get("PMID")]
            writer.writerow([csv_cell(value) for value in row])
    return output.getvalue()


def xml(value):
    return escape(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "\ufffd", str(value)), {'"': '&quot;', "'": '&apos;'})


def figure_svg(analyses, threshold, start, end):
    if not analyses or not 1 <= start <= end <= analyses[0].length:
        raise ValueError("Choose a valid analysis coordinate window before exporting.")
    width, left, plot_width = 1200, 185, 970
    cell = plot_width / (end - start + 1)
    legend_y = 160 + len(analyses) * 64
    source_lines = []
    for a in analyses:
        name = re.sub(r"\s", " ", f"{a.method} {a.version} · {a.filename}")
        source_lines.extend(name[i:i+125] for i in range(0, len(name), 125))
        source_lines.append(f"{a.scope_summary} · Partition 0 · {'Synthetic shared coordinates' if a.synthetic else 'Alignment content unverified; method-native evidence'}")
    height = legend_y + 215 + len(source_lines) * 20
    synthetic = any(a.synthetic for a in analyses)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Shift Happens — selection evidence</title>',
             f'<desc id="desc">{"SYNTHETIC illustration. " if synthetic else ""}Codons {start}–{end}. Separate method-native evidence, not a combined score.</desc>',
             '<rect width="100%" height="100%" fill="white"/><g font-family="Arial, sans-serif" fill="#203345">',
             '<text x="35" y="40" font-size="25" font-weight="bold">Shift Happens</text><text x="35" y="65" font-size="14">See where selection changes.</text>',
             f'<text x="35" y="92" font-size="14">{"SYNTHETIC ILLUSTRATION · " if synthetic else ""}Unadjusted exploratory p ≤ {threshold} · Alignment codons {start}–{end} (1-based)</text>']
    metadata = dict(threshold=threshold, start=start, end=end, sources=[dict(filename=a.filename, method=a.method, version=a.version,
                    synthetic=a.synthetic, scope=a.scope, correction=a.correction, tested=a.raw["tested"], settings=a.raw.get("settings"), partitions=a.raw["data partitions"], input_format=a.input_format, publication_metadata=a.raw.get("PMID")) for a in analyses])
    parts.append(f'<metadata>{xml(json.dumps(metadata, ensure_ascii=False))}</metadata>')
    for i, a in enumerate(analyses):
        y = 130 + i * 64
        parts.append(f'<text x="35" y="{y+20}" font-size="16" font-weight="bold">{xml(a.method)}</text>')
        for codon in range(start, end + 1):
            label, color, symbol = STATES[classify(a, a.sites.get(codon), threshold)]
            x = left + (codon - start) * cell
            parts.append(f'<rect x="{x}" y="{y}" width="{max(0.5, cell-1)}" height="30" fill="{color}" stroke="#64748b" stroke-width="0.4"><title>Codon {codon}: {xml(label)}</title></rect>')
            if cell > 10:
                fill = "#ffffff" if symbol in ("−", "+", "E", "Δ") else "#243548"
                parts.append(f'<text x="{x+cell/2}" y="{y+20}" text-anchor="middle" font-size="11" fill="{fill}">{symbol}</text>')
            if codon in (start, end) or codon % max(1, (end-start+1+11)//12) == 0:
                parts.append(f'<text x="{x+cell/2}" y="{y+46}" text-anchor="middle" font-size="10">{codon}</text>')
    for i, (label, color, symbol) in enumerate(STATES.values()):
        x, y = 35 + (i % 2) * 540, legend_y + (i // 2) * 25
        parts.append(f'<rect x="{x}" y="{y-12}" width="17" height="17" fill="{color}" stroke="#64748b"/><text x="{x+26}" y="{y+1}" font-size="13">{xml(symbol + " " + label)}</text>')
    y = legend_y + 116
    for line in source_lines:
        parts.append(f'<text x="35" y="{y}" font-size="12">{xml(line)}</text>')
        y += 20
    for offset, note in enumerate([
        "FEL: pervasive evidence. MEME: episodic diversification. Nonsignificance is not proof of neutrality.",
        "Contrast-FEL differences do not establish positive selection or locate a shift in time. No combined confidence score.",
        "Inferred selective pressures, not measured fitness. Rate ratios are omitted; original estimates remain in the evidence table.",
    ]):
        parts.append(f'<text x="35" y="{y+8+offset*19}" font-size="12">{note}</text>')
    return "".join(parts) + "</g></svg>"
