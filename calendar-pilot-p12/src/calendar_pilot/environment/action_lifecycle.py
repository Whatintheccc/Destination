from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any
import hashlib

from calendar_pilot.environment.envelope import ActionEnvelope, rollback_state_from_receipt
from calendar_pilot.providers import CalendarProviderError
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.swift_bridge.protocol import CalendarKernelProtocol
from calendar_pilot.types import (
    ActuationMode,
    AuthorityGrant,
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarObservation,
    RewardEvent,
    StageState,
)


@dataclass
class ActionLifecycleResult:
    envelope: ActionEnvelope
    status: str
    candidate: CandidateCalendarAction | None = None
    swift_receipt: CalendarActionReceipt | None = None
    provider_receipt: Any | None = None
    provider_rollback: Any | None = None
    denied_reason: str | None = None
    requires_confirmation: bool = False
    stage_state: StageState = StageState.NO_OP
    output: dict[str, Any] | None = None

    def output_payload(self) -> dict[str, Any]:
        if self.output is not None:
            payload = dict(self.output)
        else:
            payload = {}
        if self.candidate is not None:
            payload.setdefault("candidate", self.candidate.to_dict())
        if self.swift_receipt is not None:
            payload.setdefault("swift_receipt", self.swift_receipt.to_dict())
            payload.setdefault("stage_state", self.swift_receipt.stage_state.value)
        if self.provider_receipt is not None:
            payload.setdefault("provider_receipt", self.provider_receipt.to_dict())
        if self.provider_rollback is not None:
            payload.setdefault("provider_rollback", self.provider_rollback.to_dict())
            payload.setdefault("rollback_verified", getattr(self.provider_rollback, "rollback_verified", None))
        payload.setdefault("stage_state", self.stage_state.value)
        payload["action_envelope"] = self.envelope.to_dict()
        return payload


