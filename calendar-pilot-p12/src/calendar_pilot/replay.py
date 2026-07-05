from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
from typing import Any

from calendar_pilot.environment.fsio import append_jsonl, atomic_write_text
from calendar_pilot.environment.signal_streams import infer_signal_stream, normalize_signal_stream, SignalStream
from calendar_pilot.types import CalendarActionReceipt, CandidateCalendarAction, RawCalendarObservation, RewardEvent, CodexToolCall, CodexToolReceipt, to_jsonable

REPLAY_SCHEMA_VERSION = "r1"
SUPPORTED_REPLAY_SCHEMA_VERSIONS = {REPLAY_SCHEMA_VERSION}
REPLAY_KEEP_RECORD_TYPES = {
    "envelope_transition",
    "receipt",
    "model_generation_rejection",
    "adversary_finding",
    "reward",
    "semantic_signal",
    "signal_estimator_report",
    "label_activation",
    "biography_drift_finding",
}


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    p = Path(path)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    record_schema_version: str = REPLAY_SCHEMA_VERSION
    signal_stream: str | None = None

    def __post_init__(self) -> None:
        self.signal_stream = normalize_signal_stream(self.signal_stream, self.record_type, self.payload)

    def envelope(self) -> dict[str, Any]:
        return {
            "record_schema_version": self.record_schema_version,
            "record_type": self.record_type,
            "record_id": self.record_id,
            "trace_id": self.trace_id,
            "causal_parent_id": self.causal_parent_id,
            "signal_stream": self.signal_stream or infer_signal_stream(self.record_type, self.payload),
            "payload": self.payload,
        }

    @property
    def candidate(self) -> dict[str, Any]:
        return self.payload.get("candidate", {}) if self.record_type in {"decision", "candidate_receipt", "receipt", "reward"} else {}

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
    frontier_generations: int = 0
    provider_transactions: int = 0
    tuning_reductions: int = 0
    artifact_refs: int = 0
    semantic_signals: int = 0
    signal_estimator_reports: int = 0
    label_activations: int = 0
    biography_drift_findings: int = 0
    skipped_unknown_versions: int = 0


