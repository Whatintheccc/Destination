from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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
from scripts.run_p13_dogfood_d1 import prepare_args as d1_prepare_args
from scripts.run_p13_dogfood_d56 import cell_args as d56_cell_args
from scripts.run_p13_dogfood_d56 import run as run_d56


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

    def test_d7_uses_the_frozen_live_recommendation_budget(self) -> None:
        driver = (ROOT / "scripts/browser_dogfood_d1.mjs").read_text(encoding="utf-8")
        self.assertIn("['D3', 'D4', 'D6', 'D7'].includes(manifest.cell)", driver)
        self.assertEqual(self.scenario_set["performance_budgets_seconds"]["live_recommendation"], 60)

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

    def test_d56_propagates_exact_parent_and_window_into_each_cell(self) -> None:
        common = argparse.Namespace(
            app_bundle=str(ROOT / "dist/CalendarPilot.app"),
            architecture_report=str(ROOT / "runs/architecture_evals/architecture_eval_report_v2.json"),
            out_root=str(ROOT / "runs/dogfood"),
            live_timezone="America/Los_Angeles",
        )
        event_path = ROOT / "parent-event.json"
        for cell, mode in (("D5", "live_provider"), ("D6", "auto")):
            args = d56_cell_args(
                common,
                cell=cell,
                event_path=event_path,
                time_min="2026-07-18T14:00:00-07:00",
                time_max="2026-07-18T18:30:00-07:00",
                external_setup={"setup_outside_scored_cells": True},
            )
            prepared = d1_prepare_args(args)
            self.assertEqual(prepared.cell, cell)
            self.assertEqual(prepared.runtime_mode, mode)
            self.assertEqual(prepared.live_event_json, str(event_path))
            self.assertEqual(prepared.live_window_start, "2026-07-18T14:00:00-07:00")
            self.assertEqual(prepared.live_window_end, "2026-07-18T18:30:00-07:00")

    def test_d56_rejects_non_protected_source_before_external_setup(self) -> None:
        args = argparse.Namespace(
            app_bundle=str(ROOT / "dist/CalendarPilot.app"),
            architecture_report=str(ROOT / "runs/architecture_evals/architecture_eval_report_v2.json"),
            out_root=str(ROOT / "runs/dogfood"),
            calendar_id="sandbox-calendar",
            live_timezone="America/Los_Angeles",
        )
        with (
            patch("scripts.run_p13_dogfood_d56.process_identity", side_effect=RuntimeError("requires main")),
            patch("scripts.run_p13_dogfood_d56._create_managed_parent_fixture") as create_fixture,
        ):
            with self.assertRaisesRegex(RuntimeError, "requires main"):
                run_d56(args)
        create_fixture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
