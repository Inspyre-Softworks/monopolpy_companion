# GitHub Copilot Instructions

When suggesting or making changes in this repository:

## Required for code changes headed to `master`
- Update `CHANGELOG.md` under `Unreleased`
- Bump the version in `pyproject.toml`
- Bump the version in `setup.py`
- Keep both version declarations identical

## Changelog guidance
- Use one of: `Added`, `Changed`, `Fixed`, `Removed`, `Security`
- Write entries as user-facing or maintainer-facing outcomes
- Do not add low-signal implementation trivia

## Repository conventions
- Run or recommend `python -m unittest discover -s tests -v`
- Prefer focused, reviewable changes
- Keep documentation aligned with behavior and workflow changes
