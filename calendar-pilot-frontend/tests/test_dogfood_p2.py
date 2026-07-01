from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from calendar_pilot.frontend.session import DogfoodSessionState


ROOT = Path(__file__).resolve().parents[1]


class DogfoodP2Tests(unittest.TestCase):
    def make_session(self, run_dir: Path) -> DogfoodSessionState:
        return DogfoodSessionState(
            observation_path=ROOT / "data/sample_calendar.json",
            profile_path=ROOT / "data/sample_profile.json",
            run_dir=run_dir,
        )

    def test_p2_state_exposes_authority_denials_profile_replay_and_self_play_gate(self):
        with tempfile.TemporaryDirectory() as td:
            session = self.make_session(Path(td))
            authority = session.update_authority(authority_tier=3, scopes=["recommend", "stage", "undo"])
            self.assertEqual(authority["session"]["authority_scopes"], ["recommend", "stage", "undo"])

            planned = session.create_plan("Make next week less chaotic", authority_tier=3, commit=True)
            denied = [action for action in planned["snapshot"]["action_queue"] if action["status"] == "denied"]
            self.assertTrue(denied)
            self.assertIn("candidate_id", denied[0])

            explained = session.explain_denial(denied[0]["denied_reason"])
            self.assertTrue(explained["denial_history"])
            followups = explained["denial_history"][-1]["suggested_controls"]
            self.assertTrue(any(item["action"] in {"stage_instead", "narrow_scope"} for item in followups))

            candidate_id = denied[0]["candidate_id"]
            replay_by_candidate = session.replay_trace(candidate_id=candidate_id)
            self.assertGreater(len(replay_by_candidate["last_replay_query"]["traces"]), 0)
            replay_by_text = session.replay_trace(q=denied[0]["denied_reason"].split()[0])
            self.assertGreater(len(replay_by_text["last_replay_query"]["traces"]), 0)
            exported = session.export_replay(candidate_id=candidate_id)
            self.assertGreater(exported["replay_export"]["record_count"], 0)
            self.assertTrue(Path(exported["replay_export"]["path"]).exists())

            proposed = session.propose_profile_patch("evenings are fine during travel weeks")
            pending = proposed["pending_profile_patch"]
            self.assertIsNotNone(pending)
            claim = pending["repair_plan"]["candidate_claim"]
            applied = session.apply_profile_patch(claim, "evenings are fine during travel weeks", confirmed=True)
            self.assertTrue(applied["profile_patch_history"])
            self.assertTrue(any(row["claim"] == claim for row in applied["profile_claims"]))

            self_play = session.run_self_play(episodes=2)
            gate = self_play["self_play_history"][-1]["release_decision"]
            self.assertIn(gate["decision"], {"hold_autonomy", "ship_fixture_gate"})

            reloaded = self.make_session(Path(td))
            state = reloaded.state()
            self.assertEqual(state["session"]["authority_scopes"], ["recommend", "stage", "undo"])
            self.assertTrue(state["denial_history"])
            self.assertTrue(state["profile_patch_history"])
            self.assertTrue(state["self_play_history"])

    def test_reset_clears_p2_histories_and_replay_query(self):
        with tempfile.TemporaryDirectory() as td:
            session = self.make_session(Path(td))
            session.update_authority(authority_tier=3, scopes=["recommend", "stage", "undo"])
            planned = session.create_plan("Make next week less chaotic", authority_tier=3, commit=True)
            denied = next(action for action in planned["snapshot"]["action_queue"] if action["status"] == "denied")
            session.explain_denial(denied["denied_reason"])
            session.propose_profile_patch("prep blocks are too aggressive")
            session.replay_trace(q="candidate")
            session.run_self_play(episodes=1)

            reset = session.reset_fixture()
            self.assertFalse(reset["denial_history"])
            self.assertIsNone(reset["pending_profile_patch"])
            self.assertFalse(reset["self_play_history"])
            self.assertIsNone(reset["last_replay_query"])
            self.assertIsNone(reset["last_replay_export"])
            self.assertEqual(reset["replay_summary"]["records"], 0)


if __name__ == "__main__":
    unittest.main()
