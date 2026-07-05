#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.codex import CodexToolPlanner, CodexToolRuntime
from calendar_pilot.diffusiongemma.live import DEFAULT_NIM_MODEL, LIVE_DIFFUSIONGEMMA_BACKEND, PROMPT_VERSION, LiveDiffusionGemmaSchemaError, LiveDiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.self_play import SelfPlayRunner, UserSimulator
from calendar_pilot.environment.fsio import atomic_write_json, atomic_write_text
from calendar_pilot.environment.invariants import check_replay
from calendar_pilot.environment.selfplay_backends import BACKEND_POLICIES, SelfPlayActionBackend
from calendar_pilot.environment.taxonomy import normalize_intent
from calendar_pilot.frontend.runtime import RuntimeBackends, runtime_report
from calendar_pilot.providers.apple_eventkit import AppleEventKitProvider
from calendar_pilot.providers.deterministic import DeterministicCalendarProvider
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.swift_bridge.ipc import SwiftKernelIPCClient
from calendar_pilot.types import CandidateCalendarAction, PolicyTuning, RawCalendarObservation, UserBiography, to_jsonable
from scripts.lab_modules import build_diff, build_policy_report, build_scorecard, lint_seed


LAB_SCHEMA_VERSION = "lab_v0.1"
DEFAULT_OUT_ROOT = ROOT / "experiments" / "runs"


