#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.frontend.session import DogfoodSessionState
from evals.p13_ruler.core import canonical_json_bytes, sha256_bytes
from evals.p13_ruler.wave import resolve, source_revision, utc_now


COMMAND = ["python3", "scripts/produce_b_migrate_p13_2_old.py"]
PRODUCER_ID = "b_migrate.old.incumbent_candidate_card.create_prep_block"
SCENARIO_ID = "create_prep_block.cited_read_side.v1"
PROTECTED_FIELDS = [
    "candidate_id", "control_notes", "intent", "model_story", "rank",
    "required_authority_tier", "reward_breakdown", "right_moment_decision",
    "status_hint", "subtitle", "title", "type",
]


def _input() -> dict:
    return {
        "scenario_id": SCENARIO_ID,
        "goal": "Make next week less chaotic",
        "observation": json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8")),
        "biography": json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8")),
    }


def _controls(candidate_id: str) -> list[dict]:
    manifest = json.loads((ROOT / "experiments/configs/create_prep_block_required_fields_v1.json").read_text(encoding="utf-8"))
    return [row | {"route": row["route_template"].format(candidate_id=candidate_id)} for row in manifest["controls"]]


def build_artifact() -> dict:
    frozen_input = _input()
    with tempfile.TemporaryDirectory() as td:
        session = DogfoodSessionState(run_dir=Path(td))
        try:
            snapshot = session.create_plan(frozen_input["goal"])
            card = next(row for row in snapshot["chat"]["candidate_cards"] if row.get("intent") == "create_prep_block")
        finally:
            session.close()
    observable = {
        "protected_card": {key: card.get(key) for key in PROTECTED_FIELDS},
        "controls": _controls(str(card["candidate_id"])),
        "effect_owner": "incumbent",
        "new_effect_counts": {"effect_attempts": 0, "claims": 0, "dispatches": 0, "provider_mutations": 0},
    }
    stable = {
        "role": "old",
        "producer": {"producer_id": PRODUCER_ID, "bound_command": COMMAND},
        "source_revision": source_revision(),
        "input": {"scenario_id": SCENARIO_ID, "input_sha256": sha256_bytes(canonical_json_bytes(frozen_input))},
        "lineage": {"derived_from_artifact_sha256": None},
        "observable": observable,
        "observable_sha256": sha256_bytes(canonical_json_bytes(observable)),
    }
    return {
        "b_migrate_artifact_schema_version": "b_migrate_artifact.v1",
        "generated_at": utc_now(),
        **stable,
        "content_sha256": sha256_bytes(canonical_json_bytes(stable)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_artifact()
    out = resolve(args.out)
    atomic_write_json(out, payload)
    print(json.dumps({"decision": "pass", "out": str(out), "content_sha256": payload["content_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
