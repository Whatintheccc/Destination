#!/usr/bin/env python3
"""Chat-first frontend E2E smoke.

The primary path is deterministic and CI-safe: it verifies the static chat shell
contains the product affordances, then drives the same API/session loop the
browser uses. Set CALENDAR_PILOT_REAL_BROWSER=1 on a machine with a usable
Playwright browser to run an additional rendered-browser check.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.frontend.session import DogfoodSessionState  # noqa: E402


def main() -> None:
    assert_static_chat_shell()
    run_fixture_api_loop()
    if os.environ.get("CALENDAR_PILOT_REAL_BROWSER") == "1":
        run_optional_browser_check()
    print("browser e2e passed")


def assert_static_chat_shell() -> None:
    html = (ROOT / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "static" / "app.js").read_text(encoding="utf-8")
    required = [
        'data-testid="chat-transcript"',
        'data-testid="goal-input"',
        'data-testid="send-goal"',
        'data-testid="inspector-toggle"',
        'id="tab-replay"',
        'id="inspector-content"',
    ]
    for marker in required:
        if marker not in html:
            raise AssertionError(f"missing chat shell marker: {marker}")
    for marker in ["/api/plans", "stage-candidate", "commit-candidate", "feedback-useful", "replay-export"]:
        if marker not in js:
            raise AssertionError(f"missing frontend flow marker: {marker}")


def run_fixture_api_loop() -> None:
    run_dir = ROOT / "runs" / "browser_e2e"
    shutil.rmtree(run_dir, ignore_errors=True)
    session = DogfoodSessionState(run_dir=run_dir)
    state = session.snapshot()
    if state["chat"]["layout"] != "chat_first":
        raise AssertionError("state did not expose chat_first layout")

    state = session.create_plan("Make next week less chaotic")
    cards = state["chat"]["candidate_cards"]
    if not cards:
        raise AssertionError("plan did not produce candidate cards")
    candidate_id = cards[0]["candidate_id"]

    staged = session.candidate_action(candidate_id, "stage")
    if not any(a["status"] in {"stageable", "requires_confirmation"} for a in staged["action_queue"]):
        raise AssertionError("stage did not produce stageable action queue item")

    committed = session.candidate_action(candidate_id, "commit", confirmed=True)
    rollback = next((a.get("rollback_handle_id") for a in committed["action_queue"] if a.get("rollback_handle_id")), None)
    if not rollback:
        raise AssertionError("commit did not produce rollback handle")

    undone = session.undo(rollback)
    if "Undo requested" not in json.dumps(undone["chat"]["messages"]):
        raise AssertionError("undo journey did not appear in chat transcript")

    receipt_id = next((a.get("receipt_id") for a in committed["action_queue"] if a.get("rollback_handle_id") == rollback), "")
    feedback = session.feedback(receipt_id, "useful")
    if feedback["inspector"]["replay"]["summary"].get("rewards", 0) < 1:
        raise AssertionError("feedback did not create replay reward evidence")

    exported = session.replay_export()
    if not exported.get("records"):
        raise AssertionError("replay export is empty")


def run_optional_browser_check() -> None:
    from playwright.sync_api import expect, sync_playwright

    session = DogfoodSessionState(run_dir=ROOT / "runs" / "browser_e2e")
    index_html = (ROOT / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "static" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "static" / "styles.css").read_text(encoding="utf-8")

    def route_api(path: str, body: dict) -> dict:
        parts = [p for p in path.split("/") if p]
        if path == "/api/plans":
            return session.create_plan(str(body.get("goal", "")))
        if len(parts) == 4 and parts[1] == "candidates":
            return session.candidate_action(parts[2], parts[3], confirmed=bool(body.get("confirmed", parts[3] == "commit")))
        if path == "/api/undo":
            return session.undo(str(body.get("rollback_handle_id", "")))
        if path == "/api/feedback":
            return session.feedback(str(body.get("receipt_id", "")), str(body.get("feedback", "useful")))
        raise ValueError(path)

    def fulfill(route):
        request = route.request
        url = request.url
        path = "/" + url.split("/", 3)[3] if url.count("/") >= 3 else "/"
        if path == "/api/state":
            route.fulfill(status=200, content_type="application/json", body=json.dumps(session.snapshot()))
        elif path == "/api/replay/export":
            route.fulfill(status=200, content_type="application/json", body=json.dumps(session.replay_export()))
        elif path.startswith("/api/"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(route_api(path, json.loads(request.post_data or "{}"))))
        else:
            route.fulfill(status=404, body="not found")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=shutil.which("chromium") or p.chromium.executable_path, args=["--no-sandbox"])
        page = browser.new_page()
        page.route("**/*", fulfill)
        inline = index_html.replace('<link rel="stylesheet" href="styles.css" />', f'<base href="http://calendarpilot.test/"><style>{styles_css}</style>')
        inline = inline.replace('<script src="app.js"></script>', f'<script>{app_js}</script>')
        page.set_content(inline)
        expect(page.get_by_test_id("chat-transcript")).to_be_visible()
        page.get_by_test_id("goal-input").fill("Make next week less chaotic")
        page.get_by_test_id("send-goal").click()
        expect(page.get_by_test_id("candidate-card").first).to_be_visible(timeout=10000)
        browser.close()


if __name__ == "__main__":
    main()
