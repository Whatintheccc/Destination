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

    @classmethod
    def from_json(cls, path: str | Path) -> "RewardWeights":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class RewardModel:
    """Reference reward model with separate visible reward heads.

    This is intentionally simple: in production, replace this class with a model
    serving client while preserving the head decomposition in CandidateCalendarAction.
    """

    def __init__(self, weights: RewardWeights | None = None) -> None:
        self.weights = weights or RewardWeights()

    def score(self, candidate: CandidateCalendarAction) -> float:
        w = self.weights
        score = (
            w.acceptance * candidate.predicted_acceptance
            + w.utility * candidate.predicted_utility
            + w.engagement * candidate.predicted_engagement
            + w.long_horizon * candidate.predicted_long_horizon_value
            + w.regret * candidate.predicted_regret
            + w.interruption * candidate.predicted_interruption_cost
            + w.social_risk * candidate.predicted_social_risk
        )
        candidate.expected_reward = round(score, 4)
        return candidate.expected_reward

    def reward_from_event(self, event: RewardEvent) -> float:
        w = self.weights
        total = event.total_reward
        if event.undone:
            total += w.undo
        if event.ignored:
            total += w.ignored
        if event.explicit_wrong:
            total += w.explicit_wrong
        return round(total, 4)
