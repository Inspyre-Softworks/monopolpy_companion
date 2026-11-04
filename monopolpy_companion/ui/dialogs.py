"""Dialog classes that collect user input without manipulating game rules."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QMessageBox, QSpinBox, QVBoxLayout,
)

from monopolpy_companion.game import GameSession


class NewSessionDialog(QDialog):
    """Collect initial session details for a new game."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('New Monopoly session')
        self.setMinimumWidth(430)
        form = QFormLayout()
        self.name_field = QLineEdit('Game Night')
        self.name_field.setToolTip('Friendly name for this Monopoly game and its save file.')
        self.players_field = QLineEdit('Player 1, Player 2')
        self.players_field.setToolTip('Enter at least two player names, separated by commas.')
        self.cash_field = QSpinBox()
        self.cash_field.setRange(1, 100000)
        self.cash_field.setValue(1500)
        self.cash_field.setToolTip('Starting Monopoly dollars for every player.')
        form.addRow('Game name:', self.name_field)
        form.addRow('Players:', self.players_field)
        form.addRow('Starting cash:', self.cash_field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def game_name(self) -> str:
        """Return the trimmed session label."""
        return self.name_field.text().strip() or 'Game Night'

    @property
    def player_names(self) -> list[str]:
        """Return nonempty player names entered in the setup dialog."""
        return [name.strip() for name in self.players_field.text().split(',')
                if name.strip()]

    @property
    def starting_cash(self) -> int:
        """Return the selected starting balance in whole dollars."""
        return self.cash_field.value()

    def _validate(self) -> None:
        names = self.player_names
        if len(names) < 2:
            QMessageBox.warning(self, 'More players needed',
                                'Please enter at least two player names.')
            return
        if len(set(name.casefold() for name in names)) != len(names):
            QMessageBox.warning(self, 'Duplicate names',
                                'Give each player a distinct name.')
            return
        self.accept()


class TransferDialog(QDialog):
    """Collect validated player/bank transfer parameters."""

    def __init__(self, session: GameSession, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Bank and player transfer')
        self.setMinimumWidth(390)
        self.sender = QComboBox()
        self.receiver = QComboBox()
        self.sender.addItem('Bank', None)
        self.receiver.addItem('Bank', None)
        for player in session.players:
            self.sender.addItem(player.name, player.player_id)
            self.receiver.addItem(player.name, player.player_id)
        self.sender.setToolTip('Who pays? Select Bank to create a bank payout.')
        self.receiver.setToolTip('Who receives? Select Bank for a bank payment.')
        self.receiver.setCurrentIndex(1)
        self.amount_field = QSpinBox()
        self.amount_field.setRange(1, 1000000)
        self.amount_field.setValue(50)
        self.amount_field.setPrefix('$')
        self.amount_field.setToolTip('Whole-dollar amount to transfer.')
        self.category = QComboBox()
        self.category.addItem('Other payment / event', 'event')
        self.category.addItem('Player deal', 'deal')
        self.category.addItem('General transfer', 'cash_transfer')
        self.category.setToolTip('Categorize this payment for player financial statistics.')
        self.description_field = QLineEdit('Manual transfer')
        self.description_field.setToolTip('Reason recorded in the game ledger.')
        form = QFormLayout()
        form.addRow('From:', self.sender)
        form.addRow('To:', self.receiver)
        form.addRow('Amount:', self.amount_field)
        form.addRow('Category:', self.category)
        form.addRow('Reason:', self.description_field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel('All completed transfers appear in the ledger.'))
        layout.addWidget(buttons)

    @property
    def transfer_args(self) -> dict:
        """Return kwargs for GameEngine.transfer."""
        return {
            'amount': self.amount_field.value(),
            'from_player_id': self.sender.currentData(),
            'to_player_id': self.receiver.currentData(),
            'description': self.description_field.text().strip() or 'Manual transfer',
            'kind': self.category.currentData(),
        }

    def _validate(self) -> None:
        args = self.transfer_args
        if args['from_player_id'] == args['to_player_id']:
            QMessageBox.warning(self, 'Invalid transfer',
                                'Choose different source and destination accounts.')
            return
        self.accept()
