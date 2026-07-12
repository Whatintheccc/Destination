from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from evals.dogfood.capture.normalize_d1 import d7_effect_evidence, d7_undo_evidence, effect_counts, extract_candidate_dom, ids_from_dom, internal_action, latest_provider_transaction, latest_tool_receipt, restart_digest, visible_action
from evals.dogfood.predicates.product import evaluate_predicate
from scripts.run_p13_dogfood_d1 import health_matches_launch


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

    def test_d7_receipt_extractors_select_exact_terminal_operations(self) -> None:
        raw = {"replay_export": {"records": [
            {"record_type": "codex_tool_receipt", "payload": {"receipt": {"tool_name": "request_commit", "status": "denied"}}},
            {"record_type": "codex_tool_receipt", "payload": {"receipt": {"tool_name": "request_commit", "status": "committed", "output": {"effect_ticket": {"ticket_id": "t1"}}}}},
            {"record_type": "provider_transaction", "payload": {"operation": "commit", "transaction": {"external_ids": ["e1"]}}},
            {"record_type": "provider_transaction", "payload": {"operation": "rollback", "transaction": {"rollback_verified": True}}},
        ]}}
        self.assertEqual(latest_tool_receipt(raw, "request_commit", "committed")["output"]["effect_ticket"]["ticket_id"], "t1")
        self.assertEqual(latest_provider_transaction(raw, "commit")["external_ids"], ["e1"])
        self.assertTrue(latest_provider_transaction(raw, "rollback")["rollback_verified"])

    def test_d7_ledger_derivation_satisfies_exact_effect_and_undo_predicates(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            run_dir = Path(name)
            capture = run_dir / "ruler_capture"
            capture.mkdir()
            binding = {"binding_id": "binding-1", "epoch": 1}
            candidate = {"candidate_id": "c1", "action": {"attendees": [], "calendar_id": "sandbox"}}
            (run_dir / "managed-binding.json").write_text(json.dumps(binding))
            (run_dir / "d7_candidate.json").write_text(json.dumps({"candidate": candidate}))
            apply = {"ticket_id": "apply-1", "kind": "apply", "action_family": "create_prep_block", "grant_id": "grant-apply", "idempotency_key": "idem-1", "target_binding": {"binding_id": "binding-1", "binding_epoch": 1}}
            compensate = {"ticket_id": "undo-1", "kind": "compensate", "grant_id": "grant-undo", "target_receipt_hash": "receipt-hash"}
            after_commit = {
                "tickets": {"apply-1": {"ticket": apply}},
                "outbox": {"apply-1": {"facts": ["claim", "dispatch", "unknown", "verified"]}},
                "receipts": {"apply-1": {"phase": "verified"}},
                "adapter_state": {"mutation_count": 1, "compensation_mutation_count": 0},
            }
            final = {
                "tickets": {"apply-1": {"ticket": apply}, "undo-1": {"ticket": compensate}},
                "outbox": {"apply-1": {"facts": ["claim", "dispatch", "unknown", "verified"]}, "undo-1": {"facts": ["claim", "dispatch", "unknown", "verified"]}},
                "receipts": {"apply-1": {"phase": "verified"}, "undo-1": {"phase": "verified"}},
                "adapter_state": {"mutation_count": 1, "compensation_mutation_count": 1},
            }
            for filename, value in (("ledger.after_commit.raw.json", after_commit), ("ledger.after_undo.raw.json", final), ("ledger.after_restart.raw.json", final), ("provider.after.raw.json", {"events": [{"event_id": "event-1"}]}), ("provider.after_undo.raw.json", {"events": []})):
                (capture / filename).write_text(json.dumps(value))
            raw = {"replay_export": {"records": [
                {"record_type": "codex_tool_receipt", "payload": {"receipt": {"tool_name": "request_commit", "status": "committed", "output": {"swift_receipt": {"generated_event_ids": ["event-1"]}, "retirement": {"owner": "effect_kernel"}}}}},
                {"record_type": "provider_transaction", "payload": {"operation": "commit", "transaction": {"external_ids": ["event-1"], "effect_receipt_sha256": "receipt-hash"}}},
                {"record_type": "provider_transaction", "payload": {"operation": "rollback", "transaction": {"rollback_verified": True}}},
            ]}}
            effect = d7_effect_evidence(run_dir, raw)
            undo = d7_undo_evidence(run_dir, raw)
            effect_vector = {"records": {"replay": [{"effect": effect}]}, "present_sources": ["replay", "ui_action", "provider_after"], "required_sources": ["replay", "ui_action", "provider_after"], "scenario_record_count": 1}
            undo_vector = {"records": {"replay": [{"undo": undo}]}, "present_sources": ["replay", "ui_action", "provider_after_undo", "launch_state_after"], "required_sources": ["replay", "ui_action", "provider_after_undo", "launch_state_after"], "scenario_record_count": 1}
            self.assertEqual(evaluate_predicate("effect", effect_vector)["status"], "pass")
            self.assertEqual(evaluate_predicate("undo", undo_vector)["status"], "pass")

            final["outbox"]["undo-1"]["facts"].append("dispatch")
            (capture / "ledger.after_restart.raw.json").write_text(json.dumps(final))
            self.assertEqual(d7_undo_evidence(run_dir, raw)["restart_redispatch_count"], 1)

    def test_packaged_health_readiness_is_identity_based_not_status_label_based(self) -> None:
        launch = {"base_url": "http://127.0.0.1:8787", "build_id": "abc", "runtime_mode": "fixture", "server_pid": 12, "launch_id": "launch-1", "port": 8787}
        health = {"build_id": "abc", "runtime_mode": "fixture", "process": {"server_pid": 12, "launch_id": "launch-1", "port": 8787}}
        self.assertTrue(health_matches_launch(launch, health))
        self.assertFalse(health_matches_launch(launch, {**health, "build_id": "wrong"}))

    def test_dom_identity_extraction_preserves_visible_order(self) -> None:
        dom = '<div data-candidate-id="leading"></div><div data-candidate-id="second"></div><div data-candidate-id="leading"></div>'
        self.assertEqual(ids_from_dom(dom, "data-candidate-id"), ["leading", "second"])

    def test_candidate_dom_extraction_keeps_duplicate_testids_card_local(self) -> None:
        dom = '''
        <div data-testid="candidate-card" data-candidate-id="leading"><div data-testid="candidate-addresses-goal">true</div><div data-testid="candidate-compares-noop">true</div></div>
        <div data-testid="candidate-card" data-candidate-id="second"><div data-testid="candidate-addresses-goal">false</div><div data-testid="candidate-compares-noop">false</div></div>
        '''
        self.assertEqual(extract_candidate_dom(dom), [
            {"candidate_id": "leading", "fields": {"candidate-card": "", "candidate-addresses-goal": "true", "candidate-compares-noop": "true"}},
            {"candidate_id": "second", "fields": {"candidate-card": "", "candidate-addresses-goal": "false", "candidate-compares-noop": "false"}},
        ])

    def test_restart_digest_ignores_process_replacement_but_not_runtime_semantics(self) -> None:
        base = {
            "view": {
                "conversation": {"messages": []},
                "frontier": {"generation_id": "plan-1", "goal": "goal", "candidates": []},
                "pipeline": {"turns": [{"trace_id": "ephemeral"}]},
                "runtime": {
                    "build_id": "abc",
                    "runtime_mode": "fixture",
                    "requested_runtime_mode": "fixture",
                    "backends": {"provider": "deterministic_fixture_provider"},
                    "fixture_mode": True,
                    "fixture_paths": {"active_observation_id": "obs-1", "uses_sample_fixtures": True, "provider_observation_loaded": False},
                    "process": {"pid": 10, "launch_id": "before"},
                    "live_target": False,
                    "production_target": False,
                    "valid_runtime_mode": True,
                },
            },
            "replay_export": {"records": []},
        }
        after = deepcopy(base)
        after["view"]["pipeline"] = {"turns": []}
        after["view"]["runtime"]["process"] = {"pid": 20, "launch_id": "after"}
        before_digest = restart_digest(base, "before")
        after_digest = restart_digest(after, "after")
        self.assertEqual(before_digest["before_plan_digest"], after_digest["after_plan_digest"])
        self.assertEqual(before_digest["before_runtime_digest"], after_digest["after_runtime_digest"])

        after["view"]["runtime"]["backends"]["provider"] = "apple_eventkit"
        changed = restart_digest(after, "after")
        self.assertNotEqual(before_digest["before_runtime_digest"], changed["after_runtime_digest"])


if __name__ == "__main__":
    unittest.main()
