#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.p13_ruler.attestation_scaffold import (
    ScaffoldError,
    validate_report_schema,
    verify_attestation_scaffold,
    write_external_json,
)


def _optional_path(value: str) -> Path | None:
    return Path(value) if value else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify non-authorizing P13 attestation scaffold mechanics")
    parser.add_argument("--policy", default="", help="Absolute external scaffold-policy path")
    parser.add_argument("--packet", default="", help="Absolute external evaluator-packet path")
    parser.add_argument("--review", default="", help="Absolute external reviewer-attestation path")
    parser.add_argument("--out", required=True, help="Absolute external report path")
    args = parser.parse_args()

    report = verify_attestation_scaffold(
        policy_path=_optional_path(args.policy),
        packet_path=_optional_path(args.packet),
        review_path=_optional_path(args.review),
    )
    try:
        validate_report_schema(report)
        out = write_external_json(Path(args.out), report)
    except ScaffoldError as error:
        report["decision"] = "fail"
        report["mechanics_valid"] = False
        report["checks"].append({"name": "output", "status": "fail", "detail": error.detail})
        report["failures"].append({"code": error.code, "detail": error.detail})
        validate_report_schema(report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    print(
        json.dumps(
            {
                "decision": report["decision"],
                "authorizes_migration": False,
                "mechanics_valid": report["mechanics_valid"],
                "out": str(out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if report["decision"] == "fail" else 3


if __name__ == "__main__":
    raise SystemExit(main())
