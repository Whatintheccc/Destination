

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from calendar_pilot.codex.live import (
    CodexAppServerClient,
    CodexAppServerRPC,
    LiveCodexChatResult,
    LiveCodexCredentialError,
    LiveCodexNetworkError,
    LiveCodexPlanResult,
    LiveCodexRuntimeError,
    LiveCodexToolPlanner,
    ModelPlannedCall,
    _conversation_runtime_context,
)
from calendar_pilot.codex.tools import CodexToolRuntime
from calendar_pilot.frontend.runtime import runtime_is_release_safe
from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import CodexToolName, CodexToolStatus, RawCalendarObservation, UserBiography


ROOT = Path(__file__).resolve().parents[1]


def load_obs() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8")))


def load_bio() -> UserBiography:
    return UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8")))


class FakeLiveCodexClient:
    model = "gpt-5.5-test"

    def __init__(self, calls: list[ModelPlannedCall] | None = None, chat_tool_calls: list[ModelPlannedCall] | None = None) -> None:
        self.calls = calls
        self.chat_tool_calls = chat_tool_calls or []

    def health_status(self, *, validate_remote: bool = False) -> dict[str, object]:
        return {"status": "ok", "configured": True, "model": self.model, "credential_source": "test_fake"}

    def plan_tool_calls(self, **_kwargs: object) -> LiveCodexPlanResult:
        calls = self.calls or [
            ModelPlannedCall(CodexToolName.INSPECT_WEEK, {"goal": "Make next week less chaotic"}, 3, "Inspect the calendar.", "trace_live_inspect"),
            ModelPlannedCall(CodexToolName.GENERATE_CANDIDATE_FRONTIER, {"goal": "Make next week less chaotic", "limit": 4}, 3, "Generate candidate futures.", "trace_live_frontier"),
            ModelPlannedCall(CodexToolName.COMPARE_CANDIDATES, {}, 3, "Compare the frontier.", "trace_live_compare"),
            ModelPlannedCall(CodexToolName.SIMULATE_ACTION_PROGRAM, {"candidate_ref": "winner"}, 3, "Simulate the winner.", "trace_live_simulate"),
            ModelPlannedCall(CodexToolName.STAGE_ACTION_PACKET, {"candidate_ref": "winner"}, 3, "Stage the winner.", "trace_live_stage"),
        ]
        return LiveCodexPlanResult(
            calls=calls,
            recommended_next_action="stage_for_confirmation",
            metadata={
                "plan_source": "live_codex_app_server",
                "model": self.model,
                "response_id": "turn_test",
                "planned_call_count": len(calls),
                "redaction_policy": "test",
            },
        )

    def respond_to_message(self, **kwargs: object) -> LiveCodexChatResult:
        return LiveCodexChatResult(
            answer=f"Codex received: {kwargs.get('message')}",
            route="metadata",
            metadata={
                "plan_source": "live_codex_app_server",
                "prompt_version": "calendar_pilot_codex_conversation_v1",
                "model": self.model,
                "response_id": "turn_chat_test",
                "thread_id": "thread_chat_test",
                "turn_id": "turn_chat_test",
                "conversation_route": "metadata",
                "conversation_tool_call_count": len(self.chat_tool_calls),
                "conversation_tool_names": [call.tool_name.value for call in self.chat_tool_calls],
            },
            tool_calls=self.chat_tool_calls,
        )


class MissingSubscriptionClient:
    model = "codex_default"

    def health_status(self, *, validate_remote: bool = False) -> dict[str, object]:
        return {
            "status": "missing_credential",
            "configured": False,
            "backend": "live_codex_app_server",
            "auth_method": "missing",
        }

    def plan_tool_calls(self, **_kwargs: object) -> LiveCodexPlanResult:
        raise LiveCodexCredentialError("Codex ChatGPT sign-in or CODEX_ACCESS_TOKEN is required")

    def respond_to_message(self, **_kwargs: object) -> LiveCodexChatResult:
        raise LiveCodexCredentialError("Codex ChatGPT sign-in or CODEX_ACCESS_TOKEN is required")


