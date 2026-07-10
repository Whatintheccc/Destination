from __future__ import annotations

from typing import Any, Callable


PredicateResult = dict[str, Any]
Predicate = Callable[[dict[str, Any]], PredicateResult]


def _result(status: str, summary: str, **evidence: Any) -> PredicateResult:
    return {"status": status, "summary": summary, "evidence": evidence}


def _ruler(vector: dict[str, Any]) -> dict[str, Any]:
    value = vector.get("ruler")
    return value if isinstance(value, dict) else {}


def binding_manifest_signature(vector: dict[str, Any]) -> PredicateResult:
    ruler = _ruler(vector)
    valid = ruler.get("valid_manifest_decision")
    tampered = ruler.get("tampered_manifest_decision")
    codes = {str(value) for value in ruler.get("tampered_failure_codes", [])}
    if valid is None or tampered is None:
        return _result("hold", "Binding signature evidence is incomplete.", ruler=ruler)
    if valid != "pass" or tampered != "fail" or "manifest_signature" not in codes:
        return _result("fail", "A valid signature did not pass or a tampered manifest was accepted.", ruler=ruler)
    return _result("pass", "Valid manifests pass and signed-payload tampering fails closed.", failure_codes=sorted(codes))


def binding_manifest_affectedness(vector: dict[str, Any]) -> PredicateResult:
    ruler = _ruler(vector)
    valid = ruler.get("declared_diff_decision")
    undeclared = ruler.get("undeclared_diff_decision")
    codes = {str(value) for value in ruler.get("undeclared_failure_codes", [])}
    if valid is None or undeclared is None:
        return _result("hold", "Binding affectedness evidence is incomplete.", ruler=ruler)
    required_codes = {"undeclared_path", "undeclared_affectedness"}
    if valid != "pass" or undeclared != "fail" or not required_codes.issubset(codes):
        return _result("fail", "Undeclared paths or ownership categories did not fail closed.", ruler=ruler)
    return _result("pass", "Declared diffs pass while undeclared paths and ownership categories fail.", failure_codes=sorted(codes))


def instrument_mutation_rejection(vector: dict[str, Any]) -> PredicateResult:
    ruler = _ruler(vector)
    if ruler.get("baseline_valid") is not True:
        return _result("hold", "Baseline InstrumentBundle validation did not complete.", ruler=ruler)
    if ruler.get("tampered_rejected") is not True or "artifact hash mismatch" not in str(ruler.get("tampered_reason", "")):
        return _result("fail", "A mutated instrument artifact identity was accepted.", ruler=ruler)
    return _result("pass", "InstrumentBundle validation rejects a content-addressed artifact mutation.", reason=ruler.get("tampered_reason"))


def binding_manifest_protected_path_rejection(vector: dict[str, Any]) -> PredicateResult:
    ruler = _ruler(vector)
    codes = {str(value) for value in ruler.get("protected_failure_codes", [])}
    if ruler.get("protected_path_decision") is None:
        return _result("hold", "Protected-path affectedness evidence is incomplete.", ruler=ruler)
    if ruler.get("protected_path_decision") != "fail" or not {"undeclared_path", "undeclared_affectedness"}.issubset(codes):
        return _result("fail", "A protected effect-TCB path escaped the signed manifest scope.", ruler=ruler)
    return _result("pass", "A protected effect-TCB path outside the signed scope is rejected.", failure_codes=sorted(codes))


def promotion_override_rejection(vector: dict[str, Any]) -> PredicateResult:
    promotion = vector.get("promotion")
    promotion = promotion if isinstance(promotion, dict) else {}
    required = {
        "forced_returncode", "automatic_returncode", "forced_decision", "automatic_decision",
        "current_unchanged", "promotion_trees_unchanged", "promotion_artifact_writes",
    }
    if not required.issubset(promotion):
        return _result("hold", "Frozen-promotion evidence is incomplete.", promotion=promotion)
    ok = (
        int(promotion["forced_returncode"]) != 0
        and int(promotion["automatic_returncode"]) != 0
        and promotion["forced_decision"] == "hold"
        and promotion["automatic_decision"] == "hold"
        and promotion["current_unchanged"] is True
        and promotion["promotion_trees_unchanged"] is True
        and int(promotion["promotion_artifact_writes"]) == 0
    )
    if not ok:
        return _result("fail", "Forced or automatic promotion retained a writable aperture.", promotion=promotion)
    return _result("pass", "Forced and automatic promotion are held before any promotion/report artifact write; CURRENT is unchanged.", promotion=promotion)


