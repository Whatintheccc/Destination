from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.environment.action_lifecycle import ActionLifecycle
from calendar_pilot.environment.session_store import SessionStore
from calendar_pilot.providers.deterministic import DeterministicCalendarProvider
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import RawCalendarObservation, UserBiography

ROOT = Path(__file__).resolve().parents[1]


def load_obs():
    return RawCalendarObservation.from_dict(json.loads((ROOT / 'data/sample_calendar.json').read_text()))


def load_bio():
    return UserBiography.from_dict(json.loads((ROOT / 'data/sample_profile.json').read_text()))


class ActionLifecycleAndStoreTests(unittest.TestCase):
    def test_action_lifecycle_commit_emits_legacy_and_v2_envelope(self):
        obs = load_obs()
        bio = load_bio()
        candidate = DiffusionGemmaPolicy().generate_candidates(obs, bio)[0]
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=3, issued_at=obs.observed_at, confirmed_by_user=True)
        replay = ReplayBuffer()
        lifecycle = ActionLifecycle(kernel=kernel, replay=replay, provider=DeterministicCalendarProvider(seed_observation=obs))
        result = lifecycle.commit(candidate, obs, grant.grant_id, requested_authority_tier=3, trace_id='test_trace', require_live_observation=False)
        payload = result.output_payload()
        env = payload['action_envelope']
        self.assertEqual(env['schema_version'], 'calendar_action_envelope.v1')
        self.assertEqual(env['envelope_version'], 'calendar_action_envelope.v2')
        self.assertEqual(env['tool_status'], 'committed')
        self.assertIn(env['provider']['rollback_state'], {'pending', 'verified', 'unsupported', 'impossible'})
        self.assertTrue(any(r.record_type == 'envelope_transition' for r in replay.records))

    def test_session_store_atomic_save_and_restore(self):
        with tempfile.TemporaryDirectory() as td:
            store = SessionStore(Path(td))
            replay = ReplayBuffer()
            store.save(state_payload={'session_id': 's1'}, latest_snapshot={'ok': True}, session_manifest={'m': 1}, replay=replay)
            self.assertEqual(store.load_state()['session_id'], 's1')
            self.assertTrue(store.latest_path.exists())
            self.assertTrue(store.manifest_path.exists())
            self.assertEqual(store.load_replay().records, [])


if __name__ == '__main__':
    unittest.main()
