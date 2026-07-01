from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from calendar_pilot.codex import CodexToolPlanner, CodexToolRuntime
from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.frontend.surface import build_frontend_snapshot
from calendar_pilot.types import RawCalendarObservation, UserBiography


ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = ROOT / "frontend" / "static"


def build_demo_snapshot(observation_path: str | Path = "data/sample_calendar.json", profile_path: str | Path = "data/sample_profile.json", *, commit: bool = True) -> dict[str, Any]:
    observation = RawCalendarObservation.from_dict(json.loads(Path(observation_path).read_text(encoding="utf-8")))
    biography = UserBiography.from_dict(json.loads(Path(profile_path).read_text(encoding="utf-8")))
    runtime = CodexToolRuntime()
    planner = CodexToolPlanner(runtime=runtime)
    plan = planner.plan_goal("Make next week less chaotic", observation, biography, authority_tier=3, commit=commit)
    return build_frontend_snapshot(plan, observation, biography, runtime.replay).to_dict()


def write_demo_snapshot(out: str | Path = "frontend/static/frontend_state.sample.json", *, commit: bool = True) -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_demo_snapshot(commit=commit), indent=2, sort_keys=True), encoding="utf-8")
    return path


def serve(static_dir: str | Path = STATIC_DIR, host: str = "127.0.0.1", port: int = 8787, state: DogfoodSessionState | None = None) -> None:
    directory = str(Path(static_dir).resolve())
    session = state or DogfoodSessionState()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=directory, **kwargs)

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                self._send_json(session.state())
                return
            if parsed.path == "/api/replay":
                query = parse_qs(parsed.query)
                self._send_json(session.replay_trace(
                    candidate_id=query.get("candidate_id", [None])[0],
                    trace_id=query.get("trace_id", [None])[0],
                    receipt_id=query.get("receipt_id", [None])[0],
                    authority_grant_id=query.get("authority_grant_id", [None])[0],
                    rollback_handle_id=query.get("rollback_handle_id", [None])[0],
                    reward_event_id=query.get("reward_event_id", [None])[0],
                    q=query.get("q", [None])[0],
                ))
                return
            if parsed.path == "/api/replay/export":
                query = parse_qs(parsed.query)
                self._send_json(session.export_replay(
                    candidate_id=query.get("candidate_id", [None])[0],
                    trace_id=query.get("trace_id", [None])[0],
                    receipt_id=query.get("receipt_id", [None])[0],
                    authority_grant_id=query.get("authority_grant_id", [None])[0],
                    rollback_handle_id=query.get("rollback_handle_id", [None])[0],
                    reward_event_id=query.get("reward_event_id", [None])[0],
                    q=query.get("q", [None])[0],
                ))
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            parsed = urlparse(self.path)
            body = self._read_json()
            try:
                response = self._route_post(parsed.path, body)
            except Exception as exc:  # deterministic API error for dogfood UI
                self._send_json({"error": str(exc), "snapshot": session.state().get("snapshot", {})}, status=500)
                return
            status = 400 if isinstance(response, dict) and response.get("error") else 200
            self._send_json(response, status=status)

        def _route_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
            if path == "/api/plans":
                return session.create_plan(
                    str(body.get("goal", "Make next week less chaotic")),
                    authority_tier=int(body.get("authority_tier", 3)),
                    commit=bool(body.get("commit", False)),
                )
            if path == "/api/authority":
                raw_scopes = body.get("scopes")
                scopes: list[str] | None = None
                if isinstance(raw_scopes, str):
                    scopes = [item.strip() for item in raw_scopes.split(",") if item.strip()]
                elif isinstance(raw_scopes, list):
                    scopes = [str(item).strip() for item in raw_scopes if str(item).strip()]
                return session.update_authority(
                    authority_tier=int(body["authority_tier"]) if "authority_tier" in body else None,
                    scopes=scopes,
                )
            if path.startswith("/api/candidates/"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    candidate_id = parts[2]
                    op = parts[3]
                    if op == "simulate":
                        return session.simulate_candidate(candidate_id)
                    if op == "stage":
                        return session.stage_candidate(candidate_id)
                    if op == "commit":
                        return session.commit_candidate(candidate_id)
            if path.startswith("/api/receipts/") and path.endswith("/confirm"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    return session.confirm_receipt(parts[2])
            if path == "/api/undo":
                return session.undo(str(body.get("rollback_handle_id", "")))
            if path == "/api/profile/patch/propose":
                return session.propose_profile_patch(str(body.get("correction", "")))
            if path == "/api/profile/patch/apply":
                return session.apply_profile_patch(
                    str(body.get("claim", "")),
                    str(body.get("correction", "")),
                    confirmed=bool(body.get("confirmed", True)),
                )
            if path == "/api/denials/explain":
                return session.explain_denial(str(body.get("denied_reason", "")))
            if path == "/api/self-play":
                return session.run_self_play(episodes=int(body.get("episodes", 3)))
            if path == "/api/feedback":
                return session.feedback(str(body.get("receipt_id", "")), dict(body.get("feedback", {})))
            if path == "/api/reset":
                return session.reset_fixture()
            return {"error": f"unknown endpoint {path}", "snapshot": session.state().get("snapshot", {})}

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return dict(json.loads(raw or "{}"))

        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    ThreadingHTTPServer((host, port), Handler).serve_forever()
