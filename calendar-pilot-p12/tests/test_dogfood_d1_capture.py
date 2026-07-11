from __future__ import annotations

import unittest

from evals.dogfood.capture.normalize_d1 import effect_counts, ids_from_dom, internal_action, visible_action
from scripts.run_p13_dogfood_d1 import health_matches_launch


class DogfoodD1CaptureTests(unittest.TestCase):
    def test_internal_action_projects_frozen_twelve_field_contract(self) -> None:
        raw = {"replay_export": {"records": [{
            "record_type": "learning_decision",
            "payload": {"selected_behavior_payload": {
                "candidate_id": "c1",
                "actions": [{"start": "2026-07-11T08:00:00-07:00", "end": "2026-07-11T09:30:00-07:00", "calendar_id": "work", "title": "Focus", "attendees": []}],
                "affected_event_ids": ["event-1"],
                "affected_people_ids": [],
                "reversibility": "high",
                "required_authority_tier": 3,
            }},
        }]}}
        self.assertEqual(internal_action(raw, "America/Los_Angeles"), {
            "local_date": "2026-07-11",
            "timezone": "America/Los_Angeles",
            "start": "2026-07-11T08:00:00-07:00",
            "end": "2026-07-11T09:30:00-07:00",
            "duration_minutes": 90,
            "calendar_id": "work",
            "title": "Focus",
            "attendees": [],
            "affected_ids": ["event-1"],
            "conflicts": [],
            "reversibility": "high",
            "authority_need": 3,
        })

    def test_visible_action_uses_only_independently_captured_testids(self) -> None:
        semantic = {
            "candidate-start": "2026-07-11T08:00:00-07:00",
            "candidate-duration-minutes": "90",
            "candidate-attendees": "[]",
            "candidate-affected-ids": '["event-1"]',
        }
        self.assertEqual(visible_action(semantic), {
            "start": "2026-07-11T08:00:00-07:00",
            "duration_minutes": 90,
            "attendees": [],
            "affected_ids": ["event-1"],
        })

    def test_effect_counts_detects_automatic_stage_without_calling_simulation_an_effect(self) -> None:
        rows = [
            {"record_type": "codex_tool_call", "payload": {"call": {"tool_name": "simulate_action_program"}}},
            {"record_type": "codex_tool_call", "payload": {"call": {"tool_name": "stage_action_packet"}}},
            {"record_type": "effect_attempt", "payload": {}},
        ]
        self.assertEqual(effect_counts(rows), {
            "provider_mutations": 0,
            "effect_attempts": 1,
            "stage_actions": 1,
            "claims": 0,
            "outbox_dispatches": 0,
        })

    def test_packaged_health_readiness_is_identity_based_not_status_label_based(self) -> None:
        launch = {"base_url": "http://127.0.0.1:8787", "build_id": "abc", "runtime_mode": "fixture", "server_pid": 12, "launch_id": "launch-1", "port": 8787}
        health = {"build_id": "abc", "runtime_mode": "fixture", "process": {"server_pid": 12, "launch_id": "launch-1", "port": 8787}}
        self.assertTrue(health_matches_launch(launch, health))
        self.assertFalse(health_matches_launch(launch, {**health, "build_id": "wrong"}))

    def test_dom_identity_extraction_preserves_visible_order(self) -> None:
        dom = '<div data-candidate-id="leading"></div><div data-candidate-id="second"></div><div data-candidate-id="leading"></div>'
        self.assertEqual(ids_from_dom(dom, "data-candidate-id"), ["leading", "second"])


if __name__ == "__main__":
    unittest.main()
