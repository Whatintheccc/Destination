

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import time
from typing import Any

from calendar_pilot.codex.planner import CodexExecutivePlan, CodexToolPlanner
from calendar_pilot.codex.tools import CodexToolRuntime
from calendar_pilot.types import (
    CodexToolCall,
    CodexToolName,
    CodexToolReceipt,
    CodexToolStatus,
    RawCalendarObservation,
    UserBiography,
    authority_scopes_for_tier,
)


ROOT = Path(__file__).resolve().parents[3]
LIVE_CODEX_BACKEND = "live_codex_app_server"
LIVE_CODEX_PROMPT_VERSION = "calendar_pilot_codex_app_server_v1"
LIVE_CODEX_CHAT_PROMPT_VERSION = "calendar_pilot_codex_conversation_v1"
CODEX_AUTH_DOC_URL = "https://developers.openai.com/codex/auth"
SUBSCRIPTION_AUTH_MODES = {"chatgpt", "chatgptAuthTokens", "agentIdentity", "personalAccessToken"}
API_KEY_AUTH_MODES = {"apikey", "apiKey", "api_key"}
ALLOWED_LIVE_TOOLS = {
    CodexToolName.INSPECT_WEEK,
    CodexToolName.GENERATE_CANDIDATE_FRONTIER,
    CodexToolName.COMPARE_CANDIDATES,
    CodexToolName.SIMULATE_ACTION_PROGRAM,
    CodexToolName.STAGE_ACTION_PACKET,
    CodexToolName.REQUEST_COMMIT,
}
CONVERSATION_LIVE_TOOLS = {
    CodexToolName.INSPECT_AUTHORITY_SCOPE,
    CodexToolName.REQUEST_UNDO,
    CodexToolName.QUERY_REPLAY_TRACE,
    CodexToolName.INSPECT_PROFILE_CLAIMS,
    CodexToolName.PROPOSE_PROFILE_PATCH,
    CodexToolName.APPLY_PROFILE_PATCH,
    CodexToolName.RUN_SELF_PLAY_PROBE,
    CodexToolName.PROPOSE_AUTONOMY_SCOPE,
    CodexToolName.EXPLAIN_SWIFT_DENIAL,
}


class LiveCodexError(RuntimeError):
    category = "live_codex_error"


class LiveCodexCredentialError(LiveCodexError):
    category = "missing_or_invalid_credential"


class LiveCodexNetworkError(LiveCodexError):
    category = "network_failure"


class LiveCodexSchemaError(LiveCodexError):
    category = "model_tool_schema_failure"


class LiveCodexSafetyRefusal(LiveCodexError):
    category = "safety_refusal"


class LiveCodexRuntimeError(LiveCodexError):
    category = "codex_app_server_failure"


@dataclass(frozen=True)
class ModelPlannedCall:
    tool_name: CodexToolName
    input: dict[str, Any]
    requested_authority_tier: int
    user_visible_reason: str
    correlation_id: str


@dataclass(frozen=True)
class LiveCodexPlanResult:
    calls: list[ModelPlannedCall]
    recommended_next_action: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LiveCodexChatResult:
    answer: str
    route: str
    metadata: dict[str, Any]
    tool_calls: list[ModelPlannedCall] = field(default_factory=list)