def reducer_determinism(vector: dict[str, Any]) -> PredicateResult:
    evidence = vector.get("product_core")
    evidence = evidence if isinstance(evidence, dict) else {}
    required = {"first_sha256", "second_sha256", "reducer_version", "event_types"}
    if not required.issubset(evidence):
        return _result("hold", "ProductCore reducer determinism evidence is incomplete.", product_core=evidence)
    if evidence["first_sha256"] != evidence["second_sha256"] or not evidence["reducer_version"]:
        return _result("fail", "Identical ProductCore inputs did not produce an identical versioned result.", product_core=evidence)
    if evidence["event_types"] != ["authenticated_observation", "frontier_proposal", "admission_preview"]:
        return _result("fail", "The no-effect Journal sequence is incomplete or reordered.", product_core=evidence)
    return _result("pass", "Identical Journal input and command produce a byte-identical versioned preview.", product_core=evidence)


def cited_required_projection(vector: dict[str, Any]) -> PredicateResult:
    evidence = vector.get("product_core")
    evidence = evidence if isinstance(evidence, dict) else {}
    required = {"status", "reducer_version", "required_fields_present", "evidence_row_ids", "all_evidence_rows_exist"}
    if not required.issubset(evidence):
        return _result("hold", "ProductCore cited-projection evidence is incomplete.", product_core=evidence)
    if (
        evidence["status"] != "preview"
        or not evidence["reducer_version"]
        or evidence["required_fields_present"] is not True
        or not evidence["evidence_row_ids"]
        or evidence["all_evidence_rows_exist"] is not True
    ):
        return _result("fail", "The ProductCore projection is missing required fields or valid Journal citations.", product_core=evidence)
    return _result("pass", "The required prep-block projection is complete, versioned, and cites existing Journal rows.", product_core=evidence)


def product_core_no_effect_reachability(vector: dict[str, Any]) -> PredicateResult:
    evidence = vector.get("product_core")
    evidence = evidence if isinstance(evidence, dict) else {}
    required = {"can_dispatch", "forbidden_imports", "forbidden_preview_fields", "effect_counts"}
    if not required.issubset(evidence):
        return _result("hold", "ProductCore no-effect reachability evidence is incomplete.", product_core=evidence)
    expected_counts = {"effect_attempts": 0, "claims": 0, "dispatches": 0, "provider_mutations": 0}
    if (
        evidence["can_dispatch"] is not False
        or evidence["forbidden_imports"]
        or evidence["forbidden_preview_fields"]
        or evidence["effect_counts"] != expected_counts
    ):
        return _result("fail", "The P13.1 ProductCore exposes an effect-capable import, field, or observed transition.", product_core=evidence)
    return _result("pass", "ProductCore is structurally non-dispatchable and records zero effect attempts or provider mutations.", product_core=evidence)


