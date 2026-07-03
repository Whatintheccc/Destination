

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from calendar_pilot.types import CandidateCalendarAction, RewardEvent


@dataclass(frozen=True)
class RewardWeights:
    acceptance: float = 1.0
    utility: float = 1.2
    engagement: float = 0.25
    long_horizon: float = 0.8
    regret: float = -2.0
    interruption: float = -0.7
    social_risk: float = -1.5
    undo: float = -2.5
    ignored: float = -0.4
    explicit_wrong: float = -3.0
    authority_cost: float = -0.18
    reversibility_bonus: float = 0.22
    narrative_bonus: float = 0.06

    @classmethod
    def from_json(cls, path: str | Path) -> "RewardWeights":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class RewardModel:
    """Visible multi-head reward model for the agentic optimizer.

    The first repo collapsed the policy into a single dry scalar. This revision
    still returns a scalar for ranking, but it leaves the anatomy attached to the
    candidate so self-play, Codex, and offline training can argue about the same
    decision without reverse-engineering it.
    """

    def __init__(self, weights: RewardWeights | None = None) -> None:
        self.weights = weights or RewardWeights()

    def score(self, candidate: CandidateCalendarAction) -> float:
        w = self.weights
        breakdown = {
            "acceptance": w.acceptance * candidate.predicted_acceptance,
            "utility": w.utility * candidate.predicted_utility,
            "engagement": w.engagement * candidate.predicted_engagement,
            "long_horizon": w.long_horizon * candidate.predicted_long_horizon_value,
            "regret": w.regret * candidate.predicted_regret,
            "interruption": w.interruption * candidate.predicted_interruption_cost,
            "social_risk": w.social_risk * candidate.predicted_social_risk,
            "authority_cost": w.authority_cost * max(0, candidate.required_authority_tier - 2),
            "reversibility": w.reversibility_bonus * _reversibility_factor(candidate),
            "model_story": w.narrative_bonus * min(3, len(candidate.model_story)),
        }
        score = round(sum(breakdown.values()), 4)
        candidate.reward_breakdown = {k: round(v, 4) for k, v in breakdown.items()}
        candidate.expected_reward = score
        return score

    def reward_from_event(self, event: RewardEvent) -> float:
        w = self.weights
        total = event.total_reward
        if event.undone:
            total += w.undo
        if event.ignored:
            total += w.ignored
        if event.explicit_wrong:
            total += w.explicit_wrong
        if event.notification_dismissed:
            total += w.interruption
        return round(total, 4)

    @staticmethod
    def top_positive_heads(candidate: CandidateCalendarAction, n: int = 3) -> list[str]:
        heads = sorted(candidate.reward_breakdown.items(), key=lambda kv: kv[1], reverse=True)
        return [f"{k} {v:+.2f}" for k, v in heads[:n] if v > 0]

    @staticmethod
    def top_negative_heads(candidate: CandidateCalendarAction, n: int = 3) -> list[str]:
        heads = sorted(candidate.reward_breakdown.items(), key=lambda kv: kv[1])
        return [f"{k} {v:+.2f}" for k, v in heads[:n] if v < 0]


def _reversibility_factor(candidate: CandidateCalendarAction) -> float:
    return {
        "none": -1.0,
        "low": 0.0,
        "medium": 0.5,
        "high": 1.0,
    }.get(candidate.reversibility.value, 0.0)