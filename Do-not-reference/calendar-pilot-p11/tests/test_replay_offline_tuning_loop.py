import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from calendar_pilot.diffusiongemma.live import LiveDiffusionGemmaSchemaError
from calendar_pilot.replay import ReplayBuffer
from scripts import run_replay_offline_tuning_loop as loop


class ReplayOfflineTuningLoopTests(unittest.TestCase):
    def test_live_nim_schema_failure_writes_artifact_and_replay_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            old_artifact_dir = loop.ARTIFACT_DIR
            loop.ARTIFACT_DIR = tmp_path / "artifacts"
            try:
                replay = ReplayBuffer()
                replay_path = tmp_path / "replay.jsonl"
                with patch.dict("os.environ", {}, clear=True):
                    payload = loop.record_live_nim_schema_failure(
                        "frontier_tuned",
                        LiveDiffusionGemmaSchemaError("invalid JSON after retries"),
                        replay=replay,
                        replay_path=replay_path,
                        extra={"policy_tuning_id": "tuning_test"},
                    )
            finally:
                loop.ARTIFACT_DIR = old_artifact_dir

            self.assertEqual(payload["reason"], "live_nim_frontier_schema_failure")
            self.assertEqual(payload["stage"], "frontier_tuned")
            self.assertEqual(payload["policy_tuning_id"], "tuning_test")
            self.assertEqual(payload["decision"], "controlled_hold")
            self.assertFalse(payload["strict_live_required"])
            latest = json.loads((tmp_path / "artifacts" / "nim_schema_failure.json").read_text())
            self.assertEqual(latest["category"], "model_policy_schema_failure")
            rows = [json.loads(line) for line in replay_path.read_text().splitlines() if line.strip()]
            self.assertEqual(rows[0]["record_type"], "model_generation_rejection")
            self.assertEqual(rows[0]["record_schema_version"], "r1")
            self.assertEqual(rows[0]["causal_parent_id"], "ROOT")
            self.assertEqual(rows[0]["payload"]["stage"], "frontier_tuned")

    def test_live_nim_schema_failure_can_fail_closed_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            old_artifact_dir = loop.ARTIFACT_DIR
            loop.ARTIFACT_DIR = tmp_path / "artifacts"
            try:
                with patch.dict("os.environ", {loop.REQUIRE_LIVE_NIM_ENV: "1"}, clear=True):
                    payload = loop.record_live_nim_schema_failure(
                        "frontier_tuned",
                        LiveDiffusionGemmaSchemaError("invalid JSON after retries"),
                    )
            finally:
                loop.ARTIFACT_DIR = old_artifact_dir

            self.assertEqual(payload["decision"], "fail")
            self.assertTrue(payload["strict_live_required"])


if __name__ == "__main__":
    unittest.main()
