

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import RawCalendarObservation, UserBiography, RewardEvent

ROOT = Path(__file__).resolve().parents[1]


class ReplayTests(unittest.TestCase):
    def test_replay_round_trip(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))
        candidate = DiffusionGemmaPolicy().generate_candidates(observation, biography)[0]
        receipt = SwiftKernelStub().authorize_and_materialize(candidate, observation, granted_authority_tier=3)
        reward = RewardEvent(
            reward_event_id="r1",
            receipt_id=receipt.receipt_id,
            observed_at=datetime.now(timezone.utc),
            accepted=True,
            total_reward=1.25,
        )
        buffer = ReplayBuffer()
        buffer.append_candidate_receipt(candidate, receipt)
        self.assertTrue(buffer.attach_reward(receipt.receipt_id, reward))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "replay.jsonl"
            buffer.save_jsonl(path)
            loaded = ReplayBuffer.load_jsonl(path)
        self.assertEqual(len(loaded.records), 1)
        self.assertAlmostEqual(loaded.average_reward(), 1.25)


if __name__ == "__main__":
    unittest.main()