""" Run the Graphical User Interface """

from .models import windows as win
import logging

formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=formatter)
log = logging.getLogger('MonopolpyCompanion')

log.debug('Logger set up, and is set to log debug messages')


def run():
    while True:

        event, vals = win.app_win.Read(timeout=100)
        if event is None or event == 'exit_button_main_application':
            log.debug(vals)
            log.info('User exited!')
            win.app_win.Close()
            log.debug('Main window closed')
            log.debug('Exiting cleanly')
            exit()

        if not win.opts_win_active and event == 'options_main_button':
            win.opts_win_active = True
            log.debug('User entered options window!')
            win.opts_win.Show()

        if win.opts_win_active:
            opt_event, opt_val = win.opts_win.Read(timeout=100)
            if opt_event is None or opt_event == 'opts_ok':
                log.debug('User exited options window')
                win.opts_win_active = False
                win.opts_win.Hide()
            if not win.pm_win_active and opt_event == 'opts_player_man_button':
                win.pm_win_active = True
                log.debug('User entered player management window')

        if win.pm_win_active:
            pm_event, pm_val = win.pm_win.read()
            if pm_event is None or pm_event == 'player_man_ok_button':
                log.debug('User exited the Player Management window')
                win.pm_active = False
                win.pm_win.Close()
            if pm_event == 'pm_add_button':
                log.debug('User pressed \'add new\' button')
                win.pm_add_new_win()

        if not win.start_new_active and event == 'start_new_main_button':
            # start_event, start_val = win.start_win.Read(timeout=100)
            # if start_event is None or start_event ==
            win.start_new_win()
