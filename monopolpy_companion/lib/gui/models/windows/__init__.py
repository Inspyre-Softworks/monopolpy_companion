""" Namespace for all window models """
import PySimpleGUI as sg
from .application.window import MainWindow
from monopolpy_companion.lib.common.settings import Config
from monopolpy_companion.lib.gui.models.images.icons.main_default import icon as app_icon
from monopolpy_companion.lib.gui.models.images.buttons.app_win import start_new_button_img, load_saved_button_img


CONF = Config().data


app_win = MainWindow(
    title=         'Monopolpy Companion',
    icon_data=     app_icon,
    tray_menu=     ['My Menu Def', ['&Restore','&Open','---','&Message','&Save',['1','2',['a','b']],'&Properties','E&xit']],
    bg_image_path= CONF['gui_settings'].get('background_image', 'monopolpy.png'),
    location=      (450, 100),
    grab_anywhere= CONF['gui_settings']['grab_anywhere'],
    theme=         'DarkAmber',
    layout_kwargs= dict(

        start_new_img=  start_new_button_img,
        load_saved_img= load_saved_button_img

    )
)


WIN = app_win.construct()


def window():
    from monopolpy_companion.lib.common.run import opts_win_active
    from monopolpy_companion.lib.helpers.popup_man import nyi

    while True:
        event, values = app_win.read(timeout=100)

        if event in (sg.WIN_CLOSED, 'exit_button_main_application'):
            break

        if event == 'options_main_button' and not opts_win_active:
            from monopolpy_companion.lib.gui.models.windows.options import OptionsWindow

            opts_win_active = True
            OptionsWindow(CONF)
            opts_win_active = False

        if event == 'start_new_main_button':
            nyi('Start New Game')

        if event == 'load_saved_main_button':
            nyi('Load Saved Game')

    app_win.close()

