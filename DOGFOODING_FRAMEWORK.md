# CalendarPilot Frontend 2 Dogfooding Framework

Status: working document
Primary audience: dogfood team, product engineering, runtime engineering
Source of truth: this file at repository root
Target implementation: `calendar-pilot-frontend 2/`
Archived predecessor: `Do-not-reference/calendar-pilot-frontend/`
Last reviewed: 2026-07-01

## Purpose

This document restarts the dogfood framework for `calendar-pilot-frontend 2/`.

The previous dogfood app proved the machine-learning and machine-acting loop, but the first-viewport UX was a control dashboard. Frontend 2 must preserve the same product loop while presenting it as a chat-first calendar assistant:

```text
chat goal -> inspect week -> candidate action cards -> simulate/stage/commit/deny
-> undo -> feedback/reward -> replay/export -> self-play gate -> next chat request
```

The dogfood team should edit this document directly as v2 changes. Treat every status, owner, evidence line, and acceptance criterion as an operating log, not as static planning text.

## How We Arrived Here

| Phase | What changed | Dogfood implication |
|---|---|---|
| Planning corpus | Earlier plans debated witness/controller, self-play, reward, latency, calendar authority, and agentic UX. | CalendarPilot is an optimizer with controlled actuation, not a passive calendar summary surface. |
| CalendarPilot skeleton | Python package, Swift kernel, typed contracts, fixtures, replay, self-play, policy, and tests were added. | Dogfood starts from runnable primitives and typed receipts. |
| Codex tool executive | Codex became a bounded runtime over inspect, frontier, simulate, compare, stage, commit, undo, replay, profile repair, autonomy, and denial tools. | The app flow should be tool-receipt driven, even when presented as chat. |
| Authority hardening | Swift-issued `AuthorityGrant` replaced naked tiers; grants and receipts became visible state. | UX must show why Codex can request but cannot directly write. |
| Frontend 1 dogfood | `calendar-pilot-frontend/` completed P0/P1/P2: live API, fixture provider, undo, feedback, replay, self-play, and macOS bundle. | The loop was proven, but the UX became an internal dashboard. |
| UX reset | User feedback clarified the target: "more like chatgpt.com + side menu/settings." | Frontend 2 should make chat the primary product surface and move dogfood machinery into an inspector. |
| Frontend 2 baseline | `calendar-pilot-frontend 2/` adds a chat-first static shell, sidebar, composer, inspector drawer, chat/sidebar/inspector snapshot state, and a CI-friendly dogfood smoke. | The next dogfood pass is UX-first hardening over the same runtime loop. |

## Current Frontend 2 State

Observed implementation as of 2026-07-01:

- `frontend/static/index.html` has a left sidebar, chat transcript, composer, and right inspector.
- `frontend/static/app.js` maps `/api/*` state to chat messages, candidate cards, receipt cards, and inspector tabs.
- `src/calendar_pilot/frontend/surface.py` returns legacy panels plus `chat`, `sidebar`, and `inspector` presentation state.
- `src/calendar_pilot/frontend/session.py` owns an in-memory `DogfoodSessionState` with transcript events, feedback history, denials, profile patches, self-play history, authority history, and replay.
- `src/calendar_pilot/frontend/server.py` exposes live API routes for state, plans, candidates, receipts, undo, profile patch, denials, self-play, authority, feedback, reset, and replay export.
- `scripts/run_browser_e2e.py` is currently a deterministic smoke: it checks static chat-shell markers and drives `DogfoodSessionState` directly. It can optionally run a rendered Playwright check through mocked API routes.
- `scripts/browser_e2e.spec.mjs` describes the desired live browser path, but it is not the canonical CI path yet.
- `scripts/build_macos_app.sh` creates a minimal `.app` shell. It is not yet equivalent to the prior SwiftUI/WebKit wrapper and needs packaging hardening.
- `docs/CHAT_FIRST_FRONTEND_REDESIGN.md` captures the intended UX architecture.

Known gaps to keep visible:

- Session persistence writes snapshots/replay but does not reload a prior dogfood session on server restart.
- Frontend 2 does not yet port the fixture provider truth/idempotency/rollback verification from archived Frontend 1.
- The session uses `SwiftKernelStub`; Swift IPC exists but is not wired through the live dogfood path.
- Replay export returns JSON, but there is no bug-report file artifact workflow yet.
- Self-play release gating is still shallow: `hold_autonomy` is based on top failure modes rather than full reward/undo/social/fatigue thresholds.
- The macOS app builder copies static assets only and should be replaced or hardened before dogfood distribution.
- The live browser E2E should start the actual server and exercise the rendered app, not only direct session calls.

