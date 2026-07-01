#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "release"
LOG_DIR = RUN_DIR / "logs"
REPORT = RUN_DIR / "dogfood_release_report.json"


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "started_at": utc_now(),
        "root": str(ROOT),
        "checks": [],
        "artifacts": {},
        "credential_gate": {
            "fixture_dogfood_requires_credentials": False,
            "codex_auth_required": False,
            "provider_oauth_required": False,
            "diffusiongemma_nim_required": False,
        },
    }
    checks = report["checks"]
    checks.append(run_command("python_tests", ["make", "py-test"]))
    checks.append(run_command("swift_tests", ["make", "swift-test"]))
    checks.append(run_command("browser_e2e", ["make", "browser-e2e"]))
    checks.append(run_command("mac_app_build", ["make", "mac-app-build"]))
    if checks[-1]["ok"]:
        checks.append(run_app_bundle_sanity())
    else:
        checks.append({"name": "mac_app_sanity", "ok": False, "skipped": True, "reason": "app build failed"})
    secret_scan = scan_tracked_files_for_secrets()
    checks.append(secret_scan)
    report["artifacts"] = {
        "release_report": str(REPORT),
        "browser_artifacts": str(ROOT / "runs" / "browser_e2e" / "artifacts"),
        "mac_app": str(ROOT / "dist" / "CalendarPilot.app"),
        "logs": str(LOG_DIR),
    }
    report["finished_at"] = utc_now()
    report["ok"] = all(check.get("ok") for check in checks)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"release report written to {REPORT}")
    if not report["ok"]:
        failed = [check["name"] for check in checks if not check.get("ok")]
        print(f"release checks failed: {', '.join(failed)}", file=sys.stderr)
        raise SystemExit(1)


def run_command(name: str, command: list[str]) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    log_path = LOG_DIR / f"{name}.log"
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return {
        "name": name,
        "command": command,
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "seconds": round(time.time() - started, 3),
        "log": str(log_path),
    }


def run_app_bundle_sanity() -> dict[str, Any]:
    app_exe = ROOT / "dist" / "CalendarPilot.app" / "Contents" / "MacOS" / "CalendarPilot"
    app_src = ROOT / "dist" / "CalendarPilot.app" / "Contents" / "Resources" / "app" / "src" / "calendar_pilot"
    if not app_exe.exists() or not os.access(app_exe, os.X_OK):
        return {"name": "mac_app_sanity", "ok": False, "reason": "app executable missing or not executable"}
    if not app_src.exists():
        return {"name": "mac_app_sanity", "ok": False, "reason": "bundled Python source missing"}
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    run_dir = RUN_DIR / "mac_app_state"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "mac_app_sanity.log"
    env = os.environ.copy()
    env.update({
        "CALENDAR_PILOT_PORT": str(port),
        "CALENDAR_PILOT_RUN_DIR": str(run_dir),
        "CALENDAR_PILOT_OPEN_BROWSER": "0",
    })
    started = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen([str(app_exe)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            wait_for_state(base_url, proc, log_path)
            planned = api_post(base_url, "/api/plans", {"goal": "Make next week less chaotic"})
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            committed = api_post(base_url, f"/api/candidates/{candidate_id}/commit", {"confirmed": True})
            rollback = next((action.get("rollback_handle_id") for action in committed["action_queue"] if action.get("rollback_handle_id")), None)
            if not rollback:
                raise AssertionError("app commit did not produce rollback handle")
            exported = api_get(base_url, "/api/replay/export")
            if not exported.get("records"):
                raise AssertionError("app replay export was empty")
            api_post(base_url, "/api/reset", {})
            ok = True
            reason = ""
        except Exception as exc:
            ok = False
            reason = str(exc)
        finally:
            terminate(proc)
    return {
        "name": "mac_app_sanity",
        "ok": ok,
        "seconds": round(time.time() - started, 3),
        "base_url": base_url,
        "run_dir": str(run_dir),
        "log": str(log_path),
        "reason": reason,
    }


def scan_tracked_files_for_secrets() -> dict[str, Any]:
    proc = subprocess.run(["git", "ls-files"], cwd=ROOT.parent, text=True, capture_output=True, check=True)
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"nvapi-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
        re.compile(r"(OPENAI_API_KEY|NVIDIA_API_KEY|NIM_API_KEY)\s*=\s*['\"]?[A-Za-z0-9_-]{12,}", re.IGNORECASE),
    ]
    findings: list[str] = []
    for rel in proc.stdout.splitlines():
        path = ROOT.parent / rel
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                findings.append(rel)
                break
    return {"name": "secret_scan", "ok": not findings, "findings": findings}


def wait_for_state(base_url: str, proc: subprocess.Popen[str], log_path: Path) -> None:
    deadline = time.time() + 12
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise AssertionError(f"app exited with {proc.returncode}; see {log_path}")
        try:
            api_get(base_url, "/api/state")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise AssertionError(f"app did not become ready: {last_error}; see {log_path}")


def api_get(base_url: str, path: str) -> dict[str, Any]:
    with urlopen(f"{base_url}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def api_post(base_url: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def terminate(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    main()
