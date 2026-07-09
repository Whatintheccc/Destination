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
from evals.p13_ruler.wave import compare_cvar_frontier_sets, load_json, resolve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--before-artifact", required=True)
    parser.add_argument("--after-artifact", required=True)
    parser.add_argument("--thresholds", default="experiments/configs/cvar_thresholds.json")
    parser.add_argument("--out", default="runs/cvar_report_v2.json")
    args = parser.parse_args()
    payload = compare_cvar_frontier_sets(
        before_path=resolve(args.before_artifact),
        after_path=resolve(args.after_artifact),
        thresholds_path=resolve(args.thresholds),
        manifest=load_json(resolve(args.manifest)),
    )
    out = resolve(args.out)
    atomic_write_json(out, payload)
    print(json.dumps({"ok": payload["decision"] == "pass", "decision": payload["decision"], "out": str(out)}, indent=2))
    raise SystemExit(0 if payload["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
