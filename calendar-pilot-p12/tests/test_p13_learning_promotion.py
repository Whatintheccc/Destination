from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from evals.architecture.predicates.p13 import (
    holdout_non_exposure,
    optimizer_write_boundary,
    reward_identity_provenance,
    signed_policy_promotion,
)


ROOT = Path(__file__).resolve().parents[1]
HEX = "a" * 64


def _load_schema(name: str) -> dict:
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


class P13LearningRulerTests(unittest.TestCase):
    def test_contracts_are_draft_2020_12_and_registered(self):
        versions = json.loads((ROOT / "contracts/VERSIONS.json").read_text(encoding="utf-8"))
        names = {
            "learning_partition_manifest.schema.json",
            "optimizer_execution_report.schema.json",
            "policy_payload.schema.json",
            "promotion_record.schema.json",
        }
        for name in names:
            schema = _load_schema(name)
            Draft202012Validator.check_schema(schema)
            self.assertEqual(versions[name], "v1")

    def test_policy_payload_contract_rejects_unsigned_mutable_extras(self):
        schema = _load_schema("policy_payload.schema.json")
        payload = {
            "policy_payload_schema_version": "policy_payload.v1",
            "payload_id": "payload:test",
            "parent_payload_id": None,
            "policy_parameters": {"intent_reward_bias": {}},
            "respondents": ["diffusiongemma.fixture.v1"],
            "prompts": ["proposal.v1"],
            "compatibility": {"reducer_versions": ["product_core.v1"], "schema_versions": ["policy_tuning.v1"]},
            "training": {"partition_id": "search.v1", "row_count": 1, "row_set_sha256": HEX},
            "resources": {"seed_set_sha256": HEX, "max_candidates": 1, "max_compute_seconds": 10},
            "content_sha256": HEX,
        }
        Draft202012Validator(schema).validate(payload)
        payload["promotion_decision"] = "promote"
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(payload)))

    def test_partition_contract_requires_optimizer_denial_for_sealed_rails(self):
        schema = _load_schema("learning_partition_manifest.schema.json")
        base = {
            "partition_id": "search.v1",
            "artifact_path": "experiments/learning/search/search.jsonl",
            "artifact_sha256": HEX,
            "family_set_sha256": HEX,
            "row_count": 1,
            "starts_at": "2026-07-01T00:00:00Z",
            "ends_at": "2026-07-02T00:00:00Z",
            "optimizer_access": "read",
        }
        payload = {
            "learning_partition_manifest_schema_version": "learning_partition_manifest.v1",
            "instrument_epoch": "p13.6-ruler.1",
            "thresholds_sha256": HEX,
            "search": dict(base),
            "holdout": dict(base, partition_id="holdout.v1", optimizer_access="denied"),
            "forward_shadow": dict(base, partition_id="shadow.v1", optimizer_access="denied"),
            "disjointness": {
                "artifact_hashes_distinct": True,
                "family_sets_pairwise_disjoint": True,
                "forward_shadow_starts_after_search": True,
            },
            "manifest_sha256": HEX,
        }
        Draft202012Validator(schema).validate(payload)
        payload["holdout"]["optimizer_access"] = "read"
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(payload)))

    def test_optimizer_boundary_requires_proposal_write_and_all_protected_denials(self):
        attempts = [
            {"kind": kind, "operation": "write", "outcome": "denied", "errno": 1}
            for kind in ("evaluator", "manifest", "current", "effect_tcb")
        ]
        vector = {
            "optimizer_execution": {
                "boundary": "macos-sandbox-exec",
                "profile_sha256": HEX,
                "proposal": {"write_succeeded": True},
                "attempts": attempts,
            }
        }
        self.assertEqual(optimizer_write_boundary(vector)["status"], "pass")
        vector["optimizer_execution"]["attempts"].pop()
        self.assertEqual(optimizer_write_boundary(vector)["status"], "fail")

    def test_holdout_predicate_requires_distinct_disjoint_temporal_partitions_and_os_denials(self):
        vector = {
            "learning_partitions": {
                "search": {"artifact_sha256": "a" * 64},
                "holdout": {"artifact_sha256": "b" * 64},
                "forward_shadow": {"artifact_sha256": "c" * 64},
                "disjointness": {
                    "artifact_hashes_distinct": True,
                    "family_sets_pairwise_disjoint": True,
                    "forward_shadow_starts_after_search": True,
                },
            },
            "optimizer_execution": {
                "attempts": [
                    {"kind": "holdout", "operation": "read", "outcome": "denied", "errno": 1},
                    {"kind": "forward_shadow", "operation": "read", "outcome": "denied", "errno": 1},
                ]
            },
        }
        self.assertEqual(holdout_non_exposure(vector)["status"], "pass")
        vector["learning_partitions"]["holdout"]["artifact_sha256"] = "a" * 64
        self.assertEqual(holdout_non_exposure(vector)["status"], "hold")

    def test_signed_promotion_predicate_requires_bad_valid_and_rollback_drills(self):
        keys = {
            "payload_hash_verified",
            "record_signature_verified",
            "instrument_epoch_verified",
            "binding_manifest_verified",
            "all_attestations_passed",
            "tampered_payload_rejected",
            "bad_record_left_current_unchanged",
            "valid_record_promoted_atomically",
            "signed_rollback_restored_pointer",
            "runtime_loaded_exact_payload_hash",
        }
        vector = {"policy_promotion": {key: True for key in keys}}
        self.assertEqual(signed_policy_promotion(vector)["status"], "pass")
        vector["policy_promotion"]["tampered_payload_rejected"] = False
        self.assertEqual(signed_policy_promotion(vector)["status"], "fail")

    def test_reward_predicate_requires_transitive_simulator_noninterference(self):
        keys = {
            "issuer_signatures_verified",
            "global_occurrence_ids_unique",
            "duplicate_conflict_rejected",
            "source_class_from_registry",
            "simulator_direct_positive_credit_rejected",
            "simulator_transitive_positive_credit_rejected",
            "synthetic_program_a_credit_rejected",
        }
        vector = {"reward_ingress": {key: True for key in keys}}
        self.assertEqual(reward_identity_provenance(vector)["status"], "pass")
        vector["reward_ingress"]["simulator_transitive_positive_credit_rejected"] = False
        self.assertEqual(reward_identity_provenance(vector)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
