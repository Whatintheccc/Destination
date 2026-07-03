

from __future__ import annotations

import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from calendar_pilot.frontend.launch import LaunchConfig
from calendar_pilot.frontend.server import serve
from calendar_pilot.frontend.session_manager import SessionManager


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class FrontendServerApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.temp.name)
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.env_patch = patch.dict("os.environ", {"CALENDAR_PILOT_RUNTIME_MODE": "fixture"})
        self.env_patch.start()
        self.thread = threading.Thread(target=serve, kwargs={"host": "127.0.0.1", "port": self.port, "run_dir": self.run_dir}, daemon=True)
        self.thread.start()
        self._wait_for_server()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.temp.cleanup()

    def test_http_api_routes_and_error_contract(self):
        state = self.get("/api/state")
        self.assertIn("session", state)
        self.assertEqual(state["runtime"]["runtime_mode"], "fixture")
        self.assertEqual(state["runtime"]["backends"]["kernel"], "SwiftKernelStub")
        health = self.get("/api/health")
        self.assertEqual(health["runtime_mode"], state["runtime"]["runtime_mode"])
        self.assertEqual(health["backends"]["provider"], "deterministic_fixture_provider")
        provider_permission = self.post("/api/provider/permission/request", {}, expected_status=400)
        self.assertIn("active provider does not support OS permission requests", provider_permission["error"])
        runtime = self.post("/api/runtime", {"runtime_mode": "fixture"})
        self.assertEqual(runtime["runtime"]["runtime_mode"], "fixture")
        first_session_id = runtime["session"]["session_id"]

        planned = self.post("/api/plans", {"goal": "Make next week less chaotic", "authority_tier": 3})
        candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]

        simulated = self.post(f"/api/candidates/{candidate_id}/simulate", {})
        self.assertIn("simulated", json.dumps(simulated))

        staged = self.post(f"/api/candidates/{candidate_id}/stage", {})
        staged_receipt = staged["action_queue"][-1]["receipt_id"]
        self.assertTrue(staged_receipt)

        confirmed = self.post(f"/api/receipts/{staged_receipt}/confirm", {})
        rollback = next(action["rollback_handle_id"] for action in confirmed["action_queue"] if action.get("rollback_handle_id"))
        receipt_id = next(action["receipt_id"] for action in confirmed["action_queue"] if action.get("rollback_handle_id") == rollback)

        feedback = self.post("/api/feedback", {"receipt_id": receipt_id, "feedback": "useful", "reason": "http contract"})
        self.assertTrue(feedback["inspector"]["feedback"])

        profile = self.post("/api/profile/patch/propose", {"correction": "Prefer morning planning blocks."})
        self.assertTrue(profile["inspector"]["profile"]["patch_history"])
        applied = self.post("/api/profile/patch/apply", {"claim": "planning", "correction": "Prefer morning planning blocks.", "confirmed": "true"})
        self.assertTrue(applied["inspector"]["profile"]["patch_history"])

        denial = self.post("/api/denials/explain", {"denied_reason": "required authority tier exceeds Swift-issued grant"})
        self.assertTrue(denial["inspector"]["denials"])

        self_play = self.post("/api/self-play", {"episodes": 1})
        self.assertTrue(self_play["inspector"]["self_play"]["history"])
        self.assertEqual(self_play["inspector"]["self_play"]["history"][-1]["simulator_version"], "sim_v2")
        lab_view = self.get("/api/view")
        self.assertEqual(lab_view["lab"]["simulator_version"], "sim_v2")

        authority = self.post("/api/authority", {"authority_tier": 2, "scopes": "recommend, stage", "confirmed": "false"})
        self.assertEqual(authority["session"]["authority_tier"], 2)
        self.assertEqual(authority["session"]["authority_scopes"], ["recommend", "stage"])
        self.assertFalse(authority["inspector"]["authority"]["history"][-1]["grant"]["confirmed_by_user"])
        denied = self.post(f"/api/candidates/{candidate_id}/commit", {"confirmed": "false"})
        self.assertTrue(denied["inspector"]["denials"])
        self.assertIn("denied", json.dumps(denied))

        replay = self.get("/api/replay")
        self.assertGreater(replay["summary"]["records"], 0)
        exported = self.get("/api/replay/export")
        self.assertEqual(exported["session_id"], authority["session"]["session_id"])
        self.assertEqual(exported["runtime"]["runtime_mode"], "fixture")
        self.assertEqual(exported["active_plan"]["plan_id"], planned["summary"]["plan_id"])
        self.assertTrue(exported["active_plan"]["trace"])
        envelopes = exported["active_plan"]["action_envelopes"]
        self.assertTrue(envelopes)
        committed_envelopes = [row for row in envelopes if row["tool_status"] == "committed"]
        self.assertTrue(committed_envelopes)
        self.assertEqual(committed_envelopes[-1]["schema_version"], "calendar_action_envelope.v1")
        self.assertEqual(committed_envelopes[-1]["provider_id"], "deterministic_fixture_provider")
        self.assertTrue(committed_envelopes[-1]["rollback_handle_id"])
        self.assertTrue(committed_envelopes[-1]["action_program_digest"].startswith("ap_"))
        self.assertTrue(exported["records"])

        created = self.post("/api/sessions", {})
        second_session_id = created["session"]["session_id"]
        self.assertNotEqual(second_session_id, first_session_id)
        self.assertFalse(created["chat"]["candidate_cards"])
        self.assertEqual(created["inspector"]["replay"]["summary"]["records"], 0)
        child_manifest = json.loads((Path(created["session"]["run_dir"]) / "launch_state.json").read_text(encoding="utf-8"))
        self.assertEqual(child_manifest["port"], self.port)
        self.assertGreaterEqual(len(created["sidebar"]["sessions"]), 2)
        self.assertEqual([s for s in created["sidebar"]["sessions"] if s["active"]][0]["session_id"], second_session_id)

        child_runtime = self.post("/api/runtime", {"runtime_mode": "live_codex"})
        self.assertEqual(child_runtime["session"]["session_id"], second_session_id)
        self.assertEqual(child_runtime["runtime"]["runtime_mode"], "live_codex")
        child_runtime_manifest = json.loads((Path(child_runtime["session"]["run_dir"]) / "launch_state.json").read_text(encoding="utf-8"))
        self.assertEqual(child_runtime_manifest["port"], self.port)
        self.assertEqual(child_runtime_manifest["runtime_mode"], "live_codex")
        root_runtime_manifest = json.loads((self.run_dir / "launch_state.json").read_text(encoding="utf-8"))
        self.assertEqual(root_runtime_manifest["port"], self.port)
        self.assertEqual(root_runtime_manifest["active_session_id"], second_session_id)
        self.assertEqual(root_runtime_manifest["active_session_run_dir"], str(Path(child_runtime["session"]["run_dir"]).resolve()))
        self.assertEqual(root_runtime_manifest["runtime_mode"], "live_codex")
        self.assertEqual(root_runtime_manifest["health"]["runtime_mode"], "live_codex")

        restored_child_runtime = self.post("/api/runtime", {"runtime_mode": "fixture"})
        self.assertEqual(restored_child_runtime["runtime"]["runtime_mode"], "fixture")
        renamed = self.post("/api/sessions/rename", {"session_id": second_session_id, "label": "Focus cleanup"})
        self.assertEqual(renamed["session"]["label"], "Focus cleanup")
        self.assertEqual([s for s in renamed["sidebar"]["sessions"] if s["session_id"] == second_session_id][0]["label"], "Focus cleanup")

        second_activity = self.post("/api/plans", {"goal": "show replay trace"})
        self.assertEqual(second_activity["session"]["session_id"], second_session_id)
        self.assertEqual(second_activity["summary"]["latest_turn"]["metadata"]["tool_sequence"], ["query_replay_trace"])

        restored_first = self.post("/api/sessions/switch", {"session_id": first_session_id})
        self.assertEqual(restored_first["session"]["session_id"], first_session_id)
        self.assertTrue(restored_first["chat"]["candidate_cards"])
        self.assertGreater(restored_first["inspector"]["replay"]["summary"]["records"], second_activity["inspector"]["replay"]["summary"]["records"])

        targeted_second = self.post("/api/plans", {"session_id": second_session_id, "goal": "inspect profile"})
        self.assertEqual(targeted_second["session"]["session_id"], second_session_id)
        targeted_error = self.post("/api/not-a-route", {"session_id": second_session_id}, expected_status=400)
        self.assertEqual(targeted_error["state"]["session"]["session_id"], second_session_id)
        still_first = self.get("/api/state")
        self.assertEqual(still_first["session"]["session_id"], first_session_id)

        listed = self.get("/api/sessions")
        self.assertEqual(listed["active_session_id"], first_session_id)
        self.assertIn(second_session_id, [s["session_id"] for s in listed["sessions"]])
        archived = self.post("/api/sessions/archive", {"session_id": second_session_id})
        self.assertEqual(archived["session"]["session_id"], first_session_id)
        archived_list = self.get("/api/sessions")
        self.assertNotIn(second_session_id, [s["session_id"] for s in archived_list["sessions"]])

        undone = self.post("/api/undo", {"rollback_handle_id": rollback})
        self.assertIn("Undo requested", json.dumps(undone["chat"]["messages"]))

        reset = self.post("/api/reset", {})
        self.assertEqual(reset["inspector"]["replay"]["summary"]["records"], 0)
        self.assertEqual(reset["session"]["authority_tier"], 3)
        self.assertEqual(reset["session"]["authority_scopes"], ["recommend", "stage", "commit_private", "undo"])

        error = self.post("/api/not-a-route", {}, expected_status=400)
        self.assertIn("error", error)
        self.assertIn("state", error)

    def test_session_manager_preserves_manifest_and_active_pointer_without_hydrating_summaries(self):
        with tempfile.TemporaryDirectory() as td:
            launch = LaunchConfig.from_env(run_dir=Path(td), host="127.0.0.1", port=9999, runtime_mode="fixture")
            manager = SessionManager()
            root = manager.get_or_create(launch)
            child = manager.create_session(launch)

            root_manifest = json.loads((root.run_dir / "launch_state.json").read_text(encoding="utf-8"))
            child_manifest = json.loads((child.run_dir / "launch_state.json").read_text(encoding="utf-8"))
            self.assertEqual(root_manifest["port"], 9999)
            self.assertEqual(child_manifest["port"], 9999)

            restarted = SessionManager()
            summaries = restarted.session_summaries(launch)
            self.assertEqual(restarted.sessions, {})
            self.assertEqual([s for s in summaries if s["active"]][0]["session_id"], child.session_id)

            restored = restarted.get_or_create(launch)
            self.assertEqual(restored.session_id, child.session_id)
            root_launch_manifest = json.loads((Path(td) / "launch_state.json").read_text(encoding="utf-8"))
            self.assertEqual(root_launch_manifest["port"], 9999)
            self.assertEqual(root_launch_manifest["active_session_id"], child.session_id)
            self.assertEqual(root_launch_manifest["active_session_run_dir"], str(child.run_dir.resolve()))
            self.assertEqual(root_launch_manifest["runtime_mode"], restored.runtime_report()["runtime_mode"])
            self.assertEqual(root_launch_manifest["health"]["runtime_mode"], restored.runtime_report()["runtime_mode"])

    def test_new_session_inherits_active_live_runtime_when_launch_default_is_fixture(self):
        with tempfile.TemporaryDirectory() as td, patch.dict("os.environ", {
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
            "CALENDAR_PILOT_CODEX_AUTH_FILE": str(Path(td) / "missing_auth.json"),
            "CODEX_ACCESS_TOKEN": "",
        }):
            launch = LaunchConfig.from_env(run_dir=Path(td), host="127.0.0.1", port=9999, runtime_mode="fixture")
            manager = SessionManager()
            root = manager.get_or_create(launch)
            root.set_runtime_mode("live_codex")
            manager.refresh_active_launch_manifest(root, launch)

            child = manager.create_session(launch)

            self.assertEqual(child.runtime_mode, "live_codex")
            root_manifest = json.loads((Path(td) / "launch_state.json").read_text(encoding="utf-8"))
            self.assertEqual(root_manifest["runtime_mode"], "live_codex")
            self.assertEqual(root_manifest["active_session_id"], child.session_id)

    def get(self, path: str) -> dict:
        with urlopen(f"{self.base}{path}", timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def post(self, path: str, body: dict, *, expected_status: int = 200) -> dict:
        request = Request(
            f"{self.base}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                self.assertEqual(response.status, expected_status)
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            self.assertEqual(exc.code, expected_status)
            return json.loads(exc.read().decode("utf-8"))

    def _wait_for_server(self) -> None:
        deadline = time.time() + 5
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                self.get("/api/state")
                return
            except Exception as exc:  # pragma: no cover - failure prints last error below
                last_error = exc
                time.sleep(0.05)
        raise AssertionError(f"server did not start: {last_error}")


if __name__ == "__main__":
    unittest.main()
