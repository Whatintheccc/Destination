#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from statistics import mean
from typing import Any

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.reward import RewardModel, RewardWeights
from calendar_pilot.diffusiongemma.signals import CalendarSignals
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.taxonomy import taxonomy_health
from calendar_pilot.types import PolicyTuning, RawCalendarObservation, RightMomentDecision, UserBiography

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _resolve_current_tuning() -> Path | None:
    current = ROOT / "experiments" / "promoted" / "CURRENT.json"
    if not current.exists():
        return None
    try:
        payload = _load_json(current)
    except Exception:
        return current
    if isinstance(payload, dict) and payload.get("path"):
        p = Path(str(payload["path"]))
        return p if p.is_absolute() else ROOT / p
    return current


def _load_tuning(path: Path | None, *, empty_id: str) -> PolicyTuning:
    return PolicyTuning.from_dict(_load_json(path)) if path and path.exists() else PolicyTuning(tuning_id=empty_id)


def _frontier(policy: DiffusionGemmaPolicy, observation: RawCalendarObservation, biography: UserBiography, goal: str) -> list[dict]:
    return [candidate.to_dict() for candidate in policy.generate_candidates(observation, biography, goal=goal)]


class NeutralRightMomentModel:
    def decide(self, candidate, observation, biography, signals=None):
        candidate.right_moment_decision = RightMomentDecision.WAIT if candidate.intent != "do_nothing" else RightMomentDecision.DO_NOTHING
        candidate.recommended_execution_time = observation.observed_at
        candidate.right_moment_score = 0.0
        candidate.control_notes.append("right_moment_ablation=neutral_timing")
        return candidate


def _neutral_signals(observation: RawCalendarObservation, biography: UserBiography) -> CalendarSignals:
    return CalendarSignals(
        external_meeting_count=0,
        internal_meeting_count=0,
        flexible_hold_count=0,
        admin_task_minutes=0,
        prep_task_minutes=0,
        occupied_minutes_workday=0,
        open_slots=[],
        pressure_score=0.0,
        fatigue_score=0.0,
        best_response_is_now=False,
        active_surface=observation.device_context.active_surface,
        risk_cliffs=[],
        narrative=["derived signal ablation: signal extractor returned a neutral signal set"],
    )


def _ablate_tuning(tuning: PolicyTuning, ablation: str) -> PolicyTuning:
    if ablation == "no_intent_reward_bias":
        return replace(tuning, intent_reward_bias={})
    if ablation == "no_failure_penalties":
        return replace(tuning, failure_penalties={})
    if ablation == "no_denied_intents":
        return replace(tuning, denied_intents=[])
    return tuning


def _ablate_biography(biography: UserBiography, ablation: str) -> UserBiography:
    if ablation == "no_semantic_labels":
        return replace(biography, preference_claims=[], biography_claims=[])
    return biography


def _policy_for(tuning: PolicyTuning, ablation: str = "") -> DiffusionGemmaPolicy:
    reward_model = None
    right_moment = None
    normalize_intents = True
    signal_extractor = None
    if ablation == "no_provider_penalties":
        reward_model = RewardModel(RewardWeights(authority_cost=0.0, social_risk=0.0))
    if ablation == "no_right_moment_tuning":
        right_moment = NeutralRightMomentModel()
    if ablation == "no_taxonomy_normalization":
        normalize_intents = False
    if ablation == "no_derived_signals":
        signal_extractor = _neutral_signals
    kwargs = {
        "policy_tuning": _ablate_tuning(tuning, ablation),
        "normalize_intents": normalize_intents,
    }
    if reward_model is not None:
        kwargs["reward_model"] = reward_model
    if right_moment is not None:
        kwargs["right_moment"] = right_moment
    if signal_extractor is not None:
        kwargs["signal_extractor"] = signal_extractor
    return DiffusionGemmaPolicy(**kwargs)


def _deltas(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, Any]:
    before_by_id = {c["candidate_id"]: c for c in before}
    after_by_id = {c["candidate_id"]: c for c in after}
    ids = sorted(set(before_by_id) | set(after_by_id))
    deltas = {}
    for cid in ids:
        b = before_by_id.get(cid, {})
        a = after_by_id.get(cid, {})
        deltas[cid] = {
            "intent": a.get("intent") or b.get("intent"),
            "before_reward": b.get("expected_reward"),
            "after_reward": a.get("expected_reward"),
            "delta": None if not b or not a else round(float(a.get("expected_reward", 0.0)) - float(b.get("expected_reward", 0.0)), 4),
            "before_rank": next((i + 1 for i, c in enumerate(before) if c["candidate_id"] == cid), None),
            "after_rank": next((i + 1 for i, c in enumerate(after) if c["candidate_id"] == cid), None),
        }
    return deltas


