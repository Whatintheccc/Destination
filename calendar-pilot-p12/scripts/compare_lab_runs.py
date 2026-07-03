#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
import glob
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json, atomic_write_text


LAB_SCHEMA_VERSION = "lab_v0.1"
RUNS_ROOT = ROOT / "experiments" / "runs"
INDEX_PATH = ROOT / "experiments" / "index.json"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_dirs_from_globs(patterns: list[str]) -> list[Path]:
    out: set[Path] = set()
    for pattern in patterns:
        raw = Path(pattern)
        matches = glob.glob(str(raw if raw.is_absolute() else ROOT / pattern))
        for match in matches:
            path = Path(match)
            out.add(path if path.is_dir() else path.parent)
    return sorted(out)


def _discover_run_dirs() -> list[Path]:
    if not RUNS_ROOT.exists():
        return []
    return sorted(path for path in RUNS_ROOT.iterdir() if path.is_dir() and (path / "manifest.json").exists())


def _load_row(run_dir: Path) -> dict[str, Any] | None:
    manifest_path = run_dir / "manifest.json"
    report_path = run_dir / "lab_report.json"
    if not manifest_path.exists():
        return None
    manifest = _load_json(manifest_path)
    report = _load_json(report_path) if report_path.exists() else {}
    row = dict(report)
    row.setdefault("lab_schema_version", LAB_SCHEMA_VERSION)
    row.setdefault("experiment_id", manifest.get("experiment_id", run_dir.name))
    row.setdefault("batch_id", manifest.get("batch_id", "adhoc"))
    row.setdefault("seed_id", manifest.get("seed_id"))
    row.setdefault("runtime_mode", manifest.get("runtime_mode"))
    row.setdefault("policy_tuning_id", manifest.get("policy_tuning_id"))
    row.setdefault("status", manifest.get("status"))
    row.setdefault("skip_reason", manifest.get("skip_reason"))
    row["run_dir"] = _rel(run_dir)
    row["manifest"] = {
        "started_at": manifest.get("started_at"),
        "ended_at": manifest.get("ended_at"),
        "git_sha": manifest.get("git_sha"),
        "self_play_backend": manifest.get("self_play_backend"),
        "episodes": manifest.get("episodes"),
        "imported": manifest.get("imported", False),
    }
    return row


def load_rows(*, runs: list[str] | None = None, batch: str = "") -> list[dict[str, Any]]:
    run_dirs = _run_dirs_from_globs(runs) if runs else _discover_run_dirs()
    rows = [row for row in (_load_row(run_dir) for run_dir in run_dirs) if row is not None]
    if batch:
        rows = [row for row in rows if row.get("batch_id") == batch]
    return sorted(rows, key=lambda row: str(row.get("experiment_id", "")))


def pooled_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    completed = [row for row in rows if row.get("status") == "completed"]
    for row in rows:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    valid_frontiers = sum(1 for row in completed if row.get("metrics", {}).get("valid_frontier"))
    valid_candidates = sum(int(row.get("metrics", {}).get("valid_candidates", 0) or 0) for row in completed)
    rejections = sum(int(row.get("metrics", {}).get("rejections", 0) or 0) for row in completed)
    duplicate_rejections = sum(int(row.get("metrics", {}).get("duplicate_rejections", 0) or 0) for row in completed)
    generated_items = valid_candidates + rejections
    other_count = sum(int(row.get("metrics", {}).get("other_intent_count", 0) or 0) for row in completed)
    tuned_frontier_candidates = sum(
        int(row.get("metrics", {}).get("tuned_frontier_candidates", row.get("metrics", {}).get("valid_candidates", 0)) or 0)
        for row in completed
    )
    expected_rows = [row for row in completed if "expected_intent_hit" in row.get("expectation_results", {})]
    expected_hits = sum(1 for row in expected_rows if row.get("expectation_results", {}).get("expected_intent_hit"))
    bad_committed = sum(1 for row in completed if row.get("expectation_results", {}).get("bad_intent_committed"))
    return {
        "rows": len(rows),
        "completed_runs": len(completed),
        "status_counts": status_counts,
        "valid_frontier_rate": round(valid_frontiers / len(completed), 4) if completed else 0.0,
        "model_generation_rejection_rate": round(rejections / generated_items, 4) if generated_items else 0.0,
        "duplicate_candidate_rate": round(duplicate_rejections / generated_items, 4) if generated_items else 0.0,
        "other_intent_rate": round(other_count / tuned_frontier_candidates, 4) if tuned_frontier_candidates else 0.0,
        "expected_intent_hit_rate": round(expected_hits / len(expected_rows), 4) if expected_rows else 0.0,
        "bad_intent_committed": bad_committed,
        "invariant_violations_max": max([int(row.get("metrics", {}).get("invariant_violations", 0) or 0) for row in completed] or [0]),
        "leader_changed_runs": sum(1 for row in completed if row.get("metrics", {}).get("leader_changed_after_tuning")),
        "valid_candidates": valid_candidates,
        "rejections": rejections,
    }


