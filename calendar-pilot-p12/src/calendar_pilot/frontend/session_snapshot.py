from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from calendar_pilot.environment.invariants import check_replay
from calendar_pilot.environment.taxonomy import taxonomy_health
from calendar_pilot.environment.trace import TRACE_BUS
from calendar_pilot.frontend.surface import build_frontend_snapshot
from calendar_pilot.types import CodexToolName


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionSnapshotBuilder:
    """Builds browser-visible session projections from the session root."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def snapshot(self) -> dict[str, Any]:
        plan = self.session.latest_plan
        if plan is None:
            from calendar_pilot.codex.planner import CodexExecutivePlan
            plan = CodexExecutivePlan(plan_id="plan_empty", goal="")
        snapshot = build_frontend_snapshot(plan, self.session.observation, self.session.biography, self.session.replay).to_dict()
        snapshot["state_version"] = self.session.state_version
        runtime = self.session.runtime_report()
        snapshot["session"] = {
            "session_id": self.session.session_id,
            "label": self.session.session_label,
            "archived_at": self.session.archived_at,
            "runtime_mode": runtime["runtime_mode"],
            "requested_runtime_mode": runtime["requested_runtime_mode"],
            "authority_tier": self.session.authority_tier,
            "authority_scopes": self.session.authority_scopes,
            "run_dir": str(self.session.run_dir),
            "restore_error": self.session.restore_error,
            "provider_observation_error": self.session.provider_observation_error,
            "launch": self.session.launch_config.to_dict(),
            "state_version": self.session.state_version,
        }
        snapshot["runtime"] = runtime
        snapshot["summary"]["runtime_mode"] = runtime["runtime_mode"]
        snapshot["summary"]["requested_runtime_mode"] = runtime["requested_runtime_mode"]
        snapshot["summary"]["runtime_backends"] = runtime["backends"]
        snapshot["summary"]["runtime_live_blockers"] = runtime["live_blockers"]
        snapshot["summary"]["runtime_setup_notes"] = runtime.get("setup_notes", [])
        snapshot["chat"]["messages"] = self.chat_messages(snapshot)
        snapshot["summary"]["latest_turn"] = self.latest_turn_summary()
        snapshot["chat"]["latest_message_metadata"] = snapshot["summary"]["latest_turn"].get("metadata")
        snapshot["chat"]["runtime"] = {
            "mode": runtime["runtime_mode"],
            "requested_mode": runtime["requested_runtime_mode"],
            "label": runtime["mode_label"],
            "backends": runtime["backends"],
            "live_blockers": runtime["live_blockers"],
            "setup_notes": runtime.get("setup_notes", []),
        }
        snapshot["inspector"]["authority"]["history"] = self.session.authority_history[-10:]
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
        snapshot["inspector"]["profile"]["patch_history"] = self.session.profile_patch_history[-10:]
        snapshot["inspector"]["self_play"]["history"] = self.session.self_play_history[-5:]
        snapshot["inspector"]["replay"]["records"] = [record.envelope() for record in self.session.replay.records[-40:]]
        snapshot["learning"] = self.learning_snapshot(snapshot)
        snapshot["correction"] = self.correction_snapshot()
        snapshot["pipeline"] = {"turns": self.pipeline_turns()}
        snapshot["invariants"] = {"violations": [violation.to_dict() for violation in check_replay([record.envelope() for record in self.session.replay.records])]}
        snapshot["inspector"]["provider"] = self.provider_inspector()
        snapshot["inspector"]["feedback"] = self.session.feedback_history[-20:]
        snapshot["inspector"]["denials"] = self.session.denial_history[-20:]
        snapshot["sidebar"]["sessions"] = [{"session_id": self.session.session_id, "label": "Current fixture run", "active": True}]
        snapshot["sidebar"]["recent_runs"] = [
            {"label": event.get("body") or event.get("title", "run"), "created_at": event.get("created_at")}
            for event in self.session.transcript_events
            if event.get("kind") == "user"
        ][-8:]
        return snapshot

    def correction_snapshot(self) -> dict[str, Any] | None:
        applications = [
            row for row in self.session.replay.records
            if row.record_type == "candidate_correction_application"
        ]
        if not applications:
            return None
        row = applications[-1].payload
        return {
            "command_id": row.get("command_id"),
            "citation_ids": row.get("citation_ids", []),
            "old_belief_active": row.get("old_belief_active"),
            "new_plan_uses_correction": row.get("new_plan_uses_correction"),
            "before_authority_digest": row.get("before_authority_digest"),
            "after_authority_digest": row.get("after_authority_digest"),
            "replacement_minutes": row.get("replacement_minutes"),
            "actual_minutes": row.get("actual_minutes"),
        }

    def learning_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        candidate_cards = snapshot.get("chat", {}).get("candidate_cards", [])
        rejection_counts: dict[str, int] = {}
        for record in self.session.replay.records:
            if record.record_type != "model_generation_rejection":
                continue
            reason = str(record.payload.get("reason", "unknown"))
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
        tuning: dict[str, Any] = {}
        if self.session.latest_plan is not None:
            for receipt in reversed(self.session.latest_plan.receipts):
                if getattr(receipt, "tool_name", None) != CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                    continue
                output = receipt.output if isinstance(receipt.output, dict) else {}
                policy_metadata = output.get("policy_metadata") if isinstance(output.get("policy_metadata"), dict) else {}
                tuning = policy_metadata.get("policy_tuning", {}) if isinstance(policy_metadata, dict) else {}
                break
        decisions = [record for record in self.session.replay.records if record.record_type == "learning_decision"]
        latest_decision = decisions[-1] if decisions else None
        exposures = [
            record for record in self.session.replay.records
            if record.record_type == "learning_exposure"
            and latest_decision is not None
            and record.payload.get("decision_id") == latest_decision.record_id
        ]
        latest_exposure = exposures[-1] if exposures else None
        outcomes = [
            record for record in self.session.replay.records
            if record.record_type == "learning_outcome"
            and latest_exposure is not None
            and record.payload.get("exposure_id") == latest_exposure.record_id
        ]
        terminal_candidate_ids = {str(record.payload.get("candidate_id")) for record in outcomes}
        rendered_candidate_ids = list(latest_exposure.payload.get("rendered_candidate_ids", [])) if latest_exposure else []
        explicit_outcomes = [record for record in self.session.replay.records if record.record_type == "learning_outcome" and record.payload.get("outcome") in {"accepted", "dismissed", "corrected"}]
        legacy_feedback = [record for record in self.session.replay.records if record.record_type == "human_feedback_event"]
        return {
            "taxonomy_health": taxonomy_health([card for card in candidate_cards if isinstance(card, dict)]),
            "frontier_rejections": {"count": sum(rejection_counts.values()), "reasons": rejection_counts},
            "reward_stream": [record.payload.get("reward", {}) for record in self.session.replay.records if record.record_type == "reward"][-20:],
            "tuning": tuning,
            "evidence": {
                "latest_decision": latest_decision.payload if latest_decision else None,
                "latest_exposure": latest_exposure.payload if latest_exposure else None,
                "latest_outcomes": [record.payload for record in outcomes],
                "pending_candidate_ids": [candidate_id for candidate_id in rendered_candidate_ids if candidate_id not in terminal_candidate_ids],
                "program_a": {
                    "matched_examples": len(decisions),
                    "explicit_feedback": len(explicit_outcomes) + len(legacy_feedback),
                    "promotion_eligible": len(decisions) >= 20 and len(explicit_outcomes) + len(legacy_feedback) >= 10,
                },
                "formal_epoch_bound": False,
                "promotion_use": "search_only_until_pre_search_epoch_freezes"
            },
        }

    def pipeline_turns(self) -> list[dict[str, Any]]:
        events = TRACE_BUS.events(self.session.session_id)
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

    def latest_turn_summary(self) -> dict[str, Any]:
        for event in reversed(self.session.transcript_events):
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

    def provider_inspector(self) -> dict[str, Any]:
        provider_snapshot = getattr(self.session.provider, "snapshot", None)
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

    def chat_messages(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for idx, event in enumerate(self.session.transcript_events):
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
            elif event.get("kind") == "assistant_observation":
                message["cards"] = [dict(card) for card in event.get("cards", []) if isinstance(card, dict)]
            if event.get("kind") == "assistant_receipt" and event.get("receipt"):
                message["cards"] = [{"type": "receipt", "receipt": event["receipt"]}]
            if event.get("kind", "").startswith("assistant") and event.get("conversation_receipts"):
                message["cards"].extend([
                    {"type": "receipt", "receipt": receipt}
                    for receipt in event.get("conversation_receipts", [])
                    if isinstance(receipt, dict)
                ])
            messages.append(message)
        if self.session.latest_plan is None:
            return messages
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
