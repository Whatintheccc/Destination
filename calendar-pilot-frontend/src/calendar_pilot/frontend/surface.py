from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from calendar_pilot.codex.planner import CodexExecutivePlan
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import RawCalendarObservation, UserBiography, to_jsonable


@dataclass(frozen=True)
class FrontendPanel:
    panel_id: str
    title: str
    purpose: str
    surface_type: str
    user_question: str
    rows: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class FrontendAction:
    action_id: str
    label: str
    status: str
    control_boundary: str
    receipt_id: str | None = None
    grant_id: str | None = None
    rollback_handle_id: str | None = None
    requires_confirmation: bool = False
    why_user_sees_it: str = ""


@dataclass(frozen=True)
class FrontendSnapshot:
    product_name: str
    goal: str
    summary: dict[str, Any]
    panels: list[FrontendPanel]
    action_queue: list[FrontendAction]
    trace: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


def build_frontend_snapshot(
    plan: CodexExecutivePlan,
    observation: RawCalendarObservation,
    biography: UserBiography,
    replay: ReplayBuffer | None = None,
) -> FrontendSnapshot:
    """Build a user-facing state model for the non-chat product surface.

    The frontend should expose what the machine is learning and what it is
    preparing to change. It should not make the user reconstruct authority,
    reward, self-play, and rollback from a chat transcript.
    """
    replay = replay or ReplayBuffer()
    candidate_rows = _candidate_rows(plan)
    acting_rows = _acting_rows(plan)
    authority_rows = _authority_rows(plan)
    replay_summary = replay.summarize()
    self_play_rows = [
        {"failure_mode": label, "count": count}
        for label, count in sorted(replay_summary.failure_modes.items(), key=lambda kv: kv[1], reverse=True)
    ]
    profile_rows = [
        {
            "claim": claim.get("claim", ""),
            "confidence": claim.get("confidence", 0.0),
            "last_evidence": claim.get("last_evidence", claim.get("reason", "")),
            "repair_action": "edit_or_decay",
        }
        for claim in biography.preference_claims[:8]
    ]

    panels = [
        FrontendPanel(
            panel_id="calendar_pressure",
            title="Calendar pressure map",
            purpose="Show the raw-context pressure Codex inspected before asking the learner to propose actions.",
            surface_type="machine_learning_input",
            user_question="What state did the machine read before acting?",
            rows=[_inspection_summary(plan, observation)],
        ),
        FrontendPanel(
            panel_id="candidate_frontier",
            title="Candidate futures",
            purpose="Make DiffusionGemma's generated futures, reward anatomy, regret, and right-moment estimates visible.",
            surface_type="machine_learning_frontier",
            user_question="Which futures did the learner consider, and why did one win?",
            rows=candidate_rows,
        ),
        FrontendPanel(
            panel_id="acting_queue",
            title="Acting queue",
            purpose="Show staged, denied, committed, and undoable machine acts as first-class app objects, not chat prose.",
            surface_type="machine_acting_control",
            user_question="What is the machine about to change, what changed, and how do I undo it?",
            rows=acting_rows,
        ),
        FrontendPanel(
            panel_id="authority_boundary",
            title="Authority grants",
            purpose="Expose the Swift-issued grant that lets Codex request stage/commit/undo without carrying raw authority by value.",
            surface_type="machine_acting_authority",
            user_question="What authority did this action use, where did it come from, and when does it expire?",
            rows=authority_rows,
        ),
        FrontendPanel(
            panel_id="self_play_findings",
            title="Self-play failure modes",
            purpose="Surface adversary findings that should tune policy before more autonomy is granted.",
            surface_type="machine_learning_self_play",
            user_question="How did the system stress-test this policy against regret, fatigue, conflict, and engagement traps?",
            rows=self_play_rows,
        ),
        FrontendPanel(
            panel_id="biography_repair",
            title="Learned biography repair",
            purpose="Make persistent user-model claims inspectable, editable, decayable, and tied to provenance.",
            surface_type="machine_learning_profile",
            user_question="What has the app learned about me, and how can I repair it?",
            rows=profile_rows,
        ),
    ]
    return FrontendSnapshot(
        product_name="CalendarPilot",
        goal=plan.goal,
        summary={
            "plan_id": plan.plan_id,
            "observation_id": observation.observation_id,
            "recommended_next_action": plan.recommended_next_action,
            "default_path": "codex_tool_executive",
            "chat_role": "secondary_explanation_surface",
            "primary_surfaces": [p.panel_id for p in panels],
        },
        panels=panels,
        action_queue=_action_queue(plan),
        trace=[
            {
                "tool": receipt.tool_name.value,
                "status": receipt.status.value,
                "stage_state": receipt.stage_state.value,
                "swift_receipt_id": receipt.swift_receipt_id,
                "denied_reason": receipt.denied_reason,
            }
            for receipt in plan.receipts
        ],
    )


