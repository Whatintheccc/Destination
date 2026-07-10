from __future__ import annotations

from pathlib import Path
from typing import Any


P13_5_EVENTKIT_CASES = {
    "eventkit_managed_binding_state",
    "eventkit_managed_ownership",
    "eventkit_managed_runtime_commit",
    "eventkit_managed_runtime_undo",
    "eventkit_managed_durable_owner",
    "eventkit_managed_live_contract",
}


def collect_managed_eventkit_retirement_case(
    case: str,
    *,
    scenario_dir: Path,
    root: Path,
) -> dict[str, Any] | None:
    """Reserved evaluator aperture for the separately declared evidence fixture.

    The frozen predicate, not candidate code, defines success. Until an independent
    fixture is bound here, every selected managed-EventKit retirement scenario remains
    evidence-derived ``not_reached``.
    """

    if case not in P13_5_EVENTKIT_CASES:
        raise ValueError(f"unknown managed EventKit retirement case: {case}")
    del scenario_dir, root
    return None
