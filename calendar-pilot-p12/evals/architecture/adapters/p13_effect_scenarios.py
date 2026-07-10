from __future__ import annotations

import ast
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from calendar_pilot.product_core import AdmissionPreview, PrepBlockProjection


NOW = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
EVALUATOR_SIGNING_KEY = b"p13.3-frozen-evaluator-development-key"
P13_3_CASES = {
    "trusted_ingress_forgery",
    "effect_ticket_binding",
    "compensation_ticket_binding",
    "ticket_single_claim",
    "duplicate_delivery",
    "crash_before_claim",
    "crash_after_claim",
    "crash_after_dispatch",
    "verify_ambiguity_reconcile",
    "revoke_claim_race",
    "restart_reconciliation",
    "compensation_conflict_hold",
    "no_learning_effect_path",
}


def _api() -> SimpleNamespace | None:
    try:
        from calendar_pilot.effect_kernel import (
            AUTHORITY_PROFILE,
            AUTHORIZES_PRODUCTION,
            DeterministicSandboxAdapter,
            EffectAttempt,
            EffectKernelSelector,
            InjectedCrash,
            SandboxAuthorityGate,
            SandboxEffectGateway,
            SandboxEffectLedger,
        )
    except ModuleNotFoundError as exc:
        if exc.name == "calendar_pilot.effect_kernel":
            return None
        raise
    return SimpleNamespace(
        authority_profile=AUTHORITY_PROFILE,
        authorizes_production=AUTHORIZES_PRODUCTION,
        Adapter=DeterministicSandboxAdapter,
        Attempt=EffectAttempt,
        Selector=EffectKernelSelector,
        InjectedCrash=InjectedCrash,
        Gate=SandboxAuthorityGate,
        Gateway=SandboxEffectGateway,
        Ledger=SandboxEffectLedger,
    )


def _preview() -> AdmissionPreview:
    evidence = ("observation:p13.3", "proposal:p13.3")
    return AdmissionPreview(
        preview_id="preview:p13.3",
        candidate_id="candidate:p13.3",
        action_family="create_prep_block",
        status="preview",
        denial_reasons=(),
        projection=PrepBlockProjection(
            title="Prepare for architecture review",
            start="2026-07-10T13:00:00+00:00",
            end="2026-07-10T13:30:00+00:00",
            calendar_id="sandbox",
            explanation="A private cited preparation block.",
            evidence_row_ids=evidence,
        ),
        evidence_row_ids=evidence,
    )


def _fixture(api: SimpleNamespace, state_path: Path, *, grant_id: str = "grant:p13.3") -> SimpleNamespace:
    ledger = api.Ledger(state_path)
    adapter = api.Adapter()
    gate = api.Gate(ledger, signing_key=EVALUATOR_SIGNING_KEY)
    gateway = api.Gateway(ledger, signing_key=EVALUATOR_SIGNING_KEY, adapter=adapter)
    grant = gate.issue_grant(
        grant_id=grant_id,
        action_families=("create_prep_block",),
        scopes=("apply", "compensate"),
        issued_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        confirmed=True,
    )
    attempt = api.Attempt.from_preview(
        _preview(),
        source_authenticated=True,
        observed_pre_state_hash=gateway.current_state_hash,
    )
    return SimpleNamespace(api=api, ledger=ledger, adapter=adapter, gate=gate, gateway=gateway, grant=grant, attempt=attempt)


def _admit(fixture: SimpleNamespace, *, nonce: str = "nonce:apply:1", attempt: Any | None = None) -> Any:
    return fixture.gate.admit_effect(
        attempt=attempt or fixture.attempt,
        grant_id=fixture.grant.grant_id,
        grant_epoch=fixture.grant.epoch,
        nonce=nonce,
        now=NOW,
    )


def _universal(api: SimpleNamespace, case: str) -> dict[str, Any]:
    return {
        "case": case,
        "authority_profile": api.authority_profile,
        "authorizes_production": api.authorizes_production,
        "adapter_id": api.Adapter.adapter_id,
        "adapter_credential_count": len(api.Adapter.credential_fields),
        "adapter_external_io": api.Adapter.external_io,
    }


