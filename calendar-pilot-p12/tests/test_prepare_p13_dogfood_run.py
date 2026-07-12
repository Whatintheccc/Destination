from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from scripts.prepare_p13_dogfood_run import (
    ROOT,
    RUNTIME_BINDINGS,
    SCENARIO_SET,
    TRUTH_SCHEMA,
    fixture_truth,
    live_event_truth,
    live_gap_truth,
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

    def test_runtime_binding_completes_manifest_runtime_contract(self) -> None:
        runtime = {"requested_mode": "fixture", **RUNTIME_BINDINGS["fixture"]}
        self.assertEqual(set(runtime), {"requested_mode", "expected_backends", "credential_classes"})
        self.assertEqual(runtime["requested_mode"], "fixture")
        self.assertEqual(RUNTIME_BINDINGS["auto"]["expected_backends"], {
            "codex": "live_codex_app_server",
            "diffusiongemma": "nvidia_nim_diffusiongemma_policy",
            "kernel": "SwiftKernelIPCClient",
            "provider": "apple_eventkit",
        })

    def test_d6_reuses_live_read_scenarios_without_effect_or_undo(self) -> None:
        scenario_ids = [row["scenario_id"] for row in selected_scenarios(self.scenario_set, "D6")]
        self.assertIn("P-LIVE-READ", scenario_ids)
        self.assertNotIn("P-EFFECT", scenario_ids)
        self.assertNotIn("P-UNDO", scenario_ids)

    def test_fixture_truth_is_minimal_hashed_and_schema_valid(self) -> None:
        truth = fixture_truth("run-1", datetime.now(timezone.utc).isoformat(), ROOT / "data/sample_calendar.json")
        schema = json.loads(TRUTH_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(truth)
        self.assertEqual(
            [row["fact_id"] for row in truth["facts"]],
            ["evt_client_call", "evt_admin", "evt_team_sync", "fixture:noop_dominates"],
        )
        noop = truth["facts"][-1]
        self.assertEqual(noop["kind"], "fixture_truth")
        self.assertTrue(noop["value"]["noop_dominates"])
        calendar_facts = [row for row in truth["facts"] if row["kind"] == "calendar_event"]
        self.assertTrue(all(set(row["value"]) == {"event_id", "start", "end", "calendar_id", "is_user_owned", "is_flexible", "category"} for row in calendar_facts))
        serialized = json.dumps(truth)
        self.assertNotIn("client@example.com", serialized)
        self.assertNotIn("Discuss renewal options", serialized)

    def test_live_gap_truth_binds_empty_ui_verified_window_and_isolates_noop_fixture(self) -> None:
        truth = live_gap_truth(
            "run-live",
            datetime.now(timezone.utc).isoformat(),
            timezone_name="America/Los_Angeles",
            time_min="2026-07-12T00:00:00-07:00",
            time_max="2026-07-13T00:00:00-07:00",
        )
        schema = json.loads(TRUTH_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(truth)
        self.assertEqual(truth["provider_identity"], "apple_eventkit")
        self.assertEqual(truth["redaction_class"], "sensitive_local_only")
        gap, noop = truth["facts"]
        self.assertEqual(gap["kind"], "calendar_gap")
        self.assertEqual(gap["value"]["event_count"], 0)
        self.assertEqual(noop["value"]["execution_scope"], "isolated_shadow")

    def test_d7_live_event_truth_binds_one_exact_parent_and_window(self) -> None:
        truth = live_event_truth(
            "run-d7",
            datetime.now(timezone.utc).isoformat(),
            timezone_name="America/Los_Angeles",
            time_min="2026-07-18T07:00:00-07:00",
            time_max="2026-07-18T12:00:00-07:00",
            event={
                "event_id": "event-parent",
                "start": "2026-07-18T09:00:00-07:00",
                "end": "2026-07-18T09:30:00-07:00",
                "calendar_id": "sandbox-calendar",
                "is_user_owned": True,
                "is_flexible": False,
                "category": "work",
            },
        )
        schema = json.loads(TRUTH_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(truth)
        event, window = truth["facts"]
        self.assertEqual((event["kind"], event["fact_id"]), ("calendar_event", "event-parent"))
        self.assertEqual(window["value"]["event_count"], 1)
        self.assertEqual(window["value"]["verification_method"], "temporary_attendee_free_parent_fixture")

    def test_d7_live_event_truth_rejects_parent_outside_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "fully contained"):
            live_event_truth(
                "run-d7", datetime.now(timezone.utc).isoformat(),
                timezone_name="UTC", time_min="2026-07-18T08:00:00+00:00", time_max="2026-07-18T09:00:00+00:00",
                event={"event_id": "outside", "start": "2026-07-18T10:00:00+00:00", "end": "2026-07-18T10:30:00+00:00", "calendar_id": "sandbox"},
            )


if __name__ == "__main__":
    unittest.main()
