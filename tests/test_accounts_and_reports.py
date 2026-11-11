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

    def test_overall_report_uses_account_identity_and_counts_unique_games(self):
        account = {'id': 'account-avery', 'data': {'pin_salt': '', 'pin_hash': ''}}
        first = self.controller.new_session('First', ['Avery', 'Blake'], accounts={'avery': account})
        first_id = first.players[0].player_id
        self.controller.perform('move_by_dice', first_id, 1, 1)
        self.controller.perform('move_by_dice', first_id, 2, 2)
        self.controller.perform('transfer', 20, from_player_id=first_id,
                                to_player_id=first.players[1].player_id, kind='rent', space_index=3)
        first.turn_counts[first_id] = 3
        first.winner_id = first_id
        self.controller.save()
        self.repo.save(first, self.repo.directory / 'duplicate.json')
        self.controller.new_session('Same name guest', ['Avery', 'Blake'])
        active = self.controller.new_session('Renamed account', ['Avery Jr', 'Blake'],
                                             accounts={'avery jr': account})
        active_id = active.players[0].player_id
        self.controller.perform('move_by_dice', active_id, 5, 6)
        self.controller.perform('transfer', 12, from_player_id=active_id,
                                to_player_id=active.players[1].player_id, kind='rent', space_index=3)
        current, history = self.controller.player_history(active_id)
        self.assertEqual([entry[0] for entry in history], ['First'])
        overall = StatisticsService.overall(current, [entry[2] for entry in history])
        self.assertEqual(overall.gameplay.games_played, 2)
        self.assertEqual(overall.gameplay.games_completed, 1)
        self.assertEqual(overall.gameplay.games_won, 1)
        self.assertEqual(overall.gameplay.dice_rolls, 3)
        self.assertAlmostEqual(overall.gameplay.average_dice_total, 17 / 3)
        self.assertEqual(overall.finance.rent_paid_by_property, {'Baltic Avenue': 32})
        self.assertEqual(overall.finance.average_rent_paid_per_turn, 8)
        self.assertEqual(current.finance.rent_paid, 12)

    def test_guest_history_matches_unlinked_names_case_insensitively(self):
        self.avery.bankrupt = True
        self.controller.save()
        active = self.controller.new_session('Guest again', ['AVERY', 'Casey'])
        current, history = self.controller.player_history(active.players[0].player_id)
        self.assertEqual(len(history), 1)
        overall = StatisticsService.overall(current, [history[0][2]])
        self.assertEqual(overall.gameplay.games_played, 2)
        self.assertEqual(overall.gameplay.bankruptcies, 1)

    def test_history_combines_linked_and_unlinked_saves_with_the_same_name(self):
        account = {'id': 'account-avery', 'data': {'pin_salt': '', 'pin_hash': ''}}
        other_account = {**account, 'id': 'another-avery'}
        self.controller.new_session('Other account', ['Avery', 'Blake'],
                                    accounts={'avery': other_account})
        linked = self.controller.new_session('Linked', ['AVERY', 'Blake'],
                                             accounts={'avery': account})

        current, history = self.controller.player_history(linked.players[0].player_id)
        self.assertEqual([entry[0] for entry in history], ['Accounts'])
        overall = StatisticsService.overall(current, [entry[2] for entry in history])
        self.assertEqual(overall.gameplay.games_played, 2)

        self.controller.set_session(self.session)
        _, history = self.controller.player_history(self.avery.player_id)
        self.assertIn('Linked', [entry[0] for entry in history])

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

    def test_bulk_quote_includes_proceeds_interest_and_future_payoff(self):
        for index in (1, 3, 12):
            self.controller.perform('purchase', self.avery.player_id, index)
        before = self.session.to_dict()
        quote = self.controller.engine.mortgage_quote(self.avery.player_id, [1, 3, 12], 'mortgage')
        self.assertEqual(quote.total, 135)
        self.assertEqual(quote.principal_total, 135)
        self.assertEqual(quote.interest_total, 14)
        self.assertEqual(quote.payoff_total, 149)
        self.assertEqual(self.session.to_dict(), before)
        self.controller.perform('mortgage_many', self.avery.player_id, [1, 3, 12])
        payoff = self.controller.engine.mortgage_quote(self.avery.player_id, [1, 3, 12], 'unmortgage')
        self.assertEqual(payoff.total, quote.payoff_total)
        self.assertEqual(payoff.principal_total, 135)
        self.assertEqual(payoff.interest_total, 14)

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
