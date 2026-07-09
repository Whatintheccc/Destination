from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any, Callable


PredicateResult = dict[str, Any]
Predicate = Callable[[dict[str, Any]], PredicateResult]


def _result(status: str, summary: str, **evidence: Any) -> PredicateResult:
    if status not in {"pass", "fail", "hold", "not_reached"}:
        raise ValueError(f"unsupported architecture-eval status: {status}")
    return {"status": status, "summary": summary, "evidence": evidence}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_artifact(value: Any) -> tuple[bool, dict[str, Any]]:
    artifact = _as_dict(value)
    raw_path = artifact.get("path")
    expected_sha = artifact.get("sha256")
    if not isinstance(raw_path, str) or not raw_path or not isinstance(expected_sha, str):
        return False, {"path": raw_path, "expected_sha256": expected_sha, "reason": "missing_path_or_sha256"}
    path = Path(raw_path)
    if not path.is_file():
        return False, {"path": raw_path, "expected_sha256": expected_sha, "reason": "artifact_missing"}
    actual_sha = _sha256(path)
    return actual_sha == expected_sha, {
        "path": raw_path,
        "expected_sha256": expected_sha,
        "actual_sha256": actual_sha,
        "reason": None if actual_sha == expected_sha else "sha256_mismatch",
    }


def _valid_measurement(value: Any, *, allowed_units: set[str] | None = None) -> bool:
    measurement = _as_dict(value)
    status = measurement.get("status")
    unit = measurement.get("unit")
    if not isinstance(unit, str) or not unit or (allowed_units is not None and unit not in allowed_units):
        return False
    if status == "unknown":
        return isinstance(measurement.get("reason"), str) and bool(measurement.get("reason"))
    if status != "measured":
        return False
    numeric = measurement.get("value")
    return isinstance(numeric, (int, float)) and not isinstance(numeric, bool) and numeric >= 0


def _valid_frontier_field(field: str, value: Any) -> bool:
    if field == "respondent":
        return isinstance(value, str) and bool(value)
    if field == "provenance":
        return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)
    if field == "validation_errors":
        return isinstance(value, list) and all(isinstance(item, str) and item for item in value)
    if field == "failure_mode":
        if isinstance(value, str):
            return bool(value)
        unknown = _as_dict(value)
        return unknown.get("status") == "unknown" and isinstance(unknown.get("reason"), str) and bool(unknown.get("reason"))
    if field == "latency":
        return _valid_measurement(value, allowed_units={"ms"})
    if field == "cost":
        return _valid_measurement(value, allowed_units={"usd"})
    if field == "variance":
        measurement = _as_dict(value)
        if not _valid_measurement(measurement):
            return False
        if measurement.get("status") == "unknown":
            return True
        return (
            isinstance(measurement.get("metric"), str)
            and bool(measurement.get("metric"))
            and isinstance(measurement.get("sample_count"), int)
            and measurement.get("sample_count") >= 1
        )
    return False


def frontier_provenance(vector: dict[str, Any]) -> PredicateResult:
    frontier = _as_dict(vector.get("frontier"))
    candidate_ids = {str(value) for value in _as_list(frontier.get("candidate_ids")) if value}
    respondent = str(frontier.get("respondent") or "")
    provenance = _as_dict(frontier.get("provenance"))
    generation_rows = [row for row in _as_list(frontier.get("generation_rows")) if isinstance(row, dict)]
    decision_rows = [row for row in _as_list(frontier.get("decision_rows")) if isinstance(row, dict)]
    decision_by_candidate = {
        str(row.get("candidate_id")): row
        for row in decision_rows
        if row.get("candidate_id") and row.get("row_id") and row.get("trace_id")
    }
    missing_candidates = sorted(candidate_ids - set(decision_by_candidate))
    backend_matches = bool(respondent) and provenance.get("policy_backend") == respondent
    generation_cites_rows = all(row.get("row_id") and row.get("trace_id") for row in generation_rows)
    if not candidate_ids or not respondent or not generation_rows:
        return _result(
            "hold",
            "Frontier provenance cannot be graded without candidates, a respondent, and trajectory rows.",
            candidate_count=len(candidate_ids),
            respondent=respondent,
            generation_row_count=len(generation_rows),
        )
    if missing_candidates or not backend_matches or not generation_cites_rows:
        return _result(
            "fail",
            "Candidate provenance was lost between frontier generation and trajectory rows.",
            missing_candidate_rows=missing_candidates,
            respondent=respondent,
            provenance_backend=provenance.get("policy_backend"),
            generation_rows_cited=generation_cites_rows,
        )
    return _result(
        "pass",
        "Every visible candidate is tied to respondent provenance and a trajectory decision row.",
        candidate_ids=sorted(candidate_ids),
        respondent=respondent,
        generation_row_ids=[row["row_id"] for row in generation_rows],
        decision_row_ids=sorted(str(row["row_id"]) for row in decision_rows),
    )


