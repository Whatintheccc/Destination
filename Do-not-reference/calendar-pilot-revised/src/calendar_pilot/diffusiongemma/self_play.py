from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import random
from typing import Protocol

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.types import CandidateCalendarAction, RawCalendarObservation, RewardEvent, UserBiography


@dataclass(frozen=True)
class SimulatedResponse:
    outcome: str
    reward: float
    reason: str


@dataclass(frozen=True)
class AdversaryFinding:
    name: str
    reward_delta: float
    label: str
    note: str


@dataclass(frozen=True)
class SelfPlayEpisode:
    episode_index: int
    chosen_candidate_id: str
    chosen_intent: str
    baseline_candidate_id: str
    outcome: str
    reward_before_adversaries: float
    reward_after_adversaries: float
    findings: list[AdversaryFinding]
    response_reason: str


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
    adversarial_delta: float = 0.0
    failure_modes: dict[str, int] = field(default_factory=dict)
    chosen_intents: dict[str, int] = field(default_factory=dict)
    episode_log: list[SelfPlayEpisode] = field(default_factory=list)

    @property
    def acceptance_rate(self) -> float:
        return self.accepted / self.episodes if self.episodes else 0.0

    @property
    def undo_rate(self) -> float:
        return self.undone / self.episodes if self.episodes else 0.0

    @property
    def average_reward(self) -> float:
        return self.total_reward / self.episodes if self.episodes else 0.0

    @property
    def top_failure_modes(self) -> list[str]:
        return [f"{name}:{count}" for name, count in sorted(self.failure_modes.items(), key=lambda kv: kv[1], reverse=True)]


class SelfPlayAdversary(Protocol):
    name: str
    def inspect(self, candidate: CandidateCalendarAction, reward: float) -> AdversaryFinding | None: ...


class ConflictAdversary:
    name = "conflict_adversary"

    def inspect(self, candidate: CandidateCalendarAction, reward: float) -> AdversaryFinding | None:
        if candidate.predicted_social_risk > 0.18 or len(candidate.affected_people_ids) >= 3:
            return AdversaryFinding(
                self.name,
                -0.90,
                "social_conflict",
                "candidate leans on other people's calendar reality more than its scalar score admits",
            )
        return None


class FatigueAdversary:
    name = "fatigue_adversary"

    def inspect(self, candidate: CandidateCalendarAction, reward: float) -> AdversaryFinding | None:
        if candidate.right_moment_decision.value in {"notify_now", "auto_write_then_notify"} and candidate.predicted_interruption_cost > 0.15:
            return AdversaryFinding(
                self.name,
                -candidate.predicted_interruption_cost * 1.7,
                "notification_fatigue",
                "right action, bad dose: interruption cost compounds under proactive timing",
            )
        return None


class RegretAdversary:
    name = "regret_adversary"

    def inspect(self, candidate: CandidateCalendarAction, reward: float) -> AdversaryFinding | None:
        if candidate.required_authority_tier >= 3 and candidate.predicted_regret > 0.10:
            return AdversaryFinding(
                self.name,
                -1.05,
                "undo_regret",
                "auto-write candidate carries enough regret probability to deserve a rollback stress test",
            )
        return None


class EngagementAdversary:
    name = "engagement_adversary"

    def inspect(self, candidate: CandidateCalendarAction, reward: float) -> AdversaryFinding | None:
        if candidate.predicted_engagement > candidate.predicted_utility and candidate.predicted_engagement > 0.25:
            return AdversaryFinding(
                self.name,
                -0.75,
                "engagement_over_utility",
                "candidate may be winning attention instead of schedule quality",
            )
        return None


class UserSimulator:
    """Stochastic user model with reasons, not just rolls.

    The simulator is deliberately simple, but it gives self-play the important
    shape: the user is not a scalar reward function; they can accept, ignore,
    reject, or undo for different reasons.
    """

    def __init__(self, seed: int = 7) -> None:
        self.random = random.Random(seed)

    def respond(self, candidate: CandidateCalendarAction) -> SimulatedResponse:
        p_accept = max(
            0.0,
            min(
                0.95,
                candidate.predicted_acceptance
                + 0.18 * candidate.predicted_utility
                - candidate.predicted_regret
                - candidate.predicted_interruption_cost * 0.25
                - candidate.predicted_social_risk * 0.25,
            ),
        )
        roll = self.random.random()
        if candidate.intent == "do_nothing":
            return SimulatedResponse("ignored", 0.0, "baseline no-op")
        if roll < p_accept:
            regret_roll = self.random.random()
            if regret_roll < candidate.predicted_regret:
                return SimulatedResponse("undone", -2.0, "accepted first, then regretted after calendar reality changed")
            return SimulatedResponse("accepted", 1.0 + candidate.expected_reward, "accepted because expected utility cleared friction")
        if roll < p_accept + 0.12:
            return SimulatedResponse("ignored", -0.35, "user neither accepted nor corrected; treat as weak negative")
        return SimulatedResponse("rejected", -0.85, "rejected by simulated preference boundary")


