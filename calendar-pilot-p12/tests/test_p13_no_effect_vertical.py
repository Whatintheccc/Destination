from __future__ import annotations

import ast
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest


from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.product_core import AdmissionPreview, EvidenceJournal, run_create_prep_block_vertical
from calendar_pilot.types import RawCalendarObservation, UserBiography
from evals.p13_ruler.wave import compare_b_migrate_artifacts
from scripts.produce_b_migrate_p13_1_new import build_artifact as build_new_artifact
from scripts.produce_b_migrate_p13_1_old import build_artifact as build_old_artifact


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_CORE = ROOT / "src/calendar_pilot/product_core"


def _fixture() -> tuple[RawCalendarObservation, object]:
    observation = RawCalendarObservation.from_dict(
        json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8"))
    )
    biography = UserBiography.from_dict(
        json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8"))
    )
    candidate = next(
        row
        for row in DiffusionGemmaPolicy().generate_candidates(observation, biography)
        if row.intent == "create_prep_block"
    )
    return observation, candidate


class P13NoEffectVerticalTests(unittest.TestCase):
    def test_happy_path_is_cited_deterministic_and_non_dispatchable(self):
        observation, candidate = _fixture()
        first = run_create_prep_block_vertical(
            observation,
            candidate,
            source_authenticated=True,
            received_at=observation.observed_at,
        )
        second = run_create_prep_block_vertical(
            observation,
            candidate,
            source_authenticated=True,
            received_at=observation.observed_at,
        )
        self.assertEqual(first.preview.status, "preview")
        self.assertFalse(first.preview.can_dispatch)
        self.assertIsNotNone(first.preview.projection)
        self.assertEqual(first.preview.projection.evidence_row_ids, first.input_evidence_row_ids)
        self.assertEqual(first.to_observable(), second.to_observable())
        self.assertEqual(first.to_observable()["effects"], {
            "effect_attempts": 0,
            "claims": 0,
            "dispatches": 0,
            "provider_mutations": 0,
        })
        self.assertEqual([event.event_type for event in first.events], [
            "authenticated_observation",
            "frontier_proposal",
            "admission_preview",
        ])

    def test_unauthenticated_stale_and_missing_evidence_are_denied(self):
        observation, candidate = _fixture()
        unauthenticated = run_create_prep_block_vertical(
            observation,
            candidate,
            source_authenticated=False,
            received_at=observation.observed_at,
        )
        self.assertEqual(unauthenticated.preview.status, "denied")
        self.assertIn("observation_source_unauthenticated", unauthenticated.preview.denial_reasons)

        stale = run_create_prep_block_vertical(
            observation,
            candidate,
            source_authenticated=True,
            received_at=observation.observed_at + timedelta(seconds=301),
        )
        self.assertEqual(stale.preview.status, "denied")
        self.assertIn("observation_stale", stale.preview.denial_reasons)

        missing = deepcopy(candidate)
        missing.affected_event_ids = []
        no_parent = run_create_prep_block_vertical(
            observation,
            missing,
            source_authenticated=True,
            received_at=observation.observed_at,
        )
        self.assertEqual(no_parent.preview.status, "denied")
        self.assertIn("missing_parent_event_evidence", no_parent.preview.denial_reasons)

    def test_product_core_has_no_effect_capable_import_or_constructor_surface(self):
        forbidden_imports = {
            "calendar_pilot.providers",
            "calendar_pilot.swift_bridge",
            "calendar_pilot.environment.action_lifecycle",
            "subprocess",
            "socket",
            "urllib",
            "http",
        }
        imported: set[str] = set()
        for path in PRODUCT_CORE.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
        self.assertFalse({name for name in imported if any(name == root or name.startswith(root + ".") for root in forbidden_imports)})
        fields = set(AdmissionPreview.__dataclass_fields__)
        self.assertTrue(fields.isdisjoint({
            "ticket",
            "ticket_id",
            "signature",
            "nonce",
            "grant",
            "provider",
            "credential",
            "idempotency_key",
        }))

    def test_journal_is_append_only_and_rejects_duplicate_identity(self):
        journal = EvidenceJournal()
        event = journal.append(
            row_id="row:one",
            event_type="fixture",
            occurred_at="2026-07-10T00:00:00Z",
            payload={"value": 1},
        )
        self.assertEqual(journal.events, (event,))
        self.assertFalse(hasattr(journal, "delete"))
        self.assertFalse(hasattr(journal, "update"))
        with self.assertRaisesRegex(ValueError, "duplicate Journal row_id"):
            journal.append(
                row_id="row:one",
                event_type="fixture",
                occurred_at="2026-07-10T00:00:00Z",
                payload={"value": 2},
            )

    def test_independent_old_and_new_producers_match_protected_observables(self):
        old = build_old_artifact()
        new = build_new_artifact()
        manifest = {
            "manifest_id": "test:p13.1",
            "old_producer": {"b_migrate": old["producer"] | {"command": old["producer"]["bound_command"]}},
            "new_producer": {"b_migrate": new["producer"] | {"command": new["producer"]["bound_command"]}},
        }
        manifest["old_producer"]["b_migrate"].pop("bound_command")
        manifest["new_producer"]["b_migrate"].pop("bound_command")
        with tempfile.TemporaryDirectory() as td:
            old_path = Path(td) / "old.json"
            new_path = Path(td) / "new.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            new_path.write_text(json.dumps(new), encoding="utf-8")
            report = compare_b_migrate_artifacts(
                before_path=old_path,
                after_path=new_path,
                assertions_path=ROOT / "experiments/configs/b_migrate_create_prep_block_p13_1.json",
                manifest=manifest,
            )
        self.assertEqual(report["decision"], "pass", report["failures"])
        self.assertNotEqual(old["producer"]["producer_id"], new["producer"]["producer_id"])


if __name__ == "__main__":
    unittest.main()
