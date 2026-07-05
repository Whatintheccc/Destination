from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from calendar_pilot.frontend.runtime import LIVE_CODEX_MODES
from calendar_pilot.types import CodexToolCall, CodexToolName, UserBiography


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_conversation_message(message: str) -> str:
    return " ".join(str(message or "").lower().replace("-", " ").split())


def conversation_message_requests_undo(normalized: str) -> bool:
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


def conversation_message_requests_profile_apply(normalized: str) -> bool:
    return "profile" in normalized and any(term in normalized for term in [
        "apply patch",
        "apply profile",
        "confirm patch",
        "confirm profile",
        "save patch",
        "save profile",
    ])


def conversation_message_has_calendar_action(normalized: str) -> bool:
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


def profile_patch_payload_from_receipt(receipt: Any) -> dict[str, Any] | None:
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


def local_tool_response_body(receipts: list[dict[str, Any]]) -> str:
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


def conversation_tool_metadata(receipts: list[dict[str, Any]]) -> dict[str, Any]:
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

    compact_receipts = [compact(receipt) for receipt in receipts]
    return {
        "tool_sequence": [row["tool_name"] for row in compact_receipts],
        "tool_call_count": len(compact_receipts),
        "conversation_tool_receipt_count": len(compact_receipts),
        "conversation_tool_receipts": compact_receipts,
    }


