"""Run the real Chromium app and browser-native module suite using CDP.
Dev-only prerequisite: python -m pip install websocket-client
Usage: python scripts/browser_smoke.py [--browser /path/to/chrome]
No analysis files are sent to a remote service.
"""
import argparse
import base64
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
import websocket

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / '.artifacts'

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser')
    args = parser.parse_args()
    browser = args.browser or shutil.which('google-chrome') or shutil.which('chromium')
    if not browser:
        browser = next((p for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe', r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'] if Path(p).exists()), None)
    if not browser:
        raise SystemExit('No Chromium browser found. Supply --browser PATH.')
    ARTIFACTS.mkdir(exist_ok=True)
    downloads = ARTIFACTS / ('downloads-' + str(time.time_ns()))
    downloads.mkdir()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    with tempfile.TemporaryDirectory(prefix='shift-happens-browser-') as profile:
        proc = subprocess.Popen([browser, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', f'--user-data-dir={profile}', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        ws = None
        try:
            port_file = Path(profile) / 'DevToolsActivePort'
            for _ in range(200):
                if port_file.exists(): break
                time.sleep(.05)
            port = port_file.read_text().splitlines()[0]
            pages = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
            ws = websocket.create_connection(next(p['webSocketDebuggerUrl'] for p in pages if p['type'] == 'page'), suppress_origin=True, timeout=30)
            seq = 0
            errors = []
            def call(method, params=None):
                nonlocal seq
                seq += 1
                ws.send(json.dumps({'id': seq, 'method': method, 'params': params or {}}))
                while True:
                    result = json.loads(ws.recv())
                    if result.get('method') == 'Runtime.exceptionThrown': errors.append(result)
                    if result.get('id') == seq:
                        if 'error' in result: raise RuntimeError(result['error'])
                        return result.get('result', {})
            def evaluate(expression):
                r = call('Runtime.evaluate', {'expression': expression, 'awaitPromise': True, 'returnByValue': True})
                if 'exceptionDetails' in r: raise AssertionError(r['exceptionDetails'])
                return r.get('result', {}).get('value')
            def until(expression):
                for _ in range(150):
                    if evaluate(expression): return
                    time.sleep(.05)
                raise AssertionError('Timed out: ' + expression)
            call('Runtime.enable')
            call('Page.enable')
            call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1100,'deviceScaleFactor':1,'mobile':False})
            call('Page.navigate', {'url': base + '/tests/index.html'})
            until('Array.isArray(window.testResults)')
            results = evaluate('window.testResults')
            print(json.dumps(results, indent=2))
            assert all(r['ok'] for r in results), 'Module regression suite failed'
            call('Page.navigate', {'url': base + '/'})
            until('document.querySelectorAll(".track").length === 3')
            assert evaluate('document.getElementById("context").textContent.includes("SYNTHETIC")')
            evaluate('document.querySelector(\'[data-method="FEL"][data-codon="14"]\').click()')
            assert evaluate('document.querySelectorAll(".codon.selected").length === 3')
            assert evaluate('document.getElementById("inspector-title").textContent === "Codon 14"')
            evaluate('document.querySelector(".codon.selected").dispatchEvent(new KeyboardEvent("keydown", {key:"ArrowRight",bubbles:true}))')
            assert evaluate('document.getElementById("inspector-title").textContent === "Codon 15"')
            call('Browser.setDownloadBehavior', {'behavior':'allow','downloadPath':str(downloads)})
            evaluate('document.getElementById("csv").click();document.getElementById("svg").click()')
            for name in ['shift-happens-SYNTHETIC.csv', 'shift-happens-SYNTHETIC.svg']:
                for _ in range(100):
                    if (downloads / name).exists(): break
                    time.sleep(.05)
                assert (downloads / name).exists(), 'Missing export ' + name
            ET.parse(downloads / 'shift-happens-SYNTHETIC.svg')
            assert len((downloads / 'shift-happens-SYNTHETIC.csv').read_text(encoding='utf8').splitlines()) == 217
            screenshot = call('Page.captureScreenshot', {'format':'png','captureBeyondViewport':True})
            (ARTIFACTS / 'desktop.png').write_bytes(base64.b64decode(screenshot['data']))
            doc = call('DOM.getDocument')
            node = call('DOM.querySelector', {'nodeId':doc['root']['nodeId'], 'selector':'#upload'})['nodeId']
            call('DOM.setFileInputFiles', {'nodeId':node,'files':[str(ROOT/'fixtures/CD2.FEL.json'),str(ROOT/'fixtures/CD2.MEME.json')]})
            until('document.querySelectorAll(".file-card").length === 5')
            assert evaluate('document.querySelectorAll(".track").length === 1')
            assert evaluate('document.getElementById("context").textContent.includes("cross-file linking is disabled")')
            evaluate('document.querySelector(\'[data-method="MEME"][data-codon="43"]\').click()')
            assert evaluate('document.getElementById("inspection").textContent.includes("6.801478770233565")')
            evaluate('document.getElementById("threshold").value="0.01";document.getElementById("threshold").dispatchEvent(new Event("change"))')
            assert evaluate('document.querySelector(\'[data-codon="43"]\').classList.contains("nonsignificant")')
            evaluate('document.getElementById("next").click()')
            assert evaluate('document.getElementById("range").textContent.includes("73–144")')
            # Import a malicious metadata string through the actual upload handler.
            evaluate('''(async()=>{const j=await (await fetch('/fixtures/CD2.FEL.json')).json();j.input['file name']='<img src=x onerror="window.metadataExecuted=true">';const dt=new DataTransfer();dt.items.add(new File([JSON.stringify(j)],'metadata-test.json',{type:'application/json'}));const u=document.getElementById('upload');u.files=dt.files;u.dispatchEvent(new Event('change'));})()''')
            until('document.querySelectorAll(".file-card").length === 6')
            assert evaluate('!window.metadataExecuted && document.querySelectorAll("#inspection img").length===0')
            doc = call('DOM.getDocument')
            node = call('DOM.querySelector', {'nodeId':doc['root']['nodeId'], 'selector':'#upload'})['nodeId']
            call('DOM.setFileInputFiles', {'nodeId':node,'files':[str(ROOT/'fixtures/partitioned.FEL.json')]})
            until('document.getElementById("message").textContent.includes("Recombination")')
            assert evaluate('document.querySelectorAll(".file-card").length === 6')
            evaluate('document.querySelector(".file-card:last-child .remove").click()')
            assert evaluate('document.querySelectorAll(".file-card").length === 5')
            call('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
            assert evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Page overflows narrow screen'
            (ARTIFACTS/'mobile.png').write_bytes(base64.b64decode(call('Page.captureScreenshot', {'format':'png','captureBeyondViewport':True})['data']))
            assert not errors, errors
            print(f'PASS: {len(results)} module tests; browser uploads, isolation, linked demo, keyboard navigation, thresholds, pagination, metadata safety, rejection, removal, CSV/SVG downloads and mobile layout.')
        finally:
            if ws: ws.close()
            proc.terminate()
            proc.wait(timeout=10)
            server.shutdown()

if __name__ == '__main__':
    main()
