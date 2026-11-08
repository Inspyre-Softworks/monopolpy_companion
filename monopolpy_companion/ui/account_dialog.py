"""Reusable player account window with stats, PIN control and mortgage planner."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget, QScrollArea, QFrame,
)

from monopolpy_companion.controller import SessionController, SessionSaveError
from monopolpy_companion.game import PlayerAccount, StatisticsService

from .property_tracker import GROUP_COLORS, property_group


class PlayerAccountDialog(QDialog):
    """Display one player's financial history and mortgage decisions.

    Args:
        controller: Authoritative controller for the active game.
        player_id: Account owner's stable player identifier.
        parent: Optional parent widget.

    Notes:
        PIN protection is enforced by the SessionController. The dialog
        contains no rules for mortgages or financial statistics.
    """

    def __init__(self, controller: SessionController, player_id: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName('playerAccountDialog')
        self.controller = controller
        self.player_id = player_id
        self.setWindowTitle(f'Player account: {self.player.name}')
        self.resize(660, 690)
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)

        self.heading = QLabel()
        root.addWidget(self.heading)
        self.stats_scope = QComboBox()
        self.stats_scope.setAccessibleName('Statistics scope')
        self.stats_scope.setToolTip('Choose this game, a saved game, or overall totals from local saves.')
        root.addWidget(self.stats_scope)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        self.gameplay_text = self._text_tab(
            'Gameplay', 'Dice rolls, movement and property history.'
        )
        self.finance_text = self._text_tab(
            'Financial', 'Cash movements and rent broken down by player and property.'
        )
        root.addWidget(self._security_bar())
        self.mortgage_tab = self._build_mortgages()
        self.tabs.addTab(self.mortgage_tab, 'Mortgages')
        self.tabs.currentChanged.connect(
            lambda: self.stats_scope.setVisible(self.tabs.currentWidget() is not self.mortgage_tab)
        )
        self.stats_scope.currentIndexChanged.connect(self._render_statistics)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.refresh()

    @property
    def player(self):
        """Return the active Player, including changes since dialog opened."""
        return self.controller.session.get_player(self.player_id)

    def _text_tab(self, name: str, help_text: str) -> QTextEdit:
        """Add a readable, keyboard-accessible statistics tab."""
        field = QTextEdit()
        field.setReadOnly(True)
        field.setToolTip(help_text)
        field.setAccessibleDescription(help_text)
        self.tabs.addTab(field, name)
        return field

    def _security_bar(self) -> QGroupBox:
        """Set up PIN management buttons that use the controller security API."""
        panel = QGroupBox('Account PIN')
        layout = QHBoxLayout(panel)
        self.pin_status = QLabel()
        layout.addWidget(self.pin_status)
        for label, explanation, handler in [
            ('Set / change PIN', 'Set or change this player\'s 4–8 digit PIN.', self._set_pin),
            ('Remove PIN', 'Remove account protection after authorization.', self._remove_pin),
            ('Lock now', 'Forget the current PIN authorization.', self._lock_now),
        ]:
            button = QPushButton(label)
            button.setToolTip(explanation)
            button.clicked.connect(handler)
            layout.addWidget(button)
        return panel

    def _build_mortgages(self) -> QWidget:
        """Make a multi-selection mortgage planner and executor."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel(
            'Select multiple owned deeds to calculate mortgage proceeds or payoff.'
        ))
        self.operation = QComboBox()
        self.operation.addItem('Unmortgage / pay off', 'unmortgage')
        self.operation.addItem('Mortgage / borrow', 'mortgage')
        self.operation.setToolTip('Choose whether to borrow cash or repay mortgages.')
        layout.addWidget(self.operation)
        self.properties = QListWidget()
        self.properties.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.properties.setToolTip('Click each owned deed to add or remove it from the selection.')
        layout.addWidget(self.properties)
        self.quote_label = QLabel('Select one or more properties for a quote.')
        self.quote_label.setWordWrap(True)
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        quote_scroll = QScrollArea()
        quote_scroll.setWidgetResizable(True)
        quote_scroll.setFrameShape(QFrame.Shape.NoFrame)
        quote_scroll.setMinimumHeight(155)
        quote_scroll.setMaximumHeight(240)
        quote_scroll.setWidget(self.quote_label)
        layout.addWidget(quote_scroll)
        buttons = QHBoxLayout()
        calculate = QPushButton('Calculate total')
        calculate.setToolTip('Preview the amount without changing the game.')
        calculate.clicked.connect(self._calculate)
        apply = QPushButton('Apply selected mortgages')
        apply.setToolTip('Commit the selected mortgage transactions and autosave.')
        apply.clicked.connect(self._apply)
        self.apply_button = apply
        buttons.addWidget(calculate)
        buttons.addWidget(apply)
        layout.addLayout(buttons)
        self.operation.currentIndexChanged.connect(self._populate_properties)
        self.properties.itemSelectionChanged.connect(self._calculate)
        return panel

    def _selected_indices(self) -> list[int]:
        """Get selected board indices from the mortgage picker."""
        return [int(item.data(Qt.ItemDataRole.UserRole))
                for item in self.properties.selectedItems()]

    def _populate_properties(self) -> None:
        """Show only currently eligible deeds for the chosen operation."""
        operation = self.operation.currentData()
        self.properties.blockSignals(True)
        self.properties.clear()
        for space in self.controller.session.owned_spaces_for(self.player_id):
            state = self.controller.session.get_property_state(space.index)
            if (operation == 'unmortgage') != state.mortgaged:
                continue
            amount = space.mortgage_value
            if operation == 'unmortgage':
                amount += (amount + 9) // 10
            entry = QListWidgetItem(f'{space.name} — ${amount:,}')
            group = property_group(space)
            color = GROUP_COLORS.get(group)
            if color:
                swatch = QPixmap(14, 14)
                swatch.fill(QColor('#929c98'))
                with QPainter(swatch) as painter:
                    painter.fillRect(1, 1, 12, 12, QColor(color))
                entry.setIcon(QIcon(swatch))
                entry.setToolTip(f'{space.name} ({group})')
            entry.setData(Qt.ItemDataRole.UserRole, space.index)
            self.properties.addItem(entry)
        self.properties.blockSignals(False)
        self.quote_label.setText('Select one or more properties for a quote.')
        self.apply_button.setEnabled(False)
        self.apply_button.setText(
            'Unmortgage selected' if operation == 'unmortgage' else 'Mortgage selected'
        )

    def _quote(self):
        """Ask the engine for a validated, non-mutating bulk quote."""
        return self.controller.engine.mortgage_quote(
            self.player_id, self._selected_indices(), self.operation.currentData()
        )

    def select_mortgage_operation(self, operation: str) -> None:
        """Open the planner directly in mortgage or unmortgage mode."""
        index = self.operation.findData(operation)
        if index < 0:
            raise ValueError('Invalid mortgage operation')
        self.operation.setCurrentIndex(index)
        self.tabs.setCurrentWidget(self.mortgage_tab)

    def _quote_summary(self, quote) -> str:
        details = []
        for index, (name, amount) in zip(quote.space_indices, quote.line_items):
            principal = self.controller.session.board[index].mortgage_value
            interest = (principal + 9) // 10
            if quote.operation == 'mortgage':
                details.append(f'{name}: receive ${principal:,}; unmortgage later ${principal + interest:,}')
            else:
                details.append(f'{name}: repay ${amount:,} (${principal:,} principal + ${interest:,} interest)')
        lines = []
        if quote.operation == 'mortgage':
            lines.extend([f'\nCash received now: ${quote.total:,}',
                          f'Total to unmortgage these same properties later: ${quote.payoff_total:,}',
                          f'Principal: ${quote.principal_total:,} | Interest: ${quote.interest_total:,}'])
            balance = self.player.cash + quote.total
        else:
            lines.extend([f'\nTotal to unmortgage now: ${quote.payoff_total:,}',
                          f'Principal: ${quote.principal_total:,} | Interest: ${quote.interest_total:,}',
                          f'Mortgage value of these properties: ${quote.principal_total:,}'])
            balance = self.player.cash - quote.total
        lines.extend([f'Current cash: ${self.player.cash:,}', f'Cash after applying: ${balance:,}'])
        if balance < 0:
            lines.append('Insufficient cash: reduce the selection or raise funds first.')
        lines.append('\nSelected properties:')
        lines.extend(details)
        return '\n'.join(lines)

    def _calculate(self) -> None:
        """Update the live preview before allowing a batch to be committed."""
        self.apply_button.setEnabled(False)
        try:
            quote = self._quote()
        except (ValueError, KeyError) as exc:
            self.quote_label.setText(str(exc))
            return
        self.quote_label.setText(self._quote_summary(quote))
        self.apply_button.setEnabled(self.controller.session.winner_id is None and
                                     (quote.operation == 'mortgage' or quote.total <= self.player.cash))

    def _apply(self) -> None:
        """Execute a full selected batch after a verified quote."""
        try:
            quote = self._quote()
        except (ValueError, KeyError) as exc:
            QMessageBox.warning(self, 'Invalid selection', str(exc))
            return
        if quote.operation == 'unmortgage' and quote.total > self.player.cash:
            QMessageBox.warning(self, 'Insufficient cash',
                                'The selected payoff exceeds available cash.')
            return
        if QMessageBox.question(
            self, 'Confirm property transactions',
            self._quote_summary(quote) + f'\n\n{quote.operation.title()} these {len(quote.space_indices)} properties?'
        ) != QMessageBox.StandardButton.Yes:
            return
        method = 'mortgage_many' if quote.operation == 'mortgage' else 'unmortgage_many'
        try:
            self.controller.perform(method, self.player_id, list(quote.space_indices))
        except (OSError, PermissionError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, 'Cannot apply changes', str(exc))
            return
        self.refresh()

    def _ask_pin(self, title: str) -> str | None:
        """Collect a PIN using a masked, non-echoed Qt password editor."""
        value, accepted = QInputDialog.getText(
            self, title, 'Enter 4–8 digit PIN:',
            QLineEdit.EchoMode.Password
        )
        return value if accepted else None

    def _set_pin(self) -> None:
        """Change PIN with confirmation, optionally verifying old credentials."""
        first = self._ask_pin('Set player PIN')
        if first is None:
            return
        again = self._ask_pin('Confirm player PIN')
        if again is None:
            return
        if first != again:
            QMessageBox.warning(self, 'PIN mismatch', 'The PINs do not match.')
            return
        try:
            self.controller.set_player_pin(self.player_id, first)
        except (ValueError, PermissionError, OSError) as exc:
            QMessageBox.warning(self, 'Could not set PIN', str(exc))
            return
        QMessageBox.information(self, 'PIN enabled', 'This account is now locked.')
        self.refresh()

    def _remove_pin(self) -> None:
        """Remove account PIN; controller enforces authorization."""
        try:
            self.controller.set_player_pin(self.player_id, '')
        except (ValueError, PermissionError, OSError) as exc:
            QMessageBox.warning(self, 'Could not remove PIN', str(exc))
            return
        self.refresh()

    def _lock_now(self) -> None:
        """Forget unlocked session state immediately."""
        self.controller.lock_player(self.player_id)
        QMessageBox.information(self, 'Locked', 'Account authorization cleared.')
        self.refresh()

    def refresh(self) -> None:
        """Reload player stats, cash, PIN status and mortgage selections."""
        report, history = self.controller.player_history(self.player_id)
        selected = self.stats_scope.currentIndex()
        self.stats_scope.blockSignals(True)
        self.stats_scope.clear()
        self.stats_scope.addItem('This game', report)
        self.stats_scope.addItem('Overall', StatisticsService.overall(report, [entry[2] for entry in history]))
        for name, created_at, saved_report in history:
            self.stats_scope.addItem(f'{name} ({created_at:%Y-%m-%d %H:%M})', saved_report)
        self.stats_scope.setCurrentIndex(max(0, min(selected, self.stats_scope.count() - 1)))
        self.stats_scope.blockSignals(False)
        self._render_statistics()
        self.heading.setText(
            f'{report.name}  •  Current game cash ${report.cash:,}  •  '
            f'Currently owns {report.owned_properties} deeds'
        )
        account = PlayerAccount(self.player)
        self.pin_status.setText(
            'PIN locked' if account.is_locked else 'No PIN set'
        )
        self._populate_properties()

    def _render_statistics(self) -> None:
        report = self.stats_scope.currentData()
        if report is None:
            return
        p = report.gameplay
        f = report.finance
        balances = []
        if self.stats_scope.currentIndex() != 1:
            balances = [f'Cash: ${report.cash:,}', f'Deeds held: {report.owned_properties}', '']
        self.gameplay_text.setPlainText('\n'.join(balances + [
            f'Games played: {p.games_played}',
            f'Games completed: {p.games_completed}',
            f'Wins: {p.games_won}',
            f'Bankruptcies: {p.bankruptcies}',
            '',
            f'Dice rolls: {p.dice_rolls}',
            f'Doubles rolled: {p.doubles_rolled}',
            f'Total spaces moved: {p.total_spaces_moved}',
            f'Total properties purchased: {p.total_properties_purchased}',
            f'Turns started: {p.turns_started}',
            f'Times passed GO: {p.times_passed_go}',
            f'Average dice total: {p.average_dice_total:.2f}',
        ]))
        finance = [
            f'Total money spent: ${f.total_money_spent:,}',
            f'Total taxes paid: ${f.total_taxes_paid:,}',
            f'Other events paid: ${f.total_other_events_paid:,}',
            f'Property purchases: ${f.total_property_purchases:,}',
            f'Player deals paid: ${f.total_player_deals_paid:,}',
            f'Rent paid: ${f.rent_paid:,}',
            f'Rent earned: ${f.rent_earned:,}',
            f'Average rent paid / turn: ${f.average_rent_paid_per_turn:,.2f}',
            f'Average rent earned / turn: ${f.average_rent_earned_per_turn:,.2f}',
        ]
        for name, values in [
            ('Rent paid by player', f.rent_paid_by_player),
            ('Rent earned by player', f.rent_earned_by_player),
            ('Rent paid by property', f.rent_paid_by_property),
            ('Rent earned by property', f.rent_earned_by_property),
        ]:
            finance.extend(['', name + ':'])
            finance.extend(f'  {label}: ${amount:,}' for label, amount in sorted(values.items()))
            if not values:
                finance.append('  No transactions yet')
        self.finance_text.setPlainText('\n'.join(finance))
