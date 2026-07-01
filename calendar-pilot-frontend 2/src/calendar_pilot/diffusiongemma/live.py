from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.types import CandidateCalendarAction, RawCalendarObservation, UserBiography


LIVE_DIFFUSIONGEMMA_BACKEND = "nvidia_nim_diffusiongemma_policy"
LIVE_DIFFUSIONGEMMA_PROMPT_VERSION = "calendar_pilot_nim_policy_ranker_v1"
NVIDIA_NIM_DOC_URL = "https://docs.api.nvidia.com/nim/reference/diffusiongemma-26b-a4b-it-infer"
DEFAULT_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NIM_MODEL = "google/diffusiongemma-26b-a4b-it"


class LiveDiffusionGemmaError(RuntimeError):
    category = "live_diffusiongemma_error"


class LiveDiffusionGemmaCredentialError(LiveDiffusionGemmaError):
    category = "missing_or_invalid_credential"


class LiveDiffusionGemmaNetworkError(LiveDiffusionGemmaError):
    category = "network_failure"


class LiveDiffusionGemmaSchemaError(LiveDiffusionGemmaError):
    category = "model_policy_schema_failure"


class LiveDiffusionGemmaRuntimeError(LiveDiffusionGemmaError):
    category = "nvidia_nim_failure"


@dataclass(frozen=True)
class NIMPolicyRank:
    candidate_id: str
    rank: int
    score_delta: float
    reason: str


@dataclass(frozen=True)
class NIMPolicyResult:
    ranks: list[NIMPolicyRank]
    policy_summary: str
    metadata: dict[str, Any]