## Dogfood Doctrine For Frontend 2

1. Chat is the primary product surface.
2. The dogfood loop remains the product engine.
3. Candidate futures and Swift receipts should appear as inline chat action cards.
4. Authority, replay, profile repair, self-play, provider state, and debug trace belong in the inspector.
5. Codex can request actions; Swift validates and writes; providers own external truth.
6. Every meaningful user action should create typed state: tool call, tool receipt, Swift receipt, reward event, profile patch, replay row, or exported trace.
7. Real OAuth remains blocked until fixture provider state proves idempotency, conflict truth, and rollback verification in v2.

## Working Backlog

Status values: `Not started`, `In progress`, `Blocked`, `Dogfood`, `Done`

### P0.1 Archive Frontend 1 And Reset Source Of Truth

Status: Done
Owner:
Evidence: Archived tracked `calendar-pilot-frontend/` and the old root `DOGFOODING_FRAMEWORK.md` under `Do-not-reference/`; this root document now targets `calendar-pilot-frontend 2/`.

Required work:

- Move the completed dashboard-style dogfood implementation out of the active root.
- Keep its history available under `Do-not-reference/` for comparison only.
- Make root `DOGFOODING_FRAMEWORK.md` describe Frontend 2, not the archived app.

Acceptance criteria:

- `calendar-pilot-frontend/` no longer exists as the active tracked implementation.
- `Do-not-reference/calendar-pilot-frontend/` contains the archived implementation.
- Root `DOGFOODING_FRAMEWORK.md` points to `calendar-pilot-frontend 2/`.

### P0.2 Preserve And Harden The Chat-First Shell

Status: In progress
Owner:
Evidence: `frontend/static/index.html`, `app.js`, and `styles.css` already implement sidebar, transcript, composer, inspector, candidate cards, receipt cards, and inspector tabs.

Required work:

- Keep the first viewport as chat, not a dashboard.
- Make the left sidebar useful for new chat, current session, and recent dogfood runs.
- Keep inspector tabs for authority, profile, replay, self-play, provider, and debug.
- Ensure all controls fit across desktop and mobile without overlap.
- Remove any explanatory copy that reads like a landing page instead of product UI.

Acceptance criteria:

- A dogfood user lands in a chat transcript with a composer.
- Candidate cards render inside assistant messages.
- Dogfood machinery is available in the inspector, not dominant in the main chat.
- Mobile layout does not hide the primary send/action controls.

### P0.3 Stabilize The Stateful Frontend API

Status: In progress
Owner:
Evidence: `src/calendar_pilot/frontend/server.py` exposes the v2 API route set; `DogfoodSessionState` can create plans, act on candidates, undo, record feedback, patch profile, explain denials, run self-play, edit authority, reset, and export replay.

Minimum endpoint set:

| Endpoint | Method | Purpose |
|---|---:|---|
| `/api/state` | `GET` | Return snapshot with `chat`, `sidebar`, `inspector`, legacy panels, trace, queue, and session metadata. |
| `/api/plans` | `POST` | Convert chat goal into a Codex executive plan. |
| `/api/candidates/{candidate_id}/simulate` | `POST` | Run simulation and show receipt in chat. |
| `/api/candidates/{candidate_id}/stage` | `POST` | Stage selected candidate through Swift. |
| `/api/candidates/{candidate_id}/commit` | `POST` | Commit private/reversible candidate through Swift. |
| `/api/candidates/{candidate_id}/confirm` | `POST` | Commit after explicit user confirmation. |
| `/api/receipts/{receipt_id}/confirm` | `POST` | Confirm staged receipt by receipt ID. |
| `/api/undo` | `POST` | Undo by rollback handle. |
| `/api/profile/patch/propose` | `POST` | Draft profile repair. |
| `/api/profile/patch/apply` | `POST` | Apply confirmed profile repair. |
| `/api/denials/explain` | `POST` | Explain Swift denial and suggest next controls. |
| `/api/self-play` | `POST` | Run self-play release probe. |
| `/api/authority` | `POST` | Edit tier/scopes and issue a new grant. |
| `/api/feedback` | `POST` | Convert user feedback into reward data. |
| `/api/replay` | `GET` | Query replay records. |
| `/api/replay/export` | `GET` | Export replay for dogfood bug reports. |
| `/api/reset` | `POST` | Reset fixture session. |

