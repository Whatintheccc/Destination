

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

from calendar_pilot.env import load_local_env
from calendar_pilot.diffusiongemma.live import NvidiaNIMPolicyClient
from calendar_pilot.frontend.runtime import RuntimeBackends, runtime_is_release_safe, runtime_report


ROOT = Path(__file__).resolve().parents[1]
load_local_env(ROOT / ".env")
RUN_DIR = ROOT / "runs" / "live_diffusiongemma_e2e"
ARTIFACT_DIR = RUN_DIR / "artifacts"
sys.path.insert(0, str(ROOT / "scripts"))
from run_external_browser_flow import run_live_browser_check  # noqa: E402


def main() -> None:
    shutil.rmtree(RUN_DIR, ignore_errors=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("CALENDAR_PILOT_BROWSER_WAIT_MS", "60000")
    os.environ.setdefault("CALENDAR_PILOT_BROWSER_PROCESS_TIMEOUT", "240")
    os.environ.setdefault("CALENDAR_PILOT_NIM_TIMEOUT", "120")
    health = NvidiaNIMPolicyClient().health_status(validate_remote=True)
    write_artifact("nim_policy_preflight.json", health)
    if not health.get("configured"):
        report = runtime_report(
            mode="live_diffusiongemma",
            run_dir=RUN_DIR / "server_state",
            observation_path=ROOT / "data" / "sample_calendar.json",
            profile_path=ROOT / "data" / "sample_profile.json",
            session_id="live_diffusiongemma_e2e_missing_credential",
            backends=RuntimeBackends(kernel="SwiftKernelIPCClient", diffusiongemma="nvidia_nim_diffusiongemma_policy"),
        )
        write_artifact("missing_credential.json", report)
        print("live DiffusionGemma E2E requires NVIDIA NIM credentials; wrote missing credential report")
        raise SystemExit(2)
    if health.get("status") != "ok":
        write_artifact("nim_policy_preflight_blocker.json", health)
        print(f"live DiffusionGemma E2E requires healthy NVIDIA NIM remote status; got {health.get('status')}")
        raise SystemExit(2)

    try:
        with LiveDiffusionGemmaServer() as server:
            health_report = api_get(server.base_url, "/api/health", timeout=20)
            assert_live_policy_health(health_report)
            planned = post_live_plan_with_schema_retry(server.base_url)
            assert_live_policy_plan(planned)
            replay = api_get(server.base_url, "/api/replay/export", timeout=20)
            assert_no_secret_leak({"health": health_report, "planned": planned, "replay": replay})
            write_artifact("health.json", health_report)
            write_artifact("live_policy_state.json", planned)
            write_artifact("replay_export.json", replay)
            run_live_browser_check(
                server.base_url,
                ARTIFACT_DIR,
                expected_runtime_mode="live_diffusiongemma",
                expected_runtime_label="Live DiffusionGemma mode",
            )
    except Exception as exc:
        (ARTIFACT_DIR / "failure.txt").write_text(str(exc), encoding="utf-8")
        raise
    print(f"live DiffusionGemma e2e passed; artifacts: {ARTIFACT_DIR}")


def post_live_plan_with_schema_retry(base_url: str, *, attempts: int = 3) -> dict[str, Any]:
    last: dict[str, Any] = {}
    for attempt in range(1, attempts + 1):
        planned = api_post(
            base_url,
            "/api/plans",
            {"goal": "Make next week less chaotic using live DiffusionGemma policy ranking.", "authority_tier": 3},
            timeout=150,
        )
        write_artifact(f"live_policy_state_attempt_{attempt}.json", planned)
        last = planned
        if planned.get("chat", {}).get("candidate_cards"):
            return planned
        if not _is_model_schema_failure(planned):
            return planned
        if attempt < attempts:
            time.sleep(1)
    return last


def _is_model_schema_failure(state: dict[str, Any]) -> bool:
    metadata = state.get("chat", {}).get("latest_message_metadata", {})
    if metadata.get("plan_failure_category") == "model_policy_schema_failure":
        return True
    for receipt in state.get("latest_plan", {}).get("receipts", []) or []:
        output = receipt.get("output", {}) if isinstance(receipt, dict) else {}
        if isinstance(output, dict) and output.get("error_category") == "model_policy_schema_failure":
            return True
    return False


class LiveDiffusionGemmaServer:
    def __init__(self) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.log_path = ARTIFACT_DIR / "server.log"
        self.log_file = None
        self.process: subprocess.Popen[str] | None = None

    def __enter__(self) -> "LiveDiffusionGemmaServer":
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["CALENDAR_PILOT_RUNTIME_MODE"] = "live_diffusiongemma"
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
        raise AssertionError(f"live DiffusionGemma server did not become ready: {last_error}; see {self.log_path}")


def assert_live_policy_health(health: dict[str, Any]) -> None:
    if health.get("runtime_mode") != "live_diffusiongemma":
        raise AssertionError(f"expected live_diffusiongemma runtime, got {health.get('runtime_mode')}")
    backends = health.get("backends", {})
    if backends.get("kernel") != "SwiftKernelIPCClient":
        raise AssertionError(f"live DiffusionGemma must use Swift IPC, got {backends.get('kernel')}")
    if backends.get("diffusiongemma") != "nvidia_nim_diffusiongemma_policy":
        raise AssertionError(f"expected NIM policy backend, got {backends.get('diffusiongemma')}")
    if not runtime_is_release_safe(health):
        raise AssertionError(f"live DiffusionGemma health has blockers: {health.get('live_blockers')}")
    policy_health = health.get("diffusiongemma_health", {})
    if policy_health.get("status") not in {"configured", "ok"}:
        raise AssertionError(f"live DiffusionGemma health was not configured/ok: {policy_health}")


def assert_live_policy_plan(state: dict[str, Any]) -> None:
    summary = state.get("summary", {})
    backends = summary.get("runtime_backends", {})
    if backends.get("diffusiongemma") != "nvidia_nim_diffusiongemma_policy":
        raise AssertionError(f"plan did not use live DiffusionGemma backend: {backends.get('diffusiongemma')}")
    cards = state.get("chat", {}).get("candidate_cards", [])
    if not cards:
        raise AssertionError("live DiffusionGemma plan did not render candidate cards")
    if not any("policy_backend=nvidia_nim_diffusiongemma_policy" in note for card in cards for note in card.get("control_notes", [])):
        raise AssertionError("candidate cards did not include NIM policy provenance")
    records = state.get("inspector", {}).get("replay", {}).get("records", [])
    if not any(record.get("payload", {}).get("policy_version") == "nvidia_nim_diffusiongemma_policy" for record in records):
        raise AssertionError("replay did not include NIM policy provenance")
    metadata_records = [
        record
        for record in records
        if record.get("payload", {}).get("policy_metadata", {}).get("backend") == "nvidia_nim_diffusiongemma_policy"
    ]
    if not metadata_records:
        raise AssertionError("replay did not include structured NIM policy metadata")
    first_metadata = metadata_records[0].get("payload", {}).get("policy_metadata", {})
    for key in ["model", "prompt_version", "decoding_settings", "timeout_seconds", "retry_policy", "fallback_behavior", "validation"]:
        if key not in first_metadata:
            raise AssertionError(f"structured NIM policy metadata missing {key}")


def assert_no_secret_leak(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, sort_keys=True)
    for key in ["CALENDAR_PILOT_NIM_API_KEY", "NVIDIA_API_KEY", "NIM_API_KEY"]:
        secret = os.environ.get(key, "")
        if f"{key}=" in text or (secret and secret in text):
            raise AssertionError(f"live DiffusionGemma artifacts contain {key}")


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