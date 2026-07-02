
import json
import unittest
from pathlib import Path

from calendar_pilot.codex import CodexExecutiveAgent
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, SelfPlayRunner, extract_signals
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import RawCalendarObservation, UserBiography

ROOT = Path(__file__).resolve().parents[1]


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        self.biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))

    def test_signals_have_narrative_pressure(self):
        signals = extract_signals(self.observation, self.biography)
        self.assertGreater(signals.pressure_score, 0)
        self.assertTrue(signals.narrative)
        self.assertGreaterEqual(len(signals.open_slots), 1)

    def test_policy_attaches_story_breakdown_and_counterfactual(self):
        candidate = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[0]
        self.assertTrue(candidate.model_story)
        self.assertTrue(candidate.counterfactual)
        self.assertIn("utility", candidate.reward_breakdown)
        self.assertNotEqual(candidate.right_moment_score, 0.0)

    def test_codex_explains_action_anatomy(self):
        policy = DiffusionGemmaPolicy()
        candidate = policy.generate_candidates(self.observation, self.biography)[0]
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(user_scope_id=self.observation.user_scope_id, max_authority_tier=3, issued_at=self.observation.observed_at)
        receipt = kernel.authorize_and_materialize(candidate, self.observation, authority_grant=grant.grant_id, requested_authority_tier=3)
        text = CodexExecutiveAgent().explain(candidate, receipt, self.biography)
        self.assertIn("Reward anatomy", text)
        self.assertIn("Counterfactual", text)
        self.assertIn("Rollback", text)

    def test_self_play_logs_adversarial_findings(self):
        metrics = SelfPlayRunner().run(self.observation, self.biography, episodes=5, authority_tier=3)
        self.assertEqual(metrics.episodes, 5)
        self.assertEqual(len(metrics.episode_log), 5)
        self.assertIsInstance(metrics.failure_modes, dict)
        summary = CodexExecutiveAgent().summarize_self_play(metrics)
        self.assertIn("Self-play ran", summary)


if __name__ == "__main__":
    unittest.main()
