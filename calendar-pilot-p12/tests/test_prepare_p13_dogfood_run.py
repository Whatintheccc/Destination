from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from scripts.prepare_p13_dogfood_run import (
    ROOT,
    SCENARIO_SET,
    TRUTH_SCHEMA,
    fixture_truth,
    required_artifacts,
    selected_scenarios,
)


class PrepareP13DogfoodRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario_set = json.loads(SCENARIO_SET.read_text(encoding="utf-8"))

    def test_cell_selection_retains_frozen_scenario_order(self) -> None:
        self.assertEqual([row["scenario_id"] for row in selected_scenarios(self.scenario_set, "D0")], ["P-IDENTITY"])
        self.assertEqual(
            [row["scenario_id"] for row in selected_scenarios(self.scenario_set, "D1")],
            ["P-IDENTITY", "P-OBSERVE", "P-RECOMMEND", "P-ACTION-VISIBLE", "P-TIMEZONE", "P-FOLLOWUP", "P-CORRECTION", "P-SIMULATE", "P-NOOP", "P-FEEDBACK", "P-RESTART"],
        )

    def test_d7_extends_common_inventory_without_duplicates(self) -> None:
        d1 = required_artifacts(self.scenario_set, "D1")
        d7 = required_artifacts(self.scenario_set, "D7")
        self.assertEqual(d7[:len(d1)], d1)
        self.assertEqual(d7[-2:], ["provider.after.json", "provider.after_undo.json"])
        self.assertEqual(len(d7), len(set(d7)))

    def test_fixture_truth_is_minimal_hashed_and_schema_valid(self) -> None:
        truth = fixture_truth("run-1", datetime.now(timezone.utc).isoformat(), ROOT / "data/sample_calendar.json")
        schema = json.loads(TRUTH_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(truth)
        self.assertEqual([row["fact_id"] for row in truth["facts"]], ["evt_client_call", "evt_admin", "evt_team_sync"])
        self.assertTrue(all(set(row["value"]) == {"event_id", "start", "end", "calendar_id", "is_user_owned", "is_flexible", "category"} for row in truth["facts"]))
        serialized = json.dumps(truth)
        self.assertNotIn("client@example.com", serialized)
        self.assertNotIn("Discuss renewal options", serialized)


if __name__ == "__main__":
    unittest.main()
