
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform


ROOT = Path(__file__).resolve().parents[3]
KNOWN_MODES = {"fixture", "auto", "swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}
LIVE_MODES = {"auto", "swift_ipc", "live_codex", "live_diffusiongemma", "live_provider", "production"}
LIVE_CODEX_MODES = {"auto", "live_codex", "production"}
LIVE_DIFFUSIONGEMMA_MODES = {"live_diffusiongemma", "production"}
LIVE_PROVIDER_MODES = {"live_provider", "production"}
MODES_REQUIRING_NON_FIXTURE_DATA = {"live_provider", "production"}
SUBSCRIPTION_AUTH_MODES = {"chatgpt", "chatgptAuthTokens", "agentIdentity", "personalAccessToken"}
API_KEY_AUTH_MODES = {"apikey", "apiKey", "api_key"}


@dataclass(frozen=True)
class RuntimeProfile:
    mode: str
    label: str
    kernel: str
    codex: str
    diffusiongemma: str
    provider: str
    required_credentials: tuple[str, ...] = ()
    live_target: bool = False
    production_target: bool = False
    requires_non_fixture_data: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "label": self.label,
            "expected_backends": {
                "kernel": self.kernel,
                "codex": self.codex,
                "diffusiongemma": self.diffusiongemma,
                "provider": self.provider,
            },
            "required_credentials": list(self.required_credentials),
            "live_target": self.live_target,
            "production_target": self.production_target,
            "requires_non_fixture_data": self.requires_non_fixture_data,
        }


RUNTIME_REGISTRY: dict[str, RuntimeProfile] = {
    "fixture": RuntimeProfile("fixture", "Fixture mode", "SwiftKernelStub", "deterministic_codex_tool_planner", "heuristic_diffusiongemma_policy", "deterministic_fixture_provider"),
    "auto": RuntimeProfile("auto", "Auto assistant", "SwiftKernelIPCClient", "live_codex_app_server", "nvidia_nim_or_heuristic_diffusiongemma_policy", "apple_eventkit_or_deterministic_fixture_provider", required_credentials=("codex_subscription",), live_target=True),
    "swift_ipc": RuntimeProfile("swift_ipc", "Swift IPC mode", "SwiftKernelIPCClient", "deterministic_codex_tool_planner", "heuristic_diffusiongemma_policy", "deterministic_fixture_provider", live_target=True),
    "live_codex": RuntimeProfile("live_codex", "Live Codex mode", "SwiftKernelIPCClient", "live_codex_app_server", "heuristic_diffusiongemma_policy", "deterministic_fixture_provider", required_credentials=("codex_subscription",), live_target=True),
    "live_diffusiongemma": RuntimeProfile("live_diffusiongemma", "Live DiffusionGemma mode", "SwiftKernelIPCClient", "deterministic_codex_tool_planner", "nvidia_nim_diffusiongemma_policy", "deterministic_fixture_provider", required_credentials=("diffusiongemma_nim",), live_target=True),
    "live_provider": RuntimeProfile("live_provider", "Live provider mode", "SwiftKernelIPCClient", "deterministic_codex_tool_planner", "heuristic_diffusiongemma_policy", "apple_eventkit", required_credentials=("provider_oauth",), live_target=True, requires_non_fixture_data=True),
    "production": RuntimeProfile("production", "Production mode", "SwiftKernelIPCClient", "live_codex_app_server", "nvidia_nim_diffusiongemma_policy", "apple_eventkit", required_credentials=("codex_subscription", "diffusiongemma_nim", "provider_oauth"), live_target=True, production_target=True, requires_non_fixture_data=True),
}


def runtime_profile(mode: str) -> RuntimeProfile | None:
    return RUNTIME_REGISTRY.get((mode or "fixture").strip().lower().replace("-", "_"))


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
        "codex_subscription": mode in {"auto", "live_codex", "production"},
        "diffusiongemma_nim": mode in {"live_diffusiongemma", "production"},
        "provider_oauth": mode in {"live_provider", "production"},
    }
    env_names = {
        "codex_subscription": "CODEX_ACCESS_TOKEN",
        "diffusiongemma_nim": "NVIDIA_API_KEY",
        "provider_oauth": "CALENDAR_PROVIDER_OAUTH_READY",
    }
    state: dict[str, dict[str, bool | str]] = {}
    for key, is_required in required.items():
        if key == "codex_subscription":
            auth = codex_subscription_auth_state()
            state[key] = {
                "required": is_required,
                "configured": bool(auth["configured"]),
                "source": str(auth["source"]),
                "status": str(auth["status"]),
                "auth_method": str(auth["auth_method"]),
            }
            continue
        if key == "diffusiongemma_nim":
            configured, source = _nim_credential_source()
            state[key] = {
                "required": is_required,
                "configured": configured,
                "source": source,
                "status": "configured" if configured else "missing_credential",
            }
            continue
        state[key] = {
            "required": is_required,
            "configured": bool(os.environ.get(env_names[key])),
            "source": "environment" if os.environ.get(env_names[key]) else "missing",
            "status": "configured" if os.environ.get(env_names[key]) else "missing_credential",
        }
    return state


