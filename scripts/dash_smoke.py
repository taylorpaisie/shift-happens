"""Actual Dash/Chromium integration test. Requires requirements-dev.txt."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
import websocket
from werkzeug.serving import make_server, WSGIRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app  # noqa: E402


class QuietHandler(WSGIRequestHandler):
    def log(self, *_args, **_kwargs):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser")
    args = parser.parse_args()
    browser = args.browser or shutil.which("google-chrome") or shutil.which("chromium")
    if not browser:
        browser = next((p for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"] if Path(p).exists()), None)
    if not browser:
        raise SystemExit("No Chromium browser found; supply --browser PATH.")
    artifacts = ROOT / ".artifacts" / ("dash-" + str(time.time_ns()))
    artifacts.mkdir(parents=True)
    server = make_server("127.0.0.1", 0, create_app().server, threaded=True, request_handler=QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    with tempfile.TemporaryDirectory(prefix="shift-happens-dash-") as profile:
        proc = subprocess.Popen([browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        ws = None
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            port = None
            for _ in range(200):
                try:
                    # Windows can observe the file before Chrome releases its write lock.
                    lines = port_file.read_text().splitlines()
                    if len(lines) >= 2 and lines[0].isdigit():
                        port = lines[0]
                        break
                except OSError:
                    pass
                time.sleep(.05)
            if port is None:
                raise RuntimeError("Chrome did not publish a readable debugging port within 10 seconds.")
            pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
            ws = websocket.create_connection(next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page"), suppress_origin=True, timeout=30)
            seq, errors, requests = 0, [], []

            def call(method, params=None):
                nonlocal seq
                seq += 1
                ws.send(json.dumps(dict(id=seq, method=method, params=params or {})))
                while True:
                    result = json.loads(ws.recv())
                    if result.get("method") == "Runtime.exceptionThrown":
                        errors.append(result)
                    if result.get("method") == "Network.requestWillBeSent":
                        requests.append(result["params"]["request"]["url"])
                    if result.get("id") == seq:
                        if "error" in result:
                            raise RuntimeError(result["error"])
                        return result.get("result", {})

            def evaluate(expression):
                result = call("Runtime.evaluate", dict(expression=expression, awaitPromise=True, returnByValue=True))
                if "exceptionDetails" in result:
                    raise AssertionError(result["exceptionDetails"])
                return result.get("result", {}).get("value")

            def until(expression):
                for _ in range(250):
                    if evaluate(expression):
                        return
                    time.sleep(.05)
                raise AssertionError("Timed out: " + expression + "\n" + str(evaluate("document.body.innerText"))[:3000])

            def files(paths):
                doc = call("DOM.getDocument")
                node = call("DOM.querySelector", dict(nodeId=doc["root"]["nodeId"], selector='#upload input[type="file"]'))["nodeId"]
                call("DOM.setFileInputFiles", dict(nodeId=node, files=[str(path) for path in paths]))

            def download(name):
                path = artifacts / name
                for _ in range(150):
                    if path.exists():
                        return path
                    time.sleep(.05)
                raise AssertionError("Missing download " + name)

            def click_bar(index):
                position = evaluate(f"(()=>{{const r=document.querySelectorAll('#tracks .barlayer .trace.bars')[0].querySelectorAll('.point path')[{index}].getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}};}})()")
                for action in ("mousePressed", "mouseReleased"):
                    call("Input.dispatchMouseEvent", dict(type=action, button="left", clickCount=1, **position))

            def click_selector(selector):
                position = evaluate("(()=>{const r=document.querySelector(" + json.dumps(selector) + ").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()")
                for action in ("mousePressed", "mouseReleased"):
                    call("Input.dispatchMouseEvent", dict(type=action, button="left", clickCount=1, **position))

            def number(selector, value):
                click_selector(selector)
                call("Input.dispatchKeyEvent", dict(type="keyDown", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2))
                call("Input.dispatchKeyEvent", dict(type="keyUp", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2))
                call("Input.insertText", dict(text=str(value)))
                call("Input.dispatchKeyEvent", dict(type="keyDown", key="Enter", code="Enter", windowsVirtualKeyCode=13))
                call("Input.dispatchKeyEvent", dict(type="keyUp", key="Enter", code="Enter", windowsVirtualKeyCode=13))
                evaluate("document.querySelector(" + json.dumps(selector) + ").blur()")

            call("Runtime.enable")
            call("Network.enable")
            call("Page.enable")
            call("Emulation.setDeviceMetricsOverride", dict(width=1440, height=1100, deviceScaleFactor=1, mobile=False))
            call("Browser.setDownloadBehavior", dict(behavior="allow", downloadPath=str(artifacts)))
            call("Page.navigate", dict(url=base))
            until("document.querySelector('#tracks .js-plotly-plot')?.data?.length === 3")
            assert evaluate("document.getElementById('context').textContent.includes('SYNTHETIC')")
            click_bar(13)
            until("document.getElementById('inspector-title').textContent === 'Codon 14'")
            assert evaluate("document.querySelectorAll('.evidence-card').length === 3")
            evaluate("document.getElementById('csv').click()")
            assert len(download("shift-happens-SYNTHETIC.csv").read_text(encoding="utf8").splitlines()) == 217
            evaluate("document.getElementById('svg').click()")
            ET.parse(download("shift-happens-SYNTHETIC.svg"))
            assert evaluate("document.querySelector('.explorer').getBoundingClientRect().bottom <= document.querySelector('.inspector').getBoundingClientRect().top"), "Track panel overlaps inspector"
            assert evaluate("document.querySelector('#tracks .main-svg').getBoundingClientRect().bottom <= document.querySelector('.legend').getBoundingClientRect().top + 1"), "Chart overflows its container"
            (artifacts / "desktop.png").write_bytes(base64.b64decode(call("Page.captureScreenshot", dict(format="png", captureBeyondViewport=True))["data"]))
            def select_analysis(filename):
                evaluate("Array.from(document.querySelectorAll('#active label')).find(el => el.textContent.includes(" + json.dumps(filename) + ")).querySelector('input').click()")
                until("document.getElementById('context').textContent.includes(" + json.dumps(filename) + ") && document.querySelector('#tracks .js-plotly-plot').data.length === 1")

            files([ROOT / "fixtures/CD2.FEL.json", ROOT / "fixtures/CD2.MEME.json"])
            until("document.querySelectorAll('#active input').length === 3")
            select_analysis("CD2.MEME.json")
            assert evaluate("document.getElementById('message').textContent.includes('Imported 2')")
            click_bar(42)
            until("document.getElementById('inspector-title').textContent === 'Codon 43'")
            assert evaluate("document.getElementById('inspection').textContent.includes('6.801478770233565')")
            click_selector("#threshold .Select-control")
            until("document.querySelectorAll('.VirtualizedSelectOption').length === 3")
            click_selector(".VirtualizedSelectOption")
            until("document.querySelector('#tracks .js-plotly-plot').data[0].marker.color[42] === '#cbd2d9'")
            assert evaluate("document.getElementById('inspection').textContent.includes('Nonsignificant')")
            number("#codon", 76)
            until("document.getElementById('inspector-title').textContent === 'Codon 76'")
            assert evaluate("document.getElementById('inspection').textContent.includes('0.002491251281779738')")
            number("#start", 1)
            until("document.getElementById('range').textContent.includes('1–72')")
            evaluate("document.getElementById('original').click()")
            assert download("CD2.MEME.json").read_bytes() == (ROOT / "fixtures/CD2.MEME.json").read_bytes()
            evaluate("document.getElementById('next').click()")
            until("document.getElementById('range').textContent.includes('73–144')")
            evaluate("document.getElementById('previous').click()")
            until("document.getElementById('range').textContent.includes('1–72')")
            select_analysis("CD2.FEL.json")
            number("#codon", 31)
            until("document.getElementById('inspector-title').textContent === 'Codon 31'")
            assert evaluate("document.getElementById('inspection').textContent.includes('purifying')")
            select_analysis("CD2.MEME.json")
            files([ROOT / "fixtures/partitioned.FEL.json"])
            until("document.getElementById('message').textContent.includes('Recombination')")
            assert evaluate("document.getElementById('context').textContent.includes('CD2.MEME.json')")
            files([ROOT / "fixtures/lysin.MEME.json"])
            until("document.getElementById('context').textContent.includes('lysin.MEME.json')")
            click_bar(5)
            until("document.getElementById('inspector-title').textContent === 'Codon 6'")
            assert evaluate("document.getElementById('inspection').textContent.includes('23.81442994266141')")
            # Load a temporary fixture through the real upload control; rendered as text.
            # Datamonkey contract: official native CD2 output plus supplied PMID.
            raw = json.loads((ROOT / "fixtures/CD2.FEL.json").read_text())
            raw["input"]["file name"] = '<img src=x onerror="window.metadataExecuted=true">'
            raw["PMID"] = "22807683"
            upload_dir = artifacts / "upload-fixtures"
            upload_dir.mkdir()
            malicious = upload_dir / "datamonkey-results.json"
            malicious.write_text(json.dumps(raw), encoding="utf8")
            files([malicious])
            until("document.getElementById('context').textContent.includes('datamonkey-results.json')")
            assert evaluate("!window.metadataExecuted && document.querySelectorAll('#inspection img').length===0")
            assert evaluate("document.getElementById('inspection').textContent.includes('22807683')")
            evaluate("document.getElementById('original').click()")
            assert download("datamonkey-results.json").read_bytes() == malicious.read_bytes()
            evaluate("document.getElementById('csv').click()")
            assert '22807683' in download("shift-happens-evidence.csv").read_text(encoding="utf8")
            evaluate("document.getElementById('svg').click()")
            metadata = ET.parse(download("shift-happens-evidence.svg")).find(".//{http://www.w3.org/2000/svg}metadata")
            assert json.loads(metadata.text)["sources"][0]["publication_metadata"] == "22807683"
            evaluate("document.getElementById('remove').click()")
            until("document.getElementById('context').textContent.includes('SYNTHETIC')")
            # Every browser request, including Plotly and callbacks, must stay local.
            assert all(url.startswith((base, "data:", "blob:")) for url in requests), requests
            call("Emulation.setDeviceMetricsOverride", dict(width=390, height=844, deviceScaleFactor=1, mobile=True))
            time.sleep(.3)
            assert evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile page overflow"
            (artifacts / "mobile.png").write_bytes(base64.b64decode(call("Page.captureScreenshot", dict(format="png", captureBeyondViewport=True))["data"]))
            assert not errors, errors
            # Reload starts a fresh workspace, without uploaded source text.
            call("Page.reload")
            until("document.querySelector('#tracks .js-plotly-plot')?.data?.length === 3")
            assert evaluate("!document.getElementById('active').textContent.includes('CD2')")
            print("PASS: Dash renders; real Plotly clicks synchronize evidence; multi-file uploads including Datamonkey-contract JSON and official MEME 2.00, native isolation, pagination, invalid-file recovery, removal, CSV/SVG/original downloads, publication metadata, memory-only workspace and mobile layout work. All observed browser requests stayed local.")
            print("Artifacts:", artifacts)
        finally:
            if ws:
                ws.close()
            proc.terminate()
            proc.wait(timeout=10)
            server.shutdown()


if __name__ == "__main__":
    main()
