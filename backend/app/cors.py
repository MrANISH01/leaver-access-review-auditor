"""CORS restricted to explicitly configured origins. No origins configured = no CORS headers at all."""
from __future__ import annotations

from flask import Flask, request


def init_cors(app: Flask, allowed_origins: tuple[str, ...]) -> None:
    allowed = frozenset(allowed_origins)

    @app.after_request
    def _apply_cors(response):
        origin = request.headers.get("Origin")
        if origin and origin in allowed:
            response.headers["Access-Control-Allow-Origin"] = origin  # echo exact origin, never "*"
            response.headers.add("Vary", "Origin")
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Actor"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Max-Age"] = "600"
        return response
