from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from calendar_pilot.frontend.session import DogfoodSessionState


ACTION_FIELDS = {
    "local_date", "timezone", "start", "end", "duration_minutes", "calendar_id",
    "title", "attendees", "affected_ids", "conflicts", "reversibility", "authority_need",
}


class P13ActionProjectionVerticalTests(unittest.TestCase):
    def test_leading_card_projects_complete_action_and_timezone_proof(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                snapshot = session.create_plan("Suggest the single highest-value change; only recommend it.")
                card = snapshot["chat"]["candidate_cards"][0]
                self.assertEqual(set(card["action"]), ACTION_FIELDS)
                self.assertEqual(card["action"]["timezone"], "America/Los_Angeles")
                self.assertEqual(card["action"]["duration_minutes"], 25)
                self.assertEqual(card["action"]["attendees"], [])
                self.assertTrue(all(card["timezone_check"].values()), card["timezone_check"])
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
