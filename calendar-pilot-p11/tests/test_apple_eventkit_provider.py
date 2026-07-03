

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.providers import AppleEventKitProvider, CalendarProviderError
from calendar_pilot.providers.apple_eventkit import _app_bundle_for_executable, _canonical_bridge_executable
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
    to_jsonable,
)


ROOT = Path(__file__).resolve().parents[1]


def load_obs() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8")))


def load_bio() -> UserBiography:
    return UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8")))


class AppleEventKitProviderTests(unittest.TestCase):
    def test_eventkit_bridge_path_never_opens_main_app_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "CalendarPilot.app" / "Contents" / "Resources" / "app" / "bin"
            bare_bridge = bin_dir / "CalendarPilotEventKitBridge"
            app_bridge = bin_dir / "CalendarPilotEventKitBridge.app" / "Contents" / "MacOS" / "CalendarPilotEventKitBridge"
            app_bridge.parent.mkdir(parents=True)
            bare_bridge.touch()
            app_bridge.touch()

            canonical = _canonical_bridge_executable(bare_bridge)

            self.assertEqual(canonical, app_bridge)
            self.assertEqual(_app_bundle_for_executable(canonical), bin_dir / "CalendarPilotEventKitBridge.app")
            self.assertIsNone(_app_bundle_for_executable(bare_bridge))

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

            recommitted = provider.commit_candidate(candidate, receipt, obs)
            self.assertEqual(recommitted.status, "materialized")
            self.assertEqual([call[0] for call in bridge.calls].count("commit"), 2)

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

    def test_provider_expands_auto_apply_plan_before_eventkit_commit(self):
        obs = load_obs()
        start = obs.observed_at + timedelta(hours=7)
        end = start + timedelta(minutes=25)
        nested = AtomicCalendarAction(
            action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
            title="Expanded Tier 6 plan step",
            start=start,
            end=end,
            calendar_id="work",
        )
        candidate = CandidateCalendarAction(
            candidate_id="cand_eventkit_tier6_expand",
            intent="auto_apply_plan",
            actions=[
                AtomicCalendarAction(
                    action_type=AtomicActionType.AUTO_APPLY_PLAN,
                    title="Compound optimizer plan",
                    metadata={"plan_actions": json.dumps([to_jsonable(nested)])},
                )
            ],
            target_calendars=["work"],
            affected_event_ids=[],
            affected_people_ids=[],
            reversibility=Reversibility.HIGH,
            required_authority_tier=6,
        )
        receipt = make_receipt(obs, candidate)
        with tempfile.TemporaryDirectory() as td:
            bridge = FakeEventKitBridge(authorized=True)
            provider = AppleEventKitProvider(state_path=Path(td) / "apple_eventkit_state.json", bridge=bridge)

            provider.commit_candidate(candidate, receipt, obs)

            commit_payload = next(payload for command, payload in bridge.calls if command == "commit")
            self.assertEqual([row["action_type"] for row in commit_payload["actions"]], ["create_focus_block"])

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

    def test_runtime_denies_live_provider_when_provider_observation_is_not_loaded(self):
        obs = load_obs()
        candidate = create_focus_candidate(obs, "cand_runtime_fixture_observation_denied")
        provider = FakeConfiguredProvider()
        runtime = CodexToolRuntime(kernel=SwiftKernelIPCClient(), provider=provider)
        grant = runtime.kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=3, issued_at=obs.observed_at, confirmed_by_user=True)

        denied = runtime.execute(
            CodexToolCall("commit_fixture_observation_denied", CodexToolName.REQUEST_COMMIT, {"candidate": candidate.to_dict()}, 3, "commit", authority_grant_id=grant.grant_id),
            obs,
            load_bio(),
        )

        self.assertEqual(denied.status, CodexToolStatus.DENIED)
        self.assertEqual(denied.denied_reason, "provider_not_configured")
        self.assertEqual(denied.output["provider_health"]["status"], "provider_observation_not_loaded")
        self.assertFalse(provider.commit_called)

    def test_runtime_denies_when_provider_truth_cannot_be_read(self):
        obs = load_obs()
        provider_obs = RawCalendarObservation(
            observation_id="obs_apple_eventkit",
            user_scope_id=obs.user_scope_id,
            observed_at=obs.observed_at,
            time_zone_id=obs.time_zone_id,
            events=obs.events,
            tasks=obs.tasks,
            device_context=obs.device_context,
            notification_history=obs.notification_history,
            prior_actions=obs.prior_actions,
        )
        candidate = create_focus_candidate(provider_obs, "cand_runtime_truth_denied")
        provider = FakeConfiguredProvider(conflict_error=True)
        runtime = CodexToolRuntime(kernel=SwiftKernelIPCClient(), provider=provider)
        grant = runtime.kernel.issue_authority_grant(user_scope_id=provider_obs.user_scope_id, max_authority_tier=3, issued_at=provider_obs.observed_at, confirmed_by_user=True)

        denied = runtime.execute(
            CodexToolCall("commit_truth_denied", CodexToolName.REQUEST_COMMIT, {"candidate": candidate.to_dict()}, 3, "commit", authority_grant_id=grant.grant_id),
            provider_obs,
            load_bio(),
        )

        self.assertEqual(denied.status, CodexToolStatus.DENIED)
        self.assertEqual(denied.denied_reason, "provider_truth_unavailable")
        self.assertFalse(provider.commit_called)

    def test_runtime_redacts_real_provider_calendar_details_from_replay(self):
        obs = load_obs()
        provider_obs = RawCalendarObservation(
            observation_id="obs_apple_eventkit",
            user_scope_id=obs.user_scope_id,
            observed_at=obs.observed_at,
            time_zone_id=obs.time_zone_id,
            events=obs.events,
            tasks=obs.tasks,
            device_context=obs.device_context,
            notification_history=obs.notification_history,
            prior_actions=obs.prior_actions,
        )
        runtime = CodexToolRuntime(kernel=SwiftKernelIPCClient(), provider=FakeConfiguredProvider())

        week = runtime.execute(
            CodexToolCall("inspect_real_provider_week", CodexToolName.INSPECT_WEEK, {}, 1, "inspect"),
            provider_obs,
            load_bio(),
        )
        self.assertEqual(week.output["raw_events"], [])
        self.assertTrue(week.output["raw_events_redacted"])

        event = runtime.execute(
            CodexToolCall("inspect_real_provider_event", CodexToolName.INSPECT_EVENT, {"event_id": obs.events[0].event_id}, 1, "inspect"),
            provider_obs,
            load_bio(),
        )
        self.assertTrue(event.output["event"]["redacted"])
        self.assertNotIn("title", event.output["event"])
        self.assertNotIn("attendees", event.output["event"])
        self.assertNotIn("location", event.output["event"])

        replay_json = json.dumps([record.envelope() for record in runtime.replay.records])
        self.assertNotIn(obs.events[0].title, replay_json)
        self.assertNotIn(obs.events[0].location, replay_json)
        for attendee in obs.events[0].attendees:
            self.assertNotIn(attendee, replay_json)

    def test_eventkit_snapshot_redacts_private_rollback_event_payloads(self):
        obs = load_obs()
        candidate = create_focus_candidate(obs, "cand_eventkit_redaction")
        receipt = make_receipt(obs, candidate)
        with tempfile.TemporaryDirectory() as td:
            provider = AppleEventKitProvider(state_path=Path(td) / "apple_eventkit_state.json", bridge=FakeEventKitBridge(authorized=True, before_event=obs.events[0]))
            provider.commit_candidate(candidate, receipt, obs)

            snapshot = provider.snapshot()
            self.assertTrue(snapshot["recent_mutations"])
            latest = snapshot["recent_mutations"][-1]
            self.assertNotIn("before_events", latest)
            self.assertNotIn(obs.events[0].title, json.dumps(snapshot))

    def test_session_permission_request_uses_active_apple_provider(self):
        from calendar_pilot.frontend.session import DogfoodSessionState

        FakeSessionAppleProvider.status = "not_determined"
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"CALENDAR_PILOT_PROVIDER_BACKEND": "apple_eventkit"}), patch(
            "calendar_pilot.frontend.session.AppleEventKitProvider",
            FakeSessionAppleProvider,
        ):
            session = DogfoodSessionState(run_dir=Path(td))
            before = session.snapshot()["inspector"]["provider"]["permission"]
            self.assertEqual(before["status"], "not_determined")

            result = session.provider_permission_request()

            self.assertTrue(result["provider_permission"]["configured"])
            self.assertEqual(result["inspector"]["provider"]["permission"]["status"], "configured")
            self.assertEqual(result["session"]["provider_observation_error"], None)

    def test_session_does_not_restore_fixture_candidates_after_eventkit_observation_loads(self):
        from calendar_pilot.frontend.session import DogfoodSessionState

        FakeSessionAppleProvider.status = "not_determined"
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"CALENDAR_PILOT_PROVIDER_BACKEND": "apple_eventkit"}), patch(
            "calendar_pilot.frontend.session.AppleEventKitProvider",
            FakeSessionAppleProvider,
        ):
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            planned = session.create_plan("make room for focused work")
            stale_candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            self.assertIn(stale_candidate_id, session.runtime.frontier)
            session.close()

            FakeSessionAppleProvider.status = "configured"
            reloaded = DogfoodSessionState(run_dir=run_dir)
            snapshot = reloaded.snapshot()

            self.assertEqual(reloaded.observation.observation_id, "obs_apple_eventkit")
            self.assertEqual(reloaded.runtime.frontier, {})
            self.assertEqual(snapshot["chat"]["candidate_cards"], [])
            self.assertIn("Plan needs refresh", [event.get("title") for event in reloaded.transcript_events])
            reloaded.close()

    def test_session_clears_stale_provider_observation_error_after_eventkit_loads(self):
        from calendar_pilot.frontend.session import DogfoodSessionState

        FakeSessionAppleProvider.status = "not_determined"
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "CALENDAR_PILOT_RUNTIME_MODE": "live_provider",
            "CALENDAR_PILOT_PROVIDER_BACKEND": "apple_eventkit",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
        }), patch(
            "calendar_pilot.frontend.session.AppleEventKitProvider",
            FakeSessionAppleProvider,
        ):
            run_dir = Path(td)
            first = DogfoodSessionState(run_dir=run_dir)
            self.assertIn("live provider observation not loaded", first.provider_observation_error or "")
            first.persist()
            first.close()

            FakeSessionAppleProvider.status = "configured"
            reloaded = DogfoodSessionState(run_dir=run_dir)
            report = reloaded.runtime_report()

            self.assertTrue(report["fixture_paths"]["provider_observation_loaded"])
            self.assertFalse(report["fixture_paths"]["uses_sample_fixtures"])
            self.assertEqual(reloaded.provider_observation_error, None)
            self.assertNotIn("live provider observation not loaded: not_determined", report["live_blockers"])
            reloaded.close()


