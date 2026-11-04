"""Main PySide6 desktop dashboard for a physical Monopoly game.

This module contains display logic only. All banking, movement, ownership
and building rules are delegated to SessionController and GameEngine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QBrush
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QGridLayout, QLineEdit,
    QGroupBox, QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox,
    QSpinBox, QSplitter, QTableWidgetItem, QToolBar, QVBoxLayout, QWidget,
)

from monopolpy_companion.controller import SessionController, SessionSaveError
from monopolpy_companion.game import GameSession, SpaceType

from .dialogs import NewSessionDialog, TransferDialog
from .account_dialog import PlayerAccountDialog
from .branding import BOARD_GROUP_COLORS, make_app_icon
from .theme import stylesheet
from .widgets import HelpButton, ReadOnlyTable


class MainWindow(QMainWindow):
    """Main game dashboard with distinct player, board and ledger views.

    Args:
        controller: Headless session controller. A new one is constructed
            automatically if no controller is supplied.
    """

    def __init__(self, controller: SessionController | None = None) -> None:
        super().__init__()
        self.controller = controller or SessionController()
        self._dark_theme = True
        self._action_buttons: list[HelpButton] = []
        self._build_ui()
        self.controller.subscribe(lambda _event: self.refresh())
        self.refresh()

    def _build_ui(self) -> None:
        """Create accessible, reusable views and action controls."""
        self.setWindowTitle('MonopolPy Companion — Game Dashboard')
        self.setWindowIcon(make_app_icon())
        self.resize(1180, 790)
        self.setMinimumSize(920, 590)

        toolbar = QToolBar('Game commands', self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)

        self.new_action = self._toolbar_action(
            toolbar, 'New game', 'Create a new session with two or more players',
            self._new_game,
        )
        self.open_action = self._toolbar_action(
            toolbar, 'Open', 'Load a saved JSON session', self._open_game
        )
        self.save_action = self._toolbar_action(
            toolbar, 'Save', 'Save all cash balances and game state', self._save
        )
        toolbar.addSeparator()
        self.next_action = self._toolbar_action(
            toolbar, 'Next turn', 'Advance to the next nonbankrupt player',
            lambda: self._perform('advance_turn'),
        )
        toolbar.addSeparator()
        self.landing_action = self._toolbar_action(
            toolbar, 'Landing alerts', 'Ask to buy or pay rent after dice movement.',
            self._toggle_landing_prompts,
        )
        self.landing_action.setCheckable(True)
        self.landing_action.setChecked(True)
        toolbar.addSeparator()
        self.theme_action = self._toolbar_action(
            toolbar, 'Light theme', 'Switch between light and dark colors',
            self._toggle_theme,
        )

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(9)

        title = QLabel('MonopolPy Companion')
        title.setObjectName('headerTitle')
        root.addWidget(title)
        self.subtitle = QLabel('Start a game or open a save to begin.')
        self.subtitle.setObjectName('subTitle')
        root.addWidget(self.subtitle)

        self.welcome_widget = QGroupBox('Start a game')
        welcome_layout = QVBoxLayout(self.welcome_widget)
        greeting = QLabel(
            'MONOPOLPY GAME NIGHT\n'
            'Start a new session or open an existing save.'
        )
        greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(greeting)
        start_buttons = QHBoxLayout()
        start_buttons.addStretch()
        start_new = HelpButton('New Game', 'Create players and initial cash.')
        start_open = HelpButton('Open Game', 'Resume a saved board game.')
        start_new.clicked.connect(self._new_game)
        start_open.clicked.connect(self._open_game)
        start_buttons.addWidget(start_new)
        start_buttons.addWidget(start_open)
        start_buttons.addStretch()
        welcome_layout.addLayout(start_buttons)
        welcome_layout.addStretch()
        root.addWidget(self.welcome_widget, stretch=1)

        column_splitter = QSplitter(Qt.Orientation.Horizontal)
        column_splitter.addWidget(self._build_player_group())
        column_splitter.addWidget(self._build_board_group())
        column_splitter.setStretchFactor(0, 3)
        column_splitter.setStretchFactor(1, 5)

        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.addWidget(column_splitter)
        vertical_splitter.addWidget(self._build_ledger_group())
        vertical_splitter.setStretchFactor(0, 5)
        vertical_splitter.setStretchFactor(1, 2)
        self.dashboard_widget = vertical_splitter
        root.addWidget(self.dashboard_widget, stretch=1)

        self.statusBar().showMessage(
            'New game: create players. Open: resume an existing session.'
        )

    def _toolbar_action(
        self, toolbar: QToolBar, name: str, help_text: str, callback
    ) -> QAction:
        """Create one textual, described toolbar action."""
        action = QAction(name, self)
        action.setToolTip(help_text)
        action.setStatusTip(help_text)
        action.triggered.connect(callback)
        toolbar.addAction(action)
        return action

    def _button(
        self, label: str, help_text: str, callback, layout: QGridLayout,
        row: int, column: int
    ) -> HelpButton:
        """Create and register a game action button for enablement updates."""
        button = HelpButton(label, help_text, self)
        button.clicked.connect(callback)
        layout.addWidget(button, row, column)
        self._action_buttons.append(button)
        return button

    def _build_player_group(self) -> QGroupBox:
        """Build the players, dice and payment controls."""
        group = QGroupBox('Players & banker')
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel('Active player for actions:'))
        self.player_picker = QComboBox()
        self.player_picker.setToolTip(
            'Select which player moves, buys, pays tax, or manages assets.'
        )
        layout.addWidget(self.player_picker)

        self.player_table = ReadOnlyTable(
            ['Player', 'Cash', 'Position', 'Assets', 'Status'],
            'All player balances and owned deed counts in the active game.',
        )
        layout.addWidget(self.player_table, stretch=1)

        dice_row = QHBoxLayout()
        dice_row.addWidget(QLabel('Dice:'))
        self.die_one = QSpinBox()
        self.die_two = QSpinBox()
        for die in (self.die_one, self.die_two):
            die.setRange(1, 6)
            die.setValue(3)
            die.setToolTip('Choose the actual rolled result, 1 to 6.')
            dice_row.addWidget(die)
        dice_row.addStretch()
        layout.addLayout(dice_row)
        self.dice_result = QLabel('Enter dice values or use the simulator.')
        self.dice_result.setToolTip('A simulated roll is counted once you move by those dice.')
        layout.addWidget(self.dice_result)

        buttons = QGridLayout()
        self._button(
            'Move by dice', 'Advance the selected player by the two die values.',
            self._move_by_dice, buttons, 0, 0,
        )
        self._button(
            'Transfer money', 'Transfer Monopoly dollars between the bank and players.',
            self._transfer, buttons, 0, 1,
        )
        self._button(
            'Send to jail', 'Move the selected player directly to jail.',
            lambda: self._player_action('send_to_jail'), buttons, 1, 0,
        )
        self._button(
            'Release from jail', 'Pay a $50 fine, use a card, or record verified doubles.',
            self._release_from_jail, buttons, 1, 1,
        )
        self._button(
            'Roll dice', 'Simulate unbiased six-sided dice without moving yet.',
            self._roll_dice, buttons, 2, 0,
        )
        self._button(
            'Roll + move', 'Simulate dice, then move the selected token.',
            self._roll_and_move, buttons, 2, 1,
        )
        self._button(
            'Player account', 'Show PIN controls, gameplay stats, finances and mortgages.',
            self._open_account, buttons, 3, 0,
        )
        layout.addLayout(buttons)
        return group

    def _build_board_group(self) -> QGroupBox:
        """Build a selectable board list with property actions."""
        group = QGroupBox('Board & properties')
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel('Select a board space, then choose a rule action.'))
        self.board_table = ReadOnlyTable(
            ['#', 'Board space', 'Type', 'Owner', 'Development', 'Rent'],
            'All 40 Monopoly spaces; choose a row before purchasing or collecting rent.',
        )
        self.board_table.setMinimumHeight(290)
        layout.addWidget(self.board_table, stretch=1)
        buttons = QGridLayout()
        self._button(
            'Buy property', 'Purchase the selected unowned deed for the active player.',
            lambda: self._board_action('purchase'), buttons, 0, 0,
        )
        self._button(
            'Collect rent', 'Collect rent from the active player for the selected deed.',
            self._collect_rent, buttons, 0, 1,
        )
        self._button(
            'Mortgage', 'Borrow half the printed price against the selected owned deed.',
            lambda: self._board_action('mortgage'), buttons, 1, 0,
        )
        self._button(
            'Unmortgage', 'Repay the mortgage plus ten percent interest.',
            lambda: self._board_action('unmortgage'), buttons, 1, 1,
        )
        self._button(
            'Build house / hotel', 'Buy evenly across an owned unmortgaged color group.',
            lambda: self._board_action('buy_building'), buttons, 2, 0,
        )
        self._button(
            'Sell building', 'Sell a house or downgrade a hotel for half its cost.',
            lambda: self._board_action('sell_building'), buttons, 2, 1,
        )
        self._button(
            'Pay tax', 'Pay the printed tax on Income Tax or Luxury Tax.',
            lambda: self._board_action('pay_tax'), buttons, 3, 0,
        )
        layout.addLayout(buttons)
        return group

    def _build_ledger_group(self) -> QGroupBox:
        """Build the most recent transaction-history view."""
        group = QGroupBox('Recent transactions')
        layout = QVBoxLayout(group)
        self.ledger_table = ReadOnlyTable(
            ['When (UTC)', 'Action', 'Amount', 'Details'],
            'The latest 100 recorded transactions, most recent first.',
        )
        layout.addWidget(self.ledger_table)
        return group

    @staticmethod
    def _fill(row: int, values: list[str], table: ReadOnlyTable) -> None:
        """Populate a read-only row without allowing edited game state."""
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            table.setItem(row, col, item)

    def refresh(self) -> None:
        """Recreate view data from the authoritative game session."""
        session = self.controller.session
        has_game = session is not None
        self.save_action.setEnabled(has_game)
        self.next_action.setEnabled(has_game)
        self.landing_action.setEnabled(has_game)
        self.landing_action.setChecked(
            session.show_landing_prompts if session is not None else True
        )
        self.welcome_widget.setVisible(not has_game)
        self.dashboard_widget.setVisible(has_game)
        for button in self._action_buttons:
            button.setEnabled(has_game)
        self.player_picker.setEnabled(has_game)
        self.player_table.setEnabled(has_game)
        self.board_table.setEnabled(has_game)
        self.die_one.setEnabled(has_game)
        self.die_two.setEnabled(has_game)
        if session is None:
            self.subtitle.setText('No active game — create or load a saved session.')
            self.player_picker.clear()
            self.player_table.setRowCount(0)
            self.board_table.setRowCount(0)
            self.ledger_table.setRowCount(0)
            return

        current_id = self.player_picker.currentData()
        selected_row = self.board_table.currentRow()
        self.player_picker.blockSignals(True)
        self.player_picker.clear()
        for player in session.players:
            self.player_picker.addItem(player.name, player.player_id)
        if current_id:
            index = self.player_picker.findData(current_id)
            if index >= 0:
                self.player_picker.setCurrentIndex(index)
        self.player_picker.blockSignals(False)

        current = session.current_player
        turn_label = current.name if current is not None else 'None'
        self.subtitle.setText(
            f'{session.name}  •  Turn: {turn_label}  •  '
            f'{len(session.players)} players  •  Autosave enabled'
        )

        self.player_table.setRowCount(len(session.players))
        board = session.board
        for row, player in enumerate(session.players):
            owned = session.owned_spaces_for(player.player_id)
            status = 'Bankrupt' if player.bankrupt else (
                'In jail' if player.in_jail else 'Playing'
            )
            values = [
                player.name, f'${player.cash:,}',
                f'{player.position}: {board[player.position].name}',
                str(len(owned)), status,
            ]
            self._fill(row, values, self.player_table)

        self.board_table.setRowCount(len(board))
        for row, space in enumerate(board):
            owner = session.owner_for(space.index) if space.ownable else None
            state = session.property_states.get(space.index)
            if state is None:
                development = '—'
            elif state.mortgaged:
                development = 'Mortgaged'
            elif state.hotel:
                development = 'Hotel'
            elif state.houses:
                development = f'{state.houses} house(s)'
            else:
                development = '—'
            if owner is None:
                rent = '—'
            elif space.space_type is SpaceType.UTILITY:
                rent = 'Dice × 4/10'
            else:
                rent = f'${self.controller.engine.rent_due(space.index):,}'
            values = [
                str(space.index), space.name,
                space.space_type.value.replace('_', ' ').title(),
                owner.name if owner else 'Bank',
                development, rent,
            ]
            self._fill(row, values, self.board_table)
            if space.color_group in BOARD_GROUP_COLORS:
                shade = QColor(BOARD_GROUP_COLORS[space.color_group])
                # Use a readable badge-like colored name cell, not a tinted
                # entire row that obscures the selected/active highlight.
                cell = self.board_table.item(row, 1)
                cell.setBackground(QBrush(shade))
                cell.setForeground(QBrush(QColor('#ffffff' if shade.lightness() < 155 else '#151c1a')))
        if 0 <= selected_row < len(board):
            self.board_table.setCurrentCell(selected_row, 0)

        recent = list(reversed(session.transactions[-100:]))
        self.ledger_table.setRowCount(len(recent))
        for row, record in enumerate(recent):
            self._fill(row, [
                record.created_at.strftime('%Y-%m-%d %H:%M'),
                record.kind.replace('_', ' ').title(),
                f'${record.amount:,}',
                record.description,
            ], self.ledger_table)
        self.setWindowTitle(f'{session.name} — MonopolPy Companion')

    def _new_game(self) -> None:
        """Collect new-session information and open the game dashboard."""
        dialog = NewSessionDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.controller.new_session(
                dialog.game_name, dialog.player_names, dialog.starting_cash
            )
        except (OSError, ValueError) as exc:
            self._show_error('Could not start game', exc)
            return
        self.statusBar().showMessage('New game saved successfully.', 6000)

    def _open_game(self) -> None:
        """Let the user choose a JSON game file."""
        start = str(self.controller.repository.directory)
        path, _filter = QFileDialog.getOpenFileName(
            self, 'Open Monopoly game', start, 'Monopoly JSON (*.json)'
        )
        if not path:
            return
        try:
            self.controller.open_session(path)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._show_error('Could not open game', exc)
            return
        self.statusBar().showMessage(f'Loaded {Path(path).name}', 6000)

    def _save(self) -> None:
        """Persist the active session on demand."""
        try:
            self.controller.save()
        except (OSError, ValueError) as exc:
            self._show_error('Save failed', exc)
            return
        self.statusBar().showMessage('Game saved successfully.', 6000)

    def _perform(self, action: str, *args: Any, **kwargs: Any) -> Any:
        """Execute one game command, prompting for a protected payer PIN."""
        for attempt in range(2):
            try:
                result = self.controller.perform(action, *args, **kwargs)
                self.statusBar().showMessage(
                    f'{action.replace("_", " ").capitalize()} completed and saved.', 6000
                )
                return result
            except PermissionError:
                if attempt > 0:
                    break
                payer = kwargs.get('from_player_id') if action == 'transfer' else (
                    args[0] if args else kwargs.get('player_id')
                )
                if not payer or not self._unlock_player(payer):
                    return None
            except SessionSaveError as exc:
                QMessageBox.warning(
                    self, 'Autosave failed',
                    f'{exc}\nThe action was applied but has not been saved.',
                )
                return None
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self._show_error('Cannot complete game action', exc)
                return None
        self._show_error('PIN required', PermissionError('Player account is locked'))
        return None

    def _unlock_player(self, player_id: str) -> bool:
        """Unlock one account using a masked PIN prompt."""
        if self.controller.is_player_unlocked(player_id):
            return True
        player = self.controller.session.get_player(player_id)
        pin, accepted = QInputDialog.getText(
            self, f'{player.name} account', 'Enter account PIN:',
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return False
        if not self.controller.unlock_player(player_id, pin):
            QMessageBox.warning(self, 'Incorrect PIN', 'That PIN was not accepted.')
            return False
        return True

    def _selected_player_id(self) -> str:
        """Get the selected player identity or raise a user-facing error."""
        player_id = self.player_picker.currentData()
        if player_id is None:
            raise ValueError('Select a player first.')
        return player_id

    def _selected_board_index(self) -> int:
        """Get the active board row, rejecting absent selections."""
        row = self.board_table.currentRow()
        if row < 0:
            raise ValueError('Select a board space first.')
        return row

    def _player_action(self, action: str) -> None:
        """Run a player-only operation for the selected player."""
        try:
            player_id = self._selected_player_id()
        except ValueError as exc:
            self._show_error('Select player', exc)
            return
        self._perform(action, player_id)

    def _board_action(self, action: str) -> None:
        """Run an owned-deed action for selected player and board square."""
        try:
            player_id = self._selected_player_id()
            space_index = self._selected_board_index()
        except ValueError as exc:
            self._show_error('Select player and space', exc)
            return
        self._perform(action, player_id, space_index)

    def _collect_rent(self) -> None:
        """Collect rent on a selected deed from the current active player."""
        try:
            player_id = self._selected_player_id()
            space_index = self._selected_board_index()
        except ValueError as exc:
            self._show_error('Select player and space', exc)
            return
        space = self.controller.session.board[space_index]
        if space.space_type is SpaceType.UTILITY:
            # Use the explicit dice controls; no rolls are invented.
            total = self.die_one.value() + self.die_two.value()
            self._perform('collect_rent', player_id, space_index, dice_total=total)
        else:
            self._perform('collect_rent', player_id, space_index)


    def _roll_dice(self) -> None:
        """Simulate fair dice, previewing the result without moving a token."""
        if self.controller.engine is None:
            return
        first, second = self.controller.engine.simulate_dice()
        self.die_one.setValue(first)
        self.die_two.setValue(second)
        self.dice_result.setText(
            f'Rolled {first} + {second} = {first + second}'
            + (' — DOUBLES!' if first == second else '')
        )

    def _roll_and_move(self) -> None:
        """Roll physical-game dice digitally, then commit the move."""
        self._roll_dice()
        self._move_by_dice()

    def _move_by_dice(self) -> None:
        """Move selected token and highlight the landed-on board square."""
        try:
            player_id = self._selected_player_id()
        except ValueError as exc:
            self._show_error('Select player', exc)
            return
        result = self._perform(
            'move_by_dice', player_id, self.die_one.value(), self.die_two.value()
        )
        if result is not None:
            self._handle_landing(player_id, result)

    def _handle_landing(self, player_id: str, result) -> None:
        """Highlight the landing and optionally offer purchase/rent resolution."""
        space = result.landed_on
        self.board_table.selectRow(space.index)
        item = self.board_table.item(space.index, 1)
        if item is not None:
            self.board_table.scrollToItem(item)
        self.statusBar().showMessage(f'Landed on {space.name}', 9000)
        if not self.controller.session.show_landing_prompts or not space.ownable:
            return
        owner = self.controller.session.owner_for(space.index)
        if owner is None:
            choice = QMessageBox.question(
                self, 'Unowned property',
                f'{space.name} is unowned. Buy it from the bank for ${space.price:,}?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if choice == QMessageBox.StandardButton.Yes:
                self._perform('purchase', player_id, space.index)
        elif owner.player_id != player_id:
            dice_total = self.die_one.value() + self.die_two.value()
            options = {'dice_total': dice_total} if space.space_type is SpaceType.UTILITY else {}
            rent = self.controller.engine.rent_due(space.index, **options)
            if rent:
                choice = QMessageBox.question(
                    self, 'Rent due',
                    f'{space.name} belongs to {owner.name}.\n'
                    f'Rent due: ${rent:,}. Pay {owner.name} now?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if choice == QMessageBox.StandardButton.Yes:
                    self._perform('collect_rent', player_id, space.index, **options)

    def _open_account(self) -> None:
        """Prompt for PIN if locked, then open the account statistics dialog."""
        try:
            player_id = self._selected_player_id()
        except ValueError as exc:
            self._show_error('Select player', exc)
            return
        if not self._unlock_player(player_id):
            return
        PlayerAccountDialog(self.controller, player_id, self).exec()
        self.refresh()

    def _toggle_landing_prompts(self, checked: bool = True) -> None:
        """Save the optional landing popup setting in this game session."""
        if self.controller.session is None:
            return
        try:
            self.controller.set_landing_prompts(checked)
        except OSError as exc:
            self._show_error('Could not save setting', exc)
        self.refresh()

    def _transfer(self) -> None:
        """Open bank/player transfer dialog and submit it to GameEngine."""
        if self.controller.session is None:
            return
        dialog = TransferDialog(self.controller.session, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._perform('transfer', **dialog.transfer_args)

    def _release_from_jail(self) -> None:
        """Choose the permitted way to release a selected player."""
        try:
            player_id = self._selected_player_id()
        except ValueError as exc:
            self._show_error('Select player', exc)
            return
        choices = ['Pay $50 fine', 'Use Get Out of Jail Free card',
                   'Rolled doubles (verified on physical dice)']
        choice, accepted = QInputDialog.getItem(
            self, 'Release from jail', 'Method:', choices, 0, False
        )
        if not accepted:
            return
        method = {'Pay $50 fine': 'fine',
                  'Use Get Out of Jail Free card': 'card',
                  'Rolled doubles (verified on physical dice)': 'doubles'}[choice]
        self._perform('release_from_jail', player_id, method=method)

    def _toggle_theme(self) -> None:
        """Switch the desktop palette without affecting game state."""
        self._dark_theme = not self._dark_theme
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet(self._dark_theme))
        self.theme_action.setText('Light theme' if self._dark_theme else 'Dark theme')

    def _show_error(self, title: str, error: Exception) -> None:
        """Display friendly errors instead of exposing a traceback in the GUI."""
        QMessageBox.warning(self, title, str(error))