class CodexAppServerClient:
    """Codex app-server client backed by ChatGPT subscription auth.

    This intentionally uses Codex auth (`chatgpt` / `CODEX_ACCESS_TOKEN`) rather
    than Platform API keys. Codex produces a JSON plan, and Python validates and
    executes that plan through local tool/runtime boundaries.
    """

    def __init__(
        self,
        *,
        codex_bin: str | Path | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        auth_file: str | Path | None = None,
    ) -> None:
        self.codex_bin = str(codex_bin or os.environ.get("CALENDAR_PILOT_CODEX_BIN") or _default_codex_binary() or "codex")
        self.model = model if model is not None else os.environ.get("CALENDAR_PILOT_CODEX_MODEL", "")
        self.timeout_seconds = float(timeout_seconds or os.environ.get("CALENDAR_PILOT_CODEX_TIMEOUT", "120"))
        self.auth_file = Path(auth_file) if auth_file is not None else _codex_auth_file()

    def health_status(self, *, validate_remote: bool = False) -> dict[str, Any]:
        # Report subscription/auth state before binary availability so clean dogfood
        # environments produce stable missing_credential blockers instead of an
        # OS-dependent CLI status. Binary availability remains visible when auth
        # is configured.
        local_auth = _local_subscription_auth_state(self.auth_file)
        if not local_auth["configured"]:
            return {
                "status": local_auth["status"],
                "configured": False,
                "backend": LIVE_CODEX_BACKEND,
                "auth_method": local_auth["auth_method"],
                "credential_source": local_auth["source"],
                "model": self.model or "codex_default",
            }
        binary = _probe_codex_binary(self.codex_bin)
        if not binary["available"]:
            return {
                "status": "codex_cli_unavailable",
                "configured": False,
                "backend": LIVE_CODEX_BACKEND,
                "codex_bin": self.codex_bin,
                "reason": binary["reason"],
                "auth_method": local_auth["auth_method"],
                "credential_source": local_auth["source"],
                "model": self.model or "codex_default",
            }
        if not validate_remote:
            return {
                "status": local_auth["status"],
                "configured": local_auth["configured"],
                "backend": LIVE_CODEX_BACKEND,
                "auth_method": local_auth["auth_method"],
                "credential_source": local_auth["source"],
                "model": self.model or "codex_default",
            }
        try:
            with CodexAppServerRPC(self.codex_bin, timeout_seconds=self.timeout_seconds) as rpc:
                account = rpc.account_read(refresh_token=True)
        except LiveCodexCredentialError as exc:
            return {"status": "invalid_credential", "configured": True, "backend": LIVE_CODEX_BACKEND, "reason": str(exc)}
        except LiveCodexNetworkError as exc:
            return {"status": "network_failure", "configured": local_auth["configured"], "backend": LIVE_CODEX_BACKEND, "reason": str(exc)}
        except LiveCodexError as exc:
            return {"status": "codex_app_server_failure", "configured": local_auth["configured"], "backend": LIVE_CODEX_BACKEND, "reason": str(exc)}
        return _remote_account_health(account, model=self.model)

    def plan_tool_calls(
        self,
        *,
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        authority_tier: int,
        commit: bool,
        plan_id: str,
    ) -> LiveCodexPlanResult:
        local_auth = _local_subscription_auth_state(self.auth_file)
        if not local_auth["configured"]:
            if local_auth["status"] == "wrong_auth_method":
                raise LiveCodexCredentialError("Codex is signed in with API-key auth; live_codex requires ChatGPT subscription auth")
            raise LiveCodexCredentialError("Codex ChatGPT sign-in or CODEX_ACCESS_TOKEN is required for live_codex mode")
        with CodexAppServerRPC(self.codex_bin, timeout_seconds=self.timeout_seconds) as rpc:
            account = rpc.account_read(refresh_token=False)
            health = _remote_account_health(account, model=self.model)
            if not health["configured"]:
                raise LiveCodexCredentialError(f"Codex subscription auth is not configured: {health['status']}")
            thread = rpc.thread_start(model=self.model)
            turn = rpc.turn_start(
                thread_id=str(thread["id"]),
                prompt=self._planner_prompt(goal, observation, biography, authority_tier=authority_tier, commit=commit),
                output_schema=self._tool_plan_output_schema(),
                model=self.model,
            )
            planned = self._extract_plan(rpc.wait_for_turn(thread_id=str(thread["id"]), turn_id=str(turn["id"])))
        calls = [self._planned_call_from_dict(item, idx, allowed_tools=ALLOWED_LIVE_TOOLS) for idx, item in enumerate(planned.get("calls", []))]
        if not calls:
            raise LiveCodexSchemaError("live Codex returned no tool calls")
        return LiveCodexPlanResult(
            calls=calls,
            recommended_next_action=str(planned.get("recommended_next_action") or ""),
            metadata={
                "plan_source": LIVE_CODEX_BACKEND,
                "prompt_version": LIVE_CODEX_PROMPT_VERSION,
                "model": self.model or "codex_default",
                "response_id": turn.get("id"),
                "thread_id": thread.get("id"),
                "turn_id": turn.get("id"),
                "auth_method": health.get("auth_method"),
                "plan_type": health.get("plan_type"),
                "planned_call_count": len(calls),
                "redaction_policy": "event titles, attendees, notes, and locations omitted from live Codex prompt",
            },
        )

    def respond_to_message(
        self,
        *,
        message: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        runtime_report: dict[str, Any],
        intent: str,
    ) -> LiveCodexChatResult:
        local_auth = _local_subscription_auth_state(self.auth_file)
        if not local_auth["configured"]:
            if local_auth["status"] == "wrong_auth_method":
                raise LiveCodexCredentialError("Codex is signed in with API-key auth; live_codex requires ChatGPT subscription auth")
            raise LiveCodexCredentialError("Codex ChatGPT sign-in or CODEX_ACCESS_TOKEN is required for live_codex mode")
        with CodexAppServerRPC(self.codex_bin, timeout_seconds=self.timeout_seconds) as rpc:
            account = rpc.account_read(refresh_token=False)
            health = _remote_account_health(account, model=self.model)
            if not health["configured"]:
                raise LiveCodexCredentialError(f"Codex subscription auth is not configured: {health['status']}")
            thread = rpc.thread_start(model=self.model)
            turn = rpc.turn_start(
                thread_id=str(thread["id"]),
                prompt=self._conversation_prompt(message, observation, biography, runtime_report=runtime_report, intent=intent),
                output_schema=self._conversation_output_schema(),
                model=self.model,
            )
            payload = self._extract_plan(rpc.wait_for_turn(thread_id=str(thread["id"]), turn_id=str(turn["id"])))
        answer = str(payload.get("answer") or "").strip()
        if not answer:
            raise LiveCodexSchemaError("live Codex returned an empty conversation answer")
        route = str(payload.get("route") or "conversation")
        raw_tool_calls = payload.get("tool_calls", [])
        if not isinstance(raw_tool_calls, list):
            raise LiveCodexSchemaError("live Codex conversation tool_calls must be a list")
        tool_calls = [
            self._planned_call_from_dict(item, idx, allowed_tools=CONVERSATION_LIVE_TOOLS)
            for idx, item in enumerate(raw_tool_calls)
        ]
        return LiveCodexChatResult(
            answer=answer,
            route=route,
            metadata={
                "plan_source": LIVE_CODEX_BACKEND,
                "prompt_version": LIVE_CODEX_CHAT_PROMPT_VERSION,
                "model": self.model or "codex_default",
                "response_id": turn.get("id"),
                "thread_id": thread.get("id"),
                "turn_id": turn.get("id"),
                "auth_method": health.get("auth_method"),
                "plan_type": health.get("plan_type"),
                "conversation_route": route,
                "intent": intent,
                "conversation_tool_call_count": len(tool_calls),
                "conversation_tool_names": [call.tool_name.value for call in tool_calls],
                "redaction_policy": "calendar details summarized; provider credentials and raw auth tokens omitted",
            },
            tool_calls=tool_calls,
        )

    @staticmethod
    def _extract_plan(raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()
        if not text:
            raise LiveCodexSchemaError("live Codex returned an empty response")
        if text.startswith("```"):
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                if "refusal" in text.lower() or "safety" in text.lower():
                    raise LiveCodexSafetyRefusal("live Codex refused the planning request")
                raise LiveCodexSchemaError("live Codex response was not JSON")
            try:
                parsed = json.loads(text[start:end + 1])
            except json.JSONDecodeError as exc:
                raise LiveCodexSchemaError(f"live Codex JSON response was invalid: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LiveCodexSchemaError("live Codex response was not a JSON object")
        return parsed

    @staticmethod
    def _planned_call_from_dict(
        data: Any,
        index: int,
        *,
        allowed_tools: set[CodexToolName],
    ) -> ModelPlannedCall:
        if not isinstance(data, dict):
            raise LiveCodexSchemaError(f"planned call {index} is not an object")
        try:
            tool_name = CodexToolName(str(data["tool_name"]))
        except Exception as exc:
            raise LiveCodexSchemaError(f"planned call {index} used unsupported tool {data.get('tool_name')}") from exc
        if tool_name not in allowed_tools:
            raise LiveCodexSchemaError(f"planned call {index} used disallowed live tool {tool_name.value}")
        try:
            input_payload = json.loads(str(data.get("input_json") or "{}"))
        except json.JSONDecodeError as exc:
            raise LiveCodexSchemaError(f"planned call {index} input_json is invalid JSON: {exc}") from exc
        if not isinstance(input_payload, dict):
            raise LiveCodexSchemaError(f"planned call {index} input_json must decode to an object")
        return ModelPlannedCall(
            tool_name=tool_name,
            input=input_payload,
            requested_authority_tier=max(0, min(6, int(data.get("requested_authority_tier", 0)))),
            user_visible_reason=str(data.get("user_visible_reason") or "Live Codex selected this tool."),
            correlation_id=str(data.get("correlation_id") or f"live_codex_call_{index}"),
        )

    @staticmethod
    def _planner_prompt(
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        authority_tier: int,
        commit: bool,
    ) -> str:
        context = {
            "goal": goal,
            "authority_tier": authority_tier,
            "commit_requested": commit,
            "observation": _redacted_observation(observation),
            "biography": _redacted_biography(biography),
            "allowed_tools": sorted(tool.value for tool in ALLOWED_LIVE_TOOLS),
        }
        return (
            "You are CalendarPilot's live Codex executive. Return only JSON that "
            "matches the supplied output schema. Plan through local CalendarPilot "
            "tools only; do not claim to write calendars directly. Use this sequence "
            "unless impossible: inspect_week, generate_candidate_frontier, "
            "compare_candidates, simulate_action_program, then stage_action_packet "
            "or request_commit. For candidate-dependent tools, set input_json to "
            "{\"candidate_ref\":\"winner\"}; Python will replace it after comparison. "
            "Do not run shell commands or inspect the repository. Redacted planning context:\n"
            + json.dumps(context, sort_keys=True)
        )

    @staticmethod
    def _tool_plan_output_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["calls", "recommended_next_action", "rationale"],
            "properties": {
                "calls": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "tool_name",
                            "input_json",
                            "requested_authority_tier",
                            "user_visible_reason",
                            "correlation_id",
                        ],
                        "properties": {
                            "tool_name": {"type": "string", "enum": sorted(tool.value for tool in ALLOWED_LIVE_TOOLS)},
                            "input_json": {"type": "string", "description": "A JSON object string containing tool input."},
                            "requested_authority_tier": {"type": "integer", "minimum": 0, "maximum": 6},
                            "user_visible_reason": {"type": "string"},
                            "correlation_id": {"type": "string"},
                        },
                    },
                },
                "recommended_next_action": {"type": "string"},
                "rationale": {"type": "string"},
            },
        }

    @staticmethod
    def _conversation_prompt(
        message: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        runtime_report: dict[str, Any],
        intent: str,
    ) -> str:
        context = {
            "message": message,
            "intent": intent,
            "runtime": _conversation_runtime_context(runtime_report, include_diagnostics=intent == "metadata_question"),
            "calendar_summary": _conversation_calendar_summary(observation),
            "profile_summary": _conversation_profile_summary(biography),
            "available_boundaries": {
                "codex": "conversation and bounded tool planning through CalendarPilot tools",
                "diffusiongemma": "candidate frontier generation and right-moment policy",
                "swift": "authority grants, validation, stage/commit/undo receipts",
                "provider": "calendar read/write only through configured provider adapter",
            },
            "conversation_tools": {
                "allowed_tools": sorted(tool.value for tool in CONVERSATION_LIVE_TOOLS),
                "usage": (
                    "Return tool_calls when the user asks to inspect replay evidence, authority scope, "
                    "profile claims, profile repair proposals, self-play release gates, or Swift denial reasons. "
                    "Use an empty array when no local evidence tool is needed."
                ),
                "safe_inputs": {
                    "query_replay_trace": {"candidate_id": "optional candidate id"},
                    "inspect_authority_scope": {},
                    "inspect_profile_claims": {},
                    "propose_profile_patch": {"correction": "user-stated profile correction"},
                    "apply_profile_patch": {"claim": "profile claim", "correction": "user-confirmed correction", "confirmed": True},
                    "run_self_play_probe": {"episodes": "1 to 3"},
                    "propose_autonomy_scope": {"candidate_id": "latest or explicit candidate id"},
                    "explain_swift_denial": {"denied_reason": "denial reason to explain"},
                    "request_undo": {"rollback_handle_id": "optional; Python can use the latest undoable handle"},
                },
            },
        }
        return (
            "You are CalendarPilot's conversational access point. Return only JSON "
            "matching the schema. Answer the user directly when no calendar operation "
            "is needed. For smalltalk, answer briefly and do not volunteer backend, "
            "credential, endpoint, or setup-note details. For metadata/status questions, "
            "be explicit about which runtime/backends are active and distinguish true "
            "blockers from optional local fallback modes. Do not describe optional auto "
            "fallbacks as broken endpoints. If the "
            "user asks for a calendar change, say that the app should route the next "
            "turn through the tool planner rather than claiming a write happened. "
            "When the user asks for replay/profile/self-play/authority/denial evidence, "
            "include bounded tool_calls so Python can execute them and attach receipts. "
            "Include request_undo only when the user explicitly asks to undo, revert, or "
            "roll back the latest change. Include apply_profile_patch only when the user "
            "explicitly asks to apply or confirm an existing profile patch. Do not include "
            "commit tool calls in conversation mode; commits require explicit action controls. "
            "Do not claim to have contacted provider APIs or changed calendars unless "
            "a local CalendarPilot receipt exists. Redacted app context:\n"
            + json.dumps(context, sort_keys=True)
        )

    @staticmethod
    def _conversation_output_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["answer", "route", "tool_calls", "rationale"],
            "properties": {
                "answer": {"type": "string"},
                "route": {
                    "type": "string",
                    "enum": [
                        "conversation",
                        "metadata",
                        "evidence_inspection",
                        "profile_repair_proposed",
                        "self_play_probe",
                        "calendar_planning_recommended",
                        "safety_refusal",
                    ],
                },
                "tool_calls": {
                    "type": "array",
                    "minItems": 0,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "tool_name",
                            "input_json",
                            "requested_authority_tier",
                            "user_visible_reason",
                            "correlation_id",
                        ],
                        "properties": {
                            "tool_name": {"type": "string", "enum": sorted(tool.value for tool in CONVERSATION_LIVE_TOOLS)},
                            "input_json": {"type": "string", "description": "A JSON object string containing tool input."},
                            "requested_authority_tier": {"type": "integer", "minimum": 0, "maximum": 6},
                            "user_visible_reason": {"type": "string"},
                            "correlation_id": {"type": "string"},
                        },
                    },
                },
                "rationale": {"type": "string"},
            },
        }


