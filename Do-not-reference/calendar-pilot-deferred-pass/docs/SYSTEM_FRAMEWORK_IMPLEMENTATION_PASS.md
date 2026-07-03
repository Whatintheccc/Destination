# System Framework Implementation Pass

This pass records the first practical object-substrate implementation slice: evidence integrity, canonical learning keys, replay visibility, and the environment seams. It intentionally did not complete the Glass Cockpit frontend or full ActionLifecycle extraction; it created the spine those phases could attach to without blocking recommendation dogfooding.

## Implemented

- Added `calendar_pilot.environment` with protocol/object seams for trace, envelope, router, taxonomy, invariants, filesystem persistence, and self-play backend policy.
- Added per-session locking and `state_version` so `ThreadingHTTPServer` polling and mutation paths observe monotonic state.
- Replaced bare JSON state writes with atomic writes and made replay append-capable while keeping compaction support.
- Added canonical intent taxonomy so model prose intents normalize before replay reduction and policy tuning.
- Added `router_decision`, `model_generation_rejection`, and `envelope_transition` replay record paths.
- Promoted the existing Codex action envelope into a v2-compatible shape while retaining the legacy v1 schema marker for compatibility.
- Added `RewardEvent.provenance` for future reward-head decomposition without fragmenting the reducer yet.
- Added `/api/view`, `/api/events`, and `/api/trace/{trace_id}` for the Glass Cockpit migration path.
- Added `FrontendProjector` as a delegating projector over the existing snapshot builder.
- Added `check_invariants.py`, `run_secret_scan.py`, and CI evidence-bundle hooks.
- Added self-play backend policy definitions so future Swift/EventKit self-play cannot inherit stub-only self-issued confirmed grants.

## Still intentionally deferred

- Full ActionLifecycle extraction.
- Provider-backed self-play execution.
- EventKit sandbox allowlist enforced in Swift.
- Glass Cockpit ES-module frontend replacement.
- Contract golden vectors and KernelServer roundtrip command.
- Tier-6 plan graph with compound rollback ordering.

## Validation

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python3 scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl
PYTHONPATH=src python3 scripts/run_secret_scan.py --path /tmp/ci_evidence
```

Current local result for this pass:

```text
Python: 140 tests OK, 9 skipped
Swift: 17 tests OK
Invariant check: OK on golden replay
Secret scan: OK on generated evidence bundle
```

## Follow-up status

The deferred items listed above are implemented in `docs/DEFERRED_WORK_IMPLEMENTATION_PASS.md`. This document remains the evidence-integrity/object-substrate pass record; the follow-up pass owns the full ActionLifecycle/SessionStore/Glass Cockpit/self-play/provider/vector/temporal-controller implementation.