def _nim_credential_source() -> tuple[bool, str]:
    for key in ["CALENDAR_PILOT_NIM_API_KEY", "NVIDIA_API_KEY", "NIM_API_KEY"]:
        if os.environ.get(key):
            return True, key
    return False, "missing"


def codex_subscription_auth_state() -> dict[str, bool | str]:
    if os.environ.get("CODEX_ACCESS_TOKEN"):
        return {"configured": True, "source": "environment", "status": "configured", "auth_method": "CODEX_ACCESS_TOKEN"}
    path = _codex_auth_file()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"configured": False, "source": "auth_cache", "status": "invalid_credential", "auth_method": "unreadable"}
        mode = str(data.get("auth_mode") or data.get("authMode") or "")
        if mode in SUBSCRIPTION_AUTH_MODES:
            return {"configured": True, "source": "auth_cache", "status": "configured", "auth_method": mode}
        if mode in API_KEY_AUTH_MODES or data.get("OPENAI_API_KEY"):
            return {"configured": False, "source": "auth_cache", "status": "wrong_auth_method", "auth_method": mode or "apiKey"}
        return {"configured": False, "source": "auth_cache", "status": "missing_credential", "auth_method": mode or "missing"}
    return {"configured": False, "source": "missing", "status": "missing_credential", "auth_method": "missing"}


def _codex_auth_file() -> Path:
    if os.environ.get("CALENDAR_PILOT_CODEX_AUTH_FILE"):
        return Path(os.environ["CALENDAR_PILOT_CODEX_AUTH_FILE"])
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "auth.json"


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
    setup_notes: list[str] = []
    if not valid_mode:
        blockers.append(f"invalid runtime mode requested: {requested_mode}")
    if effective_mode in LIVE_MODES:
        credentials = credential_state(effective_mode)
        for key, state in credentials.items():
            if state["required"] and not state["configured"]:
                if state.get("status") == "wrong_auth_method":
                    blockers.append(f"required credential wrong auth method: {key}")
                else:
                    blockers.append(f"required credential missing: {key}")
        if uses_fixture and effective_mode in MODES_REQUIRING_NON_FIXTURE_DATA:
            blockers.append("live provider/production mode is using sample fixture data")
        if backends.kernel == "SwiftKernelStub":
            blockers.append(f"{effective_mode} mode is using SwiftKernelStub")
        if effective_mode == "swift_ipc" and backends.kernel != "SwiftKernelIPCClient":
            blockers.append("swift_ipc mode is not using SwiftKernelIPCClient")
        if backends.codex == "deterministic_codex_tool_planner" and effective_mode in LIVE_CODEX_MODES:
            blockers.append("live Codex mode is using deterministic planner")
        if backends.diffusiongemma == "heuristic_diffusiongemma_policy" and effective_mode in LIVE_DIFFUSIONGEMMA_MODES:
            blockers.append("live DiffusionGemma mode is using heuristic policy")
        if effective_mode == "auto" and backends.diffusiongemma == "heuristic_diffusiongemma_policy":
            setup_notes.append("DiffusionGemma is running in local heuristic policy mode for auto runtime")
        if backends.provider == "local_stub" and effective_mode in LIVE_PROVIDER_MODES:
            blockers.append("live provider mode is using local_stub provider")
        if effective_mode == "auto" and backends.provider != "apple_eventkit":
            setup_notes.append("Calendar provider is running through the deterministic local adapter for auto runtime")
    return {
        "runtime_mode": effective_mode,
        "requested_runtime_mode": requested_mode,
        "valid_runtime_mode": valid_mode,
        "mode_label": _mode_label(effective_mode, requested_mode=requested_mode),
        "profile": runtime_profile(effective_mode).to_dict() if runtime_profile(effective_mode) else None,
        "fixture_mode": effective_mode == "fixture",
        "production_target": effective_mode == "production",
        "live_target": effective_mode in LIVE_MODES,
        "live_blockers": blockers,
        "setup_notes": setup_notes,
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
            "launch_id": os.environ.get("CALENDAR_PILOT_LAUNCH_ID", ""),
            "launch_port": os.environ.get("CALENDAR_PILOT_LAUNCH_PORT", ""),
            "launch_requested_port": os.environ.get("CALENDAR_PILOT_LAUNCH_REQUESTED_PORT", ""),
        },
    }


def runtime_is_release_safe(report: dict[str, object]) -> bool:
    return not bool(report.get("live_blockers"))


def _mode_label(mode: str, *, requested_mode: str | None = None) -> str:
    if mode == "invalid":
        return f"Invalid runtime mode: {requested_mode or 'unknown'}"
    profile = runtime_profile(mode)
    return profile.label if profile else "Fixture mode"
