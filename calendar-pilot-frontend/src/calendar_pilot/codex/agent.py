from __future__ import annotations

from calendar_pilot.types import CalendarActionReceipt, CandidateCalendarAction, RightMomentDecision, UserBiography


class CodexExecutiveAgent:
    """Conversation/explanation layer for CalendarPilot.

    This reference agent is deterministic. A production Codex layer can call a
    language model, but it should preserve the same explanation contract.
    """

    def explain(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, biography: UserBiography) -> str:
        if receipt.denied_reason:
            return f"I did not apply '{candidate.intent}' because {receipt.denied_reason}."
        authority = f"tier {receipt.authority_tier_used}"
        if candidate.right_moment_decision == RightMomentDecision.AUTO_WRITE_THEN_NOTIFY:
            action_phrase = "I applied it now and kept an undo handle."
        elif candidate.right_moment_decision == RightMomentDecision.NOTIFY_NOW:
            action_phrase = "I would notify now before applying it."
        elif candidate.right_moment_decision == RightMomentDecision.BUNDLE_INTO_DIGEST:
            action_phrase = "I would bundle this into a later digest to reduce interruption."
        elif candidate.right_moment_decision == RightMomentDecision.ASK_CLARIFICATION:
            action_phrase = "I need confirmation because the action affects other people or a higher authority tier."
        else:
            action_phrase = "I would wait for a better response window."
        reward = f"expected reward {candidate.expected_reward:.2f}"
        return (
            f"{candidate.explanation} {action_phrase} "
            f"Authority: {authority}. Score: {reward}. "
            f"Rollback: {receipt.rollback_handle_id or 'none'}."
        )

    def ask_for_autonomy(self, candidate: CandidateCalendarAction, current_tier: int) -> str:
        if candidate.required_authority_tier <= current_tier:
            return "No extra autonomy needed."
        return (
            f"This needs autonomy tier {candidate.required_authority_tier}, "
            f"but current tier is {current_tier}. Grant a narrower scope or confirm this action once?"
        )

    def profile_repair_prompt(self, biography: UserBiography, correction: str) -> str:
        return (
            "I will update the profile as a correction, not as a hidden preference. "
            f"Correction received: {correction}. Current fatigue={biography.notification_fatigue:.2f}."
        )
