#!/usr/bin/env python3
"""Fail-closed P13.6 policy pointer transition.

Legacy automatic/forced calls remain a zero-write hold.  The sole writable aperture is
an already-signed PromotionRecord whose payload, evidence, instrument, manifest, signer,
and previous-CURRENT precondition all verify before one atomic pointer replacement.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.p13_learning_control import (
        APP_ROOT,
        atomic_write_json,
        current_pointer,
        load_json,
        load_promotion_root,
        resolve_artifact,
        sha256_bytes,
        validate_promotion_record,
    )
except ModuleNotFoundError:  # direct script execution places scripts/ on sys.path
    from p13_learning_control import (
        APP_ROOT,
        atomic_write_json,
        current_pointer,
        load_json,
        load_promotion_root,
        resolve_artifact,
        sha256_bytes,
        validate_promotion_record,
    )


FROZEN_PHASE = "P13.6-signed-record-only"


def frozen_result(*, batch: str, requested_decision: str) -> dict[str, object]:
    return {
        "promotion_record_schema_version": "promotion_frozen.v1",
        "batch": batch,
        "requested_decision": requested_decision or "automatic",
        "decision": "hold",
        "phase": FROZEN_PHASE,
        "promotion_artifact_writes": 0,
        "reason": "promotion requires an independently signed passing PromotionRecord",
    }


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else APP_ROOT / path


def apply_signed_record(*, record_path: Path, current_path: Path, root_path: Path | None = None) -> dict[str, object]:
    before = current_path.read_bytes()
    record = load_json(record_path)
    _, public_key = load_promotion_root(root_path)
    validate_promotion_record(record, public_key=public_key, current_bytes=before, promotion_root=root_path)
    if record["transition"] == "promote":
        raise ValueError("positive learning promotion remains closed until a versioned improvement-statistics attestation is installed")
    pointer = current_pointer(record_path, record)
    if record["transition"] == "rollback":
        search_attestation = load_json(resolve_artifact(record["attestations"]["search"]))
        pointer = search_attestation.get("restore_current_pointer")
        if not isinstance(pointer, dict) or pointer.get("current_policy_pointer_schema_version") != "current_policy_pointer.v1":
            raise ValueError("signed rollback attestation lacks a valid restore CURRENT pointer")
        target_record = load_json(resolve_artifact(pointer["promotion_record"]))
        validate_promotion_record(target_record, public_key=public_key, promotion_root=root_path)
        if target_record["payload"]["sha256"] != record["payload"]["sha256"] or pointer.get("payload_sha256") != record["payload"]["sha256"]:
            raise ValueError("signed rollback target does not restore the authorized payload")
    atomic_write_json(current_path, pointer)
    return {
        "decision": "pass",
        "transition": record["transition"],
        "record_id": record["record_id"],
        "previous_current_sha256": sha256_bytes(before),
        "current_sha256": sha256_bytes(current_path.read_bytes()),
        "payload_sha256": record["payload"]["sha256"],
        "atomic_pointer_writes": 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", default="")
    parser.add_argument("--thresholds", default="experiments/configs/promotion_thresholds.json")
    parser.add_argument("--candidate-tuning", default="")
    parser.add_argument("--decide", choices=["promote", "hold", "rollback"], default="")
    parser.add_argument("--human-note", default="")
    parser.add_argument("--record", default="")
    parser.add_argument("--current", default="experiments/promoted/CURRENT.json")
    parser.add_argument("--promotion-root", default="configs/p13_learning_promotion_root.json")
    args = parser.parse_args()
    if not args.record:
        payload = frozen_result(batch=args.batch, requested_decision=args.decide)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 3
    if args.decide or args.candidate_tuning or args.human_note:
        print(json.dumps({"decision": "hold", "promotion_artifact_writes": 0, "reason": "unsigned decision and payload overrides are forbidden"}, indent=2))
        return 3
    current_path = _path(args.current)
    try:
        result = apply_signed_record(
            record_path=_path(args.record),
            current_path=current_path,
            root_path=_path(args.promotion_root),
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        print(json.dumps({"decision": "hold", "promotion_artifact_writes": 0, "reason": str(error)}, indent=2))
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
