from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from jsonschema import Draft202012Validator


APP_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ARCHIVE_ROOT = APP_ROOT / "experiments" / "learning" / "archive" / "artifacts"
HEX64 = set("0123456789abcdef")


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _schema(name: str) -> dict[str, Any]:
    return load_json(APP_ROOT / "contracts" / name)


def validate_schema(payload: dict[str, Any], name: str) -> None:
    errors = sorted(Draft202012Validator(_schema(name)).iter_errors(payload), key=lambda row: list(row.path))
    if errors:
        error = errors[0]
        location = ".".join(str(value) for value in error.path) or "$"
        raise ValueError(f"{name} validation failed at {location}: {error.message}")


def _without(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    result = dict(payload)
    for key in keys:
        result.pop(key, None)
    return result


def policy_payload_hash(payload: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_without(payload, "content_sha256")))


def validate_policy_payload(payload: dict[str, Any]) -> None:
    validate_schema(payload, "policy_payload.schema.json")
    if payload["content_sha256"] != policy_payload_hash(payload):
        raise ValueError("PolicyPayload content hash mismatch")


def artifact_ref(path: Path) -> dict[str, str]:
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(APP_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"learning artifact must be inside the app root: {resolved}") from exc
    return {"path": relative, "sha256": sha256_file(resolved)}


def resolve_artifact(ref: dict[str, Any]) -> Path:
    relative = str(ref.get("path", ""))
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"unsafe learning artifact path: {relative}")
    expected_sha256 = str(ref.get("sha256", ""))
    path = (APP_ROOT / relative).resolve()
    if not path.is_file() and len(expected_sha256) == 64 and set(expected_sha256) <= HEX64:
        archived = (ARTIFACT_ARCHIVE_ROOT / f"{expected_sha256}.json").resolve()
        if archived.is_relative_to(ARTIFACT_ARCHIVE_ROOT.resolve()) and archived.is_file():
            path = archived
    if not path.is_file() or sha256_file(path) != expected_sha256:
        raise ValueError(f"learning artifact identity mismatch: {relative}")
    return path


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row {line_number} is not an object: {path}")
        rows.append(row)
    if not rows:
        raise ValueError(f"learning partition is empty: {path}")
    return rows


def validate_partition_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    validate_schema(manifest, "learning_partition_manifest.schema.json")
    expected_hash = sha256_bytes(canonical_json_bytes(_without(manifest, "manifest_sha256")))
    if manifest["manifest_sha256"] != expected_hash:
        raise ValueError("learning partition manifest content hash mismatch")
    roles: dict[str, dict[str, Any]] = {}
    family_sets: dict[str, set[str]] = {}
    times: dict[str, tuple[datetime, datetime]] = {}
    for role in ("search", "holdout", "forward_shadow"):
        descriptor = manifest[role]
        path = resolve_artifact({"path": descriptor["artifact_path"], "sha256": descriptor["artifact_sha256"]})
        rows = _jsonl(path)
        if len(rows) != descriptor["row_count"]:
            raise ValueError(f"{role} row count mismatch")
        families = {str(row.get("family_id", "")) for row in rows}
        if "" in families:
            raise ValueError(f"{role} row is missing family_id")
        family_hash = sha256_bytes(canonical_json_bytes(sorted(families)))
        if family_hash != descriptor["family_set_sha256"]:
            raise ValueError(f"{role} family-set hash mismatch")
        starts = datetime.fromisoformat(str(descriptor["starts_at"]).replace("Z", "+00:00"))
        ends = datetime.fromisoformat(str(descriptor["ends_at"]).replace("Z", "+00:00"))
        if starts > ends:
            raise ValueError(f"{role} time range is inverted")
        roles[role] = descriptor
        family_sets[role] = families
        times[role] = (starts, ends)
    hashes = [roles[role]["artifact_sha256"] for role in roles]
    pairwise = (
        family_sets["search"].isdisjoint(family_sets["holdout"])
        and family_sets["search"].isdisjoint(family_sets["forward_shadow"])
        and family_sets["holdout"].isdisjoint(family_sets["forward_shadow"])
    )
    computed = {
        "artifact_hashes_distinct": len(set(hashes)) == 3,
        "family_sets_pairwise_disjoint": pairwise,
        "forward_shadow_starts_after_search": times["forward_shadow"][0] > times["search"][1],
    }
    if computed != manifest["disjointness"]:
        raise ValueError(f"learning partition disjointness mismatch: {computed}")
    if not all(computed.values()):
        raise ValueError(f"learning partitions are not admissible: {computed}")
    return manifest


