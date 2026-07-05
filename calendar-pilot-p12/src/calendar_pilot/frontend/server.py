

from __future__ import annotations

import json
import signal
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from calendar_pilot.environment.trace import TRACE_BUS
from calendar_pilot.frontend.launch import LaunchConfig
from calendar_pilot.frontend.session import DogfoodSessionState
from calendar_pilot.frontend.session_manager import SessionManager


ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = ROOT / "frontend" / "static"
_DEFAULT_SESSION: DogfoodSessionState | None = None
_SESSION_MANAGER = SessionManager()
_CURRENT_LAUNCH = LaunchConfig.from_env()


def body_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
    return default


def get_session(session_id: str | None = None) -> DogfoodSessionState:
    global _DEFAULT_SESSION
    if session_id:
        try:
            return _SESSION_MANAGER.get_by_session_id(session_id, _CURRENT_LAUNCH, activate=False)
        except KeyError:
            if _DEFAULT_SESSION is None:
                _DEFAULT_SESSION = _SESSION_MANAGER.get_or_create(_CURRENT_LAUNCH)
            return _DEFAULT_SESSION
    if _DEFAULT_SESSION is None:
        _DEFAULT_SESSION = _SESSION_MANAGER.get_or_create(_CURRENT_LAUNCH)
    return _DEFAULT_SESSION


def set_current_session(session: DogfoodSessionState) -> DogfoodSessionState:
    global _DEFAULT_SESSION
    _DEFAULT_SESSION = session
    return session


def decorate_state(state: dict[str, Any], *, active_session_id: str | None = None) -> dict[str, Any]:
    active_session_id = active_session_id or str(state.get("session", {}).get("session_id") or "")
    if isinstance(state.get("sidebar"), dict):
        state["sidebar"]["sessions"] = _SESSION_MANAGER.session_summaries(_CURRENT_LAUNCH, active_session_id=active_session_id or None)
    return state


def build_demo_snapshot(observation_path: str | Path = "data/sample_calendar.json", profile_path: str | Path = "data/sample_profile.json", *, commit: bool = True) -> dict[str, Any]:
    session = DogfoodSessionState(observation_path=Path(observation_path), profile_path=Path(profile_path))
    session.create_plan("Make next week less chaotic", commit=commit)
    return session.snapshot()


def write_demo_snapshot(out: str | Path = "runs/dogfood/frontend_snapshot.json", *, commit: bool = True) -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_demo_snapshot(commit=commit), indent=2, sort_keys=True), encoding="utf-8")
    return path


