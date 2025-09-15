from __future__ import annotations

from typing import Optional, Tuple, List, Any
from dataclasses import dataclass, field

import PySimpleGUI as sg
import tkinter as tk
from PIL import Image, ImageTk

from .layout import MonopolPyMainLayout



@dataclass
class MainWindow:
    """
The main application window for Monopoly Companion.

On init, creates a MonopolyMainLayout and stores it as a read-only property.
Then use construct() to actually create the sg.Window.

Parameters:
title:
Window title text.
icon_data:
Base64/bytes for the window icon.
tray_menu:
Optional SystemTray menu definition.
bg_image_path:
Path to a background image file.
size:
(w, h). If None, uses image size; else defaults to (800, 600).
location:
(x, y) screen coords.
resizable:
Whether window is resizable.
grab_anywhere:
Allow dragging by clicking anywhere.
enable_bg_autoscale:
If True, background scales when window is resized.
theme:
Optional PySimpleGUI theme name.
layout_kwargs:
Extra kwargs passed to MonopolyMainLayout for customizing text,
colors, fonts, etc.
    """
    title: str
    icon_data: Optional[bytes] = None
    tray_menu: Optional[List[Any]] = None
    bg_image_path: Optional[str] = None
    size: Optional[Tuple[int, int]] = None
    location: Optional[Tuple[int, int]] = None
    resizable: bool = False
    grab_anywhere: bool = False
    enable_bg_autoscale: bool = False
    theme: Optional[str] = None
    layout_kwargs: dict = field(default_factory=dict)

    # internals
    _layout_builder: MonopolyMainLayout = field(init=False, repr=False)
    _pil_img: Optional[Image.Image] = field(default=None, init=False, repr=False)
    _photo: Optional[ImageTk.PhotoImage] = field(default=None, init=False, repr=False)
    _content_container: Optional[tk.Widget] = field(default=None, init=False, repr=False)
    window: Optional[sg.Window] = field(default=None, init=False)
    canvas: Optional[tk.Canvas] = field(default=None, init=False)

    def __post_init__(self):
        # init layout builder immediately
        self._layout_builder = MonopolPyMainLayout(**self.layout_kwargs)

    # --------- public properties ---------
    @property
    def layout(self) -> MonopolyMainLayout:
        """Read-only access to the MonopolyMainLayout instance."""
        return self._layout_builder

    # --------- main API ---------
    def construct(self) -> sg.Window:
        """Build and return the sg.Window with background and content layout."""
        if self.theme:
            if hasattr(sg, "theme"):
                sg.theme(self.theme)
            else:
                sg.set_options(theme=self.theme)

        if self.bg_image_path:
            self._pil_img = Image.open(self.bg_image_path).convert('RGBA')

        size = self._normalize_size(self.size)

        # hidden column so tk.Frame exists in same toplevel
        self._content_column = sg.Column(
            self._layout_builder.build(),
            key='-CONTENT-',
            pad=(0, 0),
            visible=False,
            background_color=None
        )
        outer_layout = [
            [sg.Canvas(key='-BG-CANVAS-', size=size, pad=(0, 0))],
            [self._content_column],
        ]

        self.window = sg.Window(
            self.title,
            outer_layout,
            icon=self.icon_data,
            margins=(0, 0),
            element_padding=(0, 0),
            resizable=self.resizable,
            grab_anywhere=self.grab_anywhere,
            location=self.location,
            finalize=True,
        )

        if self.tray_menu:
            sg.SystemTray(menu=self.tray_menu, data_base64=self.icon_data)

        self.canvas = self.window['-BG-CANVAS-'].TKCanvas
        self._draw_background_to_canvas()

        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        col_widget = self._content_column.Widget
        # Detach from any prior geometry manager and embed into the canvas
        try:
            col_widget.pack_forget()
        except Exception:
            pass
        col_widget.place(in_=self.canvas, x=cw // 2, y=ch // 2, anchor=tk.CENTER)
        self._content_container = col_widget

        def _on_resize(event):
            try:
                self._content_container.place_configure(
                    x=event.width // 2, y=event.height // 2
                )
            except Exception:
                pass
            if self.enable_bg_autoscale:
                self._redraw_autoscaled_bg(event.width, event.height)

        self.canvas.bind('<Configure>', _on_resize)

        return self.window

    def read(self, *args, **kwargs):
        return self.window.read(*args, **kwargs) if self.window else (None, {})

    def close(self):
        if self.window:
            self.window.close()

    # --------- internals ---------
    def _normalize_size(self, claimed: Optional[Tuple[int, int]]) -> Tuple[int, int]:
        if claimed is not None:
            return claimed
        if self._pil_img is not None:
            return self._pil_img.size
        return (800, 600)

    def _draw_background_to_canvas(self) -> None:
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        img = None
        if self._pil_img is not None:
            img = self._pil_img if self._pil_img.size == (cw, ch) else self._pil_img.resize((cw, ch), Image.LANCZOS)
        self.canvas.delete('all')
        if img is not None:
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)

    def _redraw_autoscaled_bg(self, new_w: int, new_h: int) -> None:
        if not self._pil_img or new_w <= 1 or new_h <= 1:
            return
        img = self._pil_img.resize((new_w, new_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)
