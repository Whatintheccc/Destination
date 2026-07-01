from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from threading import RLock
from typing import Any

from calendar_pilot.codex import CodexToolPlanner, CodexToolRuntime
from calendar_pilot.codex.planner import CodexExecutivePlan
from calendar_pilot.frontend.surface import build_frontend_snapshot
from calendar_pilot.providers import CalendarProviderError, FixtureCalendarProvider
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import (
    ActuationMode,
    CalendarActionReceipt,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    CodexToolReceipt,
    CodexToolStatus,
    RawCalendarObservation,
    RewardEvent,
    StageState,
    UserBiography,
    parse_dt,
    to_jsonable,
)


ROOT = Path(__file__).resolve().parents[3]


class DogfoodSessionState:
    """Mutable dogfood app state behind the static frontend.

    This is intentionally small and local-first. It gives the dogfood UI a real
    API and durable replay/provider state without introducing a web framework or
    external provider credentials.
    """

    def __init__(
        self,
        *,
        observation_path: str | Path = ROOT / "data/sample_calendar.json",
        profile_path: str | Path = ROOT / "data/sample_profile.json",
        run_dir: str | Path = ROOT / "runs/dogfood/default",
        runtime: CodexToolRuntime | None = None,
        provider: FixtureCalendarProvider | None = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.session_path = self.run_dir / "session.json"
        self.replay_path = self.run_dir / "replay.jsonl"
        self.lock = RLock()
        seed_observation = RawCalendarObservation.from_dict(json.loads(Path(observation_path).read_text(encoding="utf-8")))
        self.biography = UserBiography.from_dict(json.loads(Path(profile_path).read_text(encoding="utf-8")))
        self.provider = provider or FixtureCalendarProvider(self.run_dir / "fixture_provider.json", seed_observation=seed_observation)
        self.replay = ReplayBuffer.load_jsonl(self.replay_path)
        self.runtime = runtime or CodexToolRuntime(replay=self.replay)
        self.runtime.replay = self.replay
        self.planner = CodexToolPlanner(runtime=self.runtime)
        self.current_plan: CodexExecutivePlan | None = None
        self.current_goal = ""
        self.authority_tier = 3
        self.applied_swift_receipts: set[str] = set()
        self.last_error: str | None = None
        self._load_session()

    @property
    def observation(self) -> RawCalendarObservation:
        return self.provider.read_observation(self.biography.user_scope_id)

    def state(self) -> dict[str, Any]:
        with self.lock:
            return self._state_unlocked()

    def create_plan(self, goal: str, *, authority_tier: int = 3, commit: bool = False) -> dict[str, Any]:
        with self.lock:
            self.current_goal = goal.strip() or "Make next week less chaotic"
            self.authority_tier = int(authority_tier)
            self.current_plan = self.planner.plan_goal(
                self.current_goal,
                self.observation,
                self.biography,
                authority_tier=self.authority_tier,
                commit=bool(commit),
            )
            self._apply_committed_receipts()
            self._save()
            return self._state_unlocked(extra={"created_plan": self.current_plan.to_dict()})

    def simulate_candidate(self, candidate_id: str) -> dict[str, Any]:
        return self._execute_candidate_tool(CodexToolName.SIMULATE_ACTION_PROGRAM, candidate_id, confirmed=False)

    def stage_candidate(self, candidate_id: str) -> dict[str, Any]:
        return self._execute_candidate_tool(CodexToolName.STAGE_ACTION_PACKET, candidate_id, confirmed=False)

    def commit_candidate(self, candidate_id: str) -> dict[str, Any]:
        return self._execute_candidate_tool(CodexToolName.REQUEST_COMMIT, candidate_id, confirmed=True)

    def confirm_receipt(self, receipt_id: str) -> dict[str, Any]:
        with self.lock:
            candidate_id = self._candidate_id_for_receipt(receipt_id)
        if not candidate_id:
            return self._error_state(f"receipt {receipt_id} does not contain a candidate to confirm")
        return self.commit_candidate(candidate_id)

    def undo(self, rollback_handle_id: str) -> dict[str, Any]:
        with self.lock:
            grant_id = self._issue_grant(confirmed=True)
            call = self._new_call(
                CodexToolName.REQUEST_UNDO,
                {"rollback_handle_id": rollback_handle_id},
                grant_id=grant_id,
                correlation_id=rollback_handle_id,
            )
            receipt = self._execute(call)
            if receipt.status == CodexToolStatus.COMMITTED and not receipt.denied_reason:
                provider_result = self.provider.rollback(rollback_handle_id)
                receipt.output["fixture_provider"] = provider_result.to_dict()
            self._save()
            return self._state_unlocked(extra={"undo_receipt": receipt.to_dict()})

    def propose_profile_patch(self, correction: str) -> dict[str, Any]:
        with self.lock:
            call = self._new_call(CodexToolName.PROPOSE_PROFILE_PATCH, {"correction": correction})
            receipt = self._execute(call)
            self._save()
            return self._state_unlocked(extra={"profile_patch": receipt.to_dict()})

    def apply_profile_patch(self, claim: str, correction: str, *, confirmed: bool = True) -> dict[str, Any]:
        with self.lock:
            call = self._new_call(
                CodexToolName.APPLY_PROFILE_PATCH,
                {"claim": claim, "correction": correction, "confirmed": bool(confirmed)},
            )
            receipt = self._execute(call)
            biography = receipt.output.get("biography") if isinstance(receipt.output, dict) else None
            if isinstance(biography, dict):
                self.biography = UserBiography.from_dict(biography)
            self._save()
            return self._state_unlocked(extra={"profile_patch": receipt.to_dict()})

    def explain_denial(self, denied_reason: str) -> dict[str, Any]:
        with self.lock:
            call = self._new_call(CodexToolName.EXPLAIN_SWIFT_DENIAL, {"denied_reason": denied_reason})
            receipt = self._execute(call)
            self._save()
            return self._state_unlocked(extra={"denial_explanation": receipt.to_dict()})

    def replay_trace(self, candidate_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            payload: dict[str, Any] = {}
            if candidate_id:
                payload["candidate_id"] = candidate_id
            call = self._new_call(CodexToolName.QUERY_REPLAY_TRACE, payload, correlation_id=candidate_id)
            receipt = self._execute(call)
            self._save()
            return self._state_unlocked(extra={"replay": receipt.output})

    def feedback(self, receipt_id: str, feedback: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            candidate, receipt = self._candidate_and_receipt_for_reward(receipt_id)
            if candidate is None or receipt is None:
                return self._error_state(f"cannot attach feedback: unknown receipt_id {receipt_id}")
            reward = self._reward_from_feedback(receipt_id, feedback)
            attached = self.replay.attach_reward(receipt_id, reward)
            if not attached:
                self.replay.append_reward(reward, candidate, receipt, trace_id=candidate.candidate_id if candidate else receipt_id)
            self.biography = self.runtime.biography_store.update_from_reward(self.biography, reward, source="dogfood_feedback")
            self._save()
            return self._state_unlocked(extra={"feedback": {"attached": attached, "reward": reward.to_dict()}})

    def reset_fixture(self) -> dict[str, Any]:
        with self.lock:
            seed = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8")))
            self.provider.reset(seed)
            self.current_plan = None
            self.current_goal = ""
            self.applied_swift_receipts.clear()
            self.last_error = None
            self._save()
            return self._state_unlocked(extra={"reset": True})

    def _execute_candidate_tool(self, tool_name: CodexToolName, candidate_id: str, *, confirmed: bool) -> dict[str, Any]:
        with self.lock:
            if candidate_id not in self.runtime.frontier:
                return self._error_state(f"unknown candidate_id {candidate_id}")
            grant_id = self._issue_grant(confirmed=confirmed)
            call = self._new_call(tool_name, {"candidate_id": candidate_id}, grant_id=grant_id, correlation_id=candidate_id)
            receipt = self._execute(call)
            if tool_name == CodexToolName.REQUEST_COMMIT:
                self._apply_committed_receipts()
            self._save()
            return self._state_unlocked(extra={"tool_receipt": receipt.to_dict()})

    def _execute(self, call: CodexToolCall) -> CodexToolReceipt:
        observation = self.observation
        if self.current_plan is not None:
            self.current_plan.calls.append(call)
        receipt = self.runtime.execute(call, observation, self.biography)
        if self.current_plan is not None:
            self.current_plan.receipts.append(receipt)
        return receipt

    def _apply_committed_receipts(self) -> None:
        if self.current_plan is None:
            return
        for idx, receipt in enumerate(list(self.current_plan.receipts)):
            swift = receipt.output.get("swift_receipt") if isinstance(receipt.output, dict) else None
            candidate_payload = receipt.output.get("candidate") if isinstance(receipt.output, dict) else None
            if not isinstance(swift, dict) or not isinstance(candidate_payload, dict):
                continue
            receipt_id = str(swift.get("receipt_id") or receipt.swift_receipt_id or "")
            if not receipt_id or receipt_id in self.applied_swift_receipts:
                continue
            if swift.get("sync_status") != "materialized" or swift.get("denied_reason"):
                continue
            candidate = CandidateCalendarAction.from_dict(candidate_payload)
            try:
                provider_result = self.provider.apply_candidate(
                    candidate,
                    idempotency_key=f"commit:{receipt_id}",
                    rollback_handle_id=swift.get("rollback_handle_id"),
                )
                receipt.output["fixture_provider"] = provider_result.to_dict()
                self.applied_swift_receipts.add(receipt_id)
            except CalendarProviderError as exc:
                output = dict(receipt.output)
                swift_denied = dict(swift)
                swift_denied["sync_status"] = "denied"
                swift_denied["denied_reason"] = str(exc)
                swift_denied["stage_state"] = StageState.DENIED.value
                output["swift_receipt"] = swift_denied
                output["stage_state"] = StageState.DENIED.value
                output["fixture_provider"] = {"status": "denied", "message": str(exc)}
                output["provider_denied_reason"] = str(exc)
                self.current_plan.receipts[idx] = replace(
                    receipt,
                    status=CodexToolStatus.DENIED,
                    output=output,
                    denied_reason=str(exc),
                    stage_state=StageState.DENIED,
                )
                self.last_error = str(exc)

    def _state_unlocked(self, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = self._snapshot()
        summary = self.replay.summarize()
        response = {
            "session": {
                "run_dir": str(self.run_dir),
                "replay_path": str(self.replay_path),
                "provider_checksum": self.provider.checksum(),
                "authority_tier": self.authority_tier,
                "last_error": self.last_error,
            },
            "snapshot": snapshot,
            "replay_summary": to_jsonable(summary),
            "training_rows": self.replay.training_table(),
        }
        if extra:
            response.update(extra)
        return response

    def _snapshot(self) -> dict[str, Any]:
        if self.current_plan is None:
            return {
                "product_name": "CalendarPilot",
                "goal": self.current_goal,
                "summary": {
                    "recommended_next_action": "enter_goal",
                    "default_path": "codex_tool_executive",
                    "chat_role": "secondary_explanation_surface",
                    "primary_surfaces": [],
                },
                "panels": [],
                "action_queue": [],
                "trace": [],
            }
        return build_frontend_snapshot(self.current_plan, self.observation, self.biography, self.replay).to_dict()

    def _issue_grant(self, *, confirmed: bool) -> str:
        observation = self.observation
        grant = self.runtime.kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=self.authority_tier,
            scopes=["recommend", "stage", "commit_private", "undo"],
            confirmation_provenance="dogfood_user_confirmed" if confirmed else "dogfood_stage_scope",
            confirmed_by_user=confirmed,
            issued_at=observation.observed_at,
        )
        return grant.grant_id

    def _new_call(
        self,
        tool_name: CodexToolName,
        payload: dict[str, Any],
        *,
        grant_id: str | None = None,
        correlation_id: str | None = None,
    ) -> CodexToolCall:
        raw = f"{tool_name.value}|{datetime.now(timezone.utc).isoformat()}|{payload}"
        return CodexToolCall(
            tool_call_id="tool_" + hashlib.sha1(raw.encode()).hexdigest()[:12],
            tool_name=tool_name,
            input=payload,
            requested_authority_tier=self.authority_tier,
            user_visible_reason=f"dogfood {tool_name.value}",
            authority_grant_id=grant_id,
            correlation_id=correlation_id,
            created_at=datetime.now(timezone.utc),
        )

    def _candidate_id_for_receipt(self, receipt_id: str) -> str | None:
        if self.current_plan is None:
            return None
        for receipt in reversed(self.current_plan.receipts):
            swift = receipt.output.get("swift_receipt") if isinstance(receipt.output, dict) else None
            if isinstance(swift, dict) and (swift.get("receipt_id") == receipt_id or receipt.swift_receipt_id == receipt_id):
                candidate = receipt.output.get("candidate")
                if isinstance(candidate, dict):
                    return str(candidate.get("candidate_id", "")) or None
        return None

    def _candidate_and_receipt_for_reward(self, receipt_id: str) -> tuple[CandidateCalendarAction | None, CalendarActionReceipt | None]:
        for record in reversed(self.replay.records):
            receipt = record.payload.get("receipt", {})
            if receipt.get("receipt_id") != receipt_id:
                continue
            candidate_payload = record.payload.get("candidate")
            candidate = CandidateCalendarAction.from_dict(candidate_payload) if isinstance(candidate_payload, dict) else None
            return candidate, self._calendar_receipt_from_dict(receipt)
        return None, None

    @staticmethod
    def _calendar_receipt_from_dict(data: dict[str, Any] | None) -> CalendarActionReceipt | None:
        if not data:
            return None
        executed_at = parse_dt(data.get("executed_at")) or datetime.now(timezone.utc)
        return CalendarActionReceipt(
            receipt_id=str(data.get("receipt_id", "")),
            candidate_id=str(data.get("candidate_id", "")),
            executed_at=executed_at,
            executed_by=str(data.get("executed_by", "")),
            authority_tier_used=int(data.get("authority_tier_used", 0)),
            sync_status=str(data.get("sync_status", "")),
            rollback_handle_id=data.get("rollback_handle_id"),
            conflict_check_passed=bool(data.get("conflict_check_passed", False)),
            generated_event_ids=[str(x) for x in data.get("generated_event_ids", [])],
            staged_action_ids=[str(x) for x in data.get("staged_action_ids", [])],
            rejected_action_types=[str(x) for x in data.get("rejected_action_types", [])],
            provider_id=str(data.get("provider_id", "")),
            actuation_mode=ActuationMode(data.get("actuation_mode", "no_op")),
            denied_reason=data.get("denied_reason"),
            authority_grant_id=data.get("authority_grant_id"),
            confirmation_provenance=data.get("confirmation_provenance"),
            stage_state=StageState(data.get("stage_state", "no_op")),
            correlation_id=data.get("correlation_id"),
        )

    @staticmethod
    def _reward_from_feedback(receipt_id: str, feedback: dict[str, Any]) -> RewardEvent:
        flags = {k: bool(feedback.get(k, False)) for k in [
            "accepted",
            "edited",
            "undone",
            "deleted_later",
            "ignored",
            "explicit_useful",
            "explicit_wrong",
            "explicit_not_needed",
            "notification_dismissed",
            "survived_until_event",
            "downstream_conflict",
            "reengaged",
        ]}
        utility = 1.25 if flags["explicit_useful"] else 0.0
        acceptance = 1.0 if flags["accepted"] else 0.0
        engagement = (0.25 if flags["edited"] else 0.0) + (0.35 if flags["reengaged"] else 0.0)
        regret = (-2.5 if flags["undone"] else 0.0) + (-1.5 if flags["deleted_later"] else 0.0) + (-2.0 if flags["explicit_wrong"] else 0.0)
        interruption = (-0.8 if flags["notification_dismissed"] else 0.0) + (-0.5 if flags["ignored"] else 0.0) + (-1.0 if flags["explicit_not_needed"] else 0.0)
        social = -2.0 if flags["downstream_conflict"] else 0.0
        survived = 0.5 if flags["survived_until_event"] else 0.0
        total = utility + acceptance + engagement + regret + interruption + social + survived
        digest = hashlib.sha1(f"{receipt_id}|{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:12]
        return RewardEvent(
            reward_event_id=f"rew_dogfood_{digest}",
            receipt_id=receipt_id,
            observed_at=datetime.now(timezone.utc),
            **flags,
            utility_reward=round(utility + survived, 4),
            acceptance_reward=round(acceptance, 4),
            engagement_reward=round(engagement, 4),
            regret_penalty=round(regret, 4),
            interruption_penalty=round(interruption, 4),
            social_risk_penalty=round(social, 4),
            total_reward=round(total, 4),
        )

    def _error_state(self, message: str) -> dict[str, Any]:
        with self.lock:
            self.last_error = message
            self._save()
            state = self._state_unlocked()
            state["error"] = message
            return state

    def _save(self) -> None:
        self.replay.save_jsonl(self.replay_path)
        payload = {
            "current_goal": self.current_goal,
            "authority_tier": self.authority_tier,
            "biography": self.biography.to_dict(),
            "current_plan": self.current_plan.to_dict() if self.current_plan else None,
            "applied_swift_receipts": sorted(self.applied_swift_receipts),
            "last_error": self.last_error,
        }
        self.session_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _load_session(self) -> None:
        if not self.session_path.exists():
            return
        data = json.loads(self.session_path.read_text(encoding="utf-8"))
        self.current_goal = str(data.get("current_goal", ""))
        self.authority_tier = int(data.get("authority_tier", 3))
        if isinstance(data.get("biography"), dict):
            self.biography = UserBiography.from_dict(data["biography"])
        if isinstance(data.get("current_plan"), dict):
            self.current_plan = self._plan_from_dict(data["current_plan"])
            self._restore_frontier(self.current_plan)
            self._restore_kernel_undo_ledger()
        self.applied_swift_receipts = set(str(x) for x in data.get("applied_swift_receipts", []))
        self.last_error = data.get("last_error")

    @staticmethod
    def _plan_from_dict(data: dict[str, Any]) -> CodexExecutivePlan:
        return CodexExecutivePlan(
            plan_id=str(data.get("plan_id", "plan_restored")),
            goal=str(data.get("goal", "")),
            calls=[CodexToolCall.from_dict(c) for c in data.get("calls", [])],
            receipts=[CodexToolReceipt.from_dict(r) for r in data.get("receipts", [])],
            recommended_next_action=str(data.get("recommended_next_action", "")),
        )

    def _restore_frontier(self, plan: CodexExecutivePlan) -> None:
        for receipt in plan.receipts:
            candidates = receipt.output.get("candidates", []) if isinstance(receipt.output, dict) else []
            for candidate_payload in candidates:
                if isinstance(candidate_payload, dict):
                    candidate = CandidateCalendarAction.from_dict(candidate_payload)
                    self.runtime.frontier[candidate.candidate_id] = candidate

    def _restore_kernel_undo_ledger(self) -> None:
        ledger = getattr(self.runtime.kernel, "undo_ledger", None)
        if not isinstance(ledger, dict):
            return
        for rollback_handle_id, candidate_id in self.provider.rollback_records().items():
            ledger.setdefault(rollback_handle_id, candidate_id)