def _inspection_summary(plan: CodexExecutivePlan, observation: RawCalendarObservation) -> dict[str, Any]:
    inspect = next((r for r in plan.receipts if r.tool_name.value == "inspect_week"), None)
    return {
        "event_count": len(observation.events),
        "task_count": len(observation.tasks),
        "pressure_score": inspect.output.get("pressure_score") if inspect else None,
        "fatigue_score": inspect.output.get("fatigue_score") if inspect else None,
        "risk_cliffs": inspect.output.get("risk_cliffs", []) if inspect else [],
        "surface": observation.device_context.active_surface,
        "focus_mode": observation.device_context.is_focus_mode,
    }


def _candidate_rows(plan: CodexExecutivePlan) -> list[dict[str, Any]]:
    frontier = next((r for r in plan.receipts if r.tool_name.value == "generate_candidate_frontier"), None)
    compare = next((r for r in plan.receipts if r.tool_name.value == "compare_candidates"), None)
    ranks = {row.get("candidate_id"): idx + 1 for idx, row in enumerate(compare.output.get("ranking", []))} if compare else {}
    rows: list[dict[str, Any]] = []
    for candidate in (frontier.output.get("candidates", []) if frontier else []):
        rows.append({
            "rank": ranks.get(candidate.get("candidate_id")),
            "candidate_id": candidate.get("candidate_id"),
            "intent": candidate.get("intent"),
            "expected_reward": candidate.get("expected_reward"),
            "right_moment_score": candidate.get("right_moment_score"),
            "right_moment_decision": candidate.get("right_moment_decision"),
            "predicted_regret": candidate.get("predicted_regret"),
            "predicted_social_risk": candidate.get("predicted_social_risk"),
            "required_authority_tier": candidate.get("required_authority_tier"),
            "model_story": candidate.get("model_story", [])[:3],
            "reward_breakdown": candidate.get("reward_breakdown", {}),
        })
    return rows


def _acting_rows(plan: CodexExecutivePlan) -> list[dict[str, Any]]:
    rows = []
    for receipt in plan.receipts:
        swift = receipt.output.get("swift_receipt") if isinstance(receipt.output, dict) else None
        if not isinstance(swift, dict):
            continue
        rows.append({
            "tool": receipt.tool_name.value,
            "status": receipt.status.value,
            "stage_state": receipt.stage_state.value,
            "sync_status": swift.get("sync_status"),
            "actuation_mode": swift.get("actuation_mode"),
            "generated_event_ids": swift.get("generated_event_ids", []),
            "staged_action_ids": swift.get("staged_action_ids", []),
            "rollback_handle_id": swift.get("rollback_handle_id"),
            "denied_reason": swift.get("denied_reason"),
        })
    return rows


def _authority_rows(plan: CodexExecutivePlan) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for receipt in plan.receipts:
        grant_id = receipt.authority_grant_id
        if not grant_id or grant_id in seen:
            continue
        seen.add(grant_id)
        rows.append({
            "authority_grant_id": grant_id,
            "first_seen_tool": receipt.tool_name.value,
            "status": receipt.status.value,
            "stage_state": receipt.stage_state.value,
            "boundary": "Swift-issued grant id resolved inside kernel; embedded grants are ignored.",
        })
    return rows


def _action_queue(plan: CodexExecutivePlan) -> list[FrontendAction]:
    actions: list[FrontendAction] = []
    for receipt in plan.receipts:
        swift = receipt.output.get("swift_receipt") if isinstance(receipt.output, dict) else None
        if not isinstance(swift, dict):
            continue
        status = receipt.status.value
        if status not in {"stageable", "staged", "committed", "denied", "requires_confirmation"}:
            continue
        actions.append(FrontendAction(
            action_id=swift.get("receipt_id") or receipt.swift_receipt_id or receipt.tool_call_id,
            label=_action_label(receipt.tool_name.value, status, swift),
            status=status,
            control_boundary="Codex requested; Swift validated; provider write remains behind Swift.",
            receipt_id=swift.get("receipt_id") or receipt.swift_receipt_id,
            grant_id=receipt.authority_grant_id,
            rollback_handle_id=swift.get("rollback_handle_id"),
            requires_confirmation=receipt.requires_user_confirmation,
            why_user_sees_it=_why_user_sees_it(receipt.tool_name.value, swift),
        ))
    return actions


def _action_label(tool: str, status: str, swift: dict[str, Any]) -> str:
    if status == "committed":
        return "Committed calendar change"
    if status in {"stageable", "staged", "requires_confirmation"}:
        return "Staged calendar packet"
    if status == "denied":
        return "Denied machine act"
    return tool.replace("_", " ").title()


def _why_user_sees_it(tool: str, swift: dict[str, Any]) -> str:
    if swift.get("denied_reason"):
        return "The app should show denials so the user can narrow authority, choose a safer alternative, or repair the model."
    if swift.get("rollback_handle_id"):
        return "This changed calendar state and has a rollback handle, so it belongs in the acting queue."
    if swift.get("staged_action_ids"):
        return "This is not committed provider state yet; it needs user confirmation or narrower authority."
    return "This is part of the typed machine-acting trace."
