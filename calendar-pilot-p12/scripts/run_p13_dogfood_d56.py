#!/usr/bin/env python3
"""Run D5 and D6 read-only against one separately ticketed live parent fixture."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from calendar_pilot.providers.apple_eventkit import AppleEventKitManagedDriver, AppleEventKitProvider
from scripts.prepare_p13_dogfood_run import (
    DEFAULT_APP,
    DEFAULT_ARCHITECTURE_REPORT,
    app_identity as packaged_app_identity,
    process_identity,
)
from scripts.run_live_eventkit_e2e import _create_managed_parent_fixture, _file_sha256, _tree_sha256
from scripts.run_p13_dogfood_d1 import run as run_cell
from scripts.run_p13_dogfood_d7 import DEFAULT_CALENDAR_ID, cleanup_parent_fixture, event_payload, write_json


def cell_args(
    args: argparse.Namespace,
    *,
    cell: str,
    event_path: Path,
    time_min: str,
    time_max: str,
    external_setup: dict[str, Any],
) -> argparse.Namespace:
    return argparse.Namespace(
        app_bundle=str(Path(args.app_bundle).resolve()),
        architecture_report=str(Path(args.architecture_report).resolve()),
        out_root=str(Path(args.out_root).resolve()),
        run_id="",
        cell=cell,
        runtime_mode="live_provider" if cell == "D5" else "auto",
        live_window_start=time_min,
        live_window_end=time_max,
        live_timezone=args.live_timezone,
        live_event_json=str(event_path),
        external_setup=external_setup,
    )


def fixture_summary(
    *,
    external_id: str,
    calendar_id: str,
    event: Any,
    setup_receipt_sha256: str,
) -> dict[str, Any]:
    return {
        "kind": "separately_ticketed_attendee_free_parent_fixture",
        "setup_outside_scored_cells": True,
        "scored_provider_mutation_ceiling": 0,
        "external_id": external_id,
        "calendar_id": calendar_id,
        "attendee_count": len(event.attendees),
        "start": event.start.isoformat(),
        "end": event.end.isoformat(),
        "setup_receipt_sha256": setup_receipt_sha256,
        "cleanup_status": "pending",
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    app = Path(args.app_bundle).resolve()
    repository = process_identity()
    packaged_app_identity(app, repository["git_sha"])
    bridge = app / "Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge"
    if not bridge.is_file():
        raise FileNotFoundError(f"canonical bundled EventKit bridge is missing: {bridge}")
    os.environ["CALENDAR_PILOT_EVENTKIT_BRIDGE"] = str(bridge)

    fixture: dict[str, Any] | None = None
    run_dirs: list[Path] = []
    cleanup: dict[str, Any] = {"phase": "not_started"}
    result: dict[str, Any] = {"decision": "fail", "cells": []}
    with tempfile.TemporaryDirectory(prefix="calendar-pilot-d56-") as temp_name:
        temporary = Path(temp_name)
        provider = AppleEventKitProvider(state_path=temporary / "provider.json")
        now = datetime.now(timezone.utc)
        driver = AppleEventKitManagedDriver(provider, calendar_id=args.calendar_id)
        identity = driver.binding_identity()
        if str(identity.get("calendar_id") or "") != args.calendar_id:
            raise RuntimeError("D56 EventKit binding did not resolve to the requested calendar")
        app_identity = {"path": str(app), "sha256": _tree_sha256(app)}
        bridge_identity = {"path": str(bridge), "sha256": _file_sha256(bridge)}
        try:
            fixture = _create_managed_parent_fixture(
                provider,
                calendar_id=args.calendar_id,
                app_identity=app_identity,
                bridge_identity=bridge_identity,
                state_root=temporary / "parent-fixture",
                now=now,
            )
            if fixture.get("status") != "verified" or not fixture.get("external_id"):
                raise RuntimeError(f"D56 parent fixture failed verification: {fixture.get('reason')}")
            parent_id = str(fixture["external_id"])
            observation = provider.read_observation(
                "apple_eventkit_user",
                observed_at=now,
                time_zone_id=args.live_timezone,
            )
            parent = next((event for event in observation.events if str(event.event_id) == parent_id), None)
            if parent is None or parent.attendees or str(parent.calendar_id) != args.calendar_id:
                raise RuntimeError("D56 parent fixture is absent, attendee-bearing, or in the wrong calendar")

            time_min = (parent.start - timedelta(hours=2)).isoformat()
            time_max = (parent.end + timedelta(hours=2)).isoformat()
            event_path = temporary / "parent-event.json"
            write_json(event_path, event_payload(parent))
            setup = fixture_summary(
                external_id=parent_id,
                calendar_id=args.calendar_id,
                event=parent,
                setup_receipt_sha256=str(fixture["receipt"].content_sha256),
            )

            for cell in ("D5", "D6"):
                out_root = Path(args.out_root).resolve()
                before = set(out_root.iterdir()) if out_root.is_dir() else set()
                try:
                    report = run_cell(cell_args(
                        args,
                        cell=cell,
                        event_path=event_path,
                        time_min=time_min,
                        time_max=time_max,
                        external_setup=setup,
                    ))
                finally:
                    created = sorted(
                        path for path in (set(out_root.iterdir()) - before)
                        if path.is_dir() and f"-{cell.lower()}-" in path.name
                    ) if out_root.is_dir() else []
                    for path in created:
                        if path not in run_dirs:
                            run_dirs.append(path)
                run_dir = Path(str(report["run_dir"])) if report.get("run_dir") else None
                if run_dir is None:
                    # build_report does not expose its source path; the newest matching
                    # directory is unambiguous because the cells run serially.
                    matches = sorted(Path(args.out_root).resolve().glob(f"*-{cell.lower()}-*-*"))
                    if not matches:
                        raise RuntimeError(f"D56 could not locate the retained {cell} run")
                    run_dir = matches[-1]
                if run_dir not in run_dirs:
                    run_dirs.append(run_dir)
                cell_result = {
                    "cell": cell,
                    "run_dir": str(run_dir),
                    "decision": report.get("decision"),
                    "binding_eligible": report.get("binding_eligible"),
                    "first_blocking_scenario_id": report.get("first_blocking_scenario_id"),
                }
                result["cells"].append(cell_result)
                if report.get("decision") != "pass" or report.get("binding_eligible") is not True:
                    raise RuntimeError(f"D56 {cell} did not pass binding evaluation: {cell_result}")

            result["decision"] = "pass"
            return result
        finally:
            cleanup = cleanup_parent_fixture(fixture)
            if fixture and cleanup.get("phase") == "verified":
                remaining = provider.read_observation(
                    "apple_eventkit_user",
                    observed_at=datetime.now(timezone.utc),
                    time_zone_id=args.live_timezone,
                )
                if str(fixture.get("external_id")) in {str(event.event_id) for event in remaining.events}:
                    cleanup = {**cleanup, "phase": "hold", "reasons": ["parent fixture remained after cleanup"]}
            cleanup_artifact = {
                **cleanup,
                "external_id": str(fixture.get("external_id") or "") if fixture else "",
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
            for run_dir in run_dirs:
                write_json(run_dir / "external_setup_cleanup.json", cleanup_artifact)
            result["cleanup"] = cleanup_artifact
            if fixture and cleanup.get("phase") != "verified":
                result["decision"] = "fail"
                print(f"D56_PARENT_CLEANUP_REQUIRED={fixture.get('external_id')}", file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-bundle", default=str(DEFAULT_APP))
    parser.add_argument("--architecture-report", default=str(DEFAULT_ARCHITECTURE_REPORT))
    parser.add_argument("--out-root", default=str(ROOT / "runs/dogfood"))
    parser.add_argument("--calendar-id", default=DEFAULT_CALENDAR_ID)
    parser.add_argument("--live-timezone", default="America/Los_Angeles")
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    raise SystemExit(0 if result["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
