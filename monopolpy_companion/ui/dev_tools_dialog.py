"""Local game grants behind the Marauder’s Map phrase lock."""
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
)

from monopolpy_companion.controller import SessionSaveError
from monopolpy_companion.game import SpaceType


class DevToolsDialog(QDialog):
    def __init__(self, controller, player_id, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setObjectName('devToolsDialog')
        self.setWindowTitle('Marauder’s Map')
        self.setMinimumWidth(500)
        root = QVBoxLayout(self)
        form = QFormLayout()
        root.addLayout(form)

        self.player = QComboBox()
        for player in controller.session.players:
            if not player.bankrupt:
                self.player.addItem(player.name, player.player_id)
        index = self.player.findData(player_id)
        if index >= 0:
            self.player.setCurrentIndex(index)
        form.addRow('Recipient', self.player)

        self.cash = QSpinBox()
        self.cash.setRange(1, 1_000_000_000)
        self.cash.setPrefix('$')
        self.cash.setValue(500)
        self.cash_button = QPushButton('Grant cash')
        self.cash_button.clicked.connect(lambda: self._grant('dev_grant_cash', self.cash.value()))
        form.addRow(self.cash, self.cash_button)

        self.deed = QComboBox()
        self.deed_button = QPushButton('Grant deed')
        self.deed_button.clicked.connect(lambda: self._grant('dev_grant_deed', self.deed.currentData()))
        form.addRow(self.deed, self.deed_button)

        self.street = QComboBox()
        form.addRow('Owned street', self.street)
        buildings = QHBoxLayout()
        self.house_button = QPushButton('Add house')
        self.hotel_button = QPushButton('Grant hotel')
        self.house_button.clicked.connect(lambda: self._grant('dev_grant_building', self.street.currentData()))
        self.hotel_button.clicked.connect(
            lambda: self._grant('dev_grant_building', self.street.currentData(), hotel=True)
        )
        buildings.addWidget(self.house_button)
        buildings.addWidget(self.hotel_button)
        form.addRow(buildings)

        for button in (self.cash_button, self.deed_button, self.house_button, self.hotel_button):
            button.setAutoDefault(False)
        self.status = QLabel('Choose a recipient and grant an item.')
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        lock = buttons.addButton('Mischief managed', QDialogButtonBox.ButtonRole.ActionRole)
        lock.clicked.connect(self._lock)
        root.addWidget(buttons)

        self.player.currentIndexChanged.connect(self._populate)
        self.street.currentIndexChanged.connect(self._update_building_buttons)
        self._populate()

    def _populate(self):
        session = self.controller.session
        player_id = self.player.currentData()
        deed_index = self.deed.currentData()
        street_index = self.street.currentData()
        self.deed.clear()
        self.street.clear()
        for space in session.board:
            if not space.ownable:
                continue
            state = session.get_property_state(space.index)
            if state.owner_id is None:
                self.deed.addItem(space.name, space.index)
            elif (state.owner_id == player_id and space.space_type is SpaceType.PROPERTY
                  and not state.mortgaged and not state.hotel):
                unit = 'house' if state.houses == 1 else 'houses'
                self.street.addItem(f'{space.name} ({state.houses} {unit})', space.index)
        for combo, index in ((self.deed, deed_index), (self.street, street_index)):
            if index is not None and combo.findData(index) >= 0:
                combo.setCurrentIndex(combo.findData(index))
        self.deed_button.setEnabled(player_id is not None and self.deed.count() > 0)
        self.cash_button.setEnabled(player_id is not None)
        self._update_building_buttons()

    def _update_building_buttons(self):
        index = self.street.currentData()
        self.hotel_button.setEnabled(index is not None)
        self.house_button.setEnabled(
            index is not None and self.controller.session.get_property_state(index).houses < 4
        )

    def _grant(self, action, *args, **options):
        player_id = self.player.currentData()
        try:
            self.controller.perform(action, player_id, *args, **options)
        except SessionSaveError as exc:
            QMessageBox.warning(self, 'Grant applied, save failed', str(exc))
        except (ValueError, KeyError, OSError) as exc:
            QMessageBox.warning(self, 'Grant unavailable', str(exc))
            return
        else:
            player = self.controller.session.get_player(player_id)
            self.status.setText(f'Grant recorded for {player.name}. Balance ${player.cash:,}.')
        self._populate()

    def _lock(self):
        self.controller.lock_dev_tools()
        self.accept()
