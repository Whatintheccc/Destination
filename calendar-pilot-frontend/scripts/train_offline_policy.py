#!/usr/bin/env python3
"""Offline policy reducer for CalendarPilot replay.

This is still a reference trainer, not a neural fine-tune. It now consumes the
same replay records emitted by self-play: candidate decisions, Swift receipts,
reward events, denial receipts, and adversary findings. The output is a small
policy report that a real DiffusionGemma training job could consume as weights,
DPO pairs, or curriculum filters.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from calendar_pilot.replay import ReplayBuffer


def build_policy_report(buffer: ReplayBuffer) -> dict:
    summary = buffer.summarize()
    rows = buffer.training_table()
    intent_adjustments: dict[str, dict[str, float | int]] = {}
    for row in rows:
        intent = row.get("intent") or "unknown"
        bucket = intent_adjustments.setdefault(intent, {"count": 0, "observed_reward_sum": 0.0, "expected_reward_sum": 0.0, "denials": 0})
        bucket["count"] = int(bucket["count"]) + 1
        bucket["observed_reward_sum"] = float(bucket["observed_reward_sum"]) + float(row.get("observed_reward") or 0.0)
        bucket["expected_reward_sum"] = float(bucket["expected_reward_sum"]) + float(row.get("expected_reward") or 0.0)
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

    failure_penalties = {
        label: round(-0.08 * count, 4)
        for label, count in sorted(summary.failure_modes.items())
    }
    intent_reward_bias = {}
    denied_intents = []
    for intent, bucket in intent_adjustments.items():
        residual = float(bucket.get("reward_residual", 0.0))
        denial_rate = float(bucket.get("denial_rate", 0.0))
        intent_reward_bias[intent] = round(max(-0.8, min(0.8, residual * 0.25)), 4)
        if denial_rate >= 0.5:
            denied_intents.append(intent)
    policy_tuning = {
        "tuning_id": "offline_replay_v1",
        "intent_reward_bias": intent_reward_bias,
        "failure_penalties": failure_penalties,
        "denied_intents": sorted(denied_intents),
        "source_report": "train_offline_policy.py",
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
        "training_rows": len(rows),
        "recommended_next_step": "Use policy_tuning as DiffusionGemmaPolicy(policy_tuning=PolicyTuning.from_dict(...)); filter high denial_rate intents before auto-write rollout.",
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
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.tuning_out:
        tuning_out = Path(args.tuning_out)
        tuning_out.parent.mkdir(parents=True, exist_ok=True)
        tuning_out.write_text(json.dumps(report.get("policy_tuning", {}), indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
