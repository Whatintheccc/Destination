from __future__ import annotations

from calendar_pilot.biography import BiographyStore
from calendar_pilot.diffusiongemma.reward import RewardModel
from calendar_pilot.diffusiongemma.self_play import SelfPlayMetrics
from calendar_pilot.codex.planner import CodexToolPlanner
from calendar_pilot.types import CalendarActionReceipt, CandidateCalendarAction, RightMomentDecision, UserBiography, RawCalendarObservation


class CodexExecutiveAgent:
    """Conversation/explanation layer for CalendarPilot.

    This version is intentionally more agentic than the first pass: Codex does
    not just echo a score. It tells the action story: what the model saw, why it
    acted now, how Swift bounded the write, and which reward heads were doing the
    work. A production Codex layer can be model-backed, but this deterministic
    contract keeps explanations inspectable.
    """


    def operate_goal(
        self,
        goal: str,
        observation: RawCalendarObservation,
        biography: UserBiography,
        *,
        authority_tier: int = 3,
        commit: bool = False,
        planner: CodexToolPlanner | None = None,
    ) -> str:
        planner = planner or CodexToolPlanner()
        plan = planner.plan_goal(goal, observation, biography, authority_tier=authority_tier, commit=commit)
        statuses = ", ".join(f"{r.tool_name.value}:{r.status.value}" for r in plan.receipts)
        return (
            f"I operated on `{goal}` with {len(plan.calls)} tool call(s): {statuses}. "
            f"Recommended next action: {plan.recommended_next_action}."
        )

    def explain(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, biography: UserBiography) -> str:
        if receipt.denied_reason:
            return self._denied(candidate, receipt)
        action_phrase = self._action_phrase(candidate, receipt)
        positives = ", ".join(RewardModel.top_positive_heads(candidate)) or "no positive head dominated"
        negatives = ", ".join(RewardModel.top_negative_heads(candidate)) or "no major penalty"
        story = " ".join(candidate.model_story[:3]) or candidate.explanation
        counterfactual = candidate.counterfactual or "No counterfactual was attached."
        notes = self._compact_notes(candidate.control_notes)
        return (
            f"I chose `{candidate.intent}`. {story} "
            f"Counterfactual: {counterfactual} "
            f"Actuation: {action_phrase} "
            f"Reward anatomy: +[{positives}] / -[{negatives}], total {candidate.expected_reward:.2f}. "
            f"Timing: {candidate.right_moment_decision.value} at score {candidate.right_moment_score:.2f}. "
            f"Control notes: {notes} "
            f"Rollback: {receipt.rollback_handle_id or 'none'}."
        )

    def summarize_self_play(self, metrics: SelfPlayMetrics) -> str:
        failures = ", ".join(metrics.top_failure_modes) or "none"
        intents = ", ".join(f"{k}:{v}" for k, v in sorted(metrics.chosen_intents.items())) or "none"
        return (
            f"Self-play ran {metrics.episodes} episode(s): acceptance={metrics.acceptance_rate:.2f}, "
            f"undo={metrics.undo_rate:.2f}, avg_reward={metrics.average_reward:.2f}, "
            f"adversarial_delta={metrics.adversarial_delta:.2f}. "
            f"Chosen intents: {intents}. Failure modes: {failures}."
        )

    def ask_for_autonomy(self, candidate: CandidateCalendarAction, current_tier: int) -> str:
        if candidate.required_authority_tier <= current_tier:
            return "No extra autonomy needed."
        return (
            f"This needs autonomy tier {candidate.required_authority_tier}, "
            f"but current tier is {current_tier}. Grant a narrower scope, stage it as a draft, or confirm once?"
        )

    def profile_repair_prompt(self, biography: UserBiography, correction: str) -> str:
        plan = BiographyStore().propose_repair(biography, correction)
        return (
            "I will treat this as an explicit profile correction, not a hidden preference. "
            f"{plan.prompt} Current notification fatigue={biography.notification_fatigue:.2f}."
        )

    @staticmethod
    def _action_phrase(candidate: CandidateCalendarAction, receipt: CalendarActionReceipt) -> str:
        authority = f"Swift used tier {receipt.authority_tier_used} authority"
        if receipt.sync_status == "staged":
            return f"I staged this instead of mutating the calendar; {authority}; staged={receipt.staged_action_ids}."
        if candidate.right_moment_decision == RightMomentDecision.AUTO_WRITE_THEN_NOTIFY:
            return f"I applied the reversible write now; {authority}."
        if candidate.right_moment_decision == RightMomentDecision.NOTIFY_NOW:
            return f"I would notify now; {authority}."
        if candidate.right_moment_decision == RightMomentDecision.SILENTLY_DRAFT:
            return f"I would stage this silently as a draft; {authority}."
        if candidate.right_moment_decision == RightMomentDecision.BUNDLE_INTO_DIGEST:
            return f"I would bundle this into the next digest; {authority}."
        if candidate.right_moment_decision == RightMomentDecision.ASK_CLARIFICATION:
            return f"I would ask before touching people-affecting time; {authority}."
        if candidate.right_moment_decision == RightMomentDecision.WAIT:
            return f"I would wait for the predicted response window; {authority}."
        return f"I left the calendar unchanged; {authority}."

    @staticmethod
    def _denied(candidate: CandidateCalendarAction, receipt: CalendarActionReceipt) -> str:
        return (
            f"I did not apply `{candidate.intent}` because Swift denied actuation: {receipt.denied_reason}. "
            f"The candidate can still be staged or rerun with a narrower authority scope."
        )

    @staticmethod
    def _compact_notes(notes: list[str], limit: int = 3) -> str:
        if not notes:
            return "none"
        return "; ".join(notes[:limit])
