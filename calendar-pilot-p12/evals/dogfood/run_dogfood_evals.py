#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json, atomic_write_text
from evals.dogfood import admissibility as evidence_admissibility
from evals.dogfood.adapters import LiveRunAdapter
from evals.dogfood.predicates import evaluate_predicate
from evals.architecture.run_architecture_evals import validate_report as validate_architecture_report


SCENARIO_SET = ROOT / "evals/dogfood/scenarios/p13_product_v2.json"
MANIFEST_SCHEMA = ROOT / "contracts/dogfood_run_manifest.schema.json"
TRUTH_SCHEMA = ROOT / "contracts/dogfood_operator_truth.schema.json"
REPORT_SCHEMA = ROOT / "contracts/dogfood_eval_report_v3.schema.json"
PREDICATE_PATH = ROOT / "evals/dogfood/predicates/product.py"
ADAPTER_PATH = ROOT / "evals/dogfood/adapters/live_run.py"
STATUSES = ("pass", "fail", "hold", "not_reached")
EXPECTED_SCENARIO_IDS = {
    "P-IDENTITY", "P-OBSERVE", "P-RECOMMEND", "P-ACTION-VISIBLE", "P-TIMEZONE",
    "P-FOLLOWUP", "P-CORRECTION", "P-SIMULATE", "P-NOOP", "P-DENIAL",
    "P-FEEDBACK", "P-RESTART", "P-LIVE-READ", "P-EFFECT", "P-UNDO",
}
EXPECTED_COUNTEREXAMPLE_IDS = {
    "wrong_build_or_pid", "fixture_labeled_eventkit", "rendered_action_omits_times",
    "wrong_local_day", "followup_replans", "recommendation_stages", "simulation_mutates",
    "commit_without_readback", "undo_wrong_external_id", "feedback_unrendered_candidate",
    "restart_duplicates_effect", "cross_run_artifact", "model_prose_replaces_view",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(kind: str, path: Path) -> dict[str, str]:
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"dogfood artifact missing or empty: {path}")
    return {"kind": kind, "path": str(path.resolve()), "sha256": _sha256(path)}


def _validate(payload: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}" for error in errors)
        raise ValueError(f"{label} schema validation failed: {details}")


def load_scenario_set(path: Path = SCENARIO_SET) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("dogfood_scenario_set_schema_version") != "dogfood_scenario_set.v2":
        raise ValueError("unsupported dogfood scenario-set version")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("dogfood scenarios must be a list")
    ids = [str(row.get("scenario_id")) for row in scenarios if isinstance(row, dict)]
    if set(ids) != EXPECTED_SCENARIO_IDS or len(ids) != len(set(ids)):
        raise ValueError("p13_product_v1 scenario coverage changed without a version bump")
    orders = [row.get("order") for row in scenarios]
    if orders != list(range(1, 16)):
        raise ValueError("p13_product_v1 scenarios must retain causal order 1..15")
    predicates = {str(row.get("predicate_id")) for row in scenarios}
    if len(predicates) != len(EXPECTED_SCENARIO_IDS):
        raise ValueError("each dogfood scenario must bind one unique predicate")
    fixture_ids = {str(row.get("fixture_id")) for row in payload.get("fixture_families", [])}
    if len(fixture_ids) != 10:
        raise ValueError("p13_product_v1 must freeze exactly ten fixture families")
    counterexample_ids = {str(row.get("counterexample_id")) for row in payload.get("planted_counterexamples", [])}
    if counterexample_ids != EXPECTED_COUNTEREXAMPLE_IDS:
        raise ValueError("p13_product_v1 planted counterexample coverage changed without a version bump")
    for row in scenarios:
        if not row.get("cells") or not row.get("stimulus") or not row.get("required_sources"):
            raise ValueError(f"incomplete scenario binding: {row.get('scenario_id')}")
    return payload


def _stimulus_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def required_artifacts_for_cell(scenario_set: dict[str, Any], cell: str) -> list[str]:
    requirements = scenario_set.get("artifact_requirements", {})
    values = list(requirements.get("D0" if cell == "D0" else "D1-D7", []))
    if cell == "D7":
        values.extend(requirements.get("D7", []))
    if len(values) != len(set(values)):
        raise ValueError("dogfood scenario set contains duplicate artifact requirements")
    return values


