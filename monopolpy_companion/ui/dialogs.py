"""Dialog classes that collect user input without manipulating game rules."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QPushButton, QInputDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
    QLineEdit, QMessageBox, QSpinBox, QVBoxLayout,
)

from monopolpy_companion.game import GameSession


class NewSessionDialog(QDialog):
    """Collect initial session details for a new game."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('New Game')
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
        self.account_picker = QComboBox()
        self.account_picker.addItem('Select an existing account…', None)
        self.accounts = getattr(parent, 'accounts', None)
        self.selected_accounts = {}
        if self.accounts:
            for entry in self.accounts.entries():
                self.account_picker.addItem(entry['username'], entry)
        form.addRow('Existing accounts:', self.account_picker)
        add_account = QPushButton('Add selected account')
        add_account.clicked.connect(self._add_account)
        form.addRow(add_account)
        form.addRow('Starting cash:', self.cash_field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _add_account(self):
        entry = self.account_picker.currentData()
        if entry is None:
            return
        if ',' in entry['username']:
            QMessageBox.warning(self, 'Cannot add account',
                                'Account names cannot contain commas.')
            return
        try:
            try:
                account = self.accounts.unlock(entry)
            except PermissionError:
                password, ok = QInputDialog.getText(self, 'Unlock account',
                    'Password:', QLineEdit.EchoMode.Password)
                if not ok:
                    return
                account = self.accounts.unlock(entry, password)
        except (PermissionError, ValueError) as exc:
            QMessageBox.warning(self, 'Cannot unlock account', str(exc))
            return
        self.selected_accounts[entry['username'].casefold()] = account
        names = self.player_names
        if names == ['Player 1', 'Player 2']:
            names = []
        if entry['username'].casefold() not in {n.casefold() for n in names}:
            names.append(entry['username'])
        self.players_field.setText(', '.join(names))

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
        # Typed registered usernames must receive the same authentication and
        # PIN credentials as accounts chosen from the dropdown.
        if self.accounts:
            for index in range(1, self.account_picker.count()):
                entry = self.account_picker.itemData(index)
                key = entry['username'].casefold()
                if key in {name.casefold() for name in names} and key not in self.selected_accounts:
                    self.account_picker.setCurrentIndex(index)
                    self._add_account()
                    if key not in self.selected_accounts:
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


class NewAccountDialog(QDialog):
    """Register a reusable local account; credentials are never echoed."""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle('New Account')
        layout = QFormLayout(self)
        self.username = QLineEdit()
        self.availability = QLabel('Enter a username')
        self.password = QLineEdit()
        self.confirm = QLineEdit()
        self.pin = QLineEdit()
        for field in (self.password, self.confirm, self.pin):
            field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow('Username:', self.username)
        layout.addRow(self.availability)
        layout.addRow('Encryption password (optional):', self.password)
        layout.addRow('Confirm password:', self.confirm)
        layout.addRow('Transaction PIN (optional, 4–8 digits):', self.pin)
        note = QLabel('Encryption protects the local account file. Game saves remain unencrypted. '
                      'Keep your password safe: there is no password recovery.')
        note.setWordWrap(True)
        layout.addRow(note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                       QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(self.buttons)
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        self.username.textChanged.connect(self._check)
        self._check()

    def _check(self):
        available = self.store.available(self.username.text())
        self.availability.setText('Username available' if available else
                                  'Username is empty, contains a comma, or already exists')
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(available)

    def _save(self):
        if self.password.text() != self.confirm.text():
            QMessageBox.warning(self, 'Password mismatch', 'Passwords must match.')
            return
        try:
            self.store.create(self.username.text(), self.password.text(), self.pin.text())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Cannot create account', str(exc))
            return
        self.accept()


class SettingsDialog(QDialog):
    """Persist desktop preferences using the platform settings store."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle('Settings')
        layout = QFormLayout(self)
        self.dark = QCheckBox('Dark theme')
        self.sparkles = QCheckBox('Animated button glow')
        self.alerts = QCheckBox('Landing alerts for new games')
        for field, key in [(self.dark, 'dark'), (self.sparkles, 'sparkles'),
                           (self.alerts, 'landing_alerts')]:
            field.setChecked(settings.value(key, True, type=bool))
            layout.addRow(field)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                  QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

    def _save(self):
        for field, key in [(self.dark, 'dark'), (self.sparkles, 'sparkles'),
                           (self.alerts, 'landing_alerts')]:
            self.settings.setValue(key, field.isChecked())
        self.settings.sync()
        self.accept()


class GameSettingsDialog(QDialog):
    """Edit rules for the active game and persist them through its controller."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle('Game Settings')
        layout = QFormLayout(self)
        self.salary = QSpinBox()
        self.salary.setRange(0, 1000000)
        self.salary.setPrefix('$')
        self.salary.setValue(controller.session.rules.salary_on_go)
        self.salary.setToolTip('Paid automatically when forward movement passes or lands on GO. Zero disables salary.')
        layout.addRow('GO salary:', self.salary)
        self.double_salary = QCheckBox('Double salary when landing on GO')
        self.double_salary.setChecked(controller.session.rules.double_salary_on_go)
        layout.addRow(self.double_salary)
        self.three_doubles = QCheckBox('Three consecutive doubles send the player directly to Jail')
        self.three_doubles.setChecked(controller.session.rules.three_doubles_to_jail)
        self.three_doubles.setToolTip('Enabled by default. Turn off to allow further rolls after a third consecutive double.')
        layout.addRow(self.three_doubles)
        self.rent_immunity = QCheckBox('Allow rent immunity trades')
        self.rent_immunity.setChecked(controller.session.rules.allow_rent_immunity)
        layout.addRow(self.rent_immunity)
        self.immunity_follows_deed = QCheckBox('Property-specific immunity follows traded deeds')
        self.immunity_follows_deed.setChecked(controller.session.rules.immunity_follows_deed)
        layout.addRow(self.immunity_follows_deed)
        note = QLabel('Applies to this game and is saved with it. Moves that explicitly skip GO salary, '
                      'such as being sent to Jail, do not earn a payment.')
        note.setWordWrap(True)
        layout.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                  QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(buttons)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

    def _save(self):
        try:
            self.controller.set_go_salary(self.salary.value(), double_on_go=self.double_salary.isChecked(),
                                          three_doubles_to_jail=self.three_doubles.isChecked(),
                                          allow_rent_immunity=self.rent_immunity.isChecked(),
                                          immunity_follows_deed=self.immunity_follows_deed.isChecked())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Cannot save game settings', str(exc))
            return
        self.accept()
