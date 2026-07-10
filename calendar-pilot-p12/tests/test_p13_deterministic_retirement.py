from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from evals.architecture.adapters.p13_retirement_scenarios import collect_retirement_case
from evals.architecture.predicates.p13 import vertical_retirement_contract


ROOT = Path(__file__).resolve().parents[1]


class DeterministicRetirementTests(unittest.TestCase):
    def _assert_case(self, case: str) -> dict:
        with tempfile.TemporaryDirectory() as td:
            evidence = collect_retirement_case(case, scenario_dir=Path(td), root=ROOT)
        self.assertIsNotNone(evidence)
        result = vertical_retirement_contract({"vertical_retirement": evidence})
        self.assertEqual(result["status"], "pass", result)
        return evidence

    def test_exact_scope_selects_one_new_owner_without_eventkit_leakage(self):
        evidence = self._assert_case("retirement_scope_binding")
        self.assertEqual(evidence["retired_scope_cardinality"], 1)

    def test_normal_callers_cannot_restore_the_incumbent_owner(self):
        evidence = self._assert_case("retirement_single_owner")
        self.assertTrue(evidence["normal_incumbent_override_rejected"])

    def test_visible_commit_uses_one_ticket_claim_dispatch_and_no_legacy_commit(self):
        evidence = self._assert_case("retirement_runtime_commit")
        self.assertEqual(evidence["legacy_kernel_commit_count"], 0)
        self.assertEqual(evidence["legacy_provider_commit_count"], 0)

    def test_visible_undo_uses_separate_compensation_and_no_legacy_undo(self):
        evidence = self._assert_case("retirement_runtime_undo")
        self.assertTrue(evidence["effect_absent"])
        self.assertEqual(evidence["legacy_kernel_undo_count"], 0)

    def test_restart_reconciles_without_redispatch_and_owner_rollback_is_single(self):
        evidence = self._assert_case("retirement_restart_rollback")
        self.assertEqual(evidence["dispatch_count_after_restart"], 1)
        self.assertFalse(evidence["dual_owner_observed"])


if __name__ == "__main__":
    unittest.main()
