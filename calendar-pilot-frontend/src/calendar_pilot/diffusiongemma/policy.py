from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
from typing import Iterable

from calendar_pilot.diffusiongemma.reward import RewardModel
from calendar_pilot.diffusiongemma.right_moment import RightMomentModel
from calendar_pilot.diffusiongemma.signals import CalendarSignals, OpenSlot, extract_signals
from calendar_pilot.diffusiongemma.world_model import CalendarWorldModel
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    RawCalendarEvent,
    RawCalendarObservation,
    RawTask,
    Reversibility,
    UserBiography,
    PolicyTuning,
)


class DiffusionGemmaPolicy:
    """Reference DiffusionGemma policy for an agentic calendar optimizer.

    The policy now does three things the first repo only gestured at:

    1. reads raw-context pressure signals;
    2. imagines candidate futures with a small world model;
    3. scores and times actions with visible reward anatomy.

    It is still deterministic and small enough for unit tests, but the shape is
    the one a learned generator would keep: generate many action programs, attach
    a counterfactual, reward them, then let right-moment prediction decide how the
    machine acts.
    """

    def __init__(
        self,
        reward_model: RewardModel | None = None,
        right_moment: RightMomentModel | None = None,
        world_model: CalendarWorldModel | None = None,
        policy_tuning: PolicyTuning | None = None,
    ) -> None:
        self.reward_model = reward_model or RewardModel()
        self.right_moment = right_moment or RightMomentModel()
        self.world_model = world_model or CalendarWorldModel()
        self.policy_tuning = policy_tuning or PolicyTuning()

    def generate_candidates(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
    ) -> list[CandidateCalendarAction]:
        signals = extract_signals(observation, biography)
        candidates: list[CandidateCalendarAction] = []
        candidates.extend(self._prep_blocks(observation, biography, signals))
        candidates.extend(self._travel_or_setup_buffers(observation, biography, signals))
        candidates.extend(self._batch_admin(observation, biography, signals))
        candidates.extend(self._move_flexible_holds(observation, biography, signals))
        candidates.extend(self._protect_focus_windows(observation, biography, signals))
        candidates.extend(self._draft_day_repair_plan(observation, biography, signals))
        candidates.append(self._do_nothing(observation, signals))

        for candidate in candidates:
            self._attach_initial_scores(candidate, observation, biography, signals)
            self.world_model.annotate(candidate, observation, biography, signals)
            self.reward_model.score(candidate)
            self._apply_policy_tuning(candidate)
            self.right_moment.decide(candidate, observation, biography, signals)
        return sorted(candidates, key=lambda c: (c.expected_reward, c.right_moment_score), reverse=True)


    def _apply_policy_tuning(self, candidate: CandidateCalendarAction) -> None:
        """Apply offline replay/self-play feedback as a lightweight policy update.

        This is not a neural update. It is the contract shape a learned
        DiffusionGemma policy would consume: intent residuals, denial filters,
        and adversary penalties are attached after base scoring so the acting
        policy visibly changes from replay rather than merely reporting it.
        """
        tuning = self.policy_tuning
        if candidate.intent in tuning.denied_intents:
            candidate.expected_reward = round(candidate.expected_reward - 1.0, 4)
            candidate.control_notes.append("offline_tuning=deny_intent_penalty:-1.00")
        bias = tuning.intent_reward_bias.get(candidate.intent, 0.0)
        if bias:
            candidate.expected_reward = round(candidate.expected_reward + bias, 4)
            candidate.reward_breakdown["offline_intent_bias"] = round(bias, 4)
            candidate.control_notes.append(f"offline_tuning=intent_bias:{bias:+.2f}")
        penalty = 0.0
        if candidate.predicted_social_risk > 0.18 or len(candidate.affected_people_ids) >= 3:
            penalty += tuning.failure_penalties.get("social_conflict", 0.0)
        if candidate.predicted_interruption_cost > 0.15 and candidate.intent not in {"do_nothing"}:
            penalty += tuning.failure_penalties.get("notification_fatigue", 0.0)
        if candidate.required_authority_tier >= 3 and candidate.predicted_regret > 0.10:
            penalty += tuning.failure_penalties.get("undo_regret", 0.0)
        if candidate.predicted_engagement > candidate.predicted_utility and candidate.predicted_engagement > 0.25:
            penalty += tuning.failure_penalties.get("engagement_over_utility", 0.0)
        if penalty:
            candidate.expected_reward = round(candidate.expected_reward + penalty, 4)
            candidate.reward_breakdown["offline_adversary_penalty"] = round(penalty, 4)
            candidate.control_notes.append(f"offline_tuning=adversary_penalty:{penalty:+.2f}")

    def _prep_blocks(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> list[CandidateCalendarAction]:
        out: list[CandidateCalendarAction] = []
        prep_conf = biography.confidence_for("prep blocks")
        prep_tasks = [t for t in observation.tasks if t.category == "prep"]
        requested_minutes = min(45, max([t.estimated_minutes for t in prep_tasks] or [25]))
        for event in observation.events:
            if event.category != "external_meeting":
                continue
            for start_offset in (90, 75, 60, 45, 30):
                end_offset = max(5, start_offset - requested_minutes)
                start = event.start - timedelta(minutes=start_offset)
                end = event.start - timedelta(minutes=end_offset)
                if self._is_slot_free(observation.events, start, end):
                    title = _title_join("Prep", event.title)
                    action = AtomicCalendarAction(
                        action_type=AtomicActionType.CREATE_EVENT,
                        title=title,
                        start=start,
                        end=end,
                        calendar_id=event.calendar_id,
                        attendees=[],
                        metadata={
                            "parent_event_id": event.event_id,
                            "task_ids": ",".join(t.task_id for t in prep_tasks),
                            "source": "diffusiongemma.prep_blocks",
                        },
                    )
                    out.append(CandidateCalendarAction(
                        candidate_id=self._cid("prep", event.event_id, start.isoformat()),
                        intent="create_prep_block",
                        actions=[action],
                        target_calendars=[event.calendar_id],
                        affected_event_ids=[event.event_id],
                        # This creates a private prep block; it references the
                        # parent meeting for context but does not mutate attendees.
                        affected_people_ids=[],
                        reversibility=Reversibility.HIGH,
                        required_authority_tier=3,
                        predicted_acceptance=0.58 + 0.30 * prep_conf,
                        predicted_utility=0.76 + 0.08 * signals.pressure_score,
                        predicted_engagement=0.20,
                        predicted_regret=0.06,
                        predicted_interruption_cost=0.12,
                        predicted_social_risk=0.02,
                        predicted_long_horizon_value=0.62,
                        explanation=f"Create a {int((end-start).total_seconds()//60)}-minute prep block before {event.title}.",
                    ))
                    break
        return out

    def _travel_or_setup_buffers(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> list[CandidateCalendarAction]:
        if not biography.auto_create_travel_buffers:
            return []
        out: list[CandidateCalendarAction] = []
        for event in observation.events:
            needs_buffer = event.category == "external_meeting" and (event.location and event.location.lower() not in {"", "zoom", "meet", "teams"})
            setup_buffer = event.category == "external_meeting" and "external_meeting_without_preparation_space" in signals.risk_cliffs
            if not (needs_buffer or setup_buffer):
                continue
            minutes = 20 if needs_buffer else 10
            start = event.start - timedelta(minutes=minutes)
            end = event.start
            if self._is_slot_free(observation.events, start, end):
                action = AtomicCalendarAction(
                    action_type=AtomicActionType.ADD_BUFFER,
                    title=f"Buffer before {event.title}",
                    start=start,
                    end=end,
                    calendar_id=event.calendar_id,
                    metadata={"parent_event_id": event.event_id, "source": "diffusiongemma.buffer"},
                )
                out.append(CandidateCalendarAction(
                    candidate_id=self._cid("buffer", event.event_id, start.isoformat()),
                    intent="add_transition_buffer",
                    actions=[action],
                    target_calendars=[event.calendar_id],
                    affected_event_ids=[event.event_id],
                    # Transition/setup buffers are private calendar objects;
                    # attendees are not affected unless an attendee event is moved.
                    affected_people_ids=[],
                    reversibility=Reversibility.HIGH,
                    required_authority_tier=3,
                    predicted_acceptance=0.66,
                    predicted_utility=0.68,
                    predicted_engagement=0.18,
                    predicted_regret=0.05,
                    predicted_interruption_cost=0.09,
                    predicted_social_risk=0.01,
                    predicted_long_horizon_value=0.52,
                    explanation=f"Create a small transition buffer before {event.title}.",
                ))
        return out

    def _batch_admin(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> list[CandidateCalendarAction]:
        admin_tasks = [t for t in observation.tasks if t.category == "admin"]
        if not admin_tasks:
            return []
        duration = min(90, max(20, sum(t.estimated_minutes for t in admin_tasks)))
        slot = self._best_slot(signals.open_slots, duration, preferred_labels=("afternoon", "late_day", "midday"))
        if slot is None:
            return []
        start = slot.start
        end = start + timedelta(minutes=duration)
        title = "Admin batch: " + ", ".join(t.title for t in admin_tasks[:3])
        action = AtomicCalendarAction(
            action_type=AtomicActionType.BATCH_TASKS,
            title=title,
            start=start,
            end=end,
            calendar_id="work",
            metadata={"task_ids": ",".join(t.task_id for t in admin_tasks), "source": "diffusiongemma.admin_batch"},
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
            predicted_acceptance=0.55 + 0.12 * biography.confidence_for("admin"),
            predicted_utility=0.48 + min(0.22, signals.admin_task_minutes / 240.0),
            predicted_engagement=0.12,
            predicted_regret=0.04,
            predicted_interruption_cost=0.08,
            predicted_social_risk=0.00,
            predicted_long_horizon_value=0.42,
            explanation=f"Batch {len(admin_tasks)} admin task(s) into one reversible block.",
        )]

    def _move_flexible_holds(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> list[CandidateCalendarAction]:
        if not biography.auto_move_flexible_holds:
            return []
        out: list[CandidateCalendarAction] = []
        external_starts = [e.start for e in observation.events if e.category == "external_meeting"]
        for event in observation.events:
            close_to_pressure = any(abs((event.end - s).total_seconds()) <= 3600 for s in external_starts)
            if not (event.is_user_owned and event.is_flexible and close_to_pressure):
                continue
            duration = int((event.end - event.start).total_seconds() // 60)
            slot = self._best_slot(signals.open_slots, duration, after=event.end + timedelta(minutes=30), preferred_labels=("afternoon", "late_day"))
            if slot is None:
                continue
            new_start = slot.start
            new_end = new_start + timedelta(minutes=duration)
            if self._is_slot_free(observation.events, new_start, new_end, ignore_event_id=event.event_id):
                action = AtomicCalendarAction(
                    action_type=AtomicActionType.MOVE_EVENT,
                    title=event.title,
                    event_id=event.event_id,
                    start=new_start,
                    end=new_end,
                    calendar_id=event.calendar_id,
                    metadata={"source": "diffusiongemma.flexible_hold_mover"},
                )
                out.append(CandidateCalendarAction(
                    candidate_id=self._cid("move", event.event_id, new_start.isoformat()),
                    intent="move_flexible_hold",
                    actions=[action],
                    target_calendars=[event.calendar_id],
                    affected_event_ids=[event.event_id],
                    # Transition/setup buffers are private calendar objects;
                    # attendees are not affected unless an attendee event is moved.
                    affected_people_ids=[],
                    reversibility=Reversibility.MEDIUM,
                    required_authority_tier=3,
                    predicted_acceptance=0.68,
                    predicted_utility=0.60 + 0.08 * signals.pressure_score,
                    predicted_engagement=0.20,
                    predicted_regret=0.11,
                    predicted_interruption_cost=0.16,
                    predicted_social_risk=0.02,
                    predicted_long_horizon_value=0.50,
                    explanation=f"Move flexible block '{event.title}' away from external-meeting pressure.",
                ))
        return out

    def _protect_focus_windows(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> list[CandidateCalendarAction]:
        if not biography.deep_work_windows and signals.pressure_score < 0.45:
            return []
        slot = self._best_slot(signals.open_slots, 60, preferred_labels=("morning", "midday"))
        if slot is None:
            return []
        start = slot.start
        end = min(slot.end, start + timedelta(minutes=min(90, slot.minutes)))
        action = AtomicCalendarAction(
            action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
            title="Focus block",
            start=start,
            end=end,
            calendar_id="work",
            metadata={"source": "diffusiongemma.focus_protector"},
        )
        return [CandidateCalendarAction(
            candidate_id=self._cid("focus", observation.observation_id, start.isoformat()),
            intent="protect_focus_window",
            actions=[action],
            target_calendars=["work"],
            affected_event_ids=[],
            affected_people_ids=[],
            reversibility=Reversibility.HIGH,
            required_authority_tier=3,
            predicted_acceptance=0.50 + 0.15 * biography.confidence_for("deep work"),
            predicted_utility=0.56,
            predicted_engagement=0.18,
            predicted_regret=0.10,
            predicted_interruption_cost=0.10,
            predicted_social_risk=0.00,
            predicted_long_horizon_value=0.70,
            explanation=f"Protect a {int((end-start).total_seconds()//60)}-minute focus window while the gap is still open.",
        )]

    def _draft_day_repair_plan(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> list[CandidateCalendarAction]:
        if signals.pressure_score < 0.50 or len(signals.risk_cliffs) < 2:
            return []
        # A draft plan is a machine act too, but it keeps calendar write authority
        # lower while still giving the policy a multi-step trajectory to evaluate.
        action = AtomicCalendarAction(
            action_type=AtomicActionType.DRAFT_SCHEDULE_PLAN,
            title="Draft calendar repair plan",
            start=observation.observed_at,
            end=observation.observed_at + timedelta(minutes=5),
            calendar_id="work",
            metadata={"risk_cliffs": ",".join(signals.risk_cliffs), "source": "diffusiongemma.day_repair_plan"},
        )
        return [CandidateCalendarAction(
            candidate_id=self._cid("plan", observation.observation_id, ",".join(signals.risk_cliffs)),
            intent="draft_day_repair_plan",
            actions=[action],
            target_calendars=["work"],
            affected_event_ids=[e.event_id for e in observation.events if e.category == "external_meeting"],
            affected_people_ids=sorted({p for e in observation.events for p in e.attendees}),
            reversibility=Reversibility.HIGH,
            required_authority_tier=2,
            predicted_acceptance=0.58,
            predicted_utility=0.64,
            predicted_engagement=0.30,
            predicted_regret=0.04,
            predicted_interruption_cost=0.22,
            predicted_social_risk=0.08,
            predicted_long_horizon_value=0.58,
            explanation="Draft a small repair plan instead of firing several separate interventions.",
        )]

    def _do_nothing(self, observation: RawCalendarObservation, signals: CalendarSignals) -> CandidateCalendarAction:
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
            predicted_utility=max(0.0, 0.12 - signals.pressure_score * 0.1),
            predicted_engagement=0.0,
            predicted_regret=max(0.0, signals.pressure_score * 0.15),
            predicted_interruption_cost=0.0,
            predicted_social_risk=0.0,
            predicted_long_horizon_value=0.0,
            explanation="Baseline no-op candidate for counterfactual evaluation.",
        )

    @staticmethod
    def _attach_initial_scores(
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> None:
        # Policy shaping before reward: pressure improves utility, fatigue taxes
        # interruption, and social authority has a separate cost from calendar cost.
        candidate.predicted_utility = min(1.0, candidate.predicted_utility + signals.pressure_score * 0.05)
        candidate.predicted_interruption_cost = min(1.0, candidate.predicted_interruption_cost + signals.fatigue_score * 0.18)
        if candidate.affected_people_ids and candidate.required_authority_tier >= 4:
            candidate.predicted_social_risk = min(1.0, candidate.predicted_social_risk + 0.22)
        if observation.device_context.is_focus_mode and candidate.intent != "do_nothing":
            candidate.predicted_interruption_cost = min(1.0, candidate.predicted_interruption_cost + 0.20)
            candidate.control_notes.append("focus_mode_interruption_penalty=+0.20")
        if biography.has_claim("dismisses evening") and observation.device_context.local_hour >= 18:
            candidate.predicted_interruption_cost = min(1.0, candidate.predicted_interruption_cost + 0.25)
        candidate.control_notes.append(f"pressure={signals.pressure_score:.2f}, fatigue={signals.fatigue_score:.2f}")

    @staticmethod
    def _best_slot(
        slots: Iterable[OpenSlot],
        minutes: int,
        *,
        after: datetime | None = None,
        preferred_labels: tuple[str, ...] = ("morning", "midday", "afternoon", "late_day"),
    ) -> OpenSlot | None:
        candidates = [s for s in slots if s.minutes >= minutes and (after is None or s.start >= after)]
        if not candidates:
            return None
        label_rank = {label: idx for idx, label in enumerate(preferred_labels)}
        return sorted(candidates, key=lambda s: (label_rank.get(s.label, 99), s.start))[0]

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


def _title_join(prefix: str, raw_title: str) -> str:
    raw_title = raw_title.strip()
    return f"{prefix}: {raw_title}" if raw_title else prefix
