from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.providers import AppleEventKitProvider, CalendarProviderError
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import (
    ActuationMode,
    AtomicActionType,
    AtomicCalendarAction,
    CalendarActionReceipt,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    CodexToolStatus,
    RawCalendarObservation,
    Reversibility,
    StageState,
    UserBiography,
)


ROOT = Path(__file__).resolve().parents[1]


def load_obs() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8")))


def load_bio() -> UserBiography:
    return UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8")))


class AppleEventKitProviderTests(unittest.TestCase):
    def test_fake_bridge_commit_is_idempotent_and_rollback_is_verified(self):
        obs = load_obs()
        candidate = create_focus_candidate(obs, "cand_eventkit_create")
        receipt = make_receipt(obs, candidate)
        with tempfile.TemporaryDirectory() as td:
            bridge = FakeEventKitBridge(authorized=True)
            provider = AppleEventKitProvider(state_path=Path(td) / "apple_eventkit_state.json", bridge=bridge)

            mutation = provider.commit_candidate(candidate, receipt, obs)
            self.assertEqual(mutation.provider_id, "apple_eventkit")
            self.assertEqual(mutation.status, "materialized")
            self.assertEqual(mutation.created_external_ids, ["apple_evt_1"])
            self.assertEqual(provider.snapshot()["idempotency_keys"], 1)

            replayed = provider.commit_candidate(candidate, receipt, obs)
            self.assertEqual(replayed.status, "idempotent_replay")
            self.assertEqual([call[0] for call in bridge.calls].count("commit"), 1)

            rollback = provider.rollback("rb_eventkit_1")
            self.assertEqual(rollback.status, "rollback_verified")
            self.assertTrue(rollback.rollback_verified)
            self.assertEqual(provider.snapshot()["rollback_verified"], 1)

            reloaded = AppleEventKitProvider(state_path=Path(td) / "apple_eventkit_state.json", bridge=bridge)
            self.assertEqual(reloaded.snapshot()["idempotency_keys"], 1)

    def test_unconfigured_eventkit_provider_blocks_direct_commit(self):
        obs = load_obs()
        candidate = create_focus_candidate(obs, "cand_eventkit_denied")
        receipt = make_receipt(obs, candidate)
        with tempfile.TemporaryDirectory() as td:
            provider = AppleEventKitProvider(state_path=Path(td) / "apple_eventkit_state.json", bridge=FakeEventKitBridge(authorized=False))

            self.assertFalse(provider.health_status()["configured"])
            with self.assertRaises(CalendarProviderError):
                provider.commit_candidate(candidate, receipt, obs)

    def test_runtime_denies_live_provider_before_swift_commit_when_permission_missing(self):
        obs = load_obs()
        candidate = create_focus_candidate(obs, "cand_runtime_provider_denied")
        provider = FakeUnconfiguredProvider()
        runtime = CodexToolRuntime(kernel=SwiftKernelStub(), provider=provider)
        grant = runtime.kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=3, issued_at=obs.observed_at, confirmed_by_user=True)

        denied = runtime.execute(
            CodexToolCall("commit_eventkit_denied", CodexToolName.REQUEST_COMMIT, {"candidate": candidate.to_dict()}, 3, "commit", authority_grant_id=grant.grant_id),
            obs,
            load_bio(),
        )

        self.assertEqual(denied.status, CodexToolStatus.DENIED)
        self.assertEqual(denied.denied_reason, "provider_not_configured")
        self.assertFalse(provider.commit_called)
        self.assertEqual(runtime.kernel.undo_ledger, {})

    def test_session_permission_request_uses_active_apple_provider(self):
        from calendar_pilot.frontend.session import DogfoodSessionState

        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"CALENDAR_PILOT_PROVIDER_BACKEND": "apple_eventkit"}), patch(
            "calendar_pilot.frontend.session.AppleEventKitProvider",
            FakeSessionAppleProvider,
        ):
            session = DogfoodSessionState(run_dir=Path(td))
            before = session.snapshot()["inspector"]["provider"]["permission"]
            self.assertEqual(before["status"], "not_determined")

            result = session.provider_permission_request()

            self.assertTrue(result["provider_permission"]["configured"])
            self.assertEqual(result["state"]["inspector"]["provider"]["permission"]["status"], "configured")


