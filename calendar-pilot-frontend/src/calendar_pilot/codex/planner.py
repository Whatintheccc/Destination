from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any

from calendar_pilot.codex.tools import CodexToolRuntime
from calendar_pilot.types import CodexToolCall, CodexToolName, CodexToolReceipt, RawCalendarObservation, UserBiography


@dataclass
class CodexExecutivePlan:
    plan_id: str
    goal: str
    calls: list[CodexToolCall] = field(default_factory=list)
    receipts: list[CodexToolReceipt] = field(default_factory=list)
    recommended_next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "calls": [c.to_dict() for c in self.calls],
            "receipts": [r.to_dict() for r in self.receipts],
            "recommended_next_action": self.recommended_next_action,
        }


class CodexToolPlanner:
    """Small deterministic Codex planner over the tool runtime.

    The planner is the conceptual repair for Codex: it turns a goal into app
    operations. DiffusionGemma still learns/proposes, and Swift still validates,
    but Codex now owns the deliberate sequence: inspect, generate, compare,
    simulate, stage, and request commit only when the authority model permits.
    """

    def __init__(self, runtime: CodexToolRuntime | None = None) -> None:
        self.runtime = runtime or CodexToolRuntime()

    def plan_goal(
        self,
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        authority_tier: int = 3,
        commit: bool = False,
        authority_scopes: list[str] | None = None,
    ) -> CodexExecutivePlan:
        plan = CodexExecutivePlan(plan_id=self._plan_id(goal, observation.observation_id), goal=goal)
        grant = self.runtime.kernel.issue_authority_grant(
            user_scope_id=observation.user_scope_id,
            max_authority_tier=authority_tier,
            scopes=authority_scopes or ["recommend", "stage", "commit_private", "undo"],
            confirmation_provenance=f"codex_plan_goal:{plan.plan_id}",
            confirmed_by_user=commit,
            issued_at=observation.observed_at,
        )
        inspect = self._call(CodexToolName.INSPECT_WEEK, {"goal": goal}, authority_tier, "Inspect the raw calendar before asking the model to act.", grant_id=grant.grant_id, correlation_id=plan.plan_id)
        self._run(plan, inspect, observation, biography)
        frontier = self._call(CodexToolName.GENERATE_CANDIDATE_FRONTIER, {"goal": goal, "limit": 6}, authority_tier, "Ask DiffusionGemma for candidate futures.", grant_id=grant.grant_id, correlation_id=plan.plan_id)
        frontier_receipt = self._run(plan, frontier, observation, biography)
        ids = frontier_receipt.output.get("frontier_ids", [])
        compare = self._call(CodexToolName.COMPARE_CANDIDATES, {"candidate_ids": ids}, authority_tier, "Compare model futures under reward, regret, and authority.", grant_id=grant.grant_id, correlation_id=plan.plan_id)
        compare_receipt = self._run(plan, compare, observation, biography)
        winner = (compare_receipt.output.get("winner") or {}).get("candidate_id")
        if winner:
            simulate = self._call(CodexToolName.SIMULATE_ACTION_PROGRAM, {"candidate_id": winner}, authority_tier, "Simulate the winning action without committing provider state.", grant_id=grant.grant_id, correlation_id=winner)
            sim_receipt = self._run(plan, simulate, observation, biography)
            needs_confirm = bool(sim_receipt.output.get("would_require_confirmation"))
            if commit and not needs_confirm:
                commit_call = self._call(CodexToolName.REQUEST_COMMIT, {"candidate_id": winner}, authority_tier, "Request Swift to commit the selected packet.", grant_id=grant.grant_id, correlation_id=winner)
                commit_receipt = self._run(plan, commit_call, observation, biography)
                plan.recommended_next_action = "committed" if not commit_receipt.denied_reason else "commit_denied_stage_instead"
            else:
                stage_call = self._call(CodexToolName.STAGE_ACTION_PACKET, {"candidate_id": winner}, authority_tier, "Stage the packet so the user or authority policy can confirm.", grant_id=grant.grant_id, correlation_id=winner)
                self._run(plan, stage_call, observation, biography)
                plan.recommended_next_action = "stage_for_confirmation" if needs_confirm else "staged_draft"
        else:
            plan.recommended_next_action = "no_candidate_available"
        return plan

    def _run(self, plan: CodexExecutivePlan, call: CodexToolCall, observation: RawCalendarObservation, biography: UserBiography) -> CodexToolReceipt:
        plan.calls.append(call)
        receipt = self.runtime.execute(call, observation, biography)
        plan.receipts.append(receipt)
        return receipt

    @staticmethod
    def _call(
        tool_name: CodexToolName,
        payload: dict[str, Any],
        tier: int,
        reason: str,
        *,
        grant_id: str | None = None,
        correlation_id: str | None = None,
    ) -> CodexToolCall:
        raw = f"{tool_name.value}|{datetime.now(timezone.utc).isoformat()}|{payload}"
        return CodexToolCall(
            tool_call_id="tool_" + hashlib.sha1(raw.encode()).hexdigest()[:12],
            tool_name=tool_name,
            input=payload,
            requested_authority_tier=tier,
            user_visible_reason=reason,
            authority_grant_id=grant_id,
            correlation_id=correlation_id,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _plan_id(goal: str, observation_id: str) -> str:
        return "plan_" + hashlib.sha1(f"{goal}|{observation_id}".encode()).hexdigest()[:12]