class FakeEventKitBridge:
    def __init__(self, *, authorized: bool, before_event=None) -> None:
        self.authorized = authorized
        self.before_event = before_event
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
            before_events = {}
            if self.before_event is not None:
                from calendar_pilot.types import to_jsonable

                before_events[self.before_event.event_id] = to_jsonable(self.before_event)
            return {
                "external_ids": ["apple_evt_1"],
                "created_external_ids": ["apple_evt_1"],
                "moved_external_ids": [],
                "deleted_external_ids": [],
                "before_events": before_events,
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


class FakeConfiguredProvider:
    provider_id = "apple_eventkit"
    real_provider = True
    real_oauth = False
    observation_id = "obs_apple_eventkit"

    def __init__(self, *, conflict_error: bool = False) -> None:
        self.conflict_error = conflict_error
        self.commit_called = False

    def health_status(self) -> dict:
        return {
            "provider": self.provider_id,
            "configured": True,
            "status": "configured",
            "auth_method": "eventkit_os_calendar_permission",
        }

    def conflict_truth(self, _candidate: CandidateCalendarAction) -> list[dict]:
        if self.conflict_error:
            raise CalendarProviderError("provider read failed")
        return []

    def commit_candidate(self, *_args) -> None:
        self.commit_called = True
        raise AssertionError("commit_candidate should not run in this test")


class SwiftKernelIPCClient(SwiftKernelStub):
    pass


class FakeSessionAppleProvider:
    provider_id = "apple_eventkit"
    real_provider = True
    real_oauth = False
    observation_id = "obs_apple_eventkit"
    status = "not_determined"

    def __init__(self, **_kwargs) -> None:
        pass

    def health_status(self) -> dict:
        configured = type(self).status == "configured"
        return {
            "provider": self.provider_id,
            "configured": configured,
            "status": type(self).status,
            "authorization_status": type(self).status,
            "auth_method": "eventkit_os_calendar_permission",
        }

    def request_access(self) -> dict:
        type(self).status = "configured"
        return self.health_status()

    def read_observation(self, user_scope_id: str, **_kwargs) -> RawCalendarObservation:
        obs = load_obs()
        return RawCalendarObservation(
            observation_id="obs_apple_eventkit",
            user_scope_id=user_scope_id,
            observed_at=obs.observed_at,
            time_zone_id=obs.time_zone_id,
            events=obs.events,
            tasks=obs.tasks,
            device_context=obs.device_context,
            notification_history=obs.notification_history,
            prior_actions=obs.prior_actions,
        )

    def snapshot(self) -> dict:
        return {
            "provider": self.provider_id,
            "real_provider": True,
            "real_oauth": False,
            "permission_status": type(self).status,
            "auth_method": "eventkit_os_calendar_permission",
            "event_count": "eventkit_remote" if type(self).status == "configured" else "permission_required",
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