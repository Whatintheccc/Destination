from __future__ import annotations

from datetime import timedelta
import hashlib

from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    RawCalendarEvent,
    RawCalendarObservation,
    Reversibility,
    UserBiography,
)
from calendar_pilot.diffusiongemma.reward import RewardModel
from calendar_pilot.diffusiongemma.right_moment import RightMomentModel


class DiffusionGemmaPolicy:
    """Reference candidate generator.

    This class stands in for DiffusionGemma. It generates action trajectories from
    raw calendar context and a persistent biography, then scores them.
    """

    def __init__(self, reward_model: RewardModel | None = None, right_moment: RightMomentModel | None = None) -> None:
        self.reward_model = reward_model or RewardModel()
        self.right_moment = right_moment or RightMomentModel()

    def generate_candidates(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
    ) -> list[CandidateCalendarAction]:
        candidates: list[CandidateCalendarAction] = []
        candidates.extend(self._prep_blocks(observation, biography))
        candidates.extend(self._batch_admin(observation, biography))
        candidates.extend(self._move_flexible_holds(observation, biography))
        candidates.append(self._do_nothing(observation))

        for candidate in candidates:
            self._attach_initial_scores(candidate, observation, biography)
            self.reward_model.score(candidate)
            self.right_moment.decide(candidate, observation, biography)
        return sorted(candidates, key=lambda c: c.expected_reward, reverse=True)

    def _prep_blocks(self, observation: RawCalendarObservation, biography: UserBiography) -> list[CandidateCalendarAction]:
        out: list[CandidateCalendarAction] = []
        prep_conf = biography.confidence_for("prep blocks")
        for event in observation.events:
            if event.category == "external_meeting":
                # Try several near-meeting prep windows. This is intentionally a
                # generator, not a fixed rule, because the policy should imagine
                # multiple feasible futures and choose the highest value one.
                candidate_windows = [(45, 15), (30, 5), (60, 30), (90, 60)]
                for start_offset, end_offset in candidate_windows:
                    start = event.start - timedelta(minutes=start_offset)
                    end = event.start - timedelta(minutes=end_offset)
                    if self._is_slot_free(observation.events, start, end):
                        action = AtomicCalendarAction(
                            action_type=AtomicActionType.CREATE_EVENT,
                            title=f"Prep for {event.title}",
                            start=start,
                            end=end,
                            calendar_id=event.calendar_id,
                            attendees=[],
                            metadata={"parent_event_id": event.event_id, "source": "prep_block_generator"},
                        )
                        out.append(CandidateCalendarAction(
                            candidate_id=self._cid("prep", event.event_id, start.isoformat()),
                            intent="create_prep_block",
                            actions=[action],
                            target_calendars=[event.calendar_id],
                            affected_event_ids=[event.event_id],
                            affected_people_ids=list(event.attendees),
                            reversibility=Reversibility.HIGH,
                            required_authority_tier=3,
                            predicted_acceptance=0.65 + 0.25 * prep_conf,
                            predicted_utility=0.80,
                            predicted_engagement=0.25,
                            predicted_regret=0.08,
                            predicted_interruption_cost=0.15,
                            predicted_social_risk=0.02,
                            predicted_long_horizon_value=0.60,
                            explanation=f"Create a prep block before {event.title} because similar prep blocks are usually kept.",
                        ))
                        break
        return out

    def _batch_admin(self, observation: RawCalendarObservation, biography: UserBiography) -> list[CandidateCalendarAction]:
        admin_tasks = [t for t in observation.tasks if t.category == "admin"]
        if not admin_tasks:
            return []
        # Use observed day at 15:30 as simple batch slot.
        start = observation.observed_at.replace(hour=15, minute=30, second=0, microsecond=0)
        end = start + timedelta(minutes=sum(t.estimated_minutes for t in admin_tasks))
        if not self._is_slot_free(observation.events, start, end):
            return []
        title = "Admin batch: " + ", ".join(t.title for t in admin_tasks[:3])
        action = AtomicCalendarAction(
            action_type=AtomicActionType.CREATE_EVENT,
            title=title,
            start=start,
            end=end,
            calendar_id="work",
            metadata={"task_ids": [t.task_id for t in admin_tasks], "source": "admin_batch_generator"},
        )
        return [CandidateCalendarAction(
            candidate_id=self._cid("admin", observation.observation_id, start.isoformat()),
            intent="batch_admin_tasks",
            actions=[action],
            target_calendars=["work"],
            affected_event_ids=[],
            affected_people_ids=[],
            reversibility=Reversibility.HIGH,
            required_authority_tier=3,
            predicted_acceptance=0.62,
            predicted_utility=0.55,
            predicted_engagement=0.15,
            predicted_regret=0.05,
            predicted_interruption_cost=0.10,
            predicted_social_risk=0.00,
            predicted_long_horizon_value=0.45,
            explanation="Batch low-risk admin tasks into one reversible block.",
        )]

    def _move_flexible_holds(self, observation: RawCalendarObservation, biography: UserBiography) -> list[CandidateCalendarAction]:
        if not biography.auto_move_flexible_holds:
            return []
        out: list[CandidateCalendarAction] = []
        external_starts = [e.start for e in observation.events if e.category == "external_meeting"]
        for event in observation.events:
            if event.is_user_owned and event.is_flexible and any(abs((event.end - s).total_seconds()) <= 3600 for s in external_starts):
                new_start = event.start + timedelta(hours=2)
                new_end = event.end + timedelta(hours=2)
                if self._is_slot_free(observation.events, new_start, new_end, ignore_event_id=event.event_id):
                    action = AtomicCalendarAction(
                        action_type=AtomicActionType.MOVE_EVENT,
                        title=event.title,
                        event_id=event.event_id,
                        start=new_start,
                        end=new_end,
                        calendar_id=event.calendar_id,
                        metadata={"source": "flexible_hold_mover"},
                    )
                    out.append(CandidateCalendarAction(
                        candidate_id=self._cid("move", event.event_id, new_start.isoformat()),
                        intent="move_flexible_hold",
                        actions=[action],
                        target_calendars=[event.calendar_id],
                        affected_event_ids=[event.event_id],
                        affected_people_ids=list(event.attendees),
                        reversibility=Reversibility.MEDIUM,
                        required_authority_tier=3,
                        predicted_acceptance=0.70,
                        predicted_utility=0.62,
                        predicted_engagement=0.22,
                        predicted_regret=0.12,
                        predicted_interruption_cost=0.18,
                        predicted_social_risk=0.03,
                        predicted_long_horizon_value=0.50,
                        explanation=f"Move flexible block '{event.title}' away from external-meeting prep pressure.",
                    ))
        return out

    def _do_nothing(self, observation: RawCalendarObservation) -> CandidateCalendarAction:
        action = AtomicCalendarAction(action_type=AtomicActionType.DO_NOTHING, metadata={"source": "baseline"})
        return CandidateCalendarAction(
            candidate_id=self._cid("none", observation.observation_id),
            intent="do_nothing",
            actions=[action],
            target_calendars=[],
            affected_event_ids=[],
            affected_people_ids=[],
            reversibility=Reversibility.HIGH,
            required_authority_tier=0,
            predicted_acceptance=0.0,
            predicted_utility=0.0,
            predicted_engagement=0.0,
            predicted_regret=0.0,
            predicted_interruption_cost=0.0,
            predicted_social_risk=0.0,
            predicted_long_horizon_value=0.0,
            explanation="Baseline no-op candidate for counterfactual evaluation.",
        )

    @staticmethod
    def _attach_initial_scores(candidate: CandidateCalendarAction, observation: RawCalendarObservation, biography: UserBiography) -> None:
        # Penalize fatigue-heavy suggestions; social risk grows with affected people and authority.
        candidate.predicted_interruption_cost = min(1.0, candidate.predicted_interruption_cost + biography.notification_fatigue * 0.2)
        if candidate.affected_people_ids and candidate.required_authority_tier >= 4:
            candidate.predicted_social_risk = min(1.0, candidate.predicted_social_risk + 0.25)
        if observation.device_context.is_focus_mode:
            candidate.predicted_interruption_cost = min(1.0, candidate.predicted_interruption_cost + 0.25)

    @staticmethod
    def _is_slot_free(events: list[RawCalendarEvent], start, end, ignore_event_id: str | None = None) -> bool:
        for event in events:
            if ignore_event_id and event.event_id == ignore_event_id:
                continue
            if start < event.end and end > event.start:
                return False
        return True

    @staticmethod
    def _cid(*parts: str) -> str:
        return "cand_" + hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
