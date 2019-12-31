import lib.common.setup_env as env
import lib.common.utilities.db_man as database
from lib.gui.gui import gui

path = env.path
app_path = env.application_path # Might need to remove
db_path = env.db_path

if database.check_for(db_path):
    disable_player_man = True
else:
    disable_player_man = False

disable_remove_list = False

if path.exists(db_path):
    disable_remove_list = False
else:
    disable_remove_list = True

opts_playerman_frame = [
    [gui.Button('Player Management', key='opts_player_man_button')],

    ]

opts_main_frame = [
    [gui.Frame('Player Management:', opts_playerman_frame)],
    []

    ]

opts_main_layout = [
    [gui.Frame('Monopolpy Companion Options:', opts_main_frame, background_color='#40bfdbae', title_color='#ff000000',
               title_location='TITLE_LOCATION_TOP', relief='RELIEF_SUNKEN')],
    [gui.Button('OK')]

    ]

window = gui.Window('Monopolpy Companion Options', opts_main_layout, background_image='thing.png', size=(400, 300))
