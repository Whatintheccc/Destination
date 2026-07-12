from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.types import RawCalendarObservation, to_jsonable


class P13CorrectionVerticalTests(unittest.TestCase):
    def test_explicit_correction_shortens_focus_window_on_empty_calendar(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                payload = to_jsonable(session.observation)
                payload.update({"observation_id": "obs_empty_calendar", "events": [], "tasks": []})
                session.observation = RawCalendarObservation.from_dict(payload)
                session.provider.reset(session.observation)
                before = session.create_plan("Suggest the single highest-value change; only recommend it.")
                card = before["chat"]["candidate_cards"][0]
                self.assertEqual(card["intent"], "protect_deep_work")
                self.assertEqual(card["action"]["duration_minutes"], 90)
                decision = next(row for row in reversed(session.replay.records) if row.record_type == "learning_decision")
                exposure_id = session.learning_exposure(decision.record_id, [card["candidate_id"]])["exposure_id"]
                session.learning_outcome(
                    decision_id=decision.record_id,
                    exposure_id=exposure_id,
                    candidate_id=card["candidate_id"],
                    outcome="corrected",
                    reason="Explicit UI command: shorten the selected timed action by 10 minutes.",
                )

                after = session.create_plan("Correct one cited assumption, then ask for the recommendation again.")

                corrected = after["chat"]["candidate_cards"][0]
                self.assertEqual(corrected["intent"], "protect_deep_work")
                self.assertEqual(corrected["action"]["duration_minutes"], 80)
                self.assertTrue(after["correction"]["new_plan_uses_correction"])
                self.assertEqual(after["action_queue"], [])
            finally:
                session.close()

    def test_explicit_card_correction_causally_changes_recommendation_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                before = session.create_plan("Suggest the single highest-value change; only recommend it.")
                card = before["chat"]["candidate_cards"][0]
                self.assertEqual(card["action"]["duration_minutes"], 25)
                decision = next(row for row in reversed(session.replay.records) if row.record_type == "learning_decision")
                exposure_id = session.learning_exposure(decision.record_id, [card["candidate_id"]])["exposure_id"]
                session.learning_outcome(
                    decision_id=decision.record_id,
                    exposure_id=exposure_id,
                    candidate_id=card["candidate_id"],
                    outcome="corrected",
                    reason="Explicit UI command: shorten the selected timed action by 10 minutes.",
                )

                after = session.create_plan("Correct one cited assumption, then ask for the recommendation again.")

                corrected = after["chat"]["candidate_cards"][0]
                self.assertEqual(corrected["action"]["duration_minutes"], 15)
                self.assertEqual(after["action_queue"], [])
                evidence = after["correction"]
                self.assertFalse(evidence["old_belief_active"])
                self.assertTrue(evidence["new_plan_uses_correction"])
                self.assertEqual(evidence["before_authority_digest"], evidence["after_authority_digest"])
                self.assertIn(evidence["command_id"], evidence["citation_ids"])
                self.assertIn(exposure_id, evidence["citation_ids"])
                self.assertIn(decision.record_id, evidence["citation_ids"])
                application = next(
                    row for row in reversed(session.replay.records)
                    if row.record_type == "candidate_correction_application"
                )
                self.assertEqual(application.causal_parent_id, evidence["command_id"])
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
