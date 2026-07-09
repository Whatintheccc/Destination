from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from evals.p13_ruler.core import (
    build_binding_manifest,
    build_instrument_bundle,
    canonical_json_bytes,
    sha256_bytes,
    validate_instrument_bundle,
    verify_binding_manifest,
)

from .p12_current import P12CurrentAdapter


DEBT_EVIDENCE: dict[str, tuple[str, list[str]]] = {
    "reducer_determinism": ("Pure Reducer has not landed.", ["identical prefix/version/command produces byte-identical state and intents"]),
    "cited_required_projection": ("The versioned durable-field manifest and cited projection have not landed.", ["field-level event/evidence ids", "Reducer version"]),
    "trusted_ingress_forgery": ("Source-authenticated Journal/Gate ingress has not landed.", ["forged source rejection", "fresh provider precondition"]),
    "effect_ticket_binding": ("One-use EffectTicket has not landed.", ["exact intent hash", "pre-state hash", "nonce/epoch"]),
    "compensation_ticket_binding": ("One-use CompensationTicket has not landed.", ["target effect receipt hash", "fresh-state hash", "separate claim"]),
    "ticket_single_claim": ("Durable Gateway claim/outbox has not landed.", ["atomic claim", "duplicate claim denial"]),
    "duplicate_delivery": ("Idempotent Gateway delivery has not landed.", ["same idempotency key", "single provider effect"]),
    "crash_before_claim": ("Target Gateway lifecycle has not landed.", ["unclaimed ticket recovery", "no provider effect"]),
    "crash_after_claim": ("Target Gateway lifecycle has not landed.", ["durable outbox", "reconciled absent/present"]),
    "crash_after_dispatch": ("Target Gateway lifecycle has not landed.", ["applying_unknown", "reconcile before retry"]),
    "verify_ambiguity_reconcile": ("Verify/reconcile lifecycle has not landed.", ["non-committed unknown state", "verified/not_applied/hold resolution"]),
    "revoke_claim_race": ("Grant epoch and claim linearization have not landed.", ["before-claim cancel", "after-claim reconcile"]),
    "restart_reconciliation": ("Durable target outbox restore has not landed.", ["restart", "same idempotency key", "reconciled outcome"]),
    "compensation_conflict_hold": ("Conflict-aware compensation has not landed.", ["fresh external state", "later-edit preservation", "visible hold"]),
    "no_learning_effect_path": ("Learning/meta write isolation is not machine-enforced end to end.", ["no ticket minting", "no Gateway reachability"]),
    "frontier_safety_vector_v2": ("Four-role Frontier port has not landed.", ["respondent", "provenance", "failure", "variance", "cost", "latency"]),
    "holdout_non_exposure": ("Sealed learning holdout is a P13.6 prerequisite.", ["optimizer-denied cases/traces/per-case scores"]),
    "promotion_override_rejection": ("Current lab promotion still accepts a force-promote argument.", ["failed hard gate cannot update CURRENT"]),
    "reward_identity_provenance": ("Global reward identity and transitive simulator separation are incomplete.", ["source-authenticated global row id", "human/simulator decision role"]),
    "monitor_counterexample_detectability": ("V2 monitor identity has not landed.", ["planted counterexample", "detection latency", "resulting hold"]),
    "executable_explanation_controls_v2": ("Four-role executable control routes have not landed.", ["route", "authority", "artifact", "receipt"]),
}


