#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.signal_streams import infer_signal_stream


REAL_PROVENANCES = {"human_ui", "dogfood_shadow", "provider_observed"}
POSITIVE_FEEDBACK = {"accepted", "accept", "useful", "helpful"}
NEGATIVE_FEEDBACK = {"wrong", "not_needed", "too_interruptive", "downstream_conflict", "ignored"}


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _read_rows(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                malformed.append({"path": str(path), "line_no": line_no, "error": str(exc)})
                continue
            row["_source_path"] = str(path)
            row["_source_line_no"] = line_no
            rows.append(row)
    return rows, malformed


def _reward_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    reward = payload.get("reward")
    return reward if isinstance(reward, dict) else {}


def _feedback_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    feedback = payload.get("feedback_event")
    return feedback if isinstance(feedback, dict) else {}


def _candidate_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = payload.get("candidate")
    return candidate if isinstance(candidate, dict) else {}


def _receipt_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    receipt = payload.get("receipt")
    return receipt if isinstance(receipt, dict) else {}


def _feedback_value(reward: dict[str, Any], feedback_event: dict[str, Any]) -> str:
    raw = str(feedback_event.get("feedback") or "").strip().lower().replace("-", "_")
    if raw:
        return raw
    if reward.get("accepted") is True:
        return "accepted"
    if reward.get("explicit_useful") is True:
        return "useful"
    if reward.get("explicit_wrong") is True:
        return "wrong"
    if reward.get("explicit_not_needed") is True:
        return "not_needed"
    if reward.get("notification_dismissed") is True:
        return "too_interruptive"
    if reward.get("downstream_conflict") is True:
        return "downstream_conflict"
    if reward.get("ignored") is True:
        return "ignored"
    return ""


def _observed_acceptance(reward: dict[str, Any], feedback_value: str) -> bool | None:
    if reward.get("accepted") is True or reward.get("explicit_useful") is True:
        return True
    if reward.get("explicit_wrong") is True or reward.get("explicit_not_needed") is True:
        return False
    if reward.get("notification_dismissed") is True or reward.get("downstream_conflict") is True:
        return False
    if reward.get("ignored") is True:
        return False
    if feedback_value in POSITIVE_FEEDBACK:
        return True
    if feedback_value in NEGATIVE_FEEDBACK:
        return False
    return None


def _observed_undo(reward: dict[str, Any], receipt: dict[str, Any], feedback_value: str) -> bool:
    return bool(
        reward.get("undone") is True
        or receipt.get("sync_status") == "reverted"
        or feedback_value in {"undo", "undone", "reverted"}
    )


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _round_gap(observed: float | None, predicted: float | None) -> float | None:
    if observed is None or predicted is None:
        return None
    return round(observed - predicted, 4)


def _source_label(provenances: set[str], explicit_dogfood_shadow: bool) -> str:
    if "human_ui" in provenances:
        return "human_feedback"
    if "provider_observed" in provenances:
        return "provider_observed"
    if "dogfood_shadow" in provenances or explicit_dogfood_shadow:
        return "dogfood_shadow"
    return "fixture"


def _merge_example(examples: dict[str, dict[str, Any]], key: str, update: dict[str, Any]) -> None:
    current = examples.setdefault(key, {"row_ids": [], "source_rows": []})
    for field in ("candidate", "receipt", "reward", "feedback_event", "feedback_value", "provenance"):
        value = update.get(field)
        if value not in (None, {}, ""):
            current[field] = value
    current["row_ids"].extend(update.get("row_ids", []))
    current["source_rows"].extend(update.get("source_rows", []))


def _matched_examples(rows: list[dict[str, Any]], *, family: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    examples: dict[str, dict[str, Any]] = {}
    skipped: list[dict[str, Any]] = []
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        record_type = str(row.get("record_type") or "")
        stream = str(row.get("signal_stream") or infer_signal_stream(record_type, payload))
        row_id = str(row.get("record_id") or f"{record_type}:{row.get('_source_line_no', 0)}")
        if stream != "action":
            continue
        if record_type not in {"reward", "human_feedback_event", "candidate_receipt"}:
            continue
        candidate = _candidate_from_payload(payload)
        if family and candidate.get("intent") != family:
            skipped.append({"record_id": row_id, "reason": "intent_mismatch", "intent": candidate.get("intent")})
            continue
        reward = _reward_from_payload(payload)
        feedback_event = _feedback_from_payload(payload)
        feedback_value = _feedback_value(reward, feedback_event)
        provenance = str(reward.get("provenance") or feedback_event.get("provenance") or "human_ui")
        if provenance not in REAL_PROVENANCES:
            skipped.append({"record_id": row_id, "reason": "non_real_provenance", "provenance": provenance})
            continue
        if not candidate:
            skipped.append({"record_id": row_id, "reason": "missing_candidate"})
            continue
        reward_event_id = str(reward.get("reward_event_id") or feedback_event.get("reward_event_id") or row_id)
        key = reward_event_id or row_id
        _merge_example(
            examples,
            key,
            {
                "candidate": candidate,
                "receipt": _receipt_from_payload(payload),
                "reward": reward,
                "feedback_event": feedback_event,
                "feedback_value": feedback_value,
                "provenance": provenance,
                "row_ids": [row_id],
                "source_rows": [{"path": row.get("_source_path"), "line_no": row.get("_source_line_no"), "record_id": row_id}],
            },
        )
    output: list[dict[str, Any]] = []
    for key, example in sorted(examples.items()):
        reward = example.get("reward", {})
        receipt = example.get("receipt", {})
        feedback_value = str(example.get("feedback_value") or "")
        observed = _observed_acceptance(reward, feedback_value)
        if observed is None and not _observed_undo(reward, receipt, feedback_value):
            skipped.append({"record_id": ",".join(example.get("row_ids", [])), "reason": "no_observed_outcome"})
            continue
        candidate = example.get("candidate", {})
        output.append({
            "example_id": key,
            "row_ids": sorted(set(str(x) for x in example.get("row_ids", []))),
            "source_rows": example.get("source_rows", []),
            "candidate_id": candidate.get("candidate_id"),
            "family": candidate.get("intent"),
            "feedback": feedback_value,
            "provenance": example.get("provenance", "human_ui"),
            "observed_acceptance": observed,
            "predicted_acceptance": _float(candidate.get("predicted_acceptance")),
            "observed_undo": _observed_undo(reward, receipt, feedback_value),
            "predicted_undo": _float(candidate.get("predicted_regret")),
        })
    return output, skipped


def build_report(
    *,
    replay_paths: list[Path] | None = None,
    family: str = "",
    sim_batch: str = "",
    dogfood_shadow: str = "",
) -> dict[str, Any]:
    paths = replay_paths or []
    rows, malformed = _read_rows(paths)
    examples, skipped = _matched_examples(rows, family=family)
    accepted = [1.0 if ex["observed_acceptance"] else 0.0 for ex in examples if ex["observed_acceptance"] is not None]
    predicted_acceptance = [float(ex["predicted_acceptance"]) for ex in examples if ex["observed_acceptance"] is not None]
    undone = [1.0 if ex["observed_undo"] else 0.0 for ex in examples]
    predicted_undo = [float(ex["predicted_undo"]) for ex in examples]
    observed_acceptance_rate = _mean(accepted)
    predicted_acceptance_mean = _mean(predicted_acceptance)
    observed_undo_rate = _mean(undone)
    predicted_undo_mean = _mean(predicted_undo)
    acceptance_gap = _round_gap(observed_acceptance_rate, predicted_acceptance_mean)
    undo_gap = _round_gap(observed_undo_rate, predicted_undo_mean)
    decision = "pass" if examples and acceptance_gap is not None and undo_gap is not None and not malformed else "hold"
    known_biases: list[str] = []
    if not examples:
        known_biases.append("insufficient matched real examples")
    elif len(examples) < 10:
        known_biases.append("low matched real example count; do not use alone for autonomy promotion")
    if malformed:
        known_biases.append("malformed replay rows were skipped")
    provenances = {str(ex.get("provenance") or "") for ex in examples}
    family_key = family or "all"
    family_metrics = {
        family_key: {
            "matched_examples": len(examples),
            "observed_acceptance_rate": observed_acceptance_rate,
            "predicted_acceptance_mean": predicted_acceptance_mean,
            "acceptance_gap": acceptance_gap,
            "observed_undo_rate": observed_undo_rate,
            "predicted_undo_rate": predicted_undo_mean,
            "undo_gap": undo_gap,
            "decision": decision,
        }
    }
    return {
        "calibration_schema_version": "calibration_report.v1",
        "run_id": sim_batch or "p12_calibration",
        "policy_tuning_id": "CURRENT",
        "simulator_version": "sim_v2.1",
        "estimator_versions": ["interruption_tolerance_v1"],
        "real_source": _source_label(provenances, bool(dogfood_shadow)),
        "matched_examples": len(examples),
        "source_replays": [str(p) for p in paths],
        "matched_record_ids": sorted({row_id for ex in examples for row_id in ex["row_ids"]}),
        "matched_examples_detail": examples,
        "skipped_rows": skipped[:50],
        "malformed_rows": malformed,
        "action_family_metrics": family_metrics,
        "overall_acceptance_gap": acceptance_gap,
        "overall_undo_gap": undo_gap,
        "estimator_calibration_gap": undo_gap,
        "known_biases": known_biases,
        "decision": decision,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim-batch", default="")
    parser.add_argument("--dogfood-shadow", default="")
    parser.add_argument("--family", default="")
    parser.add_argument("--replay", action="append", default=None)
    parser.add_argument("--out", default="runs/p12_calibration_report.json")
    args = parser.parse_args()
    replay_paths = [_resolve(p) for p in (args.replay or [])]
    payload = build_report(
        replay_paths=replay_paths,
        family=args.family.strip(),
        sim_batch=args.sim_batch,
        dogfood_shadow=args.dogfood_shadow,
    )
    out = _resolve(args.out)
    atomic_write_json(out, payload)
    print(json.dumps({"ok": payload["decision"] == "pass", "decision": payload["decision"], "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
