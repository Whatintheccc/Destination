import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from calendar_pilot.codex.annotator import CodexSemanticAnnotator
from calendar_pilot.diffusiongemma.self_play import UserSimulator
from calendar_pilot.environment.invariants import check_replay
from calendar_pilot.environment.label_registry import LabelRegistry
from calendar_pilot.environment.signal_estimators import InterruptionToleranceEstimator
from calendar_pilot.replay import ReplayBuffer, ReplayRecord
from calendar_pilot.types import (
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarObservation,
    Reversibility,
    RewardEvent,
    SemanticSignal,
    UserBiography,
    Belief,
)

ROOT = Path(__file__).resolve().parents[1]


class P12SignalStreamTests(unittest.TestCase):
    def observation(self, dismissals=3):
        data = json.loads((ROOT / "data/sample_calendar.json").read_text())
        data["notification_history"] = [
            {"sent_at": f"2026-06-2{i}T20:15:00-07:00", "kind": "suggestion", "outcome": "dismissed"}
            for i in range(dismissals)
        ]
        return RawCalendarObservation.from_dict(data)

    def biography(self, legacy_fatigue=None):
        data = json.loads((ROOT / "data/sample_profile.json").read_text())
        if legacy_fatigue is not None:
            data["notification_fatigue"] = legacy_fatigue
        return UserBiography.from_dict(data)

    def test_replay_rows_gain_signal_stream_and_reward_rows_are_action(self):
        replay = ReplayBuffer()
        reward = RewardEvent("rew_p12", "rcpt", datetime.now(timezone.utc), total_reward=1.0)
        replay.append_reward(reward)
        row = replay.records[-1].envelope()
        self.assertEqual(row["signal_stream"], "action")
        self.assertEqual(check_replay([row]), [])

    def test_reward_purity_rejects_derived_reward_payload(self):
        row = ReplayRecord(
            record_type="semantic_signal",
            record_id="bad_signal_reward",
            trace_id="trace",
            signal_stream="derived",
            payload={"reward": {"total_reward": 1.0}, "evidence": ["x"]},
        ).envelope()
        violations = check_replay([row])
        self.assertTrue(any(v.invariant_id == "B4" for v in violations))

    def test_interruption_estimator_is_deterministic_and_evidence_cited(self):
        obs = self.observation(dismissals=5)
        estimator = InterruptionToleranceEstimator()
        first = estimator.estimate(obs)
        second = estimator.estimate(obs)
        self.assertEqual(first.signal.payload, second.signal.payload)
        self.assertEqual(first.report.estimator_version, "interruption_tolerance_v1")
        self.assertTrue(first.signal.evidence)
        replay = ReplayBuffer()
        signal_row_id = replay.append_semantic_signal(first.signal.to_dict(), trace_id=first.signal.signal_id)
        belief = Belief.from_semantic_signal(first.signal, activation_row_ids=[signal_row_id])
        belief_row_id = replay.append_belief(belief, trace_id=belief.belief_id, causal_parent_id=signal_row_id)
        replay.append_signal_estimator_report(first.report.to_dict(), trace_id=first.report.report_id, causal_parent_id=belief_row_id)
        self.assertEqual(replay.records[-2].record_type, "belief")
        self.assertEqual(replay.records[-2].signal_stream, "derived")
        self.assertFalse(check_replay([r.envelope() for r in replay.records]))

    def test_sim_v2_1_uses_behavior_not_legacy_scalar(self):
        obs_low = self.observation(dismissals=0)
        obs_high = self.observation(dismissals=8)
        cand = CandidateCalendarAction(
            candidate_id="cand_sim",
            intent="create_prep_block",
            actions=[],
            target_calendars=["work"],
            affected_event_ids=[],
            affected_people_ids=[],
            reversibility=Reversibility.HIGH,
            required_authority_tier=3,
        )
        sim_a = UserSimulator(seed=3, simulator_version="sim_v2.1")
        response_low = sim_a.respond(cand, obs_low, self.biography(legacy_fatigue=1.0))
        sim_b = UserSimulator(seed=3, simulator_version="sim_v2.1")
        response_low_again = sim_b.respond(cand, obs_low, self.biography(legacy_fatigue=0.0))
        self.assertEqual(response_low, response_low_again)
        # Behavioral history affects the underlying estimator, even when legacy scalar is held fixed.
        self.assertLess(
            InterruptionToleranceEstimator().estimate(obs_high).overall_tolerance,
            InterruptionToleranceEstimator().estimate(obs_low).overall_tolerance,
        )

    def test_label_registry_activation_disable_and_authority_barrier(self):
        replay = ReplayBuffer()
        registry = LabelRegistry(replay=replay)
        reward = RewardEvent("1", "rcpt", datetime.now(timezone.utc), notification_dismissed=True, total_reward=-1.0)
        replay.append_reward(reward, trace_id="reward_trace")
        signal = SemanticSignal(
            signal_id="sig_evening",
            user_scope_id="u",
            label="dismisses_evening_suggestions",
            statement="Dismisses evening suggestions",
            evidence=["reward:1"],
            confidence=0.8,
        )
        registry.propose(signal)
        registry.activate("sig_evening", user_scope_id="u", actor="user")
        self.assertTrue(registry.is_active("sig_evening"))
        registry.disable("sig_evening", user_scope_id="u")
        self.assertFalse(registry.is_active("sig_evening"))
        self.assertEqual(registry.authority_payload()["scopes"], [])
        rows = [r.envelope() for r in replay.records]
        self.assertFalse([v for v in check_replay(rows) if v.invariant_id in {"B1", "B2", "B3"}])

    def test_codex_annotator_requires_action_evidence(self):
        records = []
        for idx in range(3):
            records.append({
                "record_type": "reward",
                "record_id": f"reward:{idx}",
                "trace_id": f"trace:{idx}",
                "signal_stream": "action",
                "payload": {"reward": {"notification_dismissed": True, "observed_at": "2026-07-01T20:00:00-07:00"}},
            })
        signals = CodexSemanticAnnotator().propose(records, user_scope_id="u")
        self.assertTrue(signals)
        self.assertTrue(signals[0].evidence)


if __name__ == "__main__":
    unittest.main()
