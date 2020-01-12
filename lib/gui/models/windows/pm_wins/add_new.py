""" Define information for the Add New Player window """

import PySimpleGUIQt as qt

from ..start import alerts

frame1 = [
    [qt.Text('Name:', font="Monopoly, Bold", text_color='#C70000'), qt.InputText(key='user_name')],
    [qt.Text('Gender:', font="Monopoly, Bold", text_color='#C70000'), qt.Radio('Male', group_id='gender',
                                                                               key='gender_radio_male'),
     qt.Radio('Female', group_id='gender', key='gender_radio_female')]
    ]


def window():
    alerts.not_yet_implemented()


active = False
