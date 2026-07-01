from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from typing import Any

from calendar_pilot.biography import BiographyStore
from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.self_play import SelfPlayRunner
from calendar_pilot.diffusiongemma.signals import extract_signals
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.types import (
    CalendarActionReceipt,
    CandidateCalendarAction,
    CodexAutonomyScopeProposal,
    CodexToolCall,
    CodexToolName,
    CodexToolReceipt,
    CodexToolStatus,
    RawCalendarEvent,
    RawCalendarObservation,
    UserBiography,
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
        kernel: SwiftKernelStub | None = None,
        replay: ReplayBuffer | None = None,
        biography_store: BiographyStore | None = None,
    ) -> None:
        self.policy = policy or DiffusionGemmaPolicy()
        self.kernel = kernel or SwiftKernelStub()
        self.replay = replay or ReplayBuffer()
        self.biography_store = biography_store or BiographyStore()
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
        return receipt

    def _execute_inner(
        self,
        call: CodexToolCall,
        observation: RawCalendarObservation,
        biography: UserBiography,
    ) -> CodexToolReceipt:
        name = call.tool_name
        if name == CodexToolName.INSPECT_WEEK:
            return self._receipt(call, CodexToolStatus.SUCCEEDED, self._inspect_week(observation, biography))
        if name == CodexToolName.INSPECT_EVENT:
            event_id = str(call.input.get("event_id", ""))
            event = next((e for e in observation.events if e.event_id == event_id), None)
            if event is None:
                return self._receipt(call, CodexToolStatus.DENIED, {}, denied="event not found")
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"event": self._event_dict(event)})
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
            swift_receipt = self.kernel.stage_candidate(candidate, observation, requested_authority_tier=call.requested_authority_tier)
            self.replay.append_receipt(swift_receipt, candidate)
            return self._receipt(
                call,
                CodexToolStatus.STAGED,
                {"candidate": candidate.to_dict(), "swift_receipt": swift_receipt.to_dict()},
                swift_receipt_id=swift_receipt.receipt_id,
                requires_confirmation=True,
                denied=swift_receipt.denied_reason,
            )
        if name == CodexToolName.REQUEST_COMMIT:
            candidate = self._candidate_from_input(call)
            swift_receipt = self.kernel.authorize_and_materialize(candidate, observation, call.requested_authority_tier)
            self.replay.append_receipt(swift_receipt, candidate)
            status = CodexToolStatus.DENIED if swift_receipt.denied_reason else CodexToolStatus.SUCCEEDED
            return self._receipt(
                call,
                status,
                {"candidate": candidate.to_dict(), "swift_receipt": swift_receipt.to_dict()},
                swift_receipt_id=swift_receipt.receipt_id,
                denied=swift_receipt.denied_reason,
            )
        if name == CodexToolName.REQUEST_UNDO:
            rollback_id = str(call.input.get("rollback_handle_id", ""))
            output = self.kernel.request_undo(rollback_id, observation)
            self.replay.append_receipt(output)
            status = CodexToolStatus.DENIED if output.denied_reason else CodexToolStatus.SUCCEEDED
            return self._receipt(call, status, {"swift_receipt": output.to_dict()}, swift_receipt_id=output.receipt_id, denied=output.denied_reason)
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
            runner = SelfPlayRunner(policy=self.policy, kernel=self.kernel, replay=self.replay)
            metrics = runner.run(observation, biography, episodes=episodes, authority_tier=call.requested_authority_tier or 3)
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"metrics": to_jsonable(metrics), "top_failure_modes": metrics.top_failure_modes})
        if name == CodexToolName.PROPOSE_AUTONOMY_SCOPE:
            candidate = self._candidate_from_input(call)
            proposal = self._autonomy_scope(candidate)
            return self._receipt(call, CodexToolStatus.REQUIRES_CONFIRMATION, {"scope_proposal": proposal.to_dict()}, requires_confirmation=True)
        if name == CodexToolName.EXPLAIN_SWIFT_DENIAL:
            return self._receipt(call, CodexToolStatus.SUCCEEDED, {"denial_explanation": self._denial_explanation(str(call.input.get("denied_reason", "")))})
        return self._receipt(call, CodexToolStatus.DENIED, {}, denied=f"unsupported tool {name.value}")

    def _generate_frontier(self, call: CodexToolCall, observation: RawCalendarObservation, biography: UserBiography) -> CodexToolReceipt:
        limit = int(call.input.get("limit", 5))
        candidates = self.policy.generate_candidates(observation, biography)[:limit]
        for rank, candidate in enumerate(candidates):
            self.frontier[candidate.candidate_id] = candidate
            self.replay.append_decision(candidate, rank=rank, policy_version="codex_tool_frontier")
        return self._receipt(
            call,
            CodexToolStatus.SUCCEEDED,
            {
                "candidate_count": len(candidates),
                "candidates": [c.to_dict() for c in candidates],
                "frontier_ids": [c.candidate_id for c in candidates],
            },
        )

    def _simulate(self, call: CodexToolCall, candidate: CandidateCalendarAction, observation: RawCalendarObservation) -> CodexToolReceipt:
        preview = self.kernel.preview_candidate(candidate, observation, requested_authority_tier=call.requested_authority_tier)
        social = bool(candidate.affected_people_ids)
        output = {
            "candidate": candidate.to_dict(),
            "simulation_only": True,
            "would_sync_status": preview.sync_status,
            "would_actuation_mode": preview.actuation_mode.value,
            "would_denied_reason": preview.denied_reason,
            "would_require_confirmation": social or candidate.required_authority_tier > call.requested_authority_tier,
            "counterfactual": candidate.counterfactual,
            "reward_breakdown": candidate.reward_breakdown,
            "right_moment": candidate.right_moment_decision.value,
        }
        return self._receipt(call, CodexToolStatus.SUCCEEDED, output, denied=preview.denied_reason)

    def _compare(self, call: CodexToolCall) -> CodexToolReceipt:
        ids = [str(x) for x in call.input.get("candidate_ids", [])]
        candidates = [self.frontier[i] for i in ids if i in self.frontier]
        if not candidates:
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
    def _inspect_week(observation: RawCalendarObservation, biography: UserBiography) -> dict[str, Any]:
        signals = extract_signals(observation, biography)
        return {
            "observation_id": observation.observation_id,
            "event_count": len(observation.events),
            "task_count": len(observation.tasks),
            "pressure_score": round(signals.pressure_score, 4),
            "fatigue_score": round(signals.fatigue_score, 4),
            "risk_cliffs": signals.risk_cliffs,
            "open_slot_count": len(signals.open_slots),
            "raw_events": [CodexToolRuntime._event_dict(e) for e in observation.events],
            "best_response_hours": biography.best_response_hours,
        }

    @staticmethod
    def _event_dict(event: RawCalendarEvent) -> dict[str, Any]:
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

    @staticmethod
    def _authority_scope(call: CodexToolCall) -> dict[str, Any]:
        tier = call.requested_authority_tier
        return {
            "granted_authority_tier": tier,
            "can_recommend": tier >= 1,
            "can_stage": tier >= 2,
            "can_auto_write_reversible_private": tier >= 3,
            "can_social_actuate": tier >= 5,
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
    def _denial_explanation(reason: str) -> str:
        if "social actuation" in reason:
            return "Swift refused because the packet would mutate another person's calendar reality. Stage it or ask for explicit confirmation."
        if "authority tier" in reason:
            return "The requested machine act exceeds the granted autonomy tier. Codex can propose a narrower scope or stage a draft."
        if "conflict" in reason:
            return "Swift found a live calendar conflict. Simulate alternatives before requesting commit."
        if "auto_apply_plan" in reason:
            return "Multi-step auto-apply is intentionally outside kernel-v1; stage the plan and request confirmation."
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
    ) -> CodexToolReceipt:
        return CodexToolReceipt(
            tool_call_id=call.tool_call_id,
            tool_name=call.tool_name,
            status=status,
            output=to_jsonable(output),
            swift_receipt_id=swift_receipt_id,
            denied_reason=denied,
            requires_user_confirmation=requires_confirmation,
            created_at=datetime.now(timezone.utc),
        )
