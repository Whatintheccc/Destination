

import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from calendar_pilot.biography import BiographyStore
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, SelfPlayRunner
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    RawCalendarObservation,
    Reversibility,
    RewardEvent,
    UserBiography,
)

ROOT = Path(__file__).resolve().parents[1]


class BehavioralControlTests(unittest.TestCase):
    def setUp(self):
        self.raw_observation = json.loads((ROOT / "data/sample_calendar.json").read_text())
        self.profile = json.loads((ROOT / "data/sample_profile.json").read_text())
        self.biography = UserBiography.from_dict(self.profile)

    def _observation(self, focus=False):
        data = copy.deepcopy(self.raw_observation)
        data["device_context"]["is_focus_mode"] = focus
        return RawCalendarObservation.from_dict(data)

    def test_focus_mode_scoring_penalty_applies_before_ranking(self):
        normal = DiffusionGemmaPolicy().generate_candidates(self._observation(False), self.biography)
        focus = DiffusionGemmaPolicy().generate_candidates(self._observation(True), self.biography)
        normal_by_id = {c.candidate_id: c for c in normal}
        comparable = [c for c in focus if c.intent != "do_nothing" and c.candidate_id in normal_by_id]
        self.assertTrue(comparable)
        candidate = comparable[0]
        self.assertGreaterEqual(candidate.predicted_interruption_cost, normal_by_id[candidate.candidate_id].predicted_interruption_cost + 0.19)
        self.assertTrue(any("focus_mode_interruption_penalty" in n for n in candidate.control_notes))

    def test_authority_denial_receipt_is_structured(self):
        observation = self._observation(False)
        candidate = DiffusionGemmaPolicy().generate_candidates(observation, self.biography)[0]
        receipt = SwiftKernelStub().authorize_and_materialize(candidate, observation, granted_authority_tier=0)
        self.assertEqual(receipt.sync_status, "denied")
        self.assertEqual(receipt.actuation_mode.value, "denied")
        self.assertTrue(receipt.rejected_action_types)
        self.assertIn("Swift-issued authority grant", receipt.denied_reason)

    def test_social_actuation_boundary_denies_people_mutation(self):
        observation = self._observation(False)
        action = AtomicCalendarAction(
            action_type=AtomicActionType.MOVE_EVENT,
            event_id="evt_team_sync",
            start=observation.observed_at,
            end=observation.observed_at,
            calendar_id="work",
        )
        candidate = CandidateCalendarAction(
            candidate_id="cand_social_py",
            intent="move_people_meeting",
            actions=[action],
            target_calendars=["work"],
            affected_event_ids=["evt_team_sync"],
            affected_people_ids=["team@example.com"],
            reversibility=Reversibility.MEDIUM,
            required_authority_tier=5,
        )
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(user_scope_id=observation.user_scope_id, max_authority_tier=6, issued_at=observation.observed_at)
        receipt = kernel.authorize_and_materialize(candidate, observation, authority_grant=grant.grant_id, requested_authority_tier=6)
        self.assertEqual(receipt.sync_status, "denied")
        self.assertIn("social actuation", receipt.denied_reason)

    def test_draft_plan_is_staged_not_written(self):
        observation = self._observation(False)
        action = AtomicCalendarAction(
            action_type=AtomicActionType.DRAFT_SCHEDULE_PLAN,
            title="Draft repair plan",
            start=observation.observed_at,
            end=observation.observed_at,
            calendar_id="work",
        )
        candidate = CandidateCalendarAction(
            candidate_id="cand_draft_py",
            intent="draft_day_repair_plan",
            actions=[action],
            target_calendars=["work"],
            affected_event_ids=["evt_client_call"],
            affected_people_ids=["client@example.com"],
            reversibility=Reversibility.HIGH,
            required_authority_tier=2,
        )
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(user_scope_id=observation.user_scope_id, max_authority_tier=2, scopes=["recommend", "stage", "commit_private", "undo"], issued_at=observation.observed_at)
        receipt = kernel.authorize_and_materialize(candidate, observation, authority_grant=grant.grant_id, requested_authority_tier=2)
        self.assertEqual(receipt.sync_status, "staged")
        self.assertEqual(receipt.generated_event_ids, [])
        self.assertTrue(receipt.staged_action_ids)

    def test_self_play_persists_decisions_rewards_and_failures_to_replay(self):
        replay = ReplayBuffer()
        observation = self._observation(False)
        metrics = SelfPlayRunner(replay=replay).run(observation, self.biography, episodes=4, authority_tier=1)
        summary = replay.summarize()
        self.assertEqual(metrics.episodes, 4)
        self.assertGreater(summary.decisions, 0)
        self.assertGreater(summary.rewards, 0)
        self.assertGreater(summary.episodes, 0)
        self.assertGreater(summary.denials, 0)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "replay.jsonl"
            replay.save_jsonl(path)
            loaded = ReplayBuffer.load_jsonl(path)
        self.assertEqual(len(loaded.records), len(replay.records))
        self.assertGreaterEqual(loaded.summarize().denials, 1)

    def test_biography_update_event_provenance_and_decay(self):
        store = BiographyStore()
        reward = RewardEvent(
            reward_event_id="r_fatigue",
            receipt_id="rcpt",
            observed_at=datetime.now(timezone.utc),
            ignored=True,
            notification_dismissed=True,
            total_reward=-1.0,
        )
        updated = store.update_from_reward(self.biography, reward)
        self.assertEqual(updated.notification_fatigue, self.biography.notification_fatigue)
        self.assertTrue(updated.profile_update_events)
        self.assertEqual(updated.profile_update_events[-1]["claim"], "action_stream_feedback")
        repaired = store.apply_user_correction(updated, "dismisses evening suggestions", "evenings are fine during travel weeks")
        self.assertGreater(len(repaired.profile_update_events), len(updated.profile_update_events))
        prompt = store.propose_repair(repaired, "no more evening inference")
        self.assertIn("Profile repair candidate", prompt.prompt)


if __name__ == "__main__":
    unittest.main()