def validate_optimizer_report(report: dict[str, Any], partition_manifest: dict[str, Any]) -> None:
    validate_schema(report, "optimizer_execution_report.schema.json")
    if report.get("decision") != "pass":
        raise ValueError("optimizer execution did not pass")
    if report.get("search_artifact_sha256") != partition_manifest["search"]["artifact_sha256"]:
        raise ValueError("optimizer search artifact is not the partition-manifest search rail")
    required = {
        ("holdout", "read"),
        ("forward_shadow", "read"),
        ("evaluator", "write"),
        ("manifest", "write"),
        ("current", "write"),
        ("effect_tcb", "write"),
    }
    denied = {
        (str(row.get("kind")), str(row.get("operation")))
        for row in report.get("attempts", [])
        if row.get("outcome") == "denied" and row.get("errno") in {1, 13}
    }
    if not required.issubset(denied):
        raise ValueError(f"optimizer protected attempts were not denied: {sorted(required - denied)}")
    proposal_path = resolve_artifact(report["proposal"])
    payload = load_json(proposal_path)
    validate_policy_payload(payload)
    if payload["training"]["row_set_sha256"] != partition_manifest["search"]["artifact_sha256"]:
        raise ValueError("PolicyPayload training hash is not the search partition")


def global_occurrence_id(issuer_id: str, event_id: str) -> str:
    return sha256_bytes(issuer_id.encode("utf-8") + b"\0" + event_id.encode("utf-8"))


def _openssl_verify(payload: bytes, signature: bytes, public_key: Path) -> bool:
    with tempfile.NamedTemporaryFile(prefix="p13-learning-", suffix=".sig") as handle:
        handle.write(signature)
        handle.flush()
        process = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", handle.name],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    return process.returncode == 0


def _openssl_sign(payload: bytes, private_key: Path) -> bytes:
    process = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(private_key)],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise ValueError(process.stderr.decode("utf-8", errors="replace") or "OpenSSL signing failed")
    return process.stdout


def sign_reward_event(event: dict[str, Any], private_key: Path) -> dict[str, Any]:
    unsigned = _without(event, "payload_sha256", "signature")
    result = dict(unsigned)
    result["payload_sha256"] = sha256_bytes(canonical_json_bytes(unsigned))
    result["signature"] = {
        "algorithm": "rsa-sha256",
        "value_base64": base64.b64encode(_openssl_sign(canonical_json_bytes(unsigned), private_key)).decode("ascii"),
    }
    return result