class CodexAppServerRPC:
    def __init__(self, codex_bin: str, *, timeout_seconds: float) -> None:
        self.codex_bin = codex_bin
        self.timeout_seconds = timeout_seconds
        self._next_id = 1
        self._proc: subprocess.Popen[str] | None = None
        self._agent_text: dict[str, str] = {}
        self._completed_agent_text: list[str] = []

    def __enter__(self) -> "CodexAppServerRPC":
        try:
            self._proc = subprocess.Popen(
                [self.codex_bin, "app-server"],
                cwd=ROOT,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise LiveCodexRuntimeError(f"failed to start codex app-server: {exc}") from exc
        self.request("initialize", {
            "clientInfo": {
                "name": "calendar_pilot",
                "title": "CalendarPilot",
                "version": "0.1.0",
            }
        })
        self.notify("initialized", {})
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._proc is None:
            return
        proc = self._proc
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()
        self._proc = None

    def account_read(self, *, refresh_token: bool) -> dict[str, Any]:
        out = self.request("account/read", {"refreshToken": refresh_token})
        return dict(out)

    def thread_start(self, *, model: str) -> dict[str, Any]:
        params: dict[str, Any] = {
            "cwd": str(ROOT),
            "approvalPolicy": "never",
            "sandboxPolicy": {"type": "readOnly"},
            "serviceName": "calendar_pilot",
        }
        if model:
            params["model"] = model
        out = self.request("thread/start", params)
        thread = out.get("thread")
        if not isinstance(thread, dict) or not thread.get("id"):
            raise LiveCodexRuntimeError("codex app-server did not return a thread id")
        return thread

    def turn_start(self, *, thread_id: str, prompt: str, output_schema: dict[str, Any], model: str) -> dict[str, Any]:
        params: dict[str, Any] = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": prompt}],
            "approvalPolicy": "never",
            "sandboxPolicy": {"type": "readOnly"},
            "outputSchema": output_schema,
        }
        if model:
            params["model"] = model
        out = self.request("turn/start", params)
        turn = out.get("turn")
        if not isinstance(turn, dict) or not turn.get("id"):
            raise LiveCodexRuntimeError("codex app-server did not return a turn id")
        return turn

    def wait_for_turn(self, *, thread_id: str, turn_id: str) -> str:
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            message = self.read_message(timeout=max(0.1, min(2.0, deadline - time.time())))
            if "method" not in message:
                continue
            self._handle_server_message(message)
            if message.get("method") == "item/completed" and self._completed_agent_text:
                return self._completed_agent_text[-1]
            if message.get("method") == "turn/completed":
                params = message.get("params", {})
                turn = params.get("turn", {}) if isinstance(params, dict) else {}
                if turn.get("id") != turn_id:
                    continue
                if turn.get("status") == "failed":
                    raise _turn_failure(turn)
                if self._completed_agent_text:
                    return self._completed_agent_text[-1]
                joined = "".join(self._agent_text.values()).strip()
                if joined:
                    return joined
                raise LiveCodexSchemaError("live Codex turn completed without an agent message")
        raise LiveCodexNetworkError("codex app-server turn timed out")

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._write({"method": method, "id": request_id, "params": params or {}})
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            message = self.read_message(timeout=max(0.1, min(2.0, deadline - time.time())))
            if message.get("id") == request_id:
                if "error" in message:
                    raise _rpc_error(method, message["error"])
                result = message.get("result", {})
                return result if isinstance(result, dict) else {"value": result}
            self._handle_server_message(message)
        raise LiveCodexNetworkError(f"codex app-server request timed out: {method}")

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._write({"method": method, "params": params or {}})

    def read_message(self, *, timeout: float) -> dict[str, Any]:
        proc = self._require_proc()
        assert proc.stdout is not None
        ready, _, _ = select.select([proc.stdout], [], [], timeout)
        if not ready:
            if proc.poll() is not None:
                stderr = proc.stderr.read() if proc.stderr is not None else ""
                raise LiveCodexRuntimeError(f"codex app-server exited with {proc.returncode}: {_redact_secret_text(stderr)}")
            return {}
        line = proc.stdout.readline()
        if not line:
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            raise LiveCodexRuntimeError(f"codex app-server closed stdout: {_redact_secret_text(stderr)}")
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise LiveCodexRuntimeError(f"codex app-server returned invalid JSON: {exc}") from exc

    def _write(self, message: dict[str, Any]) -> None:
        proc = self._require_proc()
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    def _require_proc(self) -> subprocess.Popen[str]:
        if self._proc is None:
            raise LiveCodexRuntimeError("codex app-server is not running")
        return self._proc

    def _handle_server_message(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        params = message.get("params", {}) if isinstance(message.get("params"), dict) else {}
        if method == "item/agentMessage/delta":
            item_id = str(params.get("itemId") or "")
            self._agent_text[item_id] = self._agent_text.get(item_id, "") + str(params.get("delta") or "")
        if method == "item/completed":
            item = params.get("item", {})
            if isinstance(item, dict) and item.get("type") == "agentMessage":
                text = str(item.get("text") or "").strip()
                if text:
                    self._completed_agent_text.append(text)
        if method == "error":
            error = params.get("error", {})
            raise _rpc_error("server", error if isinstance(error, dict) else {"message": str(error)})
        if method == "account/chatgptAuthTokens/refresh":
            raise LiveCodexCredentialError("Codex requested refreshed ChatGPT auth tokens")


class LiveCodexToolPlanner:
    backend_name = LIVE_CODEX_BACKEND

    def __init__(self, *, runtime: CodexToolRuntime | None = None, client: CodexAppServerClient | None = None) -> None:
        self.runtime = runtime or CodexToolRuntime()
        self.client = client or CodexAppServerClient()

    def health_status(self, *, validate_remote: bool = False) -> dict[str, Any]:
        return self.client.health_status(validate_remote=validate_remote)

    def chat_response(
        self,
        message: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        runtime_report: dict[str, Any],
        intent: str,
    ) -> LiveCodexChatResult:
        try:
            return self.client.respond_to_message(
                message=message,
                observation=observation,
                biography=biography,
                runtime_report=runtime_report,
                intent=intent,
            )
        except LiveCodexError as exc:
            return self._failed_chat_response(message, exc)

    def plan_goal(
        self,
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        authority_tier: int = 3,
        commit: bool = False,
    ) -> CodexExecutivePlan:
        plan_id = CodexToolPlanner._plan_id(goal, observation.observation_id)
        grant = self.runtime.kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=authority_tier,
            scopes=authority_scopes_for_tier(authority_tier),
            confirmation_provenance=f"live_codex_plan_goal:{plan_id}",
            confirmed_by_user=commit,
            issued_at=observation.observed_at,
        )
        try:
            model_plan = self.client.plan_tool_calls(
                goal=goal,
                observation=observation,
                biography=biography,
                authority_tier=authority_tier,
                commit=commit,
                plan_id=plan_id,
            )
            self._validate_model_plan_before_execution(model_plan.calls)
            plan = CodexExecutivePlan(
                plan_id=plan_id,
                goal=goal,
                recommended_next_action=model_plan.recommended_next_action,
                planner_backend=LIVE_CODEX_BACKEND,
                planner_metadata=model_plan.metadata,
            )
            self._execute_model_plan(plan, model_plan.calls, observation, biography, grant_id=grant.grant_id)
            if not plan.recommended_next_action:
                plan.recommended_next_action = self._recommended_action(plan)
            return plan
        except LiveCodexError as exc:
            return self._failed_plan(goal, observation, exc)

    def _execute_model_plan(
        self,
        plan: CodexExecutivePlan,
        calls: list[ModelPlannedCall],
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        grant_id: str,
    ) -> None:
        frontier_ids: list[str] = []
        winner: str | None = None
        saw_frontier = False
        saw_compare = False
        for idx, planned in enumerate(calls):
            payload = dict(planned.input)
            if planned.tool_name == CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                saw_frontier = True
                payload.setdefault("goal", plan.goal)
                payload["limit"] = max(1, min(8, int(payload.get("limit", 6))))
            if planned.tool_name == CodexToolName.COMPARE_CANDIDATES:
                if not saw_frontier:
                    raise LiveCodexSchemaError("compare_candidates appeared before generate_candidate_frontier")
                saw_compare = True
                payload["candidate_ids"] = payload.get("candidate_ids") or frontier_ids
            if planned.tool_name in {CodexToolName.SIMULATE_ACTION_PROGRAM, CodexToolName.STAGE_ACTION_PACKET, CodexToolName.REQUEST_COMMIT}:
                if not saw_compare:
                    raise LiveCodexSchemaError(f"{planned.tool_name.value} appeared before compare_candidates")
                if payload.get("candidate_ref") == "winner" or not payload.get("candidate_id"):
                    if not winner:
                        raise LiveCodexSchemaError(f"{planned.tool_name.value} requested winner before one existed")
                    payload["candidate_id"] = winner
                payload.pop("candidate_ref", None)
                if str(payload.get("candidate_id")) not in self.runtime.frontier:
                    raise LiveCodexSchemaError(f"{planned.tool_name.value} referenced unknown candidate_id")
            call = CodexToolCall(
                tool_call_id=self._tool_call_id(plan.plan_id, idx, planned),
                tool_name=planned.tool_name,
                input=payload,
                requested_authority_tier=planned.requested_authority_tier,
                user_visible_reason=planned.user_visible_reason,
                authority_grant_id=grant_id,
                correlation_id=planned.correlation_id,
                created_at=datetime.now(timezone.utc),
            )
            receipt = self._run(plan, call, observation, biography)
            if planned.tool_name == CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                frontier_ids = [str(item) for item in receipt.output.get("frontier_ids", [])]
            if planned.tool_name == CodexToolName.COMPARE_CANDIDATES:
                winner = str((receipt.output.get("winner") or {}).get("candidate_id") or "")

    def _failed_chat_response(self, message: str, exc: LiveCodexError) -> LiveCodexChatResult:
        return LiveCodexChatResult(
            answer=(
                "Live Codex conversation is unavailable for this turn. "
                f"{exc} Sign in with ChatGPT for Codex subscription access ({CODEX_AUTH_DOC_URL}) "
                "or switch back to fixture mode for local deterministic dogfooding."
            ),
            route="conversation",
            metadata={
                "plan_source": LIVE_CODEX_BACKEND,
                "prompt_version": LIVE_CODEX_CHAT_PROMPT_VERSION,
                "error_category": exc.category,
                "model": getattr(self.client, "model", "") or "codex_default",
                "conversation_route": "live_codex_unavailable",
                "input_digest": hashlib.sha1(message.encode()).hexdigest()[:12],
                "redaction_policy": "no raw prompt, token, or model response persisted",
            },
        )

    def _run(self, plan: CodexExecutivePlan, call: CodexToolCall, observation: RawCalendarObservation, biography: UserBiography) -> CodexToolReceipt:
        plan.calls.append(call)
        receipt = self.runtime.execute(call, observation, biography)
        plan.receipts.append(receipt)
        return receipt

    def _failed_plan(self, goal: str, observation: RawCalendarObservation, exc: LiveCodexError) -> CodexExecutivePlan:
        plan_id = CodexToolPlanner._plan_id(goal, observation.observation_id)
        call = CodexToolCall(
            tool_call_id="tool_" + hashlib.sha1(f"{plan_id}|live_codex_error".encode()).hexdigest()[:12],
            tool_name=CodexToolName.VALIDATE_MODEL_PLAN,
            input={"error_category": exc.category},
            requested_authority_tier=0,
            user_visible_reason="Validate the live Codex model plan before executing local tools.",
            correlation_id=plan_id,
            created_at=datetime.now(timezone.utc),
        )
        receipt = CodexToolReceipt(
            tool_call_id=call.tool_call_id,
            tool_name=call.tool_name,
            status=CodexToolStatus.FAILED,
            output={
                "error_category": exc.category,
                "message": str(exc),
                "recovery": f"Sign in with ChatGPT for Codex subscription access ({CODEX_AUTH_DOC_URL}) or switch CALENDAR_PILOT_RUNTIME_MODE back to fixture.",
            },
            denied_reason=str(exc),
            correlation_id=plan_id,
            created_at=datetime.now(timezone.utc),
        )
        self.runtime.replay.append_tool_call(call)
        self.runtime.replay.append_tool_receipt(receipt)
        return CodexExecutivePlan(
            plan_id=plan_id,
            goal=goal,
            calls=[call],
            receipts=[receipt],
            recommended_next_action="live_codex_unavailable",
            planner_backend=LIVE_CODEX_BACKEND,
            planner_metadata={
                "plan_source": LIVE_CODEX_BACKEND,
                "prompt_version": LIVE_CODEX_PROMPT_VERSION,
                "error_category": exc.category,
                "model": self.client.model or "codex_default",
                "redaction_policy": "no raw prompt, token, or model response persisted",
            },
        )

    @staticmethod
    def _validate_model_plan_before_execution(calls: list[ModelPlannedCall]) -> None:
        if not calls:
            raise LiveCodexSchemaError("live Codex returned no tool calls")
        saw_frontier = False
        saw_compare = False
        terminal_tool: CodexToolName | None = None
        for idx, planned in enumerate(calls):
            if terminal_tool is not None:
                raise LiveCodexSchemaError(f"{planned.tool_name.value} appeared after terminal tool {terminal_tool.value}")
            if planned.tool_name == CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                saw_frontier = True
            if planned.tool_name == CodexToolName.COMPARE_CANDIDATES:
                if not saw_frontier:
                    raise LiveCodexSchemaError("compare_candidates appeared before generate_candidate_frontier")
                saw_compare = True
            if planned.tool_name in {CodexToolName.SIMULATE_ACTION_PROGRAM, CodexToolName.STAGE_ACTION_PACKET, CodexToolName.REQUEST_COMMIT} and not saw_compare:
                raise LiveCodexSchemaError(f"{planned.tool_name.value} appeared before compare_candidates")
            if planned.tool_name in {CodexToolName.STAGE_ACTION_PACKET, CodexToolName.REQUEST_COMMIT}:
                terminal_tool = planned.tool_name

    @staticmethod
    def _recommended_action(plan: CodexExecutivePlan) -> str:
        for receipt in reversed(plan.receipts):
            if receipt.tool_name == CodexToolName.REQUEST_COMMIT:
                return "committed" if not receipt.denied_reason else "commit_denied_stage_instead"
            if receipt.tool_name == CodexToolName.STAGE_ACTION_PACKET:
                return "stage_for_confirmation"
        return "live_plan_executed"

    @staticmethod
    def _tool_call_id(plan_id: str, index: int, planned: ModelPlannedCall) -> str:
        raw = f"{plan_id}|{index}|{planned.tool_name.value}|{planned.input}|{planned.correlation_id}"
        return "tool_" + hashlib.sha1(raw.encode()).hexdigest()[:12]


