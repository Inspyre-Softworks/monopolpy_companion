"""Atomic two-party trade validation, security and persistence."""
import logging
import tempfile
import unittest
from monopolpy_companion import SessionRepository
from monopolpy_companion.controller import SessionController


class TradeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.controller = SessionController(SessionRepository(self.directory.name), logger=logging.getLogger('trade.test'))
        self.session = self.controller.new_session('Trades', ['Avery', 'Blake'])
        self.a, self.b = self.session.players
        self.engine = self.controller.engine
        self.engine.purchase(self.a.player_id, 1)
        self.engine.purchase(self.b.player_id, 6)

    def test_immunity_on_incoming_deed_waives_exactly_one_charge(self):
        with self.assertRaises(ValueError):
            self.engine.trade(self.a.player_id, self.b.player_id, immunity_a=(1, 'landings', 1))
        self.session.rules.allow_rent_immunity = True
        self.controller.perform('trade', self.a.player_id, self.b.player_id,
                                properties_b=[6], immunity_a=(6, 'landings', 1))
        restored = self.controller.open_session(self.session.save_path)
        engine = self.controller.engine
        tenant = restored.get_player(self.b.player_id)
        engine.move(tenant.player_id, 6)
        self.assertEqual(engine.outstanding_payments(tenant.player_id), [])
        self.assertIsNone(engine.collect_rent(tenant.player_id, 6))
        self.assertEqual(restored.rent_immunity[0]['remaining'], 0)
        tenant.position = 0
        engine.move(tenant.player_id, 6)
        self.assertEqual(engine.outstanding_payments(tenant.player_id)[0]['amount'], 6)

    def test_deed_transfer_only_carries_immunity_when_enabled(self):
        self.session.rules.allow_rent_immunity = True
        for follows in (False, True):
            with self.subTest(follows=follows):
                game = self.controller.new_session('Transfer', ['Avery', 'Blake', 'Casey'])
                owner, tenant, buyer = game.players
                game.rules.allow_rent_immunity = True
                game.rules.immunity_follows_deed = follows
                engine = self.controller.engine
                engine.purchase(owner.player_id, 1)
                engine.trade(owner.player_id, tenant.player_id, immunity_a=(1, 'landings', 1))
                engine.trade(owner.player_id, buyer.player_id, properties_a=[1])
                engine.move(tenant.player_id, 1)
                self.assertEqual(bool(engine.outstanding_payments(tenant.player_id)), not follows)

    def test_lap_and_turn_immunity_expire_on_beneficiary_progress(self):
        self.session.rules.allow_rent_immunity = True
        self.engine.trade(self.a.player_id, self.b.player_id, immunity_a=(None, 'turns', 1),
                          immunity_b=(None, 'laps', 1))
        self.a.position = 39
        self.engine.move_by_dice(self.a.player_id, 1, 2)
        self.assertEqual([grant['remaining'] for grant in self.session.rent_immunity], [1, 0])
        self.engine.advance_turn()
        self.engine.move_by_dice(self.b.player_id, 1, 2)
        self.engine.advance_turn()
        self.assertEqual([grant['remaining'] for grant in self.session.rent_immunity], [0, 0])

    def test_cash_deeds_cards_and_mortgage_interest_are_saved_together(self):
        self.a.get_out_of_jail_cards = 1
        self.engine.mortgage(self.b.player_id, 6)
        cash_a, cash_b = self.a.cash, self.b.cash
        events = []
        self.controller.subscribe(events.append)
        quote = self.controller.perform('trade', self.a.player_id, self.b.player_id,
            properties_a=[1], properties_b=[6], cash_a=100, cards_a=1)
        self.assertEqual(quote['fee_a'], 5)
        self.assertEqual(self.a.cash, cash_a - 105)
        self.assertEqual(self.b.cash, cash_b + 100)
        self.assertEqual(self.a.get_out_of_jail_cards, 0)
        self.assertEqual(self.b.get_out_of_jail_cards, 1)
        self.assertEqual(self.session.owner_for(1).player_id, self.b.player_id)
        self.assertEqual(self.session.owner_for(6).player_id, self.a.player_id)
        self.assertTrue(self.session.get_property_state(6).mortgaged)
        self.assertEqual(events[-1].name, 'trade_completed')
        restored = self.controller.repository.load(self.session.save_path)
        self.assertEqual(restored.owner_for(6).player_id, self.a.player_id)
        self.assertEqual(restored.players[0].cash, self.a.cash)
        self.assertEqual(restored.transactions[-1].kind, 'trade')
        self.assertIn('Mediterranean Avenue', restored.transactions[-1].description)

    def test_invalid_offers_are_atomic(self):
        for args in [dict(cash_a=-1), dict(cash_a=True), dict(cash_a=100000),
                     dict(properties_a=[6]), dict(properties_a=[1,1]),
                     dict(properties_a=[False]), dict(cards_a=1), {}]:
            with self.subTest(args=args):
                before = self.session.to_dict()
                with self.assertRaises((ValueError, KeyError)):
                    self.engine.trade(self.a.player_id, self.b.player_id, **args)
                self.assertEqual(self.session.to_dict(), before)
        self.b.bankrupt = True
        with self.assertRaises(ValueError):
            self.engine.trade(self.a.player_id, self.b.player_id, cash_a=10)

    def test_buildings_anywhere_in_group_block_trade(self):
        self.engine.purchase(self.a.player_id, 3)
        self.engine.buy_building(self.a.player_id, 3)
        before = self.session.to_dict()
        with self.assertRaises(ValueError):
            self.engine.trade(self.a.player_id, self.b.player_id, properties_a=[1])
        self.assertEqual(self.session.to_dict(), before)

    def test_both_player_pins_are_required(self):
        self.controller.set_player_pin(self.a.player_id, '1234')
        self.controller.set_player_pin(self.b.player_id, '5678')
        self.assertTrue(self.controller.unlock_player(self.a.player_id, '1234'))
        before = self.session.to_dict()
        with self.assertRaises(PermissionError):
            self.controller.perform('trade', self.a.player_id, self.b.player_id, properties_a=[1])
        self.assertEqual(self.session.to_dict(), before)
        self.assertTrue(self.controller.unlock_player(self.b.player_id, '5678'))
        self.controller.perform('trade', player_a_id=self.a.player_id,
                                player_b_id=self.b.player_id, properties_a=[1])
        self.assertEqual(self.session.owner_for(1).player_id, self.b.player_id)

    def test_trade_does_not_cancel_existing_rent(self):
        self.engine.move_by_dice(self.a.player_id, 3, 3)
        debt = self.engine.outstanding_payments(self.a.player_id)
        self.engine.trade(self.a.player_id, self.b.player_id, properties_b=[6])
        self.assertEqual(self.engine.outstanding_payments(self.a.player_id), debt)
        self.assertFalse(self.engine.can_advance_turn())
        self.engine.pay_outstanding(self.a.player_id)
        self.assertTrue(self.engine.can_roll(self.a.player_id))
