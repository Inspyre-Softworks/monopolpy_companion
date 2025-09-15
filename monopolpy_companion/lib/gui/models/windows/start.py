import PySimpleGUI as sg
from .application import BackgroundWindow  # adjust path as needed

# sanitize any RGBA colors you pass to PSG widgets
from .application import tk_safe_color, tk_labelanchor

sg.theme('DarkGreen1')  # modern replacement for ChangeLookAndFeel

button_frame = [
    [sg.Button('', key='start_new_main_button', image_data=start_new_button_img)],
    [sg.Button('', key='load_saved_main_button', image_data=load_saved_button_img)],
    [sg.Button('Options', key='options_main_button', font=('Monopoly, Bold', 16))],
    [sg.Button('Manage Players', key='play_man_main_button', font=('Monopoly, Bold', 16))]
]

frame = [
    [sg.Text('Welcome to Monopolpy Companion!',
             justification='center',
             background_color=tk_safe_color('#C70000'),
             font=('Monopoly, Bold', 18))],
    [sg.Frame('What would you like to do',
              button_frame,
              title_location=tk_labelanchor('center-top'),  # becomes 'n'
              background_color=tk_safe_color('#FFFFFF'),
              title_color='#000000')],
    [sg.Button('Exit', key='exit_button_main_application')]
]

main_layout = [
    [sg.Frame('', frame, background_color=tk_safe_color('#8FBC72'))]
]

menu_def = [
    'My Menu Def',
    ['&Restore', '&Open', '---', '&Message', '&Save', ['1', '2', ['a', 'b']], '&Properties', 'E&xit']
]

bg_image_path = conf['gui_settings'].get('background_image', 'monopolpy.png')

win_mgr = BackgroundWindow(
    title='Monopolpy Companion',
    content_layout=main_layout,
    icon_data=app_icon,
    tray_menu=menu_def,
    bg_image_path=bg_image_path,
    size=None,                        # use image size if present
    location=(450, 100),
    resizable=False,
    grab_anywhere=conf['gui_settings']['grab_anywhere'],
    enable_bg_autoscale=False,        # set True if you make it resizable
    theme='DarkGreen1',
)

win = win_mgr.window