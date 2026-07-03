from __future__ import annotations

import json
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Any, Iterator


@dataclass
class TraceEvent:
    seq: int
    event_id: str
    session_id: str
    state_version: int
    trace_id: str
    object: str
    stage: str
    status: str
    ts: str
    causal_parent_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    kind: str = "trace"

    def frame(self) -> bytes:
        return f"id: {self.seq}\ndata: {json.dumps(self.__dict__, sort_keys=True)}\n\n".encode()


class _Subscriber:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.queue: Queue[bytes] = Queue(maxsize=256)

    def frames(self, *, heartbeat_seconds: float = 15.0) -> Iterator[bytes]:
        while True:
            try:
                yield self.queue.get(timeout=heartbeat_seconds)
            except Empty:
                yield b": ping\n\n"


class TraceBus:
    MAX_SUBSCRIBERS = 16
    RING = 512

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._rings: dict[str, deque[TraceEvent]] = {}
        self._subscribers: dict[str, list[_Subscriber]] = {}

    def emit(
        self,
        *,
        session_id: str,
        state_version: int,
        trace_id: str,
        obj: str,
        stage: str,
        status: str = "succeeded",
        payload: dict[str, Any] | None = None,
        causal_parent_id: str | None = None,
        kind: str = "trace",
    ) -> TraceEvent:
        with self._lock:
            self._seq += 1
            event = TraceEvent(
                seq=self._seq,
                event_id=f"evt_{self._seq}",
                session_id=session_id,
                state_version=state_version,
                trace_id=trace_id,
                object=obj,
                stage=stage,
                status=status,
                ts=datetime.now(timezone.utc).isoformat(),
                causal_parent_id=causal_parent_id,
                payload=payload or {},
                kind=kind,
            )
            ring = self._rings.setdefault(session_id, deque(maxlen=self.RING))
            ring.append(event)
            frame = event.frame()
            for sub in list(self._subscribers.get(session_id, [])):
                try:
                    sub.queue.put_nowait(frame)
                except Exception:
                    pass
            return event

    def subscribe(self, session_id: str, *, since: int = 0) -> _Subscriber:
        sub = _Subscriber(session_id)
        with self._lock:
            subs = self._subscribers.setdefault(session_id, [])
            if len(subs) >= self.MAX_SUBSCRIBERS:
                subs.pop(0)
            subs.append(sub)
            for event in self._rings.get(session_id, ()):  # replay missed ring
                if event.seq > since:
                    sub.queue.put_nowait(event.frame())
        return sub

    def unsubscribe(self, sub: _Subscriber) -> None:
        with self._lock:
            subs = self._subscribers.get(sub.session_id, [])
            if sub in subs:
                subs.remove(sub)

    def events(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            return [event.__dict__.copy() for event in self._rings.get(session_id, ())]


TRACE_BUS = TraceBus()