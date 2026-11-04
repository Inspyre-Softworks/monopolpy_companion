# MonopolPy Companion

A reusable Python library for managing money, property ownership, movement,
rent, mortgages, buildings, and save files while playing **physical Monopoly**.
The Monopoly-styled PySide6 desktop dashboard is optional, with PIN-protected
player accounts, statistics, a dice simulator and a mortgage calculator.
The old PySimpleGUI
shell remains available for migration.

**Python:** 3.10+ | **Logging:** InspyLogger 3.x | **Version:** 1.0.dev7

Headless library: `python -m pip install .`

Qt desktop GUI: `python -m pip install '.[gui]'`

Run dashboard: `monopolpy-companion --gui`

Old GUI: `python -m pip install '.[legacy-gui]'`, then
`monopolpy-companion --legacy-gui`

On Windows, the dashboard can also be launched with
`python -m monopolpy_companion.cli --gui`.

```python
from monopolpy_companion import GameEngine, SessionRepository, create_standard_session

session = create_standard_session('Game Night', ['Avery', 'Blake'])
engine = GameEngine(session)
engine.purchase(session.players[0].player_id, 1)
engine.move_by_dice(session.players[0].player_id, 2, 3)
SessionRepository().save(session)
```

See [Accounts and statistics](docs/ACCOUNTS_AND_STATISTICS.md),
[Desktop GUI guide](docs/GUI.md), [Library API](docs/LIBRARY_API.md),
[Architecture](docs/LIBRARY_ARCHITECTURE.md),
and the [playable companion roadmap](docs/PLAYABLE_COMPANION_ROADMAP.md).

## Original project notes

[![Updates](https://pyup.io/repos/github/Inspyre-Softworks/monopolpy_companion/shield.svg)](https://pyup.io/repos/github/Inspyre-Softworks/monopolpy_companion/) [![Python 3](https://pyup.io/repos/github/Inspyre-Softworks/monopolpy_companion/python-3-shield.svg)](https://pyup.io/repos/github/Inspyre-Softworks/monopolpy_companion/)



The MonopolPy Companion App aims to provide useful utilities that will help you get more out of the awesome game of Monopoly.

* peace of mind:
     - Banker: no more human bankers trying to do math 3 hours into a session. lament no more as the driving feature of this application is an automatic bank teller! This feature will include:
         
       * User money tracker: I know we all love those multicolored cat attractant, table-clinging bits of joy known as Monopoly-money, but cats, kids, entropy. This is where MC will step-in acting as the wallet for all this session's players. This will include the option to PIN or password protect your transactions for that play-session in order to ensure fairness for times when you may happen to be away from the board ( and therefore your monies)
           
       * Bank Asset Manager & Player Asset Tracker (BAM and PAT) (both can toggle on.off prior to starting of the game): The program can manage the deeds in the game including mortgages and the proper amount in order to pay one or more mortgaged properties off/how much you'll borrow upon mortgaging one or more properties.
         * Automatic Auction Manager: self-explanatory
         * Keeps logs of all transactions

     - Wallet: MC will have the ability to keep track of the players' session-wallet (if that's a feature you enable in the Start screen). This ensures:
       * All transactions get logged, and are reviewable at any time during the session, by any player
       * An option to pin-secure or password-secure one's transactions is made available
       * The deeds (including information like what they're worth, etc) will be tracked
       * Unlocks the Monopoly Asset Calculator(B-Priority)
       
     - Monopoly Asset Calculator: Use this nifty calculator for figuring out what your next move is(B-Priority)
     
     - Enhanced Private Trading Mediator:
       * Users can trade:
         - Rent immunity
         - Get out of jail cards
         - Properties
         - Loans

     

