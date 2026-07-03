

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
from calendar_pilot.environment.envelope import rollback_state_from_receipt
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.session_store import SessionStore
from calendar_pilot.environment.invariants import check_replay
from calendar_pilot.environment.router import KeywordRouter, ModelIntentRouter
from calendar_pilot.environment.taxonomy import taxonomy_health
from calendar_pilot.environment.trace import TRACE_BUS
from calendar_pilot.frontend.projector import FrontendProjector
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
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
from calendar_pilot.frontend.surface import build_frontend_snapshot
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
        self._rebuild_runtime()
        atexit.register(self.close)
        if not self._restore_session_state():
            ready_message = self._assistant_ready_message()
            self.transcript_events.append({
                "kind": "assistant",
                "title": ready_message["title"],
                "body": ready_message["body"],
                "metadata": ready_message["metadata"],
                "created_at": _now().isoformat(),
            })
            self.issue_authority_grant(confirmed=True, reason="dogfood_session_boot")
            self.persist()
        self._hydrate_runtime_frontier()
        self._write_launch_manifest_with_health()

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
                return eventkit
            return DeterministicCalendarProvider(state_path=self.run_dir / "provider_state.json", seed_observation=self.observation)
        requested_provider = explicit or ("apple_eventkit" if self.runtime_mode in {"live_provider", "production"} else "deterministic")
        if requested_provider in {"stub", "local_stub", "none"}:
            return None
        if requested_provider in {"apple", "apple_eventkit", "ios_calendar", "macos_calendar", "eventkit"}:
            return AppleEventKitProvider(state_path=self.run_dir / "apple_eventkit_provider.json")
        return DeterministicCalendarProvider(state_path=self.run_dir / "provider_state.json", seed_observation=self.observation)

    @staticmethod
    def _nim_credentials_available() -> bool:
        return any(os.environ.get(key) for key in ["CALENDAR_PILOT_NIM_API_KEY", "NVIDIA_API_KEY", "NIM_API_KEY"])

    def close(self) -> None:
        close = getattr(getattr(self, "kernel", None), "close", None)
        if callable(close):
            close()

    def reset(self) -> dict[str, Any]:
        self._load_primitives()
        self.policy = self._new_policy_for_mode()
        self.provider = self._new_provider_for_mode()
        self._hydrate_provider_observation_if_available()
        reset_provider = getattr(self.provider, "reset", None)
        if callable(reset_provider):
            reset_provider(self.observation)
        self.replay = ReplayBuffer()
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
        if intent not in {"calendar_goal", "mixed_calendar_operational"}:
            live_chat = self._live_conversation_response(goal, intent)
            if live_chat is not None:
                live_failed = bool(live_chat.metadata.get("error_category"))
                conversation_receipts = [] if live_failed else self._execute_live_conversation_tools(getattr(live_chat, "tool_calls", []), goal)
                extra_metadata = {"conversation_route": live_chat.route}
                if conversation_receipts:
                    extra_metadata.update(self._conversation_tool_metadata(conversation_receipts))
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
            local_tool_response = self._local_conversation_tool_response(goal, intent)
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
                "body": self._local_chat_body(intent),
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
        plan = self.planner.plan_goal(goal, self.observation, self.biography, authority_tier=self.authority_tier, commit=commit)
        self.latest_plan = plan
        self.latest_plan_observation_id = self.observation.observation_id
        self.latest_plan_observation_fingerprint = observation_fingerprint(self.observation)
        self._record_frontier_rejections_from_plan(plan)
        self._emit_trace(plan.plan_id, "planner", "planner_started", payload={"planner_backend": getattr(plan, "planner_backend", "unknown")})
        self._emit_trace(plan.plan_id, "frontier_service", "frontier_generated", payload=self._frontier_trace_payload(plan))
        conversation_receipts = []
        extra_metadata: dict[str, Any] = {}
        if intent == "mixed_calendar_operational":
            conversation_receipts = self._execute_live_conversation_tools(self._local_conversation_tool_calls(goal), goal)
            conversation_metadata = self._conversation_tool_metadata(conversation_receipts)
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
        plan_body = plan_failure["body"] if plan_failure else self._planner_response_body(metadata)
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

    def _live_conversation_response(self, goal: str, intent: str) -> Any | None:
        if self.runtime_mode not in LIVE_CODEX_MODES:
            return None
        chat_response = getattr(self.planner, "chat_response", None)
        if not callable(chat_response):
            return None
        return chat_response(
            goal,
            self.observation,
            self.biography,
            runtime_report=self.runtime_report(),
            intent=intent,
        )

    def _assistant_ready_message(self) -> dict[str, Any]:
        report = self.runtime_report()
        backends = report.get("backends", {})
        blockers = [str(item) for item in report.get("live_blockers", [])] if isinstance(report.get("live_blockers"), list) else []
        setup_notes = [str(item) for item in report.get("setup_notes", [])] if isinstance(report.get("setup_notes"), list) else []
        credentials = report.get("credentials", {})
        if blockers:
            title = "Assistant needs setup"
            body = (
                f"{report.get('mode_label', self.runtime_mode)} is selected, but the assistant is not fully live yet. "
                f"Active backends: Codex={backends.get('codex')}, DiffusionGemma={backends.get('diffusiongemma')}, "
                f"Swift={backends.get('kernel')}, provider={backends.get('provider')}. "
                f"Blockers: {'; '.join(blockers)}."
            )
        else:
            title = "CalendarPilot is ready"
            body = (
                f"{report.get('mode_label', self.runtime_mode)} is ready. "
                f"Active backends: Codex={backends.get('codex')}, DiffusionGemma={backends.get('diffusiongemma')}, "
                f"Swift={backends.get('kernel')}, provider={backends.get('provider')}. "
                "Tell me what you want checked or changed; I will keep actions, undo, feedback, and replay evidence visible."
            )
            if setup_notes:
                body += f" Optional setup: {'; '.join(setup_notes)}."
        return {
            "title": title,
            "body": body,
            "metadata": {
                "response_source": "ready_assistant_runtime",
                "runtime_mode": report.get("runtime_mode"),
                "planner_backend": backends.get("codex"),
                "policy_backend": backends.get("diffusiongemma"),
                "kernel_backend": backends.get("kernel"),
                "provider_backend": backends.get("provider"),
                "live_blockers": blockers,
                "setup_notes": setup_notes,
                "assistant_ready": not blockers,
                "fully_live": not blockers and not setup_notes,
            },
        }

    def _local_conversation_tool_response(self, goal: str, intent: str) -> dict[str, Any] | None:
        planned_calls = self._local_conversation_tool_calls(goal)
        if not planned_calls:
            return None
        receipts = self._execute_live_conversation_tools(planned_calls, goal)
        metadata = self._response_metadata(
            goal=goal,
            intent=intent,
            response_source="local_conversation_tools",
            reason="deterministic composer route to local CalendarPilot tools",
            extra_metadata={
                "conversation_route": "local_evidence_tool",
                **self._conversation_tool_metadata(receipts),
            },
        )
        return {
            "title": "Assistant handled request",
            "body": self._local_tool_response_body(receipts),
            "metadata": metadata,
            "receipts": receipts,
        }

    def _local_conversation_tool_calls(self, goal: str) -> list[dict[str, Any]]:
        normalized = " ".join(goal.lower().replace("-", " ").split())
        calls: list[dict[str, Any]] = []
        if any(term in normalized for term in ["replay", "trace", "evidence log", "audit log"]):
            calls.append(self._planned_conversation_tool(CodexToolName.QUERY_REPLAY_TRACE, {}, "Query replay evidence from the composer.", "local_replay"))
        if any(term in normalized for term in ["authority", "grant", "scope"]):
            calls.append(self._planned_conversation_tool(CodexToolName.INSPECT_AUTHORITY_SCOPE, {}, "Inspect Swift authority scope from the composer.", "local_authority"))
        if any(term in normalized for term in ["autonomy", "autonomous"]) and any(term in normalized for term in ["scope", "proposal", "propose", "allow"]):
            calls.append(self._planned_conversation_tool(CodexToolName.PROPOSE_AUTONOMY_SCOPE, {"candidate_id": self._latest_candidate_id() or ""}, "Propose a bounded autonomy scope from the composer.", "local_autonomy_scope"))
        if any(term in normalized for term in ["self play", "selfplay", "release gate", "adversary"]):
            calls.append(self._planned_conversation_tool(CodexToolName.RUN_SELF_PLAY_PROBE, {"episodes": self._episode_count_from_message(normalized)}, "Run self-play release gate from the composer.", "local_self_play"))
        if any(term in normalized for term in ["profile", "preference", "biography"]):
            if self._conversation_message_requests_profile_apply(normalized):
                calls.append(self._planned_conversation_tool(
                    CodexToolName.APPLY_PROFILE_PATCH,
                    self._latest_profile_patch_payload() or {"claim": "user correction", "correction": "", "confirmed": False},
                    "Apply the confirmed profile repair from the composer.",
                    "local_profile_apply",
                ))
            elif any(term in normalized for term in ["repair", "patch", "correct", "correction", "change", "prefer", "don't", "do not"]):
                calls.append(self._planned_conversation_tool(CodexToolName.PROPOSE_PROFILE_PATCH, {"correction": goal}, "Draft a profile repair from the composer.", "local_profile_patch"))
            else:
                calls.append(self._planned_conversation_tool(CodexToolName.INSPECT_PROFILE_CLAIMS, {}, "Inspect profile claims from the composer.", "local_profile_inspect"))
        if any(term in normalized for term in ["denial", "denied", "why swift", "swift denied"]):
            latest_denial = self._latest_actual_denial_reason() or goal
            calls.append(self._planned_conversation_tool(CodexToolName.EXPLAIN_SWIFT_DENIAL, {"denied_reason": latest_denial}, "Explain the latest Swift denial from the composer.", "local_denial"))
        if self._conversation_message_requests_undo(normalized):
            calls.append(self._planned_conversation_tool(CodexToolName.REQUEST_UNDO, {"rollback_handle_id": self._latest_rollback_handle_id() or ""}, "Request Swift undo from the composer.", "local_undo"))
        return calls[:4]

    def _planned_conversation_tool(self, tool_name: CodexToolName, payload: dict[str, Any], reason: str, correlation_id: str) -> dict[str, Any]:
        return {
            "tool_name": tool_name,
            "input": payload,
            "requested_authority_tier": self.authority_tier,
            "user_visible_reason": reason,
            "correlation_id": correlation_id,
        }

    @staticmethod
    def _episode_count_from_message(normalized: str) -> int:
        for token in normalized.split():
            try:
                value = int(token)
            except ValueError:
                continue
            return max(1, min(3, value))
        return 1

    @staticmethod
    def _conversation_message_requests_undo(normalized: str) -> bool:
        if normalized in {"undo", "undo it", "revert", "revert it", "rollback", "roll back"}:
            return True
        return any(term in normalized for term in [
            "undo ",
            "undo last",
            "undo the",
            "please undo",
            "revert ",
            "revert last",
            "revert the",
            "roll back",
            "rollback ",
            "rollback last",
            "rollback the",
        ])

    @staticmethod
    def _conversation_message_requests_profile_apply(normalized: str) -> bool:
        return "profile" in normalized and any(term in normalized for term in [
            "apply patch",
            "apply profile",
            "confirm patch",
            "confirm profile",
            "save patch",
            "save profile",
        ])

    @staticmethod
    def _conversation_message_has_calendar_action(normalized: str) -> bool:
        if normalized.startswith(("move ", "reschedule ", "schedule ", "plan ", "create ", "add ", "change ")):
            return True
        return any(term in normalized for term in [
            "make next week",
            "make this week",
            "less chaotic",
            "free up",
            "make room",
            "focus block",
            "prep before",
            "tomorrow meeting",
            "calendar",
            "meeting",
            "appointment",
        ])


    def _latest_rollback_handle_id(self) -> str | None:
        if getattr(self.kernel, "undo_ledger", None):
            return next(reversed(self.kernel.undo_ledger))
        if self.latest_plan is None:
            return None
        for receipt in reversed(self.latest_plan.receipts):
            output = receipt.output if isinstance(receipt.output, dict) else {}
            swift = output.get("swift_receipt")
            if isinstance(swift, dict) and swift.get("rollback_handle_id"):
                return str(swift["rollback_handle_id"])
        return None

    def _latest_candidate_id(self) -> str | None:
        if self.latest_plan is not None:
            for receipt in reversed(self.latest_plan.receipts):
                output = receipt.output if isinstance(receipt.output, dict) else {}
                winner = output.get("winner")
                if isinstance(winner, dict) and winner.get("candidate_id"):
                    return str(winner["candidate_id"])
                candidate = output.get("candidate")
                if isinstance(candidate, dict) and candidate.get("candidate_id"):
                    return str(candidate["candidate_id"])
                candidates = output.get("candidates")
                if isinstance(candidates, list) and candidates:
                    first = candidates[0]
                    if isinstance(first, dict) and first.get("candidate_id"):
                        return str(first["candidate_id"])
        if self.runtime.frontier:
            return next(iter(self.runtime.frontier))
        return None

    def _latest_profile_patch_payload(self) -> dict[str, Any] | None:
        for entry in reversed(self.profile_patch_history):
            if entry.get("kind") != "proposed":
                continue
            payload = self._profile_patch_payload_from_receipt(entry.get("receipt", {}))
            if payload is not None:
                return payload
        return None

    @staticmethod
    def _profile_patch_payload_from_receipt(receipt: Any) -> dict[str, Any] | None:
        if not isinstance(receipt, dict):
            return None
        if str(receipt.get("status")) != "requires_confirmation":
            return None
        if not bool(receipt.get("requires_user_confirmation", False)):
            return None
        output = receipt.get("output", {})
        plan = output.get("repair_plan") if isinstance(output, dict) else None
        if not isinstance(plan, dict):
            return None
        claim = str(plan.get("candidate_claim") or "").strip()
        provenance = plan.get("provenance", {})
        note = provenance.get("note") if isinstance(provenance, dict) else None
        correction = str(note).strip() if note is not None else ""
        if not correction:
            correction = str(plan.get("prompt") or "").strip()
        if not claim or not correction:
            return None
        return {
            "claim": claim,
            "correction": correction,
            "confirmed": True,
        }

    @staticmethod
    def _local_tool_response_body(receipts: list[dict[str, Any]]) -> str:
        names = [str(receipt.get("tool_name", "")) for receipt in receipts]
        if CodexToolName.REQUEST_UNDO.value in names:
            return "I requested Swift undo through the rollback ledger and attached the receipt."
        if CodexToolName.PROPOSE_AUTONOMY_SCOPE.value in names:
            autonomy = next((receipt for receipt in receipts if receipt.get("tool_name") == CodexToolName.PROPOSE_AUTONOMY_SCOPE.value), {})
            if str(autonomy.get("status")) == "failed" or autonomy.get("denied_reason"):
                return "I could not propose an autonomy scope yet. Generate or select a candidate action first."
            return "I proposed a bounded autonomy scope and attached the confirmation receipt."
        if CodexToolName.RUN_SELF_PLAY_PROBE.value in names:
            return "I ran the self-play release gate and attached the receipt."
        if CodexToolName.APPLY_PROFILE_PATCH.value in names:
            applied = next((receipt for receipt in receipts if receipt.get("tool_name") == CodexToolName.APPLY_PROFILE_PATCH.value), {})
            if str(applied.get("status")) != "succeeded":
                return "I could not apply a profile repair because there is no confirmed patch ready to apply."
            return "I applied the confirmed profile repair and attached the receipt."
        if CodexToolName.PROPOSE_PROFILE_PATCH.value in names:
            return "I drafted a profile repair proposal. It still requires confirmation before applying."
        if CodexToolName.INSPECT_PROFILE_CLAIMS.value in names:
            return "I inspected the learned profile claims and attached the receipt."
        if CodexToolName.EXPLAIN_SWIFT_DENIAL.value in names:
            return "I explained the Swift denial and attached the receipt."
        if CodexToolName.INSPECT_AUTHORITY_SCOPE.value in names:
            return "I inspected the current Swift authority scope and attached the receipt."
        return "I queried the replay evidence and attached the receipt."

    def _execute_live_conversation_tools(self, planned_calls: list[Any], user_message: str) -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        for idx, planned in enumerate(planned_calls):
            tool_name = planned.get("tool_name") if isinstance(planned, dict) else getattr(planned, "tool_name", None)
            if isinstance(tool_name, str):
                try:
                    tool_name = CodexToolName(tool_name)
                except ValueError:
                    continue
            if not isinstance(tool_name, CodexToolName):
                continue
            if tool_name == CodexToolName.REQUEST_UNDO and not self._conversation_message_requests_undo(" ".join(user_message.lower().replace("-", " ").split())):
                continue
            if tool_name == CodexToolName.APPLY_PROFILE_PATCH and not self._conversation_message_requests_profile_apply(" ".join(user_message.lower().replace("-", " ").split())):
                continue
            raw_input = planned.get("input", {}) if isinstance(planned, dict) else getattr(planned, "input", {})
            payload = self._conversation_tool_payload(tool_name, dict(raw_input or {}), user_message)
            grant_id = self._conversation_tool_grant_id(tool_name)
            raw = f"conversation|{tool_name.value}|{idx}|{_now().isoformat()}|{payload}"
            call = CodexToolCall(
                tool_call_id="tool_" + hashlib.sha1(raw.encode()).hexdigest()[:12],
                tool_name=tool_name,
                input=payload,
                requested_authority_tier=max(0, min(6, int((planned.get("requested_authority_tier") if isinstance(planned, dict) else getattr(planned, "requested_authority_tier", self.authority_tier)) or self.authority_tier))),
                user_visible_reason=str((planned.get("user_visible_reason") if isinstance(planned, dict) else getattr(planned, "user_visible_reason", "")) or "Live Codex requested this local evidence tool."),
                authority_grant_id=grant_id,
                correlation_id=str((planned.get("correlation_id") if isinstance(planned, dict) else getattr(planned, "correlation_id", "")) or f"conversation_{idx}"),
                created_at=_now(),
            )
            receipt = self.runtime.execute(call, self.observation, self.biography)
            if self.latest_plan is not None and self._receipt_is_realized_action(receipt):
                self.latest_plan.receipts.append(receipt)
            receipt_dict = receipt.to_dict()
            receipts.append(receipt_dict)
            self._record_conversation_tool_side_effect(tool_name, receipt_dict, payload)
        return receipts

    def _conversation_tool_payload(self, tool_name: CodexToolName, payload: dict[str, Any], user_message: str) -> dict[str, Any]:
        if tool_name == CodexToolName.RUN_SELF_PLAY_PROBE:
            try:
                episodes = int(payload.get("episodes", 1))
            except (TypeError, ValueError):
                episodes = 1
            payload["episodes"] = max(1, min(3, episodes))
        if tool_name == CodexToolName.PROPOSE_PROFILE_PATCH and not str(payload.get("correction", "")).strip():
            payload["correction"] = user_message
        if tool_name == CodexToolName.APPLY_PROFILE_PATCH:
            latest = self._latest_profile_patch_payload()
            if latest is None:
                payload["claim"] = str(payload.get("claim") or "user correction")
                payload["correction"] = str(payload.get("correction") or "")
                payload["confirmed"] = False
            else:
                payload["claim"] = str(payload.get("claim") or latest.get("claim") or "user correction")
                payload["correction"] = str(payload.get("correction") or latest.get("correction") or user_message)
                payload["confirmed"] = True
        if tool_name == CodexToolName.PROPOSE_AUTONOMY_SCOPE and not str(payload.get("candidate_id", "")).strip():
            payload["candidate_id"] = self._latest_candidate_id() or ""
        if tool_name == CodexToolName.EXPLAIN_SWIFT_DENIAL:
            requested_reason = str(payload.get("denied_reason", "")).strip()
            latest = self._latest_actual_denial_reason()
            if latest and self._is_generic_denial_reference(requested_reason, user_message):
                payload["denied_reason"] = latest
            elif not requested_reason:
                payload["denied_reason"] = "No denial reason was supplied."
        if tool_name == CodexToolName.REQUEST_UNDO and not str(payload.get("rollback_handle_id", "")).strip():
            payload["rollback_handle_id"] = self._latest_rollback_handle_id() or ""
        return payload

    def _latest_actual_denial_reason(self) -> str | None:
        for entry in reversed(self.denial_history):
            reason = str(entry.get("denied_reason") or "").strip()
            if not reason or self._is_generic_denial_reference(reason, ""):
                continue
            receipt = entry.get("receipt")
            if isinstance(receipt, dict):
                status = str(receipt.get("status") or receipt.get("sync_status") or "").strip()
                output = receipt.get("output", {}) if isinstance(receipt.get("output"), dict) else {}
                swift = output.get("swift_receipt", {}) if isinstance(output.get("swift_receipt"), dict) else {}
                sync_status = str(swift.get("sync_status") or output.get("sync_status") or "").strip()
                if status == "denied" or sync_status == "denied" or receipt.get("denied_reason"):
                    return reason
                continue
            if "denial_explanation" not in entry and "explanation" not in entry:
                return reason
        return None

    @staticmethod
    def _is_generic_denial_reference(value: str, user_message: str) -> bool:
        normalized = " ".join(value.lower().replace("-", " ").split())
        if not normalized:
            return True
        generic = {
            "denial",
            "denied",
            "the denial",
            "latest denial",
            "current denial",
            "last denial",
            "latest denial in current session",
            "the latest denial",
            "the current denial",
            "swift denial",
            "explain denial",
            "explain the denial",
            "explain the swift denial",
        }
        if normalized in generic or normalized.startswith("latest denial"):
            return True
        message = " ".join(user_message.lower().replace("-", " ").split())
        return bool(message and normalized == message and "denial" in message)

    def _conversation_tool_grant_id(self, tool_name: CodexToolName) -> str | None:
        if tool_name in {CodexToolName.INSPECT_AUTHORITY_SCOPE, CodexToolName.RUN_SELF_PLAY_PROBE}:
            return self.latest_grant_id(confirmed=False)
        if tool_name in {CodexToolName.PROPOSE_PROFILE_PATCH, CodexToolName.APPLY_PROFILE_PATCH}:
            return self.latest_grant_id(confirmed=True)
        if tool_name == CodexToolName.REQUEST_UNDO:
            return self.issue_authority_grant(confirmed=True, scopes=["undo"], reason="user_confirmed_composer_undo").grant_id
        return None

    def _record_conversation_tool_side_effect(self, tool_name: CodexToolName, receipt: dict[str, Any], payload: dict[str, Any]) -> None:
        output = receipt.get("output", {}) if isinstance(receipt.get("output"), dict) else {}
        if tool_name == CodexToolName.PROPOSE_PROFILE_PATCH:
            kind = "proposed" if self._profile_patch_payload_from_receipt(receipt) is not None else "proposal_failed"
            self.profile_patch_history.append({"kind": kind, "receipt": receipt, "created_at": _now().isoformat()})
        if tool_name == CodexToolName.APPLY_PROFILE_PATCH:
            bio_payload = output.get("biography") if isinstance(output, dict) else None
            if isinstance(bio_payload, dict):
                self.biography = UserBiography.from_dict(bio_payload)
            kind = "applied" if str(receipt.get("status")) == "succeeded" and isinstance(bio_payload, dict) else "needs_confirmation"
            self.profile_patch_history.append({"kind": kind, "receipt": receipt, "created_at": _now().isoformat()})
        if tool_name == CodexToolName.EXPLAIN_SWIFT_DENIAL:
            self.denial_history.append({
                "denied_reason": payload.get("denied_reason", ""),
                "explanation": output,
                "created_at": _now().isoformat(),
            })
        if tool_name == CodexToolName.RUN_SELF_PLAY_PROBE:
            metrics = output.get("metrics", {}) if isinstance(output.get("metrics"), dict) else {}
            top_failures = output.get("top_failure_modes", []) if isinstance(output.get("top_failure_modes"), list) else []
            failed = str(receipt.get("status", "")) != "succeeded" or bool(receipt.get("denied_reason"))
            release_decision = "probe_failed" if failed else ("hold_autonomy" if top_failures else "ship_runtime_gate")
            self.self_play_history.append({
                "episodes": int(payload.get("episodes", 1)),
                "backend": output.get("backend", payload.get("backend", "stub_fast")),
                "simulator_version": output.get("simulator_version", payload.get("simulator_version", "sim_v2")),
                "metrics": metrics,
                "top_failure_modes": top_failures,
                "release_decision": release_decision,
                "failure_reason": receipt.get("denied_reason") if failed else None,
                "created_at": _now().isoformat(),
            })

    @staticmethod
    def _conversation_tool_metadata(receipts: list[dict[str, Any]]) -> dict[str, Any]:
        def compact(receipt: dict[str, Any]) -> dict[str, Any]:
            output = receipt.get("output", {}) if isinstance(receipt.get("output"), dict) else {}
            swift = output.get("swift_receipt", {}) if isinstance(output.get("swift_receipt"), dict) else {}
            provider_rollback = output.get("provider_rollback", {}) if isinstance(output.get("provider_rollback"), dict) else {}
            return {
                "tool_name": str(receipt.get("tool_name", "")),
                "status": str(receipt.get("status", "")),
                "tool_call_id": str(receipt.get("tool_call_id", "")),
                "requires_user_confirmation": bool(receipt.get("requires_user_confirmation", False)),
                "denied_reason": receipt.get("denied_reason"),
                "swift_receipt_id": receipt.get("swift_receipt_id") or swift.get("receipt_id"),
                "sync_status": swift.get("sync_status") or output.get("sync_status"),
                "stage_state": receipt.get("stage_state") or swift.get("stage_state") or output.get("stage_state"),
                "rollback_handle_id": swift.get("rollback_handle_id") or output.get("rollback_handle_id"),
                "provider_rollback_status": provider_rollback.get("status"),
                "rollback_verified": provider_rollback.get("rollback_verified", output.get("rollback_verified")),
            }

        compact_receipts = [
            compact(receipt)
            for receipt in receipts
        ]
        return {
            "tool_sequence": [row["tool_name"] for row in compact_receipts],
            "tool_call_count": len(compact_receipts),
            "conversation_tool_receipt_count": len(compact_receipts),
            "conversation_tool_receipts": compact_receipts,
        }

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
        legacy_intent = self._classify_chat_intent(goal)
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

    def _classify_chat_intent(self, goal: str) -> str:
        normalized = " ".join(goal.lower().strip(" .!?\n\t").split())
        if not normalized:
            return "calendar_goal"
        calendar_terms = {
            "agenda", "appointment", "availability", "available", "block", "busy", "calendar", "call",
            "change", "commit", "day", "deadline", "event", "focus", "free", "lunch", "meeting",
            "month", "move", "plan", "prep", "reschedule", "schedule", "task", "time", "today",
            "tomorrow", "week", "weekend", "year",
        }
        metadata_terms = {
            "backend", "hard coded", "hardcoded", "llm", "metadata", "model", "response id", "thread id",
            "trace", "turn id",
        }
        operational_terms = {
            "autonomy", "autonomous", "biography", "denial", "denied", "grant", "profile", "replay",
            "rollback", "scope", "self play", "self-play", "selfplay", "undo",
        }
        greeting_terms = {"hello", "hi", "hey", "yo", "sup", "good morning", "good afternoon", "good evening"}
        has_calendar_term = any(term in normalized for term in calendar_terms)
        has_operational_term = any(term in normalized for term in operational_terms)
        profile_mutation_terms = {"repair", "patch", "correct", "correction", "prefer", "apply", "confirm", "save"}
        profile_mutation_request = any(term in normalized for term in ["profile", "preference", "biography"]) and any(term in normalized for term in profile_mutation_terms)
        undo_request = self._conversation_message_requests_undo(normalized)
        if has_operational_term and self._conversation_message_has_calendar_action(normalized):
            return "mixed_calendar_operational"
        if profile_mutation_request or undo_request:
            return "operational_tool"
        if has_operational_term:
            return "operational_tool"
        if any(term in normalized for term in metadata_terms) and not has_calendar_term:
            return "metadata_question"
        if normalized in greeting_terms or (len(normalized.split()) <= 3 and not has_calendar_term):
            return "smalltalk"
        return "calendar_goal" if has_calendar_term else "non_calendar"

    def _local_chat_body(self, intent: str) -> str:
        if intent == "metadata_question":
            return "This response was handled by the local app router. No live LLM call ran, so there is no response_id, thread_id, or turn_id for this turn."
        if intent == "smalltalk":
            return "I am here. Ask for a calendar change or inspection when you want me to generate candidate actions."
        return "I only route calendar goals into planning. This turn stayed local and did not contact a live model."

    def _planner_response_body(self, metadata: dict[str, Any]) -> str:
        if metadata.get("model_reached"):
            model = metadata.get("model_metadata", {}).get("model") or "live model"
            return f"Live Codex planned this turn with {model}; the trace metadata includes response, thread, and turn ids."
        if metadata.get("planner_backend") == "live_codex_app_server":
            return "Live Codex did not produce an executable model response for this turn. The metadata shows the blocker or failure category."
        return "I used the deterministic fixture planner, generated candidate futures, compared reward/regret, and prepared the leading action for Swift. No live LLM metadata was produced."

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
            grant_id = self.issue_authority_grant(confirmed=True, scopes=self.authority_scopes, reason=f"user_confirmed_commit:{candidate_id}").grant_id if confirmed else self.latest_grant_id(confirmed=True, scopes=scopes)
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
        attached = self.replay.attach_reward(receipt_id, reward)
        if not attached:
            candidate = self._candidate_for_receipt(receipt_id)
            self.replay.append_reward(reward, candidate=candidate, trace_id=candidate.candidate_id if candidate else receipt_id)
        entry = {"receipt_id": receipt_id, "feedback": feedback, "reason": reason, "reward": reward.to_dict(), "created_at": _now().isoformat()}
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
                },
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def propose_profile_patch(self, correction: str) -> dict[str, Any]:
        grant_id = self.latest_grant_id(confirmed=True)
        receipt = self.runtime.execute(self._call(CodexToolName.PROPOSE_PROFILE_PATCH, {"correction": correction}, grant_id=grant_id, reason="Draft a profile repair from user correction."), self.observation, self.biography)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        receipt_dict = receipt.to_dict()
        proposal_kind = "proposed" if self._profile_patch_payload_from_receipt(receipt_dict) is not None else "proposal_failed"
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

    def run_self_play(self, episodes: int = 3, backend: str = "stub_fast", simulator_version: str = "sim_v2") -> dict[str, Any]:
        episodes = int(episodes)
        if episodes <= 0:
            raise ValueError("episodes must be positive")
        simulator_version = simulator_version if simulator_version in {"sim_v1", "sim_v2"} else "sim_v2"
        grant_id = self.latest_grant_id(confirmed=True)
        receipt = self.runtime.execute(
            self._call(
                CodexToolName.RUN_SELF_PLAY_PROBE,
                {"episodes": episodes, "backend": backend, "simulator_version": simulator_version},
                grant_id=grant_id,
                reason="Probe the current policy against self-play adversaries.",
            ),
            self.observation,
            self.biography,
        )
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        metrics = receipt.output.get("metrics", {}) if isinstance(receipt.output, dict) else {}
        top_failures = receipt.output.get("top_failure_modes", []) if isinstance(receipt.output, dict) else []
        simulator_version = str(receipt.output.get("simulator_version", simulator_version)) if isinstance(receipt.output, dict) else simulator_version
        failed = receipt.status == CodexToolStatus.FAILED or not metrics or int(metrics.get("episodes", 0) or 0) < episodes
        release_decision = "probe_failed" if failed else ("hold_autonomy" if top_failures else "ship_runtime_gate")
        self.self_play_history.append({
            "episodes": episodes,
            "backend": backend,
            "simulator_version": simulator_version,
            "metrics": metrics,
            "top_failure_modes": top_failures,
            "release_decision": release_decision,
            "created_at": _now().isoformat(),
        })
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
                extra_metadata={
                    "self_play_episodes": episodes,
                    "self_play_backend": backend,
                    "simulator_version": simulator_version,
                    "release_decision": release_decision,
                },
            ),
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

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
            self._hydrate_runtime_frontier()
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
        self._hydrate_runtime_frontier()
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
        plan = self.latest_plan
        if plan is None:
            # Keep the legacy snapshot builder usable by passing an empty plan-shaped object.
            from calendar_pilot.codex.planner import CodexExecutivePlan
            plan = CodexExecutivePlan(plan_id="plan_empty", goal="")
        snapshot = build_frontend_snapshot(plan, self.observation, self.biography, self.replay).to_dict()
        snapshot["state_version"] = self.state_version
        runtime = self.runtime_report()
        snapshot["session"] = {
            "session_id": self.session_id,
            "label": self.session_label,
            "archived_at": self.archived_at,
            "runtime_mode": runtime["runtime_mode"],
            "requested_runtime_mode": runtime["requested_runtime_mode"],
            "authority_tier": self.authority_tier,
            "authority_scopes": self.authority_scopes,
            "run_dir": str(self.run_dir),
            "restore_error": self.restore_error,
            "provider_observation_error": self.provider_observation_error,
            "launch": self.launch_config.to_dict(),
            "state_version": self.state_version,
        }
        snapshot["runtime"] = runtime
        snapshot["summary"]["runtime_mode"] = runtime["runtime_mode"]
        snapshot["summary"]["requested_runtime_mode"] = runtime["requested_runtime_mode"]
        snapshot["summary"]["runtime_backends"] = runtime["backends"]
        snapshot["summary"]["runtime_live_blockers"] = runtime["live_blockers"]
        snapshot["summary"]["runtime_setup_notes"] = runtime.get("setup_notes", [])
        snapshot["chat"]["messages"] = self._chat_messages(snapshot)
        snapshot["summary"]["latest_turn"] = self._latest_turn_summary()
        snapshot["chat"]["latest_message_metadata"] = snapshot["summary"]["latest_turn"].get("metadata")
        snapshot["chat"]["runtime"] = {
            "mode": runtime["runtime_mode"],
            "requested_mode": runtime["requested_runtime_mode"],
            "label": runtime["mode_label"],
            "backends": runtime["backends"],
            "live_blockers": runtime["live_blockers"],
            "setup_notes": runtime.get("setup_notes", []),
        }
        snapshot["inspector"]["authority"]["history"] = self.authority_history[-10:]
        snapshot["inspector"]["runtime"] = {
            "title": "Runtime mode",
            "report": runtime,
            "rows": [
                {"key": "mode", "value": runtime["mode_label"]},
                {"key": "kernel", "value": runtime["backends"]["kernel"]},
                {"key": "codex", "value": runtime["backends"]["codex"]},
                {"key": "diffusiongemma", "value": runtime["backends"]["diffusiongemma"]},
                {"key": "diffusiongemma_health", "value": runtime.get("diffusiongemma_health", {}).get("status", "not_applicable")},
                {"key": "provider", "value": runtime["backends"]["provider"]},
                {"key": "provider_health", "value": runtime.get("provider_health", {}).get("status", "not_applicable")},
                {"key": "codex_health", "value": runtime.get("codex_health", {}).get("status", "not_applicable")},
                {"key": "live_blockers", "value": runtime["live_blockers"] or "none"},
                {"key": "setup_notes", "value": runtime.get("setup_notes", []) or "none"},
            ],
        }
        snapshot["inspector"]["profile"]["patch_history"] = self.profile_patch_history[-10:]
        snapshot["inspector"]["self_play"]["history"] = self.self_play_history[-5:]
        snapshot["inspector"]["replay"]["records"] = [record.envelope() for record in self.replay.records[-40:]]
        snapshot["learning"] = self._learning_snapshot(snapshot)
        snapshot["pipeline"] = {"turns": self._pipeline_turns()}
        snapshot["invariants"] = {"violations": [violation.to_dict() for violation in check_replay([record.envelope() for record in self.replay.records])]}
        snapshot["inspector"]["provider"] = self._provider_inspector()
        snapshot["inspector"]["feedback"] = self.feedback_history[-20:]
        snapshot["inspector"]["denials"] = self.denial_history[-20:]
        snapshot["sidebar"]["sessions"] = [{"session_id": self.session_id, "label": "Current fixture run", "active": True}]
        snapshot["sidebar"]["recent_runs"] = [
            {"label": event.get("body") or event.get("title", "run"), "created_at": event.get("created_at")} for event in self.transcript_events if event.get("kind") == "user"
        ][-8:]
        return snapshot

    def _learning_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        candidate_cards = snapshot.get("chat", {}).get("candidate_cards", [])
        rejection_counts: dict[str, int] = {}
        for record in self.replay.records:
            if record.record_type != "model_generation_rejection":
                continue
            reason = str(record.payload.get("reason", "unknown"))
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
        tuning: dict[str, Any] = {}
        if self.latest_plan is not None:
            for receipt in reversed(self.latest_plan.receipts):
                if getattr(receipt, "tool_name", None) != CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                    continue
                output = receipt.output if isinstance(receipt.output, dict) else {}
                policy_metadata = output.get("policy_metadata") if isinstance(output.get("policy_metadata"), dict) else {}
                tuning = policy_metadata.get("policy_tuning", {}) if isinstance(policy_metadata, dict) else {}
                break
        return {
            "taxonomy_health": taxonomy_health([card for card in candidate_cards if isinstance(card, dict)]),
            "frontier_rejections": {"count": sum(rejection_counts.values()), "reasons": rejection_counts},
            "reward_stream": [record.payload.get("reward", {}) for record in self.replay.records if record.record_type == "reward"][-20:],
            "tuning": tuning,
        }

    def _pipeline_turns(self) -> list[dict[str, Any]]:
        events = TRACE_BUS.events(self.session_id)
        by_trace: dict[str, dict[str, Any]] = {}
        for event in events:
            trace_id = str(event.get("trace_id") or "unknown")
            turn = by_trace.setdefault(trace_id, {"trace_id": trace_id, "status": "running", "stages": []})
            turn["stages"].append({
                "stage": event.get("stage"),
                "object": event.get("object"),
                "status": event.get("status"),
                "ts": event.get("ts"),
                "payload": event.get("payload", {}),
            })
            if event.get("status") in {"failed", "denied"}:
                turn["status"] = event.get("status")
            elif event.get("stage") in {"commit", "reward_recorded", "rollback", "frontier_generated"}:
                turn["status"] = "succeeded"
        return list(by_trace.values())[-50:]

    def view(self) -> dict[str, Any]:
        return self.projector.view()

    def _latest_turn_summary(self) -> dict[str, Any]:
        for event in reversed(self.transcript_events):
            kind = str(event.get("kind", ""))
            if kind == "user":
                return {
                    "role": "user",
                    "body": event.get("body", ""),
                    "created_at": event.get("created_at"),
                    "metadata": None,
                }
            if kind.startswith("assistant"):
                return {
                    "role": "assistant",
                    "kind": kind,
                    "title": event.get("title", ""),
                    "body": event.get("body", ""),
                    "created_at": event.get("created_at"),
                    "metadata": event.get("metadata"),
                }
        return {"role": None, "metadata": None}

    def _provider_inspector(self) -> dict[str, Any]:
        provider_snapshot = getattr(self.provider, "snapshot", None)
        if not callable(provider_snapshot):
            return {
                "title": "Provider state",
                "rows": [{"provider": "local_stub", "real_oauth": False, "write_boundary": "Swift/provider adapter only"}],
            }
        snapshot = provider_snapshot()
        rows = [
            {"key": "provider", "value": snapshot.get("provider")},
            {"key": "real_provider", "value": snapshot.get("real_provider", snapshot.get("real_oauth"))},
            {"key": "real_oauth", "value": snapshot.get("real_oauth")},
            {"key": "permission_status", "value": snapshot.get("permission_status", snapshot.get("oauth_status", "not_applicable"))},
            {"key": "auth_method", "value": snapshot.get("auth_method", "not_applicable")},
            {"key": "event_count", "value": snapshot.get("event_count")},
            {"key": "idempotency_keys", "value": snapshot.get("idempotency_keys")},
            {"key": "rollback_records", "value": snapshot.get("rollback_records")},
            {"key": "rollback_verified", "value": snapshot.get("rollback_verified")},
        ]
        rows.extend(snapshot.get("recent_mutations", [])[-5:])
        title = "Apple Calendar provider" if snapshot.get("provider") == "apple_eventkit" else "Deterministic provider state"
        return {
            "title": title,
            "rows": rows,
            "snapshot": snapshot,
            "permission": {"connect_enabled": bool(snapshot.get("connect_enabled")), "status": snapshot.get("permission_status")},
        }

    def persist(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        state_payload = self._state_payload()
        latest_snapshot = self.snapshot()
        session_manifest = self.session_manifest(latest_snapshot=latest_snapshot)
        self.store.save(
            state_payload=state_payload,
            latest_snapshot=latest_snapshot,
            session_manifest=session_manifest,
            replay=self.replay,
        )
        self._write_launch_manifest_with_health()

    def session_manifest(self, *, latest_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        latest_snapshot = latest_snapshot or self.snapshot()
        runtime = latest_snapshot.get("runtime") or self.runtime_report()
        return {
            "manifest_version": 2,
            "session_id": self.session_id,
            "session_label": self.session_label,
            "state_version": self.state_version,
            "runtime_mode": runtime.get("runtime_mode"),
            "requested_runtime_mode": runtime.get("requested_runtime_mode"),
            "backends": runtime.get("backends", {}),
            "run_dir": str(self.run_dir),
            "state_path": str(self.store.state_path),
            "latest_path": str(self.store.latest_path),
            "replay_path": str(self.store.replay_path),
            "observation_id": self.observation.observation_id,
            "observation_fingerprint": observation_fingerprint(self.observation),
            "updated_at": _now().isoformat(),
        }

    def _write_launch_manifest_with_health(self) -> None:
        manifest = self.launch_config.to_dict()
        manifest["health"] = self.runtime_report()
        atomic_write_json(self.launch_config.manifest_path, manifest)

    def _state_payload(self) -> dict[str, Any]:
        return {
            "version": 2,
            "state_version": self.state_version,
            "session_id": self.session_id,
            "session_label": self.session_label,
            "archived_at": self.archived_at,
            "runtime_mode": self.runtime_mode,
            "authority_tier": self.authority_tier,
            "authority_scopes": self.authority_scopes,
            "biography": self.biography.to_dict(),
            "latest_plan": self.latest_plan.to_dict() if self.latest_plan is not None else None,
            "latest_plan_observation_id": self.latest_plan_observation_id,
            "latest_plan_observation_fingerprint": self.latest_plan_observation_fingerprint,
            "transcript_events": self.transcript_events,
            "feedback_history": self.feedback_history,
            "denial_history": self.denial_history,
            "profile_patch_history": self.profile_patch_history,
            "self_play_history": self.self_play_history,
            "authority_history": self.authority_history,
            "restore_error": self.restore_error,
            "provider_observation_error": self.provider_observation_error,
            "launch": self.launch_config.to_dict(),
            "kernel": {
                "authority_grants": [grant.to_dict() for grant in self.kernel.authority_grants.values()],
                "undo_ledger": self.kernel.undo_ledger,
            },
            "updated_at": _now().isoformat(),
        }

    def _restore_session_state(self) -> bool:
        try:
            data = self.store.load_state()
            if data is None:
                return False
        except (OSError, TypeError, ValueError) as exc:
            self.restore_error = f"failed to restore {self.store.state_path.name}: {exc}"
            self.transcript_events.append({
                "kind": "assistant",
                "title": "Session restore failed",
                "body": self.restore_error,
                "created_at": _now().isoformat(),
            })
            return False
        self.session_id = str(data.get("session_id") or self.session_id)
        self.state_version = int(data.get("state_version", self.state_version) or 0)
        self.session_label = str(data.get("session_label") or "").strip() or None
        self.archived_at = str(data.get("archived_at") or "").strip() or None
        restored_runtime_mode = str(data.get("runtime_mode") or self.runtime_mode)
        if restored_runtime_mode != self.runtime_mode:
            self.runtime_mode = restored_runtime_mode
            self.launch_config = LaunchConfig.from_env(
                run_dir=self.run_dir,
                host=self.launch_config.host,
                port=self.launch_config.port,
                runtime_mode=self.runtime_mode,
            )
            self._replace_kernel_for_mode()
        else:
            self.runtime_mode = restored_runtime_mode
            self.launch_config = LaunchConfig.from_env(
                run_dir=self.run_dir,
                host=self.launch_config.host,
                port=self.launch_config.port,
                runtime_mode=self.runtime_mode,
            )
        self.restore_error = data.get("restore_error")
        self.provider_observation_error = data.get("provider_observation_error")
        self.authority_tier = int(data.get("authority_tier", self.authority_tier))
        scopes = data.get("authority_scopes")
        if isinstance(scopes, list):
            self.authority_scopes = [str(scope) for scope in scopes if str(scope).strip()]
        biography = data.get("biography")
        if isinstance(biography, dict):
            self.biography = UserBiography.from_dict(biography)
        plan = data.get("latest_plan")
        self.latest_plan = CodexExecutivePlan.from_dict(plan) if isinstance(plan, dict) else None
        self.latest_plan_observation_id = str(data.get("latest_plan_observation_id") or "") or None
        self.latest_plan_observation_fingerprint = str(data.get("latest_plan_observation_fingerprint") or "") or None
        self.transcript_events = list(data.get("transcript_events", []))
        self.feedback_history = list(data.get("feedback_history", []))
        self.denial_history = list(data.get("denial_history", []))
        self.profile_patch_history = list(data.get("profile_patch_history", []))
        self.self_play_history = list(data.get("self_play_history", []))
        self.authority_history = list(data.get("authority_history", []))
        kernel = data.get("kernel", {})
        grants = kernel.get("authority_grants", []) if isinstance(kernel, dict) else []
        self.kernel.authority_grants = {}
        self.kernel.undo_ledger = {}
        undo_ledger = kernel.get("undo_ledger", {}) if isinstance(kernel, dict) else {}
        active_undo_ledger = {str(k): str(v) for k, v in undo_ledger.items()} if isinstance(undo_ledger, dict) else {}
        if self.runtime_mode in {"auto", "swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}:
            restore_grant = getattr(self.kernel, "restore_authority_grant", None)
            if callable(restore_grant):
                for grant in grants:
                    if isinstance(grant, dict) and grant.get("grant_id"):
                        restore_grant(AuthorityGrant.from_dict(grant))
            restore_undo = getattr(self.kernel, "restore_undo_handle", None)
            generated_ids = self._generated_event_ids_by_rollback()
            if callable(restore_undo):
                for rollback_handle_id, candidate_id in active_undo_ledger.items():
                    restore_undo(
                        rollback_handle_id,
                        candidate_id,
                        self.observation,
                        generated_event_ids=generated_ids.get(rollback_handle_id, []),
                    )
        else:
            for grant in grants:
                if isinstance(grant, dict) and grant.get("grant_id"):
                    restored = AuthorityGrant.from_dict(grant)
                    self.kernel.authority_grants[restored.grant_id] = restored
            self.kernel.undo_ledger = active_undo_ledger
        if not self.transcript_events:
            self.transcript_events.append({
                "kind": "assistant",
                "title": "Session restored",
                "body": "CalendarPilot restored this dogfood run from disk.",
                "created_at": _now().isoformat(),
            })
        return True

    def _generated_event_ids_by_rollback(self) -> dict[str, list[str]]:
        generated: dict[str, list[str]] = {}
        for record in self.replay.records:
            receipt = record.payload.get("receipt", {})
            if isinstance(receipt, dict) and receipt.get("rollback_handle_id"):
                generated[str(receipt["rollback_handle_id"])] = [str(item) for item in receipt.get("generated_event_ids", [])]
        if self.latest_plan is not None:
            for tool_receipt in self.latest_plan.receipts:
                output = tool_receipt.output if isinstance(tool_receipt.output, dict) else {}
                swift_receipt = output.get("swift_receipt")
                if isinstance(swift_receipt, dict) and swift_receipt.get("rollback_handle_id"):
                    generated[str(swift_receipt["rollback_handle_id"])] = [str(item) for item in swift_receipt.get("generated_event_ids", [])]
        return generated

    def _hydrate_runtime_frontier(self) -> None:
        self.runtime.frontier.clear()
        self._prune_latest_plan_for_active_observation()
        for record in self.replay.records:
            candidate = record.payload.get("candidate")
            if isinstance(candidate, dict) and candidate.get("candidate_id"):
                if not self._candidate_restore_allowed(record.payload.get("observation_id"), record.payload.get("observation_fingerprint")):
                    continue
                restored = CandidateCalendarAction.from_dict(candidate)
                self.runtime.frontier[restored.candidate_id] = restored
        if self.latest_plan is None:
            return
        if not self._candidate_restore_allowed(self.latest_plan_observation_id, self.latest_plan_observation_fingerprint):
            return
        for receipt in self.latest_plan.receipts:
            output = receipt.output if isinstance(receipt.output, dict) else {}
            for candidate in output.get("candidates", []) if isinstance(output.get("candidates"), list) else []:
                if isinstance(candidate, dict) and candidate.get("candidate_id"):
                    restored = CandidateCalendarAction.from_dict(candidate)
                    self.runtime.frontier[restored.candidate_id] = restored
            candidate = output.get("candidate")
            if isinstance(candidate, dict) and candidate.get("candidate_id"):
                restored = CandidateCalendarAction.from_dict(candidate)
                self.runtime.frontier[restored.candidate_id] = restored

    def _candidate_restore_allowed(self, source_observation_id: Any, source_fingerprint: Any) -> bool:
        if not self._real_provider_active():
            return True
        if source_observation_id != self.observation.observation_id:
            return False
        return bool(source_fingerprint and source_fingerprint == observation_fingerprint(self.observation))

    def _prune_latest_plan_for_active_observation(self) -> None:
        if self.latest_plan is None or self._candidate_restore_allowed(self.latest_plan_observation_id, self.latest_plan_observation_fingerprint):
            return
        before = len(self.latest_plan.receipts)
        self.latest_plan.receipts = [receipt for receipt in self.latest_plan.receipts if self._receipt_is_realized_action(receipt)]
        if len(self.latest_plan.receipts) == before:
            return
        self.transcript_events.append({
            "kind": "assistant",
            "title": "Plan needs refresh",
            "body": "Candidate controls were cleared because the active calendar observation changed. Existing committed receipts remain available for undo and replay.",
            "created_at": _now().isoformat(),
            "stale_observation_id": self.latest_plan_observation_id,
            "active_observation_id": self.observation.observation_id,
        })

    def _receipt_is_realized_action(self, receipt: Any) -> bool:
        output = receipt.output if isinstance(receipt.output, dict) else {}
        swift = output.get("swift_receipt")
        if not isinstance(swift, dict):
            return False
        return str(swift.get("sync_status", "")) in {"materialized", "reverted"} or bool(swift.get("rollback_handle_id"))

    def _real_provider_active(self) -> bool:
        return bool(getattr(self.provider, "real_provider", False) or getattr(self.provider, "real_oauth", False))

    def _chat_messages(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for idx, event in enumerate(self.transcript_events):
            role = "assistant" if event.get("kind", "assistant").startswith("assistant") else "user"
            message = {
                "id": f"msg_{idx}",
                "role": role,
                "title": event.get("title", ""),
                "body": event.get("body", ""),
                "metadata": event.get("metadata"),
                "created_at": event.get("created_at"),
                "cards": [],
            }
            if event.get("kind") == "assistant_plan":
                message["cards"] = snapshot.get("chat", {}).get("candidate_cards", [])[:3]
            if event.get("kind") == "assistant_receipt" and event.get("receipt"):
                message["cards"] = [{"type": "receipt", "receipt": event["receipt"]}]
            if event.get("kind", "").startswith("assistant") and event.get("conversation_receipts"):
                message["cards"].extend([
                    {"type": "receipt", "receipt": receipt}
                    for receipt in event.get("conversation_receipts", [])
                    if isinstance(receipt, dict)
                ])
            messages.append(message)
        if self.latest_plan is None:
            return messages
        # Keep the latest action queue visible as the final assistant affordance.
        if snapshot.get("action_queue"):
            messages.append({
                "id": "msg_latest_actions",
                "role": "assistant",
                "title": "Acting controls",
                "body": "The latest Swift receipts are available for undo and feedback.",
                "cards": [{"type": "action_queue", "actions": snapshot.get("action_queue", [])}],
                "created_at": _now().isoformat(),
            })
        return messages

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
