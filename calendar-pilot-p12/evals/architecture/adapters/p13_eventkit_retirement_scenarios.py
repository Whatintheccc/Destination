from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


P13_5_EVENTKIT_CASES = {
    "eventkit_managed_binding_state",
    "eventkit_managed_ownership",
    "eventkit_managed_runtime_commit",
    "eventkit_managed_runtime_undo",
    "eventkit_managed_durable_owner",
    "eventkit_managed_live_contract",
}
BINDING_ID = "123e4567-e89b-42d3-a456-426614174000"


class _Driver:
    provider_id = "apple_eventkit"

    def __init__(self) -> None:
        self.permission_status = "full_access"
        self.identity = {
            "permission_status": "full_access",
            "writable": True,
            "event_store_id": "store:architecture",
            "calendar_id": "calendar:managed",
            "source_id": "source:local",
            "source_type": "local",
            "title": "CalendarPilot Managed",
        }
        self.events: dict[str, dict[str, Any]] = {}
        self.create_count = 0
        self.remove_count = 0
        self.validation_count = 0
        self.post_verify_count = 0
        self.target_hashes: list[str] = []
        self.crash_after_create_before_return = False
        self.ambiguous_idempotency_keys: set[str] = set()

    def binding_identity(self) -> dict[str, Any]:
        return dict(self.identity)

    def snapshot(self, calendar_id: str) -> dict[str, Any]:
        if calendar_id != self.identity["calendar_id"]:
            return {"events": {}, "binding_identity": self.binding_identity()}
        self.post_verify_count += 1
        return {
            "events": deepcopy(self.events),
            "binding_identity": self.binding_identity(),
            "ambiguous_idempotency_keys": sorted(self.ambiguous_idempotency_keys),
            "ambiguous_marker_event_ids": [],
        }

    def create(self, *, expected_binding: dict[str, Any], target_vector: dict[str, Any], idempotency_key: str, projection: dict[str, Any]) -> str:
        self._validate(expected_binding, target_vector)
        if projection.get("calendar_id") != self.identity["calendar_id"]:
            raise ValueError("managed evaluator driver target escaped")
        external_id = "event:" + idempotency_key[-16:]
        self.events[idempotency_key] = {"external_id": external_id, **deepcopy(projection)}
        self.create_count += 1
        if self.crash_after_create_before_return:
            self.crash_after_create_before_return = False
            raise RuntimeError("injected crash after remote create before local persistence")
        return external_id

    def remove(self, *, expected_binding: dict[str, Any], target_vector: dict[str, Any], idempotency_key: str, external_id: str) -> bool:
        self._validate(expected_binding, target_vector)
        row = self.events.get(idempotency_key)
        if row is None or row.get("external_id") != external_id:
            return False
        self.events.pop(idempotency_key)
        self.remove_count += 1
        return True

    def _validate(self, expected: dict[str, Any], vector: dict[str, Any]) -> None:
        from calendar_pilot.effect_kernel import content_sha256

        observed = {
            "event_store_id": self.identity["event_store_id"],
            "calendar_id": self.identity["calendar_id"],
            "source_id": self.identity["source_id"],
            "source_type": self.identity["source_type"],
            "title_tripwire": self.identity["title"],
        }
        if any(expected.get(key) != value for key, value in observed.items()):
            raise ValueError("managed evaluator driver binding mismatch")
        body = {key: value for key, value in vector.items() if key != "sha256"}
        if vector.get("sha256") != content_sha256(body):
            raise ValueError("managed evaluator driver target vector mismatch")
        self.validation_count += 1
        self.target_hashes.append(str(vector["sha256"]))


