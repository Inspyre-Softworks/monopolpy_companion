"""UI-neutral session lifecycle, action dispatch and autosave controller.

The desktop interface deliberately delegates all game mutations to GameEngine.
This controller is also reusable by terminals, tests, and other frontends.
"""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .game import (
    GameEngine, GameEvent, GameSession, SessionRepository,
    create_standard_session, get_game_logger,
)

Observer = Callable[[GameEvent], None]

MAP_UNLOCK_PHRASE = 'I solemnly swear that I am up to no good.'
MAP_LOCK_PHRASE = 'Mischief managed!'


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
        'sell_building', 'liquidate_building_group', 'send_to_jail',
        'release_from_jail', 'pay_tax',
        'mortgage_many', 'unmortgage_many', 'simulate_dice',
        'roll_for_doubles', 'pay_jail_bail', 'pay_outstanding', 'trade',
        'start_auction', 'bid_at_auction', 'pass_at_auction', 'declare_bankruptcy',
        'dev_grant_cash', 'dev_grant_deed', 'dev_grant_building',
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
        self._restore_dev_lock()

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
        events = list(self._pending)
        self._pending.clear()
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
        self._restore_dev_lock()
        self.engine = GameEngine(session, logger=self.logger)
        self._unsubscribe_engine = self.engine.subscribe(self._pending.append)
        self._pending.clear()
        self._notify(GameEvent('session_changed', {'session_id': session.session_id}))
        return session

    def new_session(
        self, name: str, player_names: list[str], starting_cash: int = 1500, *, accounts: dict | None = None,
        landing_prompts: bool = True
    ) -> GameSession:
        """Create and save a new standard game before making it active."""
        session = create_standard_session(name, player_names, starting_cash)
        session.show_landing_prompts = landing_prompts
        for player in session.players:
            account = (accounts or {}).get(player.name.casefold())
            if account:
                player.account_id = account.get('id')
                player.pin_salt = account['data']['pin_salt']
                player.pin_hash = account['data']['pin_hash']
        self.repository.save(session)
        return self.set_session(session)

    def player_history(self, player_id: str):
        """Return the live report and matching reports from distinct local saves."""
        from .game.statistics import StatisticsService

        session = self.session
        if session is None:
            raise ValueError('No active game')
        player = session.get_player(player_id)
        current = StatisticsService(session).for_player(player_id)
        history = []
        seen = {session.session_id}
        for info in self.repository.list_sessions():
            try:
                saved = self.repository.load(info.path)
                if saved.session_id in seen:
                    continue
                if player.account_id:
                    matches = (candidate for candidate in saved.players
                               if candidate.account_id == player.account_id)
                else:
                    matches = (candidate for candidate in saved.players if not candidate.account_id
                               and candidate.name.casefold() == player.name.casefold())
                match = next(matches, None)
                if match is not None:
                    report = StatisticsService(saved).for_player(match.player_id)
                    history.append((saved.name, saved.created_at, report))
                seen.add(saved.session_id)
            except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
                continue
        return current, history

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

    def set_go_salary(self, amount: int, *, double_on_go: bool | None = None,
                      three_doubles_to_jail: bool | None = None,
                      allow_rent_immunity: bool | None = None,
                      immunity_follows_deed: bool | None = None) -> None:
        """Persist the active game's salary in whole dollars; zero disables it."""
        if self.session is None:
            raise ValueError('No active session')
        if isinstance(amount, bool) or not isinstance(amount, int) or not 0 <= amount <= 1000000:
            raise ValueError('GO salary must be an integer between 0 and 1000000')
        if double_on_go is not None and not isinstance(double_on_go, bool):
            raise ValueError('Double salary must be a boolean')
        if three_doubles_to_jail is not None and not isinstance(three_doubles_to_jail, bool):
            raise ValueError('Three doubles rule must be a boolean')
        immunity_settings = {
            'allow_rent_immunity': allow_rent_immunity,
            'immunity_follows_deed': immunity_follows_deed,
        }
        if any(value is not None and not isinstance(value, bool)
               for value in immunity_settings.values()):
            raise ValueError('Rent immunity rules must be boolean')
        previous_immunity = {key: getattr(self.session.rules, key) for key in immunity_settings}
        for key, value in immunity_settings.items():
            if value is not None:
                setattr(self.session.rules, key, value)
        previous_three_doubles = self.session.rules.three_doubles_to_jail
        previous_double = self.session.rules.double_salary_on_go
        previous = self.session.rules.salary_on_go
        updated = self.session.updated_at
        self.session.rules.salary_on_go = amount
        if three_doubles_to_jail is not None:
            self.session.rules.three_doubles_to_jail = three_doubles_to_jail
        if double_on_go is not None:
            self.session.rules.double_salary_on_go = double_on_go
        self.session.touch()
        try:
            self.save()
        except OSError:
            for key, value in previous_immunity.items():
                setattr(self.session.rules, key, value)
            self.session.rules.salary_on_go = previous
            self.session.rules.three_doubles_to_jail = previous_three_doubles
            self.session.rules.double_salary_on_go = previous_double
            self.session.updated_at = updated
            raise
        self._notify(GameEvent('settings_changed', {'salary_on_go': amount}))

    @property
    def dev_tools_unlocked(self) -> bool:
        return self._dev_tools_unlocked

    @staticmethod
    def _dev_lock_path() -> Path:
        return Path.home() / 'mm.lock'

    def _restore_dev_lock(self) -> None:
        self._dev_tools_unlocked = False
        try:
            expected = MAP_UNLOCK_PHRASE.encode('utf-8')
            with self._dev_lock_path().open('rb') as handle:
                contents = handle.read(len(expected) + 1)
        except FileNotFoundError:
            return
        except OSError:
            logging.getLogger(__name__).warning('Could not read the Marauder’s Map lock',
                                                exc_info=True)
            return
        self._dev_tools_unlocked = contents == expected

    def _write_dev_lock(self, state: str) -> None:
        destination = self._dev_lock_path()
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=destination.parent,
                prefix='.mm.lock-', suffix='.tmp', delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(state)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def unlock_dev_tools(self, phrase: str) -> bool:
        """Enable developer tools for the current game and persist the state.

        Args:
            phrase: Text submitted in the unlock dialog.

        Returns:
            Whether a valid phrase enabled developer tools for an unfinished game.

        Raises:
            OSError: The profile state could not be replaced.
        """
        normalized = ' '.join(phrase.casefold().split()).rstrip('.')
        if (self.session is None or self.session.winner_id is not None
                or normalized != MAP_UNLOCK_PHRASE.casefold().rstrip('.')):
            return False
        self._write_dev_lock(MAP_UNLOCK_PHRASE)
        self._dev_tools_unlocked = True
        return True

    def lock_dev_tools(self) -> None:
        """Disable grants immediately and persist the locked state.

        Raises:
            OSError: The profile state could not be replaced. Grants remain
                disabled in this controller until the state is restored.
        """
        self._dev_tools_unlocked = False
        self._write_dev_lock(MAP_LOCK_PHRASE)

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
        dev_action = action.startswith('dev_')
        if dev_action and not self.dev_tools_unlocked:
            raise ValueError('The Marauder’s Map is locked')
        if self.session.winner_id is not None:
            raise ValueError('The game has ended')
        if self.session.auction is not None and action not in {'bid_at_auction', 'pass_at_auction'}:
            raise ValueError('Finish the active auction first')
        if action == 'trade':
            parties = [args[index] if len(args) > index else kwargs.get(key)
                       for index, key in enumerate(('player_a_id', 'player_b_id'))]
            if any(not self.is_player_unlocked(player_id) for player_id in parties):
                raise PermissionError('Both players must authorize the trade with their PINs')
        secured = None
        if action == 'transfer':
            secured = kwargs.get('from_player_id')
        elif not dev_action and action not in {'advance_turn', 'trade'}:
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
