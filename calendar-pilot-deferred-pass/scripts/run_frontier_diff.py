#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.taxonomy import taxonomy_health
from calendar_pilot.types import PolicyTuning, RawCalendarObservation, UserBiography


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _frontier(policy: DiffusionGemmaPolicy, observation: RawCalendarObservation, biography: UserBiography, goal: str) -> list[dict]:
    return [candidate.to_dict() for candidate in policy.generate_candidates(observation, biography, goal=goal)]


def build_diff(*, observation_path: Path, profile_path: Path, tuning_path: Path | None, goal: str) -> dict:
    observation = RawCalendarObservation.from_dict(_load_json(observation_path))
    biography = UserBiography.from_dict(_load_json(profile_path))
    untuned = _frontier(DiffusionGemmaPolicy(), observation, biography, goal)
    tuning = PolicyTuning.from_dict(_load_json(tuning_path)) if tuning_path and tuning_path.exists() else PolicyTuning(tuning_id="empty")
    tuned = _frontier(DiffusionGemmaPolicy(policy_tuning=tuning), observation, biography, goal)
    untuned_by_id = {c["candidate_id"]: c for c in untuned}
    tuned_by_id = {c["candidate_id"]: c for c in tuned}
    ids = sorted(set(untuned_by_id) | set(tuned_by_id))
    deltas = {}
    for cid in ids:
        before = untuned_by_id.get(cid, {})
        after = tuned_by_id.get(cid, {})
        deltas[cid] = {
            "intent": after.get("intent") or before.get("intent"),
            "before_reward": before.get("expected_reward"),
            "after_reward": after.get("expected_reward"),
            "delta": None if not before or not after else round(float(after.get("expected_reward", 0.0)) - float(before.get("expected_reward", 0.0)), 4),
            "before_rank": next((i + 1 for i, c in enumerate(untuned) if c["candidate_id"] == cid), None),
            "after_rank": next((i + 1 for i, c in enumerate(tuned) if c["candidate_id"] == cid), None),
        }
    return {
        "goal": goal,
        "observation_id": observation.observation_id,
        "tuning_id": tuning.tuning_id,
        "untuned_leader": untuned[0]["candidate_id"] if untuned else None,
        "tuned_leader": tuned[0]["candidate_id"] if tuned else None,
        "leader_changed": bool(untuned and tuned and untuned[0]["candidate_id"] != tuned[0]["candidate_id"]),
        "untuned_top_intent": untuned[0]["intent"] if untuned else None,
        "tuned_top_intent": tuned[0]["intent"] if tuned else None,
        "avg_reward_delta": round(mean([v["delta"] for v in deltas.values() if v["delta"] is not None] or [0.0]), 4),
        "taxonomy_health": taxonomy_health(tuned),
        "per_candidate_delta": deltas,
        "untuned_frontier": untuned,
        "tuned_frontier": tuned,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", default="data/sample_calendar.json")
    parser.add_argument("--profile", default="data/sample_profile.json")
    parser.add_argument("--tuning", default="", help="policy_tuning JSON. Empty means compare against empty tuning.")
    parser.add_argument("--goal", default="Make next week less chaotic")
    parser.add_argument("--out", default="runs/frontier_diff.json")
    args = parser.parse_args()
    diff = build_diff(
        observation_path=Path(args.observation),
        profile_path=Path(args.profile),
        tuning_path=Path(args.tuning) if args.tuning else None,
        goal=args.goal,
    )
    atomic_write_json(Path(args.out), diff)
    print(json.dumps(diff, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
