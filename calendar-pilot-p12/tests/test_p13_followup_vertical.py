from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.frontend.session_conversation import conversation_message_requests_existing_plan_followup


class P13FollowupVerticalTests(unittest.TestCase):
    def test_exact_time_followup_reuses_existing_plan_and_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                before = session.create_plan("Suggest the single highest-value change; only recommend it.")
                plan = session.latest_plan
                candidate = before["chat"]["candidate_cards"][0]
                frontier_count = sum(row.record_type == "frontier_generation" for row in session.replay.records)

                after = session.create_plan("What exact time and duration are you proposing? Do not replan.")

                self.assertIs(session.latest_plan, plan)
                self.assertEqual(after["chat"]["candidate_cards"][0]["candidate_id"], candidate["candidate_id"])
                self.assertEqual(
                    sum(row.record_type == "frontier_generation" for row in session.replay.records),
                    frontier_count,
                )
                followup = next(row for row in reversed(session.replay.records) if row.record_type == "existing_plan_followup")
                self.assertEqual(followup.payload["plan_id"], plan.plan_id)
                self.assertEqual(followup.payload["candidate_id"], candidate["candidate_id"])
                self.assertTrue(followup.payload["resolved_from_existing_evidence"])
                message = after["chat"]["messages"][-1]
                self.assertEqual(message["title"], "Current proposal details")
                self.assertIn("25 minutes", message["body"])
                self.assertTrue(message["metadata"]["followup_resolved_from_existing_evidence"])
            finally:
                session.close()

    def test_followup_classifier_requires_plan_preservation_language(self) -> None:
        self.assertTrue(conversation_message_requests_existing_plan_followup("what exact time and duration do not replan"))
        self.assertFalse(conversation_message_requests_existing_plan_followup("what time should we plan a new meeting"))


if __name__ == "__main__":
    unittest.main()
