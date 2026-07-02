
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.providers import DeterministicCalendarProvider
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    CodexToolStatus,
    RawCalendarObservation,
    Reversibility,
    UserBiography,
)


ROOT = Path(__file__).resolve().parents[1]


def load_obs() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))


def load_bio() -> UserBiography:
    return UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))


class DeterministicProviderTests(unittest.TestCase):
    def test_commit_writes_external_id_idempotently_and_undo_verifies_rollback(self):
        obs = load_obs()
        with tempfile.TemporaryDirectory() as td:
            provider = DeterministicCalendarProvider(state_path=Path(td) / "provider_state.json", seed_observation=obs)
            runtime = CodexToolRuntime(kernel=SwiftKernelStub(), provider=provider)
            grant = runtime.kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=3, issued_at=obs.observed_at, confirmed_by_user=True)
            candidate = create_focus_candidate(obs, "cand_provider_create")

            committed = runtime.execute(
                CodexToolCall("commit_provider", CodexToolName.REQUEST_COMMIT, {"candidate": candidate.to_dict()}, 3, "commit", authority_grant_id=grant.grant_id),
                obs,
                load_bio(),
            )

            self.assertEqual(committed.status, CodexToolStatus.COMMITTED)
            provider_receipt = committed.output["provider_receipt"]
            self.assertEqual(provider_receipt["provider_id"], "deterministic_fixture_provider")
            self.assertEqual(provider_receipt["status"], "materialized")
            self.assertTrue(provider_receipt["idempotency_key"].startswith("idem_"))
            self.assertEqual(len(provider_receipt["created_external_ids"]), 1)
            external_id = provider_receipt["created_external_ids"][0]
            self.assertTrue(external_id.startswith("det_evt_"))
            self.assertEqual(committed.output["swift_receipt"]["provider_id"], "deterministic_fixture_provider")
            self.assertIn(external_id, committed.output["swift_receipt"]["generated_event_ids"])

            replayed = runtime.execute(
                CodexToolCall("commit_provider_again", CodexToolName.REQUEST_COMMIT, {"candidate": candidate.to_dict()}, 3, "commit", authority_grant_id=grant.grant_id),
                obs,
                load_bio(),
            )
            self.assertEqual(replayed.status, CodexToolStatus.COMMITTED)
            self.assertEqual(replayed.output["provider_receipt"]["status"], "idempotent_replay")
            self.assertEqual(provider.snapshot()["event_count"], len(obs.events) + 1)

            undo = runtime.execute(
                CodexToolCall("undo_provider", CodexToolName.REQUEST_UNDO, {"rollback_handle_id": committed.output["swift_receipt"]["rollback_handle_id"]}, 3, "undo", authority_grant_id=grant.grant_id),
                obs,
                load_bio(),
            )

            self.assertEqual(undo.status, CodexToolStatus.COMMITTED)
            self.assertTrue(undo.output["provider_rollback"]["rollback_verified"])
            self.assertEqual(provider.snapshot()["event_count"], len(obs.events))
            reloaded = DeterministicCalendarProvider(state_path=Path(td) / "provider_state.json", seed_observation=obs)
            self.assertEqual(reloaded.snapshot()["rollback_verified"], 1)

    def test_provider_conflict_truth_blocks_commit_not_visible_in_original_observation(self):
        obs = load_obs()
        with tempfile.TemporaryDirectory() as td:
            provider = DeterministicCalendarProvider(state_path=Path(td) / "provider_state.json", seed_observation=obs)
            runtime = CodexToolRuntime(kernel=SwiftKernelStub(), provider=provider)
            grant = runtime.kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=3, issued_at=obs.observed_at, confirmed_by_user=True)
            first = create_focus_candidate(obs, "cand_provider_first")
            second = create_focus_candidate(obs, "cand_provider_second")

            committed = runtime.execute(
                CodexToolCall("commit_first", CodexToolName.REQUEST_COMMIT, {"candidate": first.to_dict()}, 3, "commit", authority_grant_id=grant.grant_id),
                obs,
                load_bio(),
            )
            denied = runtime.execute(
                CodexToolCall("commit_second", CodexToolName.REQUEST_COMMIT, {"candidate": second.to_dict()}, 3, "commit", authority_grant_id=grant.grant_id),
                obs,
                load_bio(),
            )

            self.assertEqual(committed.status, CodexToolStatus.COMMITTED)
            self.assertEqual(denied.status, CodexToolStatus.DENIED)
            self.assertEqual(denied.denied_reason, "provider_conflict_detected")
            self.assertTrue(denied.output["provider_conflict_truth"])
            self.assertEqual(provider.snapshot()["event_count"], len(obs.events) + 1)


def create_focus_candidate(obs: RawCalendarObservation, candidate_id: str) -> CandidateCalendarAction:
    start = obs.observed_at + timedelta(hours=4)
    end = start + timedelta(minutes=30)
    return CandidateCalendarAction(
        candidate_id=candidate_id,
        intent="create_focus_block",
        actions=[
            AtomicCalendarAction(
                action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
                title="Provider truth focus block",
                start=start,
                end=end,
                calendar_id="work",
            )
        ],
        target_calendars=["work"],
        affected_event_ids=[],
        affected_people_ids=[],
        reversibility=Reversibility.HIGH,
        required_authority_tier=3,
    )


if __name__ == "__main__":
    unittest.main()
