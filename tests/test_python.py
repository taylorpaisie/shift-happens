"""Independent Python regression tests against the same pinned official outputs."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from app import create_app
from shift_happens.demo import create_demo
from shift_happens.exports import evidence_csv, figure_svg
from shift_happens.imports import decode_upload, parse_hyphy
from shift_happens.model import can_link, classify
from shift_happens.views import track_figure, inspector
from shift_happens.workspace import active_analyses, import_files, initial_workspace, options

ROOT = Path(__file__).resolve().parents[1]


def text(name="CD2.FEL.json"):
    return (ROOT / "fixtures" / name).read_text(encoding="utf-8")


def changed(fn, name="CD2.FEL.json"):
    raw = json.loads(text(name))
    fn(raw)
    return parse_hyphy(json.dumps(raw))


def upload(value):
    return "data:application/json;base64," + base64.b64encode(value.encode()).decode()


@pytest.mark.parametrize("name,digest", [
    ("CD2.FEL.json", "78ce35a9e9e6e2b5c8b6d819b121406fa00d02f913f02b67c4493d78229b3fed"),
    ("FEL-2.6.Datamonkey.json", "87ca1554628aef7d94f3f06afc273c79bbcc1ff5ba47832afcfca17882730cd4"),
    ("CD2.MEME.json", "1f4e9819cb1fcd8a833bf6ac50bfa4324345c8456c8654348447a4513f0aeb50"),
    ("partitioned.FEL.json", "c826cda4dc13d61d6e5ac2b21ead918f20cdf115cd6a2ffe60bc2d36ce0084b5"),
])
def test_fixture_integrity(name, digest):
    assert hashlib.sha256((ROOT / "fixtures" / name).read_bytes()).hexdigest() == digest


def test_fel_expected_values_and_provenance():
    a = parse_hyphy(text(), "source.json")
    assert a.method == "FEL" and a.version == "2.00" and len(a.sites) == 187
    assert a.sites[1].values["alpha"] == 0.0004001600640256103
    assert a.sites[9].values["p"] == 0.04105795180923533
    assert a.sites[11].values["alpha"] == 1.569665853806078
    assert a.sites[187].values["beta"] == 0.8185143783777495
    assert a.sites[187].row == 186
    assert a.original_text == text() and a.filename == "source.json" and a.identity is None
    assert a.raw == json.loads(text()) and a.raw["fits"]["Nucleotide GTR"]
    assert a.raw["tested"]["0"]["Pig"] == "test"


def test_fel_26_datamonkey_fixture_and_substitution_mapping():
    a = parse_hyphy(text("FEL-2.6.Datamonkey.json"), "FEL_analysis.json")
    assert a.method == "FEL" and a.version == "2.6" and a.length == 42
    assert len(a.sites) == 42
    assert a.sites[9].values == {
        "alpha": 18.00931351361862,
        "beta": 0.00006425039486038318,
        "lrt": 6.720217894823282,
        "p": 0.0095325979984765,
        "branchLength": 1.087374464365363,
    }
    assert a.sites[42].values["p"] == 0.05979535762667387
    assert classify(a, a.sites[9]) == "purifying"
    assert a.raw["substitutions"]["0"]["8"]["root"] == "GTC"
    assert a.raw["exportMetadata"]["method"] == "FEL"


def test_meme_expected_values():
    a = parse_hyphy(text("CD2.MEME.json"))
    assert a.version == "2.1.1" and len(a.sites) == 187
    assert a.sites[43].values["betaPlus"] == 6.801478770233565
    assert a.sites[43].values["weightPlus"] == 0.1297540353909942
    assert a.sites[76].values["p"] == 0.002491251281779738
    assert a.sites[187].values["alpha"] == 2.937024731663259


@pytest.mark.parametrize("name", ["CD2.FEL.json", "CD2.MEME.json"])
def test_header_order_independence(name):
    def reverse(raw):
        raw["MLE"]["headers"].reverse()
        for row in raw["MLE"]["content"]["0"]:
            row.reverse()
    a, b = parse_hyphy(text(name)), changed(reverse, name)
    assert [s.values for s in a.sites.values()] == [s.values for s in b.sites.values()]


def test_method_specific_interpretation():
    fel, meme = parse_hyphy(text()), parse_hyphy(text("CD2.MEME.json"))
    assert classify(fel, fel.sites[9]) == "pervasive"
    assert classify(fel, fel.sites[11]) == "purifying"
    assert classify(fel, fel.sites[1]) == "nonsignificant"
    assert classify(fel, fel.sites[2]) == "insufficient"
    assert classify(meme, meme.sites[43]) == "episodic"
    assert classify(meme, meme.sites[1]) == "nonsignificant"
    assert classify(meme, meme.sites[2]) == "insufficient"
    assert classify(fel, fel.sites[9], .01) == "nonsignificant"
    assert fel.sites[9].values["p"] == 0.04105795180923533


@pytest.mark.parametrize("threshold", [0, -1, 2, float("nan"), True, "0.05"])
def test_bad_threshold(threshold):
    a = create_demo()[0]
    with pytest.raises(ValueError, match="Threshold"):
        classify(a, a.sites[1], threshold)


def test_sparse_and_reordered_coverage():
    def mutate(raw):
        raw["data partitions"]["0"]["coverage"] = [[10, 0, 186]]
        raw["MLE"]["content"]["0"] = raw["MLE"]["content"]["0"][:3]
    a = changed(mutate)
    assert [(s.codon, s.row) for s in a.sites.values()] == [(11, 0), (1, 1), (187, 2)]
    assert classify(a, a.sites.get(2)) == "untested"


@pytest.mark.parametrize("value", [1, -1, .5, 187, "0", None, False, []])
def test_bad_coordinates(value):
    with pytest.raises(ValueError, match="Coverage"):
        changed(lambda r: r["data partitions"]["0"]["coverage"][0].__setitem__(0, value))


@pytest.mark.parametrize("value", [None, "", "0", "NaN", -1, 1.1, False])
def test_invalid_values_are_not_zero(value):
    a = changed(lambda r: r["MLE"]["content"]["0"][8].__setitem__(4, value))
    assert a.sites[9].values["p"] is None
    assert classify(a, a.sites[9]) == "insufficient"
    assert a.raw["MLE"]["content"]["0"][8][4] == value


@pytest.mark.parametrize("mutation,pattern", [
    (lambda r: r["MLE"]["headers"][0].__setitem__(0, "unknown"), "Missing required"),
    (lambda r: r["MLE"]["headers"][1].__setitem__(0, "alpha"), "Duplicate"),
    (lambda r: r["MLE"]["headers"][1].__setitem__(0, "alpha;"), "Ambiguous"),
    (lambda r: r["MLE"]["headers"][4].__setitem__(0, "Corrected P-value"), "correction metadata"),
    (lambda r: r["MLE"]["content"]["0"].pop(), "row count"),
    (lambda r: r["MLE"]["content"]["0"][0].pop(), "columns"),
    (lambda r: r["analysis"].__setitem__("version", "99.0"), "Unsupported FEL method version"),
    (lambda r: r["analysis"].__setitem__("info", "Contrast-FEL"), "Unsupported analysis"),
    (lambda r: r.pop("tested"), "branch scope"),
    (lambda r: r["tested"]["0"].__setitem__("Pig", "unknown"), "branch labels"),
    (lambda r: r["input"].__setitem__("number of sites", True), "number of sites"),
    (lambda r: r["input"].pop("trees"), "input tree"),
    (lambda r: r["MLE"]["content"].__setitem__("1", []), "single-partition"),
    (lambda r: r["data partitions"].__setitem__("0", None), "coverage"),
])
def test_reject_invalid_structure(mutation, pattern):
    with pytest.raises(ValueError, match=pattern):
        changed(mutation)


def test_recombination_and_mixture():
    with pytest.raises(ValueError, match="Recombination"):
        parse_hyphy(text("partitioned.FEL.json"))
    a = changed(lambda r: r["MLE"]["content"]["0"][42].__setitem__(4, .9), "CD2.MEME.json")
    assert classify(a, a.sites[43]) == "insufficient"


@pytest.mark.parametrize("source", ["not JSON", '{"p":NaN}', '{"p":Infinity}', '[]', '{"analyses":[]}'])
def test_non_native_json(source):
    with pytest.raises(ValueError):
        parse_hyphy(source)


def test_identity_and_demo_semantics():
    a, b, contrast = create_demo()
    assert can_link(a, b) and classify(contrast, contrast.sites[13]) == "difference"
    native = parse_hyphy(text())
    assert not can_link(a, native) and not can_link(native, native)
    assert not can_link(native, parse_hyphy(text("CD2.MEME.json")))
    b.length = 71
    assert not can_link(a, b)


def test_exports_are_complete_and_safe():
    a = parse_hyphy(text(), '=HYPERLINK("bad")<script>x</script>\x00')
    rows = list(csv.DictReader(io.StringIO(evidence_csv([a], .05))))
    assert len(rows) == 187 and rows[8]["p_value"] == "0.04105795180923533"
    assert rows[0]["source"].startswith("'=") and rows[10]["state"] == "FEL · purifying"
    assert json.loads(rows[0]["native_row"])[0] == 0.0004001600640256103
    svg = figure_svg([a], .05, 1, 72)
    root = ET.fromstring(svg)
    assert "<script>" not in svg and "&lt;script&gt;" in svg
    assert "p ≤ 0.05" in svg and "purifying" in svg and "not proof of neutrality" in svg
    metadata = root.find(".//{http://www.w3.org/2000/svg}metadata")
    assert json.loads(metadata.text)["sources"][0]["method"] == "FEL"
    demo = evidence_csv(create_demo(), .05)
    assert len(list(csv.DictReader(io.StringIO(demo)))) == 216
    assert "SYNTHETIC" in figure_svg(create_demo(), .05, 1, 36)


def test_upload_workspace_isolation_and_error_recovery():
    first = initial_workspace()
    updated, selected, notice = import_files(first, [upload(text()), upload(text("partitioned.FEL.json"))], ["fel.json", "partitioned.json"])
    assert len(updated["files"]) == 1 and not first["files"] and "Recombination" in notice
    assert len(options(updated)) == 2 and active_analyses(updated, selected)[0].method == "FEL"
    assert len(active_analyses(updated, "demo")) == 3 and active_analyses(first, selected) == []
    assert decode_upload(upload(text())) == text()
    with pytest.raises(ValueError, match="Invalid upload"):
        decode_upload("data:application/json;base64,@@@")


def test_plotly_tracks_share_real_codon_axis_and_inspection():
    demo = create_demo()
    figure = track_figure(demo, .05, 1, 36, 14)
    assert len(figure.data) == 3
    assert list(figure.data[0].x) == list(figure.data[1].x) == list(range(1, 37))
    assert figure.data[0].marker.color[13] == "#2868a5"
    assert figure.data[0].customdata[13][0] == 14
    assert figure.layout.shapes[0].x0 == 13.51
    assert len(inspector(demo, 14, .05)) == 3


def test_dash_routes_and_callback_graph():
    app = create_app()
    client = app.server.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/assets/dash.css").status_code == 200
    assert client.get("/_dash-layout").status_code == 200
    assert client.get("/_dash-dependencies").status_code == 200
    assert len(app.callback_map) == 3
