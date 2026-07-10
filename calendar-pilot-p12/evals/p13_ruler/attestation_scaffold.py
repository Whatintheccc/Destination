from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import secrets
import stat
import subprocess
import tempfile
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


APP_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = APP_ROOT.parent
CONTRACT_ROOT = APP_ROOT / "contracts"

POLICY_SCHEMA = "p13_scaffolding_trust_policy.schema.json"
PACKET_SCHEMA = "p13_evaluation_packet_scaffold.schema.json"
REVIEW_SCHEMA = "p13_tcb_review_attestation_scaffold.schema.json"
REPORT_SCHEMA = "p13_attestation_scaffold_report.schema.json"

POLICY_VERSION = "p13_scaffolding_trust_policy.v1"
PACKET_VERSION = "p13_evaluation_packet.scaffold.v1"
REVIEW_VERSION = "p13_tcb_review_attestation.scaffold.v1"
REPORT_VERSION = "p13_attestation_scaffold_report.v1"

OPENSSL_PATH = Path("/usr/bin/openssl")
MAX_INPUT_BYTES = 8 * 1024 * 1024

DOMAIN_SEPARATORS = {
    PACKET_VERSION: b"calendar-pilot:p13_evaluation_packet.scaffold.v1\x00",
    REVIEW_VERSION: b"calendar-pilot:p13_tcb_review_attestation.scaffold.v1\x00",
}

DEFERRED_AUTHORITY = [
    "trusted_bootstrap_root",
    "durable_external_policy_governance",
    "pre_candidate_wave_authorization",
    "fresh_detached_checkout_identity_derivation",
    "isolated_evaluator_execution",
    "post_review_toctou_recheck",
    "evaluation_receipt",
    "protected_merge_and_deployment",
]


