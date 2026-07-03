from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import hashlib
import json


ROLLBACK_STATES = {"verified", "pending", "failed", "impossible", "unsupported"}


def _digest(payload: Any, prefix: str) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def rollback_state_from_receipt(receipt: dict[str, Any] | None, provider_rollback: dict[str, Any] | None = None) -> str:
    receipt = receipt or {}
    provider_rollback = provider_rollback or {}
    status = str(receipt.get("sync_status") or receipt.get("status") or "")
    if status == "denied":
        return "unsupported"
    if status == "reverted":
        return "verified" if provider_rollback.get("rollback_verified", True) else "failed"
    if receipt.get("rollback_handle_id"):
        return "verified" if provider_rollback.get("rollback_verified") is True else "pending"
    if status in {"materialized", "committed"}:
        return "impossible" if receipt.get("reversibility") == "none" else "unsupported"
    return "unsupported"


@dataclass
class ActionEnvelope:
    envelope_id: str
    trace_id: str
    candidate_id: str
    observation_fingerprint: str | None
    runtime_mode: str
    backends: dict[str, str]
    authority: dict[str, Any] = field(default_factory=dict)
    lifecycle: list[dict[str, Any]] = field(default_factory=list)
    provider: dict[str, Any] = field(default_factory=dict)
    reward: dict[str, Any] = field(default_factory=dict)
    replay_record_ids: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        trace_id: str,
        candidate_id: str,
        observation_fingerprint: str | None,
        runtime_mode: str,
        backends: dict[str, str],
        authority: dict[str, Any] | None = None,
    ) -> "ActionEnvelope":
        envelope_id = _digest([trace_id, candidate_id, observation_fingerprint, runtime_mode, backends], "env")
        return cls(envelope_id, trace_id, candidate_id, observation_fingerprint, runtime_mode, backends, authority or {})

    @property
    def current_state(self) -> str:
        return self.lifecycle[-1]["transition"] if self.lifecycle else "prepared"

    def transition(self, transition: str, *, status: str, swift_receipt_id: str | None = None, detail: dict[str, Any] | None = None) -> "ActionEnvelope":
        self.lifecycle.append({
            "transition": transition,
            "at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "swift_receipt_id": swift_receipt_id,
            "detail": detail or {},
        })
        if "rollback_state" not in self.provider:
            self.provider["rollback_state"] = "unsupported"
        return self

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.__dict__)
        data["current_state"] = self.current_state
        data["envelope_version"] = "calendar_action_envelope.v2"
        if data.get("provider", {}).get("rollback_state") not in ROLLBACK_STATES:
            data.setdefault("provider", {})["rollback_state"] = "unsupported"
        return data