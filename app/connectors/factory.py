from __future__ import annotations

from pathlib import Path

from ..config import Config, ConfigError
from .base import HRSource, SaaSConnector
from .synthetic import SyntheticConnector, SyntheticHRSource


def build_hr_source(config: Config) -> HRSource:
    if config.hr_source == "synthetic":
        return SyntheticHRSource(Path(config.synthetic_data_dir) / "employees.json")
    raise ConfigError(f"Unsupported HR_SOURCE {config.hr_source!r}")


def build_connector(config: Config) -> SaaSConnector:
    if config.connector == "synthetic":
        return SyntheticConnector(Path(config.synthetic_data_dir) / "accounts.json")
    if config.connector == "mock_admin":
        raise ConfigError(
            "CONNECTOR=mock_admin is not implemented yet. Add app/connectors/mock_admin.py "
            "(a SaaSConnector subclass) and register it here once the official console details exist."
        )
    raise ConfigError(f"Unsupported CONNECTOR {config.connector!r}")
