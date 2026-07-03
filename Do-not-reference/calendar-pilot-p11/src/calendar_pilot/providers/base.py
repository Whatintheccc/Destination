from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from calendar_pilot.types import AtomicCalendarAction, CalendarActionReceipt, CandidateCalendarAction, RawCalendarEvent, RawCalendarObservation


class CalendarProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class CalendarProviderReceipt:
    provider_id: str
    external_id: str | None
    status: str
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ProviderVerificationResult:
    provider_id: str
    status: str
    verified_external_ids: list[str]
    missing_external_ids: list[str]
    rollback_handle_id: str | None = None
    rollback_verified: bool | None = None
    local_time_echo_ok: bool | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class CalendarProviderAdapter(Protocol):
    """Five-method provider transaction boundary.

    Production providers live behind Swift. Python can exercise the same shape in
    fixtures and self-play: read_observation, preview, commit, verify, rollback.
    Legacy create/move/delete primitives may still exist, but they are not the
    canonical acting contract for CalendarPilot.
    """

    provider_id: str

    def read_observation(self, user_scope_id: str, **kwargs: Any) -> RawCalendarObservation:
        ...

    def preview(self, candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        ...

    def commit(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, observation: RawCalendarObservation) -> Any:
        ...

    def verify(self, transaction: Any, *, observation: RawCalendarObservation | None = None) -> ProviderVerificationResult:
        ...

    def rollback(self, rollback_handle_id: str) -> Any:
        ...

    def create_event(self, action: AtomicCalendarAction) -> CalendarProviderReceipt:
        ...

    def move_event(self, action: AtomicCalendarAction) -> CalendarProviderReceipt:
        ...

    def delete_event(self, event: RawCalendarEvent) -> CalendarProviderReceipt:
        ...
