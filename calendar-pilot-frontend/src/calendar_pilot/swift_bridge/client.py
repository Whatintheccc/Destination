from __future__ import annotations

from datetime import datetime
import hashlib

from calendar_pilot.types import (
    ActuationMode,
    AtomicActionType,
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarObservation,
    Reversibility,
)


STAGED_ACTIONS = {
    AtomicActionType.DRAFT_SCHEDULE_PLAN,
    AtomicActionType.NOTIFY,
    AtomicActionType.ASK_CLARIFICATION,
}

WRITE_ACTIONS = {
    AtomicActionType.CREATE_EVENT,
    AtomicActionType.CREATE_FOCUS_BLOCK,
    AtomicActionType.ADD_BUFFER,
    AtomicActionType.BATCH_TASKS,
    AtomicActionType.MOVE_EVENT,
    AtomicActionType.RESIZE_EVENT,
    AtomicActionType.DELETE_OWN_EVENT,
}

SOCIAL_MUTATION_ACTIONS = {
    AtomicActionType.MOVE_EVENT,
    AtomicActionType.RESIZE_EVENT,
    AtomicActionType.DELETE_OWN_EVENT,
    AtomicActionType.AUTO_APPLY_PLAN,
}


class SwiftKernelStub:
    """Python mirror of the Swift authority broker.

    This is intentionally conservative: DiffusionGemma proposes, Swift either
    materializes a typed write, stages a non-write actuation, or emits a denial
    receipt with enough structure for replay/offline learning.
    """

    def authorize_and_materialize(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        granted_authority_tier: int,
    ) -> CalendarActionReceipt:
        denied = self._denied_reason(candidate, observation, granted_authority_tier)
        generated_ids: list[str] = []
        staged_ids: list[str] = []
        rejected_types: list[str] = []
        rollback = None
        mode = ActuationMode.NO_OP
        sync_status = "materialized"

        if denied is not None:
            sync_status = "denied"
            mode = ActuationMode.DENIED
            rejected_types = [a.action_type.value for a in candidate.actions]
        else:
            for idx, action in enumerate(candidate.actions):
                if action.action_type in {AtomicActionType.CREATE_EVENT, AtomicActionType.CREATE_FOCUS_BLOCK, AtomicActionType.ADD_BUFFER, AtomicActionType.BATCH_TASKS}:
                    generated_ids.append(self._event_id(candidate.candidate_id, idx))
                    mode = ActuationMode.MATERIALIZED_WRITE
                elif action.action_type in {AtomicActionType.MOVE_EVENT, AtomicActionType.RESIZE_EVENT, AtomicActionType.DELETE_OWN_EVENT}:
                    mode = ActuationMode.MATERIALIZED_WRITE
                elif action.action_type in STAGED_ACTIONS:
                    staged_ids.append(self._stage_id(candidate.candidate_id, idx, action.action_type.value))
                    mode = ActuationMode.STAGED_NOTIFICATION if action.action_type == AtomicActionType.NOTIFY else ActuationMode.STAGED_DRAFT
                elif action.action_type == AtomicActionType.DO_NOTHING:
                    mode = ActuationMode.NO_OP
                elif action.action_type in {AtomicActionType.AUTO_APPLY_PLAN, AtomicActionType.UNDO}:
                    rejected_types.append(action.action_type.value)

            if staged_ids and not generated_ids:
                sync_status = "staged"
            rollback = self._rollback_id(candidate.candidate_id) if candidate.reversibility != Reversibility.NONE and mode == ActuationMode.MATERIALIZED_WRITE else None

        return CalendarActionReceipt(
            receipt_id="rcpt_" + hashlib.sha1((candidate.candidate_id + str(datetime.now())).encode()).hexdigest()[:12],
            candidate_id=candidate.candidate_id,
            executed_at=observation.observed_at,
            executed_by="SwiftKernelStub",
            authority_tier_used=min(granted_authority_tier, candidate.required_authority_tier),
            sync_status=sync_status,
            rollback_handle_id=rollback,
            conflict_check_passed=denied != "conflict_detected",
            generated_event_ids=generated_ids,
            staged_action_ids=staged_ids,
            rejected_action_types=rejected_types,
            provider_id="local_stub",
            actuation_mode=mode,
            denied_reason=denied,
        )


    def preview_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        requested_authority_tier: int,
    ) -> CalendarActionReceipt:
        """Dry-run Swift authority/materialization without committing provider state."""
        receipt = self.authorize_and_materialize(candidate, observation, requested_authority_tier)
        return CalendarActionReceipt(
            receipt_id="preview_" + receipt.receipt_id,
            candidate_id=receipt.candidate_id,
            executed_at=receipt.executed_at,
            executed_by="SwiftKernelStub.preview",
            authority_tier_used=receipt.authority_tier_used,
            sync_status=receipt.sync_status,
            rollback_handle_id=None,
            conflict_check_passed=receipt.conflict_check_passed,
            generated_event_ids=[],
            staged_action_ids=receipt.staged_action_ids,
            rejected_action_types=receipt.rejected_action_types,
            provider_id=receipt.provider_id,
            actuation_mode=receipt.actuation_mode,
            denied_reason=receipt.denied_reason,
        )

    def stage_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        requested_authority_tier: int,
    ) -> CalendarActionReceipt:
        """Stage a packet for approval without writing provider state.

        Staging may carry a denial-style reason when Swift would require
        social confirmation or a higher tier, but it still gives Codex a concrete
        object to present rather than silently discarding the plan.
        """
        denied = None
        if candidate.required_authority_tier > requested_authority_tier:
            denied = "requires higher authority before commit"
        elif any(a.action_type in SOCIAL_MUTATION_ACTIONS for a in candidate.actions) and candidate.affected_people_ids:
            denied = "requires social actuation confirmation before commit"
        elif self._has_hard_conflict(candidate, observation):
            denied = "conflict_detected_before_stage"
        staged_ids = [self._stage_id(candidate.candidate_id, idx, action.action_type.value) for idx, action in enumerate(candidate.actions)]
        return CalendarActionReceipt(
            receipt_id="stage_rcpt_" + hashlib.sha1((candidate.candidate_id + str(datetime.now())).encode()).hexdigest()[:12],
            candidate_id=candidate.candidate_id,
            executed_at=observation.observed_at,
            executed_by="SwiftKernelStub.stage",
            authority_tier_used=min(requested_authority_tier, candidate.required_authority_tier),
            sync_status="staged",
            rollback_handle_id=None,
            conflict_check_passed=denied != "conflict_detected_before_stage",
            generated_event_ids=[],
            staged_action_ids=staged_ids,
            rejected_action_types=[],
            provider_id="local_stub",
            actuation_mode=ActuationMode.STAGED_DRAFT,
            denied_reason=denied,
        )

    def request_undo(self, rollback_handle_id: str, observation: RawCalendarObservation) -> CalendarActionReceipt:
        if not rollback_handle_id:
            denied = "missing rollback handle"
            status = "denied"
            mode = ActuationMode.DENIED
        else:
            denied = None
            status = "reverted"
            mode = ActuationMode.NO_OP
        return CalendarActionReceipt(
            receipt_id="undo_rcpt_" + hashlib.sha1((rollback_handle_id + str(datetime.now())).encode()).hexdigest()[:12],
            candidate_id=rollback_handle_id or "unknown",
            executed_at=observation.observed_at,
            executed_by="SwiftKernelStub.undo",
            authority_tier_used=0,
            sync_status=status,
            rollback_handle_id=rollback_handle_id or None,
            conflict_check_passed=True,
            provider_id="local_stub",
            actuation_mode=mode,
            denied_reason=denied,
        )

    @staticmethod
    def _denied_reason(candidate: CandidateCalendarAction, observation: RawCalendarObservation, granted_authority_tier: int) -> str | None:
        if candidate.required_authority_tier > granted_authority_tier:
            return "required authority tier exceeds granted tier"
        if any(a.action_type == AtomicActionType.AUTO_APPLY_PLAN for a in candidate.actions):
            return "auto_apply_plan requires product-specific tier 6 policy and is not kernel-v1 materialized"
        if any(a.action_type in SOCIAL_MUTATION_ACTIONS for a in candidate.actions) and candidate.affected_people_ids:
            return "social actuation boundary: people-affecting calendar mutation must be explicitly confirmed outside kernel-v1"
        if candidate.required_authority_tier >= 3 and candidate.reversibility == Reversibility.NONE:
            return "auto-write requires a rollback or reversible action"
        if SwiftKernelStub._has_hard_conflict(candidate, observation):
            return "conflict_detected"
        return None

    @staticmethod
    def _has_hard_conflict(candidate: CandidateCalendarAction, observation: RawCalendarObservation) -> bool:
        for action in candidate.actions:
            if action.action_type not in WRITE_ACTIONS:
                continue
            if action.start is None or action.end is None:
                continue
            if action.action_type in {AtomicActionType.CREATE_EVENT, AtomicActionType.CREATE_FOCUS_BLOCK, AtomicActionType.ADD_BUFFER, AtomicActionType.BATCH_TASKS}:
                if any(action.start < e.end and action.end > e.start for e in observation.events):
                    return True
            if action.action_type in {AtomicActionType.MOVE_EVENT, AtomicActionType.RESIZE_EVENT}:
                if any(e.event_id != action.event_id and action.start < e.end and action.end > e.start for e in observation.events):
                    return True
        return False

    @staticmethod
    def _event_id(candidate_id: str, idx: int) -> str:
        return f"evt_generated_{candidate_id[-6:]}_{idx}"

    @staticmethod
    def _stage_id(candidate_id: str, idx: int, kind: str) -> str:
        return f"stage_{kind}_{candidate_id[-6:]}_{idx}"

    @staticmethod
    def _rollback_id(candidate_id: str) -> str:
        return "undo_" + candidate_id[-10:]
