# Library architecture

The package separates domain data, game operations, persistence, logging and UI.

```text
Qt GUI / CLI / third-party integrations
                 |
           SessionController
              |          |
              |     SessionRepository ---> JSON saves
              |
              GameEngine  ---> GameEvent subscribers
                 |
              GameSession ---> Player, PropertyState, Transaction
                 |
               Board (40 immutable space definitions)

SessionRepository ---> version-compatible JSON save files
       |
  legacy storage facade
```

The direction of dependencies is important: code under `game/` must never
import GUI modules. The GUI can depend on the library, not vice versa.

- `game.models`: Serializable state and the existing compatibility API.
- `game.board`: Static United States standard Monopoly board definitions.
- `game.engine`: Banking, movement, rent, mortgage and buildings policy.
- `game.events`: Immutable notification envelope for completed operations.
- `game.repository`: Atomic persistence, load and browse.
- `game.logging`: Lazy InspyLogger 3.x configuration.
- `game.storage`: Backward-compatible persistence facade.
- `cli`: Small script entry point, with lazy GUI import.

## Design constraints

1. All money values are integer Monopoly dollars. No floating point prices.
2. All operations validate input and available funds before changing state.
3. The UI observes after completed actions; it does not implement rules.
4. Existing game JSON stays compatible. Add schema migration before making
   future incompatible changes to the persisted structure.
5. A standalone library install does not require PySimpleGUI.
6. Logger import must not create GUI or write log files implicitly.
7. New modules should use typed interfaces, single-quoted Python strings and
   Google-style docstrings, with standard unittest regression tests.

## Desktop integration

`SessionController` owns the session, engine and persistence. Its
`perform()` operation validates the supported action, runs the headless
engine, autosaves and then sends a completed-action notification to observers.
The Qt `MainWindow` and input dialogs only collect and render data;
they never call `GameSession.transfer_cash`, `GameSession.buy_property`
or `GameSession.advance_turn` directly.

Desktop widgets use descriptive text, tooltips and accessible names, with
two selectable stylesheet palettes. The old GUI remains isolated as an
optional legacy entry point. See [Desktop GUI guide](GUI.md).

Next work: fully automate decks, auctions, trading, bankruptcy resolution
and the complete jail/turn policy while keeping those rules in `game/`.
