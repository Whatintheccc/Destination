
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, LiveDiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.live import (
    LiveDiffusionGemmaCredentialError,
    NIMFrontierResult,
    NIMPolicyRank,
    NIMPolicyResult,
    NvidiaNIMPolicyClient,
)
from calendar_pilot.types import CodexToolCall, CodexToolName, RawCalendarObservation, UserBiography, RightMomentDecision

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
