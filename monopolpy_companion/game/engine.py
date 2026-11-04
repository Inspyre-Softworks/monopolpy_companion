"""Reusable headless Monopoly rules and electronic banker.

GameEngine is the mutation boundary for a physical-board game. The GUI,
CLI and other integrations share its validated operations and event stream.
The original GameSession data format and methods remain available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .events import GameEvent
from .logging import get_game_logger
from .models import GameSession, Player, PropertyState, Space, SpaceType, Transaction

EventHandler = Callable[[GameEvent], None]


@dataclass(frozen=True)
class MoveResult:
    """Describe a completed movement action.

    Attributes:
        player_id: Moved player's ID.
        passed_go: True when at least one GO crossing earned salary.
        landed_on: Space landed on before a Go To Jail instruction.
        final_position: Actual position after jail handling.
    """

    player_id: str
    passed_go: bool
    landed_on: Space
    final_position: int


class GameEngine:
    """Coordinate cash, ownership, rent, building and movement actions.

    Args:
        session: Existing mutable game data model.
        logger: Standard logging-compatible object. Defaults to a lazily
            configured, console-only InspyLogger device.

    Notes:
        Card decks, bidding, trading and doubles-based turn policy are
        intentionally not automated here; these require separate services.
        Integrations should mutate the game through this engine rather than
        directly manipulating the underlying dataclasses.
    """

    def __init__(self, session: GameSession, logger: Any = None) -> None:
        if not isinstance(session, GameSession):
            raise TypeError('session must be a GameSession')
        self.session = session
        self.log = logger if logger is not None else get_game_logger()
        self._subscribers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> Callable[[], None]:
        """Register a completed-action observer and return an unsubscribe hook."""
        if not callable(handler):
            raise TypeError('handler must be callable')
        self._subscribers.append(handler)

        def unsubscribe() -> None:
            if handler in self._subscribers:
                self._subscribers.remove(handler)

        return unsubscribe

    def _emit(self, name: str, **details: Any) -> None:
        event = GameEvent(name=name, details=details)
        self.log.info('%s: %s', name, details)
        for handler in tuple(self._subscribers):
            try:
                handler(event)
            except Exception:
                self.log.exception('Game event observer failed: %s', name)

    def _space(self, index: int) -> Space:
        board = self.session.board
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(board):
            raise ValueError(f'Invalid board index: {index}')
        return board[index]

    def _owned(self, player_id: str, space_index: int) -> tuple[Space, PropertyState]:
        player = self.session.get_player(player_id)
        if player.bankrupt:
            raise ValueError('Bankrupt players cannot manage properties')
        space = self._space(space_index)
        if not space.ownable:
            raise ValueError(f'{space.name} is not ownable')
        state = self.session.get_property_state(space_index)
        if state.owner_id != player_id:
            raise ValueError(f'Player does not own {space.name}')
        return space, state

    @staticmethod
    def _positive_amount(amount: int) -> None:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError('Amount must be a positive whole number')

    def transfer(
        self,
        amount: int,
        *,
        from_player_id: Optional[str] = None,
        to_player_id: Optional[str] = None,
        description: str = 'Cash transfer',
        kind: str = 'cash_transfer',
        space_index: Optional[int] = None,
    ) -> Transaction:
        """Make an audited cash transfer involving players and/or the bank.

        Args:
            amount: Positive integer in Monopoly dollars.
            from_player_id: Source player, or None for the bank.
            to_player_id: Destination player, or None for the bank.
            description: Ledger description.

        Returns:
            A recorded Transaction object.

        Raises:
            ValueError: Invalid amount, invalid transfer or insufficient cash.
            KeyError: A supplied player ID is unknown.
        """
        self._positive_amount(amount)
        if from_player_id is None and to_player_id is None:
            raise ValueError('At least one participant must be a player')
        if from_player_id is not None and from_player_id == to_player_id:
            raise ValueError('Source and destination must be different')
        sender = self.session.get_player(from_player_id) if from_player_id is not None else None
        receiver = self.session.get_player(to_player_id) if to_player_id is not None else None
        if sender is not None and (sender.bankrupt or sender.cash < amount):
            raise ValueError('Payer has insufficient available cash')
        if receiver is not None and receiver.bankrupt:
            raise ValueError('Cannot pay a bankrupt player')
        record = self.session.transfer_cash(
            amount, description, from_player_id=from_player_id, to_player_id=to_player_id
        )
        record.kind = kind
        record.space_index = space_index
        self._emit('cash_transferred', transaction_id=record.transaction_id,
                   amount=amount, from_player_id=from_player_id, to_player_id=to_player_id)
        return record

    def purchase(self, player_id: str, space_index: int) -> PropertyState:
        """Purchase an unowned property, railroad or utility from the bank."""
        space = self._space(space_index)
        if self.session.get_player(player_id).bankrupt:
            raise ValueError('Bankrupt players cannot purchase assets')
        state = self.session.buy_property(player_id, space_index)
        self._emit('property_purchased', player_id=player_id, space_index=space_index,
                   price=space.price)
        return state

    def move(self, player_id: str, spaces: int, *, collect_go: bool = True) -> MoveResult:
        """Move a token forward, collect GO salary, and resolve Go To Jail.

        Args:
            player_id: Player ID.
            spaces: Forward movement between zero and 39 board spaces.
            collect_go: Whether passing GO collects the session salary.

        Returns:
            A MoveResult suitable for a GUI board update.

        Notes:
            Rent, taxes, purchases and card draws are separate actions so
            clients can show a decision to the human players.
        """
        player = self.session.get_player(player_id)
        if player.bankrupt or player.in_jail:
            raise ValueError('Player cannot move while bankrupt or in jail')
        if isinstance(spaces, bool) or not isinstance(spaces, int) or not 0 <= spaces < 40:
            raise ValueError('spaces must be an integer between 0 and 39')
        board_size = len(self.session.board)
        old = player.position
        destination = (old + spaces) % board_size
        crossed_go = spaces > 0 and old + spaces >= board_size and collect_go
        if crossed_go and self.session.rules.salary_on_go:
            self.transfer(self.session.rules.salary_on_go, to_player_id=player_id,
                          description='Passing GO salary')
        player.position = destination
        self.session.touch()
        landing = self._space(destination)
        if landing.space_type is SpaceType.GO_TO_JAIL:
            self.send_to_jail(player_id)
        result = MoveResult(player_id, crossed_go, landing, player.position)
        self._emit('player_moved', player_id=player_id, from_position=old,
                   landed_on=destination, final_position=player.position,
                   passed_go=crossed_go)
        return result

    def move_by_dice(self, player_id: str, first_die: int, second_die: int) -> MoveResult:
        """Move using validated six-sided dice; caller handles doubles policy."""
        for die in (first_die, second_die):
            if isinstance(die, bool) or not isinstance(die, int) or not 1 <= die <= 6:
                raise ValueError('Each die must be an integer between 1 and 6')
        result = self.move(player_id, first_die + second_die)
        self.session.dice_rolls.append({
            'player_id': player_id, 'die_one': first_die,
            'die_two': second_die, 'total': first_die + second_die,
        })
        self.session.touch()
        self._emit('dice_rolled', player_id=player_id,
                   die_one=first_die, die_two=second_die)
        return result

    def simulate_dice(self) -> tuple[int, int]:
        '''Generate two unbiased six-sided dice for use in a later move.'''
        from secrets import randbelow
        return randbelow(6) + 1, randbelow(6) + 1

    def advance_turn(self) -> Optional[Player]:
        """Advance to the next solvent player, skipping bankrupt players."""
        players = self.session.players
        if not players or all(player.bankrupt for player in players):
            return None
        for offset in range(1, len(players) + 1):
            index = (self.session.current_turn_index + offset) % len(players)
            if not players[index].bankrupt:
                self.session.current_turn_index = index
                self.session.turn_counts[players[index].player_id] = (\n                    self.session.turn_counts.get(players[index].player_id, 0) + 1\n                )
                self.session.touch()
                self._emit('turn_advanced', player_id=players[index].player_id)
                return players[index]
        return None

    def _color_group(self, space: Space) -> list[PropertyState]:
        if space.space_type is not SpaceType.PROPERTY or not space.color_group:
            raise ValueError(f'{space.name} is not a color-group property')
        return [
            self.session.get_property_state(item.index)
            for item in self.session.board
            if item.space_type is SpaceType.PROPERTY and item.color_group == space.color_group
        ]

    @staticmethod
    def _level(state: PropertyState) -> int:
        return 5 if state.hotel else state.houses

    def rent_due(self, space_index: int, *, dice_total: Optional[int] = None) -> int:
        """Calculate a deed's current rent, considering all standard modifiers.

        Args:
            space_index: Position of an ownable board space.
            dice_total: Dice total, required for a utility (2 through 12).

        Returns:
            Rent owed; zero for an unowned or mortgaged deed.
        """
        space = self._space(space_index)
        if not space.ownable:
            raise ValueError(f'{space.name} cannot collect rent')
        state = self.session.get_property_state(space_index)
        if state.owner_id is None or state.mortgaged:
            return 0
        if space.space_type is SpaceType.RAILROAD:
            owned_count = sum(
                item.owner_id == state.owner_id
                for index, item in self.session.property_states.items()
                if self._space(index).space_type is SpaceType.RAILROAD
            )
            return space.rent_schedule[owned_count - 1]
        if space.space_type is SpaceType.UTILITY:
            if isinstance(dice_total, bool) or not isinstance(dice_total, int) or not 2 <= dice_total <= 12:
                raise ValueError('Utility rent requires dice_total between 2 and 12')
            owned_count = sum(
                item.owner_id == state.owner_id
                for index, item in self.session.property_states.items()
                if self._space(index).space_type is SpaceType.UTILITY
            )
            return dice_total * (10 if owned_count == 2 else 4)
        if state.hotel:
            return space.rent_schedule[5]
        if state.houses:
            if not 1 <= state.houses <= 4:
                raise ValueError('Invalid number of houses in the session')
            return space.rent_schedule[state.houses]
        group = self._color_group(space)
        if all(item.owner_id == state.owner_id and not item.mortgaged for item in group):
            return 2 * space.rent_schedule[0]
        return space.rent_schedule[0]

    def collect_rent(
        self, tenant_id: str, space_index: int, *, dice_total: Optional[int] = None
    ) -> Optional[Transaction]:
        """Pay the owner of the landed space, or return None when no rent is due."""
        tenant = self.session.get_player(tenant_id)
        space = self._space(space_index)
        if not space.ownable:
            raise ValueError(f'{space.name} cannot collect rent')
        owner = self.session.owner_for(space_index)
        if owner is None or owner.player_id == tenant.player_id:
            return None
        amount = self.rent_due(space_index, dice_total=dice_total)
        if not amount:
            return None
        return self.transfer(amount, from_player_id=tenant_id,
                             to_player_id=owner.player_id,
                             description=f'Rent: {space.name}', kind='rent',
                             space_index=space_index)

    def mortgage(self, player_id: str, space_index: int) -> PropertyState:
        """Mortgage an owned deed once its color group has no buildings."""
        space, state = self._owned(player_id, space_index)
        if state.mortgaged:
            raise ValueError('Property is already mortgaged')
        if space.space_type is SpaceType.PROPERTY and any(
            self._level(item) for item in self._color_group(space)
        ):
            raise ValueError('Sell all buildings in this group before mortgaging')
        self.transfer(space.mortgage_value, to_player_id=player_id,
                      description=f'Mortgage: {space.name}', kind='mortgage',
                      space_index=space_index)
        state.mortgaged = True
        self.session.touch()
        self._emit('property_mortgaged', player_id=player_id, space_index=space_index)
        return state

    def unmortgage(self, player_id: str, space_index: int) -> PropertyState:
        """Repay the printed mortgage value plus 10% interest, rounded up."""
        space, state = self._owned(player_id, space_index)
        if not state.mortgaged:
            raise ValueError('Property is not mortgaged')
        amount = space.mortgage_value + (space.mortgage_value + 9) // 10
        self.transfer(amount, from_player_id=player_id,
                      description=f'Unmortgage: {space.name}', kind='unmortgage',
                      space_index=space_index)
        state.mortgaged = False
        self.session.touch()
        self._emit('property_unmortgaged', player_id=player_id,
                   space_index=space_index, amount=amount)
        return state

    def _building_supply(self) -> tuple[int, int]:
        houses = sum(item.houses for item in self.session.property_states.values()
                     if not item.hotel)
        hotels = sum(bool(item.hotel) for item in self.session.property_states.values())
        return houses, hotels

    def buy_building(self, player_id: str, space_index: int) -> PropertyState:
        """Buy one house or upgrade four houses to a hotel using even-building rules."""
        space, state = self._owned(player_id, space_index)
        group = self._color_group(space)
        if not all(item.owner_id == player_id and not item.mortgaged for item in group):
            raise ValueError('A complete unmortgaged color group is required')
        level = self._level(state)
        if level >= 5:
            raise ValueError('Property already has a hotel')
        levels_after = [self._level(item) + int(item is state) for item in group]
        if max(levels_after) - min(levels_after) > 1:
            raise ValueError('Buildings must be bought evenly across the group')
        houses, hotels = self._building_supply()
        if level == 4 and hotels >= 12:
            raise ValueError('No hotels remain in the bank')
        if level < 4 and houses >= 32:
            raise ValueError('No houses remain in the bank')
        if self.session.get_player(player_id).cash < space.house_cost:
            raise ValueError('Insufficient cash to buy a building')
        self.transfer(space.house_cost, from_player_id=player_id,
                      description=f'Building purchase: {space.name}', kind='building_purchase',
                      space_index=space_index)
        if level == 4:
            state.houses = 0
            state.hotel = True
        else:
            state.houses += 1
        self.session.touch()
        self._emit('building_purchased', player_id=player_id,
                   space_index=space_index, level=level + 1)
        return state

    def sell_building(self, player_id: str, space_index: int) -> PropertyState:
        """Sell a house or downgrade a hotel, enforcing even-selling rules."""
        space, state = self._owned(player_id, space_index)
        group = self._color_group(space)
        level = self._level(state)
        if not level:
            raise ValueError('No buildings to sell')
        levels_after = [self._level(item) - int(item is state) for item in group]
        if max(levels_after) - min(levels_after) > 1:
            raise ValueError('Buildings must be sold evenly across the group')
        houses, _ = self._building_supply()
        if level == 5 and houses + 4 > 32:
            raise ValueError('Not enough houses to downgrade the hotel')
        if level == 5:
            state.hotel = False
            state.houses = 4
        else:
            state.houses -= 1
        self.transfer(space.house_cost // 2, to_player_id=player_id,
                      description=f'Building sale: {space.name}', kind='building_sale',
                      space_index=space_index)
        self.session.touch()
        self._emit('building_sold', player_id=player_id,
                   space_index=space_index, level=level - 1)
        return state

    def send_to_jail(self, player_id: str) -> Player:
        """Send a nonbankrupt player to Jail without a GO salary award."""
        player = self.session.get_player(player_id)
        if player.bankrupt:
            raise ValueError('Cannot jail a bankrupt player')
        player.position = 10
        player.in_jail = True
        player.jail_turns = 0
        self.session.touch()
        self._emit('player_jailed', player_id=player_id)
        return player

    def release_from_jail(self, player_id: str, *, method: str = 'fine') -> Player:
        """Release a prisoner by paying $50, using a card or reporting doubles.

        Args:
            player_id: Player in jail.
            method: One of fine, card, or doubles. The caller must verify
                a qualifying doubles roll; this is not a dice controller.
        """
        player = self.session.get_player(player_id)
        if not player.in_jail:
            raise ValueError('Player is not in jail')
        if method == 'fine':
            self.transfer(50, from_player_id=player_id, description='Jail fine')
        elif method == 'card':
            if player.get_out_of_jail_cards <= 0:
                raise ValueError('Player has no Get Out of Jail Free cards')
            player.get_out_of_jail_cards -= 1
        elif method != 'doubles':
            raise ValueError('method must be fine, card, or doubles')
        player.in_jail = False
        player.jail_turns = 0
        self.session.touch()
        self._emit('player_released', player_id=player_id, method=method)
        return player


    def mortgage_quote(self, player_id: str, space_indices: list[int],
                       operation: str = 'unmortgage'):
        '''Return a validated quote for several owned properties, without mutation.'''
        from .finance import MortgageCalculator
        return MortgageCalculator(self.session).quote(player_id, space_indices, operation)

    def mortgage_many(self, player_id: str, space_indices: list[int]) -> int:
        '''Mortgage several deeds after validating the complete selection.'''
        quote = self.mortgage_quote(player_id, space_indices, 'mortgage')
        for index in quote.space_indices:
            self.mortgage(player_id, index)
        return quote.total

    def unmortgage_many(self, player_id: str, space_indices: list[int]) -> int:
        '''Pay off several mortgages with preflight affordability checks.'''
        quote = self.mortgage_quote(player_id, space_indices, 'unmortgage')
        if self.session.get_player(player_id).cash < quote.total:
            raise ValueError('Insufficient cash to unmortgage selected deeds')
        for index in quote.space_indices:
            self.unmortgage(player_id, index)
        return quote.total

    def pay_tax(self, player_id: str, space_index: int) -> Transaction:
        """Pay Income Tax ($200) or Luxury Tax ($100) to the bank."""
        space = self._space(space_index)
        amount = {4: 200, 38: 100}.get(space_index)
        if space.space_type is not SpaceType.TAX or amount is None:
            raise ValueError('No supported tax at this board position')
        return self.transfer(amount, from_player_id=player_id,
                             description=f'Tax: {space.name}', kind='tax',
                             space_index=space_index)
