#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json
from evals.architecture.adapters import P12CurrentAdapter
from evals.architecture.evaluation import derive_gate_decision, evaluate_scenario, summarize_rail


DEFAULT_SCENARIOS = ROOT / "evals/architecture/scenarios/canonical.json"
DEFAULT_OUT = ROOT / "runs/architecture_evals/architecture_eval_report.json"
DEFAULT_RUNS_ROOT = ROOT / "runs/architecture_evals"
REPORT_SCHEMA = ROOT / "contracts/architecture_eval_report.schema.json"
FORBIDDEN_SCENARIO_VERDICT_KEYS = {"decision", "expected_status", "ok", "pass", "passed"}
REQUIRED_PRESERVATION_SCENARIO_IDS = {
    "preservation.frontier_normal",
    "preservation.authority_belief_denial",
    "preservation.expired_authority",
    "preservation.missing_belief_evidence",
    "preservation.action_reward",
    "preservation.provider_commit",
    "preservation.provider_conflict",
    "preservation.provider_rollback",
    "preservation.explanation_trace",
    "preservation.frontier_timeout",
    "preservation.restart_restore",
}
REQUIRED_TARGET_SCENARIO_IDS = {
    "target.trajectory_projection",
    "target.authority_coexistence",
    "target.frontier_safety_vector",
    "target.migration_comparison",
    "target.monitor_removal",
    "target.authority_revoke",
    "target.provider_verify_failure",
    "target.executable_explanation_controls",
    "target.rollback_audit_history",
}


def _resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git(*args: str, cwd: Path) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return process.stdout.strip() if process.returncode == 0 else "unknown"


def _git_bytes(*args: str, cwd: Path) -> bytes:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.decode("utf-8", errors="replace").strip() or "git command failed")
    return process.stdout


def _working_tree_digest(git_root: Path, app_path: str) -> str:
    digest = hashlib.sha256()
    digest.update(b"tracked-diff\0")
    digest.update(_git_bytes("diff", "--binary", "HEAD", "--", app_path, cwd=git_root))
    untracked = _git_bytes("ls-files", "--others", "--exclude-standard", "-z", "--", app_path, cwd=git_root)
    for raw in sorted(value for value in untracked.split(b"\0") if value):
        relative = raw.decode("utf-8")
        path = git_root / relative
        digest.update(b"untracked\0")
        digest.update(raw)
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(os.readlink(path).encode("utf-8"))
        elif path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def repository_identity(root: Path = ROOT) -> dict[str, Any]:
    git_root_value = _git("rev-parse", "--show-toplevel", cwd=root)
    git_root = Path(git_root_value) if git_root_value != "unknown" else root.parent
    try:
        app_path = root.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError:
        app_path = root.name
    status = _git_bytes("status", "--porcelain=v1", "-z", "--", app_path, cwd=git_root)
    return {
        "git_sha": _git("rev-parse", "HEAD", cwd=git_root),
        "app_tree_sha": _git("rev-parse", f"HEAD:{app_path}", cwd=git_root),
        "app_path": app_path,
        "dirty": bool(status),
        "git_status_sha256": _sha256_bytes(status),
        "app_worktree_sha256": _working_tree_digest(git_root, app_path),
    }


