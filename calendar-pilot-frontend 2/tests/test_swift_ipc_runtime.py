from __future__ import annotations

import json
import os
import shutil
import unittest
from datetime import timedelta
from pathlib import Path

from calendar_pilot.swift_bridge import SwiftKernelIPCClient
from calendar_pilot.types import AtomicActionType, AtomicCalendarAction, CandidateCalendarAction, RawCalendarObservation, Reversibility


ROOT = Path(__file__).resolve().parents[1]


def load_observation() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data" / "sample_calendar.json").read_text(encoding="utf-8")))


def focus_candidate(candidate_id: str = "cand_ipc_focus") -> CandidateCalendarAction:
    observation = load_observation()
    start = observation.observed_at.replace(hour=9, minute=0, second=0, microsecond=0)
    end = observation.observed_at.replace(hour=10, minute=0, second=0, microsecond=0)
    return CandidateCalendarAction(
        candidate_id=candidate_id,
        intent="create_focus_block",
        actions=[
            AtomicCalendarAction(
                action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
                title="Focus block",
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


@unittest.skipUnless(os.environ.get("CALENDAR_PILOT_RUN_SWIFT_IPC_TESTS") == "1", "set CALENDAR_PILOT_RUN_SWIFT_IPC_TESTS=1")
@unittest.skipUnless(shutil.which("swift"), "Swift toolchain not available")
class SwiftIPCRuntimeTests(unittest.TestCase):
    def test_ipc_client_satisfies_kernel_protocol_for_planner_paths(self) -> None:
        observation = load_observation()
        candidate = focus_candidate()
        with SwiftKernelIPCClient(package_path=ROOT / "packages" / "CalendarPilotKernel") as kernel:
            grant = kernel.issue_authority_grant(
                user_scope_id=observation.user_scope_id,
                max_authority_tier=3,
                scopes=["recommend", "stage", "commit_private", "undo"],
                confirmation_provenance="ipc_integration_test",
                confirmed_by_user=True,
                issued_at=observation.observed_at,
            )

            self.assertEqual(kernel.resolve_authority_grant(grant.grant_id), grant)

            preview = kernel.preview_candidate(candidate, observation, authority_grant=grant.grant_id, requested_authority_tier=3)
            self.assertEqual(preview.executed_by, "CalendarPilotKernel.preview")
            self.assertEqual(preview.sync_status, "simulated")
            self.assertEqual(preview.provider_id, "local_swift")
            self.assertIsNone(preview.rollback_handle_id)

            staged = kernel.stage_candidate(candidate, observation, authority_grant=grant.grant_id, requested_authority_tier=3)
            self.assertEqual(staged.executed_by, "CalendarPilotKernel.stage")
            self.assertEqual(staged.sync_status, "staged")
            self.assertTrue(staged.staged_action_ids)

            committed = kernel.authorize_and_materialize(candidate, observation, authority_grant=grant.grant_id, requested_authority_tier=3)
            self.assertEqual(committed.executed_by, "CalendarPilotKernel")
            self.assertEqual(committed.sync_status, "materialized")
            self.assertEqual(committed.provider_id, "local_swift")
            self.assertIsNotNone(committed.rollback_handle_id)
            self.assertIn(committed.rollback_handle_id, kernel.undo_ledger)

            undone = kernel.request_undo(committed.rollback_handle_id or "", observation, authority_grant=grant.grant_id, requested_authority_tier=3)
            self.assertEqual(undone.executed_by, "CalendarPilotKernel.undo")
            self.assertEqual(undone.sync_status, "reverted")
            self.assertNotIn(committed.rollback_handle_id, kernel.undo_ledger)

            denied = kernel.request_undo(committed.rollback_handle_id or "", observation, authority_grant=grant.grant_id, requested_authority_tier=3)
            self.assertEqual(denied.sync_status, "denied")
            self.assertEqual(denied.denied_reason, "rollback handle not found")

    def test_expired_swift_grant_denies_before_stage(self) -> None:
        observation = load_observation()
        candidate = focus_candidate("cand_ipc_expired")
        with SwiftKernelIPCClient(package_path=ROOT / "packages" / "CalendarPilotKernel") as kernel:
            grant = kernel.issue_authority_grant(
                user_scope_id=observation.user_scope_id,
                max_authority_tier=3,
                scopes=["stage"],
                confirmation_provenance="ipc_expired_test",
                ttl_minutes=1,
                confirmed_by_user=True,
                issued_at=observation.observed_at - timedelta(minutes=10),
            )

            staged = kernel.stage_candidate(candidate, observation, authority_grant=grant.grant_id, requested_authority_tier=3)
            self.assertEqual(staged.sync_status, "denied")
            self.assertIn("expired", staged.denied_reason or "")


if __name__ == "__main__":
    unittest.main()