def _conversation_runtime_context(report: dict[str, Any], *, include_diagnostics: bool = True) -> dict[str, Any]:
    credentials = report.get("credentials", {})
    safe_credentials: dict[str, Any] = {}
    if isinstance(credentials, dict):
        for name, state in credentials.items():
            if not isinstance(state, dict):
                continue
            required = bool(state.get("required"))
            configured = bool(state.get("configured"))
            if not include_diagnostics and not required and not configured:
                continue
            safe_credentials[str(name)] = {
                "configured": configured,
                "required": required,
                "status": str(state.get("status", "")),
                "auth_method": str(state.get("auth_method", "")),
                "source": str(state.get("source", "")),
            }
    return {
        "runtime_mode": report.get("runtime_mode"),
        "requested_runtime_mode": report.get("requested_runtime_mode"),
        "mode_label": report.get("mode_label"),
        "backends": report.get("backends", {}),
        "live_blockers": report.get("live_blockers", []),
        "setup_notes": report.get("setup_notes", []) if include_diagnostics else [],
        "fixture_mode": report.get("fixture_mode"),
        "live_target": report.get("live_target"),
        "production_target": report.get("production_target"),
        "credentials": safe_credentials,
    }


def _conversation_calendar_summary(observation: RawCalendarObservation) -> dict[str, Any]:
    return {
        "observation_id": observation.observation_id,
        "event_count": len(observation.events),
        "task_count": len(observation.tasks),
        "time_zone_id": observation.time_zone_id,
        "device_surface": observation.device_context.active_surface,
        "focus_mode": observation.device_context.is_focus_mode,
    }


