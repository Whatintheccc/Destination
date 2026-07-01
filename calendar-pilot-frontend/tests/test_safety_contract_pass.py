from __future__ import annotations

import copy
import json
import unittest
from datetime import timedelta
from pathlib import Path

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, extract_signals
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    CodexToolStatus,
    PolicyTuning,
    RawCalendarEvent,
    RawCalendarObservation,
    Reversibility,
    UserBiography,
)

ROOT = Path(__file__).resolve().parents[1]


def load_obs() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))


def load_bio() -> UserBiography:
    return UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))


class SafetyContractPassTests(unittest.TestCase):
    def test_out_of_band_authority_tier_is_rejected_before_materialization(self):
        obs = load_obs()
        bio = load_bio()
        candidate = DiffusionGemmaPolicy().generate_candidates(obs, bio)[0]
        receipt = SwiftKernelStub().authorize_and_materialize(candidate, obs, granted_authority_tier=99)
        self.assertEqual(receipt.sync_status, "denied")
        self.assertIn("Swift-issued authority grant", receipt.denied_reason or "")
        self.assertIsNone(receipt.authority_grant_id)

    def test_swift_grant_controls_commit_scope_and_denial_reason(self):
        obs = load_obs()
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=2, issued_at=obs.observed_at)
        candidate = CandidateCalendarAction(
            candidate_id="cand_scope",
            intent="create_focus_block",
            actions=[AtomicCalendarAction(action_type=AtomicActionType.CREATE_FOCUS_BLOCK, title="Focus", start=obs.observed_at + timedelta(hours=3), end=obs.observed_at + timedelta(hours=4))],
            target_calendars=["work"],
            affected_event_ids=[],
            affected_people_ids=[],
            reversibility=Reversibility.HIGH,
            required_authority_tier=3,
        )
        receipt = kernel.authorize_and_materialize(candidate, obs, authority_grant=grant.grant_id, requested_authority_tier=3)
        self.assertEqual(receipt.sync_status, "denied")
        self.assertIn("out-of-band", receipt.denied_reason or "")
        self.assertEqual(receipt.authority_grant_id, grant.grant_id)

    def test_codex_stage_semantics_are_not_success_on_denial(self):
        obs = load_obs()
        bio = load_bio()
        runtime = CodexToolRuntime()
        candidate = DiffusionGemmaPolicy().generate_candidates(obs, bio)[0]
        receipt = runtime.execute(CodexToolCall("stage_without_grant", CodexToolName.STAGE_ACTION_PACKET, {"candidate": candidate.to_dict()}, 3, "stage"), obs, bio)
        self.assertEqual(receipt.status, CodexToolStatus.DENIED)
        self.assertEqual(receipt.stage_state.value, "denied")

    def test_codex_stage_with_grant_is_stageable(self):
        obs = load_obs()
        bio = load_bio()
        runtime = CodexToolRuntime()
        grant = runtime.kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=3, issued_at=obs.observed_at)
        frontier = runtime.execute(CodexToolCall("frontier_grant", CodexToolName.GENERATE_CANDIDATE_FRONTIER, {"limit": 2}, 3, "frontier", authority_grant_id=grant.grant_id), obs, bio)
        cid = frontier.output["frontier_ids"][0]
        staged = runtime.execute(CodexToolCall("stage_grant", CodexToolName.STAGE_ACTION_PACKET, {"candidate_id": cid}, 3, "stage", authority_grant_id=grant.grant_id), obs, bio)
        self.assertEqual(staged.status, CodexToolStatus.STAGEABLE)
        self.assertIn(staged.stage_state.value, {"stageable", "requires_confirmation"})

    def test_occupied_minutes_use_interval_union(self):
        obs = load_obs()
        data = copy.deepcopy(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        start = obs.observed_at.replace(hour=9, minute=0, second=0, microsecond=0)
        data["events"] = [
            {"event_id": "a", "title": "A", "start": start.isoformat(), "end": (start + timedelta(hours=2)).isoformat(), "calendar_id": "work"},
            {"event_id": "b", "title": "B", "start": (start + timedelta(hours=1)).isoformat(), "end": (start + timedelta(hours=3)).isoformat(), "calendar_id": "work"},
        ]
        union_obs = RawCalendarObservation.from_dict(data)
        signals = extract_signals(union_obs, load_bio())
        self.assertEqual(signals.occupied_minutes_workday, 180)

    def test_replay_failure_modes_count_normalized_findings_once(self):
        obs = load_obs()
        bio = load_bio()
        replay = ReplayBuffer()
        grant = SwiftKernelStub().issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=1, issued_at=obs.observed_at)
        from calendar_pilot.diffusiongemma import SelfPlayRunner
        SelfPlayRunner(replay=replay).run(obs, bio, episodes=3, authority_grant=grant.grant_id)
        normalized = sum(1 for r in replay.records if r.record_type == "adversary_finding")
        self.assertEqual(sum(replay.summarize().failure_modes.values()), normalized)

    def test_policy_tuning_precedes_right_moment(self):
        obs = load_obs()
        bio = load_bio()
        baseline = DiffusionGemmaPolicy().generate_candidates(obs, bio)
        target = next(c for c in baseline if c.intent == "create_prep_block")
        tuning = PolicyTuning(intent_reward_bias={"create_prep_block": 2.0})
        tuned = DiffusionGemmaPolicy(policy_tuning=tuning).generate_candidates(obs, bio)
        tuned_target = next(c for c in tuned if c.candidate_id == target.candidate_id)
        self.assertGreater(tuned_target.expected_reward, target.expected_reward)
        self.assertGreaterEqual(tuned_target.right_moment_score, target.right_moment_score)
        self.assertTrue(any("offline_tuning" in n for n in tuned_target.control_notes))


if __name__ == "__main__":
    unittest.main()
