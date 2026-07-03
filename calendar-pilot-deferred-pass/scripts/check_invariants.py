#!/usr/bin/env python3
"""Check CalendarPilot replay invariants over a JSONL replay export."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.invariants import check_replay  # noqa: E402


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    records = load_records(Path(args.replay))
    violations = [v.__dict__ for v in check_replay(records)]
    payload = {"replay": args.replay, "records": len(records), "violations": violations, "ok": not violations}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(1 if violations else 0)


if __name__ == "__main__":
    main()
