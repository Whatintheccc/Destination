#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.p13_ruler.core import build_binding_manifest


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and externally sign a pre-wave P13 BindingManifest")
    parser.add_argument("--wave", required=True)
    parser.add_argument("--change-class", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--instrument-bundle", required=True)
    parser.add_argument("--ownership-map", default="configs/p13_ownership_map.json")
    parser.add_argument("--signing-key", required=True)
    parser.add_argument("--verification-key", required=True)
    parser.add_argument("--expires-in-hours", type=int, default=24)
    parser.add_argument("--out")
    args = parser.parse_args()
    manifest = build_binding_manifest(
        wave=args.wave,
        change_class=args.change_class,
        scope_path=_path(args.scope),
        instrument_bundle_path=_path(args.instrument_bundle),
        ownership_map_path=_path(args.ownership_map),
        signing_key=Path(args.signing_key),
        verification_key=Path(args.verification_key),
        expires_in_hours=args.expires_in_hours,
    )
    out = _path(args.out or f"runs/p13_manifests/{args.wave}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": "pass", "manifest_id": manifest["manifest_id"], "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
