

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from calendar_pilot.diffusiongemma.signals import CalendarSignals
from calendar_pilot.types import AtomicActionType, CandidateCalendarAction, RawCalendarObservation, UserBiography


@dataclass(frozen=True)
class WorldSketch:
    thesis: str
    counterfactual: str
    upside: str
    risk_cliffs: list[str] = field(default_factory=list)
    schedule_delta_minutes: int = 0
    affected_people_count: int = 0
    value_decay_hours: float = 0.0
    explanation_atoms: list[str] = field(default_factory=list)


class CalendarWorldModel:
    """Small deterministic world model used to make policy imagination visible.

    In production this is the place where a learned DiffusionGemma world model
    would sample futures. Here it emits a falsifiable sketch and annotates the
    candidate so Codex and self-play can argue with it.
    """

    def sketch(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> WorldSketch:
        action_types = {a.action_type for a in candidate.actions}
        delta_minutes = sum(_duration_minutes(a) for a in candidate.actions)
        people_count = len(set(candidate.affected_people_ids))
        risk_cliffs = list(signals.risk_cliffs)
        atoms: list[str] = []

        if AtomicActionType.CREATE_EVENT in action_types and candidate.intent == "create_prep_block":
            thesis = "convert meeting pressure into a nearby prep buffer"
            counterfactual = "Without a prep block, the meeting stays naked and preparation competes with ambient admin work."
            upside = "The action creates a concrete runway before the external call."
            decay = 2.5
            atoms.append("prep-near-meeting usually decays quickly after the morning planning window")
        elif AtomicActionType.ADD_BUFFER in action_types:
            thesis = "buy travel/setup slack around a higher-cost event"
            counterfactual = "Without a buffer, the calendar looks free while the transition cost remains hidden."
            upside = "The action turns invisible transition time into reversible calendar reality."
            decay = 4.0
            atoms.append("transition buffers matter most before the day hardens")
        elif AtomicActionType.MOVE_EVENT in action_types:
            thesis = "move flexible user-owned time away from a pressure cliff"
            counterfactual = "Without the move, a flexible hold keeps occupying the hour most useful for repair."
            upside = "The action changes the shape of the day without negotiating with other people."
            decay = 6.0
            atoms.append("moving a user-owned hold is safer than touching a people meeting")
        elif AtomicActionType.CREATE_FOCUS_BLOCK in action_types:
            thesis = "protect a high-yield gap before the day becomes fragmented"
            counterfactual = "Without protection, the open slot remains attractive to later demands."
            upside = "The action turns an exposed gap into a defended work window."
            decay = 8.0
            atoms.append("focus protection has long-horizon value but moderate opportunity cost")
        elif AtomicActionType.DRAFT_SCHEDULE_PLAN in action_types:
            thesis = "bundle several small repairs into a reviewable plan"
            counterfactual = "Without a plan, each small repair competes separately for attention."
            upside = "The action lets the user approve a coherent reshaping instead of scattered prompts."
            decay = 12.0
            atoms.append("plans are slower but reduce notification spray")
        else:
            thesis = "preserve the current calendar as the counterfactual baseline"
            counterfactual = "Doing nothing is the control arm for self-play and offline evaluation."
            upside = "No actuation risk is introduced."
            decay = 0.0
            atoms.append("baseline keeps the simulator honest")

        if people_count > 0:
            atoms.append(f"{people_count} affected person signal(s) raise social-risk scrutiny")
        if signals.fatigue_score > 0.55:
            atoms.append("low interruption tolerance pushes the policy toward draft, digest, or silent write")
        if biography.ask_before_people_meetings and people_count and candidate.required_authority_tier >= 5:
            risk_cliffs.append("people_meeting_requires_question")

        return WorldSketch(
            thesis=thesis,
            counterfactual=counterfactual,
            upside=upside,
            risk_cliffs=risk_cliffs,
            schedule_delta_minutes=delta_minutes,
            affected_people_count=people_count,
            value_decay_hours=decay,
            explanation_atoms=atoms,
        )

    def annotate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        biography: UserBiography,
        signals: CalendarSignals,
    ) -> CandidateCalendarAction:
        sketch = self.sketch(candidate, observation, biography, signals)
        candidate.counterfactual = sketch.counterfactual
        candidate.model_story = [
            f"Hypothesis: {sketch.thesis}.",
            sketch.upside,
            *signals.narrative[:2],
        ]
        candidate.control_notes.extend(sketch.explanation_atoms)
        if sketch.risk_cliffs:
            candidate.control_notes.append("risk_cliffs=" + ",".join(sorted(set(sketch.risk_cliffs))))
        # Lightweight score shaping from the imagined future.
        if sketch.value_decay_hours and candidate.intent != "do_nothing":
            candidate.predicted_long_horizon_value = min(1.0, candidate.predicted_long_horizon_value + 0.03)
        if sketch.affected_people_count:
            candidate.predicted_social_risk = min(1.0, candidate.predicted_social_risk + 0.03 * sketch.affected_people_count)
        return candidate


def _duration_minutes(action) -> int:
    if action.start is None or action.end is None:
        return 0
    return max(0, int((action.end - action.start).total_seconds() // 60))