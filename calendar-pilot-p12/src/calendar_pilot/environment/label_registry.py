from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any

from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import LabelActivation, SemanticSignal, to_jsonable


@dataclass
class LabelRegistry:
    """Swift-patterned registry for user-governed semantic labels.

    Labels can influence ranking/timing only through explicit active IDs.  They
    never issue grants, raise authority tiers, or widen scopes.
    """

    signals: dict[str, SemanticSignal] = field(default_factory=dict)
    activation_state: dict[str, str] = field(default_factory=dict)
    replay: ReplayBuffer | None = None

    def propose(self, signal: SemanticSignal | dict[str, Any]) -> SemanticSignal:
        if isinstance(signal, dict):
            signal = SemanticSignal.from_dict(signal)
        if signal.kind == "derived" and not signal.evidence:
            raise ValueError("derived SemanticSignal requires evidence")
        self.signals[signal.signal_id] = signal
        self.activation_state.setdefault(signal.signal_id, signal.status or "proposed")
        if self.replay is not None:
            self.replay.append_semantic_signal(signal.to_dict(), trace_id=signal.signal_id)
        return signal

    def activate(self, signal_id: str, *, user_scope_id: str, actor: str = "user", surface: str = "signals_settings", status: str = "active", reason: str = "") -> LabelActivation:
        if signal_id not in self.signals:
            raise KeyError(signal_id)
        if actor != "user" and self.activation_state.get(signal_id) == "disabled":
            raise ValueError("disabled labels cannot be auto-reactivated")
        at = datetime.now(timezone.utc)
        digest = hashlib.sha1(f"{signal_id}|{status}|{actor}|{at.isoformat()}".encode("utf-8")).hexdigest()[:12]
        activation = LabelActivation(
            activation_id=f"label_act_{digest}",
            signal_id=signal_id,
            user_scope_id=user_scope_id,
            status=status,
            actor=actor,
            surface=surface,
            at=at,
            reason=reason,
        )
        self.activation_state[signal_id] = status
        if self.replay is not None:
            self.replay.append_label_activation(activation.to_dict(), trace_id=signal_id, causal_parent_id=f"semantic_signal:{signal_id}")
        return activation

    def disable(self, signal_id: str, *, user_scope_id: str, actor: str = "user", surface: str = "signals_settings", reason: str = "user disabled label") -> LabelActivation:
        return self.activate(signal_id, user_scope_id=user_scope_id, actor=actor, surface=surface, status="disabled", reason=reason)

    def active_labels(self) -> list[SemanticSignal]:
        return [signal for sid, signal in self.signals.items() if self.activation_state.get(sid) == "active"]

    def is_active(self, signal_id: str) -> bool:
        return self.activation_state.get(signal_id) == "active"

    def ranking_features(self) -> dict[str, Any]:
        return {signal.signal_id: signal.to_dict() for signal in self.active_labels()}

    def authority_payload(self) -> dict[str, Any]:
        """Barrier B2: label registry never contributes authority facts."""
        return {"max_authority_tier": None, "scopes": [], "grant_ids": []}

    def to_dict(self) -> dict[str, Any]:
        return {
            "signals": {sid: signal.to_dict() for sid, signal in self.signals.items()},
            "activation_state": dict(self.activation_state),
            "active_signal_ids": [signal.signal_id for signal in self.active_labels()],
        }
