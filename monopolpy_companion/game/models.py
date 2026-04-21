from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SpaceType(str, Enum):
    CORNER = "corner"
    PROPERTY = "property"
    RAILROAD = "railroad"
    UTILITY = "utility"
    TAX = "tax"
    CHANCE = "chance"
    COMMUNITY_CHEST = "community_chest"
    GO_TO_JAIL = "go_to_jail"


@dataclass(frozen=True)
class Space:
    index: int
    name: str
    space_type: SpaceType
    price: int = 0
    color_group: Optional[str] = None
    rent_schedule: tuple[int, ...] = ()
    house_cost: int = 0
    mortgage_value: int = 0
    notes: str = ""

    @property
    def ownable(self) -> bool:
        return self.space_type in {SpaceType.PROPERTY, SpaceType.RAILROAD, SpaceType.UTILITY}


@dataclass
class Player:
    name: str
    cash: int = 1500
    token: str = ""
    player_id: str = field(default_factory=lambda: str(uuid4()))
    position: int = 0
    in_jail: bool = False
    jail_turns: int = 0
    get_out_of_jail_cards: int = 0
    bankrupt: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "cash": self.cash,
            "token": self.token,
            "player_id": self.player_id,
            "position": self.position,
            "in_jail": self.in_jail,
            "jail_turns": self.jail_turns,
            "get_out_of_jail_cards": self.get_out_of_jail_cards,
            "bankrupt": self.bankrupt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Player":
        return cls(**data)


@dataclass
class PropertyState:
    space_index: int
    owner_id: Optional[str] = None
    mortgaged: bool = False
    houses: int = 0
    hotel: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "space_index": self.space_index,
            "owner_id": self.owner_id,
            "mortgaged": self.mortgaged,
            "houses": self.houses,
            "hotel": self.hotel,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PropertyState":
        return cls(**data)


@dataclass
class Transaction:
    kind: str
    amount: int
    description: str
    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    from_player_id: Optional[str] = None
    to_player_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "amount": self.amount,
            "description": self.description,
            "transaction_id": self.transaction_id,
            "created_at": self.created_at.isoformat(),
            "from_player_id": self.from_player_id,
            "to_player_id": self.to_player_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        payload = dict(data)
        payload["created_at"] = datetime.fromisoformat(payload["created_at"])
        return cls(**payload)


@dataclass
class GameRules:
    starting_cash: int = 1500
    salary_on_go: int = 200
    free_parking_collects_fees: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "starting_cash": self.starting_cash,
            "salary_on_go": self.salary_on_go,
            "free_parking_collects_fees": self.free_parking_collects_fees,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameRules":
        return cls(**data)


