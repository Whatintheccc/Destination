

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

from calendar_pilot.diffusiongemma.live import NvidiaNIMPolicyClient
from calendar_pilot.frontend.runtime import RuntimeBackends, credential_state, runtime_is_release_safe, runtime_mode_from_env, runtime_report
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
        "app_swift_ipc_browser_artifacts": str(RUN_DIR / "app_swift_ipc_browser_artifacts"),
        "mac_app": str(APP_BUNDLE),
        "logs": str(LOG_DIR),
    }
    report: dict[str, Any] = {
        "started_at": utc_now(),
        "root": str(ROOT),
        "checks": [],
        "artifacts": artifacts,
        "credential_gate": credential_gate(),
        "runtime": release_runtime_report(),
    }
    checks = report["checks"]
    checks.append(runtime_mode_gate(report["runtime"]))
    checks.append(live_codex_credential_mode_gate())
    checks.append(live_diffusiongemma_credential_mode_gate())
    checks.append(run_command("python_tests", ["make", "py-test"], timeout=60))
    checks.append(run_command("swift_tests", ["make", "swift-test"], timeout=60))
    checks.append(run_command("swift_ipc_tests", ["make", "swift-ipc-test"], timeout=120))
    checks.append(run_command("browser_e2e", ["make", "browser-e2e"], timeout=120, env_overrides={"CALENDAR_PILOT_ALLOW_BROWSER_SKIP": ""}))
    checks.append(run_command("mac_app_build", ["make", "mac-app-build"], timeout=120))
    if checks[-1]["ok"]:
        checks.append(run_app_bundle_sanity())
        checks.append(swift_ipc_runtime_mode_gate())
        checks.append(run_app_bundle_sanity(
            name="mac_app_swift_ipc_sanity",
            runtime_mode="swift_ipc",
            expected_kernel="SwiftKernelIPCClient",
            artifact_dir=RUN_DIR / "app_swift_ipc_browser_artifacts",
        ))
        checks.append(live_eventkit_release_gate())
        checks.append(run_launchservices_smoke())
        checks.append(run_occupied_port_launch_gate())
    else:
        checks.append({"name": "mac_app_sanity", "ok": False, "skipped": True, "reason": "app build failed"})
        checks.append({"name": "swift_ipc_runtime_mode_gate", "ok": False, "skipped": True, "reason": "app build failed"})
        checks.append({"name": "mac_app_swift_ipc_sanity", "ok": False, "skipped": True, "reason": "app build failed"})
        checks.append({"name": "live_eventkit_release_gate", "ok": False, "skipped": True, "reason": "app build failed"})
        checks.append({"name": "launchservices_smoke", "ok": False, "skipped": True, "reason": "app build failed"})
        checks.append({"name": "occupied_port_launch_gate", "ok": False, "skipped": True, "reason": "app build failed"})
    report["finished_at"] = utc_now()
    report["ok"] = False
    write_report(report)
    checks.append(validate_artifacts(artifacts))
    checks.append(scan_for_secrets())
    report["finished_at"] = utc_now()
    report["ok"] = all(check.get("ok") for check in checks)
    write_report(report)
    checks.append(validate_release_report())
    checks.append(scan_release_report())
    report["finished_at"] = utc_now()
    report["ok"] = all(check.get("ok") for check in checks)
    write_report(report)
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
        output = output_text(exc.stdout) + output_text(exc.stderr) + f"\nTIMEOUT after {timeout}s\n"
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


