from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import select
import subprocess
import tempfile
import uuid
from typing import Any, TextIO

from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.types import AuthorityGrant, CalendarActionReceipt, CandidateCalendarAction, RawCalendarObservation, to_jsonable


class SwiftKernelIPCError(RuntimeError):
    pass


class SwiftKernelIPCClient:
    """Persistent JSONL bridge to the Swift CalendarPilotKernelServer.

    This keeps authority grants in the Swift process. Python sends grant IDs and
    action packets; Swift resolves grants, validates, materializes, and returns
    receipts. The client is optional because unit tests still use SwiftKernelStub,
    but the boundary is concrete and can be selected by app integrations.
    """

    def __init__(
        self,
        *,
        package_path: str | Path = "packages/CalendarPilotKernel",
        executable: str = "CalendarPilotKernelServer",
        rpc_timeout_seconds: float = 20.0,
    ) -> None:
        self.package_path = str(package_path)
        self.executable = executable
        self.rpc_timeout_seconds = rpc_timeout_seconds
        self._proc: subprocess.Popen[str] | None = None
        self._stderr: TextIO | None = None
        self._grants: dict[str, AuthorityGrant] = {}

    def __enter__(self) -> "SwiftKernelIPCClient":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def start(self) -> None:
        if self._proc is not None:
            return
        self._stderr = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
        self._proc = subprocess.Popen(
            ["swift", "run", "--package-path", self.package_path, self.executable],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr,
            text=True,
            bufsize=1,
        )

    def close(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None
        if self._stderr is not None:
            self._stderr.close()
            self._stderr = None

    def issue_authority_grant(
        self,
        *,
        user_scope_id: str,
        max_authority_tier: int,
        scopes: list[str] | None = None,
        confirmation_provenance: str = "ipc_user_confirmed_scope",
        ttl_seconds: int = 1800,
        confirmed_by_user: bool = True,
        issued_at: datetime | None = None,
    ) -> AuthorityGrant:
        issued_at = issued_at or datetime.now().astimezone()
        payload = {
            "user_scope_id": user_scope_id,
            "max_authority_tier": max_authority_tier,
            "scopes": scopes or ["recommend", "stage", "commit_private", "undo"],
            "confirmation_provenance": confirmation_provenance,
            "ttl_seconds": ttl_seconds,
            "confirmed_by_user": confirmed_by_user,
            "issued_at": issued_at.isoformat(),
        }
        out = self._rpc("issue_authority_grant", payload)
        grant = AuthorityGrant.from_dict(out["authority_grant"])
        self._grants[grant.grant_id] = grant
        return grant

    def resolve_authority_grant(self, grant: AuthorityGrant | str | None) -> AuthorityGrant | None:
        # Display/cache only. Swift still resolves the grant id in its own
        # registry on preview/stage/commit/undo.
        if isinstance(grant, AuthorityGrant):
            return self._grants.get(grant.grant_id)
        if isinstance(grant, str):
            return self._grants.get(grant)
        return None

    def preview_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        authority_grant_id: str | None = None,
    ) -> CalendarActionReceipt:
        grant_ref = authority_grant if authority_grant is not None else authority_grant_id
        return self._act("preview", candidate, observation, self._grant_id(grant_ref), requested_authority_tier or candidate.required_authority_tier)

    def stage_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        authority_grant_id: str | None = None,
    ) -> CalendarActionReceipt:
        grant_ref = authority_grant if authority_grant is not None else authority_grant_id
        return self._act("stage", candidate, observation, self._grant_id(grant_ref), requested_authority_tier or candidate.required_authority_tier)

    def authorize_and_materialize(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        granted_authority_tier: int | None = None,
        authority_grant_id: str | None = None,
    ) -> CalendarActionReceipt:
        desired = requested_authority_tier if requested_authority_tier is not None else (granted_authority_tier or candidate.required_authority_tier)
        grant_ref = authority_grant if authority_grant is not None else authority_grant_id
        return self._act("commit", candidate, observation, self._grant_id(grant_ref), desired)

    def request_undo(
        self,
        rollback_handle_id: str,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        authority_grant_id: str | None = None,
    ) -> CalendarActionReceipt:
        grant_ref = authority_grant if authority_grant is not None else authority_grant_id
        out = self._rpc("undo", {
            "rollback_handle_id": rollback_handle_id,
            "authority_grant_id": self._grant_id(grant_ref),
            "requested_authority_tier": requested_authority_tier,
            "observed_at": observation.observed_at.isoformat(),
        })
        return _receipt_from_dict(out["receipt"])

    @staticmethod
    def is_people_affecting_mutation(candidate: CandidateCalendarAction) -> bool:
        return SwiftKernelStub.is_people_affecting_mutation(candidate)

    def _act(self, op: str, candidate: CandidateCalendarAction, observation: RawCalendarObservation, authority_grant_id: str | None, requested_authority_tier: int) -> CalendarActionReceipt:
        out = self._rpc(op, {
            "candidate": candidate.to_dict(),
            "observation": to_jsonable(observation),
            "authority_grant_id": authority_grant_id,
            "requested_authority_tier": requested_authority_tier,
        })
        return _receipt_from_dict(out["receipt"])

    @staticmethod
    def _grant_id(grant: AuthorityGrant | str | None) -> str | None:
        if isinstance(grant, AuthorityGrant):
            return grant.grant_id
        if isinstance(grant, str):
            return grant
        return None

    def _rpc(self, op: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.start()
        assert self._proc is not None and self._proc.stdin is not None and self._proc.stdout is not None
        request_id = "rpc_" + uuid.uuid4().hex[:12]
        self._proc.stdin.write(json.dumps({"id": request_id, "op": op, "payload": to_jsonable(payload)}, sort_keys=True) + "\n")
        self._proc.stdin.flush()
        ready, _, _ = select.select([self._proc.stdout], [], [], self.rpc_timeout_seconds)
        if not ready:
            raise SwiftKernelIPCError(f"Swift kernel RPC timed out during {op}: {self._stderr_tail()}")
        line = self._proc.stdout.readline()
        if not line:
            raise SwiftKernelIPCError(f"Swift kernel server closed: {self._stderr_tail()}")
        response = json.loads(line)
        if not response.get("ok"):
            raise SwiftKernelIPCError(response.get("error") or "Swift kernel RPC failed")
        return dict(response.get("payload", {}))

    def _stderr_tail(self) -> str:
        if self._stderr is None:
            return ""
        self._stderr.flush()
        self._stderr.seek(0)
        data = self._stderr.read()
        self._stderr.seek(0, 2)
        return data[-2000:]


def _receipt_from_dict(data: dict[str, Any]) -> CalendarActionReceipt:
    from calendar_pilot.types import ActuationMode, StageState
    return CalendarActionReceipt(
        receipt_id=data["receipt_id"],
        candidate_id=data.get("candidate_id", "unknown"),
        executed_at=datetime.fromisoformat(data["executed_at"].replace("Z", "+00:00")),
        executed_by=data.get("executed_by", "CalendarPilotKernelServer"),
        authority_tier_used=int(data.get("authority_tier_used", 0)),
        sync_status=data.get("sync_status", "denied"),
        rollback_handle_id=data.get("rollback_handle_id"),
        conflict_check_passed=bool(data.get("conflict_check_passed", False)),
        generated_event_ids=list(data.get("generated_event_ids", [])),
        staged_action_ids=list(data.get("staged_action_ids", [])),
        rejected_action_types=list(data.get("rejected_action_types", [])),
        provider_id=data.get("provider_id", "swift_ipc"),
        actuation_mode=ActuationMode(data.get("actuation_mode", "no_op")),
        denied_reason=data.get("denied_reason"),
        authority_grant_id=data.get("authority_grant_id"),
        confirmation_provenance=data.get("confirmation_provenance"),
        stage_state=StageState(data.get("stage_state", "no_op")),
        correlation_id=data.get("correlation_id"),
    )
