"""UI-neutral session lifecycle, action dispatch and autosave controller.

The desktop interface deliberately delegates all game mutations to GameEngine.
This controller is also reusable by terminals, tests, and other frontends.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .game import (
    GameEngine, GameEvent, GameSession, SessionRepository,
    create_standard_session, get_game_logger,
)

Observer = Callable[[GameEvent], None]


class SessionSaveError(OSError):
    """A game action succeeded, but its follow-up autosave failed."""


class SessionController:
    """Own a session, its rules engine, persistence, and change notifications.

    Args:
        repository: Save backend to use.
        logger: Logging device implementing standard logging methods.
        autosave: Persist after each successful state-changing command.

    Notes:
        Methods return the actual engine result. Subscribers are notified
        after the action (and attempted save) finishes, so views never see
        half-completed building or mortgage operations. This controller is
        synchronous and should be called on the GUI thread.
    """

    ACTIONS = frozenset({
        'transfer', 'purchase', 'move', 'move_by_dice', 'advance_turn',
        'collect_rent', 'mortgage', 'unmortgage', 'buy_building',
        'sell_building', 'send_to_jail', 'release_from_jail', 'pay_tax',
        'mortgage_many', 'unmortgage_many',
    })

    def __init__(
        self,
        repository: SessionRepository | None = None,
        logger: Any = None,
        autosave: bool = True,
    ) -> None:
        self.repository = repository or SessionRepository()
        self.logger = logger if logger is not None else get_game_logger(
            'MonopolPyCompanion.Controller'
        )
        self.autosave = autosave
        self.session: GameSession | None = None
        self.engine: GameEngine | None = None
        self._listeners: list[Observer] = []
        self._pending: list[GameEvent] = []
        self._unsubscribe_engine: Callable[[], None] | None = None
        self._unlocked_ids: set[str] = set()

    def subscribe(self, handler: Observer) -> Callable[[], None]:
        """Subscribe to successful actions or session replacement."""
        if not callable(handler):
            raise TypeError('handler must be callable')
        self._listeners.append(handler)

        def unsubscribe() -> None:
            if handler in self._listeners:
                self._listeners.remove(handler)

        return unsubscribe

    def _notify(self, event: GameEvent) -> None:
        for handler in tuple(self._listeners):
            try:
                handler(event)
            except Exception:
                self.logger.exception('Controller observer failed')

    def _drain(self) -> None:
        events, self._pending = self._pending, []
        for event in events:
            self._notify(event)

    def set_session(self, session: GameSession) -> GameSession:
        """Install a game session and notify clients to rebuild their views."""
        if not isinstance(session, GameSession):
            raise TypeError('session must be a GameSession')
        if self._unsubscribe_engine is not None:
            self._unsubscribe_engine()
        self.session = session
        self._unlocked_ids.clear()
        self.engine = GameEngine(session, logger=self.logger)
        self._unsubscribe_engine = self.engine.subscribe(self._pending.append)
        self._pending.clear()
        self._notify(GameEvent('session_changed', {'session_id': session.session_id}))
        return session

    def new_session(
        self, name: str, player_names: list[str], starting_cash: int = 1500
    ) -> GameSession:
        """Create and save a new standard game before making it active."""
        session = create_standard_session(name, player_names, starting_cash)
        self.repository.save(session)
        return self.set_session(session)

    def open_session(self, path: str) -> GameSession:
        """Load an existing save and install it as the active session."""
        return self.set_session(self.repository.load(path))

    def save(self) -> None:
        """Write the active session to its existing path or the default path."""
        if self.session is None:
            raise ValueError('No active session')
        self.repository.save(self.session, self.session.save_path)

    def unlock_player(self, player_id: str, pin: str) -> bool:
        '''Unlock a player account for this app session after verifying its PIN.'''
        from .game.security import PlayerAccount
        if self.session is None:
            raise ValueError('No active session')
        account = PlayerAccount(self.session.get_player(player_id))
        if account.verify_pin(pin):
            self._unlocked_ids.add(player_id)
            return True
        return False

    def lock_player(self, player_id: str) -> None:
        '''Forget a player's in-memory PIN authorization.'''
        self._unlocked_ids.discard(player_id)

    def set_player_pin(self, player_id: str, pin: str, old_pin: str | None = None) -> None:
        '''Set or clear a PIN after verifying the old one when present.'''
        from .game.security import PlayerAccount
        if self.session is None:
            raise ValueError('No active session')
        account = PlayerAccount(self.session.get_player(player_id))
        if account.is_locked and player_id not in self._unlocked_ids:
            if old_pin is None or not account.verify_pin(old_pin):
                raise PermissionError('Current PIN required')
        if pin:
            account.set_pin(pin)
        else:
            account.clear_pin()
        self._unlocked_ids.discard(player_id)
        self.save()
        self._notify(GameEvent('account_security_changed', {'player_id': player_id}))

    def is_player_unlocked(self, player_id: str) -> bool:
        '''Whether a player can perform protected game actions now.'''
        from .game.security import PlayerAccount
        if self.session is None:
            return False
        player = self.session.get_player(player_id)
        return not PlayerAccount(player).is_locked or player_id in self._unlocked_ids

    def set_landing_prompts(self, enabled: bool) -> None:
        '''Persist whether the GUI should show automatic landing dialogs.'''
        if self.session is None:
            raise ValueError('No active session')
        self.session.show_landing_prompts = bool(enabled)
        self.session.touch()
        self.save()
        self._notify(GameEvent('settings_changed', {'show_landing_prompts': enabled}))

    def perform(self, action: str, *args: Any, **kwargs: Any) -> Any:
        """Execute a validated game command and autosave its completed result.

        Args:
            action: A permitted method name on GameEngine.
            *args: Positional arguments for the game command.
            **kwargs: Keyword arguments for the game command.

        Returns:
            The value returned by the game operation.

        Raises:
            ValueError: No session or invalid operation or game rule.
            SessionSaveError: Operation completed, but the save failed.
        """
        if self.engine is None:
            raise ValueError('No active session')
        if action not in self.ACTIONS:
            raise ValueError(f'Unsupported game action: {action}')
        secured = None
        if action == 'transfer':
            secured = kwargs.get('from_player_id')
        elif action not in {'advance_turn'}:
            secured = args[0] if args else kwargs.get('player_id')
        if secured is not None and not self.is_player_unlocked(secured):
            raise PermissionError('Player account is PIN locked')
        self._pending.clear()
        try:
            result = getattr(self.engine, action)(*args, **kwargs)
        except Exception:
            # The engine validates action parameters before mutating state.
            self._drain()
            raise
        try:
            if self.autosave:
                self.save()
        except OSError as exc:
            self._drain()
            raise SessionSaveError(f'Action succeeded but autosave failed: {exc}') from exc
        self._drain()
        return result
