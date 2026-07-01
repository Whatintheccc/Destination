# CalendarPilot Dogfooding Framework

Status: working document
Primary audience: dogfood team, product engineering, runtime engineering
Source of truth: this file at repository root
Last reviewed: 2026-07-01

## Purpose

This document turns `calendar-pilot-frontend/` from a static reference surface into a dogfoodable product loop:

```text
goal -> inspect -> candidate frontier -> simulate -> stage/commit/deny -> undo -> feedback/reward -> replay -> policy tuning -> next run
```

The dogfood team should edit this document as the product changes. Every step below has room for status, owner, evidence, and acceptance criteria so the framework can serve as both roadmap and operating log.

## How We Arrived Here

The git history shows a clear shift from architecture exploration to a concrete control surface:

| Phase | Commits | What changed | Dogfood implication |
|---|---|---|---|
| Planning corpus | `f5f3da0` through `73d28a2` | The repo moved through plan-4/5/6/7/8 documents, a witness/controller debate, self-play notes, latency-bound revisions, and readme rewrites. | The product doctrine was debated before implementation: this is an agentic optimizer, not only a passive calendar witness. |
| Planning cleanup | `83b63e7`, `0df7ef7`, `d338a53` | Superseded plan files were removed and the planning corpus was retired. | The repo intentionally stopped being a document archive and made room for implementation. |
| CalendarPilot skeleton | `9f8327c` | Added the Python package, Swift kernel, contracts, sample calendar/profile fixtures, reward model, replay, self-play, tests, and docs. | Dogfood can start from runnable primitives rather than strategy docs. |
| Agent loop revision | `5de2534` | Added world-model signals, richer policy behavior, right-moment modeling, visible reward anatomy, and agent-loop tests. | Dogfood should inspect why a candidate exists, not just whether a recommendation appears. |
| Contracts/provider/replay hardening | `effa98d` | Added receipts, provider stubs, biography maturation, replay hardening, contract parity, and provider boundary docs. | Dogfood must exercise receipt and provider truth, not only UI display. |
| Codex tool executive | `835ce26` | Codex became a bounded tool runtime with inspect, frontier, simulate, compare, stage, commit, undo, replay, profile repair, autonomy, and denial tools. | The app flow should be tool-receipt driven rather than chat narrative driven. |
| Authority grants and safety | `7ae1640` | Swift-issued `AuthorityGrant` replaced naked authority tiers; replay gained causal IDs; reward contracts and safety tests landed. | Dogfood should treat authority as product state users can see and constrain. |
| Frontend and Swift IPC boundary | `b3e81b0` | Added `frontend/static`, frontend snapshot generation, frontend docs, Swift JSONL server, and `SwiftKernelIPCClient`. | The UI now exposes the right surfaces, but it is still static and not yet a complete product loop. |

Current state summary:

- `frontend/static/app.js` only fetches `frontend_state.sample.json` and renders panels.
- `src/calendar_pilot/frontend/server.py` only generates a demo snapshot and serves static files.
- `CodexToolRuntime` expects the stub-shaped kernel interface, while `SwiftKernelIPCClient` exposes an IPC-shaped interface.
- Provider adapters are explicit stubs and still throw for writes.
- Replay is trace-aware, but user feedback/reward capture is not exposed through the frontend.
- Tests cover contracts, planner/runtime behavior, static frontend snapshot state, replay, and Swift parity; there is no real browser E2E suite yet.

## Dogfood Doctrine

1. The dogfood product is the loop, not the screenshot.
2. Every visible control should create typed state: tool call, tool receipt, Swift receipt, reward event, profile patch, replay row, or policy tuning artifact.
3. The frontend should expose machine learning and machine acting directly: candidate futures, reward anatomy, authority, acting queue, self-play findings, replay, and profile repair.
4. Real provider OAuth should wait until deterministic fixture provider state proves idempotency, conflict truth, and rollback verification.
5. Higher autonomy is blocked until commit, undo, denial, feedback, and replay are all product journeys.

## Working Backlog

Use the status fields directly in this file.

Status values: `Not started`, `In progress`, `Blocked`, `Dogfood`, `Done`

### P0.1 Make The Frontend Interactive

Status: Dogfood
Owner:
Evidence: `frontend/static/app.js` now calls live `/api/*` endpoints; `frontend/static/index.html` has goal/profile controls; smoke-tested served UI API on `127.0.0.1:8790`.

