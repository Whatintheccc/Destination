#!/usr/bin/env python3
"""Offline policy reducer for CalendarPilot replay.

The reducer is deliberately small, but the key is now stable: reward residuals
bucket by canonical intent rather than model-written prose, so signal can
accumulate across daily dogfood runs.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.taxonomy import normalize_intent
from calendar_pilot.replay import ReplayBuffer


def build_policy_report(buffer: ReplayBuffer) -> dict:
    summary = buffer.summarize()
    rows = buffer.training_table()
    intent_adjustments: dict[str, dict[str, object]] = {}
    taxonomy_counts: dict[str, int] = {}
    for row in rows:
        normalized = normalize_intent(str(row.get("intent_raw") or row.get("intent") or "unknown"))
        intent = normalized["intent"]
        taxonomy_counts[normalized["matched_by"]] = taxonomy_counts.get(normalized["matched_by"], 0) + 1
        bucket = intent_adjustments.setdefault(intent, {
            "count": 0,
            "observed_reward_sum": 0.0,
            "expected_reward_sum": 0.0,
            "denials": 0,
            "raw_intents": {},
            "supporting_records": [],
            "reward_provenance": {},
        })
        bucket["count"] = int(bucket["count"]) + 1
        bucket["observed_reward_sum"] = float(bucket["observed_reward_sum"]) + float(row.get("observed_reward") or 0.0)
        bucket["expected_reward_sum"] = float(bucket["expected_reward_sum"]) + float(row.get("expected_reward") or 0.0)
        raw_intents = bucket.setdefault("raw_intents", {})
        if isinstance(raw_intents, dict):
            raw = str(row.get("intent_raw") or row.get("intent") or "unknown")
            raw_intents[raw] = int(raw_intents.get(raw, 0)) + 1
        provenance = bucket.setdefault("reward_provenance", {})
        if isinstance(provenance, dict):
            key = str(row.get("reward_provenance") or "observed")
            provenance[key] = int(provenance.get(key, 0)) + 1
        support = bucket.setdefault("supporting_records", [])
        if isinstance(support, list) and row.get("record_id"):
            support.append(str(row["record_id"]))
        if row.get("denied_reason"):
            bucket["denials"] = int(bucket["denials"]) + 1

    for bucket in intent_adjustments.values():
        count = max(1, int(bucket["count"]))
        observed = float(bucket.pop("observed_reward_sum")) / count
        expected = float(bucket.pop("expected_reward_sum")) / count
        bucket["mean_observed_reward"] = round(observed, 4)
        bucket["mean_expected_reward"] = round(expected, 4)
        bucket["reward_residual"] = round(observed - expected, 4)
        bucket["denial_rate"] = round(int(bucket["denials"]) / count, 4)
        if isinstance(bucket.get("supporting_records"), list):
            bucket["supporting_records"] = bucket["supporting_records"][:25]

    failure_penalties = {
        label: round(-0.08 * count, 4)
        for label, count in sorted(summary.failure_modes.items())
    }
    intent_reward_bias: dict[str, float] = {}
    denied_intents: list[str] = []
    bias_evidence: dict[str, dict[str, object]] = {}
    for intent, bucket in intent_adjustments.items():
        residual = float(bucket.get("reward_residual", 0.0))
        denial_rate = float(bucket.get("denial_rate", 0.0))
        bias = round(max(-0.8, min(0.8, residual * 0.25)), 4)
        intent_reward_bias[intent] = bias
        if denial_rate >= 0.5:
            denied_intents.append(intent)
        bias_evidence[intent] = {
            "reward_residual": residual,
            "supporting_records": bucket.get("supporting_records", []),
            "raw_intents": bucket.get("raw_intents", {}),
            "reward_provenance": bucket.get("reward_provenance", {}),
            "narrative": f"{bucket.get('count', 0)} rows; denial_rate={denial_rate:.2f}; bias={bias:+.2f}",
        }
    total_taxonomy = max(1, sum(taxonomy_counts.values()))
    other_count = int(intent_adjustments.get("other", {}).get("count", 0)) if "other" in intent_adjustments else 0
    policy_tuning = {
        "tuning_id": "offline_replay_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intent_reward_bias": intent_reward_bias,
        "failure_penalties": failure_penalties,
        "denied_intents": sorted(denied_intents),
        "source_report": "train_offline_policy.py",
        "bias_evidence": bias_evidence,
        "taxonomy_health": {
            "other_rate": round(other_count / total_taxonomy, 4),
            "matched_by": taxonomy_counts,
        },
    }
    return {
        "records": summary.records,
        "decisions": summary.decisions,
        "receipts": summary.receipts,
        "rewards": summary.rewards,
        "episodes": summary.episodes,
        "average_reward": summary.average_reward,
        "denials": summary.denials,
        "intent_adjustments": intent_adjustments,
        "failure_penalties": failure_penalties,
        "policy_tuning": policy_tuning,
        "tool_calls": summary.tool_calls,
        "tool_receipts": summary.tool_receipts,
        "router_decisions": summary.router_decisions,
        "model_generation_rejections": summary.model_generation_rejections,
        "envelope_transitions": summary.envelope_transitions,
        "training_rows": len(rows),
        "recommended_next_step": "Use policy_tuning as DiffusionGemmaPolicy(policy_tuning=PolicyTuning.from_dict(...)); watch taxonomy OTHER-rate before autonomy promotion.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", default="runs/replay.jsonl")
    parser.add_argument("--out", default="runs/offline_policy_report.json")
    parser.add_argument("--tuning-out", default="", help="optional path for policy_tuning-only JSON")
    args = parser.parse_args()
    buffer = ReplayBuffer.load_jsonl(args.replay)
    report = build_policy_report(buffer)
    out = Path(args.out)
    atomic_write_json(out, report)
    if args.tuning_out:
        atomic_write_json(Path(args.tuning_out), report.get("policy_tuning", {}))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
