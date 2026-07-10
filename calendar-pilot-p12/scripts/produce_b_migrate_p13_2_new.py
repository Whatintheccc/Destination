#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
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
from scripts.produce_b_migrate_p13_2_old import PROTECTED_FIELDS, SCENARIO_ID, _input


COMMAND = ["python3", "scripts/produce_b_migrate_p13_2_new.py"]
PRODUCER_ID = "b_migrate.new.cited_product_core_candidate_card.create_prep_block"


def build_artifact() -> dict:
    frozen_input = _input()
    previous = os.environ.get("CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE")
    os.environ["CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE"] = "cited"
    try:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            session = DogfoodSessionState(run_dir=run_dir)
            try:
                session.create_plan(frozen_input["goal"])
                card = next(row for row in session.view()["frontier"]["candidates"] if row.get("intent") == "create_prep_block")
                journal_row_ids = {
                    str(row.payload.get("journal_event", {}).get("row_id"))
                    for row in session.replay.records
                    if row.record_type == "product_core_journal_event"
                }
            finally:
                session.close()
            restored = DogfoodSessionState(run_dir=run_dir)
            try:
                restored_card = next(row for row in restored.view()["frontier"]["candidates"] if row.get("intent") == "create_prep_block")
            finally:
                restored.close()
    finally:
        if previous is None:
            os.environ.pop("CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE", None)
        else:
            os.environ["CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE"] = previous
    citation = card.get("citation", {})
    if citation.get("projection_version") != "product_core.cited_candidate_card.v1" or not citation.get("event_ids"):
        raise RuntimeError("P13.2 cited ProductCore card is unavailable")
    observable = {
        "protected_card": {key: card.get(key) for key in PROTECTED_FIELDS},
        "controls": card.get("controls", []),
        "citation": card.get("citation", {}),
        "projection": card.get("projection", {}),
        "all_citations_in_journal": bool(card.get("citation", {}).get("event_ids"))
        and set(card.get("citation", {}).get("event_ids", [])).issubset(journal_row_ids),
        "restart_restored": card == restored_card,
        "effect_owner": "incumbent",
        "new_effect_counts": card.get("new_effect_counts", {}),
    }
    stable = {
        "role": "new",
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
