"""Production WSGI entry point: gunicorn --config gunicorn.conf.py wsgi:server."""
from app import create_app

server = create_app().server
