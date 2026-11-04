"""Monopoly-inspired icon and board palette, without bundled proprietary assets."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap

BOARD_GROUP_COLORS = {
    'Brown': '#8f5a32',
    'Light Blue': '#78c8ed',
    'Pink': '#d86f9f',
    'Orange': '#f8a13d',
    'Red': '#df3a35',
    'Yellow': '#edcb43',
    'Green': '#36935f',
    'Dark Blue': '#2e589d',
}


def make_app_icon() -> QIcon:
    """Draw a scalable game-themed icon from basic shapes.

    Returns:
        Icon with a red Monopoly-style title tile, an ivory M and a green
        footer. No externally licensed fonts or brand artwork are included.
    """
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#183c2c'), 5))
    painter.setBrush(QColor('#f0eee4'))
    painter.drawRoundedRect(QRectF(6, 6, 116, 116), 18, 18)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#c82831'))
    painter.drawRoundedRect(QRectF(14, 17, 100, 77), 9, 9)
    painter.setPen(QColor('#ffffff'))
    title_font = QFont('Arial Black', 55, QFont.Weight.Black)
    painter.setFont(title_font)
    painter.drawText(QRectF(14, 13, 100, 85), Qt.AlignmentFlag.AlignCenter, 'M')
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#287b4c'))
    painter.drawRoundedRect(QRectF(14, 99, 100, 14), 4, 4)
    painter.end()
    return QIcon(pixmap)
