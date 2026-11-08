"""Public entry point and lifecycle API for trusted MonopolPy extensions."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Protocol

from .controller import SessionController
from .game import GameEvent

API_VERSION = 1
ENTRY_POINT_GROUP = 'monopolpy_companion.plugins'
Cleanup = Callable[[], None]
RegisterAction = Callable[[str, Callable[[], None]], Cleanup]


@dataclass(frozen=True)
class PluginMetadata:
    name: str
    min_api: int
    max_api: int


def installed_plugins() -> tuple[EntryPoint, ...]:
    """List registrations without importing plugin code."""
    return tuple(entry_points(group=ENTRY_POINT_GROUP))


class PluginContext:
    """Host services scoped to one enabled plugin."""

    def __init__(
        self, controller: SessionController, cleanup: ExitStack,
        register_action: RegisterAction | None,
    ) -> None:
        self._controller = controller
        self._cleanup = cleanup
        self._register_action = register_action

    def current_game(self) -> dict | None:
        """Return a detached snapshot of the shared game, with credentials removed."""
        session = self._controller.session
        if session is None:
            return None
        snapshot = deepcopy(session.to_dict())
        for player in snapshot['players']:
            player.pop('pin_hash', None)
            player.pop('pin_salt', None)
        return snapshot

    def subscribe(self, handler: Callable[[GameEvent], None]) -> None:
        """Subscribe to controller notifications until the plugin stops."""
        self._cleanup.callback(self._controller.subscribe(
            lambda event: handler(deepcopy(event))
        ))

    @property
    def has_ui(self) -> bool:
        return self._register_action is not None

    def add_action(self, label: str, callback: Callable[[], None]) -> None:
        """Add a desktop command that is removed automatically on shutdown."""
        if self._register_action is None:
            raise RuntimeError('This host has no plugin action surface')

        def invoke() -> None:
            try:
                callback()
            except Exception:
                self._controller.logger.exception('Plugin action failed: %s', label)

        self._cleanup.callback(self._register_action(label, invoke))


class Plugin(Protocol):
    """An entry point resolves to a zero-argument factory for this protocol."""

    metadata: PluginMetadata

    def start(self, context: PluginContext) -> None: ...

    def stop(self) -> None: ...


class PluginManager:
    """Own enabled plugins and isolate failures at extension boundaries."""

    def __init__(
        self, controller: SessionController,
        registrations: Iterable[EntryPoint] | None = None,
        register_action: RegisterAction | None = None,
    ) -> None:
        self._controller = controller
        self._register_action = register_action
        self._active: dict[str, ExitStack] = {}
        self.errors: dict[str, str] = {}
        entries = tuple(installed_plugins() if registrations is None else registrations)
        counts = Counter(entry.name for entry in entries)
        self._entries = {entry.name: entry for entry in entries if counts[entry.name] == 1}
        for name, count in counts.items():
            if count > 1:
                self.errors[name] = f'{count} distributions registered the same identifier'

    @property
    def enabled(self) -> tuple[str, ...]:
        return tuple(self._active)

    def enable(self, identifier: str) -> bool:
        if identifier in self._active:
            return True
        if identifier not in self._entries:
            self.errors.setdefault(identifier, 'Plugin is not installed')
            return False
        try:
            factory = self._entries[identifier].load()
            metadata = factory.metadata
            if not isinstance(metadata, PluginMetadata):
                raise TypeError('Expected PluginMetadata on the entry point factory')
            if not metadata.min_api <= API_VERSION <= metadata.max_api:
                raise ValueError(
                    f'Host API {API_VERSION} is outside supported range '
                    f'{metadata.min_api} through {metadata.max_api}'
                )
            cleanup = ExitStack()
            plugin: Plugin = factory()
            context = PluginContext(self._controller, cleanup, self._register_action)
            cleanup.callback(plugin.stop)
            try:
                plugin.start(context)
            except Exception:
                cleanup.close()
                raise
            self._active[identifier] = cleanup
        except Exception as exc:
            self.errors[identifier] = str(exc) or type(exc).__name__
            self._controller.logger.exception('Could not enable plugin %s', identifier)
            return False
        self.errors.pop(identifier, None)
        return True

    def disable(self, identifier: str) -> None:
        cleanup = self._active.pop(identifier, None)
        if cleanup is None:
            return
        try:
            cleanup.close()
        except Exception as exc:
            self.errors[identifier] = str(exc) or type(exc).__name__
            self._controller.logger.exception('Could not stop plugin %s', identifier)

    def close(self) -> None:
        for identifier in reversed(self.enabled):
            self.disable(identifier)
