

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.providers.deterministic import ProviderMutationResult
from calendar_pilot.types import CodexToolName, CodexToolReceipt, CodexToolStatus


class FrontendSessionPersistenceTests(unittest.TestCase):
    def test_non_calendar_message_stays_local_and_exposes_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            snapshot = session.create_plan("hello")

            self.assertEqual(snapshot["summary"]["plan_id"], "plan_empty")
            self.assertFalse(snapshot["chat"]["candidate_cards"])
            self.assertEqual(snapshot["inspector"]["replay"]["summary"]["records"], 1)
            self.assertEqual(snapshot["inspector"]["replay"]["summary"].get("router_decisions", 0), 1)
            assistant = snapshot["chat"]["messages"][-1]
            self.assertEqual(assistant["title"], "Conversation handled locally")
            self.assertIn("metadata", assistant)
            metadata = assistant["metadata"]
            self.assertEqual(metadata["intent"], "smalltalk")
            self.assertEqual(metadata["response_source"], "local_intent_router")
            self.assertFalse(metadata["model_reached"])
            self.assertEqual(metadata["planner_backend"], "deterministic_codex_tool_planner")
            self.assertEqual(metadata["tool_sequence"], [])
            self.assertIn("response_id", metadata["missing_model_metadata"])

    def test_ready_message_exposes_runtime_backends(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            snapshot = session.snapshot()

            first = snapshot["chat"]["messages"][0]
            metadata = first["metadata"]
            self.assertEqual(first["title"], "CalendarPilot is ready")
            self.assertEqual(metadata["response_source"], "ready_assistant_runtime")
            self.assertTrue(metadata["assistant_ready"])
            self.assertEqual(metadata["planner_backend"], "deterministic_codex_tool_planner")
            self.assertEqual(metadata["kernel_backend"], "SwiftKernelStub")

    def test_composer_routes_local_operational_tools(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))

            replay_state = session.create_plan("show replay trace")
            replay = replay_state["chat"]["messages"][-1]
            self.assertEqual(replay["metadata"]["response_source"], "local_conversation_tools")
            self.assertEqual(replay["metadata"]["tool_sequence"], ["query_replay_trace"])
            self.assertEqual(replay["cards"][0]["receipt"]["tool_name"], "query_replay_trace")

            profile_state = session.create_plan("repair my profile: I prefer planning blocks before lunch")
            profile = profile_state["chat"]["messages"][-1]
            self.assertEqual(profile["metadata"]["tool_sequence"], ["propose_profile_patch"])
            self.assertTrue(profile["cards"][0]["receipt"]["requires_user_confirmation"])
            self.assertTrue(profile_state["inspector"]["profile"]["patch_history"])

            self_play_state = session.create_plan("run self-play 2")
            self_play = self_play_state["chat"]["messages"][-1]
            self.assertEqual(self_play["metadata"]["tool_sequence"], ["run_self_play_probe"])
            self.assertTrue(self_play_state["inspector"]["self_play"]["history"])

            denial_state = session.create_plan("explain the denial")
            denial = denial_state["chat"]["messages"][-1]
            self.assertEqual(denial["metadata"]["tool_sequence"], ["explain_swift_denial"])
            self.assertTrue(denial_state["inspector"]["denials"])

    def test_composer_denial_explanation_uses_latest_real_swift_denial(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            session.denial_history.append({
                "candidate_id": "cand_denied",
                "denied_reason": "required authority tier exceeds Swift-issued grant",
                "receipt": {"status": "denied", "denied_reason": "required authority tier exceeds Swift-issued grant"},
            })

            receipts = session._execute_live_conversation_tools([{
                "tool_name": CodexToolName.EXPLAIN_SWIFT_DENIAL,
                "input": {"denied_reason": "latest denial in current session"},
                "requested_authority_tier": 3,
                "user_visible_reason": "Explain the latest Swift denial.",
                "correlation_id": "live_denial_placeholder",
            }], "explain the denial")

            self.assertIn("granted autonomy tier", receipts[0]["output"]["denial_explanation"])
            self.assertEqual(session.denial_history[-1]["denied_reason"], "required authority tier exceeds Swift-issued grant")

    def test_denied_action_queue_exposes_swift_reason(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            session.update_authority(tier=0, scopes=["recommend"], confirmed=True)

            denied = session.candidate_action(candidate_id, "commit", confirmed=True)

            row = denied["action_queue"][-1]
            self.assertEqual(row["status"], "denied")
            self.assertEqual(row["denied_reason"], "required authority tier exceeds Swift-issued grant")

    def test_failed_frontier_plan_does_not_claim_plan_was_found(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))

            def fail_frontier(call, _observation, _biography):
                if call.tool_name == CodexToolName.GENERATE_CANDIDATE_FRONTIER:
                    return CodexToolReceipt(
                        tool_call_id=call.tool_call_id,
                        tool_name=call.tool_name,
                        status=CodexToolStatus.FAILED,
                        output={
                            "error_category": "model_policy_schema_failure",
                            "message": "NIM frontier JSON response was invalid after 2 attempts",
                            "recovery": "NIM was reached but did not return a valid typed candidate frontier after schema retry.",
                        },
                        denied_reason="NIM frontier JSON response was invalid after 2 attempts",
                    )
                return original_execute(call, _observation, _biography)

            original_execute = session.runtime.execute
            session.runtime.execute = fail_frontier  # type: ignore[method-assign]

            state = session.create_plan("Make next week less chaotic")

            latest = state["chat"]["messages"][-1]
            self.assertEqual(latest["title"], "I could not generate candidate futures")
            self.assertTrue(latest["metadata"]["plan_failed"])
            self.assertEqual(latest["metadata"]["plan_failure_category"], "model_policy_schema_failure")
            self.assertFalse(state["chat"]["candidate_cards"])

    def test_composer_applies_confirmed_profile_patch(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            proposed = session.create_plan("repair my profile: I prefer planning blocks before lunch")
            self.assertEqual(proposed["chat"]["messages"][-1]["metadata"]["tool_sequence"], ["propose_profile_patch"])

            applied = session.create_plan("confirm profile patch")

            latest = applied["chat"]["messages"][-1]
            self.assertEqual(latest["metadata"]["tool_sequence"], ["apply_profile_patch"])
            receipt = latest["cards"][0]["receipt"]
            self.assertEqual(receipt["status"], "succeeded")
            self.assertTrue(applied["inspector"]["profile"]["patch_history"])
            self.assertEqual(applied["inspector"]["profile"]["patch_history"][-1]["kind"], "applied")

    def test_composer_profile_apply_without_proposal_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            before_events = len(session.biography.profile_update_events)

            state = session.create_plan("confirm profile patch")

            latest = state["chat"]["messages"][-1]
            self.assertEqual(latest["metadata"]["tool_sequence"], ["apply_profile_patch"])
            receipt = latest["cards"][0]["receipt"]
            self.assertEqual(receipt["status"], "requires_confirmation")
            self.assertTrue(receipt["requires_user_confirmation"])
            self.assertEqual(len(session.biography.profile_update_events), before_events)
            self.assertEqual(state["inspector"]["profile"]["patch_history"][-1]["kind"], "needs_confirmation")

    def test_composer_profile_apply_after_failed_proposal_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            original_execute = session.runtime.execute

            def fail_profile_propose(call, observation, biography):
                if call.tool_name == CodexToolName.PROPOSE_PROFILE_PATCH:
                    return CodexToolReceipt(
                        tool_call_id=call.tool_call_id,
                        tool_name=call.tool_name,
                        status=CodexToolStatus.FAILED,
                        output={},
                        denied_reason="profile proposal failed",
                    )
                return original_execute(call, observation, biography)

            session.runtime.execute = fail_profile_propose  # type: ignore[method-assign]

            proposed = session.create_plan("repair my profile: I prefer planning blocks before lunch")
            self.assertEqual(proposed["inspector"]["profile"]["patch_history"][-1]["kind"], "proposal_failed")
            before_events = len(session.biography.profile_update_events)

            state = session.create_plan("confirm profile patch")

            latest = state["chat"]["messages"][-1]
            self.assertEqual(latest["metadata"]["tool_sequence"], ["apply_profile_patch"])
            receipt = latest["cards"][0]["receipt"]
            self.assertEqual(receipt["status"], "requires_confirmation")
            self.assertEqual(len(session.biography.profile_update_events), before_events)
            self.assertEqual(state["inspector"]["profile"]["patch_history"][-1]["kind"], "needs_confirmation")

    def test_composer_profile_apply_after_malformed_proposal_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            original_execute = session.runtime.execute

            def malformed_profile_propose(call, observation, biography):
                if call.tool_name == CodexToolName.PROPOSE_PROFILE_PATCH:
                    return CodexToolReceipt(
                        tool_call_id=call.tool_call_id,
                        tool_name=call.tool_name,
                        status=CodexToolStatus.REQUIRES_CONFIRMATION,
                        output={"repair_plan": {"candidate_claim": "deep work", "provenance": {}}},
                        requires_user_confirmation=True,
                    )
                return original_execute(call, observation, biography)

            session.runtime.execute = malformed_profile_propose  # type: ignore[method-assign]

            proposed = session.create_plan("repair my profile: I prefer planning blocks before lunch")
            self.assertEqual(proposed["inspector"]["profile"]["patch_history"][-1]["kind"], "proposal_failed")
            before_events = len(session.biography.profile_update_events)

            state = session.create_plan("confirm profile patch")

            latest = state["chat"]["messages"][-1]
            receipt = latest["cards"][0]["receipt"]
            self.assertEqual(receipt["status"], "requires_confirmation")
            self.assertEqual(len(session.biography.profile_update_events), before_events)
            self.assertEqual(state["inspector"]["profile"]["patch_history"][-1]["kind"], "needs_confirmation")

    def test_composer_proposes_autonomy_scope_for_latest_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            session.create_plan("Make next week less chaotic")

            scoped = session.create_plan("propose autonomy scope for this action")

            latest = next(message for message in reversed(scoped["chat"]["messages"]) if message["title"] == "Assistant handled request")
            self.assertIn("propose_autonomy_scope", latest["metadata"]["tool_sequence"])
            receipt = next(card["receipt"] for card in latest["cards"] if card["receipt"]["tool_name"] == "propose_autonomy_scope")
            self.assertEqual(receipt["status"], "requires_confirmation")
            self.assertIn("scope_proposal", receipt["output"])

    def test_composer_autonomy_scope_without_candidate_reports_failure(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))

            scoped = session.create_plan("propose autonomy scope")

            latest = scoped["chat"]["messages"][-1]
            self.assertIn("could not propose", latest["body"])
            receipt = next(card["receipt"] for card in latest["cards"] if card["receipt"]["tool_name"] == "propose_autonomy_scope")
            self.assertEqual(receipt["status"], "failed")

    def test_failed_composer_self_play_does_not_ship_release_gate(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))

            def fail_execute(call, _observation, _biography):
                return CodexToolReceipt(
                    tool_call_id=call.tool_call_id,
                    tool_name=call.tool_name,
                    status=CodexToolStatus.FAILED,
                    output={"error": "self-play crashed"},
                    denied_reason="self-play crashed",
                )

            session.runtime.execute = fail_execute  # type: ignore[method-assign]

            state = session.create_plan("run self-play 2")

            history = state["inspector"]["self_play"]["history"][-1]
            self.assertEqual(history["release_decision"], "probe_failed")
            self.assertEqual(history["failure_reason"], "self-play crashed")

    def test_composer_routes_local_undo_to_swift_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            committed = session.candidate_action(candidate_id, "commit", confirmed=True)
            rollback = next(action["rollback_handle_id"] for action in committed["action_queue"] if action.get("rollback_handle_id"))

            undone = session.create_plan("undo the last change")

            assistant = next(message for message in reversed(undone["chat"]["messages"]) if message["title"] == "Assistant handled request")
            self.assertEqual(assistant["metadata"]["tool_sequence"], ["request_undo"])
            receipt = assistant["cards"][0]["receipt"]
            self.assertEqual(receipt["tool_name"], "request_undo")
            self.assertEqual(receipt["status"], "reverted")
            swift = receipt["output"]["swift_receipt"]
            self.assertEqual(swift["rollback_handle_id"], rollback)
            self.assertEqual(swift["sync_status"], "reverted")
            self.assertEqual(assistant["metadata"]["conversation_tool_receipts"][0]["status"], "reverted")
            self.assertEqual(assistant["metadata"]["conversation_tool_receipts"][0]["sync_status"], "reverted")
            self.assertTrue(assistant["metadata"]["conversation_tool_receipts"][0]["rollback_verified"])
            self.assertEqual(undone["action_queue"][-1]["status"], "reverted")
            self.assertFalse([action for action in undone["action_queue"] if action["status"] == "committed" and action.get("rollback_handle_id") == rollback])

    def test_failed_provider_rollback_keeps_committed_action_visible(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            committed = session.candidate_action(candidate_id, "commit", confirmed=True)
            rollback = next(action["rollback_handle_id"] for action in committed["action_queue"] if action.get("rollback_handle_id"))

            def unverified_rollback(rollback_handle_id: str) -> ProviderMutationResult:
                return ProviderMutationResult(
                    provider_id="deterministic_fixture_provider",
                    status="rollback_unverified",
                    idempotency_key="idem_unverified",
                    rollback_handle_id=rollback_handle_id,
                    rollback_verified=False,
                )

            session.provider.rollback = unverified_rollback  # type: ignore[method-assign]

            undone = session.create_plan("undo the last change")

            assistant = next(message for message in reversed(undone["chat"]["messages"]) if message["title"] == "Assistant handled request")
            receipt = assistant["cards"][0]["receipt"]
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(receipt["denied_reason"], "provider_rollback_not_verified")
            self.assertEqual(receipt["output"]["swift_receipt"]["sync_status"], "reverted")
            self.assertFalse(receipt["output"]["provider_rollback"]["rollback_verified"])
            self.assertTrue([action for action in undone["action_queue"] if action["status"] == "committed" and action.get("rollback_handle_id") == rollback])
            failed = [action for action in undone["action_queue"] if action["status"] == "failed" and action.get("rollback_handle_id") == rollback]
            self.assertEqual(failed[-1]["label"], "Rollback needs review")
            self.assertIn("provider verification failed", failed[-1]["why_user_sees_it"])

    def test_composer_routes_bare_undo_to_swift_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            committed = session.candidate_action(candidate_id, "commit", confirmed=True)
            rollback = next(action["rollback_handle_id"] for action in committed["action_queue"] if action.get("rollback_handle_id"))

            undone = session.create_plan("undo")

            assistant = next(message for message in reversed(undone["chat"]["messages"]) if message["title"] == "Assistant handled request")
            self.assertEqual(assistant["metadata"]["tool_sequence"], ["request_undo"])
            self.assertEqual(assistant["cards"][0]["receipt"]["status"], "reverted")
            swift = assistant["cards"][0]["receipt"]["output"]["swift_receipt"]
            self.assertEqual(swift["rollback_handle_id"], rollback)
            self.assertEqual(swift["sync_status"], "reverted")
            self.assertEqual(undone["action_queue"][-1]["status"], "reverted")

    def test_feedback_turn_exposes_latest_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            committed = session.candidate_action(candidate_id, "commit", confirmed=True)
            receipt_id = next(action["receipt_id"] for action in committed["action_queue"] if action.get("receipt_id"))

            state = session.feedback(receipt_id, "useful", reason="metadata regression")

            metadata = state["summary"]["latest_turn"]["metadata"]
            self.assertEqual(metadata["response_source"], "ui_feedback")
            self.assertEqual(metadata["receipt_id"], receipt_id)
            self.assertEqual(metadata["feedback"], "useful")
            self.assertTrue(metadata["reward_attached_to_existing_receipt"])

    def test_calendar_plan_message_exposes_deterministic_planner_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            snapshot = session.create_plan("Make next week less chaotic")

            assistant = next(message for message in reversed(snapshot["chat"]["messages"]) if message["title"] == "I found a plan")
            metadata = assistant["metadata"]
            self.assertEqual(metadata["intent"], "calendar_goal")
            self.assertEqual(metadata["response_source"], "planner")
            self.assertFalse(metadata["model_reached"])
            self.assertEqual(metadata["planner_backend"], "deterministic_codex_tool_planner")
            self.assertGreater(metadata["tool_call_count"], 0)
            self.assertIn("generate_candidate_frontier", metadata["tool_sequence"])
            self.assertIn("No live LLM metadata", assistant["body"])

    def test_mixed_calendar_and_operational_turn_plans_and_attaches_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))

            snapshot = session.create_plan("Make next week less chaotic and show replay trace")

            assistant = next(message for message in reversed(snapshot["chat"]["messages"]) if message["title"] == "I found a plan")
            metadata = assistant["metadata"]
            self.assertEqual(metadata["intent"], "mixed_calendar_operational")
            self.assertEqual(metadata["response_source"], "planner")
            self.assertIn("generate_candidate_frontier", metadata["planner_tool_sequence"])
            self.assertEqual(metadata["conversation_tool_sequence"], ["query_replay_trace"])
            self.assertIn("generate_candidate_frontier", metadata["tool_sequence"])
            self.assertIn("query_replay_trace", metadata["tool_sequence"])
            self.assertTrue(snapshot["chat"]["candidate_cards"])
            receipts = [card["receipt"] for card in assistant["cards"] if card.get("type") == "receipt"]
            self.assertEqual(receipts[0]["tool_name"], "query_replay_trace")

    def test_mixed_calendar_and_undo_turn_still_plans_and_requests_undo(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            session.candidate_action(candidate_id, "commit", confirmed=True)

            snapshot = session.create_plan("Make next week less chaotic and undo it")

            assistant = next(message for message in reversed(snapshot["chat"]["messages"]) if message["title"] == "I found a plan")
            metadata = assistant["metadata"]
            self.assertEqual(metadata["intent"], "mixed_calendar_operational")
            self.assertIn("generate_candidate_frontier", metadata["planner_tool_sequence"])
            self.assertEqual(metadata["conversation_tool_sequence"], ["request_undo"])
            self.assertTrue(snapshot["chat"]["candidate_cards"])
            receipts = [card["receipt"] for card in assistant["cards"] if card.get("type") == "receipt"]
            self.assertEqual(receipts[0]["tool_name"], "request_undo")
            self.assertEqual(snapshot["action_queue"][-1]["status"], "reverted")

    def test_mixed_calendar_and_profile_repair_turn_still_plans_and_proposes_patch(self):
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))

            snapshot = session.create_plan("Move prep before tomorrow meeting and repair my profile: I prefer morning prep")

            assistant = next(message for message in reversed(snapshot["chat"]["messages"]) if message["title"] == "I found a plan")
            metadata = assistant["metadata"]
            self.assertEqual(metadata["intent"], "mixed_calendar_operational")
            self.assertIn("generate_candidate_frontier", metadata["planner_tool_sequence"])
            self.assertEqual(metadata["conversation_tool_sequence"], ["propose_profile_patch"])
            self.assertTrue(snapshot["chat"]["candidate_cards"])
            receipts = [card["receipt"] for card in assistant["cards"] if card.get("type") == "receipt"]
            self.assertEqual(receipts[0]["tool_name"], "propose_profile_patch")
            self.assertEqual(snapshot["inspector"]["profile"]["patch_history"][-1]["kind"], "proposed")

    def test_session_reload_restores_visible_state_replay_frontier_and_undo(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            committed = session.candidate_action(candidate_id, "commit", confirmed=True)
            rollback = next(action["rollback_handle_id"] for action in committed["action_queue"] if action.get("rollback_handle_id"))
            receipt_id = next(action["receipt_id"] for action in committed["action_queue"] if action.get("rollback_handle_id") == rollback)
            session.feedback(receipt_id, "useful", reason="dogfood restart check")
            session.propose_profile_patch("I prefer planning blocks before lunch.")
            session.apply_profile_patch("planning blocks", "Prefer planning blocks before lunch.", confirmed=True)
            session.explain_denial("required authority tier exceeds Swift-issued grant")
            session.run_self_play(episodes=1)
            session.update_authority(tier=2, scopes=["recommend", "stage", "undo"], confirmed=True)

            reloaded = DogfoodSessionState(run_dir=run_dir)
            snapshot = reloaded.snapshot()

            self.assertEqual(snapshot["session"]["session_id"], session.session_id)
            self.assertTrue(snapshot["chat"]["candidate_cards"])
            self.assertGreaterEqual(snapshot["inspector"]["replay"]["summary"]["records"], 1)
            self.assertGreaterEqual(snapshot["inspector"]["replay"]["summary"]["rewards"], 1)
            self.assertTrue(snapshot["inspector"]["feedback"])
            self.assertTrue(snapshot["inspector"]["profile"]["patch_history"])
            self.assertTrue(snapshot["inspector"]["self_play"]["history"])
            self.assertTrue(snapshot["inspector"]["denials"])
            self.assertEqual(snapshot["session"]["authority_tier"], 2)
            self.assertEqual(snapshot["session"]["authority_scopes"], ["recommend", "stage", "undo"])
            self.assertTrue(snapshot["inspector"]["authority"]["history"])
            self.assertIn(rollback, reloaded.kernel.undo_ledger)
            self.assertIn(candidate_id, reloaded.runtime.frontier)

            undone = reloaded.undo(rollback)
            latest = undone["action_queue"][-1]
            self.assertEqual(latest["status"], "reverted")
            self.assertEqual(latest["rollback_handle_id"], rollback)
            self.assertFalse([action for action in undone["action_queue"] if action["status"] == "committed" and action.get("rollback_handle_id") == rollback])
            reverted = [record.payload.get("receipt", {}) for record in reloaded.replay.records if record.payload.get("receipt", {}).get("rollback_handle_id") == rollback]
            self.assertEqual(reverted[-1]["sync_status"], "reverted")
            self.assertNotIn(rollback, reloaded.kernel.undo_ledger)

    def test_reset_persists_clean_state_for_next_launch(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            planned = session.create_plan("Make next week less chaotic")
            candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
            session.candidate_action(candidate_id, "stage")
            self.assertGreater(session.replay.summarize().records, 0)

            session.reset()
            reloaded = DogfoodSessionState(run_dir=run_dir)
            snapshot = reloaded.snapshot()

            self.assertEqual(snapshot["inspector"]["replay"]["summary"]["records"], 0)
            self.assertEqual(snapshot["inspector"]["replay"]["summary"].get("router_decisions", 0), 0)
            self.assertFalse(snapshot["chat"]["candidate_cards"])
            self.assertEqual(len(reloaded.kernel.undo_ledger), 0)
            self.assertEqual(snapshot["session"]["authority_tier"], 3)
            self.assertEqual(snapshot["session"]["authority_scopes"], ["recommend", "stage", "commit_private", "undo"])
            self.assertIn("Reset complete", snapshot["chat"]["messages"][0]["title"])

    def test_launch_manifest_persists_runtime_health(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            session.create_plan("hello")

            manifest = json.loads((run_dir / "launch_state.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["status"], "running")
            self.assertEqual(manifest["health"]["runtime_mode"], "fixture")
            self.assertEqual(manifest["health"]["backends"]["codex"], "deterministic_codex_tool_planner")

            reloaded = DogfoodSessionState(run_dir=run_dir)
            restored_manifest = json.loads((run_dir / "launch_state.json").read_text(encoding="utf-8"))

            self.assertEqual(restored_manifest["health"]["runtime_mode"], reloaded.runtime_report()["runtime_mode"])
            self.assertEqual(restored_manifest["health"]["backends"]["kernel"], "SwiftKernelStub")

    def test_restored_runtime_refreshes_launch_manifest_runtime_mode(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            session.runtime_mode = "live_codex"
            session.persist()
            session.close()

            reloaded = DogfoodSessionState(run_dir=run_dir)
            restored_manifest = json.loads((run_dir / "launch_state.json").read_text(encoding="utf-8"))

            self.assertEqual(reloaded.runtime_report()["runtime_mode"], "live_codex")
            self.assertEqual(restored_manifest["runtime_mode"], "live_codex")
            self.assertEqual(restored_manifest["health"]["runtime_mode"], "live_codex")
            reloaded.close()

    def test_corrupt_session_state_recovers_with_visible_restore_error(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "session_state.json").write_text("{not valid json", encoding="utf-8")

            session = DogfoodSessionState(run_dir=run_dir)
            snapshot = session.snapshot()

            self.assertIn("failed to restore session_state.json", snapshot["session"]["restore_error"])
            self.assertEqual(snapshot["chat"]["messages"][0]["title"], "Session restore failed")
            self.assertTrue((run_dir / "session_state.json").exists())


if __name__ == "__main__":
    unittest.main()