def group_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("seed_id", "")), str(row.get("runtime_mode", "")))].append(row)
    out: list[dict[str, Any]] = []
    for (seed_id, runtime), group in sorted(groups.items()):
        metrics = pooled_metrics(group)
        latest = sorted(group, key=lambda row: str(row.get("experiment_id", "")))[-1]
        out.append({
            "seed_id": seed_id,
            "runtime_mode": runtime,
            "runs": len(group),
            "latest_experiment_id": latest.get("experiment_id"),
            "latest_status": latest.get("status"),
            "latest_skip_reason": latest.get("skip_reason"),
            "metrics": metrics,
        })
    return out


def rankings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("runtime_mode", ""))].append(row)
    out = []
    for runtime, group in groups.items():
        metrics = pooled_metrics(group)
        out.append({
            "runtime_mode": runtime,
            "valid_frontier_rate": metrics["valid_frontier_rate"],
            "other_intent_rate": metrics["other_intent_rate"],
            "rejection_rate": metrics["model_generation_rejection_rate"],
            "completed_runs": metrics["completed_runs"],
        })
    return sorted(out, key=lambda row: (-row["valid_frontier_rate"], row["other_intent_rate"], row["rejection_rate"], row["runtime_mode"]))


def build_comparison(rows: list[dict[str, Any]], *, batch: str = "") -> dict[str, Any]:
    return {
        "lab_schema_version": LAB_SCHEMA_VERSION,
        "batch_id": batch or "all",
        "rows": rows,
        "groups": group_rows(rows),
        "batch_metrics": pooled_metrics(rows),
        "missed_expected_intents": [
            {
                "experiment_id": row.get("experiment_id"),
                "seed_id": row.get("seed_id"),
                "runtime_mode": row.get("runtime_mode"),
                "detail": row.get("expectation_results", {}).get("expected_intent_hit_detail"),
            }
            for row in rows
            if row.get("status") == "completed" and not row.get("expectation_results", {}).get("expected_intent_hit", True)
        ],
        "leader_changed_runs": [
            {
                "experiment_id": row.get("experiment_id"),
                "seed_id": row.get("seed_id"),
                "runtime_mode": row.get("runtime_mode"),
            }
            for row in rows
            if row.get("status") == "completed" and row.get("metrics", {}).get("leader_changed_after_tuning")
        ],
        "config_rankings": rankings(rows),
    }


def write_index(rows: list[dict[str, Any]]) -> None:
    payload = {
        "lab_schema_version": LAB_SCHEMA_VERSION,
        "runs": rows,
        "batch_metrics": pooled_metrics(rows),
    }
    atomic_write_json(INDEX_PATH, payload)


def write_markdown(path: Path, comparison: dict[str, Any]) -> None:
    lines = [
        "| seed_id | runtime | runs | latest | status | valid_frontier_rate | other_intent_rate | rejection_rate |",
        "|---|---:|---:|---|---|---:|---:|---:|",
    ]
    for group in comparison.get("groups", []):
        metrics = group["metrics"]
        lines.append(
            "| {seed} | {runtime} | {runs} | {latest} | {status} | {valid:.2f} | {other:.2f} | {reject:.2f} |".format(
                seed=group["seed_id"],
                runtime=group["runtime_mode"],
                runs=group["runs"],
                latest=group["latest_experiment_id"],
                status=group["latest_status"],
                valid=metrics["valid_frontier_rate"],
                other=metrics["other_intent_rate"],
                reject=metrics["model_generation_rejection_rate"],
            )
        )
    atomic_write_text(path, "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="*", default=None)
    parser.add_argument("--batch", default="")
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--out", default="experiments/reports/comparison_latest.json")
    parser.add_argument("--md", default="")
    args = parser.parse_args()
    all_rows = load_rows()
    if args.reindex:
        write_index(all_rows)
    selected = load_rows(runs=args.runs, batch=args.batch)
    comparison = build_comparison(selected, batch=args.batch)
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    atomic_write_json(out_path, comparison)
    if args.md:
        md_path = Path(args.md)
        if not md_path.is_absolute():
            md_path = ROOT / md_path
        write_markdown(md_path, comparison)
    print(json.dumps({"rows": len(selected), "out": _rel(out_path), "reindexed": bool(args.reindex)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()