def belief_cannot_authorize(vector: dict[str, Any]) -> PredicateResult:
    belief = _as_dict(vector.get("belief"))
    attempt = _as_dict(vector.get("authority_attempt"))
    provider = _as_dict(vector.get("provider"))
    evidence_ids = [str(value) for value in _as_list(belief.get("evidence_row_ids")) if value]
    receipt_rows = [str(value) for value in _as_list(attempt.get("receipt_row_ids")) if value]
    denial = str(attempt.get("denied_reason") or "").lower()
    attempted_belief = attempt.get("embedded_belief_id") == belief.get("belief_id")
    no_grant = attempt.get("grant_id") in {None, ""}
    state_unchanged = bool(provider.get("before_state_hash")) and provider.get("before_state_hash") == provider.get("after_state_hash")
    if not evidence_ids or not receipt_rows:
        return _result(
            "hold",
            "The authority wall needs cited belief evidence and a replay-visible attempt receipt.",
            belief_evidence_row_ids=evidence_ids,
            receipt_row_ids=receipt_rows,
        )
    if not (
        attempted_belief
        and no_grant
        and attempt.get("outcome") == "denied"
        and "authority grant" in denial
        and state_unchanged
    ):
        return _result(
            "fail",
            "A belief-bearing request was not proven to fail closed without provider mutation.",
            attempted_belief=attempted_belief,
            grant_id=attempt.get("grant_id"),
            outcome=attempt.get("outcome"),
            denied_reason=attempt.get("denied_reason"),
            provider_state_unchanged=state_unchanged,
        )
    return _result(
        "pass",
        "The cited belief did not mint authority; the request was denied and provider state did not change.",
        belief_id=belief.get("belief_id"),
        evidence_row_ids=evidence_ids,
        denial_receipt_row_ids=receipt_rows,
        provider_state_hash=provider.get("before_state_hash"),
    )


def expired_authority_denied(vector: dict[str, Any]) -> PredicateResult:
    attempt = _as_dict(vector.get("authority_attempt"))
    provider = _as_dict(vector.get("provider"))
    expires_at = _iso(attempt.get("expires_at"))
    evaluated_at = _iso(attempt.get("evaluated_at"))
    if expires_at is None or evaluated_at is None:
        return _result("hold", "The stale-authority scenario lacks parseable expiry evidence.")
    genuinely_stale = evaluated_at > expires_at
    state_unchanged = bool(provider.get("before_state_hash")) and provider.get("before_state_hash") == provider.get("after_state_hash")
    denied_for_expiry = attempt.get("outcome") == "denied" and "expired" in str(attempt.get("denied_reason") or "").lower()
    if not (genuinely_stale and denied_for_expiry and state_unchanged and attempt.get("receipt_row_id")):
        return _result(
            "fail",
            "Expired authority was not proven to deny safely.",
            genuinely_stale=genuinely_stale,
            outcome=attempt.get("outcome"),
            denied_reason=attempt.get("denied_reason"),
            provider_state_unchanged=state_unchanged,
            receipt_row_id=attempt.get("receipt_row_id"),
        )
    return _result(
        "pass",
        "An expired grant was denied with a replay receipt and no provider mutation.",
        grant_id=attempt.get("grant_id"),
        expires_at=attempt.get("expires_at"),
        evaluated_at=attempt.get("evaluated_at"),
        receipt_row_id=attempt.get("receipt_row_id"),
    )


def missing_evidence_rejected(vector: dict[str, Any]) -> PredicateResult:
    belief_input = _as_dict(vector.get("belief_input"))
    construction = _as_dict(vector.get("construction"))
    evidence_ids = [value for value in _as_list(belief_input.get("evidence_row_ids")) if value]
    exception_type = str(construction.get("exception_type") or "")
    message = str(construction.get("message") or "").lower()
    object_payload = construction.get("object_payload")
    if evidence_ids:
        return _result("hold", "The planted missing-evidence input was not actually missing evidence.", evidence_row_ids=evidence_ids)
    if object_payload is not None and object_payload != "":
        return _result("fail", "An uncited belief was constructible.", object_payload=object_payload)
    if exception_type != "ValueError" or "evidence" not in message:
        return _result(
            "fail",
            "Missing belief evidence did not produce an evidence-specific rejection.",
            exception_type=exception_type,
            message=construction.get("message"),
        )
    return _result(
        "pass",
        "Belief construction rejected an empty evidence set.",
        exception_type=exception_type,
        message=construction.get("message"),
    )


def reward_actionstream_only(vector: dict[str, Any]) -> PredicateResult:
    reward = _as_dict(vector.get("reward"))
    input_rows = [row for row in _as_list(reward.get("input_rows")) if isinstance(row, dict)]
    consumed_rows = [row for row in _as_list(reward.get("consumed_rows")) if isinstance(row, dict)]
    inputs_by_identity = {
        (str(row.get("source_artifact")), str(row.get("row_id"))): row
        for row in input_rows
        if row.get("source_artifact") and row.get("row_id")
    }
    identities = [
        (str(row.get("source_artifact")), str(row.get("row_id")))
        for row in consumed_rows
        if row.get("source_artifact") and row.get("row_id")
    ]
    if not consumed_rows:
        return _result("hold", "Reward reduction consumed no evidence rows.", input_row_count=len(input_rows))
    missing_identity_rows = [
        row
        for row in consumed_rows
        if not row.get("source_artifact") or not row.get("row_id")
    ]
    missing_inputs = [identity for identity in identities if identity not in inputs_by_identity]
    duplicate_identities = len(identities) != len(set(identities))
    impure = [
        row
        for row in consumed_rows
        if row.get("stream") != "action" or row.get("record_type") != "reward"
    ]
    missing_provenance = [row.get("row_id") for row in consumed_rows if not row.get("provenance")]
    if missing_identity_rows or missing_inputs or duplicate_identities or impure or missing_provenance:
        return _result(
            "fail",
            "Reward reduction consumed missing, duplicated, unprovenanced, or non-ActionStream rows.",
            rows_missing_identity=missing_identity_rows,
            missing_input_identities=missing_inputs,
            duplicate_identities=duplicate_identities,
            impure_rows=impure,
            rows_missing_provenance=missing_provenance,
        )
    return _result(
        "pass",
        "Reward reduction consumed uniquely identified ActionStream reward rows only.",
        consumed_identities=[list(identity) for identity in identities],
        provenances=sorted({str(row["provenance"]) for row in consumed_rows}),
    )


