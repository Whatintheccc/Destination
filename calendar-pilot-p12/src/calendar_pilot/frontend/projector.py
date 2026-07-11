from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from calendar_pilot.product_core import JournalEvent, project_cited_candidate_card


ROOT = Path(__file__).resolve().parents[3]


class FrontendProjector:
    """Strangler projector for view_state.v2.

    It currently wraps DogfoodSessionState.snapshot() so the new /api/view
    endpoint can land before the glass-cockpit frontend rewrites the DOM.
    """

    def __init__(self, session: Any) -> None:
        self.session = session
        self.read_side_mode = os.environ.get("CALENDAR_PILOT_PRODUCT_CORE_READ_SIDE", "cited").strip().lower()

    def view(self) -> dict[str, Any]:
        snapshot = self.session.snapshot()
        candidates = snapshot.get("chat", {}).get("candidate_cards", [])
        receipts = snapshot.get("chat", {}).get("receipt_cards", [])
        runtime = snapshot.get("runtime", {})
        inspector = snapshot.get("inspector", {})
        learning = snapshot.get("learning", {}) or {}
        p12 = _p12_evidence_payload()
        learning = {**p12.get("learning", {}), **learning}
        lab = dict(inspector.get("self_play", {}) or {})
        lab.update(_lab_index_payload())
        lab.update(p12.get("lab", {}))
        signals = _signals_payload(getattr(self.session, "replay", None))
        if not signals.get("semantic_signals"):
            signals.update({k: v for k, v in p12.get("signals", {}).items() if k not in {"active_signal_ids", "disabled_signal_ids"}})
        else:
            signals.update({k: v for k, v in p12.get("signals", {}).items() if k not in signals})
        authority = dict(inspector.get("authority", {}) or {})
        authority.update(p12.get("authority", {}))
        view = {
            "view_version": "view_state.v2",
            "state_version": snapshot.get("state_version", 0),
            "session": snapshot.get("session", {}),
            "sidebar": snapshot.get("sidebar", {"sessions": [], "recent_runs": []}),
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
            "authority": authority,
            "learning": learning,
            "lab": lab,
            "signals": signals,
            "pipeline": snapshot.get("pipeline", {"turns": []}),
            "invariants": snapshot.get("invariants", {"violations": []}),
        }
        view["read_side"] = self._apply_product_core_read_side(view)
        return view

    def _apply_product_core_read_side(self, view: dict[str, Any]) -> dict[str, Any]:
        if self.read_side_mode == "incumbent":
            return {"mode": "incumbent", "status": "pass", "failures": []}
        if self.read_side_mode != "cited":
            return {
                "mode": self.read_side_mode,
                "status": "hold",
                "failures": [f"unsupported ProductCore read-side mode: {self.read_side_mode}"],
            }
        legacy_cards = view.get("frontier", {}).get("candidates", [])
        target_ids = {
            str(card.get("candidate_id"))
            for card in legacy_cards
            if isinstance(card, dict) and card.get("intent") == "create_prep_block"
        }
        if not target_ids:
            return {"mode": "cited", "status": "pass", "failures": [], "candidate_ids": []}
        groups: dict[str, list[JournalEvent]] = {}
        failures: list[str] = []
        latest_plan_id = str(getattr(getattr(self.session, "latest_plan", None), "plan_id", ""))
        for record in getattr(getattr(self.session, "replay", None), "records", []):
            if getattr(record, "record_type", None) != "product_core_journal_event":
                continue
            payload = record.payload if isinstance(record.payload, dict) else {}
            if str(payload.get("plan_id", "")) != latest_plan_id:
                continue
            scope_id = str(payload.get("journal_scope_id", ""))
            try:
                event_payload = payload.get("journal_event")
                if not scope_id or not isinstance(event_payload, dict):
                    raise ValueError("ProductCore Journal adapter row is incomplete")
                groups.setdefault(scope_id, []).append(JournalEvent.from_dict(event_payload))
            except ValueError as exc:
                failures.append(str(exc))
        cited_by_id: dict[str, dict[str, Any]] = {}
        if not failures:
            for events in groups.values():
                try:
                    card = project_cited_candidate_card(tuple(events))
                except ValueError as exc:
                    failures.append(str(exc))
                    continue
                candidate_id = str(card.get("candidate_id", ""))
                event_ids = {event.row_id for event in events}
                if not set(card.get("citation", {}).get("event_ids", [])).issubset(event_ids):
                    failures.append(f"cited ProductCore row is missing: {candidate_id}")
                    continue
                cited_by_id[candidate_id] = card
        missing = sorted(target_ids - set(cited_by_id))
        if missing:
            failures.append(f"cited ProductCore card unavailable: {','.join(missing)}")
        if failures:
            return {"mode": "cited", "status": "hold", "failures": failures, "candidate_ids": sorted(target_ids)}

        def substitute(cards: Any) -> None:
            if not isinstance(cards, list):
                return
            for index, card in enumerate(cards):
                if not isinstance(card, dict):
                    continue
                replacement = cited_by_id.get(str(card.get("candidate_id", "")))
                if replacement is not None:
                    cards[index] = {**card, **replacement}

        substitute(view.get("frontier", {}).get("candidates"))
        conversation = view.get("conversation", {})
        substitute(conversation.get("candidate_cards"))
        for message in conversation.get("messages", []) if isinstance(conversation.get("messages"), list) else []:
            if isinstance(message, dict):
                substitute(message.get("cards"))
        return {
            "mode": "cited",
            "status": "pass",
            "failures": [],
            "candidate_ids": sorted(cited_by_id),
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


def _p12_evidence_payload() -> dict[str, Any]:
    evidence_dir = _latest_p12_evidence_dir()
    if evidence_dir is None:
        return {"learning": {}, "lab": {}, "authority": {}, "signals": {}}
    semantic = _read_json(evidence_dir / "semantic_labels" / "semantic_signals.json")
    semantic_drift = _read_json(evidence_dir / "semantic_labels" / "semantic_signals_with_drift.json")
    return {
        "learning": {
            "measurement_report": _read_json(evidence_dir / "measurement" / "measurement_report.json"),
            "reward_head_report": _read_json(evidence_dir / "measurement" / "reward_head_report.json"),
            "signal_estimator_report": _read_json(evidence_dir / "estimators" / "signal_estimator_report.json"),
            "policy_ablations": _read_json(evidence_dir / "policy_learning" / "policy_ablation_report.json"),
            "policy_ablation_comparison": _read_json(evidence_dir / "policy_learning" / "policy_ablation_comparison.json"),
            "frontier_diff": _read_json(evidence_dir / "policy_learning" / "frontier_diff.json")
            or _read_json(evidence_dir / "p11_regression" / "frontier_diff.json"),
            "calibration_report": _read_json(evidence_dir / "calibration" / "calibration_report.json"),
            "evidence_run_dir": str(evidence_dir),
        },
        "lab": {
            "curriculum_runs": {
                "base": _read_json(evidence_dir / "self_play" / "p12_base_curriculum.json"),
                "provider_backed": _read_json(evidence_dir / "self_play" / "provider_backed_deterministic.json"),
                "comparison": _read_json(evidence_dir / "self_play" / "curriculum_comparison.json"),
            },
            "calibration_reports": _read_json(evidence_dir / "calibration" / "calibration_report.json"),
            "dogfood_shadow_batches": {
                "imported_observation": _read_json(evidence_dir / "dogfood_shadow" / "imported_observation.json"),
                "shadow_frontier": _read_json(evidence_dir / "dogfood_shadow" / "shadow_frontier.json"),
                "provider_preview": _read_json(evidence_dir / "dogfood_shadow" / "provider_preview.json"),
            },
        },
        "authority": {
            "family_matrix": _read_json(ROOT / "configs" / "autonomy_matrix.json"),
            "promotion_history": [
                _read_json(evidence_dir / "autonomy" / "create_prep_block_proposal.json"),
                _read_json(evidence_dir / "autonomy" / "create_prep_block_decision.json"),
            ],
            "rollback": {
                "command": "restore configs/autonomy_matrix.json from git and rerun make p12-release",
                "latest_decision": _read_json(evidence_dir / "autonomy" / "create_prep_block_decision.json"),
            },
        },
        "signals": {
            "semantic_signals": semantic.get("signals", []) if isinstance(semantic, dict) else [],
            "biography_drift_findings": semantic_drift.get("biography_drift_findings", []) if isinstance(semantic_drift, dict) else [],
            "label_evidence_coverage": semantic.get("label_evidence_coverage") if isinstance(semantic, dict) else None,
            "label_churn_rate": semantic.get("label_churn_rate") if isinstance(semantic, dict) else None,
            "signal_estimator_report": _read_json(evidence_dir / "estimators" / "signal_estimator_report.json"),
        },
    }


def _latest_p12_evidence_dir() -> Path | None:
    base = ROOT / "runs" / "p12_evidence"
    if not base.exists():
        return None
    candidates = [path for path in base.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.name)[-1]


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

def _signals_payload(replay: Any | None) -> dict[str, Any]:
    records = getattr(replay, "records", []) if replay is not None else []
    rows = [r.envelope() if hasattr(r, "envelope") else dict(r) for r in records]
    semantic = [row.get("payload", {}) for row in rows if row.get("record_type") == "semantic_signal"]
    activations = [row.get("payload", {}) for row in rows if row.get("record_type") == "label_activation"]
    drift = [row.get("payload", {}) for row in rows if row.get("record_type") == "biography_drift_finding"]
    active_ids = {a.get("signal_id") for a in activations if a.get("status") == "active"}
    disabled_ids = {a.get("signal_id") for a in activations if a.get("status") == "disabled"}
    return {
        "semantic_signals": semantic[-20:],
        "label_activations": activations[-20:],
        "biography_drift_findings": drift[-20:],
        "active_signal_ids": sorted(x for x in active_ids if x not in disabled_ids),
        "disabled_signal_ids": sorted(x for x in disabled_ids if x),
        "label_evidence_coverage": 1.0 if semantic and all(s.get("evidence") for s in semantic if s.get("kind", "derived") == "derived") else (None if not semantic else 0.0),
    }
