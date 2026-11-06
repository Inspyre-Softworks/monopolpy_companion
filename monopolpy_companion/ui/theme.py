"""Modern board-inspired theme with warm paper and modern surface hierarchy.

Styles deliberately avoid platform-default group boxes, heavy grid lines,
pill-less rectangular controls and oversaturated full-screen backgrounds.
"""

from __future__ import annotations

from .fonts import display_family, title_family


_DARK = {
    'app': '#101b18',
    'surface': '#192824',
    'surface_alt': '#223630',
    'field': '#243a33',
    'text': '#f7f6ef',
    'subtle': '#b6c9c0',
    'line': '#344c43',
    'red': '#e43e46',
    'red_hover': '#f05a60',
    'green': '#70d1a0',
    'green_dark': '#235b40',
    'table_alt': '#1f322c',
    'highlight': '#2b5543',
    'red_text': '#ffffff',
}
_LIGHT = {
    'app': '#e9ede6',
    'surface': '#fffef7',
    'surface_alt': '#f0f4ec',
    'field': '#ffffff',
    'text': '#14271d',
    'subtle': '#597064',
    'line': '#d8e2d8',
    'red': '#bd2934',
    'red_hover': '#a51f2d',
    'green': '#176340',
    'green_dark': '#d5efdb',
    'table_alt': '#f8faf5',
    'highlight': '#e0f1e3',
    'red_text': '#ffffff',
}


