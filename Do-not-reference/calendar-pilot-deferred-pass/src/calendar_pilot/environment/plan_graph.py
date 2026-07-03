from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json

from calendar_pilot.types import AtomicCalendarAction, to_jsonable


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    action: AtomicCalendarAction
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"step_id": self.step_id, "action": to_jsonable(self.action), "depends_on": self.depends_on}


@dataclass(frozen=True)
class TierSixPlanGraph:
    plan_id: str
    steps: list[PlanStep]
    rollback_order: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, "steps": [s.to_dict() for s in self.steps], "rollback_order": self.rollback_order}

    @classmethod
    def from_actions(cls, *, plan_id: str, actions: list[AtomicCalendarAction]) -> "TierSixPlanGraph":
        steps = [PlanStep(step_id=f"step_{idx+1}", action=action, depends_on=[] if idx == 0 else [f"step_{idx}"]) for idx, action in enumerate(actions)]
        return cls(plan_id=plan_id, steps=steps, rollback_order=[step.step_id for step in reversed(steps)])

    @classmethod
    def from_metadata(cls, metadata: dict[str, str]) -> "TierSixPlanGraph | None":
        encoded = metadata.get("plan_graph") or ""
        if not encoded:
            return None
        try:
            payload = json.loads(encoded)
        except json.JSONDecodeError:
            return None
        steps: list[PlanStep] = []
        for row in payload.get("steps", []):
            if not isinstance(row, dict) or not isinstance(row.get("action"), dict):
                continue
            try:
                steps.append(PlanStep(step_id=str(row.get("step_id") or f"step_{len(steps)+1}"), action=AtomicCalendarAction.from_dict(row["action"]), depends_on=[str(x) for x in row.get("depends_on", [])]))
            except Exception:
                continue
        if not steps:
            return None
        rollback_order = [str(x) for x in payload.get("rollback_order", [])] or [step.step_id for step in reversed(steps)]
        return cls(plan_id=str(payload.get("plan_id") or "plan_graph"), steps=steps, rollback_order=rollback_order)


def encode_plan_graph(plan: TierSixPlanGraph) -> str:
    return json.dumps(to_jsonable(plan.to_dict()), sort_keys=True, separators=(",", ":"))


def actions_from_plan_metadata(metadata: dict[str, str]) -> list[AtomicCalendarAction]:
    graph = TierSixPlanGraph.from_metadata(metadata)
    if graph is not None:
        ordered: list[PlanStep] = []
        remaining = {step.step_id: step for step in graph.steps}
        while remaining:
            ready = [step for step in remaining.values() if all(dep not in remaining for dep in step.depends_on)]
            if not ready:
                ready = list(remaining.values())
            for step in sorted(ready, key=lambda s: s.step_id):
                ordered.append(step)
                remaining.pop(step.step_id, None)
        return [step.action for step in ordered]
    encoded = metadata.get("plan_actions", "")
    if not encoded:
        return []
    try:
        payload = json.loads(encoded)
    except json.JSONDecodeError:
        return []
    actions: list[AtomicCalendarAction] = []
    if isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict):
                try:
                    actions.append(AtomicCalendarAction.from_dict(row))
                except Exception:
                    pass
    return actions


def rollback_order_from_metadata(metadata: dict[str, str]) -> list[str]:
    graph = TierSixPlanGraph.from_metadata(metadata)
    return graph.rollback_order if graph is not None else []
