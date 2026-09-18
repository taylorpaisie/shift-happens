"""Deployment contract tests that run without a Render account or paid service."""
import base64
import json
from pathlib import Path
import runpy
import pytest
import yaml
from app import create_app
from shift_happens.config import Settings
from shift_happens.imports import parse_hyphy
from shift_happens.workspace import import_files, initial_workspace

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    for key in ("RENDER", "SHIFT_HAPPENS_HOSTED", "SHIFT_HAPPENS_MAX_FILE_MIB", "SHIFT_HAPPENS_MAX_WORKSPACE_MIB", "SHIFT_HAPPENS_MAX_CODONS"):
        monkeypatch.delenv(key, raising=False)


def test_local_defaults_and_render_detection(monkeypatch):
    assert Settings.from_env() == Settings(False, 25, 50, 100000)
    monkeypatch.setenv("RENDER", "true")
    assert Settings.from_env() == Settings(True, 5, 10, 10000)


@pytest.mark.parametrize("key,value", [("SHIFT_HAPPENS_MAX_FILE_MIB", "0"), ("SHIFT_HAPPENS_MAX_WORKSPACE_MIB", "51"), ("SHIFT_HAPPENS_MAX_CODONS", "100001"), ("SHIFT_HAPPENS_MAX_FILE_MIB", "invalid")])
def test_invalid_configuration_fails_at_startup(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_request_limit_health_and_privacy():
    settings = Settings(True, 5, 10, 10000)
    app = create_app(settings)
    client = app.server.test_client()
    assert client.get("/healthz").get_json() == {"status": "ok"}
    layout = client.get("/_dash-layout")
    assert "Uploads are sent to this hosted server" in layout.get_data(as_text=True)
    assert "Runs on your computer" not in layout.get_data(as_text=True)
    assert layout.headers["Cache-Control"] == "no-store"
    assert layout.headers["X-Content-Type-Options"] == "nosniff"
    assert app.server.config["MAX_CONTENT_LENGTH"] == settings.max_request_bytes
    app.server.config["MAX_CONTENT_LENGTH"] = 32
    assert client.post("/_dash-update-component", data="x" * 100, content_type="application/json").status_code == 413


def test_hosted_limits_reject_without_replacing_workspace():
    raw = (ROOT / "fixtures/CD2.FEL.json").read_text()
    with pytest.raises(ValueError, match="100 codons"):
        parse_hyphy(raw, max_codons=100)
    oversized = "data:application/json;base64," + base64.b64encode(b" " * (1024 * 1024 + 1)).decode()
    original = initial_workspace()
    updated, selected, notice = import_files(original, [oversized], ["large.json"], Settings(True, 1, 2, 10000))
    assert updated == original and selected is None and "1 MiB" in notice


def test_production_wsgi_entrypoint():
    from wsgi import server
    assert server.test_client().get("/healthz").status_code == 200
    assert not server.debug


def test_blueprint_and_gunicorn_contract(monkeypatch):
    requirements = (ROOT / "requirements.txt").read_text().splitlines()
    assert "gunicorn==23.0.0" in requirements
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
    service, = blueprint["services"]
    assert service["type"] == "web" and service["runtime"] == "python"
    assert service["plan"] == "free" and service["autoDeployTrigger"] == "off"
    assert service["healthCheckPath"] == "/healthz"
    assert service["startCommand"] == "gunicorn --config gunicorn.conf.py wsgi:server"
    assert "requirements-render.txt" in service["buildCommand"]
    for item in service["envVars"]:
        monkeypatch.setenv(item["key"], item["value"])
    assert Settings.from_env() == Settings(True, 5, 10, 10000)
    monkeypatch.setenv("PORT", "12345")
    config = runpy.run_path(str(ROOT / "gunicorn.conf.py"))
    assert config["bind"] == "0.0.0.0:12345" and config["workers"] == 1
    assert config["threads"] == 2 and config["timeout"] == 120
