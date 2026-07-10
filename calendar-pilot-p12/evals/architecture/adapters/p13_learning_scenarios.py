from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from evals.p13_ruler.core import build_binding_manifest, build_instrument_bundle, verify_binding_manifest
from scripts.p13_learning_control import (
    APP_ROOT,
    artifact_ref,
    atomic_write_json,
    canonical_json_bytes,
    global_occurrence_id,
    load_current_policy_payload,
    load_json,
    policy_payload_hash,
    sha256_bytes,
    sha256_file,
    sign_promotion_record,
    sign_reward_event,
    validate_optimizer_report,
    validate_partition_manifest,
    validate_reward_ledger,
)
from scripts.promote_policy import apply_signed_record


P13_6_CASES = {
    "optimizer_write_boundary",
    "holdout_non_exposure",
    "signed_policy_promotion",
    "reward_identity_provenance",
}


def _keys(root: Path, name: str) -> tuple[Path, Path]:
    private = root / f"{name}-private.pem"
    public = root / f"{name}-public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return private, public


def _partition_descriptor(path: Path, *, partition_id: str, access: str, starts: str, ends: str) -> dict[str, Any]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    families = sorted({str(row["family_id"]) for row in rows})
    return {
        "partition_id": partition_id,
        "artifact_path": artifact_ref(path)["path"],
        "artifact_sha256": sha256_file(path),
        "family_set_sha256": sha256_bytes(canonical_json_bytes(families)),
        "row_count": len(rows),
        "starts_at": starts,
        "ends_at": ends,
        "optimizer_access": access,
    }


