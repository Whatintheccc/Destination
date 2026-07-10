#!/usr/bin/env python3
"""Frozen P13.0-P13.5 promotion access point.

P12's lab promoter could force ``--decide promote`` after failed gates and wrote
candidate reports before deciding.  There is intentionally no writable promotion
aperture until P13.6 installs immutable PolicyPayload and signed PromotionRecord
contracts.  Keep this refusal at the process boundary so direct invocation and the
Make target have identical behavior.
"""
from __future__ import annotations

import argparse
import json


FROZEN_PHASE = "P13.0-P13.5"


def frozen_result(*, batch: str, requested_decision: str) -> dict[str, object]:
    return {
        "promotion_record_schema_version": "promotion_frozen.v1",
        "batch": batch,
        "requested_decision": requested_decision or "automatic",
        "decision": "hold",
        "phase": FROZEN_PHASE,
        "promotion_artifact_writes": 0,
        "reason": "promotion is unavailable until P13.6 signed PolicyPayload/PromotionRecord gates exist",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True)
    parser.add_argument("--thresholds", default="experiments/configs/promotion_thresholds.json")
    parser.add_argument("--candidate-tuning", default="")
    parser.add_argument("--decide", choices=["promote", "hold", "rollback"], default="")
    parser.add_argument("--human-note", default="")
    args = parser.parse_args()
    payload = frozen_result(batch=args.batch, requested_decision=args.decide)
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(3)


if __name__ == "__main__":
    main()
