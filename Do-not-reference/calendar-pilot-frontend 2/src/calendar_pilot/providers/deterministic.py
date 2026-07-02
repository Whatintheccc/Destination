from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from calendar_pilot.providers.base import CalendarProviderError
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarEvent,
    RawCalendarObservation,
    to_jsonable,
)


PROVIDER_ID = "deterministic_fixture_provider"
WRITE_ACTIONS = {
    AtomicActionType.CREATE_EVENT,
    AtomicActionType.CREATE_FOCUS_BLOCK,
    AtomicActionType.ADD_BUFFER,
    AtomicActionType.BATCH_TASKS,
    AtomicActionType.MOVE_EVENT,
    AtomicActionType.RESIZE_EVENT,
    AtomicActionType.DELETE_OWN_EVENT,
}


@dataclass(frozen=True)
class ProviderMutationResult:
    provider_id: str
    status: str
    idempotency_key: str
    external_ids: list[str] = field(default_factory=list)
    created_external_ids: list[str] = field(default_factory=list)
    moved_external_ids: list[str] = field(default_factory=list)
    deleted_external_ids: list[str] = field(default_factory=list)
    rollback_handle_id: str | None = None
    rollback_verified: bool = False
    conflict_truth: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


class DeterministicCalendarProvider:
    """Persisted fixture provider with external IDs, idempotency, and rollback truth."""

    provider_id = PROVIDER_ID
    real_oauth = False

    def __init__(self, *, state_path: str | Path | None = None, seed_observation: RawCalendarObservation | None = None) -> None:
        self.state_path = Path(state_path) if state_path is not None else None
        self.state: dict[str, Any] = {}
        if self.state_path is not None and self.state_path.exists():
            self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
        else:
            self.reset(seed_observation)

    def reset(self, seed_observation: RawCalendarObservation | None = None) -> None:
        events = {}
        if seed_observation is not None:
            events = {
                event.event_id: {
                    "external_id": event.event_id,
                    "event": to_jsonable(event),
                    "source": "seed_observation",
                }
                for event in seed_observation.events
            }
        self.state = {
            "version": 1,
            "provider_id": self.provider_id,
            "real_oauth": False,
            "events": events,
            "idempotency": {},
            "rollback_records": {},
            "mutations": [],
        }
        self._persist()

    def read_observation(self, user_scope_id: str, *, observed_at: datetime | None = None, time_zone_id: str = "UTC") -> RawCalendarObservation:
        return RawCalendarObservation(
            observation_id=f"obs_{self.provider_id}",
            user_scope_id=user_scope_id,
            observed_at=observed_at or datetime.now().astimezone(),
            time_zone_id=time_zone_id,
            events=[RawCalendarEvent.from_dict(row["event"]) for row in self.state.get("events", {}).values()],
        )

    def conflict_truth(self, candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        if self.idempotency_key(candidate) in self.state.get("idempotency", {}):
            return []
        conflicts: list[dict[str, Any]] = []
        events = [RawCalendarEvent.from_dict(row["event"]) for row in self.state.get("events", {}).values()]
        for action in candidate.actions:
            if action.action_type not in WRITE_ACTIONS or action.start is None or action.end is None:
                continue
            if action.action_type in {AtomicActionType.MOVE_EVENT, AtomicActionType.RESIZE_EVENT}:
                ignored_event_id = action.event_id
            else:
                ignored_event_id = None
            for event in events:
                if ignored_event_id and event.event_id == ignored_event_id:
                    continue
                if action.start < event.end and action.end > event.start:
                    conflicts.append({
                        "action_type": action.action_type.value,
                        "event_id": event.event_id,
                        "external_id": self._external_id_for_event(event.event_id),
                        "start": event.start.isoformat(),
                        "end": event.end.isoformat(),
                    })
        return conflicts

    def commit_candidate(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, observation: RawCalendarObservation) -> ProviderMutationResult:
        idempotency_key = self.idempotency_key(candidate)
        existing = self.state["idempotency"].get(idempotency_key)
        if existing:
            return ProviderMutationResult(
                provider_id=self.provider_id,
                status="idempotent_replay",
                idempotency_key=idempotency_key,
                external_ids=list(existing.get("external_ids", [])),
                created_external_ids=list(existing.get("created_external_ids", [])),
                moved_external_ids=list(existing.get("moved_external_ids", [])),
                deleted_external_ids=list(existing.get("deleted_external_ids", [])),
                rollback_handle_id=existing.get("rollback_handle_id"),
                message="idempotency key already materialized; no duplicate provider write",
            )
        conflicts = self.conflict_truth(candidate)
        if conflicts:
            return ProviderMutationResult(
                provider_id=self.provider_id,
                status="conflict_denied",
                idempotency_key=idempotency_key,
                conflict_truth=conflicts,
                message="provider conflict truth denied commit before external write",
            )

        before_events = dict(self.state["events"])
        created: list[str] = []
        moved: list[str] = []
        deleted: list[str] = []
        for idx, action in enumerate(candidate.actions):
            if action.action_type in {AtomicActionType.CREATE_EVENT, AtomicActionType.CREATE_FOCUS_BLOCK, AtomicActionType.ADD_BUFFER, AtomicActionType.BATCH_TASKS}:
                external_id = self._external_id(idempotency_key, idx)
                created.append(external_id)
                event = self._event_from_action(external_id, action)
                self.state["events"][external_id] = {
                    "external_id": external_id,
                    "event": to_jsonable(event),
                    "source": "provider_commit",
                    "candidate_id": candidate.candidate_id,
                    "idempotency_key": idempotency_key,
                }
            elif action.action_type in {AtomicActionType.MOVE_EVENT, AtomicActionType.RESIZE_EVENT} and action.event_id:
                external_id = self._external_id_for_event(action.event_id)
                row = self.state["events"].get(external_id)
                if row and action.start and action.end:
                    event = RawCalendarEvent.from_dict(row["event"])
                    moved_event = RawCalendarEvent(
                        event_id=event.event_id,
                        title=event.title,
                        start=action.start,
                        end=action.end,
                        calendar_id=event.calendar_id,
                        attendees=event.attendees,
                        location=event.location,
                        notes=event.notes,
                        is_user_owned=event.is_user_owned,
                        is_flexible=event.is_flexible,
                        category=event.category,
                    )
                    row["event"] = to_jsonable(moved_event)
                    moved.append(external_id)
            elif action.action_type == AtomicActionType.DELETE_OWN_EVENT and action.event_id:
                external_id = self._external_id_for_event(action.event_id)
                row = self.state["events"].get(external_id)
                if row and bool(row.get("event", {}).get("is_user_owned")):
                    self.state["events"].pop(external_id, None)
                    deleted.append(external_id)

        external_ids = created + moved + deleted
        rollback_handle_id = receipt.rollback_handle_id
        if rollback_handle_id:
            self.state["rollback_records"][rollback_handle_id] = {
                "candidate_id": candidate.candidate_id,
                "idempotency_key": idempotency_key,
                "before_events": before_events,
                "created_external_ids": created,
                "moved_external_ids": moved,
                "deleted_external_ids": deleted,
                "rollback_verified": False,
            }
        record = {
            "idempotency_key": idempotency_key,
            "candidate_id": candidate.candidate_id,
            "external_ids": external_ids,
            "created_external_ids": created,
            "moved_external_ids": moved,
            "deleted_external_ids": deleted,
            "rollback_handle_id": rollback_handle_id,
            "status": "materialized",
        }
        self.state["idempotency"][idempotency_key] = record
        self.state["mutations"].append(record)
        self._persist()
        return ProviderMutationResult(
            provider_id=self.provider_id,
            status="materialized",
            idempotency_key=idempotency_key,
            external_ids=external_ids,
            created_external_ids=created,
            moved_external_ids=moved,
            deleted_external_ids=deleted,
            rollback_handle_id=rollback_handle_id,
        )

    def rollback(self, rollback_handle_id: str) -> ProviderMutationResult:
        record = self.state.get("rollback_records", {}).get(rollback_handle_id)
        if not record:
            return ProviderMutationResult(
                provider_id=self.provider_id,
                status="rollback_missing",
                idempotency_key="",
                rollback_handle_id=rollback_handle_id,
                rollback_verified=False,
                message="provider rollback handle not found",
            )
        self.state["events"] = dict(record.get("before_events", {}))
        record["rollback_verified"] = True
        self.state["mutations"].append({
            "status": "rollback_verified",
            "rollback_handle_id": rollback_handle_id,
            "idempotency_key": record.get("idempotency_key", ""),
        })
        self._persist()
        return ProviderMutationResult(
            provider_id=self.provider_id,
            status="rollback_verified",
            idempotency_key=str(record.get("idempotency_key", "")),
            rollback_handle_id=rollback_handle_id,
            rollback_verified=True,
            created_external_ids=list(record.get("created_external_ids", [])),
            moved_external_ids=list(record.get("moved_external_ids", [])),
            deleted_external_ids=list(record.get("deleted_external_ids", [])),
        )

    def snapshot(self) -> dict[str, Any]:
        rollback_records = self.state.get("rollback_records", {})
        return {
            "provider": self.provider_id,
            "real_oauth": False,
            "event_count": len(self.state.get("events", {})),
            "idempotency_keys": len(self.state.get("idempotency", {})),
            "rollback_records": len(rollback_records),
            "rollback_verified": sum(1 for row in rollback_records.values() if row.get("rollback_verified")),
            "recent_mutations": self.state.get("mutations", [])[-8:],
        }

    @staticmethod
    def idempotency_key(candidate: CandidateCalendarAction) -> str:
        payload = json.dumps(candidate.to_dict(), sort_keys=True)
        return "idem_" + hashlib.sha1(payload.encode()).hexdigest()[:16]

    def _external_id_for_event(self, event_id: str) -> str:
        if event_id in self.state.get("events", {}):
            return event_id
        for external_id, row in self.state.get("events", {}).items():
            if row.get("event", {}).get("event_id") == event_id:
                return external_id
        return event_id

    @staticmethod
    def _external_id(idempotency_key: str, idx: int) -> str:
        return "det_evt_" + hashlib.sha1(f"{idempotency_key}|{idx}".encode()).hexdigest()[:14]

    @staticmethod
    def _event_from_action(external_id: str, action: AtomicCalendarAction) -> RawCalendarEvent:
        if action.start is None or action.end is None:
            raise CalendarProviderError("provider create requires start and end")
        category = {
            AtomicActionType.CREATE_FOCUS_BLOCK: "focus",
            AtomicActionType.ADD_BUFFER: "buffer",
            AtomicActionType.BATCH_TASKS: "task_batch",
        }.get(action.action_type, action.metadata.get("category", "generated"))
        return RawCalendarEvent(
            event_id=external_id,
            title=action.title,
            start=action.start,
            end=action.end,
            calendar_id=action.calendar_id,
            attendees=action.attendees,
            location=action.metadata.get("location", ""),
            notes=action.metadata.get("notes", ""),
            is_user_owned=True,
            is_flexible=True,
            category=category,
        )

    def _persist(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8")
