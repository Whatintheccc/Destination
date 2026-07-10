#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.codex.tools import CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.effect_kernel import DeterministicRetirementProvider
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.product_core import run_create_prep_block_vertical
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.types import CodexToolCall, CodexToolName, RawCalendarObservation, UserBiography
from evals.p13_ruler.core import canonical_json_bytes, sha256_bytes
from evals.p13_ruler.wave import resolve, source_revision, utc_now


COMMAND = ["python3", "scripts/produce_b_migrate_p13_5_new.py"]
PRODUCER_ID = "b_migrate.new.effect_kernel_retirement.create_prep_block"
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
    product = run_create_prep_block_vertical(
        observation,
        candidate,
        source_authenticated=True,
        received_at=observation.observed_at,
    )
    projection = product.preview.projection
    if projection is None:
        raise RuntimeError("P13.5 comparison requires an admitted projection")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        provider = DeterministicRetirementProvider(
            state_path=root / "ledger.json",
            signing_key_path=root / "signing.key",
            seed_observation=observation,
        )
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            scopes=("recommend", "stage", "commit_private", "undo"),
            confirmation_provenance="p13.5_b_migrate",
            confirmed_by_user=True,
            issued_at=datetime.now(timezone.utc),
        )
        runtime = CodexToolRuntime(kernel=kernel, replay=ReplayBuffer(), provider=provider)
        runtime.frontier[candidate.candidate_id] = candidate
        receipt = runtime.execute(
            CodexToolCall(
                tool_call_id="tool:p13.5:b_migrate",
                tool_name=CodexToolName.REQUEST_COMMIT,
                input={"candidate_id": candidate.candidate_id},
                requested_authority_tier=3,
                user_visible_reason="P13.5 independent migration comparison",
                authority_grant_id=grant.grant_id,
                correlation_id="trace:p13.5:b_migrate",
                created_at=datetime.now(timezone.utc),
            ),
            observation,
            biography,
        )
        snapshot = provider.retirement_snapshot()
    effect_receipt = receipt.output.get("effect_receipt", {})
    if receipt.status.value != "committed" or effect_receipt.get("phase") != "verified":
        raise RuntimeError(f"P13.5 runtime comparison did not verify: {receipt.to_dict()}")
    observable = {
        "action_family": product.preview.action_family,
        "candidate_id": product.preview.candidate_id,
        "projection": {
            "title": projection.title,
            "start": projection.start,
            "end": projection.end,
            "calendar_id": projection.calendar_id,
            "explanation": projection.explanation,
        },
        "outcome": {
            "phase": effect_receipt["phase"],
            "effect_count": snapshot["mutation_count"],
            "compensation_available": bool(receipt.output.get("swift_receipt", {}).get("rollback_handle_id")),
        },
        "evidence": {"row_ids": list(product.input_evidence_row_ids)},
        "safety": {"authorizes_production": False, "real_provider_effect": False},
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
