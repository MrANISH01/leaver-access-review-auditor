"""Run the API locally:  python run.py   (env vars: see README)."""
import os
import sys

from app import create_app
from app.config import Config, ConfigError, validate_bind_host, _env_bool


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5001"))
    try:
        config = Config.from_env()
        validate_bind_host(host, config.demo_mode, _env_bool(os.environ.get("ALLOW_LAN_DEMO")))
        app = create_app(config)
    except ConfigError as exc:
        sys.exit(f"Configuration error: {exc}")
    if not config.approver_actors:
        print("WARNING: APPROVER_ACTORS is empty, so every approve/reject will be refused. "
              "Set e.g. APPROVER_ACTORS=approver@acme.example")
    print(f"approvers={len(config.approver_actors)} connector={config.connector} demo_mode={config.demo_mode} "
          f"cors_origins={list(config.frontend_origins) or 'none'} db={config.database_path}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
