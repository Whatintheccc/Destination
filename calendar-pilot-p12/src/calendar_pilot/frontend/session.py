

from __future__ import annotations

import atexit
import hashlib
import json
import os
import subprocess
import threading
import webbrowser
from dataclasses import dataclass, field
from functools import wraps
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from calendar_pilot.codex import CodexExecutivePlan, CodexToolPlanner, CodexToolRuntime, LiveCodexToolPlanner
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, LiveDiffusionGemmaPolicy, SelfPlayRunner
from calendar_pilot.providers import AppleEventKitProvider, DeterministicCalendarProvider
from calendar_pilot.providers.apple_eventkit import AppleEventKitManagedDriver
from calendar_pilot.effect_kernel import (
    ManagedCalendarBinding,
    ManagedEventKitRetirementProvider,
    managed_commit_confirmation_provenance,
)
from calendar_pilot.environment.session_store import SessionStore
from calendar_pilot.environment.invariants import check_replay
from calendar_pilot.environment.router import KeywordRouter, ModelIntentRouter
from calendar_pilot.environment.taxonomy import taxonomy_health
from calendar_pilot.environment.trace import TRACE_BUS
from calendar_pilot.frontend.projector import FrontendProjector
from calendar_pilot.frontend.session_conversation import (
    FrontendConversationTools,
    conversation_message_requests_candidate_correction,
    conversation_message_requests_calendar_observation,
    conversation_message_requests_existing_plan_followup,
    conversation_message_requests_noop_fixture,
    conversation_tool_metadata,
    normalize_conversation_message,
    profile_patch_payload_from_receipt,
)
from calendar_pilot.frontend.session_persistence import SessionPersistenceController
from calendar_pilot.frontend.session_snapshot import SessionSnapshotBuilder
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
from calendar_pilot.product_core import run_create_prep_block_vertical
from calendar_pilot.swift_bridge import SwiftKernelIPCClient, SwiftKernelStub
from calendar_pilot.swift_bridge.protocol import CalendarKernelProtocol
from calendar_pilot.types import (
    AuthorityGrant,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    CodexToolStatus,
    RawCalendarObservation,
    RewardEvent,
    UserBiography,
    to_jsonable,
)
from calendar_pilot.frontend.launch import LaunchConfig
from calendar_pilot.frontend.runtime import KNOWN_MODES, LIVE_CODEX_MODES, RuntimeBackends, runtime_mode_from_env, runtime_report, runtime_profile


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUTHORITY_TIER = 3
DEFAULT_AUTHORITY_SCOPES = ["recommend", "stage", "commit_private", "undo"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DogfoodSessionState:
    """Mutable backend session for local dogfood runs.

    The session keeps runtime state, visible history, replay, authority grants,
    and undo context together so browser and app launches can resume a run.
    """

    observation_path: Path = ROOT / "data" / "sample_calendar.json"
    profile_path: Path = ROOT / "data" / "sample_profile.json"
    run_dir: Path = ROOT / "runs" / "dogfood"
    session_id: str = field(default_factory=lambda: "sess_" + hashlib.sha1(str(_now()).encode()).hexdigest()[:10])
    authority_tier: int = DEFAULT_AUTHORITY_TIER
    authority_scopes: list[str] = field(default_factory=lambda: list(DEFAULT_AUTHORITY_SCOPES))
    runtime_mode: str = field(default_factory=runtime_mode_from_env)
    session_label: str | None = None
    archived_at: str | None = None
    launch_config: LaunchConfig = field(init=False)
    store: SessionStore = field(init=False)
    state_version: int = field(default=0, init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)

    observation: RawCalendarObservation = field(init=False)
    biography: UserBiography = field(init=False)
    kernel: CalendarKernelProtocol = field(init=False)
    policy: DiffusionGemmaPolicy | LiveDiffusionGemmaPolicy = field(init=False)
    provider: Any = field(init=False)
    replay: ReplayBuffer = field(init=False)
    runtime: CodexToolRuntime = field(init=False)
    planner: CodexToolPlanner = field(init=False)
    conversation: FrontendConversationTools = field(init=False, repr=False)
    persistence: SessionPersistenceController = field(init=False, repr=False)
    snapshot_builder: SessionSnapshotBuilder = field(init=False, repr=False)

    latest_plan: Any | None = None
    latest_plan_observation_id: str | None = None
    latest_plan_observation_fingerprint: str | None = None
    transcript_events: list[dict[str, Any]] = field(default_factory=list)
    feedback_history: list[dict[str, Any]] = field(default_factory=list)
    denial_history: list[dict[str, Any]] = field(default_factory=list)
    profile_patch_history: list[dict[str, Any]] = field(default_factory=list)
    self_play_history: list[dict[str, Any]] = field(default_factory=list)
    authority_history: list[dict[str, Any]] = field(default_factory=list)
    restore_error: str | None = None
    provider_observation_error: str | None = None

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self.state_version = 0
        self.router = KeywordRouter()
        self.projector = FrontendProjector(self)
        self.conversation = FrontendConversationTools(self)
        self.persistence = SessionPersistenceController(self)
        self.snapshot_builder = SessionSnapshotBuilder(self)
        self.observation_path = Path(self.observation_path)
        self.profile_path = Path(self.profile_path)
        self.run_dir = Path(self.run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.store = SessionStore(self.run_dir)
        self.launch_config = LaunchConfig.from_env(run_dir=self.run_dir, runtime_mode=self.runtime_mode)
        self.launch_config.write_manifest()
        self._load_primitives()
        self.kernel = self._new_kernel_for_mode()
        self.policy = self._new_policy_for_mode()
        self.provider = self._new_provider_for_mode()
        self._hydrate_provider_observation_if_available()
        self.replay = self.store.load_replay()
        self.replay.source_session_id = self.session_id
        self._rebuild_runtime()
        atexit.register(self.close)
        if not self.persistence.restore_session_state():
            ready_message = self.conversation.assistant_ready_message()
            self.transcript_events.append({
                "kind": "assistant",
                "title": ready_message["title"],
                "body": ready_message["body"],
                "metadata": ready_message["metadata"],
                "created_at": _now().isoformat(),
            })
            self.issue_authority_grant(confirmed=True, reason="dogfood_session_boot")
            self.persist()
        self.persistence.hydrate_runtime_frontier()
        self.persistence.write_launch_manifest_with_health()

    def _load_primitives(self) -> None:
        self.observation = RawCalendarObservation.from_dict(json.loads(self.observation_path.read_text(encoding="utf-8")))
        self.biography = UserBiography.from_dict(json.loads(self.profile_path.read_text(encoding="utf-8")))

    def _new_kernel_for_mode(self) -> CalendarKernelProtocol:
        requested_kernel = os.environ.get("CALENDAR_PILOT_KERNEL_BACKEND", "").strip().lower().replace("-", "_")
        if requested_kernel in {"stub", "swift_stub", "python_stub"}:
            return SwiftKernelStub()
        if requested_kernel in {"swift_ipc", "ipc"} or self.runtime_mode in {"auto", "swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}:
            kernel = SwiftKernelIPCClient()
            kernel.start()
            return kernel
        return SwiftKernelStub()

    def _replace_kernel_for_mode(self) -> None:
        self.close()
        self.kernel = self._new_kernel_for_mode()
        self.policy = self._new_policy_for_mode()
        self.provider = self._new_provider_for_mode()
        self._hydrate_provider_observation_if_available()
        if hasattr(self, "runtime"):
            self._rebuild_runtime()

    def _rebuild_runtime(self) -> None:
        self.runtime = CodexToolRuntime(policy=self.policy, kernel=self.kernel, replay=self.replay, provider=self.provider)
        self.planner = self._new_planner_for_mode()

    def _new_planner_for_mode(self) -> CodexToolPlanner | LiveCodexToolPlanner:
        if self.runtime_mode in LIVE_CODEX_MODES:
            return LiveCodexToolPlanner(runtime=self.runtime)
        return CodexToolPlanner(runtime=self.runtime)

    def _new_policy_for_mode(self) -> DiffusionGemmaPolicy | LiveDiffusionGemmaPolicy:
        if self.runtime_mode in {"live_diffusiongemma", "production"} or (self.runtime_mode == "auto" and self._nim_credentials_available()):
            return LiveDiffusionGemmaPolicy()
        return DiffusionGemmaPolicy()

    def _new_provider_for_mode(self) -> Any:
        explicit = os.environ.get("CALENDAR_PILOT_PROVIDER_BACKEND", "").strip().lower().replace("-", "_")
        if self.runtime_mode == "auto" and not explicit:
            eventkit = AppleEventKitProvider(state_path=self.run_dir / "apple_eventkit_provider.json")
            if eventkit.health_status().get("configured"):
                return self._managed_eventkit_provider(eventkit) or eventkit
            return DeterministicCalendarProvider(state_path=self.run_dir / "provider_state.json", seed_observation=self.observation)
        requested_provider = explicit or ("apple_eventkit" if self.runtime_mode in {"live_provider", "production"} else "deterministic")
        if requested_provider in {"stub", "local_stub", "none"}:
            return None
        if requested_provider in {"apple", "apple_eventkit", "ios_calendar", "macos_calendar", "eventkit"}:
            eventkit = AppleEventKitProvider(state_path=self.run_dir / "apple_eventkit_provider.json")
            return self._managed_eventkit_provider(eventkit) or eventkit
        return DeterministicCalendarProvider(state_path=self.run_dir / "provider_state.json", seed_observation=self.observation)

    def _managed_eventkit_provider(self, incumbent: AppleEventKitProvider) -> ManagedEventKitRetirementProvider | None:
        binding_file = os.environ.get("CALENDAR_PILOT_MANAGED_EVENTKIT_BINDING_FILE", "").strip()
        if not binding_file or self.runtime_mode == "production":
            return None
        binding_path = Path(binding_file).expanduser().resolve()
        payload = json.loads(binding_path.read_text(encoding="utf-8"))
        binding = ManagedCalendarBinding.from_dict(payload)
        state_root = Path(
            os.environ.get("CALENDAR_PILOT_MANAGED_EVENTKIT_STATE_ROOT", str(binding_path.parent / "effect-state"))
        ).expanduser().resolve()
        initialize = os.environ.get("CALENDAR_PILOT_MANAGED_EVENTKIT_INITIALIZE", "") in {"1", "true", "TRUE", "yes"}
        driver_factory = lambda row: AppleEventKitManagedDriver(
            incumbent,
            calendar_id=row.calendar_id,
            expected_binding=row,
        )
        return ManagedEventKitRetirementProvider(
            incumbent=incumbent,
            driver=driver_factory(binding),
            driver_factory=driver_factory,
            binding=binding,
            state_root=state_root,
            signing_key_path=state_root / "signing.key",
            lease_path=state_root / "owner.lock",
            seed_observation=self.observation,
            initialize=initialize,
            acquire_lease=True,
        )

    @staticmethod
    def _nim_credentials_available() -> bool:
        return any(os.environ.get(key) for key in ["CALENDAR_PILOT_NIM_API_KEY", "NVIDIA_API_KEY", "NIM_API_KEY"])

    def close(self) -> None:
        close = getattr(getattr(self, "kernel", None), "close", None)
        if callable(close):
            close()
        close_provider = getattr(getattr(self, "provider", None), "close", None)
        if callable(close_provider):
            close_provider()

    def reset(self) -> dict[str, Any]:
        self._load_primitives()
        self.policy = self._new_policy_for_mode()
        self.provider = self._new_provider_for_mode()
        self._hydrate_provider_observation_if_available()
        reset_provider = getattr(self.provider, "reset", None)
        if callable(reset_provider):
            reset_provider(self.observation)
        self.replay = ReplayBuffer(source_session_id=self.session_id)
        self.latest_plan = None
        self.latest_plan_observation_id = None
        self.latest_plan_observation_fingerprint = None
        self.authority_tier = DEFAULT_AUTHORITY_TIER
        self.authority_scopes = list(DEFAULT_AUTHORITY_SCOPES)
        self.runtime_mode = runtime_mode_from_env(self.runtime_mode)
        self._replace_kernel_for_mode()
        self.feedback_history.clear()
        self.denial_history.clear()
        self.profile_patch_history.clear()
        self.self_play_history.clear()
        self.authority_history.clear()
        self.transcript_events = [{
            "kind": "assistant",
            "title": "Reset complete",
            "body": "Fixture calendar, replay, candidate frontier, undo ledger, and session transcript were reset.",
            "created_at": _now().isoformat(),
        }]
        self.issue_authority_grant(confirmed=True, reason="dogfood_session_reset")
        self.persist()
        return self.snapshot()

    def issue_authority_grant(self, *, confirmed: bool, reason: str, tier: int | None = None, scopes: list[str] | None = None) -> AuthorityGrant:
        tier = int(self.authority_tier if tier is None else tier)
        scopes = list(scopes or self.authority_scopes)
        grant = self.kernel.issue_authority_grant(
            user_scope_id=self.observation.user_scope_id,
            max_authority_tier=tier,
            scopes=scopes,
            confirmation_provenance=reason,
            confirmed_by_user=confirmed,
            issued_at=self.observation.observed_at,
        )
        self.authority_history.append({"grant": grant.to_dict(), "reason": reason, "created_at": _now().isoformat()})
        return grant

    def _refresh_live_observation_for_confirmation(self, *, require_plan_match: bool) -> None:
        if not self._real_provider_active():
            return
        read_observation = getattr(self.provider, "read_observation", None)
        if not callable(read_observation):
            raise ValueError("confirmed live action requires a fresh provider observation")
        refreshed = read_observation(
            self.observation.user_scope_id,
            time_zone_id=self.observation.time_zone_id,
        )
        if require_plan_match:
            planned = self.latest_plan_observation_fingerprint
            if not planned or observation_fingerprint(refreshed) != planned:
                raise ValueError("calendar changed after planning; regenerate the candidate before confirming")
        self.observation = refreshed

    def latest_grant_id(self, *, confirmed: bool = False, scopes: list[str] | None = None) -> str:
        grants = list(self.kernel.authority_grants.values())
        scopes = scopes or []
        for grant in reversed(grants):
            if confirmed and not grant.confirmed_by_user:
                continue
            if any(not grant.allows_scope(scope) for scope in scopes):
                continue
            if grant.is_live_at(self.observation.observed_at):
                return grant.grant_id
        return self.issue_authority_grant(
            confirmed=False,
            scopes=self.authority_scopes + [s for s in scopes if s not in self.authority_scopes],
            reason="codex_ui_unconfirmed_grant",
        ).grant_id

    def create_plan(self, goal: str, *, commit: bool = False, authority_tier: int | None = None) -> dict[str, Any]:
        goal = (goal or "Make next week less chaotic").strip()
        self.authority_tier = int(authority_tier if authority_tier is not None else self.authority_tier)
        self.transcript_events.append({"kind": "user", "body": goal, "created_at": _now().isoformat()})
        routed = self._route_turn(goal)
        intent = routed.classified_intent
        self.replay.append_router_decision(routed, trace_id=routed.turn_id)
        self._emit_trace(routed.turn_id, "router", "route_classified", payload=routed.replay_payload())
        if self.latest_plan is not None and conversation_message_requests_existing_plan_followup(normalize_conversation_message(goal)):
            return self._create_existing_plan_followup(goal, intent, routed.turn_id)
        planning_observation = self.observation
        if conversation_message_requests_noop_fixture(normalize_conversation_message(goal)):
            planning_observation = self._activate_noop_fixture()
            intent = "calendar_goal"
        correction_command = None
        if self.latest_plan is not None and conversation_message_requests_candidate_correction(normalize_conversation_message(goal)):
            correction_command = self._activate_pending_candidate_correction()
            if correction_command is not None:
                goal = str(getattr(self.latest_plan, "goal", goal))
                intent = "calendar_goal"
        self._finalize_learning_outcomes(now=_now(), superseded=True)
        if conversation_message_requests_calendar_observation(normalize_conversation_message(goal)):
            return self._create_observation_response(goal, intent, routed.turn_id)
        if intent not in {"calendar_goal", "mixed_calendar_operational"}:
            live_chat = self.conversation.live_response(goal, intent)
            if live_chat is not None:
                live_failed = bool(live_chat.metadata.get("error_category"))
                conversation_receipts = [] if live_failed else self.conversation.execute_tools(getattr(live_chat, "tool_calls", []), goal)
                extra_metadata = {"conversation_route": live_chat.route}
                if conversation_receipts:
                    extra_metadata.update(conversation_tool_metadata(conversation_receipts))
                metadata = self._response_metadata(
                    goal=goal,
                    intent=intent,
                    response_source="live_codex_unavailable" if live_failed else "live_codex_conversation",
                    reason="live Codex conversation endpoint failed" if live_failed else "non-calendar turn routed to live Codex conversation endpoint",
                    model_metadata=live_chat.metadata,
                    planner_backend=getattr(self.planner, "backend_name", "live_codex_app_server"),
                    extra_metadata=extra_metadata,
                )
                self.transcript_events.append({
                    "kind": "assistant_chat",
                    "title": "Codex unavailable" if live_failed else ("Codex answered with evidence" if conversation_receipts else "Codex answered"),
                    "body": live_chat.answer,
                    "metadata": metadata,
                    "conversation_receipts": conversation_receipts,
                    "created_at": _now().isoformat(),
                })
                self.persist()
                return self.snapshot()
            local_tool_response = self.conversation.local_tool_response(goal, intent)
            if local_tool_response is not None:
                self.transcript_events.append({
                    "kind": "assistant_chat",
                    "title": local_tool_response["title"],
                    "body": local_tool_response["body"],
                    "metadata": local_tool_response["metadata"],
                    "conversation_receipts": local_tool_response["receipts"],
                    "created_at": _now().isoformat(),
                })
                self.persist()
                return self.snapshot()
            self.transcript_events.append({
                "kind": "assistant_chat",
                "title": "Conversation handled locally",
                "body": self.conversation.local_chat_body(intent),
                "metadata": self._response_metadata(
                    goal=goal,
                    intent=intent,
                    response_source="local_intent_router",
                    reason="input did not request calendar planning",
                ),
                "created_at": _now().isoformat(),
            })
            self.persist()
            return self.snapshot()
        plan = self.planner.plan_goal(goal, planning_observation, self.biography, authority_tier=self.authority_tier, commit=commit)
        self.latest_plan = plan
        self.latest_plan_observation_id = planning_observation.observation_id
        self.latest_plan_observation_fingerprint = observation_fingerprint(planning_observation)
        self._record_frontier_rejections_from_plan(plan)
        self._record_product_core_read_side(plan)
        if correction_command is not None:
            self._record_candidate_correction_application(correction_command, plan)
        self._emit_trace(plan.plan_id, "planner", "planner_started", payload={"planner_backend": getattr(plan, "planner_backend", "unknown")})
        self._emit_trace(plan.plan_id, "frontier_service", "frontier_generated", payload=self._frontier_trace_payload(plan))
        conversation_receipts = []
        extra_metadata: dict[str, Any] = {}
        if correction_command is not None:
            extra_metadata.update({
                "correction_command_id": correction_command["command_id"],
                "correction_applied": True,
                "correction_replacement_minutes": correction_command["replacement_minutes"],
            })
        if intent == "mixed_calendar_operational":
            conversation_receipts = self.conversation.execute_tools(self.conversation.local_tool_calls(goal), goal)
            conversation_metadata = conversation_tool_metadata(conversation_receipts)
            extra_metadata.update({
                "conversation_route": "mixed_calendar_operational",
                "planner_tool_sequence": [call.tool_name.value for call in plan.calls],
                "planner_tool_call_count": len(plan.calls),
                "conversation_tool_sequence": conversation_metadata["tool_sequence"],
                "conversation_tool_receipt_count": conversation_metadata["conversation_tool_receipt_count"],
                "conversation_tool_receipts": conversation_metadata["conversation_tool_receipts"],
                "tool_sequence": [call.tool_name.value for call in plan.calls] + conversation_metadata["tool_sequence"],
                "tool_call_count": len(plan.calls) + conversation_metadata["tool_call_count"],
            })
        metadata = self._response_metadata(
            goal=goal,
            intent=intent,
            response_source="planner",
            plan=plan,
            reason="calendar goal routed to planner" if intent == "calendar_goal" else "calendar planning plus requested operational evidence routed from one composer turn",
            extra_metadata=extra_metadata or None,
        )
        plan_failure = self._plan_failure_message(plan)
        if plan_failure:
            metadata.update(plan_failure.get("metadata", {}))
        plan_title = plan_failure["title"] if plan_failure else "I found a plan"
        plan_body = plan_failure["body"] if plan_failure else self.conversation.planner_response_body(metadata)
        if conversation_receipts and not plan_failure:
            plan_body = f"{plan_body} I also attached the requested operational evidence receipts."
        self.transcript_events.append({
            "kind": "assistant_plan",
            "title": plan_title,
            "body": plan_body,
            "plan_id": plan.plan_id,
            "metadata": metadata,
            "conversation_receipts": conversation_receipts,
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def _activate_noop_fixture(self) -> RawCalendarObservation:
        fixture_path = ROOT / "data" / "noop_dominates_calendar.json"
        fixture_observation = RawCalendarObservation.from_dict(json.loads(fixture_path.read_text(encoding="utf-8")))
        provider_id = str(getattr(self.provider, "provider_id", ""))
        if provider_id != "deterministic_fixture_provider":
            if not bool(getattr(self.provider, "real_provider", False)):
                raise ValueError("the no-op fixture requires a deterministic or real provider")
            self.replay.append_generic(
                "isolated_shadow_fixture",
                {
                    "fixture_id": "noop_dominates",
                    "observation_id": fixture_observation.observation_id,
                    "active_provider_id": provider_id,
                    "provider_replaced": False,
                },
                record_id=f"isolated_shadow_fixture:{self.state_version}",
                signal_stream="world",
            )
            return fixture_observation
        self.observation = fixture_observation
        reset_provider = getattr(self.provider, "reset", None)
        if callable(reset_provider):
            reset_provider(self.observation)
        return self.observation

    def _create_existing_plan_followup(self, goal: str, intent: str, trace_id: str) -> dict[str, Any]:
        snapshot = self.snapshot()
        cards = snapshot.get("chat", {}).get("candidate_cards", [])
        card = cards[0] if cards and isinstance(cards[0], dict) else {}
        action = card.get("action", {}) if isinstance(card.get("action"), dict) else {}
        candidate_id = str(card.get("candidate_id") or "")
        plan_id = str(getattr(self.latest_plan, "plan_id", ""))
        duration = action.get("duration_minutes")
        timezone_name = str(action.get("timezone") or self.observation.time_zone_id)
        body = (
            f"The current proposal is {action.get('title') or card.get('title') or 'the selected action'} "
            f"from {action.get('start') or 'an unknown start'} to {action.get('end') or 'an unknown end'} "
            f"({duration if duration is not None else 'unknown'} minutes) in {timezone_name}. "
            "I answered from the existing selected candidate; I did not generate or choose a new plan."
        )
        record_id = self.replay.append_generic(
            "existing_plan_followup",
            {
                "plan_id": plan_id,
                "candidate_id": candidate_id,
                "action": action,
                "question": goal,
                "resolved_from_existing_evidence": True,
            },
            trace_id=trace_id,
        )
        metadata = self._response_metadata(
            goal=goal,
            intent=intent,
            response_source="existing_plan_evidence",
            plan=self.latest_plan,
            reason="follow-up resolved from the selected candidate without replanning",
            extra_metadata={
                "followup_record_id": record_id,
                "followup_plan_id": plan_id,
                "followup_candidate_id": candidate_id,
                "followup_resolved_from_existing_evidence": True,
            },
        )
        self._emit_trace(trace_id, "conversation", "followup_resolved", payload={
            "plan_id": plan_id,
            "candidate_id": candidate_id,
            "replay_record_id": record_id,
        })
        self.transcript_events.append({
            "kind": "assistant_followup",
            "title": "Current proposal details",
            "body": body,
            "metadata": metadata,
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def _authority_state_digest(self) -> str:
        grants = [grant.to_dict() for grant in self.kernel.authority_grants.values()]
        payload = {
            "authority_tier": self.authority_tier,
            "authority_scopes": sorted(self.authority_scopes),
            "grants": sorted(grants, key=lambda row: str(row.get("grant_id", ""))),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def _pending_candidate_correction(self) -> dict[str, Any] | None:
        applied = {
            str(row.payload.get("command_id"))
            for row in self.replay.records
            if row.record_type == "candidate_correction_application"
        }
        for row in reversed(self.replay.records):
            if row.record_type != "candidate_correction_command" or row.record_id in applied:
                continue
            return dict(row.payload)
        return None

    def _record_candidate_correction_command(self, candidate_id: str, outcome_id: str, reason: str) -> str:
        candidate, action = self._candidate_correction_target(candidate_id)
        old_minutes = max(5, int((action.end - action.start).total_seconds() // 60))
        replacement_minutes = max(5, old_minutes - 10)
        snapshot = self.snapshot()
        card = next(
            (row for row in snapshot.get("chat", {}).get("candidate_cards", []) if row.get("candidate_id") == candidate_id),
            {},
        )
        citation = card.get("citation", {}) if isinstance(card.get("citation"), dict) else {}
        command_id = "correction_command:" + hashlib.sha256(
            f"{outcome_id}|{candidate_id}|{old_minutes}|{replacement_minutes}".encode("utf-8")
        ).hexdigest()[:20]
        outcome = self._learning_record(outcome_id, "learning_outcome")
        citations = [
            command_id,
            outcome_id,
            str(outcome.payload.get("exposure_id", "")),
            str(outcome.payload.get("decision_id", "")),
            *[str(value) for value in citation.get("event_ids", [])],
        ]
        self.replay.append_generic(
            "candidate_correction_command",
            {
                "command_id": command_id,
                "candidate_id": candidate_id,
                "candidate": candidate.to_dict(),
                "observation_id": self.latest_plan_observation_id,
                "observation_fingerprint": self.latest_plan_observation_fingerprint,
                "applies_to_intent": candidate.intent,
                "outcome_id": outcome_id,
                "old_belief_id": f"candidate_assumption:{candidate_id}:duration",
                "old_claim": f"{old_minutes}-minute prep duration is appropriate",
                "old_minutes": old_minutes,
                "replacement_claim": f"use a {replacement_minutes}-minute prep duration",
                "replacement_minutes": replacement_minutes,
                "citation_ids": list(dict.fromkeys(value for value in citations if value)),
                "reason": reason,
                "before_authority_digest": self._authority_state_digest(),
                "status": "pending",
            },
            record_id=command_id,
            trace_id=str(getattr(self.latest_plan, "plan_id", candidate_id)),
            causal_parent_id=outcome_id,
            signal_stream="action",
        )
        return command_id

    def _candidate_correction_target(self, candidate_id: str):
        candidate = self.runtime.frontier.get(candidate_id)
        if candidate is None or not candidate.actions:
            raise ValueError("candidate correction requires a visible candidate action")
        action = candidate.actions[0]
        if action.start is None or action.end is None:
            raise ValueError("candidate correction requires a timed action")
        return candidate, action

    def _activate_pending_candidate_correction(self) -> dict[str, Any] | None:
        command = self._pending_candidate_correction()
        if command is None:
            return None
        self.biography.preference_claims.append({
            "claim": command["replacement_claim"],
            "kind": "explicit_candidate_correction",
            "active": True,
            "applies_to_intent": command["applies_to_intent"],
            "preferred_minutes": command["replacement_minutes"],
            "candidate": command["candidate"],
            "observation_id": command.get("observation_id"),
            "observation_fingerprint": command.get("observation_fingerprint"),
            "command_id": command["command_id"],
            "citation_ids": command["citation_ids"],
            "updated_at": _now().isoformat(),
        })
        return command

    def _record_candidate_correction_application(self, command: dict[str, Any], plan: CodexExecutivePlan) -> None:
        frontier = next((receipt for receipt in plan.receipts if receipt.tool_name == CodexToolName.GENERATE_CANDIDATE_FRONTIER), None)
        candidates = frontier.output.get("candidates", []) if frontier is not None and isinstance(frontier.output, dict) else []
        leading = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
        actions = leading.get("actions", []) if isinstance(leading, dict) else []
        action = actions[0] if actions and isinstance(actions[0], dict) else {}
        try:
            start = datetime.fromisoformat(str(action.get("start")))
            end = datetime.fromisoformat(str(action.get("end")))
            duration = int((end - start).total_seconds() // 60)
        except (TypeError, ValueError):
            duration = None
        correction_applied = duration == command["replacement_minutes"]
        if correction_applied:
            for claim in reversed(self.biography.preference_claims):
                if claim.get("command_id") != command["command_id"]:
                    continue
                claim["active"] = False
                claim["status"] = "applied"
                break
        self.replay.append_generic(
            "candidate_correction_application",
            {
                "command_id": command["command_id"],
                "old_belief_id": command["old_belief_id"],
                "old_belief_active": False,
                "plan_id": plan.plan_id,
                "candidate_id": leading.get("candidate_id"),
                "replacement_minutes": command["replacement_minutes"],
                "actual_minutes": duration,
                "new_plan_uses_correction": correction_applied,
                "citation_ids": command["citation_ids"],
                "before_authority_digest": command["before_authority_digest"],
                "after_authority_digest": self._authority_state_digest(),
            },
            record_id=f"candidate_correction_application:{command['command_id']}",
            trace_id=plan.plan_id,
            causal_parent_id=command["command_id"],
            signal_stream="biography",
        )

    def _create_observation_response(self, goal: str, intent: str, trace_id: str) -> dict[str, Any]:
        facts = [
            {
                "fact_id": event.event_id,
                "citation_id": event.event_id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "calendar_id": event.calendar_id,
                "category": event.category,
            }
            for event in self.observation.events
        ]
        provider_window_owner = getattr(self.provider, "incumbent", self.provider)
        read_window = getattr(provider_window_owner, "last_read_window", None)
        observation_payload = {
            "observation_id": self.observation.observation_id,
            "timezone": self.observation.time_zone_id,
            "read_window": dict(read_window) if isinstance(read_window, dict) else None,
            "fact_ids": [fact["fact_id"] for fact in facts],
            "citation_ids": [fact["citation_id"] for fact in facts],
            "facts": facts,
            "candidate_ids": [],
        }
        replay_id = self.replay.append_generic(
            "calendar_observation",
            observation_payload,
            record_id=f"calendar_observation:{trace_id}",
            trace_id=trace_id,
            signal_stream="world",
        )
        self._emit_trace(trace_id, "provider_observation", "observation_read", payload={"replay_record_id": replay_id, "fact_ids": observation_payload["fact_ids"]})
        self.transcript_events.append({
            "kind": "assistant_observation",
            "title": "Tomorrow's calendar evidence",
            "body": f"I found {len(facts)} cited calendar events in the bound {self.observation.time_zone_id} observation. I did not generate or stage a change.",
            "metadata": self._response_metadata(
                goal=goal,
                intent=intent,
                response_source="cited_calendar_observation",
                reason="read-only calendar question resolved from the active provider observation",
                extra_metadata={"tool_sequence": ["inspect_week"], "tool_call_count": 1, "observation_replay_record_id": replay_id},
            ),
            "cards": [{"type": "observation", **observation_payload}],
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def _route_turn(self, goal: str):
        # In live modes this will move to ModelIntentRouter once Codex emits a
        # structured intent. Until then, record the deterministic legacy result
        # as the actual decision and keep the extracted/model-fallback router as
        # counterfactual evidence so confidence never belongs to a route that did
        # not decide.
        router = ModelIntentRouter() if self.runtime_mode in {"live_codex", "production"} else self.router
        routed = router.route(goal, context={"runtime_mode": self.runtime_mode})
        proposed = {
            "router_backend": routed.router_backend,
            "classified_intent": routed.classified_intent,
            "route": routed.route,
            "confidence": routed.confidence,
            "evidence": dict(routed.evidence),
        }
        legacy_intent = self.conversation.classify_intent(goal)
        routed.classified_intent = legacy_intent
        if legacy_intent in {"calendar_goal", "mixed_calendar_operational"}:
            routed.route = "planner"
        elif legacy_intent == "operational_tool":
            routed.route = "operational"
        else:
            routed.route = "conversation"
        routed.router_backend = "fixture_keywords" if self.runtime_mode not in {"live_codex", "production"} else "fallback_keywords"
        routed.confidence = 0.0
        routed.counterfactual_routes = [proposed["route"]]
        routed.evidence = {"legacy_intent": legacy_intent, "legacy_classifier_active": True, "counterfactual_router": proposed}
        return routed

    def _emit_trace(self, trace_id: str, obj: str, stage: str, *, status: str = "succeeded", payload: dict[str, Any] | None = None, causal_parent_id: str | None = None) -> None:
        TRACE_BUS.emit(
            session_id=self.session_id,
            state_version=self.state_version,
            trace_id=trace_id,
            obj=obj,
            stage=stage,
            status=status,
            payload=payload or {},
            causal_parent_id=causal_parent_id,
        )

    def _emit_action_lifecycle_trace(self, receipt: Any, *, fallback_stage: str, fallback_trace_id: str) -> None:
        if hasattr(receipt, "to_dict"):
            receipt_dict = receipt.to_dict()
        elif isinstance(receipt, dict):
            receipt_dict = receipt
        else:
            receipt_dict = {}
        output = receipt_dict.get("output", {}) if isinstance(receipt_dict.get("output"), dict) else {}
        envelope = output.get("action_envelope") if isinstance(output, dict) else None
        trace_id = str(fallback_trace_id)
        if isinstance(envelope, dict):
            trace_id = str(envelope.get("trace_id") or fallback_trace_id)
        stage_aliases = {
            "undo": "rollback",
            "verify": "provider_verify",
            "reward": "reward_recorded",
        }
        lifecycle = envelope.get("lifecycle", []) if isinstance(envelope, dict) else []
        emitted = False
        if isinstance(lifecycle, list):
            for step in lifecycle:
                if not isinstance(step, dict):
                    continue
                transition = str(step.get("transition") or "").strip()
                if not transition:
                    continue
                payload = {
                    "receipt_id": receipt_dict.get("swift_receipt_id") or receipt_dict.get("tool_call_id"),
                    "envelope_id": envelope.get("envelope_id") if isinstance(envelope, dict) else None,
                    "candidate_id": envelope.get("candidate_id") if isinstance(envelope, dict) else output.get("candidate_id"),
                    "rollback_state": (envelope.get("provider") or {}).get("rollback_state") if isinstance(envelope, dict) else None,
                    "stage_state": receipt_dict.get("stage_state"),
                    "transition": transition,
                    "detail": step.get("detail", {}),
                }
                self._emit_trace(
                    trace_id,
                    "action_lifecycle",
                    stage_aliases.get(transition, transition),
                    status=str(step.get("status") or receipt_dict.get("status") or "succeeded"),
                    payload=payload,
                    causal_parent_id=str(step.get("swift_receipt_id") or receipt_dict.get("tool_call_id") or "") or None,
                )
                emitted = True
        if not emitted:
            self._emit_trace(
                trace_id,
                "action_lifecycle",
                stage_aliases.get(fallback_stage, fallback_stage),
                status=str(receipt_dict.get("status") or "succeeded"),
                payload={"receipt": receipt_dict},
            )

    def _record_frontier_rejections_from_plan(self, plan: Any) -> None:
        for receipt in getattr(plan, "receipts", []):
            if getattr(receipt, "tool_name", None) != CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                continue
            output = receipt.output if isinstance(receipt.output, dict) else {}
            metadata = output.get("policy_metadata") or output.get("metadata") or {}
            validation = metadata.get("validation") if isinstance(metadata, dict) else None
            if not isinstance(validation, dict):
                continue
            for rejection in validation.get("rejections", []) or []:
                if isinstance(rejection, dict):
                    self.replay.append_model_generation_rejection(rejection, trace_id=receipt.correlation_id or receipt.tool_call_id)

    def _record_product_core_read_side(self, plan: Any) -> None:
        candidates: list[dict[str, Any]] = []
        ranking: list[dict[str, Any]] = []
        for receipt in getattr(plan, "receipts", []):
            output = receipt.output if isinstance(receipt.output, dict) else {}
            if getattr(receipt, "tool_name", None) == CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                rows = output.get("candidates")
                if isinstance(rows, list):
                    candidates.extend(row for row in rows if isinstance(row, dict))
            elif getattr(receipt, "tool_name", None) == CodexToolName.COMPARE_CANDIDATES:
                rows = output.get("ranking")
                if isinstance(rows, list):
                    ranking = [row for row in rows if isinstance(row, dict)]
        ranks = {str(row.get("candidate_id")): index + 1 for index, row in enumerate(ranking)}
        journal_scope_id = f"{self.session_id}:{self.state_version}:{plan.plan_id}"
        for payload in candidates:
            candidate = CandidateCalendarAction.from_dict(payload)
            if candidate.intent != "create_prep_block":
                continue
            result = run_create_prep_block_vertical(
                self.observation,
                candidate,
                source_authenticated=True,
                received_at=self.observation.observed_at,
                rank=ranks.get(candidate.candidate_id),
                journal_scope_id=journal_scope_id,
            )
            for event in result.events:
                replay_parent_id = (
                    f"product_core_journal_event:{event.causal_parent_ids[0]}"
                    if event.causal_parent_ids
                    else None
                )
                self.replay.append_generic(
                    "product_core_journal_event",
                    {
                        "journal_scope_id": journal_scope_id,
                        "plan_id": plan.plan_id,
                        "journal_event": event.to_dict(),
                    },
                    record_id=f"product_core_journal_event:{event.row_id}",
                    trace_id=plan.plan_id,
                    causal_parent_id=replay_parent_id,
                )

    def _frontier_trace_payload(self, plan: Any) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        rejections: list[Any] = []
        for receipt in getattr(plan, "receipts", []):
            if getattr(receipt, "tool_name", None) != CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                continue
            output = receipt.output if isinstance(receipt.output, dict) else {}
            raw_candidates = output.get("candidates")
            if isinstance(raw_candidates, list):
                candidates.extend(candidate for candidate in raw_candidates if isinstance(candidate, dict))
            metadata = output.get("policy_metadata") or output.get("metadata") or {}
            validation = metadata.get("validation") if isinstance(metadata, dict) else None
            if isinstance(validation, dict):
                rejections.extend(validation.get("rejections", []) or [])
        return {"valid": len(candidates), "rejected": len(rejections), "taxonomy_health": taxonomy_health(candidates)}

    @staticmethod
    def _plan_failure_message(plan: CodexExecutivePlan) -> dict[str, Any] | None:
        if plan.recommended_next_action == "live_codex_unavailable" or plan.planner_metadata.get("error_category"):
            receipt = next((row for row in reversed(plan.receipts) if row.status == CodexToolStatus.FAILED or row.denied_reason), None)
            output = receipt.output if receipt is not None and isinstance(receipt.output, dict) else {}
            message = str(output.get("message") or (receipt.denied_reason if receipt else "") or "Live Codex did not produce an executable tool plan.")
            recovery = str(output.get("recovery") or "").strip()
            body = message if not recovery else f"{message} {recovery}"
            error_category = output.get("error_category") or plan.planner_metadata.get("error_category")
            return {
                "title": "Codex plan unavailable",
                "body": body,
                "metadata": {
                    "plan_failed": True,
                    "plan_failure_tool": receipt.tool_name.value if receipt is not None else None,
                    "plan_failure_category": error_category,
                    "plan_failure_recovery": recovery,
                },
            }
        for receipt in plan.receipts:
            if receipt.tool_name != CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                continue
            if receipt.status != CodexToolStatus.FAILED and not receipt.denied_reason:
                return None
            output = receipt.output if isinstance(receipt.output, dict) else {}
            message = str(output.get("message") or receipt.denied_reason or "Candidate frontier generation failed.")
            recovery = str(output.get("recovery") or "").strip()
            body = message if not recovery else f"{message} {recovery}"
            metadata = {
                "plan_failed": True,
                "plan_failure_tool": receipt.tool_name.value,
                "plan_failure_category": output.get("error_category"),
                "plan_failure_recovery": recovery,
            }
            return {
                "title": "I could not generate candidate futures",
                "body": body,
                "metadata": metadata,
            }
        return None

    def _response_metadata(
        self,
        *,
        goal: str,
        intent: str,
        response_source: str,
        reason: str,
        plan: CodexExecutivePlan | None = None,
        model_metadata: dict[str, Any] | None = None,
        planner_backend: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        backends = self._runtime_backends().to_dict()
        planner_backend = planner_backend or (plan.planner_backend if plan is not None else backends["codex"])
        model_metadata = dict(model_metadata if model_metadata is not None else (plan.planner_metadata if plan is not None else {}))
        error_category = str(model_metadata.get("error_category") or "")
        model_reached = (
            planner_backend == "live_codex_app_server"
            and not error_category
            and bool(model_metadata.get("response_id") or (model_metadata.get("thread_id") and model_metadata.get("turn_id")))
        )
        expected_model_keys = ["response_id", "thread_id", "turn_id", "model"]
        metadata = {
            "input": goal,
            "intent": intent,
            "response_source": response_source,
            "reason": reason,
            "runtime_mode": self.runtime_mode,
            "planner_backend": planner_backend,
            "policy_backend": backends["diffusiongemma"],
            "kernel_backend": backends["kernel"],
            "provider_backend": backends["provider"],
            "model_reached": model_reached,
            "model_metadata": model_metadata,
            "missing_model_metadata": [key for key in expected_model_keys if not model_metadata.get(key)],
            "plan_id": plan.plan_id if plan is not None else None,
            "recommended_next_action": plan.recommended_next_action if plan is not None else None,
            "tool_sequence": [call.tool_name.value for call in plan.calls] if plan is not None else [],
            "tool_call_count": len(plan.calls) if plan is not None else 0,
            "replay_record_count": self.replay.summarize().records,
        }
        if error_category:
            metadata["error_category"] = error_category
        if extra_metadata:
            metadata.update(extra_metadata)
        return metadata

    def _receipt_response_metadata(
        self,
        *,
        goal: str,
        intent: str,
        response_source: str,
        reason: str,
        receipt: Any,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        receipt_dict = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
        receipt_extra = {
            "tool_sequence": [str(receipt_dict.get("tool_name", ""))],
            "tool_call_count": 1,
            "receipt_status": receipt_dict.get("status"),
            "receipt_tool_call_id": receipt_dict.get("tool_call_id"),
            "receipt_requires_confirmation": bool(receipt_dict.get("requires_user_confirmation", False)),
            "receipt_denied_reason": receipt_dict.get("denied_reason"),
        }
        output = receipt_dict.get("output", {}) if isinstance(receipt_dict.get("output"), dict) else {}
        swift = output.get("swift_receipt", {}) if isinstance(output.get("swift_receipt"), dict) else {}
        provider_rollback = output.get("provider_rollback", {}) if isinstance(output.get("provider_rollback"), dict) else {}
        if swift:
            receipt_extra.update({
                "receipt_sync_status": swift.get("sync_status"),
                "receipt_stage_state": receipt_dict.get("stage_state") or swift.get("stage_state"),
                "receipt_rollback_handle_id": swift.get("rollback_handle_id"),
                "swift_receipt_id": receipt_dict.get("swift_receipt_id") or swift.get("receipt_id"),
            })
        if provider_rollback:
            receipt_extra.update({
                "provider_rollback_status": provider_rollback.get("status"),
                "rollback_verified": provider_rollback.get("rollback_verified"),
            })
        if extra_metadata:
            receipt_extra.update(extra_metadata)
        return self._response_metadata(
            goal=goal,
            intent=intent,
            response_source=response_source,
            reason=reason,
            extra_metadata=receipt_extra,
        )

    def candidate_action(self, candidate_id: str, action: str, *, confirmed: bool = False) -> dict[str, Any]:
        candidate = self.runtime.frontier.get(candidate_id)
        if candidate is None:
            raise KeyError(f"candidate not found: {candidate_id}")
        if action == "simulate":
            name = CodexToolName.SIMULATE_ACTION_PROGRAM
            scopes = ["stage"]
            grant_id = self.latest_grant_id(confirmed=False, scopes=scopes)
            reason = "Simulate the selected action without changing provider state."
        elif action == "stage":
            name = CodexToolName.STAGE_ACTION_PACKET
            scopes = ["stage"]
            grant_id = self.latest_grant_id(confirmed=False, scopes=scopes)
            reason = "Stage the selected action for user-visible confirmation."
        elif action == "commit":
            name = CodexToolName.REQUEST_COMMIT
            scopes = ["commit_private", "undo"]
            if confirmed:
                self._refresh_live_observation_for_confirmation(require_plan_match=True)
            confirmation = (
                managed_commit_confirmation_provenance(candidate, self.provider.binding)
                if isinstance(self.provider, ManagedEventKitRetirementProvider) and self.provider.owns_candidate(candidate)
                else f"user_confirmed_commit:{candidate_id}"
            )
            grant_id = self.issue_authority_grant(confirmed=True, scopes=self.authority_scopes, reason=confirmation).grant_id if confirmed else self.latest_grant_id(confirmed=True, scopes=scopes)
            reason = "Request Swift to commit the selected private/reversible action."
        else:
            raise ValueError(f"unsupported candidate action: {action}")
        receipt = self.runtime.execute(self._call(name, {"candidate_id": candidate_id}, grant_id=grant_id, reason=reason, correlation_id=candidate_id), self.observation, self.biography)
        self._emit_action_lifecycle_trace(receipt, fallback_stage=action, fallback_trace_id=candidate_id)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        self.transcript_events.append({
            "kind": "assistant_receipt",
            "title": self._title_for_receipt(action, receipt.denied_reason),
            "body": receipt.denied_reason or f"Swift returned {receipt.status.value} for {candidate.intent}.",
            "candidate_id": candidate_id,
            "receipt": receipt.to_dict(),
            "metadata": self._receipt_response_metadata(
                goal=f"{action}:{candidate_id}",
                intent="candidate_action",
                response_source="ui_candidate_action",
                reason="candidate action requested from visible card controls",
                receipt=receipt,
                extra_metadata={"candidate_id": candidate_id, "candidate_action": action},
            ),
            "created_at": _now().isoformat(),
        })
        if receipt.denied_reason:
            self.denial_history.append({"candidate_id": candidate_id, "denied_reason": receipt.denied_reason, "receipt": receipt.to_dict()})
        self.persist()
        return self.snapshot()

    def confirm_receipt(self, receipt_id: str) -> dict[str, Any]:
        # Confirmation is modeled as a commit request against the staged receipt's candidate.
        candidate_id = self._candidate_id_for_receipt(receipt_id)
        if not candidate_id:
            raise KeyError(f"receipt not found: {receipt_id}")
        return self.candidate_action(candidate_id, "commit", confirmed=True)

    def undo(self, rollback_handle_id: str) -> dict[str, Any]:
        rollback_handle_id = rollback_handle_id.strip()
        self._refresh_live_observation_for_confirmation(require_plan_match=False)
        grant_id = self.issue_authority_grant(confirmed=True, scopes=["undo"], reason=f"user_confirmed_undo:{rollback_handle_id}").grant_id
        receipt = self.runtime.execute(self._call(CodexToolName.REQUEST_UNDO, {"rollback_handle_id": rollback_handle_id}, grant_id=grant_id, reason="Request Swift rollback through the undo ledger.", correlation_id=rollback_handle_id), self.observation, self.biography)
        self._emit_action_lifecycle_trace(receipt, fallback_stage="rollback", fallback_trace_id=rollback_handle_id)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        self.transcript_events.append({
            "kind": "assistant_receipt",
            "title": "Undo requested",
            "body": receipt.denied_reason or "Swift used the rollback ledger and marked the action reverted.",
            "receipt": receipt.to_dict(),
            "metadata": self._receipt_response_metadata(
                goal=f"undo:{rollback_handle_id}",
                intent="undo",
                response_source="ui_undo",
                reason="undo requested through the rollback ledger",
                receipt=receipt,
                extra_metadata={"rollback_handle_id": rollback_handle_id},
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def feedback(self, receipt_id: str, feedback: str, *, reason: str = "") -> dict[str, Any]:
        reward = self._reward_for_feedback(receipt_id, feedback)
        candidate = self._candidate_for_receipt(receipt_id)
        receipt = self._receipt_payload_for_receipt(receipt_id)
        trace_id = candidate.candidate_id if candidate else receipt_id
        feedback_record_id = self.replay.append_human_feedback_event(
            receipt_id=receipt_id,
            feedback=feedback,
            reason=reason,
            reward=reward,
            candidate=candidate,
            receipt=receipt,
            trace_id=trace_id,
        )
        attached = self.replay.attach_reward(receipt_id, reward)
        reward_record_id = ""
        if not attached:
            reward_record_id = f"reward:{reward.reward_event_id}"
            self.replay.append_reward(reward, candidate=candidate, trace_id=trace_id, causal_parent_id=feedback_record_id)
        entry = {"receipt_id": receipt_id, "feedback": feedback, "reason": reason, "reward": reward.to_dict(), "feedback_record_id": feedback_record_id, "reward_record_id": reward_record_id, "created_at": _now().isoformat()}
        self.feedback_history.append(entry)
        self.transcript_events.append({
            "kind": "assistant",
            "title": "Feedback captured",
            "body": f"Marked {feedback}. This creates a reward event for replay/training rather than changing authority.",
            "metadata": self._response_metadata(
                goal=f"feedback:{receipt_id}",
                intent="feedback",
                response_source="ui_feedback",
                reason="feedback reward captured for replay",
                extra_metadata={
                    "receipt_id": receipt_id,
                    "feedback": feedback,
                    "reward": reward.to_dict(),
                    "reward_attached_to_existing_receipt": attached,
                    "feedback_record_id": feedback_record_id,
                    "reward_record_id": reward_record_id,
                    "reward_written_as_action_stream": True,
                },
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def learning_exposure(self, decision_id: str, rendered_candidate_ids: list[str], *, surface: str = "operate") -> dict[str, Any]:
        decision = self._learning_record(decision_id, "learning_decision")
        rendered = list(dict.fromkeys(str(value) for value in rendered_candidate_ids if str(value)))
        for record in self.replay.records:
            if record.record_type != "learning_exposure":
                continue
            if record.payload.get("decision_id") == decision_id and record.payload.get("surface") == surface and record.payload.get("rendered_candidate_ids") == rendered:
                return {"decision": "pass", "decision_id": decision_id, "exposure_id": record.record_id, "duplicate": True}
        exposure_id = self.replay.append_learning_exposure(
            decision=decision,
            rendered_candidate_ids=rendered,
            surface=surface,
            rendered_at=_now(),
        )
        self.persist()
        return {"decision": "pass", "decision_id": decision_id, "exposure_id": exposure_id, "duplicate": False}

    def learning_outcome(
        self,
        *,
        decision_id: str,
        exposure_id: str,
        candidate_id: str,
        outcome: str,
        reason: str = "",
    ) -> dict[str, Any]:
        if outcome not in {"accepted", "dismissed", "corrected"}:
            raise ValueError("the UI may record only explicit accepted, dismissed, or corrected outcomes")
        exposure = self._learning_record(exposure_id, "learning_exposure")
        if exposure.payload.get("decision_id") != decision_id:
            raise ValueError("learning outcome does not match its decision")
        existing = self._learning_outcome_for(exposure_id, candidate_id)
        if existing is not None:
            if existing.payload.get("outcome") != outcome:
                raise ValueError("candidate already has a conflicting terminal outcome")
            return {"decision": "pass", "outcome_id": existing.record_id, "duplicate": True}
        if outcome == "corrected":
            self._candidate_correction_target(candidate_id)
        outcome_id = self.replay.append_learning_outcome(
            exposure=exposure,
            candidate_id=candidate_id,
            outcome=outcome,
            reason=reason,
            observed_at=_now(),
        )
        if outcome == "corrected":
            self._record_candidate_correction_command(candidate_id, outcome_id, reason)
        self.persist()
        return {"decision": "pass", "outcome_id": outcome_id, "duplicate": False}

    def _learning_record(self, record_id: str, expected_type: str):
        record = next((row for row in self.replay.records if row.record_id == record_id), None)
        if record is None or record.record_type != expected_type:
            raise ValueError(f"unknown {expected_type}: {record_id}")
        return record

    def _learning_outcome_for(self, exposure_id: str, candidate_id: str):
        return next((
            row for row in self.replay.records
            if row.record_type == "learning_outcome"
            and row.payload.get("exposure_id") == exposure_id
            and row.payload.get("candidate_id") == candidate_id
        ), None)

    def _finalize_learning_outcomes(self, *, now: datetime, superseded: bool) -> None:
        decisions = {row.record_id: row for row in self.replay.records if row.record_type == "learning_decision"}
        changed = False
        exposures = [row for row in self.replay.records if row.record_type == "learning_exposure"]
        for exposure in exposures:
            decision = decisions.get(str(exposure.payload.get("decision_id")))
            if decision is None:
                continue
            ends_at = datetime.fromisoformat(str(decision.payload["outcome_window"]["ends_at"]).replace("Z", "+00:00"))
            if now < ends_at and not superseded:
                continue
            outcome = "ignored" if now >= ends_at else "censored"
            censoring_reason = None if outcome == "ignored" else "superseded_by_new_decision"
            for candidate_id in exposure.payload.get("rendered_candidate_ids", []):
                candidate_id = str(candidate_id)
                if self._learning_outcome_for(exposure.record_id, candidate_id) is not None:
                    continue
                self.replay.append_learning_outcome(
                    exposure=exposure,
                    candidate_id=candidate_id,
                    outcome=outcome,
                    reason="outcome window elapsed" if outcome == "ignored" else "a later planning decision superseded this exposure",
                    censoring_reason=censoring_reason,
                    observed_at=now,
                )
                changed = True
        if changed:
            self.persist()

    def propose_profile_patch(self, correction: str) -> dict[str, Any]:
        grant_id = self.latest_grant_id(confirmed=True)
        receipt = self.runtime.execute(self._call(CodexToolName.PROPOSE_PROFILE_PATCH, {"correction": correction}, grant_id=grant_id, reason="Draft a profile repair from user correction."), self.observation, self.biography)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        receipt_dict = receipt.to_dict()
        proposal_kind = "proposed" if profile_patch_payload_from_receipt(receipt_dict) is not None else "proposal_failed"
        self.profile_patch_history.append({"kind": proposal_kind, "receipt": receipt_dict, "created_at": _now().isoformat()})
        self.transcript_events.append({
            "kind": "assistant_receipt",
            "title": "Profile repair drafted" if proposal_kind == "proposed" else "Profile repair unavailable",
            "body": "I drafted a profile patch. It will not apply until confirmed." if proposal_kind == "proposed" else (receipt.denied_reason or "I could not draft a profile repair."),
            "receipt": receipt_dict,
            "metadata": self._receipt_response_metadata(
                goal=correction,
                intent="profile_repair",
                response_source="ui_profile_patch_propose",
                reason="profile repair proposal requested from profile controls",
                receipt=receipt,
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def apply_profile_patch(self, claim: str, correction: str, *, confirmed: bool) -> dict[str, Any]:
        grant_id = self.latest_grant_id(confirmed=True)
        receipt = self.runtime.execute(self._call(CodexToolName.APPLY_PROFILE_PATCH, {"claim": claim, "correction": correction, "confirmed": confirmed}, grant_id=grant_id, reason="Apply a confirmed profile repair."), self.observation, self.biography)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        bio_payload = receipt.output.get("biography") if isinstance(receipt.output, dict) else None
        if isinstance(bio_payload, dict):
            self.biography = UserBiography.from_dict(bio_payload)
        receipt_dict = receipt.to_dict()
        applied = str(receipt_dict.get("status")) == "succeeded" and isinstance(bio_payload, dict)
        self.profile_patch_history.append({"kind": "applied" if applied else "needs_confirmation", "receipt": receipt_dict, "created_at": _now().isoformat()})
        self.transcript_events.append({
            "kind": "assistant_receipt",
            "title": "Profile repair applied" if applied else "Profile repair needs confirmation",
            "body": receipt.denied_reason or ("Profile claims were updated with correction provenance." if applied else "Profile patch requires confirmation before applying."),
            "receipt": receipt_dict,
            "metadata": self._receipt_response_metadata(
                goal=correction,
                intent="profile_apply",
                response_source="ui_profile_patch_apply",
                reason="profile repair apply requested from profile controls",
                receipt=receipt,
                extra_metadata={"profile_patch_confirmed": confirmed},
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def explain_denial(self, denied_reason: str) -> dict[str, Any]:
        receipt = self.runtime.execute(self._call(CodexToolName.EXPLAIN_SWIFT_DENIAL, {"denied_reason": denied_reason}, reason="Explain a Swift denial and suggest next controls."), self.observation, self.biography)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        self.denial_history.append({"denied_reason": denied_reason, "explanation": receipt.output, "created_at": _now().isoformat()})
        self.transcript_events.append({
            "kind": "assistant_receipt",
            "title": "Why Swift denied it",
            "body": str(receipt.output.get("denial_explanation", denied_reason)),
            "receipt": receipt.to_dict(),
            "metadata": self._receipt_response_metadata(
                goal=denied_reason,
                intent="denial_explanation",
                response_source="ui_denial_explain",
                reason="Swift denial explanation requested from visible controls",
                receipt=receipt,
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def run_self_play(self, episodes: int = 3, backend: str = "stub_fast") -> dict[str, Any]:
        episodes = int(episodes)
        if episodes <= 0:
            raise ValueError("episodes must be positive")
        grant_id = self.latest_grant_id(confirmed=True)
        receipt = self.runtime.execute(self._call(CodexToolName.RUN_SELF_PLAY_PROBE, {"episodes": episodes, "backend": backend}, grant_id=grant_id, reason="Probe the current policy against self-play adversaries."), self.observation, self.biography)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        metrics = receipt.output.get("metrics", {}) if isinstance(receipt.output, dict) else {}
        top_failures = receipt.output.get("top_failure_modes", []) if isinstance(receipt.output, dict) else []
        failed = receipt.status == CodexToolStatus.FAILED or not metrics or int(metrics.get("episodes", 0) or 0) < episodes
        release_decision = "probe_failed" if failed else ("hold_autonomy" if top_failures else "ship_runtime_gate")
        self.self_play_history.append({"episodes": episodes, "backend": backend, "metrics": metrics, "top_failure_modes": top_failures, "release_decision": release_decision, "created_at": _now().isoformat()})
        self.transcript_events.append({
            "kind": "assistant_receipt",
            "title": "Self-play release gate",
            "body": f"Decision: {release_decision}.",
            "receipt": receipt.to_dict(),
            "metadata": self._receipt_response_metadata(
                goal=f"self_play:{episodes}",
                intent="self_play",
                response_source="ui_self_play",
                reason="self-play release gate requested from visible controls",
                receipt=receipt,
                extra_metadata={"self_play_episodes": episodes, "self_play_backend": backend, "release_decision": release_decision},
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def set_signal_activation(self, signal_id: str, *, status: str, reason: str = "") -> dict[str, Any]:
        signal_id = str(signal_id or "").strip()
        status = str(status or "").strip().lower()
        if not signal_id:
            raise ValueError("signal_id is required")
        if status not in {"active", "disabled"}:
            raise ValueError("signal status must be active or disabled")
        rows = [record.envelope() for record in self.replay.records]
        signal = next(
            (
                row.get("payload", {})
                for row in reversed(rows)
                if row.get("record_type") == "semantic_signal"
                and row.get("payload", {}).get("signal_id") == signal_id
            ),
            None,
        )
        if not signal:
            signal = self._latest_p12_semantic_signal(signal_id)
            if not signal:
                raise KeyError(f"unknown semantic signal: {signal_id}")
            self._import_semantic_evidence_rows(signal, trace_id=signal_id)
            self.replay.append_semantic_signal(signal, trace_id=signal_id)
        activation = {
            "activation_id": "label_act_" + hashlib.sha1(f"{signal_id}|{status}|{_now().isoformat()}".encode("utf-8")).hexdigest()[:12],
            "signal_id": signal_id,
            "user_scope_id": signal.get("user_scope_id") or self.observation.user_scope_id,
            "status": status,
            "actor": "user",
            "surface": "signals_settings",
            "at": _now().isoformat(),
            "reason": reason or ("user disabled label" if status == "disabled" else "user activated label"),
        }
        self.replay.append_label_activation(activation, trace_id=signal_id, causal_parent_id=f"semantic_signal:{signal_id}")
        self.transcript_events.append({
            "kind": "assistant",
            "title": "Signal control recorded",
            "body": f"Semantic label {signal_id} is now {status}.",
            "metadata": self._response_metadata(
                goal=f"signal:{signal_id}:{status}",
                intent="signal_control",
                response_source="ui_signal_control",
                reason="user-governed semantic label control recorded as an ActionStream audit row",
                extra_metadata={"signal_id": signal_id, "signal_status": status},
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def _latest_p12_semantic_signal(self, signal_id: str) -> dict[str, Any] | None:
        evidence_base = ROOT / "runs" / "p12_evidence"
        if not evidence_base.exists():
            return None
        candidates = [path for path in evidence_base.iterdir() if path.is_dir()]
        for evidence_dir in sorted(candidates, key=lambda path: path.name, reverse=True):
            path = evidence_dir / "semantic_labels" / "semantic_signals.json"
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for signal in payload.get("signals", []) if isinstance(payload, dict) else []:
                if isinstance(signal, dict) and signal.get("signal_id") == signal_id:
                    return dict(signal)
        return None

    def _import_semantic_evidence_rows(self, signal: dict[str, Any], *, trace_id: str) -> None:
        known = {record.envelope().get("record_id") for record in self.replay.records}
        for evidence_id in [str(item) for item in signal.get("evidence", [])]:
            if not evidence_id or evidence_id in known or evidence_id.startswith("notification_history:"):
                continue
            if evidence_id.startswith("reward:"):
                self.replay.append_generic(
                    "reward",
                    {
                        "reward": {
                            "reward_id": evidence_id,
                            "receipt_id": "p12_evidence_import",
                            "total_reward": 0.0,
                            "source": "p12_evidence_import",
                        },
                        "imported_for_semantic_signal": signal.get("signal_id"),
                    },
                    record_id=evidence_id,
                    trace_id=trace_id,
                    signal_stream="action",
                )
                known.add(evidence_id)

    def update_authority(self, tier: int | None = None, scopes: list[str] | None = None, confirmed: bool = True) -> dict[str, Any]:
        if tier is not None:
            self.authority_tier = max(0, min(6, int(tier)))
        if scopes is not None:
            self.authority_scopes = [str(s) for s in scopes if str(s).strip()]
        self.kernel.authority_grants.clear()
        self.issue_authority_grant(confirmed=confirmed, reason="user_edited_authority_scope")
        self.persist()
        return self.snapshot()

    def set_runtime_mode(self, runtime_mode: str) -> dict[str, Any]:
        requested = (runtime_mode or "").strip().lower().replace("-", "_")
        if requested not in KNOWN_MODES:
            raise ValueError(f"unsupported runtime mode: {runtime_mode}")
        if requested != self.runtime_mode:
            self.runtime_mode = requested
            self.launch_config = LaunchConfig.from_env(
                run_dir=self.run_dir,
                host=self.launch_config.host,
                port=self.launch_config.port,
                runtime_mode=self.runtime_mode,
            )
            self.launch_config.write_manifest()
            self.latest_plan = None
            self.latest_plan_observation_id = None
            self.latest_plan_observation_fingerprint = None
            self._replace_kernel_for_mode()
            self.persistence.hydrate_runtime_frontier()
            self.issue_authority_grant(confirmed=True, reason=f"user_selected_runtime:{requested}")
            self.transcript_events.append({
                "kind": "assistant",
                "title": "Runtime changed",
                "body": f"Switched to {self.runtime_report().get('mode_label', requested)}. Existing replay evidence remains, and candidate controls will be regenerated by the next goal.",
                "created_at": _now().isoformat(),
            })
        self.persist()
        return self.snapshot()

    def start_codex_subscription_sign_in(self) -> dict[str, Any]:
        from calendar_pilot.codex.live import CODEX_AUTH_DOC_URL, CodexAppServerClient

        client = CodexAppServerClient()
        health = client.health_status(validate_remote=False)
        result: dict[str, Any] = {
            "codex_health": health,
            "auth_url": CODEX_AUTH_DOC_URL,
            "launched": False,
            "method": "not_needed" if health.get("configured") else "unavailable",
        }
        if health.get("configured"):
            body = "Codex subscription auth is already configured for this machine."
        else:
            try:
                subprocess.Popen(
                    [client.codex_bin, "login"],
                    cwd=ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                result.update({"launched": True, "method": "codex login", "codex_bin": client.codex_bin})
                body = "Opened the Codex ChatGPT sign-in flow. Finish the browser sign-in, then switch to Live Codex mode or retry the goal."
            except Exception as exc:
                webbrowser.open(CODEX_AUTH_DOC_URL)
                result.update({"launched": True, "method": "auth docs", "reason": str(exc)})
                body = "Could not launch `codex login`, so I opened the Codex auth documentation instead."
        self.transcript_events.append({
            "kind": "assistant",
            "title": "Codex sign-in",
            "body": body,
            "codex_auth": result,
            "created_at": _now().isoformat(),
        })
        self.persist()
        state = self.snapshot()
        state["codex_auth"] = result
        return state

    def replay_export(self) -> dict[str, Any]:
        plan = self.latest_plan
        active_plan: dict[str, Any] | None = None
        if plan is not None:
            candidate_ids: list[str] = []
            frontier = next((receipt for receipt in plan.receipts if receipt.tool_name == CodexToolName.GENERATE_CANDIDATE_FRONTIER), None)
            if frontier is not None:
                candidates = frontier.output.get("candidates", []) if isinstance(frontier.output, dict) else []
                if isinstance(candidates, list):
                    candidate_ids = [str(candidate.get("candidate_id")) for candidate in candidates if isinstance(candidate, dict) and candidate.get("candidate_id")]
            active_plan = {
                "plan_id": plan.plan_id,
                "goal": plan.goal,
                "planner_backend": plan.planner_backend,
                "planner_metadata": plan.planner_metadata,
                "recommended_next_action": plan.recommended_next_action,
                "candidate_ids": candidate_ids,
                "action_envelopes": [
                    receipt.output.get("action_envelope")
                    for receipt in plan.receipts
                    if isinstance(receipt.output, dict) and isinstance(receipt.output.get("action_envelope"), dict)
                ],
                "trace": [
                    {
                        "tool": receipt.tool_name.value,
                        "status": receipt.status.value,
                        "stage_state": receipt.stage_state.value,
                        "swift_receipt_id": receipt.swift_receipt_id,
                        "authority_grant_id": receipt.authority_grant_id,
                        "correlation_id": receipt.correlation_id,
                        "denied_reason": receipt.denied_reason,
                    }
                    for receipt in plan.receipts
                ],
            }
        records = [record.envelope() for record in self.replay.records]
        violations = [violation.to_dict() for violation in check_replay(records)]
        return {
            "session_id": self.session_id,
            "state_version": self.state_version,
            "runtime": self.runtime_report(),
            "summary": to_jsonable(self.replay.summarize()),
            "active_plan": to_jsonable(active_plan),
            "records": records,
            "invariants": {"violations": violations},
        }

    def provider_permission_request(self) -> dict[str, Any]:
        request_access = getattr(self.provider, "request_access", None)
        if not callable(request_access):
            raise ValueError("active provider does not support OS permission requests")
        result = request_access()
        self._hydrate_provider_observation_if_available()
        self._rebuild_runtime()
        self.persistence.hydrate_runtime_frontier()
        self.persist()
        state = self.snapshot()
        state["provider_permission"] = result
        return state

    def rename_session(self, label: str) -> dict[str, Any]:
        cleaned = " ".join(str(label or "").split())[:80]
        self.session_label = cleaned or None
        self.persist()
        return self.snapshot()

    def archive_session(self) -> dict[str, Any]:
        self.archived_at = _now().isoformat()
        self.persist()
        return self.snapshot()

    def runtime_report(self) -> dict[str, Any]:
        report = runtime_report(
            mode=self.runtime_mode,
            run_dir=self.run_dir,
            observation_path=self.observation_path,
            profile_path=self.profile_path,
            session_id=self.session_id,
            backends=self._runtime_backends(),
        )
        health_status = getattr(self.planner, "health_status", None)
        if callable(health_status):
            report["codex_health"] = health_status(validate_remote=False)
        policy_health_status = getattr(self.policy, "health_status", None)
        if callable(policy_health_status):
            validate_remote = self.runtime_mode in {"live_diffusiongemma", "production"}
            policy_health = policy_health_status(validate_remote=validate_remote)
            report["diffusiongemma_health"] = policy_health
            self._apply_live_diffusiongemma_health_blockers(report, policy_health)
        provider_health_status = getattr(self.provider, "health_status", None)
        if callable(provider_health_status):
            provider_health = provider_health_status()
            report["provider_health"] = provider_health
            self._apply_live_provider_health_blockers(report, provider_health)
        report.setdefault("fixture_paths", {})["active_observation_id"] = self.observation.observation_id
        report.setdefault("fixture_paths", {})["provider_observation_loaded"] = self._provider_observation_loaded()
        if self._provider_observation_loaded():
            report.setdefault("fixture_paths", {})["uses_sample_fixtures"] = False
            self.provider_observation_error = None
        if self.provider_observation_error:
            report.setdefault("live_blockers", []).append(self.provider_observation_error)
        return report

    def _apply_live_diffusiongemma_health_blockers(self, report: dict[str, Any], policy_health: dict[str, Any]) -> None:
        if report.get("runtime_mode") not in {"live_diffusiongemma", "production"}:
            return
        blockers = report.setdefault("live_blockers", [])
        if not isinstance(blockers, list):
            return
        status = str(policy_health.get("status", "missing_credential"))
        credentials = report.get("credentials", {})
        if isinstance(credentials, dict):
            nim = credentials.get("diffusiongemma_nim")
            if isinstance(nim, dict):
                nim["status"] = status
                if policy_health.get("credential_source"):
                    nim["source"] = str(policy_health["credential_source"])
                nim["configured"] = bool(policy_health.get("configured"))
        if status == "ok":
            return
        if status == "missing_credential" and any("diffusiongemma_nim" in str(blocker) for blocker in blockers):
            return
        blocker = f"live DiffusionGemma remote health is {status}"
        reason = policy_health.get("reason")
        if reason:
            blocker += f": {reason}"
        if blocker not in blockers:
            blockers.append(blocker)

    def _apply_live_provider_health_blockers(self, report: dict[str, Any], provider_health: dict[str, Any]) -> None:
        credentials = report.get("credentials", {})
        provider_oauth = credentials.get("provider_oauth") if isinstance(credentials, dict) else None
        configured = bool(provider_health.get("configured"))
        if isinstance(provider_oauth, dict):
            provider_oauth["configured"] = configured
            provider_oauth["status"] = str(provider_health.get("status", "configured" if configured else "missing_permission"))
            provider_oauth["source"] = str(provider_health.get("auth_method", "provider_health"))
            provider_oauth["auth_method"] = str(provider_health.get("auth_method", "provider_health"))
        blockers = report.setdefault("live_blockers", [])
        if not isinstance(blockers, list):
            return
        if configured:
            blockers[:] = [
                blocker for blocker in blockers
                if blocker not in {"required credential missing: provider_oauth", "required credential wrong auth method: provider_oauth"}
            ]
            if self._provider_observation_loaded():
                blockers[:] = [blocker for blocker in blockers if blocker != "live provider/production mode is using sample fixture data"]
            return
        if report.get("runtime_mode") not in {"auto", "live_provider", "production"}:
            return
        status = str(provider_health.get("status", "missing_permission"))
        blocker = f"live provider health is {status}"
        reason = provider_health.get("reason")
        if reason:
            blocker += f": {reason}"
        if blocker not in blockers:
            blockers.append(blocker)

    def _runtime_backends(self) -> RuntimeBackends:
        codex_backend = getattr(self.planner, "backend_name", "deterministic_codex_tool_planner")
        policy_backend = getattr(self.policy, "backend_name", "heuristic_diffusiongemma_policy")
        provider_backend = getattr(self.provider, "provider_id", "local_stub")
        return RuntimeBackends(kernel=type(self.kernel).__name__, codex=codex_backend, diffusiongemma=policy_backend, provider=provider_backend)

    def _provider_observation_loaded(self) -> bool:
        expected_observation_id = getattr(self.provider, "observation_id", None)
        return bool(expected_observation_id and self.observation.observation_id == expected_observation_id)

    def _hydrate_provider_observation_if_available(self) -> bool:
        if not bool(getattr(self.provider, "real_provider", False) or getattr(self.provider, "real_oauth", False)):
            self.provider_observation_error = None
            return False
        health_status = getattr(self.provider, "health_status", None)
        read_observation = getattr(self.provider, "read_observation", None)
        if not callable(health_status) or not callable(read_observation):
            self.provider_observation_error = "live provider observation is unavailable"
            return False
        health = health_status()
        if not health.get("configured"):
            self.provider_observation_error = f"live provider observation not loaded: {health.get('status', 'not_configured')}"
            return False
        try:
            self.observation = read_observation(self.observation.user_scope_id, time_zone_id=self.observation.time_zone_id)
        except Exception as exc:
            self.provider_observation_error = f"live provider observation not loaded: {exc}"
            return False
        self.provider_observation_error = None
        return True

    def snapshot(self) -> dict[str, Any]:
        return self.snapshot_builder.snapshot()

    def view(self) -> dict[str, Any]:
        return self.projector.view()

    def persist(self) -> None:
        self.persistence.persist()

    def session_manifest(self, *, latest_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.persistence.session_manifest(latest_snapshot=latest_snapshot)

    def _receipt_is_realized_action(self, receipt: Any) -> bool:
        output = receipt.output if isinstance(receipt.output, dict) else {}
        swift = output.get("swift_receipt")
        if not isinstance(swift, dict):
            return False
        return str(swift.get("sync_status", "")) in {"materialized", "reverted"} or bool(swift.get("rollback_handle_id"))

    def _real_provider_active(self) -> bool:
        return bool(getattr(self.provider, "real_provider", False) or getattr(self.provider, "real_oauth", False))

    def _call(self, tool_name: CodexToolName, payload: dict[str, Any], *, grant_id: str | None = None, reason: str = "", correlation_id: str | None = None) -> CodexToolCall:
        raw = f"{tool_name.value}|{_now().isoformat()}|{payload}"
        return CodexToolCall(
            tool_call_id="tool_" + hashlib.sha1(raw.encode()).hexdigest()[:12],
            tool_name=tool_name,
            input=payload,
            requested_authority_tier=self.authority_tier,
            user_visible_reason=reason,
            authority_grant_id=grant_id,
            correlation_id=correlation_id,
            created_at=_now(),
        )

    def _title_for_receipt(self, action: str, denied_reason: str | None) -> str:
        if denied_reason:
            return "Swift denied the action"
        return {"simulate": "Simulation complete", "stage": "Action staged", "commit": "Action committed"}.get(action, "Action updated")

    def _candidate_for_receipt(self, receipt_id: str) -> CandidateCalendarAction | None:
        for record in reversed(self.replay.records):
            receipt = record.payload.get("receipt", {})
            candidate = record.payload.get("candidate", {})
            if receipt.get("receipt_id") == receipt_id and candidate:
                return CandidateCalendarAction.from_dict(candidate)
        return None

    def _receipt_payload_for_receipt(self, receipt_id: str) -> dict[str, Any] | None:
        for record in reversed(self.replay.records):
            receipt = record.payload.get("receipt", {})
            if receipt.get("receipt_id") == receipt_id:
                return dict(receipt)
        return None

    def _candidate_id_for_receipt(self, receipt_id: str) -> str | None:
        for record in reversed(self.replay.records):
            receipt = record.payload.get("receipt", {})
            if receipt.get("receipt_id") == receipt_id:
                return receipt.get("candidate_id")
        return None

    def _reward_for_feedback(self, receipt_id: str, feedback: str) -> RewardEvent:
        feedback = (feedback or "useful").strip().lower().replace("-", "_")
        positive = feedback in {"useful", "accepted"}
        negative = feedback in {"wrong", "not_needed", "too_interruptive", "downstream_conflict"}
        return RewardEvent(
            reward_event_id="reward_" + hashlib.sha1(f"{receipt_id}|{feedback}|{_now()}".encode()).hexdigest()[:12],
            receipt_id=receipt_id,
            observed_at=_now(),
            accepted=True if feedback == "accepted" else None,
            explicit_useful=True if feedback == "useful" else None,
            explicit_wrong=True if feedback == "wrong" else None,
            explicit_not_needed=True if feedback == "not_needed" else None,
            notification_dismissed=True if feedback == "too_interruptive" else None,
            downstream_conflict=True if feedback == "downstream_conflict" else None,
            utility_reward=0.7 if positive else 0.0,
            acceptance_reward=0.4 if feedback == "accepted" else 0.0,
            regret_penalty=0.7 if negative else 0.0,
            interruption_penalty=0.4 if feedback == "too_interruptive" else 0.0,
            social_risk_penalty=0.8 if feedback == "downstream_conflict" else 0.0,
            total_reward=(0.9 if positive else (-0.8 if negative else 0.0)),
        )


_MUTATING_SESSION_METHODS = {
    "reset", "issue_authority_grant", "create_plan", "candidate_action", "confirm_receipt", "undo", "feedback",
    "learning_exposure", "learning_outcome",
    "propose_profile_patch", "apply_profile_patch", "explain_denial", "run_self_play", "update_authority",
    "set_runtime_mode", "start_codex_subscription_sign_in", "provider_permission_request", "rename_session", "archive_session",
}
_LOCKED_SESSION_METHODS = _MUTATING_SESSION_METHODS | {"snapshot", "runtime_report", "replay_export", "persist", "view"}


def _install_session_lock_wrappers() -> None:
    def make_wrapper(name: str, fn: Any):
        @wraps(fn)
        def wrapped(self: DogfoodSessionState, *args: Any, **kwargs: Any):
            lock = getattr(self, "_lock", None)
            if lock is None:
                return fn(self, *args, **kwargs)
            with lock:
                if name in _MUTATING_SESSION_METHODS and hasattr(self, "_bump"):
                    self._bump()
                return fn(self, *args, **kwargs)
        return wrapped

    for name in _LOCKED_SESSION_METHODS:
        fn = getattr(DogfoodSessionState, name, None)
        if callable(fn) and not getattr(fn, "_calendarpilot_locked", False):
            wrapper = make_wrapper(name, fn)
            setattr(wrapper, "_calendarpilot_locked", True)
            setattr(DogfoodSessionState, name, wrapper)


def _session_bump(self: DogfoodSessionState) -> None:
    self.state_version = int(getattr(self, "state_version", 0)) + 1


DogfoodSessionState._bump = _session_bump  # type: ignore[attr-defined]
_install_session_lock_wrappers()
