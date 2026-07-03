> Historical note: this document is retained as implementation archaeology. The current contract truth lives in `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/LAB.md`, `docs/PROVIDER_BOUNDARY.md`, and `docs/SELF_PLAY.md`.

# Deferred Work Implementation Pass

This pass completes the deferred items named in `ML-E2E.md` and in the previous System Framework pass. The goal is not to change the product split; it is to make the acting, learning, self-play, and UI surfaces share one inspectable data spine.

## Implemented in this pass

- **Full ActionLifecycle extraction**: `environment/action_lifecycle.py` now owns prepare, simulate, stage, commit, verify, reward, and undo transitions. `CodexToolRuntime` delegates Swift/provider-facing actuation to it, and every transition emits an ActionEnvelope-backed replay row.
- **Full SessionStore extraction**: `environment/session_store.py` owns state, latest snapshot, session manifest, and replay compaction paths. `DogfoodSessionState.persist()` and restore now route through that store.
- **Glass Cockpit ES-module frontend**: `frontend/static/index.html` now loads `frontend/static/js/main.js`, which renders Operate/Observe/Learn/Lab/Authority surfaces from `/api/view` and `/api/events` without templated `innerHTML` for dynamic strings. The old `app.js` is retained as a legacy reference but is no longer loaded by the page.
- **EventKit self-play sandbox enforcement in Swift**: the EventKit bridge accepts `sandbox_calendar_id` / `CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID` and rejects mutations or rollback payloads outside the sandbox below the Python layer.
- **Contract golden vectors and KernelServer roundtrip**: `contracts/testdata/kernel_vectors/*.json`, `scripts/run_contract_vectors.py`, and the `contract_roundtrip` KernelServer command exercise Python stub and optional Swift IPC contract parity.
- **Provider-backed self-play execution**: `SelfPlayRunner` now supports provider-backed action backends by routing non-stub episodes through `ActionLifecycle` with backend grant policy.
- **Tier-6 plan graph with compound rollback ordering**: `environment/plan_graph.py` defines a plan graph and rollback order. Python providers and the stub kernel expand `auto_apply_plan` through this plan graph metadata.
- **Right-moment temporal controller**: `diffusiongemma/temporal_controller.py` converts right-moment decisions into explicit act/stage/wait/digest/refresh modes and records temporal staleness/exposure costs on candidates.
- **Tuning/frontier viewer polish**: `scripts/run_frontier_diff.py`, `scripts/make_scorecard.py`, and new Make targets produce frontier diffs and ML scorecards that the Glass Cockpit Learn surface can display.

## Validation

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python3 scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl
PYTHONPATH=src python3 scripts/run_contract_vectors.py
PYTHONPATH=src python3 scripts/run_frontier_diff.py --out /tmp/frontier_diff.json
PYTHONPATH=src python3 scripts/make_scorecard.py --replay tests/fixtures/replay_golden.jsonl --frontier-diff /tmp/frontier_diff.json --out /tmp/scorecard.json
```

Local results in this container:

```text
Python: 147 tests OK, 10 skipped
Swift: 17 tests OK
Golden replay invariant check: OK
Contract vectors: OK for Python stub; Swift IPC remains opt-in
Frontier diff + scorecard: generated successfully
```

Browser E2E was attempted but the container does not have Playwright's Chromium binary installed, so the browser launch could not run here.