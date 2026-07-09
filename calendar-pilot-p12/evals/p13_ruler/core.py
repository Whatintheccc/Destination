from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable


APP_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = APP_ROOT.parent
APP_REL = APP_ROOT.relative_to(GIT_ROOT).as_posix()
CHANGE_CLASSES = {"ruler", "migration", "compression", "learning"}
SCOPE_KEYS = ("actions", "backends", "surfaces", "instruments", "control_planes")
WAVE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")


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


def _run(command: list[str], *, cwd: Path, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _checked(command: list[str], *, cwd: Path, input_bytes: bytes | None = None) -> bytes:
    process = _run(command, cwd=cwd, input_bytes=input_bytes)
    if process.returncode != 0:
        error = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or f"command failed: {' '.join(command)}")
    return process.stdout


def git_text(*args: str, git_root: Path = GIT_ROOT) -> str:
    return _checked(["git", *args], cwd=git_root).decode("utf-8").strip()


def git_zlist(*args: str, git_root: Path = GIT_ROOT) -> list[str]:
    output = _checked(["git", *args], cwd=git_root)
    return [item.decode("utf-8") for item in output.split(b"\0") if item]


def repository_identity(*, git_root: Path = GIT_ROOT, app_rel: str = APP_REL) -> dict[str, Any]:
    status = _checked(["git", "status", "--porcelain=v1", "-z"], cwd=git_root)
    return {
        "git_sha": git_text("rev-parse", "HEAD", git_root=git_root),
        "app_tree_sha": git_text("rev-parse", f"HEAD:{app_rel}", git_root=git_root),
        "app_path": app_rel,
        "dirty": bool(status),
        "git_status_sha256": sha256_bytes(status),
    }


def require_clean_repository(*, git_root: Path = GIT_ROOT) -> None:
    status = _checked(["git", "status", "--porcelain=v1", "-z"], cwd=git_root)
    if status:
        paths = [row for row in status.decode("utf-8", errors="replace").split("\0") if row]
        raise ValueError(f"binding artifacts require a clean repository: {paths[:8]}")


def _line_count(payload: bytes) -> int:
    # Match the historical `wc -l` access point exactly: newline characters,
    # not a synthetic final logical line for files without a trailing newline.
    return payload.count(b"\n")


def _matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(_path_matches(path, pattern) for pattern in patterns)


def _path_matches(path: str, pattern: str) -> bool:
    expression = re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
    return re.fullmatch(expression, path) is not None


def build_loc_report(
    *,
    git_root: Path = GIT_ROOT,
    app_rel: str = APP_REL,
    exclusions: list[str] | None = None,
    before: dict[str, Any] | None = None,
) -> dict[str, Any]:
    exclusions = sorted(set(exclusions or []))
    source_root = f"{app_rel}/src"
    tracked = sorted(
        path
        for path in git_zlist("ls-files", "--cached", "-z", "--", source_root, git_root=git_root)
        if path.endswith(".py") and not _matches_any(path, exclusions)
    )
    untracked = sorted(
        path
        for path in git_zlist("ls-files", "--others", "--exclude-standard", "-z", "--", source_root, git_root=git_root)
        if path.endswith(".py") and not _matches_any(path, exclusions)
    )
    files: list[dict[str, Any]] = []
    for relative in tracked:
        path = git_root / relative
        if path.is_file():
            payload = path.read_bytes()
            files.append(
                {
                    "path": relative,
                    "status": "present",
                    "lines": _line_count(payload),
                    "sha256": sha256_bytes(payload),
                }
            )
        else:
            files.append({"path": relative, "status": "deleted", "lines": 0, "sha256": None})
    file_list_sha256 = sha256_bytes(canonical_json_bytes([row["path"] for row in files]))
    total_lines = sum(int(row["lines"]) for row in files)
    delta: dict[str, Any] | None = None
    if before is not None:
        before_by_path = {str(row["path"]): int(row["lines"]) for row in before.get("files", [])}
        after_by_path = {str(row["path"]): int(row["lines"]) for row in files}
        paths = sorted(set(before_by_path) | set(after_by_path))
        changed = [
            {
                "path": path,
                "before_lines": before_by_path.get(path, 0),
                "after_lines": after_by_path.get(path, 0),
                "delta_lines": after_by_path.get(path, 0) - before_by_path.get(path, 0),
            }
            for path in paths
            if before_by_path.get(path, 0) != after_by_path.get(path, 0)
        ]
        delta = {
            "before_report_sha256": sha256_bytes(canonical_json_bytes(before)),
            "before_total_lines": int(before.get("total_lines", 0)),
            "after_total_lines": total_lines,
            "delta_lines": total_lines - int(before.get("total_lines", 0)),
            "changed_files": changed,
        }
    identity = repository_identity(git_root=git_root, app_rel=app_rel)
    return {
        "p13_loc_report_schema_version": "p13_loc_report.v1",
        "decision": "hold" if untracked else "pass",
        "repository": identity,
        "scope": {"root": source_root, "extensions": [".py"]},
        "exclusions": exclusions,
        "file_list_sha256": file_list_sha256,
        "file_count": len(files),
        "files": files,
        "total_lines": total_lines,
        "untracked_source_files": untracked,
        "hold_reasons": (["untracked Python source is excluded from the tracked LOC ruler"] if untracked else []),
        "delta": delta,
    }


