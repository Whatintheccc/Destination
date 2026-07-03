from __future__ import annotations

import os
import unittest
from pathlib import Path

from scripts.run_contract_vectors import run_vector

ROOT = Path(__file__).resolve().parents[1]
VECTOR = ROOT / "contracts" / "testdata" / "kernel_vectors" / "private_create_commit.json"


class ContractGoldenVectorTests(unittest.TestCase):
    def test_python_stub_matches_golden_vector(self):
        result = run_vector(VECTOR, swift=False)
        self.assertTrue(result["ok"], result)

    @unittest.skipUnless(os.environ.get("CALENDAR_PILOT_RUN_SWIFT_IPC_TESTS") == "1", "Swift IPC vector test is opt-in")
    def test_swift_kernel_server_matches_golden_vector(self):
        result = run_vector(VECTOR, swift=True)
        self.assertTrue(result["ok"], result)


if __name__ == "__main__":
    unittest.main()