Required work:

- Normalize request body keys, especially `authority_tier` vs `max_authority_tier`.
- Return stable error JSON without hiding failed actions.
- Persist and reload session state across server restarts.
- Keep response shapes stable for browser E2E and future native wrappers.

Acceptance criteria:

- Restarting the server restores the latest session, replay summary, and transcript.
- Every mutating endpoint either appends replay evidence or returns an explicit denial/error.
- A failed POST leaves the chat state coherent and inspectable.

### P0.4 Restore Fixture Provider Truth In V2

Status: Not started
Owner:
Evidence: Archived Frontend 1 contains `FixtureCalendarProvider`; Frontend 2 currently relies on kernel stub/replay behavior without persisted provider truth.

Required work:

- Port deterministic fixture provider state into Frontend 2.
- Persist provider calendar state, external IDs, idempotency keys, conflict truth, and rollback records under the v2 run directory.
- Verify rollback by provider checksum, not only Swift stub receipt status.
- Surface provider checksum/status in the inspector provider tab.

Acceptance criteria:

- Commit changes fixture provider state and returns stable external IDs.
- Replaying an idempotency key does not duplicate events.
- Undo restores provider state and cannot be reused successfully.
- Planning after a write reads current fixture provider truth.

### P0.5 Wire The Live V2 Path To Swift IPC

Status: Not started
Owner:
Evidence: `SwiftKernelIPCClient` exists; `DogfoodSessionState` currently constructs `SwiftKernelStub`.

Required work:

- Make the live dogfood session selectable between stub and Swift IPC.
- Ensure IPC supports the same kernel shape needed by `CodexToolRuntime`.
- Run inspect -> frontier -> simulate -> stage/commit -> undo through compiled Swift.
- Keep grant registry and undo ledger authoritative inside Swift when IPC is enabled.

Acceptance criteria:

- `CodexToolRuntime(kernel=SwiftKernelIPCClient(...))` runs the v2 chat flow.
- Forged or embedded grants remain ignored.
- IPC timeout, stderr capture, process cleanup, and failure state are testable.

### P0.6 Replace Smoke With Real Live Browser E2E

Status: In progress
Owner:
Evidence: `scripts/run_browser_e2e.py` validates static markers and direct session flow; `scripts/browser_e2e.spec.mjs` describes a rendered browser path.

Required work:

- Start `python3 -m calendar_pilot.app frontend --serve` on a free port.
- Drive the rendered browser with Playwright against the live server.
- Keep deterministic fixture state and reset between tests.
- Cover goal -> candidate card -> stage -> commit -> undo -> feedback -> replay export.
- Add denial, profile repair, authority edit, and self-play inspector coverage.

Acceptance criteria:

- `PYTHONPATH=src python3 scripts/run_browser_e2e.py` starts the server and drives a real browser by default where supported.
- CI reports screenshots or traces for failures.
- The optional Node spec is either made canonical or removed to avoid split truth.

### P0.7 Harden The macOS App For V2

Status: In progress
Owner:
Evidence: `scripts/build_macos_app.sh` creates a minimal shell `.app` but copies only static assets and starts Python from the app bundle path.

Required work:

- Package or locate the full v2 source needed by `python3 -m calendar_pilot.app`.
- Store run state under `~/Library/Application Support/CalendarPilot`, not inside the app bundle.
- Avoid log pipe deadlocks.
- Support WebKit JavaScript prompt/confirm paths or remove prompt-dependent UI.
- Rebuild and verify `dist/CalendarPilot.app` opens the chat-first app.

Acceptance criteria:

- `make mac-app-build` creates an app that launches the live v2 API and chat UI.
- Installed or copied app bundles can write state outside the bundle.
- The macOS app can complete the same dogfood loop as browser E2E.

## P1 Product Journeys

### P1.1 Chat Goal To Candidate Cards

Status: Dogfood
Owner:
Evidence: `DogfoodSessionState.create_plan()` appends user and assistant transcript events; `chat.candidate_cards` render inline cards.

Acceptance criteria:

- User sends "Make next week less chaotic" through the composer.
- Assistant message includes the top candidate cards with model story and reward/regret details.
- The same plan remains inspectable in debug trace and replay.

### P1.2 Inline Stage, Commit, Deny, Undo, And Feedback

