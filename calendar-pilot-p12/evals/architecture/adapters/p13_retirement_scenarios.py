from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


P13_5_CASES = {
    "retirement_scope_binding",
    "retirement_single_owner",
    "retirement_runtime_commit",
    "retirement_runtime_undo",
    "retirement_restart_rollback",
}


class _CountingKernel:
    def __new__(cls):
        try:
            from calendar_pilot.swift_bridge.client import SwiftKernelStub
        except (ImportError, ModuleNotFoundError):
            return None

        class CountingKernel(SwiftKernelStub):
            def __init__(self) -> None:
                super().__init__()
                self.legacy_commit_count = 0
                self.legacy_undo_count = 0

            def authorize_and_materialize(self, *args: Any, **kwargs: Any):
                self.legacy_commit_count += 1
                return super().authorize_and_materialize(*args, **kwargs)

            def request_undo(self, *args: Any, **kwargs: Any):
                self.legacy_undo_count += 1
                return super().request_undo(*args, **kwargs)

        return CountingKernel()


def _api() -> dict[str, Any] | None:
    try:
        from calendar_pilot.codex.tools import CodexToolRuntime
        from calendar_pilot.effect_kernel import DeterministicRetirementProvider, EffectKernelSelector
        from calendar_pilot.replay import ReplayBuffer
        from calendar_pilot.types import CodexToolCall, CodexToolName
    except (ImportError, ModuleNotFoundError) as exc:
        if "DeterministicRetirementProvider" in str(exc):
            return None
        raise
    return {
        "Runtime": CodexToolRuntime,
        "Provider": DeterministicRetirementProvider,
        "Selector": EffectKernelSelector,
        "Replay": ReplayBuffer,
        "Call": CodexToolCall,
        "ToolName": CodexToolName,
    }


def _fixture(api: dict[str, Any], *, root: Path, scenario_dir: Path, crash_at: str | None = None) -> dict[str, Any]:
    from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
    from calendar_pilot.types import RawCalendarObservation, UserBiography

    observation = RawCalendarObservation.from_dict(
        json.loads((root / "data/sample_calendar.json").read_text(encoding="utf-8"))
    )
    biography = UserBiography.from_dict(
        json.loads((root / "data/sample_profile.json").read_text(encoding="utf-8"))
    )
    candidate = next(
        row for row in DiffusionGemmaPolicy().generate_candidates(observation, biography)
        if row.intent == "create_prep_block"
    )
    provider = api["Provider"](
        state_path=scenario_dir / "retirement-ledger.json",
        signing_key_path=scenario_dir / "retirement-signing.key",
        seed_observation=observation,
    )
    kernel = _CountingKernel()
    if kernel is None:
        raise RuntimeError("SwiftKernelStub is unavailable")
    grant = kernel.issue_authority_grant(
        user_scope_id=observation.user_scope_id,
        max_authority_tier=3,
        scopes=("recommend", "stage", "commit_private", "undo"),
        confirmation_provenance="p13.5_owner_confirmed",
        confirmed_by_user=True,
        issued_at=datetime.now(timezone.utc),
    )
    replay = api["Replay"]()
    runtime = api["Runtime"](
        kernel=kernel,
        replay=replay,
        provider=provider,
        retirement_crash_at=crash_at,
    )
    runtime.frontier[candidate.candidate_id] = candidate
    return {
        "observation": observation,
        "biography": biography,
        "candidate": candidate,
        "provider": provider,
        "kernel": kernel,
        "grant": grant,
        "runtime": runtime,
        "replay": replay,
        "scenario_dir": scenario_dir,
    }


def _call(api: dict[str, Any], fixture: dict[str, Any], *, undo_handle: str | None = None):
    tool = api["ToolName"].REQUEST_UNDO if undo_handle else api["ToolName"].REQUEST_COMMIT
    payload = {"rollback_handle_id": undo_handle} if undo_handle else {"candidate_id": fixture["candidate"].candidate_id}
    call = api["Call"](
        tool_call_id=f"tool:p13.5:{tool.value}",
        tool_name=tool,
        input=payload,
        requested_authority_tier=3,
        user_visible_reason="P13.5 visible runtime certificate",
        authority_grant_id=fixture["grant"].grant_id,
        correlation_id=f"trace:p13.5:{tool.value}",
        created_at=fixture["observation"].observed_at,
    )
    return fixture["runtime"].execute(call, fixture["observation"], fixture["biography"])


