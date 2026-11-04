# Library architecture

The package separates domain data, game operations, persistence, logging and UI.

```text
GUI (next phase) / CLI / third-party integrations
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

## Next phase: desktop controller

Introduce a `SessionController` that owns the engine and repository, handles
autosave on successful events, translates errors for display, and exposes
read-only view models. The GUI should not call `GameSession.transfer_cash`,
`GameSession.buy_property` or `GameSession.advance_turn` directly. Keep
rules and transactions in the library so unit tests remain headless.
