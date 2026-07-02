#!/usr/bin/env python3
"""Build a one-page ML scorecard from a CalendarPilot run directory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.invariants import check_replay  # noqa: E402
from calendar_pilot.environment.taxonomy import taxonomy_health  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="directory containing replay.jsonl and artifacts")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    records = load_jsonl(run_dir / "replay.jsonl")
    tuning = load_json(run_dir / "policy_tuning.json")
    diff = load_json(run_dir / "frontier_diff.json")

    by_type: dict[str, int] = {}
    for record in records:
        record_type = record.get("record_type", "unknown")
        by_type[record_type] = by_type.get(record_type, 0) + 1

    candidates = [
        record.get("payload", {}).get("candidate", {})
        for record in records
        if record.get("record_type") == "decision"
    ]
    receipts = [
        record.get("payload", {}).get("receipt", {})
        for record in records
        if record.get("record_type") == "receipt"
    ]
    findings: dict[str, int] = {}
    for record in records:
        if record.get("record_type") == "adversary_finding":
            payload = record.get("payload", {})
            label = payload.get("failure_mode") or payload.get("label") or "unknown"
            findings[label] = findings.get(label, 0) + 1

    violations = check_replay(records)
    health = taxonomy_health([candidate for candidate in candidates if candidate])
    prose_keys = [key for key in (tuning.get("intent_reward_bias") or {}) if " " in key]

    scorecard = {
        "run_id": args.run_id or run_dir.name,
        "record_counts": by_type,
        "frontier": {
            "decisions": len(candidates),
            "other_intent_rate": health["other_rate"],
            "intent_matched_by": health["matched_by"],
        },
        "acting": {
            "receipts": len(receipts),
            "committed": sum(1 for receipt in receipts if receipt.get("sync_status") == "materialized"),
            "denied": sum(1 for receipt in receipts if receipt.get("denied_reason")),
            "reverted": sum(1 for receipt in receipts if receipt.get("sync_status") == "reverted"),
        },
        "learning": {
            "replay_records": len(records),
            "tuning_generated": bool(tuning),
            "tuning_id": tuning.get("tuning_id"),
            "leader_changed": diff.get("leader_changed"),
            "canonical_intent_keys_only": not prose_keys,
            "prose_keys": prose_keys,
        },
        "self_play": {
            "episodes": by_type.get("self_play_episode", 0),
            "failure_modes": findings,
        },
        "invariants": {"violations": [violation.to_dict() for violation in violations]},
        "decision": "hold" if violations or prose_keys else "promote",
    }
    text = json.dumps(scorecard, indent=2, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
