import unittest
import json
from pathlib import Path

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.environment.taxonomy import CanonicalIntent, normalize_intent, taxonomy_health
from calendar_pilot.types import RawCalendarObservation, UserBiography


ROOT = Path(__file__).resolve().parents[1]


class TaxonomyTests(unittest.TestCase):
    def test_exact_match(self):
        result = normalize_intent("create_prep_block")

        self.assertEqual(result["intent"], "create_prep_block")
        self.assertEqual(result["matched_by"], "exact")

    def test_keyword_match_normalizes_prose(self):
        result = normalize_intent("Create a prep block before the client call")

        self.assertEqual(result["intent"], "create_prep_block")
        self.assertEqual(result["matched_by"], "keyword")
        self.assertEqual(result["intent_raw"], "Create a prep block before the client call")

    def test_fallback_to_other(self):
        result = normalize_intent("write a haiku about my week")

        self.assertEqual(result["intent"], CanonicalIntent.OTHER.value)
        self.assertEqual(result["matched_by"], "fallback")

    def test_every_canonical_value_round_trips_exactly(self):
        for intent in CanonicalIntent:
            self.assertEqual(normalize_intent(intent.value)["intent"], intent.value)

    def test_taxonomy_health_other_rate(self):
        candidates = [
            {"intent": "create_prep_block", "intent_matched_by": "keyword"},
            {"intent": "other", "intent_matched_by": "fallback"},
        ]

        health = taxonomy_health(candidates)

        self.assertAlmostEqual(health["other_rate"], 0.5)
        self.assertEqual(health["matched_by"], {"keyword": 1, "fallback": 1})

    def test_heuristic_policy_candidates_carry_taxonomy_provenance(self):
        observation = RawCalendarObservation.from_dict(json.loads((ROOT / "data/sample_calendar.json").read_text()))
        biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text()))

        candidates = DiffusionGemmaPolicy().generate_candidates(observation, biography)

        self.assertTrue(candidates)
        self.assertNotIn("unknown", {candidate.intent_matched_by for candidate in candidates})
        health = taxonomy_health([candidate.to_dict() for candidate in candidates])
        self.assertEqual(health["other_rate"], 0.0)
