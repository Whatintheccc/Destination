

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol

from calendar_pilot.types import AuthorityGrant, CalendarActionReceipt, CandidateCalendarAction, RawCalendarObservation


class CalendarKernelProtocol(Protocol):
    """Shared Python surface for the local stub and Swift IPC kernel."""

    authority_grants: dict[str, AuthorityGrant]
    undo_ledger: dict[str, str]

    def issue_authority_grant(
        self,
        *,
        user_scope_id: str,
        max_authority_tier: int,
        scopes: Iterable[str] | None = None,
        confirmation_provenance: str = "user_confirmed_demo_scope",
        ttl_minutes: int = 30,
        confirmed_by_user: bool = True,
        issued_at: datetime | None = None,
    ) -> AuthorityGrant: ...

    def resolve_authority_grant(self, grant: AuthorityGrant | str | None) -> AuthorityGrant | None: ...

    def preview_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt: ...

    def stage_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt: ...

    def authorize_and_materialize(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        granted_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt: ...

    def request_undo(
        self,
        rollback_handle_id: str,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt: ...

    def is_people_affecting_mutation(self, candidate: CandidateCalendarAction) -> bool: ...

    def has_write_action(self, candidate: CandidateCalendarAction) -> bool: ...
