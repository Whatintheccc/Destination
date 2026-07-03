from __future__ import annotations

from dataclasses import dataclass, field
import inspect
from typing import Any

from calendar_pilot.environment.taxonomy import normalize_intent, taxonomy_health
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
from calendar_pilot.types import CandidateCalendarAction, RawCalendarObservation, UserBiography


@dataclass
class FrontierGenerationResult:
    candidates: list[CandidateCalendarAction]
    rejections: list[dict[str, Any]] = field(default_factory=list)
    policy_backend: str = "unknown_policy"
    goal_routed_to_policy: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata_by_candidate: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def candidate_ids(self) -> list[str]:
        return [candidate.candidate_id for candidate in self.candidates]

    @property
    def taxonomy_health(self) -> dict[str, Any]:
        return taxonomy_health([candidate.to_dict() for candidate in self.candidates])


class FrontierService:
    """Strangler façade over heuristic/live frontier generation.

    The service owns parse-time canonicalization, rejection capture, duplicate
    candidate handling, provenance stamping, and replay rows. Existing policies
    can keep their signatures; this wrapper makes the frontier a durable lab
    object before deeper model refactors.
    """

    def __init__(self, policy: Any) -> None:
        self.policy = policy

    def generate(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        goal: str = "",
        limit: int = 5,
        replay: ReplayBuffer | None = None,
        trace_id: str | None = None,
        causal_parent_id: str | None = None,
        runtime_mode: str | None = None,
    ) -> FrontierGenerationResult:
        policy_backend = getattr(self.policy, "backend_name", type(self.policy).__name__)
        generator = self.policy.generate_candidates
        params = inspect.signature(generator).parameters
        accepts_goal = "goal" in params or any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values())
        if accepts_goal:
            raw_candidates = list(generator(observation, biography, goal=goal or None))
        else:
            raw_candidates = list(generator(observation, biography))
        metadata_for = getattr(self.policy, "policy_metadata_for_candidate", None)
        metadata_by_candidate: dict[str, dict[str, Any]] = {}
        rejections: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        candidates: list[CandidateCalendarAction] = []
        for idx, candidate in enumerate(raw_candidates):
            raw_id = candidate.candidate_id
            metadata = metadata_for(raw_id) if callable(metadata_for) else {}
            if isinstance(metadata, dict):
                validation = metadata.get("validation")
                if isinstance(validation, dict):
                    for rejection in validation.get("rejections", []) or []:
                        if isinstance(rejection, dict):
                            rejections.append(dict(rejection) | {"source_candidate_id": raw_id})
            normalized = normalize_intent(candidate.intent)
            if candidate.intent != normalized["intent"]:
                candidate.intent_raw = candidate.intent_raw or normalized.get("intent_raw", candidate.intent)
                candidate.intent = normalized["intent"]
                candidate.intent_matched_by = normalized.get("matched_by", "frontier_service")
            else:
                candidate.intent_raw = candidate.intent_raw or normalized.get("intent_raw", candidate.intent)
                if not candidate.intent_matched_by or candidate.intent_matched_by == "unknown":
                    candidate.intent_matched_by = normalized.get("matched_by", "exact")
            if not candidate.actions:
                rejections.append({"reason": "candidate_without_actions", "candidate_id": raw_id, "index": idx})
                continue
            if candidate.candidate_id in seen_ids:
                original = candidate.candidate_id
                candidate.candidate_id = f"{candidate.candidate_id}_{idx}"
                rejections.append({"reason": "duplicate_candidate_id", "candidate_id": original, "repaired_candidate_id": candidate.candidate_id, "index": idx})
            seen_ids.add(candidate.candidate_id)
            candidate.control_notes.append(f"frontier_service=canonicalized:{candidate.intent_matched_by}")
            metadata_by_candidate[candidate.candidate_id] = metadata if isinstance(metadata, dict) else {}
            candidates.append(candidate)
            if len(candidates) >= max(1, limit):
                break
        provenance = {
            "policy_backend": policy_backend,
            "runtime_mode": runtime_mode,
            "goal": goal,
            "limit": limit,
            "raw_candidate_count": len(raw_candidates),
            "valid_candidate_count": len(candidates),
            "rejection_count": len(rejections),
            "taxonomy_health": taxonomy_health([candidate.to_dict() for candidate in candidates]),
        }
        result = FrontierGenerationResult(
            candidates=candidates,
            rejections=rejections,
            policy_backend=policy_backend,
            goal_routed_to_policy=accepts_goal,
            provenance=provenance,
            metadata_by_candidate=metadata_by_candidate,
        )
        if replay is not None:
            trace = trace_id or f"frontier:{observation.observation_id}"
            replay.append_frontier_generation(
                trace_id=trace,
                policy_backend=policy_backend,
                candidates=candidates,
                rejections=rejections,
                goal=goal,
                policy_metadata=provenance,
                observation_id=observation.observation_id,
                observation_fingerprint=observation_fingerprint(observation),
                causal_parent_id=causal_parent_id,
            )
            fp = observation_fingerprint(observation)
            for rank, candidate in enumerate(candidates):
                replay.append_decision(
                    candidate,
                    rank=rank,
                    policy_version=policy_backend,
                    trace_id=trace,
                    causal_parent_id=causal_parent_id,
                    policy_metadata=metadata_by_candidate.get(candidate.candidate_id, {}) | provenance,
                    observation_id=observation.observation_id,
                    observation_fingerprint=fp,
                    runtime_mode=runtime_mode,
                )
            for rejection in rejections:
                replay.append_model_generation_rejection(rejection, trace_id=trace, causal_parent_id=causal_parent_id)
        return result
