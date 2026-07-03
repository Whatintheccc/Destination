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


def _rid(rec: dict[str, Any]) -> str:
    return str(rec.get("record_id") or "?")


def _payload(rec: dict[str, Any]) -> dict[str, Any]:
    payload = rec.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def check_r1_replay_row_shape(records: list[dict[str, Any]]) -> list[Violation]:
    """Strict P11 row shape for replay rows that can feed debugging/training."""
    out: list[Violation] = []
    allowed_versions = {"r1"}
    for rec in _records(records):
        rid = _rid(rec)
        version = rec.get("record_schema_version")
        if version not in allowed_versions:
            out.append(Violation("R1", rid, f"record_schema_version={version!r}"))
        if not rec.get("record_type"):
            out.append(Violation("R1", rid, "missing record_type"))
        if not rec.get("record_id"):
            out.append(Violation("R1", rid, "missing record_id"))
        if not rec.get("trace_id"):
            out.append(Violation("R1", rid, "missing trace_id"))
        parent = rec.get("causal_parent_id")
        if parent in {None, ""}:
            out.append(Violation("R1", rid, "missing causal_parent_id"))
    return out


def check_i2_rollback_state_never_absent(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    allowed = {"verified", "pending", "failed", "impossible", "unsupported"}
    for rec in _records(records):
        if rec.get("record_type") != "envelope_transition":
            continue
        env = _payload(rec).get("envelope", {})
        state = env.get("provider", {}).get("rollback_state")
        if env.get("current_state") in {"commit", "verify", "undo"} and state not in allowed:
            out.append(Violation("I2", _rid(rec), f"rollback_state={state!r}"))
    return out


def check_i2a_committed_writes_have_meaningful_rollback(records: list[dict[str, Any]]) -> list[Violation]:
    """I2′: unsupported rollback is not adequate for committed writes."""
    out: list[Violation] = []
    for rec in _records(records):
        if rec.get("record_type") != "envelope_transition":
            continue
        env = _payload(rec).get("envelope", {})
        if env.get("current_state") != "commit":
            continue
        provider = env.get("provider", {}) if isinstance(env.get("provider", {}), dict) else {}
        swift_receipt = env.get("swift_receipt") if isinstance(env.get("swift_receipt"), dict) else {}
        rollback_state = provider.get("rollback_state") or env.get("rollback_state")
        sync_status = env.get("sync_status") or swift_receipt.get("sync_status")
        actuation_mode = env.get("actuation_mode") or swift_receipt.get("actuation_mode")
        candidate = env.get("candidate") if isinstance(env.get("candidate"), dict) else {}
        reversibility = candidate.get("reversibility") or env.get("reversibility")
        committed_write = sync_status in {"materialized", "committed"} or actuation_mode == "materialized_write" or env.get("tool_status") == "committed"
        if committed_write and rollback_state == "unsupported":
            out.append(Violation("I2′", _rid(rec), "committed materialized write has rollback_state=unsupported"))
        if committed_write and rollback_state == "impossible" and reversibility not in {"none", None}:
            out.append(Violation("I2′", _rid(rec), f"rollback impossible on reversible candidate reversibility={reversibility!r}"))
    return out


def check_i3_causal_parent_exists(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    rows = _records(records)
    known = {str(rec.get("record_id")) for rec in rows if rec.get("record_id")}
    for row in rows:
        payload = _payload(row)
        call = payload.get("call", {}) if isinstance(payload.get("call"), dict) else {}
        receipt = payload.get("receipt", {}) if isinstance(payload.get("receipt"), dict) else {}
        if call.get("tool_call_id"):
            known.add(str(call["tool_call_id"]))
        if receipt.get("receipt_id"):
            known.add(str(receipt["receipt_id"]))
    for rec in rows:
        parent = rec.get("causal_parent_id")
        if not parent:
            continue
        if parent == "ROOT":
            continue
        if str(parent).startswith("self_play_episode:") or str(parent).startswith("lab_frontier"):
            continue
        if parent not in known:
            out.append(Violation("I3", _rid(rec), f"causal_parent_id not found: {parent}"))
    return out


def check_i5_artifact_ref_hash_shape(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in _records(records):
        if rec.get("record_type") != "artifact_ref":
            continue
        payload = _payload(rec)
        sha = payload.get("sha256")
        path = payload.get("path")
        if not path:
            out.append(Violation("I5", _rid(rec), "artifact_ref missing path"))
        if sha is not None and (not isinstance(sha, str) or len(sha) != 64):
            out.append(Violation("I5", _rid(rec), f"artifact_ref invalid sha256={sha!r}"))
    return out


def check_i6_undo_never_replays(records: list[dict[str, Any]]) -> list[Violation]:
    seen: set[str] = set()
    out: list[Violation] = []
    for rec in _records(records):
        payload = _payload(rec)
        receipt = payload.get("receipt", {})
        if rec.get("record_type") == "receipt" and receipt.get("sync_status") == "reverted":
            handle = receipt.get("rollback_handle_id") or ""
            if handle in seen:
                out.append(Violation("I6", _rid(rec), f"handle replayed: {handle}"))
            if handle:
                seen.add(handle)
    return out


def check_i7_rate_cap_denials_visible(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    rows = _records(records)
    for rec in rows:
        if rec.get("record_type") != "envelope_transition":
            continue
        env = _payload(rec).get("envelope", {})
        detail = (env.get("lifecycle") or [{}])[-1].get("detail", {}) if isinstance(env.get("lifecycle"), list) else {}
        reason = str(detail.get("denied_reason") or env.get("denied_reason") or "")
        if "rate_cap_exceeded" not in reason:
            continue
        trace = rec.get("trace_id")
        has_receipt = any(
            row.get("record_type") == "receipt" and row.get("trace_id") == trace and "rate_cap_exceeded" in str(_payload(row).get("receipt", {}).get("denied_reason") or "")
            for row in rows
        )
        if not has_receipt:
            out.append(Violation("I7", _rid(rec), "rate cap denial envelope lacks denial receipt row"))
    return out


CHECKS: dict[str, Check] = {
    "R1": check_r1_replay_row_shape,
    "I2": check_i2_rollback_state_never_absent,
    "I2′": check_i2a_committed_writes_have_meaningful_rollback,
    "I3": check_i3_causal_parent_exists,
    "I5": check_i5_artifact_ref_hash_shape,
    "I6": check_i6_undo_never_replays,
    "I7": check_i7_rate_cap_denials_visible,
}


def check_replay(records: list[dict[str, Any]]) -> list[Violation]:
    violations: list[Violation] = []
    for check in CHECKS.values():
        violations.extend(check(records))
    return violations
