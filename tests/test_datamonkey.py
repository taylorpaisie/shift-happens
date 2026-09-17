"""Datamonkey's verified download contract is native JSON plus a top-level PMID.

The PMID cases below are contract transformations of official CD2 fixtures,
not mislabeled live downloads. See docs/datamonkey.md for pinned server source.
"""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from shift_happens.exports import evidence_csv, figure_svg
from shift_happens.imports import parse_results
from shift_happens.model import can_link, classify
from shift_happens.workspace import active_analyses, import_files, initial_workspace

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return (ROOT / "fixtures" / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name,method,codon,expected", [
    ("CD2.FEL.json", "FEL", 9, 0.04105795180923533),
    ("CD2.MEME.json", "MEME", 43, 0.04003591401881312),
    ("lysin.MEME.json", "MEME", 6, 0.005166111870549717),
])
def test_datamonkey_results_contract_preserves_native_evidence(name, method, codon, expected):
    raw = json.loads(fixture(name))
    raw["PMID"] = "22807683"  # Literal used by the pinned Datamonkey FEL/MEME models.
    original = json.dumps(raw, ensure_ascii=False)
    result = parse_results(original, "results.json")
    native = parse_results(fixture(name))
    assert result.method == method and result.original_text == original and result.raw == raw
    assert result.sites[codon].values["p"] == expected
    assert result.sites[codon].row == codon - 1
    assert [s.values for s in result.sites.values()] == [s.values for s in native.sites.values()]
    assert result.identity is None and not can_link(result, native)
    assert result.input_format == "Native HyPhy / Datamonkey results JSON"
    rows = list(csv.DictReader(io.StringIO(evidence_csv([result], .05))))
    assert rows[codon-1]["publication_metadata"] == "22807683"
    document = ET.fromstring(figure_svg([result], .05, 1, 36))
    metadata = json.loads(document.find(".//{http://www.w3.org/2000/svg}metadata").text)
    assert metadata["sources"][0]["publication_metadata"] == "22807683"


def test_meme_200_official_lysin_fixture():
    data = (ROOT / "fixtures/lysin.MEME.json").read_bytes()
    assert hashlib.sha256(data).hexdigest() == "a17acd9e8dbe8f33cd1c3a7f3d291c09ad1db5f639292338e826a30a19d130e8"
    a = parse_results(data.decode())
    assert a.method == "MEME" and a.version == "2.00" and a.length == 134
    assert a.sites[6].values["betaPlus"] == 23.81442994266141
    assert a.sites[6].values["weightPlus"] == 0.2097491392006071
    assert a.sites[134].values["alpha"] == 380.97244794148
    assert a.sites[134].row == 133
    assert classify(a, a.sites[1]) == "insufficient"
    assert classify(a, a.sites[6]) == "episodic"
    assert classify(a, a.sites[134]) == "nonsignificant"
    raw = json.loads(data)
    raw["MLE"]["headers"].reverse()
    for row in raw["MLE"]["content"]["0"]:
        row.reverse()
    reordered = parse_results(json.dumps(raw))
    assert [s.values for s in a.sites.values()] == [s.values for s in reordered.sites.values()]


@pytest.mark.parametrize("text,filename,expected", [
    ("<!DOCTYPE html><html>Results</html>", "results.html", "Save Page As"),
    ("https://www.datamonkey.org/meme/example", "result.txt", "URLs are not fetched"),
    ('{"status":"running","torque_id":"synthetic-job"}', "job.json", "job/status metadata"),
    ('{"analysis":{"status":"completed"},"upload_redirect_path":"/example"}', "job.json", "job/status metadata"),
    ('{"error":"invalid id"}', "results.json", "error response"),
    ('{"status":"completed"}', "job.json", "not site-level results"),
    ("Site,alpha,beta,p-value\n1,1,2,0.01", "results.csv", "full results JSON"),
    ("Site\talpha\tbeta\np", "results.txt", "results table"),
])
def test_wrong_download_has_actionable_error(text, filename, expected):
    with pytest.raises(ValueError, match=expected):
        parse_results(text, filename)


def test_unknown_version_and_methods_remain_rejected():
    raw = json.loads(fixture("CD2.MEME.json"))
    raw["analysis"]["version"] = "99.0"
    raw["PMID"] = "22807683"
    with pytest.raises(ValueError, match="Do not edit the version"):
        parse_results(json.dumps(raw))
    raw["analysis"]["info"] = "FUBAR (Fast, Unconstrained Bayesian AppRoximation)"
    with pytest.raises(ValueError, match="Other Datamonkey methods are not yet validated"):
        parse_results(json.dumps(raw))


def test_publication_metadata_is_not_a_method_or_identity_signal():
    with pytest.raises(ValueError, match="Missing analysis metadata"):
        parse_results('{"PMID":"22807683"}')
    raw = json.loads(fixture("CD2.FEL.json"))
    raw["PMID"] = '<script>window.bad=true</script>'
    a = parse_results(json.dumps(raw), "datamonkey.json")
    assert a.identity is None
    svg = figure_svg([a], .05, 1, 36)
    assert "<script>" not in svg and "&lt;script&gt;" in svg


def test_multiple_results_upload_retains_good_files_after_job_record_error():
    raw = json.loads(fixture("CD2.MEME.json"))
    raw["PMID"] = "22807683"
    contents = ["data:application/json;base64," + base64.b64encode(s.encode()).decode() for s in [json.dumps(raw), '{"status":"completed"}']]
    workspace, selected, notice = import_files(initial_workspace(), contents, ["results.json", "job.json"])
    assert len(workspace["files"]) == 1 and "job/status metadata" in notice
    assert active_analyses(workspace, selected)[0].raw["PMID"] == "22807683"
