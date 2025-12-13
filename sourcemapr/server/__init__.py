"""
SourcemapR Server - FastAPI-based observability dashboard and API.
"""

from sourcemapr.server.app import app, run_server

__all__ = ['app', 'run_server']
