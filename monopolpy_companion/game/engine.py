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
        Card decks, bidding and trading are
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
        auction = self.session.auction
        if (auction is not None and sender is not None and auction['leader'] == sender.player_id
                and sender.cash - amount < auction['bid']):
            raise ValueError('Keep enough cash to cover the leading auction bid')
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

    def trade_quote(self, player_a_id: str, player_b_id: str, *, cash_a: int = 0,
                    cash_b: int = 0, properties_a=(), properties_b=(),
                    cards_a: int = 0, cards_b: int = 0, immunity_a=None, immunity_b=None) -> dict:
        """Validate a two-party exchange before any balance or ownership changes.

        Mortgages remain in place; recipients pay 10% mortgage interest to the
        bank. No property in an improved color group can be traded.
        """
        if self.session.auction is not None:
            raise ValueError('Finish the active auction first')
        a = self.session.get_player(player_a_id)
        b = self.session.get_player(player_b_id)
        if a is b or a.bankrupt or b.bankrupt:
            raise ValueError('Choose two different solvent players')
        for amount in (cash_a, cash_b, cards_a, cards_b):
            if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                raise ValueError('Cash and card offers must be nonnegative whole numbers')
        if cash_a > a.cash or cash_b > b.cash:
            raise ValueError('A player cannot offer more cash than they have')
        if cards_a > a.get_out_of_jail_cards or cards_b > b.get_out_of_jail_cards:
            raise ValueError('A player cannot offer jail cards they do not own')
        properties_a, properties_b = tuple(properties_a), tuple(properties_b)
        fees = []
        for owner, indices in ((a, properties_a), (b, properties_b)):
            if len(set(indices)) != len(indices):
                raise ValueError('Do not include a property twice')
            fee = 0
            for index in indices:
                space, state = self._owned(owner.player_id, index)
                if space.space_type is SpaceType.PROPERTY and any(self._level(item)
                        for item in self._color_group(space)):
                    raise ValueError(f'Sell all buildings in the {space.color_group} set before trading')
                if state.mortgaged:
                    fee += (space.mortgage_value + 9) // 10
            fees.append(fee)
        for grant, owner, outgoing, incoming in (
            (immunity_a, a, properties_a, properties_b),
            (immunity_b, b, properties_b, properties_a),
        ):
            if grant is None:
                continue
            if not self.session.rules.allow_rent_immunity:
                raise ValueError('Enable rent immunity trades in Game Settings first')
            index, unit, count = grant
            if unit not in ('landings', 'laps', 'turns') or type(count) is not int or count < 1:
                raise ValueError('Choose a positive immunity duration')
            if index is not None:
                self._space(index)
                if index not in incoming:
                    self._owned(owner.player_id, index)
                    if index in outgoing:
                        raise ValueError('Choose a deed the granting player will own after the trade')
        if not (cash_a or cash_b or properties_a or properties_b or cards_a or cards_b
                or immunity_a or immunity_b):
            raise ValueError('Add something to the trade')
        fee_a, fee_b = fees[1], fees[0]
        final_a = a.cash - cash_a + cash_b - fee_a
        final_b = b.cash - cash_b + cash_a - fee_b
        if min(final_a, final_b) < 0:
            raise ValueError('Insufficient cash to cover mortgage transfer interest')
        return {'fee_a': fee_a, 'fee_b': fee_b, 'final_a': final_a, 'final_b': final_b}

    def trade(self, player_a_id: str, player_b_id: str, *, cash_a: int = 0,
              cash_b: int = 0, properties_a=(), properties_b=(),
              cards_a: int = 0, cards_b: int = 0, immunity_a=None, immunity_b=None) -> dict:
        """Commit a fully validated exchange and emit one completed trade event."""
        properties_a, properties_b = tuple(properties_a), tuple(properties_b)
        quote = self.trade_quote(player_a_id, player_b_id, cash_a=cash_a, cash_b=cash_b,
            properties_a=properties_a, properties_b=properties_b, cards_a=cards_a, cards_b=cards_b,
            immunity_a=immunity_a, immunity_b=immunity_b)
        a, b = self.session.get_player(player_a_id), self.session.get_player(player_b_id)
        a.cash, b.cash = quote['final_a'], quote['final_b']
        a.get_out_of_jail_cards += cards_b - cards_a
        b.get_out_of_jail_cards += cards_a - cards_b
        for indices, recipient in ((properties_a, b), (properties_b, a)):
            for index in indices:
                self.session.get_property_state(index).owner_id = recipient.player_id
        if self.session.rules.immunity_follows_deed:
            for grant in self.session.rent_immunity:
                index = grant['space_index']
                if index in properties_a and grant['grantor_id'] == a.player_id:
                    grant['grantor_id'] = b.player_id
                elif index in properties_b and grant['grantor_id'] == b.player_id:
                    grant['grantor_id'] = a.player_id
        for grant, grantor, beneficiary in ((immunity_a, a, b), (immunity_b, b, a)):
            if grant is not None:
                index, unit, count = grant
                self.session.rent_immunity.append({
                    'grantor_id': grantor.player_id, 'beneficiary_id': beneficiary.player_id,
                    'space_index': index, 'unit': unit, 'remaining': count,
                })
                self.session.record_transaction('rent_immunity', 0,
                    f'{grantor.name} grants {beneficiary.name}: {self.immunity_description(grant)}',
                    from_player_id=grantor.player_id, to_player_id=beneficiary.player_id,
                    space_index=index)
        for sender, recipient, cash in ((a, b, cash_a), (b, a, cash_b)):
            if cash:
                self.session.record_transaction('deal', cash, f'Trade: {sender.name} to {recipient.name}',
                    from_player_id=sender.player_id, to_player_id=recipient.player_id)
        for player, fee in ((a, quote['fee_a']), (b, quote['fee_b'])):
            if fee:
                self.session.record_transaction('mortgage_interest', fee, 'Trade mortgage interest',
                                                from_player_id=player.player_id)
        def offer(cash, indices, cards):
            names = ', '.join(self._space(index).name for index in indices) or 'no deeds'
            return f'${cash:,}; {names}; {cards} jail card(s)'
        self.session.record_transaction('trade', 0,
            f'{a.name} gives {offer(cash_a, properties_a, cards_a)}; '
            f'{b.name} gives {offer(cash_b, properties_b, cards_b)}',
            from_player_id=a.player_id, to_player_id=b.player_id)
        self.session.touch()
        self._emit('trade_completed', player_a_id=a.player_id, player_b_id=b.player_id)
        return quote

    def purchase(self, player_id: str, space_index: int) -> PropertyState:
        """Purchase an unowned property, railroad or utility from the bank."""
        space = self._space(space_index)
        if self.session.get_player(player_id).bankrupt:
            raise ValueError('Bankrupt players cannot purchase assets')
        if self.session.auction is not None:
            raise ValueError('Finish the active auction first')
        state = self.session.buy_property(player_id, space_index)
        if self.session.purchase_offer == space_index:
            self.session.purchase_offer = None
        self._emit('property_purchased', player_id=player_id, space_index=space_index,
                   price=space.price)
        return state

    def dev_grant_cash(self, player_id: str, amount: int) -> Transaction:
        """Give a player cash from the bank as an audited developer grant."""
        return self.transfer(amount, to_player_id=player_id,
                             description='Marauder’s Map cash grant', kind='dev_cash_grant')

    def dev_grant_deed(self, player_id: str, space_index: int) -> PropertyState:
        """Give an unowned deed to a solvent player without charging the price."""
        player = self.session.get_player(player_id)
        space = self._space(space_index)
        if player.bankrupt or not space.ownable:
            raise ValueError('Choose an eligible player and deed')
        if self.session.auction is not None:
            raise ValueError('Finish the active auction first')
        state = self.session.get_property_state(space_index)
        if state.owner_id is not None:
            raise ValueError('Only unowned deeds can be granted')
        state.owner_id = player_id
        if self.session.purchase_offer == space_index:
            self.session.purchase_offer = None
        self.session.record_transaction('dev_deed_grant', 0, f'Marauder’s Map granted {space.name}',
                                        to_player_id=player_id, space_index=space_index)
        self._emit('dev_grant_completed', player_id=player_id, space_index=space_index)
        return state

    def dev_grant_building(self, player_id: str, space_index: int, *, hotel: bool = False) -> PropertyState:
        """Add a free house or grant a hotel while preserving ownership and inventory."""
        space, state = self._owned(player_id, space_index)
        if space.space_type is not SpaceType.PROPERTY or state.mortgaged:
            raise ValueError('Choose an unmortgaged street owned by the player')
        if state.hotel:
            raise ValueError('This property already has a hotel')
        houses, hotels = self._building_supply()
        if hotel:
            if hotels >= 12:
                raise ValueError('No hotels remain in the bank')
            state.houses = 0
            state.hotel = True
        else:
            if state.houses >= 4:
                raise ValueError('This property already has four houses')
            if houses >= 32:
                raise ValueError('No houses remain in the bank')
            state.houses += 1
        building = 'hotel' if hotel else 'house'
        self.session.record_transaction('dev_building_grant', 0,
            f'Marauder’s Map granted a {building} on {space.name}', to_player_id=player_id,
            space_index=space_index)
        self._emit('dev_grant_completed', player_id=player_id, space_index=space_index)
        return state

    def start_auction(self, player_id: str) -> None:
        """Offer the current landing to all solvent players, including the lander."""
        if self.session.auction is not None:
            raise ValueError('An auction is already active')
        player = self.session.get_player(player_id)
        index = self.session.purchase_offer
        if player is not self.session.current_player or player.bankrupt or index is None:
            raise ValueError('No property is available to auction on this turn')
        if self.session.owner_for(index) is not None:
            raise ValueError('The property is already owned')
        self.session.purchase_offer = None
        self._open_auction(index)

    def _open_auction(self, index: int) -> None:
        self.session.auction = {
            'space_index': index,
            'bidders': [p.player_id for p in self.session.players if not p.bankrupt],
            'leader': None,
            'bid': 0,
        }
        self.session.touch()
        self._emit('auction_started', space_index=index)

    def auction_bidder(self) -> Optional[str]:
        """Return the next bidder, skipping the player whose bid is already leading."""
        auction = self.session.auction
        if auction is None:
            return None
        return next((player_id for player_id in auction['bidders']
                     if player_id != auction['leader']), None)

    def bid_at_auction(self, player_id: str, amount: int) -> None:
        """Enter a higher cash bid and move the bidder to the back of the queue."""
        self._auction_action(player_id, amount)

    def pass_at_auction(self, player_id: str) -> None:
        """Withdraw this bidder from the current auction."""
        self._auction_action(player_id, None)

    def _auction_action(self, player_id: str, amount: Optional[int]) -> None:
        auction = self.session.auction
        if auction is None or self.auction_bidder() != player_id:
            raise ValueError('It is not this player’s turn to bid')
        player = self.session.get_player(player_id)
        bidders = [bidder for bidder in auction['bidders'] if bidder != player_id]
        leader, bid = auction['leader'], auction['bid']
        if amount is not None:
            if type(amount) is not int or not bid < amount <= player.cash:
                raise ValueError('Bid more than the current bid, within available cash')
            leader, bid = player_id, amount
            bidders.append(player_id)
        index = auction['space_index']
        if any(bidder != leader for bidder in bidders):
            auction.update(bidders=bidders, leader=leader, bid=bid)
            self.session.touch()
            self._emit('auction_updated', space_index=index)
            return
        if leader is not None:
            winner = self.session.get_player(leader)
            state = self.session.get_property_state(index)
            if state.owner_id is not None or winner.bankrupt or winner.cash < bid:
                raise ValueError('The winning bid can no longer be settled')
            winner.cash -= bid
            state.owner_id = leader
            self.session.record_transaction('auction_purchase', bid,
                f'{winner.name} won {self._space(index).name} at auction',
                from_player_id=leader, space_index=index)
        self.session.auction = None
        self.session.touch()
        self._emit('auction_finished', space_index=index, winner_id=leader, amount=bid)
        if self.session.bankruptcy_auctions:
            self._open_auction(self.session.bankruptcy_auctions.pop(0))
        elif self.session.current_player is not None and self.session.current_player.bankrupt:
            self.advance_turn()

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
        return self._move(player_id, spaces, collect_go=collect_go)

    def _move(
        self, player_id: str, spaces: int, *, collect_go: bool = True,
        dice_total: Optional[int] = None,
    ) -> MoveResult:
        player = self.session.get_player(player_id)
        if player.bankrupt or player.in_jail:
            raise ValueError('Player cannot move while bankrupt or in jail')
        if isinstance(spaces, bool) or not isinstance(spaces, int) or not 0 <= spaces < 40:
            raise ValueError('spaces must be an integer between 0 and 39')
        if self.session.auction is not None:
            raise ValueError('Finish the active auction first')
        board_size = len(self.session.board)
        old = player.position
        destination = (old + spaces) % board_size
        crossed_go = spaces > 0 and old + spaces >= board_size and collect_go
        salary = self.session.rules.salary_on_go if crossed_go else 0
        if destination == 0 and self.session.rules.double_salary_on_go:
            salary *= 2
        if salary:
            self.transfer(salary, to_player_id=player_id,
                          description='Passing GO salary')
            self._emit('go_salary_paid', player_id=player_id, amount=salary,
                       balance=player.cash)
        player.position = destination
        self.session.touch()
        landing = self._space(destination)
        if landing.space_type is SpaceType.GO_TO_JAIL:
            self.send_to_jail(player_id)
        if old + spaces >= board_size:
            self._tick_immunity(player_id, 'laps')
        self._record_landing_payment(player_id, landing, dice_total)
        if player is self.session.current_player:
            self.session.purchase_offer = (
                destination if spaces and landing.ownable and self.session.owner_for(destination) is None
                else None
            )
        result = MoveResult(player_id, crossed_go, landing, player.position)
        self.session.movement_history.append({
            'player_id': player_id, 'spaces': spaces,
            'from_position': old, 'landed_on': destination,
            'final_position': player.position, 'passed_go': crossed_go,
        })
        self.session.touch()
        self._emit('player_moved', player_id=player_id, from_position=old,
                   landed_on=destination, final_position=player.position,
                   passed_go=crossed_go)
        return result

    def move_by_dice(self, player_id: str, first_die: int, second_die: int) -> MoveResult:
        """Record a played pair of dice and move the player once."""
        for die in (first_die, second_die):
            if isinstance(die, bool) or not isinstance(die, int) or not 1 <= die <= 6:
                raise ValueError('Each die must be an integer between 1 and 6')
        pending = self._pending_turn_roll(player_id)
        if pending is not None:
            if (first_die, second_die) != (pending['die_one'], pending['die_two']):
                raise ValueError('Move using the dice already rolled')
        else:
            self._validate_next_roll(player_id)
        third_double = (pending is None and first_die == second_die
                        and self.session.rules.three_doubles_to_jail
                        and self._consecutive_doubles() >= 2)
        if third_double:
            self.send_to_jail(player_id)
            result = MoveResult(player_id, False, self._space(10), 10)
        else:
            result = self._move(player_id, first_die + second_die,
                                dice_total=first_die + second_die)
        if pending is not None and (
            pending.get('die_one'), pending.get('die_two')
        ) == (first_die, second_die):
            pending['used_for_move'] = True
        else:
            self.session.dice_rolls.append({
                'player_id': player_id, 'die_one': first_die,
                'die_two': second_die, 'total': first_die + second_die,
                'source': 'manual', 'used_for_move': True,
            })
            self.session.turn_roll_indices.append(len(self.session.dice_rolls) - 1)
            self._emit('dice_rolled', player_id=player_id,
                       die_one=first_die, die_two=second_die, source='manual')
        self.session.touch()
        return result

    def simulate_dice(self, player_id: str) -> tuple[int, int]:
        """Roll two unbiased dice and persist the player's simulated result.

        The result can later be consumed by move_by_dice without double
        counting the same roll. A simulated roll counts even if not used.
        """
        from secrets import randbelow
        self._validate_next_roll(player_id)
        first, second = randbelow(6) + 1, randbelow(6) + 1
        self.session.dice_rolls.append({
            'player_id': player_id, 'die_one': first,
            'die_two': second, 'total': first + second,
            'source': 'simulated', 'used_for_move': False,
        })
        self.session.turn_roll_indices.append(len(self.session.dice_rolls) - 1)
        if self.session.rules.three_doubles_to_jail and self._consecutive_doubles() >= 3:
            self.session.dice_rolls[-1]['used_for_move'] = True
            self.send_to_jail(player_id)
        self.session.touch()
        self._emit('dice_rolled', player_id=player_id,
                   die_one=first, die_two=second, source='simulated')
        return first, second

    def _consecutive_doubles(self) -> int:
        """Count this turn's latest consecutive normal doubles, including a pending roll."""
        count = 0
        for index in reversed(self.session.turn_roll_indices):
            roll = self.session.dice_rolls[index]
            if roll.get('source') == 'jail' or roll['die_one'] != roll['die_two']:
                break
            count += 1
        return count

    def outstanding_payments(self, player_id: str) -> list[dict]:
        """Return copies of unpaid landing charges, including saved rent quotes."""
        self.session.get_player(player_id)
        return [dict(item) for item in self.session.landing_payments
                if item['player_id'] == player_id and not item['settled']]

    def immunity_description(self, grant) -> str:
        index, unit, count = grant
        scope = 'all properties' if index is None else self._space(index).name
        duration = {'landings': 'rent charges waived', 'laps': 'GO crossings',
                    'turns': 'completed turns'}[unit]
        return f'{scope}, {count} {duration}'

    def _tick_immunity(self, player_id: str, unit: str) -> None:
        for grant in self.session.rent_immunity:
            if (grant['beneficiary_id'] == player_id and grant['unit'] == unit
                    and grant['remaining'] > 0):
                grant['remaining'] -= 1

    def _waive_rent(self, player_id: str, owner_id: str, space: Space) -> bool:
        if not self.session.rules.allow_rent_immunity:
            return False
        grants = sorted(self.session.rent_immunity,
                        key=lambda grant: (grant['unit'] == 'landings', grant['space_index'] is None))
        for grant in grants:
            if (grant['remaining'] > 0 and grant['beneficiary_id'] == player_id
                    and grant['grantor_id'] == owner_id
                    and grant['space_index'] in (None, space.index)):
                if grant['unit'] == 'landings':
                    grant['remaining'] -= 1
                self.session.record_transaction('rent_waived', 0, f'Rent immunity: {space.name}',
                    from_player_id=player_id, to_player_id=owner_id, space_index=space.index)
                return True
        return False

    def _record_landing_payment(
        self, player_id: str, space: Space, dice_total: Optional[int]
    ) -> None:
        amount = None
        recipient = None
        multiplier = None
        if space.space_type is SpaceType.TAX:
            kind = 'tax'
            amount = {4: 200, 38: 100}.get(space.index)
            if amount is None:
                return
        elif space.ownable:
            owner = self.session.owner_for(space.index)
            if owner is None or owner.player_id == player_id:
                return
            state = self.session.get_property_state(space.index)
            if state.mortgaged:
                return
            kind = 'rent'
            recipient = owner.player_id
            if space.space_type is SpaceType.UTILITY:
                multiplier = self.rent_due(space.index, dice_total=2) // 2
                if dice_total is not None:
                    amount = dice_total * multiplier
            else:
                amount = self.rent_due(space.index)
            if amount == 0:
                return
        else:
            return
        waived = kind == 'rent' and self._waive_rent(player_id, recipient, space)
        self.session.landing_payments.append({
            'player_id': player_id, 'space_index': space.index,
            'kind': kind, 'amount': amount, 'recipient_id': recipient,
            'utility_multiplier': multiplier, 'settled': waived,
        })

    def _settle_landing_payment(self, payment: dict, dice_total: Optional[int] = None) -> Optional[Transaction]:
        if payment['settled']:
            return None
        amount = self._payment_amount(payment, dice_total)
        record = self.transfer(amount, from_player_id=payment['player_id'],
            to_player_id=payment['recipient_id'], kind=payment['kind'],
            space_index=payment['space_index'],
            description=f"{payment['kind'].replace('_', ' ').title()}: {self._space(payment['space_index']).name}")
        payment['amount'] = amount
        payment['settled'] = True
        self.session.touch()
        self._finalize_winner_if_ready()
        self._emit('payment_settled', player_id=payment['player_id'], amount=amount)
        return record

    def _finalize_winner_if_ready(self) -> None:
        remaining = [player for player in self.session.players if not player.bankrupt]
        if (len(remaining) == 1
                and not self.outstanding_payments(remaining[0].player_id)):
            self.session.winner_id = remaining[0].player_id
            self.session.current_turn_index = self.session.players.index(remaining[0])

    @staticmethod
    def _payment_amount(payment: dict, dice_total: Optional[int]) -> int:
        amount = payment['amount']
        if amount is None:
            if isinstance(dice_total, bool) or not isinstance(dice_total, int) or not 2 <= dice_total <= 12:
                raise ValueError('Enter the utility dice total between 2 and 12')
            amount = dice_total * payment['utility_multiplier']
        return amount

    def pay_outstanding(self, player_id: str, *, dice_total: Optional[int] = None) -> Transaction:
        """Pay the oldest outstanding rent or tax charge exactly once."""
        for payment in self.session.landing_payments:
            if payment['player_id'] == player_id and not payment['settled']:
                return self._settle_landing_payment(payment, dice_total)
        raise ValueError('No outstanding rent or tax payment')

    def _landing_payment(self, player_id: str, space_index: int, kind: str):
        return next((payment for payment in reversed(self.session.landing_payments)
                     if payment['player_id'] == player_id
                     and payment['space_index'] == space_index and payment['kind'] == kind), None)

    def bankruptcy_quote(self, player_id: str, *, dice_total: Optional[int] = None) -> dict:
        """Preview surrender for the current player's oldest unpayable obligation."""
        player = self.session.get_player(player_id)
        if (player is not self.session.current_player or player.bankrupt
                or self.session.auction is not None or self.session.winner_id is not None):
            raise ValueError('Bankruptcy is only available to the active player outside an auction')
        debts = self.outstanding_payments(player_id)
        if debts:
            debt = debts[0]
            amount = self._payment_amount(debt, dice_total)
            creditor_id = debt['recipient_id']
            if creditor_id is not None and self.session.get_player(creditor_id).bankrupt:
                raise ValueError('The creditor has already left the game')
        elif player.in_jail and player.jail_turns >= 3:
            amount, creditor_id = 50, None
        else:
            raise ValueError('Bankruptcy requires an outstanding payment or mandatory jail bail')
        deeds = self.session.owned_spaces_for(player_id)
        buildings = 0
        mortgages = 0
        interest = []
        for space in deeds:
            state = self.session.get_property_state(space.index)
            buildings += self._level(state) * (space.house_cost // 2)
            if state.mortgaged:
                if creditor_id is not None:
                    interest.append((space.index, (space.mortgage_value + 9) // 10))
            else:
                mortgages += space.mortgage_value
        funds = player.cash + buildings + mortgages
        if funds >= amount:
            raise ValueError(f'You can cover the ${amount:,} payment with up to ${funds:,} from cash, '
                             'building sales, and mortgages')
        return {'amount': amount, 'creditor_id': creditor_id, 'deeds': deeds,
                'cash': player.cash + buildings, 'building_proceeds': buildings,
                'interest': interest, 'cards': player.get_out_of_jail_cards}

    def declare_bankruptcy(self, player_id: str, *, dice_total: Optional[int] = None) -> None:
        """Surrender the estate, retire the debtor, and continue or finish the game."""
        quote = self.bankruptcy_quote(player_id, dice_total=dice_total)
        player = self.session.get_player(player_id)
        creditor_id = quote['creditor_id']
        creditor = self.session.get_player(creditor_id) if creditor_id is not None else None
        indices = {space.index for space in quote['deeds']}
        for space in quote['deeds']:
            state = self.session.get_property_state(space.index)
            proceeds = self._level(state) * (space.house_cost // 2)
            if proceeds:
                self.session.record_transaction('building_sale', proceeds,
                    f'Bankruptcy building sale: {space.name}', to_player_id=player_id,
                    space_index=space.index)
            state.houses = 0
            state.hotel = False
            state.owner_id = creditor_id
            if creditor is None:
                state.mortgaged = False
        if creditor is not None:
            creditor.cash += quote['cash']
            creditor.get_out_of_jail_cards += quote['cards']
        player.cash = 0
        player.get_out_of_jail_cards = 0
        player.bankrupt = True
        player.in_jail = False
        player.jail_turns = 0
        for payment in self.session.landing_payments:
            if payment['settled']:
                continue
            if payment['player_id'] == player_id:
                payment['settled'] = True
            elif payment['recipient_id'] == player_id:
                if creditor_id == payment['player_id']:
                    payment['settled'] = True
                else:
                    payment['recipient_id'] = creditor_id
        for grant in self.session.rent_immunity:
            if (grant['grantor_id'] == player_id and creditor is not None
                    and grant['space_index'] in indices and self.session.rules.immunity_follows_deed):
                grant['grantor_id'] = creditor_id
        self.session.rent_immunity[:] = [
            grant for grant in self.session.rent_immunity
            if player_id not in (grant['grantor_id'], grant['beneficiary_id'])
        ]
        destination = creditor.name if creditor is not None else 'the bank'
        self.session.record_transaction('bankruptcy', quote['cash'],
            f'{player.name} surrendered their estate to {destination}',
            from_player_id=player_id, to_player_id=creditor_id)
        self.session.purchase_offer = None
        self.session.turn_roll_indices.clear()
        self.session.turn_ended = True
        remaining = [candidate for candidate in self.session.players if not candidate.bankrupt]
        if creditor is not None:
            for index, amount in quote['interest']:
                if creditor.cash >= amount:
                    self.transfer(amount, from_player_id=creditor_id, kind='mortgage_interest',
                                  space_index=index, description='Bankruptcy mortgage interest')
                else:
                    self.session.landing_payments.append({
                        'player_id': creditor_id, 'space_index': index,
                        'kind': 'mortgage_interest', 'amount': amount,
                        'recipient_id': None, 'settled': False,
                    })
        if len(remaining) == 1:
            self.session.current_turn_index = self.session.players.index(remaining[0])
            self._finalize_winner_if_ready()
        elif creditor is None and indices:
            first, *rest = sorted(indices)
            self.session.bankruptcy_auctions = rest
            self._open_auction(first)
        else:
            self.advance_turn()
        self.session.touch()
        self._emit('bankruptcy_declared', player_id=player_id, creditor_id=creditor_id,
                   winner_id=self.session.winner_id)

    def can_advance_turn(self) -> bool:
        """Require a completed move or jail attempt before ending a turn."""
        player = self.session.current_player
        if self.session.auction is not None or self.session.winner_id is not None:
            return False
        if player is None or player.bankrupt:
            return True
        if self.outstanding_payments(player.player_id):
            return False
        if self.session.turn_ended:
            return True
        if not self.session.turn_roll_indices:
            return False
        roll = self.session.dice_rolls[self.session.turn_roll_indices[-1]]
        if roll.get('source') == 'jail':
            return roll['used_for_move']
        return bool(roll['used_for_move'] and roll['die_one'] != roll['die_two'])

    def can_roll_for_doubles(self, player_id: str) -> bool:
        player = self.session.get_player(player_id)
        return bool(self.session.auction is None and player is self.session.current_player and player.in_jail
                    and not player.bankrupt and not self.session.turn_ended
                    and player.jail_turns < 3
                    and not any(self.session.dice_rolls[i].get('source') == 'jail'
                                for i in self.session.turn_roll_indices))

    def roll_for_doubles(self, player_id: str) -> dict:
        """Attempt jail release once this turn; third failure requires bail."""
        from secrets import randbelow
        if not self.can_roll_for_doubles(player_id):
            raise ValueError('No jail roll available this turn')
        player = self.session.get_player(player_id)
        first, second = randbelow(6) + 1, randbelow(6) + 1
        player.jail_turns += 1
        doubles = first == second
        roll = {'player_id': player_id, 'die_one': first, 'die_two': second,
                'total': first + second, 'source': 'jail',
                'used_for_move': not doubles and player.jail_turns < 3}
        self.session.dice_rolls.append(roll)
        self.session.turn_roll_indices.append(len(self.session.dice_rolls) - 1)
        movement = None
        if doubles:
            self.release_from_jail(player_id, method='doubles')
            movement = self._move(player_id, first + second, dice_total=first + second)
            roll['used_for_move'] = True
            self.session.turn_ended = True
        self.session.touch()
        self._emit('dice_rolled', player_id=player_id, die_one=first,
                   die_two=second, source='jail')
        return {'dice': (first, second), 'movement': movement,
                'bail_required': not doubles and player.jail_turns >= 3}

    def pay_jail_bail(self, player_id: str) -> Optional[MoveResult]:
        """Pay $50 and release the current prisoner; use any jail roll made."""
        player = self.session.get_player(player_id)
        if player is not self.session.current_player or not player.in_jail:
            raise ValueError('Only the current jailed player can pay bail')
        roll = None
        if self.session.turn_roll_indices:
            candidate = self.session.dice_rolls[self.session.turn_roll_indices[-1]]
            if candidate.get('source') == 'jail':
                roll = candidate
        self.release_from_jail(player_id, method='fine')
        if roll is not None:
            movement = self._move(player_id, roll['total'], dice_total=roll['total'])
            roll['used_for_move'] = True
            self.session.turn_ended = True
            return movement
        return None

    def can_roll(self, player_id: str) -> bool:
        """Whether this player is eligible for a fresh roll this turn."""
        try:
            self._validate_next_roll(player_id)
        except (ValueError, KeyError):
            return False
        return True

    def can_move_by_dice(self, player_id: str) -> bool:
        """Whether an existing roll or an eligible manual roll can be moved."""
        try:
            if self._pending_turn_roll(player_id) is not None:
                return True
            self._validate_next_roll(player_id)
        except (ValueError, KeyError):
            return False
        return True

    def _pending_turn_roll(self, player_id: str):
        if self.session.winner_id is not None:
            raise ValueError('The game has ended')
        if self.session.auction is not None:
            raise ValueError('Finish the active auction first')
        player = self.session.get_player(player_id)
        if self.session.current_player is not player:
            raise ValueError('Only the current player can roll or move by dice')
        if self.outstanding_payments(player_id):
            raise ValueError('Pay outstanding rent or tax before rolling or moving again')
        if player.bankrupt or player.in_jail or self.session.turn_ended:
            raise ValueError('Player cannot roll while bankrupt, in jail, or after the turn has ended')
        if self.session.turn_roll_indices:
            roll = self.session.dice_rolls[self.session.turn_roll_indices[-1]]
            if not roll['used_for_move']:
                return roll
        return None

    def _validate_next_roll(self, player_id: str) -> None:
        if self._pending_turn_roll(player_id) is not None:
            raise ValueError('Move using the existing roll before rolling again')
        if self.session.turn_roll_indices:
            roll = self.session.dice_rolls[self.session.turn_roll_indices[-1]]
            if roll['die_one'] != roll['die_two']:
                raise ValueError('This player has already rolled; advance to the next turn')

    def advance_turn(self) -> Optional[Player]:
        """Advance to the next solvent player, skipping bankrupt players."""
        players = self.session.players
        if not players or all(player.bankrupt for player in players):
            return None
        if not self.can_advance_turn():
            raise ValueError('Settle outstanding payments and complete required rolls and movement before advancing the turn')
        for offset in range(1, len(players) + 1):
            index = (self.session.current_turn_index + offset) % len(players)
            if not players[index].bankrupt:
                outgoing = self.session.current_player
                if outgoing is not None:
                    self._tick_immunity(outgoing.player_id, 'turns')
                self.session.purchase_offer = None
                self.session.turn_roll_indices.clear()
                self.session.turn_ended = False
                self.session.current_turn_index = index
                self.session.turn_counts[players[index].player_id] = (
                    self.session.turn_counts.get(players[index].player_id, 0) + 1
                )
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
        payment = self._landing_payment(tenant_id, space_index, 'rent')
        if payment is not None:
            return self._settle_landing_payment(payment, dice_total)
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
        # A developer grant can leave an uneven group. Selling from its tallest
        # property lets the player restore an even group through ordinary sales.
        if max(levels_after) - min(levels_after) > 1 and level < max(self._level(item) for item in group):
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

    def liquidate_building_group(self, player_id: str, space_index: int) -> int:
        """Sell every building in a color group without requiring replacement houses."""
        space, _ = self._owned(player_id, space_index)
        group = self._color_group(space)
        if not all(item.owner_id == player_id and not item.mortgaged for item in group):
            raise ValueError('A complete unmortgaged color group is required')
        if not any(self._level(item) for item in group):
            raise ValueError('No buildings to sell')
        proceeds = 0
        for item in group:
            deed = self._space(item.space_index)
            amount = self._level(item) * (deed.house_cost // 2)
            if not amount:
                continue
            item.houses = 0
            item.hotel = False
            self.transfer(amount, to_player_id=player_id,
                          description=f'Building sale: {deed.name}', kind='building_sale',
                          space_index=item.space_index)
            proceeds += amount
        return proceeds

    def send_to_jail(self, player_id: str) -> Player:
        """Send a nonbankrupt player to Jail without a GO salary award."""
        player = self.session.get_player(player_id)
        if player.bankrupt:
            raise ValueError('Cannot jail a bankrupt player')
        player.position = 10
        player.in_jail = True
        player.jail_turns = 0
        if player is self.session.current_player:
            self.session.purchase_offer = None
            self.session.turn_ended = True
        self.session.touch()
        self._emit('player_jailed', player_id=player_id)
        return player

    def release_from_jail(self, player_id: str, *, method: str = 'fine') -> Player:
        """Release a prisoner by paying $50, using a card or reporting doubles.

        Args:
            player_id: Player in jail.
            method: One of fine, card, or doubles. Doubles release requires
                a qualifying recorded jail roll in the current turn.
        """
        if self.session.auction is not None:
            raise ValueError('Finish the active auction first')
        player = self.session.get_player(player_id)
        if not player.in_jail:
            raise ValueError('Player is not in jail')
        if method == 'fine':
            self.transfer(50, from_player_id=player_id, description='Jail fine')
        elif method == 'card':
            if player.jail_turns >= 3 or any(
                    self.session.dice_rolls[i].get('source') == 'jail'
                    for i in self.session.turn_roll_indices):
                raise ValueError('Use a jail card before attempting doubles')
            if player.get_out_of_jail_cards <= 0:
                raise ValueError('Player has no Get Out of Jail Free cards')
            player.get_out_of_jail_cards -= 1
        elif method == 'doubles':
            roll = (self.session.dice_rolls[self.session.turn_roll_indices[-1]]
                    if self.session.turn_roll_indices else {})
            if not (roll.get('source') == 'jail' and roll.get('player_id') == player_id
                    and roll.get('die_one') == roll.get('die_two')
                    and not roll.get('used_for_move')):
                raise ValueError('A recorded jail doubles roll is required')
        else:
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

    def pay_tax(self, player_id: str, space_index: int) -> Optional[Transaction]:
        """Pay Income Tax ($200) or Luxury Tax ($100) to the bank."""
        payment = self._landing_payment(player_id, space_index, 'tax')
        if payment is not None:
            return self._settle_landing_payment(payment)
        space = self._space(space_index)
        amount = {4: 200, 38: 100}.get(space_index)
        if space.space_type is not SpaceType.TAX or amount is None:
            raise ValueError('No supported tax at this board position')
        return self.transfer(amount, from_player_id=player_id,
                             description=f'Tax: {space.name}', kind='tax',
                             space_index=space_index)
