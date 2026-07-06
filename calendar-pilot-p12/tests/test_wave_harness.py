import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_b_migrate_dual_run import build_report as build_b_migrate_report
from run_cvar_report import build_report as build_cvar_report


class WaveHarnessTests(unittest.TestCase):
    def test_cvar_noop_baseline_passes_with_frozen_seed_set(self):
        report = build_cvar_report(
            seed_set_path=ROOT / "experiments/configs/cvar_seed_set.json",
            thresholds_path=ROOT / "experiments/configs/cvar_thresholds.json",
            before_current_path=ROOT / "experiments/promoted/CURRENT.json",
        )

        self.assertEqual(report["cvar_report_schema_version"], "cvar_report.v1")
        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["seed_set"]["seed_count"], 6)
        self.assertEqual(report["bootstrap"]["variance"], 0.0)
        self.assertEqual(report["borderline"]["flip_rate"], 0.0)
        self.assertTrue(report["before_current"]["current_sha256"])
        self.assertTrue(all(row["status"] == "pass" for row in report["gates"].values()))

    def test_experiment_record_template_is_the_eight_field_shape(self):
        template = json.loads((ROOT / "experiments/templates/experiment_record.template.json").read_text())
        schema = json.loads((ROOT / "contracts/experiment_record.schema.json").read_text())

        self.assertEqual(set(template), set(schema["required"]))
        self.assertEqual(len(template), 8)
        self.assertEqual(template["phase"], "Step E")
        self.assertTrue(template["promotion_harness"]["cvar_required"])
        self.assertTrue(template["promotion_harness"]["b_migrate_required"])

    def test_b_migrate_frontend_dual_run_passes_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            report = build_b_migrate_report(
                assertions_path=ROOT / "experiments/configs/b_migrate_frontend_view_state.json",
                artifacts_dir=Path(td),
            )

            self.assertEqual(report["b_migrate_report_schema_version"], "b_migrate_report.v1")
            self.assertEqual(report["decision"], "pass")
            self.assertTrue(report["assertions"])
            self.assertTrue(all(row["status"] == "pass" for row in report["assertions"]))
            self.assertTrue(Path(report["before_artifact"]).exists())
            self.assertTrue(Path(report["after_artifact"]).exists())


if __name__ == "__main__":
    unittest.main()