def validate_reward_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    validate_schema(ledger, "reward_ingress_ledger.schema.json")
    registry: dict[str, dict[str, Any]] = {}
    for row in ledger["issuer_registry"]:
        issuer = str(row["issuer_id"])
        if issuer in registry:
            raise ValueError(f"duplicate reward issuer: {issuer}")
        key = resolve_artifact({"path": row["public_key_path"], "sha256": row["public_key_sha256"]})
        registry[issuer] = {**row, "key": key}
    by_occurrence: dict[str, dict[str, Any]] = {}
    source_class: dict[str, str] = {}
    for event in ledger["events"]:
        issuer = str(event["issuer_id"])
        if issuer not in registry:
            raise ValueError(f"unregistered reward issuer: {issuer}")
        expected_id = global_occurrence_id(issuer, str(event["event_id"]))
        if event["global_occurrence_id"] != expected_id:
            raise ValueError("reward global occurrence identity mismatch")
        if expected_id in by_occurrence:
            if canonical_json_bytes(by_occurrence[expected_id]) != canonical_json_bytes(event):
                raise ValueError("conflicting duplicate reward occurrence")
            raise ValueError("duplicate reward occurrence")
        unsigned = _without(event, "payload_sha256", "signature")
        payload = canonical_json_bytes(unsigned)
        if event["payload_sha256"] != sha256_bytes(payload):
            raise ValueError("reward event payload hash mismatch")
        try:
            signature = base64.b64decode(event["signature"]["value_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("invalid reward signature encoding") from exc
        if not _openssl_verify(payload, signature, registry[issuer]["key"]):
            raise ValueError("reward issuer signature verification failed")
        by_occurrence[expected_id] = event
        source_class[expected_id] = str(registry[issuer]["source_class"])
    visiting: set[str] = set()
    memo: dict[str, set[str]] = {}

    def ancestry(occurrence_id: str) -> set[str]:
        if occurrence_id in memo:
            return memo[occurrence_id]
        if occurrence_id in visiting:
            raise ValueError("reward causal graph contains a cycle")
        visiting.add(occurrence_id)
        event = by_occurrence[occurrence_id]
        classes = {source_class[occurrence_id]}
        for parent in event["parent_occurrence_ids"]:
            if parent not in by_occurrence:
                raise ValueError(f"reward causal parent is unresolved: {parent}")
            classes.update(ancestry(parent))
        visiting.remove(occurrence_id)
        memo[occurrence_id] = classes
        return classes

    for occurrence_id, event in by_occurrence.items():
        classes = ancestry(occurrence_id)
        positive_program_a = event["program"] == "program_a_human_utility" and float(event["utility_credit"]) > 0.0
        if positive_program_a and classes != {"human"}:
            raise ValueError("simulator or synthetic evidence has direct or transitive positive human-utility credit")
        if source_class[occurrence_id] == "synthetic" and event["program"] == "program_a_human_utility":
            raise ValueError("synthetic evidence cannot be Program A feedback")
    return {
        "issuer_signatures_verified": True,
        "global_occurrence_ids_unique": True,
        "duplicate_conflict_rejected": True,
        "source_class_from_registry": True,
        "simulator_direct_positive_credit_rejected": True,
        "simulator_transitive_positive_credit_rejected": True,
        "synthetic_program_a_credit_rejected": True,
        "event_count": len(by_occurrence),
    }


def promotion_record_hash(record: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_without(record, "payload_sha256", "signature")))


def sign_promotion_record(record: dict[str, Any], private_key: Path, public_key: Path) -> dict[str, Any]:
    unsigned = _without(record, "payload_sha256", "signature")
    key_hash = sha256_file(public_key)
    if unsigned.get("signer", {}).get("public_key_sha256") != key_hash:
        raise ValueError("PromotionRecord signer does not match public key")
    payload = canonical_json_bytes(unsigned)
    result = dict(unsigned)
    result["payload_sha256"] = sha256_bytes(payload)
    result["signature"] = {
        "algorithm": "rsa-sha256",
        "value_base64": base64.b64encode(_openssl_sign(payload, private_key)).decode("ascii"),
    }
    validate_schema(result, "promotion_record.schema.json")
    return result


def load_promotion_root(path: Path | None = None) -> tuple[dict[str, Any], Path]:
    root = load_json(path or APP_ROOT / "configs/p13_learning_promotion_root.json")
    public_key = resolve_artifact({"path": root["public_key_path"], "sha256": root["public_key_sha256"]})
    return root, public_key


def validate_promotion_record(
    record: dict[str, Any],
    *,
    public_key: Path,
    current_bytes: bytes | None = None,
    promotion_root: Path | None = None,
) -> None:
    validate_schema(record, "promotion_record.schema.json")
    unsigned = _without(record, "payload_sha256", "signature")
    payload = canonical_json_bytes(unsigned)
    if record["payload_sha256"] != sha256_bytes(payload):
        raise ValueError("PromotionRecord payload hash mismatch")
    if record["signer"]["public_key_sha256"] != sha256_file(public_key):
        raise ValueError("PromotionRecord signer is not the pinned promoter root")
    try:
        signature = base64.b64decode(record["signature"]["value_base64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("invalid PromotionRecord signature encoding") from exc
    if not _openssl_verify(payload, signature, public_key):
        raise ValueError("PromotionRecord signature verification failed")
    root, _ = load_promotion_root(promotion_root)
    if record["instrument_bundle"]["instrument_epoch"] not in root["allowed_instrument_epochs"]:
        raise ValueError("PromotionRecord instrument epoch is not pinned")
    for key in ("payload", "partition_manifest"):
        resolve_artifact(record[key])
    for value in record["attestations"].values():
        resolve_artifact(value)
        if value.get("decision") != "pass":
            raise ValueError("PromotionRecord contains a non-pass attestation")
    if record["reward_evidence"] is not None:
        resolve_artifact(record["reward_evidence"])
        if record["reward_evidence"].get("decision") != "pass":
            raise ValueError("PromotionRecord contains non-pass reward evidence")
    instrument_path = resolve_artifact({"path": record["instrument_bundle"]["path"], "sha256": record["instrument_bundle"]["file_sha256"]})
    instrument = load_json(instrument_path)
    if instrument.get("bundle_sha256") != record["instrument_bundle"]["bundle_sha256"]:
        raise ValueError("PromotionRecord InstrumentBundle identity mismatch")
    resolve_artifact({"path": record["binding_manifest"]["path"], "sha256": record["binding_manifest"]["sha256"]})
    if current_bytes is not None and record["previous_current_sha256"] != sha256_bytes(current_bytes):
        raise ValueError("PromotionRecord previous CURRENT precondition mismatch")
    payload_obj = load_json(resolve_artifact(record["payload"]))
    validate_policy_payload(payload_obj)


def current_pointer(record_path: Path, record: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_policy_pointer_schema_version": "current_policy_pointer.v1",
        "promotion_record": artifact_ref(record_path),
        "payload_sha256": record["payload"]["sha256"],
        "transition": record["transition"],
    }


def load_current_policy_payload(current_path: Path, *, promotion_root: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    current = load_json(current_path)
    if current.get("current_policy_pointer_schema_version") != "current_policy_pointer.v1":
        raise ValueError("CURRENT is not a signed policy pointer")
    record_path = resolve_artifact(current["promotion_record"])
    record = load_json(record_path)
    _, public_key = load_promotion_root(promotion_root)
    validate_promotion_record(record, public_key=public_key, promotion_root=promotion_root)
    payload_path = resolve_artifact(record["payload"])
    payload = load_json(payload_path)
    if current.get("payload_sha256") != record["payload"]["sha256"]:
        raise ValueError("CURRENT payload identity does not match PromotionRecord")
    validate_policy_payload(payload)
    return payload, record
