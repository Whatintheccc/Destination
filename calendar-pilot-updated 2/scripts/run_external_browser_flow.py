
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]


def run_live_browser_check(
    base_url: str,
    artifact_dir: str | Path,
    *,
    allow_skip: bool = False,
    expected_runtime_mode: str = "fixture",
    expected_runtime_label: str | None = None,
) -> None:
    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)
    if allow_skip and os.environ.get("CALENDAR_PILOT_ALLOW_BROWSER_SKIP") == "1":
        print("live browser check skipped by CALENDAR_PILOT_ALLOW_BROWSER_SKIP=1")
        return
    node = shutil.which("node")
    chrome = os.environ.get("CHROME_PATH") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    cdp_script = ROOT / "scripts" / "browser_cdp_e2e.mjs"
    expected_runtime_label = expected_runtime_label or ("Swift IPC mode" if expected_runtime_mode == "swift_ipc" else "Fixture mode")
    if node and Path(chrome).exists():
        env = os.environ.copy()
        env["CALENDAR_PILOT_EXPECTED_RUNTIME_MODE"] = expected_runtime_mode
        env["CALENDAR_PILOT_EXPECTED_RUNTIME_LABEL"] = expected_runtime_label
        timeout = int(env.get("CALENDAR_PILOT_BROWSER_PROCESS_TIMEOUT", "120"))
        subprocess.run([node, str(cdp_script), base_url, str(artifact_path)], cwd=ROOT, env=env, check=True, timeout=timeout)
        return
    try:
        from playwright.sync_api import expect, sync_playwright
    except Exception as exc:
        raise AssertionError(f"rendered browser check requires Chrome+Node or Playwright; {exc}") from exc

    screenshot_path = artifact_path / "browser_failure.png"
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1360, "height": 900})
            page.goto(base_url, wait_until="networkidle")
            expect(page.get_by_test_id("chat-transcript")).to_be_visible()
            expect(page.get_by_test_id("runtime-chip")).to_contain_text(expected_runtime_label)
            page.get_by_test_id("goal-input").fill("Make next week less chaotic")
            page.get_by_test_id("send-goal").click()
            expect(page.get_by_test_id("candidate-card").first).to_be_visible(timeout=10000)
            page.get_by_test_id("stage-candidate").first.click()
            expect(page.get_by_test_id("receipt-card").first).to_be_visible(timeout=10000)
            page.get_by_test_id("commit-candidate").first.click()
            expect(page.get_by_test_id("undo-action").first).to_be_visible(timeout=10000)
            page.get_by_test_id("undo-action").first.click()
            expect(page.get_by_text("Undo requested")).to_be_visible(timeout=10000)
            page.get_by_test_id("feedback-useful").first.click()
            expect(page.get_by_text("Feedback captured")).to_be_visible(timeout=10000)
            page.locator("#tab-replay").click()
            page.get_by_test_id("replay-export").click()
            expect(page.locator("#replay-json")).to_contain_text("records", timeout=10000)
            page.locator("#tab-profile").click()
            page.locator("#profile-correction").fill("Prefer planning blocks before lunch.")
            page.locator("#propose-profile").click()
            expect(page.get_by_text("Profile repair drafted")).to_be_visible(timeout=10000)
            page.locator("#profile-correction").fill("Prefer planning blocks before lunch.")
            page.locator("#apply-profile").click()
            expect(page.get_by_text("Profile repair applied")).to_be_visible(timeout=10000)
            page.locator("#tab-authority").click()
            page.locator("#authority-tier").fill("0")
            page.locator("#authority-scopes").fill("recommend, stage")
            page.locator("#save-authority").click()
            expect(page.locator("#authority-chip")).to_contain_text("Tier 0", timeout=10000)
            candidate_count = page.get_by_test_id("candidate-card").count()
            page.get_by_test_id("goal-input").fill("Try a low-authority commit")
            page.get_by_test_id("send-goal").click()
            expect(page.get_by_text("Try a low-authority commit")).to_be_visible(timeout=10000)
            page.wait_for_function("(count) => document.querySelectorAll('[data-testid=\"candidate-card\"]').length > count", candidate_count)
            page.get_by_test_id("commit-candidate").nth(candidate_count).click()
            expect(page.locator(".explain-denial").first).to_be_visible(timeout=10000)
            page.locator(".explain-denial").first.click()
            expect(page.get_by_text("Why Swift denied it")).to_be_visible(timeout=10000)
            page.locator("#tab-self-play").click()
            page.get_by_test_id("run-self-play").click()
            expect(page.get_by_text("Self-play release gate")).to_be_visible(timeout=10000)
            browser_replay = api_get(base_url, "/api/replay/export")
            if not browser_replay.get("records"):
                raise AssertionError("browser replay export was empty before reset")
            if browser_replay.get("runtime", {}).get("runtime_mode") != expected_runtime_mode:
                raise AssertionError(f"browser replay export did not include {expected_runtime_mode} runtime provenance")
            (artifact_path / "browser_replay_export.json").write_text(json.dumps(browser_replay, indent=2, sort_keys=True), encoding="utf-8")
            page.locator("#tab-debug").click()
            page.locator("#reset-fixture").click()
            expect(page.get_by_text("Reset complete")).to_be_visible(timeout=10000)
            page.screenshot(path=str(artifact_path / "browser_success.png"), full_page=True)
        except Exception:
            if browser is not None:
                page.screenshot(path=str(screenshot_path), full_page=True)
            raise
        finally:
            if browser is not None:
                browser.close()


def api_get(base_url: str, path: str) -> dict[str, Any]:
    with urlopen(f"{base_url}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_external_browser_flow.py <base-url> <artifact-dir>")
    run_live_browser_check(sys.argv[1], sys.argv[2])
