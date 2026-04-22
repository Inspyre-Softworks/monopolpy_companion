from __future__ import annotations

import logging
from pathlib import Path

import yaml

from monopolpy_companion.lib.common.paths import (
    DEFAULT_CONFIG_FILE,
    PLAYER_DB_FILE,
    USER_CONFIG_FILE,
    ensure_runtime_dirs,
)


logger = logging.getLogger("MonopolpyCompanion." + __name__)


class Config:
    """Configuration handler for the application."""

    def __init__(self, file: str | Path | None = None):
        ensure_runtime_dirs()
        self.source_file = Path(file).expanduser() if file is not None else USER_CONFIG_FILE
        self.data = self.load(file)

    def load(self, file: str | Path | None = None):
        """Load configuration data from *file* or the user/default config chain."""
        source_file = Path(file).expanduser() if file is not None else self.source_file
        base_data = {}

        if DEFAULT_CONFIG_FILE.exists():
            with DEFAULT_CONFIG_FILE.open(encoding="utf-8") as handle:
                base_data = yaml.safe_load(handle) or {}

        if source_file.exists() and source_file != DEFAULT_CONFIG_FILE:
            with source_file.open(encoding="utf-8") as handle:
                user_data = yaml.safe_load(handle) or {}
            base_data = _deep_merge(base_data, user_data)

        gui_settings = base_data.setdefault("gui_settings", {})
        gui_settings.setdefault("grab_anywhere", False)
        base_data.setdefault("player_database", str(PLAYER_DB_FILE))
        base_data["player_database"] = str(Path(base_data["player_database"]).expanduser())

        return base_data

    def write(self, file: str | Path | None = None):
        """Write configuration data to *file* or the user config path."""
        ensure_runtime_dirs()
        output_file = Path(file).expanduser() if file is not None else self.source_file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as outfile:
            yaml.safe_dump(self.data, outfile, default_flow_style=False, sort_keys=False)
        self.source_file = output_file


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
