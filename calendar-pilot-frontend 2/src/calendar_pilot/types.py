from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


def parse_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def to_jsonable(obj: Any) -> Any:
    """Convert contract dataclasses/enums/datetimes into JSON-ready values."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    return obj


def string_metadata(data: dict[str, Any] | None) -> dict[str, str]:
    """Canonical cross-runtime metadata is string:string.

    Earlier Python-only candidates used arbitrary lists/dicts here. Swift uses a
    deterministic Codable map, so policy code now serializes compound metadata as
    compact comma-delimited strings before it crosses the contract boundary.
    """
    out: dict[str, str] = {}
    for key, value in (data or {}).items():
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            out[str(key)] = ",".join(str(v) for v in value)
        else:
            out[str(key)] = str(value)
    return out


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


class ActuationMode(str, Enum):
    NO_OP = "no_op"
    MATERIALIZED_WRITE = "materialized_write"
    STAGED_DRAFT = "staged_draft"
    STAGED_NOTIFICATION = "staged_notification"
    DENIED = "denied"


class StageState(str, Enum):
    SIMULATED = "simulated"
    STAGEABLE = "stageable"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    DENIED = "denied"
    COMMITTED = "committed"
    NO_OP = "no_op"


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
        start = parse_dt(data["start"])
        end = parse_dt(data["end"])
        assert isinstance(start, datetime) and isinstance(end, datetime)
        return cls(
            event_id=data["event_id"],
            title=data.get("title", ""),
            start=start,
            end=end,
            calendar_id=data.get("calendar_id", "default"),
            attendees=[str(x) for x in data.get("attendees", [])],
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
        return cls(
            task_id=data["task_id"],
            title=data.get("title", ""),
            due=parse_dt(data.get("due")),
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
        observed_at = parse_dt(data["observed_at"])
        assert isinstance(observed_at, datetime)
        return cls(
            observation_id=data["observation_id"],
            user_scope_id=data.get("user_scope_id", "default_user"),
            observed_at=observed_at,
            time_zone_id=data.get("time_zone_id", "UTC"),
            events=[RawCalendarEvent.from_dict(e) for e in data.get("events", [])],
            tasks=[RawTask.from_dict(t) for t in data.get("tasks", [])],
            device_context=DeviceContext.from_dict(data.get("device_context")),
            notification_history=list(data.get("notification_history", [])),
            prior_actions=list(data.get("prior_actions", [])),
        )


@dataclass(frozen=True)
class CorrectionProvenance:
    source: str
    surface: str
    created_at: datetime
    note: str = ""


@dataclass(frozen=True)
class ProfileUpdateEvent:
    update_id: str
    user_scope_id: str
    claim: str
    prior_confidence: float
    next_confidence: float
    reason: str
    provenance: CorrectionProvenance
    decay_applied: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class BiographyRepairPlan:
    prompt: str
    candidate_claim: str
    suggested_confidence: float
    provenance: CorrectionProvenance


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
    profile_update_events: list[dict[str, Any]] = field(default_factory=list)
    last_profile_update_at: Optional[datetime] = None

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
            profile_update_events=list(data.get("profile_update_events", [])),
            last_profile_update_at=parse_dt(data.get("last_profile_update_at")),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

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
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AtomicCalendarAction":
        return cls(
            action_type=AtomicActionType(data.get("action_type", "do_nothing")),
            title=data.get("title", ""),
            event_id=data.get("event_id"),
            start=parse_dt(data.get("start")),
            end=parse_dt(data.get("end")),
            calendar_id=data.get("calendar_id", "default"),
            attendees=[str(x) for x in data.get("attendees", [])],
            metadata=string_metadata(data.get("metadata")),
        )


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

    # Canonical cross-runtime inspection fields. Swift, JSON Schema, replay, and
    # Codex all read/write these; they are no longer Python-local convenience data.
    model_story: list[str] = field(default_factory=list)
    counterfactual: str = ""
    control_notes: list[str] = field(default_factory=list)
    reward_breakdown: dict[str, float] = field(default_factory=dict)
    right_moment_score: float = 0.0
    simulated_outcomes: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateCalendarAction":
        return cls(
            candidate_id=data["candidate_id"],
            intent=data.get("intent", "unknown"),
            actions=[AtomicCalendarAction.from_dict(a) for a in data.get("actions", [])],
            target_calendars=[str(x) for x in data.get("target_calendars", [])],
            affected_event_ids=[str(x) for x in data.get("affected_event_ids", [])],
            affected_people_ids=[str(x) for x in data.get("affected_people_ids", [])],
            reversibility=Reversibility(data.get("reversibility", "none")),
            required_authority_tier=int(data.get("required_authority_tier", 0)),
            predicted_acceptance=float(data.get("predicted_acceptance", 0.0)),
            predicted_utility=float(data.get("predicted_utility", 0.0)),
            predicted_engagement=float(data.get("predicted_engagement", 0.0)),
            predicted_regret=float(data.get("predicted_regret", 0.0)),
            predicted_interruption_cost=float(data.get("predicted_interruption_cost", 0.0)),
            predicted_social_risk=float(data.get("predicted_social_risk", 0.0)),
            predicted_long_horizon_value=float(data.get("predicted_long_horizon_value", 0.0)),
            expected_reward=float(data.get("expected_reward", 0.0)),
            recommended_execution_time=parse_dt(data.get("recommended_execution_time")),
            right_moment_decision=RightMomentDecision(data.get("right_moment_decision", "do_nothing")),
            explanation=data.get("explanation", ""),
            model_story=[str(x) for x in data.get("model_story", [])],
            counterfactual=data.get("counterfactual", ""),
            control_notes=[str(x) for x in data.get("control_notes", [])],
            reward_breakdown={str(k): float(v) for k, v in data.get("reward_breakdown", {}).items()},
            right_moment_score=float(data.get("right_moment_score", 0.0)),
            simulated_outcomes={str(k): float(v) for k, v in data.get("simulated_outcomes", {}).items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class AuthorityGrant:
    """Swift-issued authority object for machine acting.

    Codex and Python policy may request actions, but they cannot mint authority.
    A grant is issued by Swift with a maximum tier, scoped action/calendar
    permissions, expiry, and confirmation provenance. Integer authority tiers in
    tool calls are treated only as desired tier hints; materialization must see a
    live grant.
    """

    grant_id: str
    user_scope_id: str
    max_authority_tier: int
    scopes: list[str]
    issued_at: datetime
    expires_at: datetime
    confirmation_provenance: str
    issued_by: str = "SwiftKernelStub"
    confirmed_by_user: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthorityGrant":
        issued_at = parse_dt(data.get("issued_at")) or datetime.now()
        expires_at = parse_dt(data.get("expires_at")) or issued_at
        return cls(
            grant_id=str(data["grant_id"]),
            user_scope_id=str(data.get("user_scope_id", "default_user")),
            max_authority_tier=int(data.get("max_authority_tier", 0)),
            scopes=[str(x) for x in data.get("scopes", [])],
            issued_at=issued_at,
            expires_at=expires_at,
            confirmation_provenance=str(data.get("confirmation_provenance", "")),
            issued_by=str(data.get("issued_by", "SwiftKernelStub")),
            confirmed_by_user=bool(data.get("confirmed_by_user", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    def is_live_at(self, when: datetime) -> bool:
        return self.issued_at <= when <= self.expires_at

    def allows_scope(self, scope: str) -> bool:
        return "*" in self.scopes or scope in self.scopes


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
    staged_action_ids: list[str] = field(default_factory=list)
    rejected_action_types: list[str] = field(default_factory=list)
    provider_id: str = "local_stub"
    actuation_mode: ActuationMode = ActuationMode.NO_OP
    denied_reason: Optional[str] = None
    authority_grant_id: Optional[str] = None
    confirmation_provenance: Optional[str] = None
    stage_state: StageState = StageState.NO_OP
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


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

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


class CodexToolName(str, Enum):
    INSPECT_WEEK = "inspect_week"
    INSPECT_EVENT = "inspect_event"
    INSPECT_OPEN_SLOTS = "inspect_open_slots"
    INSPECT_AUTHORITY_SCOPE = "inspect_authority_scope"
    GENERATE_CANDIDATE_FRONTIER = "generate_candidate_frontier"
    SIMULATE_ACTION_PROGRAM = "simulate_action_program"
    COMPARE_CANDIDATES = "compare_candidates"
    STAGE_ACTION_PACKET = "stage_action_packet"
    REQUEST_COMMIT = "request_commit"
    REQUEST_UNDO = "request_undo"
    QUERY_REPLAY_TRACE = "query_replay_trace"
    INSPECT_PROFILE_CLAIMS = "inspect_profile_claims"
    PROPOSE_PROFILE_PATCH = "propose_profile_patch"
    APPLY_PROFILE_PATCH = "apply_profile_patch"
    RUN_SELF_PLAY_PROBE = "run_self_play_probe"
    PROPOSE_AUTONOMY_SCOPE = "propose_autonomy_scope"
    EXPLAIN_SWIFT_DENIAL = "explain_swift_denial"
    VALIDATE_MODEL_PLAN = "validate_model_plan"


class CodexToolStatus(str, Enum):
    SUCCEEDED = "succeeded"
    SIMULATED = "simulated"
    STAGEABLE = "stageable"
    STAGED = "staged"
    COMMITTED = "committed"
    DENIED = "denied"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    FAILED = "failed"


@dataclass(frozen=True)
class CodexToolCall:
    tool_call_id: str
    tool_name: CodexToolName
    input: dict[str, Any]
    requested_authority_tier: int = 0
    user_visible_reason: str = ""
    authority_grant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodexToolCall":
        created = parse_dt(data.get("created_at")) or datetime.now()
        input_payload = dict(data.get("input", {}))
        # Legacy payload compatibility: an embedded AuthorityGrant is not parsed
        # as authority. At most, its id is copied into the non-authoritative input
        # payload for diagnostics; the kernel still resolves only issued grant IDs.
        embedded = data.get("authority_grant")
        grant_id = data.get("authority_grant_id")
        if grant_id is None and isinstance(input_payload.get("authority_grant_id"), str):
            grant_id = input_payload.get("authority_grant_id")
        if grant_id is None and isinstance(embedded, dict) and embedded.get("grant_id"):
            input_payload.setdefault("embedded_authority_grant_id", embedded.get("grant_id"))
        return cls(
            tool_call_id=data["tool_call_id"],
            tool_name=CodexToolName(data.get("tool_name", "inspect_week")),
            input=input_payload,
            requested_authority_tier=int(data.get("requested_authority_tier", 0)),
            user_visible_reason=data.get("user_visible_reason", ""),
            authority_grant_id=str(grant_id) if grant_id is not None else None,
            correlation_id=data.get("correlation_id"),
            created_at=created,
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class CodexToolReceipt:
    tool_call_id: str
    tool_name: CodexToolName
    status: CodexToolStatus
    output: dict[str, Any]
    swift_receipt_id: Optional[str] = None
    replay_record_id: Optional[str] = None
    denied_reason: Optional[str] = None
    requires_user_confirmation: bool = False
    stage_state: StageState = StageState.NO_OP
    authority_grant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodexToolReceipt":
        created = parse_dt(data.get("created_at")) or datetime.now()
        return cls(
            tool_call_id=data["tool_call_id"],
            tool_name=CodexToolName(data.get("tool_name", "inspect_week")),
            status=CodexToolStatus(data.get("status", "succeeded")),
            output=dict(data.get("output", {})),
            swift_receipt_id=data.get("swift_receipt_id"),
            replay_record_id=data.get("replay_record_id"),
            denied_reason=data.get("denied_reason"),
            requires_user_confirmation=bool(data.get("requires_user_confirmation", False)),
            stage_state=StageState(data.get("stage_state", "no_op")),
            authority_grant_id=data.get("authority_grant_id"),
            correlation_id=data.get("correlation_id"),
            created_at=created,
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class CodexAutonomyScopeProposal:
    scope_id: str
    candidate_id: str
    allowed_action_types: list[str]
    max_authority_tier: int
    excluded_social_mutations: bool
    requires_confirmation_for_people: bool
    rollback_required: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(frozen=True)
class PolicyTuning:
    tuning_id: str = "default"
    intent_reward_bias: dict[str, float] = field(default_factory=dict)
    failure_penalties: dict[str, float] = field(default_factory=dict)
    denied_intents: list[str] = field(default_factory=list)
    source_report: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyTuning":
        return cls(
            tuning_id=data.get("tuning_id", "default"),
            intent_reward_bias={str(k): float(v) for k, v in data.get("intent_reward_bias", {}).items()},
            failure_penalties={str(k): float(v) for k, v in data.get("failure_penalties", {}).items()},
            denied_intents=[str(x) for x in data.get("denied_intents", [])],
            source_report=data.get("source_report", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)
