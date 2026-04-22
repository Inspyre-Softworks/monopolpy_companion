"""Dialogs for starting or loading a Monopoly companion session."""

from __future__ import annotations

from inspy_logger import InspyLogger

from monopolpy_companion.game.models import create_standard_session
from monopolpy_companion.game.storage import list_saved_sessions, load_session, save_session
from monopolpy_companion.lib.gui import gui

_log_device = InspyLogger.LogDevice("MonopolPyCompanion.GUI.StartDialogs", "warning")
log = _log_device.start()


def start_new_session_dialog():
    session_name = gui.PopupGetText(
        "Enter a session name",
        title="Start New Session",
        default_text="New Monopoly Session",
    )
    if not session_name:
        return None

    players_raw = gui.PopupGetText(
        "Enter player names separated by commas",
        title="Players",
        default_text="Player 1, Player 2",
    )
    if not players_raw:
        return None

    starting_cash_raw = gui.PopupGetText(
        "Starting cash per player",
        title="Starting Cash",
        default_text="1500",
    )
    if not starting_cash_raw:
        return None

    try:
        starting_cash = int(starting_cash_raw)
    except ValueError:
        gui.PopupOK("Starting cash must be a whole number.")
        return None

    player_names = [name.strip() for name in players_raw.split(",") if name.strip()]
    try:
        session = create_standard_session(session_name, player_names, starting_cash=starting_cash)
    except ValueError as error:
        gui.PopupOK(str(error))
        return None

    save_path = save_session(session)
    gui.PopupOK(f"Created session '{session.name}'.\nSaved to:\n{save_path}")
    return session


def load_saved_session_dialog():
    sessions = list_saved_sessions()
    if not sessions:
        gui.PopupOK("No saved sessions found.")
        return None

    options = [f"{item.display_name} | {item.path.name}" for item in sessions]
    layout = [
        [gui.Text("Choose a saved session to load")],
        [gui.Listbox(options, size=(55, 8), key="session_list")],
        [gui.Button("Load"), gui.Button("Cancel")],
    ]
    window = gui.Window("Load Saved Session", layout, modal=True)

    selected_session = None
    while True:
        event, values = window.read()
        if event in (None, "Cancel"):
            break
        if event == "Load":
            selected = values.get("session_list")
            if not selected:
                gui.PopupOK("Select a save first.")
                continue
            selected_index = options.index(selected[0])
            try:
                selected_session = load_session(sessions[selected_index].path)
            except Exception as exc:
                log.error("Failed to load session: %s", exc)
                gui.PopupOK("Failed to load session.")
                break
            break

    window.close()
    return selected_session


active = False


def window():
    return start_new_session_dialog()
