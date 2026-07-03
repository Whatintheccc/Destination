from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from calendar_pilot.providers.base import CalendarProviderError, CalendarProviderReceipt, ProviderVerificationResult
from calendar_pilot.types import AtomicCalendarAction, CalendarActionReceipt, CandidateCalendarAction, RawCalendarEvent, RawCalendarObservation


@dataclass(frozen=True)
class _ProviderStub:
    provider_id: str

    def read_observation(self, user_scope_id: str, **_: Any) -> RawCalendarObservation:
        return RawCalendarObservation(
            observation_id=f"obs_{self.provider_id}_stub",
            user_scope_id=user_scope_id,
            observed_at=datetime.now(timezone.utc),
            time_zone_id="UTC",
            events=[],
        )

    def preview(self, candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        raise CalendarProviderError(f"{self.provider_id} preview/conflict truth not implemented; Swift owns this boundary")

    def commit(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, observation: RawCalendarObservation) -> Any:
        raise CalendarProviderError(f"{self.provider_id} OAuth/write integration not implemented; Swift owns this boundary")

    def verify(self, transaction: Any, *, observation: RawCalendarObservation | None = None) -> ProviderVerificationResult:
        raise CalendarProviderError(f"{self.provider_id} provider verification not implemented; Swift owns this boundary")

    def rollback(self, rollback_handle_id: str) -> Any:
        raise CalendarProviderError(f"{self.provider_id} rollback not implemented; Swift owns this boundary")

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
