from __future__ import annotations

import unittest

from evals.dogfood.capture.normalize_d1 import effect_counts, internal_action, visible_action


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


if __name__ == "__main__":
    unittest.main()
