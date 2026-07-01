from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
import hashlib
import json

from calendar_pilot.providers.base import CalendarProviderError, CalendarProviderReceipt
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CandidateCalendarAction,
    RawCalendarEvent,
    RawCalendarObservation,
    Reversibility,
    to_jsonable,
)


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
class FixtureProviderApplyResult:
    receipt: CalendarProviderReceipt
    external_ids: list[str]
    rollback_handle_id: str | None
    checksum_before: str
    checksum_after: str
    idempotent_replay: bool = False

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


class FixtureCalendarProvider:
    """Deterministic provider state for dogfood before real OAuth.

    This provider intentionally sits behind the same conceptual boundary as
    Google/Apple/Microsoft adapters, but it is local, persisted, resettable, and
    idempotent. Dogfood should prove provider truth and rollback here before
    adding external credentials.
    """

    provider_id = "fixture"

    def __init__(
        self,
        state_path: str | Path = "runs/fixture_provider/state.json",
        seed_observation: RawCalendarObservation | None = None,
    ) -> None:
        self.state_path = Path(state_path)
        if seed_observation is not None and not self.state_path.exists():
            self.reset(seed_observation)
        elif not self.state_path.exists():
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self._write(self._empty_state())

    def reset(self, observation: RawCalendarObservation) -> None:
        state = self._empty_state()
        state["user_scope_id"] = observation.user_scope_id
        state["observed_at"] = observation.observed_at.isoformat()
        state["time_zone_id"] = observation.time_zone_id
        state["tasks"] = to_jsonable(observation.tasks)
        state["device_context"] = to_jsonable(observation.device_context)
        state["notification_history"] = to_jsonable(observation.notification_history)
        state["prior_actions"] = to_jsonable(observation.prior_actions)
        state["events"] = {event.event_id: event.to_dict() if hasattr(event, "to_dict") else to_jsonable(event) for event in observation.events}
        self._write(state)

    def read_observation(self, user_scope_id: str) -> RawCalendarObservation:
        state = self._read()
        if state["user_scope_id"] != user_scope_id:
            raise CalendarProviderError("fixture provider user scope mismatch")
        events = [
            RawCalendarEvent.from_dict(item)
            for item in sorted(state["events"].values(), key=lambda e: (e.get("start", ""), e.get("event_id", "")))
        ]
        return RawCalendarObservation.from_dict({
            "observation_id": f"obs_fixture_{state['version']}",
            "user_scope_id": state["user_scope_id"],
            "observed_at": state["observed_at"],
            "time_zone_id": state["time_zone_id"],
            "events": [to_jsonable(event) for event in events],
            "tasks": state.get("tasks", []),
            "device_context": state.get("device_context", {}),
            "notification_history": state.get("notification_history", []),
            "prior_actions": state.get("prior_actions", []),
        })

    def create_event(self, action: AtomicCalendarAction) -> CalendarProviderReceipt:
        result = self.apply_action(action, idempotency_key=self._action_key("create", action))
        return result.receipt

    def move_event(self, action: AtomicCalendarAction) -> CalendarProviderReceipt:
        result = self.apply_action(action, idempotency_key=self._action_key("move", action))
        return result.receipt

    def delete_event(self, event: RawCalendarEvent) -> CalendarProviderReceipt:
        action = AtomicCalendarAction(action_type=AtomicActionType.DELETE_OWN_EVENT, event_id=event.event_id)
        result = self.apply_action(action, idempotency_key=self._action_key("delete", action))
        return result.receipt

    def apply_candidate(
        self,
        candidate: CandidateCalendarAction,
        *,
        idempotency_key: str,
        rollback_handle_id: str | None,
    ) -> FixtureProviderApplyResult:
        state = self._read()
        if idempotency_key in state["idempotency"]:
            return self._result_from_dict(state["idempotency"][idempotency_key], idempotent_replay=True)

        checksum_before = self._checksum(state["events"])
        before_events = dict(state["events"])
        external_ids: list[str] = []
        changed = False
        for idx, action in enumerate(candidate.actions):
            if action.action_type not in WRITE_ACTIONS:
                continue
            action_external_ids, action_changed = self._apply_action_to_state(
                state,
                action,
                candidate_id=candidate.candidate_id,
                action_index=idx,
            )
            external_ids.extend(action_external_ids)
            changed = changed or action_changed

        if rollback_handle_id and changed:
            state["rollback"][rollback_handle_id] = {
                "events": before_events,
                "candidate_id": candidate.candidate_id,
                "checksum_before": checksum_before,
            }
        if changed:
            state["version"] = int(state["version"]) + 1
        checksum_after = self._checksum(state["events"])
        result = FixtureProviderApplyResult(
            receipt=CalendarProviderReceipt(
                provider_id=self.provider_id,
                external_id=external_ids[0] if external_ids else None,
                status="materialized" if changed else "no_op",
                message=f"fixture applied {len(external_ids)} provider writes",
            ),
            external_ids=external_ids,
            rollback_handle_id=rollback_handle_id if changed else None,
            checksum_before=checksum_before,
            checksum_after=checksum_after,
        )
        state["idempotency"][idempotency_key] = result.to_dict()
        self._write(state)
        return result

    def apply_action(self, action: AtomicCalendarAction, *, idempotency_key: str) -> FixtureProviderApplyResult:
        candidate = CandidateCalendarAction(
            candidate_id="fixture_action_" + hashlib.sha1(idempotency_key.encode()).hexdigest()[:10],
            intent=action.action_type.value,
            actions=[action],
            target_calendars=[action.calendar_id],
            affected_event_ids=[action.event_id] if action.event_id else [],
            affected_people_ids=action.attendees,
            reversibility=Reversibility.HIGH,
            required_authority_tier=3,
        )
        return self.apply_candidate(candidate, idempotency_key=idempotency_key, rollback_handle_id=None)

    def rollback(self, rollback_handle_id: str, *, idempotency_key: str | None = None) -> FixtureProviderApplyResult:
        state = self._read()
        key = idempotency_key
        if key and key in state["idempotency"]:
            return self._result_from_dict(state["idempotency"][key], idempotent_replay=True)
        current_checksum = self._checksum(state["events"])
        record = state["rollback"].pop(rollback_handle_id, None)
        if record is None:
            result = FixtureProviderApplyResult(
                receipt=CalendarProviderReceipt(self.provider_id, None, "denied", "rollback handle not found"),
                external_ids=[],
                rollback_handle_id=rollback_handle_id,
                checksum_before=current_checksum,
                checksum_after=current_checksum,
            )
            if key:
                state["idempotency"][key] = result.to_dict()
            self._write(state)
            return result
        state["events"] = record["events"]
        state["version"] = int(state["version"]) + 1
        checksum_after = self._checksum(state["events"])
        verified = checksum_after == record["checksum_before"]
        result = FixtureProviderApplyResult(
            receipt=CalendarProviderReceipt(
                self.provider_id,
                rollback_handle_id,
                "reverted" if verified else "failed",
                "rollback verified" if verified else "rollback checksum mismatch",
            ),
            external_ids=[],
            rollback_handle_id=rollback_handle_id,
            checksum_before=current_checksum,
            checksum_after=checksum_after,
        )
        if key:
            state["idempotency"][key] = result.to_dict()
        self._write(state)
        return result

    def checksum(self) -> str:
        return self._checksum(self._read()["events"])

    def _apply_action_to_state(
        self,
        state: dict[str, Any],
        action: AtomicCalendarAction,
        *,
        candidate_id: str,
        action_index: int,
    ) -> tuple[list[str], bool]:
        if action.action_type in {
            AtomicActionType.CREATE_EVENT,
            AtomicActionType.CREATE_FOCUS_BLOCK,
            AtomicActionType.ADD_BUFFER,
            AtomicActionType.BATCH_TASKS,
        }:
            if action.start is None or action.end is None:
                return [], False
            if self._has_conflict(state, action):
                raise CalendarProviderError("fixture conflict truth rejected provider write")
            external_id = self._external_id(candidate_id, action_index, action.action_type.value)
            category = {
                AtomicActionType.CREATE_FOCUS_BLOCK: "focus",
                AtomicActionType.ADD_BUFFER: "buffer",
                AtomicActionType.BATCH_TASKS: "task_batch",
            }.get(action.action_type, action.metadata.get("category", "generated"))
            state["events"][external_id] = to_jsonable(RawCalendarEvent(
                event_id=external_id,
                title=action.title or action.action_type.value.replace("_", " "),
                start=action.start,
                end=action.end,
                calendar_id=action.calendar_id,
                attendees=action.attendees,
                notes=action.metadata.get("notes", ""),
                is_user_owned=True,
                is_flexible=True,
                category=category,
            ))
            return [external_id], True
        if action.action_type in {AtomicActionType.MOVE_EVENT, AtomicActionType.RESIZE_EVENT}:
            if not action.event_id or action.event_id not in state["events"] or action.start is None or action.end is None:
                return [], False
            if self._has_conflict(state, action):
                raise CalendarProviderError("fixture conflict truth rejected provider write")
            event = RawCalendarEvent.from_dict(state["events"][action.event_id])
            moved = replace(event, start=action.start, end=action.end)
            state["events"][action.event_id] = to_jsonable(moved)
            return [action.event_id], True
        if action.action_type == AtomicActionType.DELETE_OWN_EVENT:
            if not action.event_id:
                return [], False
            event_data = state["events"].get(action.event_id)
            if not event_data or not bool(event_data.get("is_user_owned", False)):
                return [], False
            state["events"].pop(action.event_id, None)
            return [action.event_id], True
        return [], False

    @staticmethod
    def _has_conflict(state: dict[str, Any], action: AtomicCalendarAction) -> bool:
        if action.start is None or action.end is None:
            return False
        for raw in state["events"].values():
            event = RawCalendarEvent.from_dict(raw)
            if event.event_id == action.event_id:
                continue
            if action.start < event.end and action.end > event.start:
                return True
        return False

    def _read(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "provider_id": "fixture",
            "version": 0,
            "user_scope_id": "default_user",
            "observed_at": "2026-07-01T09:00:00+00:00",
            "time_zone_id": "UTC",
            "events": {},
            "tasks": [],
            "device_context": {},
            "notification_history": [],
            "prior_actions": [],
            "idempotency": {},
            "rollback": {},
        }

    @staticmethod
    def _checksum(events: dict[str, Any]) -> str:
        raw = json.dumps(events, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _external_id(candidate_id: str, action_index: int, action_type: str) -> str:
        digest = hashlib.sha1(f"{candidate_id}|{action_index}|{action_type}".encode()).hexdigest()[:12]
        return f"fixture_evt_{digest}"

    @staticmethod
    def _action_key(prefix: str, action: AtomicCalendarAction) -> str:
        return prefix + ":" + hashlib.sha1(json.dumps(to_jsonable(action), sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _result_from_dict(data: dict[str, Any], *, idempotent_replay: bool) -> FixtureProviderApplyResult:
        receipt_data = data.get("receipt", {})
        return FixtureProviderApplyResult(
            receipt=CalendarProviderReceipt(
                provider_id=str(receipt_data.get("provider_id", "fixture")),
                external_id=receipt_data.get("external_id"),
                status=str(receipt_data.get("status", "")),
                message=str(receipt_data.get("message", "")),
            ),
            external_ids=[str(x) for x in data.get("external_ids", [])],
            rollback_handle_id=data.get("rollback_handle_id"),
            checksum_before=str(data.get("checksum_before", "")),
            checksum_after=str(data.get("checksum_after", "")),
            idempotent_replay=idempotent_replay,
        )
