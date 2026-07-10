#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
GIT_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json
from evals.p13_ruler.core import build_loc_report, verify_binding_manifest
from evals.p13_ruler.wave import (
    build_experiment_record,
    b_migrate_assertions_path,
    compare_b_migrate_artifacts,
    compare_cvar_frontier_sets,
    is_owner_controlled_eventkit_sandbox_wave,
    is_owner_controlled_sandbox_wave,
    is_owner_controlled_vertical_retirement_wave,
    is_structurally_no_effect_wave,
    load_json,
    resolve,
    verify_root_list,
)


def uses_fixed_reward_fixture(
    manifest: dict[str, Any],
    verification: dict[str, Any],
    architecture: dict[str, Any],
) -> bool:
    return bool(
        manifest.get("change_class") == "ruler"
        or is_structurally_no_effect_wave(manifest, verification, architecture)
        or is_owner_controlled_sandbox_wave(manifest, verification, architecture)
        or is_owner_controlled_eventkit_sandbox_wave(manifest, verification, architecture)
        or is_owner_controlled_vertical_retirement_wave(manifest, verification, architecture)
    )


def _producer_command(manifest: dict[str, Any], side: str, family: str) -> list[str]:
    key = "old_producer" if side in {"before", "old"} else "new_producer"
    command = manifest.get(key, {}).get(family, {}).get("command")
    if not isinstance(command, list) or not command or not all(isinstance(value, str) and value for value in command):
        raise ValueError(f"BindingManifest has no valid {side} {family} command")
    return list(command)


def _run(command: list[str], *, artifact: Path | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    process = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False)
    decision = None
    if artifact is not None and artifact.is_file():
        try:
            decision = load_json(artifact).get("decision")
        except (ValueError, json.JSONDecodeError):
            decision = None
    if process.returncode != 0 and decision not in {"hold", "fail"}:
        decision = "fail"
    return {
        "command": command,
        "returncode": process.returncode,
        "decision": decision or ("pass" if process.returncode == 0 else "fail"),
        "stdout": process.stdout[-2000:],
        "stderr": process.stderr[-2000:],
    }


def _produce(command: list[str], out: Path) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    result = _run([*command, "--out", str(out)], artifact=out)
    if result["returncode"] != 0 or not out.is_file():
        raise RuntimeError(f"producer failed: {' '.join(command)}\n{result['stderr']}")
    return result


