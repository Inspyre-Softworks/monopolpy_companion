"""Small headless command-line harness for the reusable library."""

from __future__ import annotations

import argparse
from pathlib import Path

from .game import SessionRepository


def main(argv: list[str] | None = None) -> int:
    """Run the library's console entry point.

    Args:
        argv: Explicit CLI arguments for embedding or tests.

    Returns:
        Process exit status.
    """
    parser = argparse.ArgumentParser(
        prog='monopolpy-companion',
        description='Session information for the physical Monopoly companion.',
    )
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--list-sessions', action='store_true', help='List saved sessions')
    choice.add_argument('--summary', type=Path, help='Summarize a saved JSON session')
    choice.add_argument('--gui', action='store_true', help='Launch the optional legacy GUI')
    args = parser.parse_args(argv)

    if args.gui:
        try:
            from .lib.gui.run import run
        except ImportError as exc:
            parser.error(f'GUI requires the optional gui extra: {exc}')
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
