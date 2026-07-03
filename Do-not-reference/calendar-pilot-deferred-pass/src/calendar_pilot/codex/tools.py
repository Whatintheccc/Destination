

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import inspect
import json
from typing import Any

from calendar_pilot.biography import BiographyStore
from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.live import LiveDiffusionGemmaError
from calendar_pilot.diffusiongemma.self_play import SelfPlayRunner
from calendar_pilot.diffusiongemma.signals import extract_signals
from calendar_pilot.environment.envelope import rollback_state_from_receipt
from calendar_pilot.environment.action_lifecycle import ActionLifecycle
from calendar_pilot.providers import CalendarProviderError
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.swift_bridge.protocol import CalendarKernelProtocol
from calendar_pilot.types import (
    CalendarActionReceipt,
    AuthorityGrant,
    CandidateCalendarAction,
    CodexAutonomyScopeProposal,
    CodexToolCall,
    CodexToolName,
    CodexToolReceipt,
    CodexToolStatus,
    RawCalendarEvent,
    RawCalendarObservation,
    UserBiography,
    StageState,
    to_jsonable,
)


class CodexToolRuntime:
    """Bounded tool runtime for Codex.

    Codex is not sovereign and does not call provider APIs. It can inspect app
    state, ask DiffusionGemma for a frontier, simulate and compare futures,
    stage packets, request Swift commits, request undo, query replay, and draft
    profile/autonomy changes. Every operation returns a typed receipt so machine
    acting is auditable and replay-trainable.
    """

    def __init__(
        self,
        *,
        policy: DiffusionGemmaPolicy | None = None,
        kernel: CalendarKernelProtocol | None = None,
        replay: ReplayBuffer | None = None,
        biography_store: BiographyStore | None = None,
        provider: Any | None = None,
    ) -> None:
        self.policy = policy or DiffusionGemmaPolicy()
        self.kernel = kernel or SwiftKernelStub()
        self.replay = replay or ReplayBuffer()
        self.biography_store = biography_store or BiographyStore()
        self.provider = provider
        self.action_lifecycle = ActionLifecycle(
            kernel=self.kernel,
            replay=self.replay,
            provider=self.provider,
            runtime_mode="codex_tool_runtime",
            backends={
                "kernel": type(self.kernel).__name__,
                "provider": getattr(self.provider, "provider_id", "none") if self.provider is not None else "none",
                "codex": type(self).__name__,
                "policy": type(self.policy).__name__,
            },
        )
        self.frontier: dict[str, CandidateCalendarAction] = {}
        self.latest_observation: RawCalendarObservation | None = None
        self.latest_biography: UserBiography | None = None

    def execute(
        self,
        call: CodexToolCall,
        observation: RawCalendarObservation,
        biography: UserBiography,
    ) -> CodexToolReceipt:
        self.latest_observation = observation
        self.latest_biography = biography
        self.replay.append_tool_call(call)
        try:
            receipt = self._execute_inner(call, observation, biography)
        except Exception as exc:  # deterministic failure receipt for app surfaces
            receipt = CodexToolReceipt(
                tool_call_id=call.tool_call_id,
                tool_name=call.tool_name,
                status=CodexToolStatus.FAILED,
                output={"error": str(exc)},
                denied_reason=str(exc),
            )
        self.replay.append_tool_receipt(receipt)
        envelope = receipt.output.get("action_envelope") if isinstance(receipt.output, dict) else None
        if isinstance(envelope, dict):
            self.replay.append_envelope_transition(envelope, trace_id=receipt.correlation_id or receipt.tool_call_id)
        return receipt

    def _execute_inner(
        self,
        call: CodexToolCall,
        observation: RawCalendarObservation,
        biography: UserBiography,
    ) -> CodexToolReceipt:
        name = call.tool_name
        if name == CodexToolName.INSPECT_WEEK:
            return self._receipt(
                call,
                CodexToolStatus.SUCCEEDED,
                self._inspect_week(observation, biography, redact_raw_events=self._real_provider_active()),
            )
        if name == CodexToolName.INSPECT_EVENT:
            event_id = str(call.input.get("event_id", ""))
            event = next((e for e in observation.events if e.event_id == event_id), None)
            if event is None:
                return self._receipt(call, CodexToolStatus.DENIED, {}, denied="event not found")
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"event": self._event_dict(event, redact_private=self._real_provider_active())})
        if name == CodexToolName.INSPECT_OPEN_SLOTS:
            signals = extract_signals(observation, biography)
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"open_slots": [to_jsonable(s) for s in signals.open_slots]})
        if name == CodexToolName.INSPECT_AUTHORITY_SCOPE:
            return self._receipt(call, CodexToolStatus.SUCCEEDED, self._authority_scope(call))
        if name == CodexToolName.GENERATE_CANDIDATE_FRONTIER:
            return self._generate_frontier(call, observation, biography)
        if name == CodexToolName.SIMULATE_ACTION_PROGRAM:
            candidate = self._candidate_from_input(call)
            return self._simulate(call, candidate, observation)
        if name == CodexToolName.COMPARE_CANDIDATES:
            return self._compare(call)
        if name == CodexToolName.STAGE_ACTION_PACKET:
            candidate = self._candidate_from_input(call)
            grant = self._resolve_grant(call)
            if grant is None:
                return self._receipt(call, CodexToolStatus.DENIED, {"stage_state": StageState.DENIED.value}, denied="missing Swift-issued authority grant for staging", stage_state=StageState.DENIED)
            result = self.action_lifecycle.stage(
                candidate,
                observation,
                grant,
                requested_authority_tier=call.requested_authority_tier,
                trace_id=call.correlation_id or candidate.candidate_id,
                causal_parent_id=call.tool_call_id,
            )
            status = CodexToolStatus.DENIED if result.denied_reason else CodexToolStatus.STAGEABLE
            return self._receipt(
                call,
                status,
                result.output_payload(),
                swift_receipt_id=result.swift_receipt.receipt_id if result.swift_receipt else None,
                requires_confirmation=result.requires_confirmation,
                denied=result.denied_reason,
                stage_state=result.stage_state,
                authority_grant=grant,
                correlation_id=call.correlation_id or candidate.candidate_id,
            )
        if name == CodexToolName.REQUEST_COMMIT:
            candidate = self._candidate_from_input(call)
            grant = self._resolve_grant(call)
            if grant is None:
                return self._receipt(call, CodexToolStatus.DENIED, {"stage_state": StageState.DENIED.value}, denied="missing Swift-issued authority grant for commit", stage_state=StageState.DENIED)
            result = self.action_lifecycle.commit(
                candidate,
                observation,
                grant,
                requested_authority_tier=call.requested_authority_tier,
                trace_id=call.correlation_id or candidate.candidate_id,
                causal_parent_id=call.tool_call_id,
                require_live_observation=True,
            )
            status = CodexToolStatus.DENIED if result.denied_reason else CodexToolStatus.COMMITTED
            return self._receipt(
                call,
                status,
                result.output_payload(),
                swift_receipt_id=result.swift_receipt.receipt_id if result.swift_receipt else None,
                denied=result.denied_reason,
                stage_state=result.stage_state,
                authority_grant=grant,
                correlation_id=call.correlation_id or candidate.candidate_id,
            )
        if name == CodexToolName.REQUEST_UNDO:
            rollback_id = str(call.input.get("rollback_handle_id", ""))
            grant = self._resolve_grant(call)
            result = self.action_lifecycle.undo(
                rollback_id,
                observation,
                grant,
                requested_authority_tier=call.requested_authority_tier,
                trace_id=call.correlation_id or rollback_id,
                causal_parent_id=call.tool_call_id,
            )
            if result.status == "failed":
                status = CodexToolStatus.FAILED
            else:
                status = CodexToolStatus.DENIED if result.denied_reason else CodexToolStatus.REVERTED
            return self._receipt(
                call,
                status,
                result.output_payload(),
                swift_receipt_id=result.swift_receipt.receipt_id if result.swift_receipt else None,
                denied=result.denied_reason,
                stage_state=result.stage_state,
                authority_grant=grant,
                correlation_id=call.correlation_id or rollback_id,
            )
        if name == CodexToolName.QUERY_REPLAY_TRACE:
            return self._receipt(call, CodexToolStatus.SUCCEEDED, self._query_replay(call))
        if name == CodexToolName.INSPECT_PROFILE_CLAIMS:
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"claims": biography.preference_claims, "updates": biography.profile_update_events[-5:]})
        if name == CodexToolName.PROPOSE_PROFILE_PATCH:
            correction = str(call.input.get("correction", ""))
            plan = self.biography_store.propose_repair(biography, correction)
            return self._receipt(call, CodexToolStatus.REQUIRES_CONFIRMATION, {"repair_plan": to_jsonable(plan)}, requires_confirmation=True)
        if name == CodexToolName.APPLY_PROFILE_PATCH:
            if not bool(call.input.get("confirmed", False)):
                return self._receipt(call, CodexToolStatus.REQUIRES_CONFIRMATION, {"message": "profile patch requires explicit confirmation"}, requires_confirmation=True)
            claim = str(call.input.get("claim", ""))
            correction = str(call.input.get("correction", ""))
            updated = self.biography_store.apply_user_correction(biography, claim, correction)
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"biography": updated.to_dict(), "last_update": updated.profile_update_events[-1]})
        if name == CodexToolName.RUN_SELF_PLAY_PROBE:
            episodes = int(call.input.get("episodes", 3))
            backend_raw = str(call.input.get("backend", call.input.get("self_play_backend", "stub_fast")) or "stub_fast")
            from calendar_pilot.environment.selfplay_backends import SelfPlayActionBackend
            backend = SelfPlayActionBackend(backend_raw)
            grant = self._resolve_grant(call)
            runner = SelfPlayRunner(
                policy=self.policy,
                kernel=self.kernel,
                replay=self.replay,
                action_backend=backend,
                provider=self.provider if backend != SelfPlayActionBackend.STUB_FAST else None,
            )
            metrics = runner.run(observation, biography, episodes=episodes, authority_grant=grant.grant_id if grant else None)
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"metrics": to_jsonable(metrics), "top_failure_modes": metrics.top_failure_modes, "backend": backend.value}, authority_grant=grant, correlation_id=call.correlation_id)
        if name == CodexToolName.PROPOSE_AUTONOMY_SCOPE:
            candidate = self._candidate_from_input(call)
            proposal = self._autonomy_scope(candidate)
            return self._receipt(call, CodexToolStatus.REQUIRES_CONFIRMATION, {"scope_proposal": proposal.to_dict()}, requires_confirmation=True)
        if name == CodexToolName.EXPLAIN_SWIFT_DENIAL:
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"denial_explanation": self._denial_explanation(str(call.input.get("denied_reason", "")))})
        if name == CodexToolName.VALIDATE_MODEL_PLAN:
            return self._validate_model_plan(call)
        return self._receipt(call, CodexToolStatus.DENIED, {}, denied=f"unsupported tool {name.value}")

    def _validate_model_plan(self, call: CodexToolCall) -> CodexToolReceipt:
        errors: list[str] = []
        calls = call.input.get("calls")
        candidates = call.input.get("candidates")
        if calls is not None:
            if not isinstance(calls, list) or not calls:
                errors.append("calls must be a non-empty list when supplied")
            else:
                seen_frontier = False
                seen_compare = False
                terminal: str | None = None
                for idx, row in enumerate(calls):
                    if not isinstance(row, dict):
                        errors.append(f"calls[{idx}] is not an object")
                        continue
                    tool = str(row.get("tool_name") or row.get("tool") or "")
                    if terminal is not None:
                        errors.append(f"{tool} appears after terminal tool {terminal}")
                    if tool == CodexToolName.GENERATE_CANDIDATE_FRONTIER.value:
                        seen_frontier = True
                    if tool == CodexToolName.COMPARE_CANDIDATES.value:
                        if not seen_frontier:
                            errors.append("compare_candidates appeared before generate_candidate_frontier")
                        seen_compare = True
                    if tool in {CodexToolName.SIMULATE_ACTION_PROGRAM.value, CodexToolName.STAGE_ACTION_PACKET.value, CodexToolName.REQUEST_COMMIT.value} and not seen_compare:
                        errors.append(f"{tool} appeared before compare_candidates")
                    if tool in {CodexToolName.STAGE_ACTION_PACKET.value, CodexToolName.REQUEST_COMMIT.value, CodexToolName.REQUEST_UNDO.value}:
                        terminal = tool
        if candidates is not None:
            if not isinstance(candidates, list) or not candidates:
                errors.append("candidates must be a non-empty list when supplied")
            else:
                for idx, payload in enumerate(candidates):
                    if not isinstance(payload, dict):
                        errors.append(f"candidates[{idx}] is not an object")
                        continue
                    try:
                        candidate = CandidateCalendarAction.from_dict(payload)
                    except Exception as exc:
                        errors.append(f"candidates[{idx}] failed CandidateCalendarAction validation: {exc}")
                        continue
                    if not candidate.actions:
                        errors.append(f"candidate {candidate.candidate_id} has no actions")
                    if not candidate.target_calendars:
                        errors.append(f"candidate {candidate.candidate_id} has no target_calendars")
        if not errors:
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"validated": True, "source": "codex_tool_runtime", "checked": ["tool_plan", "candidate_frontier"]})
        return self._receipt(call, CodexToolStatus.FAILED, {"validated": False, "errors": errors, "source": "codex_tool_runtime"}, denied="model_plan_validation_failed")

    def _generate_frontier(self, call: CodexToolCall, observation: RawCalendarObservation, biography: UserBiography) -> CodexToolReceipt:
        limit = int(call.input.get("limit", 5))
        goal = str(call.input.get("goal") or "").strip()
        self.frontier.clear()
        try:
            generate_candidates = self.policy.generate_candidates
            params = inspect.signature(generate_candidates).parameters
            accepts_goal = "goal" in params or any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values())
            if accepts_goal:
                candidates = generate_candidates(observation, biography, goal=goal or None)[:limit]
            else:
                candidates = generate_candidates(observation, biography)[:limit]
        except LiveDiffusionGemmaError as exc:
            return self._receipt(
                call,
                CodexToolStatus.FAILED,
                {
                    "error_category": exc.category,
                    "message": str(exc),
                    "recovery": self._live_diffusiongemma_recovery(exc),
                },
                denied=str(exc),
            )
        policy_version = getattr(self.policy, "backend_name", "heuristic_diffusiongemma_policy")
        policy_metadata_for_candidate = getattr(self.policy, "policy_metadata_for_candidate", None)
        for rank, candidate in enumerate(candidates):
            self.frontier[candidate.candidate_id] = candidate
            policy_metadata = policy_metadata_for_candidate(candidate.candidate_id) if callable(policy_metadata_for_candidate) else {}
            self.replay.append_decision(
                candidate,
                rank=rank,
                policy_version=policy_version,
                trace_id=call.correlation_id or call.tool_call_id,
                causal_parent_id=call.tool_call_id,
                policy_metadata=policy_metadata,
                observation_id=observation.observation_id,
                observation_fingerprint=observation_fingerprint(observation),
            )
            validation = policy_metadata.get("validation") if isinstance(policy_metadata, dict) else None
            if rank == 0 and isinstance(validation, dict):
                for rejection in validation.get("rejections", []) or []:
                    if isinstance(rejection, dict):
                        self.replay.append_model_generation_rejection(rejection, trace_id=call.correlation_id or call.tool_call_id, causal_parent_id=call.tool_call_id)
        return self._receipt(
            call,
            CodexToolStatus.SUCCEEDED,
            {
                "candidate_count": len(candidates),
                "candidates": [c.to_dict() for c in candidates],
                "frontier_ids": [c.candidate_id for c in candidates],
                "goal": goal,
                "goal_routed_to_policy": accepts_goal,
            },
        )

    def _simulate(self, call: CodexToolCall, candidate: CandidateCalendarAction, observation: RawCalendarObservation) -> CodexToolReceipt:
        grant = self._resolve_grant(call)
        result = self.action_lifecycle.simulate(
            candidate,
            observation,
            grant,
            requested_authority_tier=call.requested_authority_tier,
            trace_id=call.correlation_id or candidate.candidate_id,
            causal_parent_id=call.tool_call_id,
        )
        return self._receipt(
            call,
            CodexToolStatus.SIMULATED if result.denied_reason is None else CodexToolStatus.DENIED,
            result.output_payload(),
            swift_receipt_id=result.swift_receipt.receipt_id if result.swift_receipt else None,
            denied=result.denied_reason,
            stage_state=result.stage_state,
            authority_grant=grant,
            correlation_id=call.correlation_id or candidate.candidate_id,
        )

    def _compare(self, call: CodexToolCall) -> CodexToolReceipt:
        requested_ids = call.input.get("candidate_ids")
        ids = [str(x) for x in requested_ids] if isinstance(requested_ids, list) else []
        candidates = [self.frontier[i] for i in ids if i in self.frontier]
        if not candidates and "candidate_ids" not in call.input:
            candidates = sorted(self.frontier.values(), key=lambda c: c.expected_reward, reverse=True)[:5]
        rows = []
        for c in candidates:
            robust_score = c.expected_reward - c.predicted_regret * 1.2 - c.predicted_social_risk * 1.5 - c.predicted_interruption_cost * 0.3
            rows.append({
                "candidate_id": c.candidate_id,
                "intent": c.intent,
                "expected_reward": c.expected_reward,
                "robust_score": round(robust_score, 4),
                "authority_tier": c.required_authority_tier,
                "right_moment": c.right_moment_decision.value,
                "control_notes": c.control_notes,
            })
        rows.sort(key=lambda r: r["robust_score"], reverse=True)
        return self._receipt(call, CodexToolStatus.SUCCEEDED, {"ranking": rows, "winner": rows[0] if rows else None})

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
            return {
                "provider": getattr(self.provider, "provider_id", "unknown_provider"),
                "configured": False,
                "status": "swift_ipc_required_for_live_provider",
                "kernel": type(self.kernel).__name__,
            }
        expected_observation_id = getattr(self.provider, "observation_id", None)
        if require_live_observation and expected_observation_id and observation is not None and observation.observation_id != expected_observation_id:
            return {
                "provider": getattr(self.provider, "provider_id", "unknown_provider"),
                "configured": False,
                "status": "provider_observation_not_loaded",
                "expected_observation_id": expected_observation_id,
                "actual_observation_id": observation.observation_id,
            }
        health_status = getattr(self.provider, "health_status", None)
        if not callable(health_status):
            return {"provider": getattr(self.provider, "provider_id", "unknown_provider"), "configured": False, "status": "health_unavailable"}
        health = dict(health_status())
        if health.get("configured"):
            return None
        return health

    def _real_provider_active(self) -> bool:
        return bool(getattr(self.provider, "real_provider", False) or getattr(self.provider, "real_oauth", False))

    def _commit_to_provider(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, observation: RawCalendarObservation):
        commit_candidate = getattr(self.provider, "commit_candidate", None)
        if not callable(commit_candidate):
            return None
        try:
            return commit_candidate(candidate, receipt, observation)
        except CalendarProviderError as exc:
            raise RuntimeError(f"provider write failed: {exc}") from exc

    def _rollback_provider(self, rollback_handle_id: str):
        rollback = getattr(self.provider, "rollback", None)
        if not callable(rollback):
            return None
        try:
            return rollback(rollback_handle_id)
        except CalendarProviderError as exc:
            raise RuntimeError(f"provider rollback failed: {exc}") from exc

    def _candidate_from_input(self, call: CodexToolCall) -> CandidateCalendarAction:
        candidate_id = call.input.get("candidate_id")
        if candidate_id and str(candidate_id) in self.frontier:
            return self.frontier[str(candidate_id)]
        if "candidate" in call.input:
            candidate = CandidateCalendarAction.from_dict(dict(call.input["candidate"]))
            self.frontier[candidate.candidate_id] = candidate
            return candidate
        raise ValueError("candidate_id or candidate payload required")

    @staticmethod
    def _inspect_week(observation: RawCalendarObservation, biography: UserBiography, *, redact_raw_events: bool = False) -> dict[str, Any]:
        signals = extract_signals(observation, biography)
        return {
            "observation_id": observation.observation_id,
            "event_count": len(observation.events),
            "task_count": len(observation.tasks),
            "pressure_score": round(signals.pressure_score, 4),
            "fatigue_score": round(signals.fatigue_score, 4),
            "risk_cliffs": signals.risk_cliffs,
            "open_slot_count": len(signals.open_slots),
            "raw_events": [] if redact_raw_events else [CodexToolRuntime._event_dict(e) for e in observation.events],
            "raw_events_redacted": redact_raw_events,
            "redaction_reason": "real_provider_replay_privacy" if redact_raw_events else None,
            "best_response_hours": biography.best_response_hours,
        }

    @staticmethod
    def _event_dict(event: RawCalendarEvent, *, redact_private: bool = False) -> dict[str, Any]:
        if redact_private:
            return {
                "event_id": event.event_id,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "calendar_id": event.calendar_id,
                "attendees_count": len(event.attendees),
                "category": event.category,
                "is_user_owned": event.is_user_owned,
                "is_flexible": event.is_flexible,
                "redacted": True,
                "redaction_reason": "real_provider_replay_privacy",
            }
        return {
            "event_id": event.event_id,
            "title": event.title,
            "start": event.start.isoformat(),
            "end": event.end.isoformat(),
            "calendar_id": event.calendar_id,
            "attendees": event.attendees,
            "attendees_count": len(event.attendees),
            "location": event.location,
            "category": event.category,
            "is_user_owned": event.is_user_owned,
            "is_flexible": event.is_flexible,
        }

    def _authority_scope(self, call: CodexToolCall) -> dict[str, Any]:
        grant = self._resolve_grant(call)
        tier = grant.max_authority_tier if grant else 0
        return {
            "authority_grant_id": grant.grant_id if grant else None,
            "requested_authority_tier": call.requested_authority_tier,
            "max_authority_tier": tier,
            "grant_scopes": grant.scopes if grant else [],
            "grant_expires_at": grant.expires_at.isoformat() if grant else None,
            "confirmation_provenance": grant.confirmation_provenance if grant else None,
            "can_recommend": tier >= 1,
            "can_stage": tier >= 2 and bool(grant and grant.allows_scope("stage")),
            "can_auto_write_reversible_private": tier >= 3 and bool(grant and grant.allows_scope("commit_private")),
            "can_social_actuate": tier >= 5 and bool(grant and grant.allows_scope("commit_social")),
            "provider_write_access": "swift_only",
            "codex_direct_provider_access": False,
        }

    @staticmethod
    def _autonomy_scope(candidate: CandidateCalendarAction) -> CodexAutonomyScopeProposal:
        digest = hashlib.sha1(candidate.candidate_id.encode()).hexdigest()[:10]
        action_types = sorted({a.action_type.value for a in candidate.actions})
        return CodexAutonomyScopeProposal(
            scope_id=f"scope_{digest}",
            candidate_id=candidate.candidate_id,
            allowed_action_types=action_types,
            max_authority_tier=min(candidate.required_authority_tier, 3 if candidate.affected_people_ids else candidate.required_authority_tier),
            excluded_social_mutations=bool(candidate.affected_people_ids),
            requires_confirmation_for_people=bool(candidate.affected_people_ids),
            rollback_required=candidate.reversibility.value != "none",
            reason="narrow scope generated by Codex: permit the private/reversible part, keep people-affecting mutation behind confirmation",
        )

    def _query_replay(self, call: CodexToolCall) -> dict[str, Any]:
        candidate_id = call.input.get("candidate_id")
        summary = self.replay.summarize()
        traces = []
        if candidate_id:
            for record in self.replay.records:
                cand = record.payload.get("candidate", {})
                if cand.get("candidate_id") == candidate_id:
                    traces.append({"record_type": record.record_type, "payload": record.payload})
        return {"summary": to_jsonable(summary), "traces": traces[-10:]}

    @staticmethod
    def _live_diffusiongemma_recovery(exc: LiveDiffusionGemmaError) -> str:
        if exc.category == "missing_or_invalid_credential":
            return "Configure NVIDIA NIM credentials for live_diffusiongemma mode or switch CALENDAR_PILOT_RUNTIME_MODE back to fixture."
        if exc.category == "model_policy_schema_failure":
            return "NIM was reached but did not return a valid typed candidate frontier after schema retry; retry the turn or inspect the replay/model receipt before staging."
        if exc.category == "network_failure":
            return "NIM credentials are configured, but the remote request failed; retry when the NVIDIA endpoint is reachable."
        return "NIM returned a live runtime error; inspect the model receipt before staging or committing."

    def _resolve_grant(self, call: CodexToolCall):
        # Canonical boundary: Codex carries only a grant id. Embedded grant
        # objects are deliberately ignored so authority must be resolved from
        # the Swift/kernel-issued registry.
        grant_id = call.authority_grant_id or call.input.get("authority_grant_id")
        if isinstance(grant_id, str):
            return self.kernel.resolve_authority_grant(grant_id)
        return None

    @staticmethod
    def _denial_explanation(reason: str) -> str:
        if "social actuation" in reason or "commit_social" in reason:
            return "Swift requires a live tier-5 social actuation grant with commit_social scope before Codex can commit people-affecting calendar mutations."
        if "authority tier" in reason:
            return "The requested machine act exceeds the granted autonomy tier. Codex can propose a narrower scope or stage a draft."
        if "conflict" in reason:
            return "Swift found a live calendar conflict. Simulate alternatives before requesting commit."
        if "auto_apply_plan" in reason:
            return "Swift requires a tier-6 grant with auto_apply_plan scope before Codex can commit a compound optimizer plan."
        return reason or "No denial reason was supplied."

    @staticmethod
    def _receipt(
        call: CodexToolCall,
        status: CodexToolStatus,
        output: dict[str, Any],
        *,
        swift_receipt_id: str | None = None,
        denied: str | None = None,
        requires_confirmation: bool = False,
        stage_state: StageState = StageState.NO_OP,
        authority_grant: AuthorityGrant | None = None,
        correlation_id: str | None = None,
    ) -> CodexToolReceipt:
        output_payload = to_jsonable(output)
        envelope = CodexToolRuntime._canonical_action_envelope(
            call=call,
            status=status,
            output=output_payload,
            swift_receipt_id=swift_receipt_id,
            denied=denied,
            stage_state=stage_state,
            authority_grant=authority_grant,
            correlation_id=correlation_id or call.correlation_id,
        )
        if envelope is not None:
            output_payload.setdefault("action_envelope", envelope)
        return CodexToolReceipt(
            tool_call_id=call.tool_call_id,
            tool_name=call.tool_name,
            status=status,
            output=output_payload,
            swift_receipt_id=swift_receipt_id,
            denied_reason=denied,
            requires_user_confirmation=requires_confirmation,
            stage_state=stage_state,
            authority_grant_id=authority_grant.grant_id if authority_grant else None,
            correlation_id=correlation_id or call.correlation_id,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _canonical_action_envelope(
        *,
        call: CodexToolCall,
        status: CodexToolStatus,
        output: dict[str, Any],
        swift_receipt_id: str | None,
        denied: str | None,
        stage_state: StageState,
        authority_grant: AuthorityGrant | None,
        correlation_id: str | None,
    ) -> dict[str, Any] | None:
        candidate = output.get("candidate") if isinstance(output.get("candidate"), dict) else None
        swift_receipt = output.get("swift_receipt") if isinstance(output.get("swift_receipt"), dict) else None
        provider_receipt = output.get("provider_receipt") if isinstance(output.get("provider_receipt"), dict) else None
        provider_rollback = output.get("provider_rollback") if isinstance(output.get("provider_rollback"), dict) else None
        action_tools = {
            CodexToolName.SIMULATE_ACTION_PROGRAM,
            CodexToolName.STAGE_ACTION_PACKET,
            CodexToolName.REQUEST_COMMIT,
            CodexToolName.REQUEST_UNDO,
        }
        if candidate is None and swift_receipt is None and provider_receipt is None and provider_rollback is None and call.tool_name not in action_tools:
            return None
        candidate_id = (
            str(candidate.get("candidate_id"))
            if candidate and candidate.get("candidate_id")
            else str(swift_receipt.get("candidate_id"))
            if swift_receipt and swift_receipt.get("candidate_id")
            else None
        )
        rollback_handle = (
            (swift_receipt or {}).get("rollback_handle_id")
            or (provider_receipt or {}).get("rollback_handle_id")
            or (provider_rollback or {}).get("rollback_handle_id")
        )
        provider_payload = provider_receipt or provider_rollback
        trace_id = correlation_id or call.correlation_id or call.tool_call_id
        transition = {
            CodexToolName.SIMULATE_ACTION_PROGRAM: "simulate",
            CodexToolName.STAGE_ACTION_PACKET: "stage",
            CodexToolName.REQUEST_COMMIT: "commit",
            CodexToolName.REQUEST_UNDO: "undo",
        }.get(call.tool_name, call.tool_name.value)
        rollback_state = rollback_state_from_receipt(swift_receipt, provider_rollback)
        return {
            "schema_version": "calendar_action_envelope.v1",
            "envelope_version": "calendar_action_envelope.v2",
            "envelope_id": "env_" + hashlib.sha1(f"{trace_id}|{candidate_id}|{call.tool_call_id}".encode("utf-8")).hexdigest()[:12],
            "trace_id": trace_id,
            "candidate_id": candidate_id,
            "tool_call_id": call.tool_call_id,
            "tool_name": call.tool_name.value,
            "tool_status": status.value,
            "current_state": transition,
            "authority": {
                "grant_id": (authority_grant.grant_id if authority_grant else None) or call.authority_grant_id,
                "tier": call.requested_authority_tier,
                "scopes": authority_grant.scopes if authority_grant else [],
                "confirmation_provenance": authority_grant.confirmation_provenance if authority_grant else None,
            },
            "authority_grant_id": (authority_grant.grant_id if authority_grant else None) or call.authority_grant_id,
            "action_program_digest": CodexToolRuntime._action_program_digest(candidate),
            "stage_state": (swift_receipt or {}).get("stage_state", stage_state.value),
            "sync_status": (swift_receipt or {}).get("sync_status"),
            "swift_receipt_id": swift_receipt_id or (swift_receipt or {}).get("receipt_id"),
            "provider": {
                "provider_id": (provider_payload or {}).get("provider_id") or (swift_receipt or {}).get("provider_id"),
                "provider_status": (provider_payload or {}).get("status"),
                "provider_transaction_id": (provider_payload or {}).get("idempotency_key"),
                "external_event_ids": (provider_payload or {}).get("external_ids") or (swift_receipt or {}).get("generated_event_ids") or [],
                "rollback_handle_id": rollback_handle,
                "rollback_verified": (provider_rollback or {}).get("rollback_verified") if provider_rollback else output.get("rollback_verified"),
                "rollback_state": rollback_state,
            },
            "lifecycle": [{
                "transition": transition,
                "at": datetime.now(timezone.utc).isoformat(),
                "status": status.value,
                "swift_receipt_id": swift_receipt_id or (swift_receipt or {}).get("receipt_id"),
                "detail": {"denied_reason": denied, "stage_state": (swift_receipt or {}).get("stage_state", stage_state.value)},
            }],
            "provider_id": (provider_payload or {}).get("provider_id") or (swift_receipt or {}).get("provider_id"),
            "provider_status": (provider_payload or {}).get("status"),
            "provider_transaction_id": (provider_payload or {}).get("idempotency_key"),
            "external_event_ids": (provider_payload or {}).get("external_ids") or (swift_receipt or {}).get("generated_event_ids") or [],
            "rollback_handle_id": rollback_handle,
            "rollback_verified": (provider_rollback or {}).get("rollback_verified") if provider_rollback else output.get("rollback_verified"),
            "rollback_state": rollback_state,
            "denied_reason": denied,
            "swift_receipt": swift_receipt,
            "provider_receipt": provider_receipt,
            "provider_rollback": provider_rollback,
            "replay_record_ids": [],
            "reward_events": [],
        }

    @staticmethod
    def _action_program_digest(candidate: dict[str, Any] | None) -> str | None:
        if not candidate:
            return None
        actions = candidate.get("actions", [])
        raw = json.dumps(actions, sort_keys=True, separators=(",", ":"))
        return "ap_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
