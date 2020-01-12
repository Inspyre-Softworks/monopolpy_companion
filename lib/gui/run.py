class Error(Exception):
    """ Namespace for monopolpy_companion exceptions """
    pass


class NotYetImplementedError(Error):
    """
    Exception raised when a function of the program is called that
    is currently not implemented, or disabled.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


""" Run the Graphical User Interface """

import logging

import lib.gui.models.popups.alerts as alerts
from lib.gui.models.windows import app_win
from lib.gui.models.windows import pm_win as pm_win

formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=formatter)
log = logging.getLogger('MonopolpyCompanion')

log.debug('Logger set up, and is set to log debug messages')

opts_win_active = False
load_game_active = False
opts_win_exist = False


def run():
    global wins_open, opts_win_active, opts_win_exist
    from lib.gui.models.windows import opts_win_active
    from lib.gui.models.windows import pm_win_active
    from lib.gui.models.windows import start_new_active
    while True:

        event, vals = app_win.read(timeout=100)

        if event is None or event == 'exit_button_main_application':
            log.debug(vals)
            log.info('User exited!')
            log.debug('Main window closed')
            log.debug('Exiting cleanly')
            break

        if not opts_win_active and event == 'options_main_button':
            if not opts_win_exist:
                opts_win_active = True
                log.debug('Getting options window')
            opts_win_active = True
            log.debug('User entered options window!')

        if opts_win_active:
            from lib.gui.models.windows import opts_win as opts_win
            opt_event, opt_val = opts_win.read(timeout=100)
            opts_win.reappear()
            if opt_event is None or opt_event == 'opts_ok':
                log.debug('User exited options window')
                opts_win_active = False
                opts_win.disappear()

            if not pm_win_active and opt_event == 'opts_player_man_button':
                pm_win_active = True
                log.debug('User entered player management window')

        if pm_win_active:
            pm_event, pm_val = pm_win.read(timeout=100)
            pm_win.reappear()
            if pm_event is None or pm_event == 'player_man_ok_button':
                log.debug('User exited the Player Management window')
                pm_win_active = False
                pm_win.disappear()

            if pm_event == 'pm_add_button':
                log.debug('User pressed \'add new\' button')
                try:
                    raise NotYetImplementedError('The Start New function is not yet implemented')
                except NotYetImplementedError as error:
                    log.warning(error)
                    alerts.not_yet_implemented()

        if not start_new_active and event == 'start_new_main_button':
            log.debug('User pressed \'Start new\' in main menu')
            try:
                raise NotYetImplementedError('The Start New function is not yet implemented')
            except NotYetImplementedError as error:
                log.warning(error)
                alerts.not_yet_implemented()

        if not load_game_active and event == 'load_saved_main_button':
            log.debug('User pressed \'Load Game\'')
            log.warning('Load Game is not yet implemented')
            alerts.not_yet_implemented()

    app_win.close()

    exit()