def provider_transaction(vector: dict[str, Any]) -> PredicateResult:
    provider = _as_dict(vector.get("provider"))
    operations = [row for row in _as_list(provider.get("operations")) if isinstance(row, dict)]
    by_operation = {str(row.get("operation")): row for row in operations if row.get("operation")}
    commit = by_operation.get("commit", {})
    verify = by_operation.get("verify", {})
    state_changed = bool(provider.get("before_state_hash")) and provider.get("before_state_hash") != provider.get("after_state_hash")
    common_trace = bool(commit.get("trace_id")) and commit.get("trace_id") == verify.get("trace_id")
    if not operations or not provider.get("rollback_handle_id"):
        return _result(
            "hold",
            "Provider transaction evidence is incomplete.",
            operation_names=sorted(by_operation),
            rollback_handle_id=provider.get("rollback_handle_id"),
        )
    valid = (
        provider.get("outcome") == "committed"
        and commit.get("status") in {"materialized", "idempotent_replay"}
        and verify.get("status") == "verified"
        and bool(verify.get("local_time_echo_ok"))
        and bool(provider.get("external_ids"))
        and state_changed
        and common_trace
        and commit.get("row_id")
        and verify.get("row_id")
    )
    if not valid:
        return _result(
            "fail",
            "Commit and verify did not form one observable provider transaction.",
            outcome=provider.get("outcome"),
            commit=commit,
            verify=verify,
            state_changed=state_changed,
            common_trace=common_trace,
        )
    return _result(
        "pass",
        "Provider commit changed calendar state and was verified in the same trace with a rollback handle.",
        commit_row_id=commit.get("row_id"),
        verify_row_id=verify.get("row_id"),
        rollback_handle_id=provider.get("rollback_handle_id"),
        external_ids=provider.get("external_ids"),
    )


def provider_conflict_denial(vector: dict[str, Any]) -> PredicateResult:
    provider = _as_dict(vector.get("provider"))
    unchanged = bool(provider.get("before_conflict_hash")) and provider.get("before_conflict_hash") == provider.get("after_conflict_hash")
    denial_rows = [value for value in _as_list(provider.get("denial_row_ids")) if value]
    safe = (
        provider.get("first_outcome") == "committed"
        and provider.get("conflict_outcome") == "denied"
        and provider.get("denied_reason") == "provider_conflict_detected"
        and bool(provider.get("conflict_truth"))
        and unchanged
        and bool(denial_rows)
    )
    if not provider.get("before_conflict_hash") or not denial_rows:
        return _result("hold", "Conflict denial lacks state hashes or a replay receipt.")
    if not safe:
        return _result(
            "fail",
            "Provider conflict truth did not fail closed without a second mutation.",
            first_outcome=provider.get("first_outcome"),
            conflict_outcome=provider.get("conflict_outcome"),
            denied_reason=provider.get("denied_reason"),
            conflict_truth=provider.get("conflict_truth"),
            provider_state_unchanged=unchanged,
        )
    return _result(
        "pass",
        "A live provider conflict produced a cited denial and left calendar state unchanged.",
        denial_row_ids=denial_rows,
        conflict_count=len(_as_list(provider.get("conflict_truth"))),
        provider_state_hash=provider.get("after_conflict_hash"),
    )


def rollback_effective(vector: dict[str, Any]) -> PredicateResult:
    provider = _as_dict(vector.get("provider"))
    operations = [row for row in _as_list(provider.get("operations")) if isinstance(row, dict)]
    names = [str(row.get("operation")) for row in operations]
    rollback_rows = [row for row in operations if row.get("operation") == "rollback"]
    rollback = rollback_rows[-1] if rollback_rows else {}
    restored = bool(provider.get("before_commit_hash")) and provider.get("before_commit_hash") == provider.get("after_undo_hash")
    commit_changed = bool(provider.get("after_commit_hash")) and provider.get("after_commit_hash") != provider.get("before_commit_hash")
    handle = provider.get("rollback_handle_id")
    handle_consumed = bool(handle) and str(handle) not in {str(value) for value in _as_list(provider.get("active_undo_handles_after"))}
    if not handle or not rollback_rows:
        return _result("hold", "Rollback evidence lacks a handle or rollback trajectory row.")
    ordered = all(name in names for name in ["commit", "verify", "rollback"]) and (
        names.index("commit") < names.index("verify") < names.index("rollback")
    )
    valid = (
        provider.get("commit_outcome") == "committed"
        and provider.get("undo_outcome") == "reverted"
        and provider.get("undo_receipt_status") == "reverted"
        and bool(rollback.get("rollback_verified"))
        and rollback.get("status") == "rollback_verified"
        and commit_changed
        and restored
        and handle_consumed
        and ordered
    )
    if not valid:
        return _result(
            "fail",
            "Undo did not prove a verified provider rollback and restored external state.",
            commit_outcome=provider.get("commit_outcome"),
            undo_outcome=provider.get("undo_outcome"),
            rollback=rollback,
            commit_changed_state=commit_changed,
            external_state_restored=restored,
            handle_consumed=handle_consumed,
            transaction_ordered=ordered,
            operation_order=names,
        )
    return _result(
        "pass",
        "Undo consumed its handle, emitted a verified rollback row, and restored external calendar state.",
        rollback_handle_id=handle,
        rollback_row_id=rollback.get("row_id"),
        external_state_hash=provider.get("after_undo_hash"),
        operation_order=names,
    )


