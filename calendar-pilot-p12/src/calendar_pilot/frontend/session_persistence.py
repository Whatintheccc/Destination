from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from calendar_pilot.codex import CodexExecutivePlan
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.frontend.launch import LaunchConfig
from calendar_pilot.replay import observation_fingerprint
from calendar_pilot.types import AuthorityGrant, CandidateCalendarAction, RawCalendarObservation, UserBiography, to_jsonable


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionPersistenceController:
    """Persists and restores the frontend session root."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def persist(self) -> None:
        self.session.run_dir.mkdir(parents=True, exist_ok=True)
        state_payload = self.state_payload()
        latest_snapshot = self.session.snapshot()
        session_manifest = self.session_manifest(latest_snapshot=latest_snapshot)
        self.session.store.save(
            state_payload=state_payload,
            latest_snapshot=latest_snapshot,
            session_manifest=session_manifest,
            replay=self.session.replay,
        )
        self.write_launch_manifest_with_health()

    def session_manifest(self, *, latest_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        latest_snapshot = latest_snapshot or self.session.snapshot()
        runtime = latest_snapshot.get("runtime") or self.session.runtime_report()
        return {
            "manifest_version": 2,
            "session_id": self.session.session_id,
            "session_label": self.session.session_label,
            "state_version": self.session.state_version,
            "runtime_mode": runtime.get("runtime_mode"),
            "requested_runtime_mode": runtime.get("requested_runtime_mode"),
            "backends": runtime.get("backends", {}),
            "run_dir": str(self.session.run_dir),
            "state_path": str(self.session.store.state_path),
            "latest_path": str(self.session.store.latest_path),
            "replay_path": str(self.session.store.replay_path),
            "observation_id": self.session.observation.observation_id,
            "observation_fingerprint": observation_fingerprint(self.session.observation),
            "updated_at": _now().isoformat(),
        }

    def write_launch_manifest_with_health(self) -> None:
        manifest = self.session.launch_config.to_dict()
        manifest["health"] = self.session.runtime_report()
        atomic_write_json(self.session.launch_config.manifest_path, manifest)

    def state_payload(self) -> dict[str, Any]:
        return {
            "version": 2,
            "state_version": self.session.state_version,
            "session_id": self.session.session_id,
            "session_label": self.session.session_label,
            "archived_at": self.session.archived_at,
            "runtime_mode": self.session.runtime_mode,
            "authority_tier": self.session.authority_tier,
            "authority_scopes": self.session.authority_scopes,
            "observation": to_jsonable(self.session.observation),
            "biography": self.session.biography.to_dict(),
            "latest_plan": self.session.latest_plan.to_dict() if self.session.latest_plan is not None else None,
            "latest_plan_observation_id": self.session.latest_plan_observation_id,
            "latest_plan_observation_fingerprint": self.session.latest_plan_observation_fingerprint,
            "transcript_events": self.session.transcript_events,
            "feedback_history": self.session.feedback_history,
            "denial_history": self.session.denial_history,
            "profile_patch_history": self.session.profile_patch_history,
            "self_play_history": self.session.self_play_history,
            "authority_history": self.session.authority_history,
            "restore_error": self.session.restore_error,
            "provider_observation_error": self.session.provider_observation_error,
            "launch": self.session.launch_config.to_dict(),
            "kernel": {
                "authority_grants": [grant.to_dict() for grant in self.session.kernel.authority_grants.values()],
                "undo_ledger": self.session.kernel.undo_ledger,
            },
            "updated_at": _now().isoformat(),
        }

    def restore_session_state(self) -> bool:
        try:
            data = self.session.store.load_state()
            if data is None:
                return False
        except (OSError, TypeError, ValueError) as exc:
            self.session.restore_error = f"failed to restore {self.session.store.state_path.name}: {exc}"
            self.session.transcript_events.append({
                "kind": "assistant",
                "title": "Session restore failed",
                "body": self.session.restore_error,
                "created_at": _now().isoformat(),
            })
            return False
        self.session.session_id = str(data.get("session_id") or self.session.session_id)
        self.session.state_version = int(data.get("state_version", self.session.state_version) or 0)
        self.session.session_label = str(data.get("session_label") or "").strip() or None
        self.session.archived_at = str(data.get("archived_at") or "").strip() or None
        restored_runtime_mode = str(data.get("runtime_mode") or self.session.runtime_mode)
        if restored_runtime_mode != self.session.runtime_mode:
            self.session.runtime_mode = restored_runtime_mode
            self.session.launch_config = LaunchConfig.from_env(
                run_dir=self.session.run_dir,
                host=self.session.launch_config.host,
                port=self.session.launch_config.port,
                runtime_mode=self.session.runtime_mode,
            )
            self.session._replace_kernel_for_mode()
        else:
            self.session.runtime_mode = restored_runtime_mode
            self.session.launch_config = LaunchConfig.from_env(
                run_dir=self.session.run_dir,
                host=self.session.launch_config.host,
                port=self.session.launch_config.port,
                runtime_mode=self.session.runtime_mode,
            )
        self.session.restore_error = data.get("restore_error")
        self.session.provider_observation_error = data.get("provider_observation_error")
        self.session.authority_tier = int(data.get("authority_tier", self.session.authority_tier))
        scopes = data.get("authority_scopes")
        if isinstance(scopes, list):
            self.session.authority_scopes = [str(scope) for scope in scopes if str(scope).strip()]
        observation = data.get("observation")
        provider_id = str(getattr(self.session.provider, "provider_id", ""))
        restores_fixture_observation = self.session.provider is None or provider_id == "deterministic_fixture_provider"
        if isinstance(observation, dict) and restores_fixture_observation:
            self.session.observation = RawCalendarObservation.from_dict(observation)
        biography = data.get("biography")
        if isinstance(biography, dict):
            self.session.biography = UserBiography.from_dict(biography)
        plan = data.get("latest_plan")
        self.session.latest_plan = CodexExecutivePlan.from_dict(plan) if isinstance(plan, dict) else None
        self.session.latest_plan_observation_id = str(data.get("latest_plan_observation_id") or "") or None
        self.session.latest_plan_observation_fingerprint = str(data.get("latest_plan_observation_fingerprint") or "") or None
        self.session.transcript_events = list(data.get("transcript_events", []))
        self.session.feedback_history = list(data.get("feedback_history", []))
        self.session.denial_history = list(data.get("denial_history", []))
        self.session.profile_patch_history = list(data.get("profile_patch_history", []))
        self.session.self_play_history = list(data.get("self_play_history", []))
        self.session.authority_history = list(data.get("authority_history", []))
        kernel = data.get("kernel", {})
        grants = kernel.get("authority_grants", []) if isinstance(kernel, dict) else []
        self.session.kernel.authority_grants = {}
        self.session.kernel.undo_ledger = {}
        undo_ledger = kernel.get("undo_ledger", {}) if isinstance(kernel, dict) else {}
        active_undo_ledger = {str(k): str(v) for k, v in undo_ledger.items()} if isinstance(undo_ledger, dict) else {}
        if self.session.runtime_mode in {"auto", "swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}:
            restore_grant = getattr(self.session.kernel, "restore_authority_grant", None)
            if callable(restore_grant):
                for grant in grants:
                    if isinstance(grant, dict) and grant.get("grant_id"):
                        restore_grant(AuthorityGrant.from_dict(grant))
            restore_undo = getattr(self.session.kernel, "restore_undo_handle", None)
            generated_ids = self.generated_event_ids_by_rollback()
            if callable(restore_undo):
                for rollback_handle_id, candidate_id in active_undo_ledger.items():
                    restore_undo(
                        rollback_handle_id,
                        candidate_id,
                        self.session.observation,
                        generated_event_ids=generated_ids.get(rollback_handle_id, []),
                    )
        else:
            for grant in grants:
                if isinstance(grant, dict) and grant.get("grant_id"):
                    restored = AuthorityGrant.from_dict(grant)
                    self.session.kernel.authority_grants[restored.grant_id] = restored
            self.session.kernel.undo_ledger = active_undo_ledger
        if not self.session.transcript_events:
            self.session.transcript_events.append({
                "kind": "assistant",
                "title": "Session restored",
                "body": "CalendarPilot restored this dogfood run from disk.",
                "created_at": _now().isoformat(),
            })
        return True

    def generated_event_ids_by_rollback(self) -> dict[str, list[str]]:
        generated: dict[str, list[str]] = {}
        for record in self.session.replay.records:
            receipt = record.payload.get("receipt", {})
            if isinstance(receipt, dict) and receipt.get("rollback_handle_id"):
                generated[str(receipt["rollback_handle_id"])] = [str(item) for item in receipt.get("generated_event_ids", [])]
        if self.session.latest_plan is not None:
            for tool_receipt in self.session.latest_plan.receipts:
                output = tool_receipt.output if isinstance(tool_receipt.output, dict) else {}
                swift_receipt = output.get("swift_receipt")
                if isinstance(swift_receipt, dict) and swift_receipt.get("rollback_handle_id"):
                    generated[str(swift_receipt["rollback_handle_id"])] = [str(item) for item in swift_receipt.get("generated_event_ids", [])]
        return generated

    def hydrate_runtime_frontier(self) -> None:
        self.session.runtime.frontier.clear()
        self.prune_latest_plan_for_active_observation()
        for record in self.session.replay.records:
            candidate = record.payload.get("candidate")
            if isinstance(candidate, dict) and candidate.get("candidate_id"):
                if not self.candidate_restore_allowed(record.payload.get("observation_id"), record.payload.get("observation_fingerprint")):
                    continue
                restored = CandidateCalendarAction.from_dict(candidate)
                self.session.runtime.frontier[restored.candidate_id] = restored
        if self.session.latest_plan is None:
            return
        if not self.candidate_restore_allowed(self.session.latest_plan_observation_id, self.session.latest_plan_observation_fingerprint):
            return
        for receipt in self.session.latest_plan.receipts:
            output = receipt.output if isinstance(receipt.output, dict) else {}
            for candidate in output.get("candidates", []) if isinstance(output.get("candidates"), list) else []:
                if isinstance(candidate, dict) and candidate.get("candidate_id"):
                    restored = CandidateCalendarAction.from_dict(candidate)
                    self.session.runtime.frontier[restored.candidate_id] = restored
            candidate = output.get("candidate")
            if isinstance(candidate, dict) and candidate.get("candidate_id"):
                restored = CandidateCalendarAction.from_dict(candidate)
                self.session.runtime.frontier[restored.candidate_id] = restored

    def candidate_restore_allowed(self, source_observation_id: Any, source_fingerprint: Any) -> bool:
        if not self.session._real_provider_active():
            return True
        if source_observation_id != self.session.observation.observation_id:
            return False
        return bool(source_fingerprint and source_fingerprint == observation_fingerprint(self.session.observation))

    def prune_latest_plan_for_active_observation(self) -> None:
        if self.session.latest_plan is None or self.candidate_restore_allowed(self.session.latest_plan_observation_id, self.session.latest_plan_observation_fingerprint):
            return
        before = len(self.session.latest_plan.receipts)
        self.session.latest_plan.receipts = [
            receipt for receipt in self.session.latest_plan.receipts
            if self.session._receipt_is_realized_action(receipt)
        ]
        if len(self.session.latest_plan.receipts) == before:
            return
        self.session.transcript_events.append({
            "kind": "assistant",
            "title": "Plan needs refresh",
            "body": "Candidate controls were cleared because the active calendar observation changed. Existing committed receipts remain available for undo and replay.",
            "created_at": _now().isoformat(),
            "stale_observation_id": self.session.latest_plan_observation_id,
            "active_observation_id": self.session.observation.observation_id,
        })
