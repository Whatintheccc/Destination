

# CalendarPilot

Agentic calendar optimizer built from first principles around three components:

- **Swift / CalendarPilotKernel**: raw calendar kernel, write authority broker, action materializer, undo ledger, reward telemetry.
- **DiffusionGemma / Python policy layer**: raw-context modeling, persistent user biography, candidate action generation, right-moment prediction, reward scoring, and self-play.
- **Codex / Python executive layer**: goal dialogue, explanations, profile repair, clarification, and user-facing orchestration.

This repo intentionally implements the **agentic optimizer inversion** rather than the witness architecture. It allows raw-context modeling, persistent biography, proactive recommendations, calendar write authority, right-moment prediction, reward-driven recommendation, and self-play.

## What is in this repo

```text
calendar-pilot/
  packages/CalendarPilotKernel/     Swift package: calendar authority + actuation/staging kernel
  src/calendar_pilot/               Python package: DiffusionGemma + Codex + simulator
  src/calendar_pilot/providers/     Provider adapter interfaces for Google/Apple/Microsoft
  contracts/                        Canonical snake_case JSON contracts shared with Swift/Python
  tests/                            Python unit tests
  examples/                         Demo scripts and sample scenarios
  data/                             Sample calendar/profile fixtures
  docs/                             Architecture, API, self-play, and revision notes
  configs/                          Reward and autonomy config
```

## Quickstart

```bash
cd calendar-pilot
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m calendar_pilot.app demo --observation data/sample_calendar.json --replay-out runs/replay.jsonl
PYTHONPATH=src python3 scripts/train_offline_policy.py --replay runs/replay.jsonl --out runs/offline_policy_report.json
swift test --package-path packages/CalendarPilotKernel
swift run --package-path packages/CalendarPilotKernel CalendarPilotDemo
```

The demo performs this loop and can write replay JSONL for offline policy reduction:

```text
raw calendar observation
→ biography update
→ candidate action generation
→ reward/right-moment scoring
→ authority check
→ Swift-style materialization receipt
→ Codex explanation
→ synthetic reward event
```

## Architecture stance

CalendarPilot optimizes over candidate calendar futures:

```text
state S_t = raw calendar graph
          + event/entity graph
          + persistent biography
          + interaction history
          + notification/action/reward history
          + current context signals
          + future schedule forecast
```

The policy loop is:

```text
observe → model → imagine → act → learn
```

Swift acts as the deterministic kernel. DiffusionGemma models and proposes. Codex explains and negotiates.

## Autonomy tiers

| Tier | Name | Behavior |
|---:|---|---|
| 0 | Observe | Read state and build biography. |
| 1 | Recommend | Suggest actions only. |
| 2 | Draft | Stage changes for confirmation. |
| 3 | Auto-write reversible | Create/move low-risk user-owned blocks with undo. |
| 4 | Auto-write scoped | Act inside declared scopes. |
| 5 | Social actuation | RSVP/decline/negotiate/move meetings involving others. |
| 6 | Full optimizer | Broad delegated management. |

## Safety/control posture

Privacy is not the primary product doctrine here. The repo treats data access as an engineering/control surface:

- authority tiers bound blast radius;
- write receipts and undo handles make action recoverable;
- reward is decomposed into utility, acceptance, engagement, regret, interruption, and social risk;
- self-play adversaries search for high-regret and notification-fatigue policies;
- social actuation is gated separately from reversible user-owned writes;
- staged-vs-materialized receipts make non-write actions explicit;
- contract tests keep Python dataclasses, JSON schemas, and Swift Codable mirrors aligned.

## Status

This is a runnable reference implementation skeleton. It has working contracts, heuristics, self-play, tests, and a Swift kernel. It does **not** include production calendar provider OAuth, provider sync, real ML model serving, or external API credentials.


## Latest revision

See `docs/NEXT_FOCUS_REVISION.md` for the contract reconciliation, focus-mode policy bug fix, Swift actuation/staging depth, replay/training loop, provider boundary, biography maturation, and hygiene changes.


## Latest revision: Codex as tool-using executive

The current repo focuses on machine learning, machine acting, and self-play. The major change is that Codex is no longer just an explainer. It now has a bounded tool runtime:

```text
DiffusionGemma learns and proposes candidate futures.
Codex inspects, simulates, compares, stages, repairs, and requests.
Swift validates, writes, syncs, rolls back, denies, and audits.
```

New entry points:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --codex-tools \
  --self-play 3 \
  --replay-out runs/replay.jsonl

PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay runs/replay.jsonl \
  --out runs/offline_policy_report.json \
  --tuning-out runs/policy_tuning.json
