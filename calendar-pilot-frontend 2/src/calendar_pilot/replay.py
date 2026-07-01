from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any

from calendar_pilot.types import CalendarActionReceipt, CandidateCalendarAction, RewardEvent, CodexToolCall, CodexToolReceipt, to_jsonable


@dataclass
class ReplayRecord:
    record_type: str
    payload: dict[str, Any]
    record_id: str = ""
    trace_id: str = ""
    causal_parent_id: str | None = None

    def envelope(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "record_id": self.record_id,
            "trace_id": self.trace_id,
            "causal_parent_id": self.causal_parent_id,
            "payload": self.payload,
        }

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
    tool_calls: int = 0
    tool_receipts: int = 0


@dataclass
class ReplayBuffer:
    records: list[ReplayRecord] = field(default_factory=list)

    def append_decision(
        self,
        candidate: CandidateCalendarAction,
        rank: int = 0,
        policy_version: str = "heuristic-v2",
        *,
        trace_id: str | None = None,
        causal_parent_id: str | None = None,
        policy_metadata: dict[str, Any] | None = None,
    ) -> None:
        trace = trace_id or candidate.candidate_id
        self.records.append(ReplayRecord(
            record_type="decision",
            record_id=f"decision:{candidate.candidate_id}:{rank}",
            trace_id=trace,
            causal_parent_id=causal_parent_id,
            payload={
                "candidate": candidate.to_dict(),
                "rank": rank,
                "policy_version": policy_version,
                "policy_metadata": policy_metadata or {},
                "trace_id": trace,
            },
        ))

    def append_receipt(self, receipt: CalendarActionReceipt, candidate: CandidateCalendarAction | None = None, *, trace_id: str | None = None, causal_parent_id: str | None = None) -> None:
        trace = trace_id or receipt.correlation_id or receipt.candidate_id
        payload: dict[str, Any] = {"receipt": receipt.to_dict(), "trace_id": trace}
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        self.records.append(ReplayRecord(record_type="receipt", record_id=f"receipt:{receipt.receipt_id}", trace_id=trace, causal_parent_id=causal_parent_id, payload=payload))

    def append_reward(self, reward: RewardEvent, candidate: CandidateCalendarAction | None = None, receipt: CalendarActionReceipt | None = None, *, trace_id: str | None = None, causal_parent_id: str | None = None) -> None:
        trace = trace_id or (candidate.candidate_id if candidate is not None else reward.receipt_id)
        payload: dict[str, Any] = {"reward": reward.to_dict(), "trace_id": trace}
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        if receipt is not None:
            payload["receipt"] = receipt.to_dict()
        self.records.append(ReplayRecord(record_type="reward", record_id=f"reward:{reward.reward_event_id}", trace_id=trace, causal_parent_id=causal_parent_id, payload=payload))

    def append_episode(self, episode: Any, *, trace_id: str | None = None, causal_parent_id: str | None = None) -> None:
        # Accepts diffusiongemma.self_play.SelfPlayEpisode without importing it,
        # keeping replay independent of the simulator package. Findings remain
        # embedded for episode reconstruction and are also emitted as normalized
        # finding rows; summarize() counts only normalized rows to avoid double-counting.
        payload = to_jsonable(episode)
        trace = trace_id or payload.get("chosen_candidate_id", "self_play")
        episode_id = payload.get("episode_id") or f"episode:{payload.get('episode_index', len(self.records))}"
        self.records.append(ReplayRecord(record_type="self_play_episode", record_id=str(episode_id), trace_id=trace, causal_parent_id=causal_parent_id, payload=payload))
        for idx, finding in enumerate(payload.get("findings", [])):
            self.records.append(ReplayRecord(record_type="adversary_finding", record_id=f"{episode_id}:finding:{idx}", trace_id=trace, causal_parent_id=str(episode_id), payload=finding))

    def append_tool_call(self, call: CodexToolCall) -> None:
        trace = call.correlation_id or call.tool_call_id
        self.records.append(ReplayRecord(record_type="codex_tool_call", record_id=f"tool_call:{call.tool_call_id}", trace_id=trace, payload={"call": call.to_dict(), "trace_id": trace}))

    def append_tool_receipt(self, receipt: CodexToolReceipt) -> None:
        trace = receipt.correlation_id or receipt.tool_call_id
        self.records.append(ReplayRecord(record_type="codex_tool_receipt", record_id=f"tool_receipt:{receipt.tool_call_id}:{receipt.created_at.isoformat()}", trace_id=trace, causal_parent_id=receipt.tool_call_id, payload={"receipt": receipt.to_dict(), "trace_id": trace}))

    def append_candidate_receipt(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt) -> None:
        # Backward-compatible convenience used by older tests and demos.
        trace = candidate.candidate_id
        self.records.append(ReplayRecord(
            record_type="candidate_receipt",
            record_id=f"candidate_receipt:{receipt.receipt_id}",
            trace_id=trace,
            payload={"candidate": candidate.to_dict(), "receipt": receipt.to_dict(), "trace_id": trace},
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
                f.write(json.dumps(record.envelope(), sort_keys=True) + "\n")

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
                    buffer.records.append(ReplayRecord(record_type="candidate_receipt", payload=payload, record_id="legacy", trace_id=payload.get("candidate", {}).get("candidate_id", "legacy")))
                else:
                    buffer.records.append(ReplayRecord(
                        record_type=data["record_type"],
                        payload=data.get("payload", {}),
                        record_id=data.get("record_id", ""),
                        trace_id=data.get("trace_id", data.get("payload", {}).get("trace_id", "")),
                        causal_parent_id=data.get("causal_parent_id"),
                    ))
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
            tool_calls=sum(1 for r in self.records if r.record_type == "codex_tool_call"),
            tool_receipts=sum(1 for r in self.records if r.record_type == "codex_tool_receipt"),
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
                "trace_id": record.trace_id or record.payload.get("trace_id"),
                "record_id": record.record_id,
                "causal_parent_id": record.causal_parent_id,
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
