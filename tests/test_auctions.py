"""Auction bidding, settlement, and saved progress."""
import tempfile
import unittest

from monopolpy_companion import SessionRepository
from monopolpy_companion.controller import SessionController


class AuctionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.controller = SessionController(SessionRepository(directory.name))
        self.session = self.controller.new_session('Auction test', ['Avery', 'Blake', 'Casey'])
        self.a, self.b, self.c = [player.player_id for player in self.session.players]
        self.controller.perform('move_by_dice', self.a, 1, 2)
        self.controller.perform('start_auction', self.a)

    def test_saved_auction_resumes_and_settles_highest_bid(self):
        self.controller.set_go_salary(200, require_landing_to_buy=True)
        self.controller.perform('bid_at_auction', self.a, 25)
        self.controller.perform('bid_at_auction', self.b, 40)
        with self.assertRaises(ValueError):
            self.controller.perform('advance_turn')
        restored = self.controller.open_session(self.session.save_path)
        self.assertEqual(self.controller.engine.auction_bidder(), self.c)
        self.controller.perform('pass_at_auction', self.c)
        self.controller.perform('pass_at_auction', self.a)
        self.assertIsNone(restored.auction)
        self.assertEqual(restored.owner_for(3).player_id, self.b)
        self.assertEqual(restored.get_player(self.b).cash, 1460)
        self.assertEqual(restored.transactions[-1].kind, 'auction_purchase')
        self.assertEqual(restored.transactions[-1].amount, 40)
        saved = self.controller.repository.load(restored.save_path)
        self.assertEqual(saved.owner_for(3).player_id, self.b)
        self.assertTrue(self.controller.engine.can_advance_turn())

    def test_bids_require_turn_higher_amount_and_available_cash(self):
        self.controller.perform('bid_at_auction', self.a, 25)
        before = self.session.auction.copy()
        for player_id, amount in ((self.c, 30), (self.b, 25), (self.b, 1501)):
            with self.assertRaises(ValueError):
                self.controller.perform('bid_at_auction', player_id, amount)
        with self.assertRaises(ValueError):
            self.controller.engine.transfer(1490, from_player_id=self.a)
        self.assertEqual(self.session.auction, before)
        self.assertEqual(self.session.get_player(self.a).cash, 1500)
        self.assertIsNone(self.session.owner_for(3))

    def test_everyone_passing_leaves_deed_unowned(self):
        for bidder in (self.a, self.b, self.c):
            self.controller.perform('pass_at_auction', bidder)
        self.assertIsNone(self.session.auction)
        self.assertIsNone(self.session.purchase_offer)
        self.assertIsNone(self.session.owner_for(3))
        self.assertTrue(self.controller.engine.can_advance_turn())
