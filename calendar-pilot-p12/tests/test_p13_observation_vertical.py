from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.frontend.session_conversation import conversation_message_requests_calendar_observation


class P13ObservationVerticalTests(unittest.TestCase):
    def test_read_only_calendar_question_emits_cited_facts_without_frontier_or_stage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                snapshot = session.create_plan("What do you know about my calendar tomorrow? Cite the events or gaps used.")
                self.assertIsNone(session.latest_plan)
                observation = next(row for row in session.replay.records if row.record_type == "calendar_observation")
                self.assertEqual(set(observation.payload["fact_ids"]), {"evt_client_call", "evt_admin", "evt_team_sync"})
                tool_names = {
                    row.payload.get("call", {}).get("tool_name")
                    for row in session.replay.records
                    if row.record_type == "codex_tool_call"
                }
                self.assertNotIn("generate_candidate_frontier", tool_names)
                self.assertNotIn("stage_action_packet", tool_names)
                message = next(row for row in snapshot["chat"]["messages"] if row.get("title") == "Tomorrow's calendar evidence")
                self.assertEqual(message["cards"][0]["type"], "observation")
                self.assertEqual(set(message["cards"][0]["citation_ids"]), set(observation.payload["fact_ids"]))
                self.assertEqual(snapshot["chat"]["candidate_cards"], [])
            finally:
                session.close()

    def test_observation_classifier_does_not_capture_recommendation_requests(self) -> None:
        self.assertTrue(conversation_message_requests_calendar_observation("what do you know about my calendar tomorrow cite the events or gaps used"))
        self.assertFalse(conversation_message_requests_calendar_observation("suggest a calendar change and cite the events"))


if __name__ == "__main__":
    unittest.main()
