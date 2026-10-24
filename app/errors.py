"""Uniform error envelope: {"error": {"code": "...", "message": "..."}}."""
from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

_HTTP_CODES = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    415: "UNSUPPORTED_MEDIA_TYPE",
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details


def _envelope(code: str, message: str, status: int, details: dict | None = None):
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    response = jsonify({"error": error})
    response.status_code = status
    return response


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _api_error(exc: ApiError):
        return _envelope(exc.code, exc.message, exc.status, exc.details)

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        status = exc.code or 500
        response = _envelope(_HTTP_CODES.get(status, f"HTTP_{status}"), exc.description or exc.name, status)
        allowed = getattr(exc, "valid_methods", None)
        if allowed:
            response.headers["Allow"] = ", ".join(allowed)
        return response

    @app.errorhandler(Exception)
    def _unhandled(exc: Exception):
        app.logger.exception("Unhandled error")
        return _envelope("INTERNAL_ERROR", "Internal server error", 500)
