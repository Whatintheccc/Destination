from __future__ import annotations

from datetime import datetime, timedelta

from calendar_pilot.types import CandidateCalendarAction, RawCalendarObservation, RightMomentDecision, UserBiography


class RightMomentModel:
    """Heuristic right-moment predictor.

    Production version can be a learned contextual policy. This reference model
    keeps timing decisions observable and deterministic for tests.
    """

    def decide(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        biography: UserBiography,
    ) -> CandidateCalendarAction:
        hour = observation.device_context.local_hour
        fatigue = biography.notification_fatigue
        high_value = candidate.expected_reward >= 1.0
        reversible = candidate.reversibility.value in {"medium", "high"}

        if candidate.required_authority_tier >= 5 and biography.ask_before_people_meetings:
            candidate.right_moment_decision = RightMomentDecision.ASK_CLARIFICATION
            candidate.recommended_execution_time = observation.observed_at
        elif hour in biography.bad_response_hours or fatigue > 0.7:
            candidate.right_moment_decision = RightMomentDecision.BUNDLE_INTO_DIGEST
            candidate.recommended_execution_time = observation.observed_at + timedelta(hours=12)
        elif candidate.required_authority_tier <= 3 and high_value and reversible:
            candidate.right_moment_decision = RightMomentDecision.AUTO_WRITE_THEN_NOTIFY
            candidate.recommended_execution_time = observation.observed_at
        elif hour in biography.best_response_hours:
            candidate.right_moment_decision = RightMomentDecision.NOTIFY_NOW
            candidate.recommended_execution_time = observation.observed_at
        else:
            candidate.right_moment_decision = RightMomentDecision.WAIT
            candidate.recommended_execution_time = self._next_best_hour(observation.observed_at, biography)
        return candidate

    @staticmethod
    def _next_best_hour(now: datetime, biography: UserBiography) -> datetime:
        best_hours = sorted(biography.best_response_hours or [8, 13])
        for h in best_hours:
            candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if candidate > now:
                return candidate
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=best_hours[0], minute=0, second=0, microsecond=0)
