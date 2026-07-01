import json
import unittest
from pathlib import Path

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import RawCalendarObservation, UserBiography, Reversibility

ROOT = Path(__file__).resolve().parents[1]


class KernelStubTests(unittest.TestCase):
    def setUp(self):
        self.observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        self.biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))
        self.candidate = DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)[0]

    def test_denies_when_authority_too_low(self):
        receipt = SwiftKernelStub().authorize_and_materialize(self.candidate, self.observation, granted_authority_tier=1)
        self.assertEqual(receipt.sync_status, "denied")
        self.assertIn("Swift-issued authority grant", receipt.denied_reason)

    def test_materializes_with_rollback(self):
        self.candidate.reversibility = Reversibility.HIGH
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(user_scope_id=self.observation.user_scope_id, max_authority_tier=3, issued_at=self.observation.observed_at)
        receipt = kernel.authorize_and_materialize(self.candidate, self.observation, authority_grant=grant.grant_id, requested_authority_tier=3)
        self.assertEqual(receipt.sync_status, "materialized")
        self.assertIsNotNone(receipt.rollback_handle_id)


if __name__ == "__main__":
    unittest.main()
