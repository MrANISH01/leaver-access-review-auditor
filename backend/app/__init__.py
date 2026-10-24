"""Leaver Access Review Auditor: backend."""
from __future__ import annotations

from flask import Flask

__version__ = "0.1.0"


def create_app(config=None) -> Flask:
    from . import db
    from .api import register_blueprints
    from .config import Config
    from .connectors.factory import build_connector, build_hr_source
    from .cors import init_cors
    from .errors import register_error_handlers
    from .services.seed import seed_exclusions_if_empty

    config = (config or Config.from_env()).validate()
    app = Flask(__name__)
    app.config["AUDITOR"] = config
    app.extensions["connector"] = build_connector(config)   # SaaSConnector (replaceable)
    app.extensions["hr_source"] = build_hr_source(config)   # HRSource (replaceable)
    db.init_app(app, config.database_path)
    seed_exclusions_if_empty(config)
    register_error_handlers(app)
    init_cors(app, config.frontend_origins)
    register_blueprints(app, config)
    return app
