#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
import sys

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.providers import AppleEventKitProvider
from calendar_pilot.swift_bridge import SwiftKernelIPCClient
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    RawCalendarObservation,
    Reversibility,
    UserBiography,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "live_eventkit_e2e"
ARTIFACTS = RUN_DIR / "artifacts"
APP_ROOT = ROOT / "dist" / "CalendarPilot.app" / "Contents" / "Resources" / "app"
EVENTKIT_BRIDGE = APP_ROOT / "bin" / "CalendarPilotEventKitBridge.app" / "Contents" / "MacOS" / "CalendarPilotEventKitBridge"
SWIFT_SERVER = APP_ROOT / "bin" / "CalendarPilotKernelServer"
PROBE_TITLE = "CalendarPilot live EventKit rollback probe"


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if not EVENTKIT_BRIDGE.exists():
        raise SystemExit(f"missing packaged EventKit bridge: {EVENTKIT_BRIDGE}")
    if not SWIFT_SERVER.exists():
        raise SystemExit(f"missing packaged Swift kernel server: {SWIFT_SERVER}")

    provider = AppleEventKitProvider(state_path=RUN_DIR / "apple_eventkit_provider.json", bridge_path=str(EVENTKIT_BRIDGE))
    permission = provider.request_access()
    if not permission.get("configured"):
        write_artifact({"ok": False, "permission": permission, "reason": "Apple Calendar permission not configured"})
        raise SystemExit("Apple Calendar permission is not configured")

    observation = provider.read_observation("dogfood_user")
    biography = load_bio()
    candidate = probe_candidate(observation)
    kernel = SwiftKernelIPCClient(executable_path=SWIFT_SERVER)
    kernel.start()
    try:
        runtime = CodexToolRuntime(kernel=kernel, provider=provider)
        grant = runtime.kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            scopes=["recommend", "stage", "commit_private", "undo"],
            issued_at=observation.observed_at,
            confirmed_by_user=True,
        )
        committed = runtime.execute(
            CodexToolCall("live_eventkit_commit", CodexToolName.REQUEST_COMMIT, {"candidate": candidate.to_dict()}, 3, "live EventKit rollback probe", authority_grant_id=grant.grant_id),
            observation,
            biography,
        )
        rollback_id = committed.output.get("swift_receipt", {}).get("rollback_handle_id")
        if committed.denied_reason or not rollback_id:
            write_artifact({"ok": False, "permission": permission, "commit_status": committed.status.value, "denied": committed.denied_reason})
            raise SystemExit(f"EventKit commit failed: {committed.denied_reason or 'missing rollback handle'}")
        undone = runtime.execute(
            CodexToolCall("live_eventkit_undo", CodexToolName.REQUEST_UNDO, {"rollback_handle_id": rollback_id}, 3, "undo live EventKit rollback probe", authority_grant_id=grant.grant_id),
            observation,
            biography,
        )
        if undone.denied_reason:
            write_artifact({"ok": False, "permission": permission, "commit_status": committed.status.value, "undo_status": undone.status.value, "denied": undone.denied_reason})
            raise SystemExit(f"EventKit undo failed: {undone.denied_reason}")
    finally:
        kernel.close()

    remaining = [event for event in provider.read_observation("dogfood_user").events if event.title == PROBE_TITLE]
    provider_receipt = committed.output.get("provider_receipt") or {}
    provider_rollback = undone.output.get("provider_rollback") or {}
    artifact = {
        "ok": not remaining and bool(provider_rollback.get("rollback_verified")),
        "permission_status": permission.get("status"),
        "observation_id": observation.observation_id,
        "initial_event_count": len(observation.events),
        "commit_status": committed.status.value,
        "provider_id": provider_receipt.get("provider_id"),
        "external_ids_returned": len(provider_receipt.get("external_ids", [])),
        "undo_status": undone.status.value,
        "rollback_verified": bool(provider_rollback.get("rollback_verified")),
        "remaining_probe_events": len(remaining),
    }
    write_artifact(artifact)
    if not artifact["ok"]:
        raise SystemExit("live EventKit rollback probe did not fully verify")
    print("live EventKit e2e passed")


def probe_candidate(observation: RawCalendarObservation) -> CandidateCalendarAction:
    start = observation.observed_at.replace(hour=3, minute=17, second=0, microsecond=0) + timedelta(days=13)
    if start <= observation.observed_at:
        start += timedelta(days=1)
    end = start + timedelta(minutes=10)
    return CandidateCalendarAction(
        candidate_id="cand_live_eventkit_rollback_probe",
        intent="live_eventkit_rollback_probe",
        actions=[
            AtomicCalendarAction(
                action_type=AtomicActionType.CREATE_EVENT,
                title=PROBE_TITLE,
                start=start,
                end=end,
                calendar_id="default",
                metadata={"notes": "Temporary CalendarPilot dogfood event; expected to be undone immediately."},
            )
        ],
        target_calendars=["default"],
        affected_event_ids=[],
        affected_people_ids=[],
        reversibility=Reversibility.HIGH,
        required_authority_tier=3,
    )


def load_bio() -> UserBiography:
    return UserBiography.from_dict(json.loads((ROOT / "data" / "sample_profile.json").read_text(encoding="utf-8")))


def write_artifact(payload: dict) -> None:
    (ARTIFACTS / "live_eventkit_e2e.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
