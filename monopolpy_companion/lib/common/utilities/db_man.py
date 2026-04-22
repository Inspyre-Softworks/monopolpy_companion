"""Utility helpers for working with the configured player database path."""

from __future__ import annotations

from pathlib import Path

from monopolpy_companion.lib.common.paths import PLAYER_DB_FILE
from monopolpy_companion.lib.common.settings import Config


def configured_player_database_path() -> Path:
    """Return the player database path from config, falling back to the default path."""

    config = Config().data
    configured_path = config.get("player_database")
    if configured_path:
        return Path(configured_path).expanduser()
    return PLAYER_DB_FILE


def check_for(path: str | None = None) -> bool:
    """Determine whether the target path exists.

    When *path* is omitted, the configured player database location is used.
    """

    target = Path(path).expanduser() if path else configured_player_database_path()
    return target.exists()
