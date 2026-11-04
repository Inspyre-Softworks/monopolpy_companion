"""Regression tests for account statistics and mortgage tools."""

from __future__ import annotations

import logging
import tempfile
import unittest

from monopolpy_companion import PlayerAccount, StatisticsService, SessionRepository
from monopolpy_companion.controller import SessionController


class PlayerAccountsTests(unittest.TestCase):
    """Account and finance behavior independent of Qt."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = SessionRepository(temp.name)
        self.controller = SessionController(
            repository=self.repo, logger=logging.getLogger('monopoly.tests')
        )
        self.session = self.controller.new_session('Accounts', ['Avery', 'Blake'])
        self.avery, self.blake = self.session.players

    def test_pin_is_hashed_and_authorization_is_required(self) -> None:
        self.controller.set_player_pin(self.avery.player_id, '1234')
        account = PlayerAccount(self.avery)
        self.assertTrue(account.verify_pin('1234'))
        self.assertFalse(account.verify_pin('0000'))
        self.assertNotEqual(self.avery.pin_hash, '1234')
        with self.assertRaises(PermissionError):
            self.controller.perform('purchase', self.avery.player_id, 1)
        self.assertTrue(self.controller.unlock_player(self.avery.player_id, '1234'))
        self.controller.perform('purchase', self.avery.player_id, 1)
        loaded = self.repo.load(self.session.save_path)
        self.assertTrue(PlayerAccount(loaded.players[0]).verify_pin('1234'))

    def test_ledger_statistics_by_player_and_property(self) -> None:
        self.controller.perform('purchase', self.avery.player_id, 1)
        self.controller.perform('collect_rent', self.blake.player_id, 1)
        self.controller.perform('pay_tax', self.blake.player_id, 4)
        self.controller.perform('transfer', 40, from_player_id=self.blake.player_id,
                                to_player_id=self.avery.player_id, kind='deal')
        report = StatisticsService(self.session).for_player(self.avery.player_id)
        debtor = StatisticsService(self.session).for_player(self.blake.player_id)
        self.assertEqual(report.gameplay.total_properties_purchased, 1)
        self.assertEqual(report.finance.rent_earned, 2)
        self.assertEqual(report.finance.rent_earned_by_player['Blake'], 2)
        self.assertEqual(report.finance.rent_earned_by_property['Mediterranean Avenue'], 2)
        self.assertEqual(debtor.finance.rent_paid, 2)
        self.assertEqual(debtor.finance.total_taxes_paid, 200)
        self.assertEqual(debtor.finance.total_player_deals_paid, 40)

    def test_simulator_does_not_double_count_used_roll(self) -> None:
        dice = self.controller.perform('simulate_dice', self.avery.player_id)
        self.assertTrue(all(1 <= face <= 6 for face in dice))
        self.controller.perform('move_by_dice', self.avery.player_id, *dice)
        stats = StatisticsService(self.session).for_player(self.avery.player_id).gameplay
        self.assertEqual(stats.dice_rolls, 1)
        self.assertEqual(stats.total_spaces_moved, sum(dice))
        self.assertTrue(self.session.dice_rolls[0]['used_for_move'])

    def test_bulk_mortgage_quote_and_payment(self) -> None:
        for index in (1, 3):
            self.controller.perform('purchase', self.avery.player_id, index)
        engine = self.controller.engine
        self.assertEqual(engine.mortgage_quote(self.avery.player_id, [1, 3], 'mortgage').total, 60)
        self.controller.perform('mortgage_many', self.avery.player_id, [1, 3])
        self.assertEqual(engine.mortgage_quote(self.avery.player_id, [1, 3]).total, 66)
        self.controller.perform('unmortgage_many', self.avery.player_id, [1, 3])
        self.assertFalse(self.session.property_states[1].mortgaged)

    def test_mixed_invalid_mortgage_selection_is_atomic(self) -> None:
        self.controller.perform('purchase', self.avery.player_id, 1)
        original_cash = self.avery.cash
        with self.assertRaises(ValueError):
            self.controller.perform('mortgage_many', self.avery.player_id, [1, 3])
        self.assertEqual(self.avery.cash, original_cash)
        self.assertFalse(self.session.property_states[1].mortgaged)

    def test_saved_settings_and_history(self) -> None:
        self.controller.set_landing_prompts(False)
        saved = self.repo.load(self.session.save_path)
        self.assertFalse(saved.show_landing_prompts)
        self.assertEqual(saved.turn_counts[self.avery.player_id], 1)


if __name__ == '__main__':
    unittest.main()
