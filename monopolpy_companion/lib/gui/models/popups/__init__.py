"""

File:
    monopolpy_companion/lib/gui/models/popups/__init__.py
    
Project:
    monopolpy_companion
    
Created:
    8/26/22 - 16:45 hrs
    
Author:
    Taylor-Jayde Blackstone <t.blackstone@inspyre.tech>
    
Description:
    Package containing models and code pertaining to monopolpy-companion's popup windows.
    
"""
#  Copyright (c) 2022. Inspyre-Softworks (https://softworks.inspyre.tech)

from inspect import getmembers, isfunction

from monopolpy_companion.lib.common.run import PopUpWarden
from monopolpy_companion.lib.gui.models.popups import alerts

popup_factory = None


class PopupFactory(PopUpWarden):

    def __init__(self):
        super(PopupFactory, self).__init__()

    def __new__(cls):
        global popup_factory
        if popup_factory is None:
            popup_factory = object.__new__(cls)

        return popup_factory

    def gather(self):
        for func in [m[1] for m in getmembers(alerts) if isfunction(m[1])]:
            self.PopUp(func.__name__, )

        return self.popups
