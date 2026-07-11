#!/usr/bin/env python3
"""Ruler-owned semantic DOM capture for dogfood runs.

This driver is instrument code, not product code. It launches a real headless
browser engine against the running app, binds each capture to the run/scenario
stimulus nonce, and retains the semantic DOM state the operator could actually
see. The product cannot substitute its own projection for this capture: the
evaluator re-derives the nonce from the bound run manifest and compares
product-reported visible state against these rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

BROWSER_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "chromium",
    "google-chrome",
)
CAPTURE_DIR_NAME = "ruler_capture"
CAPTURE_MANIFEST_NAME = "capture_manifest.json"
CAPTURE_ROWS_NAME = "semantic_dom.jsonl"


class _SemanticDOMParser(HTMLParser):
    """Extracts data-testid -> normalized visible text (textContent semantics)."""

    VOID_ELEMENTS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[str | None] = []
        self._texts: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        testid = next((value for name, value in attrs if name == "data-testid" and value), None)
        if testid:
            self._texts.setdefault(testid, [])
        if tag.lower() not in self.VOID_ELEMENTS:
            self._stack.append(testid)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() not in self.VOID_ELEMENTS and self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        for testid in self._stack:
            if testid:
                self._texts[testid].append(data)

    def semantic(self) -> dict[str, str]:
        return {testid: " ".join(" ".join(parts).split()) for testid, parts in self._texts.items()}


def extract_semantic_dom(dom_html: str) -> dict[str, str]:
    parser = _SemanticDOMParser()
    parser.feed(dom_html)
    return parser.semantic()


def _capture_nonce(run_id: str, scenario_id: str, stimulus_utf8_sha256: str) -> str:
    return hashlib.sha256(f"{run_id}\n{scenario_id}\n{stimulus_utf8_sha256}".encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_browser(explicit: str | None) -> str | None:
    candidates = [explicit] if explicit else [os.environ.get("CALENDAR_PILOT_CAPTURE_BROWSER"), *BROWSER_CANDIDATES]
    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).is_file():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _dump_dom(browser: str, url: str, timeout_seconds: int) -> str:
    completed = subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--virtual-time-budget=5000", "--dump-dom", url],
        capture_output=True, text=True, timeout=timeout_seconds, check=True,
    )
    return completed.stdout


def write_capture_manifest(run_dir: Path, *, run_id: str, browser: str | None, available: bool, external: bool = False, reason: str | None = None) -> Path:
    capture_dir = run_dir / CAPTURE_DIR_NAME
    capture_dir.mkdir(parents=True, exist_ok=True)
    driver_path = Path(__file__).resolve()
    payload = {
        "dogfood_capture_schema_version": "dogfood_ruler_capture.v1",
        "run_id": run_id,
        "driver": {"kind": "browser_capture_driver", "path": str(driver_path), "sha256": _sha256_file(driver_path)},
        "browser": {"kind": "headless_browser", "binary": browser},
        "available": available,
        "external": external,
        "reason": reason,
    }
    out = capture_dir / CAPTURE_MANIFEST_NAME
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def write_capture_row(run_dir: Path, *, run_id: str, scenario_id: str, stimulus_utf8_sha256: str, url: str, dom_html: str) -> dict[str, Any]:
    capture_dir = run_dir / CAPTURE_DIR_NAME
    capture_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "scenario_id": scenario_id,
        "nonce": _capture_nonce(run_id, scenario_id, stimulus_utf8_sha256),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "dom_sha256": hashlib.sha256(dom_html.encode("utf-8")).hexdigest(),
        "visible": extract_semantic_dom(dom_html),
    }
    with (capture_dir / CAPTURE_ROWS_NAME).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture ruler-owned semantic DOM state for one dogfood scenario.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--browser", default=None)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    run_id = str(manifest["run_id"])
    stimuli = {str(row["scenario_id"]): str(row["utf8_sha256"]) for row in manifest.get("stimuli", [])}
    if args.scenario not in stimuli:
        raise SystemExit(f"scenario is not bound by this run manifest: {args.scenario}")
    browser = _find_browser(args.browser)
    if browser is None:
        write_capture_manifest(run_dir, run_id=run_id, browser=None, available=False, external=True, reason="no headless browser engine is available on this host")
        raise SystemExit("no headless browser engine found; preregistered external unavailability was recorded")
    url = f"{args.base_url.rstrip('/')}/#dogfood-capture={_capture_nonce(run_id, args.scenario, stimuli[args.scenario])[:16]}"
    dom_html = _dump_dom(browser, url, args.timeout_seconds)
    write_capture_manifest(run_dir, run_id=run_id, browser=browser, available=True)
    row = write_capture_row(run_dir, run_id=run_id, scenario_id=args.scenario, stimulus_utf8_sha256=stimuli[args.scenario], url=url, dom_html=dom_html)
    print(json.dumps({"scenario_id": row["scenario_id"], "nonce": row["nonce"], "visible_keys": sorted(row["visible"])}, indent=2))


if __name__ == "__main__":
    main()
