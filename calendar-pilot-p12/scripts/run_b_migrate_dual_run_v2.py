#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json
from evals.p13_ruler.wave import b_migrate_assertions_path, compare_b_migrate_artifacts, load_json, resolve


def _command(manifest: dict, side: str) -> list[str]:
    field = "old_producer" if side == "old" else "new_producer"
    command = manifest.get(field, {}).get("b_migrate", {}).get("command")
    if not isinstance(command, list) or not command or not all(isinstance(value, str) and value for value in command):
        raise ValueError(f"BindingManifest has no valid {side} B_migrate producer command")
    return list(command)


def _produce(command: list[str], out: Path) -> None:
    process = subprocess.run([*command, "--out", str(out)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if process.returncode != 0:
        raise RuntimeError(f"producer failed ({' '.join(command)}): {process.stderr[-2000:]}")
    if not out.is_file():
        raise RuntimeError(f"producer did not write {out}")


def _assertions_path(manifest: dict, explicit: str = "") -> Path:
    fallback = resolve(explicit) if explicit else ROOT / "experiments/configs/b_migrate_frontend_view_state_v2.json"
    selected = b_migrate_assertions_path(manifest, fallback=fallback)
    if explicit and selected.resolve() != fallback.resolve():
        raise ValueError("--assertions cannot override the BindingManifest assertion set")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--before-artifact", default="")
    parser.add_argument("--after-artifact", default="")
    parser.add_argument("--assertions", default="")
    parser.add_argument("--artifacts-dir", default="runs/b_migrate_v2_artifacts")
    parser.add_argument("--out", default="runs/b_migrate_report_v2.json")
    args = parser.parse_args()
    manifest = load_json(resolve(args.manifest))
    artifacts_dir = resolve(args.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    before = resolve(args.before_artifact) if args.before_artifact else artifacts_dir / "old.json"
    after = resolve(args.after_artifact) if args.after_artifact else artifacts_dir / "new.json"
    if not args.before_artifact:
        _produce(_command(manifest, "old"), before)
    if not args.after_artifact:
        _produce(_command(manifest, "new"), after)
    payload = compare_b_migrate_artifacts(
        before_path=before,
        after_path=after,
        assertions_path=_assertions_path(manifest, args.assertions),
        manifest=manifest,
    )
    out = resolve(args.out)
    atomic_write_json(out, payload)
    print(json.dumps({"ok": payload["decision"] == "pass", "decision": payload["decision"], "out": str(out)}, indent=2))
    raise SystemExit(0 if payload["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
