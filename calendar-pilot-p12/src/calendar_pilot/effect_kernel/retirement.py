from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import secrets
from typing import Any

from calendar_pilot.product_core import run_create_prep_block_vertical
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
from calendar_pilot.types import (
    ActuationMode,
    AuthorityGrant as RuntimeAuthorityGrant,
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarEvent,
    RawCalendarObservation,
    StageState,
)

from .kernel import (
    AUTHORITY_PROFILE,
    DeterministicSandboxAdapter,
    EffectAttempt,
    EffectKernelSelector as _LegacySelector,
    EffectReceipt,
    EffectTicket,
    SandboxAuthorityGate,
    SandboxEffectGateway,
    SandboxEffectLedger,
)


RETIREMENT_PROFILE = "owner_controlled_vertical_retirement"
RETIREMENT_BACKEND = "deterministic_sandbox"
RETIREMENT_OWNER = "effect_kernel"
RETIREMENT_SCOPE = ("create_prep_block", RETIREMENT_BACKEND)


class EffectKernelSelector:
    """Exact-pair operational selector; normal callers cannot restore the old owner."""

    production_available = False
    retired_scopes = frozenset({RETIREMENT_SCOPE})
    rollback_source = "owner_frozen_selector"

    @classmethod
    def select(
        cls,
        authority_profile: str | None = None,
        *,
        action_family: str | None = None,
        backend: str | None = None,
    ) -> str:
        if (action_family, backend) == RETIREMENT_SCOPE:
            if authority_profile not in {None, RETIREMENT_PROFILE}:
                raise ValueError("normal callers cannot override the retired vertical owner")
            return RETIREMENT_OWNER
        return _LegacySelector.select(authority_profile)

    @classmethod
    def select_rollback(cls, *, action_family: str, backend: str) -> str:
        if (action_family, backend) != RETIREMENT_SCOPE:
            raise ValueError("owner rollback is bound to the exact retired vertical")
        return "incumbent"


@dataclass(frozen=True)
class RetirementActionResult:
    calendar_receipt: CalendarActionReceipt
    provider_receipt: dict[str, Any]
    ticket: EffectTicket
    effect_receipt: EffectReceipt
    access_point: str

    @property
    def phase(self) -> str:
        return self.effect_receipt.phase

    @property
    def denied_reason(self) -> str | None:
        return self.effect_receipt.reasons[0] if self.effect_receipt.reasons else None

    def output_payload(self, candidate: CandidateCalendarAction | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "swift_receipt": self.calendar_receipt.to_dict(),
            "provider_receipt": dict(self.provider_receipt),
            "effect_ticket": self.ticket.to_dict(),
            "effect_receipt": self.effect_receipt.to_dict(),
            "stage_state": self.calendar_receipt.stage_state.value,
            "retirement": {
                "access_point": self.access_point,
                "retirement_profile": RETIREMENT_PROFILE,
                "owner": RETIREMENT_OWNER,
                "backend": RETIREMENT_BACKEND,
                "phase": self.effect_receipt.phase,
                "effect_receipt_sha256": self.effect_receipt.content_sha256,
                "authorizes_production": False,
            },
        }
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        if self.ticket.kind == "compensate":
            payload["provider_rollback"] = dict(self.provider_receipt)
            payload["rollback_verified"] = self.effect_receipt.phase == "verified"
        return payload


