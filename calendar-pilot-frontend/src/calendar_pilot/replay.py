from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any

from calendar_pilot.types import CalendarActionReceipt, CandidateCalendarAction, RewardEvent


@dataclass
class ReplayRecord:
    candidate: dict[str, Any]
    receipt: dict[str, Any]
    reward: dict[str, Any] | None = None


@dataclass
class ReplayBuffer:
    records: list[ReplayRecord] = field(default_factory=list)

    def append_candidate_receipt(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt) -> None:
        self.records.append(ReplayRecord(candidate=candidate.to_dict(), receipt={k: str(v) for k, v in receipt.__dict__.items()}))

    def attach_reward(self, receipt_id: str, reward: RewardEvent) -> bool:
        for record in reversed(self.records):
            if record.receipt.get("receipt_id") == receipt_id:
                record.reward = {k: str(v) for k, v in reward.__dict__.items()}
                return True
        return False

    def save_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for record in self.records:
                f.write(json.dumps(record.__dict__, sort_keys=True) + "\n")

    @classmethod
    def load_jsonl(cls, path: str | Path) -> "ReplayBuffer":
        buffer = cls()
        p = Path(path)
        if not p.exists():
            return buffer
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    buffer.records.append(ReplayRecord(**data))
        return buffer

    def average_reward(self) -> float:
        rewards = []
        for record in self.records:
            if record.reward and "total_reward" in record.reward:
                try:
                    rewards.append(float(record.reward["total_reward"]))
                except ValueError:
                    pass
        return sum(rewards) / len(rewards) if rewards else 0.0
