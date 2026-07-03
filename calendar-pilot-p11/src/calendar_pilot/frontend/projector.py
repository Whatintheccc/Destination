from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


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
        lab = dict(inspector.get("self_play", {}) or {})
        _hydrate_self_play_lab_defaults(lab)
        lab.update(_lab_index_payload())
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
            "lab": lab,
            "pipeline": snapshot.get("pipeline", {"turns": []}),
            "invariants": snapshot.get("invariants", {"violations": []}),
            "legacy_state": snapshot,
        }


def _lab_index_payload() -> dict[str, Any]:
    index_path = ROOT / "experiments" / "index.json"
    if not index_path.exists():
        return {"experiments": [], "lab_index_status": "missing"}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"experiments": [], "lab_index_status": "unreadable", "error": str(exc)}
    rows = payload.get("runs", payload if isinstance(payload, list) else [])
    if not isinstance(rows, list):
        rows = []
    return {
        "experiments": rows[-20:],
        "lab_index_status": "loaded",
        "lab_index_path": str(index_path),
        "lab_run_count": len(rows),
        "batch_metrics": payload.get("batch_metrics", {}) if isinstance(payload, dict) else {},
    }


def _hydrate_self_play_lab_defaults(lab: dict[str, Any]) -> None:
    history = lab.get("history")
    latest = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else {}
    lab.setdefault("backend", latest.get("backend", "stub_fast"))
    lab.setdefault("simulator_version", latest.get("simulator_version", "sim_v2"))
