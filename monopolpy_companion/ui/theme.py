"""Desktop color theme definitions without coupling to the game engine."""

from __future__ import annotations

DARK = """
QMainWindow, QWidget { background: #121923; color: #e7edf4; font-size: 12px; }
QGroupBox { border: 1px solid #344354; border-radius: 9px; margin-top: 12px;
            padding: 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QPushButton, QToolButton { background: #28384a; border: 1px solid #45576a;
                         border-radius: 6px; padding: 6px 11px; }
QPushButton:hover, QToolButton:hover { background: #364d63; }
QPushButton:disabled { color: #788597; background: #202933; }
QLineEdit, QSpinBox, QComboBox, QTableWidget {
    color: #e7edf4; background: #1d2937; border: 1px solid #3a4b5b;
    border-radius: 4px; selection-background-color: #2e6880;
}
QHeaderView::section { background: #263649; color: #dce7f2; border: none;
                       padding: 7px; }
QTableWidget::item:alternate { background: #233142; }
QMenuBar, QMenu, QToolBar, QStatusBar { background: #192534; color: #e7edf4; }
QToolBar { border-bottom: 1px solid #344354; spacing: 8px; }
QSplitter::handle { background: #344354; }
QLabel#headerTitle { font-size: 22px; font-weight: 700; }
QLabel#subTitle { color: #aebdd0; }
"""

LIGHT = """
QMainWindow, QWidget { background: #f3f6fb; color: #1b2b3d; font-size: 12px; }
QGroupBox { border: 1px solid #c5d2e0; border-radius: 9px; margin-top: 12px;
            padding: 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
QPushButton, QToolButton { background: #e1e9f3; border: 1px solid #bccbdb;
                         border-radius: 6px; padding: 6px 11px; }
QPushButton:hover, QToolButton:hover { background: #d1e0ed; }
QPushButton:disabled { color: #8596a8; background: #edf1f5; }
QLineEdit, QSpinBox, QComboBox, QTableWidget {
    color: #1b2b3d; background: #ffffff; border: 1px solid #c2cfdd;
    border-radius: 4px; selection-background-color: #b7dbee;
}
QHeaderView::section { background: #dbe5f0; color: #23384b; border: none;
                       padding: 7px; }
QTableWidget::item:alternate { background: #eef4f9; }
QMenuBar, QMenu, QToolBar, QStatusBar { background: #e4ebf4; color: #1b2b3d; }
QToolBar { border-bottom: 1px solid #c5d2e0; spacing: 8px; }
QSplitter::handle { background: #c5d2e0; }
QLabel#headerTitle { font-size: 22px; font-weight: 700; }
QLabel#subTitle { color: #50677d; }
"""


def stylesheet(dark: bool = True) -> str:
    """Return Qt stylesheet for dark or light presentation."""
    return DARK if dark else LIGHT
