"""Historical per-player statistics built from the persisted game ledger."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from typing import Any

from .models import GameSession


@dataclass(frozen=True)
class GameplayStatistics:
    """Gameplay measures for one player in a saved session."""

    dice_rolls: int = 0
    doubles_rolled: int = 0
    total_spaces_moved: int = 0
    total_properties_purchased: int = 0
    turns_started: int = 0
    times_passed_go: int = 0
    average_dice_total: float = 0.0
    games_played: int = 0
    games_completed: int = 0
    games_won: int = 0
    bankruptcies: int = 0


@dataclass
class FinancialStatistics:
    """Player income and spending separated by recorded transaction type."""

    total_money_spent: int = 0
    total_taxes_paid: int = 0
    total_other_events_paid: int = 0
    total_property_purchases: int = 0
    total_player_deals_paid: int = 0
    rent_paid: int = 0
    rent_earned: int = 0
    rent_paid_by_player: dict[str, int] = field(default_factory=dict)
    rent_earned_by_player: dict[str, int] = field(default_factory=dict)
    rent_paid_by_property: dict[str, int] = field(default_factory=dict)
    rent_earned_by_property: dict[str, int] = field(default_factory=dict)
    average_rent_paid_per_turn: float = 0.0
    average_rent_earned_per_turn: float = 0.0


@dataclass
class PlayerReport:
    """Gameplay and financial reports plus current player cash and net assets."""

    player_id: str
    name: str
    cash: int
    owned_properties: int
    gameplay: GameplayStatistics
    finance: FinancialStatistics


class StatisticsService:
    """Calculate persisted player reports without requiring the GUI.

    Args:
        session: Readable Monopoly game state, including historic transactions.

    Notes:
        Counts from old saves can be partial: past movement and precise rent
        breakdowns did not exist until the account statistics schema was added.
        Average-per-turn uses turns started, including the active turn.
    """

    def __init__(self, session: GameSession) -> None:
        self.session = session

    def _property_name(self, index: int | None, description: str) -> str:
        """Resolve property names, including legacy transactions without an index."""
        board = self.session.board
        if index is not None and 0 <= index < len(board):
            return board[index].name
        if ':' in description:
            return description.split(':', 1)[1].strip()
        if ' bought ' in description:
            return description.split(' bought ', 1)[1]
        return 'Unknown property'

    @staticmethod
    def _add(mapping: dict[str, int], key: str, amount: int) -> None:
        mapping[key] = mapping.get(key, 0) + amount

    def for_player(self, player_id: str) -> PlayerReport:
        """Return a financial and gameplay breakdown for one player."""
        player = self.session.get_player(player_id)
        turns = self.session.turn_counts.get(player_id, 0)
        roll_history = [
            roll for roll in self.session.dice_rolls
            if roll.get('player_id') == player_id
        ]
        movement = [
            action for action in self.session.movement_history
            if action.get('player_id') == player_id
        ]
        purchases = 0
        finance = FinancialStatistics()
        for transaction in self.session.transactions:
            from_id = transaction.from_player_id
            to_id = transaction.to_player_id
            if from_id != player_id and to_id != player_id:
                continue
            kind = transaction.kind
            if kind == 'cash_transfer':
                if transaction.description.startswith('Rent:'):
                    kind = 'rent'
                elif transaction.description.startswith('Tax:'):
                    kind = 'tax'
            if from_id == player_id:
                finance.total_money_spent += transaction.amount
                if kind == 'tax':
                    finance.total_taxes_paid += transaction.amount
                elif kind in {'purchase', 'auction_purchase'}:
                    finance.total_property_purchases += transaction.amount
                    purchases += 1
                elif kind == 'deal':
                    finance.total_player_deals_paid += transaction.amount
                elif kind == 'rent':
                    finance.rent_paid += transaction.amount
                    counterparty = self.session.get_player(to_id).name if to_id else 'Bank'
                    self._add(finance.rent_paid_by_player, counterparty, transaction.amount)
                    self._add(finance.rent_paid_by_property,
                              self._property_name(transaction.space_index,
                                                  transaction.description), transaction.amount)
                elif kind in {'event', 'cash_transfer'}:
                    finance.total_other_events_paid += transaction.amount
            if to_id == player_id and kind == 'rent':
                finance.rent_earned += transaction.amount
                counterparty = self.session.get_player(from_id).name if from_id else 'Bank'
                self._add(finance.rent_earned_by_player, counterparty, transaction.amount)
                self._add(finance.rent_earned_by_property,
                          self._property_name(transaction.space_index,
                                              transaction.description), transaction.amount)
        finance.average_rent_paid_per_turn = finance.rent_paid / turns if turns else 0.0
        finance.average_rent_earned_per_turn = finance.rent_earned / turns if turns else 0.0
        gameplay = GameplayStatistics(
            games_played=1,
            games_completed=int(self.session.winner_id is not None),
            games_won=int(self.session.winner_id == player_id),
            bankruptcies=int(player.bankrupt),
            dice_rolls=len(roll_history),
            doubles_rolled=sum(r['die_one'] == r['die_two'] for r in roll_history),
            total_spaces_moved=sum(int(m['spaces']) for m in movement),
            total_properties_purchased=purchases,
            turns_started=turns,
            times_passed_go=sum(bool(m.get('passed_go')) for m in movement),
            average_dice_total=(
                sum(int(r['total']) for r in roll_history) / len(roll_history)
                if roll_history else 0.0
            ),
        )
        return PlayerReport(
            player_id, player.name, player.cash,
            len(self.session.owned_spaces_for(player_id)),
            gameplay, finance,
        )

    @staticmethod
    def overall(current: PlayerReport, history: list[PlayerReport]) -> PlayerReport:
        """Combine distinct game reports, weighting averages by rolls or turns."""
        reports = [current, *history]
        counts = {
            item.name: sum(getattr(report.gameplay, item.name) for report in reports)
            for item in fields(GameplayStatistics) if item.name != 'average_dice_total'
        }
        rolls = counts['dice_rolls']
        roll_total = sum(report.gameplay.average_dice_total * report.gameplay.dice_rolls
                         for report in reports)
        gameplay = GameplayStatistics(**counts, average_dice_total=roll_total / rolls if rolls else 0)
        finance = FinancialStatistics()
        for item in fields(FinancialStatistics):
            if item.name.startswith('average_'):
                continue
            total = getattr(finance, item.name)
            if isinstance(total, dict):
                for report in reports:
                    for name, amount in getattr(report.finance, item.name).items():
                        StatisticsService._add(total, name, amount)
            else:
                setattr(finance, item.name, sum(getattr(report.finance, item.name) for report in reports))
        turns = gameplay.turns_started
        if turns:
            finance.average_rent_paid_per_turn = finance.rent_paid / turns
            finance.average_rent_earned_per_turn = finance.rent_earned / turns
        return replace(current, gameplay=gameplay, finance=finance)
