from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform


ROOT = Path(__file__).resolve().parents[3]
KNOWN_MODES = {"fixture", "swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}
LIVE_MODES = {"swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}


@dataclass(frozen=True)
class RuntimeBackends:
    kernel: str = "SwiftKernelStub"
    codex: str = "deterministic_codex_tool_planner"
    diffusiongemma: str = "heuristic_diffusiongemma_policy"
    provider: str = "local_stub"

    def to_dict(self) -> dict[str, str]:
        return {
            "kernel": self.kernel,
            "codex": self.codex,
            "diffusiongemma": self.diffusiongemma,
            "provider": self.provider,
        }


def runtime_mode_from_env(default: str = "fixture") -> str:
    requested = os.environ.get("CALENDAR_PILOT_RUNTIME_MODE", default).strip().lower().replace("-", "_")
    return requested or default


def app_bundle_path(root: Path = ROOT) -> str | None:
    for parent in [root, *root.parents]:
        if parent.suffix == ".app":
            return str(parent)
    return None


def build_id(root: Path = ROOT) -> str:
    build_file = root / "build_id"
    if os.environ.get("CALENDAR_PILOT_BUILD_ID"):
        return str(os.environ["CALENDAR_PILOT_BUILD_ID"])
    try:
        value = build_file.read_text(encoding="utf-8").strip()
    except OSError:
        value = ""
    return value or _git_head(root) or "unknown"


def _git_head(root: Path) -> str | None:
    git_dir = root.parent / ".git"
    if not git_dir.exists():
        return None
    head = git_dir / "HEAD"
    try:
        value = head.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if value.startswith("ref: "):
        ref = git_dir / value.removeprefix("ref: ")
        try:
            return ref.read_text(encoding="utf-8").strip()[:12]
        except OSError:
            return None
    return value[:12]


def credential_state(mode: str) -> dict[str, dict[str, bool | str]]:
    required = {
        "codex_openai": mode in {"live_codex", "production"},
        "diffusiongemma_nim": mode in {"live_diffusiongemma", "production"},
        "provider_oauth": mode in {"live_provider", "production"},
    }
    env_names = {
        "codex_openai": "OPENAI_API_KEY",
        "diffusiongemma_nim": "NVIDIA_API_KEY",
        "provider_oauth": "CALENDAR_PROVIDER_OAUTH_READY",
    }
    return {
        key: {
            "required": is_required,
            "configured": bool(os.environ.get(env_names[key])),
            "source": "environment" if os.environ.get(env_names[key]) else "missing",
        }
        for key, is_required in required.items()
    }


def runtime_report(
    *,
    mode: str,
    run_dir: Path,
    observation_path: Path,
    profile_path: Path,
    session_id: str,
    backends: RuntimeBackends | None = None,
) -> dict[str, object]:
    backends = backends or RuntimeBackends()
    requested_mode = (mode or "fixture").strip().lower().replace("-", "_")
    valid_mode = requested_mode in KNOWN_MODES
    effective_mode = requested_mode if valid_mode else "invalid"
    uses_fixture = observation_path.name.startswith("sample_") or profile_path.name.startswith("sample_")
    blockers: list[str] = []
    if not valid_mode:
        blockers.append(f"invalid runtime mode requested: {requested_mode}")
    if effective_mode in LIVE_MODES:
        if uses_fixture:
            blockers.append("live-targeted mode is using sample fixture data")
        if backends.kernel == "SwiftKernelStub":
            blockers.append("live-targeted mode is using SwiftKernelStub")
        if backends.codex == "deterministic_codex_tool_planner" and effective_mode in {"live_codex", "production"}:
            blockers.append("live Codex mode is using deterministic planner")
        if backends.diffusiongemma == "heuristic_diffusiongemma_policy" and effective_mode in {"live_diffusiongemma", "production"}:
            blockers.append("live DiffusionGemma mode is using heuristic policy")
        if backends.provider == "local_stub" and effective_mode in {"live_provider", "production"}:
            blockers.append("live provider mode is using local_stub provider")
    return {
        "runtime_mode": effective_mode,
        "requested_runtime_mode": requested_mode,
        "valid_runtime_mode": valid_mode,
        "mode_label": _mode_label(effective_mode, requested_mode=requested_mode),
        "fixture_mode": effective_mode == "fixture",
        "production_target": effective_mode == "production",
        "live_target": effective_mode in LIVE_MODES,
        "live_blockers": blockers,
        "backends": backends.to_dict(),
        "credentials": credential_state(effective_mode),
        "fixture_paths": {
            "observation": str(observation_path),
            "profile": str(profile_path),
            "uses_sample_fixtures": uses_fixture,
        },
        "run_dir": str(run_dir),
        "app_bundle_path": app_bundle_path(),
        "build_id": build_id(),
        "process": {
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "session_id": session_id,
        },
    }


def runtime_is_release_safe(report: dict[str, object]) -> bool:
    return not bool(report.get("live_blockers"))


def _mode_label(mode: str, *, requested_mode: str | None = None) -> str:
    if mode == "invalid":
        return f"Invalid runtime mode: {requested_mode or 'unknown'}"
    return {
        "fixture": "Fixture mode",
        "swift_ipc": "Swift IPC mode",
        "live_codex": "Live Codex mode",
        "live_diffusiongemma": "Live DiffusionGemma mode",
        "live_provider": "Live provider mode",
        "production": "Production mode",
    }.get(mode, "Fixture mode")