def serve(static_dir: str | Path = STATIC_DIR, host: str = "127.0.0.1", port: int = 8787, *, run_dir: str | Path | None = None) -> None:
    directory = str(Path(static_dir).resolve())
    if run_dir is not None:
        global _DEFAULT_SESSION, _CURRENT_LAUNCH
        _CURRENT_LAUNCH = LaunchConfig.from_env(run_dir=run_dir, host=host, port=port)
        _DEFAULT_SESSION = _SESSION_MANAGER.get_or_create(_CURRENT_LAUNCH)

    class Handler(SimpleHTTPRequestHandler):
        server_version = "CalendarPilotFrontend/0.3"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=directory, **kwargs)

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            super().end_headers()

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
            body: dict[str, Any] = {}
            try:
                body = self._read_json_body()
                result = self._route_post(parsed.path, body)
                self._json(result)
            except Exception as exc:  # keep dogfood UI debuggable
                fallback_session_id = str(body.get("session_id") or "") if isinstance(body, dict) else ""
                try:
                    state = decorate_state(get_session(fallback_session_id or None).snapshot(), active_session_id=fallback_session_id or None)
                except Exception:
                    state = decorate_state(get_session().snapshot())
                self._json({"error": str(exc), "state": state}, status=HTTPStatus.BAD_REQUEST)

        def _handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
            session_id = query.get("session_id", [""])[0]
            session = get_session(session_id or None)
            if path == "/api/state":
                self._json(decorate_state(session.snapshot()))
                return
            if path == "/api/view":
                self._json(session.view())
                return
            if path == "/api/events":
                self._handle_sse(session, query)
                return
            if path.startswith("/api/trace/"):
                trace_id = path.rsplit("/", 1)[-1]
                records = session.replay.causal_chain(trace_id)
                envelope = None
                for record in reversed(records):
                    payload = record.get("payload", {})
                    if record.get("record_type") == "envelope_transition" and isinstance(payload.get("envelope"), dict):
                        envelope = payload["envelope"]
                        break
                    if isinstance(payload.get("receipt"), dict) and isinstance(payload["receipt"].get("action_envelope"), dict):
                        envelope = payload["receipt"]["action_envelope"]
                        break
                self._json({"trace_id": trace_id, "records": records, "envelope": envelope})
                return
            if path == "/api/health":
                self._json(session.runtime_report())
                return
            if path == "/api/sessions":
                self._json({"sessions": _SESSION_MANAGER.session_summaries(_CURRENT_LAUNCH, active_session_id=session.session_id), "active_session_id": session.session_id})
                return
            if path == "/api/replay":
                candidate = query.get("candidate_id", [""])[0]
                records = [record.envelope() for record in session.replay.records]
                if candidate:
                    records = [
                        r for r in records
                        if r.get("payload", {}).get("candidate", {}).get("candidate_id") == candidate
                        or r.get("payload", {}).get("receipt", {}).get("candidate_id") == candidate
                        or r.get("trace_id") == candidate
                    ]
                self._json({"summary": session.snapshot().get("inspector", {}).get("replay", {}).get("summary", {}), "records": records[-100:]})
                return
            if path == "/api/replay/export":
                self._json(session.replay_export())
                return
            self._json({"error": f"unsupported GET {path}"}, status=HTTPStatus.NOT_FOUND)

        def _route_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
            session = get_session(str(body.get("session_id") or "") or None)
            parts = [p for p in path.split("/") if p]
            if path == "/api/plans":
                tier = body.get("authority_tier", body.get("max_authority_tier"))
                return decorate_state(session.create_plan(str(body.get("goal", "")), commit=body_bool(body.get("commit"), default=False), authority_tier=tier))
            if path == "/api/sessions":
                created = set_current_session(_SESSION_MANAGER.create_session(_CURRENT_LAUNCH))
                return decorate_state(created.snapshot())
            if path == "/api/sessions/switch":
                switched = set_current_session(_SESSION_MANAGER.switch_session(str(body.get("session_id", "")), _CURRENT_LAUNCH))
                return decorate_state(switched.snapshot())
            if path == "/api/sessions/rename":
                renamed = _SESSION_MANAGER.rename_session(str(body.get("session_id", "")), str(body.get("label", "")), _CURRENT_LAUNCH)
                active = get_session()
                if active.session_id == renamed.session_id:
                    active = set_current_session(renamed)
                return decorate_state(active.snapshot())
            if path == "/api/sessions/archive":
                active = set_current_session(_SESSION_MANAGER.archive_session(str(body.get("session_id", "")), _CURRENT_LAUNCH))
                return decorate_state(active.snapshot())
            if len(parts) == 4 and parts[1] == "candidates":
                candidate_id = parts[2]
                action = parts[3]
                if action in {"simulate", "stage", "commit"}:
                    return decorate_state(session.candidate_action(candidate_id, action, confirmed=body_bool(body.get("confirmed"), default=action == "commit")))
                if action == "confirm":
                    return decorate_state(session.candidate_action(candidate_id, "commit", confirmed=True))
            if len(parts) == 4 and parts[1] == "receipts" and parts[3] == "confirm":
                return decorate_state(session.confirm_receipt(parts[2]))
            if path == "/api/undo":
                return decorate_state(session.undo(str(body.get("rollback_handle_id", ""))))
            if path == "/api/profile/patch/propose":
                return decorate_state(session.propose_profile_patch(str(body.get("correction", ""))))
            if path == "/api/profile/patch/apply":
                return decorate_state(session.apply_profile_patch(str(body.get("claim", "")), str(body.get("correction", "")), confirmed=body_bool(body.get("confirmed"), default=False)))
            if path == "/api/denials/explain":
                return decorate_state(session.explain_denial(str(body.get("denied_reason", ""))))
            if path == "/api/self-play":
                return decorate_state(session.run_self_play(int(body.get("episodes", 3)), backend=str(body.get("backend", body.get("self_play_backend", "stub_fast")))))
            if path == "/api/signals/activation":
                return decorate_state(session.set_signal_activation(
                    str(body.get("signal_id", "")),
                    status=str(body.get("status", "")),
                    reason=str(body.get("reason", "")),
                ))
            if path == "/api/authority":
                scopes = body.get("scopes")
                if isinstance(scopes, str):
                    scopes = [s.strip() for s in scopes.split(",") if s.strip()]
                tier = body.get("max_authority_tier", body.get("authority_tier"))
                return decorate_state(session.update_authority(tier=tier, scopes=scopes if isinstance(scopes, list) else None, confirmed=body_bool(body.get("confirmed"), default=True)))
            if path == "/api/feedback":
                return decorate_state(session.feedback(str(body.get("receipt_id", "")), str(body.get("feedback", "useful")), reason=str(body.get("reason", ""))))
            if path == "/api/runtime":
                state = session.set_runtime_mode(str(body.get("runtime_mode", "")))
                _SESSION_MANAGER.refresh_active_launch_manifest(session, _CURRENT_LAUNCH)
                return decorate_state(state)
            if path == "/api/codex/auth/start":
                return decorate_state(session.start_codex_subscription_sign_in())
            if path == "/api/provider/permission/request":
                return decorate_state(session.provider_permission_request())
            if path == "/api/reset":
                return decorate_state(session.reset())
            raise ValueError(f"unsupported POST {path}")

        def _handle_sse(self, session: DogfoodSessionState, query: dict[str, list[str]]) -> None:
            try:
                since = int((query.get("since", ["0"])[0]) or 0)
            except ValueError:
                since = 0
            sub = TRACE_BUS.subscribe(session.session_id, since=since)
            try:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                for frame in sub.frames():
                    self.wfile.write(frame)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                TRACE_BUS.unsubscribe(sub)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            return json.loads(raw or "{}")

        def _json(self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    httpd = ThreadingHTTPServer((host, port), Handler)

    def stop_server(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGTERM, stop_server)
        signal.signal(signal.SIGINT, stop_server)
    except ValueError:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        _SESSION_MANAGER.close_all()
