import json
import tempfile
import unittest
from pathlib import Path

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
            latest = json.loads((tmp_path / "artifacts" / "nim_schema_failure.json").read_text())
            self.assertEqual(latest["category"], "model_policy_schema_failure")
            rows = [json.loads(line) for line in replay_path.read_text().splitlines() if line.strip()]
            self.assertEqual(rows[0]["record_type"], "model_generation_rejection")
            self.assertEqual(rows[0]["record_schema_version"], "r1")
            self.assertEqual(rows[0]["causal_parent_id"], "ROOT")
            self.assertEqual(rows[0]["payload"]["stage"], "frontier_tuned")


if __name__ == "__main__":
    unittest.main()
