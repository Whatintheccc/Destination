#!/usr/bin/env python3
"""Frontend dogfood E2E.

The canonical path starts the real Python frontend server and drives the HTTP
API that the browser uses. When Playwright and a usable browser are available,
the script also drives the rendered UI against that same live server.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "browser_e2e"
ARTIFACT_DIR = RUN_DIR / "artifacts"


def main() -> None:
    shutil.rmtree(RUN_DIR, ignore_errors=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        assert_static_shell()
        with LiveServer() as server:
            result = run_live_api_loop(server.base_url)
            write_artifact("latest_state.json", result["state"])
            write_artifact("replay_export.json", result["replay_export"])
            write_artifact("dogfood_bug_report.json", {
                "summary": "CalendarPilot browser dogfood replay export",
                "base_url": server.base_url,
                "session_id": result["replay_export"].get("session_id"),
                "replay_summary": result["replay_export"].get("summary"),
                "artifact_files": ["latest_state.json", "replay_export.json", "server.log"],
            })
            run_optional_live_browser_check(server.base_url)
    except Exception as exc:
        (ARTIFACT_DIR / "failure.txt").write_text(str(exc), encoding="utf-8")
        raise
    print(f"browser e2e passed; artifacts: {ARTIFACT_DIR}")


class LiveServer:
    def __init__(self) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.log_path = ARTIFACT_DIR / "server.log"
        self.log_file = None
        self.process: subprocess.Popen[str] | None = None

    def __enter__(self) -> "LiveServer":
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        self.log_file = self.log_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "calendar_pilot.app",
                "frontend",
                "--serve",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--run-dir",
                str(RUN_DIR / "server_state"),
            ],
            cwd=ROOT,
            env=env,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.wait_until_ready()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log_file is not None:
            self.log_file.close()

    def wait_until_ready(self) -> None:
        deadline = time.time() + 10
        last_error: Exception | None = None
        while time.time() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise AssertionError(f"server exited early with code {self.process.returncode}; see {self.log_path}")
            try:
                api_get(self.base_url, "/api/state")
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.1)
        raise AssertionError(f"server did not become ready: {last_error}; see {self.log_path}")


def assert_static_shell() -> None:
    html = (ROOT / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "static" / "app.js").read_text(encoding="utf-8")
    required_html = [
        'data-testid="chat-transcript"',
        'data-testid="goal-input"',
        'data-testid="send-goal"',
        'data-testid="inspector-toggle"',
        'id="tab-replay"',
        'id="inspector-content"',
    ]
    for marker in required_html:
        if marker not in html:
            raise AssertionError(f"missing frontend marker: {marker}")
    required_js = [
        "/api/plans",
        "stage-candidate",
        "commit-candidate",
        "feedback-useful",
        "replay-export",
        "/api/profile/patch/propose",
        "/api/self-play",
        "/api/authority",
    ]
    for marker in required_js:
        if marker not in js:
            raise AssertionError(f"missing frontend flow marker: {marker}")


def run_live_api_loop(base_url: str) -> dict[str, Any]:
    state = api_get(base_url, "/api/state")
    if "session" not in state:
        raise AssertionError("/api/state did not return session state")

    planned = api_post(base_url, "/api/plans", {"goal": "Make next week less chaotic", "authority_tier": 3})
    cards = planned.get("chat", {}).get("candidate_cards", [])
    if not cards:
        raise AssertionError("/api/plans did not produce candidate cards")
    candidate_id = cards[0]["candidate_id"]

    simulated = api_post(base_url, f"/api/candidates/{candidate_id}/simulate", {})
    if "simulated" not in json.dumps(simulated):
        raise AssertionError("simulate did not return visible simulated state")

    staged = api_post(base_url, f"/api/candidates/{candidate_id}/stage", {})
    staged_receipt = staged["action_queue"][-1]["receipt_id"]
    confirmed = api_post(base_url, f"/api/receipts/{staged_receipt}/confirm", {})
    rollback = next((a.get("rollback_handle_id") for a in confirmed["action_queue"] if a.get("rollback_handle_id")), None)
    if not rollback:
        raise AssertionError("commit did not produce rollback handle")
    receipt_id = next(a["receipt_id"] for a in confirmed["action_queue"] if a.get("rollback_handle_id") == rollback)

    feedback = api_post(base_url, "/api/feedback", {"receipt_id": receipt_id, "feedback": "useful", "reason": "browser e2e"})
    if not feedback["inspector"]["feedback"]:
        raise AssertionError("feedback did not appear in inspector state")

    profile = api_post(base_url, "/api/profile/patch/propose", {"correction": "Prefer planning blocks before lunch."})
    if not profile["inspector"]["profile"]["patch_history"]:
        raise AssertionError("profile proposal did not write patch history")
    api_post(base_url, "/api/profile/patch/apply", {"claim": "planning blocks", "correction": "Prefer planning blocks before lunch.", "confirmed": True})

    denial = api_post(base_url, "/api/denials/explain", {"denied_reason": "required authority tier exceeds Swift-issued grant"})
    if not denial["inspector"]["denials"]:
        raise AssertionError("denial explanation did not write visible history")

    self_play = api_post(base_url, "/api/self-play", {"episodes": 1})
    if not self_play["inspector"]["self_play"]["history"]:
        raise AssertionError("self-play did not write visible history")

    authority = api_post(base_url, "/api/authority", {"authority_tier": 2, "scopes": "recommend, stage, undo", "confirmed": "false"})
    if authority["session"]["authority_tier"] != 2:
        raise AssertionError("authority tier edit did not apply")
    if authority["inspector"]["authority"]["history"][-1]["grant"]["confirmed_by_user"]:
        raise AssertionError("string false confirmed value minted a confirmed grant")

    undone = api_post(base_url, "/api/undo", {"rollback_handle_id": rollback})
    if "Undo requested" not in json.dumps(undone["chat"]["messages"]):
        raise AssertionError("undo journey did not appear in visible state")

    replay = api_get(base_url, "/api/replay")
    if replay["summary"].get("records", 0) < 1:
        raise AssertionError("replay endpoint returned no records")
    replay_export = api_get(base_url, "/api/replay/export")
    if not replay_export.get("records"):
        raise AssertionError("replay export is empty")

    error = api_post(base_url, "/api/not-a-route", {}, expected_status=400)
    if "error" not in error or "state" not in error:
        raise AssertionError("invalid POST did not return error and state")

    reset = api_post(base_url, "/api/reset", {})
    if reset["inspector"]["replay"]["summary"]["records"] != 0:
        raise AssertionError("reset did not clear replay summary")

    return {"state": reset, "replay_export": replay_export}


def run_optional_live_browser_check(base_url: str) -> None:
    if os.environ.get("CALENDAR_PILOT_SKIP_BROWSER") == "1":
        print("live browser check skipped by CALENDAR_PILOT_SKIP_BROWSER=1")
        return
    require_browser = os.environ.get("CALENDAR_PILOT_REQUIRE_BROWSER") == "1"
    node = shutil.which("node")
    chrome = os.environ.get("CHROME_PATH") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    cdp_script = ROOT / "scripts" / "browser_cdp_e2e.mjs"
    if node and Path(chrome).exists():
        try:
            subprocess.run([node, str(cdp_script), base_url, str(ARTIFACT_DIR)], cwd=ROOT, check=True, timeout=60)
            return
        except Exception as exc:
            if require_browser:
                raise
            print(f"live browser CDP check skipped after failure: {exc}")
            return
    try:
        from playwright.sync_api import expect, sync_playwright
    except Exception as exc:
        if require_browser:
            raise
        print(f"live browser check skipped: Playwright unavailable ({exc})")
        return

    screenshot_path = ARTIFACT_DIR / "browser_failure.png"
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1360, "height": 900})
            page.goto(base_url, wait_until="networkidle")
            expect(page.get_by_test_id("chat-transcript")).to_be_visible()
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
            page.get_by_test_id("goal-input").fill("Try a low-authority commit")
            page.get_by_test_id("send-goal").click()
            expect(page.get_by_test_id("candidate-card").first).to_be_visible(timeout=10000)
            page.get_by_test_id("commit-candidate").first.click()
            expect(page.locator(".explain-denial").first).to_be_visible(timeout=10000)
            page.locator(".explain-denial").first.click()
            expect(page.get_by_text("Why Swift denied it")).to_be_visible(timeout=10000)
            page.locator("#tab-self-play").click()
            page.get_by_test_id("run-self-play").click()
            expect(page.get_by_text("Self-play release gate")).to_be_visible(timeout=10000)
            page.locator("#tab-debug").click()
            page.locator("#reset-fixture").click()
            expect(page.get_by_text("Reset complete")).to_be_visible(timeout=10000)
        except Exception:
            if browser is not None:
                page.screenshot(path=str(screenshot_path), full_page=True)
            if require_browser:
                raise
            print(f"live browser check skipped after launch failure; screenshot: {screenshot_path}")
        finally:
            if browser is not None:
                browser.close()


def api_get(base_url: str, path: str) -> dict[str, Any]:
    with urlopen(f"{base_url}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def api_post(base_url: str, path: str, body: dict[str, Any], *, expected_status: int = 200) -> dict[str, Any]:
    request = Request(
        f"{base_url}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            if response.status != expected_status:
                raise AssertionError(f"{path} returned {response.status}, expected {expected_status}")
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code != expected_status:
            raise
        return json.loads(exc.read().decode("utf-8"))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def write_artifact(name: str, payload: dict[str, Any]) -> None:
    (ARTIFACT_DIR / name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