def cited_read_side_cutover(vector: dict[str, Any]) -> PredicateResult:
    evidence = vector.get("read_side")
    evidence = evidence if isinstance(evidence, dict) else {}
    required = {
        "manifest_valid", "protected_fields_equal", "required_fields_present",
        "citation_event_ids", "all_citations_in_journal", "reducer_version",
        "projection_version", "controls", "restart_restored", "effect_counts",
    }
    if not required.issubset(evidence):
        return _result("hold", "P13.2 cited read-side evidence is incomplete.", read_side=evidence)
    expected_counts = {"effect_attempts": 0, "claims": 0, "dispatches": 0, "provider_mutations": 0}
    controls = evidence.get("controls", [])
    controls_ok = bool(controls) and all(
        isinstance(row, dict)
        and row.get("effect_owner") == "incumbent"
        and row.get("authority_source") == "incumbent_swift_gate"
        and str(row.get("route", "")).startswith("/api/candidates/")
        for row in controls
    )
    ok = (
        evidence["manifest_valid"] is True
        and evidence["protected_fields_equal"] is True
        and evidence["required_fields_present"] is True
        and bool(evidence["citation_event_ids"])
        and evidence["all_citations_in_journal"] is True
        and bool(evidence["reducer_version"])
        and evidence["projection_version"] == "product_core.cited_candidate_card.v1"
        and controls_ok
        and evidence["restart_restored"] is True
        and evidence["effect_counts"] == expected_counts
    )
    if not ok:
        return _result("fail", "The cited read side lost a protected field, citation, restart value, incumbent control route, or no-effect wall.", read_side=evidence)
    return _result("pass", "The create-prep-block card is reconstructed from persisted cited Journal rows while incumbent controls remain the sole effect path.", read_side=evidence)


SANDBOX_CASE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "trusted_ingress_forgery": {
        "valid_admission_status": "ticket",
        "forged_admission_status": "denied",
        "forged_reason": "source_unauthenticated",
        "stale_admission_status": "denied",
        "stale_reason": "pre_state_mismatch",
        "ticket_count_after": 1,
    },
    "effect_ticket_binding": {
        "admission_status": "ticket",
        "ticket_kind": "apply",
        "signature_valid": True,
        "tampered_signature_valid": False,
        "nonce_unique": True,
        "grant_epoch_matches_current": True,
    },
    "compensation_ticket_binding": {
        "admission_status": "ticket",
        "ticket_kind": "compensate",
        "signature_valid": True,
        "separate_ticket": True,
        "separate_nonce": True,
    },
    "ticket_single_claim": {
        "first_phase": "verified",
        "second_phase": "verified",
        "claim_count": 1,
        "claim_fact_count": 1,
    },
    "duplicate_delivery": {
        "dispatch_count": 1,
        "mutation_count": 1,
        "same_receipt_hash": True,
        "same_idempotency_key": True,
    },
    "crash_before_claim": {
        "crash_stage": "before_claim",
        "phase_after_crash": "unclaimed",
        "claim_count_after_crash": 0,
        "dispatch_count_after_crash": 0,
        "mutation_count_after_crash": 0,
        "recovered_phase": "verified",
        "recovered_dispatch_count": 1,
    },
    "crash_after_claim": {
        "crash_stage": "after_claim_before_dispatch",
        "phase_after_crash": "claimed",
        "claim_count": 1,
        "dispatch_count": 0,
        "mutation_count": 0,
        "reconciled_phase": "not_applied",
    },
    "crash_after_dispatch": {
        "crash_stage": "after_dispatch_before_receipt",
        "phase_after_crash": "applying_unknown",
        "dispatch_count_before_reconcile": 1,
        "mutation_count_before_reconcile": 1,
        "reconciled_phase": "verified",
        "dispatch_count_after_reconcile": 1,
    },
    "verify_ambiguity_reconcile": {
        "initial_phase": "applying_unknown",
        "initial_success_label": False,
        "reconciled_phase": "verified",
        "dispatch_count": 1,
        "mutation_count": 1,
    },
    "revoke_claim_race": {
        "before_claim_phase": "denied",
        "before_claim_dispatch_count": 0,
        "after_claim_phase": "claimed",
        "after_claim_reconciled_phase": "not_applied",
        "after_claim_dispatch_count": 0,
        "invalid_epoch_admission_status": "denied",
        "invalid_epoch_reason": "grant_epoch_invalid",
    },
    "restart_reconciliation": {
        "phase_before_restart": "applying_unknown",
        "phase_after_restart": "verified",
        "same_ticket_id": True,
        "same_idempotency_key": True,
        "dispatch_count": 1,
        "mutation_count": 1,
    },
    "compensation_conflict_hold": {
        "initial_phase": "verified",
        "compensation_admission_status": "hold",
        "compensation_reason": "compensation_prestate_conflict",
        "compensation_dispatch_count": 0,
        "later_edit_preserved": True,
    },
    "no_learning_effect_path": {
        "forbidden_imports": [],
        "accepted_action_families": ["create_prep_block"],
        "default_selector": "incumbent",
        "explicit_selector": "deterministic_sandbox",
        "real_provider_reachable": False,
    },
}

