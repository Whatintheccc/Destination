#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.invariants import check_replay
from calendar_pilot.replay import ReplayBuffer


def _load_optional(path: str) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def build_scorecard(*, replay_path: Path, frontier_diff: dict[str, Any], offline_report: dict[str, Any]) -> dict[str, Any]:
    buffer = ReplayBuffer.load_jsonl(replay_path) if replay_path.exists() else ReplayBuffer()
    summary = buffer.summarize()
    records = [json.loads(line) for line in replay_path.read_text(encoding="utf-8").splitlines() if line.strip()] if replay_path.exists() else []
    violations = [v.to_dict() for v in check_replay(records)]
    taxonomy = frontier_diff.get("taxonomy_health") or offline_report.get("policy_tuning", {}).get("taxonomy_health", {})
    return {
        "run_id": replay_path.parent.name or "scorecard",
        "replay_path": str(replay_path),
        "frontier": {
            "valid_candidates": len(frontier_diff.get("tuned_frontier", [])),
            "leader_changed": bool(frontier_diff.get("leader_changed")),
            "other_intent_rate": taxonomy.get("other_rate", 0.0),
            "taxonomy_health": taxonomy,
        },
        "acting": {
            "receipts": summary.receipts,
            "denials": summary.denials,
            "envelope_transitions": summary.envelope_transitions,
        },
        "learning": {
            "records": summary.records,
            "training_rows": offline_report.get("training_rows", 0),
            "tuning_generated": bool(offline_report.get("policy_tuning")),
            "canonical_intent_keys_only": all(" " not in key for key in (offline_report.get("policy_tuning", {}).get("intent_reward_bias", {}) or {})),
        },
        "self_play": {
            "episodes": summary.episodes,
            "failure_modes": summary.failure_modes,
            "average_reward": summary.average_reward,
        },
        "invariants": {"violations": len(violations), "details": violations},
        "decision": "hold" if violations else "promote_candidate",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", default="runs/replay.jsonl")
    parser.add_argument("--frontier-diff", default="runs/frontier_diff.json")
    parser.add_argument("--offline-report", default="runs/offline_policy_report.json")
    parser.add_argument("--out", default="runs/ml_scorecard.json")
    args = parser.parse_args()
    scorecard = build_scorecard(
        replay_path=Path(args.replay),
        frontier_diff=_load_optional(args.frontier_diff),
        offline_report=_load_optional(args.offline_report),
    )
    atomic_write_json(Path(args.out), scorecard)
    print(json.dumps(scorecard, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
