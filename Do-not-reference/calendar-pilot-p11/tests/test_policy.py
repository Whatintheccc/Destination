

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, LiveDiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.live import (
    LiveDiffusionGemmaCredentialError,
    LiveDiffusionGemmaSchemaError,
    NIMFrontierResult,
    NIMPolicyRank,
    NIMPolicyResult,
    NvidiaNIMPolicyClient,
)
from calendar_pilot.types import CodexToolCall, CodexToolName, PolicyTuning, RawCalendarObservation, UserBiography, RightMomentDecision

ROOT = Path(__file__).resolve().parents[1]


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        self.biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))

    def test_generates_prep_candidate(self):
        candidates = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)
        intents = {c.intent for c in candidates}
        self.assertIn("create_prep_block", intents)
        self.assertGreater(candidates[0].expected_reward, 0)

    def test_right_moment_has_decision(self):
        candidates = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)
        self.assertIsInstance(candidates[0].right_moment_decision, RightMomentDecision)

    def test_live_diffusiongemma_policy_ranks_validated_local_candidates(self):
        policy = LiveDiffusionGemmaPolicy(client=FakeNIMClient())
        candidates = policy.generate_candidates(self.observation, self.biography)

        self.assertTrue(candidates)
        self.assertIn("policy_backend=nvidia_nim_diffusiongemma_policy", candidates[0].control_notes)
        self.assertIn("nim_policy_delta", candidates[0].reward_breakdown)
        self.assertTrue(any(story.startswith("NIM policy:") for story in candidates[0].model_story))
        metadata = policy.policy_metadata_for_candidate(candidates[0].candidate_id)
        self.assertEqual(metadata["backend"], "nvidia_nim_diffusiongemma_policy")
        self.assertEqual(metadata["prompt_version"], "calendar_pilot_nim_policy_ranker_v1")
        self.assertEqual(metadata["fallback_state"], "none")
        self.assertIn("decoding_settings", metadata)

    def test_live_policy_replay_records_structured_nim_metadata(self):
        runtime = CodexToolRuntime(policy=LiveDiffusionGemmaPolicy(client=FakeNIMClient()))
        receipt = runtime.execute(
            CodexToolCall(
                tool_call_id="tool_frontier",
                tool_name=CodexToolName.GENERATE_CANDIDATE_FRONTIER,
                input={"limit": 3},
                correlation_id="plan_live_policy",
            ),
            self.observation,
            self.biography,
        )
        self.assertEqual(receipt.status.value, "succeeded")
        decisions = [record for record in runtime.replay.records if record.record_type == "decision"]
        self.assertTrue(decisions)
        metadata = decisions[0].payload["policy_metadata"]
        self.assertEqual(metadata["backend"], "nvidia_nim_diffusiongemma_policy")
        self.assertEqual(metadata["model"], "google/diffusiongemma-26b-a4b-it")
        self.assertIn("retry_policy", metadata)
        self.assertIn("validation", metadata)
        self.assertEqual(decisions[0].trace_id, "plan_live_policy")


    def test_live_diffusiongemma_policy_can_generate_candidate_frontier_directly(self):
        policy = LiveDiffusionGemmaPolicy(client=FakeNIMGeneratorClient())
        candidates = policy.generate_candidates(self.observation, self.biography)

        self.assertTrue(candidates)
        self.assertIn("nim_generation=typed_candidate_frontier", candidates[0].control_notes)
        metadata = policy.policy_metadata_for_candidate(candidates[0].candidate_id)
        self.assertEqual(metadata["mode"], "model_generated_candidate_frontier")
        self.assertEqual(metadata["fallback_state"], "model_generated_frontier")
        self.assertEqual(metadata["prompt_version"], "calendar_pilot_nim_frontier_generator_v2")

    def test_live_diffusiongemma_policy_forwards_user_goal_to_nim_generator(self):
        client = GoalCaptureNIMGeneratorClient()
        policy = LiveDiffusionGemmaPolicy(client=client)

        policy.generate_candidates(self.observation, self.biography, goal="Move prep before tomorrow's meeting")

        self.assertEqual(client.last_goal, "Move prep before tomorrow's meeting")

    def test_live_diffusiongemma_policy_uses_bounded_default_frontier_limit(self):
        client = GoalCaptureNIMGeneratorClient()
        policy = LiveDiffusionGemmaPolicy(client=client)

        policy.generate_candidates(self.observation, self.biography)

        self.assertEqual(client.last_limit, 4)

    def test_live_nim_frontier_prompt_serializes_observation_contract(self):
        client = NvidiaNIMPolicyClient(api_key="test-key", timeout_seconds=1)

        prompt = client._frontier_prompt("Make next week less chaotic", self.observation, self.biography, limit=2)
        payload = json.loads(prompt)

        self.assertEqual(payload["observation"]["observation_id"], self.observation.observation_id)
        self.assertEqual(payload["observation"]["events"][0]["event_id"], self.observation.events[0].event_id)
        self.assertEqual(payload["biography"]["user_scope_id"], self.biography.user_scope_id)

    def test_nim_frontier_parser_normalizes_common_model_schema_drift(self):
        candidate = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[0].to_dict()
        candidate["candidate_id"] = "nim_drift_candidate"
        candidate["reversibility"] = True
        candidate["target_calendars"] = []
        candidate["right_moment_decision"] = 0.85
        candidate["reward_breakdown"] = "high utility, low regret"
        candidate["simulated_outcomes"] = "no conflict"
        candidate["model_story"] = "Generated by NIM."
        candidate["actions"][0]["type"] = candidate["actions"][0].pop("action_type")
        text = json.dumps({"policy_summary": "drift", "candidates": [candidate]})

        parsed = NvidiaNIMPolicyClient._parse_frontier_payload(text, self.observation, limit=1)

        self.assertEqual(parsed["candidates"][0].reversibility.value, "high")
        self.assertEqual(parsed["candidates"][0].right_moment_decision.value, "auto_write_then_notify")
        self.assertIn("normalized_reversibility_bool:0", parsed["validation_errors"])
        self.assertIn("normalized_action_type_alias:0:0", parsed["validation_errors"])
        self.assertIn("normalized_right_moment_number:0", parsed["validation_errors"])
        self.assertIn("normalized_non_dict_map:0:reward_breakdown", parsed["validation_errors"])
        self.assertIn("normalized_non_dict_map:0:simulated_outcomes", parsed["validation_errors"])
        self.assertIn("normalized_string_list:0:model_story", parsed["validation_errors"])

    def test_nim_frontier_parser_normalizes_move_action_new_time_aliases(self):
        candidate = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[0].to_dict()
        candidate["candidate_id"] = "nim_move_alias_candidate"
        candidate["intent"] = "create_prep_block"
        candidate["actions"] = [
            {
                "type": "move_event",
                "event_id": self.observation.events[0].event_id,
                "calendar_id": self.observation.events[0].calendar_id,
                "new_start": "2026-07-01T14:00:00-07:00",
                "new_end": "2026-07-01T14:30:00-07:00",
            },
            {
                "type": "create_event",
                "title": "Prepare renewal notes",
                "start": "2026-07-01T14:30:00-07:00",
                "end": "2026-07-01T15:00:00-07:00",
                "calendar_id": "work",
                "notes": "Prep for Client renewal call",
            },
        ]
        candidate["model_story"] = "NIM generated this candidate."
        candidate["control_notes"] = "Move a flexible admin event before creating prep."
        candidate["simulated_outcomes"] = [
            "User feels prepared.",
            "No scheduling conflicts created.",
        ]
        text = json.dumps({"policy_summary": "move aliases", "candidates": [candidate]})

        parsed = NvidiaNIMPolicyClient._parse_frontier_payload(text, self.observation, limit=1)

        self.assertEqual(parsed["candidates"][0].candidate_id, "nim_move_alias_candidate")
        self.assertEqual(parsed["candidates"][0].actions[0].start.isoformat(), "2026-07-01T14:00:00-07:00")
        self.assertEqual(parsed["candidates"][0].actions[0].end.isoformat(), "2026-07-01T14:30:00-07:00")
        self.assertEqual(parsed["candidates"][0].actions[1].metadata["notes"], "Prep for Client renewal call")
        self.assertIn("normalized_action_new_start_alias:0:0", parsed["validation_errors"])
        self.assertIn("normalized_action_new_end_alias:0:0", parsed["validation_errors"])
        self.assertIn("normalized_action_metadata_aliases:0:1", parsed["validation_errors"])

    def test_nim_frontier_parser_normalizes_nested_action_params(self):
        candidate = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[0].to_dict()
        candidate["candidate_id"] = "nim_nested_params_candidate"
        candidate["intent"] = "create_prep_block"
        candidate["actions"] = [
            {
                "type": "create_event",
                "params": {
                    "title": "Prep: Client renewal",
                    "start": "2026-07-01T14:30:00-07:00",
                    "end": "2026-07-01T15:00:00-07:00",
                    "calendar_id": "work",
                    "notes": "Prepare renewal notes for upcoming client call.",
                },
            },
            {
                "type": "move_event",
                "params": {
                    "event_id": self.observation.events[0].event_id,
                    "new_start": "2026-07-01T16:00:00-07:00",
                    "new_end": "2026-07-01T16:30:00-07:00",
                },
            },
            {
                "type": "batch_tasks",
                "params": {
                    "task_ids": ["task_renewal_prep", "task_expense"],
                    "target_time": "2026-07-04T14:00:00-07:00",
                },
            },
        ]
        candidate["model_story"] = "NIM generated nested params."
        candidate["control_notes"] = "Nested params should remain visibly repaired."
        candidate["simulated_outcomes"] = [{"outcome": "Prepared", "probability": 0.85}]
        text = json.dumps({"policy_summary": "nested params", "candidates": [candidate]})

        parsed = NvidiaNIMPolicyClient._parse_frontier_payload(text, self.observation, limit=1)
        actions = parsed["candidates"][0].actions

        self.assertEqual(actions[0].start.isoformat(), "2026-07-01T14:30:00-07:00")
        self.assertEqual(actions[0].metadata["notes"], "Prepare renewal notes for upcoming client call.")
        self.assertEqual(actions[1].event_id, self.observation.events[0].event_id)
        self.assertEqual(actions[1].start.isoformat(), "2026-07-01T16:00:00-07:00")
        self.assertEqual(actions[2].start.isoformat(), "2026-07-04T14:00:00-07:00")
        self.assertEqual(actions[2].end.isoformat(), "2026-07-04T14:30:00-07:00")
        self.assertEqual(actions[2].metadata["task_ids"], "task_renewal_prep,task_expense")
        self.assertIn("normalized_action_params:0:0", parsed["validation_errors"])
        self.assertIn("normalized_action_params:0:1", parsed["validation_errors"])
        self.assertIn("normalized_batch_tasks_target_time:0:2", parsed["validation_errors"])

    def test_nim_frontier_parser_skips_invalid_candidates_when_valid_typed_candidates_remain(self):
        valid = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[0].to_dict()
        invalid = dict(valid)
        invalid["candidate_id"] = "nim_invalid_no_actions"
        invalid["actions"] = []
        text = json.dumps({"policy_summary": "mixed", "candidates": [invalid, valid]})

        parsed = NvidiaNIMPolicyClient._parse_frontier_payload(text, self.observation, limit=2)

        self.assertEqual([candidate.candidate_id for candidate in parsed["candidates"]], [valid["candidate_id"]])
        self.assertIn("skipped_candidate_without_actions:nim_invalid_no_actions", parsed["validation_errors"])

    def test_nim_frontier_parser_rejects_malformed_write_actions(self):
        valid = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[0].to_dict()
        invalid = dict(valid)
        invalid["candidate_id"] = "nim_invalid_move_without_times"
        invalid["actions"] = [
            {
                "action_type": "move_event",
                "event_id": self.observation.events[0].event_id,
                "calendar_id": self.observation.events[0].calendar_id,
            }
        ]
        text = json.dumps({"policy_summary": "mixed", "candidates": [invalid, valid]})

        parsed = NvidiaNIMPolicyClient._parse_frontier_payload(text, self.observation, limit=2)

        self.assertEqual([candidate.candidate_id for candidate in parsed["candidates"]], [valid["candidate_id"]])
        self.assertIn("skipped_invalid_action_payload:nim_invalid_move_without_times", parsed["validation_errors"])
        self.assertEqual(parsed["rejections"][0]["reason"], "skipped_invalid_action_payload")
        self.assertIn("requires start and end", parsed["rejections"][0]["schema_errors"][0])

    def test_nim_frontier_generation_retries_malformed_json_with_smaller_frontier(self):
        valid = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[0].to_dict()
        client = RetryFrontierNIMClient(valid)

        result = client.generate_candidate_frontier(
            goal="Make next week less chaotic",
            observation=self.observation,
            biography=self.biography,
            limit=4,
        )

        self.assertEqual([candidate.candidate_id for candidate in result.candidates], [valid["candidate_id"]])
        self.assertEqual(client.requested_limits, [4, 2])
        self.assertEqual(result.metadata["schema_retry_count"], 1)
        self.assertIn("frontier_schema_retry_succeeded", result.metadata["validation"]["validation_errors"])
        self.assertEqual(result.metadata["retry_policy"]["max_attempts"], 2)

    def test_live_diffusiongemma_policy_applies_offline_tuning_to_nim_frontier_candidates(self):
        client = FakeNIMGeneratorClient()
        untuned = LiveDiffusionGemmaPolicy(client=client).generate_candidates(self.observation, self.biography)
        baseline_reward = untuned[0].expected_reward
        tuned_intent = untuned[0].intent

        tuning = PolicyTuning(
            tuning_id="offline_replay_v1",
            intent_reward_bias={tuned_intent: 0.4},
            source_report="train_offline_policy.py",
        )
        tuned = LiveDiffusionGemmaPolicy(client=FakeNIMGeneratorClient(), policy_tuning=tuning).generate_candidates(
            self.observation, self.biography
        )

        self.assertAlmostEqual(tuned[0].expected_reward, round(baseline_reward + 0.4, 4))
        self.assertEqual(tuned[0].reward_breakdown["offline_intent_bias"], 0.4)
        self.assertIn("offline_tuning=intent_bias:+0.40", tuned[0].control_notes)

    def test_live_diffusiongemma_policy_offline_tuning_can_reorder_nim_frontier(self):
        candidates = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)
        leader, runner_up = candidates[0], candidates[1]
        client = TwoCandidateNIMGeneratorClient(leader.to_dict(), runner_up.to_dict())

        tuning = PolicyTuning(denied_intents=[leader.intent])
        tuned = LiveDiffusionGemmaPolicy(client=client, policy_tuning=tuning).generate_candidates(self.observation, self.biography)

        self.assertEqual(tuned[0].candidate_id, runner_up.candidate_id)
        self.assertIn("offline_tuning=deny_intent_penalty:-1.00", tuned[1].control_notes)

    def test_missing_nim_credential_blocks_live_policy_without_heuristic_fallback(self):
        policy = LiveDiffusionGemmaPolicy(client=MissingNIMClient(api_key=""))
        with self.assertRaises(LiveDiffusionGemmaCredentialError):
            policy.generate_candidates(self.observation, self.biography)

    def test_nim_parser_rank_text_fallback_only_accepts_known_candidates(self):
        candidates = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[:3]
        text = f"1. {candidates[1].candidate_id} is safest\n2. cand_not_real should be ignored\n3. {candidates[0].candidate_id}"
        parsed = NvidiaNIMPolicyClient._parse_rank_payload(text, candidates)

        self.assertEqual([row.candidate_id for row in parsed["ranks"]], [candidates[1].candidate_id, candidates[0].candidate_id])
        self.assertEqual(parsed["validation_errors"], ["non_json_rank_text_fallback"])

    def test_nim_client_uses_explicit_tls_context_for_requests(self):
        client = NvidiaNIMPolicyClient(api_key="test-key", timeout_seconds=1)
        context = object()
        response = FakeHTTPResponse(b"{}")
        with patch.dict("os.environ", {"CALENDAR_PILOT_NIM_CA_FILE": "/tmp/calendarpilot-ca.pem"}), \
                patch("calendar_pilot.diffusiongemma.live.ssl.create_default_context", return_value=context) as create_context, \
                patch("calendar_pilot.diffusiongemma.live.urlopen", return_value=response) as open_url:
            data = client._request_json("GET", "/models", None)
            health = client.health_status(validate_remote=False)

        self.assertEqual(data, {})
        create_context.assert_called_once_with(cafile="/tmp/calendarpilot-ca.pem")
        self.assertIs(open_url.call_args.kwargs["context"], context)
        self.assertEqual(open_url.call_args.kwargs["timeout"], 1)
        self.assertEqual(health["tls_ca_bundle_source"], "CALENDAR_PILOT_NIM_CA_FILE")
        self.assertEqual(health["timeout_seconds"], 1)
        self.assertEqual(health["fallback_behavior"], "fail_closed_no_heuristic_fallback_in_live_mode")
        self.assertIn("retry_policy", health)