SANDBOX_EQUALITY_REQUIREMENTS: dict[str, tuple[tuple[str, str], ...]] = {
    "effect_ticket_binding": (
        ("ticket_intent_hash", "expected_intent_hash"),
        ("ticket_pre_state_hash", "expected_pre_state_hash"),
    ),
    "compensation_ticket_binding": (
        ("ticket_target_receipt_hash", "expected_target_receipt_hash"),
        ("ticket_fresh_state_hash", "expected_fresh_state_hash"),
    ),
}


def sandbox_effect_contract(vector: dict[str, Any]) -> PredicateResult:
    capability = vector.get("target_capability")
    if isinstance(capability, dict) and capability.get("reached") is False:
        return p13_target_not_implemented(vector)
    evidence = vector.get("effect_kernel")
    evidence = evidence if isinstance(evidence, dict) else {}
    case = str(evidence.get("case", ""))
    expected = SANDBOX_CASE_EXPECTATIONS.get(case)
    universal = {
        "authority_profile": "owner_controlled_sandbox",
        "authorizes_production": False,
        "adapter_id": "deterministic_sandbox",
        "adapter_credential_count": 0,
        "adapter_external_io": False,
    }
    if expected is None:
        return _result("hold", "P13.3 sandbox evidence is missing or names an unknown case.", effect_kernel=evidence)
    missing = sorted((set(universal) | set(expected)) - set(evidence))
    if missing:
        return _result("hold", "P13.3 sandbox evidence is incomplete.", case=case, missing=missing)
    mismatches = {
        key: {"expected": value, "actual": evidence.get(key)}
        for key, value in {**universal, **expected}.items()
        if evidence.get(key) != value
    }
    for left, right in SANDBOX_EQUALITY_REQUIREMENTS.get(case, ()):
        if not evidence.get(left) or evidence.get(left) != evidence.get(right):
            mismatches[f"{left}={right}"] = {"left": evidence.get(left), "right": evidence.get(right)}
    if mismatches:
        return _result("fail", "The deterministic sandbox violates a ticket, lifecycle, isolation, or non-authority invariant.", case=case, mismatches=mismatches)
    return _result(
        "pass",
        "The deterministic sandbox supplies the required raw facts while remaining non-authorizing and externally inert.",
        case=case,
        observed={key: evidence[key] for key in sorted(set(universal) | set(expected))},
    )


