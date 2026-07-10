from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from calendar_pilot.product_core import AdmissionPreview, PrepBlockProjection


NOW = datetime(2026, 7, 10, 16, 0, tzinfo=timezone.utc)
SIGNING_KEY = b"p13.4-frozen-eventkit-evaluator-key"
SANDBOX_CALENDAR_ID = "calendarpilot-sandbox-test"
APP_IDENTITY = {
    "path": "/Applications/CalendarPilot.app",
    "sha256": "a" * 64,
}
BRIDGE_IDENTITY = {
    "path": "/Applications/CalendarPilot.app/Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge",
    "sha256": "b" * 64,
}

P13_4_CASES = {
    "eventkit_identity_target_binding",
    "eventkit_ticket_binding",
    "eventkit_effect_lifecycle",
    "eventkit_revoke_claim_race",
    "eventkit_compensation_binding",
    "eventkit_compensation_conflict_hold",
    "eventkit_no_learning_effect_path",
}


class FakeEventKitSandboxDriver:
    """Deterministic remote fixture; the product adapter owns all policy checks."""

    provider_id = "apple_eventkit"
    permission_status = "full_access"

    def __init__(self) -> None:
        self.events: dict[str, dict[str, Any]] = {}
        self.create_calls = 0
        self.remove_calls = 0

    def snapshot(self, calendar_id: str) -> dict[str, Any]:
        return {
            "calendar_id": calendar_id,
            "events": {key: dict(value) for key, value in sorted(self.events.items())},
        }

    def create(self, *, calendar_id: str, idempotency_key: str, projection: dict[str, Any]) -> str:
        if idempotency_key not in self.events:
            self.events[idempotency_key] = {
                **dict(projection),
                "calendar_id": calendar_id,
                "external_id": f"event:{idempotency_key}",
            }
            self.create_calls += 1
        return str(self.events[idempotency_key]["external_id"])

    def remove(self, *, calendar_id: str, idempotency_key: str, external_id: str) -> bool:
        value = self.events.get(idempotency_key)
        if value is None:
            return True
        if value.get("calendar_id") != calendar_id or value.get("external_id") != external_id:
            return False
        del self.events[idempotency_key]
        self.remove_calls += 1
        return True

    def inject_external_edit(self, idempotency_key: str, *, title: str) -> None:
        self.events[idempotency_key]["title"] = title


