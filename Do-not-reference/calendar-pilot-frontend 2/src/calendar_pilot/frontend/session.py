from __future__ import annotations

import atexit
import hashlib
import json
import os
import subprocess
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from calendar_pilot.codex import CodexExecutivePlan, CodexToolPlanner, CodexToolRuntime, LiveCodexToolPlanner
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, LiveDiffusionGemmaPolicy, SelfPlayRunner
from calendar_pilot.providers import AppleEventKitProvider, DeterministicCalendarProvider
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
from calendar_pilot.swift_bridge import SwiftKernelIPCClient, SwiftKernelStub
from calendar_pilot.swift_bridge.protocol import CalendarKernelProtocol
from calendar_pilot.types import (
    AuthorityGrant,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    RawCalendarObservation,
    RewardEvent,
    UserBiography,
    to_jsonable,
)
from calendar_pilot.frontend.surface import build_frontend_snapshot
from calendar_pilot.frontend.runtime import KNOWN_MODES, RuntimeBackends, runtime_mode_from_env, runtime_report


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
        self.observation_path = Path(self.observation_path)
        self.profile_path = Path(self.profile_path)
        self.run_dir = Path(self.run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._load_primitives()
        self.kernel = self._new_kernel_for_mode()
        self.policy = self._new_policy_for_mode()
        self.provider = self._new_provider_for_mode()
        self._hydrate_provider_observation_if_available()
        self.replay = ReplayBuffer.load_jsonl(self.run_dir / "replay.jsonl")
        self._rebuild_runtime()
        atexit.register(self.close)
        if not self._restore_session_state():
            self.transcript_events.append({
                "kind": "assistant",
                "title": "CalendarPilot is ready",
                "body": "Tell me what you want checked or changed. I will keep actions, undo, feedback, and replay evidence visible.",
                "created_at": _now().isoformat(),
            })
            self.issue_authority_grant(confirmed=True, reason="dogfood_session_boot")
            self.persist()
        self._hydrate_runtime_frontier()

    def _load_primitives(self) -> None:
        self.observation = RawCalendarObservation.from_dict(json.loads(self.observation_path.read_text(encoding="utf-8")))
        self.biography = UserBiography.from_dict(json.loads(self.profile_path.read_text(encoding="utf-8")))

    def _new_kernel_for_mode(self) -> CalendarKernelProtocol:
        requested_kernel = os.environ.get("CALENDAR_PILOT_KERNEL_BACKEND", "").strip().lower().replace("-", "_")
        if requested_kernel in {"stub", "swift_stub", "python_stub"}:
            return SwiftKernelStub()
        if requested_kernel in {"swift_ipc", "ipc"} or self.runtime_mode in {"swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}:
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
        if self.runtime_mode in {"live_codex", "production"}:
            return LiveCodexToolPlanner(runtime=self.runtime)
        return CodexToolPlanner(runtime=self.runtime)

    def _new_policy_for_mode(self) -> DiffusionGemmaPolicy | LiveDiffusionGemmaPolicy:
        if self.runtime_mode in {"live_diffusiongemma", "production"}:
            return LiveDiffusionGemmaPolicy()
        return DiffusionGemmaPolicy()

    def _new_provider_for_mode(self) -> Any:
        requested_provider = os.environ.get("CALENDAR_PILOT_PROVIDER_BACKEND", "deterministic").strip().lower().replace("-", "_")
        if requested_provider in {"stub", "local_stub", "none"}:
            return None
        if requested_provider in {"apple", "apple_eventkit", "ios_calendar", "macos_calendar", "eventkit"}:
            return AppleEventKitProvider(state_path=self.run_dir / "apple_eventkit_provider.json")
        return DeterministicCalendarProvider(state_path=self.run_dir / "provider_state.json", seed_observation=self.observation)

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
        plan = self.planner.plan_goal(goal, self.observation, self.biography, authority_tier=self.authority_tier, commit=commit)
        self.latest_plan = plan
        self.latest_plan_observation_id = self.observation.observation_id
        self.latest_plan_observation_fingerprint = observation_fingerprint(self.observation)
        self.transcript_events.append({
            "kind": "assistant_plan",
            "title": "I found a plan",
            "body": "I inspected the week, generated candidate futures, compared reward/regret, and prepared the leading action for Swift.",
            "plan_id": plan.plan_id,
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

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
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        self.transcript_events.append({
            "kind": "assistant_receipt",
            "title": self._title_for_receipt(action, receipt.denied_reason),
            "body": receipt.denied_reason or f"Swift returned {receipt.status.value} for {candidate.intent}.",
            "candidate_id": candidate_id,
            "receipt": receipt.to_dict(),
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
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        self.transcript_events.append({
            "kind": "assistant_receipt",
            "title": "Undo requested",
            "body": receipt.denied_reason or "Swift used the rollback ledger and marked the action reverted.",
            "receipt": receipt.to_dict(),
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
            "created_at": _now().isoformat(),
        })
        self.persist()
        return self.snapshot()

    def propose_profile_patch(self, correction: str) -> dict[str, Any]:
        grant_id = self.latest_grant_id(confirmed=True)
        receipt = self.runtime.execute(self._call(CodexToolName.PROPOSE_PROFILE_PATCH, {"correction": correction}, grant_id=grant_id, reason="Draft a profile repair from user correction."), self.observation, self.biography)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        self.profile_patch_history.append({"kind": "proposed", "receipt": receipt.to_dict(), "created_at": _now().isoformat()})
        self.transcript_events.append({"kind": "assistant_receipt", "title": "Profile repair drafted", "body": "I drafted a profile patch. It will not apply until confirmed.", "receipt": receipt.to_dict(), "created_at": _now().isoformat()})
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
        self.profile_patch_history.append({"kind": "applied" if confirmed else "needs_confirmation", "receipt": receipt.to_dict(), "created_at": _now().isoformat()})
        self.transcript_events.append({"kind": "assistant_receipt", "title": "Profile repair applied" if confirmed else "Profile repair needs confirmation", "body": receipt.denied_reason or "Profile claims were updated with correction provenance.", "receipt": receipt.to_dict(), "created_at": _now().isoformat()})
        self.persist()
        return self.snapshot()

    def explain_denial(self, denied_reason: str) -> dict[str, Any]:
        receipt = self.runtime.execute(self._call(CodexToolName.EXPLAIN_SWIFT_DENIAL, {"denied_reason": denied_reason}, reason="Explain a Swift denial and suggest next controls."), self.observation, self.biography)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        self.denial_history.append({"denied_reason": denied_reason, "explanation": receipt.output, "created_at": _now().isoformat()})
        self.transcript_events.append({"kind": "assistant_receipt", "title": "Why Swift denied it", "body": str(receipt.output.get("denial_explanation", denied_reason)), "receipt": receipt.to_dict(), "created_at": _now().isoformat()})
        self.persist()
        return self.snapshot()

    def run_self_play(self, episodes: int = 3) -> dict[str, Any]:
        episodes = int(episodes)
        if episodes <= 0:
            raise ValueError("episodes must be positive")
        grant_id = self.latest_grant_id(confirmed=True)
        receipt = self.runtime.execute(self._call(CodexToolName.RUN_SELF_PLAY_PROBE, {"episodes": episodes}, grant_id=grant_id, reason="Probe the current policy against self-play adversaries."), self.observation, self.biography)
        if self.latest_plan is not None:
            self.latest_plan.receipts.append(receipt)
        metrics = receipt.output.get("metrics", {}) if isinstance(receipt.output, dict) else {}
        top_failures = receipt.output.get("top_failure_modes", []) if isinstance(receipt.output, dict) else []
        release_decision = "hold_autonomy" if top_failures else "ship_fixture_gate"
        self.self_play_history.append({"episodes": episodes, "metrics": metrics, "top_failure_modes": top_failures, "release_decision": release_decision, "created_at": _now().isoformat()})
        self.transcript_events.append({"kind": "assistant_receipt", "title": "Self-play release gate", "body": f"Decision: {release_decision}.", "receipt": receipt.to_dict(), "created_at": _now().isoformat()})
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
        return {
            "session_id": self.session_id,
            "runtime": self.runtime_report(),
            "summary": to_jsonable(self.replay.summarize()),
            "records": [record.envelope() for record in self.replay.records],
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
        blockers[:] = [
            blocker for blocker in blockers
            if blocker not in {"required credential missing: provider_oauth", "required credential wrong auth method: provider_oauth"}
        ]
        if configured:
            if self._provider_observation_loaded():
                blockers[:] = [blocker for blocker in blockers if blocker != "live provider/production mode is using sample fixture data"]
            return
        if report.get("runtime_mode") not in {"live_provider", "production"}:
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
        runtime = self.runtime_report()
        snapshot["session"] = {
            "session_id": self.session_id,
            "runtime_mode": runtime["runtime_mode"],
            "requested_runtime_mode": runtime["requested_runtime_mode"],
            "authority_tier": self.authority_tier,
            "authority_scopes": self.authority_scopes,
            "run_dir": str(self.run_dir),
            "restore_error": self.restore_error,
            "provider_observation_error": self.provider_observation_error,
        }
        snapshot["runtime"] = runtime
        snapshot["summary"]["runtime_mode"] = runtime["runtime_mode"]
        snapshot["summary"]["requested_runtime_mode"] = runtime["requested_runtime_mode"]
        snapshot["summary"]["runtime_backends"] = runtime["backends"]
        snapshot["summary"]["runtime_live_blockers"] = runtime["live_blockers"]
        snapshot["chat"]["messages"] = self._chat_messages(snapshot)
        snapshot["chat"]["runtime"] = {
            "mode": runtime["runtime_mode"],
            "requested_mode": runtime["requested_runtime_mode"],
            "label": runtime["mode_label"],
            "backends": runtime["backends"],
            "live_blockers": runtime["live_blockers"],
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
            ],
        }
        snapshot["inspector"]["profile"]["patch_history"] = self.profile_patch_history[-10:]
        snapshot["inspector"]["self_play"]["history"] = self.self_play_history[-5:]
        snapshot["inspector"]["replay"]["records"] = [record.envelope() for record in self.replay.records[-40:]]
        snapshot["inspector"]["provider"] = self._provider_inspector()
        snapshot["inspector"]["feedback"] = self.feedback_history[-20:]
        snapshot["inspector"]["denials"] = self.denial_history[-20:]
        snapshot["sidebar"]["sessions"] = [{"session_id": self.session_id, "label": "Current fixture run", "active": True}]
        snapshot["sidebar"]["recent_runs"] = [
            {"label": event.get("body") or event.get("title", "run"), "created_at": event.get("created_at")} for event in self.transcript_events if event.get("kind") == "user"
        ][-8:]
        return snapshot

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
        (self.run_dir / "session_state.json").write_text(json.dumps(self._state_payload(), indent=2, sort_keys=True), encoding="utf-8")
        (self.run_dir / "latest_session.json").write_text(json.dumps(self.snapshot(), indent=2, sort_keys=True), encoding="utf-8")
        self.replay.save_jsonl(self.run_dir / "replay.jsonl")

    def _state_payload(self) -> dict[str, Any]:
        return {
            "version": 1,
            "session_id": self.session_id,
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
            "kernel": {
                "authority_grants": [grant.to_dict() for grant in self.kernel.authority_grants.values()],
                "undo_ledger": self.kernel.undo_ledger,
            },
            "updated_at": _now().isoformat(),
        }

    def _restore_session_state(self) -> bool:
        path = self.run_dir / "session_state.json"
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError) as exc:
            self.restore_error = f"failed to restore {path.name}: {exc}"
            self.transcript_events.append({
                "kind": "assistant",
                "title": "Session restore failed",
                "body": self.restore_error,
                "created_at": _now().isoformat(),
            })
            return False
        self.session_id = str(data.get("session_id") or self.session_id)
        restored_runtime_mode = str(data.get("runtime_mode") or self.runtime_mode)
        if restored_runtime_mode != self.runtime_mode:
            self.runtime_mode = restored_runtime_mode
            self._replace_kernel_for_mode()
        else:
            self.runtime_mode = restored_runtime_mode
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
        if self.runtime_mode in {"swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}:
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
                "created_at": event.get("created_at"),
                "cards": [],
            }
            if event.get("kind") == "assistant_plan":
                message["cards"] = snapshot.get("chat", {}).get("candidate_cards", [])[:3]
            if event.get("kind") == "assistant_receipt" and event.get("receipt"):
                message["cards"] = [{"type": "receipt", "receipt": event["receipt"]}]
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
