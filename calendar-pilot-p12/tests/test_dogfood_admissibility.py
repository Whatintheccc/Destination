from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from evals.dogfood.admissibility import (
    BROWSER_CAPTURE_PATH,
    CAPTURE_MANIFEST_NAME,
    CAPTURE_ROWS_NAME,
    capture_nonce,
    check_independent_visible_capture,
    check_raw_normalized_equality,
    check_replay_parent_resolution,
    derive_admissibility,
)
from evals.dogfood.capture.browser_capture import extract_semantic_dom


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def journal_record(scope: str, row_id: str, parents: list[str], *, record_id: str, causal_parent_id: str | None) -> dict:
    return {
        "record_id": record_id,
        "record_type": "product_core_journal_event",
        "causal_parent_id": causal_parent_id,
        "payload": {
            "journal_scope_id": scope,
            "journal_event": {"row_id": row_id, "event_type": "test", "occurred_at": "t", "payload": {}, "causal_parent_ids": parents, "content_sha256": "0" * 64},
        },
    }


class ReplayParentResolutionTests(unittest.TestCase):
    def run_check(self, rows: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            write_jsonl(run_dir / "replay.jsonl", rows)
            return check_replay_parent_resolution(run_dir)

    def test_resolved_parents_pass(self) -> None:
        rows = [
            {"record_id": "a", "causal_parent_id": None, "payload": {}},
            {"record_id": "b", "causal_parent_id": "a", "payload": {}},
            journal_record("scope-1", "scope-1:obs", [], record_id="j1", causal_parent_id="b"),
            journal_record("scope-1", "scope-1:prop", ["scope-1:obs"], record_id="j2", causal_parent_id="j1"),
        ]
        result = self.run_check(rows)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["checked_replay_records"], 4)
        self.assertEqual(result["checked_journal_events"], 2)

    def test_planted_unresolved_raw_parent_fails(self) -> None:
        rows = [
            {"record_id": "a", "causal_parent_id": None, "payload": {}},
            {"record_id": "b", "causal_parent_id": "scope-1:obs", "payload": {}},
        ]
        result = self.run_check(rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("I3" in violation["detail"] for violation in result["violations"]))

    def test_journal_parent_outside_scope_fails(self) -> None:
        rows = [
            journal_record("scope-1", "scope-1:obs", [], record_id="j1", causal_parent_id=None),
            journal_record("scope-2", "scope-2:prop", ["scope-1:obs"], record_id="j2", causal_parent_id=None),
        ]
        result = self.run_check(rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("journal parent not in scope" in violation["detail"] for violation in result["violations"]))

    def test_missing_replay_fails_never_holds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = check_replay_parent_resolution(Path(td))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(result["replay_required"])

    def test_d0_missing_replay_is_admissible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = check_replay_parent_resolution(Path(td), replay_required=False)
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["replay_required"])
        self.assertEqual(result["checked_replay_records"], 0)


