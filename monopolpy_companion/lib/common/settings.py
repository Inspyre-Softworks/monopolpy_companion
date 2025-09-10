import logging
import os
import yaml


logger = logging.getLogger('MonopolpyCompanion.' + __name__)


class Config:
    """Configuration handler for the application."""

    def __init__(self, file=None):
        logger.info(f'Logger started for {logger.name}')
        self.data = self.load(file)

    def load(self, file=None):
        """Load configuration data from *file*.

        Falls back to the default configuration file when *file* is ``None``.
        Missing keys are handled gracefully with defaults and warnings logged
        instead of printing to stdout.
        """
        if file is None:
            logger.debug('A custom config file was not provided!')
            file = os.getcwd() + '/conf/default.yml'

        with open(file) as res:
            data = yaml.safe_load(res)

        gui_settings = data.setdefault('gui_settings', {})
        if gui_settings.get('grab_anywhere') is None:
            logger.warning("Missing 'grab_anywhere' in gui_settings; defaulting to False")
            gui_settings['grab_anywhere'] = False

        return data

    def write(self, file=None):
        """Write configuration data to *file*.

        If *file* is ``None``, the default configuration path is used.
        """
        if file is None:
            logger.warning('Output file not provided; using default file')
            file = os.getcwd() + '/conf/default.yml'

        with open(file, 'w') as outfile:
            yaml.safe_dump(self.data, outfile, default_flow_style=False)


if __name__ == '__main__':
    print("That's not how you use this")
    exit()
