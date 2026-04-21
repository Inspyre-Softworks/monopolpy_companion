"""Main landing window for the MonopolPy Companion shell."""

import logging

from monopolpy_companion.game.storage import save_session
from monopolpy_companion.lib.common.settings import Config
from monopolpy_companion.lib.common.state import get_current_session, set_current_session
from monopolpy_companion.lib.gui import gui
from monopolpy_companion.lib.gui.models.windows.options import OptionsWindow
from monopolpy_companion.lib.gui.models.windows.player_man import PlayerManagerWindow
from monopolpy_companion.lib.gui.models.windows.start import (
    load_saved_session_dialog,
    start_new_session_dialog,
)


name = "MonopolPyCompanion.GUI.ApplicationWindow"
log = logging.getLogger(name)

gui.theme("DarkGreen1")


def window():
    config_manager = Config()
    conf = config_manager.data
    layout = [
        [gui.Text("MonopolPy Companion", font=("Monopoly, Bold", 18))],
        [gui.Text("A Monopoly session assistant: banker, tracker, and save/load shell.")],
        [gui.Multiline("", size=(70, 12), key="session_summary", disabled=True, autoscroll=False)],
        [
            gui.Button("Start New", key="start_new_main_button"),
            gui.Button("Load Saved", key="load_saved_main_button"),
            gui.Button("Options", key="options_main_button"),
            gui.Button("Manage Players", key="play_man_main_button"),
        ],
        [gui.Button("Save Session", key="save_session_button"), gui.Button("Advance Turn", key="advance_turn_button")],
        [gui.Button("Exit", key="exit_button_main_application")],
    ]
    win = gui.Window(
        "Monopolpy Companion",
        layout,
        grab_anywhere=conf["gui_settings"]["grab_anywhere"],
        location=(450, 100),
        resizable=False,
        finalize=True,
    )

    def refresh_summary() -> None:
        session = get_current_session()
        if session is None:
            summary = [
                "No active session.",
                "",
                'Use "Start New" to create a Monopoly companion session.',
                'Use "Load Saved" to reopen a previous session file.',
            ]
        else:
            summary = session.summary_lines()
            if session.save_path:
                summary.append(f"Save file: {session.save_path}")
        win["session_summary"].update("\n".join(summary))

    refresh_summary()
    while True:
        event, values = win.read(timeout=100)

        if event is None or event == "exit_button_main_application":
            log.info("User indicated a desire to exit the application.")
            break

        if event == "start_new_main_button":
            session = start_new_session_dialog()
            if session is not None:
                set_current_session(session)
                refresh_summary()

        if event == "load_saved_main_button":
            session = load_saved_session_dialog()
            if session is not None:
                set_current_session(session)
                refresh_summary()

        if event == "options_main_button":
            OptionsWindow(conf)
            conf = Config().data
            refresh_summary()

        if event == "play_man_main_button":
            PlayerManagerWindow()
            refresh_summary()

        if event == "save_session_button":
            session = get_current_session()
            if session is None:
                gui.PopupOK("There is no active session to save.")
            else:
                path = save_session(session, session.save_path)
                gui.PopupOK(f"Session saved to:\n{path}")
                refresh_summary()

        if event == "advance_turn_button":
            session = get_current_session()
            if session is None:
                gui.PopupOK("There is no active session yet.")
            else:
                current_player = session.advance_turn()
                save_session(session, session.save_path)
                gui.PopupOK(f"It is now {current_player.name}'s turn.")
                refresh_summary()

    win.close()


active = False
