#!/usr/bin/env python3
"""Run the confirmed D7 managed-EventKit effect, compensation, and restart cell."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from calendar_pilot.effect_kernel.eventkit_retirement import ManagedCalendarBinding
from calendar_pilot.providers.apple_eventkit import AppleEventKitManagedDriver, AppleEventKitProvider
from evals.dogfood.capture.normalize_d1 import normalize
from evals.dogfood.run_dogfood_evals import build_report
from scripts.prepare_p13_dogfood_run import DEFAULT_APP, DEFAULT_ARCHITECTURE_REPORT, prepare
from scripts.run_live_eventkit_e2e import (
    _cleanup_managed_parent_fixture,
    _create_managed_parent_fixture,
    _file_sha256,
    _tree_sha256,
)
from scripts.run_p13_dogfood_d1 import (
    load_json,
    process_snapshot,
    run_browser,
    stop_launch,
    wait_for_launch,
)


DEFAULT_CALENDAR_ID = "09B50C6A-826E-4030-9908-D25DC900AC59"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def event_payload(event: Any) -> dict[str, Any]:
    return {
        "event_id": str(event.event_id),
        "title": str(event.title),
        "start": event.start.isoformat(),
        "end": event.end.isoformat(),
        "calendar_id": str(event.calendar_id),
        "attendees": list(event.attendees),
        "is_user_owned": bool(event.is_user_owned),
        "is_flexible": bool(event.is_flexible),
        "category": str(event.category),
    }


def provider_snapshot(provider: AppleEventKitProvider, *, time_zone: str) -> dict[str, Any]:
    observation = provider.read_observation("apple_eventkit_user", time_zone_id=time_zone)
    health = provider.health_status()
    return {
        "provider_identity": "apple_eventkit",
        "permission_status": health.get("authorization_status"),
        "observation_id": observation.observation_id,
        "read_window": provider.last_read_window,
        "events": [event_payload(event) for event in observation.events],
    }


def launch_d7(app_bundle: Path, run_dir: Path, *, binding_path: Path, initialize: bool, time_min: str, time_max: str) -> None:
    state_root = run_dir / "managed-effect-state"
    command = [
        "open", "-n",
        "--env", "CALENDAR_PILOT_RUNTIME_MODE=auto",
        "--env", f"CALENDAR_PILOT_RUN_DIR={run_dir}",
        "--env", f"CALENDAR_PILOT_EVENTKIT_READ_TIME_MIN={time_min}",
        "--env", f"CALENDAR_PILOT_EVENTKIT_READ_TIME_MAX={time_max}",
        "--env", f"CALENDAR_PILOT_MANAGED_EVENTKIT_BINDING_FILE={binding_path}",
        "--env", f"CALENDAR_PILOT_MANAGED_EVENTKIT_STATE_ROOT={state_root}",
        "--env", f"CALENDAR_PILOT_MANAGED_EVENTKIT_INITIALIZE={1 if initialize else 0}",
        str(app_bundle),
    ]
    subprocess.run(command, check=True)


def ledger_path(run_dir: Path) -> Path:
    return run_dir / "managed-effect-state" / "epoch-1.json"


def checkpoint_ledger(run_dir: Path, name: str) -> dict[str, Any]:
    payload = load_json(ledger_path(run_dir))
    write_json(run_dir / "ruler_capture" / f"ledger.{name}.raw.json", payload)
    return payload


def exact_confirmation(label: str, expected: str) -> None:
    print(f"D7_AWAITING_{label}={expected}", flush=True)
    received = input().strip()
    if received != expected:
        raise RuntimeError(f"D7 {label.lower()} confirmation did not match the exact bound action")


def cleanup_parent_fixture(fixture: dict[str, Any] | None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cleanup = _cleanup_managed_parent_fixture(fixture, now=now)
    if not fixture or cleanup.get("phase") == "verified":
        return cleanup
    gateway = fixture["gateway"]
    fresh_grant = gateway.gate.issue_grant(
        grant_id=f"grant:d7:parent:cleanup:{now.strftime('%Y%m%dT%H%M%S')}",
        action_families=("create_prep_block",),
        scopes=("compensate",),
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        confirmed=True,
    )
    refreshed = dict(fixture)
    refreshed["grant"] = fresh_grant
    return _cleanup_managed_parent_fixture(refreshed, now=now + timedelta(seconds=1))


def prepare_args(args: argparse.Namespace, *, event_path: Path, time_min: str, time_max: str) -> argparse.Namespace:
    return argparse.Namespace(
        cell="D7",
        runtime_mode="auto",
        scenario_set=str(ROOT / "evals/dogfood/scenarios/p13_product_v2.json"),
        app_bundle=str(Path(args.app_bundle).resolve()),
        architecture_report=str(Path(args.architecture_report).resolve()),
        fixture=str(ROOT / "data/sample_calendar.json"),
        out_root=str(Path(args.out_root).resolve()),
        run_id=args.run_id,
        live_window_start=time_min,
        live_window_end=time_max,
        live_timezone=args.live_timezone,
        live_event_json=str(event_path),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    app = Path(args.app_bundle).resolve()
    bridge = app / "Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge"
    if not bridge.is_file():
        raise FileNotFoundError(f"canonical bundled EventKit bridge is missing: {bridge}")
    os.environ["CALENDAR_PILOT_EVENTKIT_BRIDGE"] = str(bridge)
    fixture: dict[str, Any] | None = None
    run_dir: Path | None = None
    first_launch: dict[str, Any] = {}
    second_launch: dict[str, Any] = {}
    cleanup: dict[str, Any] = {"phase": "not_started"}
    with tempfile.TemporaryDirectory(prefix="calendar-pilot-d7-") as temp_name:
        temporary = Path(temp_name)
        provider = AppleEventKitProvider(state_path=temporary / "provider.json")
        now = datetime.now(timezone.utc)
        setup_driver = AppleEventKitManagedDriver(provider, calendar_id=args.calendar_id)
        identity = setup_driver.binding_identity()
        app_identity = {"path": str(app), "sha256": _tree_sha256(app)}
        bridge_identity = {"path": str(bridge), "sha256": _file_sha256(bridge)}
        binding = ManagedCalendarBinding.from_confirmed_setup(
            identity=identity,
            app_identity=app_identity,
            bridge_identity=bridge_identity,
            confirmed_at=now,
        )
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
                raise RuntimeError(f"D7 parent fixture failed verification: {fixture.get('reason')}")
            parent_id = str(fixture["external_id"])
            observation = provider.read_observation("apple_eventkit_user", observed_at=now, time_zone_id=args.live_timezone)
            parent = next((event for event in observation.events if str(event.event_id) == parent_id), None)
            if parent is None or parent.attendees:
                raise RuntimeError("D7 parent fixture is absent or is not attendee-free")
            time_min = (parent.start - timedelta(hours=2)).isoformat()
            time_max = (parent.end + timedelta(hours=2)).isoformat()
            os.environ["CALENDAR_PILOT_EVENTKIT_READ_TIME_MIN"] = time_min
            os.environ["CALENDAR_PILOT_EVENTKIT_READ_TIME_MAX"] = time_max
            event_path = temporary / "parent-event.json"
            write_json(event_path, event_payload(parent))
            run_dir = prepare(prepare_args(args, event_path=event_path, time_min=time_min, time_max=time_max))
            write_json(run_dir / "managed-binding.json", binding.to_dict())
            write_json(run_dir / "parent_fixture.json", {
                "status": "verified",
                "external_id": parent_id,
                "calendar_id": args.calendar_id,
                "attendee_count": 0,
                "start": parent.start.isoformat(),
                "end": parent.end.isoformat(),
                "cleanup_status": "pending",
            })
            write_json(run_dir / "ruler_capture" / "provider.before.raw.json", provider_snapshot(provider, time_zone=args.live_timezone))

            binding_path = run_dir / "managed-binding.json"
            launch_d7(app, run_dir, binding_path=binding_path, initialize=True, time_min=time_min, time_max=time_max)
            first_launch, health = wait_for_launch(run_dir)
            shutil.copy2(run_dir / "launch_state.json", run_dir / "launch_state.before.json")
            write_json(run_dir / "health.json", health)
            write_json(run_dir / "process_snapshot.before.json", process_snapshot(run_dir.name, first_launch, health))
            run_browser("d7-precommit", str(first_launch["base_url"]), run_dir)

            candidate_id = str(load_json(run_dir / "d7_candidate.json")["candidate_id"])
            exact_confirmation("COMMIT", f"COMMIT {candidate_id}")
            run_browser("d7-commit", str(first_launch["base_url"]), run_dir)
            after_commit = checkpoint_ledger(run_dir, "after_commit")
            apply_tickets = [row["ticket"] for row in after_commit.get("tickets", {}).values() if row.get("ticket", {}).get("kind") == "apply"]
            if len(apply_tickets) != 1:
                raise RuntimeError("D7 commit did not produce exactly one apply ticket")
            external_ids = after_commit.get("adapter_state", {}).get("external_ids", {})
            external_id = str(external_ids.get(apply_tickets[0]["idempotency_key"]) or "")
            after = provider_snapshot(provider, time_zone=args.live_timezone)
            if not external_id or external_id not in {str(row["event_id"]) for row in after["events"]}:
                raise RuntimeError("D7 committed event did not verify in an independent EventKit readback")
            write_json(run_dir / "ruler_capture" / "provider.after.raw.json", after)

            exact_confirmation("UNDO", f"UNDO {external_id}")
            run_browser("d7-undo", str(first_launch["base_url"]), run_dir)
            checkpoint_ledger(run_dir, "after_undo")
            after_undo = provider_snapshot(provider, time_zone=args.live_timezone)
            if external_id in {str(row["event_id"]) for row in after_undo["events"]}:
                raise RuntimeError("D7 compensation did not verify provider absence")
            write_json(run_dir / "ruler_capture" / "provider.after_undo.raw.json", after_undo)
            stop_launch(first_launch)
            first_launch = {}

            launch_d7(app, run_dir, binding_path=binding_path, initialize=False, time_min=time_min, time_max=time_max)
            second_launch, second_health = wait_for_launch(run_dir, previous_launch_id=str(health.get("process", {}).get("launch_id") or ""))
            run_browser("after-restart", str(second_launch["base_url"]), run_dir)
            shutil.copy2(run_dir / "launch_state.json", run_dir / "launch_state.after.json")
            write_json(run_dir / "process_snapshot.after.json", process_snapshot(run_dir.name, second_launch, second_health))
            checkpoint_ledger(run_dir, "after_restart")
            stop_launch(second_launch)
            second_launch = {}

            normalize(run_dir)
            report = build_report(run_dir=run_dir)
            write_json(run_dir / "D7_RESULT.json", {
                "run_id": run_dir.name,
                "decision": report["decision"],
                "binding_eligible": report["binding_eligible"],
                "external_id": external_id,
            })
            print(json.dumps({
                "run_dir": str(run_dir),
                "decision": report["decision"],
                "binding_eligible": report["binding_eligible"],
                "first_blocking_scenario_id": report["first_blocking_scenario_id"],
                "product_rail": report["product_rail"],
                "distance": report["distance"],
            }, indent=2, sort_keys=True), flush=True)
            return report
        finally:
            if first_launch:
                stop_launch(first_launch)
            if second_launch:
                stop_launch(second_launch)
            cleanup = cleanup_parent_fixture(fixture)
            if run_dir is not None:
                summary_path = run_dir / "parent_fixture.json"
                summary = load_json(summary_path) if summary_path.is_file() else {}
                summary["cleanup_status"] = "verified_absent" if cleanup.get("phase") == "verified" else "manual_resolution_required"
                summary["cleanup_receipt_sha256"] = cleanup.get("receipt_sha256")
                write_json(summary_path, summary)
                write_json(run_dir / "parent_fixture_cleanup.json", cleanup)
            if fixture and cleanup.get("phase") != "verified":
                print(f"D7_PARENT_CLEANUP_REQUIRED={fixture.get('external_id')}", file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-bundle", default=str(DEFAULT_APP))
    parser.add_argument("--architecture-report", default=str(DEFAULT_ARCHITECTURE_REPORT))
    parser.add_argument("--out-root", default=str(ROOT / "runs/dogfood"))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--calendar-id", default=DEFAULT_CALENDAR_ID)
    parser.add_argument("--live-timezone", default="America/Los_Angeles")
    args = parser.parse_args()
    report = run(args)
    raise SystemExit(0 if report["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
