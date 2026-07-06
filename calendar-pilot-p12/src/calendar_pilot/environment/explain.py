from __future__ import annotations

import hashlib
import json
from typing import Any

from calendar_pilot.types import (
    AuthorityGrant,
    Belief,
    CalendarActionReceipt,
    CandidateCalendarAction,
    ExplanationAnswer,
)

EXPLAIN_VERSION = "explain.v1"


def _dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return dict(value or {})


def _answer_id(object_type: str, object_id: str, question: str, evidence_row_ids: list[str]) -> str:
    raw = json.dumps(
        {
            "object_type": object_type,
            "object_id": object_id,
            "question": question,
            "evidence": evidence_row_ids,
        },
        sort_keys=True,
        default=str,
    )
    return f"answer:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def _make_answer(
    *,
    object_type: str,
    object_id: str,
    question: str,
    claim: str,
    evidence_row_ids: list[str],
    confidence: float,
    controls: dict[str, Any],
    answer: str,
    status: str = "answered",
) -> ExplanationAnswer:
    return ExplanationAnswer(
        answer_id=_answer_id(object_type, object_id, question, evidence_row_ids),
        object_type=object_type,
        object_id=object_id,
        question=question,
        claim=claim,
        evidence_row_ids=list(dict.fromkeys(str(x) for x in evidence_row_ids if str(x))),
        confidence=max(0.0, min(1.0, float(confidence))),
        controls=controls,
        version=EXPLAIN_VERSION,
        answer=answer,
        status=status,
    )


def explain_belief(belief: Belief, question: str) -> ExplanationAnswer:
    return _make_answer(
        object_type="Belief",
        object_id=belief.belief_id,
        question=question,
        claim=belief.claim,
        evidence_row_ids=belief.evidence_row_ids,
        confidence=belief.confidence,
        controls={
            **belief.controls,
            "status": belief.status,
            "source_object_type": belief.source_object_type,
            "source_object_id": belief.source_object_id,
        },
        answer=f"{belief.claim} Confidence {belief.confidence:.2f}; authority effect is {belief.controls.get('authority_effect')}.",
    )


def explain_candidate(
    candidate: CandidateCalendarAction | dict[str, Any],
    question: str,
    *,
    evidence_row_ids: list[str],
) -> ExplanationAnswer:
    data = _dict(candidate)
    story = [str(x) for x in data.get("model_story", [])]
    claim = data.get("explanation") or "; ".join(story[:2]) or f"Candidate {data.get('candidate_id', 'unknown')} is proposed for {data.get('intent', 'unknown')}."
    controls = {
        "required_authority_tier": data.get("required_authority_tier"),
        "reversibility": data.get("reversibility"),
        "right_moment_decision": data.get("right_moment_decision"),
        "control_notes": data.get("control_notes", []),
        "counterfactual": data.get("counterfactual", ""),
    }
    return _make_answer(
        object_type="Candidate",
        object_id=str(data.get("candidate_id", "candidate")),
        question=question,
        claim=str(claim),
        evidence_row_ids=evidence_row_ids,
        confidence=float(data.get("predicted_acceptance", 0.0) or 0.0),
        controls=controls,
        answer=f"{claim} Expected reward {float(data.get('expected_reward', 0.0) or 0.0):.2f}; controls require tier {controls['required_authority_tier']}.",
    )


def explain_authority(
    authority_object: AuthorityGrant | CalendarActionReceipt | dict[str, Any],
    question: str,
    *,
    evidence_row_ids: list[str],
) -> ExplanationAnswer:
    data = _dict(authority_object)
    object_id = str(data.get("receipt_id") or data.get("grant_id") or "authority")
    denied_reason = data.get("denied_reason")
    revoked = data.get("status") == "revoked" or bool(data.get("revoked_at"))
    if denied_reason:
        claim = f"Authority denied because {denied_reason}."
        status = "denied"
        confidence = 1.0
    elif revoked:
        claim = f"Authority grant {object_id} is revoked."
        status = "revoked"
        confidence = 1.0
    else:
        claim = f"Authority grant {object_id} allows scopes {', '.join(str(x) for x in data.get('scopes', []))}."
        status = "answered"
        confidence = 0.95
    controls = {
        "max_authority_tier": data.get("max_authority_tier", data.get("authority_tier_used")),
        "scopes": data.get("scopes", []),
        "sync_status": data.get("sync_status"),
        "confirmation_provenance": data.get("confirmation_provenance"),
        "next_action": "request explicit grant" if denied_reason or revoked else "respect grant scope and expiry",
    }
    return _make_answer(
        object_type="Authority",
        object_id=object_id,
        question=question,
        claim=claim,
        evidence_row_ids=evidence_row_ids,
        confidence=confidence,
        controls=controls,
        answer=claim,
        status=status,
    )


def explain_provider(provider_payload: dict[str, Any], question: str, *, evidence_row_ids: list[str]) -> ExplanationAnswer:
    data = dict(provider_payload)
    provider_id = str(data.get("provider_id") or data.get("provider") or "provider")
    operation = str(data.get("operation") or data.get("status") or "provider_state")
    rollback_verified = data.get("rollback_verified")
    claim = f"Provider {provider_id} reported {operation}."
    if rollback_verified is not None:
        claim += f" Rollback verified: {bool(rollback_verified)}."
    controls = {
        "provider_id": provider_id,
        "operation": operation,
        "rollback_handle_id": data.get("rollback_handle_id"),
        "rollback_verified": rollback_verified,
        "sandbox_calendar": data.get("sandbox_calendar") or data.get("calendar_id"),
    }
    return _make_answer(
        object_type="Provider",
        object_id=provider_id,
        question=question,
        claim=claim,
        evidence_row_ids=evidence_row_ids,
        confidence=0.9 if data else 0.5,
        controls=controls,
        answer=claim,
    )


def explain_trajectory(records: list[dict[str, Any]], question: str) -> ExplanationAnswer:
    evidence = [str(row.get("record_id") or row.get("payload", {}).get("record_id") or idx) for idx, row in enumerate(records)]
    types = [str(row.get("record_type") or "unknown") for row in records]
    statuses = [
        str(row.get("payload", {}).get("receipt", {}).get("sync_status"))
        for row in records
        if isinstance(row.get("payload"), dict) and isinstance(row.get("payload", {}).get("receipt"), dict)
    ]
    claim = f"Trajectory contains {len(records)} records: {', '.join(types)}."
    if statuses:
        claim += f" Receipt statuses: {', '.join(statuses)}."
    controls = {
        "record_types": types,
        "terminal_status": statuses[-1] if statuses else None,
        "requires_replay_visibility": True,
    }
    return _make_answer(
        object_type="Trajectory",
        object_id=evidence[-1] if evidence else "trajectory",
        question=question,
        claim=claim,
        evidence_row_ids=evidence,
        confidence=0.85 if records else 0.0,
        controls=controls,
        answer=claim,
    )
