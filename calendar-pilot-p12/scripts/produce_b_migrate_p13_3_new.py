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

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.effect_kernel import (
    DeterministicSandboxAdapter,
    EffectAttempt,
    SandboxAuthorityGate,
    SandboxEffectGateway,
    SandboxEffectLedger,
)
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.product_core import run_create_prep_block_vertical
from calendar_pilot.types import RawCalendarObservation, UserBiography
from evals.p13_ruler.core import canonical_json_bytes, sha256_bytes
from evals.p13_ruler.wave import resolve, source_revision, utc_now


COMMAND = ["python3", "scripts/produce_b_migrate_p13_3_new.py"]
PRODUCER_ID = "b_migrate.new.effect_kernel_sandbox.create_prep_block"
SCENARIO_ID = "create_prep_block.deterministic_effect.p13_3"
SIGNING_KEY = b"p13.3-b-migrate-development-key"


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
    with tempfile.TemporaryDirectory() as td:
        ledger = SandboxEffectLedger(Path(td) / "ledger.json")
        gate = SandboxAuthorityGate(ledger, signing_key=SIGNING_KEY)
        gateway = SandboxEffectGateway(ledger, signing_key=SIGNING_KEY, adapter=DeterministicSandboxAdapter())
        grant = gate.issue_grant(
            grant_id="grant:p13.3:b_migrate",
            action_families=("create_prep_block",),
            scopes=("apply", "compensate"),
            issued_at=observation.observed_at,
            expires_at=observation.observed_at.replace(year=observation.observed_at.year + 1),
            confirmed=True,
        )
        attempt = EffectAttempt.from_preview(
            product.preview,
            source_authenticated=True,
            observed_pre_state_hash=gateway.current_state_hash,
        )
        admission = gate.admit_effect(
            attempt=attempt,
            grant_id=grant.grant_id,
            grant_epoch=grant.epoch,
            nonce="nonce:p13.3:b_migrate",
            now=observation.observed_at,
        )
        if admission.ticket is None:
            raise RuntimeError(f"sandbox fixture did not admit: {admission.reasons}")
        receipt = gateway.execute(admission.ticket, now=observation.observed_at)
        snapshot = gateway.snapshot()
    projection = product.preview.projection
    if projection is None or receipt.phase != "verified":
        raise RuntimeError("sandbox deterministic fixture did not verify")
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
            "phase": receipt.phase,
            "effect_count": snapshot["mutation_count"],
            "compensation_available": bool(receipt.post_state_hash),
        },
        "evidence": {"row_ids": list(product.input_evidence_row_ids)},
        "safety": {"authorizes_production": receipt.authorizes_production, "real_provider_effect": False},
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