class FakeEventKitBridge:
    def __init__(self, *, authorized: bool) -> None:
        self.authorized = authorized
        self.calls: list[tuple[str, dict]] = []

    def call(self, command: str, payload: dict) -> dict:
        self.calls.append((command, payload))
        if command == "status":
            return self._status()
        if command == "request_access":
            self.authorized = True
            return self._status()
        if command == "read_events":
            return {"events": []}
        if command == "commit":
            return {
                "external_ids": ["apple_evt_1"],
                "created_external_ids": ["apple_evt_1"],
                "moved_external_ids": [],
                "deleted_external_ids": [],
                "before_events": {},
            }
        if command == "rollback":
            return {"rollback_verified": True}
        raise AssertionError(f"unexpected bridge command: {command}")

    def _status(self) -> dict:
        return {
            "authorization_status": "full_access" if self.authorized else "denied",
            "authorized": self.authorized,
            "bridge": "fake_eventkit",
        }


class FakeUnconfiguredProvider:
    provider_id = "apple_eventkit"
    real_provider = True
    real_oauth = False

    def __init__(self) -> None:
        self.commit_called = False

    def health_status(self) -> dict:
        return {
            "provider": self.provider_id,
            "configured": False,
            "status": "denied",
            "auth_method": "eventkit_os_calendar_permission",
        }

    def conflict_truth(self, _candidate: CandidateCalendarAction) -> list[dict]:
        return []

    def commit_candidate(self, *_args) -> None:
        self.commit_called = True
        raise AssertionError("commit_candidate should not run without provider permission")


class FakeSessionAppleProvider:
    provider_id = "apple_eventkit"
    real_provider = True
    real_oauth = False

    def __init__(self, **_kwargs) -> None:
        self.status = "not_determined"

    def health_status(self) -> dict:
        configured = self.status == "configured"
        return {
            "provider": self.provider_id,
            "configured": configured,
            "status": self.status,
            "authorization_status": self.status,
            "auth_method": "eventkit_os_calendar_permission",
        }

    def request_access(self) -> dict:
        self.status = "configured"
        return self.health_status()

    def snapshot(self) -> dict:
        return {
            "provider": self.provider_id,
            "real_provider": True,
            "real_oauth": False,
            "permission_status": self.status,
            "auth_method": "eventkit_os_calendar_permission",
            "event_count": "eventkit_remote" if self.status == "configured" else "permission_required",
            "idempotency_keys": 0,
            "rollback_records": 0,
            "rollback_verified": 0,
            "recent_mutations": [],
            "connect_enabled": True,
        }


def create_focus_candidate(obs: RawCalendarObservation, candidate_id: str) -> CandidateCalendarAction:
    start = obs.observed_at + timedelta(hours=4)
    end = start + timedelta(minutes=30)
    return CandidateCalendarAction(
        candidate_id=candidate_id,
        intent="create_focus_block",
        actions=[
            AtomicCalendarAction(
                action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
                title="Apple Calendar focus block",
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


def make_receipt(obs: RawCalendarObservation, candidate: CandidateCalendarAction) -> CalendarActionReceipt:
    return CalendarActionReceipt(
        receipt_id="receipt_eventkit_1",
        candidate_id=candidate.candidate_id,
        executed_at=obs.observed_at,
        executed_by="SwiftKernelStub",
        authority_tier_used=3,
        sync_status="materialized",
        rollback_handle_id="rb_eventkit_1",
        conflict_check_passed=True,
        provider_id="local_stub",
        actuation_mode=ActuationMode.MATERIALIZED_WRITE,
        stage_state=StageState.COMMITTED,
    )


if __name__ == "__main__":
    unittest.main()
