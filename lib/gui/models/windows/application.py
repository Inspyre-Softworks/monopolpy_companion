""" Define information for the applications 'main' landing window """

from lib.common.setup_env import path
from lib.common.setup_env import saves_path

from lib.gui import qt as gui

from os import path as path

gui.ChangeLookAndFeel('DarkGreen1')

grabby = False

disable_load_bttn = False

if path.exists(saves_path):
    disable_load_bttn = False
else:
    disable_load_bttn = True

    gui.Button()

button_frame = [
    [gui.Button('Start New', key='start_new_main_button', font=('Monopoly, Bold', 16))],
    [gui.Button('Load Saved', key='load_saved_main_button',
                disabled=disable_load_bttn, font=('Monopoly, Bold', 16))
     ],
    [gui.Button('Options', key='options_main_button', font=('Monopoly, Bold', 16))]]

frame = [
    [gui.Text('Welcome to Monopolpy Companion!', justification='center', background_color='#C70000',
              font=('Monopoly, Bold', 22))],
    [gui.Frame('What would you like to do', button_frame, background_color='#99FFFFFF', title_color='#000000',
               pad=(50, 50))],
    [gui.Button('Exit', key='exit_button_main_application')]
    ]

main_layout = [
    [gui.Frame('', frame, size=(200, 200), background_color=('#408FBC72'))]
    ]

window = gui.Window('Monopolpy Companion', main_layout, size=(600, 600),
                    background_image='monopolpy.png',
                    grab_anywhere=grabby)

active = False

#
# menu_def = ['My Menu Def',
# ['&Restore', '&Open', '---', '&Message', '&Save', ['1', '2', ['a', 'b']], '&Properties', 'E&xit']]
# tray = gui.SystemTray(menu=menu_def, data_base64=default)
# tray.Read()
