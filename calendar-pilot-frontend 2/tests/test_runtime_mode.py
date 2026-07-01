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
            self.assertEqual(report["backends"]["provider"], "deterministic_fixture_provider")
            self.assertEqual(report["live_blockers"], [])
            self.assertTrue(runtime_is_release_safe(report))

    def test_production_mode_cannot_silently_use_fixture_stubs(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "CALENDAR_PILOT_RUNTIME_MODE": "production",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
            "CALENDAR_PILOT_CODEX_AUTH_FILE": str(Path(td) / "missing_auth.json"),
            "CODEX_ACCESS_TOKEN": "",
        }):
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

            self.assertEqual(report["runtime_mode"], "production")
            self.assertEqual(report["backends"]["codex"], "live_codex_app_server")
            self.assertEqual(report["backends"]["diffusiongemma"], "nvidia_nim_diffusiongemma_policy")
            self.assertFalse(runtime_is_release_safe(report))
            blockers = " ".join(report["live_blockers"])
            self.assertIn("required credential missing: codex_subscription", blockers)
            self.assertIn("required credential missing: diffusiongemma_nim", blockers)
            self.assertIn("required credential missing: provider_oauth", blockers)
            self.assertIn("sample fixture data", blockers)
            self.assertIn("SwiftKernelStub", blockers)

    def test_invalid_runtime_mode_is_not_coerced_to_fixture_safe(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"CALENDAR_PILOT_RUNTIME_MODE": "prod"}):
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

            self.assertEqual(report["requested_runtime_mode"], "prod")
            self.assertEqual(report["runtime_mode"], "invalid")
            self.assertFalse(report["valid_runtime_mode"])
            self.assertFalse(runtime_is_release_safe(report))
            self.assertIn("invalid runtime mode requested: prod", report["live_blockers"])

    def test_live_diffusiongemma_reports_nim_backend_and_missing_credential(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "CALENDAR_PILOT_RUNTIME_MODE": "live_diffusiongemma",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
            "CALENDAR_PILOT_NIM_API_KEY": "",
            "NVIDIA_API_KEY": "",
            "NIM_API_KEY": "",
        }):
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

            self.assertEqual(report["runtime_mode"], "live_diffusiongemma")
            self.assertEqual(report["backends"]["diffusiongemma"], "nvidia_nim_diffusiongemma_policy")
            self.assertEqual(report["diffusiongemma_health"]["status"], "missing_credential")
            self.assertIn("required credential missing: diffusiongemma_nim", report["live_blockers"])

    def test_live_diffusiongemma_remote_health_failure_blocks_release(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "CALENDAR_PILOT_RUNTIME_MODE": "live_diffusiongemma",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
            "NVIDIA_API_KEY": "not-a-real-key",
            "CALENDAR_PILOT_NIM_API_KEY": "",
            "NIM_API_KEY": "",
        }), patch("calendar_pilot.frontend.session.LiveDiffusionGemmaPolicy", FakeUnhealthyLivePolicy):
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

            self.assertEqual(report["diffusiongemma_health"]["status"], "invalid_credential")
            self.assertFalse(runtime_is_release_safe(report))
            self.assertIn("live DiffusionGemma remote health is invalid_credential", " ".join(report["live_blockers"]))
            self.assertEqual(report["credentials"]["diffusiongemma_nim"]["status"], "invalid_credential")

    def test_runtime_mode_persists_across_reload(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with patch.dict("os.environ", {"CALENDAR_PILOT_RUNTIME_MODE": "live_codex", "CALENDAR_PILOT_KERNEL_BACKEND": "stub"}):
                first = DogfoodSessionState(run_dir=run_dir)
                first.persist()

            with patch.dict("os.environ", {"CALENDAR_PILOT_RUNTIME_MODE": "fixture", "CALENDAR_PILOT_KERNEL_BACKEND": "stub"}):
                reloaded = DogfoodSessionState(run_dir=run_dir)
                self.assertEqual(reloaded.runtime_report()["runtime_mode"], "live_codex")


class FakeUnhealthyLivePolicy:
    backend_name = "nvidia_nim_diffusiongemma_policy"

    def health_status(self, *, validate_remote: bool = False):
        return {
            "status": "invalid_credential" if validate_remote else "configured",
            "configured": True,
            "backend": self.backend_name,
            "credential_source": "NVIDIA_API_KEY",
            "reason": "unauthorized",
            "timeout_seconds": 90,
            "retry_policy": {"max_attempts": 1},
            "fallback_behavior": "fail_closed_no_heuristic_fallback_in_live_mode",
        }


if __name__ == "__main__":
    unittest.main()
