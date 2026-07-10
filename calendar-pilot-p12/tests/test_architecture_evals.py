from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from evals.architecture.adapters.p12_current import P12CurrentAdapter
from evals.architecture.evaluation import (
    derive_gate_decision,
    evaluate_scenario,
    summarize_rail,
)
from evals.architecture.predicates import PREDICATES, evaluate_predicate
from evals.architecture.run_architecture_evals import (
    REQUIRED_PRESERVATION_SCENARIO_IDS,
    REQUIRED_TARGET_SCENARIO_IDS,
    build_report,
    load_scenario_set,
    validate_report,
)


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_SET_PATH = ROOT / "evals/architecture/scenarios/canonical.json"
REPORT_SCHEMA_PATH = ROOT / "contracts/architecture_eval_report.schema.json"
VERSIONS_PATH = ROOT / "contracts/VERSIONS.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _result_row(
    scenario_id: str,
    *,
    rail: str = "preservation",
    gate_mode: str = "required",
    status: str = "pass",
) -> dict[str, str]:
    return {
        "scenario_id": scenario_id,
        "rail": rail,
        "gate_mode": gate_mode,
        "status": status,
    }


def _reward_vector(stream: str) -> dict:
    row = {
        "source_artifact": "/tmp/architecture-eval-reward.jsonl",
        "row_id": "reward:observable",
        "record_type": "reward",
        "stream": stream,
        "provenance": "human_ui",
    }
    return {
        "reward": {
            "input_rows": [deepcopy(row)],
            "consumed_rows": [deepcopy(row)],
        }
    }


class ArchitectureEvalContractTests(unittest.TestCase):
    def test_canonical_set_has_exact_ids_without_verdict_booleans_and_schema_is_registered(self):
        scenario_set = load_scenario_set(SCENARIO_SET_PATH)
        scenarios = scenario_set["scenarios"]
        expected_ids = {
            "preservation.frontier_normal",
            "preservation.authority_belief_denial",
            "preservation.expired_authority",
            "preservation.missing_belief_evidence",
            "preservation.action_reward",
            "preservation.provider_commit",
            "preservation.provider_conflict",
            "preservation.provider_rollback",
            "preservation.explanation_trace",
            "preservation.frontier_timeout",
            "preservation.restart_restore",
            "target.trajectory_projection",
            "target.authority_coexistence",
            "target.frontier_safety_vector",
            "target.migration_comparison",
            "target.monitor_removal",
            "target.authority_revoke",
            "target.provider_verify_failure",
            "target.executable_explanation_controls",
            "target.rollback_audit_history",
        }

        self.assertEqual(len(scenarios), 20)
        self.assertEqual({row["scenario_id"] for row in scenarios}, expected_ids)
        self.assertEqual(
            {row["scenario_id"] for row in scenarios if row["rail"] == "preservation"},
            REQUIRED_PRESERVATION_SCENARIO_IDS,
        )
        self.assertEqual(
            {row["scenario_id"] for row in scenarios if row["rail"] == "target_conformance"},
            REQUIRED_TARGET_SCENARIO_IDS,
        )
        forbidden_verdict_keys = {"decision", "expected_status", "ok", "pass", "passed"}
        for row in scenarios:
            self.assertTrue(forbidden_verdict_keys.isdisjoint(row), row["scenario_id"])
            self.assertFalse(
                any(isinstance(value, bool) for value in row.values()),
                f"scenario contains a verdict-like Boolean: {row['scenario_id']}",
            )

        versions = json.loads(VERSIONS_PATH.read_text(encoding="utf-8"))
        schema = json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(versions["architecture_eval_report.schema.json"], "v1")
        self.assertEqual(
            schema["properties"]["architecture_eval_report_schema_version"]["const"],
            "architecture_eval_report.v1",
        )
        self.assertEqual(P12CurrentAdapter(ROOT).adapter_id, scenario_set["adapter"])

    def test_scenario_set_cannot_drop_a_required_rail_or_id(self):
        payload = json.loads(SCENARIO_SET_PATH.read_text(encoding="utf-8"))
        payload["scenarios"] = [
            row for row in payload["scenarios"] if row["scenario_id"] != "preservation.frontier_normal"
        ]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "missing-preservation.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "preservation coverage changed"):
                load_scenario_set(path)

    def test_report_builder_refuses_destructive_or_preexisting_artifact_roots(self):
        with self.assertRaisesRegex(ValueError, "unsafe architecture-eval artifact root"):
            build_report(artifact_root=ROOT, out=ROOT / "runs/architecture_evals/should-not-exist.json")
        with tempfile.TemporaryDirectory() as td:
            existing = Path(td) / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(FileExistsError, "must be a new path"):
                build_report(artifact_root=existing, out=Path(td) / "report.json")


