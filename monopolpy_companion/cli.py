"""Console launcher for library management and optional desktop GUIs."""

from __future__ import annotations

import argparse
from pathlib import Path

from .game import SessionRepository


def main(argv: list[str] | None = None) -> int:
    """Run a headless command or launch the installed desktop frontend.

    Args:
        argv: Explicit CLI arguments for testing or embedding.

    Returns:
        Program exit status.
    """
    parser = argparse.ArgumentParser(
        prog='monopolpy-companion',
        description='Electronic banker for a physical Monopoly game.',
    )
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--list-sessions', action='store_true', help='List saved sessions')
    choice.add_argument('--summary', type=Path, help='Summarize a saved JSON session')
    choice.add_argument('--gui', action='store_true', help='Launch the new Qt dashboard')
    choice.add_argument('--legacy-gui', action='store_true', help='Launch the old PySimpleGUI shell')
    choice.add_argument('--list-plugins', action='store_true',
                        help='List installed plugin entry points without loading them')
    parser.add_argument('--enable-plugin', action='append', default=[],
                        metavar='ID', help='Enable a plugin for this GUI launch')
    args = parser.parse_args(argv)
    if args.enable_plugin and not args.gui:
        parser.error('--enable-plugin requires --gui')
    if args.list_plugins:
        from .plugins import installed_plugins

        for entry in sorted(installed_plugins(), key=lambda item: (item.name, item.value)):
            print(f'{entry.name}: {entry.value}')
        return 0

    if args.gui:
        try:
            from .ui.app import run
        except ImportError as exc:
            parser.error(f'Qt GUI requires the optional gui extra: {exc}')
        return run(args.enable_plugin)

    if args.legacy_gui:
        try:
            from .lib.gui.run import run
        except ImportError as exc:
            parser.error(f'Legacy GUI requires the optional legacy-gui extra: {exc}')
        run()
        return 0

    repository = SessionRepository()
    if args.list_sessions:
        for item in repository.list_sessions():
            print(f'{item.display_name}: {item.path}')
        return 0
    if args.summary is not None:
        try:
            session = repository.load(args.summary)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            parser.error(f'Cannot load saved session: {exc}')
        print('\n'.join(session.summary_lines()))
        return 0
    parser.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
