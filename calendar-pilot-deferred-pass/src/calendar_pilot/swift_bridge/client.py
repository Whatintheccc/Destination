

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Iterable

from calendar_pilot.environment.plan_graph import actions_from_plan_metadata, rollback_order_from_metadata
from calendar_pilot.types import (
    ActuationMode,
    AtomicActionType,
    AuthorityGrant,
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarObservation,
    Reversibility,
    StageState,
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
    AtomicActionType.AUTO_APPLY_PLAN,
}

SOCIAL_MUTATION_ACTIONS = {
    AtomicActionType.MOVE_EVENT,
    AtomicActionType.RESIZE_EVENT,
    AtomicActionType.DELETE_OWN_EVENT,
    AtomicActionType.AUTO_APPLY_PLAN,
}


class SwiftKernelStub:
    """Python mirror of the Swift authority broker.

    Authority is now object-based. Codex/Python may request a tier, but Swift
    must issue a live AuthorityGrant before simulation, staging, commit, or undo.
    Out-of-band integers are denied before materialization.
    """

    def __init__(self) -> None:
        self.authority_grants: dict[str, AuthorityGrant] = {}
        self.undo_ledger: dict[str, str] = {}

    def issue_authority_grant(
        self,
        *,
        user_scope_id: str,
        max_authority_tier: int,
        scopes: Iterable[str] | None = None,
        confirmation_provenance: str = "user_confirmed_demo_scope",
        ttl_minutes: int = 30,
        confirmed_by_user: bool = True,
        issued_at: datetime | None = None,
    ) -> AuthorityGrant:
        issued_at = issued_at or datetime.now(timezone.utc)
        digest = hashlib.sha1(
            f"{user_scope_id}|{max_authority_tier}|{confirmation_provenance}|{issued_at.isoformat()}|{','.join(list(scopes or []))}".encode()
        ).hexdigest()[:12]
        grant = AuthorityGrant(
            grant_id=f"grant_{digest}",
            user_scope_id=user_scope_id,
            max_authority_tier=max_authority_tier,
            scopes=list(scopes or ["recommend", "stage", "commit_private", "undo"]),
            issued_at=issued_at,
            expires_at=issued_at + timedelta(minutes=ttl_minutes),
            confirmation_provenance=confirmation_provenance,
            issued_by="SwiftKernelStub",
            confirmed_by_user=confirmed_by_user,
        )
        self.authority_grants[grant.grant_id] = grant
        return grant

    def resolve_authority_grant(self, grant: AuthorityGrant | str | None) -> AuthorityGrant | None:
        # Authority grants are Swift/kernel-issued capabilities. Passing an
        # embedded object is never enough: the id must already exist in the
        # kernel registry. This prevents Codex/Python payloads from minting
        # authority by value.
        if isinstance(grant, AuthorityGrant):
            return self.authority_grants.get(grant.grant_id)
        if isinstance(grant, str):
            return self.authority_grants.get(grant)
        return None

    def authorize_and_materialize(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        granted_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        grant = self.resolve_authority_grant(authority_grant)
        desired_tier = requested_authority_tier if requested_authority_tier is not None else (granted_authority_tier or 0)
        denied = self._grant_denied_reason(candidate, observation, grant, desired_tier=desired_tier, commit=True)
        return self._materialize(candidate, observation, grant, desired_tier=desired_tier, denied=denied, commit=True, correlation_id=correlation_id)

    def preview_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        grant = self.resolve_authority_grant(authority_grant)
        desired_tier = requested_authority_tier if requested_authority_tier is not None else candidate.required_authority_tier
        denied = self._grant_denied_reason(candidate, observation, grant, desired_tier=desired_tier, commit=False)
        receipt = self._materialize(candidate, observation, grant, desired_tier=desired_tier, denied=denied, commit=False, correlation_id=correlation_id)
        return CalendarActionReceipt(
            receipt_id="preview_" + receipt.receipt_id,
            candidate_id=receipt.candidate_id,
            executed_at=receipt.executed_at,
            executed_by="SwiftKernelStub.preview",
            authority_tier_used=receipt.authority_tier_used,
            sync_status="simulated" if denied is None else "denied",
            rollback_handle_id=None,
            conflict_check_passed=receipt.conflict_check_passed,
            generated_event_ids=[],
            staged_action_ids=receipt.staged_action_ids,
            rejected_action_types=receipt.rejected_action_types,
            provider_id=receipt.provider_id,
            actuation_mode=receipt.actuation_mode if denied is not None else ActuationMode.NO_OP,
            denied_reason=receipt.denied_reason,
            authority_grant_id=grant.grant_id if grant else None,
            confirmation_provenance=grant.confirmation_provenance if grant else None,
            stage_state=StageState.SIMULATED if denied is None else StageState.DENIED,
            correlation_id=correlation_id or candidate.candidate_id,
        )

    def stage_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        """Stage a packet for approval without writing provider state.

        Staging semantics now distinguish stageable, confirmation-required, and
        denied. A social or higher-tier packet can be stageable only when the
        grant covers staging; commit still requires a matching grant and may be
        denied independently.
        """
        grant = self.resolve_authority_grant(authority_grant)
        desired_tier = requested_authority_tier if requested_authority_tier is not None else candidate.required_authority_tier
        denied = self._grant_denied_reason(candidate, observation, grant, desired_tier=desired_tier, commit=False)
        staged_ids: list[str] = []
        rejected_types: list[str] = []
        if denied is None:
            staged_ids = [self._stage_id(candidate.candidate_id, idx, action.action_type.value) for idx, action in enumerate(candidate.actions)]
        else:
            rejected_types = [a.action_type.value for a in candidate.actions]
        social = self.is_people_affecting_mutation(candidate)
        requires_confirmation = social or candidate.required_authority_tier > (grant.max_authority_tier if grant else 0)
        state = StageState.DENIED if denied else (StageState.REQUIRES_CONFIRMATION if requires_confirmation else StageState.STAGEABLE)
        return CalendarActionReceipt(
            receipt_id=self._stable_id("stage_rcpt", candidate.candidate_id, correlation_id or ""),
            candidate_id=candidate.candidate_id,
            executed_at=observation.observed_at,
            executed_by="SwiftKernelStub.stage",
            authority_tier_used=min(desired_tier, grant.max_authority_tier if grant else 0),
            sync_status="denied" if denied else "staged",
            rollback_handle_id=None,
            conflict_check_passed=denied != "conflict_detected_before_stage",
            generated_event_ids=[],
            staged_action_ids=staged_ids,
            rejected_action_types=rejected_types,
            provider_id="local_stub",
            actuation_mode=ActuationMode.DENIED if denied else ActuationMode.STAGED_DRAFT,
            denied_reason=denied,
            authority_grant_id=grant.grant_id if grant else None,
            confirmation_provenance=grant.confirmation_provenance if grant else None,
            stage_state=state,
            correlation_id=correlation_id or candidate.candidate_id,
        )

    def request_undo(
        self,
        rollback_handle_id: str,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        grant = self.resolve_authority_grant(authority_grant)
        desired_tier = requested_authority_tier if requested_authority_tier is not None else 1
        ledger_candidate_id = self.undo_ledger.get(rollback_handle_id or "")
        if grant is None:
            denied = "missing Swift-issued authority grant for undo"
        elif grant.user_scope_id != observation.user_scope_id:
            denied = "authority grant user scope mismatch for undo"
        elif not grant.is_live_at(observation.observed_at):
            denied = "authority grant expired before undo"
        elif not grant.confirmed_by_user:
            denied = "authority grant lacks user confirmation provenance for undo"
        elif desired_tier > grant.max_authority_tier:
            denied = "out-of-band authority tier rejected before undo"
        elif not grant.allows_scope("undo"):
            denied = "authority grant scope does not include undo"
        elif not rollback_handle_id or ledger_candidate_id is None:
            denied = "rollback handle not found"
        else:
            denied = None
            self.undo_ledger.pop(rollback_handle_id, None)
        return CalendarActionReceipt(
            receipt_id=self._stable_id("undo_rcpt", rollback_handle_id or "", correlation_id or ""),
            candidate_id=ledger_candidate_id or rollback_handle_id or "unknown",
            executed_at=observation.observed_at,
            executed_by="SwiftKernelStub.undo",
            authority_tier_used=min(desired_tier, grant.max_authority_tier if grant else 0),
            sync_status="denied" if denied else "reverted",
            rollback_handle_id=rollback_handle_id or None,
            conflict_check_passed=True,
            provider_id="local_stub",
            actuation_mode=ActuationMode.DENIED if denied else ActuationMode.NO_OP,
            denied_reason=denied,
            authority_grant_id=grant.grant_id if grant else None,
            confirmation_provenance=grant.confirmation_provenance if grant else None,
            stage_state=StageState.DENIED if denied else StageState.COMMITTED,
            correlation_id=correlation_id or rollback_handle_id or None,
        )

    def _materialize(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        grant: AuthorityGrant | None,
        *,
        desired_tier: int,
        denied: str | None,
        commit: bool,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        generated_ids: list[str] = []
        staged_ids: list[str] = []
        rejected_types: list[str] = []
        rollback = None
        materialized_write = False
        staged_only_or_sidecar = False
        mode = ActuationMode.NO_OP
        sync_status = "materialized" if commit else "simulated"
        stage_state = StageState.COMMITTED if commit else StageState.SIMULATED

        if denied is not None:
            sync_status = "denied"
            mode = ActuationMode.DENIED
            stage_state = StageState.DENIED
            rejected_types = [a.action_type.value for a in candidate.actions]
        elif not commit:
            # Preview is simulation only; never create provider objects.
            mode = ActuationMode.NO_OP
        else:
            for idx, action in enumerate(self._expanded_actions(candidate.actions)):
                if action.action_type in {AtomicActionType.CREATE_EVENT, AtomicActionType.CREATE_FOCUS_BLOCK, AtomicActionType.ADD_BUFFER, AtomicActionType.BATCH_TASKS, AtomicActionType.AUTO_APPLY_PLAN}:
                    generated_ids.append(self._event_id(candidate.candidate_id, idx))
                    materialized_write = True
                elif action.action_type in {AtomicActionType.MOVE_EVENT, AtomicActionType.RESIZE_EVENT, AtomicActionType.DELETE_OWN_EVENT}:
                    materialized_write = True
                elif action.action_type in STAGED_ACTIONS:
                    staged_only_or_sidecar = True
                    staged_ids.append(self._stage_id(candidate.candidate_id, idx, action.action_type.value))
                elif action.action_type == AtomicActionType.UNDO:
                    rejected_types.append(action.action_type.value)

            if materialized_write:
                mode = ActuationMode.MATERIALIZED_WRITE
                sync_status = "materialized"
                stage_state = StageState.COMMITTED
            elif staged_only_or_sidecar:
                sync_status = "staged"
                mode = ActuationMode.STAGED_NOTIFICATION if any("notify" in sid for sid in staged_ids) else ActuationMode.STAGED_DRAFT
                stage_state = StageState.REQUIRES_CONFIRMATION if any("draft_schedule_plan" in sid for sid in staged_ids) else StageState.STAGEABLE
            else:
                mode = ActuationMode.NO_OP
                sync_status = "materialized"
                stage_state = StageState.NO_OP

            rollback = self._rollback_id(candidate.candidate_id, correlation_id or "") if candidate.reversibility != Reversibility.NONE and materialized_write else None
            if rollback:
                self.undo_ledger[rollback] = candidate.candidate_id

        return CalendarActionReceipt(
            receipt_id=self._receipt_id(
                candidate,
                grant,
                sync_status=sync_status,
                stage_state=stage_state,
                correlation_id=correlation_id,
                denied=denied,
            ),
            candidate_id=candidate.candidate_id,
            executed_at=observation.observed_at,
            executed_by="SwiftKernelStub",
            authority_tier_used=min(desired_tier, grant.max_authority_tier if grant else 0),
            sync_status=sync_status,
            rollback_handle_id=rollback,
            conflict_check_passed=denied != "conflict_detected",
            generated_event_ids=generated_ids,
            staged_action_ids=staged_ids,
            rejected_action_types=rejected_types,
            provider_id="local_stub",
            actuation_mode=mode,
            denied_reason=denied,
            authority_grant_id=grant.grant_id if grant else None,
            confirmation_provenance=grant.confirmation_provenance if grant else None,
            stage_state=stage_state,
            correlation_id=correlation_id or candidate.candidate_id,
        )

    @staticmethod
    def is_people_affecting_mutation(candidate: CandidateCalendarAction) -> bool:
        if not candidate.affected_people_ids:
            return False
        return any(action.action_type in SOCIAL_MUTATION_ACTIONS for action in candidate.actions)

    def _receipt_id(
        self,
        candidate: CandidateCalendarAction,
        grant: AuthorityGrant | None,
        *,
        sync_status: str,
        stage_state: StageState | str,
        correlation_id: str | None,
        denied: str | None,
    ) -> str:
        stage = stage_state.value if isinstance(stage_state, StageState) else str(stage_state)
        action_signature = ",".join(action.action_type.value for action in self._expanded_actions(candidate.actions))
        return self._stable_id(
            "rcpt",
            candidate.candidate_id,
            correlation_id or "",
            sync_status,
            stage,
            grant.grant_id if grant else "no_grant",
            denied or "",
            action_signature,
        )

    @staticmethod
    def has_write_action(candidate: CandidateCalendarAction) -> bool:
        return any(action.action_type in WRITE_ACTIONS for action in SwiftKernelStub._expanded_actions(candidate.actions))

    @staticmethod
    def _grant_denied_reason(
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        grant: AuthorityGrant | None,
        *,
        desired_tier: int,
        commit: bool,
    ) -> str | None:
        if grant is None:
            return "missing Swift-issued authority grant; caller-supplied tiers are rejected before materialization"
        if grant.user_scope_id != observation.user_scope_id:
            return "authority grant user scope mismatch"
        if not grant.is_live_at(observation.observed_at):
            return "authority grant expired before materialization"
        if desired_tier > grant.max_authority_tier:
            return "out-of-band authority tier rejected before materialization"
        if candidate.required_authority_tier > grant.max_authority_tier and commit:
            return "required authority tier exceeds Swift-issued grant"
        writes = SwiftKernelStub.has_write_action(candidate)
        social = SwiftKernelStub.is_people_affecting_mutation(candidate)
        auto_plan = any(a.action_type == AtomicActionType.AUTO_APPLY_PLAN for a in candidate.actions)
        if commit and writes and not grant.confirmed_by_user:
            return "authority grant lacks user confirmation provenance for commit"
        if not commit and not grant.allows_scope("stage"):
            return "authority grant scope does not include stage"
        if commit and auto_plan:
            if grant.max_authority_tier < 6 or candidate.required_authority_tier < 6:
                return "auto_apply_plan requires tier 6 authority"
            if not grant.allows_scope("auto_apply_plan"):
                return "authority grant scope does not include auto_apply_plan"
        if commit and writes and social:
            if grant.max_authority_tier < 5:
                return "social actuation requires tier 5 authority"
            if not (grant.allows_scope("commit_social") or grant.allows_scope("move_people_meeting") or grant.allows_scope("send_calendar_update")):
                return "social actuation requires commit_social scope"
        if commit and writes and not social and not auto_plan and not grant.allows_scope("commit_private"):
            return "authority grant scope does not include commit_private"
        if commit and candidate.required_authority_tier >= 3 and candidate.reversibility == Reversibility.NONE:
            return "auto-write requires a rollback or reversible action"
        if SwiftKernelStub._has_hard_conflict(candidate, observation):
            return "conflict_detected" if commit else "conflict_detected_before_stage"
        return None

    @staticmethod
    def _has_hard_conflict(candidate: CandidateCalendarAction, observation: RawCalendarObservation) -> bool:
        for action in SwiftKernelStub._expanded_actions(candidate.actions):
            if action.action_type not in WRITE_ACTIONS:
                continue
            if action.start is None or action.end is None:
                continue
            if action.action_type in {AtomicActionType.CREATE_EVENT, AtomicActionType.CREATE_FOCUS_BLOCK, AtomicActionType.ADD_BUFFER, AtomicActionType.BATCH_TASKS, AtomicActionType.AUTO_APPLY_PLAN}:
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
    def _rollback_id(candidate_id: str, correlation_id: str = "") -> str:
        return SwiftKernelStub._stable_id("undo", candidate_id, correlation_id)

    @staticmethod
    def _stable_id(prefix: str, *parts: str) -> str:
        digest = hashlib.sha1("|".join(str(part) for part in parts).encode()).hexdigest()[:12]
        return f"{prefix}_{digest}"

    @staticmethod
    def _expanded_actions(actions: Iterable[AtomicCalendarAction]) -> list[AtomicCalendarAction]:
        expanded: list[AtomicCalendarAction] = []
        for action in actions:
            if action.action_type == AtomicActionType.AUTO_APPLY_PLAN:
                nested = actions_from_plan_metadata(action.metadata)
                if nested:
                    expanded.extend(nested)
                    continue
            expanded.append(action)
        return expanded
