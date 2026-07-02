from __future__ import annotations

from typing import Any


class FrontendProjector:
    """Strangler projector for view_state.v2.

    It currently wraps DogfoodSessionState.snapshot() so the new /api/view
    endpoint can land before the glass-cockpit frontend rewrites the DOM.
    """

    def __init__(self, session: Any) -> None:
        self.session = session

    def view(self) -> dict[str, Any]:
        snapshot = self.session.snapshot()
        candidates = snapshot.get("chat", {}).get("candidate_cards", [])
        receipts = snapshot.get("chat", {}).get("receipt_cards", [])
        runtime = snapshot.get("runtime", {})
        inspector = snapshot.get("inspector", {})
        learning = snapshot.get("learning", {}) or {}
        return {
            "view_version": "view_state.v2",
            "state_version": snapshot.get("state_version", 0),
            "session": snapshot.get("session", {}),
            "runtime": runtime,
            "conversation": snapshot.get("chat", {}),
            "frontier": {
                "generation_id": snapshot.get("summary", {}).get("plan_id"),
                "goal": snapshot.get("goal", ""),
                "policy_backend": runtime.get("backends", {}).get("diffusiongemma"),
                "candidates": candidates,
                "rejections": learning.get("frontier_rejections", {"count": 0, "reasons": {}}),
            },
            "actions": {"queue": snapshot.get("action_queue", [])},
            "authority": inspector.get("authority", {}),
            "learning": learning,
            "lab": inspector.get("self_play", {}),
            "pipeline": snapshot.get("pipeline", {"turns": []}),
            "invariants": snapshot.get("invariants", {"violations": []}),
            "legacy_state": snapshot,
        }
