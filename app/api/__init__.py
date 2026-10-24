from __future__ import annotations

from flask import Flask

from ..config import Config

API_PREFIX = "/api/v1"


def register_blueprints(app: Flask, config: Config) -> None:
    from . import audit, deprovision_requests, findings, health, scans, session, summary

    for module in (health, scans, findings, summary, deprovision_requests, audit, session):
        app.register_blueprint(module.bp, url_prefix=API_PREFIX)
    if config.demo_mode:  # not even registered (so a plain 404) unless DEMO_MODE=1
        from . import dev
        app.register_blueprint(dev.bp, url_prefix=f"{API_PREFIX}/dev")
