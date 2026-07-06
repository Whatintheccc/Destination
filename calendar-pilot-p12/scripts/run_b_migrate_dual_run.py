#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.frontend.projector import FrontendProjector
from calendar_pilot.frontend.session import DogfoodSessionState


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def _git_sha() -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _path_values(data: Any, path: str) -> list[Any]:
    values = [data]
    if not path:
        return values
    for part in path.split("."):
        next_values: list[Any] = []
        is_list = part.endswith("[]")
        key = part[:-2] if is_list else part
        for value in values:
            if isinstance(value, dict):
                child = value.get(key)
            else:
                child = None
            if is_list:
                if isinstance(child, list):
                    next_values.extend(child)
            else:
                next_values.append(child)
        values = next_values
    return values


def _single(data: Any, path: str) -> Any:
    values = _path_values(data, path)
    return values[0] if values else None


def _assertion_result(assertion: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    mode = str(assertion.get("mode", "equal"))
    before_path = str(assertion.get("before_path", ""))
    after_path = str(assertion.get("after_path", ""))
    if mode == "equal_set":
        before_value = sorted({str(value) for value in _path_values(before, before_path) if value not in {None, ""}})
        after_value = sorted({str(value) for value in _path_values(after, after_path) if value not in {None, ""}})
        ok = before_value == after_value
    elif mode == "non_empty":
        before_value = _path_values(before, before_path)
        after_value = _path_values(after, after_path)
        ok = bool(before_value) and bool(after_value)
    else:
        before_value = _single(before, before_path)
        after_value = _single(after, after_path)
        ok = before_value == after_value
    return {
        "name": assertion.get("name", before_path),
        "mode": mode,
        "before_path": before_path,
        "after_path": after_path,
        "before_value": before_value,
        "after_value": after_value,
        "status": "pass" if ok else "fail",
    }


def _frontend_fixture(artifacts_dir: Path) -> tuple[Path, Path]:
    with tempfile.TemporaryDirectory() as td:
        session = DogfoodSessionState(run_dir=Path(td))
        planned = session.create_plan("Make next week less chaotic")
        candidate_id = planned["chat"]["candidate_cards"][0]["candidate_id"]
        session.candidate_action(candidate_id, "stage")
        before = session.snapshot()
        after = FrontendProjector(session).view()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    before_path = artifacts_dir / "before_session_snapshot.json"
    after_path = artifacts_dir / "after_view_state.json"
    atomic_write_json(before_path, before)
    atomic_write_json(after_path, after)
    return before_path, after_path


def build_report(
    *,
    before_path: Path | None = None,
    after_path: Path | None = None,
    assertions_path: Path,
    artifacts_dir: Path,
) -> dict[str, Any]:
    if before_path is None or after_path is None:
        before_path, after_path = _frontend_fixture(artifacts_dir)
    assertions_payload = _read_json(assertions_path)
    before = _read_json(before_path)
    after = _read_json(after_path)
    assertion_results = [_assertion_result(assertion, before, after) for assertion in assertions_payload.get("assertions", [])]
    decision = "pass" if assertion_results and all(row["status"] == "pass" for row in assertion_results) else "hold"
    return {
        "b_migrate_report_schema_version": "b_migrate_report.v1",
        "git_sha": _git_sha(),
        "assertion_set": {
            "path": str(assertions_path),
            "assertion_set_id": assertions_payload.get("assertion_set_id"),
        },
        "before_artifact": str(before_path),
        "after_artifact": str(after_path),
        "assertions": assertion_results,
        "decision": decision,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-json", default="")
    parser.add_argument("--after-json", default="")
    parser.add_argument("--assertions", default="experiments/configs/b_migrate_frontend_view_state.json")
    parser.add_argument("--artifacts-dir", default="runs/b_migrate_artifacts")
    parser.add_argument("--out", default="runs/b_migrate_report.json")
    args = parser.parse_args()
    out = _resolve(args.out)
    payload = build_report(
        before_path=_resolve(args.before_json) if args.before_json else None,
        after_path=_resolve(args.after_json) if args.after_json else None,
        assertions_path=_resolve(args.assertions),
        artifacts_dir=_resolve(args.artifacts_dir),
    )
    atomic_write_json(out, payload)
    print(json.dumps({"ok": payload["decision"] == "pass", "decision": payload["decision"], "out": str(out)}, indent=2))


if __name__ == "__main__":
    main()
