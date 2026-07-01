from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any

from calendar_pilot.types import CalendarActionReceipt, CandidateCalendarAction, RewardEvent, to_jsonable


@dataclass
class ReplayRecord:
    record_type: str
    payload: dict[str, Any]

    @property
    def candidate(self) -> dict[str, Any]:
        return self.payload.get("candidate", {}) if self.record_type in {"decision", "candidate_receipt"} else {}

    @property
    def receipt(self) -> dict[str, Any]:
        return self.payload.get("receipt", {})

    @property
    def reward(self) -> dict[str, Any] | None:
        return self.payload.get("reward")


@dataclass
class ReplaySummary:
    records: int
    decisions: int
    receipts: int
    rewards: int
    episodes: int
    denials: int
    average_reward: float
    reward_by_intent: dict[str, float]
    counts_by_intent: dict[str, int]
    failure_modes: dict[str, int]


@dataclass
class ReplayBuffer:
    records: list[ReplayRecord] = field(default_factory=list)

    def append_decision(self, candidate: CandidateCalendarAction, rank: int = 0, policy_version: str = "heuristic-v2") -> None:
        self.records.append(ReplayRecord(
            record_type="decision",
            payload={
                "candidate": candidate.to_dict(),
                "rank": rank,
                "policy_version": policy_version,
            },
        ))

    def append_receipt(self, receipt: CalendarActionReceipt, candidate: CandidateCalendarAction | None = None) -> None:
        payload: dict[str, Any] = {"receipt": receipt.to_dict()}
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        self.records.append(ReplayRecord(record_type="receipt", payload=payload))

    def append_reward(self, reward: RewardEvent, candidate: CandidateCalendarAction | None = None, receipt: CalendarActionReceipt | None = None) -> None:
        payload: dict[str, Any] = {"reward": reward.to_dict()}
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        if receipt is not None:
            payload["receipt"] = receipt.to_dict()
        self.records.append(ReplayRecord(record_type="reward", payload=payload))

    def append_episode(self, episode: Any) -> None:
        # Accepts diffusiongemma.self_play.SelfPlayEpisode without importing it,
        # keeping replay independent of the simulator package.
        payload = to_jsonable(episode)
        self.records.append(ReplayRecord(record_type="self_play_episode", payload=payload))
        for finding in payload.get("findings", []):
            self.records.append(ReplayRecord(record_type="adversary_finding", payload=finding))

    def append_candidate_receipt(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt) -> None:
        # Backward-compatible convenience used by older tests and demos.
        self.records.append(ReplayRecord(
            record_type="candidate_receipt",
            payload={"candidate": candidate.to_dict(), "receipt": receipt.to_dict()},
        ))

    def attach_reward(self, receipt_id: str, reward: RewardEvent) -> bool:
        reward_dict = reward.to_dict()
        for record in reversed(self.records):
            receipt = record.payload.get("receipt", {})
            if receipt.get("receipt_id") == receipt_id:
                record.payload["reward"] = reward_dict
                return True
        return False

    def save_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for record in self.records:
                f.write(json.dumps({"record_type": record.record_type, "payload": record.payload}, sort_keys=True) + "\n")

    @classmethod
    def load_jsonl(cls, path: str | Path) -> "ReplayBuffer":
        buffer = cls()
        p = Path(path)
        if not p.exists():
            return buffer
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                # Compatibility with the first replay format.
                if "record_type" not in data:
                    payload = {k: v for k, v in data.items() if k in {"candidate", "receipt", "reward"}}
                    buffer.records.append(ReplayRecord(record_type="candidate_receipt", payload=payload))
                else:
                    buffer.records.append(ReplayRecord(record_type=data["record_type"], payload=data.get("payload", {})))
        return buffer

    def average_reward(self) -> float:
        rewards = self._reward_values()
        return sum(rewards) / len(rewards) if rewards else 0.0

    def summarize(self) -> ReplaySummary:
        reward_by_intent: dict[str, list[float]] = {}
        failure_modes: dict[str, int] = {}
        denials = 0
        for record in self.records:
            payload = record.payload
            receipt = payload.get("receipt", {})
            if receipt.get("sync_status") == "denied" or receipt.get("denied_reason"):
                denials += 1
            reward = payload.get("reward")
            candidate = payload.get("candidate", {})
            if reward and candidate:
                try:
                    value = float(reward.get("total_reward", 0.0))
                    reward_by_intent.setdefault(candidate.get("intent", "unknown"), []).append(value)
                except (TypeError, ValueError):
                    pass
            if record.record_type == "adversary_finding":
                label = str(payload.get("label", "unknown"))
                failure_modes[label] = failure_modes.get(label, 0) + 1
            if record.record_type == "self_play_episode":
                for finding in payload.get("findings", []):
                    label = str(finding.get("label", "unknown"))
                    failure_modes[label] = failure_modes.get(label, 0) + 1

        counts_by_intent = {k: len(v) for k, v in reward_by_intent.items()}
        avg_by_intent = {k: round(sum(v) / len(v), 4) for k, v in reward_by_intent.items() if v}
        return ReplaySummary(
            records=len(self.records),
            decisions=sum(1 for r in self.records if r.record_type == "decision"),
            receipts=sum(1 for r in self.records if r.record_type in {"receipt", "candidate_receipt"}),
            rewards=sum(1 for r in self.records if r.record_type == "reward" or r.payload.get("reward") is not None),
            episodes=sum(1 for r in self.records if r.record_type == "self_play_episode"),
            denials=denials,
            average_reward=round(self.average_reward(), 4),
            reward_by_intent=avg_by_intent,
            counts_by_intent=counts_by_intent,
            failure_modes=failure_modes,
        )

    def training_table(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in self.records:
            reward = record.payload.get("reward")
            candidate = record.payload.get("candidate")
            receipt = record.payload.get("receipt", {})
            if not reward or not candidate:
                continue
            rows.append({
                "candidate_id": candidate.get("candidate_id"),
                "intent": candidate.get("intent"),
                "expected_reward": candidate.get("expected_reward", 0.0),
                "observed_reward": reward.get("total_reward", 0.0),
                "sync_status": receipt.get("sync_status"),
                "denied_reason": receipt.get("denied_reason"),
                "right_moment_decision": candidate.get("right_moment_decision"),
                "failure_heads": list(candidate.get("reward_breakdown", {}).keys()),
            })
        return rows

    def _reward_values(self) -> list[float]:
        rewards: list[float] = []
        for record in self.records:
            reward = record.payload.get("reward")
            if reward and "total_reward" in reward:
                try:
                    rewards.append(float(reward["total_reward"]))
                except (TypeError, ValueError):
                    pass
        return rewards