Status: In progress
Owner:
Evidence: `app.js` renders candidate and receipt card controls for simulate, stage, commit, undo, useful, wrong, and denial explanation.

Required work:

- Keep all acting controls inline with the assistant message that introduced the action.
- Show denied state and follow-up controls without sending users to debug panels.
- Place undo and feedback immediately after committed actions.
- Prevent duplicate submissions while requests are pending.

Acceptance criteria:

- A committed action yields a visible rollback handle and undo button.
- Undo appends a new assistant receipt message.
- Useful/wrong feedback creates reward evidence and an assistant confirmation.

### P1.3 Denials As Recoverable Chat Turns

Status: In progress
Owner:
Evidence: `/api/denials/explain` exists and appends assistant receipt messages.

Required work:

- Render denial reason, affected action, grant/scopes, and next control.
- Offer stage instead, ask confirmation where valid, narrow scope, repair profile, or simulate alternative.
- Do not offer controls that simply retry the same denied request.

Acceptance criteria:

- A scope denial can recover through explicit confirmation or scope edit.
- A social mutation denial explains why kernel-v1 refuses the write and keeps the action staged or blocked.
- Denial history appears in inspector and replay.

### P1.4 Profile Repair In Inspector And Chat

Status: In progress
Owner:
Evidence: Profile repair routes and inspector controls exist.

Required work:

- Show learned claims with confidence, provenance, last evidence, and decay/stale state.
- Propose patch from user correction.
- Require explicit apply confirmation.
- Reflect profile changes in future candidate ranking or explanation.

Acceptance criteria:

- A dogfood user can correct a claim and see a profile repair receipt.
- Replay records proposal and application.
- The next plan shows evidence that the correction affected candidate selection or explanation.

### P1.5 Authority Inspector

Status: In progress
Owner:
Evidence: Inspector authority tab edits tier/scopes and shows recent grants.

Required work:

- Show grant ID, max tier, scopes, expiry, provenance, and confirmation.
- Make expired or insufficient grants obvious in chat and inspector.
- Keep scope edits replayable and auditable.

Acceptance criteria:

- The user can tell why an action can stage but cannot commit.
- Editing scopes changes subsequent Swift validation behavior.

### P1.6 Replay Export For Bug Reports

Status: In progress
Owner:
Evidence: `/api/replay/export` returns session summary and records.

Required work:

- Add filtered export by candidate, receipt, rollback handle, grant, reward, or free text.
- Write JSON or JSONL export artifacts under the run directory.
- Link export path in inspector and bug report template.

Acceptance criteria:

- A dogfood bug report includes a replay export path.
- Exported records reproduce the decision path without adding new replay records.

## P2 Release Gates

### P2.1 Self-Play As Autonomy Gate

Status: In progress
Owner:
Evidence: `/api/self-play` runs `RUN_SELF_PLAY_PROBE`; release decision is currently based on top failure modes.

Required work:

- Include average reward, undo rate, denial rate, social conflict, notification fatigue, and high regret thresholds.
- Block autonomy increases when any threshold fails.
- Show hold/ship/lower-autonomy decision in inspector and chat.

Acceptance criteria:

- Each release candidate includes a self-play report and a decision.
- Autonomy tier cannot increase when release gate is red.

### P2.2 Offline Policy Feedback Loop

Status: In progress
Owner:
Evidence: `scripts/train_offline_policy.py` consumes replay/training data; feedback creates reward events.

Required work:

- Ensure dogfood feedback reliably creates training rows.
- Run offline report from exported replay.
- Show policy tuning deltas in inspector.

Acceptance criteria:

- A dogfood session with feedback creates nonzero training rows.
- Offline report shows intent-level reward residuals and denial penalties.

### P2.3 Real Provider OAuth Gate

Status: Blocked
Owner:
Evidence: Provider adapters remain stubs; real OAuth is intentionally blocked.

Required work before unblocking:

- Fixture provider idempotency and rollback pass repeatedly.
- Browser E2E covers commit, undo, denial, replay, and feedback.
- Replay export is sufficient for bug reproduction.
- Dogfood team explicitly approves token setup.

Acceptance criteria:

- No OAuth credentials are requested before fixture provider truth is proven.
- When credentials are needed, open a browser for user input rather than asking for secrets in chat.

## Dogfood Scenarios