def validate_manifest_binding(manifest: dict[str, Any], scenario_set: dict[str, Any], scenario_set_path: Path, run_dir: Path) -> None:
    if Path(manifest["run_dir"]).resolve() != run_dir.resolve():
        raise ValueError("run manifest run_dir does not equal evaluated directory")
    if manifest["scenario_set"]["sha256"] != _sha256(scenario_set_path):
        raise ValueError("run manifest scenario-set hash does not match frozen instrument")
    scenario_path = Path(manifest["scenario_set"]["path"])
    scenario_path = scenario_path if scenario_path.is_absolute() else ROOT / scenario_path
    if scenario_path.resolve() != scenario_set_path.resolve():
        raise ValueError("run manifest scenario-set path does not name the frozen instrument")
    applicable = [row for row in scenario_set["scenarios"] if manifest["cell"] in row["cells"]]
    applicable_ids = [row["scenario_id"] for row in applicable]
    if manifest["scenario_ids"] != applicable_ids:
        raise ValueError("run manifest scenarios do not exactly equal the frozen cell scenario order")
    expected_stimuli = {row["scenario_id"]: _stimulus_hash(row["stimulus"]) for row in applicable}
    stimulus_ids = [row["scenario_id"] for row in manifest["stimuli"]]
    if len(stimulus_ids) != len(set(stimulus_ids)):
        raise ValueError("run manifest contains duplicate scenario stimuli")
    actual_stimuli = {row["scenario_id"]: row["utf8_sha256"] for row in manifest["stimuli"]}
    if actual_stimuli != expected_stimuli:
        raise ValueError("run manifest stimulus hashes do not equal the frozen scenario bytes")
    if manifest["required_artifacts"] != required_artifacts_for_cell(scenario_set, manifest["cell"]):
        raise ValueError("run manifest artifact inventory does not equal the frozen cell requirements")
    expected_predicate_hash = _sha256(PREDICATE_PATH)
    bound = {str(row["path"]): str(row["sha256"]) for row in manifest["predicate_artifacts"]}
    matching = [value for path, value in bound.items() if Path(path).name == PREDICATE_PATH.name]
    if matching != [expected_predicate_hash]:
        raise ValueError("run manifest does not bind the current product predicate artifact")


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row["status"]) for row in results)
    status_counts = {status: counts.get(status, 0) for status in STATUSES}
    blockers = [str(row["scenario_id"]) for row in results if row["status"] != "pass"]
    if status_counts["fail"]:
        decision = "fail"
    elif status_counts["hold"]:
        decision = "hold"
    elif status_counts["not_reached"]:
        decision = "not_reached"
    else:
        decision = "pass"
    return {"decision": decision, "scenario_count": len(results), "status_counts": status_counts, "blocking_scenario_ids": blockers}


def _missing_architecture_rail(name: str) -> dict[str, Any]:
    return {"decision": "hold", "scenario_count": 0, "status_counts": {status: 0 for status in STATUSES}, "blocking_scenario_ids": [f"missing:architecture_{name}"]}