class NvidiaNIMPolicyClient:
    """NVIDIA NIM client for policy ranking over locally validated candidates."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else _nim_api_key()
        self.base_url = (base_url or os.environ.get("CALENDAR_PILOT_NIM_BASE_URL") or DEFAULT_NIM_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("CALENDAR_PILOT_NIM_MODEL") or DEFAULT_NIM_MODEL
        self.timeout_seconds = float(timeout_seconds or os.environ.get("CALENDAR_PILOT_NIM_TIMEOUT", "90"))
        self.health_cache_seconds = float(os.environ.get("CALENDAR_PILOT_NIM_HEALTH_CACHE_SECONDS", "60"))
        self._remote_health_cache: tuple[float, dict[str, Any]] | None = None

    def health_status(self, *, validate_remote: bool = False) -> dict[str, Any]:
        if not self.api_key:
            return self._health_payload({
                "status": "missing_credential",
                "configured": False,
                "credential_source": "missing",
            })
        if not validate_remote:
            return self._health_payload({
                "status": "configured",
                "configured": True,
                "credential_source": _nim_api_key_source(),
            })
        cached = self._cached_remote_health()
        if cached is not None:
            return cached
        try:
            self._request_json("GET", "/models", None)
        except LiveDiffusionGemmaCredentialError as exc:
            return self._cache_remote_health(self._health_payload({"status": "invalid_credential", "configured": True, "credential_source": _nim_api_key_source(), "reason": str(exc)}))
        except LiveDiffusionGemmaNetworkError as exc:
            return self._cache_remote_health(self._health_payload({"status": "network_failure", "configured": True, "credential_source": _nim_api_key_source(), "reason": str(exc)}))
        except LiveDiffusionGemmaError as exc:
            return self._cache_remote_health(self._health_payload({"status": "nvidia_nim_failure", "configured": True, "credential_source": _nim_api_key_source(), "reason": str(exc)}))
        return self._cache_remote_health(self._health_payload({
            "status": "ok",
            "configured": True,
            "credential_source": _nim_api_key_source(),
        }))

    def rank_candidates(
        self,
        *,
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        candidates: list[CandidateCalendarAction],
    ) -> NIMPolicyResult:
        if not self.api_key:
            raise LiveDiffusionGemmaCredentialError("NVIDIA NIM API key is required for live_diffusiongemma mode")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": self._ranking_prompt(goal, observation, biography, candidates)}],
            "max_tokens": 900,
            "temperature": 0,
            "top_p": 1,
            "stream": False,
            "response_format": self._response_format(),
            "chat_template_kwargs": {"enable_thinking": False},
        }
        data = self._request_json("POST", "/chat/completions", payload)
        parsed = self._parse_rank_payload(self._extract_text(data), candidates)
        return NIMPolicyResult(
            ranks=parsed["ranks"],
            policy_summary=parsed["policy_summary"],
            metadata={
                "backend": LIVE_DIFFUSIONGEMMA_BACKEND,
                "prompt_version": LIVE_DIFFUSIONGEMMA_PROMPT_VERSION,
                "model": self.model,
                "base_url": self.base_url,
                "response_id": data.get("id"),
                "ranked_count": len(parsed["ranks"]),
                "candidate_count": len(candidates),
                "decoding_settings": self._decoding_settings(),
                "timeout_seconds": self.timeout_seconds,
                "retry_policy": self._retry_policy(),
                "fallback_behavior": self._fallback_behavior(),
                "validation": {
                    "candidate_contract": "CandidateCalendarAction",
                    "validation_errors": parsed["validation_errors"],
                },
                "redaction_policy": "event titles, attendees, notes, and locations omitted from NIM prompt",
            },
        )

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LiveDiffusionGemmaSchemaError("NIM response did not contain choices")
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            if parts:
                return "\n".join(parts)
        raise LiveDiffusionGemmaSchemaError("NIM response did not contain text content")

    @staticmethod
    def _parse_rank_payload(text: str, candidates: list[CandidateCalendarAction]) -> dict[str, Any]:
        clean = text.strip()
        if clean.startswith("```"):
            clean = "\n".join(line for line in clean.splitlines() if not line.strip().startswith("```")).strip()
        validation_errors: list[str] = []
        try:
            payload = json.loads(clean)
        except json.JSONDecodeError:
            start = clean.find("{")
            end = clean.rfind("}")
            if start < 0 or end <= start:
                return NvidiaNIMPolicyClient._parse_rank_text_fallback(clean, candidates, "non_json_rank_text_fallback")
            try:
                payload = json.loads(clean[start:end + 1])
                validation_errors.append("json_extracted_from_surrounding_text")
            except json.JSONDecodeError:
                return NvidiaNIMPolicyClient._parse_rank_text_fallback(clean, candidates, "malformed_json_rank_text_fallback")
        if not isinstance(payload, dict):
            raise LiveDiffusionGemmaSchemaError("NIM policy response was not a JSON object")
        known = {candidate.candidate_id for candidate in candidates}
        ranks: list[NIMPolicyRank] = []
        seen: set[str] = set()
        for idx, item in enumerate(payload.get("ranked_candidates", [])):
            if not isinstance(item, dict):
                raise LiveDiffusionGemmaSchemaError(f"ranked candidate {idx} is not an object")
            candidate_id = str(item.get("candidate_id", ""))
            if candidate_id not in known or candidate_id in seen:
                continue
            seen.add(candidate_id)
            ranks.append(NIMPolicyRank(
                candidate_id=candidate_id,
                rank=max(1, int(item.get("rank", len(ranks) + 1))),
                score_delta=max(-0.5, min(0.5, float(item.get("score_delta", 0.0)))),
                reason=str(item.get("reason") or "NIM policy ranked this candidate."),
            ))
        if not ranks:
            return NvidiaNIMPolicyClient._parse_rank_text_fallback(clean, candidates, "json_without_known_rank_fallback")
        ranks.sort(key=lambda row: row.rank)
        return {"ranks": ranks, "policy_summary": str(payload.get("policy_summary") or ""), "validation_errors": validation_errors}

    @staticmethod
    def _parse_rank_text_fallback(text: str, candidates: list[CandidateCalendarAction], validation_error: str) -> dict[str, Any]:
        positions: list[tuple[int, str]] = []
        for candidate in candidates:
            match = re.search(rf"\b{re.escape(candidate.candidate_id)}\b", text)
            if match:
                positions.append((match.start(), candidate.candidate_id))
        if not positions:
            raise LiveDiffusionGemmaSchemaError("NIM policy response did not rank any known candidate")
        ranks = [
            NIMPolicyRank(
                candidate_id=candidate_id,
                rank=idx + 1,
                score_delta=0.0,
                reason="NIM response referenced this candidate outside the strict JSON schema; accepted as rank-only fallback.",
            )
            for idx, (_pos, candidate_id) in enumerate(sorted(positions))
        ]
        return {
            "ranks": ranks,
            "policy_summary": "NIM response was parsed with rank-only fallback over known candidate IDs.",
            "validation_errors": [validation_error],
        }

    @staticmethod
    def _ranking_prompt(
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        candidates: list[CandidateCalendarAction],
    ) -> str:
        context = {
            "goal": goal or "Make the week less chaotic",
            "observation": {
                "observation_id": observation.observation_id,
                "time_zone_id": observation.time_zone_id,
                "event_count": len(observation.events),
                "task_count": len(observation.tasks),
                "categories": sorted({event.category for event in observation.events}),
                "local_hour": observation.device_context.local_hour,
                "is_focus_mode": observation.device_context.is_focus_mode,
            },
            "biography": {
                "best_response_hours": biography.best_response_hours,
                "notification_fatigue": biography.notification_fatigue,
                "preference_claim_count": len(biography.preference_claims),
            },
            "candidates": [
                {
                    "candidate_id": candidate.candidate_id,
                    "intent": candidate.intent,
                    "expected_reward": candidate.expected_reward,
                    "required_authority_tier": candidate.required_authority_tier,
                    "predicted_regret": candidate.predicted_regret,
                    "predicted_social_risk": candidate.predicted_social_risk,
                    "predicted_interruption_cost": candidate.predicted_interruption_cost,
                    "right_moment_score": candidate.right_moment_score,
                    "action_types": [action.action_type.value for action in candidate.actions],
                    "story": candidate.model_story[:3],
                }
                for candidate in candidates[:10]
            ],
        }
        return (
            "You are CalendarPilot's DiffusionGemma policy ranker. Rank only the "
            "provided candidate_id values; do not invent calendar actions. Return "
            "only JSON with this shape: {\"ranked_candidates\":[{\"candidate_id\":"
            "\"...\",\"rank\":1,\"score_delta\":0.0,\"reason\":\"...\"}],"
            "\"policy_summary\":\"...\"}. score_delta must be between -0.5 and 0.5. "
            "Redacted context:\n"
            + json.dumps(context, sort_keys=True)
        )

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        url = self.base_url + path
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds, context=_nim_tls_context()) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
                if response.status == 202:
                    return self._poll_status(data)
                return data
        except HTTPError as exc:
            text = _redact_secret_text(exc.read().decode("utf-8", errors="replace"))
            if exc.code in {401, 403}:
                raise LiveDiffusionGemmaCredentialError(text or f"NIM request unauthorized: {exc.code}") from exc
            if exc.code == 422:
                raise LiveDiffusionGemmaSchemaError(text or "NIM request validation failed") from exc
            if exc.code == 429:
                raise LiveDiffusionGemmaNetworkError(text or "NIM request rate limited") from exc
            raise LiveDiffusionGemmaRuntimeError(text or f"NIM request failed: {exc.code}") from exc
        except (TimeoutError, URLError, OSError, ssl.SSLError) as exc:
            raise LiveDiffusionGemmaNetworkError(str(exc)) from exc
        except json.JSONDecodeError as exc:
            raise LiveDiffusionGemmaSchemaError(f"NIM response was not JSON: {exc}") from exc

    def _cached_remote_health(self) -> dict[str, Any] | None:
        if self._remote_health_cache is None:
            return None
        cached_at, payload = self._remote_health_cache
        if time.time() - cached_at <= self.health_cache_seconds:
            return dict(payload) | {"remote_validation_cache": "hit"}
        return None

    def _cache_remote_health(self, payload: dict[str, Any]) -> dict[str, Any]:
        cached = dict(payload) | {"remote_validation_cache": "miss"}
        self._remote_health_cache = (time.time(), cached)
        return cached

    def _health_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "backend": LIVE_DIFFUSIONGEMMA_BACKEND,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": self._retry_policy(),
            "fallback_behavior": self._fallback_behavior(),
            "polling_behavior": {
                "async_202": "poll_status_endpoint",
                "status_path_template": "/status/{request_id}",
                "poll_interval_seconds": 1.0,
                "timeout_seconds": self.timeout_seconds,
            },
            "decoding_settings": self._decoding_settings(),
            "tls_ca_bundle_source": _nim_tls_ca_bundle_source(),
        } | payload

    @classmethod
    def _decoding_settings(cls) -> dict[str, Any]:
        return {
            "max_tokens": 900,
            "temperature": 0,
            "top_p": 1,
            "stream": False,
            "response_format": cls._response_format(),
            "enable_thinking": False,
        }

    @staticmethod
    def _response_format() -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "calendar_pilot_policy_rank",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ranked_candidates", "policy_summary"],
                    "properties": {
                        "ranked_candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["candidate_id", "rank", "score_delta", "reason"],
                                "properties": {
                                    "candidate_id": {"type": "string"},
                                    "rank": {"type": "integer"},
                                    "score_delta": {"type": "number"},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                        "policy_summary": {"type": "string"},
                    },
                },
            },
        }

    @staticmethod
    def _retry_policy() -> dict[str, Any]:
        return {
            "max_attempts": 1,
            "http_retry": "none",
            "async_status_polling": "on_202_until_timeout",
        }

    @staticmethod
    def _fallback_behavior() -> str:
        return "fail_closed_no_heuristic_fallback_in_live_mode"

    def _poll_status(self, data: dict[str, Any]) -> dict[str, Any]:
        request_id = str(data.get("requestId") or data.get("request_id") or data.get("id") or "")
        if not request_id:
            raise LiveDiffusionGemmaRuntimeError("NIM returned 202 without requestId")
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            time.sleep(1.0)
            result = self._request_json("GET", f"/status/{request_id}", None)
            if result:
                return result
        raise LiveDiffusionGemmaNetworkError("NIM status polling timed out")


class LiveDiffusionGemmaPolicy:
    backend_name = LIVE_DIFFUSIONGEMMA_BACKEND

    def __init__(self, *, base_policy: DiffusionGemmaPolicy | None = None, client: NvidiaNIMPolicyClient | None = None) -> None:
        self.base_policy = base_policy or DiffusionGemmaPolicy()
        self.client = client or NvidiaNIMPolicyClient()
        self._policy_metadata_by_candidate: dict[str, dict[str, Any]] = {}

    def health_status(self, *, validate_remote: bool = False) -> dict[str, Any]:
        return self.client.health_status(validate_remote=validate_remote)

    def policy_metadata_for_candidate(self, candidate_id: str) -> dict[str, Any]:
        return dict(self._policy_metadata_by_candidate.get(candidate_id, {}))

    def generate_candidates(
        self,
        observation: RawCalendarObservation,
        biography: UserBiography,
    ) -> list[CandidateCalendarAction]:
        self._policy_metadata_by_candidate = {}
        candidates = self.base_policy.generate_candidates(observation, biography)
        result = self.client.rank_candidates(
            goal="Rank CalendarPilot candidate futures for user value and low regret.",
            observation=observation,
            biography=biography,
            candidates=candidates,
        )
        by_id = {candidate.candidate_id: candidate for candidate in candidates}
        ranked: list[CandidateCalendarAction] = []
        for row in result.ranks:
            candidate = by_id[row.candidate_id]
            candidate.expected_reward = round(candidate.expected_reward + row.score_delta, 4)
            candidate.reward_breakdown["nim_policy_delta"] = round(row.score_delta, 4)
            candidate.control_notes.extend([
                f"policy_backend={LIVE_DIFFUSIONGEMMA_BACKEND}",
                f"nim_model={self.client.model}",
                f"nim_rank={row.rank}",
                "nim_reason=" + row.reason[:160],
            ])
            if result.policy_summary:
                candidate.model_story.append("NIM policy: " + result.policy_summary[:180])
            self._policy_metadata_by_candidate[candidate.candidate_id] = self._candidate_policy_metadata(
                result.metadata,
                candidate_id=candidate.candidate_id,
                rank=row.rank,
                score_delta=row.score_delta,
                reason=row.reason,
                fallback_state="none",
                ranked_by_model=True,
            )
            ranked.append(candidate)
        ranked_ids = {candidate.candidate_id for candidate in ranked}
        unranked = [candidate for candidate in candidates if candidate.candidate_id not in ranked_ids]
        for candidate in unranked:
            candidate.control_notes.append(f"policy_backend={LIVE_DIFFUSIONGEMMA_BACKEND}:unranked_by_model")
            self._policy_metadata_by_candidate[candidate.candidate_id] = self._candidate_policy_metadata(
                result.metadata,
                candidate_id=candidate.candidate_id,
                rank=None,
                score_delta=0.0,
                reason="NIM policy response did not rank this locally validated candidate.",
                fallback_state="unranked_by_model_retained_after_local_validation",
                ranked_by_model=False,
            )
        return ranked + unranked

    @staticmethod
    def _candidate_policy_metadata(
        metadata: dict[str, Any],
        *,
        candidate_id: str,
        rank: int | None,
        score_delta: float,
        reason: str,
        fallback_state: str,
        ranked_by_model: bool,
    ) -> dict[str, Any]:
        return dict(metadata) | {
            "candidate_id": candidate_id,
            "rank": rank,
            "score_delta": round(score_delta, 4),
            "rank_reason": reason,
            "ranked_by_model": ranked_by_model,
            "fallback_state": fallback_state,
        }


def _nim_api_key() -> str:
    for key in ["CALENDAR_PILOT_NIM_API_KEY", "NVIDIA_API_KEY", "NIM_API_KEY"]:
        value = os.environ.get(key)
        if value:
            return value
    return ""


def _nim_api_key_source() -> str:
    for key in ["CALENDAR_PILOT_NIM_API_KEY", "NVIDIA_API_KEY", "NIM_API_KEY"]:
        if os.environ.get(key):
            return key
    return "missing"


def _nim_tls_context() -> ssl.SSLContext:
    ca_file = os.environ.get("CALENDAR_PILOT_NIM_CA_FILE")
    if ca_file:
        return ssl.create_default_context(cafile=ca_file)
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _nim_tls_ca_bundle_source() -> str:
    if os.environ.get("CALENDAR_PILOT_NIM_CA_FILE"):
        return "CALENDAR_PILOT_NIM_CA_FILE"
    try:
        import certifi  # type: ignore

        return f"certifi:{Path(certifi.where()).name}"
    except Exception:
        return "system_default"


def _redact_secret_text(text: str) -> str:
    redacted = text
    for key in ["CALENDAR_PILOT_NIM_API_KEY", "NVIDIA_API_KEY", "NIM_API_KEY"]:
        value = os.environ.get(key)
        if value:
            redacted = redacted.replace(value, f"<redacted:{key}>")
    return redacted
