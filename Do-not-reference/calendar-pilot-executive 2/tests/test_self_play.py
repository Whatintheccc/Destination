import json
import unittest
from pathlib import Path

from calendar_pilot.diffusiongemma import SelfPlayRunner
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


if __name__ == "__main__":
    unittest.main()