def stylesheet(dark: bool = True) -> str:
    """Return a responsive desktop stylesheet with distinct information levels."""
    t = _DARK if dark else _LIGHT
    heading_font = display_family().replace('"', '')
    title = title_family()
    title_weight = 400 if title == 'Metro Retro NF' else 900
    title = title.replace('"', '')
    return f"""
    QWidget {{
        font-size: 12px;
        color: {t['text']};
        background-color: transparent;
    }}
    QMainWindow, QWidget#centralSurface {{
        background-color: {t['app']};
    }}
    QToolTip {{
        background-color: {t['surface']};
        color: {t['text']};
        border: 1px solid {t['line']};
        padding: 5px 8px;
    }}
    QDialog#tradeDialog, QDialog#playerAccountDialog, QDialog#devToolsDialog {{ background-color: {t['app']}; }}
    QFrame#surface {{
        background-color: {t['surface']};
        border: 1px solid {t['line']};
        border-radius: 18px;
    }}
    QFrame#hero {{
        background-color: {t['surface']};
        border: 1px solid {t['line']};
        border-radius: 20px;
    }}
    QFrame#deedCard {{
        background-color: {t['surface_alt']};
        border: 1px solid {t['line']};
        border-radius: 13px;
    }}
    QLabel#headerTitle {{
        color: {t['text']};
        font-family: "{title}";
        font-size: 28px;
        font-weight: {title_weight};
        background: transparent;
    }}
    QLabel#eyebrow {{
        font-size: 10px;
        font-weight: bold;
        color: {t['red']};
        letter-spacing: 1px;
    }}
    QLabel#subTitle, QLabel#meta, QLabel#deedHint {{
        color: {t['subtle']};
        background: transparent;
    }}
    QLabel#panelTitle {{
        color: {t['text']};
        font-size: 16px;
        font-weight: 750;
    }}
    QLabel#deedTitle {{
        font-family: "{heading_font}";
        color: {t['text']};
        font-size: 19px;
        font-weight: 800;
        background: transparent;
    }}
    QLabel#deedOwner {{
        color: {t['green']};
        font-size: 13px;
        font-weight: 800;
        background: transparent;
    }}
    QFrame#playerTracker {{
        background-color: {t['surface']};
        border: 1px solid {t['line']};
        border-radius: 10px;
    }}
    QFrame#playerTracker[currentTurn="true"] {{
        background-color: {t['highlight']};
        border: 2px solid #e6bd4f;
    }}
    QFrame#playerTracker QLabel {{ border: none; background: transparent; }}
    QLabel#trackerCash {{ font-size: 24px; font-weight: 750; color: {t['green']}; }}
    QLabel#deedOwner {{ font-size: 17px; font-weight: 700; }}
    QLabel#activityBanner {{
        background-color: {t['highlight']};
        border: 1px solid {t['green_dark']};
        border-radius: 10px;
        color: {t['text']};
        padding: 12px 16px;
        font-weight: 650;
    }}
    QToolBar {{
        background: {t['surface']};
        border: 0;
        border-bottom: 1px solid {t['line']};
        spacing: 7px;
        padding: 10px 18px;
    }}
    QToolBar::separator {{
        width: 1px;
        margin: 7px 12px;
        background: {t['line']};
    }}
    QToolButton {{
        background: {t['surface_alt']};
        border: 1px solid {t['line']};
        color: {t['text']};
        border-radius: 10px;
        padding: 8px 14px;
        font-weight: 650;
    }}
    QToolButton:hover, QToolButton:checked {{
        background: {t['highlight']};
        border-color: {t['green']};
    }}
    QPushButton {{
        background-color: {t['surface_alt']};
        border: 1px solid {t['line']};
        border-radius: 10px;
        padding: 9px 14px;
        color: {t['text']};
        font-weight: 650;
        min-height: 22px;
    }}
    QPushButton:hover {{
        background-color: {t['highlight']};
        border-color: {t['green']};
    }}
    QPushButton#primaryAction {{
        background: {t['red']};
        border-color: {t['red']};
        color: {t['red_text']};
        font-weight: 750;
    }}
    QPushButton#primaryAction:hover {{
        background: {t['red_hover']};
    }}
    QPushButton:disabled, QToolButton:disabled {{
        color: {t['subtle']};
        background-color: {t['field']};
        border-color: {t['line']};
    }}
    QComboBox, QSpinBox, QLineEdit, QPlainTextEdit, QTextEdit, QListWidget {{
        background-color: {t['field']};
        color: {t['text']};
        border: 1px solid {t['line']};
        border-radius: 9px;
        padding: 8px 12px;
        min-height: 21px;
        selection-background-color: {t['green_dark']};
    }}
    QComboBox::drop-down {{ border: none; width: 27px; }}
    QComboBox QAbstractItemView {{
        background-color: {t['surface']};
        border: 1px solid {t['line']};
        selection-background-color: {t['highlight']};
    }}
    QTableWidget {{
        background-color: {t['surface']};
        alternate-background-color: {t['table_alt']};
        color: {t['text']};
        border: 0;
        border-radius: 9px;
        gridline-color: transparent;
        selection-background-color: {t['highlight']};
        selection-color: {t['text']};
    }}
    QTableWidget::item {{
        border: 0;
        padding: 4px 9px;
    }}
    QTableWidget::item:selected {{
        background-color: {t['highlight']};
        color: {t['text']};
    }}
    QHeaderView::section {{
        color: {t['subtle']};
        background-color: {t['surface_alt']};
        border: 0;
        border-bottom: 1px solid {t['line']};
        padding: 10px 10px;
        font-size: 11px;
        font-weight: 700;
    }}
    QSplitter::handle {{ background-color: transparent; }}
    QSplitter::handle:hover {{ background-color: {t['line']}; }}
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t['line']};
        border-radius: 4px;
        min-height: 28px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        border: none;
    }}
    QMenu, QStatusBar {{
        background: {t['surface']};
        color: {t['subtle']};
        border: 0;
        padding: 5px;
    }}
    QTabWidget::pane {{
        background: {t['surface']};
        border: 1px solid {t['line']};
        border-radius: 10px;
        padding: 8px;
    }}
    QTabBar::tab {{
        background: {t['surface_alt']};
        padding: 10px 18px;
        margin-right: 5px;
        border-radius: 8px;
    }}
    QTabBar::tab:selected {{
        background: {t['highlight']};
        color: {t['text']};
    }}
    QGroupBox {{
        border: 1px solid {t['line']};
        border-radius: 13px;
        margin-top: 18px;
        padding: 12px;
        background: {t['surface']};
        font-weight: 700;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 7px;
    }}
    """
