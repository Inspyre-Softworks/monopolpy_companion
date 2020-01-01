from lib.common.setup_env import path
from lib.common.setup_env import saves_path
from lib.gui.gui import gui

grabby = False

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
    [gui.Text('Welcome to Monopolpy Companion!', justification='center', background_color='#C70000')],
    [gui.Frame('What would you like to do', button_frame, background_color='#99FFFFFF', title_color='#000000')],
    [gui.Button('Exit', key='exit_button_main_application')]
    ]

main_layout = [
    [gui.Frame('', frame, size=(200, 200), background_color=('#408FBC72'))]
    ]

window = gui.Window('Monopolpy Companion', main_layout, size=(600, 600),
                    background_image='monopolpy.png',
                    grab_anywhere=grabby)

active = False
