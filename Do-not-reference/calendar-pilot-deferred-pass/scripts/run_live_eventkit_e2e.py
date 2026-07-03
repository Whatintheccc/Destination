
#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.codex.tools import CodexToolRuntime  # noqa: E402
from calendar_pilot.env import load_local_env  # noqa: E402
from calendar_pilot.providers.apple_eventkit import AppleEventKitProvider  # noqa: E402
from calendar_pilot.swift_bridge import SwiftKernelIPCClient  # noqa: E402
from calendar_pilot.types import (  # noqa: E402
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    Reversibility,
    RightMomentDecision,
    authority_scopes_for_tier,
)


RUN_DIR = ROOT / "runs" / "eventkit_e2e"
ARTIFACT = RUN_DIR / "eventkit_health.json"
MATERIALIZATION_ARTIFACT = RUN_DIR / "eventkit_materialization.json"


def main() -> None:
    load_local_env(ROOT / ".env")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    provider = AppleEventKitProvider(state_path=RUN_DIR / "apple_eventkit_provider.json")
    if _request_access_enabled():
        provider.request_access()
    health = provider.health_status()
    report: dict[str, Any] = {
        "provider": provider.provider_id,
        "health": health,
        "bridge": os.environ.get("CALENDAR_PILOT_EVENTKIT_BRIDGE", ""),
        "require_live": _require_live(),
        "mutation_enabled": _mutation_enabled(),
    }
    if not health.get("configured"):
        report["materialization"] = {
            "status": "blocked",
            "reason": f"EventKit permission is {health.get('status')}",
            "next_step": "Grant Calendar full access to CalendarPilotEventKitBridge, then rerun with CALENDAR_PILOT_EVENTKIT_MUTATION=1.",
        }
        write_artifact(ARTIFACT, report)
        if _require_live():
            raise SystemExit(f"EventKit live provider is not configured: {health}")
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if not _mutation_enabled():
        report["materialization"] = {
            "status": "skipped",
            "reason": "set CALENDAR_PILOT_EVENTKIT_MUTATION=1 or CALENDAR_PILOT_REQUIRE_EVENTKIT=1 to run the write/rollback probe",
        }
        write_artifact(ARTIFACT, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    materialization = run_materialization_probe(provider)
    report["materialization"] = materialization
    write_artifact(ARTIFACT, report)
    write_artifact(MATERIALIZATION_ARTIFACT, materialization)
    print(json.dumps(report, indent=2, sort_keys=True))


def run_materialization_probe(provider: AppleEventKitProvider) -> dict[str, Any]:
    observation = provider.read_observation("apple_eventkit_user")
    candidate = eventkit_probe_candidate()
    with SwiftKernelIPCClient() as kernel:
        runtime = CodexToolRuntime(kernel=kernel, provider=provider)
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            scopes=authority_scopes_for_tier(3),
            confirmation_provenance="eventkit_e2e_write_rollback_probe",
            confirmed_by_user=True,
            issued_at=observation.observed_at,
        )
        commit = runtime.execute(
            CodexToolCall(
                tool_call_id="tool_eventkit_commit",
                tool_name=CodexToolName.REQUEST_COMMIT,
                input={"candidate": candidate.to_dict()},
                requested_authority_tier=3,
                user_visible_reason="Commit one CalendarPilot EventKit dogfood probe event.",
                authority_grant_id=grant.grant_id,
                correlation_id="eventkit_e2e_materialization",
            ),
            observation,
            observation_biography(),
        )
        swift_receipt = commit.output.get("swift_receipt", {}) if isinstance(commit.output, dict) else {}
        rollback_handle = str(swift_receipt.get("rollback_handle_id") or "")
        undo = runtime.execute(
            CodexToolCall(
                tool_call_id="tool_eventkit_undo",
                tool_name=CodexToolName.REQUEST_UNDO,
                input={"rollback_handle_id": rollback_handle},
                requested_authority_tier=3,
                user_visible_reason="Rollback the CalendarPilot EventKit dogfood probe event.",
                authority_grant_id=grant.grant_id,
                correlation_id="eventkit_e2e_materialization",
            ),
            observation,
            observation_biography(),
        )
        return {
            "status": "passed" if commit.status.value == "committed" and undo.status.value == "reverted" else "failed",
            "candidate_id": candidate.candidate_id,
            "commit": commit.to_dict(),
            "undo": undo.to_dict(),
            "replay_records": [record.envelope() for record in runtime.replay.records],
        }


def eventkit_probe_candidate() -> CandidateCalendarAction:
    start = datetime.now(timezone.utc) + timedelta(days=21)
    start = start.replace(hour=16, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=20)
    return CandidateCalendarAction(
        candidate_id="cand_eventkit_live_probe",
        intent="create_focus_block",
        actions=[
            AtomicCalendarAction(
                action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
                title="CalendarPilot Dogfood Probe",
                start=start,
                end=end,
                calendar_id="default",
                metadata={"notes": "CalendarPilot live EventKit write/rollback probe"},
            )
        ],
        target_calendars=["default"],
        affected_event_ids=[],
        affected_people_ids=[],
        reversibility=Reversibility.HIGH,
        required_authority_tier=3,
        predicted_acceptance=0.8,
        predicted_utility=0.4,
        predicted_regret=0.05,
        expected_reward=0.35,
        right_moment_decision=RightMomentDecision.SILENTLY_DRAFT,
        model_story=["Synthetic provider dogfood candidate for EventKit write/rollback verification."],
        counterfactual="Without this probe, EventKit materialization remains unverified.",
        control_notes=["eventkit_e2e_probe", "rollback_required"],
        reward_breakdown={"utility": 0.4, "regret": -0.05},
        right_moment_score=0.2,
        simulated_outcomes={"rollback_expected": 1.0},
    )


def observation_biography():
    from calendar_pilot.types import UserBiography

    return UserBiography(user_scope_id="apple_eventkit_user")


def _request_access_enabled() -> bool:
    return os.environ.get("CALENDAR_PILOT_REQUEST_EVENTKIT_ACCESS", "") in {"1", "true", "TRUE", "yes"}


def _require_live() -> bool:
    return os.environ.get("CALENDAR_PILOT_REQUIRE_EVENTKIT", "") in {"1", "true", "TRUE", "yes"}


def _mutation_enabled() -> bool:
    return _require_live() or os.environ.get("CALENDAR_PILOT_EVENTKIT_MUTATION", "") in {"1", "true", "TRUE", "yes"}


def write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