class FakeNIMGeneratorClient:
    model = "google/diffusiongemma-26b-a4b-it"

    def health_status(self, *, validate_remote: bool = False):
        return {"status": "ok", "configured": True, "backend": "nvidia_nim_diffusiongemma_policy"}

    def generate_candidate_frontier(self, *, observation, biography, **_kwargs):
        candidate = DiffusionGemmaPolicy().generate_candidates(observation, biography)[0]
        candidate.candidate_id = "nim_generated_candidate_1"
        candidate.model_story.append("Generated directly by NIM.")
        candidate.control_notes.append("nim_generation=typed_candidate_frontier")
        return NIMFrontierResult(
            candidates=[candidate],
            policy_summary="Generated typed frontier from NIM.",
            metadata={
                "backend": "nvidia_nim_diffusiongemma_policy",
                "mode": "model_generated_candidate_frontier",
                "prompt_version": "calendar_pilot_nim_frontier_generator_v2",
                "model": self.model,
                "base_url": "https://integrate.api.nvidia.com/v1",
                "response_id": "nim_generate_test",
                "candidate_count": 1,
                "decoding_settings": {"temperature": 0.2, "top_p": 0.9},
                "timeout_seconds": 90,
                "retry_policy": {"max_attempts": 1, "http_retry": "none"},
                "fallback_behavior": "fail_closed_no_heuristic_fallback_in_live_mode",
                "validation": {"candidate_contract": "CandidateCalendarAction", "validation_errors": []},
            },
        )


