from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import random
from typing import Protocol

from calendar_pilot.types import CandidateCalendarAction, RawCalendarObservation, RewardEvent, UserBiography
from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.swift_bridge.client import SwiftKernelStub


@dataclass
class SelfPlayMetrics:
    episodes: int = 0
    accepted: int = 0
    rejected: int = 0
    undone: int = 0
    ignored: int = 0
    total_reward: float = 0.0
    fatigue_penalty: float = 0.0
    high_regret_actions: int = 0

    @property
    def acceptance_rate(self) -> float:
        return self.accepted / self.episodes if self.episodes else 0.0

    @property
    def undo_rate(self) -> float:
        return self.undone / self.episodes if self.episodes else 0.0


class SelfPlayAdversary(Protocol):
    def mutate_score(self, candidate: CandidateCalendarAction, reward: float) -> float: ...


class ConflictAdversary:
    def mutate_score(self, candidate: CandidateCalendarAction, reward: float) -> float:
        if candidate.predicted_social_risk > 0.25:
            return reward - 1.0
        return reward


class FatigueAdversary:
    def mutate_score(self, candidate: CandidateCalendarAction, reward: float) -> float:
        if candidate.right_moment_decision.value in {"notify_now", "auto_write_then_notify"}:
            return reward - candidate.predicted_interruption_cost * 1.5
        return reward


class RegretAdversary:
    def mutate_score(self, candidate: CandidateCalendarAction, reward: float) -> float:
        if candidate.required_authority_tier >= 3 and candidate.predicted_regret > 0.15:
            return reward - 1.2
        return reward


class UserSimulator:
    def __init__(self, seed: int = 7) -> None:
        self.random = random.Random(seed)

    def respond(self, candidate: CandidateCalendarAction) -> tuple[str, float]:
        p_accept = max(0.0, min(0.95, candidate.predicted_acceptance - candidate.predicted_regret - candidate.predicted_interruption_cost * 0.2))
        roll = self.random.random()
        if candidate.intent == "do_nothing":
            return "ignored", 0.0
        if roll < p_accept:
            if self.random.random() < candidate.predicted_regret:
                return "undone", -2.0
            return "accepted", 1.0 + candidate.expected_reward
        if roll < p_accept + 0.15:
            return "ignored", -0.3
        return "rejected", -0.8


@dataclass
class SelfPlayRunner:
    policy: DiffusionGemmaPolicy = field(default_factory=DiffusionGemmaPolicy)
    kernel: SwiftKernelStub = field(default_factory=SwiftKernelStub)
    user_simulator: UserSimulator = field(default_factory=UserSimulator)
    adversaries: list[SelfPlayAdversary] = field(default_factory=lambda: [ConflictAdversary(), FatigueAdversary(), RegretAdversary()])

    def run(self, observation: RawCalendarObservation, biography: UserBiography, episodes: int = 10, authority_tier: int = 3) -> SelfPlayMetrics:
        metrics = SelfPlayMetrics()
        for _ in range(episodes):
            candidates = self.policy.generate_candidates(observation, biography)
            candidate = candidates[0]
            receipt = self.kernel.authorize_and_materialize(candidate, observation, granted_authority_tier=authority_tier)
            outcome, reward = self.user_simulator.respond(candidate)
            for adversary in self.adversaries:
                reward = adversary.mutate_score(candidate, reward)
            metrics.episodes += 1
            metrics.total_reward += reward
            if outcome == "accepted":
                metrics.accepted += 1
            elif outcome == "undone":
                metrics.undone += 1
                metrics.high_regret_actions += 1
            elif outcome == "ignored":
                metrics.ignored += 1
            else:
                metrics.rejected += 1
            if candidate.predicted_interruption_cost > 0.5:
                metrics.fatigue_penalty += candidate.predicted_interruption_cost
            _ = RewardEvent(
                reward_event_id=f"rew_{metrics.episodes}",
                receipt_id=receipt.receipt_id,
                observed_at=datetime.now(observation.observed_at.tzinfo),
                accepted=(outcome == "accepted"),
                undone=(outcome == "undone"),
                ignored=(outcome == "ignored"),
                total_reward=reward,
            )
        return metrics
