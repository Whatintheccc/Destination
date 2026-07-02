

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import threading
import uuid
from typing import Any, Iterable

from calendar_pilot.types import AuthorityGrant, CalendarActionReceipt, CandidateCalendarAction, RawCalendarObservation, to_jsonable
from calendar_pilot.swift_bridge.client import SwiftKernelStub


class SwiftKernelIPCError(RuntimeError):
    pass


ROOT = Path(__file__).resolve().parents[3]


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
        package_path: str | Path | None = None,
        executable: str = "CalendarPilotKernelServer",
        executable_path: str | Path | None = None,
    ) -> None:
        configured_package = os.environ.get("CALENDAR_PILOT_SWIFT_KERNEL_PACKAGE")
        configured_executable = os.environ.get("CALENDAR_PILOT_SWIFT_KERNEL_SERVER")
        self.package_path = str(Path(package_path or configured_package or ROOT / "packages" / "CalendarPilotKernel"))
        self.executable = executable
        self.executable_path = str(executable_path or configured_executable or "") or None
        self.authority_grants: dict[str, AuthorityGrant] = {}
        self.undo_ledger: dict[str, str] = {}
        self._proc: subprocess.Popen[str] | None = None
        self._rpc_lock = threading.RLock()

    def __enter__(self) -> "SwiftKernelIPCClient":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def start(self) -> None:
        if self._proc is not None:
            return
        command = [self.executable_path] if self.executable_path else ["swift", "run", "--package-path", self.package_path, self.executable]
        try:
            self._proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise SwiftKernelIPCError(f"failed to start Swift kernel IPC server: {exc}") from exc

    def close(self) -> None:
        with self._rpc_lock:
            if self._proc is None:
                return
            proc = self._proc
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()
            self._proc = None

    def issue_authority_grant(
        self,
        *,
        user_scope_id: str,
        max_authority_tier: int,
        scopes: Iterable[str] | None = None,
        confirmation_provenance: str = "ipc_user_confirmed_scope",
        ttl_minutes: int = 30,
        ttl_seconds: int | None = None,
        confirmed_by_user: bool = True,
        issued_at: datetime | None = None,
    ) -> AuthorityGrant:
        issued_at = issued_at or datetime.now().astimezone()
        ttl_seconds = int(ttl_seconds if ttl_seconds is not None else ttl_minutes * 60)
        payload = {
            "user_scope_id": user_scope_id,
            "max_authority_tier": max_authority_tier,
            "scopes": list(scopes or ["recommend", "stage", "commit_private", "undo"]),
            "confirmation_provenance": confirmation_provenance,
            "ttl_seconds": ttl_seconds,
            "confirmed_by_user": confirmed_by_user,
            "issued_at": issued_at.isoformat(),
        }
        out = self._rpc("issue_authority_grant", payload)
        grant = AuthorityGrant.from_dict(out["authority_grant"])
        self.authority_grants[grant.grant_id] = grant
        return grant

    def resolve_authority_grant(self, grant: AuthorityGrant | str | None) -> AuthorityGrant | None:
        if isinstance(grant, AuthorityGrant):
            return self.authority_grants.get(grant.grant_id)
        if isinstance(grant, str):
            return self.authority_grants.get(grant)
        return None

    def restore_authority_grant(self, grant: AuthorityGrant) -> AuthorityGrant:
        out = self._rpc("restore_authority_grant", {"authority_grant": grant.to_dict()})
        restored = AuthorityGrant.from_dict(out["authority_grant"])
        self.authority_grants[restored.grant_id] = restored
        return restored

    def restore_undo_handle(
        self,
        rollback_handle_id: str,
        candidate_id: str,
        observation: RawCalendarObservation,
        *,
        generated_event_ids: list[str] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self._rpc("restore_undo_handle", {
            "rollback_handle_id": rollback_handle_id,
            "candidate_id": candidate_id,
            "observation": to_jsonable(observation),
            "generated_event_ids": generated_event_ids or [],
            "created_at": created_at.isoformat() if created_at else observation.observed_at.isoformat(),
        })
        self.undo_ledger[rollback_handle_id] = candidate_id

    def preview_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        return self._act(
            "preview",
            candidate,
            observation,
            self._grant_id(authority_grant),
            requested_authority_tier if requested_authority_tier is not None else candidate.required_authority_tier,
            correlation_id=correlation_id,
        )

    def stage_candidate(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        authority_grant_id: str | None = None,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        return self._act(
            "stage",
            candidate,
            observation,
            authority_grant_id or self._grant_id(authority_grant),
            requested_authority_tier if requested_authority_tier is not None else candidate.required_authority_tier,
            correlation_id=correlation_id,
        )

    def authorize_and_materialize(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        authority_grant_id: str | None = None,
        requested_authority_tier: int | None = None,
        granted_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        desired_tier = requested_authority_tier if requested_authority_tier is not None else (granted_authority_tier or candidate.required_authority_tier)
        receipt = self._act("commit", candidate, observation, authority_grant_id or self._grant_id(authority_grant), desired_tier, correlation_id=correlation_id)
        if receipt.rollback_handle_id and not receipt.denied_reason:
            self.undo_ledger[receipt.rollback_handle_id] = candidate.candidate_id
        return receipt

    def request_undo(
        self,
        rollback_handle_id: str,
        observation: RawCalendarObservation,
        authority_grant: AuthorityGrant | str | None = None,
        *,
        authority_grant_id: str | None = None,
        requested_authority_tier: int | None = None,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        out = self._rpc("undo", {
            "rollback_handle_id": rollback_handle_id,
            "authority_grant_id": authority_grant_id or self._grant_id(authority_grant),
            "observed_at": observation.observed_at.isoformat(),
            "correlation_id": correlation_id,
        })
        receipt = _receipt_from_dict(out["receipt"])
        if not receipt.denied_reason:
            self.undo_ledger.pop(rollback_handle_id, None)
        return receipt

    @staticmethod
    def is_people_affecting_mutation(candidate: CandidateCalendarAction) -> bool:
        return SwiftKernelStub.is_people_affecting_mutation(candidate)

    @staticmethod
    def has_write_action(candidate: CandidateCalendarAction) -> bool:
        return SwiftKernelStub.has_write_action(candidate)

    def _act(
        self,
        op: str,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority_grant_id: str | None,
        requested_authority_tier: int,
        *,
        correlation_id: str | None = None,
    ) -> CalendarActionReceipt:
        out = self._rpc(op, {
            "candidate": candidate.to_dict(),
            "observation": to_jsonable(observation),
            "authority_grant_id": authority_grant_id,
            "requested_authority_tier": requested_authority_tier,
            "correlation_id": correlation_id or candidate.candidate_id,
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
        with self._rpc_lock:
            self.start()
            assert self._proc is not None and self._proc.stdin is not None and self._proc.stdout is not None
            request_id = "rpc_" + uuid.uuid4().hex[:12]
            self._proc.stdin.write(json.dumps({"id": request_id, "op": op, "payload": to_jsonable(payload)}, sort_keys=True) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                stderr = self._proc.stderr.read() if self._proc.stderr else ""
                raise SwiftKernelIPCError(f"Swift kernel server closed: {stderr}")
            response = json.loads(line)
            if response.get("id") != request_id:
                raise SwiftKernelIPCError(f"Swift kernel RPC id mismatch: expected {request_id}, got {response.get('id')}")
            if not response.get("ok"):
                raise SwiftKernelIPCError(response.get("error") or "Swift kernel RPC failed")
            return dict(response.get("payload", {}))


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
