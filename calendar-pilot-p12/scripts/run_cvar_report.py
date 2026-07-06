#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.types import PolicyTuning, RawCalendarObservation, UserBiography


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _tuning_from_current(current_path: Path) -> tuple[PolicyTuning, dict[str, Any]]:
    current = _read_json(current_path)
    target = _resolve(str(current.get("path", ""))) if current.get("path") else current_path
    tuning_payload = _read_json(target) if target.exists() else {}
    return PolicyTuning.from_dict(tuning_payload), {
        "current_path": str(current_path),
        "current_sha256": _sha256(current_path),
        "policy_tuning_id": current.get("policy_tuning_id") or tuning_payload.get("tuning_id"),
        "policy_tuning_path": str(target),
        "policy_tuning_sha256": _sha256(target),
    }


def _tuning_from_path(path: Path) -> tuple[PolicyTuning, dict[str, Any]]:
    payload = _read_json(path)
    return PolicyTuning.from_dict(payload), {
        "current_path": None,
        "current_sha256": None,
        "policy_tuning_id": payload.get("tuning_id"),
        "policy_tuning_path": str(path),
        "policy_tuning_sha256": _sha256(path),
    }


def _load_seed_paths(seed_set_path: Path) -> tuple[dict[str, Any], list[Path]]:
    seed_set = _read_json(seed_set_path)
    paths = [_resolve(path) for path in seed_set.get("seed_paths", [])]
    return seed_set, paths


def _frontier(seed: dict[str, Any], tuning: PolicyTuning) -> list[dict[str, Any]]:
    observation = RawCalendarObservation.from_dict(seed["observation"])
    biography = UserBiography.from_dict(seed["profile"])
    policy = DiffusionGemmaPolicy(policy_tuning=tuning)
    return [candidate.to_dict() for candidate in policy.generate_candidates(observation, biography, goal=str(seed.get("goal", "")))]


def _top_margin(frontier: list[dict[str, Any]]) -> float | None:
    if len(frontier) < 2:
        return None
    return round(float(frontier[0].get("expected_reward", 0.0)) - float(frontier[1].get("expected_reward", 0.0)), 6)


def _decision(frontiers: list[list[dict[str, Any]]]) -> str:
    if not frontiers or any(not frontier for frontier in frontiers):
        return "hold"
    top_rewards = [float(frontier[0].get("expected_reward", 0.0)) for frontier in frontiers]
    return "promote" if mean(top_rewards) >= 0.0 else "hold"


def _bootstrap(values: list[float], *, iterations: int, seed: int) -> dict[str, Any]:
    if not values:
        return {"iterations": iterations, "seed": seed, "mean_delta": None, "variance": None, "ci95": [None, None]}
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iterations):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    overall = sum(values) / n
    variance = sum((value - overall) ** 2 for value in values) / n
    means_sorted = sorted(means)
    lo = means_sorted[int(0.025 * (iterations - 1))]
    hi = means_sorted[int(0.975 * (iterations - 1))]
    return {
        "iterations": iterations,
        "seed": seed,
        "mean_delta": round(overall, 6),
        "variance": round(variance, 8),
        "bootstrap_mean_variance": round(sum((value - (sum(means) / len(means))) ** 2 for value in means) / len(means), 8),
        "ci95": [round(lo, 6), round(hi, 6)],
    }


def _seed_row(seed_path: Path, before: list[dict[str, Any]], after: list[dict[str, Any]], *, borderline_margin: float) -> dict[str, Any]:
    seed = _read_json(seed_path)
    before_top = before[0] if before else {}
    after_top = after[0] if after else {}
    before_margin = _top_margin(before)
    after_margin = _top_margin(after)
    delta = round(float(after_top.get("expected_reward", 0.0)) - float(before_top.get("expected_reward", 0.0)), 6) if before_top and after_top else 0.0
    borderline = any(margin is not None and abs(margin) <= borderline_margin for margin in [before_margin, after_margin])
    flipped = bool(before_top and after_top and before_top.get("candidate_id") != after_top.get("candidate_id"))
    return {
        "seed_id": seed.get("seed_id", seed_path.stem),
        "seed_path": str(seed_path),
        "seed_sha256": _sha256(seed_path),
        "before_top_candidate_id": before_top.get("candidate_id"),
        "after_top_candidate_id": after_top.get("candidate_id"),
        "before_top_intent": before_top.get("intent"),
        "after_top_intent": after_top.get("intent"),
        "before_top_reward": before_top.get("expected_reward"),
        "after_top_reward": after_top.get("expected_reward"),
        "delta_top_reward": delta,
        "before_margin": before_margin,
        "after_margin": after_margin,
        "borderline": borderline,
        "top_candidate_flipped": flipped,
        "before_candidate_ids": [row.get("candidate_id") for row in before],
        "after_candidate_ids": [row.get("candidate_id") for row in after],
    }


