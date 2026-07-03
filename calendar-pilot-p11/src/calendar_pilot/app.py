

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from calendar_pilot.env import load_local_env
from calendar_pilot.codex import CodexExecutiveAgent, CodexToolPlanner, CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy, SelfPlayRunner
from calendar_pilot.environment.selfplay_backends import SelfPlayActionBackend
from calendar_pilot.providers import DeterministicCalendarProvider, AppleEventKitProvider
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import RawCalendarObservation, UserBiography, authority_scopes_for_tier


load_local_env()


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
    replay = ReplayBuffer()
    tool_runtime = CodexToolRuntime(policy=policy, kernel=kernel, replay=replay)
    tool_planner = CodexToolPlanner(runtime=tool_runtime)

    # Default app path is now Codex-executive: Codex inspects, asks the policy for
    # a frontier, simulates, stages, and only then requests Swift commit when the
    # authority grant and confirmation semantics permit it. The older direct path
    # remains represented in tests as a kernel primitive, not as the app flow.
    plan = tool_planner.plan_goal(args.goal, observation, biography, authority_tier=args.authority_tier, commit=args.commit)
    print("Codex executive plan:")
    print(json.dumps(plan.to_dict(), indent=2))

    committed_receipts = [r for r in plan.receipts if r.swift_receipt_id and r.status.value in {"committed", "reverted", "denied", "stageable"}]
    if committed_receipts:
        last = committed_receipts[-1]
        print("\nLast Swift-facing receipt:")
        print(json.dumps(last.to_dict(), indent=2))

    # Keep a human-readable action explanation, but make it downstream of the
    # tool plan rather than the default path into actuation.
    for receipt in reversed(plan.receipts):
        candidate_payload = receipt.output.get("candidate") if isinstance(receipt.output, dict) else None
        swift_payload = receipt.output.get("swift_receipt") if isinstance(receipt.output, dict) else None
        if isinstance(candidate_payload, dict) and isinstance(swift_payload, dict):
            from calendar_pilot.types import CandidateCalendarAction, CalendarActionReceipt
            candidate = CandidateCalendarAction.from_dict(candidate_payload)
            # CalendarActionReceipt does not need from_dict in the demo; pass a light shim by reusing the payload text.
            print("\nCodex explanation:")
            print("Codex operated through Swift. See the typed tool receipt above for authority grant, stage state, and denial/commit status.")
            print("Candidate story:")
            print("\n".join(f"- {line}" for line in candidate.model_story[:4]))
            break

    if args.self_play:
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=args.authority_tier,
            scopes=authority_scopes_for_tier(args.authority_tier),
            confirmation_provenance="demo_self_play_scope",
            confirmed_by_user=True,
            issued_at=observation.observed_at,
        )
        backend = SelfPlayActionBackend(args.self_play_backend)
        provider = DeterministicCalendarProvider(seed_observation=observation) if backend == SelfPlayActionBackend.SWIFT_IPC_DETERMINISTIC else (AppleEventKitProvider() if backend == SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX else None)
        metrics = SelfPlayRunner(policy=policy, kernel=kernel, replay=replay, action_backend=backend, provider=provider).run(observation, biography, episodes=args.self_play, authority_grant=grant.grant_id)
        print("\nSelf-play metrics:")
        print(json.dumps(asdict(metrics) | {"acceptance_rate": metrics.acceptance_rate, "undo_rate": metrics.undo_rate, "average_reward": metrics.average_reward}, indent=2))
        print("\nCodex self-play summary:")
        print(codex.summarize_self_play(metrics))
    if args.replay_out:
        replay.save_jsonl(args.replay_out)
        print(f"\nReplay written to {args.replay_out}")


def run_frontend(args: argparse.Namespace) -> None:
    from calendar_pilot.frontend.server import serve, write_demo_snapshot

    if args.write_snapshot or not args.serve:
        path = write_demo_snapshot(args.out, commit=args.commit)
        print(f"Frontend snapshot written to {path}")
    if args.serve:
        print(f"Serving frontend on http://{args.host}:{args.port}")
        serve(host=args.host, port=args.port, run_dir=args.run_dir)


def main() -> None:
    parser = argparse.ArgumentParser(prog="calendar-pilot")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--observation", default="data/sample_calendar.json")
    demo.add_argument("--profile", default="data/sample_profile.json")
    demo.add_argument("--authority-tier", type=int, default=3)
    demo.add_argument("--self-play", type=int, default=5)
    demo.add_argument("--self-play-backend", default="stub_fast", choices=["stub_fast", "swift_ipc_deterministic", "swift_ipc_eventkit_sandbox", "production_shadow"])
    demo.add_argument("--replay-out", default="")
    demo.add_argument("--codex-tools", action="store_true", help="kept for CLI compatibility; Codex tools are now the default path")
    demo.add_argument("--goal", default="Make next week less chaotic")
    demo.add_argument("--commit", action="store_true", help="allow Codex planner to request Swift commit when simulation does not require confirmation")
    demo.set_defaults(func=run_demo)

    frontend = sub.add_parser("frontend")
    frontend.add_argument("--out", default="frontend/static/frontend_state.sample.json")
    frontend.add_argument("--write-snapshot", action="store_true", help="write a demo frontend snapshot JSON")
    frontend.add_argument("--serve", action="store_true", help="serve frontend/static with Python's built-in HTTP server")
    frontend.add_argument("--host", default="127.0.0.1")
    frontend.add_argument("--port", type=int, default=8787)
    frontend.add_argument("--run-dir", default="runs/dogfood", help="session/replay state directory for the live frontend")
    frontend.add_argument("--commit", action="store_true", default=True, help="demo snapshot includes a committed safe private write")
    frontend.set_defaults(func=run_frontend)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()