def load_scenario_set(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("architecture_scenario_set_schema_version") != "architecture_scenario_set.v1":
        raise ValueError("unsupported architecture scenario-set version")
    if payload.get("adapter") != "p12_current":
        raise ValueError("the deterministic baseline requires the p12_current adapter")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not 10 <= len(scenarios) <= 20:
        raise ValueError("architecture baseline must contain 10-20 canonical scenarios")
    ids: set[str] = set()
    required = {"scenario_id", "rail", "gate_mode", "category", "adapter_case", "predicate_id", "binding_trigger"}
    for row in scenarios:
        if not isinstance(row, dict):
            raise ValueError("scenario rows must be objects")
        missing = required - set(row)
        if missing:
            raise ValueError(f"scenario missing fields: {sorted(missing)}")
        forbidden = FORBIDDEN_SCENARIO_VERDICT_KEYS & set(row)
        if forbidden:
            raise ValueError(f"scenario {row.get('scenario_id')} contains forbidden verdict fields: {sorted(forbidden)}")
        scenario_id = str(row["scenario_id"])
        if scenario_id in ids:
            raise ValueError(f"duplicate scenario id: {scenario_id}")
        ids.add(scenario_id)
        if row["rail"] not in {"preservation", "target_conformance"}:
            raise ValueError(f"invalid rail for {scenario_id}")
        if row["gate_mode"] not in {"required", "observe"}:
            raise ValueError(f"invalid gate mode for {scenario_id}")
        if row["rail"] == "preservation" and row["gate_mode"] != "required":
            raise ValueError(f"preservation scenario must be required: {scenario_id}")
    preservation_ids = {str(row["scenario_id"]) for row in scenarios if row["rail"] == "preservation"}
    target_ids = {str(row["scenario_id"]) for row in scenarios if row["rail"] == "target_conformance"}
    if preservation_ids != REQUIRED_PRESERVATION_SCENARIO_IDS:
        raise ValueError(
            "architecture_scenario_set.v1 preservation coverage changed without a version bump: "
            f"missing={sorted(REQUIRED_PRESERVATION_SCENARIO_IDS - preservation_ids)}, "
            f"unexpected={sorted(preservation_ids - REQUIRED_PRESERVATION_SCENARIO_IDS)}"
        )
    if target_ids != REQUIRED_TARGET_SCENARIO_IDS:
        raise ValueError(
            "architecture_scenario_set.v1 target coverage changed without a version bump: "
            f"missing={sorted(REQUIRED_TARGET_SCENARIO_IDS - target_ids)}, "
            f"unexpected={sorted(target_ids - REQUIRED_TARGET_SCENARIO_IDS)}"
        )
    return payload


def _artifact(kind: str, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"architecture-eval artifact is missing or not a file: {path}")
    return {
        "kind": kind,
        "path": str(path),
        "sha256": _sha256(path),
    }


def _instrument_artifacts() -> list[dict[str, Any]]:
    paths = [
        Path(__file__),
        ROOT / "evals/architecture/evaluation.py",
        ROOT / "evals/architecture/adapters/p12_current.py",
        ROOT / "evals/architecture/predicates/core.py",
        DEFAULT_SCENARIOS,
        REPORT_SCHEMA,
    ]
    return [_artifact("eval_instrument", path) for path in paths]


def _new_run_id(started_at: datetime) -> str:
    return f"architecture-evals-{started_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}"


def _prepare_artifact_root(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    protected = {Path("/").resolve(), Path.home().resolve(), ROOT.resolve(), ROOT.parent.resolve()}
    if resolved in protected or ROOT.resolve().is_relative_to(resolved):
        raise ValueError(f"refusing unsafe architecture-eval artifact root: {resolved}")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"architecture-eval artifact root must be a new path: {path}")
    path.mkdir(parents=True, exist_ok=False)
    return path


def validate_report(report: dict[str, Any]) -> None:
    schema = json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(report), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError(f"architecture-eval report schema validation failed: {details}")
    scenarios = report["scenarios"]
    scenario_ids = [str(row["scenario_id"]) for row in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("architecture-eval report contains duplicate scenario ids")
    expected_rails = {
        "preservation": summarize_rail(scenarios, "preservation"),
        "target_conformance": summarize_rail(scenarios, "target_conformance"),
    }
    if report["rails"] != expected_rails:
        raise ValueError("architecture-eval rail summaries are not derived from scenario results")
    decision = derive_gate_decision(scenarios)
    if report["decision"] != decision or report["execution"]["report_decision"] != decision:
        raise ValueError("architecture-eval report decision is not derived from scenario results")
    if report["execution"]["exit_code"] != (0 if decision == "pass" else 1):
        raise ValueError("architecture-eval recorded exit code disagrees with its decision")
    for artifact in [*report["instrument_artifacts"], *(item for row in scenarios for item in row["artifacts"])]:
        path = Path(str(artifact["path"]))
        if not path.is_file() or _sha256(path) != artifact["sha256"]:
            raise ValueError(f"architecture-eval artifact hash mismatch: {path}")


def build_report(
    *,
    scenario_set_path: Path = DEFAULT_SCENARIOS,
    artifact_root: Path | None = None,
    out: Path = DEFAULT_OUT,
    command: str = "PYTHONPATH=src python3 evals/architecture/run_architecture_evals.py",
    access_point: str = "python build_report API",
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    run_id = _new_run_id(started_at)
    scenario_set_path = _resolve(scenario_set_path)
    artifact_root = _resolve(artifact_root) if artifact_root is not None else DEFAULT_RUNS_ROOT / run_id / "artifacts"
    out = _resolve(out)
    scenario_set = load_scenario_set(scenario_set_path)
    artifact_root = _prepare_artifact_root(artifact_root)
    immutable_out = artifact_root.parent / "architecture_eval_report.json"
    adapter = P12CurrentAdapter(ROOT)
    results: list[dict[str, Any]] = []
    for spec in scenario_set["scenarios"]:
        scenario_id = str(spec["scenario_id"])
        scenario_dir = artifact_root / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        source_artifacts: list[tuple[str, Path]] = []
        try:
            observable_vector, source_artifacts = adapter.collect(str(spec["adapter_case"]), scenario_dir)
            evaluated = evaluate_scenario(spec, observable_vector)
        except Exception as exc:
            observable_vector = {
                "collection_error": {
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }
            }
            evaluated = {
                "status": "fail" if spec["gate_mode"] == "required" else "hold",
                "summary": "Scenario evidence collection failed.",
                "predicate_evidence": observable_vector["collection_error"],
            }
        evidence_path = scenario_dir / "evidence.json"
        atomic_write_json(
            evidence_path,
            {
                "scenario_id": scenario_id,
                "adapter_case": spec["adapter_case"],
                "predicate_id": spec["predicate_id"],
                "observable_vector": observable_vector,
                "predicate_result": evaluated,
            },
        )
        artifacts = [_artifact(kind, Path(path)) for kind, path in source_artifacts]
        artifacts.append(_artifact("scenario_evidence", evidence_path))
        results.append(
            {
                "scenario_id": scenario_id,
                "rail": spec["rail"],
                "gate_mode": spec["gate_mode"],
                "category": spec["category"],
                "adapter_case": spec["adapter_case"],
                "predicate_id": spec["predicate_id"],
                "binding_trigger": spec["binding_trigger"],
                "status": evaluated["status"],
                "summary": evaluated["summary"],
                "observable_vector": observable_vector,
                "predicate_evidence": evaluated["predicate_evidence"],
                "artifacts": artifacts,
            }
        )
    rails = {
        "preservation": summarize_rail(results, "preservation"),
        "target_conformance": summarize_rail(results, "target_conformance"),
    }
    decision = derive_gate_decision(results)
    finished_at = datetime.now(timezone.utc)
    report = {
        "architecture_eval_report_schema_version": "architecture_eval_report.v1",
        "run_id": run_id,
        "generated_at": finished_at.isoformat(),
        "decision": decision,
        "repository": repository_identity(ROOT),
        "instrument_artifacts": _instrument_artifacts(),
        "report_paths": {
            "latest": str(out),
            "immutable": str(immutable_out),
        },
        "execution": {
            "cwd": str(Path.cwd().resolve()),
            "command": command,
            "access_point": access_point,
            "adapter": adapter.adapter_id,
            "runtime_mode": "fixture",
            "backend_identities": {
                "authority": "deterministic fixture authority boundary",
                "frontier": "deterministic fixture respondents",
                "provider": "deterministic fixture provider",
            },
            "live_backends": [],
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "exit_code": 0 if decision == "pass" else 1,
            "report_decision": decision,
            "environment_variable_names_present": sorted(
                name
                for name in os.environ
                if name == "PYTHONPATH" or name.startswith("CALENDAR_PILOT_")
            ),
        },
        "scenario_set": {
            "scenario_set_id": scenario_set["scenario_set_id"],
            "path": str(scenario_set_path),
            "sha256": _sha256(scenario_set_path),
        },
        "artifact_root": str(artifact_root),
        "rails": rails,
        "scenarios": results,
    }
    validate_report(report)
    atomic_write_json(immutable_out, report)
    if out.resolve() != immutable_out.resolve():
        atomic_write_json(out, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic two-rail architecture eval baseline.")
    parser.add_argument("--scenario-set", default=str(DEFAULT_SCENARIOS))
    parser.add_argument("--artifact-root", default="")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"architecture evals must run from active app root: {ROOT}")
    command = " ".join([sys.executable, *sys.argv])
    report = build_report(
        scenario_set_path=_resolve(args.scenario_set),
        artifact_root=_resolve(args.artifact_root) if args.artifact_root else None,
        out=_resolve(args.out),
        command=command,
        access_point=os.environ.get("CALENDAR_PILOT_ARCH_EVAL_ACCESS_POINT", "direct architecture-eval CLI"),
    )
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "preservation": report["rails"]["preservation"],
                "target_conformance": report["rails"]["target_conformance"],
                "out": str(_resolve(args.out)),
                "immutable_out": report["report_paths"]["immutable"],
                "run_id": report["run_id"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise SystemExit(0 if report["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
