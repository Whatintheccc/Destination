

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import os
import random
from typing import Protocol

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.environment.selfplay_backends import BACKEND_POLICIES, SelfPlayActionBackend
from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.swift_bridge.protocol import CalendarKernelProtocol
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import AuthorityGrant, CandidateCalendarAction, RawCalendarObservation, RewardEvent, UserBiography, authority_scopes_for_tier


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
    episode_id: str
    episode_index: int
    chosen_candidate_id: str
    chosen_intent: str
    baseline_candidate_id: str
    receipt_id: str
    denied_reason: str | None
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
    kernel: CalendarKernelProtocol = field(default_factory=SwiftKernelStub)
    user_simulator: UserSimulator = field(default_factory=UserSimulator)
    adversaries: list[SelfPlayAdversary] = field(default_factory=lambda: [
        ConflictAdversary(),
        FatigueAdversary(),
        RegretAdversary(),
        EngagementAdversary(),
    ])
    replay: ReplayBuffer | None = None
    action_backend: SelfPlayActionBackend = SelfPlayActionBackend.STUB_FAST

    def run(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        episodes: int = 10,
        authority_tier: int = 3,
        top_k: int = 4,
        authority_grant: AuthorityGrant | str | None = None,
    ) -> SelfPlayMetrics:
        metrics = SelfPlayMetrics()
        for idx in range(episodes):
            episode = self.run_episode(observation, biography, idx + 1, authority_tier=authority_tier, top_k=top_k, authority_grant=authority_grant)
            self._fold_episode(metrics, episode)
        return metrics

    def run_episode(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        episode_index: int,
        authority_tier: int = 3,
        top_k: int = 4,
        authority_grant: AuthorityGrant | str | None = None,
    ) -> SelfPlayEpisode:
        candidates = self.policy.generate_candidates(observation, biography)
        for rank, candidate in enumerate(candidates[: max(1, top_k)]):
            if self.replay is not None:
                self.replay.append_decision(candidate, rank=rank, trace_id=f"self_play:{episode_index}:{candidate.candidate_id}")
        baseline = next((c for c in candidates if c.intent == "do_nothing"), candidates[-1])
        chosen = self._robust_choice(candidates, top_k=top_k)
        grant = authority_grant
        backend_policy = BACKEND_POLICIES[self.action_backend]
        if backend_policy.requires_env_flag and os.environ.get(backend_policy.requires_env_flag, "") not in {"1", "true", "TRUE", "yes"}:
            authority_tier = 0
            grant = None
        if grant is None and authority_tier > 0:
            if backend_policy.grant_issuance == "read_only":
                grant = None
            elif backend_policy.grant_issuance == "kernel_issued_sandbox":
                sandbox_scopes = sorted(set(authority_scopes_for_tier(authority_tier) + ["commit_selfplay_sandbox"]))
                grant = self.kernel.issue_authority_grant(
                    user_scope_id=observation.user_scope_id,
                    max_authority_tier=authority_tier,
                    scopes=sandbox_scopes,
                    confirmation_provenance=f"selfplay_lab:{self.action_backend.value}:episode:{episode_index}",
                    confirmed_by_user=True,
                    issued_at=observation.observed_at,
                )
            elif backend_policy.grant_issuance == "self_issued":
                grant = self.kernel.issue_authority_grant(
                    user_scope_id=observation.user_scope_id,
                    max_authority_tier=authority_tier,
                    scopes=authority_scopes_for_tier(authority_tier),
                    confirmation_provenance=f"self_play_episode:{episode_index}",
                    confirmed_by_user=True,
                    issued_at=observation.observed_at,
                )
        receipt = self.kernel.authorize_and_materialize(chosen, observation, authority_grant=grant, requested_authority_tier=authority_tier)
        if self.replay is not None:
            self.replay.append_receipt(receipt, chosen, trace_id=f"self_play:{episode_index}:{chosen.candidate_id}")
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
        reward_event = RewardEvent(
            reward_event_id=f"rew_{episode_index}",
            receipt_id=receipt.receipt_id,
            observed_at=datetime.now(observation.observed_at.tzinfo),
            accepted=(response.outcome == "accepted"),
            undone=(response.outcome == "undone"),
            ignored=(response.outcome == "ignored"),
            explicit_wrong=any(f.label == "social_conflict" for f in findings) or None,
            notification_dismissed=any(f.label == "notification_fatigue" for f in findings) or None,
            total_reward=reward_after,
            provenance="adversarial",
        )
        if self.replay is not None:
            self.replay.append_reward(reward_event, chosen, receipt, trace_id=f"self_play:{episode_index}:{chosen.candidate_id}", causal_parent_id=receipt.receipt_id)
        episode = SelfPlayEpisode(
            episode_id=f"self_play_episode_{episode_index}_{chosen.candidate_id}",
            episode_index=episode_index,
            chosen_candidate_id=chosen.candidate_id,
            chosen_intent=chosen.intent,
            baseline_candidate_id=baseline.candidate_id,
            receipt_id=receipt.receipt_id,
            denied_reason=receipt.denied_reason,
            outcome=response.outcome,
            reward_before_adversaries=round(reward_before, 4),
            reward_after_adversaries=round(reward_after, 4),
            findings=findings,
            response_reason=response.reason,
        )
        if self.replay is not None:
            self.replay.append_episode(episode, trace_id=f"self_play:{episode_index}:{chosen.candidate_id}", causal_parent_id=receipt.receipt_id)
        return episode

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