def _schema_status(payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
    schema_path = ROOT / "contracts" / schema_name
    errors = sorted(Draft202012Validator(load_json(schema_path)).iter_errors(payload), key=lambda error: list(error.path))
    return {
        "schema": schema_name,
        "status": "pass" if not errors else "fail",
        "errors": [f"{list(error.path)}: {error.message}" for error in errors],
    }


def _artifact_decision(path: Path) -> str:
    if not path.is_file():
        return "fail"
    return str(load_json(path).get("decision", "fail"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--verification-key", required=True)
    parser.add_argument("--before-cvar-artifact", default="")
    parser.add_argument("--out", default="runs/p13_wave_gate_report.json")
    args = parser.parse_args()
    manifest_path = resolve(args.manifest)
    key_path = Path(args.verification_key).resolve()
    manifest = load_json(manifest_path)
    wave = str(manifest.get("wave", "unknown"))
    artifacts = ROOT / "runs" / "p13_wave_gate" / wave
    artifacts.mkdir(parents=True, exist_ok=True)

    verification = verify_binding_manifest(manifest, verification_key=key_path)
    verification_path = artifacts / "binding_manifest_verification.json"
    atomic_write_json(verification_path, verification)

    architecture_path = artifacts / "architecture_eval_report_v2.json"
    architecture_run = _run(
        [
            sys.executable,
            "evals/architecture/run_architecture_evals.py",
            "--scenario-set",
            "evals/architecture/scenarios/p13_v2.json",
            "--binding-manifest",
            str(manifest_path),
            "--verification-key",
            str(key_path),
            "--out",
            str(architecture_path),
        ],
        artifact=architecture_path,
        env={**os.environ, "PYTHONPATH": "src", "CALENDAR_PILOT_ARCH_EVAL_ACCESS_POINT": "make wave-harness"},
    )

    before_cvar = resolve(args.before_cvar_artifact) if args.before_cvar_artifact else artifacts / "cvar_before.json"
    after_cvar = artifacts / "cvar_after.json"
    behavior_change = manifest.get("change_class") in {"migration", "compression", "learning"}
    producer_runs: dict[str, Any] = {}
    if args.before_cvar_artifact:
        producer_runs["cvar_before"] = {"decision": "pass", "command": ["frozen-artifact", str(before_cvar)], "returncode": 0}
    elif behavior_change:
        raise SystemExit("behavior-bearing waves require --before-cvar-artifact frozen before candidate work")
    else:
        producer_runs["cvar_before"] = _produce(_producer_command(manifest, "before", "cvar"), before_cvar)
    producer_runs["cvar_after"] = _produce(_producer_command(manifest, "after", "cvar"), after_cvar)
    cvar = compare_cvar_frontier_sets(
        before_path=before_cvar,
        after_path=after_cvar,
        thresholds_path=ROOT / "experiments/configs/cvar_thresholds.json",
        manifest=manifest,
    )
    cvar_path = artifacts / "cvar_report_v2.json"
    atomic_write_json(cvar_path, cvar)

    b_old = artifacts / "b_migrate_old.json"
    b_new = artifacts / "b_migrate_new.json"
    producer_runs["b_migrate_old"] = _produce(_producer_command(manifest, "old", "b_migrate"), b_old)
    producer_runs["b_migrate_new"] = _produce(_producer_command(manifest, "new", "b_migrate"), b_new)
    b_migrate = compare_b_migrate_artifacts(
        before_path=b_old,
        after_path=b_new,
        assertions_path=b_migrate_assertions_path(manifest),
        manifest=manifest,
    )
    b_migrate_path = artifacts / "b_migrate_report_v2.json"
    atomic_write_json(b_migrate_path, b_migrate)

    release_path = ROOT / "runs/p12_release/p12_release_report.json"
    release_env = {**os.environ, "PYTHONPATH": "src"}
    architecture = load_json(architecture_path)
    fixed_reward_fixture = uses_fixed_reward_fixture(manifest, verification, architecture)
    if fixed_reward_fixture:
        release_env["CALENDAR_PILOT_REWARD_REPLAY"] = "tests/fixtures/p13_action_rewards.jsonl"
    release_run = _run([sys.executable, "scripts/run_p12_release.py"], artifact=release_path, env=release_env)
    reward_path = artifacts / "reward_screen_report.json"
    reward_run = _run(
        [
            sys.executable,
            "scripts/make_reward_head_report.py",
            "--replay",
            "runs/p12_release/action_reward_replay.jsonl",
            "--require-source-shape",
            "--out",
            str(reward_path),
        ],
        artifact=reward_path,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    root_list = verify_root_list(manifest)
    root_list_path = artifacts / "root_list_verification.json"
    atomic_write_json(root_list_path, root_list)
    loc = build_loc_report()
    loc_path = artifacts / "loc_report.json"
    atomic_write_json(loc_path, loc)

    experiment_path = artifacts / "experiment_record.json"
    experiment = build_experiment_record(
        manifest_path=manifest_path,
        binding_verification_path=verification_path,
        architecture_report_path=architecture_path,
        cvar_report_path=cvar_path,
        b_migrate_report_path=b_migrate_path,
        release_report_path=release_path,
        reward_report_path=reward_path,
        root_list_report_path=root_list_path,
        loc_report_path=loc_path,
    )
    atomic_write_json(experiment_path, experiment)

    schema_checks = [
        _schema_status(load_json(before_cvar), "cvar_frontier_set.schema.json"),
        _schema_status(load_json(after_cvar), "cvar_frontier_set.schema.json"),
        _schema_status(cvar, "cvar_report_v2.schema.json"),
        _schema_status(load_json(b_old), "b_migrate_artifact.schema.json"),
        _schema_status(load_json(b_new), "b_migrate_artifact.schema.json"),
        _schema_status(b_migrate, "b_migrate_report_v2.schema.json"),
        _schema_status(root_list, "p13_root_list_verification.schema.json"),
        _schema_status(load_json(reward_path), "reward_head_report_v3.schema.json"),
        _schema_status(experiment, "experiment_record_v2.schema.json"),
    ]
    gates = {
        "binding_manifest": verification.get("decision", "fail"),
        "architecture": _artifact_decision(architecture_path),
        "cvar": cvar.get("decision", "fail"),
        "b_migrate": b_migrate.get("decision", "fail"),
        "p12_release": _artifact_decision(release_path),
        "reward_screen": _artifact_decision(reward_path),
        "root_list": root_list.get("decision", "fail"),
        "loc": loc.get("decision", "fail"),
        "experiment_record": experiment.get("decision", "fail"),
        "schema_validation": "pass" if all(row["status"] == "pass" for row in schema_checks) else "fail",
    }
    decision = "fail" if "fail" in gates.values() else "hold" if any(value != "pass" for value in gates.values()) else "pass"
    report = {
        "p13_wave_gate_report_schema_version": "p13_wave_gate_report.v1",
        "wave": wave,
        "manifest_id": manifest.get("manifest_id"),
        "change_class": manifest.get("change_class"),
        "decision": decision,
        "ok": decision == "pass",
        "gates": gates,
        "schema_checks": schema_checks,
        "producer_runs": producer_runs,
        "subprocesses": {"architecture": architecture_run, "p12_release": release_run, "reward_screen": reward_run},
        "artifacts": {
            "binding_verification": str(verification_path),
            "architecture": str(architecture_path),
            "cvar": str(cvar_path),
            "b_migrate": str(b_migrate_path),
            "p12_release": str(release_path),
            "reward_screen": str(reward_path),
            "root_list": str(root_list_path),
            "loc": str(loc_path),
            "experiment_record": str(experiment_path),
        },
    }
    wave_schema = _schema_status(report, "p13_wave_gate_report.schema.json")
    report["schema_checks"].append(wave_schema)
    if wave_schema["status"] != "pass":
        report["gates"]["schema_validation"] = "fail"
        report["decision"] = "fail"
        report["ok"] = False
    out = resolve(args.out)
    atomic_write_json(out, report)
    print(json.dumps({"ok": report["ok"], "decision": report["decision"], "out": str(out), "gates": report["gates"]}, indent=2))
    raise SystemExit(0 if report["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
