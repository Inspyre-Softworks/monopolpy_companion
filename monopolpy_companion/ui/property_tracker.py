"""Per-player property strips rendered from the authoritative session state."""
from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget, QToolTip

from monopolpy_companion.game import SpaceType
from .branding import BOARD_GROUP_COLORS

GROUPS = tuple(BOARD_GROUP_COLORS) + ('Railroads', 'Utilities')
GROUP_COLORS = {**BOARD_GROUP_COLORS, 'Railroads': '#000000', 'Utilities': '#808080'}


def property_group(space):
    if space.space_type is SpaceType.RAILROAD:
        return 'Railroads'
    if space.space_type is SpaceType.UTILITY:
        return 'Utilities'
    return space.color_group


class PropertyTile(QWidget):
    """A deed indicator with color-independent ownership and mortgage help."""

    def __init__(self, space, group, parent=None):
        super().__init__(parent)
        self.space = space
        self.color = QColor(GROUP_COLORS[group])
        self.owned = False
        self.mortgaged = False
        self.houses = 0
        self.hotel = False
        self.setFixedSize(18, 36)
        self.setAccessibleName(space.name)
        self.setToolTip(space.name)
        self.setMouseTracking(True)

    def refresh(self, state, player_id, owner_name):
        self.owned = state.owner_id == player_id
        self.mortgaged = self.owned and state.mortgaged
        self.houses = state.houses if self.owned else 0
        self.hotel = self.owned and state.hotel
        status = ('Owned by this player' if self.owned else
                  f'Owned by {owner_name}' if owner_name else 'Unowned')
        if state.mortgaged:
            status += ' (mortgaged)'
        if state.hotel:
            status += ' (hotel)'
        elif state.houses:
            unit = 'house' if state.houses == 1 else 'houses'
            status += f' ({state.houses} {unit})'
        description = f'{self.space.index}: {self.space.name} - {status}'
        self.setToolTip(description)
        self.setAccessibleDescription(description)
        self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        anchor = self.mapToGlobal(QPoint(0, self.height() + 4))
        QToolTip.showText(anchor, self.toolTip(), self, self.rect())

    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(2, 2, self.width()-4, self.height()-4)
        fill = QColor(self.color) if self.owned else None
        if self.mortgaged:
            fill = QColor(*[int(channel * .4 + 145 * .6)
                            for channel in (fill.red(), fill.green(), fill.blue())])
        painter.setBrush(fill if fill is not None else Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(self.color, 3))
        painter.drawRect(rect)
        if not self.mortgaged:
            painter.setPen(QPen(QColor('#18251d'), 1))
            if self.hotel:
                painter.setBrush(QColor('#ff4c55'))
                painter.drawRect(QRectF(3, self.height() / 2 - 4, self.width() - 6, 8))
            else:
                painter.setBrush(QColor('#60ee83'))
                for index in range(self.houses):
                    y = self.height() - 9 - index * 7
                    painter.drawRect(QRectF(3, y, self.width() - 6, 5))
        if self.mortgaged:
            # A bright under-stroke keeps the X visible on black railroads too.
            for color, width in [('#f2f2f2', 4), ('#454545', 2)]:
                painter.setPen(QPen(QColor(color), width))
                painter.drawLine(rect.topLeft(), rect.bottomRight())
                painter.drawLine(rect.bottomLeft(), rect.topRight())


class PropertyGroup(QWidget):
    """Keep a complete ownership set together inside its gold outline."""

    def __init__(self, name, spaces, parent=None):
        super().__init__(parent)
        self.name = name
        self.complete = False
        self.tiles = [PropertyTile(space, name, self) for space in spaces]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 5, 4, 5)
        layout.setSpacing(2)
        for tile in self.tiles:
            layout.addWidget(tile)
        self.setAccessibleName(name)
        self.setFixedSize(layout.sizeHint())

    def refresh(self, session, player_id):
        for tile in self.tiles:
            state = session.get_property_state(tile.space.index)
            owner = session.owner_for(tile.space.index)
            tile.refresh(state, player_id, owner.name if owner else None)
        self.complete = bool(self.tiles) and all(tile.owned for tile in self.tiles)
        description = self.name + (' - Complete set' if self.complete else ' - Incomplete set')
        self.setToolTip(description)
        self.setAccessibleDescription(description)
        self.update()

    def paintEvent(self, event):
        if self.complete:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor('#e6bd4f'), 2))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 5, 5)


class PlayerTrackerPanel(QFrame):
    """One persistent horizontal row for a player's wallet and all 28 deeds."""

    def __init__(self, player, board, parent=None):
        super().__init__(parent)
        self.player_id = player.player_id
        self.current_turn = False
        self.setObjectName('playerTracker')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        identity = QVBoxLayout()
        self.name_label = QLabel()
        self.name_label.setFixedWidth(160)
        self.name_label.setWordWrap(True)
        self.cash_label = QLabel()
        self.cash_label.setObjectName('trackerCash')
        self.cash_label.setMinimumWidth(160)
        self.turn_label = QLabel()
        self.turn_label.setObjectName('meta')
        identity.addWidget(self.name_label)
        identity.addWidget(self.cash_label)
        identity.addWidget(self.turn_label)
        layout.addLayout(identity)
        self.groups = {}
        self.tiles = {}
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(5)
        for index, name in enumerate(GROUPS):
            spaces = sorted((space for space in board if space.ownable
                             and property_group(space) == name), key=lambda space: space.index)
            group = PropertyGroup(name, spaces, self)
            self.groups[name] = group
            self.tiles.update({tile.space.index: tile for tile in group.tiles})
            grid.addWidget(group, index // 5, index % 5, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(grid)
        layout.addStretch()
        self.setMinimumHeight(130)
        self.setMinimumWidth(layout.sizeHint().width())

    def refresh(self, session):
        player = session.get_player(self.player_id)
        self.name_label.setText(player.name)
        self.cash_label.setText(f'${player.cash:,}')
        self.current_turn = session.current_player is player
        self.turn_label.setText('CURRENT TURN' if self.current_turn else
                                'BANKRUPT' if player.bankrupt else '')
        self.setProperty('currentTurn', self.current_turn)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setAccessibleName(f'{player.name} property ownership')
        self.setAccessibleDescription(f"Cash ${player.cash:,}. " + self.turn_label.text())
        for group in self.groups.values():
            group.refresh(session, player.player_id)


class PropertyTrackers(QScrollArea):
    """Independently scroll player rows without wrapping the property strips."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumHeight(150)
        self.content = QWidget()
        self.rows = QVBoxLayout(self.content)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(8)
        self.rows.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.content)
        self.panels = {}
        self._board_key = None
        self.setAccessibleName('Player property ownership trackers')

    def refresh(self, session):
        players = session.players if session else []
        board_key = session.board_key if session else None
        if list(self.panels) != [player.player_id for player in players] or self._board_key != board_key:
            while self.rows.count():
                widget = self.rows.takeAt(0).widget()
                widget.setParent(None)
                widget.deleteLater()
            self.panels = {}
            self._board_key = board_key
            for player in players:
                panel = PlayerTrackerPanel(player, session.board, self.content)
                self.panels[player.player_id] = panel
                self.rows.addWidget(panel)
        for panel in self.panels.values():
            panel.refresh(session)
