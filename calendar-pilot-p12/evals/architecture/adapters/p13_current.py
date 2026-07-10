from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from jsonschema import Draft202012Validator

from evals.p13_ruler.core import (
    build_binding_manifest,
    build_instrument_bundle,
    canonical_json_bytes,
    sha256_bytes,
    validate_instrument_bundle,
    verify_binding_manifest,
)

from .p12_current import P12CurrentAdapter
from .p13_effect_scenarios import P13_3_CASES, collect_sandbox_effect_case
from .p13_eventkit_scenarios import P13_4_CASES, collect_eventkit_effect_case
from .p13_eventkit_retirement_scenarios import P13_5_EVENTKIT_CASES, collect_managed_eventkit_retirement_case
from .p13_learning_scenarios import P13_6_CASES, collect_learning_evidence
from .p13_retirement_scenarios import P13_5_CASES, collect_retirement_case


DEBT_EVIDENCE: dict[str, tuple[str, list[str]]] = {
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
    "retirement_scope_binding": ("The first P13.5 action/backend retirement has not landed.", ["exact create_prep_block and deterministic_sandbox scope", "unaffected EventKit and other-action ownership"]),
    "retirement_single_owner": ("The normal runtime still defaults to the incumbent effect path.", ["exact-pair EffectKernel default", "one effect-capable owner", "legacy normal-path denial"]),
    "retirement_runtime_commit": ("The visible commit access point does not yet route the retired pair through Gate/Gateway.", ["REQUEST_COMMIT evidence", "one ticket/claim/dispatch/mutation", "zero legacy mutations"]),
    "retirement_runtime_undo": ("The visible undo access point does not yet route the retired pair through a compensation ticket.", ["REQUEST_UNDO evidence", "separate compensation ticket", "verified absence", "zero legacy undo"]),
    "retirement_restart_rollback": ("Durable retirement ownership and owner-controlled rollback have not landed.", ["restart reconciliation", "stable exact-pair owner", "immutable selector rollback", "no dual owner"]),
    "eventkit_managed_binding_state": ("The managed EventKit binding lineage and epoch state machine have not landed.", ["opaque binding id and monotonic epoch", "exact store/calendar/source fingerprint", "permission and drift holds", "confirmed rebind"]),
    "eventkit_managed_ownership": ("The normal runtime has no omission-proof managed-calendar ownership classifier.", ["one expanded target vector", "bound-target classification without metadata", "mixed-target hold", "zero incumbent fallback"]),
    "eventkit_managed_runtime_commit": ("The visible commit access point does not yet own the managed EventKit binding through Gate/Gateway.", ["exact per-event confirmation", "two sequential one-use tickets", "inner identity validation", "post-save unknown reconciliation", "zero legacy commit"]),
    "eventkit_managed_runtime_undo": ("Managed EventKit undo is not yet routed by its creating receipt and epoch.", ["fresh compensation confirmation", "historical fingerprint", "exact old-epoch resolution", "identity-drift hold", "zero legacy undo"]),
    "eventkit_managed_durable_owner": ("The managed EventKit ledger and process ownership boundary have not landed.", ["global durable ledger/signing state", "crash-released single-owner lease", "missing/corrupt-state hold", "restart reconciliation without redispatch"]),
    "eventkit_managed_live_contract": ("The exact-candidate managed EventKit live retirement certificate has not landed.", ["canonical app and bridge identities", "confirmed binding record", "normal commit/undo access points", "post-verification", "restart and verified cleanup"]),
    "frontier_safety_vector_v2": ("Four-role Frontier port has not landed.", ["respondent", "provenance", "failure", "variance", "cost", "latency"]),
    "holdout_non_exposure": ("Sealed learning holdout is a P13.6 prerequisite.", ["optimizer-denied cases/traces/per-case scores"]),
    "optimizer_write_boundary": ("No isolated optimizer executor or denied-syscall/mount-profile evidence exists.", ["declared candidate writes succeed", "evaluator/manifest/TCB/CURRENT writes are denied by the execution boundary"]),
    "signed_policy_promotion": ("The signed PolicyPayload/PromotionRecord transition and rollback drill have not landed.", ["content-addressed immutable payload", "signed pass record", "atomic CURRENT transition", "bad-payload rejection", "signed rollback"]),
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

    def _promotion_tree_digest(self) -> str:
        digest = hashlib.sha256()
        for root in [self.root / "experiments/promoted", self.root / "experiments/reports"]:
            if not root.exists():
                continue
            for path in sorted(value for value in root.rglob("*") if value.is_file()):
                digest.update(path.relative_to(self.root).as_posix().encode("utf-8"))
                digest.update(b"\0")
                digest.update(path.read_bytes())
                digest.update(b"\0")
        return digest.hexdigest()

    def _product_core_fixture(self) -> Any:
        from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
        from calendar_pilot.product_core import run_create_prep_block_vertical
        from calendar_pilot.types import RawCalendarObservation, UserBiography

        observation = RawCalendarObservation.from_dict(
            json.loads((self.root / "data/sample_calendar.json").read_text(encoding="utf-8"))
        )
        biography = UserBiography.from_dict(
            json.loads((self.root / "data/sample_profile.json").read_text(encoding="utf-8"))
        )
        candidate = next(
            row
            for row in DiffusionGemmaPolicy().generate_candidates(observation, biography)
            if row.intent == "create_prep_block"
        )
        return run_create_prep_block_vertical(
            observation,
            candidate,
            source_authenticated=True,
            received_at=observation.observed_at,
        )

    def _product_core_evidence(self, case: str, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        first = self._product_core_fixture()
        second = self._product_core_fixture()
        observable = first.to_observable()
        projection = first.preview.projection
        if case == "reducer_determinism":
            evidence = {
                "first_sha256": sha256_bytes(canonical_json_bytes(observable)),
                "second_sha256": sha256_bytes(canonical_json_bytes(second.to_observable())),
                "reducer_version": first.preview.reducer_version,
                "event_types": [event.event_type for event in first.events],
            }
        elif case == "cited_required_projection":
            row_ids = {event.row_id for event in first.events}
            evidence_ids = list(projection.evidence_row_ids) if projection is not None else []
            evidence = {
                "status": first.preview.status,
                "reducer_version": first.preview.reducer_version,
                "required_fields_present": bool(
                    projection
                    and projection.title
                    and projection.start
                    and projection.end
                    and projection.calendar_id
                    and projection.explanation
                ),
                "evidence_row_ids": evidence_ids,
                "all_evidence_rows_exist": bool(evidence_ids) and set(evidence_ids).issubset(row_ids),
            }
        else:
            package_root = self.root / "src/calendar_pilot/product_core"
            forbidden_roots = {
                "calendar_pilot.providers",
                "calendar_pilot.swift_bridge",
                "calendar_pilot.environment.action_lifecycle",
                "subprocess",
                "socket",
                "urllib",
                "http",
            }
            imports: set[str] = set()
            for path in package_root.glob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.update(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module)
            forbidden_imports = sorted(
                name
                for name in imports
                if any(name == root or name.startswith(root + ".") for root in forbidden_roots)
            )
            preview_fields = set(first.preview.__dataclass_fields__)
            effect_fields = {
                "ticket", "ticket_id", "signature", "nonce", "grant", "provider",
                "credential", "idempotency_key",
            }
            evidence = {
                "can_dispatch": first.preview.can_dispatch,
                "forbidden_imports": forbidden_imports,
                "forbidden_preview_fields": sorted(preview_fields & effect_fields),
                "effect_counts": observable["effects"],
            }
        path = self._write(scenario_dir / f"{case}.json", evidence)
        return {"product_core": evidence}, [(f"product_core_{case}", path)]

    def _cited_read_side_evidence(self, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        from scripts.produce_b_migrate_p13_2_new import build_artifact as build_new
        from scripts.produce_b_migrate_p13_2_old import build_artifact as build_old

        manifest = json.loads(
            (self.root / "experiments/configs/create_prep_block_required_fields_v1.json").read_text(encoding="utf-8")
        )
        schema = json.loads(
            (self.root / "contracts/required_field_manifest.schema.json").read_text(encoding="utf-8")
        )
        old = build_old()["observable"]
        new = build_new()["observable"]
        card = {
            **new.get("protected_card", {}),
            "citation": new.get("citation", {}),
            "projection": new.get("projection", {}),
            "controls": new.get("controls", []),
        }

        def has_path(payload: dict[str, Any], dotted: str) -> bool:
            value: Any = payload
            for part in dotted.split("."):
                if not isinstance(value, dict) or part not in value:
                    return False
                value = value[part]
            return True

        required_paths = [*manifest["protected_fields"], *manifest["cited_fields"]]
        citation = new.get("citation", {})
        evidence = {
            "manifest_valid": not bool(list(Draft202012Validator(schema).iter_errors(manifest))),
            "protected_fields_equal": old.get("protected_card") == new.get("protected_card"),
            "required_fields_present": all(has_path(card, path) for path in required_paths),
            "citation_event_ids": citation.get("event_ids", []),
            "all_citations_in_journal": new.get("all_citations_in_journal"),
            "reducer_version": citation.get("reducer_version"),
            "projection_version": citation.get("projection_version"),
            "controls": new.get("controls", []),
            "restart_restored": new.get("restart_restored"),
            "effect_counts": new.get("new_effect_counts", {}),
        }
        path = self._write(scenario_dir / "cited_read_side_cutover.json", evidence)
        return {"read_side": evidence}, [("cited_read_side_cutover", path)]

    def _sandbox_effect_evidence(self, case: str, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        evidence = collect_sandbox_effect_case(case, scenario_dir=scenario_dir, root=self.root)
        if evidence is None:
            blocker, required = DEBT_EVIDENCE[case]
            return {
                "target_capability": {
                    "reached": False,
                    "blocker": blocker,
                    "required_evidence": required,
                }
            }, []
        path = self._write(scenario_dir / f"{case}.json", evidence)
        return {"effect_kernel": evidence}, [(f"effect_kernel_{case}", path)]

    def _eventkit_effect_evidence(self, case: str, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        evidence = collect_eventkit_effect_case(case, scenario_dir=scenario_dir, root=self.root)
        if evidence is None:
            return {
                "target_capability": {
                    "reached": False,
                    "blocker": "P13.4 app-bundled EventKit effect kernel has not landed.",
                    "required_evidence": [
                        "owner-controlled EventKit authority profile",
                        "canonical app/bridge and sandbox-calendar binding",
                        "ticket-checked provider lifecycle and compensation facts",
                    ],
                }
            }, []
        path = self._write(scenario_dir / f"{case}.json", evidence)
        return {"eventkit_effect_kernel": evidence}, [(f"eventkit_effect_kernel_{case}", path)]

    def _retirement_evidence(self, case: str, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        evidence = collect_retirement_case(case, scenario_dir=scenario_dir, root=self.root)
        if evidence is None:
            blocker, required = DEBT_EVIDENCE[case]
            return {"target_capability": {"reached": False, "blocker": blocker, "required_evidence": required}}, []
        path = self._write(scenario_dir / f"{case}.json", evidence)
        return {"vertical_retirement": evidence}, [(f"vertical_retirement_{case}", path)]

    def _managed_eventkit_retirement_evidence(self, case: str, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        evidence = collect_managed_eventkit_retirement_case(case, scenario_dir=scenario_dir, root=self.root)
        if evidence is None:
            blocker, required = DEBT_EVIDENCE[case]
            return {"target_capability": {"reached": False, "blocker": blocker, "required_evidence": required}}, []
        path = self._write(scenario_dir / f"{case}.json", evidence)
        return {"managed_eventkit_retirement": evidence}, [(f"managed_eventkit_retirement_{case}", path)]

    def _promotion_freeze_evidence(self, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        current = self.root / "experiments/promoted/CURRENT.json"
        current_before = current.read_bytes()
        tree_before = self._promotion_tree_digest()

        def invoke(*extra: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
            process = subprocess.run(
                ["python3", "scripts/promote_policy.py", "--batch", "architecture-eval-freeze", *extra],
                cwd=self.root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            try:
                payload = json.loads(process.stdout)
            except json.JSONDecodeError:
                payload = {}
            return process, payload

        forced, forced_payload = invoke("--decide", "promote")
        automatic, automatic_payload = invoke()
        evidence = {
            "forced_returncode": forced.returncode,
            "automatic_returncode": automatic.returncode,
            "forced_decision": forced_payload.get("decision"),
            "automatic_decision": automatic_payload.get("decision"),
            "current_unchanged": current.read_bytes() == current_before,
            "promotion_trees_unchanged": self._promotion_tree_digest() == tree_before,
            "promotion_artifact_writes": max(
                int(forced_payload.get("promotion_artifact_writes", -1)),
                int(automatic_payload.get("promotion_artifact_writes", -1)),
            ),
        }
        evidence_path = self._write(scenario_dir / "promotion_freeze_evidence.json", evidence)
        return {"promotion": evidence}, [("promotion_freeze_evidence", evidence_path)]

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
        if case in {"reducer_determinism", "cited_required_projection", "product_core_no_effect_reachability"}:
            return self._product_core_evidence(case, scenario_dir)
        if case == "cited_read_side_cutover":
            return self._cited_read_side_evidence(scenario_dir)
        if case in P13_3_CASES:
            return self._sandbox_effect_evidence(case, scenario_dir)
        if case in P13_4_CASES:
            return self._eventkit_effect_evidence(case, scenario_dir)
        if case in P13_5_CASES:
            return self._retirement_evidence(case, scenario_dir)
        if case in P13_5_EVENTKIT_CASES:
            return self._managed_eventkit_retirement_evidence(case, scenario_dir)
        if case in P13_6_CASES and os.environ.get("CALENDAR_PILOT_ARCH_P13_6") == "1":
            return collect_learning_evidence(case, scenario_dir)
        if case in DEBT_EVIDENCE:
            blocker, required = DEBT_EVIDENCE[case]
            return {"target_capability": {"reached": False, "blocker": blocker, "required_evidence": required}}, []
        if case not in {
            "binding_manifest_signature", "binding_manifest_affectedness",
            "instrument_mutation_rejection", "binding_manifest_protected_path_rejection",
            "promotion_override_rejection",
        }:
            return self.p12.collect(case, scenario_dir)

        if case == "promotion_override_rejection":
            return self._promotion_freeze_evidence(scenario_dir)

        if case == "binding_manifest_protected_path_rejection":
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
