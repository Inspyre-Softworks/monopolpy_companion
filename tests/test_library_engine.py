"""Headless regressions for the reusable Monopoly game engine."""

from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from monopolpy_companion import GameEngine, SessionRepository, create_standard_session
from monopolpy_companion.game import GameEngine as GameEngineFromGame
from monopolpy_companion.game import SessionRepository as SessionRepositoryFromGame


class GameEngineTests(unittest.TestCase):
    """Test the banker and game rules without a desktop or logging dependency."""

    def test_package_root_exports_match_game_subpackage(self) -> None:
        self.assertIs(GameEngine, GameEngineFromGame)
        self.assertIs(SessionRepository, SessionRepositoryFromGame)

    def setUp(self) -> None:
        self.session = create_standard_session("Test", ["Taylor", "Dave"])
        self.engine = GameEngine(self.session, logger=logging.getLogger("monopolpy.tests"))
        self.taylor, self.dave = self.session.players

    def test_transfers_are_audited_and_atomic_on_insufficient_funds(self) -> None:
        events = []
        self.engine.subscribe(events.append)
        record = self.engine.transfer(
            70, from_player_id=self.taylor.player_id,
            to_player_id=self.dave.player_id,
        )
        self.assertEqual((self.taylor.cash, self.dave.cash), (1430, 1570))
        self.assertEqual(record.amount, 70)
        self.assertEqual(events[-1].name, "cash_transferred")
        ledger_length = len(self.session.transactions)
        with self.assertRaises(ValueError):
            self.engine.transfer(100_000, from_player_id=self.taylor.player_id,
                                 to_player_id=self.dave.player_id)
        self.assertEqual((self.taylor.cash, self.dave.cash), (1430, 1570))
        self.assertEqual(len(self.session.transactions), ledger_length)

    def test_no_bank_to_bank_or_self_payments(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.transfer(10)
        with self.assertRaises(ValueError):
            self.engine.transfer(10, from_player_id=self.taylor.player_id,
                                 to_player_id=self.taylor.player_id)

    def test_rent_doubles_on_unimproved_monopoly(self) -> None:
        self.engine.purchase(self.taylor.player_id, 1)
        self.assertEqual(self.engine.rent_due(1), 2)
        self.engine.purchase(self.taylor.player_id, 3)
        self.assertEqual(self.engine.rent_due(1), 4)
        transaction = self.engine.collect_rent(self.dave.player_id, 1)
        self.assertEqual(transaction.amount, 4)
        self.assertEqual(self.dave.cash, 1496)

    def test_railroad_and_utility_rents(self) -> None:
        self.engine.purchase(self.taylor.player_id, 5)
        self.assertEqual(self.engine.rent_due(5), 25)
        self.engine.purchase(self.taylor.player_id, 15)
        self.assertEqual(self.engine.rent_due(5), 50)
        self.engine.purchase(self.dave.player_id, 12)
        self.assertEqual(self.engine.rent_due(12, dice_total=7), 28)
        self.engine.purchase(self.dave.player_id, 28)
        self.assertEqual(self.engine.rent_due(12, dice_total=7), 70)

    def test_mortgage_and_unmortgage(self) -> None:
        self.engine.purchase(self.taylor.player_id, 1)
        self.engine.mortgage(self.taylor.player_id, 1)
        self.assertEqual(self.engine.rent_due(1), 0)
        self.engine.unmortgage(self.taylor.player_id, 1)
        self.assertEqual(self.engine.rent_due(1), 2)

    def test_build_evenly_and_enforce_mortgage_restrictions(self) -> None:
        self.engine.purchase(self.taylor.player_id, 1)
        self.engine.purchase(self.taylor.player_id, 3)
        self.engine.buy_building(self.taylor.player_id, 1)
        self.assertEqual(self.engine.rent_due(1), 10)
        with self.assertRaises(ValueError):
            self.engine.buy_building(self.taylor.player_id, 1)
        with self.assertRaises(ValueError):
            self.engine.mortgage(self.taylor.player_id, 3)
        self.engine.buy_building(self.taylor.player_id, 3)
        self.engine.sell_building(self.taylor.player_id, 1)
        self.engine.sell_building(self.taylor.player_id, 3)
        self.engine.mortgage(self.taylor.player_id, 3)

    def test_passing_go_and_jail(self) -> None:
        self.taylor.position = 38
        result = self.engine.move_by_dice(self.taylor.player_id, 1, 2)
        self.assertEqual(result.final_position, 1)
        self.assertTrue(result.passed_go)
        self.assertEqual(self.taylor.cash, 1700)
        self.taylor.position = 27
        result = self.engine.move(self.taylor.player_id, 3)
        self.assertEqual(result.landed_on.index, 30)
        self.assertEqual(result.final_position, 10)
        self.assertTrue(self.taylor.in_jail)
        self.engine.release_from_jail(self.taylor.player_id)
        self.assertFalse(self.taylor.in_jail)
        self.assertEqual(self.taylor.cash, 1650)

    def test_failed_observer_does_not_corrupt_state(self) -> None:
        def broken(_event):
            raise RuntimeError("Observer failed")

        self.engine.subscribe(broken)
        self.engine.purchase(self.taylor.player_id, 1)
        self.assertEqual(self.session.owner_for(1).player_id, self.taylor.player_id)

    def test_advance_skips_bankrupt(self) -> None:
        self.dave.bankrupt = True
        self.assertIs(self.engine.advance_turn(), self.taylor)

    def test_atomic_repository_round_trip_and_legacy_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SessionRepository(directory)
            self.engine.purchase(self.taylor.player_id, 1)
            path = repository.save(self.session)
            original = path.read_text(encoding="utf-8")
            self.assertTrue(Path(path).exists())
            loaded = repository.load(path)
            self.assertEqual(loaded.owner_for(1).player_id, self.taylor.player_id)
            self.assertEqual(repository.list_sessions()[0].display_name, "Test")
            with self.assertRaises(AttributeError):
                repository.save(object(), path)
            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
