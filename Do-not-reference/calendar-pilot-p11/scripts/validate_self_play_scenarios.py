#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = ROOT / "experiments" / "scenarios"
SEEDS_DIR = ROOT / "experiments" / "seeds"

KNOWN_ADVERSARIES = {
    "conflict_adversary",
    "fatigue_adversary",
    "regret_adversary",
    "engagement_adversary",
}
KNOWN_DISTURBANCES = {
    "remove_prep_slot",
    "increase_notification_fatigue",
    "expire_authority_grant",
    "compress_between_meetings",
    "inject_flexible_hold",
    "add_social_conflict",
    "make_observation_stale",
}
KNOWN_ASSERTIONS = {
    "I2′",
    "I3",
    "I4",
    "I5",
    "I6",
    "I7",
    "M3",
    "S2",
    "S3",
    "S4",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_one(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        scenario = _load(path)
    except Exception as exc:
        return [f"{path}: invalid JSON: {exc}"]
    scenario_id = str(scenario.get("scenario_id", ""))
    if scenario_id != path.stem:
        errors.append(f"{path}: scenario_id must match filename stem")
    seed_id = str(scenario.get("seed_id", ""))
    if not (SEEDS_DIR / f"{seed_id}.json").exists():
        errors.append(f"{path}: seed_id does not exist: {seed_id}")
    if scenario.get("simulator_version") != "sim_v2":
        errors.append(f"{path}: simulator_version must be sim_v2")
    disturbances = scenario.get("disturbances", [])
    if not isinstance(disturbances, list) or not disturbances:
        errors.append(f"{path}: disturbances must be a non-empty list")
    else:
        for item in disturbances:
            if item not in KNOWN_DISTURBANCES:
                errors.append(f"{path}: unknown disturbance {item!r}")
    adversaries = scenario.get("adversaries", [])
    if not isinstance(adversaries, list) or not adversaries:
        errors.append(f"{path}: adversaries must be a non-empty list")
    else:
        for item in adversaries:
            if item not in KNOWN_ADVERSARIES:
                errors.append(f"{path}: unknown adversary {item!r}")
    assertions = scenario.get("invariant_assertions", [])
    if not isinstance(assertions, list) or not assertions:
        errors.append(f"{path}: invariant_assertions must be a non-empty list")
    else:
        for item in assertions:
            if item not in KNOWN_ASSERTIONS:
                errors.append(f"{path}: unknown invariant assertion {item!r}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario-dir", default=str(SCENARIOS_DIR))
    args = parser.parse_args()
    root = Path(args.scenario_dir)
    paths = sorted(root.glob("*.json"))
    errors: list[str] = []
    if not paths:
        errors.append(f"no scenario files found in {root}")
    for path in paths:
        errors.extend(validate_one(path))
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print(json.dumps({"scenario_files": len(paths), "status": "ok"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
