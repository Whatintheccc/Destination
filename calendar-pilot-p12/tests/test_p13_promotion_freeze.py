from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "experiments/promoted/CURRENT.json"


def _tree_digest() -> str:
    digest = hashlib.sha256()
    for root in [ROOT / "experiments/promoted", ROOT / "experiments/reports"]:
        if not root.exists():
            continue
        for path in sorted(value for value in root.rglob("*") if value.is_file()):
            digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


class P13PromotionFreezeTests(unittest.TestCase):
    def _invoke(self, *extra: str) -> dict:
        before_tree = _tree_digest()
        before_current = CURRENT.read_bytes()
        process = subprocess.run(
            [sys.executable, "scripts/promote_policy.py", "--batch", "p13-freeze-attack", *extra],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(process.returncode, 3, process.stderr)
        self.assertEqual(_tree_digest(), before_tree)
        self.assertEqual(CURRENT.read_bytes(), before_current)
        payload = json.loads(process.stdout)
        self.assertEqual(payload["decision"], "hold")
        self.assertEqual(payload["promotion_artifact_writes"], 0)
        return payload

    def test_force_promote_is_held_before_any_write(self):
        payload = self._invoke("--decide", "promote")
        self.assertEqual(payload["requested_decision"], "promote")

    def test_automatic_promotion_is_also_held(self):
        payload = self._invoke()
        self.assertEqual(payload["requested_decision"], "automatic")

    def test_make_access_point_is_frozen(self):
        before_tree = _tree_digest()
        before_current = CURRENT.read_bytes()
        process = subprocess.run(
            ["make", "lab-promote", "BATCH=p13-freeze-attack"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertIn('"decision": "hold"', process.stdout)
        self.assertEqual(_tree_digest(), before_tree)
        self.assertEqual(CURRENT.read_bytes(), before_current)


if __name__ == "__main__":
    unittest.main()
