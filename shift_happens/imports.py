"""Bounded UTF-8 JSON decoding and normalization, without Dash dependencies."""
import base64
import binascii
import json
from .model import Analysis, Site
from .validation import validate_document, validate_values

MAX_BYTES = 25 * 1024 * 1024


def parse_results(text, filename="analysis.json", max_bytes=MAX_BYTES, max_codons=100000):
    """Read full HyPhy/Datamonkey results; neither filenames nor PMID prove origin."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > max_bytes:
        raise ValueError(f"File exceeds the {max_bytes // (1024 * 1024)} MiB limit. Use a smaller individual analysis output.")
    stripped = text.lstrip("\ufeff \t\r\n")
    if stripped.startswith("<"):
        raise ValueError("This is a webpage or XML file, not analysis results. On the completed Datamonkey results page, download the full results JSON; do not use Save Page As.")
    if stripped.lower().startswith(("https://", "http://")):
        raise ValueError("This is a results-page URL. Download the full results JSON from Datamonkey, then upload that file. URLs are not fetched by this importer.")
    def reject_constant(value):
        raise ValueError(f"Non-JSON constant {value}")
    try:
        raw = json.loads(text.lstrip("\ufeff"), parse_constant=reject_constant)
    except (ValueError, RecursionError) as error:
        first_line = stripped.splitlines()[0] if stripped else ""
        if not stripped.startswith(("{", "[")) and (filename.lower().endswith(".csv") or any(c in first_line for c in (",", "\t"))):
            raise ValueError("This is a results table, not full results JSON. Datamonkey CSV tables do not provide all required branch scope, version, and coordinate metadata. Download the full results JSON instead.") from error
        raise ValueError("Invalid JSON. Upload the full HyPhy or Datamonkey results JSON, not a log or CSV.") from error
    if isinstance(raw, dict) and "MLE" not in raw:
        job = raw.get("analysis", raw)
        if any(k in raw for k in ("status", "torque_id", "upload_redirect_path", "error", "msg")) or isinstance(job, dict) and "status" in job:
            raise ValueError("This is Datamonkey job/status metadata or an error response, not site-level results. Wait for the analysis to complete and download its full results JSON.")
    method, version, length, coordinates, rows, indexes, required = validate_document(raw, max_codons)
    sites = {}
    for i, (coordinate, row) in enumerate(zip(coordinates, rows)):
        values, issues = validate_values(row, indexes, required, method)
        sites[coordinate + 1] = Site(coordinate + 1, i, values, issues, row)
    return Analysis(method, version, length, filename, sites, raw, text)


def parse_hyphy(text, filename="analysis.json", max_bytes=MAX_BYTES, max_codons=100000):
    """Backward-compatible API for the native schema also used by Datamonkey."""
    return parse_results(text, filename, max_bytes, max_codons)


def decode_upload(contents, max_bytes=MAX_BYTES):
    if not isinstance(contents, str) or len(contents) > max_bytes * 4 // 3 + 1024:
        raise ValueError(f"Upload exceeds the {max_bytes // (1024 * 1024)} MiB limit.")
    try:
        header, payload = contents.split(",", 1)
        if not header.startswith("data:") or not header.endswith(";base64"):
            raise ValueError("Expected base64 upload")
        data = base64.b64decode(payload, validate=True)
        if len(data) > max_bytes:
            raise ValueError("Upload exceeds the configured size limit.")
        return data.decode("utf-8")
    except (ValueError, binascii.Error, UnicodeDecodeError) as error:
        raise ValueError(f"Invalid upload. Choose a UTF-8 HyPhy or Datamonkey results JSON file under {max_bytes // (1024 * 1024)} MiB.") from error