class FrontendConversationTools:
    """Session-owned conversation seam for fixture and live Codex turns."""

    def __init__(self, session: Any) -> None:
        self.session = session

    def live_response(self, goal: str, intent: str) -> Any | None:
        if self.session.runtime_mode not in LIVE_CODEX_MODES:
            return None
        chat_response = getattr(self.session.planner, "chat_response", None)
        if not callable(chat_response):
            return None
        return chat_response(
            goal,
            self.session.observation,
            self.session.biography,
            runtime_report=self.session.runtime_report(),
            intent=intent,
        )

    def assistant_ready_message(self) -> dict[str, Any]:
        report = self.session.runtime_report()
        backends = report.get("backends", {})
        blockers = [str(item) for item in report.get("live_blockers", [])] if isinstance(report.get("live_blockers"), list) else []
        setup_notes = [str(item) for item in report.get("setup_notes", [])] if isinstance(report.get("setup_notes"), list) else []
        if blockers:
            title = "Assistant needs setup"
            body = (
                f"{report.get('mode_label', self.session.runtime_mode)} is selected, but the assistant is not fully live yet. "
                f"Active backends: Codex={backends.get('codex')}, DiffusionGemma={backends.get('diffusiongemma')}, "
                f"Swift={backends.get('kernel')}, provider={backends.get('provider')}. "
                f"Blockers: {'; '.join(blockers)}."
            )
        else:
            title = "CalendarPilot is ready"
            body = (
                f"{report.get('mode_label', self.session.runtime_mode)} is ready. "
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

    def local_tool_response(self, goal: str, intent: str) -> dict[str, Any] | None:
        planned_calls = self.local_tool_calls(goal)
        if not planned_calls:
            return None
        receipts = self.execute_tools(planned_calls, goal)
        metadata = self.session._response_metadata(
            goal=goal,
            intent=intent,
            response_source="local_conversation_tools",
            reason="deterministic composer route to local CalendarPilot tools",
            extra_metadata={
                "conversation_route": "local_evidence_tool",
                **conversation_tool_metadata(receipts),
            },
        )
        return {
            "title": "Assistant handled request",
            "body": local_tool_response_body(receipts),
            "metadata": metadata,
            "receipts": receipts,
        }

    def local_tool_calls(self, goal: str) -> list[dict[str, Any]]:
        normalized = normalize_conversation_message(goal)
        calls: list[dict[str, Any]] = []
        if any(term in normalized for term in ["replay", "trace", "evidence log", "audit log"]):
            calls.append(self.planned_tool(CodexToolName.QUERY_REPLAY_TRACE, {}, "Query replay evidence from the composer.", "local_replay"))
        if any(term in normalized for term in ["authority", "grant", "scope"]):
            calls.append(self.planned_tool(CodexToolName.INSPECT_AUTHORITY_SCOPE, {}, "Inspect Swift authority scope from the composer.", "local_authority"))
        if any(term in normalized for term in ["autonomy", "autonomous"]) and any(term in normalized for term in ["scope", "proposal", "propose", "allow"]):
            calls.append(self.planned_tool(CodexToolName.PROPOSE_AUTONOMY_SCOPE, {"candidate_id": self.latest_candidate_id() or ""}, "Propose a bounded autonomy scope from the composer.", "local_autonomy_scope"))
        if any(term in normalized for term in ["self play", "selfplay", "release gate", "adversary"]):
            calls.append(self.planned_tool(CodexToolName.RUN_SELF_PLAY_PROBE, {"episodes": self.episode_count_from_message(normalized)}, "Run self-play release gate from the composer.", "local_self_play"))
        if any(term in normalized for term in ["profile", "preference", "biography"]):
            if conversation_message_requests_profile_apply(normalized):
                calls.append(self.planned_tool(
                    CodexToolName.APPLY_PROFILE_PATCH,
                    self.latest_profile_patch_payload() or {"claim": "user correction", "correction": "", "confirmed": False},
                    "Apply the confirmed profile repair from the composer.",
                    "local_profile_apply",
                ))
            elif any(term in normalized for term in ["repair", "patch", "correct", "correction", "change", "prefer", "don't", "do not"]):
                calls.append(self.planned_tool(CodexToolName.PROPOSE_PROFILE_PATCH, {"correction": goal}, "Draft a profile repair from the composer.", "local_profile_patch"))
            else:
                calls.append(self.planned_tool(CodexToolName.INSPECT_PROFILE_CLAIMS, {}, "Inspect profile claims from the composer.", "local_profile_inspect"))
        if any(term in normalized for term in ["denial", "denied", "why swift", "swift denied"]):
            latest_denial = self.latest_actual_denial_reason() or goal
            calls.append(self.planned_tool(CodexToolName.EXPLAIN_SWIFT_DENIAL, {"denied_reason": latest_denial}, "Explain the latest Swift denial from the composer.", "local_denial"))
        if conversation_message_requests_undo(normalized):
            calls.append(self.planned_tool(CodexToolName.REQUEST_UNDO, {"rollback_handle_id": self.latest_rollback_handle_id() or ""}, "Request Swift undo from the composer.", "local_undo"))
        return calls[:4]

    def planned_tool(self, tool_name: CodexToolName, payload: dict[str, Any], reason: str, correlation_id: str) -> dict[str, Any]:
        return {
            "tool_name": tool_name,
            "input": payload,
            "requested_authority_tier": self.session.authority_tier,
            "user_visible_reason": reason,
            "correlation_id": correlation_id,
        }

    @staticmethod
    def episode_count_from_message(normalized: str) -> int:
        for token in normalized.split():
            try:
                value = int(token)
            except ValueError:
                continue
            return max(1, min(3, value))
        return 1

    def latest_rollback_handle_id(self) -> str | None:
        if getattr(self.session.kernel, "undo_ledger", None):
            return next(reversed(self.session.kernel.undo_ledger))
        if self.session.latest_plan is None:
            return None
        for receipt in reversed(self.session.latest_plan.receipts):
            output = receipt.output if isinstance(receipt.output, dict) else {}
            swift = output.get("swift_receipt")
            if isinstance(swift, dict) and swift.get("rollback_handle_id"):
                return str(swift["rollback_handle_id"])
        return None

    def latest_candidate_id(self) -> str | None:
        if self.session.latest_plan is not None:
            for receipt in reversed(self.session.latest_plan.receipts):
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
        if self.session.runtime.frontier:
            return next(iter(self.session.runtime.frontier))
        return None

    def latest_profile_patch_payload(self) -> dict[str, Any] | None:
        for entry in reversed(self.session.profile_patch_history):
            if entry.get("kind") != "proposed":
                continue
            payload = profile_patch_payload_from_receipt(entry.get("receipt", {}))
            if payload is not None:
                return payload
        return None

    def execute_tools(self, planned_calls: list[Any], user_message: str) -> list[dict[str, Any]]:
        receipts: list[dict[str, Any]] = []
        normalized_message = normalize_conversation_message(user_message)
        for idx, planned in enumerate(planned_calls):
            tool_name = planned.get("tool_name") if isinstance(planned, dict) else getattr(planned, "tool_name", None)
            if isinstance(tool_name, str):
                try:
                    tool_name = CodexToolName(tool_name)
                except ValueError:
                    continue
            if not isinstance(tool_name, CodexToolName):
                continue
            if tool_name == CodexToolName.REQUEST_UNDO and not conversation_message_requests_undo(normalized_message):
                continue
            if tool_name == CodexToolName.APPLY_PROFILE_PATCH and not conversation_message_requests_profile_apply(normalized_message):
                continue
            raw_input = planned.get("input", {}) if isinstance(planned, dict) else getattr(planned, "input", {})
            payload = self.tool_payload(tool_name, dict(raw_input or {}), user_message)
            grant_id = self.tool_grant_id(tool_name)
            requested_tier = planned.get("requested_authority_tier") if isinstance(planned, dict) else getattr(planned, "requested_authority_tier", self.session.authority_tier)
            raw = f"conversation|{tool_name.value}|{idx}|{_now().isoformat()}|{payload}"
            call = CodexToolCall(
                tool_call_id="tool_" + hashlib.sha1(raw.encode()).hexdigest()[:12],
                tool_name=tool_name,
                input=payload,
                requested_authority_tier=max(0, min(6, int(requested_tier or self.session.authority_tier))),
                user_visible_reason=str((planned.get("user_visible_reason") if isinstance(planned, dict) else getattr(planned, "user_visible_reason", "")) or "Live Codex requested this local evidence tool."),
                authority_grant_id=grant_id,
                correlation_id=str((planned.get("correlation_id") if isinstance(planned, dict) else getattr(planned, "correlation_id", "")) or f"conversation_{idx}"),
                created_at=_now(),
            )
            receipt = self.session.runtime.execute(call, self.session.observation, self.session.biography)
            if self.session.latest_plan is not None and self.session._receipt_is_realized_action(receipt):
                self.session.latest_plan.receipts.append(receipt)
            receipt_dict = receipt.to_dict()
            receipts.append(receipt_dict)
            self.record_side_effect(tool_name, receipt_dict, payload)
        return receipts

    def tool_payload(self, tool_name: CodexToolName, payload: dict[str, Any], user_message: str) -> dict[str, Any]:
        if tool_name == CodexToolName.RUN_SELF_PLAY_PROBE:
            try:
                episodes = int(payload.get("episodes", 1))
            except (TypeError, ValueError):
                episodes = 1
            payload["episodes"] = max(1, min(3, episodes))
        if tool_name == CodexToolName.PROPOSE_PROFILE_PATCH and not str(payload.get("correction", "")).strip():
            payload["correction"] = user_message
        if tool_name == CodexToolName.APPLY_PROFILE_PATCH:
            latest = self.latest_profile_patch_payload()
            if latest is None:
                payload["claim"] = str(payload.get("claim") or "user correction")
                payload["correction"] = str(payload.get("correction") or "")
                payload["confirmed"] = False
            else:
                payload["claim"] = str(payload.get("claim") or latest.get("claim") or "user correction")
                payload["correction"] = str(payload.get("correction") or latest.get("correction") or user_message)
                payload["confirmed"] = True
        if tool_name == CodexToolName.PROPOSE_AUTONOMY_SCOPE and not str(payload.get("candidate_id", "")).strip():
            payload["candidate_id"] = self.latest_candidate_id() or ""
        if tool_name == CodexToolName.EXPLAIN_SWIFT_DENIAL:
            requested_reason = str(payload.get("denied_reason", "")).strip()
            latest = self.latest_actual_denial_reason()
            if latest and self.is_generic_denial_reference(requested_reason, user_message):
                payload["denied_reason"] = latest
            elif not requested_reason:
                payload["denied_reason"] = "No denial reason was supplied."
        if tool_name == CodexToolName.REQUEST_UNDO and not str(payload.get("rollback_handle_id", "")).strip():
            payload["rollback_handle_id"] = self.latest_rollback_handle_id() or ""
        return payload

    def latest_actual_denial_reason(self) -> str | None:
        for entry in reversed(self.session.denial_history):
            reason = str(entry.get("denied_reason") or "").strip()
            if not reason or self.is_generic_denial_reference(reason, ""):
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
    def is_generic_denial_reference(value: str, user_message: str) -> bool:
        normalized = normalize_conversation_message(value)
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
        message = normalize_conversation_message(user_message)
        return bool(message and normalized == message and "denial" in message)

    def tool_grant_id(self, tool_name: CodexToolName) -> str | None:
        if tool_name in {CodexToolName.INSPECT_AUTHORITY_SCOPE, CodexToolName.RUN_SELF_PLAY_PROBE}:
            return self.session.latest_grant_id(confirmed=False)
        if tool_name in {CodexToolName.PROPOSE_PROFILE_PATCH, CodexToolName.APPLY_PROFILE_PATCH}:
            return self.session.latest_grant_id(confirmed=True)
        if tool_name == CodexToolName.REQUEST_UNDO:
            return self.session.issue_authority_grant(confirmed=True, scopes=["undo"], reason="user_confirmed_composer_undo").grant_id
        return None

    def record_side_effect(self, tool_name: CodexToolName, receipt: dict[str, Any], payload: dict[str, Any]) -> None:
        output = receipt.get("output", {}) if isinstance(receipt.get("output"), dict) else {}
        if tool_name == CodexToolName.PROPOSE_PROFILE_PATCH:
            kind = "proposed" if profile_patch_payload_from_receipt(receipt) is not None else "proposal_failed"
            self.session.profile_patch_history.append({"kind": kind, "receipt": receipt, "created_at": _now().isoformat()})
        if tool_name == CodexToolName.APPLY_PROFILE_PATCH:
            bio_payload = output.get("biography") if isinstance(output, dict) else None
            if isinstance(bio_payload, dict):
                self.session.biography = UserBiography.from_dict(bio_payload)
            kind = "applied" if str(receipt.get("status")) == "succeeded" and isinstance(bio_payload, dict) else "needs_confirmation"
            self.session.profile_patch_history.append({"kind": kind, "receipt": receipt, "created_at": _now().isoformat()})
        if tool_name == CodexToolName.EXPLAIN_SWIFT_DENIAL:
            self.session.denial_history.append({
                "denied_reason": payload.get("denied_reason", ""),
                "explanation": output,
                "created_at": _now().isoformat(),
            })
        if tool_name == CodexToolName.RUN_SELF_PLAY_PROBE:
            metrics = output.get("metrics", {}) if isinstance(output.get("metrics"), dict) else {}
            top_failures = output.get("top_failure_modes", []) if isinstance(output.get("top_failure_modes"), list) else []
            failed = str(receipt.get("status", "")) != "succeeded" or bool(receipt.get("denied_reason"))
            release_decision = "probe_failed" if failed else ("hold_autonomy" if top_failures else "ship_runtime_gate")
            self.session.self_play_history.append({
                "episodes": int(payload.get("episodes", 1)),
                "metrics": metrics,
                "top_failure_modes": top_failures,
                "release_decision": release_decision,
                "failure_reason": receipt.get("denied_reason") if failed else None,
                "created_at": _now().isoformat(),
            })

    def classify_intent(self, goal: str) -> str:
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
        undo_request = conversation_message_requests_undo(normalized)
        if has_operational_term and conversation_message_has_calendar_action(normalized):
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

    @staticmethod
    def local_chat_body(intent: str) -> str:
        if intent == "metadata_question":
            return "This response was handled by the local app router. No live LLM call ran, so there is no response_id, thread_id, or turn_id for this turn."
        if intent == "smalltalk":
            return "I am here. Ask for a calendar change or inspection when you want me to generate candidate actions."
        return "I only route calendar goals into planning. This turn stayed local and did not contact a live model."

    @staticmethod
    def planner_response_body(metadata: dict[str, Any]) -> str:
        if metadata.get("model_reached"):
            model = metadata.get("model_metadata", {}).get("model") or "live model"
            return f"Live Codex planned this turn with {model}; the trace metadata includes response, thread, and turn ids."
        if metadata.get("planner_backend") == "live_codex_app_server":
            return "Live Codex did not produce an executable model response for this turn. The metadata shows the blocker or failure category."
        return "I used the deterministic fixture planner, generated candidate futures, compared reward/regret, and prepared the leading action for Swift. No live LLM metadata was produced."
