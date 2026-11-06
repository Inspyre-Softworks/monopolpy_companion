"""Offscreen Qt smoke tests that require the optional PySide6 extra."""

import logging
import os
import tempfile
import unittest
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication, QMessageBox
    from monopolpy_companion.ui.main_window import MainWindow
except ImportError:
    QApplication = None
    MainWindow = None

from monopolpy_companion.controller import SessionController
from monopolpy_companion.game import SessionRepository


@unittest.skipUnless(QApplication is not None, 'PySide6 GUI extra is not installed')
class QtGuiTests(unittest.TestCase):
    """Verify the dashboard binds to GameEngine without bypassing it."""

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.controller = SessionController(
            repository=SessionRepository(self.directory.name),
            logger=logging.getLogger('monopoly.qt.test'),
        )
        self.window = MainWindow(self.controller)
        self.addCleanup(self.window.close)

    def test_account_picker_registration_and_preferences(self):
        from PySide6.QtCore import QSettings
        from monopolpy_companion.game.accounts import AccountStore
        from monopolpy_companion.ui.dialogs import NewAccountDialog, NewSessionDialog, SettingsDialog
        self.window.accounts = AccountStore(self.directory.name + '/accounts')
        dialog = NewAccountDialog(self.window.accounts, self.window)
        dialog.username.setText('Taylor')
        self.assertEqual(dialog.availability.text(), 'Username available')
        dialog._save()
        duplicate = NewAccountDialog(self.window.accounts, self.window)
        duplicate.username.setText('taylor')
        self.assertIn('already exists', duplicate.availability.text())
        setup = NewSessionDialog(self.window)
        setup.account_picker.setCurrentIndex(1)
        setup._add_account()
        self.assertEqual(setup.player_names, ['Taylor'])
        settings = QSettings(self.directory.name + '/settings.ini', QSettings.Format.IniFormat)
        preferences = SettingsDialog(settings)
        preferences.sparkles.setChecked(False)
        preferences._save()
        restored = SettingsDialog(QSettings(self.directory.name + '/settings.ini', QSettings.Format.IniFormat))
        self.assertFalse(restored.sparkles.isChecked())

    def test_typing_registered_username_cannot_bypass_password_or_pin(self):
        from monopolpy_companion.game.accounts import AccountStore
        from monopolpy_companion.ui.dialogs import NewSessionDialog
        directory = self.directory.name + '/accounts'
        store = AccountStore(directory)
        store.create('Taylor', 'password', '1234')
        self.window.accounts = AccountStore(directory)
        setup = NewSessionDialog(self.window)
        setup.players_field.setText('Taylor, Guest')
        with patch('monopolpy_companion.ui.dialogs.QInputDialog.getText', return_value=('', False)):
            setup._validate()
        self.assertEqual(setup.result(), 0)
        self.assertEqual(setup.selected_accounts, {})
        with patch('monopolpy_companion.ui.dialogs.QInputDialog.getText', return_value=('password', True)):
            setup._validate()
        self.assertEqual(setup.result(), 1)
        self.assertTrue(setup.selected_accounts['taylor']['data']['pin_hash'])

    def test_session_render_and_action_refresh(self):
        session = self.controller.new_session('Qt Test', ['Avery', 'Blake'])
        self.assertEqual(self.window.player_table.rowCount(), 2)
        self.assertEqual(self.window.board_table.rowCount(), 40)
        self.controller.perform('purchase', session.players[0].player_id, 1)
        self.assertEqual(self.window.board_table.item(1, 3).text(), 'Avery')
        self.assertEqual(self.window.ledger_table.item(0, 1).text(), 'Purchase')

    def test_landing_purchase_updates_wallet_deed_ledger_and_save(self):
        session = self.controller.new_session('Buy a deed', ['Avery', 'Blake'])
        self.window.die_one.setValue(1)
        self.window.die_two.setValue(2)
        with patch(
            'monopolpy_companion.ui.main_window.QMessageBox.question',
            return_value=QMessageBox.StandardButton.Yes,
        ):
            self.window._move_by_dice()
        self.assertEqual(session.players[0].position, 3)
        self.assertEqual(session.property_states[3].owner_id, session.players[0].player_id)
        self.assertEqual(session.players[0].cash, 1440)
        self.assertEqual(self.window.board_table.currentRow(), 3)
        self.assertEqual(self.window.board_table.item(3, 3).text(), 'Avery')
        self.assertEqual(self.window.player_table.item(0, 1).text(), '$1,440')
        self.assertIn('OWNED BY AVERY', self.window.property_card.owner.text())
        self.assertIn('Baltic Avenue', self.window.activity_label.text())
        self.assertIn('Balance $1,440', self.window.activity_label.text())
        self.assertEqual(self.window.ledger_table.item(0, 1).text(), 'Purchase')
        saved = self.controller.repository.load(session.save_path)
        self.assertEqual(saved.property_states[3].owner_id, session.players[0].player_id)

    def test_board_purchase_button_shows_confirmation_without_movement(self):
        session = self.controller.new_session('Direct buy', ['Avery', 'Blake'])
        self.window.board_table.setCurrentCell(1, 0)
        self.window._board_action('purchase')
        self.assertEqual(session.property_states[1].owner_id, session.players[0].player_id)
        self.assertEqual(session.players[0].cash, 1440)
        self.assertIn('Mediterranean Avenue', self.window.activity_label.text())
        self.assertIn('OWNED BY AVERY', self.window.property_card.owner.text())

    def test_disabled_landing_alert_still_focuses_space_without_buying(self):
        session = self.controller.new_session('No alerts', ['Avery', 'Blake'])
        self.controller.set_landing_prompts(False)
        self.window.die_one.setValue(1)
        self.window.die_two.setValue(2)
        with patch('monopolpy_companion.ui.main_window.QMessageBox.question') as prompt:
            self.window._move_by_dice()
            prompt.assert_not_called()
        self.assertEqual(self.window.board_table.currentRow(), 3)
        self.assertIsNone(session.property_states[3].owner_id)
        self.assertIn('AVAILABLE TO BUY', self.window.property_card.owner.text())

    def test_quick_actions_show_purchase_then_auction_bidders(self):
        session = self.controller.new_session('Quick auction', ['Avery', 'Blake'])
        buttons = self.window.quick_buttons
        self.assertFalse(buttons['roll'].isHidden())
        self.controller.perform('move_by_dice', session.players[0].player_id, 1, 2)
        self.assertEqual(buttons['buy'].text(), 'Buy for $60')
        self.assertFalse(buttons['auction'].isHidden())
        buttons['auction'].click()
        self.assertIn('Avery to bid or pass', self.window.quick_status.text())
        with patch('monopolpy_companion.ui.main_window.QInputDialog.getInt', return_value=(30, True)):
            buttons['bid'].click()
        self.assertIn('Blake to bid or pass', self.window.quick_status.text())
        buttons['pass'].click()
        self.assertEqual(session.owner_for(3).player_id, session.players[0].player_id)
        self.assertIn('won Baltic Avenue for $30', self.window.activity_label.text())
        self.assertFalse(buttons['next'].isHidden())

    def test_quick_actions_pay_current_players_tax_even_with_other_player_selected(self):
        session = self.controller.new_session('Quick tax', ['Avery', 'Blake'])
        session.players[0].position = 1
        self.controller.perform('move_by_dice', session.players[0].player_id, 1, 2)
        self.window.player_picker.setCurrentIndex(1)
        button = self.window.quick_buttons['pay']
        self.assertEqual(button.text(), 'Pay tax ($200)')
        button.click()
        self.assertEqual(session.players[0].cash, 1300)
        self.assertEqual(session.players[1].cash, 1500)
        self.assertTrue(button.isHidden())

    def test_quick_actions_confirm_bankruptcy_and_show_winner(self):
        session = self.controller.new_session('Bankruptcy UI', ['Avery', 'Blake'])
        a, b = session.players
        a.cash = 10
        a.position = 1
        self.controller.perform('move_by_dice', a.player_id, 1, 2)
        button = self.window.quick_buttons['bankruptcy']
        self.assertFalse(button.isHidden())
        with patch('monopolpy_companion.ui.main_window.QMessageBox.question',
                   return_value=QMessageBox.StandardButton.No):
            button.click()
        self.assertFalse(a.bankrupt)
        with patch('monopolpy_companion.ui.main_window.QMessageBox.question',
                   return_value=QMessageBox.StandardButton.Yes):
            button.click()
        self.assertTrue(a.bankrupt)
        self.assertEqual(session.winner_id, b.player_id)
        self.assertEqual(self.window.quick_status.text(), 'Blake wins!')
        self.assertTrue(self.window.player_account_button.isEnabled())
        self.assertTrue(button.isHidden())

    def test_marauders_map_reveals_toolbar_and_grants_with_one_click(self):
        from monopolpy_companion.ui.dev_tools_dialog import DevToolsDialog
        session = self.controller.new_session('Hidden map', ['Avery', 'Blake'])
        player = session.players[0]
        self.assertFalse(self.window.dev_action.isVisible())
        with patch('monopolpy_companion.ui.main_window.QInputDialog.getText',
                   return_value=('I solemnly swear that I am up to no good', True)):
            with patch('monopolpy_companion.ui.main_window.DevToolsDialog.exec'):
                self.window._open_dev_tools()
        self.assertTrue(self.window.dev_action.isVisible())
        dialog = DevToolsDialog(self.controller, player.player_id, self.window)
        dialog.cash_button.click()
        dialog.deed_button.click()
        dialog.house_button.click()
        dialog.hotel_button.click()
        self.assertEqual(player.cash, 2000)
        self.assertEqual(session.owner_for(1).player_id, player.player_id)
        self.assertTrue(session.get_property_state(1).hotel)
        dialog._lock()
        self.window.refresh()
        self.assertFalse(self.window.dev_action.isVisible())

    def test_actions_disabled_without_game(self):
        self.assertFalse(self.window.save_action.isEnabled())
        self.assertFalse(self.window.next_action.isEnabled())
        self.assertEqual(self.window.board_table.rowCount(), 0)

    def test_welcome_and_game_visibility(self):
        self.assertTrue(self.window.welcome_widget.isVisibleTo(self.window.centralWidget()))
        self.controller.new_session('Welcome', ['Avery', 'Blake'])
        self.assertFalse(self.window.welcome_widget.isVisibleTo(self.window.centralWidget()))

    def test_rolled_simulation_updates_dice_and_stats(self):
        from monopolpy_companion import StatisticsService
        session = self.controller.new_session('Rolls', ['Avery', 'Blake'])
        self.window._roll_dice()
        self.assertEqual(
            StatisticsService(session).for_player(session.players[0].player_id).gameplay.dice_rolls,
            1,
        )

    def test_next_turn_roll_and_move_follow_incoming_player(self):
        session = self.controller.new_session('Turns', ['Avery', 'Blake', 'Casey'])
        self.controller.set_landing_prompts(False)
        first, skipped, incoming = session.players
        skipped.bankrupt = True
        self.controller.perform('move_by_dice', first.player_id, 1, 2)
        first.position = 0
        self.window.next_action.trigger()
        self.assertEqual(session.current_player.player_id, incoming.player_id)
        self.assertEqual(self.window.player_picker.currentData(), incoming.player_id)
        self.assertIn('Turn: Casey', self.window.subtitle.text())
        with patch.object(self.controller.engine, 'simulate_dice', return_value=(1, 2)) as roll:
            with patch('monopolpy_companion.ui.main_window.QInputDialog.getText') as password:
                self.window._roll_and_move()
                password.assert_not_called()
        roll.assert_called_once_with(incoming.player_id)
        self.assertEqual(incoming.position, 3)
        self.assertEqual(first.position, 0)
        self.window.next_action.trigger()
        self.assertEqual(self.window.player_picker.currentData(), first.player_id)

    def test_refresh_preserves_manual_choice_until_turn_changes(self):
        session = self.controller.new_session('Manual actions', ['Avery', 'Blake'])
        second = session.players[1]
        self.window.player_picker.setCurrentIndex(1)
        self.controller.perform('transfer', amount=20, to_player_id=second.player_id)
        self.assertEqual(self.window.player_picker.currentData(), second.player_id)
        self.controller.perform('move_by_dice', session.current_player.player_id, 1, 2)
        self.controller.perform('advance_turn')
        self.controller.perform('move_by_dice', session.current_player.player_id, 1, 2)
        self.controller.perform('advance_turn')
        self.assertEqual(self.window.player_picker.currentData(), session.players[0].player_id)

    def test_reopening_game_selects_saved_current_player(self):
        session = self.controller.new_session('Resume turn', ['Avery', 'Blake'])
        self.controller.perform('move_by_dice', session.current_player.player_id, 1, 2)
        self.controller.perform('advance_turn')
        self.window.player_picker.setCurrentIndex(0)
        self.controller.open_session(session.save_path)
        self.assertEqual(self.window.player_picker.currentData(), session.players[1].player_id)

    def test_salary_settings_gold_notice_and_roll_controls(self):
        from monopolpy_companion.ui.dialogs import GameSettingsDialog
        self.assertFalse(self.window.game_settings_action.isEnabled())
        session = self.controller.new_session('Salary', ['Avery', 'Blake'])
        self.controller.set_landing_prompts(False)
        dialog = GameSettingsDialog(self.controller, self.window)
        self.assertFalse(dialog.double_salary.isChecked())
        dialog.salary.setValue(300)
        dialog.double_salary.setChecked(True)
        dialog._save()
        player = session.players[0]
        player.position = 37
        self.window.die_one.setValue(1)
        self.window.die_two.setValue(2)
        self.window._move_by_dice()
        self.assertEqual(player.cash, 2100)
        self.assertIn('+$600', self.window.salary_notice.text())
        self.assertIn('Avery', self.window.salary_notice.text())
        self.assertIn('$2,100', self.window.salary_notice.text())
        self.assertFalse(self.window.salary_notice.isHidden())
        self.assertFalse(self.window.roll_button.isEnabled())
        self.assertFalse(self.window.roll_move_button.isEnabled())
        self.assertFalse(self.window.move_dice_button.isEnabled())
        self.window.next_action.trigger()
        self.assertTrue(self.window.roll_button.isEnabled())

    def test_pending_roll_restored_in_dice_controls(self):
        from unittest.mock import patch
        session = self.controller.new_session('Pending dice', ['Avery', 'Blake'])
        with patch('secrets.randbelow', side_effect=[0, 1]):
            self.window._roll_dice()
        self.controller.open_session(session.save_path)
        self.assertEqual((self.window.die_one.value(), self.window.die_two.value()), (1, 2))
        self.assertFalse(self.window.roll_button.isEnabled())
        self.assertTrue(self.window.move_dice_button.isEnabled())

    def test_jail_buttons_only_for_current_prisoner_and_next_turn_gating(self):
        session = self.controller.new_session('Jail UI', ['Avery', 'Blake'])
        self.controller.set_landing_prompts(False)
        first, second = session.players
        self.assertFalse(self.window.next_action.isEnabled())
        first.position = 10
        self.window.refresh()
        self.assertTrue(self.window.jail_roll_button.isHidden())
        self.assertTrue(self.window.jail_bail_button.isHidden())
        self.controller.perform('send_to_jail', first.player_id)
        self.assertFalse(self.window.jail_roll_button.isHidden())
        self.assertFalse(self.window.jail_bail_button.isHidden())
        self.assertTrue(self.window.next_action.isEnabled())
        self.window.next_action.trigger()
        self.assertTrue(self.window.jail_bail_button.isHidden())
        self.controller.perform('move_by_dice', second.player_id, 1, 2)
        self.window.next_action.trigger()
        self.assertFalse(self.window.next_action.isEnabled())
        with patch('secrets.randbelow', side_effect=[0, 1]):
            self.window._jail_roll()
        self.assertIn('1/3', self.window.jail_roll_button.text())
        self.assertFalse(self.window.jail_roll_button.isEnabled())
        self.assertTrue(self.window.next_action.isEnabled())
        self.window._jail_bail()
        self.assertFalse(first.in_jail)
        self.assertEqual(first.cash, 1450)
        self.assertEqual(first.position, 13)
        self.assertTrue(self.window.jail_bail_button.isHidden())

    def test_next_turn_disabled_after_doubles_and_until_pending_move(self):
        session = self.controller.new_session('Double roll UI', ['Avery', 'Blake'])
        first = session.players[0]
        self.controller.perform('move_by_dice', first.player_id, 1, 1)
        self.assertFalse(self.window.next_action.isEnabled())
        with patch('secrets.randbelow', side_effect=[0, 1]):
            self.controller.perform('simulate_dice', first.player_id)
        self.assertFalse(self.window.next_action.isEnabled())
        self.controller.perform('move_by_dice', first.player_id, 1, 2)
        self.assertTrue(self.window.next_action.isEnabled())

    def test_unpaid_tax_keeps_next_turn_disabled_until_payment(self):
        session = self.controller.new_session('Tax UI', ['Avery', 'Blake'])
        self.controller.set_landing_prompts(False)
        session.players[0].position = 1
        self.controller.perform('move_by_dice', session.players[0].player_id, 1, 2)
        self.assertFalse(self.window.next_action.isEnabled())
        self.assertFalse(self.window.pay_outstanding_button.isHidden())
        self.assertIn('Income Tax: $200', self.window.payment_notice.text())
        self.controller.open_session(session.save_path)
        self.assertFalse(self.window.next_action.isEnabled())
        self.window._pay_outstanding()
        self.assertTrue(self.window.next_action.isEnabled())
        self.assertTrue(self.window.pay_outstanding_button.isHidden())
        self.assertEqual(self.controller.session.players[0].cash, 1300)

    def test_property_trackers_cover_all_groups_and_update_after_actions(self):
        session = self.controller.new_session('Trackers', ['Avery', 'Blake'])
        first, second = session.players
        panel = self.window.property_trackers.panels[first.player_id]
        other = self.window.property_trackers.panels[second.player_id]
        self.assertEqual(len(panel.tiles), 28)
        self.assertEqual([len(group.tiles) for group in panel.groups.values()],
                         [2, 3, 3, 3, 3, 3, 3, 2, 4, 2])
        self.assertEqual([tile.space.index for tile in panel.groups['Railroads'].tiles], [5, 15, 25, 35])
        self.assertEqual([tile.space.index for tile in panel.groups['Utilities'].tiles], [12, 28])
        self.assertEqual(panel.groups['Railroads'].tiles[0].color.name(), '#000000')
        self.assertEqual(panel.groups['Utilities'].tiles[0].color.name(), '#808080')
        self.assertTrue(panel.current_turn)
        self.assertFalse(other.current_turn)
        self.assertFalse(panel.tiles[1].owned)
        self.controller.perform('purchase', first.player_id, 1)
        self.assertTrue(panel.tiles[1].owned)
        self.assertFalse(other.tiles[1].owned)
        self.assertFalse(panel.groups['Brown'].complete)
        self.controller.perform('purchase', first.player_id, 3)
        self.assertTrue(panel.groups['Brown'].complete)
        self.controller.perform('mortgage', first.player_id, 1)
        self.assertTrue(panel.tiles[1].mortgaged)
        self.assertTrue(panel.groups['Brown'].complete)
        self.assertIn('mortgaged', panel.tiles[1].toolTip())
        self.assertIn(f'${first.cash:,}', panel.cash_label.text())
        self.controller.perform('unmortgage', first.player_id, 1)
        self.assertFalse(panel.tiles[1].mortgaged)
        self.controller.perform('move_by_dice', first.player_id, 1, 2)
        self.window.next_action.trigger()
        self.assertFalse(panel.current_turn)
        self.assertTrue(other.current_turn)
        self.assertEqual(self.window.ledger_table.item(0, 1).text(),
                         session.transactions[-1].kind.replace('_', ' ').title())

    def test_railroad_utility_sets_and_tracker_restoration(self):
        session = self.controller.new_session('Special sets', ['Avery', 'Blake'])
        first = session.players[0]
        for index in [5, 15, 25, 35, 12, 28]:
            self.controller.perform('purchase', first.player_id, index)
        panel = self.window.property_trackers.panels[first.player_id]
        self.assertTrue(panel.groups['Railroads'].complete)
        self.assertTrue(panel.groups['Utilities'].complete)
        self.controller.perform('mortgage', first.player_id, 12)
        self.controller.open_session(session.save_path)
        panel = self.window.property_trackers.panels[first.player_id]
        self.assertTrue(panel.tiles[12].owned)
        self.assertTrue(panel.tiles[12].mortgaged)
        self.assertTrue(panel.groups['Utilities'].complete)
        self.controller.new_session('Replacement', ['Casey', 'Drew'])
        self.assertNotIn(first.player_id, self.window.property_trackers.panels)
        self.assertEqual(len(self.window.property_trackers.panels), 2)
        self.assertTrue(all(not tile.owned for row in self.window.property_trackers.panels.values()
                            for tile in row.tiles.values()))

    def test_trade_review_displays_immunity_on_incoming_deed(self):
        from monopolpy_companion.ui.trade_dialog import TradeDialog
        session = self.controller.new_session('Immunity UI', ['Avery', 'Blake'])
        session.rules.allow_rent_immunity = True
        self.controller.perform('purchase', session.players[1].player_id, 6)
        dialog = TradeDialog(self.controller, self.window)
        a, b = dialog.sides
        self.assertEqual(a['group'].title(), 'Avery gives')
        b['deeds'].item(0).setSelected(True)
        self.assertIn('$100', b['value'].text())
        incoming = a['scope'].findData(6)
        self.assertGreaterEqual(incoming, 0)
        a['scope'].setCurrentIndex(incoming)
        a['duration'].setValue(2)
        self.assertIn('Rent immunity: Oriental Avenue, 2 rent charges waived', dialog.summary.text())

    def test_trade_dialog_updates_both_property_trackers(self):
        from monopolpy_companion.ui.trade_dialog import TradeDialog
        session = self.controller.new_session('Trade UI', ['Avery', 'Blake'])
        a, b = session.players
        self.controller.perform('purchase', a.player_id, 1)
        self.controller.perform('purchase', b.player_id, 6)
        dialog = TradeDialog(self.controller, self.window)
        dialog.sides[0]['deeds'].item(0).setSelected(True)
        dialog.sides[1]['deeds'].item(0).setSelected(True)
        dialog.sides[0]['cash'].setValue(25)
        self.assertIn('Cash after trade', dialog.summary.text())
        self.assertIn('Mediterranean Avenue', dialog.summary.text())
        args = dialog.trade_args
        self.controller.perform('trade', **args)
        panels = self.window.property_trackers.panels
        self.assertFalse(panels[a.player_id].tiles[1].owned)
        self.assertTrue(panels[b.player_id].tiles[1].owned)
        self.assertTrue(panels[a.player_id].tiles[6].owned)
        self.assertFalse(panels[b.player_id].tiles[6].owned)
        self.assertIn(f'${a.cash:,}', panels[a.player_id].cash_label.text())
        self.assertEqual(self.window.ledger_table.item(0, 1).text(), 'Trade')

    def test_account_statistics_switch_between_current_saved_and_overall(self):
        from monopolpy_companion.ui.account_dialog import PlayerAccountDialog
        first = self.controller.new_session('First game', ['Avery', 'Blake'])
        self.controller.perform('move_by_dice', first.players[0].player_id, 1, 2)
        active = self.controller.new_session('Current game', ['Avery', 'Casey'])
        dialog = PlayerAccountDialog(self.controller, active.players[0].player_id, self.window)
        self.assertIn('Dice rolls: 0', dialog.gameplay_text.toPlainText())
        dialog.stats_scope.setCurrentIndex(1)
        self.assertIn('Games played: 2', dialog.gameplay_text.toPlainText())
        self.assertIn('Dice rolls: 1', dialog.gameplay_text.toPlainText())
        self.assertIn('First game', dialog.stats_scope.itemText(2))
        dialog.stats_scope.setCurrentIndex(2)
        self.assertIn('Games played: 1', dialog.gameplay_text.toPlainText())
        self.assertIn('Dice rolls: 1', dialog.gameplay_text.toPlainText())

    def test_multi_property_planner_previews_both_totals_and_confirms_batch(self):
        from monopolpy_companion.ui.account_dialog import PlayerAccountDialog
        session = self.controller.new_session('Mortgage preview', ['Avery', 'Blake'])
        player = session.players[0]
        for index in (1, 3):
            self.controller.perform('purchase', player.player_id, index)
        dialog = PlayerAccountDialog(self.controller, player.player_id, self.window)
        dialog.select_mortgage_operation('mortgage')
        self.assertIs(dialog.tabs.currentWidget(), dialog.mortgage_tab)
        self.assertFalse(dialog.apply_button.isEnabled())
        before = session.to_dict()
        for index in range(dialog.properties.count()):
            dialog.properties.item(index).setSelected(True)
        self.assertEqual(session.to_dict(), before)
        self.assertIn('Cash received now: $60', dialog.quote_label.text())
        self.assertIn('properties later: $66', dialog.quote_label.text())
        self.assertIn('Interest: $6', dialog.quote_label.text())
        self.assertIn('Cash after applying: $1,440', dialog.quote_label.text())
        with patch('monopolpy_companion.ui.account_dialog.QMessageBox.question',
                   return_value=QMessageBox.StandardButton.No):
            dialog._apply()
        self.assertEqual(session.to_dict(), before)
        with patch('monopolpy_companion.ui.account_dialog.QMessageBox.question',
                   return_value=QMessageBox.StandardButton.Yes) as confirm:
            dialog._apply()
        self.assertIn('properties later: $66', confirm.call_args.args[2])
        self.assertEqual(player.cash, 1440)
        self.assertTrue(all(session.get_property_state(index).mortgaged for index in (1, 3)))
        dialog.select_mortgage_operation('unmortgage')
        for index in range(dialog.properties.count()):
            dialog.properties.item(index).setSelected(True)
        self.assertIn('Total to unmortgage now: $66', dialog.quote_label.text())
        self.assertIn('Cash after applying: $1,374', dialog.quote_label.text())
        with patch('monopolpy_companion.ui.account_dialog.QMessageBox.question',
                   return_value=QMessageBox.StandardButton.Yes):
            dialog._apply()
        self.assertEqual(player.cash, 1374)
        saved = self.controller.repository.load(session.save_path)
        self.assertTrue(all(not saved.get_property_state(index).mortgaged for index in (1, 3)))

    def test_planner_blocks_unaffordable_payoff_and_opens_from_shortcut(self):
        from monopolpy_companion.ui.account_dialog import PlayerAccountDialog
        session = self.controller.new_session('Payoff preview', ['Avery', 'Blake'])
        player = session.players[0]
        self.controller.perform('purchase', player.player_id, 1)
        self.controller.perform('mortgage', player.player_id, 1)
        player.cash = 10
        dialog = PlayerAccountDialog(self.controller, player.player_id, self.window)
        dialog.select_mortgage_operation('unmortgage')
        dialog.properties.item(0).setSelected(True)
        self.assertIn('Insufficient cash', dialog.quote_label.text())
        self.assertFalse(dialog.apply_button.isEnabled())
        with patch('monopolpy_companion.ui.main_window.PlayerAccountDialog') as planner:
            self.window._open_mortgage_planner('unmortgage')
        planner.return_value.select_mortgage_operation.assert_called_once_with('unmortgage')
        planner.return_value.exec.assert_called_once()

    def test_third_double_stops_roll_and_move_and_setting_is_saved(self):
        from monopolpy_companion.ui.dialogs import GameSettingsDialog
        session = self.controller.new_session('Three doubles', ['Avery', 'Blake'])
        self.controller.set_landing_prompts(False)
        player = session.players[0]
        self.controller.perform('move_by_dice', player.player_id, 1, 1)
        self.controller.perform('move_by_dice', player.player_id, 2, 2)
        with patch('secrets.randbelow', side_effect=[2, 2]):
            self.window._roll_and_move()
        self.assertTrue(player.in_jail)
        self.assertEqual(player.position, 10)
        self.assertIn('three doubles', self.window.dice_result.text())
        self.assertTrue(self.window.next_action.isEnabled())
        self.assertFalse(self.window.roll_button.isEnabled())
        settings = GameSettingsDialog(self.controller, self.window)
        self.assertTrue(settings.three_doubles.isChecked())
        settings.three_doubles.setChecked(False)
        settings._save()
        restored = self.controller.repository.load(session.save_path)
        self.assertFalse(restored.rules.three_doubles_to_jail)

    def test_generated_icon_available(self):
        self.assertFalse(self.window.windowIcon().isNull())

    def test_theme_toggle_changes_label(self):
        self.window._toggle_theme()
        self.assertEqual(self.window.theme_action.text(), 'Dark theme')


if __name__ == '__main__':
    unittest.main()
