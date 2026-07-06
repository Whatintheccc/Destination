#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.environment.explain import (
    explain_authority,
    explain_candidate,
    explain_provider,
    explain_trajectory,
)
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import (
    ActuationMode,
    AuthorityGrant,
    Belief,
    CalendarActionReceipt,
    RawCalendarObservation,
    RewardEvent,
    SemanticSignal,
    StageState,
    UserBiography,
)


def _load_fixture_candidate() -> Any:
    observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8")))
    biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8")))
    candidate = DiffusionGemmaPolicy().generate_candidates(observation, biography)[0]
    candidate.model_story = candidate.model_story or ["The requested focus block fits an open slot.", "The action is reversible."]
    candidate.control_notes = candidate.control_notes or ["Requires explicit authority before commit."]
    candidate.counterfactual = candidate.counterfactual or "Without the block, the preparation window remains fragmented."
    return candidate


def _validate_answer(answer: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ["answer_id", "object_type", "object_id", "claim", "evidence_row_ids", "confidence", "controls", "version", "answer"]:
        if answer.get(field) in ("", None, [], {}):
            errors.append(f"{answer.get('object_type', 'unknown')} missing {field}")
    confidence = answer.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
        errors.append(f"{answer.get('object_type', 'unknown')} confidence out of range")
    return errors


def build_report() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    candidate = _load_fixture_candidate()
    receipt = CalendarActionReceipt(
        receipt_id="receipt_explain_commit",
        candidate_id=candidate.candidate_id,
        executed_at=now,
        executed_by="SwiftKernelStub",
        authority_tier_used=3,
        sync_status="committed",
        rollback_handle_id="rollback_explain",
        conflict_check_passed=True,
        generated_event_ids=["event_explain"],
        provider_id="local_stub",
        actuation_mode=ActuationMode.MATERIALIZED_WRITE,
        authority_grant_id="grant_explain",
        confirmation_provenance="fixture_user_confirmed",
        stage_state=StageState.COMMITTED,
        correlation_id=candidate.candidate_id,
    )
    reward = RewardEvent(
        reward_event_id="reward_explain",
        receipt_id=receipt.receipt_id,
        observed_at=now,
        explicit_useful=True,
        utility_reward=0.7,
        total_reward=0.9,
        provenance="human_ui",
    )
    replay = ReplayBuffer()
    replay.append_reward(reward, candidate=candidate, receipt=receipt, trace_id=candidate.candidate_id)
    reward_row_id = replay.records[-1].record_id
    signal = SemanticSignal(
        signal_id="sig_explain_prep_blocks_help",
        user_scope_id="default_user",
        label="prep_blocks_help",
        statement="Create-prep-block suggestions are useful for this user when the block is reversible.",
        evidence=[reward_row_id],
        confidence=0.82,
        status="active",
        estimator_version="interruption_tolerance_v1",
    )
    signal_row_id = replay.append_semantic_signal(signal.to_dict(), trace_id=signal.signal_id, causal_parent_id=reward_row_id)
    activation_row_id = replay.append_label_activation(
        {
            "activation_id": "activation_explain",
            "signal_id": signal.signal_id,
            "user_scope_id": signal.user_scope_id,
            "status": "active",
            "actor": "user",
            "surface": "dogfood",
            "at": now.isoformat(),
            "reason": "explicit useful feedback",
        },
        trace_id=signal.signal_id,
        causal_parent_id=signal_row_id,
    )
    belief = Belief.from_semantic_signal(signal, activation_row_ids=[signal_row_id, activation_row_id])
    denied_receipt = CalendarActionReceipt(
        receipt_id="receipt_authority_denied",
        candidate_id=candidate.candidate_id,
        executed_at=now,
        executed_by="SwiftKernelStub",
        authority_tier_used=0,
        sync_status="denied",
        rollback_handle_id=None,
        conflict_check_passed=False,
        provider_id="local_stub",
        actuation_mode=ActuationMode.DENIED,
        denied_reason="authority_scope_missing",
        stage_state=StageState.DENIED,
        correlation_id=candidate.candidate_id,
    )
    revoked_grant = AuthorityGrant(
        grant_id="grant_revoked",
        user_scope_id="default_user",
        max_authority_tier=3,
        scopes=["stage", "undo"],
        issued_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
        confirmation_provenance="fixture_user_confirmed",
        confirmed_by_user=True,
    ).to_dict()
    revoked_grant["status"] = "revoked"
    revoked_grant["revoked_at"] = now.isoformat()
    provider_payload = {
        "provider_id": "local_stub",
        "operation": "commit",
        "calendar_id": "CalendarPilot SelfPlay",
        "rollback_handle_id": "rollback_explain",
        "rollback_verified": True,
    }
    provider_row_id = replay.append_provider_transaction(operation="commit", transaction=provider_payload, trace_id=candidate.candidate_id)
    trajectory_records = [record.envelope() for record in replay.records]
    answers = {
        "belief": belief.explain("Why is this belief active?").to_dict(),
        "authority_denial": explain_authority(denied_receipt, "Why was authority denied?", evidence_row_ids=["receipt:receipt_authority_denied"]).to_dict(),
        "authority_revocation": explain_authority(revoked_grant, "Why is the grant unavailable?", evidence_row_ids=["authority_grant:grant_revoked"]).to_dict(),
        "candidate": explain_candidate(candidate, "Why this candidate?", evidence_row_ids=[f"candidate:{candidate.candidate_id}", reward_row_id]).to_dict(),
        "provider": explain_provider(provider_payload, "What did the provider do?", evidence_row_ids=[provider_row_id]).to_dict(),
        "trajectory": explain_trajectory(trajectory_records, "What happened in this trace?").to_dict(),
    }
    errors: list[str] = []
    for answer in answers.values():
        errors.extend(_validate_answer(answer))
    requirements = {
        "constructible_belief": bool(belief.to_dict()),
        "common_explain_answer_shape": all(not _validate_answer(answer) for answer in answers.values()),
        "replay_visible_evidence_row_ids": all(answer.get("evidence_row_ids") for answer in answers.values()),
        "confidence": all(isinstance(answer.get("confidence"), (int, float)) for answer in answers.values()),
        "controls": all(bool(answer.get("controls")) for answer in answers.values()),
        "versioning": all(bool(answer.get("version")) for answer in answers.values()),
        "authority_denial": answers["authority_denial"]["status"] == "denied",
        "authority_revocation": answers["authority_revocation"]["status"] == "revoked",
        "candidate": answers["candidate"]["object_type"] == "Candidate",
        "provider": answers["provider"]["object_type"] == "Provider",
        "trajectory": answers["trajectory"]["object_type"] == "Trajectory",
    }
    decision = "pass" if all(requirements.values()) and not errors else "hold"
    return {
        "belief_explain_report_schema_version": "belief_explain_report.v1",
        "decision": decision,
        "requirements": requirements,
        "belief": belief.to_dict(),
        "answers": answers,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="runs/p12_belief_explain_report.json")
    args = parser.parse_args()
    payload = build_report()
    out = Path(args.out)
    out = out if out.is_absolute() else ROOT / out
    atomic_write_json(out, payload)
    print(json.dumps({"ok": payload["decision"] == "pass", "decision": payload["decision"], "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
