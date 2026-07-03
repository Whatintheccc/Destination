from __future__ import annotations

from enum import Enum
from typing import Any


class CanonicalIntent(str, Enum):
    PROTECT_DEEP_WORK = "protect_deep_work"
    CREATE_PREP_BLOCK = "create_prep_block"
    ADD_BUFFER = "add_buffer"
    BATCH_ADMIN = "batch_admin"
    RESCHEDULE_CONFLICT = "reschedule_conflict"
    MOVE_MEETING = "move_meeting"
    DECLINE_OR_TRIM = "decline_or_trim"
    NOTIFY_SUMMARY = "notify_summary"
    ASK_CLARIFICATION = "ask_clarification"
    DO_NOTHING = "do_nothing"
    OTHER = "other"


_KEYWORD_MAP: list[tuple[CanonicalIntent, tuple[str, ...]]] = [
    (CanonicalIntent.PROTECT_DEEP_WORK, ("deep work", "focus block", "focus window", "protect focus", "focus time", "focus")),
    (CanonicalIntent.CREATE_PREP_BLOCK, ("prep", "prepare", "preparation", "runway", "before the call", "before call")),
    (CanonicalIntent.ADD_BUFFER, ("buffer", "transition", "breathing room", "gap between", "travel", "slack")),
    (CanonicalIntent.BATCH_ADMIN, ("batch", "admin", "inbox", "errand", "expenses", "grouped tasks", "task batch")),
    (CanonicalIntent.RESCHEDULE_CONFLICT, ("conflict", "overlap", "double book", "double-book", "collision")),
    (CanonicalIntent.MOVE_MEETING, ("move", "reschedule", "shift", "move_flexible", "flexible hold")),
    (CanonicalIntent.DECLINE_OR_TRIM, ("decline", "shorten", "trim", "cancel")),
    (CanonicalIntent.NOTIFY_SUMMARY, ("notify", "digest", "summary", "reminder")),
    (CanonicalIntent.ASK_CLARIFICATION, ("clarif", "confirm preference", "ask the user", "question")),
    (CanonicalIntent.DO_NOTHING, ("do nothing", "no action", "preserve", "baseline")),
]

_ALIASES: dict[str, CanonicalIntent] = {
    "add_transition_buffer": CanonicalIntent.ADD_BUFFER,
    "transition_buffer": CanonicalIntent.ADD_BUFFER,
    "protect_focus_window": CanonicalIntent.PROTECT_DEEP_WORK,
    "focus_window": CanonicalIntent.PROTECT_DEEP_WORK,
    "batch_admin_tasks": CanonicalIntent.BATCH_ADMIN,
    "move_flexible_hold": CanonicalIntent.MOVE_MEETING,
    "create_focus_block": CanonicalIntent.PROTECT_DEEP_WORK,
    "prep_block": CanonicalIntent.CREATE_PREP_BLOCK,
    "draft_day_repair_plan": CanonicalIntent.ASK_CLARIFICATION,
    "draft_schedule_plan": CanonicalIntent.ASK_CLARIFICATION,
    "calendar_repair_plan": CanonicalIntent.ASK_CLARIFICATION,
}


def normalize_intent(raw: str | None) -> dict[str, str]:
    """Map model/free-text intent into a bounded training taxonomy.

    Returns both the canonical value and the raw value so learning can accumulate
    while dogfood inspection remains lossless.
    """
    original = "" if raw is None else str(raw)
    text = " ".join(original.lower().strip().replace("-", "_").split())
    compact = text.replace(" ", "_")
    for enum_value in CanonicalIntent:
        if compact == enum_value.value:
            return {"intent": enum_value.value, "intent_raw": original, "matched_by": "exact"}
    if compact in _ALIASES:
        return {"intent": _ALIASES[compact].value, "intent_raw": original, "matched_by": "alias"}
    loose = text.replace("_", " ")
    for intent, needles in _KEYWORD_MAP:
        if any(needle in loose for needle in needles):
            return {"intent": intent.value, "intent_raw": original, "matched_by": "keyword"}
    return {"intent": CanonicalIntent.OTHER.value, "intent_raw": original, "matched_by": "fallback"}


def taxonomy_health(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    total = max(1, len(candidates))
    matched_by: dict[str, int] = {}
    other = 0
    for candidate in candidates:
        intent = str(candidate.get("intent") or "")
        raw = str(candidate.get("intent_raw") or intent)
        match = str(candidate.get("intent_matched_by") or normalize_intent(raw)["matched_by"])
        matched_by[match] = matched_by.get(match, 0) + 1
        if intent == CanonicalIntent.OTHER.value:
            other += 1
    return {"other_rate": round(other / total, 4), "matched_by": matched_by, "count": len(candidates)}
