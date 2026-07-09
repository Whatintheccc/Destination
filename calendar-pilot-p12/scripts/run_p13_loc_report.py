#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.p13_ruler.core import build_loc_report


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the versioned P13 tracked-source LOC report")
    parser.add_argument("--before")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--out", default="runs/p13_loc_report.json")
    args = parser.parse_args()
    before = json.loads(_path(args.before).read_text(encoding="utf-8")) if args.before else None
    report = build_loc_report(exclusions=args.exclude, before=before)
    out = _path(args.out)
    _write_json(out, report)
    print(json.dumps({"decision": report["decision"], "out": str(out), "total_lines": report["total_lines"]}, indent=2))
    return 0 if report["decision"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
