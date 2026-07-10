#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import RawCalendarObservation, UserBiography, authority_scopes_for_tier
from evals.p13_ruler.core import canonical_json_bytes, sha256_bytes
from evals.p13_ruler.wave import resolve, source_revision, utc_now


COMMAND = ["python3", "scripts/produce_b_migrate_p13_1_old.py"]
PRODUCER_ID = "b_migrate.old.swift_preview.create_prep_block"
SCENARIO_ID = "create_prep_block.no_effect.v1"


def _fixture() -> tuple[RawCalendarObservation, UserBiography, dict]:
    observation_payload = json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8"))
    biography_payload = json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8"))
    return (
        RawCalendarObservation.from_dict(observation_payload),
        UserBiography.from_dict(biography_payload),
        {"observation": observation_payload, "biography": biography_payload, "goal": "Make next week less chaotic"},
    )


def build_artifact() -> dict:
    observation, biography, frozen_input = _fixture()
    candidate = next(
        row
        for row in DiffusionGemmaPolicy().generate_candidates(observation, biography)
        if row.intent == "create_prep_block"
    )
    kernel = SwiftKernelStub()
    grant = kernel.issue_authority_grant(
        user_scope_id=observation.user_scope_id,
        max_authority_tier=3,
        scopes=authority_scopes_for_tier(3),
        confirmation_provenance="p13_1_incumbent_preview_fixture",
        confirmed_by_user=True,
        issued_at=observation.observed_at,
    )
    receipt = kernel.preview_candidate(
        candidate,
        observation,
        authority_grant=grant.grant_id,
        requested_authority_tier=3,
        correlation_id="p13_1_create_prep_block",
    )
    if receipt.denied_reason is not None or receipt.actuation_mode.value != "no_op":
        raise RuntimeError("incumbent preview fixture unexpectedly denied or materialized")
    action = candidate.actions[0]
    row_ids = [f"observation:{observation.observation_id}", f"proposal:{candidate.candidate_id}"]
    observable = {
        "action_family": candidate.intent,
        "candidate_id": candidate.candidate_id,
        "projection": {
            "title": action.title,
            "start": action.start.isoformat() if action.start else None,
            "end": action.end.isoformat() if action.end else None,
            "calendar_id": action.calendar_id,
            "explanation": candidate.explanation,
        },
        "admission": {"status": "preview", "can_dispatch": False, "denial_reasons": []},
        "evidence": {"row_ids": row_ids},
        "effects": {"effect_attempts": 0, "claims": 0, "dispatches": 0, "provider_mutations": 0},
    }
    stable = {
        "role": "old",
        "producer": {"producer_id": PRODUCER_ID, "bound_command": COMMAND},
        "source_revision": source_revision(),
        "input": {
            "scenario_id": SCENARIO_ID,
            "input_sha256": sha256_bytes(canonical_json_bytes(frozen_input)),
        },
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
