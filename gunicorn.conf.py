"""Small-instance Render defaults; source data is never kept in worker globals."""
import os

bind = "0.0.0.0:" + os.getenv("PORT", "8050")
workers = 1
worker_class = "gthread"
threads = 2
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 500
max_requests_jitter = 50
errorlog = "-"
# Do not add request bodies, uploaded metadata, or query strings to app logs.
accesslog = None
