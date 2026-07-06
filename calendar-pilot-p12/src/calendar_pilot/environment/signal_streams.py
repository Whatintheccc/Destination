from __future__ import annotations

"""P12 signal-stream classification and replay helpers.

CalendarPilot separates fast human actions, provider/world facts, user-owned
biography priors, derived semantic signals, and system/meta rows.  The mapping is
kept mechanical so reducers, simulators, and UI code can filter by stream instead
of inferring semantics ad hoc.
"""

from enum import Enum
from typing import Any


class SignalStream(str, Enum):
    ACTION = "action"
    WORLD = "world"
    BIOGRAPHY = "biography"
    DERIVED = "derived"
    SYSTEM = "system"


VALID_SIGNAL_STREAMS = {stream.value for stream in SignalStream}

RECORD_TYPE_TO_STREAM: dict[str, str] = {
    # Stream A: interpretable human/app actions. This is the only reward truth.
    "reward": SignalStream.ACTION.value,
    "human_feedback_event": SignalStream.ACTION.value,
    "label_activation": SignalStream.ACTION.value,
    # Stream B: provider/calendar world facts.
    "raw_calendar_observation": SignalStream.WORLD.value,
    "dogfood_observation": SignalStream.WORLD.value,
    "provider_transaction": SignalStream.WORLD.value,
    # Stream C: user-owned self-description and conversation-derived priors.
    "biography_claim": SignalStream.BIOGRAPHY.value,
    "biography_correction": SignalStream.BIOGRAPHY.value,
    "biography_drift_finding": SignalStream.BIOGRAPHY.value,
    "profile_update_event": SignalStream.BIOGRAPHY.value,
    # Derived layer: estimated semantic/user signals.
    "semantic_signal": SignalStream.DERIVED.value,
    "signal_estimator_report": SignalStream.DERIVED.value,
    "belief": SignalStream.DERIVED.value,
    # Everything else is system/meta unless payload content says otherwise.
    "decision": SignalStream.SYSTEM.value,
    "receipt": SignalStream.SYSTEM.value,
    "candidate_receipt": SignalStream.SYSTEM.value,
    "self_play_episode": SignalStream.SYSTEM.value,
    "adversary_finding": SignalStream.SYSTEM.value,
    "codex_tool_call": SignalStream.SYSTEM.value,
    "codex_tool_receipt": SignalStream.SYSTEM.value,
    "router_decision": SignalStream.SYSTEM.value,
    "model_generation_rejection": SignalStream.SYSTEM.value,
    "envelope_transition": SignalStream.SYSTEM.value,
    "frontier_generation": SignalStream.SYSTEM.value,
    "tuning_reduction": SignalStream.SYSTEM.value,
    "artifact_ref": SignalStream.SYSTEM.value,
}


def infer_signal_stream(record_type: str, payload: dict[str, Any] | None = None) -> str:
    """Return the canonical stream for a replay row.

    Legacy `candidate_receipt` rows may contain an attached reward; classify those
    as action rows so P11 golden replay stays readable while new P12 writes use
    explicit `reward` rows.
    """
    payload = payload if isinstance(payload, dict) else {}
    if record_type == "candidate_receipt" and isinstance(payload.get("reward"), dict):
        return SignalStream.ACTION.value
    return RECORD_TYPE_TO_STREAM.get(record_type, SignalStream.SYSTEM.value)


def normalize_signal_stream(value: str | None, record_type: str, payload: dict[str, Any] | None = None) -> str:
    if value in VALID_SIGNAL_STREAMS:
        return str(value)
    return infer_signal_stream(record_type, payload)


def stream_allows_reward(stream: str) -> bool:
    return stream == SignalStream.ACTION.value
