""" Define information for the applications 'main' landing window """

#  Copyright (c) 2022. Inspyre-Softworks (https://softworks.inspyre.tech)

import logging

# Import Config
from monopolpy_companion.lib.common.settings import Config

name = 'MonopolPyCompanion.GUI.ApplicationWindow'
log = logging.getLogger(name)

# Load Config
config = Config()
config = config.data()
print(config)

# Load bytecode for icon
from monopolpy_companion.lib.gui.models.images.icons.main_default import icon as app_icon

# Load bytecode for button images
from monopolpy_companion.lib.gui.models.images.buttons.app_win import start_new_button_img
from monopolpy_companion.lib.gui.models.images.buttons.app_win import load_saved_button_img

import PySimpleGUIQt as gui

conf = config

gui.ChangeLookAndFeel('DarkGreen1')

button_frame = [
    [gui.Button('', key='start_new_main_button',
                image_data=start_new_button_img)],
    [gui.Button('', key='load_saved_main_button',
                image_data=load_saved_button_img)],
    [gui.Button('Options', key='options_main_button', font=('Monopoly, Bold', 16))],
    [gui.Button('Manage Players', key='play_man_main_button', font=('Monopoly, Bold', 16))]
    ]

frame = [
    [gui.Text('Welcome to Monopolpy Companion!', justification='center', background_color='#C70000',
              font=('Monopoly, Bold', 18))],
    [gui.Frame('What would you like to do', button_frame, title_location='center-top', background_color='#99FFFFFF',
               title_color='#000000')],
    [gui.Button('Exit', key='exit_button_main_application')]
    ]

main_layout = [
    [gui.Frame('', frame, background_color=('#408FBC72'))]
    ]

menu_def = ['My Menu Def',
            ['&Restore', '&Open', '---', '&Message', '&Save', ['1', '2', ['a', 'b']], '&Properties', 'E&xit']]
tray = gui.SystemTray(menu=menu_def, data_base64=app_icon)

win = gui.Window('Monopolpy Companion', main_layout,
                 background_image='monopolpy.png',
                 grab_anywhere=conf['gui_settings']['grab_anywhere'],
                 icon=app_icon,
                 location=(450, 100),
                 resizable=False
                 )


def window():
    global conf, log
    from monopolpy_companion.lib.common.run import opts_win_active
    from monopolpy_companion.lib.helpers.popup_man import nyi

    while True:
        event, values = win.read(timeout=100)

        if event is None or event == 'exit_button_main_application':
            log.info('User indicated a desire to exit the application.')
            break

        if not opts_win_active and event == 'options_main_button':
            from monopolpy_companion.lib.gui.models.windows.options import OptionsWindow

            log.debug('User indicated a desire to open the options window')

            opts_win_active = True
            OptionsWindow(conf)
            log.debug('Options window has been left')

            opts_win_active = False
            log.debug(f'Options Window Active: {opts_win_active}')



        if event == 'start_new_main_button':
            nyi('Start New Game')

        if event == 'load_saved_main_button':
            nyi('Load saved game')


active = False

if __name__ == '__main__':
    print('Application is not a function')