EVENTKIT_CASE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "eventkit_identity_target_binding": {
        "app_bundle_bound": True,
        "bridge_bound": True,
        "permission_status": "full_access",
        "sandbox_calendar_id": "calendarpilot-sandbox-test",
        "raw_cli_rejected": True,
        "wrong_calendar_status": "denied",
        "wrong_calendar_reason": "target_binding_invalid",
        "effect_budget": 1,
        "dispatch_count": 0,
    },
    "eventkit_ticket_binding": {
        "admission_status": "ticket",
        "signature_valid": True,
        "tampered_signature_valid": False,
        "deterministic_profile_status": "denied",
        "deterministic_profile_reason": "authority_profile_invalid",
        "nonce_unique": True,
    },
    "eventkit_effect_lifecycle": {
        "initial_phase": "verified",
        "duplicate_same_receipt": True,
        "claim_count": 1,
        "dispatch_count": 1,
        "mutation_count": 1,
        "crash_before_phase": "unclaimed",
        "crash_before_dispatch_count": 0,
        "crash_after_claim_phase": "claimed",
        "crash_after_claim_reconciled": "not_applied",
        "crash_after_dispatch_phase": "applying_unknown",
        "restart_reconciled_phase": "verified",
        "restart_same_ticket": True,
        "restart_dispatch_count": 1,
    },
    "eventkit_revoke_claim_race": {
        "before_claim_phase": "denied",
        "before_claim_dispatch_count": 0,
        "after_claim_phase": "claimed",
        "after_claim_reconciled_phase": "not_applied",
        "after_claim_dispatch_count": 0,
        "invalid_epoch_status": "denied",
        "invalid_epoch_reason": "grant_epoch_invalid",
    },
    "eventkit_compensation_binding": {
        "apply_phase": "verified",
        "compensation_admission_status": "ticket",
        "compensation_phase": "verified",
        "compensation_dispatch_count": 1,
        "event_absent": True,
    },
    "eventkit_compensation_conflict_hold": {
        "apply_phase": "verified",
        "compensation_status": "hold",
        "compensation_reason": "compensation_prestate_conflict",
        "compensation_dispatch_count": 0,
        "external_edit_preserved": True,
    },
    "eventkit_no_learning_effect_path": {
        "forbidden_imports": [],
        "provider_only_through_gateway": True,
        "direct_commit_rejected": True,
        "production_selector_available": False,
    },
}

EVENTKIT_EQUALITY_REQUIREMENTS: dict[str, tuple[tuple[str, str], ...]] = {
    "eventkit_ticket_binding": (("ticket_target_binding", "expected_target_binding"),),
    "eventkit_compensation_binding": (
        ("target_receipt_hash", "expected_target_receipt_hash"),
        ("target_binding", "expected_target_binding"),
    ),
}


def eventkit_sandbox_contract(vector: dict[str, Any]) -> PredicateResult:
    capability = vector.get("target_capability")
    if isinstance(capability, dict) and capability.get("reached") is False:
        return p13_target_not_implemented(vector)
    evidence = vector.get("eventkit_effect_kernel")
    evidence = evidence if isinstance(evidence, dict) else {}
    case = str(evidence.get("case", ""))
    expected = EVENTKIT_CASE_EXPECTATIONS.get(case)
    universal = {
        "authority_profile": "owner_controlled_eventkit_sandbox",
        "authorizes_production": False,
        "adapter_id": "apple_eventkit_sandbox",
        "adapter_external_io": True,
        "real_provider_reachable": True,
        "action_family": "create_prep_block",
        "default_selector": "incumbent",
        "explicit_selector": "apple_eventkit_sandbox",
    }
    if expected is None:
        return _result("hold", "P13.4 EventKit evidence is missing or names an unknown case.", eventkit=evidence)
    missing = sorted((set(universal) | set(expected)) - set(evidence))
    if missing:
        return _result("hold", "P13.4 EventKit evidence is incomplete.", case=case, missing=missing)
    mismatches = {
        key: {"expected": value, "actual": evidence.get(key)}
        for key, value in {**universal, **expected}.items()
        if evidence.get(key) != value
    }
    for left, right in EVENTKIT_EQUALITY_REQUIREMENTS.get(case, ()):
        if not evidence.get(left) or evidence.get(left) != evidence.get(right):
            mismatches[f"{left}={right}"] = {"left": evidence.get(left), "right": evidence.get(right)}
    if mismatches:
        return _result(
            "fail",
            "The EventKit sandbox violates an identity, target, ticket, lifecycle, compensation, or isolation invariant.",
            case=case,
            mismatches=mismatches,
        )
    return _result(
        "pass",
        "The app-bundled EventKit sandbox satisfies the frozen single-owner effect certificate.",
        case=case,
        observed={key: evidence[key] for key in sorted(set(universal) | set(expected))},
    )


