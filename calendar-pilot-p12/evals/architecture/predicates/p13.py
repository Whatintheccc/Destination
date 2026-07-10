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
    "p13_target_not_implemented": p13_target_not_implemented,
}
