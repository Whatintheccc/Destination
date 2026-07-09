from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterator

from calendar_pilot.codex import CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.frontier_service import FrontierService
from calendar_pilot.diffusiongemma.live import (
    LiveDiffusionGemmaNetworkError,
    LiveDiffusionGemmaSchemaError,
)
from calendar_pilot.environment.explain import (
    explain_authority,
    explain_candidate,
    explain_provider,
    explain_trajectory,
)
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.invariants import check_replay
from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.providers import DeterministicCalendarProvider
from calendar_pilot.providers.base import ProviderVerificationResult
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge import SwiftKernelStub
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    Belief,
    CalendarActionReceipt,
    CandidateCalendarAction,
    CodexToolCall,
    CodexToolName,
    RawCalendarObservation,
    Reversibility,
    RewardEvent,
    SemanticSignal,
    UserBiography,
)


ROOT = Path(__file__).resolve().parents[3]


class _TimeoutPolicy:
    backend_name = "deterministic_timeout_respondent"

    def generate_candidates(self, *_args: Any, **_kwargs: Any) -> list[CandidateCalendarAction]:
        raise LiveDiffusionGemmaNetworkError("deterministic respondent timed out")


class _SchemaFailurePolicy:
    backend_name = "deterministic_schema_failure_respondent"

    def generate_candidates(self, *_args: Any, **_kwargs: Any) -> list[CandidateCalendarAction]:
        raise LiveDiffusionGemmaSchemaError("deterministic response failed typed validation")


class _VerifyFailureProvider(DeterministicCalendarProvider):
    def verify(self, transaction: Any, *, observation: RawCalendarObservation | None = None) -> ProviderVerificationResult:
        payload = transaction.to_dict() if hasattr(transaction, "to_dict") else dict(transaction or {})
        return ProviderVerificationResult(
            provider_id=self.provider_id,
            status="unverified",
            verified_external_ids=[],
            missing_external_ids=[str(value) for value in payload.get("external_ids", [])],
            rollback_handle_id=payload.get("rollback_handle_id"),
            rollback_verified=False,
            local_time_echo_ok=False,
        )


def _json(path: Path, payload: Any) -> Path:
    atomic_write_json(path, payload)
    return path


def _load_observation() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8")))


def _load_biography() -> UserBiography:
    return UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8")))


