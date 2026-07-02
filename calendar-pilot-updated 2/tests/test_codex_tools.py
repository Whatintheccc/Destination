
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from calendar_pilot.codex import CodexToolPlanner, CodexToolRuntime
from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.diffusiongemma.live import LiveDiffusionGemmaCredentialError
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.types import AtomicActionType, AtomicCalendarAction, CandidateCalendarAction, CodexToolCall, CodexToolName, CodexToolStatus, PolicyTuning, RawCalendarObservation, Reversibility, UserBiography
from scripts.train_offline_policy import build_policy_report


ROOT = Path(__file__).resolve().parents[1]


def load_obs() -> RawCalendarObservation:
    return RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))


def load_bio() -> UserBiography:
    return UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))


class CodexToolRuntimeTests(unittest.TestCase):
    def test_codex_can_inspect_generate_compare_stage_and_log_tools(self):
        replay = ReplayBuffer()
        runtime = CodexToolRuntime(replay=replay)
        obs = load_obs()
        bio = load_bio()
        grant = runtime.kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=3, issued_at=obs.observed_at)

        inspect = runtime.execute(CodexToolCall("tool_inspect", CodexToolName.INSPECT_WEEK, {}, 3, "inspect", authority_grant_id=grant.grant_id), obs, bio)
        self.assertEqual(inspect.status, CodexToolStatus.SUCCEEDED)
        self.assertGreaterEqual(inspect.output["event_count"], 1)
        self.assertIn("raw_events", inspect.output)

        frontier = runtime.execute(CodexToolCall("tool_frontier", CodexToolName.GENERATE_CANDIDATE_FRONTIER, {"limit": 4}, 3, "frontier", authority_grant_id=grant.grant_id), obs, bio)
        self.assertEqual(frontier.status, CodexToolStatus.SUCCEEDED)
        candidate_id = frontier.output["frontier_ids"][0]

        compare = runtime.execute(CodexToolCall("tool_compare", CodexToolName.COMPARE_CANDIDATES, {"candidate_ids": [candidate_id]}, 3, "compare", authority_grant_id=grant.grant_id), obs, bio)
        self.assertEqual(compare.status, CodexToolStatus.SUCCEEDED)
        self.assertEqual(compare.output["winner"]["candidate_id"], candidate_id)

        staged = runtime.execute(CodexToolCall("tool_stage", CodexToolName.STAGE_ACTION_PACKET, {"candidate_id": candidate_id}, 3, "stage", authority_grant_id=grant.grant_id), obs, bio)
        self.assertEqual(staged.status, CodexToolStatus.STAGEABLE)
        self.assertTrue(staged.requires_user_confirmation)
        summary = replay.summarize()
        self.assertGreaterEqual(summary.tool_calls, 4)
        self.assertGreaterEqual(summary.tool_receipts, 4)

    def test_codex_commit_routes_through_swift_social_boundary(self):
        runtime = CodexToolRuntime()
        obs = load_obs()
        bio = load_bio()
        target = obs.events[0]
        candidate = CandidateCalendarAction(
            candidate_id="cand_social_tool",
            intent="move_people_meeting",
            actions=[AtomicCalendarAction(
                action_type=AtomicActionType.MOVE_EVENT,
                title=target.title,
                event_id=target.event_id,
                start=target.start,
                end=target.end,
                calendar_id=target.calendar_id,
            )],
            target_calendars=[target.calendar_id],
            affected_event_ids=[target.event_id],
            affected_people_ids=["other@example.com"],
            reversibility=Reversibility.MEDIUM,
            required_authority_tier=5,
        )
        grant = runtime.kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=6, issued_at=obs.observed_at)
        receipt = runtime.execute(CodexToolCall("commit_social", CodexToolName.REQUEST_COMMIT, {"candidate": candidate.to_dict()}, 6, "commit", authority_grant_id=grant.grant_id), obs, bio)
        self.assertEqual(receipt.status, CodexToolStatus.DENIED)
        self.assertIn("social actuation", receipt.denied_reason or "")

    def test_codex_planner_operates_goal_with_tools(self):
        planner = CodexToolPlanner(runtime=CodexToolRuntime())
        plan = planner.plan_goal("Make next week less chaotic", load_obs(), load_bio(), authority_tier=3, commit=False)
        names = [c.tool_name for c in plan.calls]
        self.assertIn(CodexToolName.INSPECT_WEEK, names)
        self.assertIn(CodexToolName.GENERATE_CANDIDATE_FRONTIER, names)
        self.assertIn(CodexToolName.SIMULATE_ACTION_PROGRAM, names)
        self.assertIn(CodexToolName.STAGE_ACTION_PACKET, names)
        self.assertIn(plan.recommended_next_action, {"stage_for_confirmation", "staged_draft"})

    def test_offline_policy_tuning_changes_next_generation(self):
        replay = ReplayBuffer()
        runtime = CodexToolRuntime(replay=replay)
        obs = load_obs()
        bio = load_bio()
        grant = runtime.kernel.issue_authority_grant(user_scope_id=obs.user_scope_id, max_authority_tier=3, issued_at=obs.observed_at)
        runtime.execute(CodexToolCall("frontier", CodexToolName.GENERATE_CANDIDATE_FRONTIER, {"limit": 4}, 3, "frontier", authority_grant_id=grant.grant_id), obs, bio)
        runtime.execute(CodexToolCall("selfplay", CodexToolName.RUN_SELF_PLAY_PROBE, {"episodes": 3}, 3, "probe", authority_grant_id=grant.grant_id), obs, bio)
        report = build_policy_report(replay)
        tuning = PolicyTuning.from_dict(report["policy_tuning"])
        policy = DiffusionGemmaPolicy(policy_tuning=tuning)
        candidates = policy.generate_candidates(obs, bio)
        # At least one candidate should carry an offline tuning note or the report should be genuinely empty.
        has_note = any(any("offline_tuning" in n for n in c.control_notes) for c in candidates)
        self.assertTrue(has_note or not tuning.intent_reward_bias)

    def test_live_policy_failure_returns_failed_frontier_receipt(self):
        replay = ReplayBuffer()
        runtime = CodexToolRuntime(policy=MissingLivePolicy(), replay=replay)
        stale = DiffusionGemmaPolicy().generate_candidates(load_obs(), load_bio())[0]
        runtime.frontier[stale.candidate_id] = stale
        receipt = runtime.execute(
            CodexToolCall("frontier_missing_nim", CodexToolName.GENERATE_CANDIDATE_FRONTIER, {"limit": 4}, 3, "frontier"),
            load_obs(),
            load_bio(),
        )

        self.assertEqual(receipt.status, CodexToolStatus.FAILED)
        self.assertEqual(receipt.output["error_category"], "missing_or_invalid_credential")
        self.assertIn("NVIDIA NIM", receipt.output["recovery"])
        self.assertEqual(replay.records[-1].payload["receipt"]["status"], "failed")
        self.assertEqual(runtime.frontier, {})

    def test_planner_does_not_use_stale_frontier_after_live_policy_failure(self):
        obs = load_obs()
        bio = load_bio()
        runtime = CodexToolRuntime(policy=MissingLivePolicy())
        stale = DiffusionGemmaPolicy().generate_candidates(obs, bio)[0]
        runtime.frontier[stale.candidate_id] = stale

        plan = CodexToolPlanner(runtime=runtime).plan_goal("Make next week less chaotic", obs, bio, authority_tier=3, commit=True)

        names = [call.tool_name for call in plan.calls]
        self.assertIn(CodexToolName.GENERATE_CANDIDATE_FRONTIER, names)
        self.assertIn(CodexToolName.COMPARE_CANDIDATES, names)
        self.assertNotIn(CodexToolName.SIMULATE_ACTION_PROGRAM, names)
        self.assertNotIn(CodexToolName.STAGE_ACTION_PACKET, names)
        self.assertNotIn(CodexToolName.REQUEST_COMMIT, names)
        self.assertEqual(plan.recommended_next_action, "no_candidate_available")
        self.assertEqual(runtime.frontier, {})

    def test_tool_contract_round_trip(self):
        call = CodexToolCall("tool_x", CodexToolName.INSPECT_AUTHORITY_SCOPE, {"x": 1}, 3, "because")
        restored = CodexToolCall.from_dict(call.to_dict())
        self.assertEqual(restored.tool_name, CodexToolName.INSPECT_AUTHORITY_SCOPE)
        self.assertEqual(restored.requested_authority_tier, 3)


class MissingLivePolicy:
    backend_name = "nvidia_nim_diffusiongemma_policy"

    def generate_candidates(self, *_args, **_kwargs):
        raise LiveDiffusionGemmaCredentialError("NVIDIA NIM API key is required")


if __name__ == "__main__":
    unittest.main()
