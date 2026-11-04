"""Events emitted by the headless Monopoly companion engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import utc_now


@dataclass(frozen=True)
class GameEvent:
    """A completed action that UI and integration subscribers may observe.

    Attributes:
        name: Stable event name such as cash_transferred.
        details: JSON-compatible action details.
        created_at: UTC timestamp of the event.
    """

    name: str
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
