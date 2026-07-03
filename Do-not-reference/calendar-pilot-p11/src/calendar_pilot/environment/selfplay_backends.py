from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SelfPlayActionBackend(str, Enum):
    STUB_FAST = "stub_fast"
    SWIFT_IPC_DETERMINISTIC = "swift_ipc_deterministic"
    SWIFT_IPC_EVENTKIT_SANDBOX = "swift_ipc_eventkit_sandbox"
    PRODUCTION_SHADOW = "production_shadow"


@dataclass(frozen=True)
class SelfPlayBackendPolicy:
    backend: SelfPlayActionBackend
    grant_issuance: str
    provider_writes: bool
    max_episodes: int
    requires_env_flag: str | None


BACKEND_POLICIES: dict[SelfPlayActionBackend, SelfPlayBackendPolicy] = {
    SelfPlayActionBackend.STUB_FAST: SelfPlayBackendPolicy(SelfPlayActionBackend.STUB_FAST, "self_issued", False, 100, None),
    SelfPlayActionBackend.SWIFT_IPC_DETERMINISTIC: SelfPlayBackendPolicy(SelfPlayActionBackend.SWIFT_IPC_DETERMINISTIC, "kernel_issued_sandbox", False, 50, None),
    SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX: SelfPlayBackendPolicy(
        SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX,
        "kernel_issued_sandbox",
        True,
        10,
        "CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX",
    ),
    SelfPlayActionBackend.PRODUCTION_SHADOW: SelfPlayBackendPolicy(SelfPlayActionBackend.PRODUCTION_SHADOW, "read_only", False, 20, "CALENDAR_PILOT_SELFPLAY_SHADOW"),
}