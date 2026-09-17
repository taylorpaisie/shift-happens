# Hosting Shift Happens on Render

This is a **Python Web Service**, not a Static Site. Dash needs Python callbacks. The repository is prepared for hosting; creating a service or clicking Deploy will publish it, and neither action has been performed here.

## Blueprint setup

1. Make the reviewed commit available on GitHub. The current implementation branch is `feat/validated-hyphy-viewer`; push that branch or merge it into your intended deployment branch first. A private repository can stay private if the Render GitHub connection has access.
2. In Render, choose **New → Blueprint**, connect this repository, and select the branch containing `render.yaml` and the Dash code. Use `render.yaml` at the repository root.
3. Review the generated `shift-happens` **Web Service**. The Blueprint selects the **Free** preview compute plan, Python runtime, hosted privacy wording, and smaller dataset limits. There are no databases, disks, secrets, or other services to provision.
4. When ready to publish, apply the Blueprint. The service builds dependencies and starts Gunicorn. Initial service creation deploys the app; `autoDeployTrigger: "off"` disables subsequent automatic commit-triggered deploys, not the initial creation.
5. Open the supplied `https://…onrender.com` address. `/healthz` should return `{"status":"ok"}`. Verify the hosted-processing notice, the synthetic example, and an official CD2 fixture upload.

Because the service uses the same repository as the Blueprint, omitting `branch` makes it use the branch selected for that Blueprint. Subsequent releases can be triggered manually in Render. See the official [Blueprint specification](https://render.com/docs/blueprint-spec).

## Manual Web Service setup

If you prefer not to use a Blueprint, use these exact settings:

| Setting | Value |
| --- | --- |
| Service type | Web Service |
| Runtime | Python 3 |
| Repository branch | Branch containing this implementation |
| Root directory | Repository root (leave blank) |
| Build command | `python -m pip install -r requirements-render.txt` |
| Start command | `gunicorn --config gunicorn.conf.py wsgi:server` |
| Health check | `/healthz` |
| Compute plan | Free for preview |
| Auto-deploy | Off |

Add environment variables:

```text
SHIFT_HAPPENS_HOSTED=true
SHIFT_HAPPENS_MAX_FILE_MIB=5
SHIFT_HAPPENS_MAX_WORKSPACE_MIB=10
SHIFT_HAPPENS_MAX_CODONS=10000
PYTHONUNBUFFERED=1
```

Render provides `PORT`; do not hard-code it. Gunicorn binds to `0.0.0.0:$PORT` using the Python configuration file. `.python-version` requests the latest available Python **3.11** patch release; the local tests used Python 3.11.9. See Render's [Flask deployment guide](https://render.com/docs/deploy-flask), [Python version configuration](https://render.com/docs/python-version), and [health checks](https://render.com/docs/health-checks).

## Processing, privacy, and persistence

Hosted uploads are transmitted to Render and processed in the application server's memory. The UI states this before upload. Each browser keeps its own source files in a memory-only Dash Store and sends them with callbacks. The application writes no uploaded files to disk, has no database, and does not retain datasets in shared worker globals. Reloading clears the browser workspace; it is not a project archive or a secure-erasure guarantee. Infrastructure access/error logs are controlled by the host; the application does not deliberately log upload contents, and Gunicorn access logging is disabled.

There is no authentication or user account system. The service is a public preview interface; use local mode for data that is not approved for hosted processing. Source-specific callback responses and initial layouts use `Cache-Control: no-store`. No secret or persistent disk is required by this implementation.

Render Free web services are intended for previews and spin down after 15 minutes without inbound traffic; the next visit can take about a minute to start. Filesystems are ephemeral. Free compute does not eliminate bandwidth/build usage limits. Review the official [Free service limitations](https://render.com/docs/free) when choosing a plan.

## Resource limits and operation

The Blueprint defaults to one Gunicorn worker with two threads, a 120-second timeout, and periodic worker recycling. Callback state belongs to the browser, so recycling does not intentionally discard a shared project cache. Dataset limits are conservative starting values, not a measured concurrency or memory guarantee for Render's small instance. The browser sends workspace text with callbacks; keep preview datasets small. There is no large-file streaming, worker queue, or load benchmark yet.

Local defaults remain 25 MiB/file, 50 MiB/workspace and 100,000 codons; hosted defaults are 5 MiB/file, 10 MiB/workspace and 10,000 codons. Both modes allow at most 20 analysis files. Limits are validated at startup and during import, and the UI reports the configured values. Native linking, supported method versions, correction handling, and partition rejection are unchanged by hosting.

## Verification and troubleshooting

```sh
python -m pip install -r requirements-dev.txt -r requirements-render.txt
python -m pytest -q tests/test_python.py tests/test_hosting.py
# Linux only:
python -m gunicorn --check-config --config gunicorn.conf.py wsgi:server
python scripts/gunicorn_smoke.py
```

The production smoke script starts Gunicorn on an unused local port, checks health/hosted layout, and submits a real Dash callback. It is configured in Linux CI. Windows cannot run Gunicorn natively; use `python app.py` and `python scripts/dash_smoke.py` there.

- **Directory listing or no callbacks:** the service was configured as a static site or started with `http.server`; use the Web Service settings above.
- **Missing `server` attribute:** use `wsgi:server`, not `app:server` or `app:app`.
- **No open port detected:** keep the provided Gunicorn config and Render's `PORT` variable.
- **Missing code or requirements:** select the branch containing this increment; local commits are not available to Render until pushed.
- **Upload rejected:** the UI reports the instance limits and adapter error. Oversized HTTP requests beyond the transport allowance receive HTTP 413; retry with fewer/smaller files. Partitioned or unsupported method-version files need adapter work, not a larger server.

No Render account, live build, remote CI run, or production concurrency test was exercised as part of local preparation. See [validation.md](validation.md) for the local evidence.
