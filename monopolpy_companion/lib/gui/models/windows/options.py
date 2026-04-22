class OptionsWindow:
    """Define information for the 'Options' window."""

    def leave(self):
        import logging

        _name = self.name + ".leave"
        log = logging.getLogger(_name)
        log.debug("Received call to leave window")
        log.debug(f"Active state was {self.active}")
        self.active = False
        log.debug(f"Active state set to: {self.active}")
        self.opts_win.close()
        log.debug("Options window closed")

    def __init__(self, config):
        import logging
        from monopolpy_companion.lib.common.settings import Config
        from monopolpy_companion.lib.gui import gui

        self.name = "MonopolPyCompanion.GUI.OptionsWindow"
        log = logging.getLogger(self.name)
        log.debug(f"Logger started for {self.name}")
        self.log = log
        self.active = True
        self.config_manager = Config()
        self.conf = config

        self.opts_playman_frame = [
            [gui.Button("Player Management", key="opts_playman_button")],
        ]

        self.opts_frame = [
            [gui.Checkbox("Grab anywhere", default=self.is_grabby(), key="grab_anywhere_box")]
        ]

        self.opts_main_frame = [
            [gui.Frame("Player Management:", self.opts_playman_frame)],
            [gui.Frame("GUI Options", self.opts_frame)],
        ]

        self.layout = [
            [
                gui.Frame(
                    "Monopolpy Companion Options:",
                    self.opts_main_frame,
                    background_color="#40bfdb",
                    title_color="#000000",
                    title_location="n",
                    relief="sunken",
                )
            ],
            [gui.Button("OK", key="opts_ok"), gui.Cancel(key="opts_cancel"), gui.Button("Apply", key="opts_apply")],
        ]

        self.opts_win = gui.Window(
            "Monopolpy Companion Options",
            self.layout,
            grab_anywhere=self.conf["gui_settings"]["grab_anywhere"],
            size=(400, 200),
            modal=True,
        )

        while self.active:
            event, values = self.opts_win.read(timeout=100)

            if event in ("opts_ok", "opts_apply"):
                log.debug("User is attempting to save config to file")
                self.conf["gui_settings"]["grab_anywhere"] = values["grab_anywhere_box"]
                self.config_manager.data = self.conf
                self.config_manager.write()

            if event == "opts_ok":
                log.debug("User pressed OK in the options window")
                log.debug("Leaving window.")
                self.leave()

            if event == "opts_playman_button":
                from monopolpy_companion.lib.gui.models.windows.player_man import PlayerManagerWindow

                log.debug("User pressed the Player Manager button")
                PlayerManagerWindow()

            if event is None or event == "opts_cancel":
                log.debug("User pressed cancel in the options window")
                self.leave()

    def is_grabby(self):
        if self.conf is None:
            raise TypeError
        try:
            return self.conf["gui_settings"]["grab_anywhere"]
        except KeyError:
            return False
