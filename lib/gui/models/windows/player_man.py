""" Define information for the 'Player Management' window """

from lib.gui import qt as gui

frame1 = [
    [gui.Button('Add Player', key='pm_add_button'),
     gui.Button('Remove Player', key='player_man_rem_button'),
     gui.Button('List Players', key='player_man_list_button')
     ],
    ]

frame2 = [
    [gui.Button('OK', key='player_man_ok_button')]
    ]

layout = [
    [gui.Frame('Manager Players', frame1)],
    [gui.Frame('', frame2)]

    ]

window = gui.Window('Player Manager', layout, size=(400, 400), background_color='#40bfdbae',
                    background_image='monopoly_man.png')

active = False
