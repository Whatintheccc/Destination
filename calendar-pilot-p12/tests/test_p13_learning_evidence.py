from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.replay import payload_sha256


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "contracts/learning_evidence_event.schema.json").read_text(encoding="utf-8"))


class P13LearningEvidenceTests(unittest.TestCase):
    def _session(self, root: str) -> DogfoodSessionState:
        return DogfoodSessionState(run_dir=Path(root))

    def test_atomic_decision_rendered_exposure_and_explicit_outcome_chain(self):
        with tempfile.TemporaryDirectory() as td:
            session = self._session(td)
            try:
                session.create_plan("Make next week less chaotic")
                decisions = [row for row in session.replay.records if row.record_type == "learning_decision"]
                self.assertEqual(len(decisions), 1)
                decision = decisions[0]
                Draft202012Validator(SCHEMA).validate(decision.payload)
                self.assertEqual(decision.payload["session_id"], session.session_id)
                self.assertEqual(decision.payload["selected"]["selection_mode"], "deterministic")
                self.assertEqual(decision.payload["selected"]["propensity"], 1.0)
                eligible_ids = [row["candidate_id"] for row in decision.payload["eligible_set"]]
                self.assertEqual(len(eligible_ids), len(set(eligible_ids)))
                self.assertEqual(decision.payload["selected"]["candidate_id"], eligible_ids[0])
                self.assertEqual(
                    decision.payload["selected_behavior_payload_sha256"],
                    payload_sha256(decision.payload["selected_behavior_payload"]),
                )
                frontier = next(row for row in session.replay.records if row.record_type == "frontier_generation")
                self.assertEqual(decision.causal_parent_id, frontier.record_id)

                rendered = eligible_ids[: min(2, len(eligible_ids))]
                exposure_result = session.learning_exposure(decision.record_id, rendered, surface="operate")
                exposure = session._learning_record(exposure_result["exposure_id"], "learning_exposure")
                Draft202012Validator(SCHEMA).validate(exposure.payload)
                self.assertEqual(exposure.causal_parent_id, decision.record_id)
                self.assertEqual(exposure.payload["rendered_candidate_ids"], rendered)
                self.assertEqual(exposure.payload["eligible_candidate_ids"], eligible_ids)
                duplicate = session.learning_exposure(decision.record_id, rendered, surface="operate")
                self.assertTrue(duplicate["duplicate"])

                outcome_result = session.learning_outcome(
                    decision_id=decision.record_id,
                    exposure_id=exposure.record_id,
                    candidate_id=rendered[0],
                    outcome="accepted",
                    reason="explicit candidate-card feedback",
                )
                outcome = session._learning_record(outcome_result["outcome_id"], "learning_outcome")
                Draft202012Validator(SCHEMA).validate(outcome.payload)
                self.assertEqual(outcome.signal_stream, "action")
                self.assertEqual(outcome.causal_parent_id, exposure.record_id)
                self.assertEqual(outcome.payload["outcome"], "accepted")
                with self.assertRaisesRegex(ValueError, "conflicting terminal outcome"):
                    session.learning_outcome(
                        decision_id=decision.record_id,
                        exposure_id=exposure.record_id,
                        candidate_id=rendered[0],
                        outcome="dismissed",
                    )
                unrendered = next((candidate_id for candidate_id in eligible_ids if candidate_id not in rendered), "not-eligible")
                with self.assertRaisesRegex(ValueError, "not rendered"):
                    session.learning_outcome(
                        decision_id=decision.record_id,
                        exposure_id=exposure.record_id,
                        candidate_id=unrendered,
                        outcome="dismissed",
                    )

                evidence = session.snapshot()["learning"]["evidence"]
                self.assertEqual(evidence["latest_decision"]["decision_id"], decision.record_id)
                self.assertEqual(evidence["latest_exposure"]["exposure_id"], exposure.record_id)
                self.assertEqual(evidence["program_a"]["matched_examples"], 1)
                self.assertEqual(evidence["program_a"]["explicit_feedback"], 1)
                self.assertFalse(evidence["formal_epoch_bound"])
            finally:
                session.close()

    def test_missing_exposure_and_non_ui_terminal_outcomes_hold(self):
        with tempfile.TemporaryDirectory() as td:
            session = self._session(td)
            try:
                session.create_plan("Make next week less chaotic")
                decision = next(row for row in session.replay.records if row.record_type == "learning_decision")
                eligible_ids = [row["candidate_id"] for row in decision.payload["eligible_set"]]
                with self.assertRaisesRegex(ValueError, "non-empty subset"):
                    session.learning_exposure(decision.record_id, [], surface="operate")
                with self.assertRaisesRegex(ValueError, "non-empty subset"):
                    session.learning_exposure(decision.record_id, ["forged"], surface="operate")
                exposure_id = session.learning_exposure(decision.record_id, eligible_ids[:1])["exposure_id"]
                with self.assertRaisesRegex(ValueError, "UI may record only explicit"):
                    session.learning_outcome(
                        decision_id=decision.record_id,
                        exposure_id=exposure_id,
                        candidate_id=eligible_ids[0],
                        outcome="ignored",
                    )
            finally:
                session.close()

    def test_elapsed_window_becomes_ignored_and_superseded_window_becomes_censored(self):
        with tempfile.TemporaryDirectory() as td:
            session = self._session(td)
            try:
                session.create_plan("Make next week less chaotic")
                first = next(row for row in session.replay.records if row.record_type == "learning_decision")
                rendered = [first.payload["eligible_set"][0]["candidate_id"]]
                exposure_id = session.learning_exposure(first.record_id, rendered)["exposure_id"]
                ends_at = datetime.fromisoformat(first.payload["outcome_window"]["ends_at"])
                session._finalize_learning_outcomes(now=ends_at + timedelta(seconds=1), superseded=False)
                ignored = session._learning_outcome_for(exposure_id, rendered[0])
                self.assertEqual(ignored.payload["outcome"], "ignored")
                self.assertIsNone(ignored.payload["censoring_reason"])
                Draft202012Validator(SCHEMA).validate(ignored.payload)

                session.reset()
                session.create_plan("Make next week less chaotic")
                second = next(row for row in session.replay.records if row.record_type == "learning_decision")
                second_rendered = [second.payload["eligible_set"][0]["candidate_id"]]
                second_exposure_id = session.learning_exposure(second.record_id, second_rendered)["exposure_id"]
                starts_at = datetime.fromisoformat(second.payload["outcome_window"]["starts_at"])
                session._finalize_learning_outcomes(now=starts_at + timedelta(seconds=1), superseded=True)
                censored = session._learning_outcome_for(second_exposure_id, second_rendered[0])
                self.assertEqual(censored.payload["outcome"], "censored")
                self.assertEqual(censored.payload["censoring_reason"], "superseded_by_new_decision")
                Draft202012Validator(SCHEMA).validate(censored.payload)
            finally:
                session.close()

    def test_learning_evidence_survives_restart(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = self._session(td)
            session.create_plan("Make next week less chaotic")
            decision = next(row for row in session.replay.records if row.record_type == "learning_decision")
            candidate_id = decision.payload["eligible_set"][0]["candidate_id"]
            exposure_id = session.learning_exposure(decision.record_id, [candidate_id])["exposure_id"]
            session.learning_outcome(
                decision_id=decision.record_id,
                exposure_id=exposure_id,
                candidate_id=candidate_id,
                outcome="corrected",
                reason="wrong time",
            )
            session.close()

            restored = DogfoodSessionState(run_dir=run_dir)
            try:
                record_types = [row.record_type for row in restored.replay.records]
                self.assertIn("learning_decision", record_types)
                self.assertIn("learning_exposure", record_types)
                self.assertIn("learning_outcome", record_types)
                outcome = restored._learning_outcome_for(exposure_id, candidate_id)
                self.assertEqual(outcome.payload["reason"], "wrong time")
            finally:
                restored.close()


if __name__ == "__main__":
    unittest.main()
