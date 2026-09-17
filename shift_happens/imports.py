"""Bounded UTF-8 JSON decoding and normalization, without Dash dependencies."""
import base64
import binascii
import json
from .model import Analysis, Site
from .validation import validate_document, validate_values

MAX_BYTES = 25 * 1024 * 1024


def parse_hyphy(text, filename="analysis.json"):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("File exceeds the 25 MiB limit. Use a smaller individual analysis output.")
    def reject_constant(value):
        raise ValueError(f"Non-JSON constant {value}")
    try:
        raw = json.loads(text.lstrip("\ufeff"), parse_constant=reject_constant)
    except (ValueError, RecursionError) as error:
        raise ValueError("Invalid JSON. Upload the complete HyPhy JSON output, not a log or CSV.") from error
    method, version, length, coordinates, rows, indexes, required = validate_document(raw)
    sites = {}
    for i, (coordinate, row) in enumerate(zip(coordinates, rows)):
        values, issues = validate_values(row, indexes, required, method)
        sites[coordinate + 1] = Site(coordinate + 1, i, values, issues, row)
    return Analysis(method, version, length, filename, sites, raw, text)


def decode_upload(contents):
    if not isinstance(contents, str) or len(contents) > MAX_BYTES * 4 // 3 + 1024:
        raise ValueError("Upload exceeds the 25 MiB limit.")
    try:
        header, payload = contents.split(",", 1)
        if not header.startswith("data:") or not header.endswith(";base64"):
            raise ValueError("Expected base64 upload")
        data = base64.b64decode(payload, validate=True)
        if len(data) > MAX_BYTES:
            raise ValueError("Upload exceeds the 25 MiB limit.")
        return data.decode("utf-8")
    except (ValueError, binascii.Error, UnicodeDecodeError) as error:
        raise ValueError("Invalid upload. Choose a UTF-8 HyPhy JSON file under 25 MiB.") from error
