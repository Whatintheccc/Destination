from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


def parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    # Python accepts +00:00 but not trailing Z in all versions.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class AtomicActionType(str, Enum):
    DO_NOTHING = "do_nothing"
    NOTIFY = "notify"
    ASK_CLARIFICATION = "ask_clarification"
    CREATE_EVENT = "create_event"
    MOVE_EVENT = "move_event"
    RESIZE_EVENT = "resize_event"
    DELETE_OWN_EVENT = "delete_own_event"
    ADD_BUFFER = "add_buffer"
    CREATE_FOCUS_BLOCK = "create_focus_block"
    BATCH_TASKS = "batch_tasks"
    DRAFT_SCHEDULE_PLAN = "draft_schedule_plan"
    AUTO_APPLY_PLAN = "auto_apply_plan"
    UNDO = "undo"


class Reversibility(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RightMomentDecision(str, Enum):
    ACT_NOW = "act_now"
    NOTIFY_NOW = "notify_now"
    WAIT = "wait"
    BUNDLE_INTO_DIGEST = "bundle_into_digest"
    SILENTLY_DRAFT = "silently_draft"
    AUTO_WRITE_THEN_NOTIFY = "auto_write_then_notify"
    ASK_CLARIFICATION = "ask_clarification"
    DO_NOTHING = "do_nothing"


@dataclass(frozen=True)
class RawCalendarEvent:
    event_id: str
    title: str
    start: datetime
    end: datetime
    calendar_id: str
    attendees: list[str] = field(default_factory=list)
    location: str = ""
    notes: str = ""
    is_user_owned: bool = False
    is_flexible: bool = False
    category: str = "unknown"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawCalendarEvent":
        return cls(
            event_id=data["event_id"],
            title=data.get("title", ""),
            start=parse_dt(data["start"]),
            end=parse_dt(data["end"]),
            calendar_id=data.get("calendar_id", "default"),
            attendees=list(data.get("attendees", [])),
            location=data.get("location", ""),
            notes=data.get("notes", ""),
            is_user_owned=bool(data.get("is_user_owned", False)),
            is_flexible=bool(data.get("is_flexible", False)),
            category=data.get("category", "unknown"),
        )


@dataclass(frozen=True)
class RawTask:
    task_id: str
    title: str
    due: Optional[datetime]
    estimated_minutes: int
    category: str = "unknown"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawTask":
        due = data.get("due")
        return cls(
            task_id=data["task_id"],
            title=data.get("title", ""),
            due=parse_dt(due) if due else None,
            estimated_minutes=int(data.get("estimated_minutes", 30)),
            category=data.get("category", "unknown"),
        )


@dataclass(frozen=True)
class DeviceContext:
    local_hour: int = 9
    active_surface: str = "unknown"
    is_focus_mode: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "DeviceContext":
        data = data or {}
        return cls(
            local_hour=int(data.get("local_hour", 9)),
            active_surface=data.get("active_surface", "unknown"),
            is_focus_mode=bool(data.get("is_focus_mode", False)),
        )


@dataclass(frozen=True)
class RawCalendarObservation:
    observation_id: str
    user_scope_id: str
    observed_at: datetime
    time_zone_id: str
    events: list[RawCalendarEvent]
    tasks: list[RawTask] = field(default_factory=list)
    device_context: DeviceContext = field(default_factory=DeviceContext)
    notification_history: list[dict[str, Any]] = field(default_factory=list)
    prior_actions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawCalendarObservation":
        return cls(
            observation_id=data["observation_id"],
            user_scope_id=data.get("user_scope_id", "default_user"),
            observed_at=parse_dt(data["observed_at"]),
            time_zone_id=data.get("time_zone_id", "UTC"),
            events=[RawCalendarEvent.from_dict(e) for e in data.get("events", [])],
            tasks=[RawTask.from_dict(t) for t in data.get("tasks", [])],
            device_context=DeviceContext.from_dict(data.get("device_context")),
            notification_history=list(data.get("notification_history", [])),
            prior_actions=list(data.get("prior_actions", [])),
        )


@dataclass
class UserBiography:
    user_scope_id: str
    deep_work_windows: list[str] = field(default_factory=list)
    admin_windows: list[str] = field(default_factory=list)
    best_response_hours: list[int] = field(default_factory=lambda: [8, 13])
    bad_response_hours: list[int] = field(default_factory=lambda: [20, 21, 22, 23])
    auto_create_travel_buffers: bool = False
    auto_move_flexible_holds: bool = False
    ask_before_people_meetings: bool = True
    notification_fatigue: float = 0.0
    preference_claims: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserBiography":
        return cls(
            user_scope_id=data.get("user_scope_id", "default_user"),
            deep_work_windows=list(data.get("deep_work_windows", [])),
            admin_windows=list(data.get("admin_windows", [])),
            best_response_hours=[int(x) for x in data.get("best_response_hours", [8, 13])],
            bad_response_hours=[int(x) for x in data.get("bad_response_hours", [20, 21, 22, 23])],
            auto_create_travel_buffers=bool(data.get("auto_create_travel_buffers", False)),
            auto_move_flexible_holds=bool(data.get("auto_move_flexible_holds", False)),
            ask_before_people_meetings=bool(data.get("ask_before_people_meetings", True)),
            notification_fatigue=float(data.get("notification_fatigue", 0.0)),
            preference_claims=list(data.get("preference_claims", [])),
        )

    def confidence_for(self, phrase: str) -> float:
        phrase_l = phrase.lower()
        matches = [c for c in self.preference_claims if phrase_l in c.get("claim", "").lower()]
        if not matches:
            return 0.5
        return max(float(c.get("confidence", 0.5)) for c in matches)

    def has_claim(self, *phrases: str) -> bool:
        haystack = " ".join(c.get("claim", "") for c in self.preference_claims).lower()
        return any(p.lower() in haystack for p in phrases)


@dataclass(frozen=True)
class AtomicCalendarAction:
    action_type: AtomicActionType
    title: str = ""
    event_id: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    calendar_id: str = "default"
    attendees: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateCalendarAction:
    candidate_id: str
    intent: str
    actions: list[AtomicCalendarAction]
    target_calendars: list[str]
    affected_event_ids: list[str]
    affected_people_ids: list[str]
    reversibility: Reversibility
    required_authority_tier: int
    predicted_acceptance: float = 0.0
    predicted_utility: float = 0.0
    predicted_engagement: float = 0.0
    predicted_regret: float = 0.0
    predicted_interruption_cost: float = 0.0
    predicted_social_risk: float = 0.0
    predicted_long_horizon_value: float = 0.0
    expected_reward: float = 0.0
    recommended_execution_time: Optional[datetime] = None
    right_moment_decision: RightMomentDecision = RightMomentDecision.DO_NOTHING
    explanation: str = ""

    # Revised agent-loop fields. These make policy output inspectable instead of
    # a dry scalar: the policy carries a hypothesis, a counterfactual, and the
    # reward anatomy that made the action win.
    model_story: list[str] = field(default_factory=list)
    counterfactual: str = ""
    control_notes: list[str] = field(default_factory=list)
    reward_breakdown: dict[str, float] = field(default_factory=dict)
    right_moment_score: float = 0.0
    simulated_outcomes: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def convert(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            if hasattr(obj, "__dataclass_fields__"):
                return {k: convert(v) for k, v in asdict(obj).items()}
            if isinstance(obj, list):
                return [convert(x) for x in obj]
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            return obj
        return convert(self)


@dataclass(frozen=True)
class CalendarActionReceipt:
    receipt_id: str
    candidate_id: str
    executed_at: datetime
    executed_by: str
    authority_tier_used: int
    sync_status: str
    rollback_handle_id: Optional[str]
    conflict_check_passed: bool
    generated_event_ids: list[str] = field(default_factory=list)
    denied_reason: Optional[str] = None


@dataclass(frozen=True)
class RewardEvent:
    reward_event_id: str
    receipt_id: str
    observed_at: datetime
    accepted: Optional[bool] = None
    edited: Optional[bool] = None
    undone: Optional[bool] = None
    deleted_later: Optional[bool] = None
    ignored: Optional[bool] = None
    explicit_useful: Optional[bool] = None
    explicit_wrong: Optional[bool] = None
    explicit_not_needed: Optional[bool] = None
    notification_dismissed: Optional[bool] = None
    survived_until_event: Optional[bool] = None
    downstream_conflict: Optional[bool] = None
    reengaged: Optional[bool] = None
    utility_reward: float = 0.0
    acceptance_reward: float = 0.0
    engagement_reward: float = 0.0
    regret_penalty: float = 0.0
    interruption_penalty: float = 0.0
    social_risk_penalty: float = 0.0
    total_reward: float = 0.0