class GoalCaptureNIMGeneratorClient(FakeNIMGeneratorClient):
    def __init__(self):
        self.last_goal = None
        self.last_limit = None

    def generate_candidate_frontier(self, *, goal, observation, biography, **kwargs):
        self.last_goal = goal
        self.last_limit = kwargs.get("limit")
        return super().generate_candidate_frontier(goal=goal, observation=observation, biography=biography, **kwargs)


class TwoCandidateNIMGeneratorClient:
    model = "google/diffusiongemma-26b-a4b-it"

    def __init__(self, first: dict, second: dict):
        self.first = first
        self.second = second

    def health_status(self, *, validate_remote: bool = False):
        return {"status": "ok", "configured": True, "backend": "nvidia_nim_diffusiongemma_policy"}

    def generate_candidate_frontier(self, *, observation, biography, **_kwargs):
        from calendar_pilot.types import CandidateCalendarAction

        candidates = [CandidateCalendarAction.from_dict(self.first), CandidateCalendarAction.from_dict(self.second)]
        return NIMFrontierResult(
            candidates=candidates,
            policy_summary="Generated typed frontier from NIM.",
            metadata={
                "backend": "nvidia_nim_diffusiongemma_policy",
                "mode": "model_generated_candidate_frontier",
                "prompt_version": "calendar_pilot_nim_frontier_generator_v2",
                "model": self.model,
                "base_url": "https://integrate.api.nvidia.com/v1",
                "response_id": "nim_generate_test",
                "candidate_count": 2,
                "decoding_settings": {"temperature": 0.2, "top_p": 0.9},
                "timeout_seconds": 90,
                "retry_policy": {"max_attempts": 1, "http_retry": "none"},
                "fallback_behavior": "fail_closed_no_heuristic_fallback_in_live_mode",
                "validation": {"candidate_contract": "CandidateCalendarAction", "validation_errors": []},
            },
        )


