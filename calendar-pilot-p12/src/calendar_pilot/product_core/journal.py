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
