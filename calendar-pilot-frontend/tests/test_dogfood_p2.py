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

            confirmed = session.confirm_candidate(candidate_id)
            self.assertTrue(any(action["status"] == "committed" for action in confirmed["snapshot"]["action_queue"]))

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
            self.assertIn("average_reward", self_play["self_play_history"][-1]["metrics"])
            self.assertIn("undo_rate", self_play["self_play_history"][-1]["metrics"])

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

    def test_reset_clears_kernel_grants_and_undo_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            session = self.make_session(Path(td))
            planned = session.create_plan("Make next week less chaotic", authority_tier=3, commit=True)
            committed = next(action for action in planned["snapshot"]["action_queue"] if action.get("rollback_handle_id"))
            self.assertTrue(planned["authority_grants"])

            reset = session.reset_fixture()
            self.assertEqual(reset["authority_grants"], [])

            stale_undo = session.undo(committed["rollback_handle_id"])
            self.assertEqual(stale_undo["undo_receipt"]["status"], "denied")
            self.assertEqual(stale_undo["undo_history"], [])

    def test_self_play_rejects_invalid_episode_count_and_holds_on_bad_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            session = self.make_session(Path(td))
            invalid = session.run_self_play(episodes=0)
            self.assertIn("self-play episodes must be at least 1", invalid["error"])
            self.assertFalse(invalid["self_play_history"])
            bad_reward = DogfoodSessionState._self_play_release_decision({"average_reward": -0.01, "undo_rate": 0.0, "failure_modes": {}})
            self.assertEqual(bad_reward["decision"], "hold_autonomy")
            high_undo = DogfoodSessionState._self_play_release_decision({"average_reward": 1.0, "undo_rate": 0.2, "failure_modes": {}})
            self.assertEqual(high_undo["decision"], "hold_autonomy")

    def test_replay_export_is_complete_and_does_not_mutate_replay(self):
        with tempfile.TemporaryDirectory() as td:
            session = self.make_session(Path(td))
            planned = session.create_plan("Make next week less chaotic", authority_tier=3, commit=True)
            grant_id = planned["authority_grants"][0]["grant_id"]
            session.run_self_play(episodes=3)
            before = session.state()["replay_summary"]["records"]

            exported = session.export_replay()
            after = session.state()["replay_summary"]["records"]
            self.assertEqual(after, before)
            self.assertEqual(exported["replay_export"]["record_count"], before)

            by_grant = session.replay_trace(authority_grant_id=grant_id)
            tool_names = [
                record["payload"].get("call", {}).get("tool_name")
                for record in by_grant["last_replay_query"]["traces"]
                if record["record_type"] == "codex_tool_call"
            ]
            self.assertIn("inspect_week", tool_names)
            self.assertIn("generate_candidate_frontier", tool_names)
            self.assertIn("compare_candidates", tool_names)

    def test_stage_scope_denial_updates_recommended_next_action(self):
        with tempfile.TemporaryDirectory() as td:
            session = self.make_session(Path(td))
            session.update_authority(authority_tier=3, scopes=["recommend"])
            planned = session.create_plan("Make next week less chaotic", authority_tier=3, commit=False)
            self.assertEqual(planned["snapshot"]["summary"]["recommended_next_action"], "stage_denied")
            self.assertTrue(any(action["status"] == "denied" for action in planned["snapshot"]["action_queue"]))


if __name__ == "__main__":
    unittest.main()
