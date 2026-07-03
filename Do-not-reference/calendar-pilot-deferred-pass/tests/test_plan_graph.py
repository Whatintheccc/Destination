from __future__ import annotations

import unittest
from calendar_pilot.environment.plan_graph import TierSixPlanGraph, encode_plan_graph, actions_from_plan_metadata, rollback_order_from_metadata
from calendar_pilot.types import AtomicCalendarAction, AtomicActionType


class TierSixPlanGraphTests(unittest.TestCase):
    def test_plan_graph_expands_and_preserves_rollback_order(self):
        actions = [
            AtomicCalendarAction(action_type=AtomicActionType.CREATE_FOCUS_BLOCK, title="Focus", calendar_id="work"),
            AtomicCalendarAction(action_type=AtomicActionType.ADD_BUFFER, title="Buffer", calendar_id="work"),
        ]
        graph = TierSixPlanGraph.from_actions(plan_id="plan_6", actions=actions)
        metadata = {"plan_graph": encode_plan_graph(graph)}
        expanded = actions_from_plan_metadata(metadata)
        self.assertEqual([a.action_type for a in expanded], [AtomicActionType.CREATE_FOCUS_BLOCK, AtomicActionType.ADD_BUFFER])
        self.assertEqual(rollback_order_from_metadata(metadata), ["step_2", "step_1"])


if __name__ == "__main__":
    unittest.main()
