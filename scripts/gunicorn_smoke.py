"""Linux CI smoke test of the actual Render WSGI server and Dash callback."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    if os.name == "nt":
        raise SystemExit("Gunicorn requires Unix. Run this check in Linux CI; use dash_smoke.py on Windows.")
    from app import create_app
    from shift_happens.config import Settings
    from shift_happens.workspace import initial_workspace

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = {**os.environ, "PORT": str(port), "SHIFT_HAPPENS_HOSTED": "true"}
    proc = subprocess.Popen([sys.executable, "-m", "gunicorn", "--config", "gunicorn.conf.py", "wsgi:server"], cwd=ROOT, env=env)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(200):
            if proc.poll() is not None:
                raise AssertionError("Gunicorn exited before becoming healthy")
            try:
                with urllib.request.urlopen(base + "/healthz", timeout=1) as response:
                    assert json.load(response) == {"status": "ok"}
                break
            except (OSError, urllib.error.URLError):
                time.sleep(.1)
        else:
            raise AssertionError("Gunicorn health check timed out")
        with urllib.request.urlopen(base + "/_dash-layout") as response:
            assert "hosted server" in response.read().decode()
            assert response.headers["Cache-Control"] == "no-store"
        app = create_app(Settings(True, 5, 10, 10000))
        key = next(key for key in app.callback_map if "tracks.figure" in key)
        callback = app.callback_map[key]
        values = {"workspace": initial_workspace(), "active": "demo", "threshold": .05, "window": 72, "start": 1, "codon": 14,
                  "tracks": None, "previous": 0, "next": 0}
        payload = {"output": key, "outputs": [{"id": o.component_id, "property": o.component_property} for o in callback["output"]],
                   "inputs": [{**item, "value": values[item["id"]]} for item in callback["inputs"]], "state": [], "changedPropIds": ["codon.value"]}
        request = urllib.request.Request(base + "/_dash-update-component", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)["response"]
        assert result["inspector-title"]["children"] == "Codon 14"
        assert len(result["tracks"]["figure"]["data"]) == 3
        print("PASS: production Gunicorn health, hosted layout, no-store headers and real Dash callback")
    finally:
        proc.terminate()
        proc.wait(timeout=35)


if __name__ == "__main__":
    main()
