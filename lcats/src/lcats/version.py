"""LCATS package version helpers."""

from __future__ import annotations

import importlib.metadata

DISTRIBUTION_NAME = "lcats"
CLI_NAME = "lcats"


def get_installed_version() -> str | None:
    """Return installed package version for LCATS, or None if unavailable."""
    try:
        return importlib.metadata.version(DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError:
        return None


def format_cli_version() -> str:
    """Return CLI-friendly LCATS version text."""
    version = get_installed_version()
    if version is None:
        return f"{CLI_NAME} unknown"
    return f"{CLI_NAME} {version}"