`frontend/static/app.js` only fetches `frontend_state.sample.json` and renders panels. There are no goal inputs, approve/deny buttons, commit actions, undo controls, profile repair controls, or backend POSTs.

Required work:

- Add a goal input that creates a plan from live backend state.
- Add candidate controls for simulate, stage, approve/confirm, commit, deny, and explain denial.
- Add action queue controls for undo and receipt inspection.
- Add profile repair controls for propose patch, apply patch, and reject patch.
- Add feedback controls on committed, staged, denied, undone, and ignored actions.
- Replace static-only rendering with state refresh from the backend.
- Keep `frontend_state.sample.json` as demo fallback only.

Acceptance criteria:

- A dogfood user can enter "Make next week less chaotic" and see a new plan without regenerating a static file.
- Every button disables while its request is in flight and renders the returned receipt or denial.
- The UI shows `plan_id`, `authority_grant_id`, `candidate_id`, `receipt_id`, `rollback_handle_id`, and `trace_id` when available.
- A failed POST produces a visible, structured error and does not corrupt local state.

### P0.2 Add A Stateful Frontend/Backend API

Status: Dogfood
Owner:
Evidence: `calendar_pilot.frontend.server` exposes `/api/state`, `/api/plans`, candidate simulate/stage/commit, receipt confirm, undo, profile patch, denial explanation, replay, feedback, and reset. `DogfoodSessionState` persists replay/session/provider state under `runs/dogfood/`.

`server.py` is just snapshot generation plus static serving. Add endpoints for: create plan, stage, confirm, commit, undo, profile patch, denial explanation, replay trace, and feedback/reward.

Minimum endpoint set:

| Endpoint | Method | Purpose |
|---|---:|---|
| `/api/state` | `GET` | Return current frontend snapshot plus session metadata. |
| `/api/plans` | `POST` | Create a Codex executive plan from `{goal, authority_tier, commit}`. |
| `/api/candidates/{candidate_id}/simulate` | `POST` | Run `simulate_action_program`. |
| `/api/candidates/{candidate_id}/stage` | `POST` | Run `stage_action_packet`. |
| `/api/candidates/{candidate_id}/commit` | `POST` | Run `request_commit` with confirmed authority. |
| `/api/receipts/{receipt_id}/confirm` | `POST` | Mark a staged/confirmation-required receipt as user confirmed and continue. |
| `/api/undo` | `POST` | Run `request_undo` from `{rollback_handle_id}`. |
| `/api/profile/patch/propose` | `POST` | Run `propose_profile_patch`. |
| `/api/profile/patch/apply` | `POST` | Run `apply_profile_patch` with explicit confirmation. |
| `/api/denials/explain` | `POST` | Run `explain_swift_denial`. |
| `/api/replay` | `GET` | Query replay by trace, candidate, receipt, or session. |
| `/api/feedback` | `POST` | Create and attach a `RewardEvent`. |

Implementation notes:

- Start with an in-memory `DogfoodSessionState` and persist JSON snapshots under `calendar-pilot-frontend/runs/dogfood/`.
- Store observation, biography, runtime, planner, latest plan, current snapshot, replay buffer, authority grants, and fixture provider state per session.
- Return typed JSON from dataclass `to_dict()` methods rather than ad hoc response strings.
- Add a small API test layer before browser E2E.

Acceptance criteria:

- Restarting the server can reload the latest dogfood session from disk.
- All mutating endpoints append to replay or return an explicit reason why they did not.
- API responses are stable enough for browser tests and future mobile surfaces.

### P0.3 Wire Codex Runtime To Real Swift IPC

Status: Dogfood
Owner:
Evidence: `CalendarKernel.preview` and JSONL `preview` RPC added; `SwiftKernelIPCClient` now implements the stub-shaped runtime methods while keeping Swift-side grant resolution authoritative.

`SwiftKernelIPCClient` works directly, but `CodexToolRuntime` still expects the stub-shaped interface. Make IPC client satisfy the same kernel interface or add an adapter, then run planner paths through compiled Swift.

Required work:

