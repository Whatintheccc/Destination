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


def check_r1_record_ids(records: list[dict[str, Any]]) -> list[Violation]:
    return [
        Violation("R1", str(i), "missing record_id")
        for i, rec in enumerate(_records(records))
        if not rec.get("record_id")
    ]


def check_r2_trace_ids(records: list[dict[str, Any]]) -> list[Violation]:
    return [
        Violation("R2", rec.get("record_id", str(i)), "missing trace_id")
        for i, rec in enumerate(_records(records))
        if not rec.get("trace_id")
    ]


def check_r3_causal_parents_exist(records: list[dict[str, Any]]) -> list[Violation]:
    seen: set[str] = set()
    out: list[Violation] = []
    for rec in _records(records):
        parent = rec.get("causal_parent_id")
        if parent and parent not in seen:
            out.append(Violation("R3", rec.get("record_id", "?"), f"unknown parent: {parent}"))
        record_id = rec.get("record_id")
        if record_id:
            seen.add(str(record_id))
    return out


def check_r4_receipts_carry_candidate(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in _records(records):
        if rec.get("record_type") != "receipt":
            continue
        payload = rec.get("payload", {})
        receipt = payload.get("receipt", {}) or {}
        candidate = payload.get("candidate", {}) or {}
        if not (candidate.get("candidate_id") or receipt.get("candidate_id")):
            out.append(Violation("R4", rec.get("record_id", "?"), "receipt without candidate_id"))
    return out


def check_r5_rewards_reference_receipts(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in _records(records):
        if rec.get("record_type") != "reward":
            continue
        payload = rec.get("payload", {})
        if not rec.get("causal_parent_id") and not payload.get("receipt"):
            out.append(Violation("R5", rec.get("record_id", "?"), "reward without receipt linkage"))
    return out


CHECKS: dict[str, Check] = {
    "I2": check_i2_rollback_state_never_absent,
    "I6": check_i6_undo_never_replays,
    "R1": check_r1_record_ids,
    "R2": check_r2_trace_ids,
    "R3": check_r3_causal_parents_exist,
    "R4": check_r4_receipts_carry_candidate,
    "R5": check_r5_rewards_reference_receipts,
}


def check_replay(records: list[dict[str, Any]]) -> list[Violation]:
    violations: list[Violation] = []
    for check in CHECKS.values():
        violations.extend(check(records))
    return violations
