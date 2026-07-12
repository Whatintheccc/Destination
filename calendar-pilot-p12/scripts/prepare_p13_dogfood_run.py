#!/usr/bin/env python3
"""Preregister one immutable P13 dogfood cell before the app launches."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
SCENARIO_SET = ROOT / "evals/dogfood/scenarios/p13_product_v2.json"
MANIFEST_SCHEMA = ROOT / "contracts/dogfood_run_manifest.schema.json"
TRUTH_SCHEMA = ROOT / "contracts/dogfood_operator_truth.schema.json"
DEFAULT_APP = ROOT / "dist/CalendarPilot.app"
DEFAULT_ARCHITECTURE_REPORT = ROOT / "runs/architecture_evals/architecture_eval_report_v2.json"
DEFAULT_FIXTURE = ROOT / "data/sample_calendar.json"
NOOP_FIXTURE = ROOT / "data/noop_dominates_calendar.json"
PREDICATE_ARTIFACTS = (
    ROOT / "evals/dogfood/predicates/product.py",
    ROOT / "evals/dogfood/admissibility.py",
    ROOT / "evals/dogfood/capture/browser_capture.py",
    ROOT / "evals/dogfood/capture/normalize_d1.py",
    ROOT / "scripts/browser_dogfood_d1.mjs",
    ROOT / "scripts/run_p13_dogfood_d1.py",
    NOOP_FIXTURE,
)

RUNTIME_BINDINGS: dict[str, dict[str, Any]] = {
    "fixture": {
        "expected_backends": {
            "codex": "deterministic_codex_tool_planner",
            "diffusiongemma": "heuristic_diffusiongemma_policy",
            "kernel": "SwiftKernelStub",
            "provider": "deterministic_fixture_provider",
        },
        "credential_classes": ["none"],
    },
    "swift_ipc": {
        "expected_backends": {
            "codex": "deterministic_codex_tool_planner",
            "diffusiongemma": "heuristic_diffusiongemma_policy",
            "kernel": "SwiftKernelIPCClient",
            "provider": "deterministic_fixture_provider",
        },
        "credential_classes": ["none"],
    },
    "live_codex": {
        "expected_backends": {
            "codex": "live_codex_app_server",
            "diffusiongemma": "heuristic_diffusiongemma_policy",
            "kernel": "SwiftKernelIPCClient",
            "provider": "deterministic_fixture_provider",
        },
        "credential_classes": ["codex_subscription"],
    },
    "live_diffusiongemma": {
        "expected_backends": {
            "codex": "deterministic_codex_tool_planner",
            "diffusiongemma": "nvidia_nim_diffusiongemma_policy",
            "kernel": "SwiftKernelIPCClient",
            "provider": "deterministic_fixture_provider",
        },
        "credential_classes": ["nvidia_nim"],
    },
    "live_provider": {
        "expected_backends": {
            "codex": "deterministic_codex_tool_planner",
            "diffusiongemma": "heuristic_diffusiongemma_policy",
            "kernel": "SwiftKernelIPCClient",
            "provider": "apple_eventkit",
        },
        "credential_classes": ["eventkit_permission"],
    },
    "auto": {
        "expected_backends": {
            "codex": "live_codex_app_server",
            "diffusiongemma": "nvidia_nim_diffusiongemma_policy",
            "kernel": "SwiftKernelIPCClient",
            "provider": "apple_eventkit",
        },
        "credential_classes": ["codex_subscription", "nvidia_nim", "eventkit_permission"],
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPOSITORY_ROOT, text=True).strip()


def validate(payload: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors)
        raise ValueError(f"{label} schema validation failed: {detail}")


def selected_scenarios(scenario_set: dict[str, Any], cell: str) -> list[dict[str, Any]]:
    return [row for row in scenario_set["scenarios"] if cell in row["cells"]]


def required_artifacts(scenario_set: dict[str, Any], cell: str) -> list[str]:
    requirements = scenario_set["artifact_requirements"]
    values = list(requirements["D0" if cell == "D0" else "D1-D7"])
    if cell == "D7":
        values.extend(requirements["D7"])
    if len(values) != len(set(values)):
        raise ValueError("scenario set declares duplicate required artifacts")
    return values


def fixture_truth(run_id: str, created_at: str, fixture_path: Path) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    facts: list[dict[str, Any]] = []
    for event in fixture.get("events", []):
        value = {
            key: event.get(key)
            for key in ("event_id", "start", "end", "calendar_id", "is_user_owned", "is_flexible", "category")
        }
        facts.append({
            "fact_id": str(event["event_id"]),
            "kind": "calendar_event",
            "value": value,
            "source_hash": sha256_json(event),
        })
    noop_fixture = json.loads(NOOP_FIXTURE.read_text(encoding="utf-8"))
    facts.append({
        "fact_id": "fixture:noop_dominates",
        "kind": "fixture_truth",
        "value": {
            "fixture_id": "noop_dominates",
            "noop_dominates": True,
            "observation_id": noop_fixture["observation_id"],
            "fixture_path": str(NOOP_FIXTURE.relative_to(ROOT)),
        },
        "source_hash": sha256_file(NOOP_FIXTURE),
    })
    return {
        "dogfood_operator_truth_schema_version": "dogfood_operator_truth.v1",
        "run_id": run_id,
        "created_at": created_at,
        "timezone": str(fixture["time_zone_id"]),
        "redaction_class": "fixture",
        "provider_identity": "deterministic_fixture_provider",
        "facts": facts,
    }


def live_gap_truth(run_id: str, created_at: str, *, timezone_name: str, time_min: str, time_max: str) -> dict[str, Any]:
    lower = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
    upper = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
    if lower.tzinfo is None or upper.tzinfo is None or upper <= lower:
        raise ValueError("live EventKit truth requires an offset-aware, increasing read window")
    gap_value = {
        "time_min": lower.isoformat(),
        "time_max": upper.isoformat(),
        "event_count": 0,
        "verification_method": "mac_calendar_ui",
    }
    noop_fixture = json.loads(NOOP_FIXTURE.read_text(encoding="utf-8"))
    facts = [
        {
            "fact_id": f"calendar_gap:{sha256_json(gap_value)[:16]}",
            "kind": "calendar_gap",
            "value": gap_value,
            "source_hash": sha256_json(gap_value),
        },
        {
            "fact_id": "fixture:noop_dominates",
            "kind": "fixture_truth",
            "value": {
                "fixture_id": "noop_dominates",
                "noop_dominates": True,
                "observation_id": noop_fixture["observation_id"],
                "fixture_path": str(NOOP_FIXTURE.relative_to(ROOT)),
                "execution_scope": "isolated_shadow",
            },
            "source_hash": sha256_file(NOOP_FIXTURE),
        },
    ]
    return {
        "dogfood_operator_truth_schema_version": "dogfood_operator_truth.v1",
        "run_id": run_id,
        "created_at": created_at,
        "timezone": timezone_name,
        "redaction_class": "sensitive_local_only",
        "provider_identity": "apple_eventkit",
        "facts": facts,
    }


def process_identity() -> dict[str, str]:
    dirty = git("status", "--short")
    if dirty:
        raise RuntimeError("dogfood preregistration requires a clean worktree")
    branch = git("branch", "--show-current")
    if branch != "main":
        raise RuntimeError(f"dogfood preregistration requires main, found {branch or 'detached HEAD'}")
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    if head != origin:
        raise RuntimeError("dogfood preregistration requires HEAD == origin/main")
    return {"git_sha": head, "app_tree_sha": git("rev-parse", "HEAD:calendar-pilot-p12")}


def app_identity(app_bundle: Path, git_sha: str) -> dict[str, str]:
    build_id_path = app_bundle / "Contents/Resources/app/build_id"
    app_path = app_bundle / "Contents/MacOS/CalendarPilot"
    bridge_path = app_bundle / "Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge"
    for path in (build_id_path, app_path, bridge_path):
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"built app artifact is missing or empty: {path}")
    build_id = build_id_path.read_text(encoding="utf-8").strip()
    if build_id != git_sha[:12]:
        raise RuntimeError(f"app build_id {build_id} does not match protected-main HEAD {git_sha[:12]}")
    return {
        "build_id": build_id,
        "app_bundle_path": str(app_bundle.resolve()),
        "app_sha256": sha256_file(app_path),
        "bridge_sha256": sha256_file(bridge_path),
    }


def prepare(args: argparse.Namespace) -> Path:
    scenario_set_path = Path(args.scenario_set).resolve()
    scenario_set = json.loads(scenario_set_path.read_text(encoding="utf-8"))
    scenarios = selected_scenarios(scenario_set, args.cell)
    if not scenarios:
        raise ValueError(f"scenario set has no scenarios for {args.cell}")
    repository = process_identity()
    app = app_identity(Path(args.app_bundle).resolve(), repository["git_sha"])
    if args.runtime_mode not in RUNTIME_BINDINGS:
        raise ValueError(f"unsupported runtime mode: {args.runtime_mode}")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    created_at = now.isoformat().replace("+00:00", "Z")
    run_id = args.run_id or f"{now.strftime('%Y%m%dT%H%M%SZ')}-{args.cell.lower()}-{args.runtime_mode}-{repository['git_sha'][:12]}"
    run_dir = Path(args.out_root).resolve() / run_id
    if run_dir.exists():
        raise FileExistsError(f"dogfood run already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    try:
        architecture_source = Path(args.architecture_report).resolve()
        if not architecture_source.is_file() or architecture_source.stat().st_size == 0:
            raise FileNotFoundError(f"signed architecture report is missing: {architecture_source}")
        shutil.copy2(architecture_source, run_dir / "architecture_eval_report_v2.json")
        runtime = {"requested_mode": args.runtime_mode, **RUNTIME_BINDINGS[args.runtime_mode]}
        manifest = {
            "dogfood_run_manifest_schema_version": "dogfood_run_manifest.v1",
            "run_id": run_id,
            "created_at": created_at,
            "cell": args.cell,
            "run_dir": str(run_dir),
            "repository": {**repository, "clean": True},
            "build": app,
            "runtime": runtime,
            "scenario_set": {"path": str(scenario_set_path.relative_to(ROOT)), "sha256": sha256_file(scenario_set_path)},
            "predicate_artifacts": [
                {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
                for path in PREDICATE_ARTIFACTS
            ],
            "scenario_ids": [row["scenario_id"] for row in scenarios],
            "stimuli": [
                {"scenario_id": row["scenario_id"], "utf8_sha256": hashlib.sha256(row["stimulus"].encode("utf-8")).hexdigest()}
                for row in scenarios
            ],
            "effect_ceiling": {
                "provider_mutations": 1 if args.cell == "D7" else 0,
                "effect_attempts": 1 if args.cell == "D7" else 0,
                "stage_actions": 1 if args.cell in {"D2", "D7"} else 0,
                "claims": 1 if args.cell == "D7" else 0,
                "outbox_dispatches": 1 if args.cell == "D7" else 0,
            },
            "required_artifacts": required_artifacts(scenario_set, args.cell),
            "timeouts_seconds": scenario_set["performance_budgets_seconds"],
            "operator_checkpoints": (
                ["confirm_one_private_create", "confirm_compensation"]
                if args.cell == "D7"
                else (["confirm_live_read_window"] if args.cell in {"D5", "D6"} else [])
            ),
        }
        if args.cell in {"D5", "D6"}:
            if not args.live_window_start or not args.live_window_end:
                raise ValueError(f"{args.cell} requires a pre-confirmed bounded live EventKit window")
            truth = live_gap_truth(
                run_id,
                created_at,
                timezone_name=args.live_timezone,
                time_min=args.live_window_start,
                time_max=args.live_window_end,
            )
        elif args.cell == "D7":
            raise ValueError(f"{args.cell} live operator-truth preparation is not implemented")
        else:
            truth = fixture_truth(run_id, created_at, Path(args.fixture).resolve())
        validate(manifest, MANIFEST_SCHEMA, "dogfood run manifest")
        validate(truth, TRUTH_SCHEMA, "dogfood operator truth")
        (run_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (run_dir / "operator_truth.json").write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(run_dir)
        raise
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cell", required=True, choices=[f"D{index}" for index in range(8)])
    parser.add_argument("--runtime-mode", required=True, choices=sorted(RUNTIME_BINDINGS))
    parser.add_argument("--scenario-set", default=str(SCENARIO_SET))
    parser.add_argument("--app-bundle", default=str(DEFAULT_APP))
    parser.add_argument("--architecture-report", default=str(DEFAULT_ARCHITECTURE_REPORT))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--live-window-start", default="")
    parser.add_argument("--live-window-end", default="")
    parser.add_argument("--live-timezone", default="America/Los_Angeles")
    parser.add_argument("--out-root", default=str(ROOT / "runs/dogfood"))
    parser.add_argument("--run-id", default="")
    args = parser.parse_args()
    run_dir = prepare(args)
    print(json.dumps({"ok": True, "run_dir": str(run_dir), "run_id": run_dir.name}, indent=2))


if __name__ == "__main__":
    main()
