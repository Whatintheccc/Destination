from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from calendar_pilot.diffusiongemma.signals import CalendarSignals, extract_signals
from calendar_pilot.types import CandidateCalendarAction, RawCalendarObservation, RightMomentDecision, UserBiography


@dataclass(frozen=True)
class TemporalControlPlan:
    mode: str
    expose_at: datetime | None
    execute_at: datetime | None
    stale_after: datetime | None
    authority_expires_hint: datetime | None
    staleness_risk: float
    exposure_cost: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "expose_at": self.expose_at.isoformat() if self.expose_at else None,
            "execute_at": self.execute_at.isoformat() if self.execute_at else None,
            "stale_after": self.stale_after.isoformat() if self.stale_after else None,
            "authority_expires_hint": self.authority_expires_hint.isoformat() if self.authority_expires_hint else None,
            "staleness_risk": round(self.staleness_risk, 4),
            "exposure_cost": round(self.exposure_cost, 4),
            "reason": self.reason,
        }


class RightMomentTemporalController:
    """Controls when a candidate is exposed, staged, or executed.

    RightMomentModel predicts a timing decision; this controller turns that
    decision into an explicit temporal-control record that replay, the Glass
    Cockpit Learn surface, and action lifecycle can inspect. It deliberately
    remains deterministic and metadata-only: Swift still validates authority and
    provider writes, while the controller tells Codex/UI whether to act now,
    stage-now-commit-later, bundle, wait, or refresh before commit.
    """

    def plan(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals | None = None,
    ) -> TemporalControlPlan:
        signals = signals or extract_signals(observation, biography)
        now = observation.observed_at
        decision = candidate.right_moment_decision
        action_times = [a.start for a in candidate.actions if a.start]
        first_action_at = min(action_times) if action_times else None
        hours_until = None if first_action_at is None else max(0.0, (first_action_at - now).total_seconds() / 3600.0)
        staleness_risk = self._staleness_risk(candidate, signals, hours_until)
        exposure_cost = self._exposure_cost(candidate, signals, observation)
        stale_after = self._stale_after(now, hours_until, staleness_risk)
        authority_hint = now + timedelta(minutes=30 if candidate.required_authority_tier >= 5 else 60)

        if decision in {RightMomentDecision.AUTO_WRITE_THEN_NOTIFY, RightMomentDecision.ACT_NOW, RightMomentDecision.NOTIFY_NOW}:
            mode = "act_now" if decision != RightMomentDecision.NOTIFY_NOW else "expose_now"
            return TemporalControlPlan(
                mode=mode,
                expose_at=now,
                execute_at=candidate.recommended_execution_time or now,
                stale_after=stale_after,
                authority_expires_hint=authority_hint,
                staleness_risk=staleness_risk,
                exposure_cost=exposure_cost,
                reason=f"{decision.value} selected with low enough timing cost",
            )
        if decision == RightMomentDecision.SILENTLY_DRAFT:
            return TemporalControlPlan(
                mode="stage_now_commit_later",
                expose_at=candidate.recommended_execution_time or stale_after,
                execute_at=None,
                stale_after=stale_after,
                authority_expires_hint=authority_hint,
                staleness_risk=staleness_risk,
                exposure_cost=exposure_cost,
                reason="valuable candidate should be staged without immediate interruption",
            )
        if decision == RightMomentDecision.BUNDLE_INTO_DIGEST:
            return TemporalControlPlan(
                mode="bundle_into_digest",
                expose_at=candidate.recommended_execution_time,
                execute_at=None,
                stale_after=stale_after,
                authority_expires_hint=authority_hint,
                staleness_risk=staleness_risk,
                exposure_cost=exposure_cost,
                reason="fatigue or response-window cost favors digest exposure",
            )
        if decision == RightMomentDecision.ASK_CLARIFICATION:
            return TemporalControlPlan(
                mode="ask_for_authority_or_context",
                expose_at=now,
                execute_at=None,
                stale_after=stale_after,
                authority_expires_hint=authority_hint,
                staleness_risk=staleness_risk,
                exposure_cost=exposure_cost,
                reason="candidate needs explicit context or authority before commit",
            )
        if decision == RightMomentDecision.WAIT:
            return TemporalControlPlan(
                mode="wait_for_context_refresh" if staleness_risk >= 0.4 else "wait_for_response_window",
                expose_at=candidate.recommended_execution_time,
                execute_at=None,
                stale_after=stale_after,
                authority_expires_hint=authority_hint,
                staleness_risk=staleness_risk,
                exposure_cost=exposure_cost,
                reason="waiting improves response timing or reduces stale-observation risk",
            )
        return TemporalControlPlan(
            mode="do_nothing",
            expose_at=None,
            execute_at=None,
            stale_after=stale_after,
            authority_expires_hint=None,
            staleness_risk=staleness_risk,
            exposure_cost=exposure_cost,
            reason="baseline counterfactual",
        )

    def apply(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals | None = None,
    ) -> CandidateCalendarAction:
        plan = self.plan(candidate, observation, biography, signals)
        payload = plan.to_dict()
        candidate.simulated_outcomes["temporal_staleness_risk"] = payload["staleness_risk"]
        candidate.simulated_outcomes["temporal_exposure_cost"] = payload["exposure_cost"]
        candidate.control_notes.append(f"temporal_control={plan.mode}: {plan.reason}")
        # Keep metadata string-only for Swift boundary by storing compact fields in notes/outcomes.
        return candidate

    @staticmethod
    def _staleness_risk(candidate: CandidateCalendarAction, signals: CalendarSignals, hours_until: float | None) -> float:
        base = 0.05 + min(0.30, 0.04 * len(candidate.affected_event_ids))
        if hours_until is None:
            base += 0.08
        elif hours_until > 24:
            base += 0.20
        elif hours_until > 8:
            base += 0.12
        if "external_meeting_without_preparation_space" in signals.risk_cliffs:
            base += 0.08
        if candidate.required_authority_tier >= 5:
            base += 0.12
        return min(1.0, base)

    @staticmethod
    def _exposure_cost(candidate: CandidateCalendarAction, signals: CalendarSignals, observation: RawCalendarObservation) -> float:
        cost = signals.fatigue_score * 0.45 + candidate.predicted_interruption_cost
        if observation.device_context.is_focus_mode:
            cost += 0.20
        if candidate.required_authority_tier >= 5:
            cost += 0.10
        return min(1.0, max(0.0, cost))

    @staticmethod
    def _stale_after(now: datetime, hours_until: float | None, staleness_risk: float) -> datetime:
        if hours_until is None:
            minutes = 45
        elif hours_until <= 2:
            minutes = 15
        elif hours_until <= 8:
            minutes = 30
        else:
            minutes = 60
        if staleness_risk >= 0.45:
            minutes = max(10, minutes // 2)
        return now + timedelta(minutes=minutes)
