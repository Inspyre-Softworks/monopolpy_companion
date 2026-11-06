"""Pure mortgage quote calculations for one or several properties."""

from __future__ import annotations

from dataclasses import dataclass

from .models import GameSession, SpaceType


@dataclass(frozen=True)
class MortgageQuote:
    """Immutable total and individual fees for a mortgage operation.

    Attributes:
        operation: mortgage or unmortgage.
        space_indices: Checked and deduplicated owned property indices.
        line_items: Tuples of property name and amount.
        total: Total proceeds (mortgage) or payoff (unmortgage).
        principal_total: Combined mortgage value of the selected deeds.
        interest_total: Combined interest required to unmortgage these deeds.
        payoff_total: Combined principal plus interest for the same deeds.
    """

    operation: str
    space_indices: tuple[int, ...]
    line_items: tuple[tuple[str, int], ...]
    total: int
    principal_total: int = 0
    interest_total: int = 0
    payoff_total: int = 0


class MortgageCalculator:
    """Provide accurate non-mutating mortgage and unmortgage calculations.

    Args:
        session: Current board, deed ownership, and mortgage state.
    """

    def __init__(self, session: GameSession) -> None:
        self.session = session

    def quote(self, player_id: str, space_indices: list[int],
              operation: str = 'unmortgage') -> MortgageQuote:
        """Validate a selection and calculate the full transaction amount.

        Args:
            player_id: Owner of all selected deeds.
            space_indices: Nonempty sequence of distinct board locations.
            operation: mortgage to borrow, unmortgage to repay.

        Returns:
            MortgageQuote with each price and total.

        Raises:
            ValueError: Wrong owner, status, or other rule violation.
        """
        player = self.session.get_player(player_id)
        if player.bankrupt:
            raise ValueError('Bankrupt players cannot manage mortgages')
        if operation not in {'mortgage', 'unmortgage'}:
            raise ValueError('operation must be mortgage or unmortgage')
        if not space_indices:
            raise ValueError('Select one or more properties')
        if len(set(space_indices)) != len(space_indices):
            raise ValueError('Select each property only once')
        board = self.session.board
        items: list[tuple[str, int]] = []
        for index in space_indices:
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(board):
                raise ValueError(f'Invalid board position: {index}')
            space = board[index]
            if not space.ownable:
                raise ValueError(f'{space.name} cannot be mortgaged')
            state = self.session.get_property_state(index)
            if state.owner_id != player_id:
                raise ValueError(f'{player.name} does not own {space.name}')
            if operation == 'mortgage':
                if state.mortgaged:
                    raise ValueError(f'{space.name} is already mortgaged')
                if space.space_type is SpaceType.PROPERTY:
                    group = [
                        self.session.get_property_state(other.index)
                        for other in board if other.color_group == space.color_group
                        and other.space_type is SpaceType.PROPERTY
                    ]
                    if any(item.houses or item.hotel for item in group):
                        raise ValueError(f'Sell buildings in the {space.color_group} group first')
                amount = space.mortgage_value
            else:
                if not state.mortgaged:
                    raise ValueError(f'{space.name} is not currently mortgaged')
                amount = space.mortgage_value + (space.mortgage_value + 9) // 10
            items.append((space.name, amount))
        principal = sum(board[index].mortgage_value for index in space_indices)
        interest = sum((board[index].mortgage_value + 9) // 10 for index in space_indices)
        return MortgageQuote(operation, tuple(space_indices), tuple(items),
                             sum(amount for _name, amount in items),
                             principal, interest, principal + interest)
