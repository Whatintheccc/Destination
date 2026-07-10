from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Any

from calendar_pilot.types import AtomicActionType, CandidateCalendarAction, RawCalendarObservation, to_jsonable

from .journal import EvidenceJournal, JournalEvent, canonical_json_bytes


REDUCER_VERSION = "product_core.create_prep_block.v1"


@dataclass(frozen=True)
class PrepBlockProjection:
    title: str
    start: str
    end: str
    calendar_id: str
    explanation: str
    evidence_row_ids: tuple[str, ...]
    reducer_version: str = REDUCER_VERSION


@dataclass(frozen=True)
class AdmissionPreview:
    preview_id: str
    candidate_id: str
    action_family: str
    status: str
    denial_reasons: tuple[str, ...]
    projection: PrepBlockProjection | None
    evidence_row_ids: tuple[str, ...]
    reducer_version: str = REDUCER_VERSION
    can_dispatch: bool = False

    def __post_init__(self) -> None:
        if self.status not in {"preview", "denied"}:
            raise ValueError("AdmissionPreview status must be preview or denied")
        if self.can_dispatch:
            raise ValueError("AdmissionPreview can never dispatch")
        if self.status == "preview" and (self.projection is None or self.denial_reasons):
            raise ValueError("successful AdmissionPreview requires a projection and no denial")
        if self.status == "denied" and not self.denial_reasons:
            raise ValueError("denied AdmissionPreview requires a reason")


@dataclass(frozen=True)
class _ReducedPrepBlock:
    candidate_id: str
    action_family: str
    denial_reasons: tuple[str, ...]
    projection: PrepBlockProjection | None
    evidence_row_ids: tuple[str, ...]


@dataclass(frozen=True)
class CreatePrepBlockResult:
    preview: AdmissionPreview
    events: tuple[JournalEvent, ...]
    input_evidence_row_ids: tuple[str, ...]

    def to_observable(self) -> dict[str, Any]:
        projection = self.preview.projection
        return {
            "action_family": self.preview.action_family,
            "candidate_id": self.preview.candidate_id,
            "projection": {
                "title": projection.title if projection else None,
                "start": projection.start if projection else None,
                "end": projection.end if projection else None,
                "calendar_id": projection.calendar_id if projection else None,
                "explanation": projection.explanation if projection else None,
            },
            "admission": {
                "status": self.preview.status,
                "can_dispatch": False,
                "denial_reasons": list(self.preview.denial_reasons),
            },
            "evidence": {"row_ids": list(self.input_evidence_row_ids)},
            "effects": {
                "effect_attempts": 0,
                "claims": 0,
                "dispatches": 0,
                "provider_mutations": 0,
            },
        }


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reduce_create_prep_block(
    events: tuple[JournalEvent, ...],
    *,
    received_at: datetime,
    max_observation_age_seconds: int,
) -> _ReducedPrepBlock:
    observations = [event for event in events if event.event_type == "authenticated_observation"]
    proposals = [event for event in events if event.event_type == "frontier_proposal"]
    reasons: list[str] = []
    if len(observations) != 1:
        reasons.append("observation_cardinality")
    if len(proposals) != 1:
        reasons.append("proposal_cardinality")
    if reasons:
        return _ReducedPrepBlock("unknown", "create_prep_block", tuple(reasons), None, ())

    observation_event, proposal_event = observations[0], proposals[0]
    observation = observation_event.payload
    proposal = proposal_event.payload
    candidate = proposal.get("candidate", {})
    action_family = str(candidate.get("intent", "unknown"))
    candidate_id = str(candidate.get("candidate_id", "unknown"))
    evidence_row_ids = (observation_event.row_id, proposal_event.row_id)

    if observation.get("source_authenticated") is not True:
        reasons.append("observation_source_unauthenticated")
    observed_at = _parse_time(str(observation.get("observed_at", "")))
    age_seconds = (received_at - observed_at).total_seconds()
    if age_seconds < 0:
        reasons.append("observation_from_future")
    elif age_seconds > max_observation_age_seconds:
        reasons.append("observation_stale")
    if proposal_event.causal_parent_ids != (observation_event.row_id,):
        reasons.append("proposal_causality_invalid")
    if action_family != "create_prep_block":
        reasons.append("unsupported_action_family")

    affected_event_ids = [str(value) for value in candidate.get("affected_event_ids", [])]
    observed_event_ids = {str(value) for value in observation.get("event_ids", [])}
    if not affected_event_ids or not set(affected_event_ids).issubset(observed_event_ids):
        reasons.append("missing_parent_event_evidence")
    actions = candidate.get("actions", [])
    if not isinstance(actions, list) or len(actions) != 1:
        reasons.append("prep_block_action_cardinality")
        action: dict[str, Any] = {}
    else:
        action = actions[0] if isinstance(actions[0], dict) else {}
    if action.get("action_type") != AtomicActionType.CREATE_EVENT.value:
        reasons.append("prep_block_action_type")
    if candidate.get("affected_people_ids") or action.get("attendees"):
        reasons.append("prep_block_must_be_private")
    required = [action.get("title"), action.get("start"), action.get("end"), action.get("calendar_id"), candidate.get("explanation")]
    if not all(required):
        reasons.append("required_projection_field_missing")

    projection = None if reasons else PrepBlockProjection(
        title=str(action["title"]),
        start=str(action["start"]),
        end=str(action["end"]),
        calendar_id=str(action["calendar_id"]),
        explanation=str(candidate["explanation"]),
        evidence_row_ids=evidence_row_ids,
    )
    return _ReducedPrepBlock(candidate_id, action_family, tuple(reasons), projection, evidence_row_ids)


