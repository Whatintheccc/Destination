

#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from calendar_pilot.codex.live import CodexAppServerClient
from calendar_pilot.frontend.runtime import RuntimeBackends, runtime_is_release_safe, runtime_report


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "live_codex_e2e"
ARTIFACT_DIR = RUN_DIR / "artifacts"
sys.path.insert(0, str(ROOT / "scripts"))
from run_external_browser_flow import run_live_browser_check  # noqa: E402


def main() -> None:
    shutil.rmtree(RUN_DIR, ignore_errors=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CALENDAR_PILOT_BROWSER_WAIT_MS", "60000")
    os.environ.setdefault("CALENDAR_PILOT_BROWSER_PROCESS_TIMEOUT", "240")
    os.environ.setdefault("CALENDAR_PILOT_CODEX_TIMEOUT", "180")
    auth_preflight = CodexAppServerClient().health_status(validate_remote=True)
    write_artifact("codex_auth_preflight.json", auth_preflight)
    if not auth_preflight.get("configured") or auth_preflight.get("status") != "ok":
        report = runtime_report(
            mode="live_codex",
            run_dir=RUN_DIR / "server_state",
            observation_path=ROOT / "data" / "sample_calendar.json",
            profile_path=ROOT / "data" / "sample_profile.json",
            session_id="live_codex_e2e_missing_credential",
            backends=RuntimeBackends(kernel="SwiftKernelIPCClient", codex="live_codex_app_server"),
        )
        write_artifact("missing_credential.json", report)
        print("live Codex E2E requires Codex ChatGPT subscription auth; wrote auth preflight report")
        raise SystemExit(2)

    try:
        with LiveCodexServer() as server:
            health = api_get(server.base_url, "/api/health", timeout=20)
            assert_live_health(health)
            planned = api_post(
                server.base_url,
                "/api/plans",
                {"goal": "Make next week less chaotic using the live Codex planner.", "authority_tier": 3},
                timeout=210,
            )
            assert_live_plan(planned)
            replay = api_get(server.base_url, "/api/replay/export", timeout=20)
            assert_no_secret_leak({"health": health, "planned": planned, "replay": replay})
            write_artifact("health.json", health)
            write_artifact("live_plan_state.json", planned)
            write_artifact("replay_export.json", replay)
            run_live_browser_check(
                server.base_url,
                ARTIFACT_DIR,
                expected_runtime_mode="live_codex",
                expected_runtime_label="Live Codex mode",
            )
    except Exception as exc:
        (ARTIFACT_DIR / "failure.txt").write_text(str(exc), encoding="utf-8")
        raise
    print(f"live Codex e2e passed; artifacts: {ARTIFACT_DIR}")


class LiveCodexServer:
    def __init__(self) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.log_path = ARTIFACT_DIR / "server.log"
        self.log_file = None
        self.process: subprocess.Popen[str] | None = None

    def __enter__(self) -> "LiveCodexServer":
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["CALENDAR_PILOT_RUNTIME_MODE"] = "live_codex"
        env["CALENDAR_PILOT_BROWSER_WAIT_MS"] = env.get("CALENDAR_PILOT_BROWSER_WAIT_MS", "60000")
        self.log_file = self.log_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "calendar_pilot.app",
                "frontend",
                "--serve",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--run-dir",
                str(RUN_DIR / "server_state"),
            ],
            cwd=ROOT,
            env=env,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            self.wait_until_ready()
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log_file is not None:
            self.log_file.close()

    def wait_until_ready(self) -> None:
        deadline = time.time() + 60
        last_error: Exception | None = None
        while time.time() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise AssertionError(f"server exited early with code {self.process.returncode}; see {self.log_path}")
            try:
                api_get(self.base_url, "/api/state", timeout=10)
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.2)
        raise AssertionError(f"live Codex server did not become ready: {last_error}; see {self.log_path}")


def assert_live_health(health: dict[str, Any]) -> None:
    if health.get("runtime_mode") != "live_codex":
        raise AssertionError(f"expected live_codex runtime, got {health.get('runtime_mode')}")
    backends = health.get("backends", {})
    if backends.get("kernel") != "SwiftKernelIPCClient":
        raise AssertionError(f"live Codex must use Swift IPC, got {backends.get('kernel')}")
    if backends.get("codex") != "live_codex_app_server":
        raise AssertionError(f"live Codex must use Codex app-server planner, got {backends.get('codex')}")
    if not runtime_is_release_safe(health):
        raise AssertionError(f"live Codex health has blockers: {health.get('live_blockers')}")
    codex_health = health.get("codex_health", {})
    if codex_health.get("status") not in {"configured", "ok"}:
        raise AssertionError(f"live Codex health was not configured/ok: {codex_health}")


def assert_live_plan(state: dict[str, Any]) -> None:
    summary = state.get("summary", {})
    if summary.get("planner_backend") != "live_codex_app_server":
        raise AssertionError(f"plan did not use live Codex backend: {summary.get('planner_backend')}")
    metadata = summary.get("planner_metadata", {})
    if not metadata.get("response_id"):
        raise AssertionError("live Codex plan did not include a Codex turn id")
    if not state.get("chat", {}).get("candidate_cards"):
        raise AssertionError("live Codex plan did not render candidate cards")
    trace = state.get("trace", [])
    if not any(row.get("tool") == "stage_action_packet" for row in trace):
        raise AssertionError("live Codex plan did not reach a staged action")


def assert_no_secret_leak(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, sort_keys=True)
    for key in ["CODEX_ACCESS_TOKEN", "CODEX_API_KEY", "OPENAI_API_KEY"]:
        secret = os.environ.get(key, "")
        if f"{key}=" in text or (secret and secret in text):
            raise AssertionError(f"live Codex artifacts contain {key}")


def api_get(base_url: str, path: str, *, timeout: int) -> dict[str, Any]:
    with urlopen(f"{base_url}{path}", timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def api_post(base_url: str, path: str, body: dict[str, Any], *, timeout: int, expected_status: int = 200) -> dict[str, Any]:
    request = Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != expected_status:
                raise AssertionError(f"{path} returned {response.status}, expected {expected_status}")
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code != expected_status:
            raise
        return json.loads(exc.read().decode("utf-8"))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def write_artifact(name: str, payload: dict[str, Any]) -> None:
    (ARTIFACT_DIR / name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()