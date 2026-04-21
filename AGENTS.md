# Agent Instructions

These instructions apply to automated coding agents working in this repository.

## Merge Hygiene
For every code change intended for merge into `master`:
- update [CHANGELOG.md](./CHANGELOG.md) in the `Unreleased` section
- bump the version in [pyproject.toml](./pyproject.toml)
- bump the version in [setup.py](./setup.py)
- mention the changelog entry and version bump in the PR summary

If the change is documentation-only or repo-admin-only, a version bump is optional. For code changes, it is required.

## Versioning Rules
- patch: fixes, refactors, small behavior changes
- minor: backward-compatible features
- major: breaking changes

Keep all version declarations synchronized. Do not update only one file.

## Changelog Rules
- Write entries from the user or maintainer perspective.
- Prefer short, high-signal statements.
- Use the existing categories: `Added`, `Changed`, `Fixed`, `Removed`, `Security`.

## Validation
Before finishing work, run:
- `python -m unittest discover -s tests -v`

## Scope
- Prefer focused PRs.
- Do not silently bypass changelog or versioning requirements.
