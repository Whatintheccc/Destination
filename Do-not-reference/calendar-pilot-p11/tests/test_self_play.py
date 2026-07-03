

import json
from copy import deepcopy
import unittest
from pathlib import Path

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, SelfPlayRunner, UserSimulator
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import RawCalendarObservation, UserBiography

ROOT = Path(__file__).resolve().parents[1]


class SelfPlayTests(unittest.TestCase):
    def test_self_play_runs(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))
        metrics = SelfPlayRunner().run(observation, biography, episodes=3, authority_tier=3)
        self.assertEqual(metrics.episodes, 3)
        self.assertGreaterEqual(metrics.acceptance_rate, 0.0)
        self.assertLessEqual(metrics.acceptance_rate, 1.0)

    def test_self_play_episode_records_sim_v2_and_backend_grant_policy(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))
        replay = ReplayBuffer()
        metrics = SelfPlayRunner(replay=replay, user_simulator=UserSimulator(seed=11, simulator_version="sim_v2")).run(observation, biography, episodes=1, authority_tier=3)
        self.assertEqual(metrics.episodes, 1)
        episodes = [record.payload for record in replay.records if record.record_type == "self_play_episode"]
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["simulator_version"], "sim_v2")
        self.assertEqual(episodes[0]["backend_grant_policy"]["backend"], "stub_fast")
        self.assertEqual(episodes[0]["backend_grant_policy"]["grant_issuance"], "self_issued")

    def test_sim_v2_ignores_candidate_predicted_heads(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))
        candidate = next(c for c in DiffusionGemmaPolicy().generate_candidates(observation, biography) if c.intent != "do_nothing")
        low_self_belief = deepcopy(candidate)
        high_self_belief = deepcopy(candidate)
        low_self_belief.predicted_acceptance = 0.05
        low_self_belief.predicted_utility = 0.05
        low_self_belief.predicted_regret = 0.95
        low_self_belief.predicted_interruption_cost = 0.95
        low_self_belief.predicted_social_risk = 0.95
        high_self_belief.predicted_acceptance = 0.95
        high_self_belief.predicted_utility = 0.95
        high_self_belief.predicted_regret = 0.01
        high_self_belief.predicted_interruption_cost = 0.01
        high_self_belief.predicted_social_risk = 0.01

        low_response = UserSimulator(seed=31, simulator_version="sim_v2").respond(low_self_belief, observation, biography)
        high_response = UserSimulator(seed=31, simulator_version="sim_v2").respond(high_self_belief, observation, biography)

        self.assertEqual(low_response, high_response)


if __name__ == "__main__":
    unittest.main()
