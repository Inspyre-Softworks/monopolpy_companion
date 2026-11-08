"""Jail attempts, bail and mandatory turn progression."""
import tempfile
import unittest
from unittest.mock import patch
from monopolpy_companion import GameEngine, SessionRepository, create_standard_session


class JailTurnsTests(unittest.TestCase):
    def setUp(self):
        self.session = create_standard_session('Jail test', ['Avery', 'Blake'])
        self.engine = GameEngine(self.session)
        self.player, self.other = self.session.players

    def return_to_prisoner(self):
        self.engine.advance_turn()
        self.engine.move_by_dice(self.other.player_id, 1, 2)
        self.engine.advance_turn()

    def start_jail_turn(self):
        self.engine.send_to_jail(self.player.player_id)
        self.return_to_prisoner()

    def test_third_manual_double_sends_directly_to_jail_without_salary(self):
        self.engine.move_by_dice(self.player.player_id, 1, 1)
        self.engine.move_by_dice(self.player.player_id, 2, 2)
        self.player.position = 39
        before = self.player.cash
        result = self.engine.move_by_dice(self.player.player_id, 3, 3)
        self.assertTrue(self.player.in_jail)
        self.assertEqual(result.final_position, 10)
        self.assertFalse(result.passed_go)
        self.assertEqual(self.player.cash, before)
        self.assertEqual(len(self.session.dice_rolls), 3)
        self.assertEqual(len(self.session.movement_history), 2)
        self.assertTrue(self.engine.can_advance_turn())
        self.assertFalse(self.engine.can_roll(self.player.player_id))

    def test_third_simulated_double_jails_immediately_after_resume(self):
        self.engine.move_by_dice(self.player.player_id, 1, 1)
        self.engine.move_by_dice(self.player.player_id, 2, 2)
        with tempfile.TemporaryDirectory() as directory:
            repo = SessionRepository(directory)
            engine = GameEngine(repo.load(repo.save(self.session)))
        with patch('secrets.randbelow', side_effect=[2, 2]):
            self.assertEqual(engine.simulate_dice(self.player.player_id), (3, 3))
        self.assertTrue(engine.session.players[0].in_jail)
        self.assertTrue(engine.session.dice_rolls[-1]['used_for_move'])
        self.assertTrue(engine.can_advance_turn())
        with self.assertRaises(ValueError):
            engine.move_by_dice(self.player.player_id, 3, 3)

    def test_house_rule_off_allows_third_double_and_turn_reset_clears_count(self):
        self.session.rules.three_doubles_to_jail = False
        self.engine.move_by_dice(self.player.player_id, 1, 1)
        self.engine.move_by_dice(self.player.player_id, 2, 2)
        self.engine.move_by_dice(self.player.player_id, 3, 3)
        self.assertFalse(self.player.in_jail)
        self.assertEqual(self.player.position, 12)
        self.assertTrue(self.engine.can_roll(self.player.player_id))
        self.engine.move_by_dice(self.player.player_id, 1, 2)
        self.engine.advance_turn()
        self.session.rules.three_doubles_to_jail = True
        self.engine.move_by_dice(self.other.player_id, 1, 1)
        self.assertFalse(self.other.in_jail)
        self.assertTrue(self.engine.can_roll(self.other.player_id))

    def test_mandatory_roll_pending_move_and_doubles(self):
        self.assertFalse(self.engine.can_advance_turn())
        with self.assertRaises(ValueError):
            self.engine.advance_turn()
        self.engine.move_by_dice(self.player.player_id, 1, 1)
        self.assertFalse(self.engine.can_advance_turn())
        with patch('secrets.randbelow', side_effect=[0, 1]):
            self.engine.simulate_dice(self.player.player_id)
        self.assertFalse(self.engine.can_advance_turn())
        self.engine.move_by_dice(self.player.player_id, 1, 2)
        self.assertTrue(self.engine.can_advance_turn())

    def test_three_failed_attempts_require_bail_and_use_third_roll(self):
        self.start_jail_turn()
        for attempt in range(1, 4):
            self.assertFalse(self.engine.can_advance_turn())
            with patch('secrets.randbelow', side_effect=[0, 1]):
                result = self.engine.roll_for_doubles(self.player.player_id)
            self.assertEqual(self.player.jail_turns, attempt)
            self.assertFalse(self.engine.can_roll_for_doubles(self.player.player_id))
            with self.assertRaises(ValueError):
                self.engine.roll_for_doubles(self.player.player_id)
            if attempt < 3:
                self.assertTrue(self.engine.can_advance_turn())
                self.return_to_prisoner()
        self.assertTrue(result['bail_required'])
        self.assertFalse(self.engine.can_advance_turn())
        before = self.player.cash
        movement = self.engine.pay_jail_bail(self.player.player_id)
        self.assertEqual(self.player.cash, before - 50)
        self.assertFalse(self.player.in_jail)
        self.assertEqual(movement.final_position, 13)
        self.assertTrue(self.engine.can_advance_turn())
        self.assertFalse(self.engine.can_roll(self.player.player_id))

    def test_jail_doubles_release_move_without_extra_roll(self):
        self.start_jail_turn()
        with patch('secrets.randbelow', side_effect=[1, 1]):
            result = self.engine.roll_for_doubles(self.player.player_id)
        self.assertFalse(self.player.in_jail)
        self.assertEqual(result['movement'].final_position, 14)
        self.assertEqual(self.player.cash, 1500)
        self.assertTrue(self.engine.can_advance_turn())
        self.assertFalse(self.engine.can_roll(self.player.player_id))

    def test_bail_before_attempt_allows_regular_roll_and_insufficient_cash_is_atomic(self):
        self.start_jail_turn()
        self.player.cash = 49
        before = self.session.to_dict()
        with self.assertRaises(ValueError):
            self.engine.pay_jail_bail(self.player.player_id)
        self.assertEqual(self.session.to_dict(), before)
        self.player.cash = 100
        self.engine.pay_jail_bail(self.player.player_id)
        self.assertEqual(self.player.cash, 50)
        self.assertFalse(self.player.in_jail)
        self.assertTrue(self.engine.can_roll(self.player.player_id))
        self.assertFalse(self.engine.can_advance_turn())

    def test_jail_attempt_counter_and_required_bail_survive_reload(self):
        self.start_jail_turn()
        self.player.jail_turns = 2
        with patch('secrets.randbelow', side_effect=[0, 1]):
            self.engine.roll_for_doubles(self.player.player_id)
        with tempfile.TemporaryDirectory() as directory:
            repo = SessionRepository(directory)
            restored = GameEngine(repo.load(repo.save(self.session)))
        self.assertEqual(restored.session.players[0].jail_turns, 3)
        self.assertFalse(restored.can_advance_turn())
        self.assertFalse(restored.can_roll_for_doubles(self.player.player_id))
        restored.pay_jail_bail(self.player.player_id)
        self.assertEqual(restored.session.players[0].position, 13)