class ArchitectureEvalPredicateTests(unittest.TestCase):
    def test_preservation_fail_and_hold_block_the_top_gate(self):
        passing = [_result_row("preservation.normal")]
        failing = deepcopy(passing)
        failing[0]["status"] = "fail"
        holding = deepcopy(passing)
        holding[0]["status"] = "hold"
        target = _result_row(
            "target.observe",
            rail="target_conformance",
            gate_mode="observe",
            status="not_reached",
        )

        self.assertEqual(derive_gate_decision([*failing, target]), "fail")
        self.assertEqual(summarize_rail(failing, "preservation")["decision"], "fail")
        self.assertEqual(derive_gate_decision([*holding, target]), "hold")
        self.assertEqual(summarize_rail(holding, "preservation")["decision"], "hold")

    def test_missing_rail_holds_instead_of_passing(self):
        self.assertEqual(derive_gate_decision([]), "hold")
        self.assertEqual(summarize_rail([], "preservation")["decision"], "hold")
        observed_target = _result_row(
            "target.observe",
            rail="target_conformance",
            gate_mode="observe",
            status="not_reached",
        )
        self.assertEqual(derive_gate_decision([observed_target]), "hold")

    def test_binding_target_not_reached_blocks_but_observe_not_reached_does_not(self):
        preservation = _result_row("preservation.normal")
        required_target = _result_row(
            "target.binding",
            rail="target_conformance",
            gate_mode="required",
            status="not_reached",
        )
        observed_target = deepcopy(required_target)
        observed_target["scenario_id"] = "target.observe"
        observed_target["gate_mode"] = "observe"

        self.assertEqual(derive_gate_decision([preservation, required_target]), "hold")
        required_summary = summarize_rail([required_target], "target_conformance")
        self.assertEqual(required_summary["decision"], "not_reached")
        self.assertEqual(required_summary["blocking_scenario_ids"], ["target.binding"])

        self.assertEqual(derive_gate_decision([preservation, observed_target]), "pass")
        observed_summary = summarize_rail([observed_target], "target_conformance")
        self.assertEqual(observed_summary["decision"], "not_reached")
        self.assertEqual(observed_summary["status_counts"]["pass"], 0)
        self.assertEqual(observed_summary["blocking_scenario_ids"], [])

    def test_verdict_constants_in_evidence_cannot_make_a_predicate_pass(self):
        vector = _reward_vector("derived")
        vector.update({"passed": True, "ok": True, "decision": "pass"})
        vector["reward"].update({"passed": True, "ok": True, "decision": "pass"})
        spec = {"predicate_id": "reward_actionstream_only"}

        direct = evaluate_predicate("reward_actionstream_only", vector)
        through_scenario = evaluate_scenario(spec, vector)

        self.assertIn(direct["status"], {"fail", "hold"})
        self.assertIn(through_scenario["status"], {"fail", "hold"})
        self.assertNotEqual(direct["status"], "pass")
        self.assertEqual(through_scenario["status"], direct["status"])

    def test_planted_counterexamples_fail_or_hold(self):
        complete_frontier = {
            "respondent": "fixture",
            "provenance": ["trajectory:source"],
            "failure_mode": "timeout",
            "validation_errors": [],
            "variance": 0.0,
            "cost": {"value": 0.0, "unit": "usd"},
        }
        migration_old = {
            "producer_id": "old-organ",
            "artifact_path": "/tmp/old.json",
            "input_fingerprint": "same-input",
            "authority": "admitted",
            "reward_source": "action",
            "denial": None,
            "provenance": ["row:old"],
            "rollback": "verified",
        }
        migration_new = {
            "producer_id": "new-kernel",
            "artifact_path": "/tmp/new.json",
            "input_fingerprint": "same-input",
            "authority": "denied",
            "reward_source": "action",
            "denial": "scope_missing",
            "provenance": [],
            "rollback": "failed",
        }
        planted = {
            "frontier_provenance_lost": (
                "frontier_provenance",
                {
                    "frontier": {
                        "candidate_ids": ["cand:missing"],
                        "respondent": "fixture",
                        "provenance": {"policy_backend": "wrong"},
                        "generation_rows": [{"row_id": "frontier:generation", "trace_id": "trace"}],
                        "decision_rows": [],
                    }
                },
            ),
            "belief_mutated_provider": (
                "belief_cannot_authorize",
                {
                    "belief": {"belief_id": "belief:x", "evidence_row_ids": ["reward:x"]},
                    "authority_attempt": {
                        "embedded_belief_id": "belief:x",
                        "grant_id": None,
                        "outcome": "denied",
                        "denied_reason": "missing authority grant",
                        "receipt_row_ids": ["receipt:x"],
                    },
                    "provider": {"before_state_hash": "before", "after_state_hash": "after"},
                },
            ),
            "expired_grant_allowed": (
                "expired_authority_denied",
                {
                    "authority_attempt": {
                        "grant_id": "grant:expired",
                        "expires_at": "2026-01-01T00:00:00+00:00",
                        "evaluated_at": "2026-01-01T01:00:00+00:00",
                        "outcome": "committed",
                        "denied_reason": None,
                        "receipt_row_id": "receipt:bad",
                    },
                    "provider": {"before_state_hash": "before", "after_state_hash": "after"},
                },
            ),
            "uncited_belief_constructed": (
                "missing_evidence_rejected",
                {
                    "belief_input": {"evidence_row_ids": []},
                    "construction": {"exception_type": None, "message": None, "object_payload": {"belief_id": "uncited"}},
                },
            ),
            "non_action_reward": (
                "reward_actionstream_only",
                _reward_vector("derived"),
            ),
            "unverified_provider_commit": (
                "provider_transaction",
                {
                    "provider": {
                        "outcome": "committed",
                        "before_state_hash": "same",
                        "after_state_hash": "same",
                        "external_ids": ["event:x"],
                        "rollback_handle_id": "rollback:x",
                        "operations": [
                            {"operation": "commit", "status": "materialized", "trace_id": "t", "row_id": "commit:x"},
                            {"operation": "verify", "status": "unverified", "trace_id": "t", "row_id": "verify:x", "local_time_echo_ok": False},
                        ],
                    }
                },
            ),
            "conflict_mutated_state": (
                "provider_conflict_denial",
                {
                    "provider": {
                        "first_outcome": "committed",
                        "conflict_outcome": "denied",
                        "denied_reason": "provider_conflict_detected",
                        "conflict_truth": [{"event_id": "conflict"}],
                        "before_conflict_hash": "before",
                        "after_conflict_hash": "after",
                        "denial_row_ids": ["receipt:conflict"],
                    }
                },
            ),
            "two_authority_owners": (
                "single_authority_owner",
                {
                    "authority": {
                        "coexistence_states": [
                            {
                                "state_id": "coexistence:dual-owner",
                                "authority_owner_ids": ["old-organ", "new-kernel"],
                                "receipt_row_ids": ["receipt:old", "receipt:new"],
                            }
                        ]
                    }
                },
            ),
            "missing_frontier_latency": (
                "frontier_safety_observables",
                {
                    "frontier": {
                        "target_rows": [
                            {
                                "row_id": "frontier:claimed-target",
                                "source": deepcopy(complete_frontier),
                                "normalized": deepcopy(complete_frontier),
                            }
                        ]
                    }
                },
            ),
            "migration_mismatch": (
                "migration_equivalence",
                {
                    "migration": {
                        "comparisons": [
                            {
                                "comparison_id": "migration:mismatch",
                                "old": migration_old,
                                "new": migration_new,
                            }
                        ]
                    }
                },
            ),
            "dropped_monitor": (
                "monitor_preservation",
                {
                    "monitors": {
                        "baseline_counterexample_ids": ["counterexample:reward-leak"],
                        "baseline_detection_ids": ["counterexample:reward-leak"],
                        "removal_trials": [
                            {
                                "trial_id": "removal:dropped-monitor",
                                "counterexample_ids": ["counterexample:reward-leak"],
                                "detected_before": ["counterexample:reward-leak"],
                                "detected_after": [],
                                "removal_artifact": "/tmp/removal.json",
                            }
                        ],
                    }
                },
            ),
            "unverified_rollback": (
                "rollback_effective",
                {
                    "provider": {
                        "commit_outcome": "committed",
                        "undo_outcome": "reverted",
                        "undo_receipt_status": "reverted",
                        "rollback_handle_id": "rollback:unverified",
                        "before_commit_hash": "state-before",
                        "after_commit_hash": "state-after-commit",
                        "after_undo_hash": "state-before",
                        "active_undo_handles_after": [],
                        "operations": [
                            {
                                "operation": "commit",
                                "row_id": "provider:commit",
                                "status": "materialized",
                            },
                            {
                                "operation": "rollback",
                                "row_id": "provider:rollback",
                                "status": "rollback_unverified",
                                "rollback_verified": False,
                            },
                        ],
                    }
                },
            ),
            "uncited_explanation": (
                "explanations_cited_controls",
                {
                    "explanation": {
                        "trajectory_row_ids": ["row:known"],
                        "answers": [
                            {
                                "subject": "belief",
                                "claim": "claim",
                                "citation_ids": ["row:missing"],
                                "controls": {},
                                "version": "v1",
                            }
                        ],
                    }
                },
            ),
            "stale_frontier_survives_failure": (
                "frontier_failure_visible",
                {
                    "frontier": {
                        "stale_candidate_ids_before": ["cand:stale"],
                        "candidate_ids_after": ["cand:stale"],
                        "outcome": "failed",
                        "failure_mode": "timeout",
                        "failure_receipts": [{"row_id": "receipt:failure", "status": "failed", "failure_mode": "timeout"}],
                        "actuation_rows_after_failure": [],
                    }
                },
            ),
            "restart_loses_trajectory": (
                "restart_restore",
                {
                    "restart_restore": {
                        "before": {
                            "session_id": "session",
                            "candidate_ids": ["cand"],
                            "receipt_ids": ["receipt"],
                            "trajectory_row_ids": ["row"],
                            "transcript_event_count": 1,
                        },
                        "after": {
                            "session_id": "session",
                            "candidate_ids": [],
                            "receipt_ids": [],
                            "trajectory_row_ids": [],
                            "transcript_event_count": 0,
                            "restore_error": None,
                        },
                        "persisted_artifacts": ["session_state.json"],
                    }
                },
            ),
            "trajectory_self_attested": (
                "trajectory_reconstruction",
                {
                    "projection": {
                        "required_visible_paths": ["visible.x"],
                        "trajectory_row_ids": ["row:unrelated"],
                        "visible_values": {"visible.x": 1},
                        "trajectory_reconstruction": {"visible.x": 1},
                        "projection_sources": ["trajectory"],
                    }
                },
            ),
            "revocation_without_receipt": (
                "revoke_effective",
                {
                    "authority": {
                        "revoke_attempts": [
                            {
                                "grant_id": "grant:x",
                                "revoke_receipt_row_id": "receipt:x",
                                "exercise_before": "allowed",
                                "exercise_after": "denied",
                                "provider_hash_before_reexercise": "same",
                                "provider_hash_after_reexercise": "same",
                            }
                        ]
                    }
                },
            ),
            "verify_failure_called_committed": (
                "provider_verify_failure_state",
                {
                    "provider_verify_failure": {
                        "target_transition": {
                            "initial_outcome": "committed",
                            "final_outcome": "committed",
                            "provider_hash_before": "before",
                            "provider_hash_after_resolution": "after",
                            "operations": [{"operation": "verify", "status": "unverified"}],
                        }
                    }
                },
            ),
            "explanation_control_without_execution": (
                "executable_explanation_controls",
                {
                    "executable_controls": {
                        "controls": [
                            {
                                "control_id": "control:x",
                                "route": "/control/x",
                                "authority_requirement": "user",
                                "outcome": "applied",
                                "receipt_row_id": "receipt:x",
                            }
                        ]
                    }
                },
            ),
            "rollback_erases_audit": (
                "rollback_audit_retained",
                {
                    "rollback_audit": {
                        "trials": [
                            {
                                "trial_id": "rollback:bad",
                                "external_hash_before": "same",
                                "external_hash_after_rollback": "same",
                                "audit_row_ids_before": ["row:before"],
                                "audit_row_ids_after": ["row:rollback"],
                                "rollback_receipt_row_id": "row:rollback",
                            }
                        ]
                    }
                },
            ),
            "binding_signature_accepts_tamper": (
                "binding_manifest_signature",
                {"ruler": {"valid_manifest_decision": "pass", "tampered_manifest_decision": "pass", "tampered_failure_codes": []}},
            ),
            "binding_affectedness_accepts_undeclared": (
                "binding_manifest_affectedness",
                {"ruler": {"declared_diff_decision": "pass", "undeclared_diff_decision": "pass", "undeclared_failure_codes": []}},
            ),
            "instrument_mutation_accepted": (
                "instrument_mutation_rejection",
                {"ruler": {"baseline_valid": True, "tampered_rejected": False, "tampered_reason": ""}},
            ),
            "manifest_protected_path_accepted": (
                "binding_manifest_protected_path_rejection",
                {"ruler": {"protected_path_decision": "pass", "protected_failure_codes": []}},
            ),
            "promotion_override_accepted": (
                "promotion_override_rejection",
                {"promotion": {"forced_returncode": 0, "automatic_returncode": 0, "forced_decision": "pass", "automatic_decision": "pass", "current_unchanged": False, "promotion_trees_unchanged": False, "promotion_artifact_writes": 1}},
            ),
            "nondeterministic_product_core": (
                "reducer_determinism",
                {"product_core": {"first_sha256": "a", "second_sha256": "b", "reducer_version": "v1", "event_types": []}},
            ),
            "uncited_product_core_projection": (
                "cited_required_projection",
                {"product_core": {"status": "preview", "reducer_version": "v1", "required_fields_present": True, "evidence_row_ids": [], "all_evidence_rows_exist": False}},
            ),
            "dispatchable_product_core": (
                "product_core_no_effect_reachability",
                {"product_core": {"can_dispatch": True, "forbidden_imports": [], "forbidden_preview_fields": [], "effect_counts": {"effect_attempts": 0, "claims": 0, "dispatches": 0, "provider_mutations": 0}}},
            ),
            "uncited_read_side": (
                "cited_read_side_cutover",
                {"read_side": {}},
            ),
            "sandbox_claims_production_authority": (
                "sandbox_effect_contract",
                {
                    "effect_kernel": {
                        "case": "no_learning_effect_path",
                        "authority_profile": "owner_controlled_sandbox",
                        "authorizes_production": True,
                        "adapter_id": "deterministic_sandbox",
                        "adapter_credential_count": 0,
                        "adapter_external_io": False,
                        "forbidden_imports": [],
                        "accepted_action_families": ["create_prep_block"],
                        "default_selector": "incumbent",
                        "explicit_selector": "deterministic_sandbox",
                        "real_provider_reachable": False,
                    }
                },
            ),
            "p13_target_claim_without_evidence": (
                "p13_target_not_implemented",
                {"target_capability": {"reached": True}},
            ),
        }

        self.assertEqual(len(planted), 31)
        self.assertEqual({predicate_id for predicate_id, _ in planted.values()}, set(PREDICATES))

        for name, (predicate_id, vector) in planted.items():
            with self.subTest(name=name):
                result = evaluate_predicate(predicate_id, vector)
                self.assertIn(result["status"], {"fail", "hold"})

    def test_predicate_result_changes_when_reward_evidence_is_repaired(self):
        broken = _reward_vector("derived")
        repaired = deepcopy(broken)
        repaired["reward"]["input_rows"][0]["stream"] = "action"
        repaired["reward"]["consumed_rows"][0]["stream"] = "action"

        broken_result = evaluate_predicate("reward_actionstream_only", broken)
        repaired_result = evaluate_predicate("reward_actionstream_only", repaired)

        self.assertIn(broken_result["status"], {"fail", "hold"})
        self.assertEqual(repaired_result["status"], "pass")
        self.assertNotEqual(broken_result["status"], repaired_result["status"])

    def test_all_target_predicates_accept_hashed_repaired_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def proof(name: str, payload: dict | None = None) -> dict[str, str]:
                path = root / name
                path.write_text(json.dumps(payload or {"artifact": name}, sort_keys=True), encoding="utf-8")
                return {"path": str(path), "sha256": _sha256(path)}

            trajectory = proof("trajectory.json", {"row_ids": ["row:1"]})
            projection = proof("projection.json", {"visible.x": 1})
            frontier_row = {
                "respondent": "fixture",
                "provenance": ["source:fixture"],
                "failure_mode": "none",
                "validation_errors": [],
                "variance": {
                    "status": "measured",
                    "value": 0.0,
                    "unit": "reward_squared",
                    "metric": "top_candidate_reward",
                    "sample_count": 1,
                },
                "cost": {"status": "measured", "value": 0.0, "unit": "usd"},
                "latency": {"status": "measured", "value": 1.0, "unit": "ms"},
            }
            old_artifact = proof("old.json")
            new_artifact = proof("new.json")
            migration_side = {
                "input_fingerprint": "input:same",
                "instrument_sha256": "a" * 64,
                "authority": "admitted",
                "reward_source": "action",
                "denial": None,
                "provenance": ["source:semantic-fingerprint"],
                "rollback": "verified",
            }
            positive = {
                "trajectory_reconstruction": {
                    "projection": {
                        "required_visible_paths": ["visible.x"],
                        "trajectory_row_ids": ["row:1"],
                        "visible_values": {"visible.x": 1},
                        "trajectory_reconstruction": {"visible.x": 1},
                        "projection_sources": ["trajectory"],
                        "trajectory_artifact": trajectory,
                        "projection_artifact": projection,
                        "reconstruction_row_ids": {"visible.x": ["row:1"]},
                        "projection_execution": {
                            "producer_id": "trajectory-projector",
                            "command": "project --trajectory trajectory.json",
                            "exit_code": 0,
                            "input_trajectory_sha256": trajectory["sha256"],
                        },
                    }
                },
                "single_authority_owner": {
                    "authority": {
                        "coexistence_states": [
                            {
                                "state_id": "coexistence:one",
                                "authority_owner_ids": ["swift-authority"],
                                "receipts": [
                                    {
                                        "row_id": "receipt:one",
                                        "issuer_id": "swift-authority",
                                        "grant_id": "grant:one",
                                        "outcome": "committed",
                                        "effect_authorizing": True,
                                    }
                                ],
                            }
                        ]
                    }
                },
                "frontier_safety_observables": {
                    "frontier": {
                        "target_rows": [
                            {"row_id": "frontier:one", "source": deepcopy(frontier_row), "normalized": deepcopy(frontier_row)}
                        ]
                    }
                },
                "migration_equivalence": {
                    "migration": {
                        "comparisons": [
                            {
                                "comparison_id": "migration:one",
                                "old": migration_side
                                | {"producer_id": "old", "invocation_id": "old:1", "artifact": old_artifact},
                                "new": migration_side
                                | {"producer_id": "new", "invocation_id": "new:1", "artifact": new_artifact},
                            }
                        ]
                    }
                },
                "monitor_preservation": {
                    "monitors": {
                        "baseline_counterexample_ids": ["counterexample:one"],
                        "baseline_detection_ids": ["counterexample:one"],
                        "removal_trials": [
                            {
                                "trial_id": "removal:one",
                                "counterexample_ids": ["counterexample:one"],
                                "detected_before": ["counterexample:one"],
                                "detected_after": ["counterexample:one"],
                                "removal_artifact": proof("removal.json"),
                                "before_report": proof("monitor-before.json"),
                                "after_report": proof("monitor-after.json"),
                            }
                        ],
                    }
                },
                "revoke_effective": {
                    "authority": {
                        "revoke_attempts": [
                            {
                                "grant_id": "grant:revoke",
                                "revoke_receipt_row_id": "receipt:revoke",
                                "revoke_receipt_artifact": proof("revoke-receipt.json"),
                                "exercise_before": "allowed",
                                "exercise_after": "denied",
                                "provider_hash_before_reexercise": "same",
                                "provider_hash_after_reexercise": "same",
                                "revoke_scope": "future_and_staged",
                                "staged_before_revoke": ["stage:one"],
                                "staged_after_revoke": [],
                                "committed_effects_rolled_back_implicitly": False,
                            }
                        ]
                    }
                },
                "provider_verify_failure_state": {
                    "provider_verify_failure": {
                        "target_transition": {
                            "initial_outcome": "rollback_pending",
                            "final_outcome": "reverted",
                            "provider_hash_before": "same",
                            "provider_hash_after_resolution": "same",
                            "operations": [
                                {"operation": "verify", "status": "unverified"},
                                {"operation": "rollback", "status": "rollback_verified"},
                            ],
                        }
                    }
                },
                "executable_explanation_controls": {
                    "executable_controls": {
                        "controls": [
                            {
                                "control_id": "control:disable-belief",
                                "route": "/belief/disable",
                                "authority_requirement": "user_confirmation",
                                "outcome": "applied",
                                "receipt_row_id": "receipt:control",
                                "execution_artifact": proof("control-execution.json"),
                            }
                        ]
                    }
                },
                "rollback_audit_retained": {
                    "rollback_audit": {
                        "trials": [
                            {
                                "trial_id": "rollback:audit",
                                "external_hash_before": "same",
                                "external_hash_after_rollback": "same",
                                "audit_row_ids_before": ["row:commit"],
                                "audit_row_ids_after": ["row:commit", "row:rollback"],
                                "rollback_receipt_row_id": "row:rollback",
                            }
                        ]
                    }
                },
            }

            predicate_by_scenario = {
                "target.trajectory_projection": "trajectory_reconstruction",
                "target.authority_coexistence": "single_authority_owner",
                "target.frontier_safety_vector": "frontier_safety_observables",
                "target.migration_comparison": "migration_equivalence",
                "target.monitor_removal": "monitor_preservation",
                "target.authority_revoke": "revoke_effective",
                "target.provider_verify_failure": "provider_verify_failure_state",
                "target.executable_explanation_controls": "executable_explanation_controls",
                "target.rollback_audit_history": "rollback_audit_retained",
            }
            self.assertEqual(set(predicate_by_scenario), REQUIRED_TARGET_SCENARIO_IDS)
            self.assertEqual(set(positive), set(predicate_by_scenario.values()))
            vector_by_predicate = positive
            for scenario_id, predicate_id in predicate_by_scenario.items():
                with self.subTest(scenario_id=scenario_id):
                    self.assertEqual(evaluate_predicate(predicate_id, vector_by_predicate[predicate_id])["status"], "pass")


class ArchitectureEvalFullReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary_directory = tempfile.TemporaryDirectory()
        cls.temp_root = Path(cls._temporary_directory.name)
        cls.out = cls.temp_root / "architecture_eval_report.json"
        cls.artifact_root = cls.temp_root / "artifacts"
        cls.report = build_report(
            scenario_set_path=SCENARIO_SET_PATH,
            artifact_root=cls.artifact_root,
            out=cls.out,
            command="focused unittest architecture eval",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary_directory.cleanup()

    def test_full_report_has_expected_two_rail_results_and_evidence_identity(self):
        report = self.report
        scenario_set = load_scenario_set(SCENARIO_SET_PATH)
        expected_ids = {row["scenario_id"] for row in scenario_set["scenarios"]}

        self.assertEqual(report["decision"], "pass")
        preservation = report["rails"]["preservation"]
        self.assertEqual(preservation["decision"], "pass")
        self.assertEqual(preservation["scenario_count"], 11)
        self.assertEqual(preservation["status_counts"]["pass"], 11)
        self.assertEqual(preservation["status_counts"]["fail"], 0)
        self.assertEqual(preservation["status_counts"]["hold"], 0)
        self.assertEqual(preservation["status_counts"]["not_reached"], 0)

        target = report["rails"]["target_conformance"]
        self.assertEqual(target["decision"], "not_reached")
        self.assertEqual(target["scenario_count"], 9)
        self.assertEqual(target["status_counts"]["not_reached"], 9)
        self.assertEqual(target["status_counts"]["pass"], 0)
        self.assertEqual(target["blocking_scenario_ids"], [])

        repository = report["repository"]
        self.assertRegex(repository["git_sha"], r"^[0-9a-f]{40}$")
        self.assertRegex(repository["app_tree_sha"], r"^[0-9a-f]{40}$")
        self.assertIsInstance(repository["dirty"], bool)
        self.assertRegex(repository["git_status_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(repository["app_worktree_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(report["execution"]["cwd"], str(ROOT.resolve()))
        self.assertEqual(report["execution"]["adapter"], P12CurrentAdapter.adapter_id)
        self.assertEqual(report["execution"]["access_point"], "python build_report API")
        self.assertEqual(report["execution"]["runtime_mode"], "fixture")
        self.assertEqual(report["execution"]["live_backends"], [])
        self.assertEqual(report["execution"]["report_decision"], report["decision"])
        self.assertEqual(report["execution"]["exit_code"], 0)
        self.assertEqual({row["scenario_id"] for row in report["scenarios"]}, expected_ids)
        self.assertEqual(report["report_paths"]["latest"], str(self.out))
        self.assertEqual(report["report_paths"]["immutable"], str(self.out))

        self.assertGreaterEqual(len(report["instrument_artifacts"]), 6)
        for artifact in report["instrument_artifacts"]:
            path = Path(artifact["path"])
            self.assertTrue(path.is_file(), artifact)
            self.assertEqual(artifact["sha256"], _sha256(path))

        for row in report["scenarios"]:
            with self.subTest(scenario_id=row["scenario_id"]):
                self.assertIsInstance(row["observable_vector"], dict)
                self.assertTrue(row["observable_vector"])
                self.assertTrue(row["artifacts"])
                for artifact in row["artifacts"]:
                    path = Path(artifact["path"])
                    self.assertTrue(path.is_file(), artifact)
                    self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
                    self.assertEqual(artifact["sha256"], _sha256(path))

        self.assertTrue(self.out.is_file())
        validate_report(report)
        persisted = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(persisted["decision"], report["decision"])
        self.assertEqual(
            [row["scenario_id"] for row in persisted["scenarios"]],
            [row["scenario_id"] for row in report["scenarios"]],
        )

    def test_report_decisions_are_derived_from_scenario_statuses_not_report_booleans(self):
        self.assertEqual(self.report["decision"], derive_gate_decision(self.report["scenarios"]))
        self.assertEqual(
            self.report["rails"]["preservation"],
            summarize_rail(self.report["scenarios"], "preservation"),
        )
        self.assertEqual(
            self.report["rails"]["target_conformance"],
            summarize_rail(self.report["scenarios"], "target_conformance"),
        )

        claimed = deepcopy(self.report)
        claimed["decision"] = "pass"
        claimed["ok"] = True
        claimed["passed"] = True
        planted_failure = next(
            row for row in claimed["scenarios"] if row["rail"] == "preservation"
        )
        planted_failure["status"] = "fail"

        self.assertTrue(claimed["ok"])
        self.assertTrue(claimed["passed"])
        self.assertEqual(claimed["decision"], "pass")
        self.assertEqual(derive_gate_decision(claimed["scenarios"]), "fail")

    def test_report_validation_rejects_tampered_artifacts_and_summaries(self):
        tampered_artifact = deepcopy(self.report)
        tampered_artifact["instrument_artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
            validate_report(tampered_artifact)

        tampered_summary = deepcopy(self.report)
        tampered_summary["rails"]["preservation"]["status_counts"]["pass"] = 0
        with self.assertRaisesRegex(ValueError, "rail summaries"):
            validate_report(tampered_summary)


if __name__ == "__main__":
    unittest.main()
