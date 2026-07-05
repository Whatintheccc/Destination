import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
            self.run_script("scripts/make_calibration_report.py", "--family", "create_prep_block", "--out", str(c))
            self.assertEqual(json.loads(m.read_text())["measurement_schema_version"], "measurement_report.v1")
            calibration = json.loads(c.read_text())
            self.assertEqual(calibration["calibration_schema_version"], "calibration_report.v1")
            self.assertEqual(calibration["action_family_metrics"]["create_prep_block"]["decision"], "hold")

    def test_shadow_mode_scripts_do_not_commit(self):
        with tempfile.TemporaryDirectory() as td:
            obs = Path(td) / "obs.json"
            frontier = Path(td) / "frontier.json"
            preview = Path(td) / "preview.json"
            self.run_script("scripts/import_dogfood_observation.py", "--out", str(obs))
            self.run_script("scripts/run_shadow_frontier.py", "--observation", str(obs), "--family", "create_prep_block", "--out", str(frontier))
            self.run_script("scripts/run_shadow_provider_preview.py", "--observation", str(obs), "--frontier", str(frontier), "--out", str(preview))
            frontier_payload = json.loads(frontier.read_text())
            self.assertEqual(frontier_payload["family"], "create_prep_block")
            self.assertTrue(all(row["intent"] == "create_prep_block" for row in frontier_payload["candidates"]))
            payload = json.loads(preview.read_text())
            self.assertEqual(payload["commits"], 0)
            self.assertEqual(payload["mode"], "shadow_no_commit")

    def test_live_eventkit_release_gate_scopes_bridge_to_eventkit_probe(self):
        scripts_dir = str(ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        spec = importlib.util.spec_from_file_location("run_dogfood_release_under_test", ROOT / "scripts/run_dogfood_release.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.dict(os.environ, {"CALENDAR_PILOT_RUN_LIVE_EVENTKIT_RELEASE": "1", "CALENDAR_PILOT_EVENTKIT_RELEASE_BRIDGE": "/tmp/authorized-bridge"}, clear=True), patch.object(module, "run_command", return_value={"name": "live_eventkit_release_gate", "ok": True}) as run_command:
            result = module.live_eventkit_release_gate()

        self.assertTrue(result["ok"])
        kwargs = run_command.call_args.kwargs
        self.assertEqual(kwargs["env_overrides"]["CALENDAR_PILOT_REQUIRE_EVENTKIT"], "1")
        self.assertEqual(kwargs["env_overrides"]["CALENDAR_PILOT_REQUEST_EVENTKIT_ACCESS"], "1")
        self.assertEqual(kwargs["env_overrides"]["CALENDAR_PILOT_EVENTKIT_BRIDGE"], "/tmp/authorized-bridge")

    def test_live_eventkit_probe_targets_configured_sandbox_calendar(self):
        scripts_dir = str(ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        spec = importlib.util.spec_from_file_location("run_live_eventkit_e2e_under_test", ROOT / "scripts/run_live_eventkit_e2e.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.dict(os.environ, {"CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID": "CalendarPilot SelfPlay"}, clear=True):
            candidate = module.eventkit_probe_candidate()

        self.assertEqual(candidate.target_calendars, ["CalendarPilot SelfPlay"])
        self.assertEqual(candidate.actions[0].calendar_id, "CalendarPilot SelfPlay")


if __name__ == "__main__":
    unittest.main()
