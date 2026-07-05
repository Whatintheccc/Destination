

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from calendar_pilot.diffusiongemma.signals import CalendarSignals, extract_signals
from calendar_pilot.types import CandidateCalendarAction, RawCalendarObservation, RightMomentDecision, UserBiography


@dataclass(frozen=True)
class MomentScore:
    decision: RightMomentDecision
    execute_at: datetime | None
    score: float
    reason: str


class RightMomentModel:
    """Contextual right-moment predictor.

    It intentionally predicts intervention timing. Privacy is not the doctrine in
    this product; closed-loop control is. The model leaves a reason string so the
    actuation layer can audit why a write/notification happened now instead of in
    a digest.
    """

    def decide(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals | None = None,
    ) -> CandidateCalendarAction:
        signals = signals or extract_signals(observation, biography)
        moment = self.score_moment(candidate, observation, biography, signals)
        candidate.right_moment_decision = moment.decision
        candidate.recommended_execution_time = moment.execute_at
        candidate.right_moment_score = round(moment.score, 4)
        candidate.control_notes.append(f"right_moment={moment.decision.value}: {moment.reason}")
        return candidate

    def score_moment(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> MomentScore:
        now = observation.observed_at
        hour = observation.device_context.local_hour
        fatigue = signals.fatigue_score
        high_value = candidate.expected_reward >= 1.0
        reversible = candidate.reversibility.value in {"medium", "high"}
        authority_gap = max(0, candidate.required_authority_tier - 3)
        urgency = self._urgency(candidate, now)
        response_bonus = 0.24 if hour in biography.best_response_hours else -0.08
        interruption_penalty = fatigue * 0.34
        focus_penalty = 0.25 if observation.device_context.is_focus_mode else 0.0
        value_now = candidate.expected_reward + urgency + response_bonus - interruption_penalty - focus_penalty - 0.15 * authority_gap

        if candidate.intent == "do_nothing":
            return MomentScore(RightMomentDecision.DO_NOTHING, now, 0.0, "baseline counterfactual")

        if candidate.required_authority_tier >= 5 and biography.ask_before_people_meetings:
            return MomentScore(
                RightMomentDecision.ASK_CLARIFICATION,
                now,
                value_now - 0.2,
                "people-affecting action needs a question before actuation",
            )

        if fatigue > 0.7 or hour in biography.bad_response_hours:
            return MomentScore(
                RightMomentDecision.BUNDLE_INTO_DIGEST,
                self._next_digest(now),
                value_now - 0.35,
                "low interruption tolerance or bad response hour favors bundled intervention",
            )

        if candidate.required_authority_tier <= 3 and high_value and reversible and value_now >= 1.05:
            return MomentScore(
                RightMomentDecision.AUTO_WRITE_THEN_NOTIFY,
                now,
                value_now,
                "high value, reversible, and inside granted low-social-risk authority",
            )

        if signals.best_response_is_now and value_now >= 0.45:
            return MomentScore(
                RightMomentDecision.NOTIFY_NOW,
                now,
                value_now,
                "current hour matches learned response window",
            )

        if value_now >= 0.80 and reversible:
            return MomentScore(
                RightMomentDecision.SILENTLY_DRAFT,
                now,
                value_now - 0.05,
                "valuable but not worth an interruption yet",
            )

        return MomentScore(
            RightMomentDecision.WAIT,
            self._next_best_hour(now, biography),
            value_now - 0.1,
            "waiting for a better response window improves the intervention price",
        )

    @staticmethod
    def _urgency(candidate: CandidateCalendarAction, now: datetime) -> float:
        starts = [a.start for a in candidate.actions if a.start]
        if not starts:
            return 0.0
        hours = min(max(0.0, (s - now).total_seconds() / 3600.0) for s in starts)
        if hours < 2:
            return 0.20
        if hours < 8:
            return 0.12
        if hours < 24:
            return 0.06
        return 0.0

    @staticmethod
    def _next_digest(now: datetime) -> datetime:
        target = now.replace(hour=18, minute=0, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
        return target

    @staticmethod
    def _next_best_hour(now: datetime, biography: UserBiography) -> datetime:
        best_hours = sorted(biography.best_response_hours or [8, 13])
        for h in best_hours:
            candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if candidate > now:
                return candidate
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=best_hours[0], minute=0, second=0, microsecond=0)
