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

from run_external_browser_flow import run_live_browser_check


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "release"
LOG_DIR = RUN_DIR / "logs"
REPORT = RUN_DIR / "dogfood_release_report.json"
APP_BUNDLE = ROOT / "dist" / "CalendarPilot.app"


def main() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "release_report": str(REPORT),
        "browser_artifacts": str(ROOT / "runs" / "browser_e2e" / "artifacts"),
        "app_browser_artifacts": str(RUN_DIR / "app_browser_artifacts"),
        "mac_app": str(APP_BUNDLE),
        "logs": str(LOG_DIR),
    }
    report: dict[str, Any] = {
        "started_at": utc_now(),
        "root": str(ROOT),
        "checks": [],
        "artifacts": artifacts,
        "credential_gate": credential_gate(),
    }
    checks = report["checks"]
    checks.append(run_command("python_tests", ["make", "py-test"], timeout=60))
    checks.append(run_command("swift_tests", ["make", "swift-test"], timeout=60))
    checks.append(run_command("browser_e2e", ["make", "browser-e2e"], timeout=120, env_overrides={"CALENDAR_PILOT_ALLOW_BROWSER_SKIP": ""}))
    checks.append(run_command("mac_app_build", ["make", "mac-app-build"], timeout=60))
    if checks[-1]["ok"]:
        checks.append(run_app_bundle_sanity())
        checks.append(run_launchservices_smoke())
    else:
        checks.append({"name": "mac_app_sanity", "ok": False, "skipped": True, "reason": "app build failed"})
        checks.append({"name": "launchservices_smoke", "ok": False, "skipped": True, "reason": "app build failed"})
    checks.append(validate_artifacts(artifacts))
    checks.append(scan_for_secrets())
    report["finished_at"] = utc_now()
    report["ok"] = all(check.get("ok") for check in checks)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"release report written to {REPORT}")
    if not report["ok"]:
        failed = [check["name"] for check in checks if not check.get("ok")]
        print(f"release checks failed: {', '.join(failed)}", file=sys.stderr)
        raise SystemExit(1)


def run_command(name: str, command: list[str], *, timeout: int, env_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.time()
    env = os.environ.copy()
    for key, value in (env_overrides or {}).items():
        if value:
            env[key] = value
        else:
            env.pop(key, None)
    log_path = LOG_DIR / f"{name}.log"
    try:
        proc = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout)
        output = proc.stdout + proc.stderr
        ok = proc.returncode == 0
        exit_code = proc.returncode
        reason = ""
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "") + f"\nTIMEOUT after {timeout}s\n"
        ok = False
        exit_code = None
        reason = f"timeout after {timeout}s"
    log_path.write_text(output, encoding="utf-8")
    return {
        "name": name,
        "command": command,
        "ok": ok,
        "exit_code": exit_code,
        "seconds": round(time.time() - started, 3),
        "log": str(log_path),
        "reason": reason,
    }


def run_app_bundle_sanity() -> dict[str, Any]:
    app_exe = APP_BUNDLE / "Contents" / "MacOS" / "CalendarPilot"
    app_src = APP_BUNDLE / "Contents" / "Resources" / "app" / "src" / "calendar_pilot"
    app_index = APP_BUNDLE / "Contents" / "Resources" / "app" / "frontend" / "static" / "index.html"
    if not app_exe.exists() or not os.access(app_exe, os.X_OK):
        return {"name": "mac_app_sanity", "ok": False, "reason": "app executable missing or not executable"}
    if not app_src.exists():
        return {"name": "mac_app_sanity", "ok": False, "reason": "bundled Python source missing"}
    if not app_index.exists():
        return {"name": "mac_app_sanity", "ok": False, "reason": "bundled frontend static assets missing"}
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
            page = http_get_text(base_url, "/")
            app_js = http_get_text(base_url, "/app.js")
            if 'data-testid="chat-transcript"' not in page or "/api/plans" not in app_js:
                raise AssertionError("bundled app did not serve expected frontend assets")
            run_live_browser_check(base_url, RUN_DIR / "app_browser_artifacts")
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


def run_launchservices_smoke() -> dict[str, Any]:
    if sys.platform != "darwin":
        return {"name": "launchservices_smoke", "ok": False, "reason": "LaunchServices smoke requires macOS"}
    if shutil_which("open") is None:
        return {"name": "launchservices_smoke", "ok": False, "reason": "`open` command not found"}
    default_port = 8787
    if pids_for_port(default_port):
        return {"name": "launchservices_smoke", "ok": False, "reason": f"default port {default_port} is already in use"}
    started = time.time()
    log_path = LOG_DIR / "launchservices_smoke.log"
    base_url = f"http://127.0.0.1:{default_port}"
    proc = subprocess.run(["open", "-n", str(APP_BUNDLE)], cwd=ROOT, text=True, capture_output=True)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        return {"name": "launchservices_smoke", "ok": False, "exit_code": proc.returncode, "log": str(log_path), "reason": "`open` failed"}
    try:
        wait_for_default_app(base_url, default_port, log_path)
        page = http_get_text(base_url, "/")
        ok = 'data-testid="chat-transcript"' in page
        reason = "" if ok else "LaunchServices app did not serve frontend"
    except Exception as exc:
        ok = False
        reason = str(exc)
    finally:
        terminate_pids(pids_for_port(default_port))
    return {
        "name": "launchservices_smoke",
        "ok": ok,
        "seconds": round(time.time() - started, 3),
        "base_url": base_url,
        "log": str(log_path),
        "reason": reason,
    }


