from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
from typing import Any

from calendar_pilot.environment.fsio import append_jsonl, atomic_write_text
from calendar_pilot.types import CalendarActionReceipt, CandidateCalendarAction, RawCalendarObservation, RewardEvent, CodexToolCall, CodexToolReceipt, to_jsonable


def observation_fingerprint(observation: RawCalendarObservation | None) -> str | None:
    if observation is None:
        return None
    payload = to_jsonable(observation)
    payload.pop("observed_at", None)
    if isinstance(payload.get("events"), list):
        payload["events"] = sorted(payload["events"], key=lambda row: (str(row.get("event_id", "")), str(row.get("start", "")), str(row.get("end", ""))))
    if isinstance(payload.get("tasks"), list):
        payload["tasks"] = sorted(payload["tasks"], key=lambda row: (str(row.get("task_id", "")), str(row.get("title", ""))))
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


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
    router_decisions: int = 0
    model_generation_rejections: int = 0
    envelope_transitions: int = 0


@dataclass
class ReplayBuffer:
    records: list[ReplayRecord] = field(default_factory=list)
    jsonl_path: Path | None = field(default=None, repr=False)
    _persisted_keys: set[str] = field(default_factory=set, repr=False)

    def set_jsonl_path(self, path: str | Path | None) -> None:
        self.jsonl_path = Path(path) if path is not None else None
        self._persisted_keys = {self._record_key(record) for record in self.records}

    def append_record(self, record: ReplayRecord) -> None:
        self.records.append(record)
        key = self._record_key(record)
        if self.jsonl_path is not None and key not in self._persisted_keys:
            append_jsonl(self.jsonl_path, record.envelope())
            self._persisted_keys.add(key)

    @staticmethod
    def _record_key(record: ReplayRecord) -> str:
        if record.record_id:
            return f"{record.record_type}:{record.record_id}"
        raw = json.dumps(record.envelope(), sort_keys=True, default=str)
        return f"{record.record_type}:{hashlib.sha1(raw.encode('utf-8')).hexdigest()}"

    def append_generic(self, record_type: str, payload: dict[str, Any], *, record_id: str | None = None, trace_id: str | None = None, causal_parent_id: str | None = None) -> str:
        trace = trace_id or str(payload.get("trace_id") or record_id or record_type)
        rid = record_id or f"{record_type}:{hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:12]}"
        self.append_record(ReplayRecord(record_type=record_type, record_id=rid, trace_id=trace, causal_parent_id=causal_parent_id, payload=payload | {"trace_id": trace}))
        return rid

    def append_router_decision(self, routed: Any, *, trace_id: str | None = None, causal_parent_id: str | None = None) -> str:
        payload = routed.replay_payload() if hasattr(routed, "replay_payload") else dict(routed)
        payload.pop("record_type", None)
        turn_id = str(payload.get("turn_id") or trace_id or "router")
        return self.append_generic("router_decision", payload, record_id=f"router:{turn_id}", trace_id=trace_id or turn_id, causal_parent_id=causal_parent_id)

    def append_model_generation_rejection(self, rejection: dict[str, Any], *, trace_id: str, causal_parent_id: str | None = None) -> str:
        rid = f"model_generation_rejection:{hashlib.sha1(json.dumps(rejection, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:12]}"
        return self.append_generic("model_generation_rejection", rejection, record_id=rid, trace_id=trace_id, causal_parent_id=causal_parent_id)

    def append_envelope_transition(self, envelope: dict[str, Any], *, transition: str | None = None, trace_id: str | None = None, causal_parent_id: str | None = None) -> str:
        transition = transition or str(envelope.get("current_state") or "transition")
        env_id = str(envelope.get("envelope_id") or "env")
        rid = f"envelope_transition:{env_id}:{transition}:{len(self.records)}"
        return self.append_generic("envelope_transition", {"envelope": envelope, "transition": transition}, record_id=rid, trace_id=trace_id or str(envelope.get("trace_id") or env_id), causal_parent_id=causal_parent_id)

    def append_decision(
        self,
        candidate: CandidateCalendarAction,
        rank: int = 0,
        policy_version: str = "heuristic-v2",
        *,
        trace_id: str | None = None,
        causal_parent_id: str | None = None,
        policy_metadata: dict[str, Any] | None = None,
        observation_id: str | None = None,
        observation_fingerprint: str | None = None,
    ) -> None:
        trace = trace_id or candidate.candidate_id
        self.append_record(ReplayRecord(
            record_type="decision",
            record_id=f"decision:{candidate.candidate_id}:{rank}",
            trace_id=trace,
            causal_parent_id=causal_parent_id,
            payload={
                "candidate": candidate.to_dict(),
                "rank": rank,
                "policy_version": policy_version,
                "policy_metadata": policy_metadata or {},
                "observation_id": observation_id,
                "observation_fingerprint": observation_fingerprint,
                "trace_id": trace,
            },
        ))

    def append_receipt(
        self,
        receipt: CalendarActionReceipt,
        candidate: CandidateCalendarAction | None = None,
        *,
        trace_id: str | None = None,
        causal_parent_id: str | None = None,
        observation_id: str | None = None,
        observation_fingerprint: str | None = None,
    ) -> None:
        trace = trace_id or receipt.correlation_id or receipt.candidate_id
        payload: dict[str, Any] = {
            "receipt": receipt.to_dict(),
            "observation_id": observation_id,
            "observation_fingerprint": observation_fingerprint,
            "trace_id": trace,
        }
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        self.append_record(ReplayRecord(record_type="receipt", record_id=f"receipt:{receipt.receipt_id}", trace_id=trace, causal_parent_id=causal_parent_id, payload=payload))

    def append_reward(self, reward: RewardEvent, candidate: CandidateCalendarAction | None = None, receipt: CalendarActionReceipt | None = None, *, trace_id: str | None = None, causal_parent_id: str | None = None) -> None:
        trace = trace_id or (candidate.candidate_id if candidate is not None else reward.receipt_id)
        payload: dict[str, Any] = {"reward": reward.to_dict(), "trace_id": trace}
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        if receipt is not None:
            payload["receipt"] = receipt.to_dict()
        self.append_record(ReplayRecord(record_type="reward", record_id=f"reward:{reward.reward_event_id}", trace_id=trace, causal_parent_id=causal_parent_id, payload=payload))

    def append_episode(self, episode: Any, *, trace_id: str | None = None, causal_parent_id: str | None = None) -> None:
        payload = to_jsonable(episode)
        trace = trace_id or payload.get("chosen_candidate_id", "self_play")
        episode_id = payload.get("episode_id") or f"episode:{payload.get('episode_index', len(self.records))}"
        self.append_record(ReplayRecord(record_type="self_play_episode", record_id=str(episode_id), trace_id=trace, causal_parent_id=causal_parent_id, payload=payload))
        for idx, finding in enumerate(payload.get("findings", [])):
            self.append_record(ReplayRecord(record_type="adversary_finding", record_id=f"{episode_id}:finding:{idx}", trace_id=trace, causal_parent_id=str(episode_id), payload=finding))

    def append_tool_call(self, call: CodexToolCall) -> None:
        trace = call.correlation_id or call.tool_call_id
        self.append_record(ReplayRecord(record_type="codex_tool_call", record_id=f"tool_call:{call.tool_call_id}", trace_id=trace, payload={"call": call.to_dict(), "trace_id": trace}))

    def append_tool_receipt(self, receipt: CodexToolReceipt) -> None:
        trace = receipt.correlation_id or receipt.tool_call_id
        self.append_record(ReplayRecord(
            record_type="codex_tool_receipt",
            record_id=f"tool_receipt:{receipt.tool_call_id}:{receipt.created_at.isoformat()}",
            trace_id=trace,
            causal_parent_id=f"tool_call:{receipt.tool_call_id}",
            payload={"receipt": receipt.to_dict(), "trace_id": trace},
        ))

    def append_candidate_receipt(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt) -> None:
        trace = candidate.candidate_id
        self.append_record(ReplayRecord(
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
                # full record changed; compact later through save_jsonl/atomic rewrite
                return True
        return False

    def save_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        text = "".join(json.dumps(record.envelope(), sort_keys=True) + "\n" for record in self.records)
        atomic_write_text(p, text)
        self.jsonl_path = p
        self._persisted_keys = {self._record_key(record) for record in self.records}

    @classmethod
    def load_jsonl(cls, path: str | Path) -> "ReplayBuffer":
        buffer = cls()
        p = Path(path)
        if not p.exists():
            buffer.set_jsonl_path(p)
            return buffer
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
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
        buffer.set_jsonl_path(p)
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
                    intent = candidate.get("intent") or "unknown"
                    reward_by_intent.setdefault(intent, []).append(value)
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
            router_decisions=sum(1 for r in self.records if r.record_type == "router_decision"),
            model_generation_rejections=sum(1 for r in self.records if r.record_type == "model_generation_rejection"),
            envelope_transitions=sum(1 for r in self.records if r.record_type == "envelope_transition"),
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
                "intent_raw": candidate.get("intent_raw", candidate.get("intent")),
                "intent_matched_by": candidate.get("intent_matched_by", "unknown"),
                "expected_reward": candidate.get("expected_reward", 0.0),
                "observed_reward": reward.get("total_reward", 0.0),
                "reward_provenance": reward.get("provenance", "observed"),
                "sync_status": receipt.get("sync_status"),
                "denied_reason": receipt.get("denied_reason"),
                "right_moment_decision": candidate.get("right_moment_decision"),
                "failure_heads": list(candidate.get("reward_breakdown", {}).keys()),
                "observation_id": record.payload.get("observation_id"),
                "observation_fingerprint": record.payload.get("observation_fingerprint"),
                "trace_id": record.trace_id or record.payload.get("trace_id"),
                "record_id": record.record_id,
                "causal_parent_id": record.causal_parent_id,
            })
        return rows

    def causal_chain(self, trace_id: str) -> list[dict[str, Any]]:
        return [record.envelope() for record in self.records if record.trace_id == trace_id or record.causal_parent_id == trace_id]

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