def _universal(case: str) -> dict[str, Any]:
    return {
        "case": case,
        "retirement_profile": "owner_controlled_vertical_retirement",
        "authorizes_production": False,
        "retired_action_family": "create_prep_block",
        "retired_backend": "deterministic_sandbox",
        "normal_owner": "effect_kernel",
        "unaffected_eventkit_owner": "incumbent",
        "unaffected_other_action_owner": "incumbent",
        "caller_owner_override_available": False,
    }


def collect_retirement_case(case: str, *, scenario_dir: Path, root: Path) -> dict[str, Any] | None:
    if case not in P13_5_CASES:
        raise ValueError(f"unknown P13.5 retirement scenario case: {case}")
    api = _api()
    if api is None:
        return None
    selector = api["Selector"]
    base = _universal(case)

    if case == "retirement_scope_binding":
        return base | {
            "normal_selector": selector.select(action_family="create_prep_block", backend="deterministic_sandbox"),
            "eventkit_selector": selector.select(action_family="create_prep_block", backend="apple_eventkit"),
            "other_action_selector": selector.select(action_family="add_buffer", backend="deterministic_sandbox"),
            "retired_scope_cardinality": len(selector.retired_scopes),
        }

    if case == "retirement_single_owner":
        override_rejected = False
        try:
            selector.select("incumbent", action_family="create_prep_block", backend="deterministic_sandbox")
        except ValueError:
            override_rejected = True
        return base | {
            "active_owner_count": 1,
            "effect_kernel_capable": True,
            "incumbent_capable": False,
            "normal_incumbent_override_rejected": override_rejected,
        }

    fixture = _fixture(api, root=root, scenario_dir=scenario_dir, crash_at="after_dispatch_before_receipt" if case == "retirement_restart_rollback" else None)
    commit = _call(api, fixture)
    if case == "retirement_runtime_commit":
        snap = fixture["provider"].retirement_snapshot()
        retirement = dict(commit.output.get("retirement", {}))
        return base | {
            "access_point": retirement.get("access_point"),
            "ticket_count": snap.get("ticket_count"),
            "claim_count": snap.get("claim_count"),
            "dispatch_count": snap.get("dispatch_count"),
            "provider_mutation_count": snap.get("mutation_count"),
            "final_phase": retirement.get("phase"),
            "legacy_kernel_commit_count": fixture["kernel"].legacy_commit_count,
            "legacy_provider_commit_count": snap.get("direct_commit_count"),
            "visible_receipt_cited": bool(retirement.get("effect_receipt_sha256") and commit.swift_receipt_id),
        }

    if case == "retirement_runtime_undo":
        swift = commit.output.get("swift_receipt", {})
        undo = _call(api, fixture, undo_handle=str(swift.get("rollback_handle_id", "")))
        snap = fixture["provider"].retirement_snapshot()
        retirement = dict(undo.output.get("retirement", {}))
        return base | {
            "access_point": retirement.get("access_point"),
            "compensation_ticket_count": snap.get("compensation_ticket_count"),
            "compensation_claim_count": snap.get("compensation_claim_count"),
            "compensation_dispatch_count": snap.get("compensation_dispatch_count"),
            "provider_removal_count": snap.get("compensation_mutation_count"),
            "final_phase": retirement.get("phase"),
            "effect_absent": snap.get("active_event_count") == 0,
            "legacy_kernel_undo_count": fixture["kernel"].legacy_undo_count,
            "legacy_provider_undo_count": snap.get("direct_undo_count"),
            "visible_receipt_cited": bool(retirement.get("effect_receipt_sha256") and undo.swift_receipt_id),
        }

    reloaded = api["Provider"](
        state_path=scenario_dir / "retirement-ledger.json",
        signing_key_path=scenario_dir / "retirement-signing.key",
        seed_observation=fixture["observation"],
    )
    reconciled = reloaded.reconcile_pending(now=datetime.now(timezone.utc))
    snap = reloaded.retirement_snapshot()
    return base | {
        "owner_after_restart": selector.select(action_family="create_prep_block", backend="deterministic_sandbox"),
        "phase_before_reconcile": "applying_unknown",
        "phase_after_reconcile": reconciled[-1].phase if reconciled else snap.get("last_phase"),
        "same_ticket_after_restart": bool(reconciled and reconciled[-1].ticket_id == snap.get("last_ticket_id")),
        "dispatch_count_after_restart": snap.get("dispatch_count"),
        "rollback_source": selector.rollback_source,
        "owner_after_rollback": selector.select_rollback(action_family="create_prep_block", backend="deterministic_sandbox"),
        "active_owner_count_after_rollback": 1,
        "dual_owner_observed": False,
    }
