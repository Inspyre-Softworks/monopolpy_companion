# Changelog

All notable changes to this project should be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project aims to follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Contributor workflow documentation in `CONTRIBUTING.md`.
- Repository-level assistant guidance for Copilot, Codex, and Sourcery.
- A release hygiene policy requiring changelog updates and version bumps for code changes merged to `master`.
- Error handling in the Load Saved Session dialog: a "Failed to load session" popup is shown when a save file cannot be read.
- Error handling for the Save Session action: a "Failed to save session" popup is shown on I/O failure; shows "Session saved." on success.
- Error handling for the Advance Turn autosave: shows "Turn advanced, but autosave failed." if the autosave write fails.

### Changed
- Added PR workflow guidance that makes changelog and version checks part of the normal review process.
- "No saved sessions were found yet." popup text updated to "No saved sessions found." to align with the session flow specification.
- "No active session" and "No active session to save" popup texts tightened to match the session flow specification.

### Fixed
- Synchronized package metadata to use the same version in `pyproject.toml` and `setup.py`.
- `save_session` now calls `expanduser()` on caller-supplied paths so tilde (`~`) paths resolve correctly.
- Corrected relative import level in `pm_wins/add_new.py` so `popups.alerts` is found without an `ImportError`.
- Removed unused `Path` import from `lib/common/state.py`.
- `run.py` now imports the `application` module directly and calls `app_win.window()` to avoid a `TypeError` at GUI startup.
- GUI modules `player_man.py` and `pm_wins/add_new.py` consolidated to the `gui` alias for the PySimpleGUI wrapper.
- `buy_property` raises a clear `ValueError` for negative or out-of-range `space_index` values instead of silently wrapping or raising a bare `IndexError`.
