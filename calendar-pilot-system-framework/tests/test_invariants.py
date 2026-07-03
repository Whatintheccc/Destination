import unittest

from calendar_pilot.environment.invariants import check_replay


def _rec(record_type, record_id, trace_id="t1", parent=None, payload=None):
    return {
        "record_type": record_type,
        "record_id": record_id,
        "trace_id": trace_id,
        "causal_parent_id": parent,
        "payload": payload or {},
    }


class InvariantTests(unittest.TestCase):
    def test_clean_replay_passes(self):
        records = [
            _rec("envelope_transition", "e1", payload={
                "envelope": {
                    "envelope_id": "env1",
                    "current_state": "commit",
                    "provider": {"rollback_state": "verified"},
                }
            }),
            _rec("receipt", "r1", parent="e1", payload={
                "receipt": {
                    "sync_status": "reverted",
                    "rollback_handle_id": "u1",
                    "candidate_id": "c1",
                }
            }),
        ]

        self.assertEqual(check_replay(records), [])

    def test_missing_rollback_state_violates_i2(self):
        records = [_rec("envelope_transition", "e1", payload={
            "envelope": {"envelope_id": "env1", "current_state": "commit", "provider": {}}
        })]

        self.assertIn("I2", [v.invariant_id for v in check_replay(records)])

    def test_double_undo_violates_i6(self):
        undo = {"receipt": {"sync_status": "reverted", "rollback_handle_id": "u1", "candidate_id": "c1"}}
        records = [_rec("receipt", "r1", payload=undo), _rec("receipt", "r2", payload=undo)]

        self.assertIn("I6", [v.invariant_id for v in check_replay(records)])

    def test_missing_record_id_violates_r1(self):
        records = [_rec("decision", "")]

        self.assertIn("R1", [v.invariant_id for v in check_replay(records)])

    def test_missing_trace_id_violates_r2(self):
        records = [_rec("decision", "d1", trace_id="")]

        self.assertIn("R2", [v.invariant_id for v in check_replay(records)])

    def test_unknown_causal_parent_violates_r3(self):
        records = [_rec("decision", "d1", parent="ghost")]

        self.assertIn("R3", [v.invariant_id for v in check_replay(records)])

    def test_receipt_without_candidate_violates_r4(self):
        records = [_rec("receipt", "r1", payload={"receipt": {"sync_status": "materialized"}})]

        self.assertIn("R4", [v.invariant_id for v in check_replay(records)])

    def test_orphan_reward_violates_r5(self):
        records = [_rec("reward", "w1")]

        self.assertIn("R5", [v.invariant_id for v in check_replay(records)])
