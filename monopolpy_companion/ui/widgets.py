"""Reusable, self-documenting Qt widgets for MonopolPy Companion."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QPushButton, QTableWidget,
)


class HelpButton(QPushButton):
    """Button that carries an explanation for mouse and keyboard users.

    Args:
        label: Visible action text; this GUI avoids unlabeled icon buttons.
        help_text: Tooltip and accessible description.
        parent: Optional Qt parent widget.
    """

    def __init__(self, label: str, help_text: str, parent=None) -> None:
        super().__init__(label, parent)
        self.setToolTip(help_text)
        self.setAccessibleName(label)
        self.setAccessibleDescription(help_text)
        self.setMinimumHeight(34)


class ReadOnlyTable(QTableWidget):
    """Row-selectable, noneditable table with sensible keyboard navigation.

    Args:
        headings: Human-readable table column headings.
        description: Assistive text explaining the table contents.
        parent: Optional Qt parent.
    """

    def __init__(self, headings: list[str], description: str, parent=None) -> None:
        super().__init__(0, len(headings), parent)
        self.setHorizontalHeaderLabels(headings)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setToolTip(description)
        self.setAccessibleDescription(description)
        self.horizontalHeader().setStretchLastSection(True)
        self.setMinimumHeight(180)
