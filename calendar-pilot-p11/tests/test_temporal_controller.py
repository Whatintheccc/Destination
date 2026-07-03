from __future__ import annotations

import json
from pathlib import Path
import unittest

from calendar_pilot.diffusiongemma.temporal_controller import RightMomentTemporalController
from calendar_pilot.types import RawCalendarObservation, UserBiography
from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy


ROOT = Path(__file__).resolve().parents[1]


class TemporalControllerTests(unittest.TestCase):
    def test_policy_attaches_temporal_control(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / 'data/sample_calendar.json').read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / 'data/sample_profile.json').read_text()))
        candidates = DiffusionGemmaPolicy().generate_candidates(observation, biography)
        self.assertTrue(any('temporal_control=' in note for c in candidates for note in c.control_notes))
        self.assertTrue(any('temporal_staleness_risk' in c.simulated_outcomes for c in candidates))

    def test_controller_uses_explicit_modes(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / 'data/sample_calendar.json').read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / 'data/sample_profile.json').read_text()))
        candidate = DiffusionGemmaPolicy().generate_candidates(observation, biography)[0]
        plan = RightMomentTemporalController().plan(candidate, observation, biography)
        self.assertIn(plan.mode, {'act_now','expose_now','stage_now_commit_later','bundle_into_digest','ask_for_authority_or_context','wait_for_context_refresh','wait_for_response_window','do_nothing'})
        self.assertGreaterEqual(plan.staleness_risk, 0.0)


if __name__ == '__main__':
    unittest.main()