- Define a Python `KernelClient` shape used by `CodexToolRuntime`.
- Add a `SwiftKernelIPCAdapter` or update `SwiftKernelIPCClient` so it supports:
  - `issue_authority_grant`
  - `resolve_authority_grant`
  - `preview_candidate`
  - `stage_candidate(... authority_grant=...)`
  - `authorize_and_materialize(... authority_grant=...)`
  - `request_undo(... authority_grant=..., requested_authority_tier=...)`
  - `is_people_affecting_mutation`
- Add an IPC `preview` operation or a no-write simulation path that preserves the same semantics as the stub.
- Cache issued grant metadata in Python only for display; authority resolution must still happen in Swift.
- Ensure Swift process lifecycle, timeout, stderr capture, and cleanup are testable.

Acceptance criteria:

- `CodexToolPlanner(runtime=CodexToolRuntime(kernel=SwiftKernelIPCAdapter(...)))` can run inspect -> frontier -> compare -> simulate -> stage/commit through the Swift process.
- A forged embedded grant is still ignored.
- Commit and undo use the Swift-held grant registry and undo ledger.
- Integration tests can be skipped when Swift is unavailable, but pass on machines with Swift installed.

### P0.4 Add Fixture Provider State

Status: Dogfood
Owner:
Evidence: `FixtureCalendarProvider` persists provider state, external IDs, idempotency records, conflict truth, and rollback snapshots; `tests/test_dogfood_p0.py` verifies idempotency and single-use rollback.

Provider adapters still throw/not-implemented. Add a deterministic provider with persisted calendar state, external IDs, idempotency, conflict truth, and rollback verification before real OAuth.

Required work:

- Add a fixture provider behind the same ownership boundary intended for Google/Apple/Microsoft.
- Persist provider state to a JSON or SQLite store under `calendar-pilot-frontend/runs/fixture_provider/`.
- Track external IDs separately from local candidate/action IDs.
- Add idempotency keys for create, move, delete, commit, and undo.
- Make conflict detection read provider truth, not only the original observation.
- Verify rollback by comparing pre/post provider state checksums.
- Support deterministic reset for tests and dogfood scenarios.

Acceptance criteria:

- Create/move/delete changes fixture provider state and returns stable external IDs.
- Replaying the same idempotency key returns the same result without duplicate events.
- Conflict truth changes after writes and is visible in subsequent planning.
- Undo restores provider state and emits a verified rollback receipt.
- Real OAuth work remains blocked until fixture provider rollback passes repeatedly.

### P1.5 Turn Undo Into A Product Journey

Status: Dogfood
Owner:
Evidence: Undo now appends a persistent undo journey with before/after provider checksums, provider rollback status, linked original receipt, and undo reward event; browser E2E exercises stage -> confirm -> commit -> undo.

Undo exists as a primitive and appears as text in the UI, but no flow exercises commit -> undo -> updated receipt -> replay.

Required work:

- Add an undo button for committed receipts with rollback handles.
- Show before/after state for the original commit and the undo result.
- Render the updated receipt status as `reverted` or denied with explanation.
- Append undo tool calls, Swift receipts, and reward events to replay.
- Add a post-undo prompt that asks whether the original action was wrong, premature, or no longer needed.

Acceptance criteria:

- Dogfood can commit a safe private write, undo it, and see the fixture provider state revert.
- The same rollback handle cannot be reused successfully.
- Replay links the original commit and undo through causal IDs.
- Offline policy training can distinguish "accepted then undone" from "denied before write".

### P1.6 Capture User Feedback/Reward

Status: Dogfood
Owner:
Evidence: Acting queue feedback now captures accepted/useful/wrong/not-needed/edited/undone/ignored/dismissed/conflict controls, persists feedback history, attaches `RewardEvent`s, and updates training rows/biography.

Replay is trace-aware, but training rows still require attached rewards. The frontend needs feedback controls so committed/staged/denied user actions can become learning data.

Required work:

- Add feedback controls: useful, wrong, not needed, too interruptive, accepted, edited, undone, ignored, dismissed, downstream conflict.
- Add optional free-text reason and structured reason tags.
- Convert feedback into `RewardEvent` and attach it to the relevant receipt/candidate/trace.
- Show reward impact in the replay panel and next policy report.
- Update biography from reward where appropriate, without silently overwriting explicit profile corrections.

Acceptance criteria:

- Every staged, committed, denied, undone, or ignored action can receive feedback.
- `ReplayBuffer.training_table()` produces rows after a dogfood session without synthetic self-play rewards.
- `scripts/train_offline_policy.py` shows nonzero training rows and intent adjustments from real dogfood feedback.
- The UI makes it clear whether feedback changed policy tuning, biography, both, or neither.

### P1.7 Add Real Browser E2E After API Controls Exist

Status: Dogfood
Owner:
Evidence: `scripts/run_browser_e2e.py` starts the live API server and runs `scripts/browser_e2e.spec.mjs` through Playwright over goal -> stage -> confirm -> commit -> undo -> feedback -> training rows.

Current browser E2E can only assert static rendering. Once controls exist, test: goal -> candidate -> stage/confirm -> commit -> undo -> replay/training.

Required work:

- Add Playwright tests for the live server, not `file://` static HTML.
- Seed deterministic fixture state before each test.
- Cover happy path, denial path, conflict path, undo path, profile repair path, and feedback path.
- Capture screenshots or traces for failed runs.

Acceptance criteria:

- Browser test can create a goal, choose a candidate, stage it, confirm it, commit it, undo it, and see replay rows update.
- Browser test can trigger a social mutation denial and request a denial explanation.
- Browser test can submit feedback and verify training rows increase.
- Browser E2E runs in CI after unit and Swift tests.

## P2 Product Closure

### P2.8 Make Denials Actionable

Status: Not started
Owner:
Evidence:

Required work:

- Render denial reason, authority grant, affected action types, and suggested next control.
- Add "narrow scope", "stage instead", "ask for confirmation", and "repair profile" follow-ups where applicable.
- Group denials by cause in the dogfood dashboard.

Acceptance criteria:

- A denied social mutation leads to a staged alternative or explicit confirmation path.
- Repeated denials become visible in policy tuning and dogfood triage.

### P2.9 Complete Profile Repair Flow

Status: Not started
Owner:
Evidence:

Required work:

- Let users inspect learned claims with confidence, provenance, decay, and last evidence.
- Support edit, delete/decay, confirm, and "this is stale" actions.
- Require explicit confirmation before applying profile patches.
- Show how profile repair changes future candidate ranking.

Acceptance criteria:

- A dogfood user can correct a wrong claim and see the next plan reflect it.
- Replay records the profile repair proposal, confirmation, and applied patch.

### P2.10 Add Authority Grant Inspector And Scope Editor

Status: Not started
Owner:
Evidence:

Required work:

- Show grant ID, max tier, scopes, expiry, provenance, and confirmation status.
- Let dogfood users request narrower or broader scopes.
- Make expired grants obvious and require renewal before commit/undo.

Acceptance criteria:

- The user can tell why an action can stage but cannot commit.
- Tier and scope changes are replayed and auditable.

### P2.11 Make Self-Play A Release Gate

Status: Not started
Owner:
Evidence:

Required work:

- Add a UI control to run self-play probes for current fixture state.
- Surface top failure modes and policy tuning deltas.
- Block autonomy-tier increases when self-play finds high undo regret, social conflict, or notification fatigue.

Acceptance criteria:

- Each release candidate includes self-play metrics and a decision to ship, hold, or lower autonomy.

### P2.12 Build Replay Explorer

Status: Not started
Owner:
Evidence:

Required work:

- Add trace search by plan, candidate, receipt, grant, rollback handle, and reward event.
- Show causal chain in order.
- Export JSONL for a single trace or whole session.

Acceptance criteria:

- A dogfood bug report can include a trace export that reproduces the decision path.

## Dogfood Scenarios

Run these scenarios against fixture provider state before real provider OAuth:

| Scenario | Path | Expected result |
|---|---|---|
| Safe private focus block | goal -> candidate -> simulate -> commit | Materialized write, rollback handle, feedback prompt. |
| Commit then undo | commit -> undo -> replay | Provider state reverts, rollback cannot be reused, training row marks undo regret if selected. |
| Social meeting move | goal -> social candidate -> commit | Denied or staged with explicit social-actuation explanation. |
| Calendar conflict | create block over live fixture event | Denied with conflict truth from fixture provider. |
| Profile correction | inspect claim -> propose patch -> apply | Future plan changes and replay records repair. |
| Feedback loop | commit/stage/deny -> feedback -> train offline | Nonzero reward rows and policy tuning delta. |
| Authority expiry | wait or force expiry -> commit/undo | Denied with grant-expired explanation and renewal path. |
| Self-play release gate | run probe -> inspect failures | Top failure modes visible before autonomy increase. |