def _restart(fixture: SimpleNamespace, state_path: Path) -> SimpleNamespace:
    ledger = fixture.api.Ledger(state_path)
    gate = fixture.api.Gate(ledger, signing_key=EVALUATOR_SIGNING_KEY)
    gateway = fixture.api.Gateway(ledger, signing_key=EVALUATOR_SIGNING_KEY, adapter=fixture.api.Adapter())
    return SimpleNamespace(api=fixture.api, ledger=ledger, gate=gate, gateway=gateway)


def _verified_effect(fixture: SimpleNamespace, *, nonce: str = "nonce:apply:1") -> tuple[Any, Any]:
    admission = _admit(fixture, nonce=nonce)
    if admission.ticket is None:
        raise RuntimeError(f"fixture admission failed: {admission.reasons}")
    return admission.ticket, fixture.gateway.execute(admission.ticket, now=NOW)


def collect_sandbox_effect_case(case: str, *, scenario_dir: Path, root: Path) -> dict[str, Any] | None:
    if case not in P13_3_CASES:
        raise ValueError(f"unknown P13.3 scenario case: {case}")
    api = _api()
    if api is None:
        return None
    base = _universal(api, case)
    state_path = scenario_dir / "sandbox-ledger.json"

    if case == "trusted_ingress_forgery":
        fixture = _fixture(api, state_path)
        valid = _admit(fixture)
        forged = _admit(fixture, nonce="nonce:forged", attempt=replace(fixture.attempt, source_authenticated=False))
        stale = _admit(
            fixture,
            nonce="nonce:stale",
            attempt=replace(fixture.attempt, observed_pre_state_hash="0" * 64),
        )
        return base | {
            "valid_admission_status": valid.status,
            "forged_admission_status": forged.status,
            "forged_reason": forged.reasons[0],
            "stale_admission_status": stale.status,
            "stale_reason": stale.reasons[0],
            "ticket_count_after": fixture.gateway.snapshot()["ticket_count"],
        }

    if case == "effect_ticket_binding":
        fixture = _fixture(api, state_path)
        admission = _admit(fixture)
        ticket = admission.ticket
        if ticket is None:
            raise RuntimeError(f"fixture admission failed: {admission.reasons}")
        reused = _admit(fixture, nonce=ticket.nonce)
        tampered = replace(ticket, intent_hash="0" * 64)
        return base | {
            "admission_status": admission.status,
            "ticket_kind": ticket.kind,
            "signature_valid": fixture.gate.verify_ticket(ticket),
            "tampered_signature_valid": fixture.gate.verify_ticket(tampered),
            "nonce_unique": reused.status == "denied" and reused.reasons == ("nonce_reused",),
            "grant_epoch_matches_current": ticket.grant_epoch == fixture.gate.current_epoch(ticket.grant_id),
            "ticket_intent_hash": ticket.intent_hash,
            "expected_intent_hash": fixture.attempt.intent_hash,
            "ticket_pre_state_hash": ticket.pre_state_hash,
            "expected_pre_state_hash": fixture.attempt.observed_pre_state_hash,
        }

    if case == "compensation_ticket_binding":
        fixture = _fixture(api, state_path)
        apply_ticket, receipt = _verified_effect(fixture)
        admission = fixture.gate.admit_compensation(
            receipt=receipt,
            grant_id=fixture.grant.grant_id,
            grant_epoch=fixture.grant.epoch,
            fresh_state_hash=fixture.gateway.current_state_hash,
            nonce="nonce:compensate:1",
            now=NOW + timedelta(minutes=1),
        )
        ticket = admission.ticket
        if ticket is None:
            raise RuntimeError(f"fixture compensation admission failed: {admission.reasons}")
        return base | {
            "admission_status": admission.status,
            "ticket_kind": ticket.kind,
            "signature_valid": fixture.gate.verify_ticket(ticket),
            "separate_ticket": ticket.ticket_id != apply_ticket.ticket_id,
            "separate_nonce": ticket.nonce != apply_ticket.nonce,
            "ticket_target_receipt_hash": ticket.target_receipt_hash,
            "expected_target_receipt_hash": receipt.content_sha256,
            "ticket_fresh_state_hash": ticket.pre_state_hash,
            "expected_fresh_state_hash": fixture.gateway.current_state_hash,
        }

    if case in {"ticket_single_claim", "duplicate_delivery"}:
        fixture = _fixture(api, state_path)
        ticket, first = _verified_effect(fixture)
        second = fixture.gateway.execute(ticket, now=NOW + timedelta(seconds=1))
        snapshot = fixture.gateway.snapshot()
        if case == "ticket_single_claim":
            return base | {
                "first_phase": first.phase,
                "second_phase": second.phase,
                "claim_count": snapshot["claim_count"],
                "claim_fact_count": snapshot["claim_fact_count"],
            }
        return base | {
            "dispatch_count": snapshot["dispatch_count"],
            "mutation_count": snapshot["mutation_count"],
            "same_receipt_hash": first.content_sha256 == second.content_sha256,
            "same_idempotency_key": first.idempotency_key == second.idempotency_key,
        }

    if case == "crash_before_claim":
        fixture = _fixture(api, state_path)
        admission = _admit(fixture)
        ticket = admission.ticket
        if ticket is None:
            raise RuntimeError(f"fixture admission failed: {admission.reasons}")
        crash_stage = ""
        try:
            fixture.gateway.execute(ticket, now=NOW, crash_at="before_claim")
        except api.InjectedCrash as exc:
            crash_stage = exc.stage
        after_crash = fixture.gateway.snapshot()
        restarted = _restart(fixture, state_path)
        recovered = restarted.gateway.execute(ticket, now=NOW + timedelta(seconds=1))
        after_recovery = restarted.gateway.snapshot()
        return base | {
            "crash_stage": crash_stage,
            "phase_after_crash": fixture.gateway.phase(ticket.ticket_id),
            "claim_count_after_crash": after_crash["claim_count"],
            "dispatch_count_after_crash": after_crash["dispatch_count"],
            "mutation_count_after_crash": after_crash["mutation_count"],
            "recovered_phase": recovered.phase,
            "recovered_dispatch_count": after_recovery["dispatch_count"],
        }

    if case in {"crash_after_claim", "crash_after_dispatch", "restart_reconciliation"}:
        fixture = _fixture(api, state_path)
        admission = _admit(fixture)
        ticket = admission.ticket
        if ticket is None:
            raise RuntimeError(f"fixture admission failed: {admission.reasons}")
        stage = "after_claim_before_dispatch" if case == "crash_after_claim" else "after_dispatch_before_receipt"
        crash_stage = ""
        try:
            fixture.gateway.execute(ticket, now=NOW, crash_at=stage)
        except api.InjectedCrash as exc:
            crash_stage = exc.stage
        before = fixture.gateway.snapshot()
        phase_before = fixture.gateway.phase(ticket.ticket_id)
        restarted = _restart(fixture, state_path)
        reconciled = restarted.gateway.reconcile(ticket.ticket_id, now=NOW + timedelta(seconds=1))
        after = restarted.gateway.snapshot()
        if case == "crash_after_claim":
            return base | {
                "crash_stage": crash_stage,
                "phase_after_crash": phase_before,
                "claim_count": before["claim_count"],
                "dispatch_count": before["dispatch_count"],
                "mutation_count": before["mutation_count"],
                "reconciled_phase": reconciled.phase,
            }
        if case == "crash_after_dispatch":
            return base | {
                "crash_stage": crash_stage,
                "phase_after_crash": phase_before,
                "dispatch_count_before_reconcile": before["dispatch_count"],
                "mutation_count_before_reconcile": before["mutation_count"],
                "reconciled_phase": reconciled.phase,
                "dispatch_count_after_reconcile": after["dispatch_count"],
            }
        return base | {
            "phase_before_restart": phase_before,
            "phase_after_restart": reconciled.phase,
            "same_ticket_id": reconciled.ticket_id == ticket.ticket_id,
            "same_idempotency_key": reconciled.idempotency_key == ticket.idempotency_key,
            "dispatch_count": after["dispatch_count"],
            "mutation_count": after["mutation_count"],
        }

    if case == "verify_ambiguity_reconcile":
        fixture = _fixture(api, state_path)
        admission = _admit(fixture)
        ticket = admission.ticket
        if ticket is None:
            raise RuntimeError(f"fixture admission failed: {admission.reasons}")
        initial = fixture.gateway.execute(ticket, now=NOW, verification_mode="unknown")
        reconciled = fixture.gateway.reconcile(ticket.ticket_id, now=NOW + timedelta(seconds=1))
        snapshot = fixture.gateway.snapshot()
        return base | {
            "initial_phase": initial.phase,
            "initial_success_label": initial.phase == "verified",
            "reconciled_phase": reconciled.phase,
            "dispatch_count": snapshot["dispatch_count"],
            "mutation_count": snapshot["mutation_count"],
        }

    if case == "revoke_claim_race":
        before = _fixture(api, scenario_dir / "before-revoke.json", grant_id="grant:before")
        before_admission = _admit(before)
        before_ticket = before_admission.ticket
        if before_ticket is None:
            raise RuntimeError(f"fixture admission failed: {before_admission.reasons}")
        before.gate.revoke(before.grant.grant_id, now=NOW)
        before_receipt = before.gateway.execute(before_ticket, now=NOW + timedelta(seconds=1))

        after = _fixture(api, scenario_dir / "after-revoke.json", grant_id="grant:after")
        after_admission = _admit(after)
        after_ticket = after_admission.ticket
        if after_ticket is None:
            raise RuntimeError(f"fixture admission failed: {after_admission.reasons}")
        try:
            after.gateway.execute(after_ticket, now=NOW, crash_at="after_claim_before_dispatch")
        except api.InjectedCrash:
            pass
        phase_after_claim = after.gateway.phase(after_ticket.ticket_id)
        after.gate.revoke(after.grant.grant_id, now=NOW + timedelta(milliseconds=1))
        reconciled = after.gateway.reconcile(after_ticket.ticket_id, now=NOW + timedelta(seconds=1))
        invalid = after.gate.admit_effect(
            attempt=after.attempt,
            grant_id=after.grant.grant_id,
            grant_epoch=after.grant.epoch,
            nonce="nonce:invalid-epoch",
            now=NOW + timedelta(seconds=2),
        )
        return base | {
            "before_claim_phase": before_receipt.phase,
            "before_claim_dispatch_count": before.gateway.snapshot()["dispatch_count"],
            "after_claim_phase": phase_after_claim,
            "after_claim_reconciled_phase": reconciled.phase,
            "after_claim_dispatch_count": after.gateway.snapshot()["dispatch_count"],
            "invalid_epoch_admission_status": invalid.status,
            "invalid_epoch_reason": invalid.reasons[0],
        }

    if case == "compensation_conflict_hold":
        fixture = _fixture(api, state_path)
        _, receipt = _verified_effect(fixture)
        fixture.gateway.inject_out_of_band_edit("later-edit", {"title": "User changed this"})
        admission = fixture.gate.admit_compensation(
            receipt=receipt,
            grant_id=fixture.grant.grant_id,
            grant_epoch=fixture.grant.epoch,
            fresh_state_hash=fixture.gateway.current_state_hash,
            nonce="nonce:compensate:conflict",
            now=NOW + timedelta(minutes=1),
        )
        snapshot = fixture.gateway.snapshot()
        return base | {
            "initial_phase": receipt.phase,
            "compensation_admission_status": admission.status,
            "compensation_reason": admission.reasons[0],
            "compensation_dispatch_count": snapshot["compensation_dispatch_count"],
            "later_edit_preserved": snapshot["adapter_state"].get("out_of_band", {}).get("later-edit") == {"title": "User changed this"},
        }

    package = root / "src/calendar_pilot/effect_kernel"
    forbidden_roots = {
        "calendar_pilot.diffusiongemma",
        "calendar_pilot.codex",
        "calendar_pilot.providers",
        "calendar_pilot.swift_bridge",
        "socket",
        "subprocess",
        "urllib",
        "http",
    }
    imports: set[str] = set()
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    forbidden = sorted(
        name for name in imports
        if any(name == root_name or name.startswith(root_name + ".") for root_name in forbidden_roots)
    )
    return base | {
        "forbidden_imports": forbidden,
        "accepted_action_families": sorted(api.Adapter.supported_action_families),
        "default_selector": api.Selector.select(),
        "explicit_selector": api.Selector.select(api.authority_profile),
        "real_provider_reachable": api.Adapter.real_provider_reachable,
    }
