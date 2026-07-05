#!/usr/bin/env python3
from __future__ import annotations

import sys

from run_browser_e2e import run_live_browser_check


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_external_browser_flow.py <base-url> <artifact-dir>")
    run_live_browser_check(sys.argv[1], sys.argv[2])