def run_create_prep_block_vertical(
    observation: RawCalendarObservation,
    candidate: CandidateCalendarAction,
    *,
    source_authenticated: bool,
    received_at: datetime,
    max_observation_age_seconds: int = 300,
) -> CreatePrepBlockResult:
    if max_observation_age_seconds < 0:
        raise ValueError("max_observation_age_seconds must be nonnegative")
    journal = EvidenceJournal()
    observation_row_id = f"observation:{observation.observation_id}"
    proposal_row_id = f"proposal:{candidate.candidate_id}"
    journal.append(
        row_id=observation_row_id,
        event_type="authenticated_observation",
        occurred_at=observation.observed_at.isoformat(),
        payload={
            "observation_id": observation.observation_id,
            "user_scope_id": observation.user_scope_id,
            "observed_at": observation.observed_at.isoformat(),
            "source_authenticated": bool(source_authenticated),
            "event_ids": sorted(event.event_id for event in observation.events),
        },
    )
    journal.append(
        row_id=proposal_row_id,
        event_type="frontier_proposal",
        occurred_at=received_at.isoformat(),
        payload={"candidate": to_jsonable(candidate)},
        causal_parent_ids=(observation_row_id,),
    )
    reduced = _reduce_create_prep_block(
        journal.events,
        received_at=received_at,
        max_observation_age_seconds=max_observation_age_seconds,
    )
    preview_seed = {
        "candidate_id": reduced.candidate_id,
        "action_family": reduced.action_family,
        "denial_reasons": list(reduced.denial_reasons),
        "evidence_row_ids": list(reduced.evidence_row_ids),
        "event_hashes": [event.content_sha256 for event in journal.events],
        "reducer_version": REDUCER_VERSION,
    }
    preview = AdmissionPreview(
        preview_id="preview:" + hashlib.sha256(canonical_json_bytes(preview_seed)).hexdigest()[:24],
        candidate_id=reduced.candidate_id,
        action_family=reduced.action_family,
        status="denied" if reduced.denial_reasons else "preview",
        denial_reasons=reduced.denial_reasons,
        projection=reduced.projection,
        evidence_row_ids=reduced.evidence_row_ids,
    )
    journal.append(
        row_id=f"admission:{preview.preview_id}",
        event_type="admission_preview",
        occurred_at=received_at.isoformat(),
        payload={
            "preview_id": preview.preview_id,
            "candidate_id": preview.candidate_id,
            "status": preview.status,
            "denial_reasons": list(preview.denial_reasons),
            "evidence_row_ids": list(preview.evidence_row_ids),
            "reducer_version": preview.reducer_version,
            "can_dispatch": False,
        },
        causal_parent_ids=preview.evidence_row_ids,
    )
    return CreatePrepBlockResult(
        preview=preview,
        events=journal.events,
        input_evidence_row_ids=reduced.evidence_row_ids,
    )