def _calendar_state_hash(provider: DeterministicCalendarProvider) -> str:
    events = provider.state.get("events", {})
    payload = json.dumps(events, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _focus_candidate(observation: RawCalendarObservation, candidate_id: str) -> CandidateCalendarAction:
    start = observation.observed_at + timedelta(hours=4)
    return CandidateCalendarAction(
        candidate_id=candidate_id,
        intent="create_focus_block",
        actions=[
            AtomicCalendarAction(
                action_type=AtomicActionType.CREATE_FOCUS_BLOCK,
                title="Architecture eval focus block",
                start=start,
                end=start + timedelta(minutes=30),
                calendar_id="work",
            )
        ],
        target_calendars=["work"],
        affected_event_ids=[],
        affected_people_ids=[],
        reversibility=Reversibility.HIGH,
        required_authority_tier=3,
    )


def _tool_receipt_rows(replay: ReplayBuffer, tool_call_id: str) -> list[str]:
    return [
        row.record_id
        for row in replay.records
        if row.record_type == "codex_tool_receipt"
        and _dict(row.payload.get("receipt")).get("tool_call_id") == tool_call_id
    ]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _provider_operations(replay: ReplayBuffer) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in replay.records:
        if record.record_type != "provider_transaction":
            continue
        payload = dict(record.payload)
        rows.append(
            {
                "row_id": record.record_id,
                "operation": payload.get("operation"),
                "status": payload.get("status"),
                "trace_id": record.trace_id,
                "causal_parent_id": record.causal_parent_id,
                "local_time_echo_ok": payload.get("local_time_echo_ok"),
                "rollback_verified": payload.get("rollback_verified"),
                "rollback_handle_id": payload.get("rollback_handle_id"),
            }
        )
    return rows


def _save_replay(replay: ReplayBuffer, path: Path) -> Path:
    replay.save_jsonl(path)
    return path


def _commit(
    runtime: CodexToolRuntime,
    observation: RawCalendarObservation,
    biography: UserBiography,
    candidate: CandidateCalendarAction,
    grant_id: str | None,
    *,
    tool_call_id: str,
) -> Any:
    return runtime.execute(
        CodexToolCall(
            tool_call_id,
            CodexToolName.REQUEST_COMMIT,
            {"candidate": candidate.to_dict()},
            3,
            "architecture eval commit",
            authority_grant_id=grant_id,
            correlation_id=candidate.candidate_id,
        ),
        observation,
        biography,
    )


@contextmanager
def _fixture_environment() -> Iterator[None]:
    updates = {
        "CALENDAR_PILOT_RUNTIME_MODE": "fixture",
        "CALENDAR_PILOT_KERNEL_BACKEND": "stub",
        "CALENDAR_PILOT_PROVIDER_BACKEND": "deterministic",
    }
    prior = {key: os.environ.get(key) for key in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class P12CurrentAdapter:
    """Translate current P12 behavior into implementation-neutral evidence vectors.

    This is the only layer allowed to know current organ/module names. Predicates
    consume the JSON vectors below and never import these implementations.
    """

    adapter_id = "p12_current"

    def __init__(self, root: Path = ROOT) -> None:
        self.root = Path(root)
        self._cases: dict[str, Callable[[Path], tuple[dict[str, Any], list[tuple[str, Path]]]]] = {
            "frontier_normal": self._frontier_normal,
            "authority_belief_denial": self._authority_belief_denial,
            "expired_authority": self._expired_authority,
            "missing_belief_evidence": self._missing_belief_evidence,
            "action_reward": self._action_reward,
            "provider_commit": self._provider_commit,
            "provider_conflict": self._provider_conflict,
            "provider_rollback": self._provider_rollback,
            "explanation_trace": self._explanation_trace,
            "frontier_timeout": self._frontier_timeout,
            "restart_restore": self._restart_restore,
            "trajectory_projection": self._trajectory_projection,
            "authority_coexistence": self._authority_coexistence,
            "frontier_safety_vector": self._frontier_safety_vector,
            "migration_comparison": self._migration_comparison,
            "monitor_removal": self._monitor_removal,
            "authority_revoke": self._authority_revoke,
            "provider_verify_failure": self._provider_verify_failure,
            "executable_explanation_controls": self._executable_explanation_controls,
            "rollback_audit_history": self._rollback_audit_history,
        }

    def collect(self, adapter_case: str, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        try:
            collector = self._cases[adapter_case]
        except KeyError as exc:
            raise ValueError(f"unknown P12 architecture-eval case: {adapter_case}") from exc
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return collector(artifact_dir)

    def _frontier_normal(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        replay = ReplayBuffer()
        observation = _load_observation()
        result = FrontierService(DiffusionGemmaPolicy()).generate(
            observation,
            _load_biography(),
            goal="protect preparation time",
            limit=3,
            replay=replay,
            trace_id="architecture_eval_frontier_normal",
            runtime_mode="fixture",
        )
        generation_rows = [
            {"row_id": row.record_id, "trace_id": row.trace_id}
            for row in replay.records
            if row.record_type == "frontier_generation"
        ]
        decision_rows = [
            {
                "row_id": row.record_id,
                "trace_id": row.trace_id,
                "candidate_id": _dict(row.payload.get("candidate")).get("candidate_id"),
            }
            for row in replay.records
            if row.record_type == "decision"
        ]
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        vector = {
            "frontier": {
                "candidate_ids": result.candidate_ids,
                "respondent": result.policy_backend,
                "provenance": result.provenance,
                "generation_rows": generation_rows,
                "decision_rows": decision_rows,
            }
        }
        return vector, [("trajectory", replay_path)]

    def _authority_belief_denial(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        replay = ReplayBuffer()
        evidence_row_id = replay.append_generic(
            "reward",
            {"reward": {"reward_event_id": "authority_wall", "total_reward": 0.0, "provenance": "human_ui"}},
            record_id="reward:authority_wall",
            trace_id="authority_wall",
            signal_stream="action",
        )
        belief = Belief(
            belief_id="belief:authority_wall",
            user_scope_id=observation.user_scope_id,
            claim="Preparation blocks appear useful.",
            evidence_row_ids=[evidence_row_id],
            confidence=0.8,
            controls={"authority_effect": "none_without_explicit_grant"},
            version="belief.v1",
        )
        provider = DeterministicCalendarProvider(
            state_path=artifact_dir / "provider_state.json",
            seed_observation=observation,
        )
        runtime = CodexToolRuntime(kernel=SwiftKernelStub(), replay=replay, provider=provider)
        candidate = _focus_candidate(observation, "cand_belief_cannot_authorize")
        before = _calendar_state_hash(provider)
        call = CodexToolCall(
            "belief_authority_attempt",
            CodexToolName.REQUEST_COMMIT,
            {"candidate": candidate.to_dict(), "belief": belief.to_dict()},
            3,
            "attempt commit from belief without a grant",
            correlation_id=candidate.candidate_id,
        )
        receipt = runtime.execute(call, observation, _load_biography())
        after = _calendar_state_hash(provider)
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        return (
            {
                "belief": {
                    "belief_id": belief.belief_id,
                    "evidence_row_ids": belief.evidence_row_ids,
                    "authority_effect": belief.controls["authority_effect"],
                },
                "authority_attempt": {
                    "embedded_belief_id": belief.belief_id,
                    "grant_id": receipt.authority_grant_id,
                    "outcome": receipt.status.value,
                    "denied_reason": receipt.denied_reason,
                    "receipt_row_ids": _tool_receipt_rows(replay, call.tool_call_id),
                },
                "provider": {"before_state_hash": before, "after_state_hash": after},
            },
            [("trajectory", replay_path), ("provider_state", artifact_dir / "provider_state.json")],
        )

    def _expired_authority(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        replay = ReplayBuffer()
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            issued_at=observation.observed_at - timedelta(hours=2),
            ttl_minutes=30,
        )
        provider = DeterministicCalendarProvider(
            state_path=artifact_dir / "provider_state.json",
            seed_observation=observation,
        )
        runtime = CodexToolRuntime(kernel=kernel, replay=replay, provider=provider)
        before = _calendar_state_hash(provider)
        receipt = _commit(
            runtime,
            observation,
            _load_biography(),
            _focus_candidate(observation, "cand_expired_authority"),
            grant.grant_id,
            tool_call_id="expired_authority_attempt",
        )
        after = _calendar_state_hash(provider)
        receipt_rows = _tool_receipt_rows(replay, "expired_authority_attempt")
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        return (
            {
                "authority_attempt": {
                    "grant_id": grant.grant_id,
                    "issued_at": grant.issued_at.isoformat(),
                    "expires_at": grant.expires_at.isoformat(),
                    "evaluated_at": observation.observed_at.isoformat(),
                    "outcome": receipt.status.value,
                    "denied_reason": receipt.denied_reason,
                    "receipt_row_id": receipt_rows[-1] if receipt_rows else None,
                },
                "provider": {"before_state_hash": before, "after_state_hash": after},
            },
            [("trajectory", replay_path), ("provider_state", artifact_dir / "provider_state.json")],
        )

    def _missing_belief_evidence(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        construction: dict[str, Any]
        try:
            belief = Belief(
                belief_id="belief:missing_evidence",
                user_scope_id="default_user",
                claim="This uncited scalar must not exist.",
                evidence_row_ids=[],
                confidence=0.5,
                controls={"authority_effect": "none_without_explicit_grant"},
                version="belief.v1",
            )
        except Exception as exc:  # evidence is the observable rejection, not an expected flag
            construction = {"exception_type": type(exc).__name__, "message": str(exc), "object_payload": None}
        else:
            construction = {"exception_type": None, "message": None, "object_payload": belief.to_dict()}
        artifact = _json(artifact_dir / "construction_observation.json", construction)
        return {"belief_input": {"evidence_row_ids": []}, "construction": construction}, [("observation", artifact)]

    def _action_reward(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        candidate = DiffusionGemmaPolicy().generate_candidates(observation, _load_biography())[0]
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            issued_at=observation.observed_at,
        )
        receipt = kernel.authorize_and_materialize(
            candidate,
            observation,
            authority_grant=grant.grant_id,
            requested_authority_tier=3,
            correlation_id="architecture_eval_reward",
        )
        reward = RewardEvent(
            reward_event_id="architecture_eval_action_reward",
            receipt_id=receipt.receipt_id,
            observed_at=observation.observed_at,
            explicit_useful=True,
            utility_reward=0.6,
            total_reward=0.6,
            provenance="human_ui",
        )
        replay = ReplayBuffer()
        replay.append_reward(reward, candidate=candidate, receipt=receipt, trace_id=candidate.candidate_id)
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        source_by_id = {row.record_id: row for row in replay.records}
        consumed_rows = []
        for row in replay.training_table():
            source = source_by_id.get(str(row.get("record_id")))
            consumed_rows.append(
                {
                    "source_artifact": str(replay_path),
                    "row_id": row.get("record_id"),
                    "record_type": source.record_type if source else None,
                    "stream": source.signal_stream if source else None,
                    "provenance": row.get("reward_provenance"),
                }
            )
        input_rows = [
            {
                "source_artifact": str(replay_path),
                "row_id": row.record_id,
                "record_type": row.record_type,
                "stream": row.signal_stream,
                "provenance": _dict(row.payload.get("reward")).get("provenance"),
            }
            for row in replay.records
            if row.record_type == "reward"
        ]
        return {"reward": {"input_rows": input_rows, "consumed_rows": consumed_rows}}, [("trajectory", replay_path)]

    def _provider_commit(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        replay = ReplayBuffer()
        provider = DeterministicCalendarProvider(
            state_path=artifact_dir / "provider_state.json",
            seed_observation=observation,
        )
        kernel = SwiftKernelStub()
        runtime = CodexToolRuntime(kernel=kernel, replay=replay, provider=provider)
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            issued_at=observation.observed_at,
        )
        before = _calendar_state_hash(provider)
        receipt = _commit(
            runtime,
            observation,
            _load_biography(),
            _focus_candidate(observation, "cand_provider_transaction"),
            grant.grant_id,
            tool_call_id="provider_transaction_commit",
        )
        after = _calendar_state_hash(provider)
        provider_receipt = _dict(receipt.output.get("provider_receipt"))
        swift_receipt = _dict(receipt.output.get("swift_receipt"))
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        return (
            {
                "provider": {
                    "outcome": receipt.status.value,
                    "before_state_hash": before,
                    "after_state_hash": after,
                    "external_ids": provider_receipt.get("external_ids", []),
                    "rollback_handle_id": provider_receipt.get("rollback_handle_id") or swift_receipt.get("rollback_handle_id"),
                    "operations": _provider_operations(replay),
                }
            },
            [("trajectory", replay_path), ("provider_state", artifact_dir / "provider_state.json")],
        )

    def _provider_conflict(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        biography = _load_biography()
        replay = ReplayBuffer()
        provider = DeterministicCalendarProvider(
            state_path=artifact_dir / "provider_state.json",
            seed_observation=observation,
        )
        kernel = SwiftKernelStub()
        runtime = CodexToolRuntime(kernel=kernel, replay=replay, provider=provider)
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            issued_at=observation.observed_at,
        )
        first = _commit(
            runtime,
            observation,
            biography,
            _focus_candidate(observation, "cand_conflict_first"),
            grant.grant_id,
            tool_call_id="provider_conflict_first",
        )
        before_conflict = _calendar_state_hash(provider)
        second = _commit(
            runtime,
            observation,
            biography,
            _focus_candidate(observation, "cand_conflict_second"),
            grant.grant_id,
            tool_call_id="provider_conflict_second",
        )
        after_conflict = _calendar_state_hash(provider)
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        return (
            {
                "provider": {
                    "first_outcome": first.status.value,
                    "conflict_outcome": second.status.value,
                    "denied_reason": second.denied_reason,
                    "conflict_truth": second.output.get("provider_conflict_truth", []),
                    "before_conflict_hash": before_conflict,
                    "after_conflict_hash": after_conflict,
                    "denial_row_ids": _tool_receipt_rows(replay, "provider_conflict_second"),
                }
            },
            [("trajectory", replay_path), ("provider_state", artifact_dir / "provider_state.json")],
        )

    def _provider_rollback(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        biography = _load_biography()
        replay = ReplayBuffer()
        provider = DeterministicCalendarProvider(
            state_path=artifact_dir / "provider_state.json",
            seed_observation=observation,
        )
        kernel = SwiftKernelStub()
        runtime = CodexToolRuntime(kernel=kernel, replay=replay, provider=provider)
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            issued_at=observation.observed_at,
        )
        before = _calendar_state_hash(provider)
        committed = _commit(
            runtime,
            observation,
            biography,
            _focus_candidate(observation, "cand_provider_rollback"),
            grant.grant_id,
            tool_call_id="provider_rollback_commit",
        )
        after_commit = _calendar_state_hash(provider)
        swift_receipt = _dict(committed.output.get("swift_receipt"))
        handle = swift_receipt.get("rollback_handle_id")
        undo = runtime.execute(
            CodexToolCall(
                "provider_rollback_undo",
                CodexToolName.REQUEST_UNDO,
                {"rollback_handle_id": handle},
                3,
                "architecture eval undo",
                authority_grant_id=grant.grant_id,
                correlation_id="architecture_eval_rollback",
            ),
            observation,
            biography,
        )
        after_undo = _calendar_state_hash(provider)
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        return (
            {
                "provider": {
                    "commit_outcome": committed.status.value,
                    "undo_outcome": undo.status.value,
                    "undo_receipt_status": _dict(undo.output.get("swift_receipt")).get("sync_status"),
                    "rollback_handle_id": handle,
                    "before_commit_hash": before,
                    "after_commit_hash": after_commit,
                    "after_undo_hash": after_undo,
                    "operations": _provider_operations(replay),
                    "active_undo_handles_after": sorted(kernel.undo_ledger),
                }
            },
            [("trajectory", replay_path), ("provider_state", artifact_dir / "provider_state.json")],
        )

    def _explanation_trace(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        biography = _load_biography()
        candidate = DiffusionGemmaPolicy().generate_candidates(observation, biography)[0]
        replay = ReplayBuffer()
        replay.append_decision(candidate, rank=0, policy_version="fixture", trace_id="explanation_trace")
        decision_row_id = f"decision:{candidate.candidate_id}:0"
        kernel = SwiftKernelStub()
        denied_receipt = kernel.authorize_and_materialize(
            candidate,
            observation,
            authority_grant=None,
            requested_authority_tier=3,
            correlation_id="explanation_trace",
        )
        replay.append_receipt(denied_receipt, candidate, trace_id="explanation_trace", causal_parent_id=decision_row_id)
        denial_row_id = f"receipt:{denied_receipt.receipt_id}"
        reward = RewardEvent(
            reward_event_id="explanation_reward",
            receipt_id=denied_receipt.receipt_id,
            observed_at=observation.observed_at,
            explicit_useful=True,
            utility_reward=0.2,
            total_reward=0.2,
            provenance="human_ui",
        )
        replay.append_reward(reward, candidate=candidate, receipt=denied_receipt, trace_id="explanation_trace", causal_parent_id=denial_row_id)
        reward_row_id = f"reward:{reward.reward_event_id}"
        signal = SemanticSignal(
            signal_id="signal:explanation",
            user_scope_id=observation.user_scope_id,
            label="explanation_fixture",
            statement="Reversible preparation suggestions have cited evidence.",
            evidence=[reward_row_id],
            confidence=0.7,
            status="active",
            estimator_version="interruption_tolerance_v1",
        )
        signal_row_id = replay.append_semantic_signal(signal.to_dict(), trace_id="explanation_trace", causal_parent_id=reward_row_id)
        activation_row_id = replay.append_label_activation(
            {
                "activation_id": "activation:explanation",
                "signal_id": signal.signal_id,
                "status": "active",
                "actor": "user",
                "surface": "architecture_eval",
                "at": observation.observed_at.isoformat(),
            },
            trace_id="explanation_trace",
            causal_parent_id=signal_row_id,
        )
        belief = Belief.from_semantic_signal(signal, activation_row_ids=[signal_row_id, activation_row_id])
        provider_payload = {
            "provider_id": "deterministic_fixture_provider",
            "operation": "rollback",
            "rollback_handle_id": "rollback:explanation",
            "rollback_verified": True,
        }
        provider_row_id = replay.append_provider_transaction(
            operation="rollback",
            transaction=provider_payload,
            trace_id="explanation_trace",
            causal_parent_id=denial_row_id,
        )
        trajectory_rows = [record.envelope() for record in replay.records]
        answers = [
            ("belief", belief.explain("Why is this belief active?").to_dict()),
            ("authority", explain_authority(denied_receipt, "Why was this denied?", evidence_row_ids=[denial_row_id]).to_dict()),
            ("candidate", explain_candidate(candidate, "Why this candidate?", evidence_row_ids=[decision_row_id, reward_row_id]).to_dict()),
            ("provider", explain_provider(provider_payload, "What did the provider do?", evidence_row_ids=[provider_row_id]).to_dict()),
            ("trajectory", explain_trajectory(trajectory_rows, "What happened?").to_dict()),
        ]
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        vector_answers = [
            {
                "subject": subject,
                "claim": answer.get("claim"),
                "citation_ids": answer.get("evidence_row_ids", []),
                "controls": answer.get("controls", {}),
                "version": answer.get("version"),
            }
            for subject, answer in answers
        ]
        return (
            {
                "explanation": {
                    "trajectory_row_ids": [row.record_id for row in replay.records],
                    "answers": vector_answers,
                }
            },
            [("trajectory", replay_path)],
        )

    def _frontier_timeout(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        biography = _load_biography()
        replay = ReplayBuffer()
        runtime = CodexToolRuntime(policy=_TimeoutPolicy(), replay=replay)
        stale = DiffusionGemmaPolicy().generate_candidates(observation, biography)[0]
        runtime.frontier[stale.candidate_id] = stale
        before = sorted(runtime.frontier)
        receipt = runtime.execute(
            CodexToolCall(
                "frontier_timeout",
                CodexToolName.GENERATE_CANDIDATE_FRONTIER,
                {"limit": 3},
                3,
                "deterministic timeout injection",
            ),
            observation,
            biography,
        )
        failure_mode = _dict(receipt.output).get("error_category")
        failure_receipts = []
        for record in replay.records:
            if record.record_type != "codex_tool_receipt":
                continue
            payload = _dict(record.payload.get("receipt"))
            if payload.get("tool_call_id") != "frontier_timeout":
                continue
            failure_receipts.append(
                {
                    "row_id": record.record_id,
                    "status": payload.get("status"),
                    "failure_mode": _dict(payload.get("output")).get("error_category"),
                }
            )
        actuation_rows = [
            {"row_id": row.record_id, "record_type": row.record_type}
            for row in replay.records
            if row.record_type == "envelope_transition"
            and _dict(row.payload.get("envelope")).get("current_state") in {"simulate", "stage", "commit", "undo"}
        ]
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        return (
            {
                "frontier": {
                    "stale_candidate_ids_before": before,
                    "candidate_ids_after": sorted(runtime.frontier),
                    "outcome": receipt.status.value,
                    "failure_mode": failure_mode,
                    "failure_receipts": failure_receipts,
                    "actuation_rows_after_failure": actuation_rows,
                }
            },
            [("trajectory", replay_path)],
        )

    @staticmethod
    def _visible_restore_vector(session: DogfoodSessionState, view: dict[str, Any]) -> dict[str, Any]:
        candidates = _dict(view.get("frontier")).get("candidates", [])
        candidate_ids = sorted(
            str(row.get("candidate_id"))
            for row in candidates
            if isinstance(row, dict) and row.get("candidate_id")
        )
        receipt_ids = sorted(
            str(_dict(row.payload.get("receipt")).get("receipt_id"))
            for row in session.replay.records
            if _dict(row.payload.get("receipt")).get("receipt_id")
        )
        return {
            "session_id": _dict(view.get("session")).get("session_id"),
            "candidate_ids": candidate_ids,
            "receipt_ids": receipt_ids,
            "trajectory_row_ids": [row.record_id for row in session.replay.records],
            "transcript_event_count": len(session.transcript_events),
            "restore_error": session.restore_error,
        }

    def _restart_restore(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        run_dir = artifact_dir / "session"
        with _fixture_environment():
            first = DogfoodSessionState(run_dir=run_dir)
            first.create_plan("Make next week less chaotic")
            first_view = first.view()
            before = self._visible_restore_vector(first, first_view)
            first.close()
            second = DogfoodSessionState(run_dir=run_dir)
            second_view = second.view()
            after = self._visible_restore_vector(second, second_view)
            second.close()
        persisted = [
            run_dir / "session_state.json",
            run_dir / "replay.jsonl",
            run_dir / "latest.json",
        ]
        persisted = [path for path in persisted if path.exists()]
        return (
            {
                "restart_restore": {
                    "before": before,
                    "after": after,
                    "persisted_artifacts": [str(path) for path in persisted],
                }
            },
            [("session_state", path) for path in persisted],
        )

    def _trajectory_projection(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        run_dir = artifact_dir / "session"
        with _fixture_environment():
            session = DogfoodSessionState(run_dir=run_dir)
            session.create_plan("Protect preparation time")
            view = session.view()
            replay_path = _save_replay(session.replay, artifact_dir / "trajectory.jsonl")
            visible_values = {
                "session.session_id": _dict(view.get("session")).get("session_id"),
                "sidebar.sessions": _dict(view.get("sidebar")).get("sessions"),
                "runtime.runtime_mode": _dict(view.get("runtime")).get("runtime_mode"),
                "conversation.candidate_ids": [
                    row.get("candidate_id")
                    for row in _dict(view.get("frontier")).get("candidates", [])
                    if isinstance(row, dict)
                ],
                "actions.queue": _dict(view.get("actions")).get("queue"),
                "authority.history": _dict(view.get("authority")).get("history"),
            }
            session.close()
        view_path = _json(artifact_dir / "visible_state.json", view)
        required = list(visible_values)
        return (
            {
                "projection": {
                    "required_visible_paths": required,
                    "visible_values": visible_values,
                    "trajectory_row_ids": [row.record_id for row in session.replay.records],
                    "trajectory_reconstruction": {},
                    "projection_sources": ["trajectory", "session_state", "provider_state", "instrument_artifacts"],
                }
            },
            [("trajectory", replay_path), ("visible_state", view_path), ("session_state", run_dir / "session_state.json")],
        )

    def _authority_coexistence(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        kernel = SwiftKernelStub()
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            issued_at=observation.observed_at,
        )
        receipt = kernel.authorize_and_materialize(
            _focus_candidate(observation, "cand_current_authority_owner"),
            observation,
            authority_grant=grant.grant_id,
            requested_authority_tier=3,
            correlation_id="current_authority_owner",
        )
        receipt_path = _json(artifact_dir / "current_authority_receipt.json", receipt.to_dict())
        return (
            {
                "authority": {
                    "current_receipt_owners": [receipt.executed_by],
                    "current_grant_issuers": [grant.issued_by],
                    "coexistence_states": [],
                }
            },
            [("authority_receipt", receipt_path)],
        )

    def _frontier_safety_vector(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        biography = _load_biography()
        normal = FrontierService(DiffusionGemmaPolicy()).generate(observation, biography, limit=2)
        legacy_observations: list[dict[str, Any]] = [
            {
                "respondent": normal.policy_backend,
                "provenance": normal.provenance,
                "validation_errors": normal.rejections,
            }
        ]
        for policy, call_id in [(_SchemaFailurePolicy(), "schema_failure"), (_TimeoutPolicy(), "timeout_failure")]:
            runtime = CodexToolRuntime(policy=policy)
            receipt = runtime.execute(
                CodexToolCall(call_id, CodexToolName.GENERATE_CANDIDATE_FRONTIER, {"limit": 2}, 3, "failure injection"),
                observation,
                biography,
            )
            legacy_observations.append(
                {
                    "respondent": policy.backend_name,
                    "failure_mode": _dict(receipt.output).get("error_category"),
                    "validation_errors": [receipt.denied_reason] if receipt.denied_reason else [],
                }
            )
        legacy_path = _json(artifact_dir / "legacy_frontier_observations.json", legacy_observations)
        return (
            {"frontier": {"legacy_observations": legacy_observations, "target_rows": []}},
            [("frontier_observations", legacy_path)],
        )

    def _migration_comparison(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        current_artifacts = [
            self.root / "runs/b_migrate_report.json",
            self.root / "experiments/configs/b_migrate_frontend_view_state.json",
        ]
        existing = [path for path in current_artifacts if path.exists()]
        observation = {
            "reason": "current B_migrate is self-derived and does not compare protected migration observables",
            "required_observables": ["authority", "reward_source", "denial", "provenance", "rollback"],
            "current_artifacts": [str(path) for path in existing],
        }
        note_path = _json(artifact_dir / "current_migration_evidence.json", observation)
        return (
            {"migration": {"comparisons": [], "current_artifacts": [str(path) for path in existing]}},
            [("migration_observation", note_path), *[("current_bootstrap", path) for path in existing]],
        )

    def _monitor_removal(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        counterexample_id = "counterexample:reward_leakage:derived_stream"
        planted = [
            {
                "record_schema_version": "r1",
                "record_type": "reward",
                "record_id": "reward:planted_non_action",
                "trace_id": "monitor_counterexample",
                "causal_parent_id": None,
                "signal_stream": "derived",
                "payload": {"reward": {"reward_event_id": "planted_non_action", "total_reward": 1.0}},
            }
        ]
        findings = [violation.to_dict() for violation in check_replay(planted)]
        detections = [counterexample_id] if any(row.get("invariant_id") == "B4" for row in findings) else []
        planted_path = artifact_dir / "planted_counterexample.jsonl"
        planted_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in planted) + "\n", encoding="utf-8")
        findings_path = _json(artifact_dir / "baseline_monitor_findings.json", findings)
        return (
            {
                "monitors": {
                    "baseline_counterexample_ids": [counterexample_id],
                    "baseline_detection_ids": detections,
                    "baseline_findings": findings,
                    "removal_trials": [],
                }
            },
            [("counterexample", planted_path), ("monitor_findings", findings_path)],
        )

    def _authority_revoke(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        # Current Step-E evidence explains a synthetic revoked payload. It is
        # useful provenance, but it is not an operation/receipt/effectiveness test.
        from scripts.make_belief_explain_report import build_report

        report = build_report()
        synthetic = _json(artifact_dir / "synthetic_revocation_explanation.json", report["answers"]["authority_revocation"])
        return (
            {
                "authority": {
                    "revoke_attempts": [],
                    "synthetic_explanation_artifacts": [str(synthetic)],
                }
            },
            [("synthetic_explanation", synthetic)],
        )

    def _provider_verify_failure(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = _load_observation()
        replay = ReplayBuffer()
        provider = _VerifyFailureProvider(
            state_path=artifact_dir / "provider_state.json",
            seed_observation=observation,
        )
        kernel = SwiftKernelStub()
        runtime = CodexToolRuntime(kernel=kernel, replay=replay, provider=provider)
        grant = kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=3,
            issued_at=observation.observed_at,
        )
        before = _calendar_state_hash(provider)
        receipt = _commit(
            runtime,
            observation,
            _load_biography(),
            _focus_candidate(observation, "cand_provider_verify_failure"),
            grant.grant_id,
            tool_call_id="provider_verify_failure",
        )
        after = _calendar_state_hash(provider)
        replay_path = _save_replay(replay, artifact_dir / "trajectory.jsonl")
        observation_payload = {
            "legacy_outcome": receipt.status.value,
            "provider_hash_before": before,
            "provider_hash_after": after,
            "legacy_operations": _provider_operations(replay),
            "target_transition": {},
        }
        observation_path = _json(artifact_dir / "verify_failure_observation.json", observation_payload)
        return (
            {"provider_verify_failure": observation_payload},
            [
                ("trajectory", replay_path),
                ("provider_state", artifact_dir / "provider_state.json"),
                ("verify_failure_observation", observation_path),
            ],
        )

    def _executable_explanation_controls(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        observation = {
            "reason": "current explain controls are contextual metadata, not executable control contracts",
            "contextual_subjects": ["belief", "authority", "candidate", "provider", "trajectory"],
        }
        note_path = _json(artifact_dir / "current_explanation_controls.json", observation)
        return (
            {
                "executable_controls": {
                    "controls": [],
                    "contextual_subjects": observation["contextual_subjects"],
                }
            },
            [("explanation_control_observation", note_path)],
        )

    def _rollback_audit_history(self, artifact_dir: Path) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        legacy_vector, legacy_artifacts = self._provider_rollback(artifact_dir / "legacy")
        observation = {
            "reason": "current rollback proves external restoration but has no target old/new audit-retention comparison",
            "legacy_provider": legacy_vector.get("provider", {}),
            "trials": [],
        }
        note_path = _json(artifact_dir / "current_rollback_audit_observation.json", observation)
        return (
            {
                "rollback_audit": {
                    "trials": [],
                    "legacy_artifacts": [str(path) for _, path in legacy_artifacts],
                }
            },
            [("rollback_audit_observation", note_path), *legacy_artifacts],
        )
