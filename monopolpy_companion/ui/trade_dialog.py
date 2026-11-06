"""Two-sided trade entry and a reviewable quote from the game engine."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QSpinBox, QVBoxLayout)


from .property_tracker import property_group


class TradeDialog(QDialog):
    """Collect each player's offer without changing the game."""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.setObjectName('tradeDialog')
        self.controller = controller
        self.setWindowTitle('Trade with another player')
        self.resize(760, 600)
        root = QVBoxLayout(self)
        columns = QHBoxLayout()
        self.sides = []
        for _ in range(2):
            group = QGroupBox()
            form = QFormLayout(group)
            player = QComboBox()
            for person in controller.session.players:
                if not person.bankrupt:
                    player.addItem(person.name, person.player_id)
            cash = QSpinBox()
            cash.setRange(0, 1000000000)
            cash.setPrefix('$')
            cards = QSpinBox()
            cards.setRange(0, 1000000)
            deeds = QListWidget()
            deeds.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            deeds.setToolTip('Select all properties this player offers. Click again to deselect.')
            form.addRow('Player:', player)
            form.addRow('Cash offered:', cash)
            form.addRow('Jail cards offered:', cards)
            form.addRow('Properties:', deeds)
            value = QLabel()
            form.addRow('Cash + printed deed prices:', value)
            scope = QComboBox()
            unit = QComboBox()
            unit.addItem('Rent charges waived', 'landings')
            unit.addItem('GO crossings', 'laps')
            unit.addItem('Recipient’s completed turns', 'turns')
            duration = QSpinBox()
            duration.setRange(0, 999)
            duration.setToolTip('Zero means no immunity. GO crossings and completed turns count for the recipient.')
            if controller.session.rules.allow_rent_immunity:
                form.addRow('Rent immunity on:', scope)
                form.addRow('Measured in:', unit)
                form.addRow('Duration (0 = none):', duration)
            else:
                for widget in (scope, unit, duration):
                    widget.hide()
            self.sides.append({'player': player, 'cash': cash, 'cards': cards, 'deeds': deeds,
                               'group': group, 'value': value, 'scope': scope,
                               'unit': unit, 'duration': duration})
            columns.addWidget(group)
        root.addLayout(columns)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        note = QLabel('Mortgaged deeds stay mortgaged. Their recipient pays 10% mortgage interest to the bank. '
                      'Sell all buildings in a color set before trading its properties. '
                      'Existing unpaid rent and tax charges remain payable.')
        if controller.session.rules.allow_rent_immunity and controller.session.rules.immunity_follows_deed:
            note.setText(note.text() + ' Existing property-specific immunity follows traded deeds.')
        note.setWordWrap(True)
        root.addWidget(note)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Review trade')
        self.buttons.accepted.connect(self._validate)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)
        if self.sides[1]['player'].count() > 1:
            self.sides[1]['player'].setCurrentIndex(1)
        for index, side in enumerate(self.sides):
            side['player'].currentIndexChanged.connect(lambda _value, index=index: self._populate(index))
            side['cash'].valueChanged.connect(self._quote)
            side['cards'].valueChanged.connect(self._quote)
            side['deeds'].itemSelectionChanged.connect(self._update_scopes)
            side['scope'].currentIndexChanged.connect(self._quote)
            side['unit'].currentIndexChanged.connect(self._quote)
            side['duration'].valueChanged.connect(self._quote)
        self._populate(0)
        self._populate(1)

    def _populate(self, index):
        side = self.sides[index]
        side['group'].setTitle(f"{side['player'].currentText()} gives")
        side['duration'].setValue(0)
        side['scope'].setCurrentIndex(0)
        side['deeds'].blockSignals(True)
        side['deeds'].clear()
        player_id = side['player'].currentData()
        if player_id is not None:
            for space in self.controller.session.owned_spaces_for(player_id):
                state = self.controller.session.get_property_state(space.index)
                item = QListWidgetItem(space.name + (' (mortgaged)' if state.mortgaged else ''))
                group = property_group(space)
                color = {'Railroads': 'Black (Railroad)', 'Utilities': 'Gray (Utility)'}.get(group, group)
                item.setToolTip(f'{space.name}\nPrinted price: ${space.price:,}\nColor: {color}')
                item.setData(Qt.ItemDataRole.UserRole, space.index)
                side['deeds'].addItem(item)
        side['cash'].setValue(0)
        side['cards'].setValue(0)
        side['deeds'].blockSignals(False)
        self._update_scopes()

    def _update_scopes(self):
        if self.controller.session.rules.allow_rent_immunity:
            for index, side in enumerate(self.sides):
                other = self.sides[1 - index]
                role = Qt.ItemDataRole.UserRole
                outgoing = {item.data(role) for item in side['deeds'].selectedItems()}
                incoming = {item.data(role) for item in other['deeds'].selectedItems()}
                player_id = side['player'].currentData()
                owned = {space.index for space in self.controller.session.owned_spaces_for(player_id)}
                scope = side['scope']
                previous = scope.currentData()
                scope.blockSignals(True)
                scope.clear()
                scope.addItem('All properties owned by this player', None)
                for deed in sorted((owned - outgoing) | incoming):
                    scope.addItem(self.controller.session.board[deed].name, deed)
                previous_index = scope.findData(previous)
                if previous is not None and previous_index < 0:
                    scope.addItem('Previously selected deed unavailable', previous)
                    previous_index = scope.count() - 1
                scope.setCurrentIndex(max(previous_index, 0))
                scope.blockSignals(False)
        self._quote()

    @property
    def trade_args(self):
        result = {}
        for key, side in zip(('a', 'b'), self.sides):
            result[f'player_{key}_id'] = side['player'].currentData()
            result[f'cash_{key}'] = side['cash'].value()
            result[f'cards_{key}'] = side['cards'].value()
            result[f'properties_{key}'] = [item.data(Qt.ItemDataRole.UserRole)
                for item in side['deeds'].selectedItems()]
            if self.controller.session.rules.allow_rent_immunity and side['duration'].value():
                result[f'immunity_{key}'] = (side['scope'].currentData(), side['unit'].currentData(),
                                             side['duration'].value())
        return result

    def _quote(self, *_):
        args = self.trade_args
        board = self.controller.session.board
        for key, side in zip(('a', 'b'), self.sides):
            deed_value = sum(board[index].price for index in args[f'properties_{key}'])
            side['value'].setText(f"${args[f'cash_{key}'] + deed_value:,} (deeds: ${deed_value:,})")
        try:
            quote = self.controller.engine.trade_quote(**args)
            lines = []
            for key in ('a', 'b'):
                person = self.controller.session.get_player(args[f'player_{key}_id'])
                names = ', '.join(self.controller.session.board[index].name
                                 for index in args[f'properties_{key}']) or 'no deeds'
                grant = args.get(f'immunity_{key}')
                immunity = (f" Rent immunity: {self.controller.engine.immunity_description(grant)}."
                            if grant else '')
                if self.controller.session.rules.immunity_follows_deed:
                    for existing in self.controller.session.rent_immunity:
                        if (existing['grantor_id'] == person.player_id and existing['remaining'] > 0
                                and existing['space_index'] in args[f'properties_{key}']):
                            beneficiary = self.controller.session.get_player(existing['beneficiary_id'])
                            terms = (existing['space_index'], existing['unit'], existing['remaining'])
                            immunity += (f" Deed carries immunity for {beneficiary.name}: "
                                         f"{self.controller.engine.immunity_description(terms)}.")
                lines.append(f"{person.name} gives ${args[f'cash_{key}']:,}, {names}, "
                    f"{args[f'cards_{key}']} jail card(s). Bank interest: ${quote[f'fee_{key}']:,}. "
                    f"Cash after trade: ${quote[f'final_{key}']:,}.{immunity}")
            self.summary.setText('\n'.join(lines))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        except (ValueError, KeyError, TypeError) as exc:
            self.summary.setText(str(exc))
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _validate(self):
        self._quote()
        if self.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
            self.accept()