def run_app_bundle_sanity(
    *,
    name: str = "mac_app_sanity",
    runtime_mode: str | None = None,
    expected_kernel: str | None = None,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    runtime_mode = runtime_mode or runtime_mode_from_env()
    expected_kernel = expected_kernel or ("SwiftKernelIPCClient" if runtime_mode in {"auto", "swift_ipc", "live_codex", "live_diffusiongemma", "production"} else "SwiftKernelStub")
    artifact_dir = artifact_dir or RUN_DIR / "app_browser_artifacts"
    app_exe = APP_BUNDLE / "Contents" / "MacOS" / "CalendarPilot"
    app_src = APP_BUNDLE / "Contents" / "Resources" / "app" / "src" / "calendar_pilot"
    app_index = APP_BUNDLE / "Contents" / "Resources" / "app" / "frontend" / "static" / "index.html"
    app_swift_server = APP_BUNDLE / "Contents" / "Resources" / "app" / "bin" / "CalendarPilotKernelServer"
    app_eventkit_bridge = APP_BUNDLE / "Contents" / "Resources" / "app" / "bin" / "CalendarPilotEventKitBridge"
    app_eventkit_bridge_app = APP_BUNDLE / "Contents" / "Resources" / "app" / "bin" / "CalendarPilotEventKitBridge.app" / "Contents" / "MacOS" / "CalendarPilotEventKitBridge"
    if not app_exe.exists() or not os.access(app_exe, os.X_OK):
        return {"name": name, "ok": False, "reason": "app executable missing or not executable"}
    if not app_src.exists():
        return {"name": name, "ok": False, "reason": "bundled Python source missing"}
    if not app_index.exists():
        return {"name": name, "ok": False, "reason": "bundled frontend static assets missing"}
    if runtime_mode in {"auto", "swift_ipc", "live_codex", "live_diffusiongemma", "production"} and (not app_swift_server.exists() or not os.access(app_swift_server, os.X_OK)):
        return {"name": name, "ok": False, "reason": "bundled Swift IPC server missing or not executable"}
    if not app_eventkit_bridge.exists() or not os.access(app_eventkit_bridge, os.X_OK):
        return {"name": name, "ok": False, "reason": "bundled EventKit bridge missing or not executable"}
    if not app_eventkit_bridge_app.exists() or not os.access(app_eventkit_bridge_app, os.X_OK):
        return {"name": name, "ok": False, "reason": "bundled EventKit bridge app missing or not executable"}
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    run_dir = RUN_DIR / f"mac_app_state_{runtime_mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    launch_state_path = run_dir / "launch_state.json"
    launch_state_path.unlink(missing_ok=True)
    log_path = LOG_DIR / f"{name}.log"
    launch_id = f"release_{name}_{int(time.time() * 1000)}"
    env = os.environ.copy()
    env.update({
        "CALENDAR_PILOT_PORT": str(port),
        "CALENDAR_PILOT_RUN_DIR": str(run_dir),
        "CALENDAR_PILOT_OPEN_BROWSER": "0",
        "CALENDAR_PILOT_RUNTIME_MODE": runtime_mode,
        "CALENDAR_PILOT_LAUNCH_ID": launch_id,
    })
    started = time.time()
    swift_before = pids_for_command_pattern(str(app_swift_server)) if runtime_mode in {"auto", "swift_ipc"} else []
    terminal_state: dict[str, Any] = {}
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen([str(app_exe)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
        try:
            wait_for_state(base_url, proc, log_path)
            health = api_get(base_url, "/api/health")
            assert_owned_health(health, launch_id=launch_id, expected_port=port)
            launch_state = wait_for_launch_state(launch_state_path, launch_id=launch_id, proc=proc)
            if launch_state.get("base_url") != base_url:
                raise AssertionError(f"launch state base_url {launch_state.get('base_url')} did not match expected {base_url}")
            page = http_get_text(base_url, "/")
            main_js = http_get_text(base_url, "/js/main.js")
            if 'data-testid="chat-transcript"' not in page or 'data-testid="runtime-chip"' not in page or "/api/plans" not in main_js:
                raise AssertionError("bundled app did not serve expected frontend assets")
            if health.get("runtime_mode") != runtime_mode:
                raise AssertionError(f"bundled app health returned wrong runtime mode: {health.get('runtime_mode')}")
            if health.get("backends", {}).get("kernel") != expected_kernel:
                raise AssertionError(f"bundled app used wrong kernel backend: {health.get('backends', {}).get('kernel')}")
            if health.get("live_blockers"):
                raise AssertionError(f"runtime blockers present: {health.get('live_blockers')}")
            run_live_browser_check(base_url, artifact_dir, expected_runtime_mode=runtime_mode)
            ok = True
            reason = ""
        except Exception as exc:
            ok = False
            reason = str(exc)
        finally:
            terminate(proc)
            if runtime_mode in {"auto", "swift_ipc"}:
                swift_after = pids_for_command_pattern(str(app_swift_server))
                orphaned = sorted(set(swift_after) - set(swift_before))
                if orphaned:
                    terminate_pid_list(orphaned)
                    ok = False
                    reason = f"{reason}; orphaned Swift kernel processes: {orphaned}" if reason else f"orphaned Swift kernel processes: {orphaned}"
            terminal_state, terminal_error = finalize_terminal_launch_state(launch_state_path, reason="release cleanup completed")
            if terminal_error:
                ok = False
                reason = f"{reason}; {terminal_error}" if reason else terminal_error
    ensure_log_has_content(log_path, f"{name} ok={ok} base_url={base_url} launch_id={launch_id} reason={reason}\n")
    return {
        "name": name,
        "ok": ok,
        "seconds": round(time.time() - started, 3),
        "base_url": base_url,
        "launch_id": launch_id,
        "launch_state": str(launch_state_path),
        "terminal_launch_status": terminal_state.get("status"),
        "runtime_mode": runtime_mode,
        "expected_kernel": expected_kernel,
        "run_dir": str(run_dir),
        "log": str(log_path),
        "reason": reason,
    }


def run_launchservices_smoke() -> dict[str, Any]:
    if sys.platform != "darwin":
        return {"name": "launchservices_smoke", "ok": False, "reason": "LaunchServices smoke requires macOS"}
    if shutil_which("open") is None:
        return {"name": "launchservices_smoke", "ok": False, "reason": "`open` command not found"}
    started = time.time()
    log_path = LOG_DIR / "launchservices_smoke.log"
    run_dir = default_app_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    launch_state_path = run_dir / "launch_state.json"
    launch_state_path.unlink(missing_ok=True)
    existing_default_pids = set(pids_for_port(8787))
    app_exe = APP_BUNDLE / "Contents" / "MacOS" / "CalendarPilot"
    existing_app_pids = set(pids_for_command_pattern(str(app_exe)))
    try:
        proc = subprocess.run(["open", "-n", str(APP_BUNDLE)], cwd=ROOT, text=True, capture_output=True, timeout=10)
    except subprocess.TimeoutExpired as exc:
        output = output_text(exc.stdout) + output_text(exc.stderr) + "\nTIMEOUT after 10s\n"
        log_path.write_text(output, encoding="utf-8")
        return {"name": "launchservices_smoke", "ok": False, "exit_code": None, "log": str(log_path), "reason": "`open` timed out"}
    open_output = proc.stdout + proc.stderr
    log_path.write_text(open_output if open_output else f"open exited {proc.returncode}\n", encoding="utf-8")
    if proc.returncode != 0:
        return {"name": "launchservices_smoke", "ok": False, "exit_code": proc.returncode, "log": str(log_path), "reason": "`open` failed"}
    launch_state: dict[str, Any] = {}
    terminal_state: dict[str, Any] = {}
    try:
        launch_state = wait_for_launch_state(launch_state_path)
        base_url = str(launch_state.get("base_url"))
        deadline = time.time() + 12
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                api_get(base_url, "/api/state")
                break
            except Exception as exc:
                last_error = exc
                time.sleep(0.1)
        else:
            raise AssertionError(f"LaunchServices app did not become HTTP-ready: {last_error}")
        health = api_get(base_url, "/api/health")
        assert_owned_health(
            health,
            launch_id=str(launch_state.get("launch_id")),
            expected_port=int(launch_state.get("port")),
            expected_server_pid=int(launch_state.get("server_pid")),
        )
        page = http_get_text(base_url, "/")
        refreshed_launch_state = read_launch_state(launch_state_path)
        launch_health = refreshed_launch_state.get("health", {}) if isinstance(refreshed_launch_state.get("health"), dict) else {}
        launch_runtime_mode = launch_health.get("runtime_mode") or health.get("runtime_mode")
        blockers = [str(item) for item in health.get("live_blockers", [])]
        credentials = health.get("credentials", {})
        codex_credential = credentials.get("codex_subscription", {}) if isinstance(credentials, dict) else {}
        auto_codex_usable = (
            health.get("runtime_mode") == "auto"
            and health.get("backends", {}).get("codex") == "live_codex_app_server"
            and isinstance(codex_credential, dict)
            and bool(codex_credential.get("configured"))
            and not any("codex_subscription" in blocker for blocker in blockers)
        )
        acceptable_blockers = not blockers or auto_codex_usable
        ok = (
            'data-testid="chat-transcript"' in page
            and health.get("runtime_mode") == launch_runtime_mode
            and acceptable_blockers
        )
        reason = "" if ok else f"LaunchServices app did not serve owned frontend/runtime health: runtime={health.get('runtime_mode')} blockers={health.get('live_blockers')}"
    except Exception as exc:
        ok = False
        reason = str(exc)
    finally:
        try:
            cleanup_launch_state_processes(launch_state, existing_default_pids=existing_default_pids)
            new_app_pids = sorted(set(pids_for_command_pattern(str(app_exe))) - existing_app_pids)
            if new_app_pids:
                terminate_pid_list(new_app_pids)
            if launch_state:
                terminal_state, terminal_error = finalize_terminal_launch_state(launch_state_path, reason="release cleanup completed")
                if terminal_error:
                    ok = False
                    reason = f"{reason}; {terminal_error}" if reason else terminal_error
        except Exception as exc:
            ok = False
            reason = f"{reason}; cleanup failed: {exc}" if reason else f"cleanup failed: {exc}"
    return {
        "name": "launchservices_smoke",
        "ok": ok,
        "seconds": round(time.time() - started, 3),
        "base_url": launch_state.get("base_url"),
        "launch_state": str(launch_state_path),
        "terminal_launch_status": terminal_state.get("status"),
        "log": str(log_path),
        "reason": reason,
    }


def run_occupied_port_launch_gate() -> dict[str, Any]:
    name = "occupied_port_launch_gate"
    app_exe = APP_BUNDLE / "Contents" / "MacOS" / "CalendarPilot"
    if not app_exe.exists() or not os.access(app_exe, os.X_OK):
        return {"name": name, "ok": False, "reason": "app executable missing or not executable"}
    started = time.time()
    log_path = LOG_DIR / f"{name}.log"
    stale_log_path = LOG_DIR / f"{name}_stale_server.log"
    run_dir = RUN_DIR / "occupied_port_state"
    run_dir.mkdir(parents=True, exist_ok=True)
    launch_state_path = run_dir / "launch_state.json"
    launch_state_path.unlink(missing_ok=True)
    stale_proc: subprocess.Popen[str] | None = None
    app_proc: subprocess.Popen[str] | None = None
    terminal_state: dict[str, Any] = {}
    existing_default_pids = set(pids_for_port(8787))
    try:
        if not existing_default_pids:
            stale_dir = RUN_DIR / "occupied_port_stale_server"
            stale_dir.mkdir(parents=True, exist_ok=True)
            with stale_log_path.open("w", encoding="utf-8") as stale_log:
                stale_proc = subprocess.Popen(
                    [sys.executable, "-m", "http.server", "8787", "--bind", "127.0.0.1"],
                    cwd=stale_dir,
                    stdout=stale_log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            wait_for_port(8787, stale_proc)
        launch_id = f"release_occupied_{int(time.time() * 1000)}"
        env = os.environ.copy()
        env.update({
            "CALENDAR_PILOT_PORT": "8787",
            "CALENDAR_PILOT_RUN_DIR": str(run_dir),
            "CALENDAR_PILOT_OPEN_BROWSER": "0",
            "CALENDAR_PILOT_LAUNCH_ID": launch_id,
        })
        with log_path.open("w", encoding="utf-8") as log:
            app_proc = subprocess.Popen([str(app_exe)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
            launch_state = wait_for_launch_state(launch_state_path, launch_id=launch_id, proc=app_proc)
            chosen_port = int(launch_state.get("port"))
            if chosen_port == 8787:
                raise AssertionError("app used occupied default port 8787")
            base_url = str(launch_state.get("base_url"))
            wait_for_state(base_url, app_proc, log_path)
            health = api_get(base_url, "/api/health")
            assert_owned_health(health, launch_id=launch_id, expected_port=chosen_port, expected_server_pid=int(launch_state.get("server_pid")))
            page = http_get_text(base_url, "/")
            if 'data-testid="chat-transcript"' not in page:
                raise AssertionError("alternate-port app did not serve frontend")
        ok = True
        reason = ""
    except Exception as exc:
        ok = False
        reason = str(exc)
        launch_state = read_launch_state(launch_state_path)
    finally:
        if app_proc is not None:
            terminate(app_proc)
        cleanup_launch_state_processes(launch_state if isinstance(launch_state, dict) else {}, existing_default_pids=existing_default_pids)
        if isinstance(launch_state, dict) and launch_state:
            terminal_state, terminal_error = finalize_terminal_launch_state(launch_state_path, reason="release cleanup completed")
            if terminal_error:
                ok = False
                reason = f"{reason}; {terminal_error}" if reason else terminal_error
        if stale_proc is not None:
            terminate(stale_proc)
    ensure_log_has_content(log_path, f"{name} ok={ok} requested_port=8787 chosen_port={launch_state.get('port') if isinstance(launch_state, dict) else None} reason={reason}\n")
    return {
        "name": name,
        "ok": ok,
        "seconds": round(time.time() - started, 3),
        "base_url": launch_state.get("base_url") if isinstance(launch_state, dict) else None,
        "requested_port": 8787,
        "chosen_port": launch_state.get("port") if isinstance(launch_state, dict) else None,
        "launch_state": str(launch_state_path),
        "terminal_launch_status": terminal_state.get("status"),
        "log": str(log_path),
        "stale_server_log": str(stale_log_path),
        "reason": reason,
    }


def validate_artifacts(artifacts: dict[str, str]) -> dict[str, Any]:
    expected = [
        REPORT,
        LOG_DIR / "python_tests.log",
        LOG_DIR / "swift_tests.log",
        LOG_DIR / "swift_ipc_tests.log",
        LOG_DIR / "browser_e2e.log",
        LOG_DIR / "mac_app_build.log",
        LOG_DIR / "mac_app_sanity.log",
        LOG_DIR / "mac_app_swift_ipc_sanity.log",
        LOG_DIR / "live_eventkit_release_gate.log",
        LOG_DIR / "launchservices_smoke.log",
        LOG_DIR / "occupied_port_launch_gate.log",
        ROOT / "runs" / "browser_e2e" / "artifacts" / "browser_success.png",
        ROOT / "runs" / "browser_e2e" / "artifacts" / "health.json",
        ROOT / "runs" / "browser_e2e" / "artifacts" / "browser_replay_export.json",
        ROOT / "runs" / "browser_e2e" / "artifacts" / "dogfood_bug_report.json",
        RUN_DIR / "app_browser_artifacts" / "browser_success.png",
        RUN_DIR / "app_browser_artifacts" / "browser_replay_export.json",
        RUN_DIR / "app_swift_ipc_browser_artifacts" / "browser_success.png",
        RUN_DIR / "app_swift_ipc_browser_artifacts" / "browser_replay_export.json",
        APP_BUNDLE / "Contents" / "Info.plist",
        APP_BUNDLE / "Contents" / "MacOS" / "CalendarPilot",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "frontend" / "static" / "index.html",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "src" / "calendar_pilot" / "app.py",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "build_id",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "bin" / "CalendarPilotKernelServer",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "bin" / "CalendarPilotEventKitBridge",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "bin" / "CalendarPilotEventKitBridge.app" / "Contents" / "Info.plist",
        APP_BUNDLE / "Contents" / "Resources" / "app" / "bin" / "CalendarPilotEventKitBridge.app" / "Contents" / "MacOS" / "CalendarPilotEventKitBridge",
    ]
    missing = [str(path) for path in expected if not path.exists() or path.stat().st_size == 0]
    bad_json: list[str] = []
    for path in [
        ROOT / "runs" / "browser_e2e" / "artifacts" / "browser_replay_export.json",
        RUN_DIR / "app_browser_artifacts" / "browser_replay_export.json",
        RUN_DIR / "app_swift_ipc_browser_artifacts" / "browser_replay_export.json",
    ]:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not data.get("records"):
                bad_json.append(str(path))
    return {"name": "artifact_validation", "ok": not missing and not bad_json, "missing": missing, "empty_replay_exports": bad_json, "artifacts": artifacts}


def validate_release_report() -> dict[str, Any]:
    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"name": "release_report_validation", "ok": False, "reason": str(exc), "report": str(REPORT)}
    missing = [key for key in ["started_at", "finished_at", "root", "checks", "artifacts", "credential_gate", "runtime"] if key not in data]
    return {
        "name": "release_report_validation",
        "ok": not missing and isinstance(data.get("checks"), list) and bool(data.get("checks")),
        "missing": missing,
        "report": str(REPORT),
    }


def scan_release_report() -> dict[str, Any]:
    findings = secret_findings([REPORT])
    return {"name": "release_report_secret_scan", "ok": not findings, "findings": findings, "scanned_roots": [str(REPORT)]}


def release_runtime_report() -> dict[str, Any]:
    return runtime_report(
        mode=runtime_mode_from_env(),
        run_dir=RUN_DIR,
        observation_path=ROOT / "data" / "sample_calendar.json",
        profile_path=ROOT / "data" / "sample_profile.json",
        session_id="release_gate",
        backends=RuntimeBackends(),
    )


def runtime_mode_gate(report: dict[str, Any]) -> dict[str, Any]:
    blockers = list(report.get("live_blockers", []))
    return {
        "name": "runtime_mode_gate",
        "ok": runtime_is_release_safe(report),
        "runtime_mode": report.get("runtime_mode"),
        "backends": report.get("backends"),
        "live_blockers": blockers,
        "reason": "; ".join(blockers),
    }


def swift_ipc_runtime_mode_gate() -> dict[str, Any]:
    report = runtime_report(
        mode="swift_ipc",
        run_dir=RUN_DIR / "swift_ipc_mode_gate",
        observation_path=ROOT / "data" / "sample_calendar.json",
        profile_path=ROOT / "data" / "sample_profile.json",
        session_id="release_gate_swift_ipc",
        backends=RuntimeBackends(kernel="SwiftKernelIPCClient"),
    )
    blockers = list(report.get("live_blockers", []))
    return {
        "name": "swift_ipc_runtime_mode_gate",
        "ok": runtime_is_release_safe(report),
        "runtime_mode": report.get("runtime_mode"),
        "backends": report.get("backends"),
        "live_blockers": blockers,
        "reason": "; ".join(blockers),
    }


def live_codex_credential_mode_gate() -> dict[str, Any]:
    report = runtime_report(
        mode="live_codex",
        run_dir=RUN_DIR / "live_codex_mode_gate",
        observation_path=ROOT / "data" / "sample_calendar.json",
        profile_path=ROOT / "data" / "sample_profile.json",
        session_id="release_gate_live_codex",
        backends=RuntimeBackends(kernel="SwiftKernelIPCClient", codex="live_codex_app_server"),
    )
    blockers = list(report.get("live_blockers", []))
    credentials = report.get("credentials", {})
    codex_credential = credentials.get("codex_subscription", {}) if isinstance(credentials, dict) else {}
    configured = bool(codex_credential.get("configured")) if isinstance(codex_credential, dict) else False
    status = str(codex_credential.get("status", "")) if isinstance(codex_credential, dict) else "missing_credential"
    missing_blocker = "required credential missing: codex_subscription" in blockers
    wrong_method_blocker = "required credential wrong auth method: codex_subscription" in blockers
    ok = (
        (configured and status == "configured" and not blockers)
        or ((not configured) and missing_blocker and not runtime_is_release_safe(report))
        or ((not configured) and status == "wrong_auth_method" and wrong_method_blocker and not runtime_is_release_safe(report))
    )
    return {
        "name": "live_codex_credential_mode_gate",
        "ok": ok,
        "runtime_mode": report.get("runtime_mode"),
        "backends": report.get("backends"),
        "codex_credential_configured": configured,
        "codex_credential_status": status,
        "codex_auth_method": codex_credential.get("auth_method") if isinstance(codex_credential, dict) else "missing",
        "live_blockers": blockers,
        "reason": "; ".join(blockers),
    }


def live_diffusiongemma_credential_mode_gate() -> dict[str, Any]:
    report = runtime_report(
        mode="live_diffusiongemma",
        run_dir=RUN_DIR / "live_diffusiongemma_mode_gate",
        observation_path=ROOT / "data" / "sample_calendar.json",
        profile_path=ROOT / "data" / "sample_profile.json",
        session_id="release_gate_live_diffusiongemma",
        backends=RuntimeBackends(kernel="SwiftKernelIPCClient", diffusiongemma="nvidia_nim_diffusiongemma_policy"),
    )
    blockers = list(report.get("live_blockers", []))
    credentials = report.get("credentials", {})
    nim_credential = credentials.get("diffusiongemma_nim", {}) if isinstance(credentials, dict) else {}
    configured = bool(nim_credential.get("configured")) if isinstance(nim_credential, dict) else False
    status = str(nim_credential.get("status", "")) if isinstance(nim_credential, dict) else "missing_credential"
    missing_blocker = "required credential missing: diffusiongemma_nim" in blockers
    nim_health: dict[str, Any] = {}
    if configured:
        nim_health = NvidiaNIMPolicyClient().health_status(validate_remote=True)
        status = str(nim_health.get("status", status))
        if status != "ok":
            blockers.append(f"live DiffusionGemma remote health is {status}")
    elif missing_blocker:
        nim_health = NvidiaNIMPolicyClient().health_status(validate_remote=False)
    ok = (configured and status == "ok" and not blockers) or ((not configured) and missing_blocker and not runtime_is_release_safe(report))
    return {
        "name": "live_diffusiongemma_credential_mode_gate",
        "ok": ok,
        "runtime_mode": report.get("runtime_mode"),
        "backends": report.get("backends"),
        "nim_credential_configured": configured,
        "nim_credential_status": status,
        "nim_credential_source": nim_credential.get("source") if isinstance(nim_credential, dict) else "missing",
        "nim_health": nim_health,
        "live_blockers": blockers,
        "reason": "; ".join(blockers),
    }


def live_eventkit_release_gate() -> dict[str, Any]:
    if os.environ.get("CALENDAR_PILOT_RUN_LIVE_EVENTKIT_RELEASE") != "1":
        log_path = LOG_DIR / "live_eventkit_release_gate.log"
        log_path.write_text("skipped; set CALENDAR_PILOT_RUN_LIVE_EVENTKIT_RELEASE=1 to run the mutating Apple Calendar read/write/undo probe\n", encoding="utf-8")
        return {"name": "live_eventkit_release_gate", "ok": True, "skipped": True, "log": str(log_path), "reason": "mutating live provider probe is opt-in"}
    env_overrides = {"CALENDAR_PILOT_REQUIRE_EVENTKIT": "1", "CALENDAR_PILOT_REQUEST_EVENTKIT_ACCESS": "1"}
    bridge = os.environ.get("CALENDAR_PILOT_EVENTKIT_RELEASE_BRIDGE", "").strip()
    if bridge:
        env_overrides["CALENDAR_PILOT_EVENTKIT_BRIDGE"] = bridge
    return run_command("live_eventkit_release_gate", ["make", "live-eventkit-e2e"], timeout=120, env_overrides=env_overrides)


def credential_gate() -> dict[str, Any]:
    mode = runtime_mode_from_env()
    credentials = credential_state(mode)
    runtime_refs = find_runtime_credential_refs()
    return {
        "runtime_mode": mode,
        "fixture_dogfood_requires_credentials": mode == "fixture" and any(item["required"] for item in credentials.values()),
        "codex_auth_required": bool(credentials["codex_subscription"]["required"]),
        "provider_oauth_required": bool(credentials["provider_oauth"]["required"]),
        "diffusiongemma_nim_required": bool(credentials["diffusiongemma_nim"]["required"]),
        "credential_state": credentials,
        "runtime_credential_refs": runtime_refs,
    }


def find_runtime_credential_refs() -> list[str]:
    roots = [ROOT / "src", ROOT / "frontend"]
    tokens = re.compile(r"(CODEX_ACCESS_TOKEN|CODEX_API_KEY|OPENAI_API_KEY|NVIDIA_API_KEY|NIM_API_KEY|CODEX_AUTH|OAUTH|GOOGLE_CLIENT|MICROSOFT_CLIENT|APPLE_CLIENT)")
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
    paths: list[Path] = []
    proc = subprocess.run(["git", "ls-files"], cwd=ROOT.parent, text=True, capture_output=True, check=True, timeout=10)
    for rel in proc.stdout.splitlines():
        paths.append(ROOT.parent / rel)
    for generated_root in [ROOT / "runs", ROOT / "dist"]:
        if generated_root.exists():
            paths.extend(path for path in generated_root.rglob("*") if path.is_file())
    findings = secret_findings(paths)
    return {"name": "secret_scan", "ok": not findings, "findings": findings, "scanned_roots": ["tracked files", "calendar-pilot-frontend 2/runs", "calendar-pilot-frontend 2/dist"]}


def secret_findings(paths: list[Path]) -> list[str]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"nvapi-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
        re.compile(r"(CODEX_ACCESS_TOKEN|CODEX_API_KEY|OPENAI_API_KEY|NVIDIA_API_KEY|NIM_API_KEY)\s*=\s*['\"]?[A-Za-z0-9_-]{12,}", re.IGNORECASE),
    ]
    findings: list[str] = []
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
    return sorted(set(findings))


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


def wait_for_launch_state(path: Path, *, launch_id: str | None = None, proc: subprocess.Popen[str] | None = None) -> dict[str, Any]:
    deadline = time.time() + 12
    last_error: Exception | None = None
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise AssertionError(f"app exited with {proc.returncode}; launch state: {read_launch_state(path)}")
        try:
            state = read_launch_state(path)
            if state.get("status") != "running":
                raise AssertionError(f"launch status is {state.get('status')}")
            if launch_id and state.get("launch_id") != launch_id:
                raise AssertionError(f"launch id {state.get('launch_id')} did not match {launch_id}")
            return state
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise AssertionError(f"launch state did not become ready: {last_error}; path={path}")


def read_launch_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "unreadable", "reason": str(exc)}


def wait_for_terminal_launch_state(path: Path) -> dict[str, Any]:
    deadline = time.time() + 5
    state: dict[str, Any] = {}
    while time.time() < deadline:
        state = read_launch_state(path)
        if state.get("status") in {"stopped", "failed"}:
            return state
        time.sleep(0.1)
    return state


def finalize_terminal_launch_state(path: Path, *, reason: str) -> tuple[dict[str, Any], str]:
    state = wait_for_terminal_launch_state(path)
    if state.get("status") != "running":
        return state, ""
    live_pids = [pid for pid in [state.get("launcher_pid"), state.get("server_pid")] if isinstance(pid, int) and pid_alive(pid)]
    if live_pids:
        return state, f"launch_state still running after cleanup; live pids: {live_pids}"
    state["status"] = "stopped"
    state["reason"] = reason
    state["updated_at"] = utc_now()
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return state, ""


def assert_owned_health(
    health: dict[str, Any],
    *,
    launch_id: str,
    expected_port: int,
    expected_server_pid: int | None = None,
) -> None:
    process = health.get("process", {}) if isinstance(health, dict) else {}
    if process.get("launch_id") != launch_id:
        raise AssertionError(f"health launch id {process.get('launch_id')} did not match {launch_id}")
    if str(process.get("launch_port")) != str(expected_port):
        raise AssertionError(f"health launch port {process.get('launch_port')} did not match {expected_port}")
    if expected_server_pid is not None and process.get("pid") != expected_server_pid:
        raise AssertionError(f"health pid {process.get('pid')} did not match server pid {expected_server_pid}")


def cleanup_launch_state_processes(launch_state: dict[str, Any], *, existing_default_pids: set[int]) -> None:
    launcher_pid = int(launch_state.get("launcher_pid") or 0)
    server_pid = int(launch_state.get("server_pid") or 0)
    port = int(launch_state.get("port") or 0)
    if launcher_pid and launcher_pid != os.getpid():
        terminate_pid_list([launcher_pid])
    elif server_pid and server_pid not in existing_default_pids:
        terminate_pid_list([server_pid])
    if port and port != 8787:
        terminate_pid_list(pids_for_port(port))


def wait_for_port(port: int, proc: subprocess.Popen[str] | None = None) -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise AssertionError(f"stale server exited with {proc.returncode}")
        if pids_for_port(port):
            return
        time.sleep(0.1)
    raise AssertionError(f"port {port} did not become occupied")


def default_app_run_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "CalendarPilot"


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
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def ensure_log_has_content(path: Path, fallback: str) -> None:
    try:
        if not path.exists() or path.stat().st_size == 0:
            path.write_text(fallback, encoding="utf-8")
    except OSError:
        pass


def pids_for_port(port: int) -> list[int]:
    proc = subprocess.run(["lsof", "-ti", f"tcp:{port}"], text=True, capture_output=True, timeout=5)
    return [int(line) for line in proc.stdout.splitlines() if line.strip().isdigit()]


def terminate_pids(pids: list[int], port: int) -> None:
    for pid in pids:
        subprocess.run(["kill", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    time.sleep(0.5)
    for pid in pids_for_port(port):
        subprocess.run(["kill", "-9", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)


def pids_for_command_pattern(pattern: str) -> list[int]:
    if not pattern:
        return []
    proc = subprocess.run(["pgrep", "-f", pattern], text=True, capture_output=True, timeout=5)
    return [int(line) for line in proc.stdout.splitlines() if line.strip().isdigit() and int(line) != os.getpid()]


def terminate_pid_list(pids: list[int]) -> None:
    for pid in pids:
        subprocess.run(["kill", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    time.sleep(0.5)
    for pid in pids:
        subprocess.run(["kill", "-9", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def write_report(report: dict[str, Any]) -> None:
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


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
