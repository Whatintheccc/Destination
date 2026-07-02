# Validation

Updated repo generated on 2026-07-02 from the `calendar-pilot-updated 2` snapshot plus `SYSTEM_FRAMEWORK.md`.

## Checks run

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Result: 140 tests passed, 9 skipped.

```bash
swift test --package-path packages/CalendarPilotKernel
```

Result: 17 tests passed, 0 failures.

```bash
PYTHONPATH=src python3 scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl
make evidence-bundle
```

Result: invariant check passed; generated evidence bundle passed the zero-dependency secret scan.

## Notes

Browser E2E, real macOS Finder launch, live Codex, live NIM, and live EventKit mutation were not run in this Linux/container environment. The repo includes the same macOS app/EventKit paths and now adds CI/evidence scaffolding, but local live-provider validation should still be run on macOS.
