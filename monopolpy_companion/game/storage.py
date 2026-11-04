"""Legacy persistence facade, retained for existing integrations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from monopolpy_companion.lib.common.paths import SAVE_DIR

from .models import GameSession


@dataclass(frozen=True)
class SavedSessionInfo:
    """Location and friendly title of a saved Monopoly session."""

    path: Path
    display_name: str


def slugify(value: str) -> str:
    """Convert a session title into a filename-safe slug."""
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '-', value.strip().lower()).strip('-')
    return cleaned or 'session'


def default_session_path(session: GameSession) -> Path:
    """Return the established default save path for a session."""
    return SAVE_DIR / f'{slugify(session.name)}-{session.session_id[:8]}.json'


def save_session(session: GameSession, path: str | Path | None = None) -> Path:
    """Save through the atomic SessionRepository implementation."""
    from .repository import SessionRepository

    return SessionRepository().save(session, path)


def load_session(path: str | Path) -> GameSession:
    """Load a session in the established JSON schema."""
    from .repository import SessionRepository

    return SessionRepository().load(path)


def list_saved_sessions(directory: str | Path | None = None) -> list[SavedSessionInfo]:
    """Enumerate readable saves, newest first."""
    from .repository import SessionRepository

    return SessionRepository(directory).list_sessions()
