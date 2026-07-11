from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from calendar_pilot.frontend.session import DogfoodSessionState


class P13RestartProjectionTests(unittest.TestCase):
    def test_synthetic_acting_controls_message_has_stable_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                planned = session.create_plan("Suggest the single highest-value change; only recommend it.")
                candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
                first = session.candidate_action(candidate_id, "stage")
                second = session.snapshot()
                first_message = next(row for row in first["chat"]["messages"] if row["id"] == "msg_latest_actions")
                second_message = next(row for row in second["chat"]["messages"] if row["id"] == "msg_latest_actions")
                self.assertEqual(first_message["created_at"], second_message["created_at"])
                self.assertIsNotNone(first_message["created_at"])
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
