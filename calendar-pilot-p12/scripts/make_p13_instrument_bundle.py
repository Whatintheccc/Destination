#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.p13_ruler.core import build_instrument_bundle


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze the P13 evaluator InstrumentBundle")
    parser.add_argument("--verification-key", required=True)
    parser.add_argument("--artifacts", default="configs/p13_instrument_artifacts.json")
    parser.add_argument("--out", default="runs/p13_instrument_bundle.json")
    parser.add_argument("--allow-dirty", action="store_true", help="test/bootstrap only; never valid for a wave")
    args = parser.parse_args()
    bundle = build_instrument_bundle(
        verification_key=Path(args.verification_key),
        artifact_config=_path(args.artifacts),
        require_clean=not args.allow_dirty,
    )
    out = _path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": "pass", "out": str(out), "bundle_sha256": bundle["bundle_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
