"""Integration tests for the UI-neutral session controller."""

import logging
import tempfile
import unittest

from monopolpy_companion import SessionRepository
from monopolpy_companion.controller import SessionController, SessionSaveError


class SessionControllerTests(unittest.TestCase):
    """Exercise session lifecycle and event delivery without Qt."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repository = SessionRepository(self.temp_dir.name)
        self.controller = SessionController(
            repository=self.repository, logger=logging.getLogger('monopoly.test')
        )

    def test_creates_autosaves_and_reopens_session(self):
        events = []
        self.controller.subscribe(events.append)
        session = self.controller.new_session('Demo', ['Avery', 'Blake'])
        self.assertEqual(events[-1].name, 'session_changed')
        player = session.players[0]
        self.controller.perform('purchase', player.player_id, 1)
        self.assertEqual(events[-1].name, 'property_purchased')
        self.assertEqual(len(self.repository.list_sessions()), 1)
        restored = self.controller.open_session(session.save_path)
        self.assertEqual(restored.owner_for(1).player_id, player.player_id)

    def test_rejects_unknown_actions_without_mutation(self):
        session = self.controller.new_session('Demo', ['Avery', 'Blake'])
        before = session.to_dict()
        with self.assertRaises(ValueError):
            self.controller.perform('__getattribute__', 'session')
        self.assertEqual(session.to_dict(), before)

    def test_controller_events_arrive_after_save(self):
        session = self.controller.new_session('Demo', ['Avery', 'Blake'])
        observations = []

        def observer(event):
            loaded = self.repository.load(session.save_path)
            observations.append((event.name, loaded.players[0].cash))

        self.controller.subscribe(observer)
        self.controller.perform('transfer', 25, to_player_id=session.players[0].player_id)
        self.assertEqual(observations[-1], ('cash_transferred', 1525))

    def test_observer_failure_cannot_abort_successful_game_action(self):
        self.controller.new_session('Demo', ['Avery', 'Blake'])

        def broken(_event):
            raise RuntimeError('Subscriber failure')

        self.controller.subscribe(broken)
        self.controller.perform('advance_turn')
        self.assertEqual(self.controller.session.current_turn_index, 1)


if __name__ == '__main__':
    unittest.main()
