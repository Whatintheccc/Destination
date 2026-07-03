import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class P12ContractsAndScriptsTests(unittest.TestCase):
    def test_p12_contracts_are_versioned(self):
        versions = json.loads((ROOT / "contracts/VERSIONS.json").read_text())
        for name in [
            "semantic_signal.schema.json",
            "signal_estimator_report.schema.json",
            "label_activation.schema.json",
            "biography_drift_finding.schema.json",
            "measurement_report.schema.json",
            "calibration_report.schema.json",
            "provider_capability_report.schema.json",
            "autonomy_family_promotion.schema.json",
            "curriculum_run.schema.json",
            "policy_ablation_report.schema.json",
        ]:
            self.assertIn(name, versions)
            self.assertTrue((ROOT / "contracts" / name).exists())

    def run_script(self, *args):
        return subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True, check=True)

    def test_signal_estimator_script_writes_report(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "signals.json"
            self.run_script("scripts/run_signal_estimators.py", "--out", str(out))
            payload = json.loads(out.read_text())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["report"]["estimator_version"], "interruption_tolerance_v1")

    def test_measurement_and_calibration_scripts_write_contract_shapes(self):
        with tempfile.TemporaryDirectory() as td:
            m = Path(td) / "measurement.json"
            c = Path(td) / "calibration.json"
            self.run_script("scripts/make_measurement_report.py", "--out", str(m))
            self.run_script("scripts/make_calibration_report.py", "--out", str(c))
            self.assertEqual(json.loads(m.read_text())["measurement_schema_version"], "measurement_report.v1")
            self.assertEqual(json.loads(c.read_text())["calibration_schema_version"], "calibration_report.v1")

    def test_shadow_mode_scripts_do_not_commit(self):
        with tempfile.TemporaryDirectory() as td:
            obs = Path(td) / "obs.json"
            frontier = Path(td) / "frontier.json"
            preview = Path(td) / "preview.json"
            self.run_script("scripts/import_dogfood_observation.py", "--out", str(obs))
            self.run_script("scripts/run_shadow_frontier.py", "--observation", str(obs), "--out", str(frontier))
            self.run_script("scripts/run_shadow_provider_preview.py", "--observation", str(obs), "--frontier", str(frontier), "--out", str(preview))
            payload = json.loads(preview.read_text())
            self.assertEqual(payload["commits"], 0)
            self.assertEqual(payload["mode"], "shadow_no_commit")


if __name__ == "__main__":
    unittest.main()
