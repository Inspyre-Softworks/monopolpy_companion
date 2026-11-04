"""Reusable polished Qt components for the Monopoly desktop dashboard.

Widgets carry their own accessible descriptions and help text. Views consume
presentation data only; game rules always remain in the headless engine.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QVBoxLayout, QWidget,
)

from .fonts import display_font


class HelpButton(QPushButton):
    """Action button with a visible label and keyboard-accessible description.

    Args:
        label: Action label.
        help_text: Tooltip and accessibility description.
        parent: Optional Qt parent.
    """

    def __init__(self, label: str, help_text: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.setToolTip(help_text)
        self.setStatusTip(help_text)
        self.setAccessibleName(label)
        self.setAccessibleDescription(help_text)
        self.setMinimumHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class ReadOnlyTable(QTableWidget):
    """Borderless, large-row table with accessible row-based selection.

    Args:
        headings: Visible column titles.
        description: Table purpose for accessibility and tooltips.
        parent: Optional Qt parent.
    """

    def __init__(
        self, headings: list[str], description: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(0, len(headings), parent)
        self.setHorizontalHeaderLabels(headings)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(42)
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWordWrap(False)
        self.setToolTip(description)
        self.setAccessibleDescription(description)
        self.horizontalHeader().setStretchLastSection(True)
        self.setMinimumHeight(180)


class PanelCard(QFrame):
    """Card with a modern typographic heading and a content layout.

    Args:
        title: Text heading.
        description: Short helper text below the title.
        parent: Optional Qt parent.
    """

    def __init__(
        self, title: str, description: str = '', parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName('surface')
        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(20, 18, 20, 18)
        self.layout_root.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName('panelTitle')
        self.layout_root.addWidget(heading)
        if description:
            explanation = QLabel(description)
            explanation.setObjectName('meta')
            explanation.setWordWrap(True)
            self.layout_root.addWidget(explanation)


class PropertyDetailCard(QFrame):
    """Always-visible ownership and price preview for a selected deed.

    Args:
        parent: Optional Qt parent.

    Notes:
        Game engine calculations are provided to update_property() as
        presentation-ready values. No game state is mutated by this widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('deedCard')
        self.setMinimumHeight(113)
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 16, 12)
        root.setSpacing(14)
        self.color_stripe = QFrame(self)
        self.color_stripe.setFixedWidth(9)
        self.color_stripe.setStyleSheet(
            'background-color: #24764e; border-radius: 4px;'
        )
        root.addWidget(self.color_stripe)
        words = QVBoxLayout()
        words.setSpacing(5)
        self.title = QLabel('Select a property')
        self.title.setObjectName('deedTitle')
        self.title.setFont(display_font(17))
        self.owner = QLabel('Owner —')
        self.owner.setObjectName('deedOwner')
        self.meta = QLabel('Choose a space on the board for its price and status.')
        self.meta.setObjectName('deedHint')
        self.meta.setWordWrap(True)
        words.addWidget(self.title)
        words.addWidget(self.owner)
        words.addWidget(self.meta)
        root.addLayout(words, stretch=1)

    def update_property(
        self, name: str, owner_name: str | None, *, price: int | None,
        rent_label: str, details: str, color: str | None = None,
    ) -> None:
        """Display a current deed and unmistakable owner state.

        Args:
            name: Board square display name.
            owner_name: Owning player's name, or None if unowned.
            price: Deed purchase price or None for nonownable squares.
            rent_label: Current rent or utility multiplier.
            details: Mortgage/development status.
            color: Optional property group color in hexadecimal form.
        """
        self.title.setText(name)
        self.owner.setText(
            f'OWNED BY {owner_name.upper()}' if owner_name else
            ('AVAILABLE TO BUY' if price is not None else 'BOARD SPACE')
        )
        parts = []
        if price is not None:
            parts.append(f'Price ${price:,}')
        if rent_label:
            parts.append(rent_label)
        if details:
            parts.append(details)
        self.meta.setText('   •   '.join(parts) if parts else 'No deed information')
        shade = color or '#24764e'
        self.color_stripe.setStyleSheet(
            f'background-color: {shade}; border-radius: 4px;'
        )

    def clear(self) -> None:
        """Restore empty selection hints."""
        self.update_property(
            'Select a property', None, price=None, rent_label='',
            details='Choose a board row to see its price and ownership.',
        )
