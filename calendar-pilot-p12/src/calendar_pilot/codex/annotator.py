from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

from calendar_pilot.types import SemanticSignal


class CodexSemanticAnnotator:
    """Evidence-cited semantic annotator over stream-tagged replay windows."""

    def propose(self, records: list[dict[str, Any]], *, user_scope_id: str = "default_user") -> list[SemanticSignal]:
        action_rows = [r for r in records if r.get("signal_stream") == "action" or r.get("record_type") in {"reward", "human_feedback_event", "label_activation"}]
        world_rows = [r for r in records if r.get("signal_stream") == "world" or r.get("record_type") in {"raw_calendar_observation", "provider_transaction"}]
        proposals: list[SemanticSignal] = []
        evening_dismissals: list[str] = []
        prep_accepts: list[str] = []
        for row in action_rows:
            payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
            reward = payload.get("reward", payload)
            rid = str(row.get("record_id") or payload.get("reward_event_id") or "row")
            if reward.get("notification_dismissed") or reward.get("ignored") or reward.get("outcome") in {"dismissed", "ignored"}:
                hour = _hour_from_payload(payload)
                if hour is None or hour >= 18:
                    evening_dismissals.append(rid)
            candidate = payload.get("candidate", {}) if isinstance(payload.get("candidate"), dict) else {}
            if candidate.get("intent") == "create_prep_block" and (reward.get("accepted") or reward.get("explicit_useful")):
                prep_accepts.append(rid)
        if len(evening_dismissals) >= 2:
            proposals.append(self._signal(
                label="dismisses_evening_suggestions",
                statement="Dismisses or ignores suggestion notifications sent in the evening",
                evidence=evening_dismissals,
                user_scope_id=user_scope_id,
                confidence=min(0.95, 0.55 + 0.08 * len(evening_dismissals)),
            ))
        if len(prep_accepts) >= 2 or (prep_accepts and world_rows):
            proposals.append(self._signal(
                label="accepts_prep_blocks_near_external_calls",
                statement="Accepts prep blocks adjacent to externally relevant meetings",
                evidence=prep_accepts + [str(r.get("record_id")) for r in world_rows[:2]],
                user_scope_id=user_scope_id,
                confidence=min(0.95, 0.55 + 0.08 * len(prep_accepts)),
            ))
        return proposals

    def _signal(self, *, label: str, statement: str, evidence: list[str], user_scope_id: str, confidence: float) -> SemanticSignal:
        now = datetime.now(timezone.utc)
        digest = hashlib.sha1(f"{user_scope_id}|{label}|{','.join(evidence)}".encode("utf-8")).hexdigest()[:12]
        return SemanticSignal(
            signal_id=f"sig_{label}_{digest}",
            user_scope_id=user_scope_id,
            label=label,
            statement=statement,
            kind="derived",
            created_by="codex_annotator",
            evidence=evidence,
            evidence_window={"from": None, "to": None},
            confidence=round(confidence, 3),
            half_life_days=28,
            status="proposed",
            activation={},
            estimator_version=None,
        )


def _hour_from_payload(payload: dict[str, Any]) -> int | None:
    raw = payload.get("observed_at") or payload.get("sent_at")
    if not raw and isinstance(payload.get("reward"), dict):
        raw = payload["reward"].get("observed_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).hour
    except ValueError:
        return None
