"""Monopoly-inspired Qt palettes with readable system font substitutions.

The project does not ship any proprietary Monopoly trademark typeface.
Arial Black and Impact are only optional local system-family fallbacks.
"""

from __future__ import annotations

DARK = """
QMainWindow, QWidget { background: #10261c; color: #faf7ed; font-size: 12px; }
QGroupBox { border: 1px solid #63977d; border-radius: 8px; margin-top: 12px;
            padding: 10px; font-weight: 700; }
QGroupBox::title { subcontrol-origin: margin; left: 13px; padding: 0 5px; }
QPushButton, QToolButton { background: #b82932; color: white; border: 1px solid #e07b7b;
                         border-radius: 4px; padding: 7px 10px; font-weight: bold; }
QPushButton:hover, QToolButton:hover { background: #d63a42; }
QPushButton:disabled { color: #a8b4ac; background: #3d5848; border-color: #5d7366; }
QLineEdit, QSpinBox, QComboBox, QListWidget, QTextEdit, QTableWidget {
    color: #fff8e9; background: #1b3b2a; border: 1px solid #84a691;
    border-radius: 3px; selection-background-color: #b72e37;
}
QHeaderView::section { background: #26583a; color: #fff8e9; border: none;
                       padding: 7px; font-weight: bold; }
QTableWidget::item:selected { background: #b72e37; color: white; }
QMenuBar, QMenu, QToolBar, QStatusBar { background: #1c402b; color: white; }
QSplitter::handle { background: #467052; }
QLabel#headerTitle { font-size: 28px; font-weight: 900;
                     font-family: "Arial Black", Impact, sans-serif;
                     background: #b82932; padding: 10px 18px; color: #ffffff; }
QLabel#subTitle { color: #dbe5da; }
"""

LIGHT = """
QMainWindow, QWidget { background: #f4f0df; color: #17251b; font-size: 12px; }
QGroupBox { border: 2px solid #287b4c; border-radius: 7px; margin-top: 12px;
            padding: 9px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 13px; padding: 0 5px; }
QPushButton, QToolButton { background: #c62932; color: white; border: 1px solid #8c111b;
                         border-radius: 4px; padding: 7px 10px; font-weight: bold; }
QPushButton:hover, QToolButton:hover { background: #dd3c42; }
QPushButton:disabled { color: #657a6b; background: #d7dfd0; border-color: #b6c6b8; }
QLineEdit, QSpinBox, QComboBox, QListWidget, QTextEdit, QTableWidget {
    color: #17251b; background: #fffdf5; border: 1px solid #6f8f76;
    border-radius: 3px; selection-background-color: #f0c862;
}
QHeaderView::section { background: #287b4c; color: white; border: none;
                       padding: 7px; font-weight: bold; }
QTableWidget::item:selected { background: #c62932; color: white; }
QMenuBar, QMenu, QToolBar, QStatusBar { background: #e3e7d6; color: #17251b; }
QSplitter::handle { background: #a6c3a9; }
QLabel#headerTitle { font-size: 28px; font-weight: 900;
                     font-family: "Arial Black", Impact, sans-serif;
                     background: #c62932; padding: 10px 18px; color: white; }
QLabel#subTitle { color: #49624d; }
"""


def stylesheet(dark: bool = True) -> str:
    """Return a green/cream/red board-inspired desktop stylesheet."""
    return DARK if dark else LIGHT
