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

    def test_generated_icon_available(self):
        self.assertFalse(self.window.windowIcon().isNull())

    def test_theme_toggle_changes_label(self):
        self.window._toggle_theme()
        self.assertEqual(self.window.theme_action.text(), 'Dark theme')


if __name__ == '__main__':
    unittest.main()
