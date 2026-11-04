"""Offscreen Qt smoke tests that require the optional PySide6 extra."""

import logging
import os
import tempfile
import unittest

try:
    from PySide6.QtWidgets import QApplication
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

    def test_actions_disabled_without_game(self):
        self.assertFalse(self.window.save_action.isEnabled())
        self.assertFalse(self.window.next_action.isEnabled())
        self.assertEqual(self.window.board_table.rowCount(), 0)

    def test_theme_toggle_changes_label(self):
        self.window._toggle_theme()
        self.assertEqual(self.window.theme_action.text(), 'Dark theme')


if __name__ == '__main__':
    unittest.main()
