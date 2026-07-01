from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import subprocess
import uuid
from typing import Any

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

    def __init__(self, *, package_path: str | Path = "packages/CalendarPilotKernel", executable: str = "CalendarPilotKernelServer") -> None:
        self.package_path = str(package_path)
        self.executable = executable
        self._proc: subprocess.Popen[str] | None = None

    def __enter__(self) -> "SwiftKernelIPCClient":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def start(self) -> None:
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            ["swift", "run", "--package-path", self.package_path, self.executable],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
        return AuthorityGrant.from_dict(out["authority_grant"])

    def stage_candidate(self, candidate: CandidateCalendarAction, observation: RawCalendarObservation, *, authority_grant_id: str | None, requested_authority_tier: int) -> CalendarActionReceipt:
        return self._act("stage", candidate, observation, authority_grant_id, requested_authority_tier)

    def authorize_and_materialize(self, candidate: CandidateCalendarAction, observation: RawCalendarObservation, *, authority_grant_id: str | None, requested_authority_tier: int) -> CalendarActionReceipt:
        return self._act("commit", candidate, observation, authority_grant_id, requested_authority_tier)

    def request_undo(self, rollback_handle_id: str, observation: RawCalendarObservation, *, authority_grant_id: str | None) -> CalendarActionReceipt:
        out = self._rpc("undo", {
            "rollback_handle_id": rollback_handle_id,
            "authority_grant_id": authority_grant_id,
            "observed_at": observation.observed_at.isoformat(),
        })
        return _receipt_from_dict(out["receipt"])

    def _act(self, op: str, candidate: CandidateCalendarAction, observation: RawCalendarObservation, authority_grant_id: str | None, requested_authority_tier: int) -> CalendarActionReceipt:
        out = self._rpc(op, {
            "candidate": candidate.to_dict(),
            "observation": to_jsonable(observation),
            "authority_grant_id": authority_grant_id,
            "requested_authority_tier": requested_authority_tier,
        })
        return _receipt_from_dict(out["receipt"])

    def _rpc(self, op: str, payload: dict[str, Any]) -> dict[str, Any]:
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
