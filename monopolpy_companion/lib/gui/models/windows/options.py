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
        from monopolpy_companion.lib.common.run import opts_win_active
        import PySimpleGUI as gui
        # First we pull in the environment variables
        from monopolpy_companion.conf import conf as defaults
        import logging

        self.name = 'MonopolPyCompanion.GUI.OptionsWindow'
        log = logging.getLogger(self.name)
        log.debug(f'Logger started for {self.name}')
        self.log = log

        log.debug(f'Current active state: {opts_win_active}')
        opts_win_active = True
        log.debug(f'New active state: {opts_win_active}')
        self.active = opts_win_active

        self._config_obj = None
        if hasattr(config, 'data') and hasattr(config, 'write'):
            self._config_obj = config
            conf = config.data
        else:
            conf = config
        self.conf = conf

        self.opts_playman_frame = [
            [gui.Button('Player Management', key='opts_playman_button')],
            ]

        self.opts_frame = [
            [gui.Checkbox('Grab anywhere', default=self.is_grabby(), key='grab_anywhere_box')]
            ]

        self.opts_main_frame = [
            [gui.Frame('Player Management:', self.opts_playman_frame)],
            [gui.Frame('GUI Options', self.opts_frame)]

            ]

        self.layout = [
            [gui.Frame('Monopolpy Companion Options:', self.opts_main_frame, background_color='#40bfdbae',
                       title_color='#ff000000', title_location='TITLE_LOCATION_TOP',
                       relief='RELIEF_SUNKEN')],
            [gui.Button('OK', key='opts_ok'), gui.Cancel(key='opts_cancel'), gui.Button('Apply', key='opts_apply')]
            ]

        import inspect
        window_kwargs = {
            'grab_anywhere': self.conf['gui_settings']['grab_anywhere'],
            'size': (400, 200)
        }
        if 'background_image' in inspect.signature(gui.Window.__init__).parameters:
            window_kwargs['background_image'] = 'thing.png'
        self.opts_win = gui.Window('Monopolpy Companion Options', self.layout, **window_kwargs)
        from monopolpy_companion.lib.common.run import pm_active

        log.debug(f'Imported active state of the Player Manager window which is: {pm_active}')

        while self.active:

            event, values = self.opts_win.read(timeout=100)

            if event == 'opts_ok' or event == 'opts_apply':
                log.debug('User is attempting to save config to file')
                self.save_config(values)

            if event == 'opts_ok':
                log.debug('User pressed OK in the options window')
                log.debug('Leaving window.')
                self.leave()

            if event == 'opts_playman_button' and not pm_active:
                from monopolpy_companion.lib.gui.models.windows.player_man import PlayerManagerWindow
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

    def save_config(self, values):
        """Persist the configuration using the active Config instance."""

        if self.conf is None:
            self.log.error('Configuration not loaded; cannot save')
            return

        gui_settings = self.conf.setdefault('gui_settings', {})
        new_grab_anywhere = bool(values.get('grab_anywhere_box'))
        old_grab_anywhere = gui_settings.get('grab_anywhere')
        gui_settings['grab_anywhere'] = new_grab_anywhere
        if old_grab_anywhere != new_grab_anywhere:
            self.log.debug(
                "Updated 'grab_anywhere' from %s to %s",
                old_grab_anywhere,
                new_grab_anywhere,
            )

        if self._config_obj is not None:
            try:
                self._config_obj.write()
                path = getattr(self._config_obj, 'path', None)
                if path:
                    self.log.info('Configuration saved to %s', path)
                else:
                    self.log.info('Configuration saved')
            except Exception:
                self.log.exception('Failed to save configuration to disk')
        else:
            self.log.warning('No Config instance supplied; changes not persisted to disk')
