# Contributing

Thanks for contributing to MonopolPy Companion.

This project is currently evolving from an early prototype into a playable Monopoly companion app. To keep the repository stable, every change merged into `master` must follow the contribution and release hygiene rules below.

## Branching
- Do not commit directly to `master`.
- Create a feature or fix branch for every change.
- Open a pull request for all changes, even small ones.
- If `master` is ever renamed to `main`, treat the rules in this document as applying to that default branch as well.

## Development Setup
1. Create and activate a Python environment that satisfies the version in [pyproject.toml](./pyproject.toml).
2. Install dependencies with either:
   - `poetry install`
   - `pip install -r requirements.txt`
3. Run tests before opening or updating a pull request:
   - `python -m unittest discover -s tests -v`

## Pull Request Expectations
Every pull request should:
- explain what changed and why
- include validation notes
- keep scope focused
- update docs when behavior or workflow changes

## Changelog Policy
This repository should maintain a human-readable changelog in [CHANGELOG.md](./CHANGELOG.md).

For every code change intended to merge into `master`:
- add a concise entry to the `Unreleased` section of `CHANGELOG.md`
- place the entry in the right category: `Added`, `Changed`, `Fixed`, `Removed`, or `Security`
- write entries from the user or maintainer perspective, not as implementation notes

Examples:
- `Added a session save/load flow for in-progress Monopoly games.`
- `Fixed the GUI startup path when launching with --gui.`

## Version Bump Policy
For every code change merged into `master`, bump the project version.

Until version metadata is centralized, update all version declarations together:
- [pyproject.toml](./pyproject.toml)
- [setup.py](./setup.py)

Use semantic versioning as the default rule:
- patch bump for fixes, internal improvements, and small behavior changes
- minor bump for backward-compatible new features
- major bump for breaking changes

If the repository is intentionally on a prerelease version, keep the prerelease suffixes aligned across all version declarations.

## Definition Of Done For Merge Readiness
Before requesting merge to `master`, make sure:
- the relevant tests pass locally
- `CHANGELOG.md` has been updated
- the version has been bumped in all required files
- new or changed contributor workflows are reflected in docs
- the PR description calls out the changelog and version bump explicitly

## Repository-Specific Notes
- Keep new files ASCII unless there is a strong reason not to.
- Prefer small, reviewable PRs over large mixed-purpose changes.
- If you touch packaging or release metadata, keep `pyproject.toml` and `setup.py` in sync.
