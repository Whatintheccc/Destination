"""E-REPLAY-INTEGRITY: evidence admissibility prerequisite for dogfood eval reports.

This module is ruler-owned. It gates the three outcome rails behind raw-evidence
admissibility and never mutates the run directory it inspects. An internally
produced integrity contradiction is fail, never hold; only a preregistered
externally unavailable capture prerequisite may hold.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from calendar_pilot.environment import invariants as replay_invariants


PREREQUISITE_ID = "E-REPLAY-INTEGRITY"
ADMISSIBILITY_SCHEMA_VERSION = "dogfood_admissibility.v1"
REQUIRED_INVARIANT_IDS = ("I3",)
CAPTURE_MANIFEST_NAME = "ruler_capture/capture_manifest.json"
CAPTURE_ROWS_NAME = "ruler_capture/semantic_dom.jsonl"
CAPTURE_SCHEMA_VERSION = "dogfood_ruler_capture.v1"

REPLAY_CHECKER_PATH = Path(replay_invariants.__file__).resolve()
ADMISSIBILITY_MODULE_PATH = Path(__file__).resolve()
BROWSER_CAPTURE_PATH = (Path(__file__).resolve().parent / "capture/browser_capture.py")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture_nonce(run_id: str, scenario_id: str, stimulus_utf8_sha256: str) -> str:
    return hashlib.sha256(f"{run_id}\n{scenario_id}\n{stimulus_utf8_sha256}".encode("utf-8")).hexdigest()


def _violation(check: str, subject: str, detail: str) -> dict[str, str]:
    return {"check": check, "subject": subject, "detail": detail}


def _load_jsonl(path: Path) -> list[Any]:
    rows: list[Any] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL in {path} line {line_number}: {exc}") from exc
    return rows


def check_replay_parent_resolution(run_dir: Path) -> dict[str, Any]:
    """Every replay parent resolves inside the same retained run; every embedded
    Journal parent resolves inside its journal scope."""
    violations: list[dict[str, str]] = []
    replay_path = run_dir / "replay.jsonl"
    if not replay_path.is_file() or replay_path.stat().st_size == 0:
        return {
            "status": "fail",
            "violations": [_violation("replay_parent_resolution", "replay.jsonl", "retained replay is missing or empty")],
            "checked_replay_records": 0,
            "checked_journal_events": 0,
        }
    rows = [row for row in _load_jsonl(replay_path) if isinstance(row, dict)]
    for invariant_id in REQUIRED_INVARIANT_IDS:
        for found in replay_invariants.CHECKS[invariant_id](rows):
            violations.append(_violation("replay_parent_resolution", found.record_id, f"{found.invariant_id}: {found.detail}"))
    journal_scopes: dict[str, set[str]] = {}
    journal_events: list[tuple[str, dict[str, Any]]] = []
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        event = payload.get("journal_event")
        scope = payload.get("journal_scope_id")
        if not isinstance(event, dict) or not isinstance(scope, str) or not scope:
            continue
        journal_events.append((scope, event))
        row_id = event.get("row_id")
        if isinstance(row_id, str) and row_id:
            journal_scopes.setdefault(scope, set()).add(row_id)
    for scope, event in journal_events:
        parents = event.get("causal_parent_ids")
        if not isinstance(parents, list):
            violations.append(_violation("replay_parent_resolution", str(event.get("row_id")), "embedded journal event lacks causal_parent_ids list"))
            continue
        for parent in parents:
            if str(parent) not in journal_scopes.get(scope, set()):
                violations.append(_violation("replay_parent_resolution", str(event.get("row_id")), f"journal parent not in scope {scope}: {parent}"))
    return {
        "status": "fail" if violations else "pass",
        "violations": violations,
        "checked_replay_records": len(rows),
        "checked_journal_events": len(journal_events),
    }


def _resolve_raw_record(artifact_path: Path, record_id: str) -> dict[str, Any] | None:
    if artifact_path.suffix == ".jsonl":
        for row in _load_jsonl(artifact_path):
            if isinstance(row, dict) and str(row.get("record_id")) == record_id:
                return row
        return None
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and str(payload.get("record_id")) == record_id:
        return payload
    return None


def _raw_field_value(raw: dict[str, Any], field: str) -> tuple[bool, Any]:
    if field in raw:
        return True, raw[field]
    payload = raw.get("payload")
    if isinstance(payload, dict) and field in payload:
        return True, payload[field]
    return False, None


def check_raw_normalized_equality(run_dir: Path, evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Each normalized row cites artifact hash, raw record identity, and scenario
    boundary; the evaluator re-derives every protected payload field from those
    raw sources."""
    violations: list[dict[str, str]] = []
    envelopes = [row for row in evidence_rows if isinstance(row.get("envelope"), dict)]
    for row in envelopes:
        envelope = row["envelope"]
        scenario_id = str(row.get("scenario_id"))
        subject = f"{row.get('label')}:{scenario_id}"
        raw_refs = envelope.get("raw_refs")
        if not isinstance(raw_refs, list) or not raw_refs:
            violations.append(_violation("raw_normalized_equality", subject, "normalized row does not cite raw_refs"))
            continue
        payload = envelope.get("payload", {})
        covered: set[str] = set()
        for index, ref in enumerate(raw_refs):
            if not isinstance(ref, dict):
                violations.append(_violation("raw_normalized_equality", subject, f"raw_refs[{index}] is not an object"))
                continue
            artifact = str(ref.get("artifact") or "")
            artifact_path = (run_dir / artifact).resolve()
            if not artifact or not artifact_path.is_relative_to(run_dir.resolve()) or not artifact_path.is_file():
                violations.append(_violation("raw_normalized_equality", subject, f"cited raw artifact is not retained in this run: {artifact}"))
                continue
            if _sha256_file(artifact_path) != ref.get("artifact_sha256"):
                violations.append(_violation("raw_normalized_equality", subject, f"cited artifact hash mismatch: {artifact}"))
                continue
            if str(ref.get("scenario_id")) != scenario_id:
                violations.append(_violation("raw_normalized_equality", subject, f"raw_refs[{index}] crosses scenario boundary: {ref.get('scenario_id')}"))
                continue
            record_id = str(ref.get("record_id") or "")
            raw = _resolve_raw_record(artifact_path, record_id)
            if raw is None:
                violations.append(_violation("raw_normalized_equality", subject, f"raw record identity not found: {artifact}:{record_id}"))
                continue
            if raw.get("dogfood_evidence_schema_version"):
                violations.append(_violation("raw_normalized_equality", subject, f"raw_refs[{index}] cites a normalized row, not a raw record: {record_id}"))
                continue
            fields = ref.get("fields")
            if not isinstance(fields, list) or not fields:
                violations.append(_violation("raw_normalized_equality", subject, f"raw_refs[{index}] declares no derived fields"))
                continue
            for field in fields:
                field = str(field)
                present, raw_value = _raw_field_value(raw, field)
                if not present:
                    violations.append(_violation("raw_normalized_equality", subject, f"protected field is not derivable from {record_id}: {field}"))
                    continue
                if payload.get(field) != raw_value:
                    violations.append(_violation("raw_normalized_equality", subject, f"normalized payload disagrees with cited raw row {record_id} on field: {field}"))
                    continue
                covered.add(field)
        uncovered = sorted(set(payload) - covered)
        if uncovered and not any(violation["subject"] == subject for violation in violations):
            violations.append(_violation("raw_normalized_equality", subject, f"protected fields not re-derived from raw sources: {uncovered}"))
    return {
        "status": "fail" if violations else "pass",
        "violations": violations,
        "checked_normalized_rows": len(envelopes),
    }


