"""Bounded UTF-8 JSON decoding and normalization, without Dash dependencies."""
import base64
import binascii
import json
from .model import Analysis, Site
from .validation import validate_document, validate_values

MAX_BYTES = 25 * 1024 * 1024


def parse_hyphy(text, filename="analysis.json", max_bytes=MAX_BYTES, max_codons=100000):
    if not isinstance(text, str) or len(text.encode("utf-8")) > max_bytes:
        raise ValueError(f"File exceeds the {max_bytes // (1024 * 1024)} MiB limit. Use a smaller individual analysis output.")
    def reject_constant(value):
        raise ValueError(f"Non-JSON constant {value}")
    try:
        raw = json.loads(text.lstrip("\ufeff"), parse_constant=reject_constant)
    except (ValueError, RecursionError) as error:
        raise ValueError("Invalid JSON. Upload the complete HyPhy JSON output, not a log or CSV.") from error
    method, version, length, coordinates, rows, indexes, required = validate_document(raw, max_codons)
    sites = {}
    for i, (coordinate, row) in enumerate(zip(coordinates, rows)):
        values, issues = validate_values(row, indexes, required, method)
        sites[coordinate + 1] = Site(coordinate + 1, i, values, issues, row)
    return Analysis(method, version, length, filename, sites, raw, text)


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
        raise ValueError(f"Invalid upload. Choose a UTF-8 HyPhy JSON file under {max_bytes // (1024 * 1024)} MiB.") from error
