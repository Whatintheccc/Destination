from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
import sys

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evals.p13_ruler.core import canonical_json_bytes, sha256_bytes, sha256_file
from evals.p13_ruler.wave import (
    P13_3_SANDBOX_SCENARIOS,
    P13_4_EVENTKIT_SCENARIOS,
    P13_5_RETIREMENT_SCENARIOS,
    build_b_migrate_artifact,
    build_cvar_frontier_set,
    build_experiment_record,
    b_migrate_assertions_path,
    compare_b_migrate_artifacts,
    compare_cvar_frontier_sets,
    is_owner_controlled_eventkit_sandbox_wave,
    is_owner_controlled_sandbox_wave,
    is_owner_controlled_vertical_retirement_wave,
    is_structurally_no_effect_wave,
    verify_root_list,
)
from scripts.make_reward_head_report import build_report as build_reward_report
from scripts.run_b_migrate_dual_run_v2 import _assertions_path


def _manifest() -> dict:
    return {
        "manifest_id": "test:manifest",
        "change_class": "ruler",
        "base_repository": {"git_sha": "base"},
        "old_producer": {
            "cvar": {
                "producer_id": "cvar.before.current",
                "command": ["python3", "scripts/produce_cvar_frontier.py", "--role", "before", "--current", "experiments/promoted/CURRENT.json"],
            },
            "b_migrate": {
                "producer_id": "b_migrate.old.session_snapshot",
                "command": ["python3", "scripts/produce_b_migrate_old.py"],
            },
        },
        "new_producer": {
            "cvar": {
                "producer_id": "cvar.after.current",
                "command": ["python3", "scripts/produce_cvar_frontier.py", "--role", "after", "--current", "experiments/promoted/CURRENT.json"],
            },
            "b_migrate": {
                "producer_id": "b_migrate.new.frontend_projector",
                "command": ["python3", "scripts/produce_b_migrate_new.py"],
            },
        },
        "live_legs": [],
    }


