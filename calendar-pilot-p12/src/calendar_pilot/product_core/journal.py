from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class JournalEvent:
    row_id: str
    event_type: str
    occurred_at: str
    payload_json: str
    causal_parent_ids: tuple[str, ...]
    content_sha256: str

    @property
    def payload(self) -> dict[str, Any]:
        value = json.loads(self.payload_json)
        if not isinstance(value, dict):
            raise ValueError("Journal payload must be an object")
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_id": self.row_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "payload": self.payload,
            "causal_parent_ids": list(self.causal_parent_ids),
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "JournalEvent":
        required = {
            "row_id", "event_type", "occurred_at", "payload",
            "causal_parent_ids", "content_sha256",
        }
        if set(value) != required or not isinstance(value.get("payload"), dict):
            raise ValueError("Journal event shape is invalid")
        parents = value.get("causal_parent_ids")
        if not isinstance(parents, list) or not all(isinstance(parent, str) and parent for parent in parents):
            raise ValueError("Journal causal parents are invalid")
        identity = {
            "row_id": str(value["row_id"]),
            "event_type": str(value["event_type"]),
            "occurred_at": str(value["occurred_at"]),
            "payload": value["payload"],
            "causal_parent_ids": parents,
        }
        actual_hash = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
        if actual_hash != value.get("content_sha256"):
            raise ValueError(f"Journal event content hash mismatch: {value.get('row_id')}")
        return cls(
            row_id=identity["row_id"],
            event_type=identity["event_type"],
            occurred_at=identity["occurred_at"],
            payload_json=canonical_json_bytes(identity["payload"]).decode("utf-8"),
            causal_parent_ids=tuple(parents),
            content_sha256=actual_hash,
        )


class EvidenceJournal:
    """Small append-only Journal used by the first ProductCore vertical."""

    def __init__(self) -> None:
        self._events: list[JournalEvent] = []
        self._row_ids: set[str] = set()

    @property
    def events(self) -> tuple[JournalEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        *,
        row_id: str,
        event_type: str,
        occurred_at: str,
        payload: dict[str, Any],
        causal_parent_ids: tuple[str, ...] = (),
    ) -> JournalEvent:
        if not row_id or row_id in self._row_ids:
            raise ValueError(f"duplicate Journal row_id: {row_id}")
        if not event_type or not occurred_at:
            raise ValueError("Journal event_type and occurred_at are required")
        payload_json = canonical_json_bytes(payload).decode("utf-8")
        identity = {
            "row_id": row_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "payload": json.loads(payload_json),
            "causal_parent_ids": list(causal_parent_ids),
        }
        event = JournalEvent(
            row_id=row_id,
            event_type=event_type,
            occurred_at=occurred_at,
            payload_json=payload_json,
            causal_parent_ids=tuple(causal_parent_ids),
            content_sha256=hashlib.sha256(canonical_json_bytes(identity)).hexdigest(),
        )
        self._events.append(event)
        self._row_ids.add(row_id)
        return event
