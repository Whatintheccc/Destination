from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

from evals.architecture.predicates.p13 import (
    holdout_non_exposure,
    optimizer_write_boundary,
    reward_identity_provenance,
    signed_policy_promotion,
)
from scripts.p13_learning_control import (
    artifact_ref,
    atomic_write_json,
    canonical_json_bytes,
    global_occurrence_id,
    load_current_policy_payload,
    load_json,
    policy_payload_hash,
    sha256_bytes,
    sha256_file,
    sign_promotion_record,
    sign_reward_event,
    validate_optimizer_report,
    validate_partition_manifest,
    validate_reward_ledger,
)
from scripts.promote_policy import apply_signed_record


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
            "reward_ingress_ledger.schema.json",
        }
        for name in names:
            schema = _load_schema(name)
            Draft202012Validator.check_schema(schema)
            self.assertEqual(versions[name], "v1")

    def test_committed_promoter_root_matches_public_key_and_control_epoch(self):
        root = json.loads((ROOT / "configs/p13_learning_promotion_root.json").read_text(encoding="utf-8"))
        key = ROOT / root["public_key_path"]
        self.assertEqual(sha256_file(key), root["public_key_sha256"])
        self.assertEqual(root["allowed_instrument_epochs"], ["p13.6-control.1"])

    def test_positive_learning_transition_stays_closed_without_statistics_contract(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as td:
            out = Path(td) / "promoter"
            process = subprocess.run(
                [sys.executable, "scripts/evaluate_policy_payload.py", "--payload", "missing", "--optimizer-report", "missing", "--partitions", "missing", "--binding-manifest", "missing", "--instrument-bundle", "missing", "--verification-key", "missing", "--signing-key", "missing", "--transition", "promote", "--out-dir", str(out)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(process.returncode, 3, process.stderr)
            self.assertIn("improvement-statistics attestation", process.stdout)
            self.assertFalse(out.exists())

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


class P13LearningControlPlaneTests(unittest.TestCase):
    def _keys(self, root: Path, name: str) -> tuple[Path, Path]:
        private = root / f"{name}-private.pem"
        public = root / f"{name}-public.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return private, public

    def _payload(self, path: Path, payload_id: str, *, bias: float = 0.0) -> dict:
        payload = {
            "policy_payload_schema_version": "policy_payload.v1",
            "payload_id": payload_id,
            "parent_payload_id": None,
            "policy_parameters": {"policy_tuning": {"tuning_id": payload_id, "intent_reward_bias": {"create_prep_block": bias}}},
            "respondents": ["diffusiongemma.fixture.v1"],
            "prompts": ["policy-payload-proposal.v1"],
            "compatibility": {"reducer_versions": ["product_core.create_prep_block.v1"], "schema_versions": ["policy_tuning.v1"]},
            "training": {"partition_id": "p13.6.search", "row_count": 1, "row_set_sha256": "1" * 64},
            "resources": {"seed_set_sha256": "2" * 64, "max_candidates": 1, "max_compute_seconds": 30},
        }
        payload["content_sha256"] = policy_payload_hash(payload)
        atomic_write_json(path, payload)
        return payload

    def _record(
        self,
        *,
        root: Path,
        payload_path: Path,
        current: Path,
        private_key: Path,
        public_key: Path,
        transition: str,
        record_name: str,
        restore_pointer: dict | None = None,
    ) -> Path:
        attestation_refs = {}
        for role in ("search", "holdout", "forward_shadow"):
            attestation = {"decision": "pass", "role": role}
            if role == "search" and restore_pointer is not None:
                attestation["restore_current_pointer"] = restore_pointer
            path = root / f"{record_name}-{role}.json"
            atomic_write_json(path, attestation)
            attestation_refs[role] = {**artifact_ref(path), "decision": "pass"}
        partitions = root / "partitions.json"
        if not partitions.exists():
            atomic_write_json(partitions, {"fixture": True})
        instrument = root / "instrument.json"
        if not instrument.exists():
            atomic_write_json(instrument, {"instrument_epoch": "test", "bundle_sha256": "3" * 64})
        manifest = root / "manifest.json"
        if not manifest.exists():
            atomic_write_json(manifest, {"manifest_id": "test:manifest"})
        record = {
            "promotion_record_schema_version": "promotion_record.v1",
            "record_id": record_name,
            "transition": transition,
            "created_at": "2026-07-10T00:00:00Z",
            "payload": artifact_ref(payload_path),
            "previous_current_sha256": sha256_bytes(current.read_bytes()),
            "instrument_bundle": {"path": artifact_ref(instrument)["path"], "file_sha256": sha256_file(instrument), "bundle_sha256": "3" * 64, "instrument_epoch": "test"},
            "binding_manifest": {"path": artifact_ref(manifest)["path"], "sha256": sha256_file(manifest), "manifest_id": "test:manifest"},
            "partition_manifest": artifact_ref(partitions),
            "attestations": attestation_refs,
            "reward_evidence": None,
            "decision": "pass",
            "signer": {"role": "promoter", "algorithm": "rsa-sha256", "public_key_sha256": sha256_file(public_key)},
        }
        signed = sign_promotion_record(record, private_key, public_key)
        path = root / f"{record_name}.json"
        atomic_write_json(path, signed)
        return path

    def _promotion_root(self, root: Path, public_key: Path) -> Path:
        path = root / "promotion-root.json"
        atomic_write_json(path, {
            "learning_promotion_root_schema_version": "learning_promotion_root.v1",
            "algorithm": "rsa-sha256",
            "public_key_path": artifact_ref(public_key)["path"],
            "public_key_sha256": sha256_file(public_key),
            "allowed_instrument_epochs": ["test"],
        })
        return path

    def test_authenticated_reward_ingress_rejects_direct_and_transitive_simulator_credit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as td:
            root = Path(td)
            human_private, human_public = self._keys(root, "human")
            simulator_private, simulator_public = self._keys(root, "simulator")
            human_id = global_occurrence_id("human-app", "h1")
            simulator_id = global_occurrence_id("sim", "s1")
            human = sign_reward_event({
                "issuer_id": "human-app", "event_id": "h1", "global_occurrence_id": human_id,
                "observed_at": "2026-07-10T00:00:00Z", "program": "program_a_human_utility",
                "parent_occurrence_ids": [], "utility_credit": 1.0,
            }, human_private)
            simulator = sign_reward_event({
                "issuer_id": "sim", "event_id": "s1", "global_occurrence_id": simulator_id,
                "observed_at": "2026-07-10T00:00:00Z", "program": "failure_detector",
                "parent_occurrence_ids": [], "utility_credit": 0.0,
            }, simulator_private)
            ledger = {
                "reward_ingress_ledger_schema_version": "reward_ingress_ledger.v1",
                "issuer_registry": [
                    {"issuer_id": "human-app", "source_class": "human", "public_key_path": artifact_ref(human_public)["path"], "public_key_sha256": sha256_file(human_public)},
                    {"issuer_id": "sim", "source_class": "simulator", "public_key_path": artifact_ref(simulator_public)["path"], "public_key_sha256": sha256_file(simulator_public)},
                ],
                "events": [human, simulator],
            }
            self.assertTrue(validate_reward_ledger(ledger)["simulator_transitive_positive_credit_rejected"])
            direct = json.loads(json.dumps(ledger))
            direct["events"][1] = sign_reward_event({
                **{key: value for key, value in simulator.items() if key not in {"payload_sha256", "signature"}},
                "program": "program_a_human_utility", "utility_credit": 1.0,
            }, simulator_private)
            with self.assertRaisesRegex(ValueError, "direct or transitive"):
                validate_reward_ledger(direct)
            child_id = global_occurrence_id("human-app", "h2")
            child = sign_reward_event({
                "issuer_id": "human-app", "event_id": "h2", "global_occurrence_id": child_id,
                "observed_at": "2026-07-10T00:01:00Z", "program": "program_a_human_utility",
                "parent_occurrence_ids": [simulator_id], "utility_credit": 1.0,
            }, human_private)
            transitive = json.loads(json.dumps(ledger))
            transitive["events"].append(child)
            with self.assertRaisesRegex(ValueError, "direct or transitive"):
                validate_reward_ledger(transitive)

    def test_signed_pointer_rejects_tamper_and_restores_exact_prior_pointer(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as td:
            root = Path(td)
            private_key, public_key = self._keys(root, "promoter")
            promotion_root = self._promotion_root(root, public_key)
            current = root / "CURRENT.json"
            atomic_write_json(current, {"legacy": "baseline"})
            baseline_payload_path = root / "baseline-payload.json"
            self._payload(baseline_payload_path, "baseline")
            baseline_record = self._record(root=root, payload_path=baseline_payload_path, current=current, private_key=private_key, public_key=public_key, transition="bootstrap", record_name="baseline")
            apply_signed_record(record_path=baseline_record, current_path=current, root_path=promotion_root)
            baseline_pointer = current.read_bytes()
            candidate_payload_path = root / "candidate-payload.json"
            candidate_payload = self._payload(candidate_payload_path, "candidate", bias=0.1)
            candidate_record = self._record(root=root, payload_path=candidate_payload_path, current=current, private_key=private_key, public_key=public_key, transition="bootstrap", record_name="candidate")
            original_candidate = candidate_payload_path.read_bytes()
            candidate_payload["policy_parameters"]["policy_tuning"]["intent_reward_bias"]["create_prep_block"] = 99.0
            atomic_write_json(candidate_payload_path, candidate_payload)
            before_bad = current.read_bytes()
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                apply_signed_record(record_path=candidate_record, current_path=current, root_path=promotion_root)
            self.assertEqual(current.read_bytes(), before_bad)
            candidate_payload_path.write_bytes(original_candidate)
            apply_signed_record(record_path=candidate_record, current_path=current, root_path=promotion_root)
            self.assertNotEqual(current.read_bytes(), baseline_pointer)
            loaded, _ = load_current_policy_payload(current, promotion_root=promotion_root)
            self.assertEqual(loaded["content_sha256"], load_json(candidate_payload_path)["content_sha256"])
            rollback_record = self._record(
                root=root, payload_path=baseline_payload_path, current=current, private_key=private_key,
                public_key=public_key, transition="rollback", record_name="rollback", restore_pointer=json.loads(baseline_pointer),
            )
            apply_signed_record(record_path=rollback_record, current_path=current, root_path=promotion_root)
            self.assertEqual(current.read_bytes(), baseline_pointer)

    @unittest.skipUnless(os.environ.get("CALENDAR_PILOT_RUN_MACOS_SANDBOX") == "1", "requires an unsandboxed macOS host to nest sandbox-exec")
    def test_real_optimizer_executor_denies_sealed_reads_and_protected_write_opens(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "runs") as td:
            root = Path(td)
            for name in ("search", "holdout", "shadow"):
                (root / f"{name}.jsonl").write_text(json.dumps({"row_id": name, "family_id": name, "observed_at": "2026-07-10T00:00:00Z"}) + "\n", encoding="utf-8")
            for name in ("evaluator", "manifest", "current", "effect"):
                (root / f"{name}.txt").write_text(name, encoding="utf-8")
            parameters = root / "parameters.json"
            parameters.write_text(json.dumps({"policy_tuning": {"tuning_id": "sandbox", "intent_reward_bias": {}}}), encoding="utf-8")
            out_dir = root / "proposals"
            process = subprocess.run([
                sys.executable, "scripts/run_policy_optimizer.py",
                "--search", str(root / "search.jsonl"), "--holdout", str(root / "holdout.jsonl"),
                "--forward-shadow", str(root / "shadow.jsonl"), "--evaluator", str(root / "evaluator.txt"),
                "--manifest", str(root / "manifest.txt"), "--current", str(root / "current.txt"),
                "--effect-tcb", str(root / "effect.txt"), "--out-dir", str(out_dir),
                "--payload-id", "sandbox-payload", "--policy-parameters", str(parameters),
            ], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            report = load_json(out_dir / "optimizer_execution_report.json")
            self.assertEqual(report["decision"], "pass")
            self.assertTrue(report["proposal"]["write_succeeded"])
            self.assertTrue(all(row["outcome"] == "denied" for row in report["attempts"]))


if __name__ == "__main__":
    unittest.main()
