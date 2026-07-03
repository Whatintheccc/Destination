
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import hashlib
import threading
from typing import Any

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.frontend.launch import LaunchConfig
from calendar_pilot.frontend.session import DogfoodSessionState


@dataclass
class SessionManager:
    """Process-local session registry keyed by run directory/session id."""

    sessions: dict[str, DogfoodSessionState] = field(default_factory=dict)
    active_key: str | None = None
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def get_or_create(self, launch: LaunchConfig | None = None) -> DogfoodSessionState:
        launch = launch or LaunchConfig.from_env()
        with self._lock:
            key = self.active_key or self._read_active_key(launch) or self._root_key(launch)
            session = self.sessions.get(key)
            if session is None:
                run_dir = Path(key)
                session = DogfoodSessionState(run_dir=run_dir, runtime_mode=launch.runtime_mode)
                self._bind_launch(session, launch)
                self.sessions[key] = session
            self.active_key = key
            self._write_active_pointer(launch, session)
            self._write_root_launch_manifest(launch, session)
            return session

    def get_by_session_id(self, session_id: str, launch: LaunchConfig | None = None, *, activate: bool = False) -> DogfoodSessionState:
        launch = launch or LaunchConfig.from_env()
        requested = str(session_id or "").strip()
        with self._lock:
            for summary in self.session_summaries(launch, active_session_id=requested, include_archived=True):
                if summary.get("session_id") == requested:
                    key = str(Path(str(summary["run_dir"])).resolve())
                    session = self.sessions.get(key)
                    if session is None:
                        session = DogfoodSessionState(run_dir=Path(key), runtime_mode=launch.runtime_mode)
                        self._bind_launch(session, launch)
                        self.sessions[key] = session
                    if activate:
                        self.active_key = key
                        self._write_active_pointer(launch, session)
                        self._write_root_launch_manifest(launch, session)
                    return session
        raise KeyError(f"session not found: {session_id}")

    def create_session(self, launch: LaunchConfig | None = None) -> DogfoodSessionState:
        launch = launch or LaunchConfig.from_env()
        base = Path(launch.run_dir).resolve()
        created = datetime.now(timezone.utc)
        digest = hashlib.sha1(f"{created.isoformat()}|{len(self.sessions)}".encode()).hexdigest()[:10]
        run_dir = base / "sessions" / f"session_{created.strftime('%Y%m%d_%H%M%S')}_{digest}"
        key = str(run_dir.resolve())
        with self._lock:
            session = DogfoodSessionState(run_dir=run_dir, runtime_mode=self._runtime_mode_for_new_session(launch))
            self._bind_launch(session, launch)
            self.sessions[key] = session
            self.active_key = key
            self._write_active_pointer(launch, session)
            self._write_root_launch_manifest(launch, session)
            return session

    def switch_session(self, session_id: str, launch: LaunchConfig | None = None) -> DogfoodSessionState:
        return self.get_by_session_id(session_id, launch, activate=True)

    def rename_session(self, session_id: str, label: str, launch: LaunchConfig | None = None) -> DogfoodSessionState:
        launch = launch or LaunchConfig.from_env()
        with self._lock:
            session = self.get_by_session_id(session_id, launch, activate=False)
            session.rename_session(label)
            if str(session.run_dir.resolve()) == (self.active_key or self._read_active_key(launch) or self._root_key(launch)):
                self._write_root_launch_manifest(launch, session)
            return session

    def archive_session(self, session_id: str, launch: LaunchConfig | None = None) -> DogfoodSessionState:
        launch = launch or LaunchConfig.from_env()
        requested = str(session_id or "").strip()
        with self._lock:
            session = self.get_by_session_id(requested, launch, activate=False)
            archived_key = str(session.run_dir.resolve())
            session.archive_session()
            active_key = self.active_key or self._read_active_key(launch) or self._root_key(launch)
            if archived_key != active_key:
                active = self.sessions.get(active_key)
                if active is not None:
                    return active
                return self.get_or_create(launch)
            for summary in self.session_summaries(launch, include_archived=False):
                if summary.get("session_id") == requested:
                    continue
                return self.switch_session(str(summary["session_id"]), launch)
            return self.create_session(launch)

    def refresh_active_launch_manifest(self, session: DogfoodSessionState, launch: LaunchConfig | None = None) -> None:
        launch = launch or LaunchConfig.from_env()
        with self._lock:
            active_key = self.active_key or self._read_active_key(launch) or self._root_key(launch)
            if str(session.run_dir.resolve()) != active_key:
                return
            self._write_active_pointer(launch, session)
            self._write_root_launch_manifest(launch, session)

    def session_summaries(self, launch: LaunchConfig | None = None, *, active_session_id: str | None = None, include_archived: bool = False) -> list[dict[str, object]]:
        launch = launch or LaunchConfig.from_env()
        base = Path(launch.run_dir).resolve()
        with self._lock:
            active_key = self.active_key or self._read_active_key(launch) or self._root_key(launch)
            known_keys = list(self.sessions)
            rows: list[dict[str, object]] = []
            seen: set[str] = set()
            for run_dir in self._discover_run_dirs(base, known_keys):
                key = str(run_dir.resolve())
                if key in seen:
                    continue
                seen.add(key)
                session = self.sessions.get(key)
                if session is not None:
                    summary = self._summary_for_session(session, active_key=active_key, active_session_id=active_session_id)
                    if include_archived or not summary.get("archived_at"):
                        rows.append(summary)
                    continue
                summary = self._summary_from_disk(run_dir, active_key=active_key, active_session_id=active_session_id)
                if summary is not None and (include_archived or not summary.get("archived_at")):
                    rows.append(summary)
        rows.sort(key=lambda row: str(row.get("updated_at", "")), reverse=True)
        return rows

    def reset(self, launch: LaunchConfig | None = None) -> DogfoodSessionState:
        launch = launch or LaunchConfig.from_env()
        key = self.active_key or self._root_key(launch)
        with self._lock:
            old = self.sessions.pop(key, None)
            if old is not None:
                old.close()
            session = DogfoodSessionState(run_dir=Path(key), runtime_mode=launch.runtime_mode)
            self._bind_launch(session, launch)
            self.sessions[key] = session
            self.active_key = key
            self._write_active_pointer(launch, session)
            self._write_root_launch_manifest(launch, session)
            return session

    def close_all(self) -> None:
        with self._lock:
            sessions = list(self.sessions.values())
            self.sessions.clear()
            self.active_key = None
        for session in sessions:
            session.close()

    @staticmethod
    def _root_key(launch: LaunchConfig) -> str:
        return str(Path(launch.run_dir).resolve())

    def _discover_run_dirs(self, base: Path, known_keys: list[str]) -> list[Path]:
        dirs = [base]
        sessions_dir = base / "sessions"
        if sessions_dir.exists():
            dirs.extend(path for path in sessions_dir.iterdir() if path.is_dir())
        for key in known_keys:
            dirs.append(Path(key))
        return dirs

    def _summary_for_session(self, session: DogfoodSessionState, *, active_key: str, active_session_id: str | None = None) -> dict[str, object]:
        label = session.session_label or "New chat"
        if label == "New chat":
            for event in session.transcript_events:
                if event.get("kind") == "user" and str(event.get("body", "")).strip():
                    label = str(event["body"]).strip()
                    break
        if label == "New chat" and session.transcript_events:
            label = str(session.transcript_events[0].get("title") or label)
        updated_at = ""
        if session.transcript_events:
            updated_at = str(session.transcript_events[-1].get("created_at") or "")
        return {
            "session_id": session.session_id,
            "label": label[:80],
            "active": session.session_id == active_session_id if active_session_id else str(session.run_dir.resolve()) == active_key,
            "run_dir": str(session.run_dir.resolve()),
            "runtime_mode": session.runtime_mode,
            "replay_records": session.replay.summarize().records,
            "updated_at": updated_at,
            "archived_at": session.archived_at,
        }

    def _summary_from_disk(self, run_dir: Path, *, active_key: str, active_session_id: str | None = None) -> dict[str, object] | None:
        path = run_dir / "session_state.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return None
        session_id = str(data.get("session_id") or "")
        if not session_id:
            return None
        transcript = data.get("transcript_events", [])
        label = str(data.get("session_label") or "").strip() or "New chat"
        updated_at = str(data.get("updated_at") or "")
        if isinstance(transcript, list):
            if label == "New chat":
                for event in transcript:
                    if isinstance(event, dict) and event.get("kind") == "user" and str(event.get("body", "")).strip():
                        label = str(event["body"]).strip()
                        break
            if transcript and isinstance(transcript[-1], dict):
                updated_at = str(transcript[-1].get("created_at") or updated_at)
            if label == "New chat" and transcript and isinstance(transcript[0], dict):
                label = str(transcript[0].get("title") or label)
        return {
            "session_id": session_id,
            "label": label[:80],
            "active": session_id == active_session_id if active_session_id else str(run_dir.resolve()) == active_key,
            "run_dir": str(run_dir.resolve()),
            "runtime_mode": str(data.get("runtime_mode") or "fixture"),
            "replay_records": self._replay_record_count(run_dir),
            "updated_at": updated_at,
            "archived_at": str(data.get("archived_at") or "").strip() or None,
        }

    def _runtime_mode_for_new_session(self, launch: LaunchConfig) -> str:
        active_key = self.active_key or self._read_active_key(launch) or self._root_key(launch)
        active_runtime = ""
        active = self.sessions.get(active_key)
        if active is not None:
            active_runtime = active.runtime_mode
        else:
            summary = self._summary_from_disk(Path(active_key), active_key=active_key)
            if summary is not None:
                active_runtime = str(summary.get("runtime_mode") or "")
        if active_runtime and (active_runtime != "fixture" or launch.runtime_mode == "fixture"):
            return active_runtime
        return launch.runtime_mode

    def _bind_launch(self, session: DogfoodSessionState, launch: LaunchConfig) -> None:
        session.launch_config = LaunchConfig.from_env(
            run_dir=session.run_dir,
            host=launch.host,
            port=launch.port,
            runtime_mode=session.runtime_mode,
        )
        session.persist()

    def _write_root_launch_manifest(self, launch: LaunchConfig, session: DogfoodSessionState) -> None:
        manifest = launch.to_dict()
        manifest["runtime_mode"] = session.runtime_mode
        manifest["active_session_id"] = session.session_id
        manifest["active_session_run_dir"] = str(session.run_dir.resolve())
        manifest["health"] = session.runtime_report()
        atomic_write_json(launch.manifest_path, manifest)

    @staticmethod
    def _replay_record_count(run_dir: Path) -> int:
        path = run_dir / "replay.jsonl"
        try:
            return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError:
            return 0

    def _active_pointer_path(self, launch: LaunchConfig) -> Path:
        return Path(launch.run_dir).resolve() / "active_session.json"

    def _write_active_pointer(self, launch: LaunchConfig, session: DogfoodSessionState) -> None:
        path = self._active_pointer_path(launch)
        atomic_write_json(path, {
            "session_id": session.session_id,
            "run_dir": str(session.run_dir.resolve()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    def _read_active_key(self, launch: LaunchConfig) -> str | None:
        try:
            data = json.loads(self._active_pointer_path(launch).read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            return None
        run_dir = data.get("run_dir") if isinstance(data, dict) else None
        if not run_dir:
            return None
        path = Path(str(run_dir)).resolve()
        if (path / "session_state.json").exists():
            return str(path)
        return None