class Error(Exception):
    """Namespace for monopolpy_companion exceptions."""


class NotYetImplementedError(Error):
    """Raised when a function of the program is called before it exists."""

    def __init__(self, message):
        self.message = message


from monopolpy_companion.lib.common.settings import Config

conf = Config().data


def run(cli_args=None, player_db_file=None):
    from monopolpy_companion.lib.gui.models.windows import app_win

    return app_win()
