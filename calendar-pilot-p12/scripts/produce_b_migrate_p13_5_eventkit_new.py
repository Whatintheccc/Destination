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

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.effect_kernel import (
    ManagedCalendarBinding,
    ManagedEventKitRetirementProvider,
    content_sha256,
    managed_commit_confirmation_provenance,
)
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.product_core import run_create_prep_block_vertical
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import CandidateCalendarAction, CodexToolCall, CodexToolName, CodexToolStatus, RawCalendarObservation, UserBiography
from evals.p13_ruler.core import canonical_json_bytes, sha256_bytes
from evals.p13_ruler.wave import resolve, source_revision, utc_now


COMMAND = ["python3", "scripts/produce_b_migrate_p13_5_eventkit_new.py"]
PRODUCER_ID = "b_migrate.new.effect_kernel_eventkit_binding.create_prep_block"
SCENARIO_ID = "create_prep_block.eventkit_binding.p13_5"
CALENDAR_ID = "calendar:managed"
BINDING_ID = "123e4567-e89b-42d3-a456-426614174000"


class FixtureDriver:
    provider_id = "apple_eventkit"

    def __init__(self) -> None:
        self.permission_status = "full_access"
        self.identity = {
            "permission_status": "full_access",
            "writable": True,
            "event_store_id": "store:fixture",
            "calendar_id": CALENDAR_ID,
            "source_id": "source:local",
            "source_type": "local",
            "title": "CalendarPilot Managed",
        }
        self.events: dict[str, dict] = {}

    def binding_identity(self) -> dict:
        return dict(self.identity)

    def snapshot(self, calendar_id: str) -> dict:
        return {"events": dict(self.events) if calendar_id == CALENDAR_ID else {}, "binding_identity": self.binding_identity()}

    def create(self, *, expected_binding: dict, target_vector: dict, idempotency_key: str, projection: dict) -> str:
        self._validate(expected_binding, target_vector)
        external_id = "fixture:event:" + idempotency_key[-16:]
        self.events[idempotency_key] = {"external_id": external_id, **dict(projection)}
        return external_id

    def remove(self, *, expected_binding: dict, target_vector: dict, idempotency_key: str, external_id: str) -> bool:
        self._validate(expected_binding, target_vector)
        row = self.events.get(idempotency_key)
        if row is None or row["external_id"] != external_id:
            return False
        self.events.pop(idempotency_key)
        return True

    def _validate(self, expected: dict, vector: dict) -> None:
        fields = {
            "event_store_id": self.identity["event_store_id"],
            "calendar_id": self.identity["calendar_id"],
            "source_id": self.identity["source_id"],
            "source_type": self.identity["source_type"],
            "title_tripwire": self.identity["title"],
        }
        if any(expected[key] != value for key, value in fields.items()):
            raise ValueError("fixture binding mismatch")
        if vector.get("sha256") != content_sha256({key: value for key, value in vector.items() if key != "sha256"}):
            raise ValueError("fixture target vector mismatch")


class FixtureIncumbent:
    provider_id = "apple_eventkit"

    def __init__(self, observation: RawCalendarObservation) -> None:
        self.observation = observation

    def read_observation(self, *_args, **_kwargs):
        return self.observation

    def preview(self, _candidate):
        return []

    def conflict_truth(self, _candidate):
        return []

    def commit_candidate(self, *_args, **_kwargs):
        raise AssertionError("managed comparison escaped to incumbent commit")

    def rollback(self, _handle):
        raise AssertionError("managed comparison escaped to incumbent undo")


def _fixture() -> tuple[RawCalendarObservation, UserBiography, dict]:
    observation_payload = json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8"))
    biography_payload = json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8"))
    return (
        RawCalendarObservation.from_dict(observation_payload),
        UserBiography.from_dict(biography_payload),
        {"observation": observation_payload, "biography": biography_payload, "goal": "Make next week less chaotic"},
    )


def _bound_candidate(candidate: CandidateCalendarAction) -> CandidateCalendarAction:
    payload = candidate.to_dict()
    payload["target_calendars"] = [CALENDAR_ID]
    for action in payload["actions"]:
        action["calendar_id"] = CALENDAR_ID
        action.setdefault("metadata", {})["calendarpilot_binding_id"] = BINDING_ID
        action["metadata"]["calendarpilot_binding_epoch"] = "1"
    return CandidateCalendarAction.from_dict(payload)


def build_artifact() -> dict:
    observation, biography, frozen_input = _fixture()
    candidate = _bound_candidate(next(
        row for row in DiffusionGemmaPolicy().generate_candidates(observation, biography)
        if row.intent == "create_prep_block"
    ))
    product = run_create_prep_block_vertical(
        observation,
        candidate,
        source_authenticated=True,
        received_at=observation.observed_at,
    )
    projection = product.preview.projection
    if projection is None:
        raise RuntimeError("managed EventKit comparison requires an admitted projection")
    driver = FixtureDriver()
    binding = ManagedCalendarBinding.from_confirmed_setup(
        identity=driver.binding_identity(),
        app_identity={"path": "/Applications/CalendarPilot.app", "sha256": "a" * 64},
        bridge_identity={
            "path": "/Applications/CalendarPilot.app/Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge",
            "sha256": "b" * 64,
        },
        confirmed_at=observation.observed_at,
        binding_id=BINDING_ID,
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        provider = ManagedEventKitRetirementProvider(
            incumbent=FixtureIncumbent(observation),
            driver=driver,
            binding=binding,
            state_root=root / "state",
            signing_key_path=root / "signing.key",
            lease_path=root / "owner.lock",
            seed_observation=observation,
            initialize=True,
            acquire_lease=False,
        )
        kernel = SwiftKernelStub()
        runtime = CodexToolRuntime(kernel=kernel, replay=ReplayBuffer(), provider=provider)
        runtime.frontier[candidate.candidate_id] = candidate
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            scopes=("recommend", "stage", "commit_private", "undo"),
            confirmation_provenance=managed_commit_confirmation_provenance(candidate, binding),
            confirmed_by_user=True,
            issued_at=datetime.now(timezone.utc),
        )
        result = runtime.execute(
            CodexToolCall(
                tool_call_id="p13_5_eventkit_new_commit",
                tool_name=CodexToolName.REQUEST_COMMIT,
                input={"candidate_id": candidate.candidate_id},
                requested_authority_tier=3,
                user_visible_reason="Managed EventKit EffectKernel comparison.",
                authority_grant_id=grant.grant_id,
            ),
            observation,
            biography,
        )
        snapshot = provider.retirement_snapshot()
    if result.status != CodexToolStatus.COMMITTED or result.output.get("effect_receipt", {}).get("phase") != "verified":
        raise RuntimeError(f"managed EventKit fixture did not verify: {result.to_dict()}")
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
            "phase": result.output["effect_receipt"]["phase"],
            "effect_count": snapshot["mutation_count"],
            "compensation_available": bool(result.output["swift_receipt"].get("rollback_handle_id")),
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
