"""Qt dialogs for the Marauder's Map unlock sequence."""

from __future__ import annotations

import logging
from functools import lru_cache
from importlib.resources import files

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QLabel, QLineEdit, QVBoxLayout, QWidget,
)

_STYLE = """
QDialog#mapParchment { background: #65442d; }
QFrame#parchmentSheet {
    background: #f3e0b6;
    border: 2px solid #a27649;
    border-radius: 10px;
}
QLabel { background: transparent; color: #3d281b; border: none; }
QLineEdit {
    background: #fff6dc; color: #352216; selection-background-color: #67472d;
    selection-color: #ffffff; border: 2px solid #96704c; border-radius: 5px;
    padding: 6px 10px;
}
QLineEdit:focus { border-color: #694124; }
QPushButton {
    background: #72492d; color: #fff6dc; border: 2px solid #72492d;
    border-radius: 5px; padding: 6px 14px;
}
QPushButton:hover { background: #885836; }
QPushButton:focus { border-color: #e3b16c; }
"""


@lru_cache(maxsize=2)
def _font_family(resource: str, family: str) -> str | None:
    try:
        data = files('monopolpy_companion.ui').joinpath('resources', resource).read_bytes()
    except OSError:
        logging.getLogger(__name__).warning('Could not read bundled font %s', resource, exc_info=True)
        return None
    font_id = QFontDatabase.addApplicationFontFromData(data)
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    if family not in families:
        logging.getLogger(__name__).warning('Qt could not load bundled font %s', resource)
        return None
    return family


def _script_font(widget: QWidget, size: int) -> None:
    family = _font_family('Caveat.ttf', 'Caveat')
    if family:
        widget.setStyleSheet(f'font: {size}pt "{family}";')
    else:
        widget.setStyleSheet('font-style: italic; font-size: 14pt;')


def _parchment(parent: QWidget, title: str) -> tuple[QDialog, QVBoxLayout]:
    dialog = QDialog(parent)
    dialog.setObjectName('mapParchment')
    dialog.setWindowTitle(title)
    family = _font_family('SourceSans3.ttf', 'Source Sans 3')
    body_family = f'font-family: "{family}";' if family else ''
    dialog.setStyleSheet(_STYLE + f'QLabel, QPushButton {{ font-size: 12pt; {body_family} }}')
    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(10, 10, 10, 10)
    sheet = QFrame(dialog)
    sheet.setObjectName('parchmentSheet')
    outer.addWidget(sheet)
    layout = QVBoxLayout(sheet)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(14)
    return dialog, layout


def _text(layout: QVBoxLayout, text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    layout.addWidget(label)
    return label


def _buttons(dialog: QDialog, layout: QVBoxLayout, label: str) -> None:
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
    accept = buttons.addButton(label, QDialogButtonBox.ButtonRole.AcceptRole)
    accept.setDefault(True)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)


def _introduction(parent: QWidget) -> QDialog:
    dialog, layout = _parchment(parent, 'Marauder’s Map')
    _text(layout, 'You unfurl an old, weathered piece of parchment. Though its surface '
          'appears entirely blank, a faint inscription catches your eye:')
    inscription = _text(layout, 'Moony, Wormtail, Padfoot, and Prongs.')
    inscription.setAlignment(Qt.AlignmentFlag.AlignCenter)
    _script_font(inscription, 25)
    _text(layout, 'There is something peculiar about this parchment. Almost as though '
          "it's waiting for you to say something...")
    _buttons(dialog, layout, '&Continue')
    dialog.resize(560, dialog.sizeHint().height())
    return dialog


def _phrase_entry(parent: QWidget) -> tuple[QDialog, QLineEdit]:
    dialog, layout = _parchment(parent, 'Marauder’s Map')
    instruction = 'Speak the words that reveal its secrets.'
    label = _text(layout, instruction)
    editor = QLineEdit()
    editor.setAccessibleName(instruction)
    editor.setEchoMode(QLineEdit.EchoMode.Normal)
    label.setBuddy(editor)
    _script_font(editor, 23)
    layout.addWidget(editor)
    _buttons(dialog, layout, '&Reveal the Map')
    editor.returnPressed.connect(dialog.accept)
    editor.setFocus()
    dialog.resize(560, dialog.sizeHint().height())
    return dialog, editor