```

Read `docs/CODEX_TOOL_EXECUTIVE.md` and `docs/ML_ACTING_SELF_PLAY_LOOP.md` for the new architecture.

## Latest revision: Authority grants and causal tool traces

This pass makes the Codex-executive route the default app path and hardens the machine-acting boundary.

```text
Codex plans and stages.
Swift issues authority grants, validates, writes, denies, and audits.
DiffusionGemma learns from the full trace instead of isolated reward rows.
```

Key changes:

- Python/Codex can no longer supply naked authority tiers as authority. Swift issues `AuthorityGrant` objects with max tier, scopes, expiry, and confirmation provenance.
- Swift rejects out-of-band tiers before materialization.
- Codex tool receipts now distinguish `simulated`, `stageable`, `requires_confirmation`, `denied`, and `committed` states.
- Swift `JSONValue` is recursive and lossless for nested tool payloads.
- The demo path is now Codex-first: inspect → candidate frontier → compare → simulate → stage or commit through Swift.
- Replay records shared causal/correlation IDs across tool calls, tool receipts, candidate decisions, Swift receipts, rewards, self-play episodes, denials, and adversary findings.
- Offline training consumes the causal trace and emits `PolicyTuning` that can change future policy ranking before right-moment decisions.

Run the current default path:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --self-play 2 \
  --replay-out runs/replay.jsonl \
  --commit

PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay runs/replay.jsonl \
  --out runs/offline_policy_report.json \
  --tuning-out runs/policy_tuning.json
```

Read `docs/SAFETY_CONTRACT_PASS.md` for the authority-grant, staging, replay, and contract-parity details.

## Latest revision: frontend control surface and hard authority boundary

This pass adds a small non-chat frontend and fixes the grant boundary bugs found in `calendar-pilot-executive 2`.

Frontend surfaces now treat machine learning and machine acting as first-class app state:

```text
calendar pressure map;
DiffusionGemma candidate futures;
reward/right-moment anatomy;
Swift acting queue;
authority-grant panel;
self-play failure modes;
learned-biography repair.
```

Generate and view the demo surface:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend --write-snapshot
# open frontend/static/index.html

PYTHONPATH=src python3 -m calendar_pilot.app frontend --serve
# then open http://127.0.0.1:8787
```

Boundary fixes:

- `CodexToolCall` now carries only `authority_grant_id`; embedded `AuthorityGrant` payloads are ignored.
- Python and Swift resolve authority from kernel-issued grant registries before stage/commit/undo.
- `confirmed_by_user` / `confirmedByUser` is enforced for commits and undo.
- Swift undo now checks grant registry, liveness, confirmation, scope, and rollback ledger.
- Safe private prep/focus writes can commit through the default Codex-executive path.
- People-affecting mutations still stage/deny rather than silently committing.
- Mixed packets with a write plus staged sidecar keep materialized status and rollback handles.
- `python3 -m pytest -q` now works without manually setting `PYTHONPATH`.


Optional Swift IPC boundary:

```bash
swift build --package-path packages/CalendarPilotKernel --product CalendarPilotKernelServer
# Python integrations can use SwiftKernelIPCClient to keep grants and commit/undo ledgers in the Swift process.
```

This is still not a real Google/Apple/Microsoft provider. It is the concrete kernel boundary for grant issuance, stage, commit, undo, and receipts. Provider tokens and provider truth remain future Swift/provider-adapter work.

Read `docs/FRONTEND_SURFACES.md` for the product split between chat, learning surfaces, acting surfaces, authority, self-play, and profile repair.

## Latest revision: Swift runtime materialization and live generation

This pass materializes the macOS/Swift entry point and closes the main consistency gap from the previous transformation.

Key changes:

- Added `CalendarPilotMacApp` as the app-bundle entry point. It writes `launch_state.json`, starts the Python frontend server, exposes the Swift kernel/EventKit bridge paths, and loads the local product UI in `WKWebView`.
- Added Python-side `LaunchConfig` and `SessionManager` so Finder, CLI, browser E2E, and release runs share the same launch/session manifest.
- Added `RuntimeProfile` / `RUNTIME_REGISTRY` so runtime modes, expected backends, credentials, and blockers are declared in one place.
- Replaced Swift process-random `hashValue` IDs with deterministic `StableID` IDs.
- Made Tier 5 social actuation and Tier 6 `auto_apply_plan` executable scoped product-policy paths instead of permanent kernel-v1 hard stops.
- Updated live DiffusionGemma/NIM to generate typed candidate frontiers directly. The old ranker path remains only for injected compatibility clients.
- Made the EventKit bridge compile-safe for Linux CI while preserving real EventKit behavior on macOS.

See `docs/SWIFT_RUNTIME_MATERIALIZATION_PASS.md`.


## Latest revision: System Framework implementation pass

This pass implements the first slice of `SYSTEM_FRAMEWORK.md`: the object-substrate seams, session evidence integrity, canonical intent keys, replay-visible router/model rejection/envelope records, invariant checking, and `/api/view` + `/api/events` + `/api/trace/{trace_id}` for the Glass Cockpit migration path.

Key implementation points:

- `src/calendar_pilot/environment/` now contains the delegating substrate: taxonomy, router, trace bus, envelope, invariants, self-play backend policy, protocol definitions, and atomic/append filesystem helpers.
- `DogfoodSessionState` now has a per-session `RLock` and monotonic `state_version`, with public mutators wrapped while the larger object split proceeds.
- Replay now supports `router_decision`, `model_generation_rejection`, and `envelope_transition` records, and the offline reducer keys policy tuning on canonical intents instead of model-written prose.
- `RewardEvent` carries a `provenance` field now, while reward-head splitting remains deferred until daily-driver data volume exists.
- CI now runs Python/Swift checks and produces a secret-scanned evidence bundle.

Read `docs/SYSTEM_FRAMEWORK_IMPLEMENTATION_PASS.md` for details.
