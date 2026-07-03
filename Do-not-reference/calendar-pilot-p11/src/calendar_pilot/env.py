
from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_local_env(path: str | Path | None = None, *, override: bool = False) -> Path | None:
    """Load a simple KEY=VALUE .env file without adding a runtime dependency."""

    env_path = _env_path(path)
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or (key in os.environ and not override):
            continue
        os.environ[key] = _unquote_env_value(value.strip())
    return env_path


def _env_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    configured = os.environ.get("CALENDAR_PILOT_ENV_FILE")
    if configured:
        return Path(configured)
    for base in [ROOT, *ROOT.parents]:
        candidate = base / ".env"
        if candidate.exists():
            return candidate
    return ROOT / ".env"


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value