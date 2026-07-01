from __future__ import annotations

from datetime import datetime
import hashlib

from calendar_pilot.types import (
    AtomicActionType,
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarObservation,
    Reversibility,
)


class SwiftKernelStub:
    """Python mirror of the Swift authority broker.

    It is used for local policy/self-play tests. The Swift package contains the
    real deterministic kernel implementation for app integration.
    """

    def authorize_and_materialize(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        granted_authority_tier: int,
    ) -> CalendarActionReceipt:
        denied = self._denied_reason(candidate, granted_authority_tier)
        generated_ids: list[str] = []
        rollback = None
        if denied is None:
            generated_ids = [self._event_id(candidate.candidate_id, idx) for idx, a in enumerate(candidate.actions) if a.action_type in {AtomicActionType.CREATE_EVENT, AtomicActionType.CREATE_FOCUS_BLOCK, AtomicActionType.ADD_BUFFER}]
            rollback = self._rollback_id(candidate.candidate_id) if candidate.reversibility != Reversibility.NONE else None
        return CalendarActionReceipt(
            receipt_id="rcpt_" + hashlib.sha1((candidate.candidate_id + str(datetime.now())).encode()).hexdigest()[:12],
            candidate_id=candidate.candidate_id,
            executed_at=observation.observed_at,
            executed_by="SwiftKernelStub",
            authority_tier_used=min(granted_authority_tier, candidate.required_authority_tier),
            sync_status="denied" if denied else "materialized",
            rollback_handle_id=rollback,
            conflict_check_passed=denied != "conflict_detected",
            generated_event_ids=generated_ids,
            denied_reason=denied,
        )

    @staticmethod
    def _denied_reason(candidate: CandidateCalendarAction, granted_authority_tier: int) -> str | None:
        if candidate.required_authority_tier > granted_authority_tier:
            return "required authority tier exceeds granted tier"
        if candidate.required_authority_tier >= 5 and candidate.affected_people_ids:
            return "social actuation requires explicit tier 5+ confirmation"
        if candidate.required_authority_tier >= 3 and candidate.reversibility == Reversibility.NONE:
            return "auto-write requires a rollback or reversible action"
        return None

    @staticmethod
    def _event_id(candidate_id: str, idx: int) -> str:
        return f"evt_generated_{candidate_id[-6:]}_{idx}"

    @staticmethod
    def _rollback_id(candidate_id: str) -> str:
        return "undo_" + candidate_id[-10:]
