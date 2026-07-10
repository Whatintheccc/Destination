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
from evals.p13_ruler.wave import build_cvar_frontier_set, resolve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["before", "after"], required=True)
    parser.add_argument("--current", default="experiments/promoted/CURRENT.json")
    parser.add_argument("--seed-set", default="experiments/configs/cvar_seed_set.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    producer_id = f"cvar.{args.role}.current"
    bound_command = [
        "python3",
        "scripts/produce_cvar_frontier.py",
        "--role",
        args.role,
        "--current",
        args.current,
    ]
    if args.seed_set != "experiments/configs/cvar_seed_set.json":
        bound_command.extend(["--seed-set", args.seed_set])
    payload = build_cvar_frontier_set(
        role=args.role,
        current_path=resolve(args.current),
        seed_set_path=resolve(args.seed_set),
        producer_id=producer_id,
        bound_command=bound_command,
    )
    out = resolve(args.out)
    atomic_write_json(out, payload)
    print(json.dumps({"decision": "pass", "out": str(out), "content_sha256": payload["content_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
