"""API-nyckelskydd för admin- och scenario-endpoints.

Sätt ADMIN_API_KEY i .env. Skicka nyckeln som header:
  X-Api-Key: <din-nyckel>

Om ADMIN_API_KEY inte är satt körs servern utan skydd (lämpligt för lokal dev).
"""
import os
import functools
from flask import request, jsonify

_KEY = os.environ.get("ADMIN_API_KEY", "")


def require_api_key(f):
    """Dekorator som kräver giltig X-Api-Key om ADMIN_API_KEY är satt."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if _KEY and request.headers.get("X-Api-Key") != _KEY:
            return jsonify({"error": "Ogiltig eller saknad API-nyckel"}), 401
        return f(*args, **kwargs)
    return wrapper


def check_api_key():
    """Används som before_request-hook i blueprints."""
    if _KEY and request.headers.get("X-Api-Key") != _KEY:
        return jsonify({"error": "Ogiltig eller saknad API-nyckel"}), 401
