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
            feedback = session.feedback(committed["receipt_id"], {"explicit_useful": True, "accepted": True})
            self.assertGreater(feedback["replay_summary"]["rewards"], 0)
            self.assertGreater(len(feedback["training_rows"]), 0)


if __name__ == "__main__":
    unittest.main()
