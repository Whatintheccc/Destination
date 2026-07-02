
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from calendar_pilot.types import AtomicCalendarAction, RawCalendarEvent, RawCalendarObservation


class CalendarProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class CalendarProviderReceipt:
    provider_id: str
    external_id: str | None
    status: str
    message: str = ""


class CalendarProviderAdapter(Protocol):
    """Provider boundary owned by Swift in production.

    Python may propose action programs and run self-play. Real OAuth, sync,
    conflict truth, and write execution belong behind Swift/provider adapters.
    """

    provider_id: str

    def read_observation(self, user_scope_id: str) -> RawCalendarObservation:
        ...

    def create_event(self, action: AtomicCalendarAction) -> CalendarProviderReceipt:
        ...

    def move_event(self, action: AtomicCalendarAction) -> CalendarProviderReceipt:
        ...

    def delete_event(self, event: RawCalendarEvent) -> CalendarProviderReceipt:
        ...