def check_independent_visible_capture(run_dir: Path, manifest: dict[str, Any], evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """A ruler-owned browser driver binds the stimulus/nonce and captures semantic
    DOM state; product-reported visible state agrees with that capture."""
    violations: list[dict[str, str]] = []
    rendered: dict[str, list[dict[str, Any]]] = {}
    for row in evidence_rows:
        if row.get("source") == "rendered_view" and isinstance(row.get("envelope"), dict):
            rendered.setdefault(str(row.get("scenario_id")), []).append(row)
    result: dict[str, Any] = {"checked_scenarios": len(rendered), "external_unavailable": False, "reason": None}
    if not rendered:
        result.update({"status": "pass", "violations": []})
        return result
    manifest_path = run_dir / CAPTURE_MANIFEST_NAME
    rows_path = run_dir / CAPTURE_ROWS_NAME
    if not manifest_path.is_file():
        result.update({"status": "fail", "violations": [_violation("independent_visible_capture", CAPTURE_MANIFEST_NAME, "ruler capture manifest is missing and no external unavailability was preregistered")]})
        return result
    capture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if capture_manifest.get("dogfood_capture_schema_version") != CAPTURE_SCHEMA_VERSION:
        violations.append(_violation("independent_visible_capture", CAPTURE_MANIFEST_NAME, "unsupported ruler capture schema version"))
    if capture_manifest.get("run_id") != manifest.get("run_id"):
        violations.append(_violation("independent_visible_capture", CAPTURE_MANIFEST_NAME, "ruler capture binds a different run_id"))
    if capture_manifest.get("available") is False:
        result["external_unavailable"] = capture_manifest.get("external") is True
        result["reason"] = str(capture_manifest.get("reason") or "capture prerequisite unavailable")
        if violations:
            result.update({"status": "fail", "violations": violations})
        elif result["external_unavailable"]:
            result.update({"status": "hold", "violations": []})
        else:
            result.update({"status": "fail", "violations": [_violation("independent_visible_capture", CAPTURE_MANIFEST_NAME, "capture unavailability is not an external prerequisite")]})
        return result
    driver = capture_manifest.get("driver", {}) if isinstance(capture_manifest.get("driver"), dict) else {}
    if not BROWSER_CAPTURE_PATH.is_file() or driver.get("sha256") != _sha256_file(BROWSER_CAPTURE_PATH):
        violations.append(_violation("independent_visible_capture", CAPTURE_MANIFEST_NAME, "capture driver hash does not bind the ruler-owned browser driver"))
    stimuli = {str(row.get("scenario_id")): str(row.get("utf8_sha256")) for row in manifest.get("stimuli", [])}
    capture_rows: dict[str, dict[str, Any]] = {}
    if rows_path.is_file() and rows_path.stat().st_size > 0:
        for index, row in enumerate(_load_jsonl(rows_path), 1):
            if not isinstance(row, dict):
                continue
            scenario_id = str(row.get("scenario_id"))
            subject = f"{CAPTURE_ROWS_NAME}:{index}"
            if scenario_id not in stimuli:
                violations.append(_violation("independent_visible_capture", subject, f"capture row names a scenario outside this run: {scenario_id}"))
                continue
            expected_nonce = capture_nonce(str(manifest.get("run_id")), scenario_id, stimuli[scenario_id])
            if row.get("nonce") != expected_nonce:
                violations.append(_violation("independent_visible_capture", subject, f"capture nonce does not bind this run/stimulus: {scenario_id}"))
                continue
            capture_rows[scenario_id] = row
    for scenario_id, rows in sorted(rendered.items()):
        capture = capture_rows.get(scenario_id)
        if capture is None:
            violations.append(_violation("independent_visible_capture", scenario_id, "no nonce-bound independent capture exists for a scenario with product-reported visible state"))
            continue
        captured_visible = capture.get("visible") if isinstance(capture.get("visible"), dict) else {}
        for row in rows:
            visible = row["envelope"].get("payload", {}).get("visible")
            if not isinstance(visible, dict) or not visible:
                violations.append(_violation("independent_visible_capture", f"{row.get('label')}:{scenario_id}", "product-reported rendered view declares no visible state to confirm"))
                continue
            for key, value in visible.items():
                if key not in captured_visible:
                    violations.append(_violation("independent_visible_capture", f"{scenario_id}:{key}", "product-reported visible field is absent from the independent capture"))
                elif captured_visible[key] != value:
                    violations.append(_violation("independent_visible_capture", f"{scenario_id}:{key}", "product-reported rendering disagrees with independent DOM capture"))
    result.update({"status": "fail" if violations else "pass", "violations": violations})
    return result


def instrument_binding() -> dict[str, Any]:
    return {
        "replay_checker": {"kind": "replay_checker", "path": str(REPLAY_CHECKER_PATH), "sha256": _sha256_file(REPLAY_CHECKER_PATH)},
        "required_invariant_ids": list(REQUIRED_INVARIANT_IDS),
        "admissibility_module": {"kind": "admissibility_module", "path": str(ADMISSIBILITY_MODULE_PATH), "sha256": _sha256_file(ADMISSIBILITY_MODULE_PATH)},
        "browser_capture": {"kind": "browser_capture_driver", "path": str(BROWSER_CAPTURE_PATH), "sha256": _sha256_file(BROWSER_CAPTURE_PATH)},
    }


def derive_admissibility(run_dir: Path, manifest: dict[str, Any], evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    checks = {
        "replay_parent_resolution": check_replay_parent_resolution(run_dir),
        "raw_normalized_equality": check_raw_normalized_equality(run_dir, evidence_rows),
        "independent_visible_capture": check_independent_visible_capture(run_dir, manifest, evidence_rows),
    }
    statuses = [check["status"] for check in checks.values()]
    status = "fail" if "fail" in statuses else ("hold" if "hold" in statuses else "pass")
    return {
        "prerequisite_id": PREREQUISITE_ID,
        "prerequisite_schema_version": ADMISSIBILITY_SCHEMA_VERSION,
        "status": status,
        "binding_eligible": status == "pass",
        "checks": checks,
        "instrument": instrument_binding(),
    }


def capture_artifacts(run_dir: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for name, kind in ((CAPTURE_MANIFEST_NAME, "ruler_capture_manifest"), (CAPTURE_ROWS_NAME, "ruler_capture_rows")):
        path = run_dir / name
        if path.is_file() and path.stat().st_size > 0:
            artifacts.append({"kind": kind, "path": str(path.resolve()), "sha256": _sha256_file(path)})
    return artifacts
