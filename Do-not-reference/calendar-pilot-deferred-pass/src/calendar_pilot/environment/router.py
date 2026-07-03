from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import hashlib


@dataclass
class RoutedTurn:
    turn_id: str
    router_backend: str
    classified_intent: str
    route: str
    confidence: float
    counterfactual_routes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def replay_payload(self) -> dict[str, Any]:
        return {
            "record_type": "router_decision",
            "turn_id": self.turn_id,
            "router_backend": self.router_backend,
            "classified_intent": self.classified_intent,
            "route": self.route,
            "confidence": self.confidence,
            "counterfactual_routes": self.counterfactual_routes,
            "evidence": self.evidence,
        }


class KeywordRouter:
    """Extracted fixture/fallback router matching DogfoodSessionState's current keyword behavior."""

    def route(self, turn_text: str, *, context: dict[str, Any] | None = None) -> RoutedTurn:
        text = " ".join((turn_text or "").lower().split())
        turn_id = "turn_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
        metadata_terms = ("status", "runtime", "backend", "codex", "nim", "diffusion", "provider", "calendar access", "health", "trace")
        profile_terms = ("profile", "preference", "remember", "forget", "correction")
        undo_terms = ("undo", "revert", "roll back", "rollback")
        calendar_terms = ("calendar", "meeting", "schedule", "block", "focus", "prep", "buffer", "free", "plan", "move", "reschedule", "event")
        if any(term in text for term in undo_terms):
            intent, route, confidence = "operational_tool", "operational", 0.88
        elif any(term in text for term in metadata_terms):
            intent, route, confidence = "metadata_question", "conversation", 0.8
        elif any(term in text for term in profile_terms):
            intent, route, confidence = "profile_repair", "operational", 0.72
        elif any(term in text for term in calendar_terms):
            intent, route, confidence = "calendar_goal", "planner", 0.68
        elif text:
            intent, route, confidence = "non_calendar", "conversation", 0.55
        else:
            intent, route, confidence = "non_calendar", "conversation", 0.0
        return RoutedTurn(
            turn_id=turn_id,
            router_backend="fixture_keywords",
            classified_intent=intent,
            route=route,
            confidence=confidence,
            counterfactual_routes=[],
            evidence={"matched_text": text[:180]},
        )


class ModelIntentRouter:
    """Placeholder seam for live Codex intent routing.

    The live implementation will read intent from the Codex conversation output.
    This delegating pass records the model backend name but falls back to the
    deterministic keyword router until that output schema is landed.
    """

    def __init__(self, fallback: KeywordRouter | None = None) -> None:
        self.fallback = fallback or KeywordRouter()

    def route(self, turn_text: str, *, context: dict[str, Any] | None = None) -> RoutedTurn:
        routed = self.fallback.route(turn_text, context=context or {})
        routed.router_backend = "fallback_keywords"
        routed.counterfactual_routes = [routed.route]
        routed.evidence = dict(routed.evidence) | {"model_router_pending": True}
        return routed
