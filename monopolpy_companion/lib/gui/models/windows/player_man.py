class PlayerManagerWindow:
    """Define information for the 'Player Management' window."""

    def __init__(self):
        import logging

        from monopolpy_companion.game.storage import save_session
        from monopolpy_companion.lib.common.state import get_current_session
        from monopolpy_companion.lib.gui import gui

        log = logging.getLogger("MonopolPyCompanion.GUI.PlayerManagement")
        session = get_current_session()
        if session is None:
            gui.PopupOK("Start or load a session before managing players.")
            self.active = False
            return

        frame1 = [
            [gui.Listbox(values=[], size=(45, 8), key="player_list")],
            [
                gui.Button("Add Player", key="pm_add_button"),
                gui.Button("Remove Player", key="pm_rem_button"),
                gui.Button("Refresh", key="pm_list_button"),
            ],
        ]

        frame2 = [
            [gui.Button("OK", key="player_man_ok_button")]
        ]

        layout = [
            [gui.Frame("Manage Players", frame1)],
            [gui.Frame("", frame2)],
        ]

        self.window = gui.Window("Player Manager", layout, size=(400, 400), modal=True, finalize=True)
        self.active = True

        def refresh_player_list() -> None:
            values = [
                f"{player.name} | ${player.cash} | {len(session.owned_spaces_for(player.player_id))} assets"
                for player in session.players
            ]
            self.window["player_list"].update(values)

        refresh_player_list()

        while self.active:
            event, values = self.window.read(timeout=100)

            if event is None or event == "player_man_ok_button":
                self.active = False
                self.window.close()

            if event == "pm_add_button":
                new_name = gui.PopupGetText("Enter the new player name", title="Add Player")
                if new_name:
                    session.add_player(new_name)
                    save_session(session, session.save_path)
                    refresh_player_list()

            if event == "pm_rem_button":
                selected = values.get("player_list")
                if not selected:
                    gui.PopupOK("Select a player to remove.")
                    continue
                selected_name = selected[0].split("|", 1)[0].strip()
                target_player = next((player for player in session.players if player.name == selected_name), None)
                if target_player is None:
                    gui.PopupOK("Could not match the selected player.")
                    continue
                session.remove_player(target_player.player_id)
                save_session(session, session.save_path)
                refresh_player_list()

            if event == "pm_list_button":
                log.debug("Refreshing player list")
                refresh_player_list()
