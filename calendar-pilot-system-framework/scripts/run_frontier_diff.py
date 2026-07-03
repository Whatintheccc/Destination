#!/usr/bin/env python3
"""Deterministic A/B frontier diff: heuristic policy with and without tuning."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy  # noqa: E402
from calendar_pilot.environment.taxonomy import taxonomy_health  # noqa: E402
from calendar_pilot.types import PolicyTuning, RawCalendarObservation, UserBiography  # noqa: E402


def frontier(policy: DiffusionGemmaPolicy, observation, biography) -> list[dict]:
    rows = []
    for candidate in policy.generate_candidates(observation, biography):
        rows.append({
            "candidate_id": candidate.candidate_id,
            "intent": candidate.intent,
            "intent_raw": candidate.intent_raw,
            "intent_matched_by": candidate.intent_matched_by,
            "expected_reward": round(float(candidate.expected_reward), 4),
            "predicted_regret": round(float(candidate.predicted_regret), 4),
            "predicted_social_risk": round(float(candidate.predicted_social_risk), 4),
            "predicted_interruption_cost": round(float(candidate.predicted_interruption_cost), 4),
            "right_moment_decision": getattr(candidate.right_moment_decision, "value", str(candidate.right_moment_decision)),
        })
    return rows


def _avg(rows: list[dict], key: str) -> float:
    return round(sum(float(row[key]) for row in rows) / max(1, len(rows)), 4)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", default="data/sample_calendar.json")
    parser.add_argument("--profile", default="data/sample_profile.json")
    parser.add_argument("--tuning", required=True, help="policy_tuning.json from train_offline_policy.py")
    parser.add_argument("--out", default="runs/frontier_diff/frontier_diff.json")
    args = parser.parse_args()

    observation = RawCalendarObservation.from_dict(json.loads(Path(args.observation).read_text(encoding="utf-8")))
    biography = UserBiography.from_dict(json.loads(Path(args.profile).read_text(encoding="utf-8")))
    tuning = PolicyTuning.from_dict(json.loads(Path(args.tuning).read_text(encoding="utf-8")))

    untuned = frontier(DiffusionGemmaPolicy(), observation, biography)
    tuned = frontier(DiffusionGemmaPolicy(policy_tuning=tuning), observation, biography)
    base = {candidate["candidate_id"]: candidate for candidate in untuned}
    diff = {
        "tuning_id": tuning.tuning_id,
        "untuned_leader": untuned[0]["candidate_id"] if untuned else None,
        "tuned_leader": tuned[0]["candidate_id"] if tuned else None,
        "leader_changed": bool(untuned and tuned and untuned[0]["candidate_id"] != tuned[0]["candidate_id"]),
        "top3_untuned": [candidate["candidate_id"] for candidate in untuned[:3]],
        "top3_tuned": [candidate["candidate_id"] for candidate in tuned[:3]],
        "per_candidate_delta": {
            candidate["candidate_id"]: round(candidate["expected_reward"] - base[candidate["candidate_id"]]["expected_reward"], 4)
            for candidate in tuned
            if candidate["candidate_id"] in base
        },
        "avg_predicted_regret": {"untuned": _avg(untuned, "predicted_regret"), "tuned": _avg(tuned, "predicted_regret")},
        "avg_predicted_social_risk": {"untuned": _avg(untuned, "predicted_social_risk"), "tuned": _avg(tuned, "predicted_social_risk")},
        "avg_predicted_interruption_cost": {
            "untuned": _avg(untuned, "predicted_interruption_cost"),
            "tuned": _avg(tuned, "predicted_interruption_cost"),
        },
        "taxonomy_health": {
            "untuned": taxonomy_health(untuned),
            "tuned": taxonomy_health(tuned),
        },
        "frontier_untuned": untuned,
        "frontier_tuned": tuned,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(diff, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({key: diff[key] for key in ("tuning_id", "untuned_leader", "tuned_leader", "leader_changed")}, indent=2))


if __name__ == "__main__":
    main()

