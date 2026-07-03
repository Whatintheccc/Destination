from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.replay import ReplayBuffer


@dataclass
class SessionStore:
    """Extracted persistence/restore boundary for a dogfood session.

    The store owns file names, atomic writes, session manifests, and replay
    compaction. DogfoodSessionState remains the coordinator, but no longer owns
    filesystem semantics directly.
    """

    run_dir: Path

    @property
    def state_path(self) -> Path:
        return self.run_dir / "session_state.json"

    @property
    def latest_path(self) -> Path:
        return self.run_dir / "latest_session.json"

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "session_manifest.json"

    @property
    def replay_path(self) -> Path:
        return self.run_dir / "replay.jsonl"

    def load_state(self) -> dict[str, Any] | None:
        if not self.state_path.exists():
            return None
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def load_replay(self) -> ReplayBuffer:
        replay = ReplayBuffer.load_jsonl(self.replay_path)
        replay.set_jsonl_path(self.replay_path)
        return replay

    def save(
        self,
        *,
        state_payload: dict[str, Any],
        latest_snapshot: dict[str, Any],
        session_manifest: dict[str, Any],
        replay: ReplayBuffer,
    ) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.state_path, state_payload)
        atomic_write_json(self.latest_path, latest_snapshot)
        atomic_write_json(self.manifest_path, session_manifest)
        # Replay is append-first as records arrive; save_jsonl is a compaction
        # step preserving the exact in-memory list at snapshot points.
        replay.save_jsonl(self.replay_path)