@dataclass
class SelfPlayRunner:
    policy: DiffusionGemmaPolicy = field(default_factory=DiffusionGemmaPolicy)
    kernel: SwiftKernelStub = field(default_factory=SwiftKernelStub)
    user_simulator: UserSimulator = field(default_factory=UserSimulator)
    adversaries: list[SelfPlayAdversary] = field(default_factory=lambda: [
        ConflictAdversary(),
        FatigueAdversary(),
        RegretAdversary(),
        EngagementAdversary(),
    ])

    def run(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        episodes: int = 10,
        authority_tier: int = 3,
        top_k: int = 4,
    ) -> SelfPlayMetrics:
        metrics = SelfPlayMetrics()
        for idx in range(episodes):
            episode = self.run_episode(observation, biography, idx + 1, authority_tier=authority_tier, top_k=top_k)
            self._fold_episode(metrics, episode)
        return metrics

    def run_episode(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        episode_index: int,
        authority_tier: int = 3,
        top_k: int = 4,
    ) -> SelfPlayEpisode:
        candidates = self.policy.generate_candidates(observation, biography)
        baseline = next((c for c in candidates if c.intent == "do_nothing"), candidates[-1])
        chosen = self._robust_choice(candidates, top_k=top_k)
        receipt = self.kernel.authorize_and_materialize(chosen, observation, granted_authority_tier=authority_tier)
        response = self.user_simulator.respond(chosen)
        reward_before = response.reward
        reward_after = reward_before
        findings: list[AdversaryFinding] = []
        if receipt.denied_reason:
            findings.append(AdversaryFinding("swift_authority", -1.0, "denied_actuation", receipt.denied_reason))
            reward_after -= 1.0
        for adversary in self.adversaries:
            finding = adversary.inspect(chosen, reward_after)
            if finding:
                findings.append(finding)
                reward_after += finding.reward_delta
        chosen.simulated_outcomes[response.outcome] = chosen.simulated_outcomes.get(response.outcome, 0.0) + 1.0
        _ = RewardEvent(
            reward_event_id=f"rew_{episode_index}",
            receipt_id=receipt.receipt_id,
            observed_at=datetime.now(observation.observed_at.tzinfo),
            accepted=(response.outcome == "accepted"),
            undone=(response.outcome == "undone"),
            ignored=(response.outcome == "ignored"),
            total_reward=reward_after,
        )
        return SelfPlayEpisode(
            episode_index=episode_index,
            chosen_candidate_id=chosen.candidate_id,
            chosen_intent=chosen.intent,
            baseline_candidate_id=baseline.candidate_id,
            outcome=response.outcome,
            reward_before_adversaries=round(reward_before, 4),
            reward_after_adversaries=round(reward_after, 4),
            findings=findings,
            response_reason=response.reason,
        )

    def _robust_choice(self, candidates: list[CandidateCalendarAction], top_k: int) -> CandidateCalendarAction:
        # Pick the highest candidate after adversarial preview, not merely the dry
        # maximum expected reward. This approximates robust policy selection.
        frontier = candidates[: max(1, top_k)]
        scored: list[tuple[float, CandidateCalendarAction]] = []
        for candidate in frontier:
            preview = candidate.expected_reward
            for adversary in self.adversaries:
                finding = adversary.inspect(candidate, preview)
                if finding:
                    preview += finding.reward_delta
            scored.append((preview, candidate))
        return sorted(scored, key=lambda pair: pair[0], reverse=True)[0][1]

    @staticmethod
    def _fold_episode(metrics: SelfPlayMetrics, episode: SelfPlayEpisode) -> None:
        metrics.episodes += 1
        metrics.total_reward += episode.reward_after_adversaries
        metrics.adversarial_delta += episode.reward_after_adversaries - episode.reward_before_adversaries
        metrics.chosen_intents[episode.chosen_intent] = metrics.chosen_intents.get(episode.chosen_intent, 0) + 1
        if episode.outcome == "accepted":
            metrics.accepted += 1
        elif episode.outcome == "undone":
            metrics.undone += 1
            metrics.high_regret_actions += 1
        elif episode.outcome == "ignored":
            metrics.ignored += 1
        else:
            metrics.rejected += 1
        for finding in episode.findings:
            metrics.failure_modes[finding.label] = metrics.failure_modes.get(finding.label, 0) + 1
            if finding.label == "notification_fatigue":
                metrics.fatigue_penalty += abs(finding.reward_delta)
        metrics.episode_log.append(episode)
