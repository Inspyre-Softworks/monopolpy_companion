from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from monopolpy_companion.lib.common.paths import SAVE_DIR, ensure_runtime_dirs

from .models import GameSession


@dataclass(frozen=True)
class SavedSessionInfo:
    path: Path
    display_name: str


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "session"


def default_session_path(session: GameSession) -> Path:
    ensure_runtime_dirs()
    return SAVE_DIR / f"{slugify(session.name)}-{session.session_id[:8]}.json"


def save_session(session: GameSession, path: str | Path | None = None) -> Path:
    ensure_runtime_dirs()
    output_path = Path(path) if path is not None else default_session_path(session)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
    session.save_path = str(output_path)
    return output_path


def load_session(path: str | Path) -> GameSession:
    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    session = GameSession.from_dict(data)
    session.save_path = str(input_path)
    return session


def list_saved_sessions(directory: str | Path | None = None) -> list[SavedSessionInfo]:
    ensure_runtime_dirs()
    target_dir = Path(directory) if directory is not None else SAVE_DIR
    if not target_dir.exists():
        return []
    sessions: list[SavedSessionInfo] = []
    for path in sorted(target_dir.glob("*.json"), key=lambda candidate: candidate.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        display_name = data.get("name", path.stem)
        sessions.append(SavedSessionInfo(path=path, display_name=display_name))
    return sessions
