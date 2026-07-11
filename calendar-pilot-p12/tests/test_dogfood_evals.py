from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from evals.dogfood.predicates.product import ACTION_FIELDS, evaluate_predicate
from evals.dogfood.run_dogfood_evals import PREDICATE_PATH, ROOT, SCENARIO_SET, build_report, load_scenario_set, required_artifacts_for_cell


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def vector(records: dict[str, list[dict]], *, sources: tuple[str, ...]) -> dict:
    return {
        "records": records,
        "scenario_record_count": sum(len(rows) for rows in records.values()),
        "required_sources": list(sources),
        "present_sources": list(sources),
        "operator_truth": {},
        "external_prerequisite": {},
    }


class DogfoodPredicateTests(unittest.TestCase):
    def assert_pass_then_fail(self, predicate_id: str, good: dict, mutate) -> None:
        self.assertEqual(evaluate_predicate(predicate_id, good)["status"], "pass")
        bad = deepcopy(good)
        mutate(bad)
        self.assertEqual(evaluate_predicate(predicate_id, bad)["status"], "fail")

    def test_scenario_set_freezes_product_fixtures_and_counterexamples(self):
        scenario_set = load_scenario_set()
        self.assertEqual(len(scenario_set["scenarios"]), 15)
        self.assertEqual(len(scenario_set["fixture_families"]), 10)
        self.assertEqual(len(scenario_set["planted_counterexamples"]), 13)

    def test_identity_rejects_wrong_process_and_cross_run_artifact(self):
        manifest = {"run_id": "run-1", "run_dir": "/tmp/run-1", "build": {"build_id": "abcdef123456", "app_bundle_path": "/tmp/App.app"}, "runtime": {"requested_mode": "fixture", "expected_backends": {"provider": "deterministic_fixture_provider"}}}
        launch = {"run_id": "run-1", "run_dir": "/tmp/run-1", "build_id": "abcdef123456", "app_bundle_path": "/tmp/App.app", "runtime_mode": "fixture", "server_pid": 10, "port": 8888, "launch_id": "launch-1"}
        health = {"build_id": "abcdef123456", "runtime_mode": "fixture", "backends": {"provider": "deterministic_fixture_provider"}, "process": {"server_pid": 10, "port": 8888, "launch_id": "launch-1"}}
        good = vector({}, sources=("run_manifest", "launch_state_before", "health", "process_snapshot_before"))
        good.update({"manifest": manifest, "launch_state": launch, "health": health, "process_snapshot": {"server_pid": 10, "port": 8888, "launch_id": "launch-1", "ambient_attachment": False}, "cross_run_artifacts": [], "instrument_hashes_valid": True, "build_hashes_valid": True})
        self.assert_pass_then_fail("identity", good, lambda row: row["health"]["process"].__setitem__("server_pid", 11))
        self.assert_pass_then_fail("identity", good, lambda row: row.__setitem__("cross_run_artifacts", ["replay.jsonl:2"]))

    def test_live_read_rejects_fixture_labeled_eventkit(self):
        good = vector({"provider_read": [{"fact_ids": ["e1"], "provider_identity": "apple_eventkit", "uses_sample_fixtures": False, "fixture_rows": [], "permission_owner": "app"}], "rendered_view": [{"fact_ids": ["e1"]}]}, sources=("operator_truth", "provider_read", "rendered_view"))
        good.update({"operator_truth": {"provider_identity": "apple_eventkit", "facts": [{"fact_id": "e1"}]}, "health": {"backends": {"provider": "apple_eventkit"}}})
        self.assert_pass_then_fail("live_read", good, lambda row: row["records"]["provider_read"][0].__setitem__("uses_sample_fixtures", True))

    def test_action_projection_rejects_omissions_and_model_prose(self):
        action = {field: f"value-{field}" for field in ACTION_FIELDS}
        good = vector({"replay": [{"action": action}], "rendered_view": [{"action": deepcopy(action), "captured_from_ui": True}], "screenshot": [{"sha256": "a" * 64}]}, sources=("replay", "rendered_view", "screenshot"))
        self.assert_pass_then_fail("action_visible", good, lambda row: row["records"]["rendered_view"][0]["action"].pop("start"))
        self.assert_pass_then_fail("action_visible", good, lambda row: row["records"]["rendered_view"][0].__setitem__("captured_from_ui", False))

    def test_timezone_rejects_wrong_local_day(self):
        checks = {"local_day_matches": True, "offset_roundtrip": True, "duration_preserved": True, "tomorrow_uses_bound_timezone": True, "dst_case_resolved": True}
        good = vector({"rendered_view": [{"timezone_check": checks}]}, sources=("rendered_view",))
        self.assert_pass_then_fail("timezone", good, lambda row: row["records"]["rendered_view"][0]["timezone_check"].__setitem__("local_day_matches", False))

    def test_followup_rejects_replanning(self):
        continuity = {"before_plan_digest": "p", "after_plan_digest": "p", "before_candidate_digest": "c", "after_candidate_digest": "c", "before_action_digest": "a", "after_action_digest": "a", "frontier_generations": 0, "resolved_from_existing_evidence": True}
        good = vector({"replay": [{"continuity": continuity}], "rendered_view": [{}]}, sources=("replay", "rendered_view"))
        self.assert_pass_then_fail("followup", good, lambda row: row["records"]["replay"][0]["continuity"].__setitem__("after_plan_digest", "new"))

    def test_recommendation_rejects_automatic_staging(self):
        good = vector({"replay": [{"candidate_id": "c1"}], "rendered_view": [{"candidate_id": "c1", "addresses_goal": True, "rationale_compares_noop": True}]}, sources=("replay", "rendered_view"))
        self.assert_pass_then_fail("recommend", good, lambda row: row["records"]["replay"][0].__setitem__("stage_actions", 1))

    def test_simulation_rejects_mutation(self):
        preview = {"action": {}, "provider_result": {}, "conflict_result": {}, "uncertainty": 0.1, "admitted": True}
        good = vector({"rendered_view": [{"preview": preview}], "replay": [{}], "ui_action": [{}]}, sources=("rendered_view", "replay", "ui_action"))
        self.assert_pass_then_fail("simulate", good, lambda row: row["records"]["replay"][0].__setitem__("provider_mutations", 1))

    def test_effect_rejects_commit_without_readback(self):
        effect = {"tickets": 1, "claims": 1, "dispatches": 1, "provider_mutations": 1, "verify_count": 1, "ticket_external_id": "x", "provider_external_id": "x", "verify_external_id": "x", "receipt_external_id": "x", "target_binding": "b@1", "expected_binding": "b@1", "receipt_status": "committed", "has_attendees": False, "action_family": "create_prep_block", "legacy_owner_mutations": 0}
        good = vector({"replay": [{"effect": effect}], "ui_action": [{}], "provider_after": [{}]}, sources=("replay", "ui_action", "provider_after"))
        self.assert_pass_then_fail("effect", good, lambda row: row["records"]["replay"][0]["effect"].__setitem__("verify_count", 0))

    def test_undo_rejects_wrong_external_id(self):
        undo = {"separate_compensation_authority": True, "remove_count": 1, "committed_external_id": "x", "remove_external_id": "x", "absence_external_id": "x", "verified_absent": True, "audit_retained": True, "restart_redispatch_count": 0}
        good = vector({"replay": [{"undo": undo}], "ui_action": [{}], "provider_after_undo": [{}], "launch_state_after": [{}]}, sources=("replay", "ui_action", "provider_after_undo", "launch_state_after"))
        self.assert_pass_then_fail("undo", good, lambda row: row["records"]["replay"][0]["undo"].__setitem__("remove_external_id", "wrong"))

    def test_feedback_rejects_unrendered_candidate(self):
        exposure = {"exposure_id": "e", "candidate_id": "c", "decision_id": "d"}
        outcome = {"exposure_id": "e", "candidate_id": "c", "decision_id": "d", "terminal_count": 1}
        good = vector({"rendered_view": [{"exposure": exposure}], "replay": [{"outcome": outcome}], "ui_action": [{}]}, sources=("rendered_view", "replay", "ui_action"))
        self.assert_pass_then_fail("feedback", good, lambda row: row["records"]["replay"][0]["outcome"].__setitem__("candidate_id", "unrendered"))

    def test_restart_rejects_duplicate_effect(self):
        restart = {f"{side}_{name}_digest": name for side in ("before", "after") for name in ("conversation", "plan", "candidate", "receipt", "outcome", "runtime", "replay")}
        restart.update({"duplicate_tool_calls": 0, "duplicate_effects": 0})
        good = vector({"replay": [{"restart": restart}], "rendered_view": [{}], "launch_state_after": [{}]}, sources=("replay", "rendered_view", "launch_state_after"))
        self.assert_pass_then_fail("restart", good, lambda row: row["records"]["replay"][0]["restart"].__setitem__("duplicate_effects", 1))


