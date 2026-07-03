from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Violation:
    invariant_id: str
    record_id: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"invariant_id": self.invariant_id, "record_id": self.record_id, "detail": self.detail}


Check = Callable[[list[dict[str, Any]]], list[Violation]]


def _records(records: list[Any]) -> list[dict[str, Any]]:
    out = []
    for rec in records:
        if hasattr(rec, "envelope"):
            out.append(rec.envelope())
        else:
            out.append(dict(rec))
    return out


def check_i2_rollback_state_never_absent(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    allowed = {"verified", "pending", "failed", "impossible", "unsupported"}
    for rec in _records(records):
        if rec.get("record_type") != "envelope_transition":
            continue
        env = rec.get("payload", {}).get("envelope", {})
        state = env.get("provider", {}).get("rollback_state")
        if env.get("current_state") in {"commit", "verify", "undo"} and state not in allowed:
            out.append(Violation("I2", rec.get("record_id", "?"), f"rollback_state={state!r}"))
    return out


def check_i6_undo_never_replays(records: list[dict[str, Any]]) -> list[Violation]:
    seen: set[str] = set()
    out: list[Violation] = []
    for rec in _records(records):
        payload = rec.get("payload", {})
        receipt = payload.get("receipt", {})
        if rec.get("record_type") == "receipt" and receipt.get("sync_status") == "reverted":
            handle = receipt.get("rollback_handle_id") or ""
            if handle in seen:
                out.append(Violation("I6", rec.get("record_id", "?"), f"handle replayed: {handle}"))
            if handle:
                seen.add(handle)
    return out


CHECKS: dict[str, Check] = {
    "I2": check_i2_rollback_state_never_absent,
    "I6": check_i6_undo_never_replays,
}


def check_replay(records: list[dict[str, Any]]) -> list[Violation]:
    violations: list[Violation] = []
    for check in CHECKS.values():
        violations.extend(check(records))
    return violations