def _root_relative(path: Path, git_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(git_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"instrument artifact must be inside the repository: {path}") from exc


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _openssl_version() -> str:
    return _checked(["openssl", "version"], cwd=GIT_ROOT).decode("utf-8").strip()


def build_instrument_bundle(
    *,
    verification_key: Path,
    artifact_config: Path,
    git_root: Path = GIT_ROOT,
    app_rel: str = APP_REL,
    require_clean: bool = True,
) -> dict[str, Any]:
    if require_clean:
        require_clean_repository(git_root=git_root)
    verification_key = Path(verification_key)
    if not verification_key.is_file():
        raise FileNotFoundError(f"verification key not found: {verification_key}")
    config = _load_json(artifact_config)
    if config.get("instrument_artifact_set_schema_version") != "p13_instrument_artifact_set.v1":
        raise ValueError("unsupported P13 instrument artifact-set version")
    rows = config.get("artifacts")
    if not isinstance(rows, list) or not rows:
        raise ValueError("instrument artifact set must contain artifacts")
    artifacts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"kind", "path"}:
            raise ValueError("instrument artifact rows require exactly kind and path")
        relative = str(row["path"])
        if relative.startswith("/") or ".." in Path(relative).parts or relative in seen:
            raise ValueError(f"unsafe or duplicate instrument artifact path: {relative}")
        seen.add(relative)
        path = git_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"instrument artifact not found: {relative}")
        artifacts.append(
            {
                "kind": str(row["kind"]),
                "path": relative,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    artifacts.sort(key=lambda row: (row["kind"], row["path"]))
    payload: dict[str, Any] = {
        "p13_instrument_bundle_schema_version": "p13_instrument_bundle.v1",
        "instrument_epoch": str(config.get("instrument_epoch", "p13.0")),
        "repository": repository_identity(git_root=git_root, app_rel=app_rel),
        "verification_root": {
            "algorithm": "rsa-sha256",
            "public_key_sha256": sha256_file(verification_key),
        },
        "toolchain": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "openssl": _openssl_version(),
        },
        "artifacts": artifacts,
    }
    payload["bundle_sha256"] = sha256_bytes(canonical_json_bytes(payload))
    return payload


def validate_instrument_bundle(
    bundle: dict[str, Any],
    *,
    verification_key: Path | None = None,
    git_root: Path = GIT_ROOT,
    check_artifacts: bool = True,
) -> None:
    if bundle.get("p13_instrument_bundle_schema_version") != "p13_instrument_bundle.v1":
        raise ValueError("unsupported P13 instrument bundle version")
    expected = dict(bundle)
    recorded_hash = str(expected.pop("bundle_sha256", ""))
    if recorded_hash != sha256_bytes(canonical_json_bytes(expected)):
        raise ValueError("instrument bundle content hash mismatch")
    if verification_key is not None:
        actual_key_hash = sha256_file(Path(verification_key))
        if actual_key_hash != bundle.get("verification_root", {}).get("public_key_sha256"):
            raise ValueError("instrument verification root mismatch")
    if check_artifacts:
        for artifact in bundle.get("artifacts", []):
            path = git_root / str(artifact.get("path", ""))
            if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
                raise ValueError(f"instrument artifact hash mismatch: {path}")


def _unsigned_manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload.pop("payload_sha256", None)
    payload.pop("signature", None)
    return payload


def _sign(payload: bytes, private_key: Path, *, git_root: Path = GIT_ROOT) -> bytes:
    return _checked(
        ["openssl", "dgst", "-sha256", "-sign", str(private_key)],
        cwd=git_root,
        input_bytes=payload,
    )


def _verify_signature(payload: bytes, signature: bytes, public_key: Path, *, git_root: Path = GIT_ROOT) -> bool:
    with tempfile.NamedTemporaryFile(prefix="p13-binding-", suffix=".sig") as handle:
        handle.write(signature)
        handle.flush()
        process = _run(
            ["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", handle.name],
            cwd=git_root,
            input_bytes=payload,
        )
    return process.returncode == 0


def _validate_scope(scope: dict[str, Any]) -> None:
    if scope.get("wave_scope_schema_version") != "p13_wave_scope.v1":
        raise ValueError("unsupported P13 wave scope version")
    patterns = scope.get("declared_paths")
    if not isinstance(patterns, list) or not patterns:
        raise ValueError("wave scope requires declared_paths")
    for pattern in patterns:
        value = str(pattern)
        if value.startswith("/") or ".." in Path(value).parts:
            raise ValueError(f"unsafe declared path: {value}")
    declared = scope.get("declared")
    if not isinstance(declared, dict) or set(declared) != set(SCOPE_KEYS):
        raise ValueError(f"wave scope declared keys must be {SCOPE_KEYS}")
    for key in SCOPE_KEYS:
        if not isinstance(declared[key], list):
            raise ValueError(f"wave scope declared.{key} must be a list")
    required = scope.get("required_scenarios")
    if not isinstance(required, list):
        raise ValueError("wave scope required_scenarios must be a list")
    live_legs = scope.get("live_legs")
    if not isinstance(live_legs, list):
        raise ValueError("wave scope live_legs must be a list")
    live_leg_keys = {
        "leg", "status", "reason", "artifact", "owner", "sign_off",
        "affected_by_wave", "expires_at", "next_unblock_action",
    }
    for entry in live_legs:
        if not isinstance(entry, dict) or set(entry) != live_leg_keys:
            raise ValueError("live-leg entry does not match the versioned contract")
        status = entry.get("status")
        reason = entry.get("reason")
        artifact = entry.get("artifact")
        if status not in {"ran", "root-listed"}:
            raise ValueError("live-leg status must be ran or root-listed")
        if not isinstance(reason, dict) or set(reason) != {"basis", "detail"}:
            raise ValueError("live-leg reason requires exactly basis and detail")
        allowed_basis = {"ran"} if status == "ran" else {"unaffected", "unavailable"}
        if reason.get("basis") not in allowed_basis or not str(reason.get("detail", "")).strip():
            raise ValueError("live-leg reason basis does not match its status")
        if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
            raise ValueError("live-leg artifact requires exactly path and sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))):
            raise ValueError("live-leg artifact sha256 is invalid")
        if not isinstance(entry.get("affected_by_wave"), bool):
            raise ValueError("live-leg affected_by_wave must be boolean")
        for key in ["leg", "owner", "sign_off", "expires_at", "next_unblock_action"]:
            if not str(entry.get(key, "")).strip():
                raise ValueError(f"live-leg {key} is required")


def build_binding_manifest(
    *,
    wave: str,
    change_class: str,
    scope_path: Path,
    instrument_bundle_path: Path,
    ownership_map_path: Path,
    signing_key: Path,
    verification_key: Path,
    expires_in_hours: int = 24,
    now: datetime | None = None,
    git_root: Path = GIT_ROOT,
    app_rel: str = APP_REL,
    require_clean: bool = True,
) -> dict[str, Any]:
    if not WAVE_RE.fullmatch(wave):
        raise ValueError("wave id must be 2-64 lowercase letters, numbers, dot, underscore, or dash")
    if change_class not in CHANGE_CLASSES:
        raise ValueError(f"unsupported change class: {change_class}")
    if expires_in_hours <= 0:
        raise ValueError("manifest expiry must be positive")
    if require_clean:
        require_clean_repository(git_root=git_root)
    scope = _load_json(scope_path)
    _validate_scope(scope)
    bundle = _load_json(instrument_bundle_path)
    validate_instrument_bundle(bundle, verification_key=verification_key, git_root=git_root)
    ownership_map = _load_json(ownership_map_path)
    if ownership_map.get("ownership_map_schema_version") != "p13_ownership_map.v1":
        raise ValueError("unsupported P13 ownership map version")
    if sha256_file(verification_key) != bundle["verification_root"]["public_key_sha256"]:
        raise ValueError("signer verification key is not the InstrumentBundle root")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    identity = repository_identity(git_root=git_root, app_rel=app_rel)
    base: dict[str, Any] = {
        "binding_manifest_schema_version": "p13_binding_manifest.v1",
        "manifest_id": f"{wave}:{identity['git_sha'][:12]}:{now.strftime('%Y%m%dT%H%M%SZ')}",
        "wave": wave,
        "change_class": change_class,
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(hours=expires_in_hours)).isoformat().replace("+00:00", "Z"),
        "base_repository": identity,
        "instrument_bundle": {
            "path": _root_relative(instrument_bundle_path, git_root),
            "file_sha256": sha256_file(instrument_bundle_path),
            "bundle_sha256": bundle["bundle_sha256"],
        },
        "ownership_map": {
            "path": _root_relative(ownership_map_path, git_root),
            "sha256": sha256_file(ownership_map_path),
        },
        "scope_source": {
            "path": _root_relative(scope_path, git_root),
            "sha256": sha256_file(scope_path),
        },
        "declared_scope": {
            "paths": sorted(set(str(value) for value in scope["declared_paths"])),
            **{key: sorted(set(str(value) for value in scope["declared"][key])) for key in SCOPE_KEYS},
        },
        "required_scenarios": sorted(set(str(value) for value in scope["required_scenarios"])),
        "old_producer": scope.get("old_producer"),
        "new_producer": scope.get("new_producer"),
        "live_legs": scope.get("live_legs", []),
        "signer": {
            "algorithm": "rsa-sha256",
            "public_key_sha256": sha256_file(verification_key),
        },
    }
    unsigned = canonical_json_bytes(base)
    signature = _sign(unsigned, Path(signing_key), git_root=git_root)
    manifest = dict(base)
    manifest["payload_sha256"] = sha256_bytes(unsigned)
    manifest["signature"] = {"algorithm": "rsa-sha256", "value_base64": base64.b64encode(signature).decode("ascii")}
    return manifest


def derive_changed_paths(base_git_sha: str, *, git_root: Path = GIT_ROOT) -> list[str]:
    committed = git_zlist("diff", "--name-only", "-z", base_git_sha, "HEAD", git_root=git_root)
    working = git_zlist("diff", "--name-only", "-z", "HEAD", git_root=git_root)
    untracked = git_zlist("ls-files", "--others", "--exclude-standard", "-z", git_root=git_root)
    return sorted(set(committed) | set(working) | set(untracked))


def _ownership_for(path: str, ownership_map: dict[str, Any]) -> dict[str, set[str]]:
    derived = {key: set() for key in SCOPE_KEYS}
    matched = False
    for row in ownership_map.get("rules", []):
        if _path_matches(path, str(row.get("pattern", ""))):
            matched = True
            for key in SCOPE_KEYS:
                derived[key].update(str(value) for value in row.get(key, []))
    if not matched:
        derived["surfaces"].add("unowned")
    return derived


def verify_binding_manifest(
    manifest: dict[str, Any],
    *,
    verification_key: Path,
    changed_paths: list[str] | None = None,
    now: datetime | None = None,
    git_root: Path = GIT_ROOT,
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    instrument_changes: list[dict[str, Any]] = []

    def fail(code: str, detail: str) -> None:
        failures.append({"code": code, "detail": detail})

    if manifest.get("binding_manifest_schema_version") != "p13_binding_manifest.v1":
        fail("manifest_version", "unsupported binding manifest version")
    unsigned_payload = canonical_json_bytes(_unsigned_manifest_payload(manifest))
    if manifest.get("payload_sha256") != sha256_bytes(unsigned_payload):
        fail("manifest_payload_hash", "binding manifest payload hash mismatch")
    try:
        signature = base64.b64decode(str(manifest.get("signature", {}).get("value_base64", "")), validate=True)
    except (ValueError, TypeError):
        signature = b""
    if not signature or not _verify_signature(unsigned_payload, signature, Path(verification_key), git_root=git_root):
        fail("manifest_signature", "binding manifest signature verification failed")
    key_hash = sha256_file(Path(verification_key))
    if manifest.get("signer", {}).get("public_key_sha256") != key_hash:
        fail("manifest_signer", "binding manifest signer does not match verification root")
    try:
        expires_at = datetime.fromisoformat(str(manifest.get("expires_at", "")).replace("Z", "+00:00"))
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if expires_at <= current:
            fail("manifest_expired", f"binding manifest expired at {expires_at.isoformat()}")
    except ValueError:
        fail("manifest_expiry", "binding manifest expiry is invalid")

    actual_paths = changed_paths if changed_paths is not None else derive_changed_paths(
        str(manifest.get("base_repository", {}).get("git_sha", "")), git_root=git_root
    )
    actual_path_set = set(actual_paths)
    change_class = str(manifest.get("change_class", ""))
    bundle_ref = manifest.get("instrument_bundle", {})
    bundle_path = git_root / str(bundle_ref.get("path", ""))
    if not bundle_path.is_file() or sha256_file(bundle_path) != bundle_ref.get("file_sha256"):
        fail("instrument_bundle_file", "InstrumentBundle file is missing or changed")
        bundle: dict[str, Any] | None = None
    else:
        bundle = _load_json(bundle_path)
        try:
            validate_instrument_bundle(
                bundle,
                verification_key=verification_key,
                git_root=git_root,
                check_artifacts=change_class != "ruler",
            )
            if bundle.get("bundle_sha256") != bundle_ref.get("bundle_sha256"):
                fail("instrument_bundle_hash", "InstrumentBundle content identity changed")
            if change_class == "ruler":
                for artifact in bundle.get("artifacts", []):
                    relative = str(artifact.get("path", ""))
                    path = git_root / relative
                    actual_hash = sha256_file(path) if path.is_file() else None
                    if actual_hash != artifact.get("sha256"):
                        instrument_changes.append(
                            {"path": relative, "before_sha256": artifact.get("sha256"), "after_sha256": actual_hash}
                        )
                        if relative not in actual_path_set:
                            fail("unexplained_instrument_change", relative)
        except (ValueError, FileNotFoundError) as exc:
            fail("instrument_bundle_validation", str(exc))

    ownership_ref = manifest.get("ownership_map", {})
    ownership_path = git_root / str(ownership_ref.get("path", ""))
    if not ownership_path.is_file() or sha256_file(ownership_path) != ownership_ref.get("sha256"):
        fail("ownership_map", "ownership map is missing or changed")
        ownership_map = {"rules": []}
    else:
        ownership_map = _load_json(ownership_path)

    scope_ref = manifest.get("scope_source", {})
    scope_path = git_root / str(scope_ref.get("path", ""))
    if not scope_path.is_file() or sha256_file(scope_path) != scope_ref.get("sha256"):
        fail("scope_source", "pre-wave scope source is missing or changed")

    declared = manifest.get("declared_scope", {})
    patterns = [str(value) for value in declared.get("paths", [])]
    affected = {key: set() for key in SCOPE_KEYS}
    path_rows: list[dict[str, Any]] = []
    for path in sorted(set(actual_paths)):
        ownership = _ownership_for(path, ownership_map)
        for key in SCOPE_KEYS:
            affected[key].update(ownership[key])
        declared_path = _matches_any(path, patterns)
        if not declared_path:
            fail("undeclared_path", path)
        path_rows.append(
            {
                "path": path,
                "declared": declared_path,
                "ownership": {key: sorted(ownership[key]) for key in SCOPE_KEYS},
            }
        )
    for key in SCOPE_KEYS:
        allowed = set(str(value) for value in declared.get(key, []))
        missing = affected[key] - allowed
        for value in sorted(missing):
            fail("undeclared_affectedness", f"{key}:{value}")

    decision = "pass" if not failures else "fail"
    return {
        "binding_manifest_verification_schema_version": "p13_binding_manifest_verification.v1",
        "decision": decision,
        "manifest_id": manifest.get("manifest_id"),
        "changed_paths": path_rows,
        "derived_affectedness": {key: sorted(affected[key]) for key in SCOPE_KEYS},
        "instrument_changes": instrument_changes,
        "failures": failures,
    }
