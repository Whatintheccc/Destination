from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from evals.p13_ruler.core import (
    APP_ROOT,
    GIT_ROOT,
    build_binding_manifest,
    build_instrument_bundle,
    build_loc_report,
    canonical_json_bytes,
    sha256_bytes,
    validate_instrument_bundle,
    verify_binding_manifest,
)


class P13RulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        (APP_ROOT / "runs").mkdir(parents=True, exist_ok=True)

    def _keys(self, root: Path) -> tuple[Path, Path]:
        private_key = root / "signing-private.pem"
        public_key = root / "signing-public.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(private_key), "-pubout", "-out", str(public_key)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return private_key, public_key

    def _schema(self, name: str) -> dict:
        schema = json.loads((APP_ROOT / "contracts" / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        return schema

    def _validate_schema(self, name: str, payload: dict) -> None:
        validator = Draft202012Validator(self._schema(name), format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
        self.assertEqual([], [error.message for error in errors])

    def _scope(self, path: Path) -> Path:
        payload = {
            "wave_scope_schema_version": "p13_wave_scope.v1",
            "declared_paths": ["calendar-pilot-p12/src/calendar_pilot/frontend/**"],
            "declared": {
                "actions": ["*"],
                "backends": [],
                "surfaces": ["frontend"],
                "instruments": [],
                "control_planes": [],
            },
            "required_scenarios": ["target.reducer_projection"],
            "old_producer": {"identity": "old", "command": ["python3", "old.py"]},
            "new_producer": {"identity": "new", "command": ["python3", "new.py"]},
            "live_legs": [],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return path

    def _bundle(self, root: Path, public_key: Path) -> tuple[dict, Path]:
        bundle = build_instrument_bundle(
            verification_key=public_key,
            artifact_config=APP_ROOT / "configs/p13_instrument_artifacts.json",
            require_clean=False,
        )
        path = root / "instrument.json"
        path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return bundle, path

    def test_loc_report_freezes_files_counts_and_delta(self):
        report = build_loc_report()
        self._validate_schema("p13_loc_report.schema.json", report)
        wave_scope = json.loads((APP_ROOT / "experiments/templates/p13_wave_scope.template.json").read_text(encoding="utf-8"))
        self._validate_schema("p13_wave_scope.schema.json", wave_scope)
        self.assertEqual(report["decision"], "pass")
        self.assertGreater(report["total_lines"], 10_000)
        self.assertEqual(report["file_count"], len(report["files"]))
        self.assertEqual(report["total_lines"], sum(row["lines"] for row in report["files"]))
        self.assertFalse(report["untracked_source_files"])
        self.assertEqual(len(report["file_list_sha256"]), 64)

        before = deepcopy(report)
        before["files"][0]["lines"] -= 1
        before["total_lines"] -= 1
        after = build_loc_report(before=before)
        self.assertEqual(after["delta"]["delta_lines"], 1)
        self.assertEqual(after["delta"]["changed_files"][0]["delta_lines"], 1)

    def test_instrument_bundle_is_content_addressed_and_detects_tamper(self):
        with tempfile.TemporaryDirectory(dir=APP_ROOT / "runs") as td:
            root = Path(td)
            _, public_key = self._keys(root)
            bundle, _ = self._bundle(root, public_key)
            self._validate_schema("p13_instrument_bundle.schema.json", bundle)
            validate_instrument_bundle(bundle, verification_key=public_key)
            self.assertTrue(any(row["path"].endswith("p13_ownership_map.json") for row in bundle["artifacts"]))

            tampered = deepcopy(bundle)
            tampered["artifacts"][0]["sha256"] = "0" * 64
            tampered_without_hash = dict(tampered)
            tampered_without_hash.pop("bundle_sha256")
            tampered["bundle_sha256"] = sha256_bytes(canonical_json_bytes(tampered_without_hash))
            with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
                validate_instrument_bundle(tampered, verification_key=public_key)

    def test_signed_manifest_passes_declared_diff_and_fails_scope_tamper(self):
        with tempfile.TemporaryDirectory(dir=APP_ROOT / "runs") as td:
            root = Path(td)
            private_key, public_key = self._keys(root)
            _, bundle_path = self._bundle(root, public_key)
            scope_path = self._scope(root / "scope.json")
            now = datetime(2026, 7, 9, 20, 0, tzinfo=timezone.utc)
            manifest = build_binding_manifest(
                wave="p13-ruler-test",
                change_class="ruler",
                scope_path=scope_path,
                instrument_bundle_path=bundle_path,
                ownership_map_path=APP_ROOT / "configs/p13_ownership_map.json",
                signing_key=private_key,
                verification_key=public_key,
                now=now,
                require_clean=False,
            )
            self._validate_schema("p13_binding_manifest.schema.json", manifest)
            report = verify_binding_manifest(
                manifest,
                verification_key=public_key,
                changed_paths=["calendar-pilot-p12/src/calendar_pilot/frontend/session.py"],
                now=now + timedelta(minutes=1),
            )
            self._validate_schema("p13_binding_manifest_verification.schema.json", report)
            self.assertEqual(report["decision"], "pass")

            undeclared = verify_binding_manifest(
                manifest,
                verification_key=public_key,
                changed_paths=["calendar-pilot-p12/src/calendar_pilot/providers/base.py"],
                now=now + timedelta(minutes=1),
            )
            self.assertEqual(undeclared["decision"], "fail")
            self.assertIn("undeclared_path", {row["code"] for row in undeclared["failures"]})
            self.assertIn("undeclared_affectedness", {row["code"] for row in undeclared["failures"]})

            changed_manifest = deepcopy(manifest)
            changed_manifest["declared_scope"]["paths"].append("calendar-pilot-p12/src/calendar_pilot/providers/**")
            signature_failure = verify_binding_manifest(
                changed_manifest,
                verification_key=public_key,
                changed_paths=[],
                now=now + timedelta(minutes=1),
            )
            self.assertIn("manifest_signature", {row["code"] for row in signature_failure["failures"]})

    def test_manifest_expiry_blocks(self):
        with tempfile.TemporaryDirectory(dir=APP_ROOT / "runs") as td:
            root = Path(td)
            private_key, public_key = self._keys(root)
            _, bundle_path = self._bundle(root, public_key)
            scope_path = self._scope(root / "scope.json")
            now = datetime(2026, 7, 9, 20, 0, tzinfo=timezone.utc)
            manifest = build_binding_manifest(
                wave="p13-expiry-test",
                change_class="ruler",
                scope_path=scope_path,
                instrument_bundle_path=bundle_path,
                ownership_map_path=APP_ROOT / "configs/p13_ownership_map.json",
                signing_key=private_key,
                verification_key=public_key,
                expires_in_hours=1,
                now=now,
                require_clean=False,
            )
            report = verify_binding_manifest(
                manifest,
                verification_key=public_key,
                changed_paths=[],
                now=now + timedelta(hours=2),
            )
            self.assertEqual(report["decision"], "fail")
            self.assertIn("manifest_expired", {row["code"] for row in report["failures"]})


if __name__ == "__main__":
    unittest.main()