def _conversation_profile_summary(biography: UserBiography) -> dict[str, Any]:
    return {
        "preference_claim_count": len(biography.preference_claims),
        "best_response_hours": biography.best_response_hours,
        "deep_work_windows": biography.deep_work_windows,
        "admin_windows": biography.admin_windows,
        "notification_fatigue": biography.notification_fatigue,
    }


def _remote_account_health(account_result: dict[str, Any], *, model: str) -> dict[str, Any]:
    account = account_result.get("account")
    if not isinstance(account, dict):
        return {
            "status": "missing_credential" if account_result.get("requiresOpenaiAuth") else "not_required",
            "configured": False,
            "backend": LIVE_CODEX_BACKEND,
            "auth_method": "missing",
            "model": model or "codex_default",
        }
    auth_method = str(account.get("type") or "")
    if auth_method in SUBSCRIPTION_AUTH_MODES:
        return {
            "status": "ok",
            "configured": True,
            "backend": LIVE_CODEX_BACKEND,
            "auth_method": auth_method,
            "plan_type": str(account.get("planType") or ""),
            "credential_source": "codex_app_server",
            "model": model or "codex_default",
        }
    if auth_method in API_KEY_AUTH_MODES:
        return {
            "status": "wrong_auth_method",
            "configured": False,
            "backend": LIVE_CODEX_BACKEND,
            "auth_method": auth_method,
            "credential_source": "codex_app_server",
            "model": model or "codex_default",
        }
    return {
        "status": "invalid_credential",
        "configured": False,
        "backend": LIVE_CODEX_BACKEND,
        "auth_method": auth_method or "unknown",
        "model": model or "codex_default",
    }


