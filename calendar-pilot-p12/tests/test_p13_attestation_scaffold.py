from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.p13_ruler.attestation_scaffold import (
    PACKET_SCHEMA,
    POLICY_SCHEMA,
    REPORT_SCHEMA,
    REVIEW_SCHEMA,
    candidate_identity_sha256,
    effect_tcb_blob_set_sha256,
    effect_tcb_path_set_sha256,
    policy_content_sha256,
    signed_record_bytes,
    signed_record_payload_sha256,
    strict_load_json,
    validate_report_schema,
    verify_attestation_scaffold,
    write_external_json,
)


NOW = datetime(2026, 7, 10, 1, 0, tzinfo=timezone.utc)
CURRENT = ROOT / "experiments/promoted/CURRENT.json"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class P13AttestationScaffoldTests(unittest.TestCase):
    def _key(self, root: Path, name: str, principal: str) -> tuple[Path, dict]:
        private = root / f"{name}.private.pem"
        der = root / f"{name}.public.der"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(private), "-pubout", "-outform", "DER", "-out", str(der)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        public_bytes = der.read_bytes()
        role = {
            "principal_id": principal,
            "key_id": f"key:{name}",
            "algorithm": "rsa-sha256",
            "spki_der_base64": base64.b64encode(public_bytes).decode("ascii"),
            "public_key_sha256": hashlib.sha256(public_bytes).hexdigest(),
            "not_before": _iso(NOW - timedelta(minutes=45)),
            "not_after": _iso(NOW + timedelta(hours=10)),
        }
        return private, role

    def _sign(self, record: dict, private_key: Path) -> dict:
        record["payload_sha256"] = "0" * 64
        record["signature"] = {"algorithm": "rsa-sha256", "value_base64": "AA=="}
        record["payload_sha256"] = signed_record_payload_sha256(record)
        process = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", str(private_key)],
            input=signed_record_bytes(record),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        record["signature"]["value_base64"] = base64.b64encode(process.stdout).decode("ascii")
        return record

    def _write(self, path: Path, payload: dict) -> Path:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def _fixture(self, root: Path, *, review_decision: str = "approve") -> dict:
        operator_private, operator = self._key(root, "operator", "principal:operator")
        evaluator_private, evaluator = self._key(root, "evaluator", "principal:evaluator")
        reviewer_private, reviewer = self._key(root, "reviewer", "principal:reviewer")
        policy = {
            "scaffolding_trust_policy_schema_version": "p13_scaffolding_trust_policy.v1",
            "mode": "scaffold_only",
            "policy_id": "policy:p13-scaffold-test",
            "policy_epoch": 1,
            "repository_origin_id": "github.com:Whatintheccc:Destination",
            "valid_from": _iso(NOW - timedelta(hours=1)),
            "expires_at": _iso(NOW + timedelta(hours=12)),
            "roles": {
                "operator_authorizer": operator,
                "isolated_evaluator": evaluator,
                "independent_tcb_reviewer": reviewer,
            },
            "protected_candidate_principals": ["principal:candidate-author"],
            "revoked_key_ids": [],
        }
        policy_path = self._write(root / "policy.json", policy)
        candidate = {
            "repository_origin_id": policy["repository_origin_id"],
            "base_commit": "1" * 40,
            "base_tree": "2" * 40,
            "candidate_commit": "3" * 40,
            "candidate_tree": "4" * 40,
            "candidate_app_tree": "5" * 40,
            "canonical_binary_diff_sha256": _sha("binary-diff"),
            "changed_paths_sha256": _sha("changed-paths"),
            "affectedness_sha256": _sha("affectedness"),
            "identity_sha256": "0" * 64,
        }
        candidate["identity_sha256"] = candidate_identity_sha256(candidate)
        tcb_entries = [
            {
                "repository_relative_path": "calendar-pilot-p12/src/policy.py",
                "before": {"mode": "100644", "blob_sha256": _sha("policy-before")},
                "after": {"mode": "100644", "blob_sha256": _sha("policy-after")},
            },
            {
                "repository_relative_path": "calendar-pilot-p12/swift_bridge/Gateway.swift",
                "before": {"mode": "100644", "blob_sha256": _sha("gateway-before")},
                "after": {"mode": "100644", "blob_sha256": _sha("gateway-after")},
            },
        ]
        packet = {
            "evaluation_packet_schema_version": "p13_evaluation_packet.scaffold.v1",
            "packet_id": "packet:p13-scaffold-test",
            "policy": {
                "policy_id": policy["policy_id"],
                "policy_epoch": policy["policy_epoch"],
                "content_sha256": policy_content_sha256(policy),
            },
            "manifest": {"manifest_id": "manifest:p13-scaffold-test", "payload_sha256": _sha("manifest")},
            "candidate": candidate,
            "instrument": {
                "bundle_sha256": _sha("instrument"),
                "scope_sha256": _sha("scope"),
                "ownership_map_sha256": _sha("ownership"),
            },
            "effect_tcb": {
                "entries": tcb_entries,
                "path_set_sha256": effect_tcb_path_set_sha256(tcb_entries),
                "blob_set_sha256": effect_tcb_blob_set_sha256(tcb_entries),
                "entry_count": len(tcb_entries),
            },
            "sealed_inputs": [
                {"kind": "cvar-before", "content_sha256": _sha("cvar-before"), "byte_size": 300, "store_id": "store:cvar-before"}
            ],
            "raw_evidence": [
                {"kind": "architecture", "content_sha256": _sha("architecture"), "byte_size": 500, "store_id": "store:architecture"},
                {"kind": "release", "content_sha256": _sha("release"), "byte_size": 700, "store_id": "store:release"},
            ],
            "evaluator": {
                "principal_id": evaluator["principal_id"],
                "key_id": evaluator["key_id"],
                "image_digest": f"sha256:{_sha('evaluator-image')}",
                "entrypoint_sha256": _sha("evaluator-entrypoint"),
            },
            "issued_at": _iso(NOW - timedelta(minutes=30)),
            "expires_at": _iso(NOW + timedelta(hours=2)),
        }
        self._sign(packet, evaluator_private)
        packet_path = self._write(root / "packet.json", packet)
        review = {
            "tcb_review_attestation_schema_version": "p13_tcb_review_attestation.scaffold.v1",
            "review_id": "review:p13-scaffold-test",
            "policy": deepcopy(packet["policy"]),
            "packet": {"packet_id": packet["packet_id"], "payload_sha256": packet["payload_sha256"]},
            "candidate_identity_sha256": candidate["identity_sha256"],
            "tcb_path_set_sha256": packet["effect_tcb"]["path_set_sha256"],
            "tcb_blob_set_sha256": packet["effect_tcb"]["blob_set_sha256"],
            "reviewer": {"principal_id": reviewer["principal_id"], "key_id": reviewer["key_id"]},
            "decision": review_decision,
            "reason": "scaffold review fixture",
            "issued_at": _iso(NOW - timedelta(minutes=15)),
            "expires_at": _iso(NOW + timedelta(hours=1)),
        }
        self._sign(review, reviewer_private)
        review_path = self._write(root / "review.json", review)
        return {
            "operator_private": operator_private,
            "evaluator_private": evaluator_private,
            "reviewer_private": reviewer_private,
            "policy": policy,
            "policy_path": policy_path,
            "packet": packet,
            "packet_path": packet_path,
            "review": review,
            "review_path": review_path,
        }

    def _verify(self, fixture: dict) -> dict:
        report = verify_attestation_scaffold(
            policy_path=fixture["policy_path"],
            packet_path=fixture["packet_path"],
            review_path=fixture["review_path"],
            now=NOW,
        )
        validate_report_schema(report)
        return report

    def test_valid_distinct_scaffold_is_permanently_non_authorizing(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            report = self._verify(self._fixture(Path(td)))
        self.assertEqual(report["decision"], "hold")
        self.assertTrue(report["mechanics_valid"])
        self.assertFalse(report["authorizes_migration"])
        self.assertFalse(report["policy_provenance_verified"])
        self.assertEqual(report["trust_root_status"], "unanchored_scaffold")
        self.assertIn("trusted_bootstrap_root", report["deferred_authority"])
        self.assertIn("policy_provenance_unverified", {row["code"] for row in report["hold_reasons"]})
        self.assertIn("evaluation_receipt", report["deferred_authority"])
        schema = json.loads((ROOT / "contracts" / REPORT_SCHEMA).read_text(encoding="utf-8"))
        self.assertNotIn("pass", schema["properties"]["decision"]["enum"])

    def test_missing_external_inputs_hold(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            fixture = self._fixture(Path(td))
            missing_policy = verify_attestation_scaffold(policy_path=None, packet_path=None, review_path=None, now=NOW)
            missing_review = verify_attestation_scaffold(
                policy_path=fixture["policy_path"], packet_path=fixture["packet_path"], review_path=None, now=NOW
            )
            unavailable_review = verify_attestation_scaffold(
                policy_path=fixture["policy_path"],
                packet_path=fixture["packet_path"],
                review_path=Path(td) / "not-created-review.json",
                now=NOW,
            )
            unavailable_parent = verify_attestation_scaffold(
                policy_path=fixture["policy_path"],
                packet_path=fixture["packet_path"],
                review_path=Path(td) / "absent" / "not-created-review.json",
                now=NOW,
            )
        self.assertEqual(missing_policy["decision"], "hold")
        self.assertFalse(missing_policy["mechanics_valid"])
        self.assertIn("policy_missing", {row["code"] for row in missing_policy["hold_reasons"]})
        self.assertEqual(missing_review["decision"], "hold")
        self.assertIn("review_missing", {row["code"] for row in missing_review["hold_reasons"]})
        self.assertEqual(unavailable_review["decision"], "hold")
        self.assertIn("review_missing", {row["code"] for row in unavailable_review["hold_reasons"]})
        self.assertEqual(unavailable_parent["decision"], "hold")
        self.assertIn("review_missing", {row["code"] for row in unavailable_parent["hold_reasons"]})

    def test_role_key_and_reviewer_author_collisions_fail(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            collision = deepcopy(fixture["policy"])
            collision["roles"]["independent_tcb_reviewer"]["spki_der_base64"] = collision["roles"]["isolated_evaluator"]["spki_der_base64"]
            collision["roles"]["independent_tcb_reviewer"]["public_key_sha256"] = collision["roles"]["isolated_evaluator"]["public_key_sha256"]
            fixture["policy_path"] = self._write(root / "policy-collision.json", collision)
            key_collision = self._verify(fixture)

            fixture = self._fixture(root)
            author_collision = deepcopy(fixture["policy"])
            author_collision["roles"]["independent_tcb_reviewer"]["principal_id"] = "principal:candidate-author"
            fixture["policy_path"] = self._write(root / "policy-author-collision.json", author_collision)
            reviewer_collision = self._verify(fixture)
        self.assertEqual(key_collision["decision"], "fail")
        self.assertIn("role_key_collision", {row["code"] for row in key_collision["failures"]})
        self.assertEqual(reviewer_collision["decision"], "fail")
        self.assertIn("reviewer_author_collision", {row["code"] for row in reviewer_collision["failures"]})

    def test_signature_payload_candidate_and_tcb_tamper_fail(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            packet = deepcopy(fixture["packet"])
            packet["raw_evidence"][0]["content_sha256"] = _sha("tampered")
            fixture["packet_path"] = self._write(root / "packet-tampered.json", packet)
            payload_tamper = self._verify(fixture)

            fixture = self._fixture(root)
            review = deepcopy(fixture["review"])
            review["candidate_identity_sha256"] = _sha("other-candidate")
            self._sign(review, fixture["reviewer_private"])
            fixture["review_path"] = self._write(root / "review-candidate-replay.json", review)
            candidate_replay = self._verify(fixture)

            fixture = self._fixture(root)
            review = deepcopy(fixture["review"])
            review["tcb_blob_set_sha256"] = _sha("other-tcb")
            self._sign(review, fixture["reviewer_private"])
            fixture["review_path"] = self._write(root / "review-tcb-replay.json", review)
            tcb_replay = self._verify(fixture)
        self.assertIn("payload_hash_mismatch", {row["code"] for row in payload_tamper["failures"]})
        self.assertIn("review_candidate_mismatch", {row["code"] for row in candidate_replay["failures"]})
        self.assertIn("review_tcb_blob_mismatch", {row["code"] for row in tcb_replay["failures"]})

    def test_expired_policy_packet_and_review_fail(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            policy = deepcopy(fixture["policy"])
            policy["expires_at"] = _iso(NOW - timedelta(minutes=1))
            fixture["policy_path"] = self._write(root / "policy-expired.json", policy)
            policy_expired = self._verify(fixture)

            fixture = self._fixture(root)
            packet = deepcopy(fixture["packet"])
            packet["expires_at"] = _iso(NOW - timedelta(minutes=1))
            self._sign(packet, fixture["evaluator_private"])
            fixture["packet_path"] = self._write(root / "packet-expired.json", packet)
            packet_expired = self._verify(fixture)

            fixture = self._fixture(root)
            review = deepcopy(fixture["review"])
            review["expires_at"] = _iso(NOW - timedelta(minutes=1))
            self._sign(review, fixture["reviewer_private"])
            fixture["review_path"] = self._write(root / "review-expired.json", review)
            review_expired = self._verify(fixture)
        self.assertIn("policy_inactive", {row["code"] for row in policy_expired["failures"]})
        self.assertIn("packet_time_order", {row["code"] for row in packet_expired["failures"]})
        self.assertIn("review_time_order", {row["code"] for row in review_expired["failures"]})

    def test_reviewer_hold_holds_and_reject_fails(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            hold_report = self._verify(self._fixture(root, review_decision="hold"))
            reject_report = self._verify(self._fixture(root, review_decision="reject"))
        self.assertEqual(hold_report["decision"], "hold")
        self.assertTrue(hold_report["mechanics_valid"])
        self.assertIn("review_hold", {row["code"] for row in hold_report["hold_reasons"]})
        self.assertEqual(reject_report["decision"], "fail")
        self.assertTrue(reject_report["mechanics_valid"])
        self.assertIn("review_rejected", {row["code"] for row in reject_report["failures"]})

    def test_repository_local_and_symlink_inputs_fail(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            with tempfile.TemporaryDirectory(dir=ROOT / "runs") as local_td:
                local_policy = self._write(Path(local_td) / "policy.json", fixture["policy"])
                local_report = verify_attestation_scaffold(
                    policy_path=local_policy,
                    packet_path=fixture["packet_path"],
                    review_path=fixture["review_path"],
                    now=NOW,
                )
            link = root / "policy-link.json"
            link.symlink_to(fixture["policy_path"])
            symlink_report = verify_attestation_scaffold(
                policy_path=link,
                packet_path=fixture["packet_path"],
                review_path=fixture["review_path"],
                now=NOW,
            )
        self.assertIn("input_inside_candidate_workspace", {row["code"] for row in local_report["failures"]})
        self.assertIn("input_path_symlink", {row["code"] for row in symlink_report["failures"]})

    def test_hardlink_and_git_worktree_inputs_fail(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            with tempfile.TemporaryDirectory(dir=ROOT / "runs") as local_td:
                local_policy = self._write(Path(local_td) / "policy.json", fixture["policy"])
                hardlink = root / "policy-hardlink.json"
                os.link(local_policy, hardlink)
                hardlink_report = verify_attestation_scaffold(
                    policy_path=hardlink,
                    packet_path=fixture["packet_path"],
                    review_path=fixture["review_path"],
                    now=NOW,
                )

            worktree = root / "linked-worktree"
            worktree.mkdir()
            (worktree / ".git").write_text("gitdir: /private/tmp/nonexistent\n", encoding="utf-8")
            worktree_policy = self._write(worktree / "policy.json", fixture["policy"])
            worktree_report = verify_attestation_scaffold(
                policy_path=worktree_policy,
                packet_path=fixture["packet_path"],
                review_path=fixture["review_path"],
                now=NOW,
            )
        self.assertIn("input_hardlink", {row["code"] for row in hardlink_report["failures"]})
        self.assertIn("input_inside_git_worktree", {row["code"] for row in worktree_report["failures"]})

    def test_parent_symlinks_cannot_redirect_input_or_output(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            actual = root / "actual"
            actual.mkdir()
            alias = root / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            redirected_policy = self._write(actual / "policy.json", fixture["policy"])
            input_report = verify_attestation_scaffold(
                policy_path=alias / redirected_policy.name,
                packet_path=fixture["packet_path"],
                review_path=fixture["review_path"],
                now=NOW,
            )
            with self.assertRaisesRegex(Exception, "alias"):
                write_external_json(alias / "report.json", {"not": "written"})
            output_exists = (actual / "report.json").exists()
        self.assertIn("input_path_symlink_escape", {row["code"] for row in input_report["failures"]})
        self.assertFalse(output_exists)

    def test_verifier_ignores_path_shadowed_openssl(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            shadow = root / "shadow"
            shadow.mkdir()
            marker = root / "shadow-ran"
            fake = shadow / "openssl"
            fake.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 99\n", encoding="utf-8")
            fake.chmod(0o755)
            with patch.dict(os.environ, {"PATH": str(shadow)}):
                report = self._verify(fixture)
            shadow_ran = marker.exists()
        self.assertEqual(report["decision"], "hold")
        self.assertTrue(report["mechanics_valid"])
        self.assertFalse(shadow_ran)

    def test_strict_json_rejects_duplicates_unknowns_nonfinite_and_commands(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            encoded = json.dumps(fixture["policy"], sort_keys=True)
            duplicate = root / "policy-duplicate.json"
            duplicate.write_text('{"mode":"scaffold_only",' + encoded[1:], encoding="utf-8")
            with self.assertRaisesRegex(Exception, "duplicate JSON key"):
                strict_load_json(duplicate, POLICY_SCHEMA)

            unknown = deepcopy(fixture["packet"])
            unknown["command"] = ["python3", "candidate.py"]
            unknown_path = self._write(root / "packet-command.json", unknown)
            with self.assertRaisesRegex(Exception, "Additional properties"):
                strict_load_json(unknown_path, PACKET_SCHEMA)

            policy_text = json.dumps(fixture["policy"], sort_keys=True).replace('"policy_epoch": 1', '"policy_epoch": NaN')
            nonfinite = root / "policy-nonfinite.json"
            nonfinite.write_text(policy_text, encoding="utf-8")
            with self.assertRaisesRegex(Exception, "non-finite JSON number"):
                strict_load_json(nonfinite, POLICY_SCHEMA)

    def test_wrong_role_revocation_and_reference_replay_fail(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            packet = deepcopy(fixture["packet"])
            self._sign(packet, fixture["reviewer_private"])
            fixture["packet_path"] = self._write(root / "packet-wrong-role.json", packet)
            wrong_role = self._verify(fixture)

            fixture = self._fixture(root)
            policy = deepcopy(fixture["policy"])
            policy["revoked_key_ids"] = [policy["roles"]["isolated_evaluator"]["key_id"]]
            fixture["policy_path"] = self._write(root / "policy-revoked.json", policy)
            revoked = self._verify(fixture)

            fixture = self._fixture(root)
            review = deepcopy(fixture["review"])
            review["packet"]["payload_sha256"] = _sha("other-packet")
            self._sign(review, fixture["reviewer_private"])
            fixture["review_path"] = self._write(root / "review-other-packet.json", review)
            replay = self._verify(fixture)
        self.assertIn("signature_verification", {row["code"] for row in wrong_role["failures"]})
        self.assertIn("revoked_role_key", {row["code"] for row in revoked["failures"]})
        self.assertIn("review_packet_mismatch", {row["code"] for row in replay["failures"]})

    def test_tcb_entries_are_reviewable_and_hash_bound(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            packet = deepcopy(fixture["packet"])
            packet["effect_tcb"]["entries"][0]["after"]["blob_sha256"] = _sha("tampered-tcb-blob")
            self._sign(packet, fixture["evaluator_private"])
            fixture["packet_path"] = self._write(root / "packet-tcb-entry-tampered.json", packet)
            report = self._verify(fixture)

            invalid_git_id = deepcopy(fixture["packet"])
            invalid_git_id["candidate"]["base_commit"] = "a" * 41
            invalid_path = self._write(root / "packet-invalid-git-id.json", invalid_git_id)
            with self.assertRaisesRegex(Exception, "does not match"):
                strict_load_json(invalid_path, PACKET_SCHEMA)
        self.assertIn("effect_tcb_blob_hash_mismatch", {row["code"] for row in report["failures"]})

    def test_cli_never_exits_success_or_mutates_candidate_state(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as td:
            root = Path(td)
            fixture = self._fixture(root)
            out = root / "report.json"
            current_before = CURRENT.read_bytes()
            status_before = subprocess.run(
                ["git", "status", "--porcelain=v1", "-z"], cwd=ROOT.parent, stdout=subprocess.PIPE, check=True
            ).stdout
            process = subprocess.run(
                [
                    sys.executable,
                    "scripts/verify_p13_attestation_scaffold.py",
                    "--policy",
                    str(fixture["policy_path"]),
                    "--packet",
                    str(fixture["packet_path"]),
                    "--review",
                    str(fixture["review_path"]),
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            status_after = subprocess.run(
                ["git", "status", "--porcelain=v1", "-z"], cwd=ROOT.parent, stdout=subprocess.PIPE, check=True
            ).stdout
            report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(process.returncode, 3, process.stderr)
        self.assertEqual(report["decision"], "hold")
        self.assertFalse(report["authorizes_migration"])
        self.assertEqual(CURRENT.read_bytes(), current_before)
        self.assertEqual(status_after, status_before)

    def test_contracts_reject_pass_and_embedded_paths_or_keys(self):
        report_schema = json.loads((ROOT / "contracts" / REPORT_SCHEMA).read_text(encoding="utf-8"))
        packet_schema = json.loads((ROOT / "contracts" / PACKET_SCHEMA).read_text(encoding="utf-8"))
        review_schema = json.loads((ROOT / "contracts" / REVIEW_SCHEMA).read_text(encoding="utf-8"))
        self.assertEqual(report_schema["properties"]["decision"]["enum"], ["hold", "fail"])
        serialized = json.dumps({"packet": packet_schema, "review": review_schema})
        self.assertNotIn('"command"', serialized)
        self.assertNotIn("spki_der_base64", json.dumps(review_schema))


if __name__ == "__main__":
    unittest.main()
