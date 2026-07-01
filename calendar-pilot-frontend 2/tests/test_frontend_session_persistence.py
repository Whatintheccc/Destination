from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from calendar_pilot.frontend.session import DogfoodSessionState


class FrontendSessionPersistenceTests(unittest.TestCase):
    def test_session_reload_restores_visible_state_replay_frontier_and_undo(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            committed = session.candidate_action(candidate_id, "commit", confirmed=True)
            rollback = next(action["rollback_handle_id"] for action in committed["action_queue"] if action.get("rollback_handle_id"))
            receipt_id = next(action["receipt_id"] for action in committed["action_queue"] if action.get("rollback_handle_id") == rollback)
            session.feedback(receipt_id, "useful", reason="dogfood restart check")
            session.propose_profile_patch("I prefer planning blocks before lunch.")
            session.apply_profile_patch("planning blocks", "Prefer planning blocks before lunch.", confirmed=True)
            session.explain_denial("required authority tier exceeds Swift-issued grant")
            session.run_self_play(episodes=1)
            session.update_authority(tier=2, scopes=["recommend", "stage", "undo"], confirmed=True)

            reloaded = DogfoodSessionState(run_dir=run_dir)
            snapshot = reloaded.snapshot()

            self.assertEqual(snapshot["session"]["session_id"], session.session_id)
            self.assertTrue(snapshot["chat"]["candidate_cards"])
            self.assertGreaterEqual(snapshot["inspector"]["replay"]["summary"]["records"], 1)
            self.assertGreaterEqual(snapshot["inspector"]["replay"]["summary"]["rewards"], 1)
            self.assertTrue(snapshot["inspector"]["feedback"])
            self.assertTrue(snapshot["inspector"]["profile"]["patch_history"])
            self.assertTrue(snapshot["inspector"]["self_play"]["history"])
            self.assertTrue(snapshot["inspector"]["denials"])
            self.assertIn(rollback, reloaded.kernel.undo_ledger)
            self.assertIn(candidate_id, reloaded.runtime.frontier)

            undone = reloaded.undo(rollback)
            latest = undone["action_queue"][-1]
            self.assertEqual(latest["status"], "committed")
            self.assertEqual(latest["rollback_handle_id"], rollback)

    def test_reset_persists_clean_state_for_next_launch(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            session.candidate_action(candidate_id, "stage")
            self.assertGreater(session.replay.summarize().records, 0)

            session.reset()
            reloaded = DogfoodSessionState(run_dir=run_dir)
            snapshot = reloaded.snapshot()

            self.assertEqual(snapshot["inspector"]["replay"]["summary"]["records"], 0)
            self.assertFalse(snapshot["chat"]["candidate_cards"])
            self.assertEqual(len(reloaded.kernel.undo_ledger), 0)
            self.assertIn("Reset complete", snapshot["chat"]["messages"][0]["title"])


if __name__ == "__main__":
    unittest.main()
