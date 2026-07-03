from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from calendar_pilot.environment.signal_streams import SignalStream, infer_signal_stream, VALID_SIGNAL_STREAMS


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


def _stream(rec: dict[str, Any]) -> str:
    return str(rec.get("signal_stream") or infer_signal_stream(str(rec.get("record_type") or ""), _payload(rec)))


def check_b0_signal_stream_present(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in _records(records):
        stream = _stream(rec)
        if stream not in VALID_SIGNAL_STREAMS:
            out.append(Violation("B0", _rid(rec), f"invalid signal_stream={stream!r}"))
    return out


def check_b1_semantic_signal_has_evidence(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    rows = _records(records)
    known = {str(row.get("record_id")) for row in rows if row.get("record_id")}
    for rec in rows:
        if rec.get("record_type") != "semantic_signal":
            continue
        payload = _payload(rec)
        if payload.get("kind", "derived") != "derived":
            continue
        evidence = [str(e) for e in payload.get("evidence", [])]
        if not evidence:
            out.append(Violation("B1", _rid(rec), "derived SemanticSignal lacks evidence"))
            continue
        missing = [e for e in evidence if e not in known and not e.startswith("notification_history:")]
        if missing:
            out.append(Violation("B1", _rid(rec), f"semantic signal evidence not found: {missing[:3]}"))
    return out


def check_b2_labels_never_gate_authority(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    forbidden_keys = {"semantic_signal_id", "semantic_signal_ids", "active_labels", "active_label_ids", "signal_id"}
    authority_types = {"codex_tool_call", "codex_tool_receipt", "receipt", "envelope_transition"}
    for rec in _records(records):
        if rec.get("record_type") not in authority_types:
            continue
        raw = str(_payload(rec))
        if any(key in raw for key in forbidden_keys) and any(token in raw for token in ["authority", "grant", "scope", "tier"]):
            out.append(Violation("B2", _rid(rec), "semantic label/signal appears in authority payload"))
    return out


def check_b3_label_activation_user_audited(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in _records(records):
        if rec.get("record_type") != "label_activation":
            continue
        payload = _payload(rec)
        if not payload.get("actor"):
            out.append(Violation("B3", _rid(rec), "label activation missing actor"))
        if payload.get("actor") == "default_policy" and payload.get("status") == "active":
            # Allowed only if explicitly marked as ranking/timing-only activation.
            if payload.get("authority_effect") not in {None, "none"}:
                out.append(Violation("B3", _rid(rec), "default activation has authority effect"))
    return out


def check_b4_reward_purity(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in _records(records):
        payload = _payload(rec)
        has_reward = rec.get("record_type") == "reward" or isinstance(payload.get("reward"), dict)
        if has_reward and _stream(rec) != SignalStream.ACTION.value:
            out.append(Violation("B4", _rid(rec), f"reward payload in non-action stream {_stream(rec)!r}"))
    return out


def check_b5_biography_drift_findings_are_explicit(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in _records(records):
        if rec.get("record_type") != "biography_drift_finding":
            continue
        payload = _payload(rec)
        for key in ["biography_claim", "semantic_signal_id", "conflict", "evidence"]:
            if not payload.get(key):
                out.append(Violation("B5", _rid(rec), f"biography drift finding missing {key}"))
    return out


def check_b6_estimator_version(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in _records(records):
        if rec.get("record_type") == "signal_estimator_report":
            if not _payload(rec).get("estimator_version"):
                out.append(Violation("B6", _rid(rec), "estimator report missing estimator_version"))
        if rec.get("record_type") == "semantic_signal" and _payload(rec).get("created_by") == "estimator":
            if not _payload(rec).get("estimator_version"):
                out.append(Violation("B6", _rid(rec), "estimator-created signal missing estimator_version"))
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
        rollback_state = provider.get("rollback_state") or env.get("rollback_state")
        sync_status = env.get("sync_status") or env.get("swift_receipt", {}).get("sync_status")
        actuation_mode = env.get("actuation_mode") or env.get("swift_receipt", {}).get("actuation_mode")
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
    "B0": check_b0_signal_stream_present,
    "B1": check_b1_semantic_signal_has_evidence,
    "B2": check_b2_labels_never_gate_authority,
    "B3": check_b3_label_activation_user_audited,
    "B4": check_b4_reward_purity,
    "B5": check_b5_biography_drift_findings_are_explicit,
    "B6": check_b6_estimator_version,
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
