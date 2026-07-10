#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json
from evals.p13_ruler.wave import build_experiment_record, resolve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--binding-verification", required=True)
    parser.add_argument("--architecture-report", required=True)
    parser.add_argument("--cvar-report", required=True)
    parser.add_argument("--b-migrate-report", required=True)
    parser.add_argument("--release-report", required=True)
    parser.add_argument("--reward-report", required=True)
    parser.add_argument("--root-list-report", required=True)
    parser.add_argument("--loc-report", required=True)
    parser.add_argument("--out", default="runs/p13_experiment_record.json")
    args = parser.parse_args()
    record = build_experiment_record(
        manifest_path=resolve(args.manifest),
        binding_verification_path=resolve(args.binding_verification),
        architecture_report_path=resolve(args.architecture_report),
        cvar_report_path=resolve(args.cvar_report),
        b_migrate_report_path=resolve(args.b_migrate_report),
        release_report_path=resolve(args.release_report),
        reward_report_path=resolve(args.reward_report),
        root_list_report_path=resolve(args.root_list_report),
        loc_report_path=resolve(args.loc_report),
    )
    out = resolve(args.out)
    atomic_write_json(out, record)
    print(json.dumps({"ok": record["decision"] == "pass", "decision": record["decision"], "out": str(out)}, indent=2))
    raise SystemExit(0 if record["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
