from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from calendar_pilot.frontend.session import DogfoodSessionState


class P13RecommendationVerticalTests(unittest.TestCase):
    def test_recommendation_stops_before_simulation_and_stage_and_compares_noop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                snapshot = session.create_plan("Suggest the single highest-value change. Explain why, including no-op, but only recommend it; do not stage or change my calendar.")
                self.assertIsNotNone(session.latest_plan)
                names = [call.tool_name.value for call in session.latest_plan.calls]
                self.assertEqual(names, ["inspect_week", "generate_candidate_frontier", "compare_candidates"])
                self.assertEqual(session.latest_plan.recommended_next_action, "recommendation_ready")
                decision = next(row for row in reversed(session.replay.records) if row.record_type == "learning_decision")
                cards = snapshot["chat"]["candidate_cards"]
                self.assertEqual(cards[0]["candidate_id"], decision.payload["selected"]["candidate_id"])
                self.assertTrue(cards[0]["addresses_goal"])
                self.assertTrue(cards[0]["rationale_compares_noop"])
                self.assertTrue(cards[0]["counterfactual"])
                self.assertEqual(snapshot["action_queue"], [])
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