class P13WaveHarnessV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        manifest = _manifest()
        cls.before_cvar = build_cvar_frontier_set(
            role="before",
            current_path=ROOT / "experiments/promoted/CURRENT.json",
            seed_set_path=ROOT / "experiments/configs/cvar_seed_set.json",
            producer_id=manifest["old_producer"]["cvar"]["producer_id"],
            bound_command=manifest["old_producer"]["cvar"]["command"],
        )
        cls.after_cvar = build_cvar_frontier_set(
            role="after",
            current_path=ROOT / "experiments/promoted/CURRENT.json",
            seed_set_path=ROOT / "experiments/configs/cvar_seed_set.json",
            producer_id=manifest["new_producer"]["cvar"]["producer_id"],
            bound_command=manifest["new_producer"]["cvar"]["command"],
        )

    def test_cvar_consumes_distinct_artifacts_and_rejects_self_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            before_path = Path(td) / "before.json"
            after_path = Path(td) / "after.json"
            before_path.write_text(json.dumps(self.before_cvar), encoding="utf-8")
            after_path.write_text(json.dumps(self.after_cvar), encoding="utf-8")
            report = compare_cvar_frontier_sets(
                before_path=before_path,
                after_path=after_path,
                thresholds_path=ROOT / "experiments/configs/cvar_thresholds.json",
                manifest=_manifest(),
            )
            self.assertEqual(report["decision"], "pass")
            planted = compare_cvar_frontier_sets(
                before_path=before_path,
                after_path=before_path,
                thresholds_path=ROOT / "experiments/configs/cvar_thresholds.json",
                manifest=_manifest(),
            )
            self.assertEqual(planted["decision"], "hold")
            self.assertEqual(planted["gates"]["artifact_independence"]["status"], "hold")
            tampered = deepcopy(self.after_cvar)
            tampered["rows"][0]["frontier"][0]["expected_reward"] += 1.0
            after_path.write_text(json.dumps(tampered), encoding="utf-8")
            integrity = compare_cvar_frontier_sets(
                before_path=before_path,
                after_path=after_path,
                thresholds_path=ROOT / "experiments/configs/cvar_thresholds.json",
                manifest=_manifest(),
            )
            self.assertEqual(integrity["gates"]["artifact_integrity"]["status"], "hold")

    def test_behavior_cvar_requires_clean_frozen_before_and_changed_after(self):
        with tempfile.TemporaryDirectory() as td:
            before = deepcopy(self.before_cvar)
            after = deepcopy(self.after_cvar)
            before["source_revision"].update({"clean": True, "git_sha": "base", "source_sha256": "same"})
            after["source_revision"].update({"source_sha256": "same"})
            before["tuning"]["policy_tuning_sha256"] = "same"
            after["tuning"]["policy_tuning_sha256"] = "same"
            for payload in [before, after]:
                stable = {key: value for key, value in payload.items() if key not in {"generated_at", "cvar_frontier_set_schema_version", "content_sha256"}}
                payload["content_sha256"] = sha256_bytes(canonical_json_bytes(stable))
            before_path = Path(td) / "before.json"
            after_path = Path(td) / "after.json"
            before_path.write_text(json.dumps(before), encoding="utf-8")
            after_path.write_text(json.dumps(after), encoding="utf-8")
            manifest = _manifest()
            manifest["change_class"] = "compression"
            report = compare_cvar_frontier_sets(
                before_path=before_path,
                after_path=after_path,
                thresholds_path=ROOT / "experiments/configs/cvar_thresholds.json",
                manifest=manifest,
            )
            self.assertEqual(report["decision"], "hold")
            self.assertEqual(report["gates"]["generated_after_source"]["status"], "hold")

    def test_b_migrate_runs_independent_producers_and_rejects_alias(self):
        manifest = _manifest()
        old = build_b_migrate_artifact(
            role="old",
            producer_id=manifest["old_producer"]["b_migrate"]["producer_id"],
            bound_command=manifest["old_producer"]["b_migrate"]["command"],
        )
        new = build_b_migrate_artifact(
            role="new",
            producer_id=manifest["new_producer"]["b_migrate"]["producer_id"],
            bound_command=manifest["new_producer"]["b_migrate"]["command"],
        )
        with tempfile.TemporaryDirectory() as td:
            old_path = Path(td) / "old.json"
            new_path = Path(td) / "new.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            new_path.write_text(json.dumps(new), encoding="utf-8")
            report = compare_b_migrate_artifacts(
                before_path=old_path,
                after_path=new_path,
                assertions_path=ROOT / "experiments/configs/b_migrate_frontend_view_state_v2.json",
                manifest=manifest,
            )
            self.assertEqual(report["decision"], "pass")
            alias = deepcopy(new)
            alias["producer"] = deepcopy(old["producer"])
            new_path.write_text(json.dumps(alias), encoding="utf-8")
            planted = compare_b_migrate_artifacts(
                before_path=old_path,
                after_path=new_path,
                assertions_path=ROOT / "experiments/configs/b_migrate_frontend_view_state_v2.json",
                manifest=manifest,
            )
            self.assertEqual(planted["decision"], "hold")
            self.assertIn("identical_producer", {row["code"] for row in planted["failures"]})

    def test_b_migrate_assertion_set_is_manifest_bound(self):
        manifest = _manifest()
        self.assertEqual(
            b_migrate_assertions_path(manifest),
            ROOT / "experiments/configs/b_migrate_frontend_view_state_v2.json",
        )
        with tempfile.TemporaryDirectory() as td:
            assertions = Path(td) / "assertions.json"
            assertions.write_text("{}", encoding="utf-8")
            binding = {"path": str(assertions), "sha256": sha256_file(assertions)}
            manifest["old_producer"]["b_migrate"]["assertion_set"] = binding
            manifest["new_producer"]["b_migrate"]["assertion_set"] = deepcopy(binding)
            self.assertEqual(b_migrate_assertions_path(manifest), assertions)
            self.assertEqual(_assertions_path(manifest), assertions)
            other = Path(td) / "other.json"
            other.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot override"):
                _assertions_path(manifest, str(other))
            manifest["new_producer"]["b_migrate"]["assertion_set"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "same assertion set"):
                b_migrate_assertions_path(manifest)

    def test_root_list_expiry_and_missing_behavior_coverage_hold(self):
        manifest = _manifest()
        manifest["change_class"] = "migration"
        missing = verify_root_list(manifest)
        self.assertEqual(missing["decision"], "hold")
        with tempfile.TemporaryDirectory() as td:
            artifact = Path(td) / "last-pass.json"
            artifact.write_text("{}", encoding="utf-8")
            manifest["live_legs"] = [
                {
                    "leg": "live-eventkit-e2e",
                    "status": "root-listed",
                    "reason": {"basis": "unavailable", "detail": "sandbox unavailable"},
                    "artifact": {"path": str(artifact), "sha256": __import__("hashlib").sha256(b"{}").hexdigest()},
                    "owner": "provider owner",
                    "sign_off": "owner-frozen affected leg",
                    "affected_by_wave": True,
                    "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                    "next_unblock_action": "run the sandbox leg",
                }
            ]
            expired = verify_root_list(manifest)
            self.assertEqual(expired["decision"], "hold")
            self.assertEqual(expired["hold_reasons"][0]["code"], "root_list_expired")
            self.assertIn("affected_live_leg_not_run", {row["code"] for row in expired["hold_reasons"]})

    def test_v2_experiment_contract_names_the_eight_evidence_fields(self):
        schema = json.loads((ROOT / "contracts/experiment_record_v2.schema.json").read_text(encoding="utf-8"))
        template = json.loads((ROOT / "experiments/templates/experiment_record_v2.template.json").read_text(encoding="utf-8"))
        core = {"delta", "fixed", "rows", "baseline", "effect", "regressed", "ablation", "rollback"}
        self.assertTrue(core.issubset(schema["required"]))
        self.assertTrue(core.issubset(template))
        self.assertEqual(template["phase"], "P13")
        Draft202012Validator(schema).validate(template)
        broken = deepcopy(template)
        broken["change_class"] = "compression"
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(broken)))

    def test_no_effect_migration_record_passes_only_with_exact_additive_rollback(self):
        schema = json.loads((ROOT / "contracts/experiment_record_v2.schema.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def write(name: str, payload: dict) -> Path:
                path = root / name
                path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                return path

            manifest = {
                "manifest_id": "p13-no-effect:test",
                "wave": "p13-no-effect-test",
                "change_class": "migration",
                "base_repository": {"git_sha": "base-sha", "app_tree_sha": "base-app-tree"},
                "instrument_bundle": {"bundle_sha256": "bundle", "file_sha256": "bundle-file"},
                "required_scenarios": ["target.product_core_no_effect_reachability"],
            }
            verification = {
                "decision": "pass",
                "changed_paths": [{"path": "calendar-pilot-p12/src/calendar_pilot/product_core/new.py"}],
                "derived_affectedness": {
                    "actions": ["create_prep_block"],
                    "backends": [],
                    "surfaces": ["journal", "projection", "reducer"],
                    "instruments": [],
                    "control_planes": [],
                },
            }
            architecture = {
                "decision": "pass",
                "rails": {"preservation": {"status_counts": {"pass": 11}}},
                "scenarios": [{
                    "scenario_id": "target.product_core_no_effect_reachability",
                    "gate_mode": "required",
                    "status": "pass",
                }],
            }
            cvar = {
                "decision": "pass",
                "compared_rows": [{"seed_id": "seed:one", "delta_top_reward": 0.0}],
                "promotion_decisions": {"before": "promote", "after": "promote"},
                "bootstrap": {"mean_delta": 0.0, "ci95": [0.0, 0.0], "variance": 0.0},
                "borderline": {"flip_rate": 0.0},
                "thresholds": {"values": {"max_delta_variance": 0.0025}},
                "before_artifact": {"path": "before.json", "sha256": "before"},
            }
            b_migrate = {
                "decision": "pass",
                "assertions": [{"name": "projection", "status": "pass"}],
                "before_artifact": {"path": "old.json", "sha256": "old"},
            }
            release = {"decision": "pass"}
            reward = {
                "decision": "pass",
                "reward_head_deltas": {},
                "reward_evidence": {"consumed_reward_rows": [], "declared_source_classification": {}},
            }
            paths = {
                "manifest_path": write("manifest.json", manifest),
                "binding_verification_path": write("binding.json", verification),
                "architecture_report_path": write("architecture.json", architecture),
                "cvar_report_path": write("cvar.json", cvar),
                "b_migrate_report_path": write("b_migrate.json", b_migrate),
                "release_report_path": write("release.json", release),
                "reward_report_path": write("reward.json", reward),
                "root_list_report_path": write("root_list.json", {"decision": "pass"}),
                "loc_report_path": write("loc.json", {"decision": "pass", "delta": {"delta_lines": 10}}),
            }
            candidate = {"git_sha": "candidate-sha", "app_tree_sha": "candidate-app-tree"}
            additive = [{"status": "A", "path": "calendar-pilot-p12/src/calendar_pilot/product_core/new.py"}]
            record = build_experiment_record(**paths, candidate_repository=candidate, git_delta=additive)
            Draft202012Validator(schema).validate(record)
            self.assertEqual(record["decision"], "pass")
            self.assertTrue(record["ablation"]["decision_stable"])
            self.assertTrue(record["rollback"]["baseline_restored"])
            self.assertEqual(record["identifiability"]["status"], "identified")
            self.assertTrue(is_structurally_no_effect_wave(manifest, verification, architecture))

            modified = build_experiment_record(
                **paths,
                candidate_repository=candidate,
                git_delta=[{"status": "M", "path": additive[0]["path"]}],
            )
            Draft202012Validator(schema).validate(modified)
            self.assertEqual(modified["decision"], "hold")
            self.assertFalse(modified["rollback"]["baseline_restored"])

            forged = deepcopy(modified)
            forged["decision"] = "pass"
            self.assertTrue(list(Draft202012Validator(schema).iter_errors(forged)))

            manifest["required_scenarios"].append("target.cited_read_side_cutover")
            architecture["scenarios"].append({
                "scenario_id": "target.cited_read_side_cutover",
                "gate_mode": "required",
                "status": "pass",
            })
            paths["manifest_path"] = write("manifest.json", manifest)
            paths["architecture_report_path"] = write("architecture.json", architecture)
            read_side = build_experiment_record(
                **paths,
                candidate_repository=candidate,
                git_delta=[{"status": "M", "path": additive[0]["path"]}],
            )
            Draft202012Validator(schema).validate(read_side)
            self.assertEqual(read_side["decision"], "pass")
            self.assertEqual(read_side["rollback"]["proof_artifact"]["mode"], "incumbent_read_selector")

    def test_sandbox_migration_record_passes_only_for_exact_additive_non_authorizing_scope(self):
        schema = json.loads((ROOT / "contracts/experiment_record_v2.schema.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def write(name: str, payload: dict) -> Path:
                path = root / name
                path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                return path

            changed = [
                "calendar-pilot-p12/src/calendar_pilot/effect_kernel/kernel.py",
                "calendar-pilot-p12/tests/test_p13_deterministic_sandbox.py",
            ]
            manifest = {
                "manifest_id": "p13-sandbox:test",
                "wave": "p13-sandbox-test",
                "change_class": "migration",
                "base_repository": {"git_sha": "base-sha", "app_tree_sha": "base-app-tree"},
                "instrument_bundle": {"bundle_sha256": "bundle", "file_sha256": "bundle-file"},
                "required_scenarios": sorted(P13_3_SANDBOX_SCENARIOS),
            }
            verification = {
                "decision": "pass",
                "changed_paths": [{"path": path} for path in changed],
                "derived_affectedness": {
                    "actions": ["create_prep_block"],
                    "backends": ["deterministic_sandbox"],
                    "surfaces": ["authority_gate", "effect_gateway", "provider", "tests"],
                    "instruments": ["tests"],
                    "control_planes": ["effect_tcb", "evaluator"],
                },
            }
            architecture = {
                "decision": "pass",
                "rails": {"preservation": {"status_counts": {"pass": 11}}},
                "scenarios": [
                    {"scenario_id": scenario_id, "gate_mode": "required", "status": "pass"}
                    for scenario_id in sorted(P13_3_SANDBOX_SCENARIOS)
                ],
            }
            cvar = {
                "decision": "pass",
                "compared_rows": [{"seed_id": "seed:one", "delta_top_reward": 0.0}],
                "promotion_decisions": {"before": "promote", "after": "promote"},
                "bootstrap": {"mean_delta": 0.0, "ci95": [0.0, 0.0], "variance": 0.0},
                "borderline": {"flip_rate": 0.0},
                "thresholds": {"values": {"max_delta_variance": 0.0025}},
                "before_artifact": {"path": "before.json", "sha256": "before"},
            }
            b_migrate = {
                "decision": "pass",
                "assertions": [{"name": "verified_normal_outcome", "status": "pass"}],
                "before_artifact": {"path": "old.json", "sha256": "old"},
            }
            reward = {
                "decision": "pass",
                "reward_head_deltas": {},
                "reward_evidence": {"consumed_reward_rows": [], "declared_source_classification": {}},
            }
            paths = {
                "manifest_path": write("manifest.json", manifest),
                "binding_verification_path": write("binding.json", verification),
                "architecture_report_path": write("architecture.json", architecture),
                "cvar_report_path": write("cvar.json", cvar),
                "b_migrate_report_path": write("b_migrate.json", b_migrate),
                "release_report_path": write("release.json", {"decision": "pass"}),
                "reward_report_path": write("reward.json", reward),
                "root_list_report_path": write("root_list.json", {"decision": "pass"}),
                "loc_report_path": write("loc.json", {"decision": "pass", "delta": {"delta_lines": 700}}),
            }
            record = build_experiment_record(
                **paths,
                candidate_repository={"git_sha": "candidate", "app_tree_sha": "candidate-tree"},
                git_delta=[{"status": "A", "path": path} for path in changed],
            )
            Draft202012Validator(schema).validate(record)
            self.assertTrue(is_owner_controlled_sandbox_wave(manifest, verification, architecture))
            self.assertEqual(record["decision"], "pass")
            self.assertEqual(record["candidate"]["evidence_class"], "owner_controlled_sandbox")
            self.assertEqual(record["rollback"]["proof_artifact"]["mode"], "exact_additive_sandbox_revert")
            self.assertEqual(record["outcomes"]["outcome_window"], "not_applicable_non_authorizing_sandbox")

            broadened = deepcopy(verification)
            broadened["derived_affectedness"]["backends"] = ["deterministic_sandbox", "eventkit"]
            self.assertFalse(is_owner_controlled_sandbox_wave(manifest, broadened, architecture))

    def test_eventkit_sandbox_record_uses_manifest_complete_incumbent_selector_rollback(self):
        schema = json.loads((ROOT / "contracts/experiment_record_v2.schema.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def write(name: str, payload: dict) -> Path:
                path = root / name
                path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                return path

            changed = [
                "calendar-pilot-p12/src/calendar_pilot/effect_kernel/kernel.py",
                "calendar-pilot-p12/scripts/run_live_eventkit_e2e.py",
                "calendar-pilot-p12/tests/test_p13_eventkit_sandbox.py",
            ]
            manifest = {
                "manifest_id": "p13-eventkit:test",
                "wave": "p13-eventkit-test",
                "change_class": "migration",
                "base_repository": {"git_sha": "base-sha", "app_tree_sha": "base-app-tree"},
                "instrument_bundle": {"bundle_sha256": "bundle", "file_sha256": "bundle-file"},
                "required_scenarios": sorted(P13_4_EVENTKIT_SCENARIOS),
            }
            verification = {
                "decision": "pass",
                "changed_paths": [{"path": path} for path in changed],
                "derived_affectedness": {
                    "actions": ["create_prep_block"],
                    "backends": ["deterministic_sandbox"],
                    "surfaces": ["authority_gate", "effect_gateway", "provider", "ruler_scripts", "tests"],
                    "instruments": ["release_and_wave_ruler", "tests"],
                    "control_planes": ["effect_tcb", "evaluator", "optimizer"],
                },
            }
            architecture = {
                "decision": "pass",
                "rails": {"preservation": {"status_counts": {"pass": 11}}},
                "scenarios": [
                    {"scenario_id": scenario_id, "gate_mode": "required", "status": "pass"}
                    for scenario_id in sorted(P13_4_EVENTKIT_SCENARIOS)
                ],
            }
            cvar = {
                "decision": "pass",
                "compared_rows": [{"seed_id": "seed:one", "delta_top_reward": 0.0}],
                "promotion_decisions": {"before": "promote", "after": "promote"},
                "bootstrap": {"mean_delta": 0.0, "ci95": [0.0, 0.0], "variance": 0.0},
                "borderline": {"flip_rate": 0.0},
                "thresholds": {"values": {"max_delta_variance": 0.0025}},
                "before_artifact": {"path": "before.json", "sha256": "before"},
            }
            b_migrate = {
                "decision": "pass",
                "assertions": [{"name": "verified_normal_outcome", "status": "pass"}],
                "before_artifact": {"path": "old.json", "sha256": "old"},
            }
            reward = {
                "decision": "pass",
                "reward_head_deltas": {},
                "reward_evidence": {"consumed_reward_rows": [], "declared_source_classification": {}},
            }
            paths = {
                "manifest_path": write("manifest.json", manifest),
                "binding_verification_path": write("binding.json", verification),
                "architecture_report_path": write("architecture.json", architecture),
                "cvar_report_path": write("cvar.json", cvar),
                "b_migrate_report_path": write("b_migrate.json", b_migrate),
                "release_report_path": write("release.json", {"decision": "pass"}),
                "reward_report_path": write("reward.json", reward),
                "root_list_report_path": write("root_list.json", {"decision": "pass"}),
                "loc_report_path": write("loc.json", {"decision": "pass", "delta": {"delta_lines": 800}}),
            }
            record = build_experiment_record(
                **paths,
                candidate_repository={"git_sha": "candidate", "app_tree_sha": "candidate-tree"},
                git_delta=[{"status": "M", "path": path} for path in changed],
            )
            Draft202012Validator(schema).validate(record)
            self.assertTrue(is_owner_controlled_eventkit_sandbox_wave(manifest, verification, architecture))
            self.assertEqual(record["decision"], "pass")
            self.assertEqual(record["candidate"]["evidence_class"], "owner_controlled_eventkit_sandbox")
            self.assertEqual(record["rollback"]["proof_artifact"]["mode"], "incumbent_effect_selector")
            self.assertEqual(record["outcomes"]["outcome_window"], "bounded_owner_controlled_eventkit_probe")

    def test_vertical_retirement_record_requires_exact_scope_and_owner_frozen_rollback(self):
        schema = json.loads((ROOT / "contracts/experiment_record_v2.schema.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def write(name: str, payload: dict) -> Path:
                path = root / name
                path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                return path

            changed = [
                "calendar-pilot-p12/src/calendar_pilot/effect_kernel/retirement.py",
                "calendar-pilot-p12/src/calendar_pilot/codex/tools.py",
                "calendar-pilot-p12/tests/test_p13_deterministic_retirement.py",
            ]
            manifest = {
                "manifest_id": "p13-retirement:test",
                "wave": "p13-retirement-test",
                "change_class": "migration",
                "base_repository": {"git_sha": "base-sha", "app_tree_sha": "base-app-tree"},
                "instrument_bundle": {"bundle_sha256": "bundle", "file_sha256": "bundle-file"},
                "required_scenarios": sorted(P13_5_RETIREMENT_SCENARIOS),
            }
            verification = {
                "decision": "pass",
                "changed_paths": [{"path": path} for path in changed],
                "derived_affectedness": {
                    "actions": ["create_prep_block"],
                    "backends": ["deterministic_sandbox"],
                    "surfaces": ["authority_gate", "effect_gateway", "provider", "tests"],
                    "instruments": ["release_and_wave_ruler", "tests"],
                    "control_planes": ["effect_tcb", "evaluator", "optimizer"],
                },
            }
            architecture = {
                "decision": "pass",
                "rails": {"preservation": {"status_counts": {"pass": 11}}},
                "scenarios": [
                    {"scenario_id": scenario_id, "gate_mode": "required", "status": "pass"}
                    for scenario_id in sorted(P13_5_RETIREMENT_SCENARIOS)
                ],
            }
            cvar = {
                "decision": "pass",
                "compared_rows": [{"seed_id": "seed:one", "delta_top_reward": 0.0}],
                "promotion_decisions": {"before": "promote", "after": "promote"},
                "bootstrap": {"mean_delta": 0.0, "ci95": [0.0, 0.0], "variance": 0.0},
                "borderline": {"flip_rate": 0.0},
                "thresholds": {"values": {"max_delta_variance": 0.0025}},
                "before_artifact": {"path": "before.json", "sha256": "before"},
            }
            b_migrate = {
                "decision": "pass",
                "assertions": [{"name": "verified_normal_outcome", "status": "pass"}],
                "before_artifact": {"path": "old.json", "sha256": "old"},
            }
            reward = {
                "decision": "pass",
                "reward_head_deltas": {},
                "reward_evidence": {"consumed_reward_rows": [], "declared_source_classification": {}},
            }
            paths = {
                "manifest_path": write("manifest.json", manifest),
                "binding_verification_path": write("binding.json", verification),
                "architecture_report_path": write("architecture.json", architecture),
                "cvar_report_path": write("cvar.json", cvar),
                "b_migrate_report_path": write("b_migrate.json", b_migrate),
                "release_report_path": write("release.json", {"decision": "pass"}),
                "reward_report_path": write("reward.json", reward),
                "root_list_report_path": write("root_list.json", {"decision": "pass"}),
                "loc_report_path": write("loc.json", {"decision": "pass", "delta": {"delta_lines": 500}}),
            }
            record = build_experiment_record(
                **paths,
                candidate_repository={"git_sha": "candidate", "app_tree_sha": "candidate-tree"},
                git_delta=[{"status": "M", "path": path} for path in changed],
            )
            Draft202012Validator(schema).validate(record)
            self.assertTrue(is_owner_controlled_vertical_retirement_wave(manifest, verification, architecture))
            self.assertEqual(record["decision"], "pass")
            self.assertEqual(record["candidate"]["evidence_class"], "owner_controlled_vertical_retirement")
            self.assertEqual(record["rollback"]["proof_artifact"]["mode"], "owner_frozen_selector")
            self.assertEqual(record["outcomes"]["outcome_window"], "bounded_deterministic_runtime_retirement")

            broadened = deepcopy(verification)
            broadened["derived_affectedness"]["backends"] = ["deterministic_sandbox", "apple_eventkit"]
            self.assertFalse(is_owner_controlled_vertical_retirement_wave(manifest, broadened, architecture))

    def test_reward_rows_gain_occurrence_identity_and_declared_source_class(self):
        with tempfile.TemporaryDirectory() as td:
            replay = Path(td) / "rewards.jsonl"
            rows = [
                {
                    "record_schema_version": "r1",
                    "record_type": "reward",
                    "record_id": "reward:shared",
                    "trace_id": "candidate:1",
                    "causal_parent_id": "feedback:event-1",
                    "signal_stream": "action",
                    "payload": {"reward": {"reward_event_id": "human-1", "provenance": "human_ui", "utility_reward": 1.0}},
                },
                {
                    "record_schema_version": "r1",
                    "record_type": "reward",
                    "record_id": "reward:shared",
                    "trace_id": "self_play:1:candidate",
                    "causal_parent_id": "receipt:1",
                    "signal_stream": "action",
                    "payload": {"reward": {"reward_event_id": "sim-1", "provenance": "self_play_simulator", "utility_reward": 0.0}},
                },
            ]
            replay.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            report = build_reward_report(replay_path=replay, require_source_shape=True)
            self.assertEqual(report["decision"], "pass")
            evidence = report["reward_evidence"]
            self.assertTrue(evidence["occurrence_ids_unique"])
            self.assertEqual(len(evidence["declared_source_classification"]["human_occurrence_ids"]), 1)
            self.assertEqual(len(evidence["declared_source_classification"]["simulator_occurrence_ids"]), 1)
            rows[0]["causal_parent_id"] = "forged"
            replay.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            planted = build_reward_report(replay_path=replay, require_source_shape=True)
            self.assertEqual(planted["decision"], "hold")
            self.assertFalse(planted["gates"]["declared_source_shape"])
            rows[0]["causal_parent_id"] = "feedback:event-1"
            rows[1]["payload"]["reward"]["utility_reward"] = 1.0
            replay.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            credit_attack = build_reward_report(replay_path=replay, require_source_shape=True)
            self.assertEqual(credit_attack["decision"], "hold")
            self.assertFalse(credit_attack["gates"]["direct_simulator_credit_screen"])
            rows[1]["payload"]["reward"]["utility_reward"] = 0.0
            rows[1]["payload"]["reward"]["total_reward"] = 1.0
            replay.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            aggregate_attack = build_reward_report(replay_path=replay, require_source_shape=True)
            self.assertEqual(aggregate_attack["decision"], "hold")
            self.assertIn(
                "total_reward",
                {row["head"] for row in aggregate_attack["reward_evidence"]["declared_source_classification"]["simulator_positive_credit_violations"]},
            )


if __name__ == "__main__":
    unittest.main()
