from __future__ import annotations

from typing import Any

from calendar_pilot.types import CodexToolName


COMPARE_REQUIRED_TOOLS = {
    CodexToolName.SIMULATE_ACTION_PROGRAM.value,
    CodexToolName.STAGE_ACTION_PACKET.value,
    CodexToolName.REQUEST_COMMIT.value,
}
TERMINAL_TOOLS = {
    CodexToolName.STAGE_ACTION_PACKET.value,
    CodexToolName.REQUEST_COMMIT.value,
    CodexToolName.REQUEST_UNDO.value,
}


def tool_name_value(item: Any) -> str:
    value = getattr(item, "tool_name", item)
    if isinstance(value, CodexToolName):
        return value.value
    if isinstance(item, dict):
        value = item.get("tool_name") or item.get("tool") or value
    return str(value or "")


def validate_tool_plan_order(calls: list[Any]) -> list[str]:
    if not calls:
        return ["calls must be a non-empty list when supplied"]
    errors: list[str] = []
    seen_frontier = False
    seen_compare = False
    terminal: str | None = None
    for idx, item in enumerate(calls):
        if not hasattr(item, "tool_name") and not isinstance(item, dict):
            errors.append(f"calls[{idx}] is not an object")
            continue
        tool = tool_name_value(item)
        if terminal is not None:
            errors.append(f"{tool} appears after terminal tool {terminal}")
        if tool == CodexToolName.GENERATE_CANDIDATE_FRONTIER.value:
            seen_frontier = True
        if tool == CodexToolName.COMPARE_CANDIDATES.value:
            if not seen_frontier:
                errors.append("compare_candidates appeared before generate_candidate_frontier")
            seen_compare = True
        if tool in COMPARE_REQUIRED_TOOLS and not seen_compare:
            errors.append(f"{tool} appeared before compare_candidates")
        if tool in TERMINAL_TOOLS:
            terminal = tool
    return errors
