#!/usr/bin/env python3
"""Run the identity-only P13 D0 cell against the packaged app."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evals.dogfood.capture.normalize_d1 import normalize
from evals.dogfood.run_dogfood_evals import build_report
from scripts.prepare_p13_dogfood_run import DEFAULT_APP, DEFAULT_ARCHITECTURE_REPORT, prepare
from scripts.run_p13_dogfood_d1 import launch, process_snapshot, stop_launch, wait_for_launch


def prepare_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        cell="D0",
        runtime_mode="fixture",
        scenario_set=str(ROOT / "evals/dogfood/scenarios/p13_product_v2.json"),
        app_bundle=str(Path(args.app_bundle).resolve()),
        architecture_report=str(Path(args.architecture_report).resolve()),
        fixture=str(ROOT / "data/sample_calendar.json"),
        out_root=str(Path(args.out_root).resolve()),
        run_id=args.run_id,
        live_window_start="",
        live_window_end="",
        live_timezone="America/Los_Angeles",
        live_event_json="",
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = prepare(prepare_args(args))
    first_launch: dict[str, Any] = {}
    second_launch: dict[str, Any] = {}
    try:
        app = Path(args.app_bundle).resolve()
        launch(app, run_dir, "fixture")
        first_launch, health = wait_for_launch(run_dir)
        shutil.copy2(run_dir / "launch_state.json", run_dir / "launch_state.before.json")
        _write_json(run_dir / "health.json", health)
        _write_json(run_dir / "process_snapshot.before.json", process_snapshot(run_dir.name, first_launch, health))
        stop_launch(first_launch)
        first_launch = {}

        launch(app, run_dir, "fixture")
        second_launch, second_health = wait_for_launch(
            run_dir,
            previous_launch_id=str(health.get("process", {}).get("launch_id") or ""),
        )
        shutil.copy2(run_dir / "launch_state.json", run_dir / "launch_state.after.json")
        _write_json(run_dir / "process_snapshot.after.json", process_snapshot(run_dir.name, second_launch, second_health))
        stop_launch(second_launch)
        second_launch = {}

        normalize(run_dir)
        report = build_report(run_dir=run_dir)
        report["run_dir"] = str(run_dir)
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
        (run_dir / "RUN_FAILURE.txt").write_text(
            "D0 execution aborted; inspect retained launch and identity evidence.\n",
            encoding="utf-8",
        )
        raise
    finally:
        if first_launch:
            stop_launch(first_launch)
        if second_launch:
            stop_launch(second_launch)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-bundle", default=str(DEFAULT_APP))
    parser.add_argument("--architecture-report", default=str(DEFAULT_ARCHITECTURE_REPORT))
    parser.add_argument("--out-root", default=str(ROOT / "runs/dogfood"))
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()
    report = run(args)
    raise SystemExit(0 if report["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
