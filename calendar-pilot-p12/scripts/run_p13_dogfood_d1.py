#!/usr/bin/env python3
"""Run the complete preregistered P13 D1 cell against the packaged app."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evals.dogfood.capture.normalize_d1 import normalize
from evals.dogfood.run_dogfood_evals import build_report
from scripts.prepare_p13_dogfood_run import DEFAULT_APP, DEFAULT_ARCHITECTURE_REPORT, prepare


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def health_matches_launch(launch_state: dict[str, Any], health: dict[str, Any]) -> bool:
    process = health.get("process", {})
    return all((
        bool(launch_state.get("base_url")),
        health.get("build_id") == launch_state.get("build_id"),
        health.get("runtime_mode") == launch_state.get("runtime_mode"),
        bool(process.get("server_pid")) and process.get("server_pid") == launch_state.get("server_pid"),
        bool(process.get("launch_id")) and process.get("launch_id") == launch_state.get("launch_id"),
        process.get("port") == launch_state.get("port"),
    ))


def launch(app_bundle: Path, run_dir: Path, runtime_mode: str, *, live_window: dict[str, str] | None = None) -> None:
    command = [
        "open", "-n",
        "--env", f"CALENDAR_PILOT_RUNTIME_MODE={runtime_mode}",
        "--env", f"CALENDAR_PILOT_RUN_DIR={run_dir}",
    ]
    if live_window:
        command.extend([
            "--env", f"CALENDAR_PILOT_EVENTKIT_READ_TIME_MIN={live_window['time_min']}",
            "--env", f"CALENDAR_PILOT_EVENTKIT_READ_TIME_MAX={live_window['time_max']}",
        ])
    command.append(str(app_bundle))
    subprocess.run(command, check=True)


def wait_for_launch(run_dir: Path, *, previous_launch_id: str | None = None, timeout: float = 15) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            launch_state = load_json(run_dir / "launch_state.json")
            if previous_launch_id and launch_state.get("launch_id") == previous_launch_id:
                time.sleep(0.1)
                continue
            health = get_json(f"{launch_state['base_url']}/api/health")
            if health_matches_launch(launch_state, health):
                return launch_state, health
        except Exception as exc:
            last_error = exc
        time.sleep(0.1)
    raise TimeoutError(f"packaged app did not become ready: {last_error}")


def process_snapshot(run_id: str, launch_state: dict[str, Any], health: dict[str, Any]) -> dict[str, Any]:
    process = health.get("process", {})
    return {
        "run_id": run_id,
        "launcher_pid": launch_state.get("launcher_pid"),
        "server_pid": process.get("server_pid"),
        "port": process.get("port"),
        "launch_id": process.get("launch_id"),
        "ambient_attachment": False,
    }


def stop_launch(launch_state: dict[str, Any]) -> None:
    pid = int(launch_state.get("launcher_pid") or 0)
    if pid <= 0:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    raise TimeoutError(f"CalendarPilot launcher {pid} did not terminate")


def run_browser(phase: str, base_url: str, run_dir: Path) -> None:
    subprocess.run(["node", str(ROOT / "scripts/browser_dogfood_d1.mjs"), phase, base_url, str(run_dir)], cwd=ROOT, check=True, timeout=180)


def prepare_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        cell=args.cell,
        runtime_mode=args.runtime_mode,
        scenario_set=str(ROOT / "evals/dogfood/scenarios/p13_product_v2.json"),
        app_bundle=str(Path(args.app_bundle).resolve()),
        architecture_report=str(Path(args.architecture_report).resolve()),
        fixture=str(ROOT / "data/sample_calendar.json"),
        out_root=str(Path(args.out_root).resolve()),
        run_id=args.run_id,
        live_window_start=args.live_window_start,
        live_window_end=args.live_window_end,
        live_timezone=args.live_timezone,
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = prepare(prepare_args(args))
    run_id = run_dir.name
    truth = load_json(run_dir / "operator_truth.json")
    gap = next((row for row in truth.get("facts", []) if row.get("kind") == "calendar_gap"), None)
    live_window = None
    if gap is not None:
        value = gap.get("value", {})
        live_window = {"time_min": str(value["time_min"]), "time_max": str(value["time_max"])}
    first_launch: dict[str, Any] = {}
    second_launch: dict[str, Any] = {}
    try:
        launch(Path(args.app_bundle).resolve(), run_dir, args.runtime_mode, live_window=live_window)
        first_launch, health = wait_for_launch(run_dir)
        shutil.copy2(run_dir / "launch_state.json", run_dir / "launch_state.before.json")
        (run_dir / "health.json").write_text(json.dumps(health, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (run_dir / "process_snapshot.before.json").write_text(json.dumps(process_snapshot(run_id, first_launch, health), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        run_browser("before-restart", str(first_launch["base_url"]), run_dir)
        stop_launch(first_launch)
        first_launch = {}

        launch(Path(args.app_bundle).resolve(), run_dir, args.runtime_mode, live_window=live_window)
        second_launch, second_health = wait_for_launch(run_dir, previous_launch_id=str(health.get("process", {}).get("launch_id") or ""))
        run_browser("after-restart", str(second_launch["base_url"]), run_dir)
        shutil.copy2(run_dir / "launch_state.json", run_dir / "launch_state.after.json")
        (run_dir / "process_snapshot.after.json").write_text(json.dumps(process_snapshot(run_id, second_launch, second_health), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stop_launch(second_launch)
        second_launch = {}

        normalize(run_dir)
        report = build_report(run_dir=run_dir)
        print(json.dumps({
            "run_dir": str(run_dir),
            "decision": report["decision"],
            "binding_eligible": report["binding_eligible"],
            "first_blocking_scenario_id": report["first_blocking_scenario_id"],
            "product_rail": report["product_rail"],
            "distance": report["distance"],
        }, indent=2, sort_keys=True))
        return report
    except Exception:
        (run_dir / "RUN_FAILURE.txt").write_text("D1 execution aborted; inspect retained artifacts and browser failure evidence.\n", encoding="utf-8")
        raise
    finally:
        if first_launch:
            stop_launch(first_launch)
        if second_launch:
            stop_launch(second_launch)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-bundle", default=str(DEFAULT_APP))
    parser.add_argument("--cell", default="D1", choices=("D1", "D2", "D3", "D4", "D5", "D6"))
    parser.add_argument("--runtime-mode", default="fixture", choices=("fixture", "swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "auto"))
    parser.add_argument("--architecture-report", default=str(DEFAULT_ARCHITECTURE_REPORT))
    parser.add_argument("--out-root", default=str(ROOT / "runs/dogfood"))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--live-window-start", default="")
    parser.add_argument("--live-window-end", default="")
    parser.add_argument("--live-timezone", default="America/Los_Angeles")
    args = parser.parse_args()
    expected_mode = {
        "D1": "fixture",
        "D2": "swift_ipc",
        "D3": "live_codex",
        "D4": "live_diffusiongemma",
        "D5": "live_provider",
        "D6": "auto",
    }[args.cell]
    if args.runtime_mode != expected_mode:
        parser.error(f"{args.cell} requires --runtime-mode {expected_mode}")
    report = run(args)
    raise SystemExit(0 if report["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