def _architecture_rails(run_dir: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    path = run_dir / "architecture_eval_report_v2.json"
    if not path.is_file():
        return {"preservation": _missing_architecture_rail("preservation"), "target_conformance": _missing_architecture_rail("target_conformance")}, []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("architecture_eval_report_schema_version") != "architecture_eval_report.v2":
        raise ValueError("dogfood requires architecture_eval_report.v2")
    validate_architecture_report(payload)
    repository = payload.get("repository", {})
    if repository.get("git_sha") != manifest["repository"]["git_sha"] or repository.get("app_tree_sha") != manifest["repository"]["app_tree_sha"]:
        raise ValueError("architecture report repository identity differs from dogfood manifest")
    rails: dict[str, Any] = {}
    for name in ("preservation", "target_conformance"):
        source = payload.get("rails", {}).get(name, {})
        rails[name] = {"decision": source.get("decision", "hold"), "scenario_count": source.get("scenario_count", 0), "status_counts": {status: source.get("status_counts", {}).get(status, 0) for status in STATUSES}, "blocking_scenario_ids": list(source.get("blocking_scenario_ids", []))}
    return rails, [_artifact("architecture_eval_report", path)]


def _overall_decision(admissibility_status: str, product: dict[str, Any], architecture: dict[str, Any]) -> str:
    decisions = [admissibility_status, product["decision"], architecture["preservation"]["decision"], architecture["target_conformance"]["decision"]]
    for status in ("fail", "hold", "not_reached", "pass"):
        if status in decisions:
            return status
    return "hold"


def _derived_admissibility_status(checks: dict[str, Any]) -> str:
    statuses = [str(check.get("status")) for check in checks.values()]
    if "fail" in statuses:
        return "fail"
    if "hold" in statuses:
        return "hold"
    return "pass"


def _first_blocker(admissibility_status: str, product: dict[str, Any], architecture: dict[str, Any]) -> str | None:
    if admissibility_status != "pass":
        return evidence_admissibility.PREREQUISITE_ID
    return (product["blocking_scenario_ids"] or architecture["preservation"]["blocking_scenario_ids"] or architecture["target_conformance"]["blocking_scenario_ids"] or [None])[0]


def _inventory(run_dir: Path, required: list[str]) -> tuple[list[dict[str, str]], float]:
    excluded = {"dogfood_eval_report.json", "SHA256SUMS"}
    expected = [name for name in required if name not in excluded]
    artifacts: list[dict[str, str]] = []
    present = 0
    for name in expected:
        path = run_dir / name
        if path.is_file() and path.stat().st_size > 0:
            present += 1
            artifacts.append(_artifact("run_evidence", path))
    ratio = 1.0 if not expected else present / len(expected)
    return artifacts, ratio


def _distance(results: list[dict[str, Any]], completeness: float) -> dict[str, Any]:
    counts = Counter(str(row["status"]) for row in results)
    def total(metric: str) -> int:
        return sum(int(row.get("metrics", {}).get(metric, 0)) for row in results)
    return {
        "status_counts": {status: counts.get(status, 0) for status in STATUSES},
        "required_blocking_scenario_ids": [row["scenario_id"] for row in results if row["status"] != "pass"],
        "evidence_completeness_ratio": round(completeness, 6),
        "internal_visible_projection_divergence": total("projection_divergence"),
        "requested_actual_effect_ceiling_divergence": total("effect_ceiling_divergence"),
        "plan_continuity_violations": total("plan_continuity_violations"),
        "provider_truth_divergence": total("provider_truth_divergence"),
        "latency_cost_variance_resources": {},
        "unreached_capabilities": [row["scenario_id"] for row in results if row["status"] == "not_reached"],
    }


def validate_report(report: dict[str, Any]) -> None:
    _validate(report, REPORT_SCHEMA, "dogfood eval report")
    expected_product = _summary(report["scenarios"])
    if report["product_rail"] != expected_product:
        raise ValueError("product rail is not derived from scenario results")
    admissibility = report["evidence_admissibility"]
    expected_status = _derived_admissibility_status(admissibility["checks"])
    if admissibility["status"] != expected_status:
        raise ValueError("evidence admissibility status is not derived from its per-check evidence")
    if admissibility["binding_eligible"] != (expected_status == "pass") or report["binding_eligible"] != admissibility["binding_eligible"]:
        raise ValueError("binding eligibility is not derived from the admissibility prerequisite")
    if list(admissibility["instrument"]["required_invariant_ids"]) != list(evidence_admissibility.REQUIRED_INVARIANT_IDS):
        raise ValueError("admissibility does not bind the required replay invariant ids")
    for name in ("replay_checker", "admissibility_module", "browser_capture"):
        artifact = admissibility["instrument"][name]
        path = Path(artifact["path"])
        if not path.is_file() or _sha256(path) != artifact["sha256"]:
            raise ValueError(f"admissibility instrument hash mismatch: {name}")
    expected_decision = _overall_decision(expected_status, expected_product, report["architecture_rails"])
    if report["decision"] != expected_decision:
        raise ValueError("dogfood decision is not derived from the admissibility prerequisite and three rails")
    expected_first = _first_blocker(expected_status, expected_product, report["architecture_rails"])
    if report["first_blocking_scenario_id"] != expected_first:
        raise ValueError("first blocking scenario is not derived in causal order")
    distance = report["distance"]
    expected_counts = Counter(str(row["status"]) for row in report["scenarios"])
    expected_distance_fields = {
        "status_counts": {status: expected_counts.get(status, 0) for status in STATUSES},
        "required_blocking_scenario_ids": [row["scenario_id"] for row in report["scenarios"] if row["status"] != "pass"],
        "internal_visible_projection_divergence": sum(int(row.get("metrics", {}).get("projection_divergence", 0)) for row in report["scenarios"]),
        "requested_actual_effect_ceiling_divergence": sum(int(row.get("metrics", {}).get("effect_ceiling_divergence", 0)) for row in report["scenarios"]),
        "plan_continuity_violations": sum(int(row.get("metrics", {}).get("plan_continuity_violations", 0)) for row in report["scenarios"]),
        "provider_truth_divergence": sum(int(row.get("metrics", {}).get("provider_truth_divergence", 0)) for row in report["scenarios"]),
        "unreached_capabilities": [row["scenario_id"] for row in report["scenarios"] if row["status"] == "not_reached"],
    }
    if any(distance[key] != value for key, value in expected_distance_fields.items()):
        raise ValueError("dogfood distance vector is not derived from scenario results")
    for artifact in [report["manifest"], report["scenario_set"], *report["instrument_artifacts"], *report["artifact_inventory"]]:
        path = Path(artifact["path"])
        if not path.is_file() or _sha256(path) != artifact["sha256"]:
            raise ValueError(f"dogfood artifact hash mismatch: {path}")


def build_report(*, run_dir: Path, scenario_set_path: Path = SCENARIO_SET, out: Path | None = None) -> dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    scenario_set_path = Path(scenario_set_path).resolve()
    out = (Path(out).resolve() if out is not None else run_dir / "dogfood_eval_report.json")
    if out.parent != run_dir:
        raise ValueError("dogfood report must be written directly inside its bound run directory")
    manifest_path = run_dir / "run_manifest.json"
    truth_path = run_dir / "operator_truth.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    operator_truth = json.loads(truth_path.read_text(encoding="utf-8"))
    _validate(manifest, MANIFEST_SCHEMA, "dogfood run manifest")
    _validate(operator_truth, TRUTH_SCHEMA, "dogfood operator truth")
    if operator_truth["run_id"] != manifest["run_id"]:
        raise ValueError("operator truth run_id differs from run manifest")
    scenario_set = load_scenario_set(scenario_set_path)
    validate_manifest_binding(manifest, scenario_set, scenario_set_path, run_dir)
    adapter = LiveRunAdapter(ROOT, run_dir, manifest, operator_truth)
    applicable = [row for row in scenario_set["scenarios"] if manifest["cell"] in row["cells"]]
    results: list[dict[str, Any]] = []
    for scenario in applicable:
        vector = adapter.collect(scenario)
        evaluated = evaluate_predicate(str(scenario["predicate_id"]), vector)
        results.append({
            "scenario_id": scenario["scenario_id"], "order": scenario["order"],
            "status": evaluated["status"], "summary": evaluated["summary"],
            "required_sources": list(scenario["required_sources"]),
            "present_sources": list(vector["present_sources"]),
            "evidence": evaluated.get("evidence", {}), "metrics": evaluated.get("metrics", {}),
        })
    product = _summary(results)
    architecture, architecture_artifacts = _architecture_rails(run_dir, manifest)
    inventory, completeness = _inventory(run_dir, manifest["required_artifacts"])
    admissibility = evidence_admissibility.derive_admissibility(run_dir, manifest, adapter.evidence_rows)
    decision = _overall_decision(admissibility["status"], product, architecture)
    first_blocker = _first_blocker(admissibility["status"], product, architecture)
    instrument_artifacts = [_artifact("dogfood_runner", Path(__file__)), _artifact("dogfood_predicates", PREDICATE_PATH), _artifact("dogfood_adapter", ADAPTER_PATH), _artifact("dogfood_report_schema", REPORT_SCHEMA), _artifact("dogfood_manifest_schema", MANIFEST_SCHEMA), _artifact("dogfood_operator_truth_schema", TRUTH_SCHEMA)]
    report = {
        "dogfood_eval_report_schema_version": "dogfood_eval_report.v3",
        "run_id": manifest["run_id"], "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision, "binding_eligible": admissibility["binding_eligible"],
        "first_blocking_scenario_id": first_blocker,
        "manifest": _artifact("dogfood_run_manifest", manifest_path),
        "scenario_set": _artifact("dogfood_scenario_set", scenario_set_path),
        "instrument_artifacts": instrument_artifacts,
        "evidence_admissibility": admissibility,
        "architecture_rails": architecture, "product_rail": product,
        "distance": _distance(results, completeness), "scenarios": results,
        "artifact_inventory": sorted([*inventory, *architecture_artifacts, *adapter.artifacts, *evidence_admissibility.capture_artifacts(run_dir)], key=lambda row: (row["path"], row["kind"])),
    }
    validate_report(report)
    atomic_write_json(out, report)
    checksum_paths = sorted({Path(row["path"]) for row in report["artifact_inventory"] if Path(row["path"]).is_relative_to(run_dir)} | {out})
    atomic_write_text(run_dir / "SHA256SUMS", "".join(f"{_sha256(path)}  {path.relative_to(run_dir)}\n" for path in checksum_paths))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one preregistered P13 product dogfood run.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--scenario-set", default=str(SCENARIO_SET))
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"dogfood evals must run from active app root: {ROOT}")
    report = build_report(run_dir=Path(args.run_dir), scenario_set_path=Path(args.scenario_set), out=Path(args.out) if args.out else None)
    print(json.dumps({"decision": report["decision"], "binding_eligible": report["binding_eligible"], "first_blocking_scenario_id": report["first_blocking_scenario_id"], "evidence_admissibility_status": report["evidence_admissibility"]["status"], "product_rail": report["product_rail"], "distance": report["distance"]}, indent=2, sort_keys=True))
    raise SystemExit(0 if report["decision"] == "pass" else 1)


if __name__ == "__main__":
    main()
