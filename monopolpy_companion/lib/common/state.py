from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AppState:
    current_session: Optional["GameSession"] = None


app_state = AppState()


def set_current_session(session: "GameSession") -> None:
    app_state.current_session = session


def get_current_session() -> Optional["GameSession"]:
    return app_state.current_session


def clear_current_session() -> None:
    app_state.current_session = None


if False:
    from monopolpy_companion.game.models import GameSession