def _local_subscription_auth_state(auth_file: Path | None = None) -> dict[str, Any]:
    if os.environ.get("CODEX_ACCESS_TOKEN"):
        return {"status": "configured", "configured": True, "source": "environment", "auth_method": "CODEX_ACCESS_TOKEN"}
    path = auth_file or _codex_auth_file()
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"status": "invalid_credential", "configured": False, "source": "auth_cache", "auth_method": "unreadable"}
        mode = str(data.get("auth_mode") or data.get("authMode") or "")
        if mode in SUBSCRIPTION_AUTH_MODES:
            return {"status": "configured", "configured": True, "source": "auth_cache", "auth_method": mode}
        if mode in API_KEY_AUTH_MODES or data.get("OPENAI_API_KEY"):
            return {"status": "wrong_auth_method", "configured": False, "source": "auth_cache", "auth_method": mode or "apiKey"}
        return {"status": "missing_credential", "configured": False, "source": "auth_cache", "auth_method": mode or "missing"}
    return {"status": "missing_credential", "configured": False, "source": "missing", "auth_method": "missing"}


def _codex_auth_file() -> Path:
    if os.environ.get("CALENDAR_PILOT_CODEX_AUTH_FILE"):
        return Path(os.environ["CALENDAR_PILOT_CODEX_AUTH_FILE"])
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    return home / "auth.json"


