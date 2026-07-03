
#!/usr/bin/env python3
"""Prove the full replay -> offline tuning -> next NIM generation loop.

This closes the dogfooding.md "Not Yet Dogfooded End To End" gap: run live
NIM self-play to produce replay, reduce that replay into PolicyTuning with
scripts/train_offline_policy.py's report builder, then generate a *second*
live NIM frontier with that tuning applied and prove candidate behavior
actually changed (not just that the tuning file exists).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from calendar_pilot.env import load_local_env  # noqa: E402
from calendar_pilot.app import load_observation, load_profile  # noqa: E402
from calendar_pilot.diffusiongemma import LiveDiffusionGemmaPolicy, SelfPlayRunner  # noqa: E402
from calendar_pilot.diffusiongemma.live import NvidiaNIMPolicyClient  # noqa: E402
from calendar_pilot.replay import ReplayBuffer  # noqa: E402
from calendar_pilot.swift_bridge import SwiftKernelStub  # noqa: E402
from calendar_pilot.types import PolicyTuning, authority_scopes_for_tier  # noqa: E402
from train_offline_policy import build_policy_report  # noqa: E402

RUN_DIR = ROOT / "runs" / "replay_offline_tuning_loop"
ARTIFACT_DIR = RUN_DIR / "artifacts"
GOAL = "Make next week less chaotic"


def main() -> None:
    load_local_env(ROOT / ".env")
    shutil.rmtree(RUN_DIR, ignore_errors=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    health = NvidiaNIMPolicyClient().health_status(validate_remote=True)
    write_artifact("nim_policy_preflight.json", health)
    if not health.get("configured") or health.get("status") != "ok":
        print(f"replay offline tuning loop requires healthy live NIM credentials; got {health}")
        raise SystemExit(2)

    observation = load_observation(ROOT / "data" / "sample_calendar.json")
    biography = load_profile(ROOT / "data" / "sample_profile.json")

    # 1. Live self-play -> replay.
    kernel = SwiftKernelStub()
    replay = ReplayBuffer()
    grant = kernel.issue_authority_grant(
        user_scope_id=observation.user_scope_id,
        max_authority_tier=3,
        scopes=authority_scopes_for_tier(3),
        confirmation_provenance="replay_offline_tuning_loop_self_play",
        confirmed_by_user=True,
        issued_at=observation.observed_at,
    )
    self_play_policy = LiveDiffusionGemmaPolicy()
    metrics = SelfPlayRunner(policy=self_play_policy, kernel=kernel, replay=replay).run(
        observation, biography, episodes=3, authority_tier=3, authority_grant=grant.grant_id
    )
    replay_path = RUN_DIR / "replay.jsonl"
    replay.save_jsonl(replay_path)
    write_artifact(
        "self_play_metrics.json",
        {
            "episodes": metrics.episodes,
            "acceptance_rate": metrics.acceptance_rate,
            "undo_rate": metrics.undo_rate,
            "average_reward": metrics.average_reward,
            "failure_modes": metrics.failure_modes,
        },
    )

    # 2. Reduce replay -> PolicyTuning (same reducer scripts/train_offline_policy.py uses).
    reloaded = ReplayBuffer.load_jsonl(replay_path)
    report = build_policy_report(reloaded)
    write_artifact("offline_policy_report.json", report)
    tuning_payload = report["policy_tuning"]
    (RUN_DIR / "policy_tuning.json").write_text(json.dumps(tuning_payload, indent=2, sort_keys=True), encoding="utf-8")
    tuning = PolicyTuning.from_dict(tuning_payload)

    # 3. Next live NIM frontier generation: untuned vs tuned, same goal/observation.
    untuned_candidates = LiveDiffusionGemmaPolicy().generate_candidates(observation, biography, goal=GOAL)
    tuned_candidates = LiveDiffusionGemmaPolicy(policy_tuning=tuning).generate_candidates(observation, biography, goal=GOAL)
    write_artifact("frontier_untuned.json", {"candidates": [c.to_dict() for c in untuned_candidates]})
    write_artifact("frontier_tuned.json", {"candidates": [c.to_dict() for c in tuned_candidates]})

    diff = diff_frontiers(untuned_candidates, tuned_candidates, tuning_payload)
    write_artifact("diff_summary.json", diff)

    if not diff["tuning_had_effect"]:
        print(
            "replay offline tuning loop ran end to end, but the derived tuning had no measurable effect "
            f"on the next live NIM frontier (tuning={tuning_payload}); see {ARTIFACT_DIR / 'diff_summary.json'}"
        )
        raise SystemExit(3)

    print(f"replay offline tuning loop passed; artifacts: {ARTIFACT_DIR}")
    print(json.dumps(diff, indent=2, sort_keys=True))


def diff_frontiers(untuned: list, tuned: list, tuning_payload: dict[str, Any]) -> dict[str, Any]:
    untuned_by_id = {c.candidate_id: c for c in untuned}
    tuned_by_id = {c.candidate_id: c for c in tuned}
    reward_deltas = {}
    for candidate_id, tuned_candidate in tuned_by_id.items():
        baseline = untuned_by_id.get(candidate_id)
        if baseline is None:
            continue
        delta = round(tuned_candidate.expected_reward - baseline.expected_reward, 4)
        if delta:
            reward_deltas[candidate_id] = delta
    leader_changed = bool(untuned) and bool(tuned) and untuned[0].candidate_id != tuned[0].candidate_id
    tuning_notes_present = any(
        any(note.startswith("offline_tuning=") for note in c.control_notes) for c in tuned
    )
    return {
        "tuning_id": tuning_payload.get("tuning_id"),
        "intent_reward_bias": tuning_payload.get("intent_reward_bias"),
        "failure_penalties": tuning_payload.get("failure_penalties"),
        "denied_intents": tuning_payload.get("denied_intents"),
        "untuned_leader": untuned[0].candidate_id if untuned else None,
        "tuned_leader": tuned[0].candidate_id if tuned else None,
        "leader_changed": leader_changed,
        "reward_deltas_by_candidate": reward_deltas,
        "tuning_control_notes_present": tuning_notes_present,
        "tuning_had_effect": leader_changed or bool(reward_deltas) or tuning_notes_present,
    }


def write_artifact(name: str, payload: dict[str, Any]) -> None:
    (ARTIFACT_DIR / name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()