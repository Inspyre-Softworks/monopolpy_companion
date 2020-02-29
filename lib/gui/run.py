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


from lib.common.settings import Config

conf = Config()
conf = conf.data()


def run(cli_args=None, player_db_file=None):
    from lib.gui.models.windows import app_win
    # while True:
    #
    #     event, vals = app_win.read(timeout=100)
    #     print(event + str(vals))
    #
    #     if event is None or event == 'exit_button_main_application':
    #         log.debug(vals)
    #         log.info('User exited!')
    #         log.debug('Main window closed')
    #         log.debug('Exiting cleanly')
    #         break
    #
    #     if not opts_win_active and event == 'options_main_button':
    #         if not opts_win_exist:
    #             opts_win_active = True
    #             log.debug('Getting options window')
    #         opts_win_active = True
    #         log.debug('User entered options window!')
    #
    #     if opts_win_active:
    #         from lib.gui.models.windows import opts_win as opts_win
    #         opt_event, opt_val = opts_win.read(timeout=100)
    #         print(opt_event, opt_val)
    #         conf['gui_settings']['grab_anywhere'] = opt_val['grab_anywhere_box']
    #         if opt_event is None or opt_event == 'opts_ok':
    #             log.debug('User exited options window')
    #             log.debug('Calling on config.write()')
    #             lib.common.conf.write()
    #             opts_win_active = False
    #             opts_win.close()
    #             print(conf['gui_settings'])
    #
    #         if not pm_win_active and opt_event == 'opts_player_man_button':
    #             pm_win_active = True
    #             log.debug('User entered player management window')
    #
    #
    #     if pm_win_active:
    #         pm_event, pm_val = pm_win.read(timeout=100)
    #         pm_win.reappear()
    #         if pm_event is None or pm_event == 'player_man_ok_button':
    #             log.debug('User exited the Player Management window')
    #             pm_win_active = False
    #             pm_win.disappear()
    #
    #         if pm_event == 'pm_add_button':
    #             log.debug('User pressed \'add new\' button')
    #             try:
    #                 raise NotYetImplementedError('The Start New function is not yet implemented')
    #             except NotYetImplementedError as error:
    #                 log.warning(error)
    #                 alerts.not_yet_implemented()
    #
    #     if not load_game_active and event == 'load_saved_main_button':
    #         log.debug('User pressed \'Load Game\'')
    #         log.warning('Load Game is not yet implemented')
    #         alerts.not_yet_implemented()

    app_win()

    exit()


if __name__ == '__main__':
    print('There has been a problem.')
    exit()
