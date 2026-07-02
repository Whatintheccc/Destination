from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from calendar_pilot.providers.base import CalendarProviderError, CalendarProviderReceipt
from calendar_pilot.types import AtomicCalendarAction, RawCalendarEvent, RawCalendarObservation


@dataclass(frozen=True)
class _ProviderStub:
    provider_id: str

    def read_observation(self, user_scope_id: str) -> RawCalendarObservation:
        return RawCalendarObservation(
            observation_id=f"obs_{self.provider_id}_stub",
            user_scope_id=user_scope_id,
            observed_at=datetime.now(timezone.utc),
            time_zone_id="UTC",
            events=[],
        )

    def create_event(self, action: AtomicCalendarAction) -> CalendarProviderReceipt:
        raise CalendarProviderError(f"{self.provider_id} OAuth/write integration not implemented; Swift owns this boundary")

    def move_event(self, action: AtomicCalendarAction) -> CalendarProviderReceipt:
        raise CalendarProviderError(f"{self.provider_id} OAuth/write integration not implemented; Swift owns this boundary")

    def delete_event(self, event: RawCalendarEvent) -> CalendarProviderReceipt:
        raise CalendarProviderError(f"{self.provider_id} OAuth/write integration not implemented; Swift owns this boundary")


class GoogleCalendarAdapter(_ProviderStub):
    def __init__(self) -> None:
        super().__init__("google")


class AppleCalendarAdapter(_ProviderStub):
    def __init__(self) -> None:
        super().__init__("apple")


class MicrosoftCalendarAdapter(_ProviderStub):
    def __init__(self) -> None:
        super().__init__("microsoft")