def validate_artifacts(artifacts: dict[str, str]) -> dict[str, Any]:
    expected = [
        ROOT / "runs" / "browser_e2e" / "artifacts" / "browser_success.png",
        ROOT / "runs" / "browser_e2e" / "artifacts" / "browser_replay_export.json",
        ROOT / "runs" / "browser_e2e" / "artifacts" / "dogfood_bug_report.json",
        RUN_DIR / "app_browser_artifacts" / "browser_success.png",
        RUN_DIR / "app_browser_artifacts" / "browser_replay_export.json",
        APP_BUNDLE / "Contents" / "Info.plist",
        APP_BUNDLE / "Contents" / "MacOS" / "CalendarPilot",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "frontend" / "static" / "index.html",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "src" / "calendar_pilot" / "app.py",
    ]
    missing = [str(path) for path in expected if not path.exists() or path.stat().st_size == 0]
    bad_json: list[str] = []
    for path in [ROOT / "runs" / "browser_e2e" / "artifacts" / "browser_replay_export.json", RUN_DIR / "app_browser_artifacts" / "browser_replay_export.json"]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not data.get("records"):
                bad_json.append(str(path))
    return {"name": "artifact_validation", "ok": not missing and not bad_json, "missing": missing, "empty_replay_exports": bad_json, "artifacts": artifacts}


def credential_gate() -> dict[str, Any]:
    runtime_refs = find_runtime_credential_refs()
    return {
        "fixture_dogfood_requires_credentials": bool(runtime_refs),
        "codex_auth_required": any("CODEX" in ref for ref in runtime_refs),
        "provider_oauth_required": any("OAUTH" in ref or "GOOGLE" in ref or "MICROSOFT" in ref or "APPLE" in ref for ref in runtime_refs),
        "diffusiongemma_nim_required": any("NVIDIA" in ref or "NIM" in ref for ref in runtime_refs),
        "runtime_credential_refs": runtime_refs,
    }


def find_runtime_credential_refs() -> list[str]:
    roots = [ROOT / "src", ROOT / "frontend"]
    tokens = re.compile(r"(OPENAI_API_KEY|NVIDIA_API_KEY|NIM_API_KEY|CODEX_AUTH|OAUTH|GOOGLE_CLIENT|MICROSOFT_CLIENT|APPLE_CLIENT)")
    refs: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if tokens.search(text):
                refs.append(str(path.relative_to(ROOT)))
    return refs


def scan_for_secrets() -> dict[str, Any]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"nvapi-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
        re.compile(r"(OPENAI_API_KEY|NVIDIA_API_KEY|NIM_API_KEY)\s*=\s*['\"]?[A-Za-z0-9_-]{12,}", re.IGNORECASE),
    ]
    findings: list[str] = []
    paths: list[Path] = []
    proc = subprocess.run(["git", "ls-files"], cwd=ROOT.parent, text=True, capture_output=True, check=True)
    for rel in proc.stdout.splitlines():
        paths.append(ROOT.parent / rel)
    for generated_root in [ROOT / "runs", ROOT / "dist"]:
        if generated_root.exists():
            paths.extend(path for path in generated_root.rglob("*") if path.is_file())
    for path in paths:
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                findings.append(str(path.relative_to(ROOT.parent)))
                break
    return {"name": "secret_scan", "ok": not findings, "findings": sorted(set(findings)), "scanned_roots": ["tracked files", "calendar-pilot-frontend 2/runs", "calendar-pilot-frontend 2/dist"]}


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


def wait_for_default_app(base_url: str, port: int, log_path: Path) -> None:
    deadline = time.time() + 12
    last_error: Exception | None = None
    while time.time() < deadline:
        if not pids_for_port(port):
            time.sleep(0.1)
            continue
        try:
            api_get(base_url, "/api/state")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise AssertionError(f"LaunchServices app did not become ready: {last_error}; see {log_path}")


def api_get(base_url: str, path: str) -> dict[str, Any]:
    with urlopen(f"{base_url}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get_text(base_url: str, path: str) -> str:
    with urlopen(f"{base_url}{path}", timeout=10) as response:
        return response.read().decode("utf-8")


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


def pids_for_port(port: int) -> list[int]:
    proc = subprocess.run(["lsof", "-ti", f"tcp:{port}"], text=True, capture_output=True)
    return [int(line) for line in proc.stdout.splitlines() if line.strip().isdigit()]


def terminate_pids(pids: list[int]) -> None:
    for pid in pids:
        subprocess.run(["kill", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    for pid in pids_for_port(8787):
        subprocess.run(["kill", "-9", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def shutil_which(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    main()