class P13CurrentAdapter:
    adapter_id = "p13_current"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.p12 = P12CurrentAdapter(root)

    def _write(self, path: Path, payload: dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def _keys(self, root: Path) -> tuple[Path, Path]:
        private_key = root / "scenario-private.pem"
        public_key = root / "scenario-public.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return private_key, public_key

    def _ruler_fixture(self, scenario_dir: Path, *, scope_kind: str = "frontend") -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        private_key, public_key = self._keys(scenario_dir)
        bundle = build_instrument_bundle(
            verification_key=public_key,
            artifact_config=self.root / "configs/p13_instrument_artifacts.json",
            require_clean=False,
        )
        bundle_path = self._write(scenario_dir / "instrument.json", bundle)
        if scope_kind == "optimizer":
            pattern = "calendar-pilot-p12/src/calendar_pilot/diffusiongemma/**"
            declared = {
                "actions": ["*"], "backends": ["nim"], "surfaces": ["frontier", "learning"],
                "instruments": [], "control_planes": ["optimizer"],
            }
        else:
            pattern = "calendar-pilot-p12/src/calendar_pilot/frontend/**"
            declared = {
                "actions": ["*"], "backends": [], "surfaces": ["frontend"],
                "instruments": [], "control_planes": [],
            }
        scope = {
            "wave_scope_schema_version": "p13_wave_scope.v1",
            "declared_paths": [pattern],
            "declared": declared,
            "required_scenarios": [],
            "old_producer": None,
            "new_producer": None,
            "live_legs": [],
        }
        scope_path = self._write(scenario_dir / "scope.json", scope)
        manifest = build_binding_manifest(
            wave=f"scenario-{scope_kind}",
            change_class="ruler" if scope_kind == "frontend" else "learning",
            scope_path=scope_path,
            instrument_bundle_path=bundle_path,
            ownership_map_path=self.root / "configs/p13_ownership_map.json",
            signing_key=private_key,
            verification_key=public_key,
            require_clean=False,
        )
        private_key.unlink()
        manifest_path = self._write(scenario_dir / "manifest.json", manifest)
        return {
            "bundle": bundle,
            "manifest": manifest,
            "public_key": public_key,
        }, [
            ("ruler_public_key", public_key),
            ("ruler_instrument", bundle_path),
            ("ruler_scope", scope_path),
            ("ruler_manifest", manifest_path),
        ]

    def collect(self, case: str, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        if case in DEBT_EVIDENCE:
            blocker, required = DEBT_EVIDENCE[case]
            return {"target_capability": {"reached": False, "blocker": blocker, "required_evidence": required}}, []
        if case not in {
            "binding_manifest_signature", "binding_manifest_affectedness",
            "instrument_mutation_rejection", "optimizer_write_boundary",
        }:
            return self.p12.collect(case, scenario_dir)

        if case == "optimizer_write_boundary":
            fixture, artifacts = self._ruler_fixture(scenario_dir, scope_kind="optimizer")
            protected = verify_binding_manifest(
                fixture["manifest"],
                verification_key=fixture["public_key"],
                changed_paths=["calendar-pilot-p12/src/calendar_pilot/swift_bridge/client.py"],
            )
            return {
                "ruler": {
                    "protected_path_decision": protected["decision"],
                    "protected_failure_codes": [row["code"] for row in protected["failures"]],
                }
            }, artifacts

        fixture, artifacts = self._ruler_fixture(scenario_dir)
        frontend_path = "calendar-pilot-p12/src/calendar_pilot/frontend/session.py"
        valid = verify_binding_manifest(
            fixture["manifest"], verification_key=fixture["public_key"], changed_paths=[frontend_path]
        )
        if case == "binding_manifest_signature":
            tampered = json.loads(json.dumps(fixture["manifest"]))
            tampered["declared_scope"]["paths"].append("calendar-pilot-p12/src/calendar_pilot/providers/**")
            rejected = verify_binding_manifest(tampered, verification_key=fixture["public_key"], changed_paths=[])
            return {
                "ruler": {
                    "valid_manifest_decision": valid["decision"],
                    "tampered_manifest_decision": rejected["decision"],
                    "tampered_failure_codes": [row["code"] for row in rejected["failures"]],
                }
            }, artifacts
        if case == "binding_manifest_affectedness":
            rejected = verify_binding_manifest(
                fixture["manifest"],
                verification_key=fixture["public_key"],
                changed_paths=["calendar-pilot-p12/src/calendar_pilot/providers/base.py"],
            )
            return {
                "ruler": {
                    "declared_diff_decision": valid["decision"],
                    "undeclared_diff_decision": rejected["decision"],
                    "undeclared_failure_codes": [row["code"] for row in rejected["failures"]],
                }
            }, artifacts

        bundle = json.loads(json.dumps(fixture["bundle"]))
        validate_instrument_bundle(bundle, verification_key=fixture["public_key"])
        bundle["artifacts"][0]["sha256"] = "0" * 64
        without_hash = dict(bundle)
        without_hash.pop("bundle_sha256")
        bundle["bundle_sha256"] = sha256_bytes(canonical_json_bytes(without_hash))
        rejected = False
        reason = ""
        try:
            validate_instrument_bundle(bundle, verification_key=fixture["public_key"])
        except ValueError as exc:
            rejected = True
            reason = str(exc)
        return {"ruler": {"baseline_valid": True, "tampered_rejected": rejected, "tampered_reason": reason}}, artifacts
