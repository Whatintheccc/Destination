from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

from calendar_pilot.frontend.session import DogfoodSessionState


class P13NoopVerticalTests(unittest.TestCase):
    def test_bound_dominated_fixture_selects_only_noop_and_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            session.create_plan("Suggest the single highest-value change; only recommend it.")
            snapshot = session.create_plan("Use the fixture where every calendar change is dominated.")
            self.assertEqual(session.observation.observation_id, "fixture_noop_dominates")
            cards = snapshot["chat"]["candidate_cards"]
            self.assertEqual(len(cards), 1)
            self.assertEqual(cards[0]["intent"], "do_nothing")
            self.assertIn("no admissible calendar change", cards[0]["binding_constraint"])
            self.assertEqual(snapshot["action_queue"], [])
            plan_id = session.latest_plan.plan_id
            session.close()

            restored = DogfoodSessionState(run_dir=run_dir)
            try:
                self.assertEqual(restored.observation.observation_id, "fixture_noop_dominates")
                self.assertEqual(restored.latest_plan.plan_id, plan_id)
                restored_cards = restored.snapshot()["chat"]["candidate_cards"]
                self.assertEqual([card["intent"] for card in restored_cards], ["do_nothing"])
            finally:
                restored.close()

    def test_noop_fixture_is_available_with_swift_ipc_and_deterministic_provider(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"CALENDAR_PILOT_KERNEL_BACKEND": "stub"}):
            session = DogfoodSessionState(run_dir=Path(td), runtime_mode="swift_ipc")
            try:
                snapshot = session.create_plan("Use the fixture where every calendar change is dominated.")
                self.assertEqual(snapshot["chat"]["candidate_cards"][0]["intent"], "do_nothing")
                self.assertEqual(session.runtime_mode, "swift_ipc")
                self.assertEqual(session.provider.provider_id, "deterministic_fixture_provider")
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
