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

from evals.p13_ruler.core import canonical_json_bytes, sha256_bytes
from evals.p13_ruler.wave import (
    build_b_migrate_artifact,
    build_cvar_frontier_set,
    compare_b_migrate_artifacts,
    compare_cvar_frontier_sets,
    verify_root_list,
)
from scripts.make_reward_head_report import build_report as build_reward_report


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
                    "sign_off": "external reviewer",
                    "affected_by_wave": True,
                    "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                    "next_unblock_action": "run the sandbox leg",
                }
            ]
            expired = verify_root_list(manifest)
            self.assertEqual(expired["decision"], "hold")
            self.assertEqual(expired["hold_reasons"][0]["code"], "root_list_expired")

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

    def test_reward_rows_gain_global_identity_and_authenticated_source_class(self):
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
            report = build_reward_report(replay_path=replay, require_authenticated_provenance=True)
            self.assertEqual(report["decision"], "pass")
            evidence = report["reward_evidence"]
            self.assertTrue(evidence["global_row_ids_unique"])
            self.assertEqual(len(evidence["provenance_separation"]["human_global_row_ids"]), 1)
            self.assertEqual(len(evidence["provenance_separation"]["simulator_global_row_ids"]), 1)
            rows[0]["causal_parent_id"] = "forged"
            replay.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            planted = build_reward_report(replay_path=replay, require_authenticated_provenance=True)
            self.assertEqual(planted["decision"], "hold")
            self.assertFalse(planted["gates"]["source_authenticated_provenance"])
            rows[0]["causal_parent_id"] = "feedback:event-1"
            rows[1]["payload"]["reward"]["utility_reward"] = 1.0
            replay.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            credit_attack = build_reward_report(replay_path=replay, require_authenticated_provenance=True)
            self.assertEqual(credit_attack["decision"], "hold")
            self.assertFalse(credit_attack["gates"]["simulator_no_positive_human_utility_credit"])


if __name__ == "__main__":
    unittest.main()
