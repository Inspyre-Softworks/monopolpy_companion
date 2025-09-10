"""Utility helpers for working with the player database path.

This module previously relied on ``lib.common.setup_env`` which no longer
exists. The database path is now loaded from the project's YAML
configuration file.
"""

import os
from pathlib import Path

import yaml


_CONFIG_PATH = Path(__file__).resolve().parents[3] / "conf" / "default.yml"
with _CONFIG_PATH.open() as fh:
    _CONFIG = yaml.safe_load(fh)

db_path = os.path.expanduser(_CONFIG.get("player_database"))

def check_for(path: str | None = None) -> bool:
    """Determine whether a filesystem path exists.

    Parameters
    ----------
    path:
        A specific path to check.  When ``None`` (the default), the function
        uses the ``player_database`` path loaded from the configuration file.

    Returns
    -------
    bool
        ``True`` if the path exists, otherwise ``False``.
    """

    target = os.path.abspath(os.path.expanduser(path or db_path))
    return os.path.exists(target)
