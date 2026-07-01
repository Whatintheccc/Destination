from __future__ import annotations

import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from calendar_pilot.frontend.server import serve


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
        self.thread = threading.Thread(target=serve, kwargs={"host": "127.0.0.1", "port": self.port, "run_dir": self.run_dir}, daemon=True)
        self.thread.start()
        self._wait_for_server()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_http_api_routes_and_error_contract(self):
        state = self.get("/api/state")
        self.assertIn("session", state)
        self.assertEqual(state["runtime"]["runtime_mode"], "fixture")
        self.assertEqual(state["runtime"]["backends"]["kernel"], "SwiftKernelStub")
        health = self.get("/api/health")
        self.assertEqual(health["runtime_mode"], state["runtime"]["runtime_mode"])
        self.assertEqual(health["backends"]["provider"], "local_stub")

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
        self.assertTrue(exported["records"])

        undone = self.post("/api/undo", {"rollback_handle_id": rollback})
        self.assertIn("Undo requested", json.dumps(undone["chat"]["messages"]))

        reset = self.post("/api/reset", {})
        self.assertEqual(reset["inspector"]["replay"]["summary"]["records"], 0)
        self.assertEqual(reset["session"]["authority_tier"], 3)
        self.assertEqual(reset["session"]["authority_scopes"], ["recommend", "stage", "commit_private", "undo"])

        error = self.post("/api/not-a-route", {}, expected_status=400)
        self.assertIn("error", error)
        self.assertIn("state", error)

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
