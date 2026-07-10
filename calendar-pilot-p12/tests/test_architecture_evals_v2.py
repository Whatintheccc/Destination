from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from evals.architecture.run_architecture_evals import (
    P13_SCENARIOS,
    REQUIRED_PRESERVATION_SCENARIO_IDS,
    build_report,
    load_scenario_set,
)
from evals.p13_ruler.core import APP_ROOT, build_binding_manifest, build_instrument_bundle
from evals.architecture.predicates.p13 import (
    cited_required_projection,
    product_core_no_effect_reachability,
    reducer_determinism,
)


RULER_TARGETS = {
    "target.binding_manifest_signature",
    "target.binding_manifest_affectedness",
    "target.binding_manifest_protected_path_rejection",
    "target.instrument_mutation_rejection",
    "target.promotion_override_rejection",
}

P13_1_TARGETS = {
    "target.reducer_determinism",
    "target.cited_required_projection",
    "target.product_core_no_effect_reachability",
}


class ArchitectureEvalV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (APP_ROOT / "runs").mkdir(parents=True, exist_ok=True)

    def _keys(self, root: Path) -> tuple[Path, Path]:
        private_key = root / "private.pem"
        public_key = root / "public.pem"
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

    def _binding(self, root: Path, *, required_targets: set[str]) -> tuple[Path, Path]:
        private_key, public_key = self._keys(root)
        bundle = build_instrument_bundle(
            verification_key=public_key,
            artifact_config=APP_ROOT / "configs/p13_instrument_artifacts.json",
            require_clean=False,
        )
        bundle_path = root / "instrument.json"
        bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        scope = {
            "wave_scope_schema_version": "p13_wave_scope.v1",
            "declared_paths": ["calendar-pilot-p12/evals/architecture/**"],
            "declared": {
                "actions": [],
                "backends": [],
                "surfaces": ["evaluation"],
                "instruments": ["architecture_eval"],
                "control_planes": ["evaluator"],
            },
            "required_scenarios": sorted(REQUIRED_PRESERVATION_SCENARIO_IDS | required_targets),
            "old_producer": None,
            "new_producer": None,
            "live_legs": [],
        }
        scope_path = root / "scope.json"
        scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
        manifest = build_binding_manifest(
            wave="architecture-v2-test",
            change_class="ruler",
            scope_path=scope_path,
            instrument_bundle_path=bundle_path,
            ownership_map_path=APP_ROOT / "configs/p13_ownership_map.json",
            signing_key=private_key,
            verification_key=public_key,
            require_clean=False,
        )
        private_key.unlink()
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest_path, public_key

    def test_v2_has_no_fixed_count_ceiling_but_keeps_required_families(self):
        scenario_set = load_scenario_set(P13_SCENARIOS)
        self.assertEqual(scenario_set["architecture_scenario_set_schema_version"], "architecture_scenario_set.v2")
        self.assertGreater(len(scenario_set["scenarios"]), 20)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "expanded.json"
            expanded = deepcopy(scenario_set)
            row = deepcopy(expanded["scenarios"][-1])
            row["scenario_id"] = "target.future_additive_scenario"
            expanded["scenarios"].append(row)
            path.write_text(json.dumps(expanded), encoding="utf-8")
            loaded = load_scenario_set(path)
            self.assertEqual(len(loaded["scenarios"]), len(scenario_set["scenarios"]) + 1)

    def test_v2_requires_a_verified_binding_manifest(self):
        with tempfile.TemporaryDirectory(dir=APP_ROOT / "runs") as td:
            root = Path(td)
            with self.assertRaisesRegex(ValueError, "requires BindingManifest"):
                build_report(
                    scenario_set_path=P13_SCENARIOS,
                    artifact_root=root / "artifacts",
                    out=root / "latest.json",
                )

    def test_manifest_selected_ruler_targets_bind_and_pass(self):
        with tempfile.TemporaryDirectory(dir=APP_ROOT / "runs") as td:
            root = Path(td)
            manifest_path, public_key = self._binding(root, required_targets=RULER_TARGETS)
            report = build_report(
                scenario_set_path=P13_SCENARIOS,
                binding_manifest_path=manifest_path,
                verification_key=public_key,
                binding_changed_paths=[],
                artifact_root=root / "artifacts",
                out=root / "latest.json",
            )
            self.assertEqual(report["architecture_eval_report_schema_version"], "architecture_eval_report.v2")
            self.assertEqual(report["decision"], "pass")
            self.assertEqual(report["rails"]["preservation"]["status_counts"]["pass"], 11)
            by_id = {row["scenario_id"]: row for row in report["scenarios"]}
            self.assertTrue(all(by_id[scenario_id]["gate_mode"] == "required" for scenario_id in RULER_TARGETS))
            self.assertTrue(all(by_id[scenario_id]["status"] == "pass" for scenario_id in RULER_TARGETS))
            self.assertGreater(report["rails"]["target_conformance"]["status_counts"]["not_reached"], 0)

    def test_required_unimplemented_target_blocks_with_hold(self):
        with tempfile.TemporaryDirectory(dir=APP_ROOT / "runs") as td:
            root = Path(td)
            manifest_path, public_key = self._binding(root, required_targets={"target.effect_ticket_binding"})
            report = build_report(
                scenario_set_path=P13_SCENARIOS,
                binding_manifest_path=manifest_path,
                verification_key=public_key,
                binding_changed_paths=[],
                artifact_root=root / "artifacts",
                out=root / "latest.json",
            )
            by_id = {row["scenario_id"]: row for row in report["scenarios"]}
            self.assertEqual(by_id["target.effect_ticket_binding"]["gate_mode"], "required")
            self.assertEqual(by_id["target.effect_ticket_binding"]["status"], "not_reached")
            self.assertEqual(report["decision"], "hold")

    def test_manifest_selected_p13_1_targets_bind_and_pass(self):
        with tempfile.TemporaryDirectory(dir=APP_ROOT / "runs") as td:
            root = Path(td)
            manifest_path, public_key = self._binding(root, required_targets=P13_1_TARGETS)
            report = build_report(
                scenario_set_path=P13_SCENARIOS,
                binding_manifest_path=manifest_path,
                verification_key=public_key,
                binding_changed_paths=[],
                artifact_root=root / "artifacts",
                out=root / "latest.json",
            )
            by_id = {row["scenario_id"]: row for row in report["scenarios"]}
            self.assertEqual(report["decision"], "pass")
            self.assertTrue(all(by_id[scenario_id]["gate_mode"] == "required" for scenario_id in P13_1_TARGETS))
            self.assertTrue(all(by_id[scenario_id]["status"] == "pass" for scenario_id in P13_1_TARGETS))

    def test_p13_1_predicates_reject_planted_counterexamples(self):
        deterministic = reducer_determinism({"product_core": {
            "first_sha256": "a",
            "second_sha256": "b",
            "reducer_version": "p13.1",
            "event_types": ["authenticated_observation", "frontier_proposal", "admission_preview"],
        }})
        cited = cited_required_projection({"product_core": {
            "status": "preview",
            "reducer_version": "p13.1",
            "required_fields_present": True,
            "evidence_row_ids": ["missing"],
            "all_evidence_rows_exist": False,
        }})
        reachable = product_core_no_effect_reachability({"product_core": {
            "can_dispatch": True,
            "forbidden_imports": [],
            "forbidden_preview_fields": [],
            "effect_counts": {"effect_attempts": 0, "claims": 0, "dispatches": 0, "provider_mutations": 0},
        }})
        self.assertEqual(deterministic["status"], "fail")
        self.assertEqual(cited["status"], "fail")
        self.assertEqual(reachable["status"], "fail")

    def test_optimizer_boundary_remains_explicit_debt(self):
        scenario_set = load_scenario_set(P13_SCENARIOS)
        row = next(row for row in scenario_set["scenarios"] if row["scenario_id"] == "target.optimizer_write_boundary")
        self.assertEqual(row["predicate_id"], "p13_target_not_implemented")


if __name__ == "__main__":
    unittest.main()