class DogfoodReportTests(unittest.TestCase):
    def test_d0_report_passes_only_with_complete_three_rail_evidence(self):
        scenario_set = load_scenario_set()
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as td:
            run_dir = Path(td).resolve()
            run_id = run_dir.name
            scenario = scenario_set["scenarios"][0]
            bundle = run_dir / "CalendarPilot.app"
            app = bundle / "Contents/MacOS/CalendarPilot"
            bridge = bundle / "Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge"
            app.parent.mkdir(parents=True)
            bridge.parent.mkdir(parents=True)
            app.write_text("app", encoding="utf-8")
            bridge.write_text("bridge", encoding="utf-8")
            manifest = {
                "dogfood_run_manifest_schema_version": "dogfood_run_manifest.v1", "run_id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat(), "cell": "D0", "run_dir": str(run_dir),
                "repository": {"git_sha": "a" * 40, "app_tree_sha": "b" * 40, "clean": True},
                "build": {"build_id": "abcdef123456", "app_bundle_path": str(bundle), "app_sha256": digest("app"), "bridge_sha256": digest("bridge")},
                "runtime": {"requested_mode": "package", "expected_backends": {}, "credential_classes": []},
                "scenario_set": {"path": str(SCENARIO_SET), "sha256": digest(SCENARIO_SET.read_text(encoding="utf-8"))},
                "predicate_artifacts": [{"path": str(PREDICATE_PATH), "sha256": digest(PREDICATE_PATH.read_text(encoding="utf-8"))}],
                "scenario_ids": ["P-IDENTITY"], "stimuli": [{"scenario_id": "P-IDENTITY", "utf8_sha256": digest(scenario["stimulus"])}],
                "effect_ceiling": {"provider_mutations": 0, "effect_attempts": 0, "stage_actions": 0, "claims": 0, "outbox_dispatches": 0},
                "required_artifacts": required_artifacts_for_cell(scenario_set, "D0"),
                "timeouts_seconds": {"health": 10}, "operator_checkpoints": []
            }
            truth = {"dogfood_operator_truth_schema_version": "dogfood_operator_truth.v1", "run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(), "timezone": "UTC", "redaction_class": "fixture", "provider_identity": "none", "facts": []}
            launch = {"run_id": run_id, "run_dir": str(run_dir), "build_id": "abcdef123456", "app_bundle_path": str(bundle), "runtime_mode": "package", "server_pid": 10, "port": 8888, "launch_id": "launch-1"}
            health = {"build_id": "abcdef123456", "runtime_mode": "package", "backends": {}, "process": {"server_pid": 10, "port": 8888, "launch_id": "launch-1"}}
            snapshot = {"server_pid": 10, "port": 8888, "launch_id": "launch-1", "ambient_attachment": False}
            for name, payload in (("run_manifest.json", manifest), ("operator_truth.json", truth), ("launch_state.before.json", launch), ("health.json", health), ("process_snapshot.before.json", snapshot)):
                (run_dir / name).write_text(json.dumps(payload), encoding="utf-8")
            bound_artifact = {"kind": "test_fixture", "path": str(SCENARIO_SET), "sha256": digest(SCENARIO_SET.read_text(encoding="utf-8"))}
            architecture_rail = {"decision": "pass", "scenario_count": 1, "status_counts": {"pass": 1, "fail": 0, "hold": 0, "not_reached": 0}, "blocking_scenario_ids": [], "unmet_scenario_ids": []}
            def architecture_scenario(scenario_id: str, rail: str) -> dict:
                return {"scenario_id": scenario_id, "rail": rail, "gate_mode": "required", "category": "test", "adapter_case": "test", "predicate_id": "test", "binding_trigger": "test", "status": "pass", "summary": "test", "observable_vector": {}, "predicate_evidence": {}, "artifacts": [bound_artifact]}
            architecture = {
                "architecture_eval_report_schema_version": "architecture_eval_report.v2", "run_id": "arch-test",
                "generated_at": datetime.now(timezone.utc).isoformat(), "decision": "pass", "repository": manifest["repository"],
                "instrument_artifacts": [bound_artifact], "report_paths": {},
                "execution": {"report_decision": "pass", "exit_code": 0}, "scenario_set": {},
                "binding": {"manifest": bound_artifact, "verification": bound_artifact, "required_scenario_ids": ["preservation.test", "target.test"]},
                "artifact_root": str(run_dir), "rails": {"preservation": architecture_rail, "target_conformance": architecture_rail},
                "scenarios": [architecture_scenario("preservation.test", "preservation"), architecture_scenario("target.test", "target_conformance")],
            }
            extra_json = {
                "launch_state.after.json": {}, "session_state.json": {}, "replay_export.json": {},
                "process_snapshot.after.json": {}, "architecture_eval_report_v2.json": architecture,
            }
            for name, payload in extra_json.items():
                (run_dir / name).write_text(json.dumps(payload), encoding="utf-8")
            for name in ("rendered_views.jsonl", "ui_actions.jsonl", "replay.jsonl"):
                (run_dir / name).write_text("{}\n", encoding="utf-8")
            (run_dir / "screenshots").mkdir()
            (run_dir / "screenshots/manifest.json").write_text(json.dumps({"run_id": run_id, "screenshots": []}), encoding="utf-8")
            report = build_report(run_dir=run_dir)
            self.assertEqual(report["dogfood_eval_report_schema_version"], "dogfood_eval_report.v2")
            self.assertEqual(report["product_rail"]["decision"], "pass")
            self.assertEqual(report["decision"], "pass")
            self.assertEqual(report["evidence_admissibility"]["status"], "pass")
            self.assertTrue(report["binding_eligible"])
            self.assertIsNone(report["first_blocking_scenario_id"])
            self.assertEqual(report["distance"]["evidence_completeness_ratio"], 1.0)
            self.assertTrue((run_dir / "SHA256SUMS").is_file())


if __name__ == "__main__":
    unittest.main()