def explanations_cited_controls(vector: dict[str, Any]) -> PredicateResult:
    explanation = _as_dict(vector.get("explanation"))
    trajectory_ids = {str(value) for value in _as_list(explanation.get("trajectory_row_ids")) if value}
    answers = [row for row in _as_list(explanation.get("answers")) if isinstance(row, dict)]
    required_controls = {
        "belief": {"authority_effect"},
        "authority": {"next_action"},
        "candidate": {"required_authority_tier", "reversibility"},
        "provider": {"rollback_handle_id", "rollback_verified"},
        "trajectory": {"requires_replay_visibility"},
    }
    if not trajectory_ids or not answers:
        return _result("hold", "Explanation grading needs trajectory rows and answer artifacts.")
    failures: list[dict[str, Any]] = []
    for answer in answers:
        subject = str(answer.get("subject") or "")
        citations = {str(value) for value in _as_list(answer.get("citation_ids")) if value}
        controls = _as_dict(answer.get("controls"))
        missing_controls = sorted(required_controls.get(subject, set()) - set(controls))
        unresolved = sorted(citations - trajectory_ids)
        if not answer.get("claim") or not answer.get("version") or not citations or unresolved or missing_controls:
            failures.append(
                {
                    "subject": subject,
                    "unresolved_citations": unresolved,
                    "missing_controls": missing_controls,
                    "has_claim": bool(answer.get("claim")),
                    "has_version": bool(answer.get("version")),
                }
            )
    observed_subjects = {str(row.get("subject")) for row in answers}
    missing_subjects = sorted(set(required_controls) - observed_subjects)
    if failures or missing_subjects:
        return _result(
            "fail",
            "One or more explanations lacked trajectory citations or context-relevant controls.",
            failures=failures,
            missing_subjects=missing_subjects,
        )
    return _result(
        "pass",
        "Belief, authority, candidate, provider, and trajectory explanations cite rows and expose controls.",
        subjects=sorted(observed_subjects),
        trajectory_row_count=len(trajectory_ids),
    )


def frontier_failure_visible(vector: dict[str, Any]) -> PredicateResult:
    frontier = _as_dict(vector.get("frontier"))
    before = [value for value in _as_list(frontier.get("stale_candidate_ids_before")) if value]
    after = [value for value in _as_list(frontier.get("candidate_ids_after")) if value]
    receipts = [row for row in _as_list(frontier.get("failure_receipts")) if isinstance(row, dict)]
    actuation_rows = [row for row in _as_list(frontier.get("actuation_rows_after_failure")) if isinstance(row, dict)]
    if not before or not receipts:
        return _result("hold", "Failure injection lacks stale candidates or a replay-visible failure receipt.")
    receipt_matches = any(
        row.get("row_id")
        and row.get("status") == "failed"
        and row.get("failure_mode") == frontier.get("failure_mode")
        for row in receipts
    )
    safe = (
        frontier.get("outcome") == "failed"
        and bool(frontier.get("failure_mode"))
        and not after
        and receipt_matches
        and not actuation_rows
    )
    if not safe:
        return _result(
            "fail",
            "A respondent failure was not fully visible or stale candidates remained actionable.",
            outcome=frontier.get("outcome"),
            failure_mode=frontier.get("failure_mode"),
            stale_candidate_ids_before=before,
            candidate_ids_after=after,
            failure_receipt_matches=receipt_matches,
            actuation_row_count=len(actuation_rows),
        )
    return _result(
        "pass",
        "The respondent failure was replay-visible, cleared stale candidates, and produced no actuation.",
        failure_mode=frontier.get("failure_mode"),
        failure_receipt_row_ids=[row.get("row_id") for row in receipts],
        cleared_candidate_ids=before,
    )


def restart_restore(vector: dict[str, Any]) -> PredicateResult:
    restart = _as_dict(vector.get("restart_restore"))
    before = _as_dict(restart.get("before"))
    after = _as_dict(restart.get("after"))
    artifacts = [str(value) for value in _as_list(restart.get("persisted_artifacts")) if value]
    fields = ["session_id", "candidate_ids", "receipt_ids", "trajectory_row_ids", "transcript_event_count"]
    missing = [field for field in fields if field not in before or field not in after]
    if missing or not artifacts:
        return _result("hold", "Restart evidence is incomplete.", missing_fields=missing, persisted_artifacts=artifacts)
    mismatches = {
        field: {"before": before.get(field), "after": after.get(field)}
        for field in fields
        if before.get(field) != after.get(field)
    }
    if mismatches or after.get("restore_error") not in {None, ""}:
        return _result(
            "fail",
            "The current persisted session did not restore its visible identifiers and trajectory.",
            mismatches=mismatches,
            restore_error=after.get("restore_error"),
        )
    return _result(
        "pass",
        "The current P12 persistence path restored visible identifiers and trajectory rows.",
        restored_fields=fields,
        persisted_artifacts=artifacts,
    )


