from __future__ import annotations

from collections import Counter
from typing import Any

from .predicates import evaluate_predicate


STATUSES = ("pass", "fail", "hold", "not_reached")
RAILS = ("preservation", "target_conformance")


def evaluate_scenario(spec: dict[str, Any], observable_vector: dict[str, Any]) -> dict[str, Any]:
    result = evaluate_predicate(str(spec["predicate_id"]), observable_vector)
    return {
        "status": result["status"],
        "summary": result["summary"],
        "predicate_evidence": result.get("evidence", {}),
    }


def summarize_rail(results: list[dict[str, Any]], rail: str) -> dict[str, Any]:
    rows = [row for row in results if row.get("rail") == rail]
    counts = Counter(str(row.get("status")) for row in rows)
    status_counts = {status: counts.get(status, 0) for status in STATUSES}
    unmet = [str(row["scenario_id"]) for row in rows if row.get("status") != "pass"]
    if not rows:
        blocking = [f"missing:{rail}"]
        decision = "hold"
        unmet = list(blocking)
    elif rail == "preservation":
        blocking = list(unmet)
        if status_counts["fail"]:
            decision = "fail"
        elif unmet:
            decision = "hold"
        else:
            decision = "pass"
    else:
        blocking = [
            str(row["scenario_id"])
            for row in rows
            if (
                row.get("gate_mode") == "required" and row.get("status") != "pass"
            ) or (
                row.get("gate_mode") == "observe" and row.get("status") in {"fail", "hold"}
            )
        ]
        if status_counts["fail"]:
            decision = "fail"
        elif status_counts["hold"]:
            decision = "hold"
        elif status_counts["not_reached"]:
            decision = "not_reached"
        else:
            decision = "pass"
    return {
        "decision": decision,
        "scenario_count": len(rows),
        "status_counts": status_counts,
        "blocking_scenario_ids": blocking,
        "unmet_scenario_ids": unmet,
    }


def derive_gate_decision(results: list[dict[str, Any]]) -> str:
    preservation = [row for row in results if row.get("rail") == "preservation"]
    target = [row for row in results if row.get("rail") == "target_conformance"]
    if not preservation or not target:
        return "hold"
    if any(row.get("status") == "fail" for row in preservation):
        return "fail"
    if any(row.get("status") != "pass" for row in preservation):
        return "hold"

    required_target = [row for row in target if row.get("gate_mode") == "required"]
    if any(row.get("status") == "fail" for row in required_target):
        return "fail"
    if any(row.get("status") != "pass" for row in required_target):
        return "hold"
    # A future target that has evidence and already contradicts the architecture
    # cannot be waved through as mere debt. Only observe-mode `not_reached` is
    # nonblocking before its documented trigger.
    if any(row.get("gate_mode") == "observe" and row.get("status") in {"fail", "hold"} for row in target):
        return "hold"
    return "pass"
