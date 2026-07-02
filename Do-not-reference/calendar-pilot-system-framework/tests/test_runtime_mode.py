

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from calendar_pilot.frontend.launch import LaunchConfig
from calendar_pilot.env import load_local_env
from calendar_pilot.frontend.runtime import process_cwd, runtime_is_release_safe
from calendar_pilot.frontend.session import DogfoodSessionState


class RuntimeModeTests(unittest.TestCase):
    def test_launch_config_defaults_to_auto_without_runtime_env(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {}, clear=True):
            launch = LaunchConfig.from_env(run_dir=Path(td))

            self.assertEqual(launch.runtime_mode, "auto")

    def test_process_cwd_falls_back_when_packaged_cwd_is_replaced(self):
        with patch("calendar_pilot.frontend.runtime.os.getcwd", side_effect=FileNotFoundError), patch.dict("os.environ", {"CALENDAR_PILOT_APP_ROOT": "/tmp/calendarpilot-app-root"}):
            self.assertEqual(process_cwd(), "/tmp/calendarpilot-app-root")

    def test_local_env_loader_hydrates_nim_key_without_overriding_process_env(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {"NVIDIA_API_KEY": "from-process"}, clear=True):
            env_path = Path(td) / ".env"
            env_path.write_text("NVIDIA_API_KEY=from-file\nCALENDAR_PILOT_NIM_TIMEOUT=42\n", encoding="utf-8")

            loaded = load_local_env(env_path)

            self.assertEqual(loaded, env_path)
            self.assertEqual(__import__("os").environ["NVIDIA_API_KEY"], "from-process")
            self.assertEqual(__import__("os").environ["CALENDAR_PILOT_NIM_TIMEOUT"], "42")

    def test_local_env_loader_searches_parent_dirs_for_packaged_app_root(self):
        from calendar_pilot import env as env_module

        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {}, clear=True):
            root = Path(td)
            packaged_root = root / "dist" / "CalendarPilot.app" / "Contents" / "Resources" / "app"
            packaged_root.mkdir(parents=True)
            (root / ".env").write_text("NVIDIA_API_KEY=from-parent\n", encoding="utf-8")
            with patch.object(env_module, "ROOT", packaged_root):
                loaded = env_module.load_local_env()

            self.assertEqual(loaded, root / ".env")
            self.assertEqual(__import__("os").environ["NVIDIA_API_KEY"], "from-parent")

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

    def test_auto_runtime_prefers_live_codex_and_reports_fallbacks(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "CALENDAR_PILOT_RUNTIME_MODE": "auto",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
            "CALENDAR_PILOT_CODEX_AUTH_FILE": str(Path(td) / "missing_auth.json"),
            "CODEX_ACCESS_TOKEN": "",
            "CALENDAR_PILOT_NIM_API_KEY": "",
            "NVIDIA_API_KEY": "",
            "NIM_API_KEY": "",
            "CALENDAR_PROVIDER_OAUTH_READY": "",
        }):
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

            self.assertEqual(report["runtime_mode"], "auto")
            self.assertEqual(report["backends"]["codex"], "live_codex_app_server")
            self.assertEqual(report["backends"]["diffusiongemma"], "heuristic_diffusiongemma_policy")
            self.assertEqual(report["backends"]["provider"], "deterministic_fixture_provider")
            self.assertFalse(runtime_is_release_safe(report))
            blockers = " ".join(report["live_blockers"])
            notes = " ".join(report["setup_notes"])
            self.assertIn("required credential missing: codex_subscription", blockers)
            self.assertNotIn("diffusiongemma_nim", blockers)
            self.assertNotIn("provider_oauth", blockers)
            self.assertIn("local heuristic policy mode", notes)
            self.assertIn("deterministic local adapter", notes)

    def test_production_mode_cannot_silently_use_fixture_stubs(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "CALENDAR_PILOT_RUNTIME_MODE": "production",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
            "CALENDAR_PILOT_CODEX_AUTH_FILE": str(Path(td) / "missing_auth.json"),
            "CODEX_ACCESS_TOKEN": "",
            "CALENDAR_PILOT_NIM_API_KEY": "",
            "NVIDIA_API_KEY": "",
            "NIM_API_KEY": "",
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

    def test_runtime_switch_to_live_codex_clears_fixture_candidate_controls(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "CALENDAR_PILOT_RUNTIME_MODE": "fixture",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
            "CALENDAR_PILOT_CODEX_AUTH_FILE": str(Path(td) / "missing_auth.json"),
            "CODEX_ACCESS_TOKEN": "",
        }):
            session = DogfoodSessionState(run_dir=Path(td))
            fixture_state = session.create_plan("Make next week less chaotic")
            self.assertTrue(fixture_state["chat"]["candidate_cards"])

            live_state = session.set_runtime_mode("live_codex")

            self.assertEqual(live_state["runtime"]["runtime_mode"], "live_codex")
            self.assertEqual(live_state["runtime"]["backends"]["codex"], "live_codex_app_server")
            self.assertFalse(live_state["chat"]["candidate_cards"])
            self.assertIn("required credential missing: codex_subscription", live_state["runtime"]["live_blockers"])


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