def trajectory_reconstruction(vector: dict[str, Any]) -> PredicateResult:
    projection = _as_dict(vector.get("projection"))
    required_paths = [str(value) for value in _as_list(projection.get("required_visible_paths")) if value]
    trajectory_rows = [str(value) for value in _as_list(projection.get("trajectory_row_ids")) if value]
    reconstructed = _as_dict(projection.get("trajectory_reconstruction"))
    visible = _as_dict(projection.get("visible_values"))
    sources = {str(value) for value in _as_list(projection.get("projection_sources")) if value}
    if not required_paths or not trajectory_rows:
        return _result("hold", "Trajectory projection needs an explicit visible-field set and trajectory rows.")
    if not reconstructed or sources != {"trajectory"}:
        return _result(
            "not_reached",
            "Visible state still depends on non-Trajectory state or has no Trajectory-only projection artifact.",
            non_trajectory_sources=sorted(sources - {"trajectory"}),
            unreconstructed_paths=sorted(set(required_paths) - set(reconstructed)),
        )
    trajectory_artifact_ok, trajectory_artifact = _verified_artifact(projection.get("trajectory_artifact"))
    projection_artifact_ok, projection_artifact = _verified_artifact(projection.get("projection_artifact"))
    row_citations = _as_dict(projection.get("reconstruction_row_ids"))
    cited_rows = {
        path: {str(value) for value in _as_list(row_citations.get(path)) if value}
        for path in required_paths
    }
    uncited_paths = sorted(path for path, row_ids in cited_rows.items() if not row_ids)
    unknown_rows = sorted({row_id for row_ids in cited_rows.values() for row_id in row_ids if row_id not in set(trajectory_rows)})
    projection_metadata = _as_dict(projection.get("projection_execution"))
    execution_bound = (
        bool(projection_metadata.get("producer_id"))
        and bool(projection_metadata.get("command"))
        and projection_metadata.get("exit_code") == 0
        and projection_metadata.get("input_trajectory_sha256") == trajectory_artifact.get("actual_sha256")
    )
    if not trajectory_artifact_ok or not projection_artifact_ok or not execution_bound or uncited_paths or unknown_rows:
        return _result(
            "hold",
            "Trajectory reconstruction lacks independently hashed projection evidence tied to cited rows.",
            trajectory_artifact=trajectory_artifact,
            projection_artifact=projection_artifact,
            projection_execution_bound=execution_bound,
            uncited_paths=uncited_paths,
            unknown_row_ids=unknown_rows,
        )
    missing = sorted(set(required_paths) - set(reconstructed))
    mismatches = {
        path: {"visible": visible.get(path), "reconstructed": reconstructed.get(path)}
        for path in required_paths
        if path in reconstructed and visible.get(path) != reconstructed.get(path)
    }
    if missing:
        return _result("hold", "Trajectory projection evidence is incomplete.", missing_paths=missing)
    if mismatches:
        return _result("fail", "Trajectory reconstruction differs from visible state.", mismatches=mismatches)
    return _result(
        "pass",
        "The declared visible state is reconstructed from Trajectory rows alone.",
        reconstructed_paths=required_paths,
        trajectory_row_count=len(trajectory_rows),
    )


def single_authority_owner(vector: dict[str, Any]) -> PredicateResult:
    authority = _as_dict(vector.get("authority"))
    states = [row for row in _as_list(authority.get("coexistence_states")) if isinstance(row, dict)]
    if not states:
        return _result(
            "not_reached",
            "No old/new authority coexistence state exists yet.",
            current_receipt_owners=authority.get("current_receipt_owners", []),
        )
    invalid: list[dict[str, Any]] = []
    for state in states:
        owners = sorted({str(value) for value in _as_list(state.get("authority_owner_ids")) if value})
        receipts = [row for row in _as_list(state.get("receipts")) if isinstance(row, dict)]
        effect_receipts = [row for row in receipts if row.get("effect_authorizing") is True]
        receipt_issuers = sorted({str(row.get("issuer_id")) for row in receipts if row.get("issuer_id")})
        receipts_complete = all(
            row.get("row_id") and row.get("issuer_id") and row.get("grant_id") and row.get("outcome")
            for row in receipts
        )
        if (
            len(owners) != 1
            or len(effect_receipts) != 1
            or not receipts_complete
            or receipt_issuers != owners
        ):
            invalid.append(
                {
                    "state_id": state.get("state_id"),
                    "authority_owner_ids": owners,
                    "receipt_issuer_ids": receipt_issuers,
                    "effect_authorizing_receipt_count": len(effect_receipts),
                    "receipts_complete": receipts_complete,
                }
            )
    if invalid:
        return _result("fail", "A migration coexistence state had zero or multiple authority owners.", invalid_states=invalid)
    return _result(
        "pass",
        "Every observed migration coexistence state has exactly one receipt-issuing authority owner.",
        state_ids=[row.get("state_id") for row in states],
    )


