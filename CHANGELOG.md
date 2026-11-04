# Changelog

All notable changes to this project should be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
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

### Changed
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
