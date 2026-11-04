"""GUI-independent, atomic JSON session persistence."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from monopolpy_companion.lib.common.paths import SAVE_DIR

from .models import GameSession
from .storage import SavedSessionInfo, slugify


class SessionRepository:
    """Read and write Monopoly games without coupling to any user interface.

    Args:
        directory: Save directory, defaulting to the established user save path.

    Notes:
        Writes use atomic replacement to avoid truncating previous saves.
        JSON stays compatible with the original GameSession storage format.
    """

    def __init__(self, directory: str | Path | None = None) -> None:
        self.directory = Path(directory).expanduser() if directory is not None else SAVE_DIR

    def save(self, session: GameSession, path: str | Path | None = None) -> Path:
        """Save a session atomically and update its save_path on success."""
        destination = Path(path).expanduser() if path is not None else (
            self.directory / f'{slugify(session.name)}-{session.session_id[:8]}.json'
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=destination.parent,
                prefix=f'.{destination.name}.', suffix='.tmp', delete=False
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(session.to_dict(), handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, destination)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        session.save_path = str(destination)
        return destination

    def load(self, path: str | Path) -> GameSession:
        """Load a save, raising for missing, invalid or corrupt JSON."""
        source = Path(path).expanduser()
        with source.open('r', encoding='utf-8') as handle:
            session = GameSession.from_dict(json.load(handle))
        session.save_path = str(source)
        return session

    def list_sessions(self) -> list[SavedSessionInfo]:
        """List readable saves newest first, skipping malformed files."""
        if not self.directory.is_dir():
            return []
        sessions: list[SavedSessionInfo] = []
        for path in sorted(self.directory.glob('*.json'),
                           key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                with path.open('r', encoding='utf-8') as handle:
                    data = json.load(handle)
                if not isinstance(data, dict) or not isinstance(data.get('name'), str):
                    continue
            except (OSError, ValueError):
                continue
            sessions.append(SavedSessionInfo(path=path, display_name=data['name']))
        return sessions