RETIREMENT_CASE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "retirement_scope_binding": {
        "normal_selector": "effect_kernel",
        "eventkit_selector": "incumbent",
        "other_action_selector": "incumbent",
        "retired_scope_cardinality": 1,
    },
    "retirement_single_owner": {
        "active_owner_count": 1,
        "effect_kernel_capable": True,
        "incumbent_capable": False,
        "normal_incumbent_override_rejected": True,
    },
    "retirement_runtime_commit": {
        "access_point": "CodexToolRuntime.REQUEST_COMMIT",
        "ticket_count": 1,
        "claim_count": 1,
        "dispatch_count": 1,
        "provider_mutation_count": 1,
        "final_phase": "verified",
        "legacy_kernel_commit_count": 0,
        "legacy_provider_commit_count": 0,
        "visible_receipt_cited": True,
    },
    "retirement_runtime_undo": {
        "access_point": "CodexToolRuntime.REQUEST_UNDO",
        "compensation_ticket_count": 1,
        "compensation_claim_count": 1,
        "compensation_dispatch_count": 1,
        "provider_removal_count": 1,
        "final_phase": "verified",
        "effect_absent": True,
        "legacy_kernel_undo_count": 0,
        "legacy_provider_undo_count": 0,
        "visible_receipt_cited": True,
    },
    "retirement_restart_rollback": {
        "owner_after_restart": "effect_kernel",
        "phase_before_reconcile": "applying_unknown",
        "phase_after_reconcile": "verified",
        "same_ticket_after_restart": True,
        "dispatch_count_after_restart": 1,
        "rollback_source": "owner_frozen_selector",
        "owner_after_rollback": "incumbent",
        "active_owner_count_after_rollback": 1,
        "dual_owner_observed": False,
    },
}


def vertical_retirement_contract(vector: dict[str, Any]) -> PredicateResult:
    capability = vector.get("target_capability")
    if isinstance(capability, dict) and capability.get("reached") is False:
        return p13_target_not_implemented(vector)
    evidence = vector.get("vertical_retirement")
    evidence = evidence if isinstance(evidence, dict) else {}
    case = str(evidence.get("case", ""))
    expected = RETIREMENT_CASE_EXPECTATIONS.get(case)
    universal = {
        "retirement_profile": "owner_controlled_vertical_retirement",
        "authorizes_production": False,
        "retired_action_family": "create_prep_block",
        "retired_backend": "deterministic_sandbox",
        "normal_owner": "effect_kernel",
        "unaffected_eventkit_owner": "incumbent",
        "unaffected_other_action_owner": "incumbent",
        "caller_owner_override_available": False,
    }
    if expected is None:
        return _result("hold", "P13.5 retirement evidence is missing or names an unknown case.", retirement=evidence)
    required = set(universal) | set(expected)
    missing = sorted(required - set(evidence))
    if missing:
        return _result("hold", "P13.5 retirement evidence is incomplete.", case=case, missing=missing)
    mismatches = {
        key: {"expected": value, "actual": evidence.get(key)}
        for key, value in {**universal, **expected}.items()
        if evidence.get(key) != value
    }
    if mismatches:
        return _result(
            "fail",
            "The vertical retirement violates scope, sole ownership, runtime routing, compensation, restart, or rollback invariants.",
            case=case,
            mismatches=mismatches,
        )
    return _result(
        "pass",
        "The exact deterministic action/backend pair has one normal EffectKernel owner and a bounded owner-controlled rollback.",
        case=case,
        observed={key: evidence[key] for key in sorted(required)},
    )


