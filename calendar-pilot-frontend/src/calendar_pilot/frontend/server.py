from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from calendar_pilot.codex import CodexToolPlanner, CodexToolRuntime
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


def serve(static_dir: str | Path = STATIC_DIR, host: str = "127.0.0.1", port: int = 8787) -> None:
    directory = str(Path(static_dir).resolve())

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=directory, **kwargs)

    ThreadingHTTPServer((host, port), Handler).serve_forever()
