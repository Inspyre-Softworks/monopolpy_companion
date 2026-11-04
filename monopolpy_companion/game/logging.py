"""Lazy InspyLogger configuration for the game library."""

from __future__ import annotations

from typing import Any


def get_game_logger(name: str = 'MonopolPyCompanion.Game', level: str = 'warning') -> Any:
    """Return an InspyLogger 3.x device, with file logging disabled.

    Args:
        name: Name of the hierarchical logging device.
        level: Console logging level.

    Returns:
        An InspyLogger object implementing standard logging methods.

    Notes:
        Instantiating the engine is the earliest this dependency is imported;
        importing model classes never starts logging. Consumers can supply
        their own logger to GameEngine to configure file output.
    """
    from inspy_logger import InspyLogger

    return InspyLogger(name, console_level=level, no_file_logging=True)