class RetryFrontierNIMClient(NvidiaNIMPolicyClient):
    def __init__(self, valid_candidate: dict):
        super().__init__(api_key="test-key", timeout_seconds=1)
        self.valid_candidate = valid_candidate
        self.requested_limits: list[int] = []

    def _request_json(self, method, path, payload):  # type: ignore[override]
        prompt = json.loads(payload["messages"][0]["content"])
        self.requested_limits.append(int(prompt["limit"]))
        if len(self.requested_limits) == 1:
            return {"id": "nim_bad_json", "choices": [{"message": {"content": "{\"policy_summary\":\"bad\",\"candidates\":[{\"candidate_id\":\"broken\"}"}}]}
        if not prompt.get("strict_retry_instruction"):
            raise LiveDiffusionGemmaSchemaError("retry prompt did not include strict retry instruction")
        return {
            "id": "nim_retry_ok",
            "choices": [{
                "message": {
                    "content": json.dumps({"policy_summary": "retry ok", "candidates": [self.valid_candidate]})
                }
            }],
        }


class FakeNIMClient:
    model = "google/diffusiongemma-26b-a4b-it"

    def health_status(self, *, validate_remote: bool = False):
        return {"status": "ok", "configured": True, "backend": "nvidia_nim_diffusiongemma_policy"}

    def rank_candidates(self, *, candidates, **_kwargs):
        return NIMPolicyResult(
            ranks=[
                NIMPolicyRank(candidate_id=candidates[-1].candidate_id, rank=1, score_delta=0.25, reason="Prefer the safer control arm."),
                NIMPolicyRank(candidate_id=candidates[0].candidate_id, rank=2, score_delta=0.05, reason="Still useful."),
            ],
            policy_summary="Ranked for low regret and explicit user value.",
            metadata={
                "backend": "nvidia_nim_diffusiongemma_policy",
                "prompt_version": "calendar_pilot_nim_policy_ranker_v1",
                "model": self.model,
                "base_url": "https://integrate.api.nvidia.com/v1",
                "response_id": "nim_test",
                "ranked_count": 2,
                "candidate_count": len(candidates),
                "decoding_settings": {"temperature": 0, "top_p": 1},
                "timeout_seconds": 90,
                "retry_policy": {"max_attempts": 1, "http_retry": "none"},
                "fallback_behavior": "fail_closed_no_heuristic_fallback_in_live_mode",
                "validation": {"candidate_contract": "CandidateCalendarAction", "validation_errors": []},
            },
        )


class MissingNIMClient(NvidiaNIMPolicyClient):
    def rank_candidates(self, **_kwargs):
        raise LiveDiffusionGemmaCredentialError("NVIDIA NIM API key is required")


class FakeHTTPResponse:
    status = 200

    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def read(self):
        return self.body


if __name__ == "__main__":
    unittest.main()
