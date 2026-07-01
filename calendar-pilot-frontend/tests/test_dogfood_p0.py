from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.providers import FixtureCalendarProvider
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    RawCalendarObservation,
    Reversibility,
)


ROOT = Path(__file__).resolve().parents[1]


def load_obs() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))


class DogfoodP0Tests(unittest.TestCase):
    def test_fixture_provider_persists_idempotency_conflict_truth_and_rollback(self):
        obs = load_obs()
        with tempfile.TemporaryDirectory() as td:
            provider = FixtureCalendarProvider(Path(td) / "fixture.json", seed_observation=obs)
            initial = provider.checksum()
            start = obs.observed_at + timedelta(hours=4)
            candidate = CandidateCalendarAction(
                candidate_id="cand_fixture_create",
                intent="create_focus_block",
                actions=[
                    AtomicCalendarAction(
                        action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
                        title="Focus",
                        start=start,
                        end=start + timedelta(minutes=30),
                        calendar_id="work",
                    )
                ],
                target_calendars=["work"],
                affected_event_ids=[],
                affected_people_ids=[],
                reversibility=Reversibility.HIGH,
                required_authority_tier=3,
            )
            result = provider.apply_candidate(candidate, idempotency_key="commit:test", rollback_handle_id="undo_test")
            self.assertEqual(result.receipt.status, "materialized")
            self.assertNotEqual(provider.checksum(), initial)
            replay = provider.apply_candidate(candidate, idempotency_key="commit:test", rollback_handle_id="undo_test")
            self.assertTrue(replay.idempotent_replay)
            self.assertEqual(replay.external_ids, result.external_ids)
            reverted = provider.rollback("undo_test")
            self.assertEqual(reverted.receipt.status, "reverted")
            self.assertEqual(provider.checksum(), initial)
            reused = provider.rollback("undo_test")
            self.assertEqual(reused.receipt.status, "denied")

    def test_fixture_rollback_of_older_write_preserves_later_write(self):
        obs = load_obs()
        with tempfile.TemporaryDirectory() as td:
            provider = FixtureCalendarProvider(Path(td) / "fixture.json", seed_observation=obs)
            start_a = obs.observed_at + timedelta(hours=4)
            start_b = obs.observed_at + timedelta(hours=5)
            candidate_a = CandidateCalendarAction(
                candidate_id="cand_fixture_a",
                intent="create_focus_block",
                actions=[AtomicCalendarAction(AtomicActionType.CREATE_FOCUS_BLOCK, "A", start=start_a, end=start_a + timedelta(minutes=30), calendar_id="work")],
                target_calendars=["work"],
                affected_event_ids=[],
                affected_people_ids=[],
                reversibility=Reversibility.HIGH,
                required_authority_tier=3,
            )
            candidate_b = CandidateCalendarAction(
                candidate_id="cand_fixture_b",
                intent="create_focus_block",
                actions=[AtomicCalendarAction(AtomicActionType.CREATE_FOCUS_BLOCK, "B", start=start_b, end=start_b + timedelta(minutes=30), calendar_id="work")],
                target_calendars=["work"],
                affected_event_ids=[],
                affected_people_ids=[],
                reversibility=Reversibility.HIGH,
                required_authority_tier=3,
            )
            a = provider.apply_candidate(candidate_a, idempotency_key="commit:a", rollback_handle_id="undo_a")
            b = provider.apply_candidate(candidate_b, idempotency_key="commit:b", rollback_handle_id="undo_b")
            provider.rollback("undo_a")
            event_ids = {event.event_id for event in provider.read_observation(obs.user_scope_id).events}
            self.assertNotIn(a.external_ids[0], event_ids)
            self.assertIn(b.external_ids[0], event_ids)

    def test_dogfood_session_runs_commit_undo_feedback_training_loop(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(
                observation_path=ROOT / "data/sample_calendar.json",
                profile_path=ROOT / "data/sample_profile.json",
                run_dir=Path(td),
            )
            initial = session.provider.checksum()
            planned = session.create_plan("Make next week less chaotic", authority_tier=3, commit=True)
            actions = planned["snapshot"]["action_queue"]
            committed = next(action for action in actions if action["status"] == "committed" and action.get("rollback_handle_id"))
            self.assertNotEqual(session.provider.checksum(), initial)
            undone = session.undo(committed["rollback_handle_id"])
            self.assertEqual(undone["undo_receipt"]["status"], "committed")
            self.assertEqual(session.provider.checksum(), initial)
            self.assertEqual(undone["undo_history"][-1]["provider_status"], "reverted")
            self.assertGreaterEqual(undone["replay_summary"]["rewards"], 1)
            feedback = session.feedback(committed["receipt_id"], {"explicit_useful": True, "accepted": True})
            self.assertGreater(feedback["replay_summary"]["rewards"], 0)
            self.assertGreater(len(feedback["training_rows"]), 0)
            self.assertTrue(feedback["feedback_history"])

    def test_dogfood_session_can_undo_after_reload(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            first = DogfoodSessionState(
                observation_path=ROOT / "data/sample_calendar.json",
                profile_path=ROOT / "data/sample_profile.json",
                run_dir=run_dir,
            )
            initial = first.provider.checksum()
            planned = first.create_plan("Make next week less chaotic", authority_tier=3, commit=True)
            committed = next(action for action in planned["snapshot"]["action_queue"] if action.get("rollback_handle_id"))
            self.assertNotEqual(first.provider.checksum(), initial)
            second = DogfoodSessionState(
                observation_path=ROOT / "data/sample_calendar.json",
                profile_path=ROOT / "data/sample_profile.json",
                run_dir=run_dir,
            )
            undone = second.undo(committed["rollback_handle_id"])
            self.assertEqual(undone["undo_receipt"]["output"]["swift_receipt"]["sync_status"], "reverted")
            self.assertEqual(second.provider.checksum(), initial)
            self.assertEqual(undone["undo_history"][-1]["original_receipt_id"], committed["receipt_id"])

    def test_feedback_rejects_unknown_receipt_without_polluting_rewards(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(
                observation_path=ROOT / "data/sample_calendar.json",
                profile_path=ROOT / "data/sample_profile.json",
                run_dir=Path(td),
            )
            response = session.feedback("missing_receipt", {"explicit_useful": True})
            self.assertIn("unknown receipt_id", response["error"])
            self.assertEqual(response["replay_summary"]["rewards"], 0)
            self.assertEqual(response["training_rows"], [])


if __name__ == "__main__":
    unittest.main()
