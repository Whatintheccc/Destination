"""Environment substrate for CalendarPilot.

The first pass is intentionally a strangler layer: objects are small, typed, and
can delegate to the existing DogfoodSessionState/CodexToolRuntime machinery while
new call sites migrate onto them.
"""

from .taxonomy import CanonicalIntent, normalize_intent
from .trace import TRACE_BUS, TraceBus, TraceEvent
from .envelope import ActionEnvelope, rollback_state_from_receipt
from .invariants import Violation, check_replay
from .selfplay_backends import SelfPlayActionBackend, SelfPlayBackendPolicy, BACKEND_POLICIES

__all__ = [
    "CanonicalIntent",
    "normalize_intent",
    "TRACE_BUS",
    "TraceBus",
    "TraceEvent",
    "ActionEnvelope",
    "rollback_state_from_receipt",
    "Violation",
    "check_replay",
    "SelfPlayActionBackend",
    "SelfPlayBackendPolicy",
    "BACKEND_POLICIES",
]