def build_report(
    *,
    seed_set_path: Path,
    thresholds_path: Path,
    before_current_path: Path,
    after_tuning_path: Path | None = None,
    out: Path | None = None,
) -> dict[str, Any]:
    seed_set, seed_paths = _load_seed_paths(seed_set_path)
    thresholds = _read_json(thresholds_path)
    before_tuning, before_pin = _tuning_from_current(before_current_path)
    after_tuning, after_pin = _tuning_from_path(after_tuning_path) if after_tuning_path is not None else (before_tuning, dict(before_pin))
    iterations = int(thresholds.get("bootstrap_iterations", 200))
    bootstrap_seed = int(thresholds.get("bootstrap_seed", 1729))
    borderline_margin = float(thresholds.get("borderline_margin", 0.05))
    seed_rows: list[dict[str, Any]] = []
    before_frontiers: list[list[dict[str, Any]]] = []
    after_frontiers: list[list[dict[str, Any]]] = []
    errors: list[dict[str, Any]] = []
    for seed_path in seed_paths:
        try:
            seed = _read_json(seed_path)
            before = _frontier(seed, before_tuning)
            after = _frontier(seed, after_tuning)
        except Exception as exc:
            errors.append({"seed_path": str(seed_path), "error": str(exc)})
            continue
        before_frontiers.append(before)
        after_frontiers.append(after)
        seed_rows.append(_seed_row(seed_path, before, after, borderline_margin=borderline_margin))
    deltas = [float(row["delta_top_reward"]) for row in seed_rows]
    bootstrap = _bootstrap(deltas, iterations=iterations, seed=bootstrap_seed)
    borderline = [row for row in seed_rows if row["borderline"]]
    borderline_flips = [row for row in borderline if row["top_candidate_flipped"]]
    flip_rate = round(len(borderline_flips) / len(borderline), 6) if borderline else 0.0
    before_decision = _decision(before_frontiers)
    after_decision = _decision(after_frontiers)
    decision_changed = before_decision != after_decision
    gates = {
        "current_pinned": {
            "status": "pass" if before_pin.get("current_sha256") and before_pin.get("policy_tuning_sha256") else "hold",
            "actual": before_pin,
        },
        "seed_set_frozen": {
            "status": "pass" if seed_paths and all(row.get("seed_sha256") for row in seed_rows) else "hold",
            "actual": {"seed_set_path": str(seed_set_path), "seed_set_sha256": _sha256(seed_set_path), "seed_count": len(seed_rows)},
        },
        "bootstrap_variance": {
            "status": "pass" if bootstrap.get("variance") is not None and float(bootstrap["variance"]) <= float(thresholds.get("max_delta_variance", 0.0025)) else "hold",
            "actual": bootstrap.get("variance"),
            "threshold": thresholds.get("max_delta_variance", 0.0025),
        },
        "borderline_flip_rate": {
            "status": "pass" if flip_rate <= float(thresholds.get("max_borderline_flip_rate", 0.1)) else "hold",
            "actual": flip_rate,
            "threshold": thresholds.get("max_borderline_flip_rate", 0.1),
        },
        "promotion_decision_flip": {
            "status": "pass" if (not decision_changed or bool(thresholds.get("allow_promotion_decision_flip", False))) else "hold",
            "actual": {"before": before_decision, "after": after_decision, "changed": decision_changed},
            "threshold": {"allow_promotion_decision_flip": bool(thresholds.get("allow_promotion_decision_flip", False))},
        },
        "seed_errors": {
            "status": "pass" if not errors else "hold",
            "actual": errors,
        },
    }
    decision = "pass" if all(row["status"] == "pass" for row in gates.values()) else "hold"
    payload = {
        "cvar_report_schema_version": "cvar_report.v1",
        "run_id": out.parent.name if out is not None else "cvar",
        "git_sha": _git_sha(),
        "seed_set": {
            "seed_set_id": seed_set.get("seed_set_id"),
            "path": str(seed_set_path),
            "sha256": _sha256(seed_set_path),
            "seed_count": len(seed_rows),
        },
        "thresholds": {
            "path": str(thresholds_path),
            "sha256": _sha256(thresholds_path),
            "values": thresholds,
        },
        "before_current": before_pin,
        "after_tuning": after_pin,
        "frozen_candidate_set": seed_rows,
        "bootstrap": bootstrap,
        "borderline": {
            "margin_threshold": borderline_margin,
            "borderline_count": len(borderline),
            "flip_count": len(borderline_flips),
            "flip_rate": flip_rate,
        },
        "promotion_decisions": {
            "before": before_decision,
            "after": after_decision,
            "changed": decision_changed,
        },
        "gates": gates,
        "decision": decision,
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-set", default="experiments/configs/cvar_seed_set.json")
    parser.add_argument("--thresholds", default="experiments/configs/cvar_thresholds.json")
    parser.add_argument("--before-current", default="experiments/promoted/CURRENT.json")
    parser.add_argument("--after-tuning", default="")
    parser.add_argument("--out", default="runs/cvar_report.json")
    args = parser.parse_args()
    out = _resolve(args.out)
    payload = build_report(
        seed_set_path=_resolve(args.seed_set),
        thresholds_path=_resolve(args.thresholds),
        before_current_path=_resolve(args.before_current),
        after_tuning_path=_resolve(args.after_tuning) if args.after_tuning else None,
        out=out,
    )
    atomic_write_json(out, payload)
    print(json.dumps({"ok": payload["decision"] == "pass", "decision": payload["decision"], "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
