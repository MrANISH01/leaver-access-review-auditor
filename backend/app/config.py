"""Environment-driven configuration. Nothing here is a secret; there is no auth in the MVP."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from flask import current_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
DEFAULT_DB_PATH = PROJECT_ROOT / "instance" / "auditor.sqlite3"

SUPPORTED_CONNECTORS = ("synthetic", "mock_admin")
SUPPORTED_HR_SOURCES = ("synthetic",)
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")

# Actor labels (X-Actor / APPROVER_ACTORS entries): letters, digits and . _ @ + - only.
ACTOR_RE = re.compile(r"^[A-Za-z0-9._@+\-]{1,100}$")

# scheme://host[:port] only: no wildcard, no path, no trailing slash.
_ORIGIN_RE = re.compile(r"^https?://[^/*\s]+$")


class ConfigError(Exception):
    """Raised for invalid or unsafe configuration. Fails startup loudly."""


def _env_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    database_path: str = str(DEFAULT_DB_PATH)
    connector: str = "synthetic"          # CONNECTOR=synthetic|mock_admin
    hr_source: str = "synthetic"          # HR_SOURCE=synthetic
    demo_mode: bool = False               # DEMO_MODE=1 enables /dev/* endpoints
    frontend_origins: tuple[str, ...] = ()  # FRONTEND_ORIGIN=http://localhost:5173 (empty = no CORS)
    synthetic_data_dir: str = str(DEFAULT_DATA_DIR)
    approver_actors: tuple[str, ...] = ()   # APPROVER_ACTORS=a@x.com,b@x.com (empty = nobody can approve)

    def is_approver(self, actor: str) -> bool:
        """Case-insensitive allowlist check. Fails closed: an empty allowlist approves nobody."""
        return (actor or "").strip().lower() in {a.lower() for a in self.approver_actors}

    @classmethod
    def from_env(cls, env=None) -> "Config":
        env = os.environ if env is None else env
        origins = tuple(
            o.strip().rstrip("/")
            for o in (env.get("FRONTEND_ORIGIN") or "").split(",")
            if o.strip()
        )
        approvers = tuple(dict.fromkeys(
            a.strip().lower() for a in (env.get("APPROVER_ACTORS") or "").split(",") if a.strip()))
        return cls(
            database_path=env.get("DATABASE_PATH") or str(DEFAULT_DB_PATH),
            connector=(env.get("CONNECTOR") or "synthetic").strip().lower(),
            hr_source=(env.get("HR_SOURCE") or "synthetic").strip().lower(),
            demo_mode=_env_bool(env.get("DEMO_MODE")),
            frontend_origins=origins,
            synthetic_data_dir=env.get("SYNTHETIC_DATA_DIR") or str(DEFAULT_DATA_DIR),
            approver_actors=approvers,
        )

    def validate(self) -> "Config":
        if self.connector not in SUPPORTED_CONNECTORS:
            raise ConfigError(f"CONNECTOR must be one of {SUPPORTED_CONNECTORS}, got {self.connector!r}")
        if self.hr_source not in SUPPORTED_HR_SOURCES:
            raise ConfigError(f"HR_SOURCE must be one of {SUPPORTED_HR_SOURCES}, got {self.hr_source!r}")
        for origin in self.frontend_origins:
            if not _ORIGIN_RE.match(origin):
                raise ConfigError(
                    f"FRONTEND_ORIGIN entry {origin!r} is invalid. Use an exact origin such as "
                    "http://localhost:5173 (no wildcard, path or trailing slash)."
                )
        for actor in self.approver_actors:
            if not ACTOR_RE.match(actor):
                raise ConfigError(
                    f"APPROVER_ACTORS entry {actor!r} is invalid. Use explicit identities such as "
                    "approver@acme.example (letters, digits and . _ @ + - only; no wildcards).")
        return self


def validate_bind_host(host: str, demo_mode: bool, allow_lan: bool) -> None:
    """Demo mode exposes reset/fault-injection endpoints with no real auth: keep it on loopback."""
    if demo_mode and host not in LOOPBACK_HOSTS and not allow_lan:
        raise ConfigError(
            f"Refusing to bind {host!r} with DEMO_MODE=1: demo endpoints have no real authentication. "
            "Use HOST=127.0.0.1, or set ALLOW_LAN_DEMO=1 only on a trusted private network."
        )


def current_config() -> Config:
    return current_app.config["AUDITOR"]
