"""Monopoly-style typography with licensed-font-safe fallbacks.

The logo typeface is Kabel Heavy. This module uses a locally installed Kabel
font if the user has one. The Map loads its separate Caveat resource.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

from monopolpy_companion.lib.common.paths import APP_DATA_DIR

_DISPLAY_FAMILIES = (
    'Kabel LT Std', 'Kabel LTStd', 'ITC Kabel', 'Kabel Heavy', 'Kabel',
    'Monopoly Sans', 'Monopoly', 'League Spartan', 'Century Gothic', 'Avenir Next',
    'Montserrat', 'Arial Black', 'Segoe UI',
)
_BODY_FAMILIES = ('Monopoly Sans', 'Monopoly', 'Segoe UI Variable', 'Segoe UI', 'Inter', 'Arial')


def _available_family(candidates: tuple[str, ...]) -> str:
    """Pick an installed font family in preference order.

    Args:
        candidates: System font names, ordered by design preference.

    Returns:
        First installed family or the last fallback.
    """
    families = QFontDatabase.families()
    matches = {family.casefold(): family for family in families}
    return next(
        (matches[name.casefold()] for name in candidates if name.casefold() in matches),
        candidates[-1],
    )


def display_font(point_size: int = 24) -> QFont:
    """Return the actual Monopoly-style display font when installed."""
    font = QFont(_available_family(_DISPLAY_FAMILIES), point_size)
    font.setWeight(QFont.Weight.Black)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
    return font


def body_font(point_size: int = 10, *, family: str | None = None) -> QFont:
    """Return the requested body font or the first available default."""
    font = QFont(family or _available_family(_BODY_FAMILIES), point_size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def display_family() -> str:
    """Expose the available display family for QSS style rules."""
    return _available_family(_DISPLAY_FAMILIES)

def title_family() -> str:
    """Load Metro Retro NF from the local fonts folder, with a system fallback."""
    family = 'Metro Retro NF'
    if family in QFontDatabase.families():
        return family
    path = APP_DATA_DIR / 'fonts' / 'MetroRetroNF.ttf'
    if path.is_file():
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                return families[0]
    return display_family()


def load_user_font() -> str | None:
    """Register an optional font file owned and licensed by the user.

    The MONOPOLPY_FONT_FILE environment variable can point to an installed
    or otherwise legitimately licensed TTF/OTF font.

    Returns:
        The registered family name, or None if the file could not be loaded.
    """
    source = os.environ.get('MONOPOLPY_FONT_FILE', '').strip()
    if not source or not Path(source).is_file():
        return None
    font_id = QFontDatabase.addApplicationFont(source)
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    return families[0] if families else None