MANAGED_EVENTKIT_RETIREMENT_CASE_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "eventkit_managed_binding_state": {
        "binding_id_generation": "csprng_opaque",
        "binding_epoch": 1,
        "binding_states": ["UNBOUND", "ACTIVE", "SUSPENDED", "REBIND_REQUIRED"],
        "fingerprint_fields": ["event_store_id", "calendar_id", "source_id", "source_type", "title_tripwire"],
        "title_authority_locator": False,
        "permission_loss_state": "SUSPENDED",
        "identity_mismatch_state": "REBIND_REQUIRED",
        "rebind_increments_epoch": True,
        "stale_epoch_denied": True,
        "setup_confirmation_exact": True,
        "identity_counterexamples_all_hold": True,
        "identity_counterexamples_zero_mutation": True,
    },
    "eventkit_managed_ownership": {
        "classifier_input": "canonical_expanded_target_vector",
        "explicit_binding_owner": "effect_kernel",
        "bound_target_without_binding_result": "hold",
        "unknown_binding_result": "hold",
        "nested_bound_target_owner": "effect_kernel",
        "mixed_target_result": "hold",
        "missing_target_metadata_result": "hold",
        "wholly_outside_owner": "incumbent",
        "managed_legacy_fallback_count": 0,
    },
    "eventkit_managed_runtime_commit": {
        "access_point": "CodexToolRuntime.REQUEST_COMMIT",
        "per_mutation_confirmation_exact": True,
        "ticket_count": 2,
        "claim_count": 2,
        "dispatch_count": 2,
        "verified_event_count": 2,
        "replay_dispatch_count": 2,
        "inner_identifier_only_validation": True,
        "post_save_verification": True,
        "toctou_phase": "applying_unknown",
        "blind_retry_count": 0,
        "legacy_kernel_commit_count": 0,
        "legacy_provider_commit_count": 0,
        "same_id_substitution_result": "denied",
        "substitution_zero_mutation": True,
        "visible_external_id_matches": True,
    },
    "eventkit_managed_runtime_undo": {
        "access_point": "CodexToolRuntime.REQUEST_UNDO",
        "compensation_confirmation_exact": True,
        "receipt_owner_routing": True,
        "historical_fingerprint_retained": True,
        "exact_old_epoch_result": "verified",
        "drifted_old_epoch_result": "hold",
        "redirected_to_current_epoch": False,
        "ambiguous_event_recovery_result": "hold",
        "effect_absent": True,
        "legacy_kernel_undo_count": 0,
        "legacy_provider_undo_count": 0,
    },
    "eventkit_managed_durable_owner": {
        "global_durable_ledger": True,
        "durable_signing_state": True,
        "process_lease": "os_held_crash_released",
        "concurrent_owner_result": "hold",
        "missing_ledger_result": "hold",
        "corrupt_ledger_result": "hold",
        "second_initialize_result": "hold",
        "owner_after_restart": "effect_kernel",
        "same_ticket_after_restart": True,
        "phase_before_reconcile": "applying_unknown",
        "phase_after_reconcile": "verified",
        "redispatch_count_after_restart": 0,
        "dual_owner_observed": False,
        "actual_external_id_recovered": True,
    },
    "eventkit_managed_live_contract": {
        "live_leg": "live-eventkit-e2e",
        "canonical_app_bound": True,
        "canonical_bridge_bound": True,
        "confirmed_binding_record": True,
        "permission_status": "full_access",
        "calendar_writable": True,
        "exact_candidate_bound": True,
        "commit_access_point": "CodexToolRuntime.REQUEST_COMMIT",
        "undo_access_point": "CodexToolRuntime.REQUEST_UNDO",
        "apply_post_verified": True,
        "restart_reconciled_without_redispatch": True,
        "cleanup_status": "verified_absent",
        "legacy_mutation_count": 0,
    },
}


MANAGED_EVENTKIT_RETIREMENT_EQUALITY_REQUIREMENTS: dict[str, tuple[tuple[str, str], ...]] = {
    "eventkit_managed_runtime_commit": (
        ("canonical_target_vector_sha256", "bridge_target_vector_sha256"),
        ("ticket_binding", "expected_binding"),
        ("post_apply_binding", "expected_binding"),
    ),
    "eventkit_managed_runtime_undo": (
        ("receipt_binding", "expected_original_binding"),
        ("bridge_binding", "expected_original_binding"),
    ),
    "eventkit_managed_live_contract": (
        ("live_binding", "expected_binding"),
        ("apply_ticket_binding", "expected_binding"),
        ("compensation_receipt_binding", "expected_binding"),
    ),
}