class ActionLifecycle:
    """Single mutation path for simulate/stage/commit/verify/reward/undo.

    This is the extracted acting spine. CodexToolRuntime delegates to it, and
    self-play can use it for provider-backed episodes instead of direct kernel
    calls. The class remains stdlib-only and wraps existing kernel/provider
    APIs so behavior transfer is incremental rather than a big-bang rewrite.
    """

    def __init__(
        self,
        *,
        kernel: CalendarKernelProtocol | None = None,
        replay: ReplayBuffer | None = None,
        provider: Any | None = None,
        runtime_mode: str = "tool_runtime",
        backends: dict[str, str] | None = None,
        max_commits_per_run: int = 20,
        max_mutations_per_run: int | None = None,
    ) -> None:
        self.kernel = kernel or SwiftKernelStub()
        self.replay = replay or ReplayBuffer()
        self.provider = provider
        self.runtime_mode = runtime_mode
        self.backends = backends or {
            "kernel": type(self.kernel).__name__,
            "provider": getattr(self.provider, "provider_id", "none") if self.provider is not None else "none",
            "codex": "CodexToolRuntime",
            "policy": "unknown",
        }
        self.max_commits_per_run = int(max_commits_per_run)
        self.max_mutations_per_run = max_mutations_per_run
        self._commits_this_run = 0
        self._mutations_this_run = 0

    def prepare(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        grant: AuthorityGrant | str | None,
        *,
        trace_id: str,
        causal_parent_id: str | None = None,
    ) -> ActionEnvelope:
        resolved = self._resolve_grant(grant)
        envelope = ActionEnvelope.create(
            trace_id=trace_id,
            candidate_id=candidate.candidate_id,
            observation_fingerprint=observation_fingerprint(observation),
            runtime_mode=self.runtime_mode,
            backends=dict(self.backends),
            authority={
                "grant_id": resolved.grant_id if resolved else (grant if isinstance(grant, str) else None),
                "tier": resolved.max_authority_tier if resolved else candidate.required_authority_tier,
                "scopes": resolved.scopes if resolved else [],
                "confirmation_provenance": resolved.confirmation_provenance if resolved else None,
            },
        )
        envelope.transition("prepare", status="succeeded", detail={"candidate_id": candidate.candidate_id})
        self._append(envelope, transition="prepare", causal_parent_id=causal_parent_id)
        return envelope

    def simulate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        grant: AuthorityGrant | str | None,
        *,
        requested_authority_tier: int,
        trace_id: str,
        causal_parent_id: str | None = None,
    ) -> ActionLifecycleResult:
        envelope = self.prepare(candidate, observation, grant, trace_id=trace_id, causal_parent_id=causal_parent_id)
        resolved = self._resolve_grant(grant)
        receipt = self.kernel.preview_candidate(
            candidate,
            observation,
            authority_grant=resolved.grant_id if resolved else (grant if isinstance(grant, str) else None),
            requested_authority_tier=requested_authority_tier,
            correlation_id=trace_id,
        )
        social = self.kernel.is_people_affecting_mutation(candidate)
        status = "denied" if receipt.denied_reason else "simulated"
        envelope.provider.update({
            "provider_id": receipt.provider_id,
            "rollback_handle_id": receipt.rollback_handle_id,
            "rollback_state": rollback_state_from_receipt(receipt.to_dict()),
        })
        envelope.transition("simulate", status=status, swift_receipt_id=receipt.receipt_id, detail={"denied_reason": receipt.denied_reason})
        self._append(envelope, transition="simulate", causal_parent_id=causal_parent_id)
        return ActionLifecycleResult(
            envelope=envelope,
            status=status,
            candidate=candidate,
            swift_receipt=receipt,
            denied_reason=receipt.denied_reason,
            requires_confirmation=social or candidate.required_authority_tier > requested_authority_tier,
            stage_state=receipt.stage_state,
            output={
                "simulation_only": True,
                "authority_grant_id": resolved.grant_id if resolved else None,
                "would_sync_status": receipt.sync_status,
                "would_actuation_mode": receipt.actuation_mode.value,
                "would_denied_reason": receipt.denied_reason,
                "would_require_confirmation": social or candidate.required_authority_tier > requested_authority_tier,
                "counterfactual": candidate.counterfactual,
                "reward_breakdown": candidate.reward_breakdown,
                "right_moment": candidate.right_moment_decision.value,
            },
        )

    def stage(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        grant: AuthorityGrant | str | None,
        *,
        requested_authority_tier: int,
        trace_id: str,
        causal_parent_id: str | None = None,
    ) -> ActionLifecycleResult:
        envelope = self.prepare(candidate, observation, grant, trace_id=trace_id, causal_parent_id=causal_parent_id)
        resolved = self._resolve_grant(grant)
        receipt = self.kernel.stage_candidate(
            candidate,
            observation,
            authority_grant=resolved.grant_id if resolved else (grant if isinstance(grant, str) else None),
            requested_authority_tier=requested_authority_tier,
            correlation_id=trace_id,
        )
        self.replay.append_receipt(receipt, candidate, trace_id=trace_id, causal_parent_id=causal_parent_id, observation_id=observation.observation_id, observation_fingerprint=observation_fingerprint(observation), runtime_mode=self.runtime_mode, policy_backend=self.backends.get("policy"))
        status = "denied" if receipt.denied_reason else "stageable"
        envelope.provider.update({
            "provider_id": receipt.provider_id,
            "rollback_handle_id": receipt.rollback_handle_id,
            "rollback_state": rollback_state_from_receipt(receipt.to_dict()),
        })
        envelope.transition("stage", status=status, swift_receipt_id=receipt.receipt_id, detail={"denied_reason": receipt.denied_reason, "stage_state": receipt.stage_state.value})
        self._append(envelope, transition="stage", causal_parent_id=causal_parent_id)
        return ActionLifecycleResult(
            envelope=envelope,
            status=status,
            candidate=candidate,
            swift_receipt=receipt,
            denied_reason=receipt.denied_reason,
            requires_confirmation=receipt.stage_state in {StageState.REQUIRES_CONFIRMATION, StageState.STAGEABLE},
            stage_state=receipt.stage_state,
        )

    def commit(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        grant: AuthorityGrant | str | None,
        *,
        requested_authority_tier: int,
        trace_id: str,
        causal_parent_id: str | None = None,
        require_live_observation: bool = True,
    ) -> ActionLifecycleResult:
        envelope = self.prepare(candidate, observation, grant, trace_id=trace_id, causal_parent_id=causal_parent_id)
        resolved = self._resolve_grant(grant)
        cap_denial = self._cap_denial(candidate, observation, trace_id=trace_id, grant=resolved or grant)
        if cap_denial is not None:
            receipt = cap_denial
            envelope.provider.update({
                "provider_id": receipt.provider_id,
                "provider_status": "rate_cap_denied",
                "rollback_state": "unsupported",
            })
            envelope.transition("commit", status="denied", swift_receipt_id=receipt.receipt_id, detail={"denied_reason": receipt.denied_reason})
            self.replay.append_receipt(receipt, candidate, trace_id=trace_id, causal_parent_id=causal_parent_id, observation_id=observation.observation_id, observation_fingerprint=observation_fingerprint(observation), runtime_mode=self.runtime_mode, policy_backend=self.backends.get("policy"))
            self._append(envelope, transition="commit", causal_parent_id=causal_parent_id)
            return ActionLifecycleResult(envelope=envelope, status="denied", candidate=candidate, swift_receipt=receipt, denied_reason=receipt.denied_reason, stage_state=StageState.DENIED)
        blocker = self._provider_write_blocker(observation, require_live_observation=require_live_observation)
        if blocker is not None:
            envelope.provider.update({
                "provider_id": getattr(self.provider, "provider_id", "unknown_provider"),
                "provider_status": blocker.get("status"),
                "rollback_state": "unsupported",
            })
            envelope.transition("commit", status="denied", detail={"denied_reason": "provider_not_configured", "provider_health": blocker})
            self._append(envelope, transition="commit", causal_parent_id=causal_parent_id)
            return ActionLifecycleResult(envelope=envelope, status="denied", candidate=candidate, denied_reason="provider_not_configured", stage_state=StageState.DENIED, output={"provider_id": getattr(self.provider, "provider_id", "unknown_provider"), "provider_health": blocker})
        try:
            provider_conflicts = self._provider_conflict_truth(candidate)
        except CalendarProviderError as exc:
            envelope.provider.update({"provider_id": getattr(self.provider, "provider_id", "unknown_provider"), "rollback_state": "unsupported"})
            envelope.transition("commit", status="denied", detail={"denied_reason": "provider_truth_unavailable", "provider_error": str(exc)})
            self._append(envelope, transition="commit", causal_parent_id=causal_parent_id)
            return ActionLifecycleResult(envelope=envelope, status="denied", candidate=candidate, denied_reason="provider_truth_unavailable", stage_state=StageState.DENIED, output={"provider_error": str(exc), "provider_id": getattr(self.provider, "provider_id", "unknown_provider")})
        if provider_conflicts:
            envelope.provider.update({"provider_id": getattr(self.provider, "provider_id", "unknown_provider"), "conflict_truth": provider_conflicts, "rollback_state": "unsupported"})
            envelope.transition("commit", status="denied", detail={"denied_reason": "provider_conflict_detected", "provider_conflict_truth": provider_conflicts})
            self._append(envelope, transition="commit", causal_parent_id=causal_parent_id)
            return ActionLifecycleResult(envelope=envelope, status="denied", candidate=candidate, denied_reason="provider_conflict_detected", stage_state=StageState.DENIED, output={"provider_conflict_truth": provider_conflicts, "provider_id": getattr(self.provider, "provider_id", "unknown_provider")})
        swift_receipt = self.kernel.authorize_and_materialize(
            candidate,
            observation,
            authority_grant=resolved.grant_id if resolved else (grant if isinstance(grant, str) else None),
            requested_authority_tier=requested_authority_tier,
            correlation_id=trace_id,
        )
        provider_receipt = self._commit_to_provider(candidate, swift_receipt, observation) if swift_receipt.denied_reason is None else None
        if provider_receipt is not None and getattr(provider_receipt, "status", "") == "conflict_denied":
            envelope.provider.update(provider_receipt.to_dict() | {"rollback_state": "unsupported"})
            envelope.transition("commit", status="denied", swift_receipt_id=swift_receipt.receipt_id, detail={"denied_reason": "provider_conflict_detected"})
            self._append(envelope, transition="commit", causal_parent_id=causal_parent_id)
            return ActionLifecycleResult(envelope=envelope, status="denied", candidate=candidate, swift_receipt=swift_receipt, provider_receipt=provider_receipt, denied_reason="provider_conflict_detected", stage_state=StageState.DENIED)
        provider_verify: dict[str, Any] = {}
        if provider_receipt is not None:
            swift_receipt = replace(
                swift_receipt,
                provider_id=provider_receipt.provider_id,
                generated_event_ids=provider_receipt.external_ids or swift_receipt.generated_event_ids,
                rollback_handle_id=provider_receipt.rollback_handle_id or swift_receipt.rollback_handle_id,
            )
            self.replay.append_provider_transaction(operation="commit", transaction=provider_receipt.to_dict(), trace_id=trace_id, causal_parent_id=swift_receipt.receipt_id)
            verified = self._verify_provider(provider_receipt, observation)
            if verified is not None:
                provider_verify = verified.to_dict() if hasattr(verified, "to_dict") else dict(verified)
                self.replay.append_provider_transaction(operation="verify", transaction=provider_verify, trace_id=trace_id, causal_parent_id=swift_receipt.receipt_id)
        if swift_receipt.denied_reason is None:
            self._commits_this_run += 1
            self._mutations_this_run += self._estimated_mutations(candidate)
        self.replay.append_receipt(swift_receipt, candidate, trace_id=trace_id, causal_parent_id=causal_parent_id, observation_id=observation.observation_id, observation_fingerprint=observation_fingerprint(observation), runtime_mode=self.runtime_mode, policy_backend=self.backends.get("policy"))
        status = "denied" if swift_receipt.denied_reason else "committed"
        provider_payload = provider_receipt.to_dict() if provider_receipt is not None else {}
        envelope.provider.update({
            "provider_id": provider_payload.get("provider_id") or swift_receipt.provider_id,
            "provider_status": provider_payload.get("status"),
            "provider_transaction_id": provider_payload.get("idempotency_key"),
            "external_event_ids": provider_payload.get("external_ids") or swift_receipt.generated_event_ids,
            "rollback_handle_id": provider_payload.get("rollback_handle_id") or swift_receipt.rollback_handle_id,
            "rollback_state": rollback_state_from_receipt(swift_receipt.to_dict()),
            "local_time_echo_ok": provider_verify.get("local_time_echo_ok") if provider_verify else None,
            "verified_external_ids": provider_verify.get("verified_external_ids") if provider_verify else None,
        })
        envelope.transition("commit", status=status, swift_receipt_id=swift_receipt.receipt_id, detail={"denied_reason": swift_receipt.denied_reason, "stage_state": swift_receipt.stage_state.value})
        self._append(envelope, transition="commit", causal_parent_id=causal_parent_id)
        return ActionLifecycleResult(envelope=envelope, status=status, candidate=candidate, swift_receipt=swift_receipt, provider_receipt=provider_receipt, denied_reason=swift_receipt.denied_reason, stage_state=swift_receipt.stage_state)

    def verify(self, envelope: ActionEnvelope) -> ActionEnvelope:
        state = envelope.provider.get("rollback_state") or "unsupported"
        detail: dict[str, Any] = {"rollback_state": state}
        provider_verify = getattr(self.provider, "verify", None)
        if callable(provider_verify):
            try:
                result = provider_verify(envelope.provider)
                payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
                detail["provider_verify"] = payload
                envelope.provider.update({
                    "provider_status": payload.get("status", envelope.provider.get("provider_status")),
                    "local_time_echo_ok": payload.get("local_time_echo_ok"),
                    "verified_external_ids": payload.get("verified_external_ids"),
                })
                self.replay.append_provider_transaction(operation="verify", transaction=payload, trace_id=envelope.trace_id, causal_parent_id=envelope.envelope_id)
            except Exception as exc:
                detail["provider_verify_error"] = str(exc)
        envelope.transition("verify", status="succeeded", detail=detail)
        self._append(envelope, transition="verify")
        return envelope

    def reward(self, envelope: ActionEnvelope, event: RewardEvent) -> ActionEnvelope:
        envelope.reward.setdefault("reward_event_ids", []).append(event.reward_event_id)
        envelope.transition("reward", status="succeeded", detail={"reward_event_id": event.reward_event_id, "provenance": event.provenance})
        self._append(envelope, transition="reward")
        return envelope

    def undo(
        self,
        rollback_handle_id: str,
        observation: RawCalendarObservation,
        grant: AuthorityGrant | str | None,
        *,
        requested_authority_tier: int,
        trace_id: str,
        causal_parent_id: str | None = None,
    ) -> ActionLifecycleResult:
        envelope = ActionEnvelope.create(
            trace_id=trace_id,
            candidate_id=rollback_handle_id,
            observation_fingerprint=observation_fingerprint(observation),
            runtime_mode=self.runtime_mode,
            backends=dict(self.backends),
            authority={"grant_id": grant.grant_id if isinstance(grant, AuthorityGrant) else grant},
        )
        envelope.transition("prepare", status="succeeded", detail={"rollback_handle_id": rollback_handle_id})
        resolved = self._resolve_grant(grant)
        blocker = self._provider_write_blocker(observation, require_live_observation=False)
        if blocker is not None:
            envelope.provider.update({"provider_id": getattr(self.provider, "provider_id", "unknown_provider"), "provider_status": blocker.get("status"), "rollback_state": "unsupported"})
            envelope.transition("undo", status="denied", detail={"denied_reason": "provider_not_configured", "provider_health": blocker})
            self._append(envelope, transition="undo", causal_parent_id=causal_parent_id)
            return ActionLifecycleResult(envelope=envelope, status="denied", denied_reason="provider_not_configured", stage_state=StageState.DENIED, output={"provider_id": getattr(self.provider, "provider_id", "unknown_provider"), "provider_health": blocker})
        receipt = self.kernel.request_undo(
            rollback_handle_id,
            observation,
            authority_grant=resolved.grant_id if resolved else (grant if isinstance(grant, str) else None),
            requested_authority_tier=requested_authority_tier,
            correlation_id=trace_id,
        )
        provider_rollback = self._rollback_provider(rollback_handle_id) if receipt.denied_reason is None else None
        if provider_rollback is not None:
            receipt = replace(receipt, provider_id=provider_rollback.provider_id)
            self.replay.append_provider_transaction(operation="rollback", transaction=provider_rollback.to_dict(), trace_id=trace_id, causal_parent_id=receipt.receipt_id)
        self.replay.append_receipt(receipt, trace_id=trace_id, causal_parent_id=causal_parent_id, observation_id=observation.observation_id, observation_fingerprint=observation_fingerprint(observation), runtime_mode=self.runtime_mode, policy_backend=self.backends.get("policy"))
        status = "denied" if receipt.denied_reason else "reverted"
        if provider_rollback is not None and not provider_rollback.rollback_verified:
            status = "failed"
        rollback_payload = provider_rollback.to_dict() if provider_rollback is not None else {}
        envelope.provider.update({
            "provider_id": rollback_payload.get("provider_id") or receipt.provider_id,
            "provider_status": rollback_payload.get("status"),
            "rollback_handle_id": rollback_handle_id,
            "rollback_verified": rollback_payload.get("rollback_verified"),
            "rollback_state": rollback_state_from_receipt(receipt.to_dict(), rollback_payload),
        })
        envelope.transition("undo", status=status, swift_receipt_id=receipt.receipt_id, detail={"denied_reason": receipt.denied_reason, "rollback_verified": rollback_payload.get("rollback_verified")})
        self._append(envelope, transition="undo", causal_parent_id=causal_parent_id)
        denied = receipt.denied_reason if status != "failed" else "provider_rollback_not_verified"
        return ActionLifecycleResult(envelope=envelope, status=status, swift_receipt=receipt, provider_rollback=provider_rollback, denied_reason=denied, stage_state=receipt.stage_state)


    def _cap_denial(self, candidate: CandidateCalendarAction, observation: RawCalendarObservation, *, trace_id: str, grant: AuthorityGrant | str | None) -> CalendarActionReceipt | None:
        estimated = self._estimated_mutations(candidate)
        if estimated <= 0:
            return None
        reason: str | None = None
        if self.max_commits_per_run >= 0 and self._commits_this_run >= self.max_commits_per_run:
            reason = f"rate_cap_exceeded:max_commits_per_run={self.max_commits_per_run}"
        elif self.max_mutations_per_run is not None and self._mutations_this_run + estimated > int(self.max_mutations_per_run):
            reason = f"rate_cap_exceeded:max_mutations_per_run={self.max_mutations_per_run}"
        if reason is None:
            return None
        grant_id = grant.grant_id if isinstance(grant, AuthorityGrant) else (grant if isinstance(grant, str) else None)
        return CalendarActionReceipt(
            receipt_id="cap_denial_" + hashlib.sha1(f"{trace_id}|{candidate.candidate_id}|{reason}".encode()).hexdigest()[:12],
            candidate_id=candidate.candidate_id,
            executed_at=observation.observed_at,
            executed_by="ActionLifecycle.rate_limiter",
            authority_tier_used=0,
            sync_status="denied",
            rollback_handle_id=None,
            conflict_check_passed=True,
            rejected_action_types=[a.action_type.value for a in candidate.actions],
            provider_id=getattr(self.provider, "provider_id", "rate_limiter"),
            actuation_mode=ActuationMode.DENIED,
            denied_reason=reason,
            authority_grant_id=grant_id,
            stage_state=StageState.DENIED,
            correlation_id=trace_id,
        )

    @staticmethod
    def _estimated_mutations(candidate: CandidateCalendarAction) -> int:
        write_types = {"create_event", "create_focus_block", "add_buffer", "batch_tasks", "move_event", "resize_event", "delete_own_event", "auto_apply_plan"}
        return sum(1 for action in candidate.actions if action.action_type.value in write_types)

    def _verify_provider(self, provider_receipt: Any, observation: RawCalendarObservation):
        verify = getattr(self.provider, "verify", None)
        if not callable(verify):
            return None
        try:
            return verify(provider_receipt, observation=observation)
        except TypeError:
            return verify(provider_receipt)

    def _append(self, envelope: ActionEnvelope, *, transition: str, causal_parent_id: str | None = None) -> None:
        rid = self.replay.append_envelope_transition(envelope.to_dict(), transition=transition, trace_id=envelope.trace_id, causal_parent_id=causal_parent_id)
        envelope.replay_record_ids.append(rid)

    def _resolve_grant(self, grant: AuthorityGrant | str | None) -> AuthorityGrant | None:
        if isinstance(grant, AuthorityGrant):
            return grant
        resolver = getattr(self.kernel, "resolve_authority_grant", None)
        if isinstance(grant, str) and callable(resolver):
            return resolver(grant)
        return None

    def _provider_conflict_truth(self, candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        conflict_truth = getattr(self.provider, "conflict_truth", None)
        if not callable(conflict_truth):
            return []
        return list(conflict_truth(candidate))

    def _provider_write_blocker(self, observation: RawCalendarObservation | None, *, require_live_observation: bool) -> dict[str, Any] | None:
        is_real_provider = bool(getattr(self.provider, "real_provider", False) or getattr(self.provider, "real_oauth", False))
        if self.provider is None or not is_real_provider:
            return None
        if type(self.kernel).__name__ != "SwiftKernelIPCClient":
            return {"provider": getattr(self.provider, "provider_id", "unknown_provider"), "configured": False, "status": "swift_ipc_required_for_live_provider", "kernel": type(self.kernel).__name__}
        expected_observation_id = getattr(self.provider, "observation_id", None)
        if require_live_observation and expected_observation_id and observation is not None and observation.observation_id != expected_observation_id:
            return {"provider": getattr(self.provider, "provider_id", "unknown_provider"), "configured": False, "status": "provider_observation_not_loaded", "expected_observation_id": expected_observation_id, "actual_observation_id": observation.observation_id}
        health_status = getattr(self.provider, "health_status", None)
        if not callable(health_status):
            return {"provider": getattr(self.provider, "provider_id", "unknown_provider"), "configured": False, "status": "health_unavailable"}
        health = dict(health_status())
        if health.get("configured"):
            return None
        return health

    def _commit_to_provider(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, observation: RawCalendarObservation):
        commit_candidate = getattr(self.provider, "commit_candidate", None)
        if not callable(commit_candidate):
            return None
        return commit_candidate(candidate, receipt, observation)

    def _rollback_provider(self, rollback_handle_id: str):
        rollback = getattr(self.provider, "rollback", None)
        if not callable(rollback):
            return None
        return rollback(rollback_handle_id)
