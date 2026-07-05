

#!/usr/bin/env python3
"""Frontend dogfood E2E.

The canonical path starts the real Python frontend server, verifies persisted
state across restart, and drives rendered browser controls against the live
server. The HTTP loop remains as API-level evidence, but browser coverage is a
default gate rather than an optional smoke.
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
        with LiveServer() as restarted:
            restored = api_get(restarted.base_url, "/api/state")
            assert_restarted_state(restored)
            reset = api_post(restarted.base_url, "/api/reset", {})
            if reset["inspector"]["replay"]["summary"]["records"] != 0:
                raise AssertionError("reset did not clear replay summary before browser run")
            run_live_browser_check(restarted.base_url, ARTIFACT_DIR)
            final_state = api_get(restarted.base_url, "/api/state")
            final_health = api_get(restarted.base_url, "/api/health")
            final_replay = api_get(restarted.base_url, "/api/replay/export")
            write_artifact("latest_state.json", final_state)
            write_artifact("health.json", final_health)
            write_artifact("replay_export.json", final_replay)
            write_artifact("dogfood_bug_report.json", {
                "summary": "CalendarPilot browser dogfood replay export",
                "base_url": restarted.base_url,
                "session_id": final_replay.get("session_id"),
                "runtime": final_replay.get("runtime"),
                "api_replay_summary_before_browser": result["replay_export"].get("summary"),
                "restored_replay_summary": restored["inspector"]["replay"]["summary"],
                "final_replay_summary": final_replay.get("summary"),
                "artifact_files": ["latest_state.json", "health.json", "replay_export.json", "browser_replay_export.json", "browser_success.png", "server.log"],
            })
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
        env["CALENDAR_PILOT_RUNTIME_MODE"] = "fixture"
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
        try:
            self.wait_until_ready()
        except Exception:
            self.__exit__(None, None, None)
            raise
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
    expected_runtime_label = expected_runtime_label or runtime_label(expected_runtime_mode)
    if node and Path(chrome).exists():
        env = os.environ.copy()
        env["CALENDAR_PILOT_EXPECTED_RUNTIME_MODE"] = expected_runtime_mode
        env["CALENDAR_PILOT_EXPECTED_RUNTIME_LABEL"] = expected_runtime_label
        if expected_runtime_mode != "fixture":
            env.setdefault("CALENDAR_PILOT_BROWSER_REQUIRE_UNDO", "0")
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
            if expected_runtime_mode == "fixture":
                expect(page.get_by_test_id("undo-action").first).to_be_visible(timeout=10000)
                page.get_by_test_id("undo-action").first.click()
                expect(page.get_by_text("Undo requested")).to_be_visible(timeout=10000)
            else:
                page.wait_for_function(
                    "() => document.querySelector('[data-testid=\"undo-action\"]') || document.querySelector('[data-testid=\"feedback-useful\"]')"
                )
                if page.get_by_test_id("undo-action").count() > 0:
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
            if expected_runtime_mode == "fixture":
                page.get_by_test_id("goal-input").fill("Try a low-authority commit")
                page.get_by_test_id("send-goal").click()
                expect(page.get_by_text("Try a low-authority commit")).to_be_visible(timeout=10000)
                page.wait_for_function("() => document.querySelectorAll('[data-testid=\"candidate-card\"]').length > 0")
                page.get_by_test_id("commit-candidate").last.click()
                expect(page.locator(".explain-denial").first).to_be_visible(timeout=10000)
                page.locator(".explain-denial").first.click()
                expect(page.get_by_text("Why Swift denied it")).to_be_visible(timeout=10000)
            elif page.get_by_test_id("commit-candidate").count() > 0:
                page.get_by_test_id("commit-candidate").last.click()
                expect(page.locator("body")).to_contain_text("denied", timeout=10000, ignore_case=True)
                (artifact_path / "live_low_authority_denial.json").write_text(
                    json.dumps({"exercised": True, "strategy": "existing_candidate_after_authority_drop"}, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
            else:
                (artifact_path / "live_low_authority_denial.json").write_text(
                    json.dumps({"exercised": False, "reason": "no_existing_candidate_button_after_authority_drop"}, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
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


def runtime_label(mode: str) -> str:
    return {
        "auto": "Auto assistant",
        "fixture": "Fixture mode",
        "swift_ipc": "Swift IPC mode",
        "live_codex": "Live Codex mode",
        "live_diffusiongemma": "Live DiffusionGemma mode",
        "live_provider": "Live provider mode",
        "production": "Production mode",
    }.get(mode, mode)


def assert_static_shell() -> None:
    html = (ROOT / "frontend" / "static" / "index.html").read_text(encoding="utf-8")
    js_root = ROOT / "frontend" / "static" / "js"
    main_js = (js_root / "main.js").read_text(encoding="utf-8")
    required_html = [
        '<script type="module" src="js/main.js"></script>',
        'data-testid="chat-transcript"',
        'data-testid="goal-input"',
        'data-testid="send-goal"',
        'data-testid="inspector-toggle"',
        'data-testid="runtime-chip"',
        'data-surface="operate"',
        'data-surface="observe"',
        'data-surface="learn"',
        'data-surface="lab"',
        'data-surface="authority"',
        'id="inspector-content"',
    ]
    for marker in required_html:
        if marker not in html:
            raise AssertionError(f"missing frontend marker: {marker}")
    required_js = [
        "/api/plans",
        "simulate-btn",
        "stage-btn",
        "commit-btn",
        "feedback-useful",
        "replay-export",
        "/api/self-play",
        "/api/authority",
        "/api/runtime",
        "openEnvelopeOverlay",
        "connectEvents",
    ]
    for marker in required_js:
        if marker not in main_js:
            raise AssertionError(f"missing frontend flow marker: {marker}")
    dynamic_sources = "\n".join(path.read_text(encoding="utf-8") for path in js_root.rglob("*.js"))
    if "innerHTML" in dynamic_sources:
        raise AssertionError("ES module frontend should not render dynamic state with innerHTML")


def run_live_api_loop(base_url: str) -> dict[str, Any]:
    state = api_get(base_url, "/api/state")
    if "session" not in state:
        raise AssertionError("/api/state did not return session state")
    health = api_get(base_url, "/api/health")
    if state.get("runtime", {}).get("runtime_mode") != health.get("runtime_mode"):
        raise AssertionError("/api/state and /api/health disagree on runtime mode")
    if health.get("runtime_mode") != "fixture":
        raise AssertionError(f"browser e2e expected fixture mode, got {health.get('runtime_mode')}")
    if state.get("runtime", {}).get("backends", {}).get("kernel") != "SwiftKernelStub":
        raise AssertionError("fixture state did not expose SwiftKernelStub backend")

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

    self_play = api_post(base_url, "/api/self-play", {"episodes": 1})
    if not self_play["inspector"]["self_play"]["history"]:
        raise AssertionError("self-play did not write visible history")

    authority = api_post(base_url, "/api/authority", {"authority_tier": 2, "scopes": "recommend, stage, undo", "confirmed": "false"})
    if authority["session"]["authority_tier"] != 2:
        raise AssertionError("authority tier edit did not apply")
    if authority["inspector"]["authority"]["history"][-1]["grant"]["confirmed_by_user"]:
        raise AssertionError("string false confirmed value minted a confirmed grant")

    denied_commit = api_post(base_url, f"/api/candidates/{candidate_id}/commit", {"confirmed": "false"})
    if "denied" not in json.dumps(denied_commit):
        raise AssertionError("low-authority commit did not produce a denial")
    denial_reason = denied_commit["inspector"]["denials"][-1]["denied_reason"]
    denial = api_post(base_url, "/api/denials/explain", {"denied_reason": denial_reason})
    if not denial["inspector"]["denials"]:
        raise AssertionError("denial explanation did not write visible history")

    undone = api_post(base_url, "/api/undo", {"rollback_handle_id": rollback})
    if "Undo requested" not in json.dumps(undone["chat"]["messages"]):
        raise AssertionError("undo journey did not appear in visible state")

    replay = api_get(base_url, "/api/replay")
    if replay["summary"].get("records", 0) < 1:
        raise AssertionError("replay endpoint returned no records")
    replay_export = api_get(base_url, "/api/replay/export")
    if not replay_export.get("records"):
        raise AssertionError("replay export is empty")
    if replay_export.get("runtime", {}).get("runtime_mode") != "fixture":
        raise AssertionError("replay export did not include fixture runtime provenance")

    error = api_post(base_url, "/api/not-a-route", {}, expected_status=400)
    if "error" not in error or "state" not in error:
        raise AssertionError("invalid POST did not return error and state")

    return {"state": error["state"], "replay_export": replay_export}


def assert_restarted_state(state: dict[str, Any]) -> None:
    if state["inspector"]["replay"]["summary"].get("records", 0) < 1:
        raise AssertionError("restarted live server did not restore replay records")
    if not state["inspector"]["feedback"]:
        raise AssertionError("restarted live server did not restore feedback evidence")
    if not state["inspector"]["profile"]["patch_history"]:
        raise AssertionError("restarted live server did not restore profile history")
    if not state["inspector"]["self_play"]["history"]:
        raise AssertionError("restarted live server did not restore self-play history")
    if not state["inspector"]["denials"]:
        raise AssertionError("restarted live server did not restore denial history")


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
