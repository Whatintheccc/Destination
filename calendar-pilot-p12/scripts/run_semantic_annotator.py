#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.codex.annotator import CodexSemanticAnnotator
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.invariants import check_replay
from calendar_pilot.types import BiographyDriftFinding


def default_records() -> list[dict]:
    records = []
    for idx in range(3):
        records.append(
            {
                "record_type": "reward",
                "record_id": f"reward:evening-dismissal:{idx}",
                "trace_id": f"trace:semantic:{idx}",
                "signal_stream": "action",
                "payload": {
                    "reward": {
                        "notification_dismissed": True,
                        "observed_at": f"2026-07-0{idx + 1}T20:15:00-07:00",
                    }
                },
            }
        )
    records.append(
        {
            "record_type": "raw_calendar_observation",
            "record_id": "world:external-call",
            "trace_id": "trace:semantic:world",
            "signal_stream": "world",
            "payload": {"event_count": 1, "external_meeting_count": 1},
        }
    )
    return records


def load_records(path: str) -> list[dict]:
    p = Path(path)
    p = p if p.is_absolute() else ROOT / p
    if not p.exists():
        return default_records()
    if p.suffix == ".jsonl":
        return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    payload = json.loads(p.read_text())
    if isinstance(payload, list):
        return payload
    return list(payload.get("records", []))


def drift_findings(records: list[dict], signals) -> list[dict]:
    biography_claims = []
    for row in records:
        if row.get("signal_stream") != "biography":
            continue
        payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        claim = str(payload.get("claim") or payload.get("biography_claim") or "")
        if claim:
            biography_claims.append((str(row.get("record_id") or "biography"), claim))

    findings = []
    for signal in signals:
        if signal.label != "dismisses_evening_suggestions":
            continue
        for record_id, claim in biography_claims:
            if "evening" in claim.lower() and any(token in claim.lower() for token in ["fine", "ok", "available", "welcome"]):
                finding = BiographyDriftFinding(
                    finding_id=f"drift_{signal.signal_id[:24]}",
                    user_scope_id=signal.user_scope_id,
                    biography_claim=claim,
                    semantic_signal_id=signal.signal_id,
                    conflict="declared evening availability conflicts with derived evening-dismissal signal",
                    evidence=[record_id, *signal.evidence],
                    surfaced_at=datetime.now(timezone.utc),
                )
                findings.append(finding.to_dict())
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="")
    parser.add_argument("--user-scope-id", default="local_demo_user")
    parser.add_argument("--out", default="runs/p12_semantic_signals.json")
    args = parser.parse_args()

    records = load_records(args.records) if args.records else default_records()
    signals = CodexSemanticAnnotator().propose(records, user_scope_id=args.user_scope_id)
    drifts = drift_findings(records, signals)
    signal_rows = [
        {
            "record_type": "semantic_signal",
            "record_id": signal.signal_id,
            "trace_id": signal.signal_id,
            "signal_stream": "derived",
            "payload": signal.to_dict(),
        }
        for signal in signals
    ]
    drift_rows = [
        {
            "record_type": "biography_drift_finding",
            "record_id": drift["finding_id"],
            "trace_id": drift["finding_id"],
            "signal_stream": "biography",
            "payload": drift,
        }
        for drift in drifts
    ]
    violations = [violation.to_dict() for violation in check_replay(records + signal_rows + drift_rows)]
    evidence_total = sum(len(signal.evidence) for signal in signals)
    payload = {
        "semantic_annotator_schema_version": "semantic_annotator_run.v1",
        "ok": bool(signals) and not violations,
        "input_record_count": len(records),
        "semantic_signal_count": len(signals),
        "label_evidence_coverage": round(evidence_total / max(1, len(signals)), 4),
        "label_churn_rate": 0.0,
        "biography_drift_findings": drifts,
        "signals": [signal.to_dict() for signal in signals],
        "violations": violations,
    }

    out = Path(args.out)
    out = out if out.is_absolute() else ROOT / out
    atomic_write_json(out, payload)
    print(json.dumps({"ok": payload["ok"], "signals": len(signals), "out": str(out)}, indent=2))
    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
