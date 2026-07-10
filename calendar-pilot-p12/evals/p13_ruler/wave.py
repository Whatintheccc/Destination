from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tempfile
from statistics import mean
from typing import Any

from evals.p13_ruler.core import (
    APP_ROOT,
    GIT_ROOT,
    canonical_json_bytes,
    repository_identity,
    sha256_bytes,
    sha256_file,
)


def resolve(path: str | Path, *, root: Path = APP_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def load_json(path: str | Path) -> dict[str, Any]:
    resolved = Path(path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {resolved}")
    return payload


def b_migrate_assertions_path(
    manifest: dict[str, Any], *, fallback: Path | None = None
) -> Path:
    fallback = fallback or APP_ROOT / "experiments/configs/b_migrate_frontend_view_state_v2.json"
    old = manifest.get("old_producer", {}).get("b_migrate", {}).get("assertion_set")
    new = manifest.get("new_producer", {}).get("b_migrate", {}).get("assertion_set")
    if old is None and new is None:
        return Path(fallback)
    if not isinstance(old, dict) or not isinstance(new, dict) or old != new:
        raise ValueError("old/new B_migrate producers must bind the same assertion set")
    if set(old) != {"path", "sha256"}:
        raise ValueError("B_migrate assertion binding requires exactly path and sha256")
    path = resolve(str(old["path"]))
    if not path.is_file() or sha256_file(path) != old["sha256"]:
        raise ValueError("B_migrate assertion set is missing or changed after binding")
    return path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_bytes(command: list[str]) -> bytes:
    process = subprocess.run(command, cwd=GIT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if process.returncode != 0:
        raise RuntimeError(process.stderr.decode("utf-8", errors="replace").strip() or "command failed")
    return process.stdout


def source_revision() -> dict[str, Any]:
    git_sha = _run_bytes(["git", "rev-parse", "HEAD"]).decode().strip()
    status = _run_bytes(["git", "status", "--porcelain=v1", "-z"])
    tracked_diff = _run_bytes(["git", "diff", "--binary", "HEAD"])
    untracked_names = [
        value.decode("utf-8")
        for value in _run_bytes(["git", "ls-files", "--others", "--exclude-standard", "-z"]).split(b"\0")
        if value
    ]
    untracked = [
        {"path": name, "sha256": sha256_file(GIT_ROOT / name)}
        for name in sorted(untracked_names)
        if (GIT_ROOT / name).is_file()
    ]
    identity = {
        "git_sha": git_sha,
        "clean": not bool(status),
        "status_sha256": sha256_bytes(status),
        "tracked_diff_sha256": sha256_bytes(tracked_diff),
        "untracked": untracked,
    }
    identity["source_sha256"] = sha256_bytes(canonical_json_bytes(identity))
    return identity


def _tuning_pin(current_path: Path) -> tuple[Any, dict[str, Any]]:
    from calendar_pilot.types import PolicyTuning

    current = load_json(current_path)
    target = resolve(str(current.get("path", ""))) if current.get("path") else current_path
    tuning_payload = load_json(target) if target.exists() else {}
    return PolicyTuning.from_dict(tuning_payload), {
        "current_path": str(current_path),
        "current_sha256": sha256_file(current_path),
        "policy_tuning_id": current.get("policy_tuning_id") or tuning_payload.get("tuning_id"),
        "policy_tuning_path": str(target),
        "policy_tuning_sha256": sha256_file(target),
    }


def _cvar_frontier(seed: dict[str, Any], tuning: Any) -> list[dict[str, Any]]:
    from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
    from calendar_pilot.types import RawCalendarObservation, UserBiography

    observation = RawCalendarObservation.from_dict(seed["observation"])
    biography = UserBiography.from_dict(seed["profile"])
    policy = DiffusionGemmaPolicy(policy_tuning=tuning)
    return [
        candidate.to_dict()
        for candidate in policy.generate_candidates(observation, biography, goal=str(seed.get("goal", "")))
    ]


def build_cvar_frontier_set(
    *,
    role: str,
    current_path: Path,
    seed_set_path: Path,
    producer_id: str,
    bound_command: list[str],
) -> dict[str, Any]:
    if role not in {"before", "after"}:
        raise ValueError("C-VAR producer role must be before or after")
    seed_set = load_json(seed_set_path)
    tuning, tuning_pin = _tuning_pin(current_path)
    rows: list[dict[str, Any]] = []
    for raw_path in seed_set.get("seed_paths", []):
        seed_path = resolve(str(raw_path))
        seed = load_json(seed_path)
        frontier = _cvar_frontier(seed, tuning)
        rows.append(
            {
                "seed_id": str(seed.get("seed_id", seed_path.stem)),
                "seed_path": str(seed_path),
                "seed_sha256": sha256_file(seed_path),
                "frontier": frontier,
                "frontier_sha256": sha256_bytes(canonical_json_bytes(frontier)),
            }
        )
    stable = {
        "role": role,
        "producer": {"producer_id": producer_id, "bound_command": bound_command},
        "source_revision": source_revision(),
        "tuning": tuning_pin,
        "seed_set": {
            "seed_set_id": seed_set.get("seed_set_id"),
            "path": str(seed_set_path),
            "sha256": sha256_file(seed_set_path),
        },
        "rows": rows,
    }
    return {
        "cvar_frontier_set_schema_version": "cvar_frontier_set.v1",
        "generated_at": utc_now(),
        **stable,
        "content_sha256": sha256_bytes(canonical_json_bytes(stable)),
    }


def _top_margin(frontier: list[dict[str, Any]]) -> float | None:
    if len(frontier) < 2:
        return None
    return round(
        float(frontier[0].get("expected_reward", 0.0)) - float(frontier[1].get("expected_reward", 0.0)),
        6,
    )


def _promotion_decision(rows: list[dict[str, Any]]) -> str:
    if not rows or any(not row.get("frontier") for row in rows):
        return "hold"
    rewards = [float(row["frontier"][0].get("expected_reward", 0.0)) for row in rows]
    return "promote" if mean(rewards) >= 0.0 else "hold"


def _bootstrap(values: list[float], *, iterations: int, seed: int) -> dict[str, Any]:
    if not values:
        return {"iterations": iterations, "seed": seed, "mean_delta": None, "variance": None, "ci95": [None, None]}
    rng = random.Random(seed)
    count = len(values)
    samples = [mean(values[rng.randrange(count)] for _ in range(count)) for _ in range(iterations)]
    average = mean(values)
    variance = mean((value - average) ** 2 for value in values)
    ordered = sorted(samples)
    return {
        "iterations": iterations,
        "seed": seed,
        "mean_delta": round(average, 6),
        "variance": round(variance, 8),
        "bootstrap_mean_variance": round(mean((value - mean(samples)) ** 2 for value in samples), 8),
        "ci95": [
            round(ordered[int(0.025 * (iterations - 1))], 6),
            round(ordered[int(0.975 * (iterations - 1))], 6),
        ],
    }


def compare_cvar_frontier_sets(
    *,
    before_path: Path,
    after_path: Path,
    thresholds_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    before = load_json(before_path)
    after = load_json(after_path)
    thresholds = load_json(thresholds_path)
    change_class = str(manifest.get("change_class", ""))
    expected_before = manifest.get("old_producer", {}).get("cvar", {})
    expected_after = manifest.get("new_producer", {}).get("cvar", {})
    gates: dict[str, dict[str, Any]] = {}

    def gate(name: str, ok: bool, actual: Any, expected: Any = None) -> None:
        gates[name] = {"status": "pass" if ok else "hold", "actual": actual}
        if expected is not None:
            gates[name]["expected"] = expected

    before_hash = sha256_file(before_path)
    after_hash = sha256_file(after_path)
    def cvar_integrity(payload: dict[str, Any]) -> bool:
        stable = {
            key: value
            for key, value in payload.items()
            if key not in {"cvar_frontier_set_schema_version", "generated_at", "content_sha256"}
        }
        return (
            payload.get("cvar_frontier_set_schema_version") == "cvar_frontier_set.v1"
            and payload.get("content_sha256") == sha256_bytes(canonical_json_bytes(stable))
            and bool(payload.get("rows"))
            and all(
                row.get("frontier_sha256") == sha256_bytes(canonical_json_bytes(row.get("frontier", [])))
                for row in payload.get("rows", [])
            )
        )
    gate(
        "artifact_integrity",
        cvar_integrity(before) and cvar_integrity(after),
        {"before": cvar_integrity(before), "after": cvar_integrity(after)},
    )
    producer_pair = [before.get("producer", {}).get("producer_id"), after.get("producer", {}).get("producer_id")]
    command_pair = [before.get("producer", {}).get("bound_command"), after.get("producer", {}).get("bound_command")]
    gate(
        "artifact_independence",
        before_path.resolve() != after_path.resolve() and before_hash != after_hash and producer_pair[0] != producer_pair[1],
        {"before_sha256": before_hash, "after_sha256": after_hash, "producer_ids": producer_pair},
    )
    gate(
        "producer_binding",
        before.get("producer") == {"producer_id": expected_before.get("producer_id"), "bound_command": expected_before.get("command")}
        and after.get("producer") == {"producer_id": expected_after.get("producer_id"), "bound_command": expected_after.get("command")},
        command_pair,
        [expected_before.get("command"), expected_after.get("command")],
    )
    base_sha = str(manifest.get("base_repository", {}).get("git_sha", ""))
    before_source = before.get("source_revision", {})
    after_source = after.get("source_revision", {})
    behavior_change = change_class in {"migration", "compression", "learning"}
    gate(
        "frozen_before_source",
        (not behavior_change) or (before_source.get("clean") is True and before_source.get("git_sha") == base_sha),
        before_source,
        {"clean": True, "git_sha": base_sha} if behavior_change else "not required for ruler",
    )
    source_changed = before_source.get("source_sha256") != after_source.get("source_sha256")
    tuning_changed = before.get("tuning", {}).get("policy_tuning_sha256") != after.get("tuning", {}).get("policy_tuning_sha256")
    gate(
        "generated_after_source",
        (not behavior_change) or source_changed or tuning_changed,
        {"source_changed": source_changed, "tuning_changed": tuning_changed},
        "source or tuning identity changes for behavior-bearing waves",
    )
    before_rows = {str(row.get("seed_id")): row for row in before.get("rows", [])}
    after_rows = {str(row.get("seed_id")): row for row in after.get("rows", [])}
    seed_ids_match = bool(before_rows) and set(before_rows) == set(after_rows)
    seed_hashes_match = seed_ids_match and all(
        before_rows[key].get("seed_sha256") == after_rows[key].get("seed_sha256") for key in before_rows
    )
    gate("frozen_seed_set", seed_hashes_match, sorted(before_rows), sorted(after_rows))

    borderline_margin = float(thresholds.get("borderline_margin", 0.05))
    rows: list[dict[str, Any]] = []
    for seed_id in sorted(set(before_rows) & set(after_rows)):
        before_frontier = list(before_rows[seed_id].get("frontier", []))
        after_frontier = list(after_rows[seed_id].get("frontier", []))
        before_top = before_frontier[0] if before_frontier else {}
        after_top = after_frontier[0] if after_frontier else {}
        before_margin = _top_margin(before_frontier)
        after_margin = _top_margin(after_frontier)
        borderline = any(value is not None and abs(value) <= borderline_margin for value in [before_margin, after_margin])
        rows.append(
            {
                "seed_id": seed_id,
                "before_top_candidate_id": before_top.get("candidate_id"),
                "after_top_candidate_id": after_top.get("candidate_id"),
                "before_top_intent": before_top.get("intent"),
                "after_top_intent": after_top.get("intent"),
                "before_top_reward": before_top.get("expected_reward"),
                "after_top_reward": after_top.get("expected_reward"),
                "delta_top_reward": round(float(after_top.get("expected_reward", 0.0)) - float(before_top.get("expected_reward", 0.0)), 6),
                "before_margin": before_margin,
                "after_margin": after_margin,
                "borderline": borderline,
                "top_candidate_flipped": bool(before_top and after_top and before_top.get("candidate_id") != after_top.get("candidate_id")),
            }
        )
    deltas = [float(row["delta_top_reward"]) for row in rows]
    bootstrap = _bootstrap(
        deltas,
        iterations=int(thresholds.get("bootstrap_iterations", 200)),
        seed=int(thresholds.get("bootstrap_seed", 1729)),
    )
    borderline = [row for row in rows if row["borderline"]]
    flips = [row for row in borderline if row["top_candidate_flipped"]]
    flip_rate = round(len(flips) / len(borderline), 6) if borderline else 0.0
    before_decision = _promotion_decision(list(before_rows.values()))
    after_decision = _promotion_decision(list(after_rows.values()))
    gate(
        "bootstrap_variance",
        bootstrap.get("variance") is not None and float(bootstrap["variance"]) <= float(thresholds.get("max_delta_variance", 0.0025)),
        bootstrap.get("variance"),
        thresholds.get("max_delta_variance", 0.0025),
    )
    gate(
        "borderline_flip_rate",
        flip_rate <= float(thresholds.get("max_borderline_flip_rate", 0.1)),
        flip_rate,
        thresholds.get("max_borderline_flip_rate", 0.1),
    )
    decision_changed = before_decision != after_decision
    gate(
        "promotion_decision_flip",
        not decision_changed or bool(thresholds.get("allow_promotion_decision_flip", False)),
        {"before": before_decision, "after": after_decision, "changed": decision_changed},
    )
    decision = "pass" if all(value["status"] == "pass" for value in gates.values()) else "hold"
    return {
        "cvar_report_schema_version": "cvar_report.v2",
        "decision": decision,
        "change_class": change_class,
        "manifest_id": manifest.get("manifest_id"),
        "before_artifact": {"path": str(before_path), "sha256": before_hash, "content_sha256": before.get("content_sha256")},
        "after_artifact": {"path": str(after_path), "sha256": after_hash, "content_sha256": after.get("content_sha256")},
        "thresholds": {"path": str(thresholds_path), "sha256": sha256_file(thresholds_path), "values": thresholds},
        "compared_rows": rows,
        "bootstrap": bootstrap,
        "borderline": {"margin_threshold": borderline_margin, "count": len(borderline), "flip_count": len(flips), "flip_rate": flip_rate},
        "promotion_decisions": {"before": before_decision, "after": after_decision, "changed": decision_changed},
        "gates": gates,
    }


def _frontend_session() -> Any:
    from calendar_pilot.frontend.session import DogfoodSessionState

    temporary = tempfile.TemporaryDirectory()
    session = DogfoodSessionState(run_dir=Path(temporary.name), session_id="sess_p13_b_migrate")
    planned = session.create_plan("Make next week less chaotic")
    candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
    session.candidate_action(candidate_id, "stage")
    return temporary, session


def build_b_migrate_artifact(*, role: str, producer_id: str, bound_command: list[str]) -> dict[str, Any]:
    if role not in {"old", "new"}:
        raise ValueError("B_migrate producer role must be old or new")
    temporary, session = _frontend_session()
    try:
        if role == "old":
            observable = session.snapshot()
        else:
            from calendar_pilot.frontend.projector import FrontendProjector

            observable = FrontendProjector(session).view()
    finally:
        temporary.cleanup()
    stable = {
        "role": role,
        "producer": {"producer_id": producer_id, "bound_command": bound_command},
        "source_revision": source_revision(),
        "input": {
            "scenario_id": "frontend.staged_candidate.v1",
            "goal": "Make next week less chaotic",
            "input_sha256": sha256_bytes(canonical_json_bytes({"goal": "Make next week less chaotic", "action": "stage_first"})),
        },
        "lineage": {"derived_from_artifact_sha256": None},
        "observable": observable,
        "observable_sha256": sha256_bytes(canonical_json_bytes(observable)),
    }
    return {
        "b_migrate_artifact_schema_version": "b_migrate_artifact.v1",
        "generated_at": utc_now(),
        **stable,
        "content_sha256": sha256_bytes(canonical_json_bytes(stable)),
    }


def _path_values(data: Any, path: str) -> list[Any]:
    values = [data]
    for part in path.split(".") if path else []:
        next_values: list[Any] = []
        list_mode = part.endswith("[]")
        key = part[:-2] if list_mode else part
        for value in values:
            child = value.get(key) if isinstance(value, dict) else None
            if list_mode and isinstance(child, list):
                next_values.extend(child)
            elif not list_mode:
                next_values.append(child)
        values = next_values
    return values


def _b_assertion(assertion: dict[str, Any], before: Any, after: Any) -> dict[str, Any]:
    mode = str(assertion.get("mode", "equal"))
    before_values = _path_values(before, str(assertion.get("before_path", "")))
    after_values = _path_values(after, str(assertion.get("after_path", "")))
    if mode == "equal_set":
        before_value = sorted({str(value) for value in before_values if value not in {None, ""}})
        after_value = sorted({str(value) for value in after_values if value not in {None, ""}})
        ok = before_value == after_value
    elif mode == "non_empty":
        before_value, after_value = before_values, after_values
        ok = bool(before_value) and bool(after_value) and all(value is not None and value != "" and value != [] for value in before_value + after_value)
    else:
        before_value = before_values[0] if before_values else None
        after_value = after_values[0] if after_values else None
        ok = before_value == after_value
    return {
        "name": assertion.get("name"),
        "mode": mode,
        "before_path": assertion.get("before_path"),
        "after_path": assertion.get("after_path"),
        "before_value": before_value,
        "after_value": after_value,
        "status": "pass" if ok else "fail",
    }


def compare_b_migrate_artifacts(
    *,
    before_path: Path,
    after_path: Path,
    assertions_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    before = load_json(before_path)
    after = load_json(after_path)
    assertions_payload = load_json(assertions_path)
    expected_before = manifest.get("old_producer", {}).get("b_migrate", {})
    expected_after = manifest.get("new_producer", {}).get("b_migrate", {})
    failures: list[dict[str, str]] = []

    def fail(code: str, detail: str) -> None:
        failures.append({"code": code, "detail": detail})

    before_hash = sha256_file(before_path)
    after_hash = sha256_file(after_path)
    def artifact_integrity(payload: dict[str, Any]) -> bool:
        stable = {
            key: value
            for key, value in payload.items()
            if key not in {"b_migrate_artifact_schema_version", "generated_at", "content_sha256"}
        }
        return (
            payload.get("b_migrate_artifact_schema_version") == "b_migrate_artifact.v1"
            and payload.get("content_sha256") == sha256_bytes(canonical_json_bytes(stable))
            and payload.get("observable_sha256") == sha256_bytes(canonical_json_bytes(payload.get("observable", {})))
        )
    if not artifact_integrity(before) or not artifact_integrity(after):
        fail("artifact_integrity", "old or new artifact content hash does not match its evidence")
    if before_path.resolve() == after_path.resolve() or before_hash == after_hash:
        fail("identical_artifact", "old and new artifacts must be distinct files with distinct identities")
    if before.get("producer", {}).get("producer_id") == after.get("producer", {}).get("producer_id"):
        fail("identical_producer", "old and new artifacts must come from independently named producers")
    for actual, expected, role in [(before, expected_before, "old"), (after, expected_after, "new")]:
        if actual.get("role") != role:
            fail("producer_role", f"{role} artifact has role {actual.get('role')}")
        if actual.get("producer") != {"producer_id": expected.get("producer_id"), "bound_command": expected.get("command")}:
            fail("producer_binding", f"{role} producer does not match BindingManifest")
        if actual.get("lineage", {}).get("derived_from_artifact_sha256") in {
            before_hash, after_hash, before.get("content_sha256"), after.get("content_sha256")
        }:
            fail("self_derived_artifact", f"{role} artifact declares old/new comparison output as its source")
    if before.get("input", {}).get("input_sha256") != after.get("input", {}).get("input_sha256"):
        fail("input_mismatch", "old and new producers did not consume the same frozen input")
    assertions = [
        _b_assertion(row, before.get("observable", {}), after.get("observable", {}))
        for row in assertions_payload.get("assertions", [])
    ]
    if not assertions:
        fail("missing_assertions", "comparison vector is empty")
    if any(row["status"] != "pass" for row in assertions):
        fail("observable_mismatch", "one or more protected observables differ")
    return {
        "b_migrate_report_schema_version": "b_migrate_report.v2",
        "decision": "pass" if not failures else "hold",
        "manifest_id": manifest.get("manifest_id"),
        "producer_commands": {"old": expected_before.get("command"), "new": expected_after.get("command")},
        "before_artifact": {"path": str(before_path), "sha256": before_hash, "content_sha256": before.get("content_sha256")},
        "after_artifact": {"path": str(after_path), "sha256": after_hash, "content_sha256": after.get("content_sha256")},
        "assertion_set": {"path": str(assertions_path), "sha256": sha256_file(assertions_path), "assertion_set_id": assertions_payload.get("assertion_set_id")},
        "assertions": assertions,
        "failures": failures,
    }


def verify_root_list(manifest: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    entries = manifest.get("live_legs", [])
    failures: list[dict[str, str]] = []
    holds: list[dict[str, str]] = []
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    checked: list[dict[str, Any]] = []
    if not isinstance(entries, list):
        failures.append({"code": "root_list_shape", "detail": "live_legs must be an array"})
        entries = []
    if manifest.get("change_class") != "ruler" and not entries:
        holds.append({"code": "missing_live_leg_coverage", "detail": "behavior-bearing waves require ran or root-listed live legs"})
    for entry in entries:
        row_failures: list[str] = []
        required = {"leg", "status", "reason", "artifact", "owner", "sign_off", "affected_by_wave", "expires_at", "next_unblock_action"}
        if not isinstance(entry, dict) or set(entry) != required:
            row_failures.append("entry keys do not match the versioned root-list contract")
            checked.append({"entry": entry, "status": "fail", "failures": row_failures})
            continue
        status = entry.get("status")
        if status not in {"ran", "root-listed"}:
            row_failures.append("status must be ran or root-listed")
        reason = entry.get("reason", {})
        allowed_basis = {"ran"} if status == "ran" else {"unaffected", "unavailable"}
        if not isinstance(reason, dict) or set(reason) != {"basis", "detail"} or reason.get("basis") not in allowed_basis or not str(reason.get("detail", "")).strip():
            row_failures.append("reason basis and detail must match the entry status")
        artifact = entry.get("artifact", {})
        artifact_path = resolve(str(artifact.get("path", "")), root=GIT_ROOT)
        if not artifact_path.is_file() or sha256_file(artifact_path) != artifact.get("sha256"):
            row_failures.append("artifact is missing or its hash changed")
        if not str(entry.get("owner", "")).strip() or not str(entry.get("sign_off", "")).strip():
            row_failures.append("owner and sign_off are required")
        try:
            expiry = datetime.fromisoformat(str(entry.get("expires_at", "")).replace("Z", "+00:00"))
            if expiry <= current:
                holds.append({"code": "root_list_expired", "detail": str(entry.get("leg"))})
        except ValueError:
            row_failures.append("expires_at is invalid")
        if status == "root-listed":
            if reason.get("basis") == "unaffected" and entry.get("affected_by_wave") is not False:
                row_failures.append("unaffected root-list entries must set affected_by_wave false")
        if row_failures:
            failures.append({"code": "root_list_entry", "detail": f"{entry.get('leg')}: {'; '.join(row_failures)}"})
        checked.append({"entry": entry, "status": "fail" if row_failures else "pass", "failures": row_failures})
    decision = "fail" if failures else "hold" if holds else "pass"
    return {
        "p13_root_list_verification_schema_version": "p13_root_list_verification.v1",
        "decision": decision,
        "manifest_id": manifest.get("manifest_id"),
        "signed_by_binding_manifest": True,
        "entries": checked,
        "failures": failures,
        "hold_reasons": holds,
    }


def artifact_ref(path: Path, *, decision: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"path": str(path), "sha256": sha256_file(path)}
    if decision is not None:
        row["decision"] = decision
    return row


def git_delta_against(base_git_sha: str) -> list[dict[str, Any]]:
    """Return the committed candidate delta in a machine-checkable form."""
    payload = _run_bytes(["git", "diff", "--name-status", "-z", base_git_sha, "HEAD"])
    tokens = [token.decode("utf-8") for token in payload.split(b"\0") if token]
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if status.startswith(("R", "C")):
            if index + 1 >= len(tokens):
                raise ValueError("truncated git rename/copy delta")
            rows.append({"status": status, "old_path": tokens[index], "path": tokens[index + 1]})
            index += 2
        else:
            if index >= len(tokens):
                raise ValueError("truncated git path delta")
            rows.append({"status": status, "path": tokens[index]})
            index += 1
    return rows


def _selected_scenario_passes(
    manifest: dict[str, Any], architecture: dict[str, Any], scenario_id: str
) -> bool:
    if scenario_id not in manifest.get("required_scenarios", []):
        return False
    return any(
        row.get("scenario_id") == scenario_id
        and row.get("gate_mode") == "required"
        and row.get("status") == "pass"
        for row in architecture.get("scenarios", [])
        if isinstance(row, dict)
    )


def is_structurally_no_effect_wave(
    manifest: dict[str, Any],
    verification: dict[str, Any],
    architecture: dict[str, Any],
) -> bool:
    affected = verification.get("derived_affectedness", {})
    return bool(
        manifest.get("change_class") == "migration"
        and verification.get("decision") == "pass"
        and _selected_scenario_passes(
            manifest, architecture, "target.product_core_no_effect_reachability"
        )
        and not affected.get("backends")
        and not affected.get("control_planes")
    )


P13_3_SANDBOX_SCENARIOS = {
    "target.trusted_ingress_forgery",
    "target.effect_ticket_binding",
    "target.compensation_ticket_binding",
    "target.ticket_single_claim",
    "target.duplicate_delivery",
    "target.crash_before_claim",
    "target.crash_after_claim",
    "target.crash_after_dispatch",
    "target.verify_ambiguity_reconcile",
    "target.revoke_claim_race",
    "target.restart_reconciliation",
    "target.compensation_conflict_hold",
    "target.no_learning_effect_path",
}


def is_owner_controlled_sandbox_wave(
    manifest: dict[str, Any],
    verification: dict[str, Any],
    architecture: dict[str, Any],
) -> bool:
    affected = verification.get("derived_affectedness", {})
    return bool(
        manifest.get("change_class") == "migration"
        and verification.get("decision") == "pass"
        and set(affected.get("actions", [])) == {"create_prep_block"}
        and set(affected.get("backends", [])) == {"deterministic_sandbox"}
        and set(affected.get("control_planes", [])) == {"effect_tcb", "evaluator"}
        and all(_selected_scenario_passes(manifest, architecture, scenario_id) for scenario_id in P13_3_SANDBOX_SCENARIOS)
    )


def build_experiment_record(
    *,
    manifest_path: Path,
    binding_verification_path: Path,
    architecture_report_path: Path,
    cvar_report_path: Path,
    b_migrate_report_path: Path,
    release_report_path: Path,
    reward_report_path: Path,
    root_list_report_path: Path,
    loc_report_path: Path,
    candidate_repository: dict[str, Any] | None = None,
    git_delta: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    verification = load_json(binding_verification_path)
    architecture = load_json(architecture_report_path)
    cvar = load_json(cvar_report_path)
    b_migrate = load_json(b_migrate_report_path)
    release = load_json(release_report_path)
    reward = load_json(reward_report_path)
    root_list = load_json(root_list_report_path)
    loc = load_json(loc_report_path)
    decisions = {
        "binding_manifest": verification.get("decision"),
        "architecture": architecture.get("decision"),
        "cvar": cvar.get("decision"),
        "b_migrate": b_migrate.get("decision"),
        "p12_release": release.get("decision"),
        "reward_screen": reward.get("decision"),
        "root_list": root_list.get("decision"),
        "loc": loc.get("decision"),
    }
    change_class = str(manifest.get("change_class", ""))
    ruler = change_class == "ruler"
    changed_paths = [str(row.get("path")) for row in verification.get("changed_paths", [])]
    candidate_repository = candidate_repository or repository_identity()
    if git_delta is None:
        try:
            git_delta = git_delta_against(str(manifest.get("base_repository", {}).get("git_sha", "")))
        except (RuntimeError, ValueError):
            git_delta = []
    structural_no_effect = is_structurally_no_effect_wave(manifest, verification, architecture)
    sandbox_effect = is_owner_controlled_sandbox_wave(manifest, verification, architecture)
    bounded_development = structural_no_effect or sandbox_effect
    delta_paths = [str(row.get("path")) for row in git_delta]
    exact_additive_rollback = bool(
        bounded_development
        and git_delta
        and all(row.get("status") == "A" and row.get("path") for row in git_delta)
        and set(delta_paths) == set(changed_paths)
    )
    cited_read_side_rollback = bool(
        structural_no_effect
        and _selected_scenario_passes(manifest, architecture, "target.cited_read_side_cutover")
        and b_migrate.get("decision") == "pass"
    )
    compared_seed_ids = [str(row.get("seed_id")) for row in cvar.get("compared_rows", [])]
    compared_assertions = [str(row.get("name")) for row in b_migrate.get("assertions", [])]
    deltas = [float(row.get("delta_top_reward", 0.0)) for row in cvar.get("compared_rows", [])]
    worst_delta = min(deltas) if deltas else None
    ablation_stable = bool(bounded_development and b_migrate.get("decision") == "pass")
    rollback_restored = bool(
        (exact_additive_rollback or cited_read_side_rollback)
        and verification.get("decision") == "pass"
        and architecture.get("decision") == "pass"
        and cvar.get("decision") == "pass"
        and b_migrate.get("decision") == "pass"
        and release.get("decision") == "pass"
    )
    behavior_evidence_complete = bool(bounded_development and ablation_stable and rollback_restored)
    decision = "pass" if all(value == "pass" for value in decisions.values()) and (ruler or behavior_evidence_complete) else "hold"
    record = {
        "experiment_record_schema_version": "experiment_record.v2",
        "experiment_id": str(manifest.get("wave")),
        "phase": "P13",
        "change_class": change_class,
        "hypothesis": "The declared wave preserves protected behavior while changing only its signed scope.",
        "binding_manifest": {
            "manifest_id": manifest.get("manifest_id"),
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
            "instrument_bundle_sha256": manifest.get("instrument_bundle", {}).get("bundle_sha256"),
        },
        "delta": {
            "summary": "P13 ruler and evidence plumbing only" if ruler else "declared behavior-bearing wave",
            "spans": changed_paths,
            "cluster_ids": [],
            "loc_delta": loc.get("delta", {}).get("delta_lines") if isinstance(loc.get("delta"), dict) else None,
        },
        "fixed": {
            "instrument_bundle_sha256": manifest.get("instrument_bundle", {}).get("bundle_sha256"),
            "instrument_bundle_file_sha256": manifest.get("instrument_bundle", {}).get("file_sha256"),
            "base_git_sha": manifest.get("base_repository", {}).get("git_sha"),
            "base_app_tree_sha": manifest.get("base_repository", {}).get("app_tree_sha"),
        },
        "rows": {
            "trained": [],
            "graded": compared_seed_ids,
            "compared": [*compared_seed_ids, *compared_assertions],
        },
        "baseline": {
            "metrics": {
                "cvar_before_decision": cvar.get("promotion_decisions", {}).get("before"),
                "p12_release": release.get("decision"),
                "preservation_pass": architecture.get("rails", {}).get("preservation", {}).get("status_counts", {}).get("pass"),
            },
            "artifacts": {
                "cvar_before": cvar.get("before_artifact"),
                "b_migrate_old": b_migrate.get("before_artifact"),
            },
        },
        "effect": {
            "metrics": {
                "cvar_mean_delta": cvar.get("bootstrap", {}).get("mean_delta"),
                "cvar_borderline_flip_rate": cvar.get("borderline", {}).get("flip_rate"),
                "b_migrate_failed_assertions": len([row for row in b_migrate.get("assertions", []) if row.get("status") != "pass"]),
            },
            "uncertainty": {
                "method": "seed bootstrap",
                "ci95": cvar.get("bootstrap", {}).get("ci95"),
                "variance": cvar.get("bootstrap", {}).get("variance"),
            },
        },
        "regressed": {
            "applicable": not ruler,
            "metric": None if ruler else ("top_candidate_reward_worst_seed" if worst_delta is not None else "none_measured"),
            "delta": None if ruler else worst_delta,
            "acceptable": None if ruler else bool(worst_delta is not None and worst_delta >= -0.05),
            "reason": "No product metric is claimed for a ruler-only wave" if ruler else "Worst named C-VAR seed delta",
        },
        "ablation": {
            "applicable": not ruler,
            "method": None if ruler else ("independent incumbent B_migrate producer" if bounded_development else "declared organ disabled or stubbed"),
            "artifact": artifact_ref(b_migrate_report_path, decision=str(b_migrate.get("decision"))) if bounded_development else None,
            "decision_stable": None if ruler else ablation_stable,
            "reason": (
                "No product organ changed"
                if ruler
                else (
                    "The independent incumbent path is the ablation and preserves the signed comparison vector."
                    if ablation_stable
                    else "A behavior-bearing wave must attach a passing ablation artifact before promotion"
                )
            ),
        },
        "rollback": {
            "applicable": not ruler,
            "revert_sha": None if ruler else manifest.get("base_repository", {}).get("git_sha"),
            "proof_artifact": (
                {
                    "mode": (
                        "incumbent_read_selector"
                        if cited_read_side_rollback
                        else "exact_additive_sandbox_revert" if sandbox_effect
                        else "exact_additive_revert"
                    ),
                    "base_git_sha": manifest.get("base_repository", {}).get("git_sha"),
                    "base_app_tree_sha": manifest.get("base_repository", {}).get("app_tree_sha"),
                    "candidate_git_sha": candidate_repository.get("git_sha"),
                    "candidate_app_tree_sha": candidate_repository.get("app_tree_sha"),
                    "git_delta": git_delta,
                    "binding_verification": artifact_ref(binding_verification_path, decision=str(verification.get("decision"))),
                    "incumbent_projection": b_migrate.get("before_artifact") if (cited_read_side_rollback or sandbox_effect) else None,
                }
                if bounded_development
                else None
            ),
            "baseline_restored": None if ruler else rollback_restored,
            "reason": (
                "No product code or payload promotion occurred"
                if ruler
                else (
                    (
                        "The independent incumbent projection remains executable and equivalent behind the compatibility selector."
                        if cited_read_side_rollback
                        else (
                            "The incumbent remains the default effect owner; removing the additive sandbox delta restores the signed base tree."
                            if sandbox_effect
                            else "Every candidate path is a new, manifest-declared no-effect file; removing the exact additive delta restores the signed base tree."
                        )
                    )
                    if rollback_restored
                    else "A behavior-bearing wave must attach exact rollback proof before promotion"
                )
            ),
        },
        "candidate": None if ruler else {
            "git_sha": candidate_repository.get("git_sha"),
            "app_tree_sha": candidate_repository.get("app_tree_sha"),
            "base_git_sha": manifest.get("base_repository", {}).get("git_sha"),
            "changed_paths": changed_paths,
            "evidence_class": (
                "structurally_no_effect"
                if structural_no_effect
                else "owner_controlled_sandbox" if sandbox_effect
                else "behavior_evidence_incomplete"
            ),
        },
        "outcomes": {
            "reward_vector": reward.get("reward_head_deltas"),
            "source_identity": {
                "status": "not_established",
                "occurrences": reward.get("reward_evidence", {}).get("consumed_reward_rows"),
            },
            "provenance": reward.get("reward_evidence", {}).get("declared_source_classification"),
            "outcome_window": (
                "not_applicable_structurally_no_effect"
                if structural_no_effect
                else "not_applicable_non_authorizing_sandbox" if sandbox_effect
                else None
            ),
        },
        "statistics": {
            "estimand": "no product effect" if ruler else "protected behavior equivalence",
            "uncertainty_method": "seed bootstrap",
            "equivalence_margin": cvar.get("thresholds", {}).get("values", {}).get("max_delta_variance"),
            "protected_slices": compared_seed_ids,
        },
        "identifiability": {
            "status": "not_applicable" if ruler else ("identified" if behavior_evidence_complete else "not_identifiable"),
            "reason": (
                "Ruler-only wave makes no product-effect claim"
                if ruler
                else (
                    (
                        "The claim is limited to deterministic sandbox lifecycle semantics and protected-observable equivalence; no real-provider, production, or human-outcome effect is claimed."
                        if sandbox_effect
                        else "The claim is limited to structural non-reachability and protected-observable equivalence; no human-outcome effect is claimed."
                    )
                    if behavior_evidence_complete
                    else "Behavior evidence is incomplete until candidate, ablation, and rollback attestations are attached"
                )
            ),
        },
        "attestations": {
            "binding_manifest": artifact_ref(binding_verification_path, decision=str(verification.get("decision"))),
            "architecture": artifact_ref(architecture_report_path, decision=str(architecture.get("decision"))),
            "cvar": artifact_ref(cvar_report_path, decision=str(cvar.get("decision"))),
            "b_migrate": artifact_ref(b_migrate_report_path, decision=str(b_migrate.get("decision"))),
            "p12_release": artifact_ref(release_report_path, decision=str(release.get("decision"))),
            "reward_screen": artifact_ref(reward_report_path, decision=str(reward.get("decision"))),
            "root_list": artifact_ref(root_list_report_path, decision=str(root_list.get("decision"))),
            "loc": artifact_ref(loc_report_path, decision=str(loc.get("decision"))),
        },
        "decision": decision,
    }
    return record
