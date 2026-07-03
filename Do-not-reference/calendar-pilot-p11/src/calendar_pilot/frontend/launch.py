
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]

from calendar_pilot.environment.fsio import atomic_write_json


def _stable_launch_id(seed: str | None = None) -> str:
    raw = seed or f"{datetime.now(timezone.utc).isoformat()}|{os.getpid()}"
    return "launch_" + hashlib.sha1(raw.encode()).hexdigest()[:12]


@dataclass(frozen=True)
class LaunchConfig:
    """Single launch/session manifest shared by Finder, CLI, browser, and tests."""

    app_root: Path = ROOT
    run_dir: Path = ROOT / "runs" / "dogfood"
    runtime_mode: str = "auto"
    host: str = "127.0.0.1"
    port: int = 8787
    launch_id: str = field(default_factory=_stable_launch_id)
    build_id: str = "unknown"
    app_bundle_path: str | None = None
    static_dir: Path = ROOT / "frontend" / "static"
    swift_kernel_server: str = ""
    eventkit_bridge: str = ""
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_env(
        cls,
        *,
        run_dir: str | Path | None = None,
        host: str | None = None,
        port: int | None = None,
        runtime_mode: str | None = None,
    ) -> "LaunchConfig":
        app_root = Path(os.environ.get("CALENDAR_PILOT_APP_ROOT", str(ROOT))).resolve()
        selected_run_dir = Path(run_dir or os.environ.get("CALENDAR_PILOT_RUN_DIR", str(app_root / "runs" / "dogfood"))).resolve()
        selected_runtime = (runtime_mode or os.environ.get("CALENDAR_PILOT_RUNTIME_MODE") or "auto").strip().lower().replace("-", "_")
        build_id = os.environ.get("CALENDAR_PILOT_BUILD_ID") or _read_text(app_root / "build_id") or "unknown"
        return cls(
            app_root=app_root,
            run_dir=selected_run_dir,
            runtime_mode=selected_runtime,
            host=host or os.environ.get("CALENDAR_PILOT_HOST", "127.0.0.1"),
            port=int(port if port is not None else os.environ.get("CALENDAR_PILOT_LAUNCH_PORT") or os.environ.get("CALENDAR_PILOT_PORT") or 8787),
            launch_id=os.environ.get("CALENDAR_PILOT_LAUNCH_ID") or _stable_launch_id(str(selected_run_dir)),
            build_id=build_id,
            app_bundle_path=os.environ.get("CALENDAR_PILOT_APP_BUNDLE_PATH"),
            static_dir=Path(os.environ.get("CALENDAR_PILOT_STATIC_DIR", str(app_root / "frontend" / "static"))).resolve(),
            swift_kernel_server=os.environ.get("CALENDAR_PILOT_SWIFT_KERNEL_SERVER", ""),
            eventkit_bridge=os.environ.get("CALENDAR_PILOT_EVENTKIT_BRIDGE", ""),
        )

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "launch_state.json"

    def to_dict(self) -> dict[str, Any]:
        server_pid = os.getpid()
        launcher_pid = int(os.environ.get("CALENDAR_PILOT_LAUNCHER_PID") or server_pid)
        return {
            "status": "running",
            "launch_id": self.launch_id,
            "launcher_pid": launcher_pid,
            "server_pid": server_pid,
            "build_id": self.build_id,
            "app_root": str(self.app_root),
            "run_dir": str(self.run_dir),
            "runtime_mode": self.runtime_mode,
            "host": self.host,
            "port": self.port,
            "base_url": f"http://{self.host}:{self.port}",
            "app_bundle_path": self.app_bundle_path,
            "static_dir": str(self.static_dir),
            "swift_kernel_server": self.swift_kernel_server,
            "eventkit_bridge": self.eventkit_bridge,
            "started_at": self.started_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def write_manifest(self) -> Path:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.manifest_path, self.to_dict())
        return self.manifest_path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""