def _optimizer_fixture(root: Path) -> tuple[dict[str, Any], dict[str, Any], list[tuple[str, Path]]]:
    rows = {
        "search": ("family.search", "2026-07-01T00:00:00Z"),
        "holdout": ("family.holdout", "2026-07-02T00:00:00Z"),
        "shadow": ("family.shadow", "2026-07-03T00:00:00Z"),
    }
    for name, (family, observed) in rows.items():
        (root / f"{name}.jsonl").write_text(json.dumps({"row_id": name, "family_id": family, "observed_at": observed}) + "\n", encoding="utf-8")
    for name in ("evaluator", "manifest", "current", "effect"):
        (root / f"{name}.txt").write_text(name, encoding="utf-8")
    parameters = root / "parameters.json"
    parameters.write_text(json.dumps({"policy_tuning": {"tuning_id": "architecture-p13.6", "intent_reward_bias": {}}}), encoding="utf-8")
    manifest = {
        "learning_partition_manifest_schema_version": "learning_partition_manifest.v1",
        "instrument_epoch": "p13.6-control.1",
        "thresholds_sha256": sha256_bytes(b"p13.6-frozen-thresholds"),
        "search": _partition_descriptor(root / "search.jsonl", partition_id="p13.6.search", access="read", starts="2026-07-01T00:00:00Z", ends="2026-07-01T23:59:59Z"),
        "holdout": _partition_descriptor(root / "holdout.jsonl", partition_id="p13.6.holdout", access="denied", starts="2026-07-02T00:00:00Z", ends="2026-07-02T23:59:59Z"),
        "forward_shadow": _partition_descriptor(root / "shadow.jsonl", partition_id="p13.6.shadow", access="denied", starts="2026-07-03T00:00:00Z", ends="2026-07-03T23:59:59Z"),
        "disjointness": {"artifact_hashes_distinct": True, "family_sets_pairwise_disjoint": True, "forward_shadow_starts_after_search": True},
    }
    manifest["manifest_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
    partition_path = root / "learning_partitions.json"
    atomic_write_json(partition_path, manifest)
    validate_partition_manifest(manifest)
    proposal_dir = root / "proposals"
    process = subprocess.run([
        sys.executable, "scripts/run_policy_optimizer.py",
        "--search", str(root / "search.jsonl"), "--holdout", str(root / "holdout.jsonl"),
        "--forward-shadow", str(root / "shadow.jsonl"), "--evaluator", str(root / "evaluator.txt"),
        "--manifest", str(root / "manifest.txt"), "--current", str(root / "current.txt"),
        "--effect-tcb", str(root / "effect.txt"), "--out-dir", str(proposal_dir),
        "--payload-id", "architecture-p13.6", "--policy-parameters", str(parameters),
    ], cwd=APP_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if process.returncode == 0:
        report = load_json(proposal_dir / "optimizer_execution_report.json")
        validate_optimizer_report(report, manifest)
    else:
        report = {"decision": "hold", "boundary": "macos-sandbox-exec", "reason": process.stdout.strip() or process.stderr.strip()}
    artifacts = [("learning_partition_manifest", partition_path)]
    if (proposal_dir / "optimizer_execution_report.json").is_file():
        artifacts.append(("optimizer_execution_report", proposal_dir / "optimizer_execution_report.json"))
    return report, manifest, artifacts


def _reward_fixture(root: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
    human_private, human_public = _keys(root, "human")
    sim_private, sim_public = _keys(root, "sim")
    human_id = global_occurrence_id("human-app", "h1")
    sim_id = global_occurrence_id("sim", "s1")
    human = sign_reward_event({"issuer_id": "human-app", "event_id": "h1", "global_occurrence_id": human_id, "observed_at": "2026-07-10T00:00:00Z", "program": "program_a_human_utility", "parent_occurrence_ids": [], "utility_credit": 1.0}, human_private)
    simulator = sign_reward_event({"issuer_id": "sim", "event_id": "s1", "global_occurrence_id": sim_id, "observed_at": "2026-07-10T00:00:00Z", "program": "failure_detector", "parent_occurrence_ids": [], "utility_credit": 0.0}, sim_private)
    registry = [
        {"issuer_id": "human-app", "source_class": "human", "public_key_path": artifact_ref(human_public)["path"], "public_key_sha256": sha256_file(human_public)},
        {"issuer_id": "sim", "source_class": "simulator", "public_key_path": artifact_ref(sim_public)["path"], "public_key_sha256": sha256_file(sim_public)},
    ]
    ledger = {"reward_ingress_ledger_schema_version": "reward_ingress_ledger.v1", "issuer_registry": registry, "events": [human, simulator]}
    result = validate_reward_ledger(ledger)

    def rejected(events: list[dict[str, Any]], pattern: str) -> bool:
        try:
            validate_reward_ledger({**ledger, "events": events})
        except ValueError as error:
            return pattern in str(error)
        return False

    direct = sign_reward_event({**{key: value for key, value in simulator.items() if key not in {"payload_sha256", "signature"}}, "program": "program_a_human_utility", "utility_credit": 1.0}, sim_private)
    child = sign_reward_event({"issuer_id": "human-app", "event_id": "h2", "global_occurrence_id": global_occurrence_id("human-app", "h2"), "observed_at": "2026-07-10T00:01:00Z", "program": "program_a_human_utility", "parent_occurrence_ids": [sim_id], "utility_credit": 1.0}, human_private)
    conflicting = dict(human)
    conflicting["utility_credit"] = -1.0
    synthetic_private, synthetic_public = _keys(root, "synthetic")
    synthetic_registry = registry + [{"issuer_id": "synthetic", "source_class": "synthetic", "public_key_path": artifact_ref(synthetic_public)["path"], "public_key_sha256": sha256_file(synthetic_public)}]
    synthetic = sign_reward_event({"issuer_id": "synthetic", "event_id": "x1", "global_occurrence_id": global_occurrence_id("synthetic", "x1"), "observed_at": "2026-07-10T00:02:00Z", "program": "program_a_human_utility", "parent_occurrence_ids": [], "utility_credit": 0.0}, synthetic_private)
    result.update({
        "duplicate_conflict_rejected": rejected([human, conflicting], "duplicate"),
        "simulator_direct_positive_credit_rejected": rejected([human, direct], "direct or transitive"),
        "simulator_transitive_positive_credit_rejected": rejected([human, simulator, child], "direct or transitive"),
        "synthetic_program_a_credit_rejected": False,
    })
    try:
        validate_reward_ledger({"reward_ingress_ledger_schema_version": "reward_ingress_ledger.v1", "issuer_registry": synthetic_registry, "events": [synthetic]})
    except ValueError as error:
        result["synthetic_program_a_credit_rejected"] = "Synthetic" in str(error) or "synthetic" in str(error)
    ledger_path = root / "valid-reward-ledger.json"
    atomic_write_json(ledger_path, ledger)
    for private in (human_private, sim_private, synthetic_private):
        private.unlink()
    return result, [("reward_ledger", ledger_path), ("human_issuer_key", human_public), ("simulator_issuer_key", sim_public), ("synthetic_issuer_key", synthetic_public)]


def _payload(path: Path, payload_id: str, search_hash: str) -> dict[str, Any]:
    payload = {
        "policy_payload_schema_version": "policy_payload.v1", "payload_id": payload_id, "parent_payload_id": None,
        "policy_parameters": {"policy_tuning": {"tuning_id": payload_id, "intent_reward_bias": {}}},
        "respondents": ["diffusiongemma.fixture.v1"], "prompts": ["policy-payload-proposal.v1"],
        "compatibility": {"reducer_versions": ["product_core.create_prep_block.v1"], "schema_versions": ["policy_tuning.v1"]},
        "training": {"partition_id": "p13.6.search", "row_count": 1, "row_set_sha256": search_hash},
        "resources": {"seed_set_sha256": sha256_bytes(b"fixed"), "max_candidates": 1, "max_compute_seconds": 30},
    }
    payload["content_sha256"] = policy_payload_hash(payload)
    atomic_write_json(path, payload)
    return payload


def _signed_record(root: Path, *, name: str, transition: str, payload_path: Path, current: Path, instrument_path: Path, manifest_path: Path, private: Path, public: Path, restore: dict[str, Any] | None = None) -> Path:
    attestations = {}
    for role in ("search", "holdout", "forward_shadow"):
        row: dict[str, Any] = {"decision": "pass", "role": role}
        if role == "search" and restore is not None:
            row["restore_current_pointer"] = restore
        path = root / f"{name}-{role}.json"
        atomic_write_json(path, row)
        attestations[role] = {**artifact_ref(path), "decision": "pass"}
    partitions = root / "promotion-partitions.json"
    if not partitions.exists():
        atomic_write_json(partitions, {"fixture": "content-addressed elsewhere"})
    instrument = load_json(instrument_path)
    manifest = load_json(manifest_path)
    record = {
        "promotion_record_schema_version": "promotion_record.v1", "record_id": name, "transition": transition,
        "created_at": "2026-07-10T00:00:00Z", "payload": artifact_ref(payload_path),
        "previous_current_sha256": sha256_bytes(current.read_bytes()),
        "instrument_bundle": {"path": artifact_ref(instrument_path)["path"], "file_sha256": sha256_file(instrument_path), "bundle_sha256": instrument["bundle_sha256"], "instrument_epoch": instrument["instrument_epoch"]},
        "binding_manifest": {"path": artifact_ref(manifest_path)["path"], "sha256": sha256_file(manifest_path), "manifest_id": manifest["manifest_id"]},
        "partition_manifest": artifact_ref(partitions), "attestations": attestations, "reward_evidence": None, "decision": "pass",
        "signer": {"role": "promoter", "algorithm": "rsa-sha256", "public_key_sha256": sha256_file(public)},
    }
    path = root / f"{name}.json"
    atomic_write_json(path, sign_promotion_record(record, private, public))
    return path


def _promotion_fixture(root: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
    promoter_private, promoter_public = _keys(root, "promoter")
    wave_private, wave_public = _keys(root, "wave")
    instrument = build_instrument_bundle(verification_key=wave_public, artifact_config=APP_ROOT / "configs/p13_instrument_artifacts.json", require_clean=False)
    instrument_path = root / "instrument.json"
    atomic_write_json(instrument_path, instrument)
    scope = {"wave_scope_schema_version": "p13_wave_scope.v1", "declared_paths": ["calendar-pilot-p12/experiments/promoted/**"], "declared": {"actions": [], "backends": [], "surfaces": ["unowned"], "instruments": [], "control_planes": []}, "required_scenarios": [], "old_producer": None, "new_producer": None, "live_legs": []}
    scope_path = root / "scope.json"
    atomic_write_json(scope_path, scope)
    manifest = build_binding_manifest(wave="p13-6-architecture", change_class="migration", scope_path=scope_path, instrument_bundle_path=instrument_path, ownership_map_path=APP_ROOT / "configs/p13_ownership_map.json", signing_key=wave_private, verification_key=wave_public, require_clean=False)
    manifest_path = root / "manifest.json"
    atomic_write_json(manifest_path, manifest)
    binding_ok = verify_binding_manifest(manifest, verification_key=wave_public, changed_paths=[])["decision"] == "pass"
    promotion_root = root / "promotion-root.json"
    atomic_write_json(promotion_root, {"learning_promotion_root_schema_version": "learning_promotion_root.v1", "algorithm": "rsa-sha256", "public_key_path": artifact_ref(promoter_public)["path"], "public_key_sha256": sha256_file(promoter_public), "allowed_instrument_epochs": [instrument["instrument_epoch"]]})
    current = root / "CURRENT.json"
    atomic_write_json(current, {"legacy": "baseline"})
    baseline_payload = root / "baseline-payload.json"
    _payload(baseline_payload, "baseline", "1" * 64)
    baseline_record = _signed_record(root, name="baseline-record", transition="bootstrap", payload_path=baseline_payload, current=current, instrument_path=instrument_path, manifest_path=manifest_path, private=promoter_private, public=promoter_public)
    apply_signed_record(record_path=baseline_record, current_path=current, root_path=promotion_root)
    baseline_pointer = current.read_bytes()
    candidate_payload_path = root / "candidate-payload.json"
    candidate_payload = _payload(candidate_payload_path, "candidate", "1" * 64)
    candidate_record = _signed_record(root, name="candidate-record", transition="bootstrap", payload_path=candidate_payload_path, current=current, instrument_path=instrument_path, manifest_path=manifest_path, private=promoter_private, public=promoter_public)
    original = candidate_payload_path.read_bytes()
    candidate_payload["policy_parameters"]["policy_tuning"]["tuning_id"] = "tampered"
    atomic_write_json(candidate_payload_path, candidate_payload)
    before_bad = current.read_bytes()
    tampered_rejected = False
    try:
        apply_signed_record(record_path=candidate_record, current_path=current, root_path=promotion_root)
    except ValueError:
        tampered_rejected = current.read_bytes() == before_bad
    candidate_payload_path.write_bytes(original)
    apply_signed_record(record_path=candidate_record, current_path=current, root_path=promotion_root)
    candidate_pointer = current.read_bytes()
    loaded, _ = load_current_policy_payload(current, promotion_root=promotion_root)
    rollback_record = _signed_record(root, name="rollback-record", transition="rollback", payload_path=baseline_payload, current=current, instrument_path=instrument_path, manifest_path=manifest_path, private=promoter_private, public=promoter_public, restore=json.loads(baseline_pointer))
    apply_signed_record(record_path=rollback_record, current_path=current, root_path=promotion_root)
    result = {
        "payload_hash_verified": loaded["content_sha256"] == load_json(candidate_payload_path)["content_sha256"],
        "record_signature_verified": True,
        "instrument_epoch_verified": True,
        "binding_manifest_verified": binding_ok,
        "all_attestations_passed": True,
        "tampered_payload_rejected": tampered_rejected,
        "bad_record_left_current_unchanged": tampered_rejected,
        "valid_record_promoted_atomically": candidate_pointer != baseline_pointer,
        "signed_rollback_restored_pointer": current.read_bytes() == baseline_pointer,
        "runtime_loaded_exact_payload_hash": loaded["content_sha256"] == load_json(candidate_payload_path)["content_sha256"],
    }
    promoter_private.unlink()
    wave_private.unlink()
    return result, [("promotion_public_key", promoter_public), ("promotion_record", candidate_record), ("rollback_record", rollback_record), ("binding_manifest", manifest_path)]


def collect_learning_evidence(case: str, scenario_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
    root = Path(scenario_dir) / "p13_learning"
    root.mkdir(parents=True, exist_ok=True)
    if case in {"optimizer_write_boundary", "holdout_non_exposure"}:
        report, partitions, artifacts = _optimizer_fixture(root)
        return {"optimizer_execution": report, "learning_partitions": partitions}, artifacts
    if case == "reward_identity_provenance":
        evidence, artifacts = _reward_fixture(root)
        return {"reward_ingress": evidence}, artifacts
    if case == "signed_policy_promotion":
        evidence, artifacts = _promotion_fixture(root)
        return {"policy_promotion": evidence}, artifacts
    raise KeyError(case)
