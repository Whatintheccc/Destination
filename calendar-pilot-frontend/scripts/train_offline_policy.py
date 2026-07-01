#!/usr/bin/env python3
"""Offline training stub.

This script intentionally does not train a real model. It shows where replay data
is aggregated before replacing the reference heuristic with a learned policy.
"""
from __future__ import annotations

import argparse
from calendar_pilot.replay import ReplayBuffer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", default="runs/replay.jsonl")
    args = parser.parse_args()
    buffer = ReplayBuffer.load_jsonl(args.replay)
    print(f"records={len(buffer.records)} average_reward={buffer.average_reward():.4f}")
    print("Next step: export candidate/reward pairs to DiffusionGemma fine-tuning or offline RL pipeline.")


if __name__ == "__main__":
    main()
