# MonopolPy Companion: headless library API

This is a package for assisting a **physical Monopoly board game**, not a digital
simulation. The game package can be imported without opening the GUI.

## Install

For headless library use:

    python -m pip install .

For the new desktop GUI:

    python -m pip install '.[gui]'
    monopolpy-companion --gui

The original PySimpleGUI shell uses `pip install '.[legacy-gui]'`
and `monopolpy-companion --legacy-gui`. The headless library does not
depend on either GUI toolkit.

Requires Python 3.10+ and InspyLogger 3.x. Poetry users may install the
new desktop extra with `poetry install -E gui` after refreshing the
Poetry lockfile for updated dependency metadata.

## Quick start

```python
from monopolpy_companion.game import (
    GameEngine, SessionRepository, create_standard_session
)

session = create_standard_session('Friday Monopoly', ['Avery', 'Blake'])
engine = GameEngine(session)
avery, blake = session.players

unsubscribe = engine.subscribe(lambda event: print(event.name, event.details))
engine.purchase(avery.player_id, 1)
engine.transfer(50, from_player_id=blake.player_id,
                to_player_id=avery.player_id, description='House rule payment')
print(engine.rent_due(1))  # 2 without the second brown property
repository = SessionRepository('./saves')
path = repository.save(session)
reopened = repository.load(path)
print(reopened.summary_lines())
unsubscribe()
```

## Public types

| Type | Responsibility |
| --- | --- |
| `GameSession` | Serializable state: players, turn, properties, transactions, rules |
| `GameRules` | Starting cash, GO salary, Free Parking option |
| `Player` | A player identity, cash, token, position and jail status |
| `Space` / `SpaceType` | Immutable definition of a board square |
| `PropertyState` | Owner, mortgage and house/hotel state |
| `Transaction` | Timestamped auditable ledger entry |
| `GameEngine` | Validated mutations and calculations; UI-independent |
| `GameEvent` | Completed-action notification for subscribed observers |
| `MoveResult` | Landing position and pass-GO metadata |
| `SessionRepository` | Atomic JSON persistence and saved-session browsing |

Imports from `monopolpy_companion.game` are the supported entry point. The
earlier `game.models` and `game.storage` imports remain compatible.

## GameEngine operations

| API | Behavior |
| --- | --- |
| `transfer(amount, from_player_id=..., to_player_id=...)` | Bank or player transfers with insufficient-funds checks |
| `purchase(player_id, space_index)` | Buy unowned deed at face value |
| `move(player_id, spaces)` | Cross GO, pay salary, handle Go To Jail |
| `move_by_dice(player_id, first_die, second_die)` | Validated 2d6 move |
| `advance_turn()` | Skip bankrupt players |
| `rent_due(space_index, dice_total=...)` | Monopoly, railroad, utility and developed-property rent |
| `collect_rent(tenant_id, space_index, dice_total=...)` | Pay owner and record in ledger |
| `mortgage(player_id, space_index)` | Mortgage with no developed buildings in group |
| `unmortgage(player_id, space_index)` | Pay principal plus rounded-up 10% interest |
| `buy_building(player_id, space_index)` | Buy evenly, obey 32-house and 12-hotel limits |
| `sell_building(player_id, space_index)` | Sell evenly at half cost |
| `send_to_jail(player_id)` | Set jail state and move to index 10 |
| `release_from_jail(player_id, method=...)` | Fine, stored card or verified doubles |
| `pay_tax(player_id, space_index)` | Printed tax on indices 4 and 38 |
| `subscribe(handler)` | Receive GameEvent instances; returns unsubscribe callback |

Except for explicitly optional results, invalid operations raise `ValueError`
or `KeyError` before modifying cash/deeds. Calls that transfer cash emit a
`cash_transferred` event, followed by any higher-level event.

## GUI integration contract

The new Qt GUI uses `SessionController` to manage a GameSession,
GameEngine, SessionRepository and automatic saving after actions.
Its `perform(action, ...)` method restricts commands to the supported
game operations, dispatching events only once each action is complete.
Observer failures are logged without aborting a game operation. A
`SessionSaveError` specifically means the game action succeeded but
its save failed. Applications can inject an InspyLogger-compatible logger.

The engine is synchronous, not thread-safe, and should be called from one
game-state controller. For consistency, do not bypass its operations by
mutating GameSession dataclasses directly.

## Persistence

`SessionRepository(directory)` saves in the same JSON schema as the existing
GUI and uses a temporary file plus atomic rename. The original `save_session`,
`load_session`, and `list_saved_sessions` functions forward to the repository.
`save_path` is updated only after a successful save. No automatic saving is performed directly by GameEngine. SessionController
autosaves completed actions, with observer notifications after saving.

CLI: `monopolpy-companion --list-sessions` or
`monopolpy-companion --summary path/to/session.json`.

## Not yet automated

Chance/Community Chest decks, auctions, property trades, full bankruptcy
settlements, rent immunity/loans, PIN authentication, full jail-turn/doubles
sequencing, and rule presets are future modules. Do not present their outcomes
as automatically resolved by this foundation. The existing experimental GUI
remains available separately. See [GUI guide](GUI.md).