def frontier_safety_observables(vector: dict[str, Any]) -> PredicateResult:
    frontier = _as_dict(vector.get("frontier"))
    rows = [row for row in _as_list(frontier.get("target_rows")) if isinstance(row, dict)]
    required = {"respondent", "provenance", "failure_mode", "validation_errors", "variance", "cost", "latency"}
    if not rows:
        legacy = [row for row in _as_list(frontier.get("legacy_observations")) if isinstance(row, dict)]
        legacy_fields = sorted({key for row in legacy for key in row})
        return _result(
            "not_reached",
            "No normalized target Frontier rows exist for the complete safety-observable vector.",
            observed_legacy_fields=legacy_fields,
            missing_target_fields=sorted(required - set(legacy_fields)),
        )
    failures: list[dict[str, Any]] = []
    for row in rows:
        source = _as_dict(row.get("source"))
        normalized = _as_dict(row.get("normalized"))
        missing_source = sorted(required - set(source))
        missing_normalized = sorted(required - set(normalized))
        invalid_source = sorted(
            field
            for field in required
            if field in source and not _valid_frontier_field(field, source.get(field))
        )
        invalid_normalized = sorted(
            field
            for field in required
            if field in normalized and not _valid_frontier_field(field, normalized.get(field))
        )
        field_mismatches = []
        for field in required - {"provenance"}:
            if field in source and field in normalized and source[field] != normalized[field]:
                field_mismatches.append(field)
        source_provenance = set(str(value) for value in _as_list(source.get("provenance")) if value)
        normalized_provenance = set(str(value) for value in _as_list(normalized.get("provenance")) if value)
        provenance_lost = sorted(source_provenance - normalized_provenance)
        if not row.get("row_id") or missing_source or missing_normalized or invalid_source or invalid_normalized or field_mismatches or provenance_lost:
            failures.append(
                {
                    "row_id": row.get("row_id"),
                    "missing_source_fields": missing_source,
                    "missing_normalized_fields": missing_normalized,
                    "invalid_source_fields": invalid_source,
                    "invalid_normalized_fields": invalid_normalized,
                    "field_mismatches": sorted(field_mismatches),
                    "provenance_lost": provenance_lost,
                }
            )
    if failures:
        return _result("fail", "Frontier normalization lost safety observables.", failures=failures)
    return _result(
        "pass",
        "Frontier normalization preserved respondent failure, validation, variance, cost, latency, and provenance.",
        row_ids=[row.get("row_id") for row in rows],
    )


def migration_equivalence(vector: dict[str, Any]) -> PredicateResult:
    migration = _as_dict(vector.get("migration"))
    comparisons = [row for row in _as_list(migration.get("comparisons")) if isinstance(row, dict)]
    required = {"authority", "reward_source", "denial", "provenance", "rollback"}
    if not comparisons:
        return _result(
            "not_reached",
            "No independently generated old/new migration comparison exists.",
            required_observables=sorted(required),
            current_artifacts=migration.get("current_artifacts", []),
        )
    failures: list[dict[str, Any]] = []
    for comparison in comparisons:
        old = _as_dict(comparison.get("old"))
        new = _as_dict(comparison.get("new"))
        missing = sorted((required - set(old)) | (required - set(new)))
        old_artifact_ok, old_artifact = _verified_artifact(old.get("artifact"))
        new_artifact_ok, new_artifact = _verified_artifact(new.get("artifact"))
        independent = (
            bool(old.get("producer_id"))
            and bool(new.get("producer_id"))
            and old.get("producer_id") != new.get("producer_id")
            and bool(old.get("invocation_id"))
            and bool(new.get("invocation_id"))
            and old.get("invocation_id") != new.get("invocation_id")
            and old_artifact_ok
            and new_artifact_ok
            and old_artifact.get("path") != new_artifact.get("path")
        )
        same_input = bool(old.get("input_fingerprint")) and old.get("input_fingerprint") == new.get("input_fingerprint")
        same_instrument = bool(old.get("instrument_sha256")) and old.get("instrument_sha256") == new.get("instrument_sha256")
        mismatches = [field for field in ["authority", "reward_source", "denial", "rollback"] if old.get(field) != new.get(field)]
        old_provenance = {str(value) for value in _as_list(old.get("provenance")) if value}
        new_provenance = {str(value) for value in _as_list(new.get("provenance")) if value}
        lost_provenance = sorted(old_provenance - new_provenance)
        incomplete_values = sorted(
            field
            for field in ["authority", "reward_source", "rollback"]
            if not old.get(field) or not new.get(field)
        )
        if missing or incomplete_values or not independent or not same_input or not same_instrument or mismatches or lost_provenance:
            failures.append(
                {
                    "comparison_id": comparison.get("comparison_id"),
                    "missing_observables": missing,
                    "independent_paths": independent,
                    "same_input": same_input,
                    "same_instrument": same_instrument,
                    "old_artifact": old_artifact,
                    "new_artifact": new_artifact,
                    "incomplete_values": incomplete_values,
                    "mismatches": mismatches,
                    "lost_provenance": lost_provenance,
                }
            )
    if failures:
        return _result("fail", "Old/new migration paths differ on protected observables or are not independent.", failures=failures)
    return _result(
        "pass",
        "Independent old/new paths agree on authority, reward source, denial, and rollback while preserving provenance.",
        comparison_ids=[row.get("comparison_id") for row in comparisons],
    )


