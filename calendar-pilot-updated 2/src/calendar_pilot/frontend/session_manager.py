from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import threading

from calendar_pilot.frontend.launch import LaunchConfig
from calendar_pilot.frontend.session import DogfoodSessionState


@dataclass
class SessionManager:
    """Process-local session registry keyed by run directory/session id."""

    sessions: dict[str, DogfoodSessionState] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def get_or_create(self, launch: LaunchConfig | None = None) -> DogfoodSessionState:
        launch = launch or LaunchConfig.from_env()
        launch.write_manifest()
        key = str(Path(launch.run_dir).resolve())
        with self._lock:
            session = self.sessions.get(key)
            if session is None:
                session = DogfoodSessionState(run_dir=launch.run_dir, runtime_mode=launch.runtime_mode)
                self.sessions[key] = session
            return session

    def reset(self, launch: LaunchConfig | None = None) -> DogfoodSessionState:
        launch = launch or LaunchConfig.from_env()
        key = str(Path(launch.run_dir).resolve())
        with self._lock:
            old = self.sessions.pop(key, None)
            if old is not None:
                old.close()
            session = DogfoodSessionState(run_dir=launch.run_dir, runtime_mode=launch.runtime_mode)
            self.sessions[key] = session
            return session

    def close_all(self) -> None:
        with self._lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
        for session in sessions:
            session.close()
