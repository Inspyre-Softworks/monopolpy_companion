"""Reusable account persistence and protection regression checks."""
import tempfile
import unittest
from pathlib import Path
from monopolpy_companion.game.accounts import AccountStore
from monopolpy_companion.controller import SessionController
from monopolpy_companion.game import SessionRepository


class LocalAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = AccountStore(Path(self.temp.name) / 'accounts')

    def test_encrypted_writes_and_cached_unlock(self):
        account = self.store.create('Taylor', 'secret password', '1234')
        source = self.store.directory / (account['id'] + '.json')
        self.assertNotIn('pin_hash', source.read_text())
        fresh = AccountStore(self.store.directory)
        entry = fresh.entries()[0]
        with self.assertRaises(PermissionError):
            fresh.unlock(entry, 'wrong')
        with self.assertRaises(PermissionError):
            fresh.write(account)
        unlocked = fresh.unlock(entry, 'secret password')
        unlocked['data']['note'] = 'protected value'
        fresh.write(unlocked)
        self.assertNotIn('protected value', source.read_text())
        self.assertEqual(fresh.unlock(fresh.entries()[0])['data']['note'], 'protected value')
        self.assertFalse(self.store.available(' tAYLOR '))
        with self.assertRaises(ValueError):
            self.store.create('TAYLOR')

    def test_account_pin_is_applied_before_first_game_save(self):
        account = self.store.create('Taylor', pin='1234')
        controller = SessionController(SessionRepository(Path(self.temp.name) / 'saves'))
        session = controller.new_session('Test', ['Taylor', 'Guest'],
                                         accounts={'taylor': account}, landing_prompts=False)
        player = session.players[0]
        self.assertFalse(controller.is_player_unlocked(player.player_id))
        self.assertTrue(controller.unlock_player(player.player_id, '1234'))
        saved = controller.repository.load(session.save_path)
        self.assertTrue(saved.players[0].pin_hash)
        self.assertFalse(saved.show_landing_prompts)

    def test_invalid_pin_creates_no_account(self):
        with self.assertRaises(ValueError):
            self.store.create('Taylor', pin='abc')
        self.assertEqual(self.store.entries(), [])
