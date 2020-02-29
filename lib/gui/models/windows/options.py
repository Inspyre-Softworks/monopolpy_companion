class OptionsWindow:
    """ Define information for the 'Options' window """

    def leave(self):
        import logging
        _name = self.name + '.leave'
        log = logging.getLogger(_name)
        log.debug('Received call to leave window')
        log.debug(f'Active state was {self.active}')
        self.active = False
        log.debug(f'Active state set to: {self.active}')
        self.opts_win.close()
        log.debug('Options window closed')


    def __init__(self, config):
        from lib.common.run import opts_win_active
        import PySimpleGUIQt as qt
        # First we pull in the environment variables
        from conf import conf as defaults
        import logging

        self.name = 'MonopolPyCompanion.GUI.OptionsWindow'
        log = logging.getLogger(self.name)
        log.debug(f'Logger started for {self.name}')
        self.log = log

        log.debug(f'Current active state: {opts_win_active}')
        opts_win_active = True
        log.debug(f'New active state: {opts_win_active}')
        self.active = opts_win_active

        conf = config
        self.conf = conf

        self.opts_playman_frame = [
            [qt.Button('Player Management', key='opts_playman_button')],
            ]

        self.opts_frame = [
            [qt.Checkbox('Grab anywhere', default=self.is_grabby(), key='grab_anywhere_box')]
            ]

        self.opts_main_frame = [
            [qt.Frame('Player Management:', self.opts_playman_frame)],
            [qt.Frame('GUI Options', self.opts_frame)]

            ]

        self.layout = [
            [qt.Frame('Monopolpy Companion Options:', self.opts_main_frame, background_color='#40bfdbae',
                      title_color='#ff000000', title_location='TITLE_LOCATION_TOP',
                      relief='RELIEF_SUNKEN')],
            [qt.Button('OK', key='opts_ok'), qt.Cancel(key='opts_cancel'), qt.Button('Apply', key='opts_apply')]
            ]

        self.opts_win = qt.Window('Monopolpy Companion Options', self.layout, grab_anywhere=self.conf['gui_settings'][
            'grab_anywhere'],
                                  background_image='thing.png', size=(400, 200))
        from lib.common.run import pm_active

        log.debug(f'Imported active state of the Player Manager window which is: {pm_active}')

        while self.active:

            event, values = self.opts_win.read(timeout=100)

            if event == 'opts_ok' or event == 'opts_apply':
                log.debug('User is attempting to save config to file')
                from lib.helpers.popup_man import nyi

                nyi('Save Config')

            if event == 'opts_ok':
                log.debug('User pressed OK in the options window')
                log.debug('Leaving window.')
                self.leave()

            if event == 'opts_playman_button' and not pm_active:
                from lib.gui.models.windows.player_man import PlayerManagerWindow
                log.debug('User pressed the Player Manager button')
                play_man_win = PlayerManagerWindow()
                log.debug(f'Player Manager active state was {play_man_win.active}')
                play_man_win.active = True

            if event is None or event == 'opts_cancel':
                log.debug('User pressed cancel in the options window')
                self.leave()

    def is_grabby(self):
        if self.conf is None:
            raise TypeError
        else:
            try:
                return self.conf['gui_settings']['grab_anywhere']
            except KeyError:
                return False