@dataclass
class GameSession:
    name: str
    players: list[Player]
    rules: GameRules = field(default_factory=GameRules)
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    current_turn_index: int = 0
    board_key: str = "standard_us"
    property_states: dict[int, PropertyState] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)
    notes: str = ""
    save_path: Optional[str] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.property_states:
            for space in self.board:
                if space.ownable:
                    self.property_states[space.index] = PropertyState(space_index=space.index)

    @property
    def board(self) -> list[Space]:
        from .board import build_standard_board

        if self.board_key != "standard_us":
            raise ValueError(f"Unsupported board: {self.board_key}")
        return build_standard_board()

    @property
    def current_player(self) -> Optional[Player]:
        if not self.players:
            return None
        return self.players[self.current_turn_index % len(self.players)]

    def touch(self) -> None:
        self.updated_at = utc_now()

    def add_player(self, name: str, token: str = "") -> Player:
        player = Player(name=name.strip(), cash=self.rules.starting_cash, token=token.strip())
        self.players.append(player)
        self.touch()
        return player

    def remove_player(self, player_id: str) -> None:
        self.players = [player for player in self.players if player.player_id != player_id]
        if self.players:
            self.current_turn_index %= len(self.players)
        else:
            self.current_turn_index = 0
        self.touch()

    def get_player(self, player_id: str) -> Player:
        for player in self.players:
            if player.player_id == player_id:
                return player
        raise KeyError(f"Unknown player_id: {player_id}")

    def get_property_state(self, space_index: int) -> PropertyState:
        try:
            return self.property_states[space_index]
        except KeyError as exc:
            raise KeyError(f"Space {space_index} is not ownable") from exc

    def owner_for(self, space_index: int) -> Optional[Player]:
        state = self.get_property_state(space_index)
        if state.owner_id is None:
            return None
        return self.get_player(state.owner_id)

    def owned_spaces_for(self, player_id: str) -> list[Space]:
        owned_indexes = {
            state.space_index
            for state in self.property_states.values()
            if state.owner_id == player_id
        }
        return [space for space in self.board if space.index in owned_indexes]

    def advance_turn(self) -> Optional[Player]:
        if not self.players:
            return None
        self.current_turn_index = (self.current_turn_index + 1) % len(self.players)
        self.touch()
        return self.current_player

    def record_transaction(
        self,
        kind: str,
        amount: int,
        description: str,
        from_player_id: Optional[str] = None,
        to_player_id: Optional[str] = None,
    ) -> Transaction:
        transaction = Transaction(
            kind=kind,
            amount=amount,
            description=description,
            from_player_id=from_player_id,
            to_player_id=to_player_id,
        )
        self.transactions.append(transaction)
        self.touch()
        return transaction

    def transfer_cash(
        self,
        amount: int,
        description: str,
        from_player_id: Optional[str] = None,
        to_player_id: Optional[str] = None,
    ) -> Transaction:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        if from_player_id is not None:
            payer = self.get_player(from_player_id)
            payer.cash -= amount
        if to_player_id is not None:
            payee = self.get_player(to_player_id)
            payee.cash += amount
        return self.record_transaction(
            kind="cash_transfer",
            amount=amount,
            description=description,
            from_player_id=from_player_id,
            to_player_id=to_player_id,
        )

    def buy_property(self, player_id: str, space_index: int) -> PropertyState:
        player = self.get_player(player_id)
        space = self.board[space_index]
        if not space.ownable:
            raise ValueError(f"{space.name} is not ownable")
        state = self.get_property_state(space_index)
        if state.owner_id is not None:
            raise ValueError(f"{space.name} is already owned")
        if player.cash < space.price:
            raise ValueError(f"{player.name} does not have enough cash to buy {space.name}")

        player.cash -= space.price
        state.owner_id = player.player_id
        self.record_transaction(
            kind="purchase",
            amount=space.price,
            description=f"{player.name} bought {space.name}",
            from_player_id=player.player_id,
        )
        self.touch()
        return state

    def summary_lines(self) -> list[str]:
        lines = [
            f"Session: {self.name}",
            f"Players: {len(self.players)}",
            f"Current turn: {self.current_player.name if self.current_player else 'N/A'}",
            f"Transactions logged: {len(self.transactions)}",
        ]
        for player in self.players:
            owned = self.owned_spaces_for(player.player_id)
            lines.append(f"- {player.name}: ${player.cash} | position {player.position} | assets {len(owned)}")
        return lines

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "players": [player.to_dict() for player in self.players],
            "rules": self.rules.to_dict(),
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_turn_index": self.current_turn_index,
            "board_key": self.board_key,
            "property_states": {
                str(space_index): state.to_dict()
                for space_index, state in self.property_states.items()
            },
            "transactions": [transaction.to_dict() for transaction in self.transactions],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameSession":
        payload = dict(data)
        payload["players"] = [Player.from_dict(player) for player in payload["players"]]
        payload["rules"] = GameRules.from_dict(payload["rules"])
        payload["created_at"] = datetime.fromisoformat(payload["created_at"])
        payload["updated_at"] = datetime.fromisoformat(payload["updated_at"])
        payload["property_states"] = {
            int(space_index): PropertyState.from_dict(state)
            for space_index, state in payload.get("property_states", {}).items()
        }
        payload["transactions"] = [
            Transaction.from_dict(transaction)
            for transaction in payload.get("transactions", [])
        ]
        return cls(**payload)


def create_standard_session(
    name: str,
    player_names: list[str],
    starting_cash: int = 1500,
) -> GameSession:
    rules = GameRules(starting_cash=starting_cash)
    players = [Player(name=player_name.strip(), cash=starting_cash) for player_name in player_names if player_name.strip()]
    if len(players) < 2:
        raise ValueError("At least two players are required to start a Monopoly session")
    session = GameSession(name=name.strip() or "New Monopoly Session", players=players, rules=rules)
    session.record_transaction(
        kind="session_created",
        amount=0,
        description=f"Created session '{session.name}' with {len(players)} players",
    )
    return session
