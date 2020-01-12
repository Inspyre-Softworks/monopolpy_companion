""" Namespace for all window models """

from .application import window as app_win, active as app_win_active

from .options import window as opts_win
from .options import active as opts_win_active

from .player_man import window as pm_win
from .player_man import active as pm_win_active

from .start import window as start_new_win, active as start_new_active

from .pm_wins.add_new import window as pm_add_new_win, active as pm_add_new_active

from ..popups import alerts as alerts
