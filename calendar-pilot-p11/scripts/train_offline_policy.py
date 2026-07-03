#!/usr/bin/env python3
"""Offline policy reducer for CalendarPilot replay.

Rows are partitioned by runtime/policy backend and reward provenance so simulator
feedback cannot silently overwhelm human UI feedback. Legacy provenance values
are mapped by ReplayBuffer.training_table().
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.taxonomy import normalize_intent
from calendar_pilot.replay import ReplayBuffer

ROOT = Path(__file__).resolve().parents[1]


def _load_training_weights() -> dict[str, float]:
    path = ROOT / "configs" / "training_weights.json"
    if not path.exists():
        return {"human_ui": 1.0, "self_play_simulator": 0.3, "synthetic_demo": 0.0, "legacy_observed": 1.0, "legacy_adversarial": 0.3, "legacy_model": 0.0}
    return {str(k): float(v) for k, v in json.loads(path.read_text(encoding="utf-8")).items()}


def _partition_key(row: dict[str, Any]) -> str:
    return f"{row.get('runtime_mode') or 'unknown'}|{row.get('policy_backend') or 'unknown'}|{row.get('reward_provenance') or 'human_ui'}"


def _empty_bucket() -> dict[str, object]:
    return {
        "count": 0,
        "weighted_count": 0.0,
        "observed_reward_sum": 0.0,
        "expected_reward_sum": 0.0,
        "denials": 0,
        "raw_intents": {},
        "supporting_records": [],
        "reward_provenance": {},
        "partitions": {},
    }


def build_policy_report(buffer: ReplayBuffer) -> dict:
    summary = buffer.summarize()
    rows = buffer.training_table()
    weights = _load_training_weights()
    intent_adjustments: dict[str, dict[str, object]] = {}
    taxonomy_counts: dict[str, int] = {}
    partition_counts: dict[str, int] = {}
    skipped_zero_weight = 0
    for row in rows:
        provenance = str(row.get("reward_provenance") or "human_ui")
        weight = float(weights.get(provenance, 1.0))
        if weight <= 0:
            skipped_zero_weight += 1
            continue
        partition = _partition_key(row)
        partition_counts[partition] = partition_counts.get(partition, 0) + 1
        normalized = normalize_intent(str(row.get("intent_raw") or row.get("intent") or "unknown"))
        intent = normalized["intent"]
        taxonomy_counts[normalized["matched_by"]] = taxonomy_counts.get(normalized["matched_by"], 0) + 1
        bucket = intent_adjustments.setdefault(intent, _empty_bucket())
        bucket["count"] = int(bucket["count"]) + 1
        bucket["weighted_count"] = float(bucket["weighted_count"]) + weight
        bucket["observed_reward_sum"] = float(bucket["observed_reward_sum"]) + float(row.get("observed_reward") or 0.0) * weight
        bucket["expected_reward_sum"] = float(bucket["expected_reward_sum"]) + float(row.get("expected_reward") or 0.0) * weight
        raw_intents = bucket.setdefault("raw_intents", {})
        if isinstance(raw_intents, dict):
            raw = str(row.get("intent_raw") or row.get("intent") or "unknown")
            raw_intents[raw] = int(raw_intents.get(raw, 0)) + 1
        provenance_bucket = bucket.setdefault("reward_provenance", {})
        if isinstance(provenance_bucket, dict):
            provenance_bucket[provenance] = int(provenance_bucket.get(provenance, 0)) + 1
        partitions = bucket.setdefault("partitions", {})
        if isinstance(partitions, dict):
            partitions[partition] = int(partitions.get(partition, 0)) + 1
        support = bucket.setdefault("supporting_records", [])
        if isinstance(support, list) and row.get("record_id"):
            support.append(str(row["record_id"]))
        if row.get("denied_reason"):
            bucket["denials"] = int(bucket["denials"]) + 1

    for bucket in intent_adjustments.values():
        count = max(1.0, float(bucket.get("weighted_count", 0.0) or 0.0))
        observed = float(bucket.pop("observed_reward_sum")) / count
        expected = float(bucket.pop("expected_reward_sum")) / count
        bucket["mean_observed_reward"] = round(observed, 4)
        bucket["mean_expected_reward"] = round(expected, 4)
        bucket["reward_residual"] = round(observed - expected, 4)
        bucket["denial_rate"] = round(int(bucket["denials"]) / max(1, int(bucket["count"])), 4)
        bucket["weighted_count"] = round(float(bucket.get("weighted_count", 0.0)), 4)
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
            "partitions": bucket.get("partitions", {}),
            "narrative": f"{bucket.get('count', 0)} rows; weighted_count={bucket.get('weighted_count', 0)}; denial_rate={denial_rate:.2f}; bias={bias:+.2f}",
        }
    total_taxonomy = max(1, sum(taxonomy_counts.values()))
    other_count = int(intent_adjustments.get("other", {}).get("count", 0)) if "other" in intent_adjustments else 0
    generated_at = datetime.now(timezone.utc).isoformat()
    policy_tuning = {
        "tuning_id": "offline_replay_v3_partitioned",
        "generated_at": generated_at,
        "intent_reward_bias": intent_reward_bias,
        "failure_penalties": failure_penalties,
        "denied_intents": sorted(denied_intents),
        "source_report": "train_offline_policy.py",
        "bias_evidence": bias_evidence,
        "taxonomy_health": {
            "other_rate": round(other_count / total_taxonomy, 4),
            "matched_by": taxonomy_counts,
        },
        "partitions": partition_counts,
        "training_weights": weights,
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
        "frontier_generations": summary.frontier_generations,
        "provider_transactions": summary.provider_transactions,
        "artifact_refs": summary.artifact_refs,
        "training_rows": len(rows),
        "skipped_zero_weight_rows": skipped_zero_weight,
        "skipped_unknown_version_rows": summary.skipped_unknown_versions,
        "partitions": partition_counts,
        "training_weights": weights,
        "recommended_next_step": "Compare policy_tuning against CURRENT with run_frontier_diff.py --baseline-tuning before promotion.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", default="runs/replay.jsonl")
    parser.add_argument("--out", default="runs/offline_policy_report.json")
    parser.add_argument("--tuning-out", default="", help="optional path for policy_tuning-only JSON")
    parser.add_argument("--append-tuning-reduction", action="store_true", help="append a tuning_reduction replay row to the input replay file")
    args = parser.parse_args()
    buffer = ReplayBuffer.load_jsonl(args.replay)
    report = build_policy_report(buffer)
    out = Path(args.out)
    atomic_write_json(out, report)
    tuning_path = Path(args.tuning_out) if args.tuning_out else None
    if tuning_path:
        atomic_write_json(tuning_path, report.get("policy_tuning", {}))
    if args.append_tuning_reduction:
        buffer.append_tuning_reduction({
            "input_replay": args.replay,
            "output_report": str(out),
            "output_tuning": str(tuning_path) if tuning_path else None,
            "partitions": report.get("partitions", {}),
            "training_weights": report.get("training_weights", {}),
            "skipped_unknown_version_rows": report.get("skipped_unknown_version_rows", 0),
        })
        buffer.save_jsonl(args.replay)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
