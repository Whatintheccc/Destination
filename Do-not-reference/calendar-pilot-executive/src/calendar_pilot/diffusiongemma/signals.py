from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from calendar_pilot.types import RawCalendarEvent, RawCalendarObservation, UserBiography


@dataclass(frozen=True)
class OpenSlot:
    start: datetime
    end: datetime
    minutes: int
    label: str


@dataclass(frozen=True)
class CalendarSignals:
    """A compact, inspectable read of raw calendar state.

    This is not privacy-minimized; it is the agentic optimizer's scratch view.
    It exists so the policy can be more than a pile of if-statements while still
    being testable and serializable.
    """

    external_meeting_count: int
    internal_meeting_count: int
    flexible_hold_count: int
    admin_task_minutes: int
    prep_task_minutes: int
    occupied_minutes_workday: int
    open_slots: list[OpenSlot] = field(default_factory=list)
    pressure_score: float = 0.0
    fatigue_score: float = 0.0
    best_response_is_now: bool = False
    active_surface: str = "unknown"
    risk_cliffs: list[str] = field(default_factory=list)
    narrative: list[str] = field(default_factory=list)

    def slot_after(self, anchor: datetime, minutes: int) -> OpenSlot | None:
        for slot in self.open_slots:
            if slot.start >= anchor and slot.minutes >= minutes:
                return slot
        return None


def extract_signals(observation: RawCalendarObservation, biography: UserBiography) -> CalendarSignals:
    events = sorted(observation.events, key=lambda e: e.start)
    external = [e for e in events if e.category == "external_meeting"]
    internal = [e for e in events if e.category == "internal_meeting"]
    flexible = [e for e in events if e.is_user_owned and e.is_flexible]
    admin_minutes = sum(t.estimated_minutes for t in observation.tasks if t.category == "admin")
    prep_minutes = sum(t.estimated_minutes for t in observation.tasks if t.category == "prep")
    work_start = observation.observed_at.replace(hour=8, minute=0, second=0, microsecond=0)
    work_end = observation.observed_at.replace(hour=18, minute=0, second=0, microsecond=0)
    open_slots = _open_slots(events, work_start, work_end)
    occupied = _occupied_minutes(events, work_start, work_end)
    fatigue = _fatigue(observation, biography)
    pressure = _pressure(events, external, admin_minutes, prep_minutes, occupied)
    risks: list[str] = []
    if external and prep_minutes:
        risks.append("external_meeting_without_preparation_space")
    if occupied > 7 * 60:
        risks.append("workday_density_high")
    if fatigue > 0.65:
        risks.append("notification_fatigue_high")
    if any(e.end > s.start and e.end <= s.start + timedelta(minutes=60) for e in flexible for s in external):
        risks.append("flexible_hold_near_external_meeting")
    narrative = _narrative(external, internal, flexible, admin_minutes, prep_minutes, occupied, open_slots, fatigue, pressure)
    return CalendarSignals(
        external_meeting_count=len(external),
        internal_meeting_count=len(internal),
        flexible_hold_count=len(flexible),
        admin_task_minutes=admin_minutes,
        prep_task_minutes=prep_minutes,
        occupied_minutes_workday=occupied,
        open_slots=open_slots,
        pressure_score=pressure,
        fatigue_score=fatigue,
        best_response_is_now=observation.device_context.local_hour in biography.best_response_hours,
        active_surface=observation.device_context.active_surface,
        risk_cliffs=risks,
        narrative=narrative,
    )


def _open_slots(events: list[RawCalendarEvent], start: datetime, end: datetime) -> list[OpenSlot]:
    cursor = start
    slots: list[OpenSlot] = []
    for event in sorted(events, key=lambda e: e.start):
        if event.end <= start or event.start >= end:
            continue
        event_start = max(event.start, start)
        event_end = min(event.end, end)
        if event_start > cursor:
            minutes = int((event_start - cursor).total_seconds() // 60)
            if minutes >= 15:
                slots.append(OpenSlot(cursor, event_start, minutes, _slot_label(cursor)))
        cursor = max(cursor, event_end)
    if cursor < end:
        minutes = int((end - cursor).total_seconds() // 60)
        if minutes >= 15:
            slots.append(OpenSlot(cursor, end, minutes, _slot_label(cursor)))
    return slots


def _occupied_minutes(events: list[RawCalendarEvent], start: datetime, end: datetime) -> int:
    minutes = 0
    for event in events:
        overlap_start = max(start, event.start)
        overlap_end = min(end, event.end)
        if overlap_end > overlap_start:
            minutes += int((overlap_end - overlap_start).total_seconds() // 60)
    return minutes


def _fatigue(observation: RawCalendarObservation, biography: UserBiography) -> float:
    recent_dismissals = sum(1 for n in observation.notification_history if n.get("outcome") in {"dismissed", "ignored"})
    return min(1.0, biography.notification_fatigue + 0.06 * recent_dismissals)


def _pressure(
    events: list[RawCalendarEvent],
    external: list[RawCalendarEvent],
    admin_minutes: int,
    prep_minutes: int,
    occupied_minutes: int,
) -> float:
    raw = (
        0.18 * len(external)
        + 0.10 * len(events)
        + min(0.20, admin_minutes / 300.0)
        + min(0.15, prep_minutes / 240.0)
        + min(0.35, occupied_minutes / 600.0)
    )
    return round(min(1.0, raw), 3)


def _slot_label(start: datetime) -> str:
    if start.hour < 11:
        return "morning"
    if start.hour < 14:
        return "midday"
    if start.hour < 17:
        return "afternoon"
    return "late_day"


def _narrative(
    external: list[RawCalendarEvent],
    internal: list[RawCalendarEvent],
    flexible: list[RawCalendarEvent],
    admin_minutes: int,
    prep_minutes: int,
    occupied: int,
    open_slots: list[OpenSlot],
    fatigue: float,
    pressure: float,
) -> list[str]:
    lines = [f"Schedule pressure {pressure:.2f}: {occupied} occupied workday minutes and {len(open_slots)} usable gaps."]
    if external:
        lines.append(f"{len(external)} external meeting(s) create preparation and social-risk cliffs.")
    if internal:
        lines.append(f"{len(internal)} internal meeting(s) are movable only if authority and social cost allow it.")
    if flexible:
        lines.append(f"{len(flexible)} user-owned flexible hold(s) can absorb repair without touching other people.")
    if admin_minutes:
        lines.append(f"{admin_minutes} minutes of admin work can be batched instead of sprayed across the day.")
    if prep_minutes:
        lines.append(f"{prep_minutes} minutes of prep work becomes more valuable when placed near the related meeting.")
    if fatigue > 0.6:
        lines.append("Notification fatigue is elevated; acting silently or bundling beats interruption.")
    return lines
