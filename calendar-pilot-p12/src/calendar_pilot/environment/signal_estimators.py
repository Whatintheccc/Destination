from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from calendar_pilot.types import RawCalendarObservation, SemanticSignal, SignalEstimatorReport

INTERruption_VERSION = "interruption_tolerance_v1"
INTERUPTION_TOLERANCE_VERSION = INTERruption_VERSION  # backwards-safe alias for typos in callers
INTERRUPTION_TOLERANCE_VERSION = INTERruption_VERSION


@dataclass(frozen=True)
class InterruptionToleranceOutput:
    signal: SemanticSignal
    report: SignalEstimatorReport

    @property
    def overall_tolerance(self) -> float:
        return float(self.signal.payload.get("overall_tolerance", 0.5))

    @property
    def dismissal_streak(self) -> int:
        return int(self.signal.payload.get("dismissal_streak", 0))

    @property
    def by_hour(self) -> dict[int, float]:
        return {int(k): float(v) for k, v in self.signal.payload.get("interruption_tolerance_by_hour", {}).items()}


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _evidence_window(rows: list[dict[str, Any]]) -> dict[str, str | None]:
    stamps = [_parse_dt(row.get("sent_at") or row.get("observed_at") or row.get("at")) for row in rows]
    stamps = [stamp for stamp in stamps if stamp is not None]
    if not stamps:
        return {"from": None, "to": None}
    return {"from": min(stamps).isoformat(), "to": max(stamps).isoformat()}


def _input_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class InterruptionToleranceEstimator:
    """Estimate interruption tolerance from ActionStream/WorldStream behavior.

    The estimator intentionally does not read the removed notification-fatigue scalar.
    It consumes observable notification outcomes, undo-after-accept rows, and
    response timing if available. Higher tolerance means a proactive suggestion is
    more likely to be welcome; lower tolerance means bundling/drafting is safer.
    """

    version = INTERRUPTION_TOLERANCE_VERSION

    def estimate(self, observation: RawCalendarObservation, *, now: datetime | None = None, window_days: int = 28) -> InterruptionToleranceOutput:
        now = now or observation.observed_at or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=window_days)
        raw_history = list(observation.notification_history or [])
        history: list[dict[str, Any]] = []
        for idx, row in enumerate(raw_history):
            row = dict(row)
            row.setdefault("evidence_id", f"notification_history:{observation.observation_id}:{idx}")
            stamp = _parse_dt(row.get("sent_at") or row.get("observed_at") or row.get("at"))
            if stamp is not None and stamp < cutoff:
                continue
            history.append(row)
        by_hour_counts: dict[int, dict[str, int]] = {hour: {"total": 0, "negative": 0, "positive": 0} for hour in range(24)}
        streak = 0
        for row in sorted(history, key=lambda r: str(r.get("sent_at") or r.get("observed_at") or r.get("at") or "")):
            stamp = _parse_dt(row.get("sent_at") or row.get("observed_at") or row.get("at"))
            hour = stamp.hour if stamp is not None else int(row.get("hour", observation.device_context.local_hour))
            outcome = str(row.get("outcome") or row.get("action") or "").lower()
            negative = outcome in {"dismissed", "ignored", "explicit_wrong", "not_needed", "label_disabled"}
            positive = outcome in {"accepted", "useful", "explicit_useful", "clicked"}
            by_hour_counts[hour]["total"] += 1
            by_hour_counts[hour]["negative"] += int(negative)
            by_hour_counts[hour]["positive"] += int(positive)
            if negative:
                streak += 1
            elif positive:
                streak = 0
        tolerance_by_hour: dict[str, float] = {}
        all_total = 0
        all_negative = 0
        all_positive = 0
        for hour, counts in by_hour_counts.items():
            total = counts["total"]
            all_total += total
            all_negative += counts["negative"]
            all_positive += counts["positive"]
            if total == 0:
                tolerance = 0.5
            else:
                # Smoothed beta estimate. Negative outcomes lower tolerance.
                tolerance = (1.0 + counts["positive"] + 0.25 * max(0, total - counts["negative"] - counts["positive"])) / (2.0 + total)
            tolerance_by_hour[str(hour)] = round(max(0.0, min(1.0, tolerance)), 3)
        if all_total == 0:
            overall = 0.5
        else:
            overall = (1.0 + all_positive + 0.25 * max(0, all_total - all_negative - all_positive)) / (2.0 + all_total)
        overall = max(0.0, min(1.0, overall - min(0.25, 0.03 * streak)))
        evidence = [str(row.get("evidence_id")) for row in history]
        payload = {
            "interruption_tolerance_by_hour": tolerance_by_hour,
            "dismissal_streak": streak,
            "overall_tolerance": round(overall, 3),
            "sample_count": all_total,
            "negative_count": all_negative,
            "positive_count": all_positive,
            "window_days": window_days,
        }
        digest = hashlib.sha1(json.dumps({"obs": observation.observation_id, "payload": payload}, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        signal = SemanticSignal(
            signal_id=f"sig_interruption_tolerance_{digest}",
            user_scope_id=observation.user_scope_id,
            label="interruption_tolerance",
            statement="Estimated tolerance for proactive suggestions by hour from observed dismiss/accept behavior",
            kind="derived",
            created_by="estimator",
            evidence=evidence,
            evidence_window=_evidence_window(history),
            confidence=round(min(0.95, 0.35 + 0.05 * min(12, all_total)), 3),
            half_life_days=28,
            status="active" if all_total >= 3 else "proposed",
            activation={"actor": "default_policy", "surface": "signal_estimator", "at": now.isoformat()} if all_total >= 3 else {},
            estimator_version=self.version,
            payload=payload,
        )
        report = SignalEstimatorReport(
            report_id=f"estimator_report_{digest}",
            estimator_version=self.version,
            user_scope_id=observation.user_scope_id,
            input_streams=["action", "world"],
            input_hash=_input_hash({"notification_history": history, "observation_id": observation.observation_id}),
            coverage={"notification_history_rows": len(history), "window_days": window_days, "hours_observed": sum(1 for c in by_hour_counts.values() if c["total"] > 0)},
            output_signal_ids=[signal.signal_id],
            evidence=evidence,
            created_at=now,
        )
        return InterruptionToleranceOutput(signal=signal, report=report)


def estimate_interruption_tolerance(observation: RawCalendarObservation) -> InterruptionToleranceOutput:
    return InterruptionToleranceEstimator().estimate(observation)