def monitor_preservation(vector: dict[str, Any]) -> PredicateResult:
    monitors = _as_dict(vector.get("monitors"))
    counterexamples = {str(value) for value in _as_list(monitors.get("baseline_counterexample_ids")) if value}
    baseline_detections = {str(value) for value in _as_list(monitors.get("baseline_detection_ids")) if value}
    undetected_baseline = sorted(counterexamples - baseline_detections)
    if not counterexamples or undetected_baseline:
        return _result(
            "fail",
            "The monitor baseline cannot detect its planted counterexamples.",
            counterexample_ids=sorted(counterexamples),
            undetected_counterexample_ids=undetected_baseline,
        )
    trials = [row for row in _as_list(monitors.get("removal_trials")) if isinstance(row, dict)]
    if not trials:
        return _result(
            "not_reached",
            "No organ-removal trial exists yet; baseline counterexample detectability is recorded.",
            detected_counterexample_ids=sorted(baseline_detections),
        )
    failures: list[dict[str, Any]] = []
    for trial in trials:
        planted = {str(value) for value in _as_list(trial.get("counterexample_ids")) if value}
        before = {str(value) for value in _as_list(trial.get("detected_before")) if value}
        after = {str(value) for value in _as_list(trial.get("detected_after")) if value}
        missing_before = sorted(planted - before)
        missing_after = sorted(planted - after)
        removal_ok, removal_artifact = _verified_artifact(trial.get("removal_artifact"))
        before_ok, before_artifact = _verified_artifact(trial.get("before_report"))
        after_ok, after_artifact = _verified_artifact(trial.get("after_report"))
        if not removal_ok or not before_ok or not after_ok or missing_before or missing_after:
            failures.append(
                {
                    "trial_id": trial.get("trial_id"),
                    "missing_before": missing_before,
                    "missing_after": missing_after,
                    "removal_artifact": removal_artifact,
                    "before_report": before_artifact,
                    "after_report": after_artifact,
                }
            )
    if failures:
        return _result("fail", "Organ removal reduced planted-counterexample detectability.", failures=failures)
    return _result(
        "pass",
        "All planted counterexamples remain detectable after organ removal.",
        trial_ids=[row.get("trial_id") for row in trials],
    )


def revoke_effective(vector: dict[str, Any]) -> PredicateResult:
    authority = _as_dict(vector.get("authority"))
    attempts = [row for row in _as_list(authority.get("revoke_attempts")) if isinstance(row, dict)]
    if not attempts:
        return _result(
            "not_reached",
            "P12 has no replay-visible revoke operation and post-revoke exercise evidence.",
            observed_explanation_artifacts=authority.get("synthetic_explanation_artifacts", []),
        )
    failures: list[dict[str, Any]] = []
    for attempt in attempts:
        state_unchanged = bool(attempt.get("provider_hash_before_reexercise")) and attempt.get("provider_hash_before_reexercise") == attempt.get("provider_hash_after_reexercise")
        receipt_ok, receipt_artifact = _verified_artifact(attempt.get("revoke_receipt_artifact"))
        staged_before = {str(value) for value in _as_list(attempt.get("staged_before_revoke")) if value}
        staged_after = {str(value) for value in _as_list(attempt.get("staged_after_revoke")) if value}
        if not (
            attempt.get("grant_id")
            and attempt.get("revoke_receipt_row_id")
            and receipt_ok
            and attempt.get("exercise_before") == "allowed"
            and attempt.get("exercise_after") == "denied"
            and state_unchanged
            and attempt.get("revoke_scope") == "future_and_staged"
            and bool(staged_before)
            and not staged_after
            and attempt.get("committed_effects_rolled_back_implicitly") is False
        ):
            failures.append(
                {
                    "grant_id": attempt.get("grant_id"),
                    "revoke_receipt_row_id": attempt.get("revoke_receipt_row_id"),
                    "exercise_before": attempt.get("exercise_before"),
                    "exercise_after": attempt.get("exercise_after"),
                    "provider_state_unchanged": state_unchanged,
                    "revoke_receipt_artifact": receipt_artifact,
                    "revoke_scope": attempt.get("revoke_scope"),
                    "staged_before_revoke": sorted(staged_before),
                    "staged_after_revoke": sorted(staged_after),
                    "committed_effects_rolled_back_implicitly": attempt.get("committed_effects_rolled_back_implicitly"),
                }
            )
    if failures:
        return _result("fail", "Revoked authority remained effective or lacked a revocation receipt.", failures=failures)
    return _result(
        "pass",
        "Revocation is replay-visible and prevents subsequent exercise without provider mutation.",
        grant_ids=[row.get("grant_id") for row in attempts],
    )