class RawNormalizedEqualityTests(unittest.TestCase):
    def build_run(self, td: str) -> tuple[Path, list[dict]]:
        run_dir = Path(td)
        raw_rows = [{"record_id": "replay:1", "record_type": "planning_decision", "payload": {"stage_actions": 0, "candidate_id": "c1"}}]
        write_jsonl(run_dir / "replay.jsonl", raw_rows)
        envelope = {
            "dogfood_evidence_schema_version": "dogfood_evidence.v1",
            "scenario_id": "P-RECOMMEND",
            "payload": {"stage_actions": 0, "candidate_id": "c1"},
            "raw_refs": [{
                "artifact": "replay.jsonl",
                "artifact_sha256": sha256_path(run_dir / "replay.jsonl"),
                "record_id": "replay:1",
                "scenario_id": "P-RECOMMEND",
                "fields": ["stage_actions", "candidate_id"],
            }],
        }
        rows = [{"scenario_id": "P-RECOMMEND", "source": "replay", "payload": envelope["payload"], "label": "replay.jsonl:2", "envelope": envelope}]
        return run_dir, rows

    def test_re_derived_fields_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir, rows = self.build_run(td)
            result = check_raw_normalized_equality(run_dir, rows)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["checked_normalized_rows"], 1)

    def test_planted_normalized_payload_disagrees_with_cited_raw_row(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir, rows = self.build_run(td)
            rows[0]["envelope"]["payload"] = dict(rows[0]["envelope"]["payload"], stage_actions=1)
            result = check_raw_normalized_equality(run_dir, rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("disagrees with cited raw row" in violation["detail"] for violation in result["violations"]))

    def test_missing_raw_refs_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir, rows = self.build_run(td)
            del rows[0]["envelope"]["raw_refs"]
            result = check_raw_normalized_equality(run_dir, rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("does not cite raw_refs" in violation["detail"] for violation in result["violations"]))

    def test_uncovered_protected_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir, rows = self.build_run(td)
            rows[0]["envelope"]["raw_refs"][0]["fields"] = ["stage_actions"]
            result = check_raw_normalized_equality(run_dir, rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("not re-derived" in violation["detail"] for violation in result["violations"]))

    def test_stale_artifact_hash_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir, rows = self.build_run(td)
            rows[0]["envelope"]["raw_refs"][0]["artifact_sha256"] = "0" * 64
            result = check_raw_normalized_equality(run_dir, rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("hash mismatch" in violation["detail"] for violation in result["violations"]))

    def test_scenario_boundary_crossing_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir, rows = self.build_run(td)
            rows[0]["envelope"]["raw_refs"][0]["scenario_id"] = "P-OBSERVE"
            result = check_raw_normalized_equality(run_dir, rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("crosses scenario boundary" in violation["detail"] for violation in result["violations"]))

    def test_normalized_self_citation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir, rows = self.build_run(td)
            raw = {"record_id": "replay:1", "dogfood_evidence_schema_version": "dogfood_evidence.v1", "payload": {"stage_actions": 0, "candidate_id": "c1"}}
            write_jsonl(run_dir / "replay.jsonl", [raw])
            rows[0]["envelope"]["raw_refs"][0]["artifact_sha256"] = sha256_path(run_dir / "replay.jsonl")
            result = check_raw_normalized_equality(run_dir, rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("normalized row, not a raw record" in violation["detail"] for violation in result["violations"]))


class IndependentVisibleCaptureTests(unittest.TestCase):
    RUN_ID = "run-1"
    SCENARIO = "P-ACTION-VISIBLE"
    STIMULUS_HASH = sha256_text("Inspect the leading candidate before opening debug UI.")

    def manifest(self) -> dict:
        return {"run_id": self.RUN_ID, "stimuli": [{"scenario_id": self.SCENARIO, "utf8_sha256": self.STIMULUS_HASH}]}

    def rendered_rows(self, visible: dict) -> list[dict]:
        envelope = {"dogfood_evidence_schema_version": "dogfood_evidence.v1", "scenario_id": self.SCENARIO, "payload": {"visible": visible}}
        return [{"scenario_id": self.SCENARIO, "source": "rendered_view", "payload": envelope["payload"], "label": "rendered_views.jsonl:1", "envelope": envelope}]

    def write_capture(self, run_dir: Path, *, visible: dict, nonce: str | None = None, driver_sha: str | None = None, available: bool = True, external: bool = False) -> None:
        capture_manifest = {
            "dogfood_capture_schema_version": "dogfood_ruler_capture.v1",
            "run_id": self.RUN_ID,
            "driver": {"kind": "browser_capture_driver", "path": str(BROWSER_CAPTURE_PATH), "sha256": driver_sha or sha256_path(BROWSER_CAPTURE_PATH)},
            "browser": {"kind": "headless_browser", "binary": "/usr/bin/true"},
            "available": available, "external": external, "reason": None if available else "no headless browser engine is available on this host",
        }
        manifest_path = run_dir / CAPTURE_MANIFEST_NAME
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(capture_manifest), encoding="utf-8")
        if available:
            row = {"scenario_id": self.SCENARIO, "nonce": nonce or capture_nonce(self.RUN_ID, self.SCENARIO, self.STIMULUS_HASH), "captured_at": "t", "url": "http://127.0.0.1:8787/", "dom_sha256": "0" * 64, "visible": visible}
            write_jsonl(run_dir / CAPTURE_ROWS_NAME, [row])

    def test_agreeing_capture_passes(self) -> None:
        visible = {"candidate-start": "2026-07-11 08:00 PDT", "candidate-duration": "90 min"}
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self.write_capture(run_dir, visible=dict(visible, extra="allowed"))
            result = check_independent_visible_capture(run_dir, self.manifest(), self.rendered_rows(visible))
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["checked_scenarios"], 1)

    def test_planted_rendering_disagrees_with_independent_capture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self.write_capture(run_dir, visible={"candidate-start": "2026-07-11 01:00 PDT"})
            result = check_independent_visible_capture(run_dir, self.manifest(), self.rendered_rows({"candidate-start": "2026-07-11 08:00 PDT"}))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("disagrees with independent DOM capture" in violation["detail"] for violation in result["violations"]))

    def test_cross_run_nonce_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            wrong = capture_nonce("another-run", self.SCENARIO, self.STIMULUS_HASH)
            self.write_capture(run_dir, visible={"candidate-start": "x"}, nonce=wrong)
            result = check_independent_visible_capture(run_dir, self.manifest(), self.rendered_rows({"candidate-start": "x"}))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("does not bind this run/stimulus" in violation["detail"] for violation in result["violations"]))

    def test_unbound_driver_hash_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self.write_capture(run_dir, visible={"candidate-start": "x"}, driver_sha="1" * 64)
            result = check_independent_visible_capture(run_dir, self.manifest(), self.rendered_rows({"candidate-start": "x"}))
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("does not bind the ruler-owned browser driver" in violation["detail"] for violation in result["violations"]))

    def test_missing_capture_without_preregistration_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = check_independent_visible_capture(Path(td), self.manifest(), self.rendered_rows({"candidate-start": "x"}))
        self.assertEqual(result["status"], "fail")

    def test_preregistered_external_unavailability_holds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self.write_capture(run_dir, visible={}, available=False, external=True)
            result = check_independent_visible_capture(run_dir, self.manifest(), self.rendered_rows({"candidate-start": "x"}))
        self.assertEqual(result["status"], "hold")
        self.assertTrue(result["external_unavailable"])

    def test_internal_unavailability_fails_never_holds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self.write_capture(run_dir, visible={}, available=False, external=False)
            result = check_independent_visible_capture(run_dir, self.manifest(), self.rendered_rows({"candidate-start": "x"}))
        self.assertEqual(result["status"], "fail")

    def test_undeclared_visible_state_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            self.write_capture(run_dir, visible={"candidate-start": "x"})
            rows = self.rendered_rows({"candidate-start": "x"})
            del rows[0]["envelope"]["payload"]["visible"]
            result = check_independent_visible_capture(run_dir, self.manifest(), rows)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("declares no visible state" in violation["detail"] for violation in result["violations"]))

    def test_no_rendered_views_is_vacuously_admissible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = check_independent_visible_capture(Path(td), self.manifest(), [])
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["checked_scenarios"], 0)