def _load_or_create_key(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        value = path.read_bytes()
        if len(value) < 32:
            raise ValueError("retirement signing key is invalid")
        return value
    value = secrets.token_bytes(32)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    return value


class DeterministicRetirementProvider:
    """Non-production runtime backend whose sole mutation aperture is EffectKernel."""

    provider_id = RETIREMENT_BACKEND
    real_oauth = False
    real_provider = False
    authorizes_production = False
    direct_commit_rejected = True
    direct_undo_rejected = True

    def __init__(
        self,
        *,
        state_path: str | Path,
        signing_key_path: str | Path,
        seed_observation: RawCalendarObservation,
    ) -> None:
        self.state_path = Path(state_path)
        self.signing_key_path = Path(signing_key_path)
        self.seed_observation = seed_observation
        self.adapter = DeterministicSandboxAdapter()
        self.signing_key = _load_or_create_key(self.signing_key_path)
        self.ledger = SandboxEffectLedger(self.state_path, authority_profile=AUTHORITY_PROFILE, adapter=self.adapter)
        self.gate = SandboxAuthorityGate(self.ledger, signing_key=self.signing_key)
        self.gateway = SandboxEffectGateway(self.ledger, signing_key=self.signing_key, adapter=self.adapter)
        self.direct_commit_count = 0
        self.direct_undo_count = 0

    def health_status(self) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "configured": True,
            "status": "configured",
            "authority_profile": RETIREMENT_PROFILE,
            "authorizes_production": False,
        }

    def commit_candidate(self, *_args: Any, **_kwargs: Any) -> None:
        self.direct_commit_count += 1
        raise RuntimeError("direct deterministic retirement commit is disabled; use EffectKernel Gateway")

    def rollback(self, *_args: Any, **_kwargs: Any) -> None:
        self.direct_undo_count += 1
        raise RuntimeError("direct deterministic retirement undo is disabled; use a CompensationTicket")

    def preview(self, _candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        return []

    def conflict_truth(self, _candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        return []

    def read_observation(
        self,
        user_scope_id: str,
        *,
        observed_at: datetime | None = None,
        time_zone_id: str | None = None,
    ) -> RawCalendarObservation:
        events = list(self.seed_observation.events)
        state = self.ledger.snapshot()["adapter_state"]
        for idempotency_key, projection in sorted(state.get("events", {}).items()):
            events.append(
                RawCalendarEvent.from_dict(
                    {
                        "event_id": "retired:" + hashlib.sha1(idempotency_key.encode()).hexdigest()[:16],
                        "title": projection["title"],
                        "start": projection["start"],
                        "end": projection["end"],
                        "calendar_id": projection["calendar_id"],
                        "notes": projection.get("explanation", ""),
                        "is_user_owned": True,
                        "is_flexible": True,
                        "category": "focus",
                    }
                )
            )
        return RawCalendarObservation(
            observation_id="obs_deterministic_sandbox",
            user_scope_id=user_scope_id,
            observed_at=observed_at or datetime.now(timezone.utc),
            time_zone_id=time_zone_id or self.seed_observation.time_zone_id,
            events=events,
            tasks=list(self.seed_observation.tasks),
            device_context=self.seed_observation.device_context,
            notification_history=list(self.seed_observation.notification_history),
            prior_actions=list(self.seed_observation.prior_actions),
        )

    def snapshot(self) -> dict[str, Any]:
        state = self.retirement_snapshot()
        return {
            "provider": self.provider_id,
            "real_oauth": False,
            "event_count": len(self.seed_observation.events) + int(state["active_event_count"]),
            "idempotency_keys": len(state["adapter_state"].get("idempotency", {})),
            "rollback_records": state["compensation_ticket_count"],
            "rollback_verified": state["compensation_mutation_count"],
            "recent_mutations": state["audit"][-8:],
        }

    def reset(self, seed_observation: RawCalendarObservation | None = None) -> None:
        if seed_observation is not None:
            self.seed_observation = seed_observation
        if self.state_path.exists():
            self.state_path.unlink()
        self.ledger = SandboxEffectLedger(self.state_path, authority_profile=AUTHORITY_PROFILE, adapter=self.adapter)
        self.gate = SandboxAuthorityGate(self.ledger, signing_key=self.signing_key)
        self.gateway = SandboxEffectGateway(self.ledger, signing_key=self.signing_key, adapter=self.adapter)

    def _ensure_grant(self, authority: RuntimeAuthorityGrant) -> int:
        state = self.ledger.snapshot()
        existing = state["grants"].get(authority.grant_id)
        if isinstance(existing, dict):
            return int(existing["epoch"])
        scopes = []
        if authority.allows_scope("commit_private"):
            scopes.append("apply")
        if authority.allows_scope("undo"):
            scopes.append("compensate")
        grant = self.gate.issue_grant(
            grant_id=authority.grant_id,
            action_families=("create_prep_block",),
            scopes=tuple(scopes),
            issued_at=authority.issued_at,
            expires_at=authority.expires_at,
            confirmed=authority.confirmed_by_user,
        )
        return grant.epoch

    def _existing_apply_ticket(self, candidate_id: str) -> EffectTicket | None:
        for row in self.ledger.snapshot()["tickets"].values():
            ticket = EffectTicket.from_dict(row["ticket"])
            if ticket.kind == "apply" and ticket.candidate_id == candidate_id:
                return ticket
        return None

    def _receipt_by_hash(self, receipt_hash: str) -> EffectReceipt | None:
        for value in self.ledger.snapshot()["receipts"].values():
            receipt = EffectReceipt.from_dict(value)
            if receipt.content_sha256 == receipt_hash:
                return receipt
        return None

    def owns_rollback_handle(self, rollback_handle_id: str) -> bool:
        if not rollback_handle_id.startswith("retirement:"):
            return False
        return self._receipt_by_hash(rollback_handle_id.removeprefix("retirement:")) is not None

    def commit_via_gateway(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority: RuntimeAuthorityGrant,
        *,
        replay: ReplayBuffer,
        trace_id: str,
        causal_parent_id: str | None,
        now: datetime | None = None,
        crash_at: str | None = None,
    ) -> RetirementActionResult:
        now = now or datetime.now(timezone.utc)
        product = run_create_prep_block_vertical(
            observation,
            candidate,
            source_authenticated=True,
            received_at=observation.observed_at,
            journal_scope_id=f"retirement:{trace_id}",
        )
        if product.preview.status != "preview":
            raise ValueError("retired vertical did not produce an admitted cited preview")
        epoch = self._ensure_grant(authority)
        ticket = self._existing_apply_ticket(candidate.candidate_id)
        if ticket is None:
            attempt = EffectAttempt.from_preview(
                product.preview,
                source_authenticated=True,
                observed_pre_state_hash=self.gateway.current_state_hash,
            )
            nonce = "nonce:" + hashlib.sha256(
                f"{authority.grant_id}|{candidate.candidate_id}|{attempt.observed_pre_state_hash}".encode()
            ).hexdigest()[:24]
            admission = self.gate.admit_effect(
                attempt=attempt,
                grant_id=authority.grant_id,
                grant_epoch=epoch,
                nonce=nonce,
                now=now,
            )
            if admission.ticket is None:
                raise ValueError(f"retired vertical admission blocked: {admission.reasons}")
            ticket = admission.ticket
        receipt = self.gateway.execute(ticket, now=now, crash_at=crash_at)
        return self._action_result(
            ticket,
            receipt,
            authority,
            replay=replay,
            trace_id=trace_id,
            causal_parent_id=causal_parent_id,
            candidate=candidate,
            access_point="CodexToolRuntime.REQUEST_COMMIT",
        )

    def undo_via_gateway(
        self,
        rollback_handle_id: str,
        observation: RawCalendarObservation,
        authority: RuntimeAuthorityGrant,
        *,
        replay: ReplayBuffer,
        trace_id: str,
        causal_parent_id: str | None,
        now: datetime | None = None,
    ) -> RetirementActionResult:
        del observation
        now = now or datetime.now(timezone.utc)
        target = self._receipt_by_hash(rollback_handle_id.removeprefix("retirement:"))
        if target is None:
            raise ValueError("retirement rollback handle does not name a verified effect receipt")
        epoch = self._ensure_grant(authority)
        admission = self.gate.admit_compensation(
            receipt=target,
            grant_id=authority.grant_id,
            grant_epoch=epoch,
            fresh_state_hash=self.gateway.current_state_hash,
            nonce="nonce:" + hashlib.sha256(f"{authority.grant_id}|{target.content_sha256}".encode()).hexdigest()[:24],
            now=now,
        )
        if admission.ticket is None:
            raise ValueError(f"retired vertical compensation blocked: {admission.reasons}")
        receipt = self.gateway.execute(admission.ticket, now=now)
        return self._action_result(
            admission.ticket,
            receipt,
            authority,
            replay=replay,
            trace_id=trace_id,
            causal_parent_id=causal_parent_id,
            candidate=None,
            access_point="CodexToolRuntime.REQUEST_UNDO",
        )

    def _action_result(
        self,
        ticket: EffectTicket,
        receipt: EffectReceipt,
        authority: RuntimeAuthorityGrant,
        *,
        replay: ReplayBuffer,
        trace_id: str,
        causal_parent_id: str | None,
        candidate: CandidateCalendarAction | None,
        access_point: str,
    ) -> RetirementActionResult:
        verified = receipt.phase == "verified"
        rollback_handle = "retirement:" + receipt.content_sha256 if ticket.kind == "apply" and verified else None
        calendar_receipt = CalendarActionReceipt(
            receipt_id=receipt.receipt_id,
            candidate_id=ticket.candidate_id,
            executed_at=datetime.fromisoformat(receipt.issued_at),
            executed_by="EffectKernel.Gateway",
            authority_tier_used=authority.max_authority_tier,
            sync_status="materialized" if ticket.kind == "apply" and verified else "reverted" if verified else receipt.phase,
            rollback_handle_id=rollback_handle,
            conflict_check_passed=receipt.phase not in {"hold", "denied"},
            generated_event_ids=[ticket.idempotency_key] if ticket.kind == "apply" and verified else [],
            provider_id=self.provider_id,
            actuation_mode=ActuationMode.MATERIALIZED_WRITE if verified else ActuationMode.DENIED,
            denied_reason=None if verified else (receipt.reasons[0] if receipt.reasons else receipt.phase),
            authority_grant_id=authority.grant_id,
            confirmation_provenance=authority.confirmation_provenance,
            stage_state=StageState.COMMITTED if ticket.kind == "apply" and verified else StageState.NO_OP,
            correlation_id=trace_id,
        )
        provider_receipt = {
            "provider_id": self.provider_id,
            "status": "materialized" if ticket.kind == "apply" and verified else "rollback_verified" if verified else receipt.phase,
            "idempotency_key": ticket.idempotency_key,
            "external_ids": [ticket.idempotency_key] if ticket.kind == "apply" and verified else [],
            "rollback_handle_id": rollback_handle or rollback_handle_for_target(ticket, self.ledger.snapshot()),
            "rollback_verified": bool(ticket.kind == "compensate" and verified),
            "effect_receipt_sha256": receipt.content_sha256,
            "authorizes_production": False,
        }
        replay.append_provider_transaction(
            operation="commit" if ticket.kind == "apply" else "rollback",
            transaction=provider_receipt,
            trace_id=trace_id,
            causal_parent_id=receipt.receipt_id,
        )
        replay.append_receipt(
            calendar_receipt,
            candidate,
            trace_id=trace_id,
            causal_parent_id=causal_parent_id,
            observation_id=self.seed_observation.observation_id,
            observation_fingerprint=observation_fingerprint(self.seed_observation),
            runtime_mode="codex_tool_runtime",
            policy_backend="effect_kernel_retirement",
        )
        return RetirementActionResult(calendar_receipt, provider_receipt, ticket, receipt, access_point)

    def reconcile_pending(self, *, now: datetime | None = None) -> list[EffectReceipt]:
        now = now or datetime.now(timezone.utc)
        reconciled: list[EffectReceipt] = []
        state = self.ledger.snapshot()
        for ticket_id in sorted(state["outbox"]):
            if self.gateway.phase(ticket_id) in {"claimed", "applying_unknown"}:
                reconciled.append(self.gateway.reconcile(ticket_id, now=now))
        return reconciled

    def retirement_snapshot(self) -> dict[str, Any]:
        snapshot = self.gateway.snapshot()
        state = self.ledger.snapshot()
        tickets = [EffectTicket.from_dict(row["ticket"]) for row in state["tickets"].values()]
        receipts = [EffectReceipt.from_dict(row) for row in state["receipts"].values()]
        snapshot.update(
            {
                "retirement_profile": RETIREMENT_PROFILE,
                "owner": RETIREMENT_OWNER,
                "backend": RETIREMENT_BACKEND,
                "active_event_count": len(state["adapter_state"]["events"]),
                "compensation_ticket_count": sum(ticket.kind == "compensate" for ticket in tickets),
                "compensation_claim_count": sum(
                    row["kind"] == "compensate" and "claim" in row["facts"] for row in state["outbox"].values()
                ),
                "compensation_mutation_count": int(state["adapter_state"]["compensation_mutation_count"]),
                "direct_commit_count": self.direct_commit_count,
                "direct_undo_count": self.direct_undo_count,
                "last_phase": receipts[-1].phase if receipts else None,
                "last_ticket_id": receipts[-1].ticket_id if receipts else None,
            }
        )
        return snapshot


def rollback_handle_for_target(ticket: EffectTicket, state: dict[str, Any]) -> str | None:
    if ticket.kind != "compensate" or ticket.target_receipt_hash is None:
        return None
    return "retirement:" + ticket.target_receipt_hash
