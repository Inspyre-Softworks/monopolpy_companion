"""Integration tests for the UI-neutral session controller."""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monopolpy_companion import SessionRepository
from monopolpy_companion.controller import SessionController, SessionSaveError


class SessionControllerTests(unittest.TestCase):
    """Exercise session lifecycle and event delivery without Qt."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.map_lock = Path(self.temp_dir.name) / 'mm.lock'
        map_path = patch.object(SessionController, '_dev_lock_path', return_value=self.map_lock)
        map_path.start()
        self.addCleanup(map_path.stop)
        self.repository = SessionRepository(self.temp_dir.name)
        self.controller = SessionController(
            repository=self.repository, logger=logging.getLogger('monopoly.test')
        )

    def test_marauders_map_restores_profile_unlock_and_persists_relock(self):
        session = self.controller.new_session('Map', ['Avery', 'Blake'])
        player = session.players[0]
        self.assertFalse(self.controller.unlock_dev_tools('Mischief managed'))
        with self.assertRaisesRegex(ValueError, 'locked'):
            self.controller.perform('dev_grant_cash', player.player_id, 500)
        self.assertTrue(self.controller.unlock_dev_tools('I solemnly swear that I am up to no good.'))
        self.assertEqual(self.map_lock.read_text(encoding='utf-8'),
                         'I solemnly swear that I am up to no good.')
        self.controller.perform('dev_grant_cash', player.player_id, 500)
        self.controller.perform('dev_grant_deed', player.player_id, 1)
        with self.assertRaisesRegex(ValueError, 'unowned'):
            self.controller.perform('dev_grant_deed', session.players[1].player_id, 1)
        self.controller.perform('dev_grant_building', player.player_id, 1)
        self.controller.perform('dev_grant_building', player.player_id, 1, hotel=True)
        reopened = SessionController(repository=self.repository)
        self.assertTrue(reopened.dev_tools_unlocked)
        restored = reopened.open_session(session.save_path)
        self.assertTrue(reopened.dev_tools_unlocked)
        reopened.lock_dev_tools()
        self.assertEqual(self.map_lock.read_text(encoding='utf-8'), 'Mischief managed!')
        self.controller.set_session(restored)
        self.assertFalse(self.controller.dev_tools_unlocked)
        self.assertEqual(restored.players[0].cash, 2000)
        self.assertEqual(restored.owner_for(1).player_id, player.player_id)
        self.assertTrue(restored.get_property_state(1).hotel)
        self.assertEqual(restored.transactions[-1].kind, 'dev_building_grant')
        self.controller.perform('sell_building', player.player_id, 1)
        self.assertEqual(restored.get_property_state(1).houses, 4)
        self.map_lock.write_text('I solemnly swear that I am up to no good.\n',
                                 encoding='utf-8')
        self.assertFalse(SessionController(repository=self.repository).dev_tools_unlocked)

    def test_invalid_map_state_is_disabled_on_startup(self):
        for contents in (b'', b'\xff', b'unexpected', b'Mischief managed!'):
            with self.subTest(contents=contents):
                self.map_lock.write_bytes(contents)
                self.assertFalse(SessionController(repository=self.repository).dev_tools_unlocked)

    def test_failed_map_replacement_preserves_previous_state_and_cleans_temp(self):
        self.controller.new_session('Map', ['Avery', 'Blake'])
        self.controller.unlock_dev_tools('I solemnly swear that I am up to no good.')
        with patch('monopolpy_companion.controller.os.replace', side_effect=OSError('denied')):
            with self.assertRaisesRegex(OSError, 'denied'):
                self.controller.lock_dev_tools()
        self.assertFalse(self.controller.dev_tools_unlocked)
        self.assertEqual(self.map_lock.read_text(encoding='utf-8'),
                         'I solemnly swear that I am up to no good.')
        self.assertEqual(list(self.map_lock.parent.glob('.mm.lock-*')), [])

    def test_go_salary_settings_save_validate_and_rollback(self):
        from unittest.mock import patch
        session = self.controller.new_session('Salary', ['Avery', 'Blake'])
        self.controller.set_go_salary(350, double_on_go=True)
        restored = self.repository.load(session.save_path)
        self.assertEqual(restored.rules.salary_on_go, 350)
        self.assertTrue(restored.rules.double_salary_on_go)
        for invalid in (-1, True, 1.5, 1000001):
            with self.assertRaises(ValueError):
                self.controller.set_go_salary(invalid)
        before = session.to_dict()
        with patch.object(self.repository, 'save', side_effect=OSError('Disk full')):
            with self.assertRaises(OSError):
                self.controller.set_go_salary(500, double_on_go=False, require_landing_to_buy=True)
        self.assertEqual(session.to_dict(), before)

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

        self.controller.perform('move_by_dice', self.controller.session.current_player.player_id, 1, 2)
        self.controller.subscribe(broken)
        self.controller.perform('advance_turn')
        self.assertEqual(self.controller.session.current_turn_index, 1)


if __name__ == '__main__':
    unittest.main()
