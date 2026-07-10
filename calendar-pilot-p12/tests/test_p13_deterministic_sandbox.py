from __future__ import annotations

from datetime import datetime, timedelta, timezone
import itertools
import json
from pathlib import Path
import tempfile
import unittest

from calendar_pilot.effect_kernel import (
    AUTHORITY_PROFILE,
    DeterministicSandboxAdapter,
    EffectAttempt,
    EffectKernelSelector,
    SandboxAuthorityGate,
    SandboxEffectGateway,
    SandboxEffectLedger,
    derive_phase,
)
from calendar_pilot.product_core import AdmissionPreview, PrepBlockProjection
from evals.architecture.adapters.p13_effect_scenarios import P13_3_CASES, collect_sandbox_effect_case
from evals.architecture.predicates.p13 import sandbox_effect_contract


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
KEY = b"p13.3-focused-test-development-key"


def _preview() -> AdmissionPreview:
    rows = ("observation:test", "proposal:test")
    return AdmissionPreview(
        preview_id="preview:test",
        candidate_id="candidate:test",
        action_family="create_prep_block",
        status="preview",
        denial_reasons=(),
        projection=PrepBlockProjection(
            title="Prepare",
            start="2026-07-10T13:00:00+00:00",
            end="2026-07-10T13:30:00+00:00",
            calendar_id="sandbox",
            explanation="Cited preparation",
            evidence_row_ids=rows,
        ),
        evidence_row_ids=rows,
    )


def _kernel(state_path: Path, *, confirmed: bool = True):
    ledger = SandboxEffectLedger(state_path)
    gate = SandboxAuthorityGate(ledger, signing_key=KEY)
    gateway = SandboxEffectGateway(ledger, signing_key=KEY, adapter=DeterministicSandboxAdapter())
    grant = gate.issue_grant(
        grant_id="grant:test",
        action_families=("create_prep_block",),
        scopes=("apply", "compensate"),
        issued_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        confirmed=confirmed,
    )
    attempt = EffectAttempt.from_preview(
        _preview(),
        source_authenticated=True,
        observed_pre_state_hash=gateway.current_state_hash,
    )
    return ledger, gate, gateway, grant, attempt


class P13DeterministicSandboxTests(unittest.TestCase):
    def test_frozen_architecture_scenarios_all_pass_from_raw_runtime_facts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as td:
            root = Path(td)
            for case in sorted(P13_3_CASES):
                with self.subTest(case=case):
                    scenario_dir = root / case
                    scenario_dir.mkdir()
                    evidence = collect_sandbox_effect_case(case, scenario_dir=scenario_dir, root=ROOT)
                    self.assertIsNotNone(evidence)
                    result = sandbox_effect_contract({"effect_kernel": evidence})
                    self.assertEqual(result["status"], "pass", result)

    def test_fact_precedence_is_permutation_invariant_and_conflict_holds(self):
        for facts, expected in [
            (("claim",), "claimed"),
            (("claim", "dispatch", "unknown"), "applying_unknown"),
            (("claim", "dispatch", "unknown", "verified"), "verified"),
            (("claim", "not_applied"), "not_applied"),
            (("claim", "verified", "not_applied"), "hold"),
        ]:
            with self.subTest(facts=facts):
                self.assertTrue(all(derive_phase(order) == expected for order in itertools.permutations(facts)))

    def test_separately_admitted_compensation_verifies_and_retains_audit(self):
        with tempfile.TemporaryDirectory() as td:
            _, gate, gateway, grant, attempt = _kernel(Path(td) / "ledger.json")
            admission = gate.admit_effect(
                attempt=attempt,
                grant_id=grant.grant_id,
                grant_epoch=grant.epoch,
                nonce="nonce:apply",
                now=NOW,
            )
            applied = gateway.execute(admission.ticket, now=NOW)
            audit_before = list(gateway.snapshot()["audit"])
            compensation = gate.admit_compensation(
                receipt=applied,
                grant_id=grant.grant_id,
                grant_epoch=grant.epoch,
                fresh_state_hash=gateway.current_state_hash,
                nonce="nonce:compensate",
                now=NOW + timedelta(minutes=1),
            )
            reverted = gateway.execute(compensation.ticket, now=NOW + timedelta(minutes=1))
            snapshot = gateway.snapshot()
            self.assertEqual(applied.phase, "verified")
            self.assertEqual(reverted.phase, "verified")
            self.assertEqual(snapshot["adapter_state"]["events"], {})
            self.assertEqual(snapshot["compensation_dispatch_count"], 1)
            self.assertEqual(snapshot["audit"][:len(audit_before)], audit_before)
            self.assertGreater(len(snapshot["audit"]), len(audit_before))

    def test_ledger_rejects_production_authority_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "ledger.json"
            ledger, _, _, _, _ = _kernel(state_path)
            payload = ledger.snapshot()
            payload["authorizes_production"] = True
            state_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot carry production authority"):
                SandboxEffectLedger(state_path)

    def test_ticket_is_not_portable_to_an_unrelated_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            _, gate, _, grant, attempt = _kernel(Path(td) / "source.json")
            admission = gate.admit_effect(
                attempt=attempt,
                grant_id=grant.grant_id,
                grant_epoch=grant.epoch,
                nonce="nonce:source",
                now=NOW,
            )
            target_ledger = SandboxEffectLedger(Path(td) / "target.json")
            target_gateway = SandboxEffectGateway(
                target_ledger,
                signing_key=KEY,
                adapter=DeterministicSandboxAdapter(),
            )
            receipt = target_gateway.execute(admission.ticket, now=NOW)
            self.assertEqual(receipt.phase, "denied")
            self.assertEqual(receipt.reasons, ("ticket_invalid",))
            self.assertEqual(target_gateway.snapshot()["dispatch_count"], 0)

    def test_unconfirmed_and_expired_grants_cannot_mint_tickets(self):
        with tempfile.TemporaryDirectory() as td:
            _, gate, _, grant, attempt = _kernel(Path(td) / "unconfirmed.json", confirmed=False)
            denied = gate.admit_effect(
                attempt=attempt,
                grant_id=grant.grant_id,
                grant_epoch=grant.epoch,
                nonce="nonce:unconfirmed",
                now=NOW,
            )
            self.assertEqual(denied.reasons, ("grant_unconfirmed",))

        with tempfile.TemporaryDirectory() as td:
            _, gate, _, grant, attempt = _kernel(Path(td) / "expired.json")
            denied = gate.admit_effect(
                attempt=attempt,
                grant_id=grant.grant_id,
                grant_epoch=grant.epoch,
                nonce="nonce:expired",
                now=NOW + timedelta(hours=2),
            )
            self.assertEqual(denied.reasons, ("grant_expired",))

    def test_selector_is_default_incumbent_and_sandbox_is_explicit(self):
        self.assertEqual(EffectKernelSelector.select(), "incumbent")
        self.assertEqual(EffectKernelSelector.select("incumbent"), "incumbent")
        self.assertEqual(EffectKernelSelector.select(AUTHORITY_PROFILE), "deterministic_sandbox")
        with self.assertRaisesRegex(ValueError, "unsupported effect owner"):
            EffectKernelSelector.select("eventkit")


if __name__ == "__main__":
    unittest.main()