def _api() -> SimpleNamespace | None:
    try:
        from calendar_pilot.effect_kernel import (
            EVENTKIT_ADAPTER_ID,
            EVENTKIT_AUTHORITY_PROFILE,
            EffectAttempt,
            EffectKernelSelector,
            EventKitSandboxAdapter,
            InjectedCrash,
            SandboxAuthorityGate,
            SandboxEffectGateway,
            SandboxEffectLedger,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        if "EventKitSandboxAdapter" in str(exc) or "EVENTKIT_" in str(exc):
            return None
        if isinstance(exc, ModuleNotFoundError) and exc.name == "calendar_pilot.effect_kernel":
            return None
        raise
    return SimpleNamespace(
        authority_profile=EVENTKIT_AUTHORITY_PROFILE,
        adapter_id=EVENTKIT_ADAPTER_ID,
        Attempt=EffectAttempt,
        Selector=EffectKernelSelector,
        Adapter=EventKitSandboxAdapter,
        InjectedCrash=InjectedCrash,
        Gate=SandboxAuthorityGate,
        Gateway=SandboxEffectGateway,
        Ledger=SandboxEffectLedger,
    )


def _preview(calendar_id: str = SANDBOX_CALENDAR_ID) -> AdmissionPreview:
    evidence = ("observation:p13.4", "proposal:p13.4")
    return AdmissionPreview(
        preview_id="preview:p13.4",
        candidate_id="candidate:p13.4",
        action_family="create_prep_block",
        status="preview",
        denial_reasons=(),
        projection=PrepBlockProjection(
            title="CalendarPilot P13.4 Probe",
            start="2026-07-17T16:00:00+00:00",
            end="2026-07-17T16:20:00+00:00",
            calendar_id=calendar_id,
            explanation="Cited owner-controlled EventKit sandbox probe.",
            evidence_row_ids=evidence,
        ),
        evidence_row_ids=evidence,
    )


def _fixture(api: SimpleNamespace, state_path: Path) -> SimpleNamespace:
    driver = FakeEventKitSandboxDriver()
    adapter = api.Adapter(
        driver=driver,
        app_identity=APP_IDENTITY,
        bridge_identity=BRIDGE_IDENTITY,
        sandbox_calendar_id=SANDBOX_CALENDAR_ID,
        effect_budget=1,
    )
    ledger = api.Ledger(state_path, authority_profile=api.authority_profile, adapter=adapter)
    gate = api.Gate(ledger, signing_key=SIGNING_KEY)
    gateway = api.Gateway(ledger, signing_key=SIGNING_KEY, adapter=adapter)
    grant = gate.issue_grant(
        grant_id="grant:p13.4",
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
        authority_profile=api.authority_profile,
        target_binding=adapter.ticket_binding,
    )
    return SimpleNamespace(
        api=api,
        driver=driver,
        adapter=adapter,
        ledger=ledger,
        gate=gate,
        gateway=gateway,
        grant=grant,
        attempt=attempt,
        state_path=state_path,
    )


def _admit(fixture: SimpleNamespace, *, nonce: str = "nonce:eventkit:apply", attempt: Any | None = None) -> Any:
    return fixture.gate.admit_effect(
        attempt=attempt or fixture.attempt,
        grant_id=fixture.grant.grant_id,
        grant_epoch=fixture.grant.epoch,
        nonce=nonce,
        now=NOW,
    )


def _verified_effect(fixture: SimpleNamespace, *, nonce: str = "nonce:eventkit:apply") -> tuple[Any, Any]:
    admission = _admit(fixture, nonce=nonce)
    if admission.ticket is None:
        raise RuntimeError(f"EventKit fixture admission failed: {admission.reasons}")
    return admission.ticket, fixture.gateway.execute(admission.ticket, now=NOW)


def _universal(fixture: SimpleNamespace, case: str) -> dict[str, Any]:
    return {
        "case": case,
        "authority_profile": fixture.api.authority_profile,
        "authorizes_production": False,
        "adapter_id": fixture.api.adapter_id,
        "adapter_external_io": fixture.adapter.external_io,
        "real_provider_reachable": fixture.adapter.real_provider_reachable,
        "action_family": "create_prep_block",
        "default_selector": fixture.api.Selector.select(),
        "explicit_selector": fixture.api.Selector.select(fixture.api.authority_profile),
    }


def collect_eventkit_effect_case(case: str, *, scenario_dir: Path, root: Path) -> dict[str, Any] | None:
    del root
    if case not in P13_4_CASES:
        raise ValueError(f"unknown P13.4 scenario case: {case}")
    api = _api()
    if api is None:
        return None
    fixture = _fixture(api, scenario_dir / "eventkit-ledger.json")
    base = _universal(fixture, case)

    if case == "eventkit_identity_target_binding":
        wrong = api.Attempt.from_preview(
            _preview("default"),
            source_authenticated=True,
            observed_pre_state_hash=fixture.gateway.current_state_hash,
            authority_profile=api.authority_profile,
            target_binding={**fixture.adapter.ticket_binding, "sandbox_calendar_id": "default"},
        )
        wrong_admission = _admit(fixture, nonce="nonce:eventkit:wrong-calendar", attempt=wrong)
        return base | {
            "app_bundle_bound": fixture.adapter.app_bundle_bound,
            "bridge_bound": fixture.adapter.bridge_bound,
            "permission_status": fixture.adapter.permission_status,
            "sandbox_calendar_id": fixture.adapter.sandbox_calendar_id,
            "raw_cli_rejected": fixture.adapter.raw_cli_rejected,
            "wrong_calendar_status": wrong_admission.status,
            "wrong_calendar_reason": wrong_admission.reasons[0],
            "effect_budget": fixture.adapter.effect_budget,
            "dispatch_count": fixture.gateway.snapshot()["dispatch_count"],
        }

    if case == "eventkit_ticket_binding":
        admission = _admit(fixture)
        ticket = admission.ticket
        if ticket is None:
            raise RuntimeError(f"EventKit fixture admission failed: {admission.reasons}")
        tampered = replace(ticket, target_binding={**ticket.target_binding, "bridge_sha256": "0" * 64})
        deterministic_attempt = replace(
            fixture.attempt,
            authority_profile="owner_controlled_sandbox",
            target_binding=None,
        )
        rejected = _admit(fixture, nonce="nonce:eventkit:deterministic", attempt=deterministic_attempt)
        return base | {
            "admission_status": admission.status,
            "signature_valid": fixture.gate.verify_ticket(ticket),
            "tampered_signature_valid": fixture.gate.verify_ticket(tampered),
            "deterministic_profile_status": rejected.status,
            "deterministic_profile_reason": rejected.reasons[0],
            "ticket_target_binding": ticket.target_binding,
            "expected_target_binding": fixture.adapter.ticket_binding,
            "nonce_unique": _admit(fixture, nonce=ticket.nonce).reasons == ("nonce_reused",),
        }

    if case == "eventkit_effect_lifecycle":
        ticket, receipt = _verified_effect(fixture)
        duplicate = fixture.gateway.execute(ticket, now=NOW)

        before = _fixture(api, scenario_dir / "before.json")
        before_ticket = _admit(before).ticket
        try:
            before.gateway.execute(before_ticket, now=NOW, crash_at="before_claim")
        except api.InjectedCrash:
            pass

        after_claim = _fixture(api, scenario_dir / "after-claim.json")
        after_claim_ticket = _admit(after_claim).ticket
        try:
            after_claim.gateway.execute(after_claim_ticket, now=NOW, crash_at="after_claim_before_dispatch")
        except api.InjectedCrash:
            pass
        after_claim_phase = after_claim.gateway.phase(after_claim_ticket.ticket_id)
        after_claim_reconciled = after_claim.gateway.reconcile(after_claim_ticket.ticket_id, now=NOW)

        after_dispatch = _fixture(api, scenario_dir / "after-dispatch.json")
        after_dispatch_ticket = _admit(after_dispatch).ticket
        try:
            after_dispatch.gateway.execute(after_dispatch_ticket, now=NOW, crash_at="after_dispatch_before_receipt")
        except api.InjectedCrash:
            pass
        restarted_ledger = api.Ledger(
            after_dispatch.state_path,
            authority_profile=api.authority_profile,
            adapter=after_dispatch.adapter,
        )
        restarted = api.Gateway(restarted_ledger, signing_key=SIGNING_KEY, adapter=after_dispatch.adapter)
        restarted_receipt = restarted.reconcile(after_dispatch_ticket.ticket_id, now=NOW)
        return base | {
            "initial_phase": receipt.phase,
            "duplicate_same_receipt": duplicate.content_sha256 == receipt.content_sha256,
            "claim_count": fixture.gateway.snapshot()["claim_count"],
            "dispatch_count": fixture.gateway.snapshot()["dispatch_count"],
            "mutation_count": fixture.gateway.snapshot()["mutation_count"],
            "crash_before_phase": before.gateway.phase(before_ticket.ticket_id),
            "crash_before_dispatch_count": before.gateway.snapshot()["dispatch_count"],
            "crash_after_claim_phase": after_claim_phase,
            "crash_after_claim_reconciled": after_claim_reconciled.phase,
            "crash_after_dispatch_phase": after_dispatch.gateway.phase(after_dispatch_ticket.ticket_id),
            "restart_reconciled_phase": restarted_receipt.phase,
            "restart_same_ticket": restarted_receipt.ticket_id == after_dispatch_ticket.ticket_id,
            "restart_dispatch_count": restarted.snapshot()["dispatch_count"],
        }

    if case == "eventkit_revoke_claim_race":
        before = _fixture(api, scenario_dir / "revoke-before.json")
        before_ticket = _admit(before).ticket
        before.gate.revoke(before.grant.grant_id, now=NOW + timedelta(minutes=1))
        before_receipt = before.gateway.execute(before_ticket, now=NOW + timedelta(minutes=1))

        after = _fixture(api, scenario_dir / "revoke-after.json")
        after_ticket = _admit(after).ticket
        try:
            after.gateway.execute(after_ticket, now=NOW, crash_at="after_claim_before_dispatch")
        except api.InjectedCrash:
            pass
        after.gate.revoke(after.grant.grant_id, now=NOW + timedelta(minutes=1))
        reconciled = after.gateway.reconcile(after_ticket.ticket_id, now=NOW + timedelta(minutes=1))
        invalid = _admit(after, nonce="nonce:eventkit:invalid-epoch")
        return base | {
            "before_claim_phase": before_receipt.phase,
            "before_claim_dispatch_count": before.gateway.snapshot()["dispatch_count"],
            "after_claim_phase": "claimed",
            "after_claim_reconciled_phase": reconciled.phase,
            "after_claim_dispatch_count": after.gateway.snapshot()["dispatch_count"],
            "invalid_epoch_status": invalid.status,
            "invalid_epoch_reason": invalid.reasons[0],
        }

    if case == "eventkit_compensation_binding":
        apply_ticket, receipt = _verified_effect(fixture)
        admission = fixture.gate.admit_compensation(
            receipt=receipt,
            grant_id=fixture.grant.grant_id,
            grant_epoch=fixture.grant.epoch,
            fresh_state_hash=fixture.gateway.current_state_hash,
            nonce="nonce:eventkit:compensate",
            now=NOW + timedelta(minutes=1),
        )
        compensation = admission.ticket
        if compensation is None:
            raise RuntimeError(f"EventKit compensation admission failed: {admission.reasons}")
        result = fixture.gateway.execute(compensation, now=NOW + timedelta(minutes=1))
        return base | {
            "apply_phase": receipt.phase,
            "compensation_admission_status": admission.status,
            "compensation_phase": result.phase,
            "target_receipt_hash": compensation.target_receipt_hash,
            "expected_target_receipt_hash": receipt.content_sha256,
            "target_binding": compensation.target_binding,
            "expected_target_binding": fixture.adapter.ticket_binding,
            "compensation_dispatch_count": fixture.gateway.snapshot()["compensation_dispatch_count"],
            "event_absent": apply_ticket.idempotency_key not in fixture.driver.events,
        }

    if case == "eventkit_compensation_conflict_hold":
        apply_ticket, receipt = _verified_effect(fixture)
        fixture.driver.inject_external_edit(apply_ticket.idempotency_key, title="User changed title")
        admission = fixture.gate.admit_compensation(
            receipt=receipt,
            grant_id=fixture.grant.grant_id,
            grant_epoch=fixture.grant.epoch,
            fresh_state_hash=fixture.gateway.current_state_hash,
            nonce="nonce:eventkit:conflict",
            now=NOW + timedelta(minutes=1),
        )
        return base | {
            "apply_phase": receipt.phase,
            "compensation_status": admission.status,
            "compensation_reason": admission.reasons[0],
            "compensation_dispatch_count": fixture.gateway.snapshot()["compensation_dispatch_count"],
            "external_edit_preserved": fixture.driver.events[apply_ticket.idempotency_key]["title"] == "User changed title",
        }

    if case == "eventkit_no_learning_effect_path":
        return base | {
            "forbidden_imports": fixture.adapter.forbidden_imports,
            "provider_only_through_gateway": fixture.adapter.provider_only_through_gateway,
            "direct_commit_rejected": fixture.adapter.direct_commit_rejected,
            "production_selector_available": fixture.api.Selector.production_available,
        }

    raise AssertionError(case)