class FakeRPC:
    result: dict[str, object] = {
        "account": {"type": "chatgpt", "planType": "pro"},
        "requiresOpenaiAuth": True,
    }
    failure: Exception | None = None

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def __enter__(self) -> "FakeRPC":
        if self.failure is not None:
            raise self.failure
        return self

    def __exit__(self, *_exc: object) -> None:
        pass

    def account_read(self, *, refresh_token: bool) -> dict[str, object]:
        return self.result


class RemoteHealthClient(CodexAppServerClient):
    def __init__(self, failure: Exception | None) -> None:
        super().__init__(codex_bin="/bin/echo", model="test-model")
        self.failure = failure

    def health_status(self, *, validate_remote: bool = False) -> dict[str, object]:
        FakeRPC.failure = self.failure
        try:
            with patch("calendar_pilot.codex.live._probe_codex_binary", return_value={"available": True, "reason": ""}), patch(
                "calendar_pilot.codex.live._local_subscription_auth_state",
                return_value={"status": "configured", "configured": True, "source": "auth_cache", "auth_method": "chatgpt"},
            ), patch("calendar_pilot.codex.live.CodexAppServerRPC", FakeRPC):
                return super().health_status(validate_remote=validate_remote)
        finally:
            FakeRPC.failure = None


class LiveCodexTests(unittest.TestCase):
    def test_live_codex_planner_executes_model_planned_tool_calls(self) -> None:
        runtime = CodexToolRuntime(kernel=SwiftKernelStub(), replay=ReplayBuffer())
        planner = LiveCodexToolPlanner(runtime=runtime, client=FakeLiveCodexClient())
        plan = planner.plan_goal("Make next week less chaotic", load_obs(), load_bio(), authority_tier=3, commit=False)

        self.assertEqual(plan.planner_backend, "live_codex_app_server")
        self.assertEqual(plan.planner_metadata["response_id"], "turn_test")
        self.assertEqual([call.tool_name for call in plan.calls[:3]], [
            CodexToolName.INSPECT_WEEK,
            CodexToolName.GENERATE_CANDIDATE_FRONTIER,
            CodexToolName.COMPARE_CANDIDATES,
        ])
        self.assertEqual(plan.receipts[-1].tool_name, CodexToolName.STAGE_ACTION_PACKET)
        self.assertEqual(plan.receipts[-1].correlation_id, "trace_live_stage")
        self.assertIn(plan.recommended_next_action, {"stage_for_confirmation", "staged_draft"})

    def test_live_codex_planner_answers_non_calendar_chat_with_metadata(self) -> None:
        planner = LiveCodexToolPlanner(runtime=CodexToolRuntime(kernel=SwiftKernelStub()), client=FakeLiveCodexClient())

        result = planner.chat_response(
            "hello metadata check",
            load_obs(),
            load_bio(),
            runtime_report={"runtime_mode": "live_codex", "backends": {"codex": "live_codex_app_server"}},
            intent="metadata_question",
        )

        self.assertEqual(result.route, "metadata")
        self.assertIn("hello metadata check", result.answer)
        self.assertEqual(result.metadata["response_id"], "turn_chat_test")
        self.assertEqual(result.metadata["thread_id"], "thread_chat_test")
        self.assertEqual(result.tool_calls, [])

    def test_session_routes_live_codex_non_calendar_turn_to_conversation_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            session.runtime_mode = "live_codex"
            session.planner = LiveCodexToolPlanner(runtime=CodexToolRuntime(kernel=SwiftKernelStub()), client=FakeLiveCodexClient())

            state = session.create_plan("hello metadata check")

        assistant = state["chat"]["messages"][-1]
        metadata = assistant["metadata"]
        self.assertEqual(assistant["title"], "Codex answered")
        self.assertEqual(metadata["response_source"], "live_codex_conversation")
        self.assertTrue(metadata["model_reached"])
        self.assertEqual(metadata["model_metadata"]["response_id"], "turn_chat_test")
        self.assertEqual(metadata["conversation_route"], "metadata")
        self.assertEqual(metadata["tool_call_count"], 0)
        self.assertEqual(state["summary"]["latest_turn"]["metadata"]["response_source"], "live_codex_conversation")

    def test_auto_runtime_routes_first_smalltalk_turn_to_live_codex(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {
            "CALENDAR_PILOT_RUNTIME_MODE": "auto",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
        }):
            session = DogfoodSessionState(run_dir=Path(td))
            session.planner = LiveCodexToolPlanner(runtime=session.runtime, client=FakeLiveCodexClient())

            state = session.create_plan("hello")

        assistant = state["chat"]["messages"][-1]
        metadata = assistant["metadata"]
        self.assertEqual(state["runtime"]["runtime_mode"], "auto")
        self.assertEqual(assistant["title"], "Codex answered")
        self.assertEqual(metadata["response_source"], "live_codex_conversation")
        self.assertTrue(metadata["model_reached"])
        self.assertEqual(metadata["model_metadata"]["response_id"], "turn_chat_test")

    def test_smalltalk_runtime_context_hides_absent_optional_credentials(self) -> None:
        report = {
            "runtime_mode": "auto",
            "requested_runtime_mode": "auto",
            "mode_label": "Auto assistant",
            "backends": {
                "codex": "live_codex_app_server",
                "diffusiongemma": "heuristic_diffusiongemma_policy",
                "kernel": "SwiftKernelIPCClient",
                "provider": "deterministic_fixture_provider",
            },
            "live_blockers": [],
            "setup_notes": [
                "DiffusionGemma is running in local heuristic policy mode for auto runtime",
                "Calendar provider is running through the deterministic local adapter for auto runtime",
            ],
            "credentials": {
                "codex_subscription": {"configured": True, "required": True, "status": "configured", "auth_method": "chatgpt", "source": "auth_cache"},
                "diffusiongemma_nim": {"configured": False, "required": False, "status": "missing_credential", "source": "missing"},
                "provider_oauth": {"configured": False, "required": False, "status": "missing_credential", "source": "missing"},
            },
        }

        smalltalk = _conversation_runtime_context(report, include_diagnostics=False)
        metadata = _conversation_runtime_context(report, include_diagnostics=True)

        self.assertEqual(smalltalk["credentials"], {
            "codex_subscription": {
                "configured": True,
                "required": True,
                "status": "configured",
                "auth_method": "chatgpt",
                "source": "auth_cache",
            }
        })
        self.assertEqual(smalltalk["setup_notes"], [])
        self.assertIn("diffusiongemma_nim", metadata["credentials"])
        self.assertTrue(metadata["setup_notes"])

    def test_session_executes_live_codex_conversation_tool_calls(self) -> None:
        tool_calls = [
            ModelPlannedCall(
                CodexToolName.QUERY_REPLAY_TRACE,
                {},
                0,
                "Inspect replay evidence before answering.",
                "trace_chat_replay",
            )
        ]
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            session.runtime_mode = "live_codex"
            session.planner = LiveCodexToolPlanner(
                runtime=session.runtime,
                client=FakeLiveCodexClient(chat_tool_calls=tool_calls),
            )

            state = session.create_plan("show replay metadata")

        assistant = state["chat"]["messages"][-1]
        metadata = assistant["metadata"]
        self.assertEqual(assistant["title"], "Codex answered with evidence")
        self.assertEqual(metadata["response_source"], "live_codex_conversation")
        self.assertTrue(metadata["model_reached"])
        self.assertEqual(metadata["tool_sequence"], [CodexToolName.QUERY_REPLAY_TRACE.value])
        self.assertEqual(metadata["tool_call_count"], 1)
        self.assertEqual(metadata["conversation_tool_receipt_count"], 1)
        self.assertEqual(assistant["cards"][0]["type"], "receipt")
        self.assertEqual(assistant["cards"][0]["receipt"]["tool_name"], CodexToolName.QUERY_REPLAY_TRACE.value)
        self.assertEqual(assistant["cards"][0]["receipt"]["status"], CodexToolStatus.SUCCEEDED.value)
        self.assertGreaterEqual(state["inspector"]["replay"]["summary"]["records"], 2)

    def test_conversation_output_schema_requires_tool_calls(self) -> None:
        schema = CodexAppServerClient._conversation_output_schema()

        self.assertIn("tool_calls", schema["required"])
        tool_names = schema["properties"]["tool_calls"]["items"]["properties"]["tool_name"]["enum"]
        self.assertIn(CodexToolName.QUERY_REPLAY_TRACE.value, tool_names)
        self.assertIn(CodexToolName.RUN_SELF_PLAY_PROBE.value, tool_names)
        self.assertIn(CodexToolName.REQUEST_UNDO.value, tool_names)
        self.assertIn(CodexToolName.APPLY_PROFILE_PATCH.value, tool_names)
        self.assertIn(CodexToolName.PROPOSE_AUTONOMY_SCOPE.value, tool_names)

    def test_session_labels_failed_live_codex_chat_as_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            session.runtime_mode = "live_codex"
            session.planner = LiveCodexToolPlanner(runtime=CodexToolRuntime(kernel=SwiftKernelStub()), client=MissingSubscriptionClient())

            state = session.create_plan("hello metadata check")

        assistant = state["chat"]["messages"][-1]
        metadata = assistant["metadata"]
        self.assertEqual(assistant["title"], "Codex unavailable")
        self.assertEqual(metadata["response_source"], "live_codex_unavailable")
        self.assertFalse(metadata["model_reached"])
        self.assertEqual(metadata["error_category"], "missing_or_invalid_credential")

    def test_invalid_model_plan_is_rejected_as_failed_validation_receipt(self) -> None:
        invalid_calls = [
            ModelPlannedCall(CodexToolName.SIMULATE_ACTION_PROGRAM, {"candidate_ref": "winner"}, 3, "Invalid order.", "trace_bad")
        ]
        replay = ReplayBuffer()
        planner = LiveCodexToolPlanner(runtime=CodexToolRuntime(replay=replay), client=FakeLiveCodexClient(invalid_calls))
        plan = planner.plan_goal("Make next week less chaotic", load_obs(), load_bio(), authority_tier=3, commit=False)

        self.assertEqual(plan.recommended_next_action, "live_codex_unavailable")
        self.assertEqual(plan.receipts[-1].tool_name, CodexToolName.VALIDATE_MODEL_PLAN)
        self.assertEqual(plan.receipts[-1].status, CodexToolStatus.FAILED)
        self.assertEqual(plan.receipts[-1].output["error_category"], "model_tool_schema_failure")
        self.assertEqual([record.record_type for record in replay.records[-2:]], ["codex_tool_call", "codex_tool_receipt"])

    def test_session_labels_failed_live_codex_plan_as_unavailable(self) -> None:
        invalid_calls = [
            ModelPlannedCall(CodexToolName.SIMULATE_ACTION_PROGRAM, {"candidate_ref": "winner"}, 3, "Invalid order.", "trace_bad")
        ]
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            session.runtime_mode = "live_codex"
            session.planner = LiveCodexToolPlanner(runtime=CodexToolRuntime(kernel=SwiftKernelStub()), client=FakeLiveCodexClient(invalid_calls))

            state = session.create_plan("Make next week less chaotic")

        assistant = state["chat"]["messages"][-1]
        metadata = assistant["metadata"]
        self.assertEqual(assistant["title"], "Codex plan unavailable")
        self.assertTrue(metadata["plan_failed"])
        self.assertEqual(metadata["plan_failure_category"], "model_tool_schema_failure")
        self.assertEqual(metadata["recommended_next_action"], "live_codex_unavailable")
        self.assertFalse(metadata["model_reached"])

    def test_terminal_commit_plan_is_validated_before_any_execution(self) -> None:
        invalid_calls = [
            ModelPlannedCall(CodexToolName.INSPECT_WEEK, {"goal": "Make next week less chaotic"}, 3, "Inspect.", "trace_inspect"),
            ModelPlannedCall(CodexToolName.GENERATE_CANDIDATE_FRONTIER, {"goal": "Make next week less chaotic"}, 3, "Generate.", "trace_frontier"),
            ModelPlannedCall(CodexToolName.COMPARE_CANDIDATES, {}, 3, "Compare.", "trace_compare"),
            ModelPlannedCall(CodexToolName.REQUEST_COMMIT, {"candidate_ref": "winner"}, 3, "Commit.", "trace_commit"),
            ModelPlannedCall(CodexToolName.SIMULATE_ACTION_PROGRAM, {"candidate_ref": "winner"}, 3, "Invalid after commit.", "trace_late"),
        ]
        replay = ReplayBuffer()
        planner = LiveCodexToolPlanner(runtime=CodexToolRuntime(replay=replay), client=FakeLiveCodexClient(invalid_calls))
        plan = planner.plan_goal("Make next week less chaotic", load_obs(), load_bio(), authority_tier=3, commit=True)

        self.assertEqual(plan.recommended_next_action, "live_codex_unavailable")
        self.assertEqual(plan.receipts[-1].tool_name, CodexToolName.VALIDATE_MODEL_PLAN)
        replayed_calls = [
            record.payload.get("call", {}).get("tool_name")
            for record in replay.records
            if record.record_type == "codex_tool_call"
        ]
        self.assertEqual(replayed_calls, [CodexToolName.VALIDATE_MODEL_PLAN.value])

    def test_missing_codex_subscription_degrades_live_codex_plan_without_secret_output(self) -> None:
        planner = LiveCodexToolPlanner(runtime=CodexToolRuntime(), client=MissingSubscriptionClient())
        plan = planner.plan_goal("Make next week less chaotic", load_obs(), load_bio(), authority_tier=3, commit=False)

        self.assertEqual(plan.recommended_next_action, "live_codex_unavailable")
        self.assertEqual(plan.receipts[-1].output["error_category"], "missing_or_invalid_credential")
        self.assertNotIn("CODEX_ACCESS_TOKEN=", json.dumps(plan.to_dict()))

    def test_live_codex_runtime_reports_missing_credential_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {
            "CALENDAR_PILOT_RUNTIME_MODE": "live_codex",
            "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
            "CALENDAR_PILOT_CODEX_AUTH_FILE": str(Path(td) / "missing_auth.json"),
            "CODEX_ACCESS_TOKEN": "",
        }):
            session = DogfoodSessionState(run_dir=Path(td))
            report = session.runtime_report()

        self.assertEqual(report["runtime_mode"], "live_codex")
        self.assertEqual(report["backends"]["codex"], "live_codex_app_server")
        self.assertFalse(runtime_is_release_safe(report))
        self.assertIn("required credential missing: codex_subscription", report["live_blockers"])
        self.assertEqual(report["codex_health"]["status"], "missing_credential")

    def test_codex_app_server_health_distinguishes_remote_failure_categories(self) -> None:
        self.assertEqual(RemoteHealthClient(None).health_status(validate_remote=True)["status"], "ok")
        self.assertEqual(
            RemoteHealthClient(LiveCodexCredentialError("bad auth")).health_status(validate_remote=True)["status"],
            "invalid_credential",
        )
        self.assertEqual(
            RemoteHealthClient(LiveCodexNetworkError("dns")).health_status(validate_remote=True)["status"],
            "network_failure",
        )
        self.assertEqual(
            RemoteHealthClient(LiveCodexRuntimeError("app server failed")).health_status(validate_remote=True)["status"],
            "codex_app_server_failure",
        )

    def test_app_server_wait_accepts_completed_agent_message_without_turn_completed(self) -> None:
        rpc = CodexAppServerRPC("/bin/echo", timeout_seconds=1)
        messages = iter([
            {
                "method": "item/agentMessage/delta",
                "params": {"itemId": "msg_test", "delta": "{\"calls\":[]}"},
            },
            {
                "method": "item/completed",
                "params": {"item": {"type": "agentMessage", "id": "msg_test", "text": "{\"calls\":[]}"}},
            },
        ])
        rpc.read_message = lambda *, timeout: next(messages)  # type: ignore[method-assign]

        self.assertEqual(rpc.wait_for_turn(thread_id="thread", turn_id="turn"), "{\"calls\":[]}")


if __name__ == "__main__":
    unittest.main()