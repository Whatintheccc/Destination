#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, pstdev
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.taxonomy import taxonomy_health
from calendar_pilot.types import RawCalendarObservation, UserBiography
from seed_calendar_corpus import lint_seed


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_row(seed_path: Path, repeat: int) -> dict[str, Any]:
    errors = lint_seed(seed_path)
    if errors:
        raise ValueError("seed validation failed:\n" + "\n".join(errors))
    seed = _load_json(seed_path)
    observation = RawCalendarObservation.from_dict(seed["observation"])
    biography = UserBiography.from_dict(seed["profile"])
    candidates = [candidate.to_dict() for candidate in DiffusionGemmaPolicy().generate_candidates(observation, biography, goal=seed.get("goal", ""))]
    taxonomy = taxonomy_health(candidates)
    top = candidates[0] if candidates else {}
    return {
        "repeat": repeat,
        "valid_candidates": len(candidates),
        "top_candidate_id": top.get("candidate_id"),
        "top_intent": top.get("intent"),
        "top_expected_reward": top.get("expected_reward", 0.0),
        "other_intent_rate": taxonomy.get("other_rate", 0.0),
    }


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "mean": round(mean(values), 6) if values else 0.0,
        "stddev": round(pstdev(values), 6) if len(values) > 1 else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="experiments/seeds/seed_ae_renewal_week_high_pressure.json")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--out", default="experiments/reports/variance_probe.json")
    args = parser.parse_args()
    seed_path = Path(args.seed)
    if not seed_path.is_absolute():
        seed_path = ROOT / seed_path
    rows = [_metric_row(seed_path, idx + 1) for idx in range(max(1, int(args.repeats)))]
    payload = {
        "seed_path": str(seed_path.relative_to(ROOT) if seed_path.is_relative_to(ROOT) else seed_path),
        "repeats": len(rows),
        "runtime_mode": "fixture",
        "rows": rows,
        "metrics": {
            "valid_candidates": _stats([float(row["valid_candidates"]) for row in rows]),
            "top_expected_reward": _stats([float(row["top_expected_reward"]) for row in rows]),
            "other_intent_rate": _stats([float(row["other_intent_rate"]) for row in rows]),
        },
        "leader_changed_count": len({row["top_candidate_id"] for row in rows}),
    }
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    atomic_write_json(out, payload)
    print(json.dumps({"out": str(out.relative_to(ROOT) if out.is_relative_to(ROOT) else out), "repeats": len(rows)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
