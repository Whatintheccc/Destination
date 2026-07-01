import json
import unittest
from pathlib import Path

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, LiveDiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.live import (
    LiveDiffusionGemmaCredentialError,
    NIMPolicyRank,
    NIMPolicyResult,
    NvidiaNIMPolicyClient,
)
from calendar_pilot.types import RawCalendarObservation, UserBiography, RightMomentDecision

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

    def test_missing_nim_credential_blocks_live_policy_without_heuristic_fallback(self):
        policy = LiveDiffusionGemmaPolicy(client=MissingNIMClient(api_key=""))
        with self.assertRaises(LiveDiffusionGemmaCredentialError):
            policy.generate_candidates(self.observation, self.biography)


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
            metadata={"response_id": "nim_test"},
        )


class MissingNIMClient(NvidiaNIMPolicyClient):
    def rank_candidates(self, **_kwargs):
        raise LiveDiffusionGemmaCredentialError("NVIDIA NIM API key is required")


if __name__ == "__main__":
    unittest.main()
