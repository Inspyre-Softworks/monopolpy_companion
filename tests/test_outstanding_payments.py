"""Landing debts must be settled before the next turn."""
import tempfile
import unittest
from monopolpy_companion import GameEngine, SessionRepository, create_standard_session


class OutstandingPaymentTests(unittest.TestCase):
    def setUp(self):
        self.session = create_standard_session('Payments', ['Avery', 'Blake'])
        self.engine = GameEngine(self.session)
        self.player, self.owner = self.session.players

    def test_tax_blocks_next_turn_and_can_be_paid_only_once(self):
        self.player.position = 1
        self.engine.move_by_dice(self.player.player_id, 1, 2)
        self.assertFalse(self.engine.can_advance_turn())
        with self.assertRaises(ValueError):
            self.engine.advance_turn()
        self.assertEqual(self.engine.outstanding_payments(self.player.player_id)[0]['amount'], 200)
        self.engine.pay_tax(self.player.player_id, 4)
        self.assertEqual(self.player.cash, 1300)
        self.assertTrue(self.engine.can_advance_turn())
        self.assertIsNone(self.engine.pay_tax(self.player.player_id, 4))
        self.assertEqual(self.player.cash, 1300)
        with self.assertRaises(ValueError):
            self.engine.pay_outstanding(self.player.player_id)

    def test_rent_quote_is_preserved_and_insufficient_funds_keep_debt(self):
        self.engine.purchase(self.owner.player_id, 3)
        self.engine.move_by_dice(self.player.player_id, 1, 2)
        debt = self.engine.outstanding_payments(self.player.player_id)[0]
        self.assertEqual(debt['amount'], 4)
        self.player.cash = 3
        before = self.session.to_dict()
        with self.assertRaises(ValueError):
            self.engine.collect_rent(self.player.player_id, 3)
        self.assertEqual(self.session.to_dict(), before)
        self.engine.transfer(10, to_player_id=self.player.player_id)
        self.assertFalse(self.engine.can_advance_turn())
        self.engine.mortgage(self.owner.player_id, 3)
        before = self.owner.cash
        self.engine.pay_outstanding(self.player.player_id)
        self.assertEqual(self.owner.cash, before + 4)
        self.assertTrue(self.engine.can_advance_turn())
        self.assertIsNone(self.engine.collect_rent(self.player.player_id, 3))

    def test_utility_uses_landing_roll_and_debt_survives_reopen(self):
        self.engine.purchase(self.owner.player_id, 12)
        self.player.position = 9
        self.engine.move_by_dice(self.player.player_id, 1, 2)
        with tempfile.TemporaryDirectory() as directory:
            repo = SessionRepository(directory)
            engine = GameEngine(repo.load(repo.save(self.session)))
        self.assertFalse(engine.can_advance_turn())
        # A different input total cannot change the saved landing quote.
        record = engine.collect_rent(self.player.player_id, 12, dice_total=12)
        self.assertEqual(record.amount, 12)
        self.assertTrue(engine.can_advance_turn())

    def test_non_dice_utility_movement_waits_for_supplied_dice_total(self):
        self.engine.purchase(self.owner.player_id, 12)
        self.player.position = 9
        self.engine.move(self.player.player_id, 3)
        payment = self.engine.outstanding_payments(self.player.player_id)[0]
        self.assertIsNone(payment['amount'])
        record = self.engine.collect_rent(self.player.player_id, 12, dice_total=7)
        self.assertEqual(record.amount, 28)

    def test_unowned_own_and_mortgaged_deeds_do_not_block_turn(self):
        for owner, mortgaged in [(None, False), (self.player.player_id, False),
                                  (self.owner.player_id, True)]:
            with self.subTest(owner=owner, mortgaged=mortgaged):
                state = self.session.get_property_state(3)
                state.owner_id = owner
                state.mortgaged = mortgaged
                self.session.turn_roll_indices.clear()
                self.player.position = 0
                self.engine.move_by_dice(self.player.player_id, 1, 2)
                self.assertTrue(self.engine.can_advance_turn())
                self.assertEqual(self.engine.outstanding_payments(self.player.player_id), [])

    def test_unpaid_rent_blocks_extra_roll_earned_by_doubles(self):
        self.engine.purchase(self.owner.player_id, 6)
        self.player.position = 2
        self.engine.move_by_dice(self.player.player_id, 2, 2)
        self.assertFalse(self.engine.can_roll(self.player.player_id))
        self.assertFalse(self.engine.can_advance_turn())
        self.engine.pay_outstanding(self.player.player_id)
        self.assertTrue(self.engine.can_roll(self.player.player_id))
        self.assertFalse(self.engine.can_advance_turn())

    def test_each_new_landing_creates_a_new_charge(self):
        self.player.position = 1
        self.engine.move_by_dice(self.player.player_id, 1, 2)
        self.engine.pay_outstanding(self.player.player_id)
        self.engine.advance_turn()
        self.engine.move_by_dice(self.owner.player_id, 1, 2)
        self.engine.advance_turn()
        self.player.position = 1
        self.engine.move_by_dice(self.player.player_id, 1, 2)
        self.assertFalse(self.engine.can_advance_turn())
        self.engine.pay_outstanding(self.player.player_id)
        self.assertEqual(self.player.cash, 1100)
