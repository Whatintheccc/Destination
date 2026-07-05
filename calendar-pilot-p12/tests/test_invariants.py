from __future__ import annotations

import unittest

from calendar_pilot.environment.invariants import check_replay


class InvariantCheckerTests(unittest.TestCase):
    def test_denied_commit_with_null_swift_receipt_is_inspectable(self):
        records = [
            {
                "record_type": "envelope_transition",
                "record_id": "envelope_transition:env_denied:commit:1",
                "trace_id": "trace_denied",
                "payload": {
                    "envelope": {
                        "envelope_id": "env_denied",
                        "current_state": "commit",
                        "swift_receipt": None,
                        "provider": {"rollback_state": "unsupported"},
                        "lifecycle": [
                            {
                                "transition": "commit",
                                "status": "denied",
                                "detail": {"denied_reason": "autonomy_matrix_denied:create_prep_block"},
                            }
                        ],
                    }
                },
            }
        ]

        self.assertEqual(check_replay(records), [])


if __name__ == "__main__":
    unittest.main()
