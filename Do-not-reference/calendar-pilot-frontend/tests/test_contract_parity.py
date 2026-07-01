import json
import unittest
from dataclasses import fields
from pathlib import Path

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.types import AuthorityGrant, CalendarActionReceipt, CandidateCalendarAction, CodexToolCall, CodexToolReceipt, RawCalendarObservation, RewardEvent, UserBiography
from calendar_pilot.swift_bridge import SwiftKernelStub

ROOT = Path(__file__).resolve().parents[1]


class ContractParityTests(unittest.TestCase):
    def test_candidate_schema_covers_python_dataclass_agent_fields(self):
        schema = json.loads((ROOT / "contracts/candidate_calendar_action.schema.json").read_text())
        props = set(schema["properties"].keys())
        dataclass_names = {f.name for f in fields(CandidateCalendarAction)}
        self.assertTrue(dataclass_names <= props, f"missing from schema: {sorted(dataclass_names - props)}")
        for canonical in ["model_story", "counterfactual", "reward_breakdown", "right_moment_score", "simulated_outcomes"]:
            self.assertIn(canonical, props)

    def test_receipt_schema_covers_python_dataclass(self):
        schema = json.loads((ROOT / "contracts/calendar_action_receipt.schema.json").read_text())
        props = set(schema["properties"].keys())
        dataclass_names = {f.name for f in fields(CalendarActionReceipt)}
        self.assertTrue(dataclass_names <= props, f"missing from schema: {sorted(dataclass_names - props)}")


    def test_authority_grant_schema_covers_python_dataclass(self):
        schema = json.loads((ROOT / "contracts/authority_grant.schema.json").read_text())
        props = set(schema["properties"].keys())
        self.assertTrue({f.name for f in fields(AuthorityGrant)} <= props)

    def test_swift_observation_and_reward_contracts_have_python_parity_fields(self):
        source = (ROOT / "packages/CalendarPilotKernel/Sources/CalendarPilotKernel/CalendarContracts.swift").read_text()
        for token in ["RawTask", "DeviceContext", "tasks", "notificationHistory", "priorActions"]:
            self.assertIn(token, source)
        for token in ["utilityReward", "acceptanceReward", "engagementReward", "regretPenalty", "interruptionPenalty", "socialRiskPenalty"]:
            self.assertIn(token, source)
        schema = json.loads((ROOT / "contracts/reward_event.schema.json").read_text())
        self.assertTrue({f.name for f in fields(RewardEvent)} <= set(schema["properties"].keys()))

    def test_policy_candidate_round_trips_through_contract_dict(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))
        candidate = DiffusionGemmaPolicy().generate_candidates(observation, biography)[0]
        restored = CandidateCalendarAction.from_dict(candidate.to_dict())
        self.assertEqual(restored.candidate_id, candidate.candidate_id)
        self.assertEqual(restored.right_moment_decision, candidate.right_moment_decision)
        self.assertEqual(restored.reward_breakdown["utility"], candidate.reward_breakdown["utility"])

    def test_swift_contract_source_contains_canonical_agent_fields(self):
        source = (ROOT / "packages/CalendarPilotKernel/Sources/CalendarPilotKernel/CalendarContracts.swift").read_text()
        for token in ["modelStory", "counterfactual", "rewardBreakdown", "rightMomentScore", "simulatedOutcomes", "CodingKeys"]:
            self.assertIn(token, source)
        self.assertIn('case modelStory = "model_story"', source)
        self.assertIn('case actionType = "action_type"', source)


    def test_codex_tool_schemas_cover_python_contracts(self):
        call_schema = json.loads((ROOT / "contracts/codex_tool_call.schema.json").read_text())
        receipt_schema = json.loads((ROOT / "contracts/codex_tool_receipt.schema.json").read_text())
        self.assertTrue({f.name for f in fields(CodexToolCall)} <= set(call_schema["properties"].keys()))
        self.assertTrue({f.name for f in fields(CodexToolReceipt)} <= set(receipt_schema["properties"].keys()))
        self.assertIn("request_commit", call_schema["properties"]["tool_name"]["enum"])
        self.assertIn("requires_confirmation", receipt_schema["properties"]["status"]["enum"])

    def test_swift_contract_source_contains_codex_tool_contracts(self):
        source = (ROOT / "packages/CalendarPilotKernel/Sources/CalendarPilotKernel/CodexToolContracts.swift").read_text()
        for token in ["CodexToolCall", "CodexToolReceipt", "CodexToolName", "CodexToolStatus", "requestedAuthorityTier"]:
            self.assertIn(token, source)
        self.assertIn('case requestCommit = "request_commit"', source)

    def test_receipt_contract_round_trip_from_kernel_stub(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))
        candidate = DiffusionGemmaPolicy().generate_candidates(observation, biography)[0]
        receipt = SwiftKernelStub().authorize_and_materialize(candidate, observation, granted_authority_tier=3)
        data = receipt.to_dict()
        self.assertIn(data["actuation_mode"], {"no_op", "materialized_write", "staged_draft", "staged_notification", "denied"})
        self.assertIn("staged_action_ids", data)


if __name__ == "__main__":
    unittest.main()
