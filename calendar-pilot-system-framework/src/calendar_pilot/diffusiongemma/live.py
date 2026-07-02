

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

from calendar_pilot.env import load_local_env
from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy, apply_policy_tuning
from calendar_pilot.environment.taxonomy import CanonicalIntent, normalize_intent
from calendar_pilot.types import CandidateCalendarAction, PolicyTuning, RawCalendarObservation, UserBiography, to_jsonable


load_local_env()
LIVE_DIFFUSIONGEMMA_BACKEND = "nvidia_nim_diffusiongemma_policy"
LIVE_DIFFUSIONGEMMA_PROMPT_VERSION = "calendar_pilot_nim_frontier_generator_v2"
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


@dataclass(frozen=True)
class NIMFrontierResult:
    candidates: list[CandidateCalendarAction]
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

    def generate_candidate_frontier(
        self,
        *,
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        limit: int = 8,
    ) -> NIMFrontierResult:
        """Ask NIM/DiffusionGemma to generate typed candidate action programs.

        The model is no longer only a ranker in live_diffusiongemma mode. It is
        expected to emit CandidateCalendarAction-shaped dictionaries that Codex
        and Swift can execute through the existing tool/authority boundary.
        """
        if not self.api_key:
            raise LiveDiffusionGemmaCredentialError("NVIDIA NIM API key is required for live_diffusiongemma mode")
        schema_retries: list[dict[str, Any]] = []
        attempts = [
            {"limit": max(1, int(limit)), "temperature": 0.2, "top_p": 0.9, "retry": False},
            {"limit": max(1, min(2, int(limit))), "temperature": 0.0, "top_p": 1.0, "retry": True},
        ]
        data: dict[str, Any] = {}
        parsed: dict[str, Any] | None = None
        for attempt_index, attempt in enumerate(attempts, start=1):
            payload = self._frontier_request_payload(
                goal,
                observation,
                biography,
                limit=attempt["limit"],
                temperature=attempt["temperature"],
                top_p=attempt["top_p"],
                retry=attempt["retry"],
            )
            try:
                data = self._request_json("POST", "/chat/completions", payload)
                parsed = self._parse_frontier_payload(self._extract_text(data), observation, limit=attempt["limit"])
                if schema_retries:
                    parsed["validation_errors"].append("frontier_schema_retry_succeeded")
                break
            except LiveDiffusionGemmaSchemaError as exc:
                schema_retries.append({
                    "attempt": attempt_index,
                    "category": exc.category,
                    "message": str(exc),
                    "limit": attempt["limit"],
                })
                if attempt_index == len(attempts):
                    messages = "; ".join(row["message"] for row in schema_retries)
                    raise LiveDiffusionGemmaSchemaError(
                        f"NIM frontier JSON response was invalid after {len(attempts)} attempts: {messages}"
                    ) from exc
        if parsed is None:
            raise LiveDiffusionGemmaSchemaError("NIM frontier response did not parse")
        return NIMFrontierResult(
            candidates=parsed["candidates"],
            policy_summary=parsed["policy_summary"],
            metadata={
                "backend": LIVE_DIFFUSIONGEMMA_BACKEND,
                "mode": "model_generated_candidate_frontier",
                "prompt_version": LIVE_DIFFUSIONGEMMA_PROMPT_VERSION,
                "model": self.model,
                "base_url": self.base_url,
                "response_id": data.get("id"),
                "candidate_count": len(parsed["candidates"]),
                "decoding_settings": self._decoding_settings() | {"temperature": 0.2, "top_p": 0.9},
                "timeout_seconds": self.timeout_seconds,
                "retry_policy": self._retry_policy(),
                "schema_retry_count": len(schema_retries),
                "schema_retry_errors": schema_retries,
                "fallback_behavior": self._fallback_behavior(),
                "validation": {
                    "candidate_contract": "CandidateCalendarAction",
                    "validation_errors": parsed["validation_errors"],
                    "rejections": parsed.get("rejections", []),
                    "rejection_count": len(parsed.get("rejections", [])),
                },
                "redaction_policy": "raw event titles, attendees, notes, and locations are included in the reference implementation input envelope",
            },
        )

    def _frontier_request_payload(
        self,
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        limit: int,
        temperature: float,
        top_p: float,
        retry: bool,
    ) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": self._frontier_prompt(goal, observation, biography, limit=limit, retry=retry)}],
            "max_tokens": int(os.environ.get("CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS", "4200")),
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
            "response_format": self._frontier_response_format(),
            "chat_template_kwargs": {"enable_thinking": False},
        }

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
    def _parse_frontier_payload(text: str, observation: RawCalendarObservation, *, limit: int) -> dict[str, Any]:
        clean = text.strip()
        if clean.startswith("```"):
            clean = "\n".join(line for line in clean.splitlines() if not line.strip().startswith("```")).strip()
        validation_errors: list[str] = []
        rejections: list[dict[str, Any]] = []
        try:
            payload = json.loads(clean)
        except json.JSONDecodeError as exc:
            start = clean.find("{")
            end = clean.rfind("}")
            if start < 0 or end <= start:
                raise LiveDiffusionGemmaSchemaError(f"NIM frontier response was not JSON: {exc}") from exc
            try:
                payload = json.loads(clean[start:end + 1])
                validation_errors.append("json_extracted_from_surrounding_text")
            except json.JSONDecodeError as inner:
                raise LiveDiffusionGemmaSchemaError(f"NIM frontier JSON response was invalid: {inner}") from inner
        raw_candidates = payload.get("candidates") if isinstance(payload, dict) else None
        if not isinstance(raw_candidates, list) or not raw_candidates:
            raise LiveDiffusionGemmaSchemaError("NIM frontier response did not contain candidates")
        candidates: list[CandidateCalendarAction] = []
        seen: set[str] = set()
        for idx, item in enumerate(raw_candidates[:max(1, limit)]):
            raw_item = item
            if not isinstance(item, dict):
                validation_errors.append(f"skipped_non_object_candidate:{idx}")
                rejections.append({"reason": "skipped_non_object_candidate", "index": idx, "raw_item": raw_item})
                continue
            item = NvidiaNIMPolicyClient._normalize_frontier_candidate(item, idx=idx, validation_errors=validation_errors)
            try:
                candidate = CandidateCalendarAction.from_dict(item)
            except Exception as exc:
                reason = f"skipped_invalid_candidate:{idx}:{exc}"
                validation_errors.append(reason)
                rejections.append({"reason": "skipped_invalid_candidate", "index": idx, "schema_errors": [str(exc)], "raw_item": raw_item})
                continue
            if candidate.candidate_id in seen:
                validation_errors.append(f"duplicate_candidate_id:{candidate.candidate_id}")
                rejections.append({"reason": "duplicate_candidate_id", "index": idx, "raw_item": raw_item, "candidate_id": candidate.candidate_id})
                candidate.candidate_id = f"{candidate.candidate_id}_{idx}"
            seen.add(candidate.candidate_id)
            if not candidate.actions:
                validation_errors.append(f"skipped_candidate_without_actions:{candidate.candidate_id}")
                rejections.append({"reason": "skipped_candidate_without_actions", "index": idx, "raw_item": raw_item, "candidate_id": candidate.candidate_id})
                continue
            if not candidate.target_calendars:
                validation_errors.append(f"missing_target_calendars:{candidate.candidate_id}")
                rejections.append({"reason": "missing_target_calendars", "index": idx, "raw_item": raw_item, "candidate_id": candidate.candidate_id, "recoverable": True})
                candidate.target_calendars = sorted({a.calendar_id for a in candidate.actions if a.calendar_id}) or ["default"]
            candidate.control_notes.append(f"policy_backend={LIVE_DIFFUSIONGEMMA_BACKEND}")
            candidate.control_notes.append("nim_generation=typed_candidate_frontier")
            if not candidate.explanation:
                candidate.explanation = "Generated by live DiffusionGemma/NIM candidate frontier."
            if not candidate.model_story:
                candidate.model_story = ["NIM generated this candidate as part of the live frontier."]
            candidates.append(candidate)
        if not candidates:
            raise LiveDiffusionGemmaSchemaError("NIM frontier response did not contain any valid typed candidates")
        candidates.sort(key=lambda c: c.expected_reward, reverse=True)
        return {"candidates": candidates, "policy_summary": str(payload.get("policy_summary") or ""), "validation_errors": validation_errors, "rejections": rejections}

    @staticmethod
    def _normalize_frontier_candidate(item: dict[str, Any], *, idx: int, validation_errors: list[str]) -> dict[str, Any]:
        normalized = dict(item)
        for list_field in ["target_calendars", "affected_event_ids", "affected_people_ids", "model_story", "control_notes"]:
            value = normalized.get(list_field)
            if isinstance(value, str):
                normalized[list_field] = [value] if value else []
                validation_errors.append(f"normalized_string_list:{idx}:{list_field}")
            elif value is None:
                normalized[list_field] = []
        for map_field in ["reward_breakdown", "simulated_outcomes"]:
            value = normalized.get(map_field)
            if value is None:
                normalized[map_field] = {}
            elif not isinstance(value, dict):
                normalized[map_field] = {}
                validation_errors.append(f"normalized_non_dict_map:{idx}:{map_field}")
        reversibility = normalized.get("reversibility")
        if isinstance(reversibility, bool):
            normalized["reversibility"] = "high" if reversibility else "none"
            validation_errors.append(f"normalized_reversibility_bool:{idx}")
        elif str(reversibility).lower() in {"true", "yes"}:
            normalized["reversibility"] = "high"
            validation_errors.append(f"normalized_reversibility_text:{idx}")
        elif str(reversibility).lower() in {"false", "no", ""}:
            normalized["reversibility"] = "none"
            validation_errors.append(f"normalized_reversibility_text:{idx}")
        actions = []
        for action_idx, action in enumerate(normalized.get("actions", [])):
            if not isinstance(action, dict):
                actions.append(action)
                continue
            action_payload = dict(action)
            if "action_type" not in action_payload and "type" in action_payload:
                action_payload["action_type"] = action_payload["type"]
                validation_errors.append(f"normalized_action_type_alias:{idx}:{action_idx}")
            if "calendar_id" not in action_payload and "calendar" in action_payload:
                action_payload["calendar_id"] = action_payload["calendar"]
                validation_errors.append(f"normalized_calendar_alias:{idx}:{action_idx}")
            actions.append(action_payload)
        normalized["actions"] = actions
        if not normalized.get("target_calendars"):
            target_calendars = sorted({str(action.get("calendar_id")) for action in actions if isinstance(action, dict) and action.get("calendar_id")})
            if target_calendars:
                normalized["target_calendars"] = target_calendars
                validation_errors.append(f"filled_target_calendars:{idx}")
        if not normalized.get("affected_event_ids"):
            event_ids = sorted({str(action.get("event_id")) for action in actions if isinstance(action, dict) and action.get("event_id")})
            if event_ids:
                normalized["affected_event_ids"] = event_ids
                validation_errors.append(f"filled_affected_event_ids:{idx}")
        raw_right_moment = normalized.get("right_moment_decision", "do_nothing")
        if isinstance(raw_right_moment, bool):
            normalized["right_moment_decision"] = "auto_write_then_notify" if raw_right_moment else "do_nothing"
            validation_errors.append(f"normalized_right_moment_bool:{idx}")
            raw_right_moment = normalized["right_moment_decision"]
        elif isinstance(raw_right_moment, (int, float)):
            score = float(raw_right_moment)
            if score >= 0.75:
                normalized["right_moment_decision"] = "auto_write_then_notify"
            elif score >= 0.45:
                normalized["right_moment_decision"] = "notify_now"
            else:
                normalized["right_moment_decision"] = "wait"
            normalized.setdefault("right_moment_score", score)
            validation_errors.append(f"normalized_right_moment_number:{idx}")
            raw_right_moment = normalized["right_moment_decision"]
        right_moment = str(raw_right_moment).lower().strip().replace("-", "_").replace(" ", "_")
        aliases = {
            "auto_write": "auto_write_then_notify",
            "draft": "silently_draft",
            "silent_draft": "silently_draft",
            "notify": "notify_now",
            "ask": "ask_clarification",
        }
        if right_moment in aliases:
            normalized["right_moment_decision"] = aliases[right_moment]
            validation_errors.append(f"normalized_right_moment_alias:{idx}")
        intent_meta = normalize_intent(str(normalized.get("intent") or ""))
        if normalized.get("intent") != intent_meta["intent"]:
            validation_errors.append(f"normalized_intent:{idx}:{normalized.get('intent')}->{intent_meta['intent']}")
        normalized["intent_raw"] = normalized.get("intent_raw") or intent_meta["intent_raw"]
        normalized["intent"] = intent_meta["intent"]
        normalized["intent_matched_by"] = intent_meta["matched_by"]
        return normalized

    def _frontier_prompt(self, goal: str, observation: RawCalendarObservation, biography: UserBiography, *, limit: int, retry: bool = False) -> str:
        return json.dumps({
            "instruction": "Generate a candidate frontier for CalendarPilot. Return only JSON matching the schema: {policy_summary: string, candidates: CandidateCalendarAction[]}. Each candidate must have candidate_id, intent, actions, target_calendars, affected_event_ids, affected_people_ids, required_authority_tier, reversibility, reward heads, right_moment_decision, model_story, counterfactual, control_notes, reward_breakdown, right_moment_score, and simulated_outcomes.",
            "strict_retry_instruction": "Previous output was not valid JSON. Return one compact JSON object only, with no markdown, no prose, no comments, and no trailing commas." if retry else None,
            "goal": goal,
            "limit": limit,
            "observation": to_jsonable(observation),
            "biography": biography.to_dict(),
            "canonical_intents": [intent.value for intent in CanonicalIntent],
            "intent_instruction": "Pick the closest canonical_intent value for candidate.intent. If none fits, use other and explain in model_story.",
            "allowed_action_types": [
                "do_nothing", "notify", "ask_clarification", "create_event", "move_event", "resize_event",
                "delete_own_event", "add_buffer", "create_focus_block", "batch_tasks", "draft_schedule_plan",
                "auto_apply_plan", "undo",
            ],
            "authority_tiers": {
                "0": "no-op/read",
                "3": "private reversible write",
                "5": "social calendar actuation",
                "6": "compound auto_apply_plan",
            },
        }, indent=2, default=str)

    @staticmethod
    def _frontier_response_format() -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "calendar_pilot_candidate_frontier",
                "strict": False,
                "schema": {
                    "type": "object",
                    "required": ["policy_summary", "candidates"],
                    "properties": {
                        "policy_summary": {"type": "string"},
                        "candidates": {"type": "array", "items": {"type": "object"}},
                    },
                },
            },
        }


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
            "max_attempts": 2,
            "http_retry": "none",
            "schema_retry": "one smaller deterministic frontier retry on malformed JSON",
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

    def __init__(
        self,
        *,
        base_policy: DiffusionGemmaPolicy | None = None,
        client: NvidiaNIMPolicyClient | None = None,
        policy_tuning: PolicyTuning | None = None,
    ) -> None:
        self.policy_tuning = policy_tuning or PolicyTuning()
        self.base_policy = base_policy or DiffusionGemmaPolicy(policy_tuning=self.policy_tuning)
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
        *,
        goal: str | None = None,
    ) -> list[CandidateCalendarAction]:
        self._policy_metadata_by_candidate = {}
        user_goal = (goal or "Generate CalendarPilot candidate futures for user value, right moment, and machine acting.").strip()
        generate_frontier = getattr(self.client, "generate_candidate_frontier", None)
        if callable(generate_frontier):
            frontier_limit = int(os.environ.get("CALENDAR_PILOT_NIM_FRONTIER_LIMIT", "4"))
            result = generate_frontier(
                goal=user_goal,
                observation=observation,
                biography=biography,
                limit=max(1, frontier_limit),
            )
            for idx, candidate in enumerate(result.candidates, start=1):
                candidate.control_notes.extend([
                    f"policy_backend={LIVE_DIFFUSIONGEMMA_BACKEND}",
                    f"nim_model={self.client.model}",
                    f"nim_generated_rank={idx}",
                ])
                if result.policy_summary:
                    candidate.model_story.append("NIM frontier: " + result.policy_summary[:180])
                apply_policy_tuning(candidate, self.policy_tuning)
                self._policy_metadata_by_candidate[candidate.candidate_id] = self._candidate_policy_metadata(
                    result.metadata,
                    candidate_id=candidate.candidate_id,
                    rank=idx,
                    score_delta=0.0,
                    reason="NIM generated this typed candidate frontier directly.",
                    fallback_state="model_generated_frontier",
                    ranked_by_model=True,
                )
            return sorted(result.candidates, key=lambda c: (c.expected_reward, c.right_moment_score), reverse=True)

        # Compatibility for old tests/injected clients: if a fake client exposes
        # only rank_candidates, keep that path alive. The production client above
        # generates the frontier.
        candidates = self.base_policy.generate_candidates(observation, biography, goal=user_goal)
        result = self.client.rank_candidates(
            goal=user_goal,
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
