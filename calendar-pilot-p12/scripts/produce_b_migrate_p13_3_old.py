#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.providers import DeterministicCalendarProvider
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import CodexToolCall, CodexToolName, CodexToolStatus, RawCalendarObservation, UserBiography
from evals.p13_ruler.core import canonical_json_bytes, sha256_bytes
from evals.p13_ruler.wave import resolve, source_revision, utc_now


COMMAND = ["python3", "scripts/produce_b_migrate_p13_3_old.py"]
PRODUCER_ID = "b_migrate.old.incumbent_deterministic.create_prep_block"
SCENARIO_ID = "create_prep_block.deterministic_effect.p13_3"


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
        row for row in DiffusionGemmaPolicy().generate_candidates(observation, biography)
        if row.intent == "create_prep_block"
    )
    provider = DeterministicCalendarProvider(seed_observation=observation)
    runtime = CodexToolRuntime(kernel=SwiftKernelStub(), provider=provider)
    grant = runtime.kernel.issue_authority_grant(
        user_scope_id=observation.user_scope_id,
        max_authority_tier=3,
        issued_at=observation.observed_at,
        confirmed_by_user=True,
    )
    result = runtime.execute(
        CodexToolCall(
            "p13_3_old_commit",
            CodexToolName.REQUEST_COMMIT,
            {"candidate": candidate.to_dict()},
            3,
            "incumbent deterministic comparison",
            authority_grant_id=grant.grant_id,
        ),
        observation,
        biography,
    )
    if result.status != CodexToolStatus.COMMITTED:
        raise RuntimeError(f"incumbent deterministic fixture did not commit: {result.status.value}")
    action = candidate.actions[0]
    provider_receipt = result.output["provider_receipt"]
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
        "outcome": {
            "phase": "verified",
            "effect_count": len(provider_receipt["created_external_ids"]),
            "compensation_available": bool(result.output["swift_receipt"].get("rollback_handle_id")),
        },
        "evidence": {
            "row_ids": [f"observation:{observation.observation_id}", f"proposal:{candidate.candidate_id}"],
        },
        "safety": {"authorizes_production": False, "real_provider_effect": False},
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