_BINARY_PROBE_CACHE: dict[str, dict[str, Any]] = {}


def _probe_codex_binary(codex_bin: str) -> dict[str, Any]:
    cached = _BINARY_PROBE_CACHE.get(codex_bin)
    if cached:
        return cached
    try:
        proc = subprocess.run([codex_bin, "--version"], text=True, capture_output=True, timeout=5)
        ok = proc.returncode == 0
        reason = "" if ok else _redact_secret_text((proc.stdout or "") + (proc.stderr or ""))
    except Exception as exc:
        ok = False
        reason = str(exc)
    result = {"available": ok, "reason": reason}
    _BINARY_PROBE_CACHE[codex_bin] = result
    return result


def _default_codex_binary() -> str | None:
    candidates = [
        "/Applications/Codex.app/Contents/Resources/codex",
        str(Path.home() / ".codex" / "plugins" / ".plugin-appserver" / "codex"),
        shutil.which("codex") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists() and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("codex")


def _rpc_error(method: str, error: Any) -> LiveCodexError:
    data = error if isinstance(error, dict) else {"message": str(error)}
    message = str(data.get("message") or data)
    info = data.get("codexErrorInfo") if isinstance(data.get("codexErrorInfo"), dict) else {}
    code = str(info.get("type") or data.get("code") or "")
    status = info.get("httpStatusCode")
    if status in {401, 403} or code in {"Unauthorized"}:
        return LiveCodexCredentialError(message)
    if code in {"HttpConnectionFailed", "ResponseStreamConnectionFailed", "ResponseStreamDisconnected"}:
        return LiveCodexNetworkError(message)
    if "refusal" in message.lower() or "safety" in message.lower():
        return LiveCodexSafetyRefusal(message)
    if method in {"turn/start", "server"} or code in {"BadRequest", "ResponseTooManyFailedAttempts"}:
        return LiveCodexSchemaError(message)
    return LiveCodexRuntimeError(message)


def _turn_failure(turn: dict[str, Any]) -> LiveCodexError:
    error = turn.get("error") if isinstance(turn.get("error"), dict) else {"message": str(turn.get("error") or "turn failed")}
    return _rpc_error("turn/start", error)


def _redact_secret_text(text: str) -> str:
    redacted = text
    for key in ["CODEX_ACCESS_TOKEN", "CODEX_API_KEY", "OPENAI_API_KEY", "NVIDIA_API_KEY", "NIM_API_KEY"]:
        value = os.environ.get(key)
        if value:
            redacted = redacted.replace(value, f"<redacted:{key}>")
    return redacted


def _redacted_observation(observation: RawCalendarObservation) -> dict[str, Any]:
    return {
        "observation_id": observation.observation_id,
        "user_scope_id_hash": hashlib.sha1(observation.user_scope_id.encode()).hexdigest()[:12],
        "observed_at": observation.observed_at.isoformat(),
        "time_zone_id": observation.time_zone_id,
        "device_context": {
            "local_hour": observation.device_context.local_hour,
            "active_surface": observation.device_context.active_surface,
            "is_focus_mode": observation.device_context.is_focus_mode,
        },
        "events": [
            {
                "event_id": event.event_id,
                "calendar_id": event.calendar_id,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "duration_minutes": int((event.end - event.start).total_seconds() // 60),
                "category": event.category,
                "is_user_owned": event.is_user_owned,
                "is_flexible": event.is_flexible,
                "attendee_count": len(event.attendees),
            }
            for event in observation.events[:40]
        ],
        "tasks": [
            {
                "task_id": task.task_id,
                "due": task.due.isoformat() if task.due else None,
                "estimated_minutes": task.estimated_minutes,
                "category": task.category,
            }
            for task in observation.tasks[:40]
        ],
    }


def _redacted_biography(biography: UserBiography) -> dict[str, Any]:
    return {
        "best_response_hours": biography.best_response_hours,
        "notification_fatigue": biography.notification_fatigue,
        "preference_claim_count": len(biography.preference_claims),
        "preference_claims": [
            {
                "claim_id": f"claim_{idx}",
                "confidence": claim.get("confidence", 0.0),
                "evidence_count": len(str(claim.get("last_evidence", claim.get("reason", ""))).split()),
            }
            for idx, claim in enumerate(biography.preference_claims[:8])
        ],
    }
