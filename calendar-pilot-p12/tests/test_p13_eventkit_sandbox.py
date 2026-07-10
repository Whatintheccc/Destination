from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from calendar_pilot.effect_kernel import (
    AUTHORITY_PROFILE,
    EVENTKIT_AUTHORITY_PROFILE,
    EffectAttempt,
    EffectKernelSelector,
    EventKitSandboxAdapter,
    SandboxAuthorityGate,
    SandboxEffectGateway,
    SandboxEffectLedger,
)
from calendar_pilot.product_core import AdmissionPreview, PrepBlockProjection
from evals.architecture.adapters.p13_eventkit_scenarios import (
    APP_IDENTITY,
    BRIDGE_IDENTITY,
    FakeEventKitSandboxDriver,
    P13_4_CASES,
    SANDBOX_CALENDAR_ID,
    collect_eventkit_effect_case,
)
from evals.architecture.predicates.p13 import eventkit_sandbox_contract


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 10, 16, 0, tzinfo=timezone.utc)
KEY = b"p13.4-focused-owner-key"


def _adapter(driver: FakeEventKitSandboxDriver | None = None) -> EventKitSandboxAdapter:
    return EventKitSandboxAdapter(
        driver=driver or FakeEventKitSandboxDriver(),
        app_identity=APP_IDENTITY,
        bridge_identity=BRIDGE_IDENTITY,
        sandbox_calendar_id=SANDBOX_CALENDAR_ID,
        effect_budget=1,
    )


def _preview(calendar_id: str = SANDBOX_CALENDAR_ID) -> AdmissionPreview:
    rows = ("observation:test:p13.4", "proposal:test:p13.4")
    return AdmissionPreview(
        preview_id="preview:test:p13.4",
        candidate_id="candidate:test:p13.4",
        action_family="create_prep_block",
        status="preview",
        denial_reasons=(),
        projection=PrepBlockProjection(
            title="P13.4 test probe",
            start="2026-07-17T16:00:00+00:00",
            end="2026-07-17T16:20:00+00:00",
            calendar_id=calendar_id,
            explanation="Cited test probe.",
            evidence_row_ids=rows,
        ),
        evidence_row_ids=rows,
    )


class P13EventKitSandboxTests(unittest.TestCase):
    def test_frozen_eventkit_scenarios_all_pass_from_runtime_facts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as td:
            root = Path(td)
            for case in sorted(P13_4_CASES):
                with self.subTest(case=case):
                    scenario = root / case
                    scenario.mkdir()
                    evidence = collect_eventkit_effect_case(case, scenario_dir=scenario, root=ROOT)
                    self.assertIsNotNone(evidence)
                    self.assertEqual(
                        eventkit_sandbox_contract({"eventkit_effect_kernel": evidence})["status"],
                        "pass",
                    )

    def test_adapter_rejects_raw_or_wrong_app_identity_and_default_calendar(self):
        driver = FakeEventKitSandboxDriver()
        with self.assertRaisesRegex(ValueError, "app-bundled bridge"):
            EventKitSandboxAdapter(
                driver=driver,
                app_identity=APP_IDENTITY,
                bridge_identity={"path": "/tmp/CalendarPilotEventKitBridge", "sha256": "b" * 64},
                sandbox_calendar_id=SANDBOX_CALENDAR_ID,
            )
        with self.assertRaisesRegex(ValueError, "non-default calendar"):
            EventKitSandboxAdapter(
                driver=driver,
                app_identity=APP_IDENTITY,
                bridge_identity=BRIDGE_IDENTITY,
                sandbox_calendar_id="default",
            )

    def test_eventkit_gateway_rejects_deterministic_profile_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = _adapter()
            ledger = SandboxEffectLedger(
                Path(td) / "ledger.json",
                authority_profile=EVENTKIT_AUTHORITY_PROFILE,
                adapter=adapter,
            )
            gate = SandboxAuthorityGate(ledger, signing_key=KEY)
            gateway = SandboxEffectGateway(ledger, signing_key=KEY, adapter=adapter)
            grant = gate.issue_grant(
                grant_id="grant:test:p13.4",
                action_families=("create_prep_block",),
                scopes=("apply",),
                issued_at=NOW,
                expires_at=NOW + timedelta(hours=1),
                confirmed=True,
            )
            attempt = EffectAttempt.from_preview(
                _preview(),
                source_authenticated=True,
                observed_pre_state_hash=gateway.current_state_hash,
                authority_profile=AUTHORITY_PROFILE,
            )
            denied = gate.admit_effect(
                attempt=attempt,
                grant_id=grant.grant_id,
                grant_epoch=grant.epoch,
                nonce="nonce:test:p13.4",
                now=NOW,
            )
            self.assertEqual(denied.status, "denied")
            self.assertEqual(denied.reasons, ("authority_profile_invalid",))
            self.assertEqual(gateway.snapshot()["dispatch_count"], 0)

    def test_eventkit_profile_is_explicit_and_never_production(self):
        self.assertEqual(EffectKernelSelector.select(), "incumbent")
        self.assertEqual(EffectKernelSelector.select(EVENTKIT_AUTHORITY_PROFILE), "apple_eventkit_sandbox")
        self.assertFalse(EffectKernelSelector.production_available)

    def test_permission_and_effect_budget_are_fail_closed(self):
        denied = FakeEventKitSandboxDriver()
        denied.permission_status = "denied"
        with self.assertRaisesRegex(ValueError, "full_access"):
            _adapter(denied)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            EventKitSandboxAdapter(
                driver=FakeEventKitSandboxDriver(),
                app_identity=APP_IDENTITY,
                bridge_identity=BRIDGE_IDENTITY,
                sandbox_calendar_id=SANDBOX_CALENDAR_ID,
                effect_budget=2,
            )


if __name__ == "__main__":
    unittest.main()