| Scenario | V2 path | Expected result |
|---|---|---|
| Chat goal to candidate | composer -> assistant plan | Candidate cards appear inline with model story and action controls. |
| Safe private focus block | candidate card -> simulate -> commit | Swift commits private/reversible write and receipt appears in chat. |
| Commit then undo | committed receipt -> undo | Undo receipt appears in chat; provider state reverts once fixture provider is restored. |
| Feedback loop | receipt -> useful/wrong | Reward event appears in replay/training evidence. |
| Scope denial | lower authority -> commit | Denial appears in chat with useful recovery controls. |
| Profile correction | inspector profile -> propose/apply | Profile patch receipt appears and future plan reflects correction. |
| Replay bug report | inspector replay -> export | Export artifact or JSON payload includes complete causal records. |
| Self-play release gate | inspector self-play -> run | Gate returns ship/hold/lower-autonomy decision with failure modes. |
| macOS app | open `dist/CalendarPilot.app` | Chat-first app opens and completes dogfood loop. |

## Metrics And Scorecard

Update weekly during dogfood.

| Metric | Target before OAuth | Current | Notes |
|---|---:|---:|---|
| Chat goal to first candidate | >= 95% | | |
| Candidate action card render success | >= 95% | | |
| Candidate to stage success | >= 90% | | |
| Safe private commit success | >= 90% | | |
| Undo success for reversible writes | 100% | | Requires fixture provider truth. |
| Denials with actionable recovery | >= 95% | | |
| Feedback coverage on acted items | >= 80% | | |
| Replay traces with complete causal chain | >= 95% | | |
| Replay exports attached to bug reports | >= 90% | | |
| Self-play gate run per release candidate | 100% | | |
| Browser E2E pass rate | >= 95% | | |
| macOS app bundle launch success | 100% | | |

## Weekly Dogfood Ritual

1. Monday: choose three dogfood scenarios and assign owners.
2. Daily: each dogfood user runs one chat-first loop and submits feedback in-product.
3. Triage: label findings as UX gap, runtime bug, provider truth bug, policy bug, authority bug, replay bug, or test gap.
4. Friday: export replay, run offline policy report, update scorecard, and decide whether autonomy can change.
5. Before provider work: confirm P0 gates and fixture rollback are green.

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
Replay export path or payload:
Browser/app:
Screenshot/trace:
```

## Release Gates

Do not start real OAuth/provider tokens until:

- P0.2 through P0.7 are `Dogfood` or `Done`.
- Fixture provider writes are idempotent and rollback-verified in Frontend 2.
- Chat UI can complete commit -> undo -> feedback -> replay export.
- Denials are actionable in chat.
- Real browser E2E passes against the live server.
- macOS app can complete the same loop.

Do not raise autonomy above tier 3 until:

- Undo success is 100% for reversible writes.
- Self-play gate shows no high-severity undo regret, social conflict, or notification fatigue regression.
- Dogfood feedback coverage is at least 80% for acted items.
- Replay exports have complete causal chains.

## Decision Log

| Date | Decision | Reason | Revisit trigger |
|---|---|---|---|
| 2026-07-01 | Archive Frontend 1 under `Do-not-reference/`. | It proved dogfood mechanics but used the wrong dashboard-first UX. | Only for reference when porting proven mechanics. |
| 2026-07-01 | Make Frontend 2 chat-first. | User expectation is ChatGPT-like chat plus side menu/settings. | If dogfood users cannot find action controls or debugging evidence. |
| 2026-07-01 | Keep inspector as secondary surface. | Authority, replay, self-play, profile repair, and debug trace are necessary but should not dominate first viewport. | If operators need faster triage during dogfood. |
| 2026-07-01 | Keep OAuth blocked. | Provider truth, rollback, replay, and E2E still need v2 proof. | Fixture provider and release gates pass repeatedly. |

## Evidence Log

Append links to traces, screenshots, replay exports, policy reports, commits, or PRs here.

| Date | Step | Evidence | Result |
|---|---|---|---|
| 2026-07-01 | Frontend 1 archive | Moved tracked `calendar-pilot-frontend/` and old framework to `Do-not-reference/`. | Active root can focus on Frontend 2. |
| 2026-07-01 | Frontend 2 baseline review | Reviewed `frontend/static`, `DogfoodSessionState`, `server.py`, `surface.py`, `scripts/run_browser_e2e.py`, `scripts/build_macos_app.sh`, and `docs/CHAT_FIRST_FRONTEND_REDESIGN.md`. | Framework reset for chat-first dogfood. |
