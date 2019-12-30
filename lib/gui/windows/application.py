from lib.gui.gui import gui
from lib.common.setup_env import saves_path
from lib.common.setup_env import application_path
from lib.common.setup_env import path

if path.exists(saves_path):
    disable_load_game = False
else:
    disable_load_game = True

button_frame = [
    [gui.Button('Start New', key='start_new_main_button')],
    [gui.Button('Load Saved', key='load_saved_main_button', disabled=disable_load_game)],
    [gui.Button('Options', key='options_main_button')]
    ]

frame = [
    [gui.Text('Welcome to Monopolpy Companion!', justification='center')],
    [gui.Frame('What would you like to do', button_frame)],
    [gui.Button('Exit')]
    ]

main_layout = [
    [gui.Frame('', frame)]
    ]

app_window = gui.Window('Monopolpy Companion', main_layout, default_element_size=(600, 500))
