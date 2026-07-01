from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from calendar_pilot.codex import CodexExecutiveAgent
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, SelfPlayRunner
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import RawCalendarObservation, UserBiography


def load_observation(path: str | Path) -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def load_profile(path: str | Path | None) -> UserBiography:
    if path is None:
        path = Path("data/sample_profile.json")
    return UserBiography.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def run_demo(args: argparse.Namespace) -> None:
    observation = load_observation(args.observation)
    biography = load_profile(args.profile)
    policy = DiffusionGemmaPolicy()
    kernel = SwiftKernelStub()
    codex = CodexExecutiveAgent()

    candidates = policy.generate_candidates(observation, biography)
    best = candidates[0]
    receipt = kernel.authorize_and_materialize(best, observation, granted_authority_tier=args.authority_tier)
    explanation = codex.explain(best, receipt, biography)

    print("Top candidate:")
    print(json.dumps(best.to_dict(), indent=2))
    print("\nSwift receipt:")
    print(json.dumps(receipt.to_dict(), indent=2))
    print("\nCodex explanation:")
    print(explanation)

    if args.self_play:
        replay = ReplayBuffer()
        metrics = SelfPlayRunner(policy=policy, kernel=kernel, replay=replay).run(observation, biography, episodes=args.self_play, authority_tier=args.authority_tier)
        print("\nSelf-play metrics:")
        print(json.dumps(asdict(metrics) | {"acceptance_rate": metrics.acceptance_rate, "undo_rate": metrics.undo_rate, "average_reward": metrics.average_reward}, indent=2))
        print("\nCodex self-play summary:")
        print(codex.summarize_self_play(metrics))
        if args.replay_out:
            replay.save_jsonl(args.replay_out)
            print(f"\nReplay written to {args.replay_out}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="calendar-pilot")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--observation", default="data/sample_calendar.json")
    demo.add_argument("--profile", default="data/sample_profile.json")
    demo.add_argument("--authority-tier", type=int, default=3)
    demo.add_argument("--self-play", type=int, default=5)
    demo.add_argument("--replay-out", default="")
    demo.set_defaults(func=run_demo)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
