from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from calendar_pilot.frontend.session import DogfoodSessionState
from evals.dogfood.admissibility import check_replay_parent_resolution


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "experiments/configs/create_prep_block_required_fields_v1.json"
SCHEMA_PATH = ROOT / "contracts/required_field_manifest.schema.json"
PROTECTED_FIELDS = {
    "candidate_id", "control_notes", "intent", "model_story", "rank",
    "required_authority_tier", "reward_breakdown", "right_moment_decision",
    "status_hint", "subtitle", "title", "type",
}


def _card(view: dict) -> dict:
    return next(row for row in view["frontier"]["candidates"] if row.get("intent") == "create_prep_block")


class P13CitedReadSideTests(unittest.TestCase):
    def test_required_field_manifest_is_versioned_exact_and_registered(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        versions = json.loads((ROOT / "contracts/VERSIONS.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(manifest)
        self.assertEqual(set(manifest["protected_fields"]), PROTECTED_FIELDS)
        self.assertEqual(versions["required_field_manifest.schema.json"], "v1")
        self.assertEqual({row["control_id"] for row in manifest["controls"]}, {"simulate", "stage", "commit"})

    def test_cited_view_preserves_card_fields_and_incumbent_controls(self):
        with patch.dict("os.environ", {"CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE": "cited"}), tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                incumbent = _card({"frontier": {"candidates": session.create_plan("Make next week less chaotic")["chat"]["candidate_cards"]}})
                view = session.view()
                cited = _card(view)
                self.assertEqual({key: cited.get(key) for key in PROTECTED_FIELDS}, {key: incumbent.get(key) for key in PROTECTED_FIELDS})
                self.assertEqual(cited["citation"]["projection_version"], "product_core.cited_candidate_card.v1")
                row_ids = {
                    str(record.payload.get("journal_event", {}).get("row_id"))
                    for record in session.replay.records
                    if record.record_type == "product_core_journal_event"
                }
                self.assertTrue(set(cited["citation"]["event_ids"]).issubset(row_ids))
                self.assertTrue(cited["projection"]["title"])
                self.assertTrue(cited["projection"]["start"])
                self.assertEqual({row["effect_owner"] for row in cited["controls"]}, {"incumbent"})
                self.assertEqual({row["authority_source"] for row in cited["controls"]}, {"incumbent_swift_gate"})
                self.assertEqual(cited["new_effect_counts"], {
                    "effect_attempts": 0, "claims": 0, "dispatches": 0, "provider_mutations": 0,
                })
                self.assertEqual(view["read_side"]["status"], "pass")
            finally:
                session.close()

    def test_exported_product_core_journal_parents_resolve_in_replay_namespace(self):
        with patch.dict("os.environ", {"CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE": "cited"}), tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            try:
                session.create_plan("Make next week less chaotic")
            finally:
                session.close()
            result = check_replay_parent_resolution(run_dir)
            self.assertEqual(result["status"], "pass", result["violations"])
            product_core_rows = [
                row for row in session.replay.records
                if row.record_type == "product_core_journal_event" and row.causal_parent_id
            ]
            self.assertTrue(product_core_rows)
            self.assertTrue(all(row.causal_parent_id.startswith("product_core_journal_event:") for row in product_core_rows))

    def test_cited_view_is_restart_stable_and_incumbent_selector_remains_available(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with patch.dict("os.environ", {"CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE": "cited"}):
                session = DogfoodSessionState(run_dir=run_dir)
                try:
                    session.create_plan("Make next week less chaotic")
                    before = _card(session.view())
                finally:
                    session.close()
                restored = DogfoodSessionState(run_dir=run_dir)
                try:
                    self.assertEqual(_card(restored.view()), before)
                finally:
                    restored.close()
            with patch.dict("os.environ", {"CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE": "incumbent"}):
                incumbent = DogfoodSessionState(run_dir=run_dir)
                try:
                    view = incumbent.view()
                    self.assertNotIn("citation", _card(view))
                    self.assertEqual(view["read_side"]["mode"], "incumbent")
                finally:
                    incumbent.close()

    def test_tampered_journal_event_holds_and_falls_back_to_incumbent_projection(self):
        with patch.dict("os.environ", {"CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE": "cited"}), tempfile.TemporaryDirectory() as td:
            session = DogfoodSessionState(run_dir=Path(td))
            try:
                session.create_plan("Make next week less chaotic")
                record = next(row for row in session.replay.records if row.record_type == "product_core_journal_event")
                record.payload["journal_event"]["content_sha256"] = "0" * 64
                view = session.view()
                self.assertEqual(view["read_side"]["status"], "hold")
                self.assertTrue(view["read_side"]["failures"])
                self.assertNotIn("citation", _card(view))
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
