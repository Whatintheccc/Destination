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
from evals.p13_ruler.wave import build_b_migrate_artifact, resolve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    command = ["python3", "scripts/produce_b_migrate_old.py"]
    payload = build_b_migrate_artifact(
        role="old",
        producer_id="b_migrate.old.session_snapshot",
        bound_command=command,
    )
    out = resolve(args.out)
    atomic_write_json(out, payload)
    print(json.dumps({"decision": "pass", "out": str(out), "content_sha256": payload["content_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