@dataclass
class ReplayBuffer:
    records: list[ReplayRecord] = field(default_factory=list)
    jsonl_path: Path | None = field(default=None, repr=False)
    _persisted_keys: set[str] = field(default_factory=set, repr=False)
    skipped_unknown_versions: int = 0

    def set_jsonl_path(self, path: str | Path | None) -> None:
        self.jsonl_path = Path(path) if path is not None else None
        self._persisted_keys = {self._record_key(record) for record in self.records}

    def append_record(self, record: ReplayRecord) -> None:
        if not record.record_schema_version:
            record.record_schema_version = REPLAY_SCHEMA_VERSION
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

    def append_generic(self, record_type: str, payload: dict[str, Any], *, record_id: str | None = None, trace_id: str | None = None, causal_parent_id: str | None = None, record_schema_version: str = REPLAY_SCHEMA_VERSION, signal_stream: str | None = None) -> str:
        trace = trace_id or str(payload.get("trace_id") or record_id or record_type)
        payload = dict(payload)
        payload.setdefault("trace_id", trace)
        rid = record_id or f"{record_type}:{hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:12]}"
        self.append_record(ReplayRecord(record_type=record_type, record_id=rid, trace_id=trace, causal_parent_id=causal_parent_id, payload=payload, record_schema_version=record_schema_version, signal_stream=signal_stream))
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

    def append_frontier_generation(
        self,
        *,
        trace_id: str,
        policy_backend: str,
        candidates: list[CandidateCalendarAction],
        rejections: list[dict[str, Any]] | None = None,
        goal: str = "",
        policy_metadata: dict[str, Any] | None = None,
        observation_id: str | None = None,
        observation_fingerprint: str | None = None,
        causal_parent_id: str | None = None,
    ) -> str:
        from calendar_pilot.environment.taxonomy import taxonomy_health
        rows = [candidate.to_dict() for candidate in candidates]
        payload = {
            "goal": goal,
            "policy_backend": policy_backend,
            "candidate_ids": [candidate.candidate_id for candidate in candidates],
            "valid_candidate_count": len(candidates),
            "rejection_count": len(rejections or []),
            "rejections": rejections or [],
            "taxonomy_health": taxonomy_health(rows),
            "policy_metadata": policy_metadata or {},
            "observation_id": observation_id,
            "observation_fingerprint": observation_fingerprint,
        }
        rid = f"frontier_generation:{hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:12]}"
        return self.append_generic("frontier_generation", payload, record_id=rid, trace_id=trace_id, causal_parent_id=causal_parent_id, signal_stream=SignalStream.SYSTEM.value)

    def append_provider_transaction(self, *, operation: str, transaction: dict[str, Any], trace_id: str, causal_parent_id: str | None = None) -> str:
        payload = dict(transaction)
        payload["operation"] = operation
        provider_id = str(payload.get("provider_id") or payload.get("provider") or "provider")
        digest = hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        return self.append_generic("provider_transaction", payload, record_id=f"provider_transaction:{provider_id}:{operation}:{digest}", trace_id=trace_id, causal_parent_id=causal_parent_id, signal_stream=SignalStream.WORLD.value)

    def append_tuning_reduction(self, payload: dict[str, Any], *, trace_id: str = "tuning_reduction", causal_parent_id: str | None = None) -> str:
        digest = hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        return self.append_generic("tuning_reduction", payload, record_id=f"tuning_reduction:{digest}", trace_id=trace_id, causal_parent_id=causal_parent_id, signal_stream=SignalStream.SYSTEM.value)

    def append_artifact_ref(self, *, artifact_type: str, path: str | Path, trace_id: str, causal_parent_id: str | None = None, extra: dict[str, Any] | None = None) -> str:
        p = Path(path)
        payload = {
            "artifact_type": artifact_type,
            "path": str(p),
            "sha256": sha256_file(p) if p.exists() else None,
        }
        if extra:
            payload.update(extra)
        digest = hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        return self.append_generic("artifact_ref", payload, record_id=f"artifact_ref:{artifact_type}:{digest}", trace_id=trace_id, causal_parent_id=causal_parent_id, signal_stream=SignalStream.SYSTEM.value)


    def append_semantic_signal(self, signal: dict[str, Any], *, trace_id: str | None = None, causal_parent_id: str | None = None) -> str:
        payload = dict(signal)
        signal_id = str(payload.get("signal_id") or f"signal:{hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:12]}")
        payload.setdefault("signal_id", signal_id)
        return self.append_generic("semantic_signal", payload, record_id=f"semantic_signal:{signal_id}", trace_id=trace_id or signal_id, causal_parent_id=causal_parent_id, signal_stream=SignalStream.DERIVED.value)

    def append_signal_estimator_report(self, report: dict[str, Any], *, trace_id: str | None = None, causal_parent_id: str | None = None) -> str:
        payload = dict(report)
        report_id = str(payload.get("report_id") or payload.get("estimator_run_id") or f"estimator:{hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:12]}")
        payload.setdefault("report_id", report_id)
        return self.append_generic("signal_estimator_report", payload, record_id=f"signal_estimator_report:{report_id}", trace_id=trace_id or report_id, causal_parent_id=causal_parent_id, signal_stream=SignalStream.DERIVED.value)

    def append_label_activation(self, activation: dict[str, Any], *, trace_id: str | None = None, causal_parent_id: str | None = None) -> str:
        payload = dict(activation)
        activation_id = str(payload.get("activation_id") or f"label_activation:{hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:12]}")
        payload.setdefault("activation_id", activation_id)
        return self.append_generic("label_activation", payload, record_id=f"label_activation:{activation_id}", trace_id=trace_id or activation_id, causal_parent_id=causal_parent_id, signal_stream=SignalStream.ACTION.value)

    def append_biography_drift_finding(self, finding: dict[str, Any], *, trace_id: str | None = None, causal_parent_id: str | None = None) -> str:
        payload = dict(finding)
        finding_id = str(payload.get("finding_id") or f"bio_drift:{hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()[:12]}")
        payload.setdefault("finding_id", finding_id)
        return self.append_generic("biography_drift_finding", payload, record_id=f"biography_drift_finding:{finding_id}", trace_id=trace_id or finding_id, causal_parent_id=causal_parent_id, signal_stream=SignalStream.BIOGRAPHY.value)

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
        runtime_mode: str | None = None,
    ) -> None:
        trace = trace_id or candidate.candidate_id
        self.append_record(ReplayRecord(
            record_type="decision",
            record_id=f"decision:{candidate.candidate_id}:{rank}",
            trace_id=trace,
            causal_parent_id=causal_parent_id,
            signal_stream=SignalStream.SYSTEM.value,
            payload={
                "candidate": candidate.to_dict(),
                "rank": rank,
                "policy_version": policy_version,
                "policy_backend": policy_version,
                "runtime_mode": runtime_mode,
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
        runtime_mode: str | None = None,
        policy_backend: str | None = None,
    ) -> None:
        trace = trace_id or receipt.correlation_id or receipt.candidate_id
        payload: dict[str, Any] = {
            "receipt": receipt.to_dict(),
            "observation_id": observation_id,
            "observation_fingerprint": observation_fingerprint,
            "runtime_mode": runtime_mode,
            "policy_backend": policy_backend,
            "trace_id": trace,
        }
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        self.append_record(ReplayRecord(record_type="receipt", record_id=f"receipt:{receipt.receipt_id}", trace_id=trace, causal_parent_id=causal_parent_id, payload=payload, signal_stream=SignalStream.SYSTEM.value))

    def append_reward(self, reward: RewardEvent, candidate: CandidateCalendarAction | None = None, receipt: CalendarActionReceipt | None = None, *, trace_id: str | None = None, causal_parent_id: str | None = None, runtime_mode: str | None = None, policy_backend: str | None = None) -> None:
        trace = trace_id or (candidate.candidate_id if candidate is not None else reward.receipt_id)
        payload: dict[str, Any] = {"reward": reward.to_dict(), "runtime_mode": runtime_mode, "policy_backend": policy_backend, "trace_id": trace}
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        if receipt is not None:
            payload["receipt"] = receipt.to_dict()
        self.append_record(ReplayRecord(record_type="reward", record_id=f"reward:{reward.reward_event_id}", trace_id=trace, causal_parent_id=causal_parent_id, payload=payload, signal_stream=SignalStream.ACTION.value))

    def append_episode(self, episode: Any, *, trace_id: str | None = None, causal_parent_id: str | None = None) -> None:
        payload = to_jsonable(episode)
        trace = trace_id or payload.get("chosen_candidate_id", "self_play")
        episode_id = payload.get("episode_id") or f"episode:{payload.get('episode_index', len(self.records))}"
        self.append_record(ReplayRecord(record_type="self_play_episode", record_id=str(episode_id), trace_id=trace, causal_parent_id=causal_parent_id, payload=payload, signal_stream=SignalStream.SYSTEM.value))
        for idx, finding in enumerate(payload.get("findings", [])):
            self.append_record(ReplayRecord(record_type="adversary_finding", record_id=f"{episode_id}:finding:{idx}", trace_id=trace, causal_parent_id=str(episode_id), payload=finding, signal_stream=SignalStream.SYSTEM.value))

    def append_tool_call(self, call: CodexToolCall) -> None:
        trace = call.correlation_id or call.tool_call_id
        self.append_record(ReplayRecord(record_type="codex_tool_call", record_id=f"tool_call:{call.tool_call_id}", trace_id=trace, payload={"call": call.to_dict(), "trace_id": trace}, signal_stream=SignalStream.SYSTEM.value))

    def append_tool_receipt(self, receipt: CodexToolReceipt) -> None:
        trace = receipt.correlation_id or receipt.tool_call_id
        self.append_record(ReplayRecord(record_type="codex_tool_receipt", record_id=f"tool_receipt:{receipt.tool_call_id}:{receipt.created_at.isoformat()}", trace_id=trace, causal_parent_id=receipt.tool_call_id, payload={"receipt": receipt.to_dict(), "trace_id": trace}, signal_stream=SignalStream.SYSTEM.value))

    def append_candidate_receipt(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt) -> None:
        trace = candidate.candidate_id
        self.append_record(ReplayRecord(
            record_type="candidate_receipt",
            record_id=f"candidate_receipt:{receipt.receipt_id}",
            trace_id=trace,
            payload={"candidate": candidate.to_dict(), "receipt": receipt.to_dict(), "trace_id": trace},
            signal_stream=SignalStream.SYSTEM.value,
        ))

    def attach_reward(self, receipt_id: str, reward: RewardEvent) -> bool:
        reward_dict = reward.to_dict()
        for record in reversed(self.records):
            receipt = record.payload.get("receipt", {})
            if receipt.get("receipt_id") == receipt_id:
                record.payload["reward"] = reward_dict
                return True
        return False

    def compact_records(self) -> list[ReplayRecord]:
        """Deduplicate only non-keep rows by record_id while preserving evidence rows."""
        seen: set[str] = set()
        output: list[ReplayRecord] = []
        for record in self.records:
            if record.record_type in REPLAY_KEEP_RECORD_TYPES:
                output.append(record)
                continue
            key = record.record_id or self._record_key(record)
            if key in seen:
                continue
            seen.add(key)
            output.append(record)
        return output

    def save_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        text = "".join(json.dumps(record.envelope(), sort_keys=True) + "\n" for record in self.compact_records())
        atomic_write_text(p, text)
        self.jsonl_path = p
        self.records = self.compact_records()
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
                    buffer.skipped_unknown_versions += 1
                    continue
                version = data.get("record_schema_version")
                if version not in SUPPORTED_REPLAY_SCHEMA_VERSIONS:
                    buffer.skipped_unknown_versions += 1
                    continue
                buffer.records.append(ReplayRecord(
                    record_type=data["record_type"],
                    payload=data.get("payload", {}),
                    record_id=data.get("record_id", ""),
                    trace_id=data.get("trace_id", data.get("payload", {}).get("trace_id", "")),
                    causal_parent_id=data.get("causal_parent_id"),
                    record_schema_version=version,
                    signal_stream=data.get("signal_stream"),
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
            frontier_generations=sum(1 for r in self.records if r.record_type == "frontier_generation"),
            provider_transactions=sum(1 for r in self.records if r.record_type == "provider_transaction"),
            tuning_reductions=sum(1 for r in self.records if r.record_type == "tuning_reduction"),
            artifact_refs=sum(1 for r in self.records if r.record_type == "artifact_ref"),
            semantic_signals=sum(1 for r in self.records if r.record_type == "semantic_signal"),
            signal_estimator_reports=sum(1 for r in self.records if r.record_type == "signal_estimator_report"),
            label_activations=sum(1 for r in self.records if r.record_type == "label_activation"),
            biography_drift_findings=sum(1 for r in self.records if r.record_type == "biography_drift_finding"),
            skipped_unknown_versions=self.skipped_unknown_versions,
        )

    @staticmethod
    def canonical_reward_provenance(value: str | None) -> str:
        raw = str(value or "human_ui")
        mapping = {
            "observed": "legacy_observed",
            "provider": "legacy_provider",
            "adversarial": "legacy_adversarial",
            "model": "legacy_model",
        }
        return mapping.get(raw, raw)

    def training_table(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in self.records:
            if record.record_schema_version not in SUPPORTED_REPLAY_SCHEMA_VERSIONS:
                continue
            reward = record.payload.get("reward")
            candidate = record.payload.get("candidate")
            receipt = record.payload.get("receipt", {})
            stream = record.signal_stream or infer_signal_stream(record.record_type, record.payload)
            if reward and stream != SignalStream.ACTION.value:
                continue
            if not reward or not candidate:
                continue
            provenance = self.canonical_reward_provenance(str(reward.get("provenance") or "human_ui"))
            rows.append({
                "candidate_id": candidate.get("candidate_id"),
                "intent": candidate.get("intent"),
                "intent_raw": candidate.get("intent_raw", candidate.get("intent")),
                "intent_matched_by": candidate.get("intent_matched_by", "unknown"),
                "expected_reward": candidate.get("expected_reward", 0.0),
                "observed_reward": reward.get("total_reward", 0.0),
                "reward_provenance": provenance,
                "sync_status": receipt.get("sync_status"),
                "denied_reason": receipt.get("denied_reason"),
                "right_moment_decision": candidate.get("right_moment_decision"),
                "failure_heads": list(candidate.get("reward_breakdown", {}).keys()),
                "runtime_mode": record.payload.get("runtime_mode") or record.payload.get("policy_metadata", {}).get("runtime_mode") or "unknown",
                "policy_backend": record.payload.get("policy_backend") or record.payload.get("policy_version") or record.payload.get("policy_metadata", {}).get("backend") or "unknown",
                "trace_id": record.trace_id or record.payload.get("trace_id"),
                "record_id": record.record_id,
                "causal_parent_id": record.causal_parent_id,
                "record_schema_version": record.record_schema_version,
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