class StaticFrontierPolicy:
    def __init__(self, source_policy: Any, candidates: list[CandidateCalendarAction]) -> None:
        self.source_policy = source_policy
        self.candidates = [CandidateCalendarAction.from_dict(candidate.to_dict()) for candidate in candidates]
        self.backend_name = getattr(source_policy, "backend_name", type(source_policy).__name__)

    def generate_candidates(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        goal: str | None = None,
    ) -> list[CandidateCalendarAction]:
        return [CandidateCalendarAction.from_dict(candidate.to_dict()) for candidate in self.candidates]

    def policy_metadata_for_candidate(self, candidate_id: str) -> dict[str, Any]:
        metadata_for = getattr(self.source_policy, "policy_metadata_for_candidate", None)
        if callable(metadata_for):
            return metadata_for(candidate_id)
        return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _git_sha() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _git_dirty() -> bool:
    proc = subprocess.run(["git", "status", "--short", "--", "."], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return bool(proc.stdout.strip()) if proc.returncode == 0 else True


def _allocate_experiment_id(out_root: Path, requested: str = "") -> str:
    if requested:
        return requested
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    used: set[int] = set()
    pattern = re.compile(rf"^lab_{date}_(\d{{3}})$")
    if out_root.exists():
        for path in out_root.iterdir():
            match = pattern.match(path.name)
            if match:
                used.add(int(match.group(1)))
    seq = 1
    while seq in used:
        seq += 1
    return f"lab_{date}_{seq:03d}"


def _resolve_path(raw: str | Path, *, base: Path = ROOT) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else base / path


def _default_tuning_path() -> Path | None:
    current = ROOT / "experiments" / "promoted" / "CURRENT.json"
    if not current.exists():
        return None
    try:
        payload = _json_load(current)
    except (OSError, json.JSONDecodeError):
        return current
    if isinstance(payload, dict) and payload.get("path"):
        return _resolve_path(str(payload["path"]))
    return current


def _load_tuning(path: Path | None) -> tuple[PolicyTuning, Path | None]:
    if path is None:
        return PolicyTuning(tuning_id="empty"), None
    if not path.exists():
        raise FileNotFoundError(f"policy tuning not found: {path}")
    return PolicyTuning.from_dict(_json_load(path)), path


def _seed_path(seed: str) -> Path:
    if not seed:
        raise ValueError("--seed is required unless --from-replay is used")
    path = _resolve_path(seed)
    if path.is_dir():
        raise ValueError(f"seed path is a directory: {path}")
    return path


def _load_seed(path: Path) -> tuple[dict[str, Any], RawCalendarObservation, UserBiography]:
    errors = lint_seed(path)
    if errors:
        raise ValueError("seed validation failed:\n" + "\n".join(errors))
    seed = _json_load(path)
    return seed, RawCalendarObservation.from_dict(seed["observation"]), UserBiography.from_dict(seed["profile"])


def _sample_seed(seed_id: str, goal: str) -> tuple[dict[str, Any], RawCalendarObservation, UserBiography, Path]:
    observation_path = ROOT / "data" / "sample_calendar.json"
    profile_path = ROOT / "data" / "sample_profile.json"
    observation = _json_load(observation_path)
    profile = _json_load(profile_path)
    seed = {
        "seed_id": seed_id or "imported_replay",
        "seed_schema_version": "imported",
        "goal": goal or "Imported dogfood replay analysis",
        "authority": {"profile": "tier1_recommend"},
        "expectations": {"expected_good_intents": [], "expected_bad_intents": []},
        "expects_tuning_leader_change": False,
        "observation": observation,
        "profile": profile,
    }
    return seed, RawCalendarObservation.from_dict(observation), UserBiography.from_dict(profile), observation_path


def _authority_tier(seed: dict[str, Any]) -> int:
    profile = str(seed.get("authority", {}).get("profile", "tier3_private"))
    return 1 if profile == "tier1_recommend" else 3


def _kernel_backend_for_self_play(backend: SelfPlayActionBackend) -> str:
    if backend in {SelfPlayActionBackend.SWIFT_IPC_DETERMINISTIC, SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX}:
        return "SwiftKernelIPCClient"
    return "SwiftKernelStub"


def _kernel_context(backend: SelfPlayActionBackend):
    if _kernel_backend_for_self_play(backend) == "SwiftKernelIPCClient":
        return SwiftKernelIPCClient()
    return nullcontext(SwiftKernelStub())


def _swift_toolchain_available() -> bool:
    proc = subprocess.run(["swift", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return proc.returncode == 0


def _provider_for_backend(backend: SelfPlayActionBackend, run_dir: Path, observation: RawCalendarObservation):
    if backend == SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX:
        return AppleEventKitProvider(state_path=run_dir / "eventkit_state.json")
    return DeterministicCalendarProvider(state_path=run_dir / "provider_state.json", seed_observation=observation)


def _model_policy(runtime: str, tuning: PolicyTuning):
    if runtime == "live_diffusiongemma":
        return LiveDiffusionGemmaPolicy(policy_tuning=tuning)
    if runtime != "fixture":
        raise ValueError(f"unsupported lab runtime: {runtime}")
    return DiffusionGemmaPolicy(policy_tuning=tuning)


def _policy_backend(runtime: str) -> str:
    return LIVE_DIFFUSIONGEMMA_BACKEND if runtime == "live_diffusiongemma" else "heuristic_diffusiongemma_policy"


def _decoding() -> dict[str, Any]:
    return {
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": int(os.environ.get("CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS", "4200")),
    }


def _live_skip_reason(policy: Any, backend: SelfPlayActionBackend) -> str | None:
    if hasattr(policy, "health_status"):
        health = policy.health_status(validate_remote=True)
        if health.get("status") != "ok":
            return f"nim_{health.get('status', 'not_ok')}"
    if backend in {SelfPlayActionBackend.SWIFT_IPC_DETERMINISTIC, SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX} and not _swift_toolchain_available():
        return "swift_toolchain_unavailable"
    if backend == SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX:
        if os.environ.get("CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX", "") not in {"1", "true", "TRUE", "yes"}:
            return "eventkit_sandbox_flag_missing"
        if not (os.environ.get("CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID") or os.environ.get("CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID")):
            return "eventkit_sandbox_calendar_missing"
        health = AppleEventKitProvider().health_status()
        if not health.get("configured"):
            return f"eventkit_{health.get('status', 'not_configured')}"
    if backend == SelfPlayActionBackend.PRODUCTION_SHADOW and os.environ.get("CALENDAR_PILOT_SELFPLAY_SHADOW", "") not in {"1", "true", "TRUE", "yes"}:
        return "production_shadow_flag_missing"
    return None


def _base_manifest(
    *,
    experiment_id: str,
    batch_id: str,
    seed: dict[str, Any],
    seed_path: Path,
    runtime: str,
    self_play_backend: SelfPlayActionBackend,
    episodes: int,
    tuning: PolicyTuning,
    tuning_path: Path | None,
    observation_path: Path,
    profile_path: Path,
    provider_backend: str,
    imported: bool = False,
) -> dict[str, Any]:
    kernel_backend = _kernel_backend_for_self_play(self_play_backend)
    backends = RuntimeBackends(
        kernel=kernel_backend,
        codex="deterministic_codex_tool_planner",
        diffusiongemma=_policy_backend(runtime),
        provider=provider_backend,
    )
    report = runtime_report(
        mode=runtime,
        run_dir=DEFAULT_OUT_ROOT / experiment_id,
        observation_path=observation_path,
        profile_path=profile_path,
        session_id=experiment_id,
        backends=backends,
    )
    return {
        "lab_schema_version": LAB_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "batch_id": batch_id,
        "seed_id": seed.get("seed_id"),
        "seed_path": _rel(seed_path),
        "seed_sha256": _sha256_file(seed_path) if seed_path.exists() else None,
        "goal": seed.get("goal", ""),
        "runtime_mode": runtime,
        "policy_backend": backends.diffusiongemma,
        "codex_backend": backends.codex,
        "kernel_backend": backends.kernel,
        "provider_backend": provider_backend,
        "model": (os.environ.get("CALENDAR_PILOT_NIM_MODEL") or os.environ.get("NIM_MODEL") or DEFAULT_NIM_MODEL) if runtime == "live_diffusiongemma" else None,
        "prompt_version": PROMPT_VERSION,
        "decoding": _decoding(),
        "policy_tuning_id": tuning.tuning_id,
        "policy_tuning_path": _rel(tuning_path) if tuning_path else None,
        "reward_weights_id": None,
        "authority_profile": seed.get("authority", {}).get("profile", "tier3_private"),
        "self_play_backend": self_play_backend.value,
        "episodes": episodes,
        "git_sha": _git_sha(),
        "git_dirty": _git_dirty(),
        "started_at": _utc_now(),
        "ended_at": None,
        "status": "running",
        "skip_reason": None,
        "imported": imported,
        "runtime_report": report,
    }


def _finish_manifest(path: Path, manifest: dict[str, Any], status: str, skip_reason: str | None = None) -> None:
    manifest["status"] = status
    manifest["skip_reason"] = skip_reason
    manifest["ended_at"] = _utc_now()
    atomic_write_json(path, manifest)


def _frontier_rows(policy: Any, candidates: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid = [candidate.to_dict() for candidate in candidates]
    rejections: list[dict[str, Any]] = []
    metadata_for = getattr(policy, "policy_metadata_for_candidate", None)
    seen: set[str] = set()
    if callable(metadata_for):
        for candidate in candidates:
            metadata = metadata_for(candidate.candidate_id)
            validation = metadata.get("validation") if isinstance(metadata, dict) else None
            if not isinstance(validation, dict):
                continue
            for rejection in validation.get("rejections", []) or []:
                if not isinstance(rejection, dict):
                    continue
                key = json.dumps(rejection, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    rejections.append(rejection)
    return valid, rejections


def _append_frontier_replay(replay: ReplayBuffer, candidates: list[Any], rejections: list[dict[str, Any]], policy: Any, observation: RawCalendarObservation) -> None:
    policy_version = getattr(policy, "backend_name", _policy_backend("fixture"))
    metadata_for = getattr(policy, "policy_metadata_for_candidate", None)
    fingerprint = observation_fingerprint(observation)
    for rank, candidate in enumerate(candidates):
        metadata = metadata_for(candidate.candidate_id) if callable(metadata_for) else {}
        replay.append_decision(
            candidate,
            rank=rank,
            policy_version=policy_version,
            trace_id=f"lab_frontier:{observation.observation_id}",
            causal_parent_id="lab_frontier",
            policy_metadata=metadata,
            observation_id=observation.observation_id,
            observation_fingerprint=fingerprint,
        )
    for rejection in rejections:
        replay.append_model_generation_rejection(rejection, trace_id=f"lab_frontier:{observation.observation_id}", causal_parent_id="lab_frontier")


def _canonical_intent(value: str) -> str:
    return normalize_intent(value).get("intent", "other")


def _expected_bad(seed: dict[str, Any]) -> set[str]:
    rows = seed.get("expectations", {}).get("expected_bad_intents", [])
    out: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            out.add(_canonical_intent(str(row.get("intent", ""))))
        else:
            out.add(_canonical_intent(str(row)))
    return out


def _committed_bad_intent(replay_path: Path, bad: set[str]) -> bool:
    if not bad:
        return False
    for record in _read_jsonl(replay_path):
        if str(record.get("trace_id", "")).startswith("self_play:"):
            continue
        payload = record.get("payload", {})
        receipt = payload.get("receipt", {})
        candidate = payload.get("candidate", {})
        if receipt.get("sync_status") not in {"materialized", "committed", "reverted"}:
            continue
        if _canonical_intent(str(candidate.get("intent", ""))) in bad:
            return True
    return False


def _evaluate_perturbation_checks(seed: dict[str, Any], frontier: list[dict[str, Any]], scorecard: dict[str, Any]) -> list[dict[str, Any]]:
    checks = seed.get("expectations", {}).get("perturbation_checks", []) or []
    top_intents = [_canonical_intent(str(row.get("intent", ""))) for row in frontier]
    failure_modes = scorecard.get("self_play", {}).get("failure_modes", {}) or {}
    denials = int(scorecard.get("acting", {}).get("denials", 0) or 0)
    out: list[dict[str, Any]] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        kind = str(check.get("check", "note"))
        expected = _canonical_intent(str(check.get("intent", ""))) if check.get("intent") else ""
        passed = True
        detail = ""
        if kind == "intent_in_top_k":
            k = int(check.get("k", 3))
            passed = expected in top_intents[:k]
            detail = f"{expected} in top {k}: {passed}"
        elif kind == "intent_not_top1":
            passed = not top_intents or top_intents[0] != expected
            detail = f"top1={top_intents[0] if top_intents else 'none'}"
        elif kind == "failure_mode_present":
            mode = str(check.get("mode", ""))
            minimum = int(check.get("min", 1))
            count = int(failure_modes.get(mode, 0) or 0)
            passed = count >= minimum
            detail = f"{mode}={count}, min={minimum}"
        elif kind == "denial_present":
            minimum = int(check.get("min", 1))
            passed = denials >= minimum
            detail = f"denials={denials}, min={minimum}"
        elif kind == "note":
            passed = True
            detail = str(check.get("text", "tracked only"))
        else:
            passed = False
            detail = f"unknown check type: {kind}"
        out.append({"check": kind, "passed": passed, "detail": detail, "source": check})
    return out


def _lab_report(
    *,
    manifest: dict[str, Any],
    seed: dict[str, Any],
    run_dir: Path,
    valid_rows: list[dict[str, Any]],
    rejection_rows: list[dict[str, Any]],
    frontier_diff: dict[str, Any],
    scorecard: dict[str, Any],
) -> dict[str, Any]:
    tuned = list(frontier_diff.get("tuned_frontier", []) or [])
    top = tuned[0] if tuned else {}
    top_intent = _canonical_intent(str(top.get("intent", ""))) if top else None
    tuned_intents = [_canonical_intent(str(row.get("intent", ""))) for row in tuned]
    other_count = sum(1 for intent in tuned_intents if intent == "other")
    good = {_canonical_intent(str(item)) for item in seed.get("expectations", {}).get("expected_good_intents", [])}
    bad = _expected_bad(seed)
    hit_intent = next((intent for intent in tuned_intents[:3] if intent in good), None)
    bad_committed = _committed_bad_intent(run_dir / "replay.jsonl", bad)
    metrics = {
        "valid_candidates": len(valid_rows),
        "valid_frontier": len(valid_rows) >= 3,
        "generated_items": len(valid_rows) + len(rejection_rows),
        "rejections": len(rejection_rows),
        "duplicate_rejections": sum(1 for row in rejection_rows if row.get("reason") == "duplicate_candidate_id"),
        "other_intent_count": other_count,
        "tuned_frontier_candidates": len(tuned_intents),
        "other_intent_rate": round(other_count / len(tuned_intents), 4) if tuned_intents else 0.0,
        "frontier_distinct_intents": len({intent for intent in tuned_intents if intent != "other"}),
        "top_candidate_intent": top_intent,
        "top_candidate_expected_reward": top.get("expected_reward"),
        "top_candidate_predicted_regret": top.get("predicted_regret"),
        "top_candidate_predicted_social_risk": top.get("predicted_social_risk"),
        "top_candidate_right_moment_decision": top.get("right_moment_decision"),
        "leader_changed_after_tuning": bool(frontier_diff.get("leader_changed")),
        "avg_reward_delta_after_tuning": frontier_diff.get("avg_reward_delta"),
        "self_play_average_reward": scorecard.get("self_play", {}).get("average_reward", 0.0),
        "failure_modes": scorecard.get("self_play", {}).get("failure_modes", {}),
        "receipts": scorecard.get("acting", {}).get("receipts", 0),
        "denials": scorecard.get("acting", {}).get("denials", 0),
        "invariant_violations": scorecard.get("invariants", {}).get("violations", 0),
    }
    expectation_results = {
        "expected_intent_hit": bool(hit_intent) if good else True,
        "expected_intent_hit_detail": f"{hit_intent} in tuned top 3" if hit_intent else f"top3={tuned_intents[:3]} expected={sorted(good)}",
        "bad_intent_top1": bool(top_intent and top_intent in bad),
        "bad_intent_committed": bad_committed,
        "perturbation_checks": _evaluate_perturbation_checks(seed, tuned, scorecard),
    }
    return {
        "lab_schema_version": LAB_SCHEMA_VERSION,
        "experiment_id": manifest["experiment_id"],
        "batch_id": manifest["batch_id"],
        "seed_id": manifest["seed_id"],
        "runtime_mode": manifest["runtime_mode"],
        "policy_tuning_id": manifest["policy_tuning_id"],
        "status": manifest["status"],
        "skip_reason": manifest.get("skip_reason"),
        "metrics": metrics,
        "expectation_results": expectation_results,
        "scorecard_decision": scorecard.get("decision", "hold"),
    }


def _postprocess(
    *,
    run_dir: Path,
    manifest: dict[str, Any],
    seed: dict[str, Any],
    observation: RawCalendarObservation,
    biography: UserBiography,
    valid_rows: list[dict[str, Any]],
    rejection_rows: list[dict[str, Any]],
    status: str,
    skip_reason: str | None = None,
) -> None:
    replay_path = run_dir / "replay.jsonl"
    if not replay_path.exists():
        replay_path.write_text("", encoding="utf-8")
    atomic_write_json(run_dir / "observation.json", to_jsonable(observation))
    atomic_write_json(run_dir / "profile.json", biography.to_dict())
    _write_jsonl(run_dir / "valid_candidates.jsonl", valid_rows)
    _write_jsonl(run_dir / "model_generation_rejections.jsonl", rejection_rows)
    records = _read_jsonl(replay_path)
    violations = [v.to_dict() for v in check_replay(records)]
    invariant_report = {"checked": ["I2", "I6"], "violations": len(violations), "details": violations}
    atomic_write_json(run_dir / "invariant_report.json", invariant_report)
    buffer = ReplayBuffer.load_jsonl(replay_path)
    offline_report = build_policy_report(buffer)
    atomic_write_json(run_dir / "offline_policy_report.json", offline_report)
    policy_tuning = offline_report.get("policy_tuning", {}) or {"tuning_id": "empty"}
    atomic_write_json(run_dir / "policy_tuning.json", policy_tuning)
    frontier_diff = build_diff(
        observation_path=run_dir / "observation.json",
        profile_path=run_dir / "profile.json",
        tuning_path=run_dir / "policy_tuning.json",
        goal=str(seed.get("goal", "")),
    )
    atomic_write_json(run_dir / "frontier_diff.json", frontier_diff)
    scorecard = build_scorecard(replay_path=replay_path, frontier_diff=frontier_diff, offline_report=offline_report)
    atomic_write_json(run_dir / "scorecard.json", scorecard)
    _finish_manifest(run_dir / "manifest.json", manifest, status, skip_reason)
    lab_report = _lab_report(
        manifest=manifest,
        seed=seed,
        run_dir=run_dir,
        valid_rows=valid_rows,
        rejection_rows=rejection_rows,
        frontier_diff=frontier_diff,
        scorecard=scorecard,
    )
    lab_report["status"] = status
    lab_report["skip_reason"] = skip_reason
    atomic_write_json(run_dir / "lab_report.json", lab_report)


def run_import(args: argparse.Namespace) -> int:
    out_root = _resolve_path(args.out_root)
    experiment_id = _allocate_experiment_id(out_root, args.experiment_id)
    run_dir = out_root / experiment_id
    if run_dir.exists() and not args.force:
        raise FileExistsError(f"{run_dir} exists; pass --force to replace it")
    run_dir.mkdir(parents=True, exist_ok=True)
    replay_src = _resolve_path(args.from_replay, base=Path.cwd())
    if not replay_src.exists():
        raise FileNotFoundError(f"import replay not found: {replay_src}")
    if args.seed:
        seed_path = _seed_path(args.seed)
        seed, observation, biography = _load_seed(seed_path)
    else:
        seed, observation, biography, seed_path = _sample_seed(args.seed_id or replay_src.parent.name, args.goal)
    seed["seed_id"] = args.seed_id or seed.get("seed_id") or replay_src.parent.name
    tuning, tuning_path = _load_tuning(_resolve_path(args.tuning) if args.tuning else _default_tuning_path())
    manifest = _base_manifest(
        experiment_id=experiment_id,
        batch_id=args.batch,
        seed=seed,
        seed_path=seed_path,
        runtime=args.runtime,
        self_play_backend=SelfPlayActionBackend(args.self_play_backend),
        episodes=0,
        tuning=tuning,
        tuning_path=tuning_path,
        observation_path=run_dir / "observation.json",
        profile_path=run_dir / "profile.json",
        provider_backend="imported_replay",
        imported=True,
    )
    atomic_write_json(run_dir / "manifest.json", manifest)
    shutil.copyfile(replay_src, run_dir / "replay.jsonl")
    _postprocess(
        run_dir=run_dir,
        manifest=manifest,
        seed=seed,
        observation=observation,
        biography=biography,
        valid_rows=[],
        rejection_rows=[],
        status="completed",
    )
    print(json.dumps({"experiment_id": experiment_id, "run_dir": _rel(run_dir), "status": "completed"}, indent=2, sort_keys=True))
    return 0


def run_seed(args: argparse.Namespace) -> int:
    out_root = _resolve_path(args.out_root)
    experiment_id = _allocate_experiment_id(out_root, args.experiment_id)
    run_dir = out_root / experiment_id
    if run_dir.exists():
        if not args.force:
            raise FileExistsError(f"{run_dir} exists; pass --force to replace it")
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    seed_path = _seed_path(args.seed)
    seed, observation, biography = _load_seed(seed_path)
    tuning_arg = _resolve_path(args.tuning) if args.tuning else _default_tuning_path()
    tuning, tuning_path = _load_tuning(tuning_arg)
    backend = SelfPlayActionBackend(args.self_play_backend)
    episodes = min(int(args.episodes), BACKEND_POLICIES[backend].max_episodes)
    provider_backend = "apple_eventkit" if backend == SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX else os.environ.get("CALENDAR_PILOT_PROVIDER_BACKEND", "deterministic")
    manifest = _base_manifest(
        experiment_id=experiment_id,
        batch_id=args.batch,
        seed=seed,
        seed_path=seed_path,
        runtime=args.runtime,
        self_play_backend=backend,
        episodes=episodes,
        tuning=tuning,
        tuning_path=tuning_path,
        observation_path=run_dir / "observation.json",
        profile_path=run_dir / "profile.json",
        provider_backend=provider_backend,
    )
    manifest["simulator_version"] = args.simulator_version
    manifest["simulator_seed"] = int(args.simulator_seed)
    atomic_write_json(run_dir / "manifest.json", manifest)
    replay = ReplayBuffer()
    replay.set_jsonl_path(run_dir / "replay.jsonl")
    policy = _model_policy(args.runtime, tuning)
    skip_reason = _live_skip_reason(policy, backend) if args.runtime == "live_diffusiongemma" else None
    if skip_reason:
        _postprocess(
            run_dir=run_dir,
            manifest=manifest,
            seed=seed,
            observation=observation,
            biography=biography,
            valid_rows=[],
            rejection_rows=[],
            status="skipped",
            skip_reason=skip_reason,
        )
        print(json.dumps({"experiment_id": experiment_id, "run_dir": _rel(run_dir), "status": "skipped", "skip_reason": skip_reason}, indent=2, sort_keys=True))
        return 2
    valid_rows: list[dict[str, Any]] = []
    rejection_rows: list[dict[str, Any]] = []
    try:
        try:
            candidates = policy.generate_candidates(observation, biography, goal=seed.get("goal"))[:8]
        except LiveDiffusionGemmaSchemaError as exc:
            candidates = []
            rejection_rows = [{
                "reason": "live_frontier_schema_failure",
                "schema_errors": [str(exc)],
                "recoverable": False,
            }]
        else:
            valid_rows, rejection_rows = _frontier_rows(policy, candidates)
        _append_frontier_replay(replay, candidates, rejection_rows, policy, observation)
        if candidates:
            execution_policy = StaticFrontierPolicy(policy, candidates)
            with _kernel_context(backend) as kernel:
                provider = _provider_for_backend(backend, run_dir, observation)
                runtime = CodexToolRuntime(policy=execution_policy, kernel=kernel, replay=replay, provider=provider)
                CodexToolPlanner(runtime=runtime).plan_goal(str(seed.get("goal", "")), observation, biography, authority_tier=_authority_tier(seed), commit=bool(args.commit))
                runner = SelfPlayRunner(
                    policy=execution_policy,
                    kernel=kernel,
                    replay=replay,
                    action_backend=backend,
                    provider=provider if backend != SelfPlayActionBackend.STUB_FAST else None,
                    user_simulator=UserSimulator(seed=int(args.simulator_seed), simulator_version=args.simulator_version),
                )
                runner.run(observation, biography, episodes=episodes, authority_tier=_authority_tier(seed))
        replay.save_jsonl(run_dir / "replay.jsonl")
    except Exception as exc:
        replay.save_jsonl(run_dir / "replay.jsonl")
        _finish_manifest(run_dir / "manifest.json", manifest, "failed", None)
        raise RuntimeError(str(exc)) from exc
    _postprocess(
        run_dir=run_dir,
        manifest=manifest,
        seed=seed,
        observation=observation,
        biography=biography,
        valid_rows=valid_rows,
        rejection_rows=rejection_rows,
        status="completed",
    )
    print(json.dumps({"experiment_id": experiment_id, "run_dir": _rel(run_dir), "status": "completed"}, indent=2, sort_keys=True))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="")
    parser.add_argument("--runtime", default="fixture", choices=["fixture", "live_diffusiongemma"])
    parser.add_argument("--self-play-backend", default="stub_fast", choices=[item.value for item in SelfPlayActionBackend])
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--simulator-version", default="sim_v2.1", choices=["sim_v2", "sim_v2.1"])
    parser.add_argument("--simulator-seed", type=int, default=7)
    parser.add_argument("--batch", default="adhoc")
    parser.add_argument("--tuning", default="")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--experiment-id", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--from-replay", default="")
    parser.add_argument("--seed-id", default="")
    parser.add_argument("--goal", default="")
    args = parser.parse_args()
    try:
        code = run_import(args) if args.from_replay else run_seed(args)
    except Exception as exc:
        print(f"run_lab_experiment failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
