"""Define information for the Add New Player window"""

import PySimpleGUI as gui

from ..start import alerts

frame1 = [
    [gui.Text('Name:', font="Monopoly, Bold", text_color='#C70000'), gui.InputText(key='user_name')],
    [gui.Text('Gender:', font="Monopoly, Bold", text_color='#C70000'), gui.Radio('Male', group_id='gender',
                                                                                key='gender_radio_male'),
     gui.Radio('Female', group_id='gender', key='gender_radio_female')]
    ]


def window():
    alerts.not_yet_implemented()


active = False
