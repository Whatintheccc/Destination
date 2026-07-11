from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


JSON_DOCUMENTS = {
    "launch_state.before.json": "launch_state_before",
    "launch_state.after.json": "launch_state_after",
    "health.json": "health",
    "session_state.json": "session_state",
    "replay_export.json": "replay_export",
    "provider.before.json": "provider_read",
    "provider.after.json": "provider_after",
    "provider.after_undo.json": "provider_after_undo",
    "process_snapshot.before.json": "process_snapshot_before",
    "process_snapshot.after.json": "process_snapshot_after",
}

JSONL_DOCUMENTS = {
    "rendered_views.jsonl": "rendered_view",
    "ui_actions.jsonl": "ui_action",
    "replay.jsonl": "replay",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[Any]:
    rows: list[Any] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL in {path} line {line_number}: {exc}") from exc
    return rows


class LiveRunAdapter:
    adapter_id = "dogfood_live_run.v1"

    def __init__(self, app_root: Path, run_dir: Path, manifest: dict[str, Any], operator_truth: dict[str, Any]):
        self.app_root = Path(app_root)
        self.run_dir = Path(run_dir)
        self.manifest = manifest
        self.operator_truth = operator_truth
        self.documents: dict[str, Any] = {}
        self.evidence_rows: list[dict[str, Any]] = []
        self.cross_run_artifacts: list[str] = []
        self.artifacts: list[dict[str, str]] = []
        self._load()

    def _record_artifact(self, path: Path, kind: str) -> None:
        self.artifacts.append({"kind": kind, "path": str(path.resolve()), "sha256": sha256(path)})

    def _consider_run_id(self, value: Any, label: str) -> None:
        if isinstance(value, dict) and value.get("run_id") not in {None, self.manifest["run_id"]}:
            self.cross_run_artifacts.append(label)

    def _accept_evidence(self, row: Any, *, default_source: str, label: str) -> None:
        if not isinstance(row, dict):
            return
        if row.get("dogfood_evidence_schema_version") != "dogfood_evidence.v1":
            return
        self._consider_run_id(row, label)
        scenario_id = row.get("scenario_id")
        payload = row.get("payload")
        if not isinstance(scenario_id, str) or not isinstance(payload, dict):
            raise ValueError(f"invalid dogfood evidence envelope in {label}")
        source = str(row.get("source") or default_source)
        self.evidence_rows.append({"scenario_id": scenario_id, "source": source, "payload": payload, "label": label, "envelope": dict(row)})

    def _load(self) -> None:
        for filename, source in JSON_DOCUMENTS.items():
            path = self.run_dir / filename
            if not path.is_file():
                continue
            if path.stat().st_size == 0:
                raise ValueError(f"zero-byte dogfood artifact: {path}")
            payload = _load_json(path)
            self.documents[source] = payload
            self._consider_run_id(payload, filename)
            self._record_artifact(path, source)
            self._accept_evidence(payload, default_source=source, label=filename)
            if isinstance(payload, dict):
                for row in payload.get("dogfood_evidence", []):
                    self._accept_evidence(row, default_source=source, label=filename)
        for filename, source in JSONL_DOCUMENTS.items():
            path = self.run_dir / filename
            if not path.is_file():
                continue
            if path.stat().st_size == 0:
                raise ValueError(f"zero-byte dogfood artifact: {path}")
            self._record_artifact(path, source)
            for index, row in enumerate(_load_jsonl(path), 1):
                self._consider_run_id(row, f"{filename}:{index}")
                self._accept_evidence(row, default_source=source, label=f"{filename}:{index}")
        screenshot_manifest = self.run_dir / "screenshots/manifest.json"
        if screenshot_manifest.is_file():
            if screenshot_manifest.stat().st_size == 0:
                raise ValueError(f"zero-byte dogfood artifact: {screenshot_manifest}")
            payload = _load_json(screenshot_manifest)
            if not isinstance(payload, dict) or payload.get("run_id") != self.manifest["run_id"]:
                raise ValueError("screenshot manifest must bind the exact dogfood run_id")
            self._record_artifact(screenshot_manifest, "screenshot_manifest")
            for index, row in enumerate(payload.get("screenshots", []), 1):
                if not isinstance(row, dict) or not isinstance(row.get("scenario_id"), str):
                    raise ValueError(f"invalid screenshot manifest row {index}")
                image_path = self.run_dir / str(row.get("path", ""))
                if not image_path.resolve().is_relative_to((self.run_dir / "screenshots").resolve()):
                    raise ValueError(f"screenshot escapes run screenshot directory: {image_path}")
                if not image_path.is_file() or image_path.stat().st_size == 0 or sha256(image_path) != row.get("sha256"):
                    raise ValueError(f"screenshot hash mismatch: {image_path}")
                self._record_artifact(image_path, "screenshot")
                self.evidence_rows.append({"scenario_id": row["scenario_id"], "source": "screenshot", "payload": {"path": str(image_path), "sha256": row["sha256"]}, "label": f"screenshots/manifest.json:{index}"})

    def _resolve_bound_artifact(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self.app_root / path

    def instrument_hashes_valid(self) -> bool:
        bound = [self.manifest.get("scenario_set", {}), *self.manifest.get("predicate_artifacts", [])]
        for item in bound:
            path = self._resolve_bound_artifact(str(item.get("path", "")))
            if not path.is_file() or sha256(path) != item.get("sha256"):
                return False
        return True

    def build_hashes_valid(self) -> bool:
        bundle = Path(str(self.manifest.get("build", {}).get("app_bundle_path", "")))
        app = bundle / "Contents/MacOS/CalendarPilot"
        bridge = bundle / "Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge"
        return (
            app.is_file() and bridge.is_file()
            and sha256(app) == self.manifest.get("build", {}).get("app_sha256")
            and sha256(bridge) == self.manifest.get("build", {}).get("bridge_sha256")
        )

    def collect(self, scenario: dict[str, Any]) -> dict[str, Any]:
        scenario_id = str(scenario["scenario_id"])
        records: dict[str, list[dict[str, Any]]] = {}
        labels: list[str] = []
        for row in self.evidence_rows:
            if row["scenario_id"] != scenario_id:
                continue
            records.setdefault(row["source"], []).append(row["payload"])
            labels.append(row["label"])
        global_sources = {"run_manifest", "operator_truth"}
        for source in ("launch_state_before", "launch_state_after", "health", "process_snapshot_before", "process_snapshot_after", "provider_read", "provider_after", "provider_after_undo"):
            if source in self.documents:
                global_sources.add(source)
        present_sources = sorted(global_sources | set(records))
        prerequisite: dict[str, Any] = {}
        for row in records.get("prerequisite", []):
            if row.get("available") is False:
                prerequisite = row
                break
        generated = {"dogfood_eval_report.json", "SHA256SUMS"}
        missing_required_artifacts = [
            name for name in self.manifest.get("required_artifacts", [])
            if name not in generated and not (self.run_dir / name).is_file()
        ]
        empty_required_artifacts = [
            name for name in self.manifest.get("required_artifacts", [])
            if name not in generated and (self.run_dir / name).is_file() and (self.run_dir / name).stat().st_size == 0
        ]
        return {
            "scenario_id": scenario_id,
            "manifest": self.manifest,
            "operator_truth": self.operator_truth,
            "launch_state": self.documents.get("launch_state_before", {}),
            "health": self.documents.get("health", {}),
            "process_snapshot": self.documents.get("process_snapshot_before", {}),
            "records": records,
            "scenario_record_count": sum(len(rows) for rows in records.values()),
            "required_sources": list(scenario.get("required_sources", [])),
            "present_sources": present_sources,
            "source_labels": labels,
            "cross_run_artifacts": sorted(set(self.cross_run_artifacts)),
            "instrument_hashes_valid": self.instrument_hashes_valid(),
            "build_hashes_valid": self.build_hashes_valid(),
            "missing_required_artifacts": missing_required_artifacts,
            "empty_required_artifacts": empty_required_artifacts,
            "external_prerequisite": prerequisite,
        }
