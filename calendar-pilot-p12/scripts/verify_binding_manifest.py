#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.p13_ruler.core import verify_binding_manifest


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a signed P13 BindingManifest and derive affectedness")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--verification-key", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    manifest_path = _path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = verify_binding_manifest(manifest, verification_key=Path(args.verification_key))
    out = _path(args.out) if args.out else manifest_path.with_name(f"{manifest_path.stem}.verification.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": report["decision"], "out": str(out), "failures": report["failures"]}, indent=2))
    return 0 if report["decision"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