def provider_verify_failure_state(vector: dict[str, Any]) -> PredicateResult:
    provider = _as_dict(vector.get("provider_verify_failure"))
    target = _as_dict(provider.get("target_transition"))
    if not target:
        return _result(
            "not_reached",
            "Provider verify failure is still reported through the legacy committed path.",
            legacy_outcome=provider.get("legacy_outcome"),
            legacy_operations=provider.get("legacy_operations", []),
        )
    before = target.get("provider_hash_before")
    after = target.get("provider_hash_after_resolution")
    operations = [row for row in _as_list(target.get("operations")) if isinstance(row, dict)]
    names = [str(row.get("operation")) for row in operations]
    verify_rows = [row for row in operations if row.get("operation") == "verify"]
    rollback_rows = [row for row in operations if row.get("operation") == "rollback"]
    safe = (
        target.get("initial_outcome") in {"unverified", "rollback_pending"}
        and target.get("initial_outcome") != "committed"
        and any(row.get("status") == "unverified" for row in verify_rows)
        and bool(rollback_rows)
        and target.get("final_outcome") in {"reverted", "hold_unresolved"}
        and bool(before)
        and (
            (target.get("final_outcome") == "reverted" and before == after)
            or (target.get("final_outcome") == "hold_unresolved" and target.get("promotion_decision") == "hold")
        )
    )
    if not safe:
        return _result(
            "fail",
            "Verify failure was mislabeled committed or did not enter rollback/hold resolution.",
            target_transition=target,
            operation_order=names,
        )
    return _result(
        "pass",
        "Verify failure is non-committed, replay-visible, and resolves through verified rollback or an explicit hold.",
        initial_outcome=target.get("initial_outcome"),
        final_outcome=target.get("final_outcome"),
        operation_order=names,
    )


def executable_explanation_controls(vector: dict[str, Any]) -> PredicateResult:
    explanation = _as_dict(vector.get("executable_controls"))
    rows = [row for row in _as_list(explanation.get("controls")) if isinstance(row, dict)]
    if not rows:
        return _result(
            "not_reached",
            "Explanations expose contextual control metadata but no executable control contract.",
            contextual_subjects=explanation.get("contextual_subjects", []),
        )
    failures = []
    for row in rows:
        artifact_ok, artifact = _verified_artifact(row.get("execution_artifact"))
        if not (
            row.get("control_id")
            and row.get("route")
            and row.get("authority_requirement")
            and row.get("outcome") in {"applied", "denied", "staged"}
            and row.get("receipt_row_id")
            and artifact_ok
        ):
            failures.append({"control_id": row.get("control_id"), "artifact": artifact, "row": row})
    if failures:
        return _result("fail", "An actionable explanation control was not executable and receipted.", failures=failures)
    return _result(
        "pass",
        "Every actionable explanation control has a route, authority requirement, execution artifact, and receipt.",
        control_ids=[row.get("control_id") for row in rows],
    )


def rollback_audit_retained(vector: dict[str, Any]) -> PredicateResult:
    rollback = _as_dict(vector.get("rollback_audit"))
    trials = [row for row in _as_list(rollback.get("trials")) if isinstance(row, dict)]
    if not trials:
        return _result(
            "not_reached",
            "No target rollback comparison proves external restoration with append-only audit retention.",
            legacy_artifacts=rollback.get("legacy_artifacts", []),
        )
    failures = []
    for trial in trials:
        before_rows = [str(value) for value in _as_list(trial.get("audit_row_ids_before")) if value]
        after_rows = [str(value) for value in _as_list(trial.get("audit_row_ids_after")) if value]
        retained = set(before_rows).issubset(after_rows)
        appended = len(after_rows) > len(before_rows)
        if not (
            trial.get("external_hash_before")
            and trial.get("external_hash_before") == trial.get("external_hash_after_rollback")
            and retained
            and appended
            and trial.get("rollback_receipt_row_id") in after_rows
        ):
            failures.append(
                {
                    "trial_id": trial.get("trial_id"),
                    "external_state_restored": trial.get("external_hash_before") == trial.get("external_hash_after_rollback"),
                    "prior_audit_retained": retained,
                    "audit_appended": appended,
                    "rollback_receipt_row_id": trial.get("rollback_receipt_row_id"),
                }
            )
    if failures:
        return _result("fail", "Rollback erased audit history or failed to restore external state.", failures=failures)
    return _result(
        "pass",
        "Rollback restores external state while retaining and extending append-only audit history.",
        trial_ids=[row.get("trial_id") for row in trials],
    )


PREDICATES: dict[str, Predicate] = {
    "frontier_provenance": frontier_provenance,
    "belief_cannot_authorize": belief_cannot_authorize,
    "expired_authority_denied": expired_authority_denied,
    "missing_evidence_rejected": missing_evidence_rejected,
    "reward_actionstream_only": reward_actionstream_only,
    "provider_transaction": provider_transaction,
    "provider_conflict_denial": provider_conflict_denial,
    "rollback_effective": rollback_effective,
    "explanations_cited_controls": explanations_cited_controls,
    "frontier_failure_visible": frontier_failure_visible,
    "restart_restore": restart_restore,
    "trajectory_reconstruction": trajectory_reconstruction,
    "single_authority_owner": single_authority_owner,
    "frontier_safety_observables": frontier_safety_observables,
    "migration_equivalence": migration_equivalence,
    "monitor_preservation": monitor_preservation,
    "revoke_effective": revoke_effective,
    "provider_verify_failure_state": provider_verify_failure_state,
    "executable_explanation_controls": executable_explanation_controls,
    "rollback_audit_retained": rollback_audit_retained,
}


def evaluate_predicate(predicate_id: str, vector: dict[str, Any]) -> PredicateResult:
    try:
        predicate = PREDICATES[predicate_id]
    except KeyError as exc:
        raise ValueError(f"unknown architecture predicate: {predicate_id}") from exc
    # Deliberately pass only observable evidence. Scenario or fixture fields such
    # as `pass`, `passed`, `ok`, or `decision` have no special meaning here.
    return predicate(dict(vector))
