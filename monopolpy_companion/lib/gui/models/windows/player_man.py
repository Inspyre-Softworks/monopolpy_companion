class PlayerManagerWindow:
    """ Define information for the 'Player Management' window """

    def __init__(self):
        from monopolpy_companion.lib.gui import qt as gui
        from monopolpy_companion.lib.helpers.popup_man import nyi
        import logging

        log = logging.getLogger('MonopolPyCompanion.GUI.PlayerManagement')

        frame1 = [
            [gui.Button('Add Player', key='pm_add_button'),
             gui.Button('Remove Player', key='pm_rem_button'),
             gui.Button('List Players', key='pm_list_button')
             ],
            ]

        frame2 = [
            [gui.Button('OK', key='player_man_ok_button')]
            ]

        layout = [
            [gui.Frame('Manager Players', frame1)],
            [gui.Frame('', frame2)]

            ]

        self.window = gui.Window('Player Manager', layout, size=(400, 400), background_color='#40bfdbae',
                                 background_image='monopoly_man.png')

        from monopolpy_companion.lib.common.run import pm_win_active

        self.active = pm_active
        self.active = True

        unimplemented_buttons = [
            'pm_add_button',
            'pm_rem_button',
            'pm_list_button'
            ]

        while self.active:
            event, values = self.window.read(timeout=100)

            if event is None or event == 'player_man_ok_button':
                self.active = False
                self.window.close()

            if event in unimplemented_buttons:
                log.warning('This button leads to a feature that does not yet exist!')
                nyi(event)