def managed_eventkit_retirement_contract(vector: dict[str, Any]) -> PredicateResult:
    capability = vector.get("target_capability")
    if isinstance(capability, dict) and capability.get("reached") is False:
        return p13_target_not_implemented(vector)
    evidence = vector.get("managed_eventkit_retirement")
    evidence = evidence if isinstance(evidence, dict) else {}
    case = str(evidence.get("case", ""))
    expected = MANAGED_EVENTKIT_RETIREMENT_CASE_EXPECTATIONS.get(case)
    universal = {
        "retirement_profile": "owner_controlled_eventkit_binding_retirement",
        "authorizes_production": False,
        "retired_action_family": "create_prep_block",
        "retired_backend": "apple_eventkit",
        "retirement_scope": "binding_id@epoch",
        "normal_owner": "effect_kernel",
        "unaffected_other_calendar_owner": "incumbent",
        "unaffected_other_action_owner": "incumbent",
        "caller_owner_override_available": False,
        "invalid_managed_fallback_available": False,
        "one_event_per_ticket": True,
    }
    if expected is None:
        return _result("hold", "Managed EventKit retirement evidence is missing or names an unknown case.", retirement=evidence)
    required = set(universal) | set(expected)
    for left, right in MANAGED_EVENTKIT_RETIREMENT_EQUALITY_REQUIREMENTS.get(case, ()):
        required.update((left, right))
    missing = sorted(required - set(evidence))
    if missing:
        return _result("hold", "Managed EventKit retirement evidence is incomplete.", case=case, missing=missing)
    mismatches = {
        key: {"expected": value, "actual": evidence.get(key)}
        for key, value in {**universal, **expected}.items()
        if evidence.get(key) != value
    }
    for left, right in MANAGED_EVENTKIT_RETIREMENT_EQUALITY_REQUIREMENTS.get(case, ()):
        if not evidence.get(left) or evidence.get(left) != evidence.get(right):
            mismatches[f"{left}={right}"] = {"left": evidence.get(left), "right": evidence.get(right)}
    if mismatches:
        return _result(
            "fail",
            "The managed EventKit retirement violates binding, ownership, confirmation, materialization, compensation, durability, or live-certificate invariants.",
            case=case,
            mismatches=mismatches,
        )
    return _result(
        "pass",
        "The exact person-confirmed EventKit binding has one normal EffectKernel owner without global production authority.",
        case=case,
        observed={key: evidence[key] for key in sorted(required)},
    )


def p13_target_not_implemented(vector: dict[str, Any]) -> PredicateResult:
    capability = vector.get("target_capability")
    capability = capability if isinstance(capability, dict) else {}
    blocker = capability.get("blocker")
    required_evidence = capability.get("required_evidence")
    if capability.get("reached") is False and isinstance(blocker, str) and blocker and isinstance(required_evidence, list) and required_evidence:
        return _result(
            "not_reached",
            "The target contract is explicit but has no independently graded implementation evidence.",
            blocker=blocker,
            required_evidence=required_evidence,
        )
    return _result(
        "hold",
        "The target adapter cannot claim conformance until a scenario-specific predicate is installed.",
        capability=capability,
    )


P13_PREDICATES: dict[str, Predicate] = {
    "binding_manifest_signature": binding_manifest_signature,
    "binding_manifest_affectedness": binding_manifest_affectedness,
    "instrument_mutation_rejection": instrument_mutation_rejection,
    "binding_manifest_protected_path_rejection": binding_manifest_protected_path_rejection,
    "promotion_override_rejection": promotion_override_rejection,
    "reducer_determinism": reducer_determinism,
    "cited_required_projection": cited_required_projection,
    "product_core_no_effect_reachability": product_core_no_effect_reachability,
    "cited_read_side_cutover": cited_read_side_cutover,
    "sandbox_effect_contract": sandbox_effect_contract,
    "eventkit_sandbox_contract": eventkit_sandbox_contract,
    "vertical_retirement_contract": vertical_retirement_contract,
    "managed_eventkit_retirement_contract": managed_eventkit_retirement_contract,
    "p13_target_not_implemented": p13_target_not_implemented,
}
