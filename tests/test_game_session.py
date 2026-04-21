import tempfile
import unittest
from pathlib import Path

from monopolpy_companion.game.models import create_standard_session
from monopolpy_companion.game.storage import load_session, save_session


class GameSessionTests(unittest.TestCase):
    def test_create_standard_session_requires_two_players(self) -> None:
        with self.assertRaises(ValueError):
            create_standard_session("Solo", ["Only One"])

    def test_purchase_and_persistence_round_trip(self) -> None:
        session = create_standard_session("Friday Night", ["Avery", "Blake"])
        buyer = session.players[0]

        session.buy_property(buyer.player_id, 1)

        self.assertEqual(buyer.cash, 1440)
        self.assertEqual(session.owner_for(1).player_id, buyer.player_id)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = save_session(session, Path(temp_dir) / "session.json")
            loaded = load_session(path)

        self.assertEqual(loaded.name, "Friday Night")
        self.assertEqual(len(loaded.players), 2)
        self.assertEqual(loaded.owner_for(1).name, "Avery")
        self.assertEqual(loaded.players[0].cash, 1440)


if __name__ == "__main__":
    unittest.main()