## Metrics And Scorecard

Update weekly during dogfood.

| Metric | Target before OAuth | Current | Notes |
|---|---:|---:|---|
| Goal-to-first-candidate success | >= 95% | | |
| Candidate-to-stage success | >= 90% | | |
| Safe private commit success | >= 90% | | |
| Undo success for reversible writes | 100% | | |
| Denials with actionable explanation | >= 95% | | |
| Feedback coverage on acted items | >= 80% | | |
| Replay traces with complete causal chain | >= 95% | | |
| Training rows per dogfood session | >= 5 | | |
| Fixture idempotency duplicate writes | 0 | | |
| Rollback verification failures | 0 | | |
| Browser E2E pass rate | >= 95% | | |

## Weekly Dogfood Ritual

1. Monday: choose three scenarios, reset fixture provider users, and assign owners.
2. Daily: each dogfood user runs at least one full loop and records feedback in-product.
3. Triage: label findings as product gap, runtime bug, provider truth bug, policy bug, UX bug, or test gap.
4. Friday: export replay, run offline policy report, update scorecard, and decide whether any autonomy scope can increase.
5. Before merging provider work: confirm P0 and P1 are green against fixture provider state.

## Bug Report Template

```text
Title:
Scenario:
Session ID:
Plan ID:
Candidate ID:
Receipt ID:
Rollback handle:
Authority grant ID:
Trace ID:
Expected:
Actual:
Was provider state changed:
Was undo available:
Feedback submitted:
Replay export path:
Screenshots/traces:
```

## Release Gates

Do not start real OAuth/provider tokens until:

- P0.1 through P0.4 are `Dogfood` or `Done`.
- Fixture provider writes are idempotent and rollback-verified.
- Commit -> undo -> replay -> training works from the browser.
- Denials are actionable and visible.
- Feedback creates real `RewardEvent` rows without hand-editing replay files.

Do not raise autonomy above tier 3 until:

- Undo success is 100% for reversible writes.
- Self-play release gate shows no high-severity undo regret or social conflict regressions.
- Dogfood feedback coverage is at least 80% for acted items.
- Browser E2E covers the full product loop.

## Decision Log

| Date | Decision | Reason | Revisit trigger |
|---|---|---|---|
| 2026-07-01 | Keep real OAuth blocked behind fixture provider state. | Provider truth, idempotency, and rollback need deterministic proof first. | Fixture provider passes rollback/idempotency gates for one week. |
| 2026-07-01 | Treat the static frontend as a demo fallback, not the dogfood product. | Dogfood requires live POSTs, receipts, feedback, and replay. | P0 API and interactive frontend are complete. |
| 2026-07-01 | Use Swift-issued authority grants as product-visible state. | History already hardened authority away from naked tiers. | None; this is a core boundary. |

## Evidence Log

Append links to traces, screenshots, replay exports, policy reports, or PRs here.

| Date | Step | Evidence | Result |
|---|---|---|---|
| 2026-07-01 | Baseline review | Git history through `b3e81b0`; current `frontend/static/app.js`, `frontend/server.py`, Codex runtime, Swift IPC, provider stubs, replay, tests. | Framework created. |
| 2026-07-01 | P0 dogfood slice | `python3 -m pytest -q` passed 44 tests; `swift test --package-path packages/CalendarPilotKernel` passed 16 tests; live API smoke test created plan, committed, undid, and attached feedback. | P0 ready for subagent review. |
| 2026-07-01 | P0 review fixes | Two subagent reviews found restart undo, provider denial, rollback isolation, feedback validation, UI fallback, and IPC undo-tier/timeout gaps. `python3 -m pytest -q` passed 47 tests; `swift test --package-path packages/CalendarPilotKernel` passed 17 tests; direct Swift IPC smoke denied out-of-band undo. | P0 review findings addressed. |
| 2026-07-01 | P1 dogfood slice | `python3 -m pytest -q` passed 47 tests; `swift test --package-path packages/CalendarPilotKernel` passed 17 tests; `PYTHONPATH=src python3 scripts/run_browser_e2e.py` passed 1 browser E2E. | P1 ready for subagent review. |
