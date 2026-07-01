from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from calendar_pilot.frontend.session import DogfoodSessionState


ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = ROOT / "frontend" / "static"
_DEFAULT_SESSION: DogfoodSessionState | None = None


def get_session() -> DogfoodSessionState:
    global _DEFAULT_SESSION
    if _DEFAULT_SESSION is None:
        _DEFAULT_SESSION = DogfoodSessionState()
    return _DEFAULT_SESSION


def build_demo_snapshot(observation_path: str | Path = "data/sample_calendar.json", profile_path: str | Path = "data/sample_profile.json", *, commit: bool = True) -> dict[str, Any]:
    session = DogfoodSessionState(observation_path=Path(observation_path), profile_path=Path(profile_path))
    session.create_plan("Make next week less chaotic", commit=commit)
    return session.snapshot()


def write_demo_snapshot(out: str | Path = "frontend/static/frontend_state.sample.json", *, commit: bool = True) -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_demo_snapshot(commit=commit), indent=2, sort_keys=True), encoding="utf-8")
    return path


def serve(static_dir: str | Path = STATIC_DIR, host: str = "127.0.0.1", port: int = 8787, *, run_dir: str | Path | None = None) -> None:
    directory = str(Path(static_dir).resolve())
    if run_dir is not None:
        global _DEFAULT_SESSION
        _DEFAULT_SESSION = DogfoodSessionState(run_dir=Path(run_dir))

    class Handler(SimpleHTTPRequestHandler):
        server_version = "CalendarPilotFrontend/0.3"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=directory, **kwargs)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._handle_api_get(parsed.path, parse_qs(parsed.query))
                return
            if parsed.path == "/":
                self.path = "/index.html"
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/api/"):
                self.send_error(HTTPStatus.NOT_FOUND, "API endpoint not found")
                return
            try:
                body = self._read_json_body()
                result = self._route_post(parsed.path, body)
                self._json(result)
            except Exception as exc:  # keep dogfood UI debuggable
                self._json({"error": str(exc), "state": get_session().snapshot()}, status=HTTPStatus.BAD_REQUEST)

        def _handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
            session = get_session()
            if path == "/api/state":
                self._json(session.snapshot())
                return
            if path == "/api/replay":
                candidate = query.get("candidate_id", [""])[0]
                records = [record.envelope() for record in session.replay.records]
                if candidate:
                    records = [r for r in records if candidate in json.dumps(r)]
                self._json({"summary": session.snapshot().get("inspector", {}).get("replay", {}).get("summary", {}), "records": records[-100:]})
                return
            if path == "/api/replay/export":
                self._json(session.replay_export())
                return
            self._json({"error": f"unsupported GET {path}"}, status=HTTPStatus.NOT_FOUND)

        def _route_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
            session = get_session()
            parts = [p for p in path.split("/") if p]
            if path == "/api/plans":
                tier = body.get("authority_tier", body.get("max_authority_tier"))
                return session.create_plan(str(body.get("goal", "")), commit=bool(body.get("commit", False)), authority_tier=tier)
            if len(parts) == 4 and parts[1] == "candidates":
                candidate_id = parts[2]
                action = parts[3]
                if action in {"simulate", "stage", "commit"}:
                    return session.candidate_action(candidate_id, action, confirmed=bool(body.get("confirmed", action == "commit")))
                if action == "confirm":
                    return session.candidate_action(candidate_id, "commit", confirmed=True)
            if len(parts) == 4 and parts[1] == "receipts" and parts[3] == "confirm":
                return session.confirm_receipt(parts[2])
            if path == "/api/undo":
                return session.undo(str(body.get("rollback_handle_id", "")))
            if path == "/api/profile/patch/propose":
                return session.propose_profile_patch(str(body.get("correction", "")))
            if path == "/api/profile/patch/apply":
                return session.apply_profile_patch(str(body.get("claim", "")), str(body.get("correction", "")), confirmed=bool(body.get("confirmed", False)))
            if path == "/api/denials/explain":
                return session.explain_denial(str(body.get("denied_reason", "")))
            if path == "/api/self-play":
                return session.run_self_play(int(body.get("episodes", 3)))
            if path == "/api/authority":
                scopes = body.get("scopes")
                if isinstance(scopes, str):
                    scopes = [s.strip() for s in scopes.split(",") if s.strip()]
                tier = body.get("max_authority_tier", body.get("authority_tier"))
                return session.update_authority(tier=tier, scopes=scopes if isinstance(scopes, list) else None, confirmed=bool(body.get("confirmed", True)))
            if path == "/api/feedback":
                return session.feedback(str(body.get("receipt_id", "")), str(body.get("feedback", "useful")), reason=str(body.get("reason", "")))
            if path == "/api/reset":
                return session.reset()
            raise ValueError(f"unsupported POST {path}")

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            return json.loads(raw or "{}")

        def _json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    ThreadingHTTPServer((host, port), Handler).serve_forever()