class DerivedAdmissibilityTests(unittest.TestCase):
    def test_any_check_failure_blocks_binding_eligibility(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            write_jsonl(run_dir / "replay.jsonl", [{"record_id": "b", "causal_parent_id": "missing", "payload": {}}])
            result = derive_admissibility(run_dir, {"run_id": "run-1", "stimuli": []}, [])
        self.assertEqual(result["prerequisite_id"], "E-REPLAY-INTEGRITY")
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["binding_eligible"])
        self.assertEqual(result["instrument"]["required_invariant_ids"], ["I3"])

    def test_clean_run_is_binding_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            write_jsonl(run_dir / "replay.jsonl", [{"record_id": "a", "causal_parent_id": None, "payload": {}}])
            result = derive_admissibility(run_dir, {"run_id": "run-1", "stimuli": []}, [])
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["binding_eligible"])
        for name in ("replay_checker", "admissibility_module", "browser_capture"):
            self.assertTrue(Path(result["instrument"][name]["path"]).is_file())

    def test_d0_is_binding_eligible_without_product_replay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = derive_admissibility(Path(td), {"run_id": "run-1", "cell": "D0", "stimuli": []}, [])
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["binding_eligible"])
        self.assertFalse(result["checks"]["replay_parent_resolution"]["replay_required"])


class SemanticDOMExtractionTests(unittest.TestCase):
    def test_extracts_normalized_testid_text(self) -> None:
        html = (
            '<main><section data-testid="candidate-card">'
            '<h2 data-testid="candidate-title">Protect  Deep\n Work</h2>'
            '<span data-testid="candidate-start">2026-07-11 08:00 PDT</span>'
            "<p>uninstrumented prose</p></section></main>"
        )
        visible = extract_semantic_dom(html)
        self.assertEqual(visible["candidate-title"], "Protect Deep Work")
        self.assertEqual(visible["candidate-start"], "2026-07-11 08:00 PDT")
        self.assertEqual(visible["candidate-card"], "Protect Deep Work 2026-07-11 08:00 PDT uninstrumented prose")
        self.assertNotIn("uninstrumented", visible.get("candidate-title", ""))


if __name__ == "__main__":
    unittest.main()
