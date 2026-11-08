"""Main PySide6 desktop dashboard for a physical Monopoly game.

This module contains display logic only. All banking, movement, ownership
and building rules are delegated to SessionController and GameEngine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QBoxLayout, QButtonGroup, QComboBox, QDialog, QFileDialog, QGridLayout, QLineEdit,
    QFrame, QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox,
    QHeaderView, QLayout, QMenu, QScrollArea, QSpinBox, QTabWidget,
    QTableWidgetItem, QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from monopolpy_companion.controller import SessionController, SessionSaveError
from monopolpy_companion.game import GameSession, SpaceType
from monopolpy_companion.plugins import PluginManager

from .dialogs import NewSessionDialog, TransferDialog, NewAccountDialog, SettingsDialog, GameSettingsDialog
from monopolpy_companion.game.accounts import AccountStore
from monopolpy_companion.lib.common.paths import APP_DATA_DIR
from .trade_dialog import TradeDialog
from .dev_tools_dialog import DevToolsDialog
from .map_unlock import _introduction, _phrase_entry
from .property_tracker import PropertyTrackers
from .widgets import TitleBar
from .account_dialog import PlayerAccountDialog
from .branding import BOARD_GROUP_COLORS, make_app_icon
from .theme import stylesheet
from .widgets import HelpButton, PanelCard, PropertyDetailCard, ReadOnlyTable


def _board_color_swatch(color: str) -> QIcon:
    pixmap = QPixmap(10, 10)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    """Main game dashboard with distinct player, board and ledger views.

    Args:
        controller: Headless session controller. A new one is constructed
            automatically if no controller is supplied.
    """

    def __init__(
        self, controller: SessionController | None = None, *,
        enabled_plugins: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.controller = controller or SessionController()
        self.settings = QSettings('Inspyre Softworks', 'MonopolPy Companion')
        self.accounts = AccountStore(APP_DATA_DIR / 'accounts')
        self._dark_theme = self.settings.value('dark', True, type=bool)
        self._action_buttons: list[HelpButton] = []
        self._focused_property_index: int | None = None
        self._board_swatches = {
            group: _board_color_swatch(color) for group, color in BOARD_GROUP_COLORS.items()
        }
        self._build_ui()
        self._apply_preferences()
        self.controller.subscribe(self._on_game_event)
        self.refresh()
        self._plugins = PluginManager(
            self.controller, register_action=self._register_plugin_action
        ) if enabled_plugins else None
        if self._plugins is not None:
            for identifier in enabled_plugins:
                self._plugins.enable(identifier)

    def _register_plugin_action(self, label, callback):
        if not self._plugin_toolbar.actions():
            self._plugin_toolbar.show()
        action = self._plugin_toolbar.addAction(label)
        action.triggered.connect(callback)

        def remove():
            self._plugin_toolbar.removeAction(action)
            action.deleteLater()
            if not self._plugin_toolbar.actions():
                self._plugin_toolbar.hide()

        return remove

    def closeEvent(self, event):
        super().closeEvent(event)
        if event.isAccepted() and self._plugins is not None:
            self._plugins.close()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_board_workspace()

    def _layout_board_workspace(self):
        stacked = self.width() < 1550
        self._board_workspace.setDirection(
            QBoxLayout.Direction.BottomToTop if stacked else QBoxLayout.Direction.LeftToRight
        )
        self._board_workspace.setStretch(1, 0 if stacked else 2)
        self.board_table.setMaximumWidth(1200 if stacked else 880)

    def _on_game_event(self, event):
        self.refresh(follow_turn=event.name in {'turn_advanced', 'session_changed'})
        if event.name == 'session_changed':
            self.dashboard_widget.setCurrentWidget(self.turn_view)
            self.activity_label.hide()
            self.statusBar().clearMessage()
            self.salary_timer.stop()
            self.salary_notice.hide()
        elif event.name == 'bankruptcy_declared':
            player = self.controller.session.get_player(event.details['player_id'])
            message = f'{player.name} declared bankruptcy and is out of the game.'
            if event.details['winner_id'] is not None:
                winner = self.controller.session.get_player(event.details['winner_id'])
                message += f' {winner.name} wins!'
            self.activity_label.setText(message)
            self.activity_label.show()
        elif event.name == 'auction_finished':
            space = self.controller.session.board[event.details['space_index']]
            winner_id = event.details['winner_id']
            if winner_id is None:
                message = f'{space.name} received no bids and remains unowned.'
            else:
                winner = self.controller.session.get_player(winner_id)
                message = f"{winner.name} won {space.name} for ${event.details['amount']:,}."
            self.activity_label.setText(message)
            self.activity_label.show()
        elif event.name == 'go_salary_paid':
            player = self.controller.session.get_player(event.details['player_id'])
            self.salary_notice.setText(
                f"GO SALARY  +${event.details['amount']:,}  |  {player.name}  |  "
                f"Balance ${event.details['balance']:,}"
            )
            self.salary_notice.show()
            self.salary_timer.start(10000)

    def _build_ui(self) -> None:
        """Build a contemporary, card-based electronic banker dashboard."""
        self.setWindowTitle('MonopolPy Companion')
        self.setWindowIcon(make_app_icon())
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setMenuWidget(TitleBar(self))
        self.resize(1360, 880)
        self.setMinimumSize(980, 670)

        toolbar = QToolBar('Game commands', self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)
        self._plugin_toolbar = QToolBar('Plugins', self)
        self._plugin_toolbar.setMovable(False)
        self.addToolBar(self._plugin_toolbar)
        self._plugin_toolbar.hide()

        game_menu = QMenu('Game', self)
        game_button = QToolButton()
        game_button.setText('Game')
        game_button.setMenu(game_menu)
        game_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        toolbar.addWidget(game_button)
        self.save_action = self._toolbar_action(
            toolbar, 'Save', 'Save player balances and game state', self._save
        )
        self.new_action = self._toolbar_action(
            game_menu, 'New game', 'Create a new session with two or more players',
            self._new_game,
        )
        self.open_action = self._toolbar_action(
            game_menu, 'Open', 'Resume an existing saved game', self._open_game
        )
        self._toolbar_action(game_menu, 'Create Account', 'Register a local account', self._create_account)
        self._toolbar_action(game_menu, 'Settings', 'Save desktop preferences', self._settings)
        self.game_settings_action = self._toolbar_action(
            game_menu, 'Game Settings', 'Set the active game GO salary', self._game_settings
        )
        self.mortgages_action = self._toolbar_action(game_menu, 'Mortgages', 'Select several properties and preview borrowing or repayment', lambda: self._open_mortgage_planner('mortgage'))
        self.dev_action = self._toolbar_action(
            game_menu, 'Marauder’s Map', 'Open unlocked game grants', self._open_dev_tools
        )
        self.dev_action.setVisible(False)
        self.dev_shortcut = QShortcut(QKeySequence('Ctrl+Shift+M'), self)
        self.dev_shortcut.activated.connect(self._open_dev_tools)
        self.trade_action = self._toolbar_action(game_menu, 'Trade', 'Exchange cash and assets between players', self._trade)
        game_menu.addSeparator()
        self.next_action = self._toolbar_action(
            game_menu, 'Next turn', 'Advance to the next nonbankrupt player',
            lambda: self._perform('advance_turn'),
        )
        game_menu.addSeparator()
        self.landing_action = self._toolbar_action(
            game_menu, 'Landing alerts', 'Show purchase and rent decisions after movement',
            self._toggle_landing_prompts,
        )
        self.landing_action.setCheckable(True)
        self.landing_action.setChecked(True)
        game_menu.addSeparator()
        self.theme_action = self._toolbar_action(
            game_menu, 'Light theme', 'Switch between light and dark palettes',
            self._toggle_theme,
        )

        central = QWidget(self)
        central.setObjectName('centralSurface')
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 21, 24, 20)
        root.setSpacing(16)

        hero = QFrame()
        hero.setObjectName('hero')
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 18, 24, 18)
        hero_layout.setSpacing(16)
        headline = QVBoxLayout()
        headline.setSpacing(4)
        eyebrow = QLabel('THE ELECTRONIC BANKER  /  GAME NIGHT')
        eyebrow.setObjectName('eyebrow')
        headline.addWidget(eyebrow)
        title = QLabel('MONOPOLPY')
        title.setObjectName('headerTitle')
        headline.addWidget(title)
        brand_subtitle = QLabel(
            'Start a session to keep every deed and dollar accounted for.'
        )
        brand_subtitle.setObjectName('subTitle')
        headline.addWidget(brand_subtitle)
        hero_layout.addLayout(headline, stretch=1)
        brand_mark = QLabel('BUY  •  BUILD  •  COLLECT')
        brand_mark.setObjectName('meta')
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hero_layout.addWidget(brand_mark)
        root.addWidget(hero)

        self.activity_label = QLabel('')
        self.activity_label.setObjectName('activityBanner')
        self.activity_label.setWordWrap(True)
        self.activity_label.setAccessibleDescription(
            'Confirmation for completed property purchases and payments.'
        )
        self.activity_label.setVisible(False)
        root.addWidget(self.activity_label)
        self.salary_notice = QLabel()
        self.salary_notice.setObjectName('salaryNotice')
        self.salary_notice.setWordWrap(True)
        self.salary_notice.setAccessibleDescription('Automatic GO salary payment confirmation')
        self.salary_notice.setStyleSheet(
            'background-color: #5b4515; color: #fff1b8; border: 1px solid #e7bd51; '
            'border-radius: 10px; padding: 12px 16px; font-weight: 700;'
        )
        self.salary_notice.hide()
        self.salary_timer = QTimer(self)
        self.salary_timer.setSingleShot(True)
        self.salary_timer.timeout.connect(self.salary_notice.hide)
        root.addWidget(self.salary_notice)

        self.welcome_widget = PanelCard(
            'Welcome to game night',
            'Every property, payment and roll in one place. Choose how to begin.',
        )
        welcome_layout = self.welcome_widget.layout_root
        welcome_layout.addStretch()
        welcome_message = QLabel('READY TO PASS GO?')
        welcome_message.setObjectName('headerTitle')
        welcome_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(welcome_message)
        start_buttons = QHBoxLayout()
        start_buttons.addStretch()
        start_new = HelpButton('Start new game', 'Create players and starting balances')
        start_new.setObjectName('primaryAction')
        start_open = HelpButton('Open saved game', 'Resume a saved Monopoly session')
        start_new.clicked.connect(self._new_game)
        start_open.clicked.connect(self._open_game)
        start_buttons.addWidget(start_new)
        start_buttons.addWidget(start_open)
        create = HelpButton('Create Account', 'Register a reusable local player')
        create.clicked.connect(self._create_account)
        start_buttons.addWidget(create)
        start_buttons.addStretch()
        welcome_layout.addLayout(start_buttons)
        welcome_layout.addStretch()
        root.addWidget(self.welcome_widget, stretch=1)

        turn = QWidget()
        turn_layout = QVBoxLayout(turn)
        turn_layout.setContentsMargins(0, 24, 0, 16)
        turn_content = QWidget()
        turn_content.setMaximumWidth(660)
        content_layout = QVBoxLayout(turn_content)
        content_layout.setContentsMargins(12, 0, 12, 0)
        content_layout.setSpacing(12)
        self.subtitle = QLabel()
        self.subtitle.setObjectName('eyebrow')
        content_layout.addWidget(self.subtitle)
        self.turn_title = QLabel()
        self.turn_title.setObjectName('turnTitle')
        self.turn_title.setTextFormat(Qt.TextFormat.PlainText)
        self.turn_title.setWordWrap(True)
        content_layout.addWidget(self.turn_title)
        content_layout.addWidget(self._build_quick_actions())
        self.turn_balances = QLabel()
        self.turn_balances.setObjectName('meta')
        self.turn_balances.setTextFormat(Qt.TextFormat.PlainText)
        self.turn_balances.setWordWrap(True)
        content_layout.addWidget(self.turn_balances)
        turn_row = QHBoxLayout()
        turn_row.addStretch()
        turn_row.addWidget(turn_content, stretch=8)
        turn_row.addStretch()
        turn_layout.addLayout(turn_row)
        turn_layout.addStretch()

        self.property_trackers = PropertyTrackers()
        tracker_card = PanelCard('Property ownership',
            'Outline = not owned here. Filled = owned. X = mortgaged. Gold outline = complete set.')
        tracker_card.layout_root.addWidget(self.property_trackers)
        board = QWidget()
        board_layout = QVBoxLayout(board)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.addWidget(self._build_board_group(tracker_card), stretch=1)

        self.dashboard_widget = QTabWidget()
        self.dashboard_widget.setObjectName('dashboardTabs')
        self.dashboard_widget.tabBar().setDrawBase(False)
        self.turn_view = turn
        self.players_view = self._scroll_view(self._build_player_group())
        self.player_picker.currentIndexChanged.connect(self._update_property_card)
        self.dashboard_widget.addTab(turn, 'This Turn')
        board_view = self._scroll_view(board)
        self.dashboard_widget.addTab(board_view, 'Board')
        self.dashboard_widget.addTab(self.players_view, 'Players')
        self.dashboard_widget.addTab(self._build_ledger_group(), 'Ledger')
        self.dashboard_widget.currentChanged.connect(
            lambda _: hero.setVisible(self.dashboard_widget.currentWidget() is not board_view)
        )
        root.addWidget(self.dashboard_widget, stretch=1)

        self.statusBar().showMessage(
            'Create a new game or open a save to start managing the board.'
        )

    @staticmethod
    def _scroll_view(panel: QWidget) -> QScrollArea:
        panel.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.Shape.NoFrame)
        scroller.setWidget(panel)
        return scroller

    def _toolbar_action(
        self, toolbar: QToolBar | QMenu, name: str, help_text: str, callback
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

    def _build_quick_actions(self) -> PanelCard:
        self.quick_actions = QFrame()
        self.quick_actions.setObjectName('surface')
        layout = QVBoxLayout(self.quick_actions)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        self.turn_property = QLabel()
        self.turn_property.setObjectName('deedTitle')
        self.turn_property.setWordWrap(True)
        layout.addWidget(self.turn_property)
        self.quick_status = QLabel()
        self.quick_status.setTextFormat(Qt.TextFormat.PlainText)
        self.quick_status.setWordWrap(True)
        layout.addWidget(self.quick_status)
        row = QHBoxLayout()
        self.quick_buttons = {}
        actions = (
            ('roll_move', 'Roll + move', lambda: self._quick_for_current(self._roll_and_move)),
            ('roll', 'Roll dice', lambda: self._quick_for_current(self._roll_dice)),
            ('move', 'Move using roll', lambda: self._quick_for_current(self._move_by_dice)),
            ('pay', 'Pay amount owed', lambda: self._quick_for_current(self._pay_outstanding)),
            ('buy', 'Buy property', self._buy_landing),
            ('auction', 'Start auction', self._start_landing_auction),
            ('bid', 'Place bid', self._place_auction_bid),
            ('pass', 'Pass', lambda: self._auction_command('pass_at_auction')),
            ('jail_roll', 'Roll for doubles', lambda: self._quick_for_current(self._jail_roll)),
            ('bail', 'Pay $50 bail', lambda: self._quick_for_current(self._jail_bail)),
            ('jail_card', 'Use jail release card', lambda: self._quick_for_current(self._release_from_jail)),
            ('mortgage', 'Mortgages', lambda: self._quick_for_current(lambda: self._open_mortgage_planner('mortgage'))),
            ('manual', 'Enter dice', lambda: self._quick_for_current(
                lambda: self.dashboard_widget.setCurrentWidget(self.players_view))),
            ('bankruptcy', 'Declare bankruptcy', self._declare_bankruptcy),
            ('next', 'Next turn', lambda: self._perform('advance_turn')),
        )
        for key, text, callback in actions:
            button = HelpButton(text, text, self.quick_actions)
            button.clicked.connect(callback)
            self.quick_buttons[key] = button
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        return self.quick_actions

    def _quick_for_current(self, callback):
        player = self.controller.session.current_player
        if player is not None:
            self.player_picker.setCurrentIndex(self.player_picker.findData(player.player_id))
            callback()

    def _refresh_quick_actions(self):
        session = self.controller.session
        player = session.current_player if session else None
        self.quick_actions.setVisible(player is not None)
        if player is None:
            return
        engine = self.controller.engine
        visible = {}
        primary = None
        property_name = ''
        status = player.name
        auction = session.auction
        if session.winner_id is not None:
            status = f'{session.get_player(session.winner_id).name} wins!'
        elif auction is not None:
            bidder = session.get_player(engine.auction_bidder())
            space = session.board[auction['space_index']]
            leader = session.get_player(auction['leader']).name if auction['leader'] else None
            high_bid = f"{leader} leads at ${auction['bid']:,}." if leader else 'No bids yet.'
            status = f'Auction for {space.name}. {high_bid} {bidder.name} to bid or pass.'
            visible = {'bid': bidder.cash > auction['bid'], 'pass': True}
            property_name = space.name
            primary = 'bid' if visible['bid'] else 'pass'
        else:
            player_id = player.player_id
            debts = engine.outstanding_payments(player_id)
            offer = session.purchase_offer
            if debts:
                debt = debts[0]
                space = session.board[debt['space_index']]
                amount = f"${debt['amount']:,}" if debt['amount'] is not None else 'dice total required'
                status += f" owes {debt['kind']} on {space.name} ({amount})."
                self.quick_buttons['pay'].setText(f"Pay {debt['kind']} ({amount})")
                visible.update(pay=True, mortgage=True)
                primary = 'pay'
                if debt['amount'] is None or debt['amount'] > player.cash:
                    visible['bankruptcy'] = True
            elif offer is not None:
                space = session.board[offer]
                property_name = space.name
                status = f'Landed on an unowned property. Buy it for ${space.price:,}, or start an auction.'
                self.quick_buttons['buy'].setText(f'Buy for ${space.price:,}')
                on_space = not session.rules.require_landing_to_buy or player.position == offer
                visible.update(buy=on_space and player.cash >= space.price, auction=True)
                primary = 'buy' if visible['buy'] else 'auction'
            elif player.in_jail and not session.turn_ended:
                status += ' is in Jail.'
                visible.update(jail_roll=engine.can_roll_for_doubles(player_id), bail=player.cash >= 50,
                               jail_card=player.get_out_of_jail_cards > 0 and player.jail_turns < 3
                               and not any(session.dice_rolls[index].get('source') == 'jail'
                                           for index in session.turn_roll_indices))
                primary = next((key for key in ('jail_roll', 'bail', 'jail_card')
                                if visible[key]), None)
                if player.cash < 50:
                    visible['mortgage'] = True
                    if player.jail_turns >= 3:
                        visible['bankruptcy'] = True
            elif engine.can_roll(player_id):
                status += ' can roll the dice.'
                visible.update(roll=True, roll_move=True, manual=True)
                primary = 'roll_move'
            elif engine.can_move_by_dice(player_id):
                roll = session.dice_rolls[session.turn_roll_indices[-1]]
                status += f" rolled {roll['die_one']} + {roll['die_two']}. Move using that roll."
                visible['move'] = True
                primary = 'move'
            elif engine.can_advance_turn():
                status += ' can end the turn.'
            if offer is None and engine.can_advance_turn():
                visible['next'] = True
                primary = primary or 'next'
        self.turn_property.setText(property_name)
        self.turn_property.setVisible(bool(property_name))
        self.quick_status.setText(status)
        for key, button in self.quick_buttons.items():
            button.setVisible(key in visible)
            button.setEnabled(visible.get(key, False))
            name = 'turnPrimaryAction' if key == primary else ''
            if button.objectName() != name:
                button.setObjectName(name)
                button.style().unpolish(button)
                button.style().polish(button)

    def _declare_bankruptcy(self):
        session = self.controller.session
        player_id = session.current_player.player_id
        debts = self.controller.engine.outstanding_payments(player_id)
        options = {}
        if debts and debts[0]['amount'] is None:
            total, accepted = QInputDialog.getInt(self, 'Utility rent',
                                                  'Dice total for this utility landing:', 7, 2, 12)
            if not accepted:
                return
            options['dice_total'] = total
        try:
            quote = self.controller.engine.bankruptcy_quote(player_id, **options)
        except (ValueError, KeyError) as exc:
            self._show_error('Cannot declare bankruptcy', exc)
            return
        creditor_id = quote['creditor_id']
        destination = session.get_player(creditor_id).name if creditor_id is not None else 'the bank'
        deeds = ', '.join(space.name for space in quote['deeds']) or 'none'
        review = (
            f"{session.current_player.name} owes ${quote['amount']:,} and will leave the game.\n\n"
            f"Recipient: {destination}\n"
            f"Cash surrendered: ${quote['cash']:,} (including ${quote['building_proceeds']:,} from buildings)\n"
            f"Deeds: {deeds}\nJail cards surrendered: {quote['cards']}"
        )
        if sum(not player.bankrupt for player in session.players) == 2:
            review += '\nThe remaining player wins.'
        elif creditor_id is None and quote['deeds']:
            review += '\nThe bank will clear mortgages and auction the deeds.'
        elif quote['interest']:
            interest = sum(amount for _, amount in quote['interest'])
            review += f'\n{destination} takes over the mortgages and owes ${interest:,} in interest.'
        if QMessageBox.question(self, 'Confirm bankruptcy', review,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self._perform('declare_bankruptcy', player_id, **options)

    def _buy_landing(self):
        session = self.controller.session
        if session.purchase_offer is not None:
            self._perform('purchase', session.current_player.player_id, session.purchase_offer)

    def _start_landing_auction(self):
        self._perform('start_auction', self.controller.session.current_player.player_id)

    def _auction_command(self, action, *args):
        bidder = self.controller.engine.auction_bidder()
        if bidder is not None:
            self._perform(action, bidder, *args)

    def _place_auction_bid(self):
        auction = self.controller.session.auction
        bidder = self.controller.engine.auction_bidder()
        if auction is None or bidder is None:
            return
        player = self.controller.session.get_player(bidder)
        minimum = auction['bid'] + 1
        maximum = min(player.cash, 2_147_483_647)
        if minimum <= maximum:
            amount, accepted = QInputDialog.getInt(
                self, 'Auction bid', f'{player.name} bids (available cash ${player.cash:,})',
                minimum, minimum, maximum)
            if accepted:
                self._auction_command('bid_at_auction', amount)

    def _build_player_group(self) -> PanelCard:
        """Build the players, dice and payment controls."""
        group = PanelCard('Players & banker', 'Track wallets, dice and player actions.')
        layout = group.layout_root
        layout.addWidget(QLabel('Active player for actions:'))
        self.player_picker = QComboBox()
        self.player_picker.setToolTip(
            'Select which player moves, buys, pays tax, or manages assets.'
        )
        layout.addWidget(self.player_picker)
        self.player_picker.currentIndexChanged.connect(self._update_player_focus)
        self.player_focus = QLabel('Choose a player to see their wallet.')
        self.player_focus.setObjectName('deedOwner')
        layout.addWidget(self.player_focus)
        self.payment_notice = QLabel()
        self.payment_notice.setWordWrap(True)
        self.payment_notice.setAccessibleDescription('Unpaid rent and tax charges blocking the next turn')
        layout.addWidget(self.payment_notice)
        self.pay_outstanding_button = HelpButton('Pay amount owed', 'Pay the oldest outstanding rent or tax charge')
        self.pay_outstanding_button.clicked.connect(self._pay_outstanding)
        layout.addWidget(self.pay_outstanding_button)
        self.payment_notice.hide()
        self.pay_outstanding_button.hide()

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
        self.move_dice_button = self._button(
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
        self.jail_card_button = self._button(
            'Use jail release card', 'Use an owned Get Out of Jail Free card before attempting doubles.',
            self._release_from_jail, buttons, 1, 1,
        )
        self.roll_button = self._button(
            'Roll dice', 'Simulate unbiased six-sided dice without moving yet.',
            self._roll_dice, buttons, 2, 0,
        )
        self.roll_move_button = self._button(
            'Roll + move', 'Simulate dice, then move the selected token.',
            self._roll_and_move, buttons, 2, 1,
        )
        self.player_account_button = self._button(
            'Player account', 'Show PIN controls, gameplay stats, finances and mortgages.',
            self._open_account, buttons, 3, 0,
        )
        self._button(
            'Trade', 'Exchange cash, properties and jail cards between two players.',
            self._trade, buttons, 3, 1,
        )
        self.jail_roll_button = self._button(
            'Roll for doubles (0/3)', 'One jail attempt per turn. Third failure requires $50 bail.',
            self._jail_roll, buttons, 4, 0,
        )
        self.jail_bail_button = self._button(
            'Pay $50 bail and release', 'Pay the bank $50 to leave Jail. Use a jail roll already made.',
            self._jail_bail, buttons, 4, 1,
        )
        self.jail_roll_button.hide()
        self.jail_bail_button.hide()
        layout.addLayout(buttons)
        return group

    def _build_board_group(self, tracker_card: PanelCard) -> PanelCard:
        """Build a selectable board list with property actions."""
        group = PanelCard('Board & properties')
        workspace = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._board_workspace = workspace
        workspace.setSpacing(18)
        group.layout_root.addLayout(workspace, stretch=1)
        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(12)
        side_top = QHBoxLayout()
        side_layout.addLayout(side_top)
        filters = QVBoxLayout()
        filters.addWidget(QLabel('Ownership filter'))
        self.board_filters = QButtonGroup(self)
        for index, label in enumerate(('Show all', 'Show owned', 'Show unowned', 'Show owned by others')):
            button = HelpButton(label, 'Ownership is relative to the player whose turn it is.')
            button.setObjectName('boardFilter')
            button.setCheckable(True)
            self.board_filters.addButton(button, index)
            filters.addWidget(button)
        self.board_filters.button(0).setChecked(True)
        self.board_filters.idClicked.connect(self._apply_board_filter)
        filters.addStretch()
        side_top.addLayout(filters)

        detail = QFrame()
        detail.setObjectName('boardDeedWell')
        detail.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        detail.setMaximumWidth(620)
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(14, 14, 14, 14)
        detail_layout.setSpacing(12)
        self.property_card = PropertyDetailCard()
        detail_layout.addWidget(self.property_card)
        self.board_table = ReadOnlyTable(
            ['#', 'Board space', 'Type', 'Owner', 'Development', 'Rent'],
            'All 40 Monopoly spaces; choose a row before purchasing or collecting rent.',
        )
        self.board_table.setObjectName('boardTable')
        self.board_table.setIconSize(QSize(10, 10))
        self.board_table.setMinimumHeight(250)
        self.board_table.verticalHeader().setDefaultSectionSize(30)
        header = self.board_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.board_table.setColumnWidth(3, 110)
        self.board_table.itemSelectionChanged.connect(self._update_property_card)
        buttons = QGridLayout()
        self.board_buy_button = self._button(
            'Buy property', 'Purchase the selected unowned deed for the active player.',
            lambda: self._board_action('purchase'), buttons, 0, 0,
        )
        self._button(
            'Collect rent', 'Collect rent from the active player for the selected deed.',
            self._collect_rent, buttons, 0, 1,
        )
        self._button(
            'Mortgage properties', 'Select owned deeds and preview proceeds and total future payoff.',
            lambda: self._open_mortgage_planner('mortgage'), buttons, 1, 0,
        )
        self._button(
            'Unmortgage properties', 'Select mortgaged deeds and preview the total payoff before applying.',
            lambda: self._open_mortgage_planner('unmortgage'), buttons, 1, 1,
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
            'Liquidate group', 'Sell all buildings in a color group without needing replacement houses.',
            lambda: self._board_action('liquidate_building_group'), buttons, 3, 0,
        )
        self._button(
            'Pay tax', 'Pay the printed tax on Income Tax or Luxury Tax.',
            lambda: self._board_action('pay_tax'), buttons, 3, 1,
        )
        for index in range(buttons.count()):
            button = buttons.itemAt(index).widget()
            button.setObjectName('boardAction')
        buttons.setColumnStretch(0, 1)
        buttons.setColumnStretch(1, 1)
        detail_layout.addLayout(buttons)
        side_top.addWidget(detail, stretch=1, alignment=Qt.AlignmentFlag.AlignTop)
        side_layout.addWidget(tracker_card, stretch=1)
        workspace.addWidget(self.board_table, stretch=3)
        workspace.addWidget(side, stretch=2)
        self._layout_board_workspace()
        return group

    def _apply_board_filter(self, _index: int = -1) -> None:
        session = self.controller.session
        if session is None:
            return
        mode = self.board_filters.checkedId()
        player = session.current_player
        player_id = player.player_id if player else None
        self.board_filters.button(1).setToolTip(
            f'Show properties owned by {player.name}' if player else 'There is no active turn.'
        )
        table = self.board_table
        for row, space in enumerate(session.board[:table.rowCount()]):
            state = session.property_states.get(space.index)
            owner_id = state.owner_id if state else None
            matches = (
                mode == 0
                or space.ownable and (
                    (mode == 1 and owner_id is not None and owner_id == player_id)
                    or (mode == 2 and owner_id is None)
                    or (mode == 3 and owner_id is not None and owner_id != player_id)
                )
            )
            table.setRowHidden(row, not matches)
        if table.currentRow() >= 0 and table.isRowHidden(table.currentRow()):
            table.setCurrentCell(-1, -1)
            table.clearSelection()
            self._update_property_card()

    def _build_ledger_group(self) -> PanelCard:
        """Build the most recent transaction-history view."""
        group = PanelCard('Transaction ledger', 'Audited changes to cash and ownership, newest first.')
        layout = group.layout_root
        self.ledger_table = ReadOnlyTable(
            ['When (UTC)', 'Action', 'From', 'To', 'Amount', 'Details'],
            'All recorded transactions, most recent first. Scroll independently from the ownership trackers.',
        )
        self.ledger_table.setMinimumWidth(270)
        self.ledger_table.setWordWrap(True)
        for column, width in enumerate((104, 75, 76, 76, 65)):
            self.ledger_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.ledger_table.setColumnWidth(column, width)
        self.ledger_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.ledger_table.setColumnWidth(5, 180)
        layout.addWidget(self.ledger_table)
        return group

    @staticmethod
    def _fill(row: int, values: list[str], table: ReadOnlyTable) -> None:
        """Populate a read-only row without allowing edited game state."""
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setToolTip(str(value))
            table.setItem(row, col, item)

    def refresh(self, *, follow_turn: bool = False) -> None:
        """Recreate view data from the authoritative game session."""
        session = self.controller.session
        self.property_trackers.refresh(session)
        has_game = session is not None
        self.save_action.setEnabled(has_game)
        dev_available = has_game and session.winner_id is None and session.auction is None
        self.dev_shortcut.setEnabled(dev_available)
        self.dev_action.setVisible(self.controller.dev_tools_unlocked)
        self.dev_action.setEnabled(dev_available)
        self.trade_action.setEnabled(has_game and session.auction is None and session.winner_id is None)
        self.mortgages_action.setEnabled(has_game and session.auction is None and session.winner_id is None)
        self.game_settings_action.setEnabled(has_game)
        self.next_action.setEnabled(has_game and self.controller.engine.can_advance_turn())
        self._refresh_quick_actions()
        current_debts = (self.controller.engine.outstanding_payments(session.current_player.player_id)
                         if has_game and session.current_player else [])
        self.next_action.setToolTip('Pay outstanding rent or tax before advancing the turn' if current_debts
            else 'Complete required rolls and movement before advancing the turn')
        self.landing_action.setEnabled(has_game)
        self.landing_action.setChecked(
            session.show_landing_prompts if session is not None else True
        )
        self.welcome_widget.setVisible(not has_game)
        self.dashboard_widget.setVisible(has_game)
        for button in self._action_buttons:
            button.setEnabled(has_game and session.winner_id is None)
        self.player_account_button.setEnabled(has_game)
        self.player_picker.setEnabled(has_game)
        self.player_table.setEnabled(has_game)
        self.board_table.setEnabled(has_game)
        self.die_one.setEnabled(has_game)
        self.die_two.setEnabled(has_game)
        if session is None:
            self.setWindowTitle('MonopolPy Companion')
            self.player_picker.clear()
            self.player_table.setRowCount(0)
            self.board_table.setRowCount(0)
            self.ledger_table.setRowCount(0)
            self.player_focus.setText('Choose a player to see their wallet.')
            self.property_card.clear()
            self.activity_label.setVisible(False)
            self.jail_roll_button.hide()
            self.jail_bail_button.hide()
            self.jail_card_button.hide()
            self.payment_notice.hide()
            self.pay_outstanding_button.hide()
            return

        current_id = (
            session.current_player.player_id
            if follow_turn and session.current_player is not None
            else self.player_picker.currentData()
        )
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
        self._update_player_focus()

        current = session.current_player
        turn_number = sum(session.turn_counts.values())
        self.subtitle.setText(f'TURN {turn_number}' if current else 'GAME OVER')
        self.turn_title.setText(
            f'{session.get_player(session.winner_id).name} wins!' if session.winner_id
            else f'{current.name}’s turn' if current else 'Game over'
        )
        self.turn_balances.setText('   •   '.join(
            f'{player.name}  ${player.cash:,}' for player in session.players if not player.bankrupt
        ))

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
            if session.current_player is not None and player.player_id == session.current_player.player_id:
                active_item = self.player_table.item(row, 0)
                font = active_item.font()
                font.setBold(True)
                active_item.setFont(font)

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
            if owner is not None:
                owner_cell = self.board_table.item(row, 3)
                strong = owner_cell.font()
                strong.setBold(True)
                owner_cell.setFont(strong)
            if space.color_group in self._board_swatches:
                self.board_table.item(row, 1).setIcon(self._board_swatches[space.color_group])
        self._apply_board_filter()
        focus_row = (
            selected_row if 0 <= selected_row < len(board)
            else self._focused_property_index
        )
        if focus_row is not None and 0 <= focus_row < len(board) and not self.board_table.isRowHidden(focus_row):
            self.board_table.setCurrentCell(focus_row, 0)
            self.board_table.selectRow(focus_row)
        self._update_property_card()

        recent = list(reversed(session.transactions))
        self.ledger_table.setRowCount(len(recent))
        player_names = {player.player_id: player.name for player in session.players}
        for row, record in enumerate(recent):
            sender, recipient = record.from_player_id, record.to_player_id
            missing_side = 'Bank' if sender is not None or recipient is not None else '—'
            from_name = player_names.get(sender, sender) if sender is not None else missing_side
            to_name = player_names.get(recipient, recipient) if recipient is not None else missing_side
            self._fill(row, [
                record.created_at.strftime('%Y-%m-%d %H:%M'),
                record.kind.replace('_', ' ').title(),
                from_name,
                to_name,
                f'${record.amount:,}',
                record.description,
            ], self.ledger_table)
        self.ledger_table.resizeRowsToContents()
        self.player_table.resizeColumnsToContents()
        self.setWindowTitle(session.name)

    def _update_player_focus(self, _index: int = -1) -> None:
        """Update the visible wallet summary whenever the active player changes."""
        if self.controller.session is None:
            self.player_focus.setText('Choose a player to see their wallet.')
            return
        player_id = self.player_picker.currentData()
        if player_id is None:
            self.player_focus.setText('Select a player')
            return
        player = self.controller.session.get_player(player_id)
        debts = self.controller.engine.outstanding_payments(player_id)
        self.payment_notice.setVisible(bool(debts))
        self.pay_outstanding_button.setVisible(bool(debts))
        self.pay_outstanding_button.setEnabled(bool(debts))
        if debts:
            lines = []
            for debt in debts:
                amount = f"${debt['amount']:,}" if debt['amount'] is not None else 'utility dice total required'
                lines.append(f"{debt['kind'].title()} on {self.controller.session.board[debt['space_index']].name}: {amount}")
            self.payment_notice.setText('Amount owed: ' + '; '.join(lines))
        jailed_turn = (player.in_jail and player is self.controller.session.current_player
                       and self.controller.session.winner_id is None)
        self.jail_roll_button.setVisible(jailed_turn)
        self.jail_bail_button.setVisible(jailed_turn)
        self.jail_roll_button.setText(f'Roll for doubles ({player.jail_turns}/3 attempts)')
        self.jail_roll_button.setEnabled(jailed_turn and self.controller.engine.can_roll_for_doubles(player_id))
        self.jail_bail_button.setEnabled(jailed_turn and player.cash >= 50)
        self.jail_card_button.setVisible(jailed_turn and player.get_out_of_jail_cards > 0)
        self.jail_card_button.setEnabled(jailed_turn and player.jail_turns < 3 and
            not any(self.controller.session.dice_rolls[i].get('source') == 'jail'
                    for i in self.controller.session.turn_roll_indices))
        can_roll = self.controller.engine.can_roll(player_id)
        can_move = self.controller.engine.can_move_by_dice(player_id)
        self.roll_button.setEnabled(can_roll)
        self.roll_move_button.setEnabled(can_roll)
        self.move_dice_button.setEnabled(can_move)
        pending = None
        if self.controller.session.turn_roll_indices:
            pending = self.controller.session.dice_rolls[
                self.controller.session.turn_roll_indices[-1]]
        if jailed_turn:
            if self.controller.session.turn_ended:
                self.dice_result.setText('Sent to Jail. Advance the turn; attempt doubles on your next turn.')
            elif player.jail_turns >= 3:
                self.dice_result.setText('Third attempt used. Pay $50 bail to release and move by the saved roll.')
            elif pending and pending.get('source') == 'jail':
                self.dice_result.setText('No doubles. Advance the turn or pay $50 bail and move by this roll.')
            else:
                self.dice_result.setText('In Jail. Attempt doubles once this turn, or pay $50 bail before rolling.')
        elif pending and not pending['used_for_move'] and pending['player_id'] == player_id:
            self.die_one.setValue(pending['die_one'])
            self.die_two.setValue(pending['die_two'])
            self.dice_result.setText(f"Pending roll: {pending['die_one']} + {pending['die_two']}. Move before rolling again.")
        elif debts:
            self.dice_result.setText('Pay the outstanding rent or tax before continuing.')
        elif not can_roll:
            self.dice_result.setText('No roll available. Advance the turn or select the current player.')
        else:
            self.dice_result.setText('Roll available for the current player.')
        self.die_one.setEnabled(can_roll)
        self.die_two.setEnabled(can_roll)
        count = len(self.controller.session.owned_spaces_for(player_id))
        self.player_focus.setText(
            f'WALLET  ${player.cash:,}   •   {count} deed(s)'
        )

    def _update_property_card(self) -> None:
        """Render ownership and price from actual session state, not cached UI."""
        session = self.controller.session
        index = self.board_table.currentRow()
        selected = index >= 0 and not self.board_table.isRowHidden(index)
        player_id = self.player_picker.currentData()
        landing_required = session is not None and session.rules.require_landing_to_buy
        on_space = selected and player_id is not None and session.get_player(player_id).position == index
        self.board_buy_button.setEnabled(
            session is not None and session.winner_id is None and (not landing_required or on_space)
        )
        self.board_buy_button.setToolTip(
            'The buying player must be on the selected board space.' if landing_required and not on_space
            else 'Purchase the selected unowned deed for the active player.'
        )
        if session is None:
            self.property_card.clear()
            return
        if not 0 <= index < len(session.board) or self.board_table.isRowHidden(index):
            self.property_card.clear()
            return
        space = session.board[index]
        state = session.property_states.get(index)
        owner = session.owner_for(index) if space.ownable else None
        details = space.notes or space.space_type.value.replace('_', ' ').title()
        if state is not None:
            if state.mortgaged:
                details = 'Mortgaged'
            elif state.hotel:
                details = 'Hotel'
            elif state.houses:
                details = f'{state.houses} houses'
        if owner is None or not space.ownable:
            rent_label = ''
        elif space.space_type is SpaceType.UTILITY:
            rent_label = 'Rent: dice × 4 or 10'
        else:
            rent_label = f'Rent ${self.controller.engine.rent_due(index):,}'
        self.property_card.update_property(
            space.name,
            owner.name if owner is not None else None,
            price=space.price if space.ownable else None,
            rent_label=rent_label,
            details=details,
            color=BOARD_GROUP_COLORS.get(space.color_group),
        )

    def _purchase_receipt(self, player_id: str, space_index: int) -> None:
        """Show a durable confirmation and focus the newly acquired deed.

        The session itself, not the popup choice, is the source of truth.
        """
        session = self.controller.session
        if session is None:
            return
        state = session.get_property_state(space_index)
        if state.owner_id != player_id:
            self.activity_label.setText('Purchase could not be confirmed.')
            self.activity_label.setVisible(True)
            return
        player = session.get_player(player_id)
        space = session.board[space_index]
        self._focused_property_index = space_index
        self.board_table.setCurrentCell(space_index, 0)
        self.board_table.selectRow(space_index)
        self._update_property_card()
        self._update_player_focus()
        self.activity_label.setText(
            f'✓ PURCHASE RECORDED  •  {player.name} owns {space.name}  •  '
            f'Paid ${space.price:,}  •  Balance ${player.cash:,}'
        )
        self.activity_label.setVisible(True)
        self.statusBar().showMessage(
            f'{space.name} is now owned by {player.name}. Game saved.', 12000
        )

    def _new_game(self) -> None:
        """Collect new-session information and open the game dashboard."""
        dialog = NewSessionDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._focused_property_index = None
            self.activity_label.setVisible(False)
            self.controller.new_session(
                dialog.game_name, dialog.player_names, dialog.starting_cash,
                accounts=dialog.selected_accounts,
                landing_prompts=self.settings.value('landing_alerts', True, type=bool),
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
            self._focused_property_index = None
            self.activity_label.setVisible(False)
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
                if action == 'purchase':
                    self._purchase_receipt(args[0], args[1])
                    return result
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
        if row < 0 or self.board_table.isRowHidden(row):
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
        if action == 'liquidate_building_group' and not self._confirm_group_liquidation(player_id, space_index):
            return
        self._perform(action, player_id, space_index)

    def _confirm_group_liquidation(self, player_id: str, space_index: int) -> bool:
        try:
            proceeds = self.controller.engine.building_group_liquidation_quote(player_id, space_index)
        except ValueError as exc:
            self._show_error('Cannot liquidate group', exc)
            return False
        space = self.controller.session.board[space_index]
        dialog = QMessageBox(QMessageBox.Icon.Question, 'Confirm group liquidation',
                             f'Sell all buildings in the {space.color_group} group?\n\n'
                             f'Expected cash return: ${proceeds:,}.',
                             QMessageBox.StandardButton.Cancel, self)
        dialog.setTextFormat(Qt.TextFormat.PlainText)
        confirm = dialog.addButton('Confirm', QMessageBox.ButtonRole.AcceptRole)
        dialog.setDefaultButton(QMessageBox.StandardButton.Cancel)
        dialog.exec()
        return dialog.clickedButton() is confirm

    def _pay_outstanding(self):
        player_id = self._selected_player_id()
        debts = self.controller.engine.outstanding_payments(player_id)
        if not debts:
            return
        options = {}
        if debts[0]['amount'] is None:
            total, accepted = QInputDialog.getInt(self, 'Utility rent', 'Dice total for this utility landing:', 7, 2, 12)
            if not accepted:
                return
            options['dice_total'] = total
        self._perform('pay_outstanding', player_id, **options)

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


    def _roll_dice(self) -> bool:
        """Roll unbiased dice through the controller and save the statistics."""
        if self.controller.engine is None:
            return False
        try:
            player_id = self._selected_player_id()
        except ValueError as exc:
            self._show_error('Select player', exc)
            return False
        result = self._perform('simulate_dice', player_id)
        if result is None:
            return False
        first, second = result
        if self.controller.session.get_player(player_id).in_jail:
            self.dice_result.setText(f'Rolled {first} + {second}: three doubles. Go directly to Jail; turn ended.')
            self.statusBar().showMessage('Three doubles: sent directly to Jail without passing GO.', 10000)
            self.board_table.selectRow(10)
            self._update_property_card()
            return False
        self.die_one.setValue(first)
        self.die_two.setValue(second)
        self.dice_result.setText(
            f'Rolled {first} + {second} = {first + second}'
            + (' — DOUBLES!' if first == second else '')
        )
        return True

    def _roll_and_move(self) -> None:
        """Simulate one roll and apply exactly that result to movement."""
        if self._roll_dice():
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
        self._focused_property_index = space.index
        self.board_table.selectRow(space.index)
        self._update_property_card()
        item = self.board_table.item(space.index, 1)
        if item is not None:
            self.board_table.scrollToItem(item)
        self.statusBar().showMessage(f'Landed on {space.name}', 9000)
        if self.dashboard_widget.currentWidget() is self.turn_view:
            return  # This Turn already presents purchase and payment actions inline.
        if not self.controller.session.show_landing_prompts or not space.ownable:
            return
        owner = self.controller.session.owner_for(space.index)
        if owner is None:
            choice = QMessageBox.question(
                self, 'Unowned property',
                f'{space.name} is unowned. Buy it from the bank for ${space.price:,}? '
                'Choose No to start an auction.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if choice == QMessageBox.StandardButton.Yes:
                self._perform('purchase', player_id, space.index)
            elif choice == QMessageBox.StandardButton.No and self.controller.session.purchase_offer == space.index:
                self._perform('start_auction', player_id)
        elif owner.player_id != player_id:
            dice_total = self.die_one.value() + self.die_two.value()
            options = {'dice_total': dice_total} if space.space_type is SpaceType.UTILITY else {}
            payment = next((item for item in self.controller.engine.outstanding_payments(player_id)
                            if item['space_index'] == space.index and item['kind'] == 'rent'), None)
            if payment is None:
                return
            rent = payment['amount']
            if rent is None:
                rent = dice_total * payment['utility_multiplier']
            if rent:
                choice = QMessageBox.question(
                    self, 'Rent due',
                    f'{space.name} belongs to {owner.name}.\n'
                    f'Rent due: ${rent:,}. Pay {owner.name} now?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if choice == QMessageBox.StandardButton.Yes:
                    self._perform('collect_rent', player_id, space.index, **options)

    def _open_mortgage_planner(self, operation: str):
        try:
            player_id = self._selected_player_id()
        except ValueError as exc:
            self._show_error('Select player', exc)
            return
        if not self._unlock_player(player_id):
            return
        dialog = PlayerAccountDialog(self.controller, player_id, self)
        dialog.select_mortgage_operation(operation)
        dialog.exec()
        self.refresh()

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

    def _open_dev_tools(self):
        session = self.controller.session
        if session is None or session.winner_id is not None or session.auction is not None:
            return
        if not self.controller.dev_tools_unlocked:
            if not self._introduce_map():
                return
            phrase = self._prompt_map_phrase()
            if phrase is None:
                return
            try:
                unlocked = self.controller.unlock_dev_tools(phrase)
            except OSError as exc:
                self._show_error('Could not write mm.lock', exc)
                return
            if not unlocked:
                QMessageBox.information(self, 'Marauder’s Map', 'The map stays blank.')
                return
        self.refresh()
        DevToolsDialog(self.controller, self.player_picker.currentData(), self).exec()
        self.refresh()

    def _introduce_map(self) -> bool:
        return _introduction(self).exec() == QDialog.DialogCode.Accepted

    def _prompt_map_phrase(self) -> str | None:
        prompt, editor = _phrase_entry(self)
        return editor.text() if prompt.exec() == QDialog.DialogCode.Accepted else None

    def _trade(self):
        if self.controller.session is None:
            return
        dialog = TradeDialog(self.controller, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        args = dialog.trade_args
        if QMessageBox.question(self, 'Confirm trade', dialog.summary.text() + '\n\nCommit this exchange?') != QMessageBox.StandardButton.Yes:
            return
        for key in ('player_a_id', 'player_b_id'):
            if not self._unlock_player(args[key]):
                return
        self._perform('trade', **args)

    def _transfer(self) -> None:
        """Open bank/player transfer dialog and submit it to GameEngine."""
        if self.controller.session is None:
            return
        dialog = TransferDialog(self.controller.session, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._perform('transfer', **dialog.transfer_args)

    def _jail_roll(self):
        player_id = self._selected_player_id()
        result = self._perform('roll_for_doubles', player_id)
        if result is None:
            return
        first, second = result['dice']
        message = f'Jail roll: {first} + {second}.'
        if result['bail_required']:
            message += ' Third attempt: pay $50 bail to release and move by this roll.'
        elif result['movement'] is None:
            message += ' No doubles. Advance to the next turn.'
        else:
            message += ' Doubles! Released from Jail; no extra roll.'
            self._handle_landing(player_id, result['movement'])
        self.dice_result.setText(message)

    def _jail_bail(self):
        player_id = self._selected_player_id()
        movement = self._perform('pay_jail_bail', player_id)
        if movement is not None:
            self._handle_landing(player_id, movement)

    def _release_from_jail(self) -> None:
        """Choose the permitted way to release a selected player."""
        try:
            player_id = self._selected_player_id()
        except ValueError as exc:
            self._show_error('Select player', exc)
            return
        self._perform('release_from_jail', player_id, method='card')

    def _toggle_theme(self) -> None:
        """Switch the desktop palette without affecting game state."""
        self._dark_theme = not self._dark_theme
        self.settings.setValue('dark', self._dark_theme)
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet(self._dark_theme))
        self.theme_action.setText('Light theme' if self._dark_theme else 'Dark theme')
        self.refresh()

    def _create_account(self):
        NewAccountDialog(self.accounts, self).exec()

    def _game_settings(self):
        if self.controller.session is not None:
            GameSettingsDialog(self.controller, self).exec()

    def _settings(self):
        if SettingsDialog(self.settings, self).exec() == QDialog.DialogCode.Accepted:
            self._apply_preferences()

    def _apply_preferences(self):
        self._dark_theme = self.settings.value('dark', True, type=bool)
        app = QApplication.instance()
        app.setStyleSheet(stylesheet(self._dark_theme))
        app.setProperty('sparkles', self.settings.value('sparkles', True, type=bool))
        self.theme_action.setText('Light theme' if self._dark_theme else 'Dark theme')
        self.refresh()

    def _show_error(self, title: str, error: Exception) -> None:
        """Display friendly errors instead of exposing a traceback in the GUI."""
        QMessageBox.warning(self, title, str(error))