class ScaffoldError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ScaffoldError("duplicate_json_key", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ScaffoldError("nonfinite_json_number", f"non-finite JSON number: {value}")


def _reject_floats(value: Any, location: str = "$") -> None:
    if isinstance(value, float):
        raise ScaffoldError("floating_json_number", f"floating JSON number is forbidden at {location}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_floats(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_floats(item, f"{location}[{index}]")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _external_path(path: Path, kind: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ScaffoldError(f"{kind}_path_not_absolute", str(candidate))
    if any(part in {".", ".."} for part in candidate.parts[1:]):
        raise ScaffoldError(f"{kind}_path_not_normalized", str(candidate))
    if not candidate.name:
        raise ScaffoldError(f"{kind}_path_invalid", str(candidate))
    if _is_within(candidate, GIT_ROOT.resolve()):
        raise ScaffoldError(f"{kind}_inside_candidate_workspace", str(candidate))
    return candidate


def _git_marker_present(directory_fd: int) -> bool:
    try:
        os.stat(".git", dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ScaffoldError("external_directory_unavailable", str(exc)) from exc
    return True


def _open_external_directory(path: Path, kind: str) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        directory_fd = os.open("/", flags)
    except OSError as exc:
        raise ScaffoldError(f"{kind}_parent_unavailable", "/") from exc
    try:
        if _git_marker_present(directory_fd):
            raise ScaffoldError(f"{kind}_inside_git_worktree", str(path))
        for component in path.parts[1:]:
            try:
                next_fd = os.open(component, flags, dir_fd=directory_fd)
            except FileNotFoundError as exc:
                raise ScaffoldError(f"{kind}_parent_missing", str(path)) from exc
            except OSError as exc:
                raise ScaffoldError(f"{kind}_path_symlink_escape", str(path)) from exc
            os.close(directory_fd)
            directory_fd = next_fd
            if _git_marker_present(directory_fd):
                raise ScaffoldError(f"{kind}_inside_git_worktree", str(path))
        return directory_fd, os.fstat(directory_fd)
    except Exception:
        os.close(directory_fd)
        raise


def _directory_path_matches(path: Path, expected: os.stat_result, kind: str) -> None:
    check_fd, current = _open_external_directory(path, kind)
    os.close(check_fd)
    if expected.st_dev != current.st_dev or expected.st_ino != current.st_ino:
        raise ScaffoldError(f"{kind}_parent_mutated", str(path))


def _lstat_at(directory_fd: int, name: str, missing_code: str, detail: str) -> os.stat_result:
    try:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise ScaffoldError(missing_code, detail) from exc
    except OSError as exc:
        raise ScaffoldError("external_path_unavailable", detail) from exc


def _read_external_bytes(path: Path) -> tuple[Path, bytes]:
    resolved = _external_path(path, "input")
    directory_fd, parent_before = _open_external_directory(resolved.parent, "input")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        current = _lstat_at(directory_fd, resolved.name, "input_missing", str(resolved))
        if stat.S_ISLNK(current.st_mode):
            raise ScaffoldError("input_path_symlink", str(resolved))
        try:
            descriptor = os.open(resolved.name, flags, dir_fd=directory_fd)
        except OSError as exc:
            raise ScaffoldError("input_unavailable", str(resolved)) from exc
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise ScaffoldError("input_not_file", str(resolved))
            if before.st_nlink != 1:
                raise ScaffoldError("input_hardlink", str(resolved))
            if before.st_size > MAX_INPUT_BYTES:
                raise ScaffoldError("input_too_large", str(resolved))
            chunks: list[bytes] = []
            remaining = MAX_INPUT_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
            if len(payload) > MAX_INPUT_BYTES:
                raise ScaffoldError("input_too_large", str(resolved))
            after = os.fstat(descriptor)
            current = _lstat_at(directory_fd, resolved.name, "input_mutated_during_read", str(resolved))
            stable_fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
            if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
                raise ScaffoldError("input_mutated_during_read", str(resolved))
            if any(getattr(before, field) != getattr(current, field) for field in stable_fields):
                raise ScaffoldError("input_mutated_during_read", str(resolved))
            _directory_path_matches(resolved.parent, parent_before, "input")
            return resolved, payload
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)


def write_external_json(path: Path, payload: dict[str, Any]) -> Path:
    candidate = _external_path(path, "output")
    directory_fd, parent = _open_external_directory(candidate.parent, "output")
    temporary_name = f".{candidate.name}.{secrets.token_hex(16)}"
    created = False
    try:
        try:
            current = os.stat(candidate.name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            current = None
        if current is not None and stat.S_ISLNK(current.st_mode):
            raise ScaffoldError("output_path_symlink", str(candidate))
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            output_fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        except OSError as exc:
            raise ScaffoldError("output_unavailable", str(candidate)) from exc
        created = True
        try:
            encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
            view = memoryview(encoded)
            while view:
                try:
                    written = os.write(output_fd, view)
                except OSError as exc:
                    raise ScaffoldError("output_write", str(candidate)) from exc
                if written <= 0:
                    raise ScaffoldError("output_write", str(candidate))
                view = view[written:]
            try:
                os.fsync(output_fd)
            except OSError as exc:
                raise ScaffoldError("output_fsync", str(candidate)) from exc
        finally:
            os.close(output_fd)
        _directory_path_matches(candidate.parent, parent, "output")
        try:
            os.replace(temporary_name, candidate.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        except OSError as exc:
            raise ScaffoldError("output_replace", str(candidate)) from exc
        created = False
        try:
            os.fsync(directory_fd)
        except OSError as exc:
            raise ScaffoldError("output_fsync", str(candidate)) from exc
        _directory_path_matches(candidate.parent, parent, "output")
        return candidate
    finally:
        if created:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except OSError:
                pass
        os.close(directory_fd)


def _load_schema(name: str) -> dict[str, Any]:
    payload = json.loads((CONTRACT_ROOT / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def strict_load_json(path: Path, schema_name: str) -> dict[str, Any]:
    resolved, encoded = _read_external_bytes(path)
    try:
        text = encoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ScaffoldError("invalid_utf8", str(resolved)) from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except json.JSONDecodeError as exc:
        raise ScaffoldError("invalid_json", f"{resolved}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ScaffoldError("json_not_object", str(resolved))
    _reject_floats(payload)
    validator = Draft202012Validator(_load_schema(schema_name), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(f"{list(error.absolute_path)}: {error.message}" for error in errors[:8])
        raise ScaffoldError("schema_validation", f"{schema_name}: {details}")
    return payload


def policy_content_sha256(policy: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(policy))


def _record_version(record: dict[str, Any]) -> str:
    for key in ("evaluation_packet_schema_version", "tcb_review_attestation_schema_version"):
        value = record.get(key)
        if isinstance(value, str):
            return value
    raise ScaffoldError("record_version", "signed record has no recognized version")


def signed_record_bytes(record: dict[str, Any]) -> bytes:
    version = _record_version(record)
    separator = DOMAIN_SEPARATORS.get(version)
    if separator is None:
        raise ScaffoldError("record_version", f"unsupported signed record version: {version}")
    if "payload_sha256" not in record or "signature" not in record:
        raise ScaffoldError("signed_record_shape", "signed record lacks payload hash or signature")
    unsigned = {key: value for key, value in record.items() if key not in {"payload_sha256", "signature"}}
    return separator + canonical_json_bytes(unsigned)


def signed_record_payload_sha256(record: dict[str, Any]) -> str:
    return sha256_bytes(signed_record_bytes(record))


def candidate_identity_sha256(candidate: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in candidate.items() if key != "identity_sha256"}
    return sha256_bytes(canonical_json_bytes(unsigned))


def effect_tcb_path_set_sha256(entries: list[dict[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes([entry["repository_relative_path"] for entry in entries]))


def effect_tcb_blob_set_sha256(entries: list[dict[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes(entries))


def _validate_effect_tcb(effect_tcb: dict[str, Any]) -> None:
    entries = effect_tcb["entries"]
    paths = [entry["repository_relative_path"] for entry in entries]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ScaffoldError("effect_tcb_path_order", "effect TCB paths must be unique and lexically sorted")
    for path, entry in zip(paths, entries):
        parsed = PurePosixPath(path)
        if path.startswith("/") or "\\" in path or any(part in {"", ".", ".."} for part in parsed.parts):
            raise ScaffoldError("effect_tcb_path", path)
        if str(parsed) != path:
            raise ScaffoldError("effect_tcb_path", path)
        if entry["before"] is None and entry["after"] is None:
            raise ScaffoldError("effect_tcb_empty_transition", path)
    if effect_tcb["entry_count"] != len(entries):
        raise ScaffoldError("effect_tcb_entry_count", str(effect_tcb["entry_count"]))
    if effect_tcb["path_set_sha256"] != effect_tcb_path_set_sha256(entries):
        raise ScaffoldError("effect_tcb_path_hash_mismatch", effect_tcb["path_set_sha256"])
    if effect_tcb["blob_set_sha256"] != effect_tcb_blob_set_sha256(entries):
        raise ScaffoldError("effect_tcb_blob_hash_mismatch", effect_tcb["blob_set_sha256"])


def _parse_time(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScaffoldError("invalid_timestamp", f"{field}: {value}") from exc
    if parsed.tzinfo is None:
        raise ScaffoldError("invalid_timestamp", f"{field} has no timezone")
    return parsed.astimezone(timezone.utc)


def _decode_base64(value: Any, field: str) -> bytes:
    try:
        return base64.b64decode(str(value), validate=True)
    except (ValueError, TypeError) as exc:
        raise ScaffoldError("invalid_base64", field) from exc


def _verify_rsa_signature(record: dict[str, Any], role: dict[str, Any]) -> None:
    expected_hash = signed_record_payload_sha256(record)
    if record.get("payload_sha256") != expected_hash:
        raise ScaffoldError("payload_hash_mismatch", _record_version(record))
    der = _decode_base64(role.get("spki_der_base64"), "spki_der_base64")
    if sha256_bytes(der) != role.get("public_key_sha256"):
        raise ScaffoldError("policy_key_hash_mismatch", str(role.get("key_id")))
    signature = _decode_base64(record.get("signature", {}).get("value_base64"), "signature.value_base64")
    try:
        openssl = OPENSSL_PATH.resolve(strict=True)
        openssl_stat = openssl.stat()
    except OSError as exc:
        raise ScaffoldError("trusted_openssl_unavailable", str(OPENSSL_PATH)) from exc
    if openssl != OPENSSL_PATH or not stat.S_ISREG(openssl_stat.st_mode):
        raise ScaffoldError("trusted_openssl_path", str(OPENSSL_PATH))
    if openssl_stat.st_uid != 0 or openssl_stat.st_mode & 0o022:
        raise ScaffoldError("trusted_openssl_permissions", str(OPENSSL_PATH))
    verifier_env = {
        "HOME": "/nonexistent",
        "LANG": "C",
        "LC_ALL": "C",
        "OPENSSL_CONF": "/dev/null",
        "PATH": "/usr/bin:/bin",
    }
    with tempfile.TemporaryDirectory(prefix="p13-attestation-verify-") as directory:
        root = Path(directory)
        der_path = root / "key.der"
        pem_path = root / "key.pem"
        signature_path = root / "signature.bin"
        der_path.write_bytes(der)
        signature_path.write_bytes(signature)
        convert = subprocess.run(
            [str(openssl), "pkey", "-pubin", "-inform", "DER", "-in", str(der_path), "-out", str(pem_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=verifier_env,
            check=False,
        )
        if convert.returncode != 0:
            raise ScaffoldError("invalid_policy_public_key", str(role.get("key_id")))
        verify = subprocess.run(
            [str(openssl), "dgst", "-sha256", "-verify", str(pem_path), "-signature", str(signature_path)],
            input=signed_record_bytes(record),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=verifier_env,
            check=False,
        )
    if verify.returncode != 0:
        raise ScaffoldError("signature_verification", _record_version(record))


def _validate_role(role_name: str, role: dict[str, Any], policy: dict[str, Any], at: datetime) -> None:
    if role.get("key_id") in policy.get("revoked_key_ids", []):
        raise ScaffoldError("revoked_role_key", f"{role_name}:{role.get('key_id')}")
    not_before = _parse_time(role.get("not_before"), f"roles.{role_name}.not_before")
    not_after = _parse_time(role.get("not_after"), f"roles.{role_name}.not_after")
    if not_before > at or not_after <= at or not_before >= not_after:
        raise ScaffoldError("role_key_inactive", role_name)
    der = _decode_base64(role.get("spki_der_base64"), f"roles.{role_name}.spki_der_base64")
    if sha256_bytes(der) != role.get("public_key_sha256"):
        raise ScaffoldError("policy_key_hash_mismatch", role_name)


def _validate_policy(policy: dict[str, Any], now: datetime) -> None:
    if policy.get("scaffolding_trust_policy_schema_version") != POLICY_VERSION:
        raise ScaffoldError("policy_version", str(policy.get("scaffolding_trust_policy_schema_version")))
    if policy.get("mode") != "scaffold_only":
        raise ScaffoldError("policy_mode", str(policy.get("mode")))
    valid_from = _parse_time(policy.get("valid_from"), "policy.valid_from")
    expires_at = _parse_time(policy.get("expires_at"), "policy.expires_at")
    if valid_from > now or expires_at <= now or valid_from >= expires_at:
        raise ScaffoldError("policy_inactive", str(policy.get("policy_id")))
    roles = policy["roles"]
    role_rows = [roles[name] for name in ("operator_authorizer", "isolated_evaluator", "independent_tcb_reviewer")]
    if len({row["key_id"] for row in role_rows}) != len(role_rows):
        raise ScaffoldError("role_key_id_collision", "required roles share a key id")
    if len({row["public_key_sha256"] for row in role_rows}) != len(role_rows):
        raise ScaffoldError("role_key_collision", "required roles share a public key")
    if len({row["principal_id"] for row in role_rows}) != len(role_rows):
        raise ScaffoldError("role_principal_collision", "required roles share a principal")
    reviewer = roles["independent_tcb_reviewer"]
    if reviewer["principal_id"] in policy.get("protected_candidate_principals", []):
        raise ScaffoldError("reviewer_author_collision", reviewer["principal_id"])
    for name, role in roles.items():
        _validate_role(name, role, policy, now)
        role_start = _parse_time(role["not_before"], f"roles.{name}.not_before")
        role_end = _parse_time(role["not_after"], f"roles.{name}.not_after")
        if role_start < valid_from or role_end > expires_at:
            raise ScaffoldError("role_validity_outside_policy", name)


def _validate_packet(packet: dict[str, Any], policy: dict[str, Any], policy_hash: str, now: datetime) -> None:
    if packet.get("evaluation_packet_schema_version") != PACKET_VERSION:
        raise ScaffoldError("packet_version", str(packet.get("evaluation_packet_schema_version")))
    policy_ref = packet["policy"]
    if policy_ref != {
        "policy_id": policy["policy_id"],
        "policy_epoch": policy["policy_epoch"],
        "content_sha256": policy_hash,
    }:
        raise ScaffoldError("packet_policy_mismatch", str(packet.get("packet_id")))
    if packet["candidate"]["repository_origin_id"] != policy["repository_origin_id"]:
        raise ScaffoldError("packet_repository_mismatch", str(packet.get("packet_id")))
    if packet["candidate"]["identity_sha256"] != candidate_identity_sha256(packet["candidate"]):
        raise ScaffoldError("candidate_identity_mismatch", str(packet.get("packet_id")))
    _validate_effect_tcb(packet["effect_tcb"])
    evaluator = policy["roles"]["isolated_evaluator"]
    if packet["evaluator"]["principal_id"] != evaluator["principal_id"] or packet["evaluator"]["key_id"] != evaluator["key_id"]:
        raise ScaffoldError("packet_evaluator_mismatch", str(packet.get("packet_id")))
    issued_at = _parse_time(packet["issued_at"], "packet.issued_at")
    expires_at = _parse_time(packet["expires_at"], "packet.expires_at")
    policy_start = _parse_time(policy["valid_from"], "policy.valid_from")
    policy_end = _parse_time(policy["expires_at"], "policy.expires_at")
    if issued_at < policy_start or issued_at > now or expires_at <= now or issued_at >= expires_at or expires_at > policy_end:
        raise ScaffoldError("packet_time_order", str(packet.get("packet_id")))
    _validate_role("isolated_evaluator", evaluator, policy, issued_at)
    _verify_rsa_signature(packet, evaluator)


def _validate_review(
    review: dict[str, Any],
    packet: dict[str, Any],
    policy: dict[str, Any],
    policy_hash: str,
    now: datetime,
) -> None:
    if review.get("tcb_review_attestation_schema_version") != REVIEW_VERSION:
        raise ScaffoldError("review_version", str(review.get("tcb_review_attestation_schema_version")))
    if review["policy"] != packet["policy"] or review["policy"]["content_sha256"] != policy_hash:
        raise ScaffoldError("review_policy_mismatch", str(review.get("review_id")))
    if review["packet"] != {"packet_id": packet["packet_id"], "payload_sha256": packet["payload_sha256"]}:
        raise ScaffoldError("review_packet_mismatch", str(review.get("review_id")))
    if review["candidate_identity_sha256"] != packet["candidate"]["identity_sha256"]:
        raise ScaffoldError("review_candidate_mismatch", str(review.get("review_id")))
    if review["tcb_path_set_sha256"] != packet["effect_tcb"]["path_set_sha256"]:
        raise ScaffoldError("review_tcb_path_mismatch", str(review.get("review_id")))
    if review["tcb_blob_set_sha256"] != packet["effect_tcb"]["blob_set_sha256"]:
        raise ScaffoldError("review_tcb_blob_mismatch", str(review.get("review_id")))
    reviewer = policy["roles"]["independent_tcb_reviewer"]
    if review["reviewer"] != {"principal_id": reviewer["principal_id"], "key_id": reviewer["key_id"]}:
        raise ScaffoldError("reviewer_role_mismatch", str(review.get("review_id")))
    packet_issued = _parse_time(packet["issued_at"], "packet.issued_at")
    packet_expires = _parse_time(packet["expires_at"], "packet.expires_at")
    issued_at = _parse_time(review["issued_at"], "review.issued_at")
    expires_at = _parse_time(review["expires_at"], "review.expires_at")
    if issued_at < packet_issued or issued_at > now or expires_at <= now or issued_at >= expires_at or expires_at > packet_expires:
        raise ScaffoldError("review_time_order", str(review.get("review_id")))
    _validate_role("independent_tcb_reviewer", reviewer, policy, issued_at)
    _verify_rsa_signature(review, reviewer)


def _base_report() -> dict[str, Any]:
    return {
        "attestation_scaffold_report_schema_version": REPORT_VERSION,
        "decision": "hold",
        "authorizes_migration": False,
        "mechanics_valid": False,
        "policy_provenance_verified": False,
        "trust_root_status": "unanchored_scaffold",
        "policy_id": None,
        "packet_id": None,
        "review_id": None,
        "review_decision": None,
        "checks": [],
        "failures": [],
        "hold_reasons": [
            {
                "code": "external_authority_not_provisioned",
                "detail": "scaffold mechanics do not establish migration authority",
            },
            {
                "code": "policy_provenance_unverified",
                "detail": "the scaffold policy is self-declared and has no trusted bootstrap-root binding",
            },
        ],
        "deferred_authority": list(DEFERRED_AUTHORITY),
    }


def verify_attestation_scaffold(
    *,
    policy_path: Path | None,
    packet_path: Path | None,
    review_path: Path | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    report = _base_report()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    missing_input_codes = {"input_missing", "input_parent_missing", "input_unavailable"}

    def hold(name: str, code: str, detail: str) -> dict[str, Any]:
        report["checks"].append({"name": name, "status": "hold", "detail": detail})
        report["hold_reasons"].append({"code": code, "detail": detail})
        return report

    def fail(name: str, error: ScaffoldError) -> dict[str, Any]:
        report["checks"].append({"name": name, "status": "fail", "detail": error.detail})
        report["failures"].append({"code": error.code, "detail": error.detail})
        report["decision"] = "fail"
        return report

    if policy_path is None:
        return hold("policy", "policy_missing", "external scaffold policy was not supplied")
    try:
        policy = strict_load_json(policy_path, POLICY_SCHEMA)
        _validate_policy(policy, current)
    except ScaffoldError as error:
        if error.code in missing_input_codes:
            return hold("policy", "policy_missing", error.detail)
        return fail("policy", error)
    policy_hash = policy_content_sha256(policy)
    report["policy_id"] = policy["policy_id"]
    report["checks"].append(
        {
            "name": "policy",
            "status": "pass",
            "detail": "self-declared scaffold-only policy shape, timing, and role mechanics are valid; provenance is unverified",
        }
    )

    if packet_path is None:
        return hold("packet", "packet_missing", "external evaluation packet was not supplied")
    try:
        packet = strict_load_json(packet_path, PACKET_SCHEMA)
        _validate_packet(packet, policy, policy_hash, current)
    except ScaffoldError as error:
        if error.code in missing_input_codes:
            return hold("packet", "packet_missing", error.detail)
        return fail("packet", error)
    report["packet_id"] = packet["packet_id"]
    report["checks"].append({"name": "packet", "status": "pass", "detail": "evaluator packet signature and content bindings are valid"})

    if review_path is None:
        return hold("review", "review_missing", "external TCB review attestation was not supplied")
    try:
        review = strict_load_json(review_path, REVIEW_SCHEMA)
        _validate_review(review, packet, policy, policy_hash, current)
    except ScaffoldError as error:
        if error.code in missing_input_codes:
            return hold("review", "review_missing", error.detail)
        return fail("review", error)
    report["review_id"] = review["review_id"]
    report["review_decision"] = review["decision"]
    report["checks"].append({"name": "review", "status": "pass", "detail": "review signature and exact packet bindings are valid"})
    report["mechanics_valid"] = True

    if review["decision"] == "reject":
        report["decision"] = "fail"
        report["failures"].append({"code": "review_rejected", "detail": review["reason"]})
    elif review["decision"] == "hold":
        report["hold_reasons"].append({"code": "review_hold", "detail": review["reason"]})
    else:
        report["hold_reasons"].append(
            {
                "code": "scaffold_approval_is_non_authorizing",
                "detail": "mechanically valid approval remains hold until the deferred external authority chain exists",
            }
        )
    return report


def validate_report_schema(report: dict[str, Any]) -> None:
    validator = Draft202012Validator(_load_schema(REPORT_SCHEMA), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(report), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(f"{list(error.absolute_path)}: {error.message}" for error in errors[:8])
        raise ScaffoldError("report_schema", details)
