import logging
from pathlib import Path
from typing import Optional

import yaml


logger = logging.getLogger('MonopolpyCompanion.' + __name__)


class Config:
    """Configuration handler for the application."""

    def __init__(self, file: Optional[Path] = None):
        logger.info(f'Logger started for {logger.name}')
        root = Path(__file__).resolve().parents[2]
        self._default_file = root / 'conf' / 'default.yml'
        self._user_file = root / 'conf' / 'user.yml'
        self._path: Optional[Path] = None
        self.data = self.load(file)

    @property
    def path(self) -> Optional[Path]:
        """Return the path that configuration writes will target."""

        return self._path

    def load(self, file: Optional[Path] = None):
        """Load configuration data from *file*.

        Falls back to the saved user configuration when ``file`` is ``None``.
        If no user configuration exists, the bundled defaults are used for
        reading while future writes target the user configuration path.

        Missing keys are handled gracefully with defaults and warnings logged
        instead of printing to stdout.
        """

        if file is not None:
            load_path = Path(file)
            target_path = load_path
        else:
            if self._user_file.exists():
                load_path = self._user_file
                target_path = self._user_file
            else:
                logger.debug('A custom config file was not provided!')
                load_path = self._default_file
                target_path = self._user_file

        logger.debug('Loading configuration from %s', load_path)
        with open(load_path) as res:
            data = yaml.safe_load(res) or {}

        self._path = target_path

        gui_settings = data.setdefault('gui_settings', {})
        if gui_settings.get('grab_anywhere') is None:
            logger.warning("Missing 'grab_anywhere' in gui_settings; defaulting to False")
            gui_settings['grab_anywhere'] = False

        return data

    def write(self, file: Optional[Path] = None):
        """Write configuration data to *file*.

        If *file* is ``None``, the most appropriate user configuration path is
        used.
        """

        if file is not None:
            target = Path(file)
        else:
            if self._path is None:
                logger.warning('Output file not provided; using default user file')
                self._path = self._user_file
            target = self._path

        target.parent.mkdir(parents=True, exist_ok=True)
        logger.debug('Writing configuration to %s', target)
        with open(target, 'w') as outfile:
            yaml.safe_dump(self.data, outfile, default_flow_style=False)
        self._path = target


if __name__ == '__main__':
    print("That's not how you use this")
    exit()
