# MonopolPy Companion

A reusable Python library for managing money, property ownership, movement,
rent, mortgages, buildings, and save files while playing **physical Monopoly**.
The optional PySide6 dashboard uses a board-inspired card layout with PIN-protected
player accounts, statistics, a dice simulator, a mortgage calculator, and visible
purchase confirmations. The old PySimpleGUI shell remains available for migration.

The dashboard title uses Metro Retro NF when installed. You can also place
`MetroRetroNF.ttf` in the app data folder at
`Documents/Games/Monopolpy_Companion/fonts` to use it without installing it
system-wide. [Metro Retro NF by Nick Curtis](https://www.1001fonts.com/metro-retro-font.html)

**Python:** 3.10+ | **Logging:** InspyLogger 3.x | **Version:** 1.0.dev8

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

     



### Local accounts and desktop preferences

Use **Create Account** to register a reusable username, optional encryption
password and optional 4–8 digit transaction PIN. New Game offers existing
accounts in a dropdown; select each account and click **Add selected account**.
Guest names can still be entered in the Players field. Passwords unlock account
files once per application session. PINs authorize transactions separately.

Account files use authenticated AES-GCM encryption with password-derived scrypt
keys when a password is supplied. Every account write keeps that encryption.
Usernames remain visible for account selection. Game saves are separate,
unencrypted JSON files; PINs protect casual terminal access rather than tampering
with save files. There is no password recovery.

**Settings** saves the theme, animated button glow and default landing alerts
between launches. The styled title bar supports dragging, double-click maximize,
minimize, restore and close; the bottom corner provides a resize grip.


**Game Settings** applies to the active saved game: GO salary defaults to $200;
set it to $0 to disable it. The optional **Double salary when landing on GO**
house rule defaults off and pays twice that amount on an exact landing only.
Salary payments appear in the ledger and in a gold notification for ten seconds.
Moves explicitly excluding GO collection and being sent directly to Jail do not
pay salary.

Dice rolls follow the current turn: use a simulated roll before rolling again.
After moving, another roll requires doubles. Pending dice and turn eligibility
are saved with the game; Next turn makes the incoming player eligible to roll.


When the current player is in Jail, **Roll for doubles** shows attempts used
out of three, and **Pay $50 bail and release** offers an immediate paid exit.
Just visiting does not show these controls. Each jail turn permits one attempt;
a failed first or second attempt allows Next turn. Doubles release and move the
player without earning another roll. After the third failed attempt, pay bail
before moving by that saved third roll. Paying before attempting doubles allows
a normal roll. Insufficient cash leaves the player in Jail until payment is
possible. An owned jail release card can be used before attempting doubles.

Next turn stays disabled until the current player has completed required dice
movement, including extra rolls earned by doubles, or completed a jail attempt.
Being sent to Jail ends the turn immediately.


Landing on tax or an opponent's unmortgaged deed records an unpaid charge.
**Amount owed** and **Pay amount owed** show and settle the charge; existing
Pay tax and Collect rent actions settle the same charge without charging twice.
Next turn and further dice rolls stay disabled until rent and tax are paid.
Charges survive save/load and retain the rent quote from the landing, including
utility dice totals. Turning off landing alerts does not waive payment.
Manual transfers are separate transactions and do not silently dismiss a charge.


### Property ownership dashboard

The left pane stacks a horizontal ownership tracker for each player, with their
name and cash at the left and a highlighted row for the current turn. Each panel arranges groups across two lines and
shows the eight color sets, then four black Railroads and two gray Utilities;
properties follow board order within their group. Empty rectangles match the panel background and have thick
set-colored borders; owned deeds are solid, and mortgaged deeds are dimmed with
an X. A gold outline surrounds every fully owned group, including Railroads and
Utilities (mortgages do not remove ownership). Hover over a rectangle for its
property name and status. The strips scroll horizontally on smaller windows.

The right pane is an independently scrollable transaction log, newest first,
with all recorded transactions. Players & banker and Board & properties tabs
keep the game controls below the ownership trackers. Purchases, mortgages,
unmortgages, saved-game loads and turn changes refresh the trackers immediately.


**Trade** opens a two-player cash, property and jail-card exchange. Review each
side, bank mortgage-interest charges and resulting balances before confirming.
Both players must unlock their PINs if enabled. Mortgaged deeds stay mortgaged;
the recipient pays 10% mortgage interest. Sell buildings across a color group
before trading any property in it. Trades are validated together before changes,
autosaved and logged, and refresh both ownership trackers. Trades do not cancel
existing rent or tax obligations. These restrictions follow the
[classic Hasbro rules](https://www.hasbro.com/common/instruct/Monopoly.pdf).


**Mortgages** opens the selected player's multi-property planner directly.
Choose Mortgage or Unmortgage and click each deed to select multiple properties.
The live preview shows individual amounts, total proceeds, the full cost to
unmortgage those same deeds (principal plus interest), and cash after applying.
Unmortgage previews show the total repayment and resulting balance; unaffordable
selections cannot be applied. Confirm the itemized preview to commit the batch.
The Board & properties tab also provides Mortgage properties and Unmortgage
properties shortcuts to this planner.


Game Settings enables **Three consecutive doubles send the player directly to
Jail** by default. The third double ends the turn immediately, without moving
by that roll or collecting GO salary. Uncheck this option to disable the rule
for the active saved game. Both manual dice entry and simulated rolls enforce
it; the consecutive-double count survives saving and reopening mid-turn.