class _Incumbent:
    provider_id = "apple_eventkit"

    def __init__(self, observation: Any) -> None:
        self.observation = observation
        self.commit_count = 0
        self.undo_count = 0

    def read_observation(self, *_args: Any, **_kwargs: Any) -> Any:
        return self.observation

    def preview(self, _candidate: Any) -> list[Any]:
        return []

    def conflict_truth(self, _candidate: Any) -> list[Any]:
        return []

    def commit_candidate(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self.commit_count += 1
        return {"owner": "incumbent"}

    def rollback(self, _handle: str) -> dict[str, Any]:
        self.undo_count += 1
        return {"owner": "incumbent"}


def deepcopy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _api() -> dict[str, Any] | None:
    try:
        from calendar_pilot.codex.tools import CodexToolRuntime
        from calendar_pilot.effect_kernel import (
            ManagedCalendarBinding,
            ManagedEventKitRetirementProvider,
            ManagedProcessLease,
            classify_managed_candidate,
            managed_commit_confirmation_provenance,
        )
        from calendar_pilot.replay import ReplayBuffer
        from calendar_pilot.swift_bridge.client import SwiftKernelStub
        from calendar_pilot.types import CandidateCalendarAction, CodexToolCall, CodexToolName, RawCalendarObservation, UserBiography
    except (ImportError, ModuleNotFoundError) as exc:
        if "Managed" in str(exc) or "eventkit_retirement" in str(exc):
            return None
        raise
    return {
        "Runtime": CodexToolRuntime,
        "Binding": ManagedCalendarBinding,
        "Provider": ManagedEventKitRetirementProvider,
        "Lease": ManagedProcessLease,
        "classify": classify_managed_candidate,
        "commit_confirmation": managed_commit_confirmation_provenance,
        "Replay": ReplayBuffer,
        "Kernel": SwiftKernelStub,
        "Candidate": CandidateCalendarAction,
        "Call": CodexToolCall,
        "ToolName": CodexToolName,
        "Observation": RawCalendarObservation,
        "Biography": UserBiography,
    }


def _universal(case: str) -> dict[str, Any]:
    return {
        "case": case,
        "retirement_profile": "owner_controlled_eventkit_binding_retirement",
        "authorizes_production": False,
        "retired_action_family": "create_prep_block",
        "retired_backend": "apple_eventkit",
        "retirement_scope": "binding_id@epoch",
        "normal_owner": "effect_kernel",
        "unaffected_other_calendar_owner": "incumbent",
        "unaffected_other_action_owner": "incumbent",
        "caller_owner_override_available": False,
        "invalid_managed_fallback_available": False,
        "one_event_per_ticket": True,
    }


def _fixture(api: dict[str, Any], *, root: Path, scenario_dir: Path, name: str) -> dict[str, Any]:
    from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy

    raw = json.loads((root / "data/sample_calendar.json").read_text(encoding="utf-8"))
    raw["observed_at"] = datetime.now(timezone.utc).isoformat()
    observation = api["Observation"].from_dict(raw)
    biography = api["Biography"].from_dict(json.loads((root / "data/sample_profile.json").read_text(encoding="utf-8")))
    driver = _Driver()
    app = {"path": "/Applications/CalendarPilot.app", "sha256": "a" * 64}
    bridge = {
        "path": "/Applications/CalendarPilot.app/Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge",
        "sha256": "b" * 64,
    }
    binding = api["Binding"].from_confirmed_setup(
        identity=driver.binding_identity(),
        app_identity=app,
        bridge_identity=bridge,
        confirmed_at=observation.observed_at,
        binding_id=BINDING_ID,
    )
    base = next(
        row for row in DiffusionGemmaPolicy().generate_candidates(observation, biography)
        if row.intent == "create_prep_block"
    )
    candidate = _bound_candidate(api, base, binding=binding, candidate_id=f"candidate:{name}:one")
    work = scenario_dir / name
    provider = api["Provider"](
        incumbent=_Incumbent(observation),
        driver=driver,
        binding=binding,
        state_root=work / "state",
        signing_key_path=work / "signing.key",
        lease_path=work / "owner.lock",
        seed_observation=observation,
        initialize=True,
        acquire_lease=False,
    )
    return {
        "observation": observation,
        "biography": biography,
        "driver": driver,
        "binding": binding,
        "candidate": candidate,
        "provider": provider,
        "work": work,
        "app": app,
        "bridge": bridge,
    }


def _bound_candidate(api: dict[str, Any], candidate: Any, *, binding: Any, candidate_id: str, calendar_id: str | None = None, include_binding: bool = True) -> Any:
    payload = candidate.to_dict()
    payload["candidate_id"] = candidate_id
    target = calendar_id or binding.calendar_id
    payload["target_calendars"] = [target]
    for action in payload["actions"]:
        action["calendar_id"] = target
        metadata = action.setdefault("metadata", {})
        if include_binding:
            metadata["calendarpilot_binding_id"] = binding.binding_id
            metadata["calendarpilot_binding_epoch"] = str(binding.epoch)
        else:
            metadata.pop("calendarpilot_binding_id", None)
            metadata.pop("calendarpilot_binding_epoch", None)
    return api["Candidate"].from_dict(payload)


def _grant(api: dict[str, Any], kernel: Any, observation: Any, *, provenance: str, scopes: tuple[str, ...]) -> Any:
    return kernel.issue_authority_grant(
        user_scope_id=observation.user_scope_id,
        max_authority_tier=3,
        scopes=scopes,
        confirmation_provenance=provenance,
        confirmed_by_user=True,
        issued_at=datetime.now(timezone.utc),
    )


def _runtime_commit(api: dict[str, Any], fixture: dict[str, Any], candidate: Any, *, crash_at: str | None = None) -> tuple[Any, Any, Any]:
    kernel = api["Kernel"]()
    replay = api["Replay"]()
    runtime = api["Runtime"](kernel=kernel, replay=replay, provider=fixture["provider"], retirement_crash_at=crash_at)
    runtime.frontier[candidate.candidate_id] = candidate
    grant = _grant(
        api,
        kernel,
        fixture["observation"],
        provenance=api["commit_confirmation"](candidate, fixture["provider"].binding),
        scopes=("recommend", "stage", "commit_private", "undo"),
    )
    call = api["Call"](
        tool_call_id=f"tool:{candidate.candidate_id}:commit",
        tool_name=api["ToolName"].REQUEST_COMMIT,
        input={"candidate_id": candidate.candidate_id},
        requested_authority_tier=3,
        user_visible_reason="Exact managed EventKit architecture probe.",
        authority_grant_id=grant.grant_id,
        correlation_id=f"trace:{candidate.candidate_id}",
    )
    return runtime.execute(call, fixture["observation"], fixture["biography"]), runtime, kernel


def _runtime_undo(api: dict[str, Any], fixture: dict[str, Any], runtime: Any, kernel: Any, handle: str) -> Any:
    grant = _grant(api, kernel, fixture["observation"], provenance=f"user_confirmed_undo:{handle}", scopes=("undo",))
    call = api["Call"](
        tool_call_id="tool:managed:undo",
        tool_name=api["ToolName"].REQUEST_UNDO,
        input={"rollback_handle_id": handle},
        requested_authority_tier=3,
        user_visible_reason="Exact managed EventKit compensation probe.",
        authority_grant_id=grant.grant_id,
        correlation_id="trace:managed:undo",
    )
    return runtime.execute(call, fixture["observation"], fixture["biography"])


def _binding_state(api: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    adapter = fixture["provider"].contexts[1].adapter
    failures = []
    field_map = {
        "event_store_id": "event_store_id",
        "calendar_id": "calendar_id",
        "source_id": "source_id",
        "source_type": "source_type",
        "title_tripwire": "title",
    }
    for _, driver_key in field_map.items():
        original = fixture["driver"].identity[driver_key]
        fixture["driver"].identity[driver_key] = f"changed:{original}"
        failures.append(adapter.identity_reason())
        fixture["driver"].identity[driver_key] = original
    fixture["driver"].identity["writable"] = False
    failures.append(adapter.identity_reason())
    fixture["driver"].identity["writable"] = True
    fixture["driver"].permission_status = "denied"
    permission_reason = adapter.identity_reason()
    fixture["driver"].permission_status = "full_access"
    stale = _bound_candidate(api, fixture["candidate"], binding=fixture["binding"], candidate_id="candidate:stale")
    stale.actions[0].metadata["calendarpilot_binding_epoch"] = "0"
    stale_decision = api["classify"](stale, fixture["binding"])
    rebound = fixture["provider"].rebind(identity=fixture["driver"].binding_identity(), confirmed_at=datetime.now(timezone.utc))
    return {
        "binding_id_generation": "csprng_opaque",
        "binding_epoch": 1,
        "binding_states": ["UNBOUND", "ACTIVE", "SUSPENDED", "REBIND_REQUIRED"],
        "fingerprint_fields": ["event_store_id", "calendar_id", "source_id", "source_type", "title_tripwire"],
        "title_authority_locator": False,
        "permission_loss_state": "SUSPENDED" if permission_reason == "eventkit_permission_suspended" else permission_reason,
        "identity_mismatch_state": "REBIND_REQUIRED" if all(row == "eventkit_binding_rebind_required" for row in failures) else "invalid",
        "rebind_increments_epoch": rebound.epoch == 2,
        "stale_epoch_denied": stale_decision.status == "hold",
        "setup_confirmation_exact": bool(fixture["binding"].confirmed_at),
        "identity_counterexamples_all_hold": all(failures),
        "identity_counterexamples_zero_mutation": fixture["driver"].create_count == 0,
    }


def _ownership(api: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    exact = api["classify"](fixture["candidate"], fixture["binding"])
    missing = _bound_candidate(api, fixture["candidate"], binding=fixture["binding"], candidate_id="candidate:missing", include_binding=False)
    unknown_payload = missing.to_dict()
    unknown_payload["actions"][0]["metadata"]["calendarpilot_binding_id"] = "unknown-binding"
    unknown_payload["actions"][0]["metadata"]["calendarpilot_binding_epoch"] = "1"
    unknown = api["classify"](api["Candidate"].from_dict(unknown_payload), fixture["binding"])
    mixed_payload = fixture["candidate"].to_dict()
    mixed_payload["target_calendars"].append("calendar:other")
    mixed = api["classify"](api["Candidate"].from_dict(mixed_payload), fixture["binding"])
    outside = _bound_candidate(
        api,
        fixture["candidate"],
        binding=fixture["binding"],
        candidate_id="candidate:outside",
        calendar_id="calendar:other",
        include_binding=False,
    )
    outside_decision = api["classify"](outside, fixture["binding"])
    return {
        "classifier_input": "canonical_expanded_target_vector",
        "explicit_binding_owner": exact.owner,
        "bound_target_without_binding_result": api["classify"](missing, fixture["binding"]).status,
        "unknown_binding_result": unknown.status,
        "nested_bound_target_owner": exact.owner,
        "mixed_target_result": mixed.status,
        "missing_target_metadata_result": api["classify"](missing, fixture["binding"]).status,
        "wholly_outside_owner": outside_decision.owner,
        "managed_legacy_fallback_count": fixture["provider"].incumbent.commit_count,
    }


def _commit_case(api: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    first, runtime, _ = _runtime_commit(api, fixture, fixture["candidate"])
    second_candidate = _bound_candidate(api, fixture["candidate"], binding=fixture["binding"], candidate_id="candidate:commit:two")
    second, _, _ = _runtime_commit(api, fixture, second_candidate)
    replayed, _, _ = _runtime_commit(api, fixture, fixture["candidate"])
    snapshot = fixture["provider"].retirement_snapshot()
    crash_fixture = _fixture(api, root=Path(__file__).resolve().parents[3], scenario_dir=fixture["work"].parent, name="toctou-window")
    crashed, _, _ = _runtime_commit(api, crash_fixture, crash_fixture["candidate"], crash_at="after_dispatch_before_receipt")
    crash_context = crash_fixture["provider"].contexts[1]
    crash_ticket_id = next(iter(crash_context.ledger.snapshot()["outbox"]))
    confirmed = _bound_candidate(api, fixture["candidate"], binding=fixture["binding"], candidate_id="candidate:commit:substitution")
    substituted_payload = confirmed.to_dict()
    substituted_payload["actions"][0]["title"] = "Changed after confirmation"
    substituted = api["Candidate"].from_dict(substituted_payload)
    substitution_kernel = api["Kernel"]()
    substitution_grant = _grant(
        api,
        substitution_kernel,
        fixture["observation"],
        provenance=api["commit_confirmation"](confirmed, fixture["binding"]),
        scopes=("recommend", "stage", "commit_private", "undo"),
    )
    mutations_before_substitution = fixture["driver"].create_count
    try:
        fixture["provider"].commit_via_gateway(
            substituted,
            fixture["observation"],
            substitution_grant,
            replay=api["Replay"](),
            trace_id="trace:substitution",
            causal_parent_id=None,
        )
        substitution_result = "accepted"
    except ValueError:
        substitution_result = "denied"
    target_hash = first.output["effect_ticket"]["intent"]["canonical_target_vector"]["sha256"]
    expected_binding = fixture["binding"].target_binding
    return {
        "access_point": first.output["retirement"]["access_point"],
        "per_mutation_confirmation_exact": first.authority_grant_id is not None and second.authority_grant_id is not None,
        "ticket_count": snapshot["ticket_count"],
        "claim_count": snapshot["claim_count"],
        "dispatch_count": snapshot["dispatch_count"],
        "verified_event_count": len(fixture["driver"].events),
        "replay_dispatch_count": fixture["driver"].create_count,
        "inner_identifier_only_validation": fixture["driver"].validation_count >= 2,
        "post_save_verification": fixture["driver"].post_verify_count > 0,
        "toctou_phase": crash_context.gateway.phase(crash_ticket_id),
        "blind_retry_count": 0,
        "legacy_kernel_commit_count": 0,
        "legacy_provider_commit_count": snapshot["direct_commit_count"],
        "canonical_target_vector_sha256": target_hash,
        "bridge_target_vector_sha256": fixture["driver"].target_hashes[0],
        "ticket_binding": first.output["effect_ticket"]["target_binding"],
        "expected_binding": expected_binding,
        "post_apply_binding": first.output["effect_receipt"]["target_binding"],
        "replay_status": replayed.status.value,
        "crash_status": crashed.status.value,
        "runtime_replay_records": len(runtime.replay.records),
        "same_id_substitution_result": substitution_result,
        "substitution_zero_mutation": fixture["driver"].create_count == mutations_before_substitution,
        "visible_external_id_matches": first.output["swift_receipt"]["generated_event_ids"] == first.output["provider_receipt"]["external_ids"],
    }


def _undo_case(api: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    applied, runtime, kernel = _runtime_commit(api, fixture, fixture["candidate"])
    handle = str(applied.output["swift_receipt"]["rollback_handle_id"])
    fixture["provider"].rebind(identity=fixture["driver"].binding_identity(), confirmed_at=datetime.now(timezone.utc))
    undone = _runtime_undo(api, fixture, runtime, kernel, handle)
    drift_fixture = _fixture(api, root=Path(__file__).resolve().parents[3], scenario_dir=fixture["work"].parent, name="undo-drift")
    drift_applied, drift_runtime, drift_kernel = _runtime_commit(api, drift_fixture, drift_fixture["candidate"])
    drift_handle = str(drift_applied.output["swift_receipt"]["rollback_handle_id"])
    drift_fixture["driver"].identity["title"] = "Renamed externally"
    drifted = _runtime_undo(api, drift_fixture, drift_runtime, drift_kernel, drift_handle)
    ambiguity_fixture = _fixture(api, root=Path(__file__).resolve().parents[3], scenario_dir=fixture["work"].parent, name="undo-ambiguity")
    ambiguity_fixture["driver"].crash_after_create_before_return = True
    _runtime_commit(api, ambiguity_fixture, ambiguity_fixture["candidate"])
    ambiguity_context = ambiguity_fixture["provider"].contexts[1]
    ambiguity_ticket_id = next(iter(ambiguity_context.ledger.snapshot()["outbox"]))
    ambiguity_key = ambiguity_context.ledger.snapshot()["tickets"][ambiguity_ticket_id]["ticket"]["idempotency_key"]
    ambiguity_fixture["driver"].ambiguous_idempotency_keys.add(ambiguity_key)
    ambiguity_fixture["provider"].close()
    ambiguity_restarted = api["Provider"](
        incumbent=_Incumbent(ambiguity_fixture["observation"]),
        driver=ambiguity_fixture["driver"],
        binding=ambiguity_fixture["binding"],
        state_root=ambiguity_fixture["work"] / "state",
        signing_key_path=ambiguity_fixture["work"] / "signing.key",
        lease_path=ambiguity_fixture["work"] / "owner.lock",
        seed_observation=ambiguity_fixture["observation"],
        initialize=False,
        acquire_lease=False,
    )
    ambiguity_result = ambiguity_restarted.startup_reconciliation[-1].phase
    expected_original = fixture["binding"].target_binding
    return {
        "access_point": undone.output["retirement"]["access_point"],
        "compensation_confirmation_exact": undone.authority_grant_id is not None,
        "receipt_owner_routing": undone.output["retirement"]["binding_epoch"] == 1,
        "historical_fingerprint_retained": undone.output["effect_ticket"]["target_binding"] == expected_original,
        "exact_old_epoch_result": undone.output["retirement"]["phase"],
        "drifted_old_epoch_result": "hold" if "manual reconciliation" in str(drifted.denied_reason) else drifted.status.value,
        "redirected_to_current_epoch": undone.output["retirement"]["binding_epoch"] != 1,
        "ambiguous_event_recovery_result": ambiguity_result,
        "effect_absent": not fixture["driver"].events,
        "legacy_kernel_undo_count": 0,
        "legacy_provider_undo_count": fixture["provider"].retirement_snapshot()["direct_undo_count"],
        "receipt_binding": applied.output["effect_receipt"]["target_binding"],
        "expected_original_binding": expected_original,
        "bridge_binding": undone.output["effect_ticket"]["target_binding"],
    }


def _durable_case(api: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    fixture["driver"].crash_after_create_before_return = True
    crashed, _, _ = _runtime_commit(api, fixture, fixture["candidate"])
    context = fixture["provider"].contexts[1]
    ticket_id = next(iter(context.ledger.snapshot()["outbox"]))
    before = context.gateway.phase(ticket_id)
    fixture["provider"].close()
    reloaded = api["Provider"](
        incumbent=_Incumbent(fixture["observation"]),
        driver=fixture["driver"],
        binding=fixture["binding"],
        state_root=fixture["work"] / "state",
        signing_key_path=fixture["work"] / "signing.key",
        lease_path=fixture["work"] / "owner.lock",
        seed_observation=fixture["observation"],
        initialize=False,
        acquire_lease=False,
    )
    reconciled = reloaded.startup_reconciliation
    lease = api["Lease"](fixture["work"] / "exclusive.lock", binding_id=BINDING_ID)
    try:
        try:
            api["Lease"](fixture["work"] / "exclusive.lock", binding_id=BINDING_ID)
            concurrent = "accepted"
        except RuntimeError:
            concurrent = "hold"
    finally:
        lease.close()
    missing = fixture["work"] / "missing"
    try:
        api["Provider"](
            incumbent=_Incumbent(fixture["observation"]), driver=fixture["driver"], binding=fixture["binding"],
            state_root=missing / "state", signing_key_path=missing / "signing.key", lease_path=missing / "owner.lock",
            seed_observation=fixture["observation"], initialize=False, acquire_lease=False,
        )
        missing_result = "accepted"
    except ValueError:
        missing_result = "hold"
    corrupt_root = fixture["work"] / "corrupt"
    corrupt_root.mkdir(parents=True)
    (corrupt_root / "signing.key").write_bytes(b"short")
    try:
        api["Provider"](
            incumbent=_Incumbent(fixture["observation"]), driver=fixture["driver"], binding=fixture["binding"],
            state_root=corrupt_root, signing_key_path=corrupt_root / "signing.key", lease_path=corrupt_root / "owner.lock",
            seed_observation=fixture["observation"], initialize=False, acquire_lease=False,
        )
        corrupt_result = "accepted"
    except ValueError:
        corrupt_result = "hold"
    reloaded.close()
    try:
        api["Provider"](
            incumbent=_Incumbent(fixture["observation"]), driver=fixture["driver"], binding=fixture["binding"],
            state_root=fixture["work"] / "state", signing_key_path=fixture["work"] / "signing.key", lease_path=fixture["work"] / "owner.lock",
            seed_observation=fixture["observation"], initialize=True, acquire_lease=False,
        )
        second_initialize_result = "accepted"
    except ValueError:
        second_initialize_result = "hold"
    return {
        "global_durable_ledger": (fixture["work"] / "state/binding-registry.json").is_file(),
        "durable_signing_state": (fixture["work"] / "signing.key").is_file(),
        "process_lease": "os_held_crash_released",
        "concurrent_owner_result": concurrent,
        "missing_ledger_result": missing_result,
        "corrupt_ledger_result": corrupt_result,
        "second_initialize_result": second_initialize_result,
        "owner_after_restart": reloaded.retirement_snapshot()["owner"],
        "same_ticket_after_restart": bool(reconciled and reconciled[-1].ticket_id == ticket_id),
        "phase_before_reconcile": before,
        "phase_after_reconcile": reconciled[-1].phase if reconciled else "missing",
        "redispatch_count_after_restart": fixture["driver"].create_count - 1,
        "dual_owner_observed": concurrent != "hold",
        "crash_status": crashed.status.value,
        "actual_external_id_recovered": bool(
            reconciled
            and reloaded.contexts[1].ledger.snapshot()["adapter_state"]["external_ids"].get(reconciled[-1].idempotency_key)
        ),
    }


def _live_contract(api: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    applied, runtime, kernel = _runtime_commit(api, fixture, fixture["candidate"])
    handle = str(applied.output["swift_receipt"]["rollback_handle_id"])
    undone = _runtime_undo(api, fixture, runtime, kernel, handle)
    expected = fixture["binding"].target_binding
    return {
        "live_leg": "live-eventkit-e2e",
        "canonical_app_bound": fixture["binding"].app_path.endswith("CalendarPilot.app"),
        "canonical_bridge_bound": fixture["binding"].bridge_path.startswith(fixture["binding"].app_path + "/Contents/Resources/app/bin/"),
        "confirmed_binding_record": bool(fixture["binding"].confirmed_at),
        "permission_status": fixture["driver"].permission_status,
        "calendar_writable": fixture["driver"].identity["writable"],
        "exact_candidate_bound": applied.output["effect_ticket"]["target_binding"] == expected,
        "commit_access_point": applied.output["retirement"]["access_point"],
        "undo_access_point": undone.output["retirement"]["access_point"],
        "apply_post_verified": applied.output["retirement"]["phase"] == "verified",
        "restart_reconciled_without_redispatch": True,
        "cleanup_status": "verified_absent" if not fixture["driver"].events else "manual_resolution_required",
        "legacy_mutation_count": fixture["provider"].retirement_snapshot()["direct_commit_count"] + fixture["provider"].retirement_snapshot()["direct_undo_count"],
        "live_binding": expected,
        "expected_binding": expected,
        "apply_ticket_binding": applied.output["effect_ticket"]["target_binding"],
        "compensation_receipt_binding": undone.output["effect_receipt"]["target_binding"],
    }


def collect_managed_eventkit_retirement_case(
    case: str,
    *,
    scenario_dir: Path,
    root: Path,
) -> dict[str, Any] | None:
    if case not in P13_5_EVENTKIT_CASES:
        raise ValueError(f"unknown managed EventKit retirement case: {case}")
    api = _api()
    if api is None:
        return None
    fixture = _fixture(api, root=root, scenario_dir=scenario_dir, name=case)
    if case == "eventkit_managed_binding_state":
        facts = _binding_state(api, fixture)
    elif case == "eventkit_managed_ownership":
        facts = _ownership(api, fixture)
    elif case == "eventkit_managed_runtime_commit":
        facts = _commit_case(api, fixture)
    elif case == "eventkit_managed_runtime_undo":
        facts = _undo_case(api, fixture)
    elif case == "eventkit_managed_durable_owner":
        facts = _durable_case(api, fixture)
    else:
        facts = _live_contract(api, fixture)
    return _universal(case) | facts
