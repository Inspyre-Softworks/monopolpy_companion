# MonopolPy Companion: Qt desktop dashboard

The optional PySide6 desktop GUI is designed for managing a physical Monopoly
board game. It does not replace the actual board or dice.

## Install and launch

From a checkout on Python 3.10 or newer:

```powershell
python -m pip install -e '.[gui]'
python -m monopolpy_companion.cli --gui
```

Or launch through the installed console script:

```powershell
monopolpy-companion --gui
```

Poetry users: `poetry lock`, `poetry install -E gui`, then
`poetry run monopolpy-companion --gui`.

For the old experimental PySimpleGUI interface:

```powershell
python -m pip install -e '.[legacy-gui]'
monopolpy-companion --legacy-gui
```

The GUI is not required for `from monopolpy_companion import GameEngine`.

## Workflows

See [Player accounts and statistics](ACCOUNTS_AND_STATISTICS.md) for
PIN controls, the dice simulator, financial reports and mortgage planning.

The opening screen presents only **New Game** and **Open Game**; the dashboard
appears after a session is selected. The board uses familiar title-card red,
board green, ivory and property color groups. The app icon is generated from
Qt shapes. See the [Marauder’s Map guide](MARAUDERS_MAP.md) for the separate
parchment fonts and their licenses.


1. Use **New game** to enter the session name and at least two players.
   The new session saves immediately.
2. Select the acting player in the left-hand selector.
3. Use the two dice controls to enter the **actual** physical dice roll;
   **Move by dice** updates board position and GO salary.
4. To buy a property, select its row in the **Board & properties** table
   and choose **Buy property**.
5. To collect rent, select the **tenant** as acting player, select the
   owned deed on the board, then choose **Collect rent**. For utilities,
   the two dice controls supply the total used to compute rent.
6. Use **Transfer money** for player-to-player or bank transfers.
   Transactions appear in the ledger and save automatically.
7. Use the deed controls for mortgages, unmortgages, and even building.
   The headless GameEngine rejects invalid purchases.
8. **Next turn** advances through active players. **Save** saves on demand;
   **Open** restores an existing JSON session.
9. Open **Player account** for a PIN, statistics or multi-deed mortgage quote.
10. Use **Roll dice** to simulate a roll, or **Roll + move** to roll and move.
    The board selects the landed space. **Landing alerts** controls whether
    purchase/rent dialogs appear and is saved per session.
11. Switch between dark and light colors with the named theme button.

All important actions use visible text labels and tooltips; there are no
unlabeled icon-only controls. Screen-reader descriptions are set on custom
buttons and tables. Errors appear as dialogs.

## Architecture

`ui.main_window.MainWindow` handles visual layout and display data.
`ui.dialogs` gathers new session and transfer inputs.
`ui.widgets` defines reusable, self-documenting control classes.
`ui.theme` supplies dark and light palettes.

`SessionController` is UI-neutral and owns the authoritative
`GameEngine` plus a `SessionRepository`. The UI never changes cash,
board position, mortgages or house counts directly.

## Current limitations

- Chance/Community Chest, auctions, loans/trades and full bankruptcy handling
  are not yet automated.
- Doubles/jail release is recorded as a human-verified action rather than a
  complete turn-state machine.
- The new GUI shows a board-space **table** rather than an illustrated board.
  A graphical, selectable Monopoly board can be added later without replacing
  the underlying `GameEngine`.
- Automatic saves follow completed commands, not arbitrary changes made
  directly to GameSession outside SessionController.
- The dashboard is a desktop app; it is not a browser-based client.

## Validation

Headless suite:

```powershell
python -m unittest discover -s tests -v
```

With PySide6 installed, test the Qt view offscreen on Linux:

```bash
QT_QPA_PLATFORM=offscreen python -m unittest tests.test_qt_gui -v
```

On Windows, run the same test without the display environment override.

## Display font and modern purchase feedback

The distinctive lettering in the Monopoly logo is Kabel Heavy, a commercial
font. MonopolPy uses Kabel automatically if it is already installed and
detectable by Qt; otherwise it chooses a similarly geometric installed font
before falling back to a readable system UI font. The Qt dashboard does not require a commercial font binary.

To load a legitimately licensed font from another location, set
`MONOPOLPY_FONT_FILE` to a local TTF or OTF file before starting the GUI:

```powershell
$env:MONOPOLPY_FONT_FILE = 'C:\\Fonts\\Kabel-Heavy.otf'
poetry run monopolpy-companion --gui
```

The redesigned dashboard has a branded header, clean surface cards and a
persistent selected-deed preview. After purchase, it selects the acquired
property, shows the current owner and rent, updates the player's wallet, and
displays a confirmation with the exact paid amount and remaining balance.
Both purchase paths (manual buy and a purchase decision after dice movement)
are covered by offscreen GUI regression tests.
