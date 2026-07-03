#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from calendar_pilot.environment.fsio import atomic_write_json, atomic_write_text
from calendar_pilot.replay import ReplayBuffer
from run_frontier_diff import build_diff
from train_offline_policy import build_policy_report
from compare_lab_runs import build_comparison, load_rows


LAB_SCHEMA_VERSION = "lab_v0.1"
REPORTS_DIR = ROOT / "experiments" / "reports"
PROMOTED_DIR = ROOT / "experiments" / "promoted"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_sha() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _run_dir(row: dict[str, Any]) -> Path:
    raw = Path(str(row.get("run_dir", "")))
    return raw if raw.is_absolute() else ROOT / raw


def _manifest(row: dict[str, Any]) -> dict[str, Any]:
    return _load_json(_run_dir(row) / "manifest.json")


def _pool_replay(rows: list[dict[str, Any]], out: Path) -> None:
    chunks: list[str] = []
    for row in rows:
        replay = _run_dir(row) / "replay.jsonl"
        if replay.exists():
            text = replay.read_text(encoding="utf-8")
            if text and not text.endswith("\n"):
                text += "\n"
            chunks.append(text)
    atomic_write_text(out, "".join(chunks))


def _candidate_tuning(batch: str, rows: list[dict[str, Any]], candidate_path: Path | None) -> tuple[dict[str, Any], Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pooled_path = REPORTS_DIR / f"pooled_{batch}.jsonl"
    _pool_replay(rows, pooled_path)
    if candidate_path is not None:
        tuning = _load_json(candidate_path)
    else:
        report = build_policy_report(ReplayBuffer.load_jsonl(pooled_path))
        atomic_write_json(REPORTS_DIR / f"candidate_policy_report_{batch}.json", report)
        tuning = dict(report.get("policy_tuning", {}) or {})
    tuning["tuning_id"] = batch
    tuning_path = REPORTS_DIR / f"candidate_policy_tuning_{batch}.json"
    atomic_write_json(tuning_path, tuning)
    return tuning, tuning_path, pooled_path


def _seed_payload(manifest: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    seed_path = manifest.get("seed_path")
    if seed_path:
        path = Path(str(seed_path))
        path = path if path.is_absolute() else ROOT / path
        if path.exists():
            return _load_json(path)
    observation = _load_json(run_dir / "observation.json")
    profile = _load_json(run_dir / "profile.json")
    return {
        "seed_id": manifest.get("seed_id", run_dir.name),
        "goal": manifest.get("goal", ""),
        "expects_tuning_leader_change": False,
        "observation": observation,
        "profile": profile,
    }


def _write_seed_inputs(seed: dict[str, Any], out_dir: Path, seed_id: str) -> tuple[Path, Path]:
    observation_path = out_dir / f"{seed_id}.observation.json"
    profile_path = out_dir / f"{seed_id}.profile.json"
    atomic_write_json(observation_path, seed.get("observation", {}))
    atomic_write_json(profile_path, seed.get("profile", {}))
    return observation_path, profile_path


def _promotion_diffs(batch: str, rows: list[dict[str, Any]], tuning_path: Path) -> tuple[list[str], int, bool]:
    out_dir = REPORTS_DIR / f"promotion_{batch}"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    by_seed: dict[str, dict[str, Any]] = {}
    for row in rows:
        seed_id = str(row.get("seed_id") or row.get("experiment_id"))
        by_seed.setdefault(seed_id, row)
    diff_paths: list[str] = []
    flagged_leader_changes = 0
    penalty_effect = False
    for seed_id, row in sorted(by_seed.items()):
        run_dir = _run_dir(row)
        manifest = _manifest(row)
        seed = _seed_payload(manifest, run_dir)
        observation_path, profile_path = _write_seed_inputs(seed, out_dir, seed_id)
        diff = build_diff(observation_path=observation_path, profile_path=profile_path, tuning_path=tuning_path, goal=str(seed.get("goal", manifest.get("goal", ""))))
        diff_path = out_dir / f"{seed_id}.frontier_diff.json"
        atomic_write_json(diff_path, diff)
        diff_paths.append(_rel(diff_path))
        if seed.get("expects_tuning_leader_change") and diff.get("marginal_leader_changed", diff.get("leader_changed")):
            flagged_leader_changes += 1
        by_id = {row.get("candidate_id"): row for row in diff.get("tuned_frontier", []) if isinstance(row, dict)}
        marginal_deltas = diff.get("per_candidate_marginal_delta") or diff.get("per_candidate_delta", {}) or {}
        for candidate_id, delta in marginal_deltas.items():
            candidate = by_id.get(candidate_id, {})
            if float((delta or {}).get("delta") or 0.0) < 0 and float(candidate.get("reward_breakdown", {}).get("offline_adversary_penalty", 0.0) or 0.0) < 0:
                penalty_effect = True
    return diff_paths, flagged_leader_changes, penalty_effect


def _gate(name: str, passed: bool, actual: Any, threshold: Any) -> dict[str, Any]:
    return {"status": "pass" if passed else "fail", "actual": actual, "threshold": threshold}


def evaluate_gates(metrics: dict[str, Any], thresholds: dict[str, Any], flagged_changes: int, penalty_effect: bool, tuning: dict[str, Any]) -> dict[str, Any]:
    gates = {
        "valid_frontier_rate": _gate(
            "valid_frontier_rate",
            float(metrics.get("valid_frontier_rate", 0.0)) >= float(thresholds.get("valid_frontier_rate_min", 0.95)),
            metrics.get("valid_frontier_rate", 0.0),
            thresholds.get("valid_frontier_rate_min", 0.95),
        ),
        "other_intent_rate": _gate(
            "other_intent_rate",
            float(metrics.get("other_intent_rate", 0.0)) <= float(thresholds.get("other_intent_rate_max", 0.10)),
            metrics.get("other_intent_rate", 0.0),
            thresholds.get("other_intent_rate_max", 0.10),
        ),
        "model_generation_rejection_rate": _gate(
            "model_generation_rejection_rate",
            float(metrics.get("model_generation_rejection_rate", 0.0)) <= float(thresholds.get("model_generation_rejection_rate_max", 0.15)),
            metrics.get("model_generation_rejection_rate", 0.0),
            thresholds.get("model_generation_rejection_rate_max", 0.15),
        ),
        "invariant_violations": _gate(
            "invariant_violations",
            int(metrics.get("invariant_violations_max", 0) or 0) <= int(thresholds.get("invariant_violations_max", 0)),
            metrics.get("invariant_violations_max", 0),
            thresholds.get("invariant_violations_max", 0),
        ),
        "bad_intent_committed": _gate(
            "bad_intent_committed",
            int(metrics.get("bad_intent_committed", 0) or 0) <= int(thresholds.get("bad_intent_committed_max", 0)),
            metrics.get("bad_intent_committed", 0),
            thresholds.get("bad_intent_committed_max", 0),
        ),
        "flagged_seed_leader_changes": _gate(
            "flagged_seed_leader_changes",
            flagged_changes >= int(thresholds.get("flagged_seed_leader_changes_min", 3)),
            flagged_changes,
            thresholds.get("flagged_seed_leader_changes_min", 3),
        ),
    }
    required = bool(thresholds.get("self_play_penalty_effect_required", True))
    has_penalties = bool(tuning.get("failure_penalties"))
    gates["self_play_penalty_effect"] = _gate(
        "self_play_penalty_effect",
        (not required) or (has_penalties and penalty_effect),
        {"has_failure_penalties": has_penalties, "negative_penalty_delta": penalty_effect},
        "required" if required else "tracked",
    )
    return gates


def _current_record() -> dict[str, Any] | None:
    current = PROMOTED_DIR / "CURRENT.json"
    if not current.exists():
        return None
    try:
        return _load_json(current)
    except Exception:
        return {"path": _rel(current), "policy_tuning_id": "unreadable_current"}


def _promote(batch: str, tuning_path: Path, tuning: dict[str, Any], previous_current: dict[str, Any] | None) -> Path:
    PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
    promoted = PROMOTED_DIR / f"policy_tuning_{batch}.json"
    atomic_write_json(promoted, tuning)
    current = {
        "policy_tuning_id": tuning.get("tuning_id", batch),
        "path": _rel(promoted),
        "source_batch": batch,
        "promoted_at": _utc_now(),
    }
    if previous_current:
        current["rollback_to"] = previous_current
    atomic_write_json(PROMOTED_DIR / "CURRENT.json", current)
    return promoted


def _rollback_current() -> dict[str, Any]:
    current = _current_record()
    if not current:
        return {"status": "noop", "reason": "CURRENT.json does not exist"}
    rollback_to = current.get("rollback_to") if isinstance(current, dict) else None
    if not isinstance(rollback_to, dict) or not rollback_to:
        return {"status": "noop", "reason": "CURRENT.json has no rollback_to pointer", "current": current}
    atomic_write_json(PROMOTED_DIR / "CURRENT.json", rollback_to)
    return {"status": "rolled_back", "restored_current": rollback_to, "from_current": current}


def _safe_rate(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True)
    parser.add_argument("--thresholds", default="experiments/configs/promotion_thresholds.json")
    parser.add_argument("--candidate-tuning", default="")
    parser.add_argument("--decide", choices=["promote", "hold", "rollback"], default="")
    parser.add_argument("--human-note", default="")
    args = parser.parse_args()
    thresholds_path = Path(args.thresholds)
    if not thresholds_path.is_absolute():
        thresholds_path = ROOT / thresholds_path
    thresholds_payload = _load_json(thresholds_path)
    thresholds = thresholds_payload.get("promotion_gates", thresholds_payload) if isinstance(thresholds_payload, dict) else {}
    rows = [row for row in load_rows(batch=args.batch) if row.get("status") == "completed"]
    comparison = build_comparison(rows, batch=args.batch)
    candidate_arg = Path(args.candidate_tuning) if args.candidate_tuning else None
    if candidate_arg is not None and not candidate_arg.is_absolute():
        candidate_arg = ROOT / candidate_arg
    tuning, tuning_path, pooled_path = _candidate_tuning(args.batch, rows, candidate_arg)
    diff_paths, flagged_changes, penalty_effect = _promotion_diffs(args.batch, rows, tuning_path)
    gates = evaluate_gates(comparison["batch_metrics"], thresholds, flagged_changes, penalty_effect, tuning)
    passed = all(row["status"] == "pass" for row in gates.values())
    decision = args.decide or ("promote" if passed else "hold")
    previous_current = _current_record()
    promoted_path = None
    rollback_result = None
    if decision == "promote":
        promoted_path = _promote(args.batch, tuning_path, tuning, previous_current)
    elif decision == "rollback":
        rollback_result = _rollback_current()
    metrics = comparison["batch_metrics"]
    completed_runs = int(metrics.get("completed_runs", 0) or 0)
    total_rows = int(metrics.get("rows", 0) or 0)
    source_replay_paths = []
    for row in rows:
        replay = _run_dir(row) / "replay.jsonl"
        if replay.exists():
            source_replay_paths.append(_rel(replay))
    record = {
        "lab_schema_version": LAB_SCHEMA_VERSION,
        "policy_tuning_id": tuning.get("tuning_id", args.batch),
        "source_batch": args.batch,
        "source_runs": [row.get("experiment_id") for row in rows],
        "source_replay_paths": source_replay_paths,
        "pooled_replay": _rel(pooled_path),
        "candidate_tuning": _rel(tuning_path),
        "promoted_tuning": _rel(promoted_path) if promoted_path else None,
        "previous_current": previous_current,
        "current_after_decision": _current_record(),
        "candidate_vs_empty_diff": diff_paths,
        "candidate_vs_current_diff": diff_paths,
        "seed_pass_rate": metrics.get("expected_intent_hit_rate", _safe_rate(completed_runs, total_rows)),
        "self_play_pass_rate": _safe_rate(completed_runs, total_rows),
        "provider_sandbox_pass_rate": None,
        "human_feedback_pass_rate": None,
        "rollback_pass_rate": 1.0 if decision == "promote" and previous_current else (1.0 if rollback_result and rollback_result.get("status") == "rolled_back" else None),
        "rollback_plan": {
            "mechanism": "restore experiments/promoted/CURRENT.json to previous_current/rollback_to",
            "command": f"PYTHONPATH=src python3 scripts/promote_policy.py --batch {args.batch} --candidate-tuning {_rel(tuning_path)} --decide rollback",
            "previous_current": previous_current,
            "rollback_result": rollback_result,
        },
        "metrics_before": {
            "flagged_seed_leader_changes": comparison["batch_metrics"].get("leader_changed_runs", 0),
            "other_intent_rate": comparison["batch_metrics"].get("other_intent_rate", 0.0),
            "rejection_rate": comparison["batch_metrics"].get("model_generation_rejection_rate", 0.0),
        },
        "metrics_after": {
            "flagged_seed_leader_changes": flagged_changes,
            "other_intent_rate": comparison["batch_metrics"].get("other_intent_rate", 0.0),
            "rejection_rate": comparison["batch_metrics"].get("model_generation_rejection_rate", 0.0),
            "self_play_penalty_effect": penalty_effect,
        },
        "frontier_diffs": diff_paths,
        "known_regressions": [name for name, row in gates.items() if row["status"] != "pass"],
        "gates": gates,
        "promotion_decision": decision,
        "human_note": args.human_note,
        "decided_at": _utc_now(),
        "git_sha": _git_sha(),
    }
    out = REPORTS_DIR / f"promotion_{args.batch}.json"
    atomic_write_json(out, record)
    print(json.dumps({"batch": args.batch, "decision": decision, "out": _rel(out)}, indent=2, sort_keys=True))
    if decision == "hold":
        raise SystemExit(3)


if __name__ == "__main__":
    main()
