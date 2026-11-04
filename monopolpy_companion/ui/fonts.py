"""Monopoly-style typography with licensed-font-safe fallbacks.

The logo typeface is Kabel Heavy. This module uses a locally installed Kabel
font if the user has one, and never bundles proprietary font files.
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase

_DISPLAY_FAMILIES = (
    'Kabel LT Std', 'Kabel LTStd', 'ITC Kabel', 'Kabel Heavy', 'Kabel',
    'Monopoly', 'League Spartan', 'Century Gothic', 'Avenir Next',
    'Montserrat', 'Arial Black', 'Segoe UI',
)
_BODY_FAMILIES = ('Segoe UI Variable', 'Segoe UI', 'Inter', 'Arial')


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


def body_font(point_size: int = 10) -> QFont:
    """Return a modern and readable system UI typeface."""
    font = QFont(_available_family(_BODY_FAMILIES), point_size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def display_family() -> str:
    """Expose the available display family for QSS style rules."""
    return _available_family(_DISPLAY_FAMILIES)
