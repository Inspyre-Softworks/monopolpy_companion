"""
Author:
Inspyre Softworks

Project:
MonopolPy Companion

File:
layout.py

Description:
Provides a class-based PySimpleGUI layout builder with explicit build/rebuild
lifecycle and introspection via `layout` and `built` properties. Designed to
be consumed by a window-construction layer (e.g., MonopolPyAppWindow).

Dependencies:
- PySimpleGUI

Example Usage:
layout_builder = MonopolPyMainLayout(
start_new_img=start_new_button_img,
load_saved_img=load_saved_button_img,
title_text='Welcome to Monopolpy Companion!',
theme='DarkGreen1',
frame_title='What would you like to do',
title_location='center-top',   # human-friendly; mapped internally
frame_bg='#FFFFFF',            # 6-hex or #AARRGGBB; RGBA auto-sanitized
root_frame_bg='#8FBC72'
)
layout = layout_builder.build()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Sequence

import PySimpleGUI as sg


# ----------------------- small helpers (DRY, safe) -----------------------

_TITLE_LOC_MAP = {
    'center-top': 'n', 'top-center': 'n',
    'top-left': 'nw', 'top-right': 'ne',
    'bottom-center': 's', 'center-bottom': 's',
    'bottom-left': 'sw', 'bottom-right': 'se',
    'left-center': 'w', 'right-center': 'e',
}

def tk_labelanchor(value: Optional[str], default: str = 'nw') -> str:
    if not value:
        return default
    v = value.strip().lower()
    return _TITLE_LOC_MAP.get(v, v)

def tk_safe_color(color: Optional[str]) -> Optional[str]:
    """
Convert '#AARRGGBB' -> '#RRGGBB' for Tk (drops alpha); pass-through otherwise.
    """
    if not color or not isinstance(color, str):
        return color
    c = color.strip()
    if c.startswith('#') and len(c) == 9:
        return f'#{c[3:]}'
    return c


# ----------------------- the layout class you asked for -----------------------

@dataclass
class MonopolPyMainLayout:
    """
A configurable, class-based builder for the application's main window layout.

Parameters:
start_new_img:
Image data for the "Start New" button (bytes/base64 supported by PSG).
load_saved_img:
Image data for the "Load Saved" button.
title_text:
Header text displayed at the top.
theme:
Optional PySimpleGUI theme to set before building.
frame_title:
Title for the main action frame.
title_location:
Human-friendly label position (e.g., 'center-top'). Will be mapped to Tk.
frame_bg:
Background color for the action frame (supports '#AARRGGBB' or '#RRGGBB').
root_frame_bg:
Background color for the outer/root frame (supports '#AARRGGBB' or '#RRGGBB').
title_bg:
Background for the header text line.
title_font:
Tuple for the header font, e.g., ('Monopoly, Bold', 18).
action_font:
Tuple for the action buttons font, e.g., ('Monopoly, Bold', 16).

Properties:
layout:
The last-built layout (list[list[sg.Element]]). None until build() runs.
built:
True iff build() has been called and layout is materialized.

Methods:
build() -> list[list[sg.Element]]:
Construct the layout once (idempotent if already built).
rebuild(**overrides) -> list[list[sg.Element]]:
Regenerate from current config (plus overrides). Always returns a fresh layout.

Raises:
ValueError:
If required images are missing when attempting to build.
    """
    start_new_img: bytes
    load_saved_img: bytes
    title_text: str = 'Welcome to Monopolpy Companion!'
    theme: Optional[str] = 'DarkGreen1'
    frame_title: str = 'What would you like to do'
    title_location: str = 'center-top'
    frame_bg: str = '#FFFFFF'
    root_frame_bg: str = '#8FBC72'
    title_bg: str = '#C70000'
    title_font: Sequence[Any] = ('Monopoly, Bold', 18)
    action_font: Sequence[Any] = ('Monopoly, Bold', 16)

    # internal state
    _layout: Optional[List[List[sg.Element]]] = field(default=None, init=False, repr=False)

    # ---- properties ----
    @property
    def layout(self) -> Optional[List[List[sg.Element]]]:
        return self._layout

    @property
    def built(self) -> bool:
        return self._layout is not None

    # ---- public API ----
    def build(self) -> List[List[sg.Element]]:
        """
Build the layout once. Safe to call repeatedly; subsequent calls return
the already-built layout.

Returns:
The PySimpleGUI layout (list of rows).
        """
        if self._layout is None:
            self._layout = self._build_layout()
        return self._layout

    def rebuild(self, **overrides: Any) -> List[List[sg.Element]]:
        """
Recompute the layout from current settings, applying optional overrides.

Parameters:
overrides:
Any field on this dataclass you want to temporarily (or permanently)
change prior to building. The attributes are set on `self` before
re-building.

Returns:
A brand-new layout.
        """
        for k, v in overrides.items():
            if not hasattr(self, k):
                raise AttributeError(f'Unknown layout option: {k}')
            setattr(self, k, v)
        self._layout = self._build_layout()
        return self._layout

    # ---- internal ----
    def _build_layout(self) -> List[List[sg.Element]]:
        if self.theme:
            sg.theme(self.theme)

        if not self.start_new_img or not self.load_saved_img:
            raise ValueError('start_new_img and load_saved_img are required to build the layout.')

        action_buttons_col = [
            [sg.Button('', key='start_new_main_button', image_data=self.start_new_img)],
            [sg.Button('', key='load_saved_main_button', image_data=self.load_saved_img)],
            [sg.Button('Options', key='options_main_button', font=tuple(self.action_font))],
            [sg.Button('Manage Players', key='play_man_main_button', font=tuple(self.action_font))],
        ]

        # Header line
        header_row = [sg.Text(
                          self.title_text,
                          justification='center',
                          background_color=tk_safe_color(self.title_bg),
                          font=tuple(self.title_font),
                          expand_x=True,
                      )]

        # Action frame
        action_frame = sg.Frame(
            self.frame_title,
            action_buttons_col,
            title_location=tk_labelanchor(self.title_location),
            background_color=tk_safe_color(self.frame_bg),
            title_color='#000000',
        )

        inner_frame = [
            header_row,
            [action_frame],
            [sg.Button('Exit', key='exit_button_main_application')],
        ]

        # Root frame that can carry a different background
        root = [[sg.Frame('', inner_frame, background_color=tk_safe_color(self.root_frame_bg))]]

        return root
