
#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.codex.tools import CodexToolRuntime  # noqa: E402
from calendar_pilot.effect_kernel import (  # noqa: E402
    EVENTKIT_AUTHORITY_PROFILE,
    EffectAttempt,
    EventKitSandboxAdapter,
    SandboxAuthorityGate,
    SandboxEffectGateway,
    SandboxEffectLedger,
)
from calendar_pilot.env import load_local_env  # noqa: E402
from calendar_pilot.product_core import AdmissionPreview, PrepBlockProjection  # noqa: E402
from calendar_pilot.providers.apple_eventkit import AppleEventKitProvider  # noqa: E402
from calendar_pilot.swift_bridge import SwiftKernelIPCClient  # noqa: E402
from calendar_pilot.types import (  # noqa: E402
    AtomicActionType,
    AtomicCalendarAction,
    ActuationMode,
    CalendarActionReceipt,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    Reversibility,
    RightMomentDecision,
    StageState,
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
        materialization = {
            "status": "blocked",
            "reason": f"EventKit permission is {health.get('status')}",
            "next_step": "Grant Calendar full access to CalendarPilotEventKitBridge, then rerun with CALENDAR_PILOT_EVENTKIT_MUTATION=1.",
        }
        report["materialization"] = materialization
        write_artifact(ARTIFACT, report)
        write_artifact(MATERIALIZATION_ARTIFACT, materialization)
        if _require_live():
            raise SystemExit(f"EventKit live provider is not configured: {health}")
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if not _mutation_enabled():
        materialization = {
            "status": "skipped",
            "reason": "set CALENDAR_PILOT_EVENTKIT_MUTATION=1 or CALENDAR_PILOT_REQUIRE_EVENTKIT=1 to run the write/rollback probe",
        }
        report["materialization"] = materialization
        write_artifact(ARTIFACT, report)
        write_artifact(MATERIALIZATION_ARTIFACT, materialization)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    materialization = (
        run_p13_eventkit_sandbox_probe(provider)
        if _p13_eventkit_sandbox_enabled()
        else run_materialization_probe(provider)
    )
    report["materialization"] = materialization
    write_artifact(ARTIFACT, report)
    write_artifact(MATERIALIZATION_ARTIFACT, materialization)
    print(json.dumps(report, indent=2, sort_keys=True))


class AppleEventKitSandboxDriver:
    provider_id = "apple_eventkit"

    def __init__(self, provider: AppleEventKitProvider, *, sandbox_calendar_id: str):
        self.provider = provider
        self.sandbox_calendar_id = sandbox_calendar_id
        health = provider.health_status()
        self.permission_status = "full_access" if health.get("configured") else str(health.get("status", "unknown"))
        self.handles: dict[str, str] = {}
        self.external_ids: dict[str, str] = {}

    def snapshot(self, calendar_id: str) -> dict[str, Any]:
        if calendar_id != self.sandbox_calendar_id:
            raise ValueError("EventKit driver rejected an unbound calendar")
        observation = self.provider.read_observation("apple_eventkit_user")
        by_id = {event.event_id: event for event in observation.events if event.calendar_id == calendar_id}
        events: dict[str, Any] = {}
        for idempotency_key, external_id in sorted(self.external_ids.items()):
            event = by_id.get(external_id)
            if event is not None:
                events[idempotency_key] = {
                    "external_id": event.event_id,
                    "title": event.title,
                    "start": event.start.isoformat(),
                    "end": event.end.isoformat(),
                    "calendar_id": event.calendar_id,
                    "notes": event.notes,
                }
        return {"calendar_id": calendar_id, "events": events}

    def create(self, *, calendar_id: str, idempotency_key: str, projection: dict[str, Any]) -> str:
        if calendar_id != self.sandbox_calendar_id:
            raise ValueError("EventKit driver rejected an unbound calendar")
        existing = self.external_ids.get(idempotency_key)
        if existing:
            return existing
        candidate = CandidateCalendarAction(
            candidate_id=f"p13.4:{idempotency_key}",
            intent="create_prep_block",
            actions=[AtomicCalendarAction(
                action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
                title=str(projection["title"]),
                start=datetime.fromisoformat(str(projection["start"]).replace("Z", "+00:00")),
                end=datetime.fromisoformat(str(projection["end"]).replace("Z", "+00:00")),
                calendar_id=calendar_id,
                metadata={"notes": "CalendarPilot P13.4 owner-controlled sandbox probe"},
            )],
            target_calendars=[calendar_id],
            affected_event_ids=[],
            affected_people_ids=[],
            reversibility=Reversibility.HIGH,
            required_authority_tier=3,
            explanation=str(projection.get("explanation", "")),
            right_moment_decision=RightMomentDecision.SILENTLY_DRAFT,
            control_notes=["p13.4_eventkit_sandbox", "rollback_required"],
        )
        rollback_handle = f"rollback:{idempotency_key}"
        receipt = CalendarActionReceipt(
            receipt_id=f"receipt:{idempotency_key}",
            candidate_id=candidate.candidate_id,
            executed_at=datetime.now(timezone.utc),
            executed_by="P13.4EffectGateway",
            authority_tier_used=3,
            sync_status="pending",
            rollback_handle_id=rollback_handle,
            conflict_check_passed=True,
            provider_id="apple_eventkit",
            actuation_mode=ActuationMode.MATERIALIZED_WRITE,
            stage_state=StageState.COMMITTED,
            confirmation_provenance="p13.4_owner_controlled_eventkit_sandbox",
        )
        observation = self.provider.read_observation("apple_eventkit_user")
        result = self.provider.commit_candidate(candidate, receipt, observation)
        external_ids = list(result.created_external_ids)
        if result.status not in {"materialized", "idempotent_replay"} or len(external_ids) != 1:
            raise RuntimeError(f"EventKit sandbox create was not a single materialized effect: {result.to_dict()}")
        self.handles[idempotency_key] = rollback_handle
        self.external_ids[idempotency_key] = external_ids[0]
        return external_ids[0]

    def remove(self, *, calendar_id: str, idempotency_key: str, external_id: str) -> bool:
        if calendar_id != self.sandbox_calendar_id or self.external_ids.get(idempotency_key) != external_id:
            return False
        handle = self.handles.get(idempotency_key, "")
        result = self.provider.rollback(handle)
        if result.rollback_verified:
            self.handles.pop(idempotency_key, None)
            self.external_ids.pop(idempotency_key, None)
            return True
        return False


def run_p13_eventkit_sandbox_probe(provider: AppleEventKitProvider) -> dict[str, Any]:
    sandbox_calendar_id = (
        os.environ.get("CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID")
        or os.environ.get("CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID")
        or ""
    )
    if not sandbox_calendar_id or sandbox_calendar_id == "default":
        return {"status": "blocked", "reason": "P13.4 requires an exact non-default EventKit sandbox calendar id"}
    bridge_path = Path(os.environ.get("CALENDAR_PILOT_EVENTKIT_BRIDGE", "")).resolve()
    app_path = _calendar_pilot_app(bridge_path)
    if app_path is None or not bridge_path.is_file():
        return {"status": "blocked", "reason": "P13.4 requires the canonical bridge inside CalendarPilot.app"}
    app_identity = {"path": str(app_path), "sha256": _tree_sha256(app_path)}
    bridge_identity = {"path": str(bridge_path), "sha256": _file_sha256(bridge_path)}
    driver = AppleEventKitSandboxDriver(provider, sandbox_calendar_id=sandbox_calendar_id)
    adapter = EventKitSandboxAdapter(
        driver=driver,
        app_identity=app_identity,
        bridge_identity=bridge_identity,
        sandbox_calendar_id=sandbox_calendar_id,
        effect_budget=1,
    )
    ledger_path = RUN_DIR / "p13_eventkit_sandbox_ledger.json"
    try:
        ledger_path.unlink()
    except FileNotFoundError:
        pass
    ledger = SandboxEffectLedger(
        ledger_path,
        authority_profile=EVENTKIT_AUTHORITY_PROFILE,
        adapter=adapter,
    )
    signing_key = os.urandom(32)
    gate = SandboxAuthorityGate(ledger, signing_key=signing_key)
    gateway = SandboxEffectGateway(ledger, signing_key=signing_key, adapter=adapter)
    now = datetime.now(timezone.utc)
    grant = gate.issue_grant(
        grant_id=f"grant:p13.4:{now.strftime('%Y%m%dT%H%M%S')}",
        action_families=("create_prep_block",),
        scopes=("apply", "compensate"),
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        confirmed=True,
    )
    start = (now + timedelta(days=7)).replace(hour=16, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=20)
    rows = ("observation:p13.4:live", "proposal:p13.4:live")
    preview = AdmissionPreview(
        preview_id="preview:p13.4:live",
        candidate_id=f"candidate:p13.4:{now.strftime('%Y%m%dT%H%M%S')}",
        action_family="create_prep_block",
        status="preview",
        denial_reasons=(),
        projection=PrepBlockProjection(
            title=f"CalendarPilot P13.4 Probe {now.strftime('%Y%m%dT%H%M%S')}",
            start=start.isoformat(),
            end=end.isoformat(),
            calendar_id=sandbox_calendar_id,
            explanation="Cited owner-controlled app-bundled EventKit sandbox probe.",
            evidence_row_ids=rows,
        ),
        evidence_row_ids=rows,
    )
    before = driver.snapshot(sandbox_calendar_id)
    attempt = EffectAttempt.from_preview(
        preview,
        source_authenticated=True,
        observed_pre_state_hash=gateway.current_state_hash,
        authority_profile=EVENTKIT_AUTHORITY_PROFILE,
        target_binding=adapter.ticket_binding,
    )
    admission = gate.admit_effect(
        attempt=attempt,
        grant_id=grant.grant_id,
        grant_epoch=grant.epoch,
        nonce=f"nonce:p13.4:apply:{now.timestamp()}",
        now=now,
    )
    if admission.ticket is None:
        return {"status": "failed", "reason": list(admission.reasons), "before": before}
    applying = gateway.execute(admission.ticket, now=now, verification_mode="unknown")
    restarted_ledger = SandboxEffectLedger(
        ledger_path,
        authority_profile=EVENTKIT_AUTHORITY_PROFILE,
        adapter=adapter,
    )
    restarted = SandboxEffectGateway(restarted_ledger, signing_key=signing_key, adapter=adapter)
    applied = restarted.reconcile(admission.ticket.ticket_id, now=now + timedelta(seconds=1))
    after_apply = driver.snapshot(sandbox_calendar_id)
    compensation_admission = restarted.gate.admit_compensation(
        receipt=applied,
        grant_id=grant.grant_id,
        grant_epoch=grant.epoch,
        fresh_state_hash=restarted.current_state_hash,
        nonce=f"nonce:p13.4:compensate:{now.timestamp()}",
        now=now + timedelta(seconds=2),
    )
    if compensation_admission.ticket is None:
        return {
            "status": "failed",
            "reason": list(compensation_admission.reasons),
            "apply_phase": applied.phase,
            "cleanup_status": "manual_resolution_required",
            "before": before,
            "after_apply": after_apply,
        }
    compensated = restarted.execute(compensation_admission.ticket, now=now + timedelta(seconds=2))
    after_cleanup = driver.snapshot(sandbox_calendar_id)
    cleanup_ok = admission.ticket.idempotency_key not in after_cleanup["events"]
    status = "passed" if applying.phase == "applying_unknown" and applied.phase == "verified" and compensated.phase == "verified" and cleanup_ok else "failed"
    return {
        "status": status,
        "authority_profile": EVENTKIT_AUTHORITY_PROFILE,
        "authorizes_production": False,
        "repository_commit": _git("rev-parse", "HEAD"),
        "app_identity": app_identity,
        "bridge_identity": bridge_identity,
        "provider_id": "apple_eventkit",
        "permission_status": driver.permission_status,
        "sandbox_calendar_id": sandbox_calendar_id,
        "effect_budget": 1,
        "candidate_id": preview.candidate_id,
        "apply_ticket_sha256": admission.ticket.content_sha256 if hasattr(admission.ticket, "content_sha256") else hashlib.sha256(json.dumps(admission.ticket.to_dict(), sort_keys=True).encode()).hexdigest(),
        "apply_phase_before_reconcile": applying.phase,
        "apply_phase": applied.phase,
        "compensation_ticket_id": compensation_admission.ticket.ticket_id,
        "compensation_phase": compensated.phase,
        "cleanup_status": "verified_absent" if cleanup_ok else "manual_resolution_required",
        "before": before,
        "after_apply": after_apply,
        "after_cleanup": after_cleanup,
        "gateway": restarted.snapshot(),
    }


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
    start = datetime.now(timezone.utc) + timedelta(days=7)
    start = start.replace(hour=16, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=20)
    calendar_id = os.environ.get("CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID") or os.environ.get("CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID") or "default"
    return CandidateCalendarAction(
        candidate_id="cand_eventkit_live_probe",
        intent="create_focus_block",
        actions=[
            AtomicCalendarAction(
                action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
                title="CalendarPilot Dogfood Probe",
                start=start,
                end=end,
                calendar_id=calendar_id,
                metadata={"notes": "CalendarPilot live EventKit write/rollback probe"},
            )
        ],
        target_calendars=[calendar_id],
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


def _p13_eventkit_sandbox_enabled() -> bool:
    return os.environ.get("CALENDAR_PILOT_P13_EVENTKIT_SANDBOX", "") in {"1", "true", "TRUE", "yes"}


def _calendar_pilot_app(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if parent.name == "CalendarPilot.app":
            return parent
    return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(row for row in root.rglob("*") if row.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(_file_sha256(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


def write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
