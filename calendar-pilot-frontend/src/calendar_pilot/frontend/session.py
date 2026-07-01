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
        self.authority_scopes = ["recommend", "stage", "commit_private", "undo"]
        self.applied_swift_receipts: set[str] = set()
        self.undo_history: list[dict[str, Any]] = []
        self.feedback_history: list[dict[str, Any]] = []
        self.profile_patch_history: list[dict[str, Any]] = []
        self.pending_profile_patch: dict[str, Any] | None = None
        self.denial_history: list[dict[str, Any]] = []
        self.self_play_history: list[dict[str, Any]] = []
        self.last_replay_query: dict[str, Any] | None = None
        self.last_replay_export: dict[str, Any] | None = None
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
                authority_scopes=self.authority_scopes,
            )
            self._apply_committed_receipts()
            self._save()
            return self._state_unlocked(extra={"created_plan": self.current_plan.to_dict()})

    def update_authority(self, *, authority_tier: int | None = None, scopes: list[str] | None = None) -> dict[str, Any]:
        with self.lock:
            if authority_tier is not None:
                self.authority_tier = max(0, min(6, int(authority_tier)))
            if scopes is not None:
                cleaned = [scope.strip() for scope in scopes if str(scope).strip()]
                self.authority_scopes = cleaned or ["recommend", "stage"]
            self._save()
            return self._state_unlocked(extra={"authority": {"authority_tier": self.authority_tier, "scopes": self.authority_scopes}})

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
            checksum_before = self.provider.checksum()
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
                original_receipt_id = self._receipt_id_for_rollback(rollback_handle_id)
                undo_reward = None
                if original_receipt_id:
                    undo_reward = self._reward_from_feedback(original_receipt_id, {"undone": True})
                    candidate, original_receipt = self._candidate_and_receipt_for_reward(original_receipt_id)
                    if candidate is not None and original_receipt is not None:
                        self.replay.append_reward(undo_reward, candidate, original_receipt, trace_id=candidate.candidate_id, causal_parent_id=original_receipt.receipt_id)
                self.undo_history.append({
                    "rollback_handle_id": rollback_handle_id,
                    "original_receipt_id": original_receipt_id,
                    "undo_receipt_id": receipt.swift_receipt_id,
                    "swift_status": receipt.output.get("swift_receipt", {}).get("sync_status"),
                    "provider_status": provider_result.receipt.status,
                    "checksum_before": checksum_before,
                    "checksum_after": self.provider.checksum(),
                    "reward_event_id": undo_reward.reward_event_id if undo_reward else None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
            self._save()
            return self._state_unlocked(extra={"undo_receipt": receipt.to_dict()})

    def propose_profile_patch(self, correction: str) -> dict[str, Any]:
        with self.lock:
            call = self._new_call(CodexToolName.PROPOSE_PROFILE_PATCH, {"correction": correction})
            receipt = self._execute(call)
            repair_plan = receipt.output.get("repair_plan") if isinstance(receipt.output, dict) else None
            if isinstance(repair_plan, dict):
                self.pending_profile_patch = {"correction": correction, "repair_plan": repair_plan, "receipt": receipt.to_dict()}
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
                self.profile_patch_history.append({
                    "claim": claim,
                    "correction": correction,
                    "receipt": receipt.to_dict(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                self.pending_profile_patch = None
            self._save()
            return self._state_unlocked(extra={"profile_patch": receipt.to_dict()})

    def explain_denial(self, denied_reason: str) -> dict[str, Any]:
        with self.lock:
            call = self._new_call(CodexToolName.EXPLAIN_SWIFT_DENIAL, {"denied_reason": denied_reason})
            receipt = self._execute(call)
            self.denial_history.append({
                "denied_reason": denied_reason,
                "explanation": receipt.output.get("denial_explanation"),
                "suggested_controls": self._denial_followups(denied_reason),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            self._save()
            return self._state_unlocked(extra={"denial_explanation": receipt.to_dict()})

    def replay_trace(
        self,
        *,
        candidate_id: str | None = None,
        trace_id: str | None = None,
        receipt_id: str | None = None,
        authority_grant_id: str | None = None,
        rollback_handle_id: str | None = None,
        reward_event_id: str | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            payload: dict[str, Any] = {}
            for key, value in {
                "candidate_id": candidate_id,
                "trace_id": trace_id,
                "receipt_id": receipt_id,
                "authority_grant_id": authority_grant_id,
                "rollback_handle_id": rollback_handle_id,
                "reward_event_id": reward_event_id,
                "q": q,
            }.items():
                if value:
                    payload[key] = value
            call = self._new_call(CodexToolName.QUERY_REPLAY_TRACE, payload, correlation_id=trace_id or candidate_id or receipt_id or q)
            receipt = self._execute(call)
            self.last_replay_query = receipt.output
            self._save()
            return self._state_unlocked(extra={"replay": receipt.output})

    def export_replay(
        self,
        *,
        candidate_id: str | None = None,
        trace_id: str | None = None,
        receipt_id: str | None = None,
        authority_grant_id: str | None = None,
        rollback_handle_id: str | None = None,
        reward_event_id: str | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        with self.lock:
            self.replay_trace(
                candidate_id=candidate_id,
                trace_id=trace_id,
                receipt_id=receipt_id,
                authority_grant_id=authority_grant_id,
                rollback_handle_id=rollback_handle_id,
                reward_event_id=reward_event_id,
                q=q,
            )
            query = self.last_replay_query or {"traces": []}
            digest = hashlib.sha1(json.dumps(query.get("query", {}), sort_keys=True).encode()).hexdigest()[:12]
            export_path = self.run_dir / "exports" / f"replay_export_{digest}.jsonl"
            export_path.parent.mkdir(parents=True, exist_ok=True)
            with export_path.open("w", encoding="utf-8") as handle:
                for record in query.get("traces", []):
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
            self.last_replay_export = {
                "path": str(export_path),
                "record_count": len(query.get("traces", [])),
                "query": query.get("query", {}),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save()
            return self._state_unlocked(extra={"replay_export": self.last_replay_export})

    def run_self_play(self, *, episodes: int = 3) -> dict[str, Any]:
        with self.lock:
            grant_id = self._issue_grant(confirmed=True)
            call = self._new_call(
                CodexToolName.RUN_SELF_PLAY_PROBE,
                {"episodes": int(episodes)},
                grant_id=grant_id,
                correlation_id=f"self_play:{len(self.self_play_history) + 1}",
            )
            receipt = self._execute(call)
            metrics = receipt.output.get("metrics", {}) if isinstance(receipt.output, dict) else {}
            self.self_play_history.append({
                "episodes": int(episodes),
                "metrics": metrics,
                "top_failure_modes": receipt.output.get("top_failure_modes", []),
                "release_decision": self._self_play_release_decision(metrics),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            self._save()
            return self._state_unlocked(extra={"self_play": receipt.to_dict()})

    def feedback(self, receipt_id: str, feedback: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            candidate, receipt = self._candidate_and_receipt_for_reward(receipt_id)
            if candidate is None or receipt is None:
                return self._error_state(f"cannot attach feedback: unknown receipt_id {receipt_id}")
            reward = self._reward_from_feedback(receipt_id, feedback)
            self.replay.append_reward(reward, candidate, receipt, trace_id=candidate.candidate_id, causal_parent_id=receipt.receipt_id)
            self.biography = self.runtime.biography_store.update_from_reward(self.biography, reward, source="dogfood_feedback")
            self.feedback_history.append({
                "receipt_id": receipt_id,
                "reward_event_id": reward.reward_event_id,
                "total_reward": reward.total_reward,
                "feedback": dict(feedback),
                "created_at": reward.observed_at.isoformat(),
            })
            self._save()
            return self._state_unlocked(extra={"feedback": {"appended": True, "reward": reward.to_dict()}})

    def reset_fixture(self) -> dict[str, Any]:
        with self.lock:
            seed = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8")))
            self.provider.reset(seed)
            self.current_plan = None
            self.current_goal = ""
            self.applied_swift_receipts.clear()
            self.undo_history.clear()
            self.feedback_history.clear()
            self.profile_patch_history.clear()
            self.pending_profile_patch = None
            self.denial_history.clear()
            self.self_play_history.clear()
            self.last_replay_query = None
            self.last_replay_export = None
            self.replay = ReplayBuffer()
            self.runtime.replay = self.replay
            self.runtime.frontier.clear()
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
                "authority_scopes": self.authority_scopes,
                "last_error": self.last_error,
            },
            "snapshot": snapshot,
            "replay_summary": to_jsonable(summary),
            "training_rows": self.replay.training_table(),
            "undo_history": self.undo_history,
            "feedback_history": self.feedback_history,
            "profile_patch_history": self.profile_patch_history,
            "pending_profile_patch": self.pending_profile_patch,
            "denial_history": self.denial_history,
            "self_play_history": self.self_play_history,
            "last_replay_query": self.last_replay_query,
            "last_replay_export": self.last_replay_export,
            "authority_grants": self._authority_grants(),
            "profile_claims": self._profile_claims(),
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
            scopes=self.authority_scopes,
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

    def _receipt_id_for_rollback(self, rollback_handle_id: str) -> str | None:
        if self.current_plan is None:
            return None
        for receipt in reversed(self.current_plan.receipts):
            swift = receipt.output.get("swift_receipt") if isinstance(receipt.output, dict) else None
            if (
                isinstance(swift, dict)
                and swift.get("rollback_handle_id") == rollback_handle_id
                and swift.get("sync_status") == "materialized"
            ):
                return swift.get("receipt_id") or receipt.swift_receipt_id
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
            "authority_scopes": self.authority_scopes,
            "biography": self.biography.to_dict(),
            "current_plan": self.current_plan.to_dict() if self.current_plan else None,
            "applied_swift_receipts": sorted(self.applied_swift_receipts),
            "undo_history": self.undo_history,
            "feedback_history": self.feedback_history,
            "profile_patch_history": self.profile_patch_history,
            "pending_profile_patch": self.pending_profile_patch,
            "denial_history": self.denial_history,
            "self_play_history": self.self_play_history,
            "last_replay_query": self.last_replay_query,
            "last_replay_export": self.last_replay_export,
            "last_error": self.last_error,
        }
        self.session_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _load_session(self) -> None:
        if not self.session_path.exists():
            return
        data = json.loads(self.session_path.read_text(encoding="utf-8"))
        self.current_goal = str(data.get("current_goal", ""))
        self.authority_tier = int(data.get("authority_tier", 3))
        scopes = data.get("authority_scopes", ["recommend", "stage", "commit_private", "undo"])
        self.authority_scopes = [str(scope) for scope in scopes] if isinstance(scopes, list) else ["recommend", "stage", "commit_private", "undo"]
        if isinstance(data.get("biography"), dict):
            self.biography = UserBiography.from_dict(data["biography"])
        if isinstance(data.get("current_plan"), dict):
            self.current_plan = self._plan_from_dict(data["current_plan"])
            self._restore_frontier(self.current_plan)
            self._restore_kernel_undo_ledger()
        self.applied_swift_receipts = set(str(x) for x in data.get("applied_swift_receipts", []))
        self.undo_history = list(data.get("undo_history", []))
        self.feedback_history = list(data.get("feedback_history", []))
        self.profile_patch_history = list(data.get("profile_patch_history", []))
        self.pending_profile_patch = data.get("pending_profile_patch") if isinstance(data.get("pending_profile_patch"), dict) else None
        self.denial_history = list(data.get("denial_history", []))
        self.self_play_history = list(data.get("self_play_history", []))
        self.last_replay_query = data.get("last_replay_query") if isinstance(data.get("last_replay_query"), dict) else None
        self.last_replay_export = data.get("last_replay_export") if isinstance(data.get("last_replay_export"), dict) else None
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

    def _authority_grants(self) -> list[dict[str, Any]]:
        registry = getattr(self.runtime.kernel, "authority_grants", None)
        if not isinstance(registry, dict):
            registry = getattr(self.runtime.kernel, "_grants", {})
        if not isinstance(registry, dict):
            return []
        return [grant.to_dict() if hasattr(grant, "to_dict") else to_jsonable(grant) for grant in registry.values()]

    def _profile_claims(self) -> list[dict[str, Any]]:
        rows = []
        events = {str(event.get("claim", "")): event for event in self.biography.profile_update_events if isinstance(event, dict)}
        for claim in self.biography.preference_claims:
            if not isinstance(claim, dict):
                continue
            name = str(claim.get("claim", ""))
            event = events.get(name, {})
            rows.append({
                "claim": name,
                "confidence": claim.get("confidence", 0.0),
                "source": claim.get("source") or claim.get("provenance") or event.get("provenance", {}).get("source"),
                "updated_at": claim.get("updated_at") or event.get("provenance", {}).get("created_at"),
                "last_evidence": claim.get("last_evidence") or claim.get("reason") or event.get("reason"),
                "correction": claim.get("correction"),
                "last_update_id": event.get("update_id"),
            })
        return rows

    @staticmethod
    def _denial_followups(denied_reason: str) -> list[dict[str, Any]]:
        reason = denied_reason.lower()
        controls = [{"action": "stage_instead", "label": "Stage instead", "description": "Keep the packet reviewable instead of committing provider state."}]
        if "social" in reason or "people" in reason:
            controls.append({"action": "ask_confirmation", "label": "Ask confirmation", "description": "Require explicit user confirmation before any people-affecting mutation."})
            controls.append({"action": "repair_profile", "label": "Repair profile", "description": "Correct a learned claim if social risk was inferred from stale profile data."})
        if "authority" in reason or "tier" in reason or "scope" in reason:
            controls.append({"action": "narrow_scope", "label": "Narrow scope", "description": "Lower authority and keep only recommend/stage/undo scopes."})
        if "conflict" in reason:
            controls.append({"action": "simulate_alternative", "label": "Simulate alternative", "description": "Return to candidate futures and choose a non-conflicting slot."})
        return controls

    @staticmethod
    def _self_play_release_decision(metrics: dict[str, Any]) -> dict[str, Any]:
        failures = metrics.get("failure_modes", {}) if isinstance(metrics, dict) else {}
        average_reward = float(metrics.get("average_reward", 0.0) or 0.0) if isinstance(metrics, dict) else 0.0
        undo_rate = float(metrics.get("undo_rate", 0.0) or 0.0) if isinstance(metrics, dict) else 0.0
        high_risk = {
            "undo_regret",
            "social_conflict",
            "notification_fatigue",
            "denied_actuation",
        }
        blocking = sorted(label for label, count in failures.items() if label in high_risk and int(count) > 0)
        if average_reward < 0 or undo_rate > 0.1 or blocking:
            return {
                "decision": "hold_autonomy",
                "reason": "Self-play found regret, social, fatigue, denial, or negative-reward risk.",
                "blocking_failure_modes": blocking,
            }
        return {
            "decision": "ship_fixture_gate",
            "reason": "Fixture self-play did not find blocking regret, social, fatigue, or denial risk.",
            "blocking_failure_modes": [],
        }
