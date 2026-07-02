#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.providers.apple_eventkit import AppleEventKitProvider  # noqa: E402


def main() -> None:
    provider = AppleEventKitProvider(state_path=ROOT / "runs" / "eventkit_e2e" / "apple_eventkit_provider.json")
    health = provider.health_status()
    report = {
        "provider": provider.provider_id,
        "health": health,
        "bridge": os.environ.get("CALENDAR_PILOT_EVENTKIT_BRIDGE", ""),
        "require_live": os.environ.get("CALENDAR_PILOT_REQUIRE_EVENTKIT", "") in {"1", "true", "TRUE", "yes"},
    }
    out = ROOT / "runs" / "eventkit_e2e" / "eventkit_health.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if report["require_live"] and not health.get("configured"):
        raise SystemExit(f"EventKit live provider is not configured: {health}")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