def build_diff(*, observation_path: Path, profile_path: Path, tuning_path: Path | None, goal: str, baseline_tuning_path: Path | None = None, ablation: str = "") -> dict:
    observation = RawCalendarObservation.from_dict(_load_json(observation_path))
    biography = UserBiography.from_dict(_load_json(profile_path))
    empty = _frontier(DiffusionGemmaPolicy(), observation, biography, goal)
    baseline_tuning = _load_tuning(baseline_tuning_path, empty_id="empty")
    tuning = _load_tuning(tuning_path, empty_id="empty")
    if ablation:
        baseline = _frontier(_policy_for(tuning), observation, biography, goal)
        ablated_biography = _ablate_biography(biography, ablation)
        tuned = _frontier(_policy_for(tuning, ablation), observation, ablated_biography, goal)
        baseline_tuning_id = tuning.tuning_id
        tuning_id = f"{tuning.tuning_id}:{ablation}"
    else:
        baseline = _frontier(_policy_for(baseline_tuning), observation, biography, goal)
        tuned = _frontier(_policy_for(tuning), observation, biography, goal)
        baseline_tuning_id = baseline_tuning.tuning_id
        tuning_id = tuning.tuning_id
    vs_empty = _deltas(empty, tuned)
    marginal = _deltas(baseline, tuned)
    return {
        "goal": goal,
        "observation_id": observation.observation_id,
        "baseline_tuning_id": baseline_tuning_id,
        "tuning_id": tuning_id,
        "ablation": ablation or None,
        "ablation_applied": bool(ablation),
        "untuned_leader": empty[0]["candidate_id"] if empty else None,
        "baseline_leader": baseline[0]["candidate_id"] if baseline else None,
        "tuned_leader": tuned[0]["candidate_id"] if tuned else None,
        "leader_changed": bool(empty and tuned and empty[0]["candidate_id"] != tuned[0]["candidate_id"]),
        "marginal_leader_changed": bool(baseline and tuned and baseline[0]["candidate_id"] != tuned[0]["candidate_id"]),
        "untuned_top_intent": empty[0]["intent"] if empty else None,
        "baseline_top_intent": baseline[0]["intent"] if baseline else None,
        "tuned_top_intent": tuned[0]["intent"] if tuned else None,
        "avg_reward_delta": round(mean([v["delta"] for v in vs_empty.values() if v["delta"] is not None] or [0.0]), 4),
        "avg_marginal_reward_delta": round(mean([v["delta"] for v in marginal.values() if v["delta"] is not None] or [0.0]), 4),
        "taxonomy_health": taxonomy_health(tuned),
        "per_candidate_delta": vs_empty,
        "per_candidate_marginal_delta": marginal,
        "untuned_frontier": empty,
        "baseline_frontier": baseline,
        "tuned_frontier": tuned,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", default="data/sample_calendar.json")
    parser.add_argument("--profile", default="data/sample_profile.json")
    parser.add_argument("--tuning", default="", help="candidate policy_tuning JSON. Empty means compare against empty tuning.")
    parser.add_argument("--baseline-tuning", default="", help="baseline policy_tuning JSON. Default: experiments/promoted/CURRENT.json target if present, else empty.")
    parser.add_argument("--goal", default="Make next week less chaotic")
    parser.add_argument("--ablation", default="", help="optional policy component to disable for an ablation frontier diff")
    parser.add_argument("--out", default="runs/frontier_diff.json")
    args = parser.parse_args()
    baseline = Path(args.baseline_tuning) if args.baseline_tuning else _resolve_current_tuning()
    diff = build_diff(
        observation_path=Path(args.observation),
        profile_path=Path(args.profile),
        tuning_path=Path(args.tuning) if args.tuning else None,
        baseline_tuning_path=baseline,
        goal=args.goal,
        ablation=args.ablation,
    )
    atomic_write_json(Path(args.out), diff)
    print(json.dumps(diff, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
