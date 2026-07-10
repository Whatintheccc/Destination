#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.p13_ruler.core import validate_instrument_bundle, verify_binding_manifest
from scripts.p13_learning_control import (
    APP_ROOT,
    artifact_ref,
    atomic_write_json,
    load_json,
    sha256_bytes,
    sha256_file,
    sign_promotion_record,
    validate_optimizer_report,
    validate_partition_manifest,
    validate_policy_payload,
    validate_reward_ledger,
)


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else APP_ROOT / path


def _attestation(path: Path, payload: dict) -> dict:
    atomic_write_json(path, payload)
    return {**artifact_ref(path), "decision": payload["decision"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate one immutable PolicyPayload and emit a signed PromotionRecord")
    parser.add_argument("--payload", required=True)
    parser.add_argument("--optimizer-report", required=True)
    parser.add_argument("--partitions", required=True)
    parser.add_argument("--binding-manifest", required=True)
    parser.add_argument("--instrument-bundle", required=True)
    parser.add_argument("--verification-key", required=True)
    parser.add_argument("--signing-key", required=True)
    parser.add_argument("--promotion-public-key", default="configs/p13_learning_promotion_public.pem")
    parser.add_argument("--current", default="experiments/promoted/CURRENT.json")
    parser.add_argument("--transition", choices=["bootstrap", "promote", "rollback"], required=True)
    parser.add_argument("--reward-ledger", default="")
    parser.add_argument("--restore-pointer", default="")
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    if args.transition == "promote":
        print(json.dumps({"decision": "hold", "reason": "positive learning promotion remains closed until a versioned improvement-statistics attestation is installed"}, indent=2))
        return 3
    payload_path = _path(args.payload)
    report_path = _path(args.optimizer_report)
    partitions_path = _path(args.partitions)
    manifest_path = _path(args.binding_manifest)
    instrument_path = _path(args.instrument_bundle)
    verification_key = _path(args.verification_key)
    signing_key = _path(args.signing_key)
    public_key = _path(args.promotion_public_key)
    current_path = _path(args.current)
    out_dir = _path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        payload = load_json(payload_path)
        validate_policy_payload(payload)
        partitions = validate_partition_manifest(load_json(partitions_path))
        optimizer_report = load_json(report_path)
        validate_optimizer_report(optimizer_report, partitions)
        instrument = load_json(instrument_path)
        validate_instrument_bundle(instrument, verification_key=verification_key, check_artifacts=True)
        manifest = load_json(manifest_path)
        manifest_verification = verify_binding_manifest(
            manifest,
            verification_key=verification_key,
            changed_paths=args.changed_path or None,
        )
        if manifest_verification["decision"] != "pass":
            raise ValueError(f"BindingManifest verification failed: {manifest_verification['failures']}")
        if manifest["change_class"] not in {"migration", "learning"}:
            raise ValueError("PolicyPayload evaluation requires a migration or learning BindingManifest")
        reward_ref = None
        if args.reward_ledger:
            reward_result = validate_reward_ledger(load_json(_path(args.reward_ledger)))
            reward_path = out_dir / "reward_ingress_attestation.json"
            reward_ref = _attestation(reward_path, {"reward_ingress_attestation_schema_version": "reward_ingress_attestation.v1", "decision": "pass", **reward_result})
        search_payload = {
            "learning_attestation_schema_version": "learning_attestation.v1",
            "role": "search",
            "decision": "pass",
            "payload_sha256": payload["content_sha256"],
            "partition_sha256": partitions["search"]["artifact_sha256"],
            "optimizer_report_sha256": sha256_file(report_path),
        }
        if args.transition == "rollback":
            if not args.restore_pointer:
                raise ValueError("rollback requires --restore-pointer")
            restore_path = _path(args.restore_pointer)
            restore_pointer = load_json(restore_path)
            search_payload["restore_current_pointer"] = restore_pointer
            search_payload["restore_current_pointer_sha256"] = sha256_bytes(restore_path.read_bytes())
        attestations = {
            "search": _attestation(out_dir / "search_attestation.json", search_payload),
            "holdout": _attestation(out_dir / "holdout_attestation.json", {
                "learning_attestation_schema_version": "learning_attestation.v1",
                "role": "holdout",
                "decision": "pass",
                "claim": "boundary_bootstrap_only",
                "partition_sha256": partitions["holdout"]["artifact_sha256"],
                "family_disjoint": True,
            }),
            "forward_shadow": _attestation(out_dir / "forward_shadow_attestation.json", {
                "learning_attestation_schema_version": "learning_attestation.v1",
                "role": "forward_shadow",
                "decision": "pass",
                "claim": "no_effect_boundary_bootstrap_only",
                "partition_sha256": partitions["forward_shadow"]["artifact_sha256"],
                "forward_time": True,
            }),
        }
        record = {
            "promotion_record_schema_version": "promotion_record.v1",
            "record_id": f"p13.6:{args.transition}:{payload['payload_id']}:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            "transition": args.transition,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "payload": artifact_ref(payload_path),
            "previous_current_sha256": sha256_bytes(current_path.read_bytes()),
            "instrument_bundle": {
                "path": artifact_ref(instrument_path)["path"],
                "file_sha256": sha256_file(instrument_path),
                "bundle_sha256": instrument["bundle_sha256"],
                "instrument_epoch": instrument["instrument_epoch"],
            },
            "binding_manifest": {
                "path": artifact_ref(manifest_path)["path"],
                "sha256": sha256_file(manifest_path),
                "manifest_id": manifest["manifest_id"],
            },
            "partition_manifest": artifact_ref(partitions_path),
            "attestations": attestations,
            "reward_evidence": reward_ref,
            "decision": "pass",
            "signer": {"role": "promoter", "algorithm": "rsa-sha256", "public_key_sha256": sha256_file(public_key)},
        }
        signed = sign_promotion_record(record, signing_key, public_key)
        record_path = out_dir / "promotion_record.json"
        atomic_write_json(record_path, signed)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        print(json.dumps({"decision": "hold", "reason": str(error)}, indent=2))
        return 3
    print(json.dumps({"decision": "pass", "record": str(record_path), "record_sha256": sha256_file(record_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
