
# Swift Runtime Materialization Pass

This pass turns the previous transformation into a more durable local app/repo baseline.

## Entry point

`CalendarPilotMacApp` is now a real Swift package target under:

```text
packages/CalendarPilotKernel/Sources/CalendarPilotMacApp/main.swift
```

The app bundle launch path is now:

```text
CalendarPilot.app
  -> CalendarPilotMacApp
  -> launch_state.json
  -> Python frontend server
  -> CalendarPilotKernelServer
  -> CalendarPilotEventKitBridge
  -> WKWebView localhost frontend
```

The launch manifest is mirrored on the Python side by:

```text
src/calendar_pilot/frontend/launch.py
src/calendar_pilot/frontend/session_manager.py
```

Every Finder/CLI/browser run now has a stable `launch_id`, `build_id`, `run_dir`, runtime mode, server port, Swift kernel path, EventKit bridge path, and app root.

## Runtime consolidation

`RuntimeProfile` and `RUNTIME_REGISTRY` now live in `calendar_pilot.frontend.runtime`. Runtime reports include the selected profile, expected backends, required credentials, live/prod target flags, and blockers. The frontend server now routes through `SessionManager` instead of ad hoc singleton creation.

## Swift hardening

Swift now has deterministic `StableID` identifiers rather than process-random `hashValue` IDs for grants, receipts, staged receipts, preview receipts, undo receipts, and rollback handles.

`CalendarPilotEventKitBridge` can be present in the Swift package on Linux CI without failing `swift test`; on macOS it still compiles the real EventKit bridge and keeps the Info.plist linker setting macOS-only.

## Acting materialization

Tier 5 social actuation and Tier 6 `auto_apply_plan` are no longer hard-coded kernel-v1 dead ends. They are scoped product-policy paths:

```text
Tier 5 social mutation -> requires commit_social / social scope
Tier 6 auto_apply_plan -> requires auto_apply_plan scope and tier 6
```

`auto_apply_plan` can expand nested `plan_actions` from string metadata and materialize those typed atomic actions through the same Swift receipt path.

## ML generation

`LiveDiffusionGemmaPolicy` now prefers NIM/DiffusionGemma frontier generation over local heuristic candidates. The default live client calls `generate_candidate_frontier(...)` and expects typed `CandidateCalendarAction` objects. The old ranker path remains only as compatibility for injected test clients.

## Validation

Validated in this repo snapshot:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
```

Current results:

```text
Python: 87 tests OK, 8 skipped
Swift: 17 tests OK
```
