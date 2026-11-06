# Changelog

All notable changes to this project should be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Discover independently installed plugins and enable compatible extensions for the desktop session.

### Added
- Unlock the hidden Marauder’s Map to grant cash, unowned deeds, houses, and hotels with ledger entries.

### Added
- Show who paid and who received each entry in the transaction ledger.

### Added
- View current, saved-game, and overall player statistics, including wins and bankruptcies.

### Added
- Declare bankruptcy on unpayable debt, transfer the estate or auction bank-repossessed deeds, and record the winner.

### Added
- Show property color swatches in the mortgage and unmortgage lists.

### Changed
- Center the title and supporting text in the dashboard banner.

### Changed
- Use Metro Retro NF for the dashboard title when the font is installed or present in the local fonts folder.

### Added
- Quick Actions panel for the current roll, landing, payments, jail, trades, and turn progression.
- Saved auctions with turn-based bidding, cash validation, and automatic deed settlement.

### Added
- Show up to four green house bars or a centered red hotel bar on property tiles.

### Added
- Trade rent immunity by rent charge, GO crossing, or completed turn, with optional deed transfer.
- Show player names and cash plus printed deed values in trade offers.

### Added
- Show each deed’s printed price and color in trade window tooltips.

### Fixed
- Show the property name immediately when hovering over an ownership tile.

### Added
- Three consecutive doubles in a turn send the player directly to Jail without
  movement or GO salary; Game Settings can disable this rule per saved game.
- Direct multi-property mortgage planner with live proceeds, principal, interest,
  total unmortgage cost and resulting balance previews before confirmation.
- Reviewed two-player trades for cash, deeds and jail cards, with both-player
  PIN authorization, mortgage interest quotes and immediate tracker updates.
- Per-player property ownership strips with all 28 deeds, mortgage crosses,
  gold complete-set outlines and current-turn highlighting.
- Two-pane dashboard with ownership and game controls beside an independently
  scrollable full transaction log.
- Saved landing rent and tax charges with visible amounts owed and a payment
  control that settles each charge once.
- Jail-only doubles attempts with a saved three-attempt counter and $50 bail
  release controls; the third failed roll must be paid before moving.
- Game Settings window for changing the automatic GO salary per saved game,
  disabling salary, or doubling it on an exact GO landing.
- Gold notifications showing automatic GO salary payments and updated balances.
- Reusable local accounts with username availability checks, optional encrypted
  account files and transaction PINs, and account selection during game setup.
- Styled title bar, animated button glow and saved desktop preferences.

- Modern card-based desktop layout, prominent deed ownership panel,
  selected player wallet summary, and successful-purchase confirmation.
- Kabel Heavy font detection when installed, with geometric typography
  fallbacks and user-licensed font-file loading via MONOPOLPY_FONT_FILE.
- Qt smoke tests for purchasing after landing and using the buy button,
  including ownership, balance, ledger and persisted save verification.
- PIN-lockable player accounts using salted one-way hashes and session-scoped unlocks.
- Persisted gameplay and financial reports, rent breakdowns by player and deed,
  and virtual dice rolls with per-player statistics.
- Per-player, multi-property mortgage and unmortgage calculator with total quotes.
- Monopoly-inspired light/dark styling, a generated icon, and simpler game startup.
- Dice-landing board highlighting with optional purchase/rent prompts.
- A Qt/PySide6 desktop dashboard with session setup, save/load, banker,
  dice movement, board/deed overview, rent, mortgages, building controls,
  jail actions, and transaction history.
- Reusable UI widgets with explicit labels, tooltips and accessible descriptions,
  plus light and dark themes.
- A GUI-independent SessionController that coordinates state, events and autosave.
- Qt offscreen smoke tests and a dedicated optional GUI CI job.
- A headless GameEngine with validated banking, board movement, rent,
  mortgages, buildings, jail actions and completed-action subscriptions.
- Atomic SessionRepository with original save-format compatibility.
- Public library API and architecture documentation for the planned GUI.
- Headless CLI commands for listing and summarizing saved sessions.
- Automated library unit-test workflow across Python 3.10, 3.12 and 3.13.

### Fixed
- Keep Next turn disabled while the current player owes rent or tax, including
  after reopening the game; block extra rolls until those charges are settled.
- Disable Next turn until required rolls and moves are complete, including
  extra rolls earned through doubles.
- Enforce one roll per turn unless doubles earn another, and preserve pending
  rolls and turn eligibility when saving and reopening a game.
- Select the incoming player after advancing a turn so subsequent rolls and
  movement apply to the correct player; restore the current player on game load.
- Keep player balances, board ownership and ledger rows current after repeated actions.

### Changed
- Updated packaging version to 1.0.dev17.
- Updated packaging version to 1.0.dev16.
- Wrap property groups onto two lines, blend empty tiles into the panel
  background and enlarge player cash totals.
- Updated packaging version to 1.0.dev15.
- Updated packaging version to 1.0.dev14.
- Updated packaging version to 1.0.dev13.
- Updated packaging version to 1.0.dev12.
- Updated packaging version to 1.0.dev11.
- Updated packaging version to 1.0.dev10.
- Updated packaging version to 1.0.dev9.

- Restyled tables, panels, toolbars and controls for a contemporary layout.
- Updated packaging version to 1.0.dev8.
- Updated packaging to version 1.0.dev7 and registered the Poetry CLI script.
- Bumped both package metadata files to 1.0.dev6.
- Made the Qt dashboard the --gui entry point and retained the original shell
  under --legacy-gui with its own optional dependencies.
- Updated InspyLogger integration to the current 3.x API.
- Made experimental GUI dependencies optional instead of core requirements.
- Updated package metadata and Python floor, synchronizing version 1.0.dev5.
- Routed legacy save/load helpers through atomic repository storage.

### Fixed
- Exported the public engine, repository, session factory and models from the
  package root so direct imports work in notebooks and applications.
- Prevented a failing session write from truncating a previous good save.
- Prevented invalid engine transfers from changing balances or ledger records.

## Prior work

See the Git history for the earlier 1.0.dev4 changelog and release notes.
