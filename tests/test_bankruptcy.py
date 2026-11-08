"""Bankruptcy eligibility, estate distribution, and game progression."""
import tempfile
import unittest

from monopolpy_companion import SessionRepository
from monopolpy_companion.controller import SessionController


class BankruptcyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.controller = SessionController(SessionRepository(directory.name))
        self.session = self.controller.new_session('Bankruptcy', ['Avery', 'Blake', 'Casey'])
        self.a, self.b, self.c = self.session.players
        self.engine = self.controller.engine

    def test_player_creditor_receives_estate_and_pays_mortgage_interest(self):
        self.engine.purchase(self.b.player_id, 39)
        self.engine.purchase(self.a.player_id, 1)
        self.engine.purchase(self.a.player_id, 3)
        self.engine.mortgage(self.a.player_id, 1)
        self.session.get_property_state(3).houses = 1
        self.session.get_property_state(39).houses = 1
        self.a.cash = 10
        self.a.get_out_of_jail_cards = 1
        self.a.position = 36
        self.engine.move_by_dice(self.a.player_id, 1, 2)
        previous_cash = self.b.cash
        self.controller.perform('declare_bankruptcy', self.a.player_id)
        self.assertTrue(self.a.bankrupt)
        self.assertEqual(self.a.cash, 0)
        self.assertEqual(self.b.cash, previous_cash + 10 + 25 - 3)
        self.assertEqual(self.b.get_out_of_jail_cards, 1)
        self.assertIs(self.session.owner_for(1), self.b)
        self.assertTrue(self.session.get_property_state(1).mortgaged)
        self.assertIs(self.session.owner_for(3), self.b)
        self.assertEqual(self.session.get_property_state(3).houses, 0)
        self.assertEqual(self.engine.outstanding_payments(self.a.player_id), [])
        self.assertIs(self.session.current_player, self.b)
        saved = self.controller.repository.load(self.session.save_path)
        self.assertTrue(saved.players[0].bankrupt)

    def test_bank_repossesses_and_queues_deeds_then_resumes_turns(self):
        for index in (1, 3):
            self.engine.purchase(self.a.player_id, index)
        self.engine.mortgage(self.a.player_id, 1)
        self.a.cash = 10
        self.a.position = 1
        self.engine.move_by_dice(self.a.player_id, 1, 2)
        self.controller.perform('declare_bankruptcy', self.a.player_id)
        self.assertFalse(self.session.get_property_state(1).mortgaged)
        self.assertEqual(self.session.auction['space_index'], 1)
        self.assertEqual(self.session.bankruptcy_auctions, [3])
        saved = self.controller.open_session(self.session.save_path)
        self.controller.perform('bid_at_auction', self.b.player_id, 40)
        self.controller.perform('pass_at_auction', self.c.player_id)
        self.assertEqual(saved.owner_for(1).player_id, self.b.player_id)
        self.assertEqual(saved.auction['space_index'], 3)
        self.controller.perform('pass_at_auction', self.b.player_id)
        self.controller.perform('pass_at_auction', self.c.player_id)
        self.assertIsNone(saved.auction)
        self.assertIsNone(saved.owner_for(3))
        self.assertEqual(saved.current_player.player_id, self.b.player_id)

    def test_can_raise_enough_cash_and_cannot_surrender(self):
        self.engine.purchase(self.a.player_id, 39)
        self.a.cash = 10
        self.a.position = 1
        self.engine.move_by_dice(self.a.player_id, 1, 2)
        with self.assertRaisesRegex(ValueError, 'cover the'):
            self.controller.perform('declare_bankruptcy', self.a.player_id)
        self.assertFalse(self.a.bankrupt)
        self.assertIs(self.session.owner_for(39), self.a)

    def test_group_liquidation_works_when_hotel_downgrades_exceed_house_supply(self):
        for index in (1, 3):
            self.engine.purchase(self.a.player_id, index)
            self.session.get_property_state(index).hotel = True
        self.a.cash = 0
        houses_to_place = 29
        for index in self.session.property_states:
            if index in (1, 3):
                continue
            state = self.session.get_property_state(index)
            state.houses = min(4, houses_to_place)
            houses_to_place -= state.houses
            if not houses_to_place:
                break
        self.a.position = 1
        self.engine.move_by_dice(self.a.player_id, 1, 2)
        with self.assertRaisesRegex(ValueError, 'Not enough houses'):
            self.engine.sell_building(self.a.player_id, 1)
        with self.assertRaisesRegex(ValueError, 'cover the'):
            self.engine.bankruptcy_quote(self.a.player_id)
        proceeds = self.controller.perform('liquidate_building_group', self.a.player_id, 1)
        self.assertEqual(proceeds, 250)
        self.assertFalse(self.session.get_property_state(1).hotel)
        self.assertFalse(self.session.get_property_state(3).hotel)
        self.engine.pay_outstanding(self.a.player_id)
        self.assertEqual(self.a.cash, 50)

    def test_final_bankruptcy_on_required_bail_declares_winner(self):
        self.c.bankrupt = True
        self.a.in_jail = True
        self.a.jail_turns = 3
        self.a.cash = 1
        self.controller.perform('declare_bankruptcy', self.a.player_id)
        self.assertEqual(self.session.winner_id, self.b.player_id)
        self.assertFalse(self.engine.can_advance_turn())
        with self.assertRaisesRegex(ValueError, 'ended'):
            self.controller.perform('simulate_dice', self.b.player_id)

    def test_final_bankruptcy_queues_inherited_mortgage_interest_before_winner(self):
        self.engine.purchase(self.b.player_id, 3)
        self.engine.purchase(self.a.player_id, 1)
        self.engine.mortgage(self.a.player_id, 1)
        self.a.cash = 0
        self.b.cash = 0
        self.c.bankrupt = True
        self.a.position = 0
        self.engine.move_by_dice(self.a.player_id, 1, 2)
        self.controller.perform('declare_bankruptcy', self.a.player_id)
        self.assertIsNone(self.session.winner_id)
        self.assertEqual(self.session.current_player.player_id, self.b.player_id)
        self.assertEqual(self.engine.outstanding_payments(self.b.player_id)[0]['kind'],
                         'mortgage_interest')
        self.assertFalse(self.engine.can_advance_turn())
        self.controller.perform('mortgage', self.b.player_id, 3)
        self.controller.perform('pay_outstanding', self.b.player_id)
        self.assertEqual(self.session.winner_id, self.b.player_id)
