from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from calendar_pilot.frontend.runtime import runtime_is_release_safe
from calendar_pilot.frontend.session import DogfoodSessionState


class RuntimeModeTests(unittest.TestCase):
    def test_fixture_runtime_is_explicit_and_release_safe(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

            self.assertEqual(report["runtime_mode"], "fixture")
            self.assertEqual(report["backends"]["kernel"], "SwiftKernelStub")
            self.assertEqual(report["backends"]["codex"], "deterministic_codex_tool_planner")
            self.assertEqual(report["backends"]["diffusiongemma"], "heuristic_diffusiongemma_policy")
            self.assertEqual(report["backends"]["provider"], "local_stub")
            self.assertEqual(report["live_blockers"], [])
            self.assertTrue(runtime_is_release_safe(report))

    def test_production_mode_cannot_silently_use_fixture_stubs(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"CALENDAR_PILOT_RUNTIME_MODE": "production"}):
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

            self.assertEqual(report["runtime_mode"], "production")
            self.assertFalse(runtime_is_release_safe(report))
            blockers = " ".join(report["live_blockers"])
            self.assertIn("sample fixture data", blockers)
            self.assertIn("SwiftKernelStub", blockers)
            self.assertIn("deterministic planner", blockers)
            self.assertIn("heuristic policy", blockers)
            self.assertIn("local_stub provider", blockers)

    def test_invalid_runtime_mode_is_not_coerced_to_fixture_safe(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"CALENDAR_PILOT_RUNTIME_MODE": "prod"}):
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

            self.assertEqual(report["requested_runtime_mode"], "prod")
            self.assertEqual(report["runtime_mode"], "invalid")
            self.assertFalse(report["valid_runtime_mode"])
            self.assertFalse(runtime_is_release_safe(report))
            self.assertIn("invalid runtime mode requested: prod", report["live_blockers"])

    def test_runtime_mode_persists_across_reload(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with patch.dict("os.environ", {"CALENDAR_PILOT_RUNTIME_MODE": "live_codex"}):
                first = DogfoodSessionState(run_dir=run_dir)
                first.persist()

            with patch.dict("os.environ", {"CALENDAR_PILOT_RUNTIME_MODE": "fixture"}):
                reloaded = DogfoodSessionState(run_dir=run_dir)
                self.assertEqual(reloaded.runtime_report()["runtime_mode"], "live_codex")


if __name__ == "__main__":
    unittest.main()
