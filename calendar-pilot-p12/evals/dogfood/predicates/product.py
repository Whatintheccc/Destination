from __future__ import annotations

from typing import Any, Callable


ACTION_FIELDS = (
    "local_date", "timezone", "start", "end", "duration_minutes", "calendar_id",
    "title", "attendees", "affected_ids", "conflicts", "reversibility", "authority_need",
)
ZERO_EFFECT_FIELDS = ("provider_mutations", "effect_attempts", "stage_actions", "claims", "outbox_dispatches")


def _result(status: str, summary: str, *, evidence: dict[str, Any] | None = None, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": status, "summary": summary, "evidence": evidence or {}, "metrics": metrics or {}}


def _latest(vector: dict[str, Any], source: str) -> dict[str, Any]:
    rows = vector.get("records", {}).get(source, [])
    return dict(rows[-1]) if rows else {}


def _counts(vector: dict[str, Any]) -> dict[str, int]:
    counts = {field: 0 for field in ZERO_EFFECT_FIELDS}
    for rows in vector.get("records", {}).values():
        for row in rows:
            for field in ZERO_EFFECT_FIELDS:
                value = row.get(field)
                if isinstance(value, int):
                    counts[field] += value
    return counts


def _zero_effects(vector: dict[str, Any]) -> tuple[bool, dict[str, int]]:
    counts = _counts(vector)
    return all(counts[field] == 0 for field in ZERO_EFFECT_FIELDS), counts


def _equal_fields(left: dict[str, Any], right: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if field not in left or field not in right or left.get(field) != right.get(field)]


def _identity(vector: dict[str, Any]) -> dict[str, Any]:
    manifest = vector.get("manifest", {})
    launch = vector.get("launch_state", {})
    health = vector.get("health", {})
    snapshot = vector.get("process_snapshot", {}) or _latest(vector, "process_snapshot_before")
    expected_backends = manifest.get("runtime", {}).get("expected_backends", {})
    comparisons = {
        "run_id": manifest.get("run_id") == launch.get("run_id", manifest.get("run_id")),
        "run_dir": manifest.get("run_dir") == launch.get("run_dir"),
        "build_id_launch": manifest.get("build", {}).get("build_id") == launch.get("build_id"),
        "build_id_health": manifest.get("build", {}).get("build_id") == health.get("build_id"),
        "app_bundle": manifest.get("build", {}).get("app_bundle_path") == launch.get("app_bundle_path"),
        "runtime_launch": manifest.get("runtime", {}).get("requested_mode") == launch.get("runtime_mode"),
        "runtime_health": manifest.get("runtime", {}).get("requested_mode") == health.get("runtime_mode"),
        "backends": all(health.get("backends", {}).get(key) == value for key, value in expected_backends.items()),
        "pid": bool(launch.get("server_pid")) and launch.get("server_pid") == health.get("process", {}).get("server_pid") == snapshot.get("server_pid"),
        "port": bool(launch.get("port")) and launch.get("port") == health.get("process", {}).get("port") == snapshot.get("port"),
        "launch_id": bool(launch.get("launch_id")) and launch.get("launch_id") == health.get("process", {}).get("launch_id") == snapshot.get("launch_id"),
        "fresh_run": snapshot.get("ambient_attachment") is False,
        "artifact_run_ids": not vector.get("cross_run_artifacts"),
        "instrument_hashes": vector.get("instrument_hashes_valid") is True,
        "build_hashes": vector.get("build_hashes_valid") is True,
        "required_artifacts": not vector.get("missing_required_artifacts") and not vector.get("empty_required_artifacts"),
    }
    failures = sorted(key for key, ok in comparisons.items() if not ok)
    return _result("fail" if failures else "pass", "Run identity is incoherent." if failures else "Run identity and process ownership agree.", evidence={"comparisons": comparisons, "failures": failures, "missing_required_artifacts": vector.get("missing_required_artifacts", []), "empty_required_artifacts": vector.get("empty_required_artifacts", [])})


def _observe(vector: dict[str, Any]) -> dict[str, Any]:
    truth = {
        str(row.get("fact_id"))
        for row in vector.get("operator_truth", {}).get("facts", [])
        if row.get("kind") == "calendar_event"
    }
    provider = _latest(vector, "provider_read")
    rendered = _latest(vector, "rendered_view")
    provider_ids = {str(value) for value in provider.get("fact_ids", [])}
    visible_ids = {str(value) for value in rendered.get("fact_ids", [])}
    citation_ids = {str(value) for value in rendered.get("citation_ids", [])}
    zero, counts = _zero_effects(vector)
    ok = bool(truth) and provider_ids == truth == visible_ids and visible_ids.issubset(citation_ids) and not rendered.get("candidate_ids") and zero
    divergence = len(truth.symmetric_difference(visible_ids))
    return _result("pass" if ok else "fail", "Visible cited observation agrees with provider and operator truth." if ok else "Observation truth, citations, or no-effect ceiling diverged.", evidence={"truth_fact_ids": sorted(truth), "provider_fact_ids": sorted(provider_ids), "visible_fact_ids": sorted(visible_ids), "citation_ids": sorted(citation_ids), "effect_counts": counts}, metrics={"provider_truth_divergence": divergence, "effect_ceiling_divergence": sum(counts.values())})


def _recommend(vector: dict[str, Any]) -> dict[str, Any]:
    replay = _latest(vector, "replay")
    rendered = _latest(vector, "rendered_view")
    zero, counts = _zero_effects(vector)
    ok = bool(replay.get("candidate_id")) and replay.get("candidate_id") == rendered.get("candidate_id") and rendered.get("addresses_goal") is True and rendered.get("rationale_compares_noop") is True and zero
    return _result("pass" if ok else "fail", "Recommendation is relevant, compares no-op, and remains non-mutating." if ok else "Recommendation content or effect ceiling failed.", evidence={"candidate_id": replay.get("candidate_id"), "visible_candidate_id": rendered.get("candidate_id"), "effect_counts": counts}, metrics={"effect_ceiling_divergence": sum(counts.values())})


def _action_visible(vector: dict[str, Any]) -> dict[str, Any]:
    internal = _latest(vector, "replay").get("action", {})
    visible = _latest(vector, "rendered_view").get("action", {})
    mismatches = _equal_fields(internal, visible, ACTION_FIELDS)
    authentic_view = _latest(vector, "rendered_view").get("captured_from_ui") is True
    if not internal:
        mismatches.append("internal_action")
    if not authentic_view:
        mismatches.append("rendered_ui_capture")
    return _result("fail" if mismatches else "pass", "Rendered action is incomplete or differs from the internal candidate." if mismatches else "Rendered action completely and exactly projects the candidate.", evidence={"mismatched_fields": sorted(set(mismatches))}, metrics={"projection_divergence": len(set(mismatches))})


def _timezone(vector: dict[str, Any]) -> dict[str, Any]:
    row = _latest(vector, "rendered_view").get("timezone_check", {})
    checks = {name: row.get(name) is True for name in ("local_day_matches", "offset_roundtrip", "duration_preserved", "tomorrow_uses_bound_timezone", "dst_case_resolved")}
    failures = [name for name, ok in checks.items() if not ok]
    return _result("fail" if failures else "pass", "Local date/time conversion diverged." if failures else "Timezone, duration, tomorrow, and DST semantics round-trip.", evidence={"checks": checks, "failures": failures}, metrics={"projection_divergence": len(failures)})


def _followup(vector: dict[str, Any]) -> dict[str, Any]:
    row = _latest(vector, "replay").get("continuity", {})
    zero, counts = _zero_effects(vector)
    checks = {
        "plan": bool(row.get("before_plan_digest")) and row.get("before_plan_digest") == row.get("after_plan_digest"),
        "candidate": bool(row.get("before_candidate_digest")) and row.get("before_candidate_digest") == row.get("after_candidate_digest"),
        "action": bool(row.get("before_action_digest")) and row.get("before_action_digest") == row.get("after_action_digest"),
        "no_frontier_generation": row.get("frontier_generations", 1) == 0,
        "resolved_from_existing_evidence": row.get("resolved_from_existing_evidence") is True,
        "zero_effects": zero,
    }
    failures = [name for name, ok in checks.items() if not ok]
    return _result("fail" if failures else "pass", "Follow-up replanned or failed to resolve from existing evidence." if failures else "Follow-up preserves plan and candidate continuity.", evidence={"checks": checks, "effect_counts": counts}, metrics={"plan_continuity_violations": len(failures)})


def _correction(vector: dict[str, Any]) -> dict[str, Any]:
    row = _latest(vector, "replay").get("correction", {})
    checks = {"command_cited": bool(row.get("command_id")) and row.get("command_id") in row.get("citation_ids", []), "old_belief_inactive": row.get("old_belief_active") is False, "new_plan_uses_correction": row.get("new_plan_uses_correction") is True, "authority_unchanged": bool(row.get("before_authority_digest")) and row.get("before_authority_digest") == row.get("after_authority_digest")}
    failures = [name for name, ok in checks.items() if not ok]
    return _result("fail" if failures else "pass", "Correction did not replace the cited belief without changing authority." if failures else "Correction is cited and causally updates the plan only.", evidence={"checks": checks})


def _simulate(vector: dict[str, Any]) -> dict[str, Any]:
    preview = _latest(vector, "rendered_view").get("preview", {})
    zero, counts = _zero_effects(vector)
    required = ("action", "provider_result", "conflict_result", "uncertainty")
    missing = [field for field in required if field not in preview]
    if preview.get("admitted") is False and not preview.get("denial_or_hold_reason"):
        missing.append("denial_or_hold_reason")
    ok = not missing and zero
    return _result("pass" if ok else "fail", "Simulation is specific and non-mutating." if ok else "Simulation hid required preview fields or mutated state.", evidence={"missing_fields": missing, "effect_counts": counts}, metrics={"effect_ceiling_divergence": sum(counts.values())})


def _noop(vector: dict[str, Any]) -> dict[str, Any]:
    row = _latest(vector, "rendered_view")
    fixture_truth = any(
        fact.get("kind") == "fixture_truth"
        and fact.get("value", {}).get("fixture_id") == "noop_dominates"
        and fact.get("value", {}).get("noop_dominates") is True
        for fact in vector.get("operator_truth", {}).get("facts", [])
    )
    ok = fixture_truth and row.get("winner") == "no_op" and bool(row.get("binding_constraint")) and row.get("write_controls_visible") is False
    return _result("pass" if ok else "fail", "Dominated fixture selects and explains no-op." if ok else "No-op did not win cleanly or the UI still implied a write.", evidence={"fixture_truth": fixture_truth, "winner": row.get("winner"), "binding_constraint": row.get("binding_constraint"), "write_controls_visible": row.get("write_controls_visible")})


def _denial(vector: dict[str, Any]) -> dict[str, Any]:
    row = _latest(vector, "rendered_view").get("denial", {})
    zero, counts = _zero_effects(vector)
    ok = all(bool(row.get(field)) for field in ("owner", "reason", "repair")) and row.get("specific") is True and zero
    return _result("pass" if ok else "fail", "Denial is specific, repairable, and non-mutating." if ok else "Denial ownership, specificity, repair path, or no-effect contract failed.", evidence={"denial": row, "effect_counts": counts}, metrics={"effect_ceiling_divergence": sum(counts.values())})


def _feedback(vector: dict[str, Any]) -> dict[str, Any]:
    exposure = _latest(vector, "rendered_view").get("exposure", {})
    outcome = _latest(vector, "replay").get("outcome", {})
    ok = bool(exposure.get("exposure_id")) and exposure.get("candidate_id") == outcome.get("candidate_id") and exposure.get("exposure_id") == outcome.get("exposure_id") and outcome.get("terminal_count") == 1 and outcome.get("decision_id") == exposure.get("decision_id")
    return _result("pass" if ok else "fail", "Feedback is linked to exactly one rendered exposure." if ok else "Feedback targeted an unrendered/wrong candidate or has conflicting terminal outcomes.", evidence={"exposure": exposure, "outcome": outcome})


def _restart(vector: dict[str, Any]) -> dict[str, Any]:
    row = _latest(vector, "replay").get("restart", {})
    digest_fields = ("conversation", "plan", "candidate", "receipt", "outcome", "runtime", "replay")
    mismatches = [field for field in digest_fields if not row.get(f"before_{field}_digest") or row.get(f"before_{field}_digest") != row.get(f"after_{field}_digest")]
    duplicates = int(row.get("duplicate_tool_calls", 1)) + int(row.get("duplicate_effects", 1))
    ok = not mismatches and duplicates == 0
    return _result("pass" if ok else "fail", "Restart restores causal state without duplicate work." if ok else "Restart state diverged or duplicated tool/effect work.", evidence={"mismatched_digests": mismatches, "duplicate_count": duplicates}, metrics={"plan_continuity_violations": len(mismatches) + duplicates})


def _live_read(vector: dict[str, Any]) -> dict[str, Any]:
    truth = vector.get("operator_truth", {})
    provider = _latest(vector, "provider_read")
    rendered = _latest(vector, "rendered_view")
    truth_ids = {str(row.get("fact_id")) for row in truth.get("facts", [])}
    provider_ids = {str(value) for value in provider.get("fact_ids", [])}
    visible_ids = {str(value) for value in rendered.get("fact_ids", [])}
    health = vector.get("health", {})
    provider_ok = health.get("backends", {}).get("provider") == "apple_eventkit" and provider.get("provider_identity") == "apple_eventkit" and truth.get("provider_identity") == "apple_eventkit"
    fixture_free = provider.get("uses_sample_fixtures") is False and not provider.get("fixture_rows")
    ok = bool(truth_ids) and truth_ids == provider_ids == visible_ids and provider_ok and fixture_free and provider.get("permission_owner") == "app"
    divergence = len(truth_ids.symmetric_difference(provider_ids)) + len(truth_ids.symmetric_difference(visible_ids))
    return _result("pass" if ok else "fail", "Live provider read agrees with operator truth and contains no fixture leakage." if ok else "Provider identity, permission ownership, truth, or fixture isolation diverged.", evidence={"truth_fact_ids": sorted(truth_ids), "provider_fact_ids": sorted(provider_ids), "visible_fact_ids": sorted(visible_ids), "provider_ok": provider_ok, "fixture_free": fixture_free}, metrics={"provider_truth_divergence": divergence + (0 if provider_ok and fixture_free else 1)})


def _effect(vector: dict[str, Any]) -> dict[str, Any]:
    row = _latest(vector, "replay").get("effect", {})
    expected = {"tickets": 1, "claims": 1, "dispatches": 1, "provider_mutations": 1, "verify_count": 1}
    counts_ok = all(row.get(key) == value for key, value in expected.items())
    ids = [row.get(name) for name in ("ticket_external_id", "provider_external_id", "verify_external_id", "receipt_external_id")]
    ids_ok = bool(ids[0]) and len(set(ids)) == 1
    binding_ok = row.get("target_binding") == row.get("expected_binding") and bool(row.get("expected_binding"))
    ok = counts_ok and ids_ok and binding_ok and row.get("receipt_status") == "committed" and row.get("has_attendees") is False and row.get("action_family") == "create_prep_block" and row.get("legacy_owner_mutations", 1) == 0
    return _result("pass" if ok else "fail", "One exact bound effect was claimed, applied, verified, and receipted." if ok else "Effect cardinality, binding, readback, ownership, or receipt truth failed.", evidence={"expected_counts": expected, "observed": row, "external_ids_equal": ids_ok, "binding_equal": binding_ok}, metrics={"effect_ceiling_divergence": 0 if counts_ok else 1, "provider_truth_divergence": 0 if ids_ok else 1})


def _undo(vector: dict[str, Any]) -> dict[str, Any]:
    row = _latest(vector, "replay").get("undo", {})
    ids = [row.get("committed_external_id"), row.get("remove_external_id"), row.get("absence_external_id")]
    ids_ok = bool(ids[0]) and len(set(ids)) == 1
    ok = row.get("separate_compensation_authority") is True and row.get("remove_count") == 1 and ids_ok and row.get("verified_absent") is True and row.get("audit_retained") is True and row.get("restart_redispatch_count") == 0
    return _result("pass" if ok else "fail", "Compensation is separately authorized, exact, verified absent, and restart-safe." if ok else "Undo authority, target identity, verification, audit, or restart safety failed.", evidence={"undo": row, "external_ids_equal": ids_ok}, metrics={"effect_ceiling_divergence": 0 if row.get("remove_count") == 1 else 1, "provider_truth_divergence": 0 if ids_ok and row.get("verified_absent") is True else 1})


PREDICATES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "identity": _identity, "observe": _observe, "recommend": _recommend,
    "action_visible": _action_visible, "timezone": _timezone, "followup": _followup,
    "correction": _correction, "simulate": _simulate, "noop": _noop, "denial": _denial,
    "feedback": _feedback, "restart": _restart, "live_read": _live_read,
    "effect": _effect, "undo": _undo,
}


def evaluate_predicate(predicate_id: str, vector: dict[str, Any]) -> dict[str, Any]:
    if predicate_id not in PREDICATES:
        raise KeyError(f"unknown dogfood predicate: {predicate_id}")
    prerequisite = vector.get("external_prerequisite", {})
    if prerequisite.get("available") is False:
        status = "hold" if prerequisite.get("external") is True else "fail"
        return _result(status, str(prerequisite.get("reason") or "Required prerequisite is unavailable."), evidence={"prerequisite": prerequisite})
    if predicate_id != "identity" and vector.get("scenario_record_count", 0) == 0:
        return _result("not_reached", "Scenario was not executed.")
    missing_sources = sorted(set(vector.get("required_sources", [])) - set(vector.get("present_sources", [])))
    if missing_sources:
        return _result("fail", "Executed scenario is missing required independent evidence.", evidence={"missing_sources": missing_sources})
    return PREDICATES[predicate_id](vector)
