# CalendarPilot Frontend 2 Dogfooding Framework

Status: working document
Primary audience: dogfood team, product engineering, runtime engineering
Source of truth: this file at repository root
Target implementation: `calendar-pilot-frontend 2/`
Archived predecessor: `Do-not-reference/calendar-pilot-frontend/`
Last reviewed: 2026-07-01

## Purpose

This document is the dogfood operating plan for `calendar-pilot-frontend 2/`.

The goal is general: prove that the application works end to end for a local dogfood user. Do not treat this document as a mandate to preserve a specific previous product loop, frontend layout, or UX philosophy. The current implementation happens to expose chat, sidebar, inspector, API, replay, Swift-kernel, policy, and macOS packaging surfaces; dogfood should validate those surfaces only because they exist in the codebase.

The dogfood team should edit this document directly as implementation changes. Treat statuses, evidence, risks, and release gates as an operating log.

## Current Implementation Under Test

Observed implementation as of 2026-07-01:

- `calendar-pilot-frontend 2/frontend/static/index.html` renders the browser UI.
- `calendar-pilot-frontend 2/frontend/static/app.js` calls `/api/*`, renders messages/cards, handles action buttons, and opens inspector tabs.
- `calendar-pilot-frontend 2/src/calendar_pilot/frontend/server.py` serves static assets and API endpoints.
- `calendar-pilot-frontend 2/src/calendar_pilot/frontend/session.py` owns local dogfood session state.
- `calendar-pilot-frontend 2/src/calendar_pilot/frontend/surface.py` builds frontend snapshots from planner, policy, replay, and profile data.
- `calendar-pilot-frontend 2/packages/CalendarPilotKernel/` contains the Swift kernel and IPC server.
- `calendar-pilot-frontend 2/scripts/run_browser_e2e.py` is the dogfood browser/API smoke.
- `calendar-pilot-frontend 2/scripts/build_macos_app.sh` builds the macOS `.app` bundle.

## Dogfood Principles

1. Validate the product that exists, not a presumed product direction.
2. Every phase must leave runnable evidence: tests, browser/API checks, app build artifacts, replay exports, or logs.
3. Prefer deterministic fixture state until provider truth, idempotency, and rollback checks are proven.
4. Credential setup is manual and user-owned. When Codex Auth, OAuth, or DiffusionGemma/NVIDIA NIM keys are required, open the browser for the user and pause at the credential field.
5. Do not proceed from P0 to P1, or P1 to P2, until the completed phase is committed and reviewed by two subagents.
6. Reviews are blockers only for correctness, data loss, broken launch, hidden failures, unsafe authority, or missing phase acceptance criteria.
7. Keep this document current when a phase starts, when evidence is collected, and when a gate changes.

## Phase Protocol

For each phase:

1. Mark the phase `In progress`.
2. Implement the smallest changes needed to satisfy that phase.
3. Run the phase checks.
4. Update this document with evidence and remaining risks.
5. Commit the completed phase.
6. Ask two subagents to review the committed phase independently.
7. Address blocking findings before starting the next phase.
8. Mark the phase `Done` only after the review findings are resolved or explicitly accepted as non-blocking.

## P0 Baseline Health

Status: Done
Owner: Codex
Goal: make the repository self-describing, runnable, and restart-safe enough for dogfood work.

### P0.1 Correct Dogfood Framing

Status: Done

Required work:

- Remove the incorrect assumption that Frontend 2 must preserve a prior product loop.
- Keep the archived implementation available under `Do-not-reference/`.
- Keep the active framework rooted on `calendar-pilot-frontend 2/`.

Acceptance criteria:

- Root `DOGFOODING_FRAMEWORK.md` is a general dogfood plan.
- It does not require a specific UI direction beyond validating the current implementation.
- It defines P0, P1, and P2 phase gates.

### P0.2 Baseline Test And Build Commands

Status: Done

Required work:

- Verify Python unit tests.
- Verify Swift unit tests.
- Verify browser/API dogfood smoke.
- Verify macOS app build script.
- Keep generated build artifacts ignored.

Acceptance criteria:

- `make py-test` passes.
- `make swift-test` passes.
- `make browser-e2e` passes.
- `make mac-app-build` creates `dist/CalendarPilot.app`.

### P0.3 Session Persistence Baseline

Status: Done

Required work:

- Persist the latest dogfood session to the run directory.
- Reload enough state after server restart to keep transcript, feedback, denials, profile patches, self-play history, authority edits, and replay summary inspectable.
- Make persistence failures explicit in tests.

Acceptance criteria:

- Creating a session, taking actions, then constructing a new session with the same `run_dir` restores the previous visible state.
- Replay JSONL reloads into the inspector summary after restart.
- Reset intentionally starts a clean session and persists the clean state.

### P0.4 API Shape And Error Contract

Status: Done

Required work:

- Confirm the frontend endpoints used by `app.js` exist and return stable JSON.
- Keep failed POSTs debuggable by returning an error and current state.
- Normalize authority request body handling.

Acceptance criteria:

- `/api/state`, `/api/plans`, candidate actions, undo, feedback, replay, profile patch, denial explanation, self-play, authority, and reset are covered by tests or E2E.
- Invalid actions return structured JSON with `error` and `state`.

## P1 Interactive Dogfood Workflows

Status: Done
Owner: Codex
Goal: prove that a dogfood user can exercise the real frontend/backend workflows without touching Python internals.

### P1.1 Live Browser E2E

Status: Done

Required work:

- Start the Python frontend server on an available local port.
- Drive the rendered browser against the live server.
- Exercise user-visible controls instead of calling `DogfoodSessionState` directly as the primary path.
- Keep a deterministic fallback where Playwright or a browser is unavailable.

Acceptance criteria:

- Browser E2E covers goal entry, candidate rendering, stage, commit, undo, feedback, replay export, authority edit, profile patch, denial explanation, self-play, and reset.
- The test fails with a useful message when the UI cannot reach the backend.
- Failure artifacts are easy to locate.

### P1.2 Replay And Feedback Evidence

Status: Done

Required work:

- Ensure useful/wrong feedback attaches to receipts or creates a reward record with a traceable receipt ID.
- Ensure replay export contains enough state for a dogfood bug report.
- Add a simple dogfood bug-report artifact path if needed.

Acceptance criteria:

- A committed or denied action can receive feedback from the UI.
- Replay export includes session ID, summary, and records.
- Training/replay evidence survives restart.

### P1.3 Profile, Authority, Denial, And Self-Play Controls

Status: Done

Required work:

- Verify inspector controls invoke backend APIs and update visible state.
- Ensure authority edits do not bypass Swift/kernel validation.
- Make denial explanation and profile repair flows recoverable for a dogfood user.
- Ensure self-play output is surfaced as a release gate signal.

Acceptance criteria:

- Authority edits append grant history.
- Profile patch propose/apply creates inspectable history.
- Denial explanation creates a visible explanation record.
- Self-play writes history and release decision.

## P2 macOS App And Release Readiness

Status: In review
Owner: Codex
Goal: deliver a local macOS app bundle that can run the same dogfood workflows as the browser.

### P2.1 macOS Bundle Launch

Status: Done

Required work:

- Build `dist/CalendarPilot.app`.
- Package or locate the Python source, static assets, data, and scripts needed by the app at launch.
- Store mutable run state outside the app bundle.
- Avoid relying on the current shell working directory.
- Provide a desktop shortcut to the active app if needed.

Acceptance criteria:

- Launching the `.app` starts the local server and opens or displays the frontend.
- The app uses `~/Library/Application Support/CalendarPilot` or another user-writable run directory.
- The same workflows validated in P1 are possible from the app.

### P2.2 Release Gate Script

Status: Done

Required work:

- Provide one command that runs the release checks expected before dogfood distribution.
- Include Python tests, Swift tests, browser E2E, app build, and app bundle sanity checks.
- Produce a concise release report artifact.

Acceptance criteria:

- `make dogfood-release` or equivalent exits non-zero on failure.
- The release report records command results, timestamps, and artifact paths.

### P2.3 Credential Gates

Status: Done

Required work:

- Identify whether Codex Auth, provider OAuth, or DiffusionGemma/NVIDIA NIM credentials are required for the current dogfood scope.
- If credentials are required, open the browser for the user to enter them.
- Do not store secrets in git, replay, logs, or generated reports.

Acceptance criteria:

- Local fixture dogfood can run without credentials, or the required manual credential setup is documented and verified.
- No committed file contains secrets.

## Standard Dogfood Scenarios

Run these whenever a phase touches frontend, API, replay, persistence, or packaging:

1. Baseline load: open the app and confirm the first visible state renders without console or server errors.
2. User request: submit a realistic calendar request and confirm the UI updates.
3. Candidate action: simulate or stage a candidate and verify a visible receipt.
4. Commit path: commit a safe fixture action and verify a rollback handle appears.
5. Undo path: undo the committed action and verify visible state changes.
6. Feedback path: mark the result useful or wrong and verify replay/reward evidence.
7. Replay path: export replay and verify non-empty records.
8. Authority path: change authority settings and verify grant history.
9. Profile path: propose/apply a profile correction and verify history.
10. Denial path: trigger or explain a denied action and verify recovery guidance.
11. Self-play path: run a small probe and verify release decision state.
12. Restart path: stop and restart the server, then verify visible session evidence remains.
13. App path: build and launch the macOS app, then rerun the critical workflow.

## Scorecard

| Metric | Target Before P1 | Target Before P2 | Release Target |
|---|---:|---:|---:|
| Python unit tests | pass | pass | pass |
| Swift unit tests | pass | pass | pass |
| Browser/API smoke | pass | live browser primary | live browser primary |
| Session restart evidence | basic | full dogfood state | full dogfood state |
| Replay export | non-empty | bug-report ready | bug-report ready |
| macOS app build | builds | launches | dogfood usable |
| Secrets in repo | none | none | none |

## Evidence Log

| Date | Phase | Evidence | Result |
|---|---|---|---|
| 2026-07-01 | Archive | Moved tracked `calendar-pilot-frontend/` and old framework to `Do-not-reference/`. | Active root now targets `calendar-pilot-frontend 2/`. |
| 2026-07-01 | P0 framing | Replaced the chat-specific dogfood mandate with this general validation framework. | Done. |
| 2026-07-01 | P0 persistence | Added `session_state.json` persistence/reload for session metadata, plan, transcript, feedback, denials, profile patches, self-play history, authority grants, undo ledger, replay, and corrupt-state recovery. | `test_frontend_session_persistence.py` passes. |
| 2026-07-01 | P0 API contract | Added HTTP-level route coverage for state, plans, candidates, receipt confirmation, undo, feedback, replay, profile patch, denial explanation, self-play, authority, reset, and invalid POST JSON. | `test_frontend_server_api.py` passes. |
| 2026-07-01 | P0 baseline checks | Ran root `make py-test`, `make swift-test`, `make browser-e2e`, and `make mac-app-build`. | Python 46 tests, Swift 16 tests, browser smoke, app build, bundle layout, and launcher syntax passed. |
| 2026-07-01 | P1 live frontend | Reworked `scripts/run_browser_e2e.py` to start the real Python server, verify live restart persistence, drive live HTTP endpoints, write replay/bug-report artifacts, and require a rendered browser gate by default. | `make browser-e2e` passed with `browser CDP e2e passed`. |
| 2026-07-01 | P1 controls | Browser/API E2E covers goal entry, candidate rendering, stage, commit, undo, feedback, replay export, profile propose/apply, authority edit, real low-authority commit denial, denial explanation, self-play, reset, and invalid route handling. | `browser_replay_export.json` contains 81 records before reset; reset evidence is captured afterward. |
| 2026-07-01 | P2 release gate | Added `scripts/run_dogfood_release.py` and `make dogfood-release` to run Python tests, Swift tests, mandatory browser E2E, macOS app build, app bundle launch/API sanity, and secret scan. | Release report passed at `calendar-pilot-frontend 2/runs/release/dogfood_release_report.json`. |
| 2026-07-01 | P2 app bundle | Built `dist/CalendarPilot.app`, verified bundled source/static/data layout, launched the bundle executable on a free port with run state outside the bundle, and exercised plan/commit/replay/reset through the app server. | `mac_app_sanity` passed in the release report. |
| 2026-07-01 | P2 desktop shortcut | Updated `/Users/temp/Desktop/CalendarPilot.app` to point at `calendar-pilot-frontend 2/dist/CalendarPilot.app`. | Shortcut target verified with `readlink`. |
| 2026-07-01 | P2 credentials | Confirmed local fixture dogfood requires no Codex Auth, provider OAuth, or DiffusionGemma/NVIDIA NIM credentials. | `secret_scan` passed in the release report. |

## Review Log

| Date | Phase | Reviewer | Result | Follow-up |
|---|---|---|---|---|
| 2026-07-01 | P0 | Bohr | Found string boolean authority confirmation risk, missing HTTP API coverage, incomplete persistence assertions, and corrupt-state risk. | Fixed with `body_bool`, `test_frontend_server_api.py`, stronger restart assertions, and visible corrupt restore recovery. |
| 2026-07-01 | P0 | Epicurus | Found premature review bookkeeping, missing HTTP API coverage, root command ambiguity, weak app bundle evidence, and stale browser run risk. | Fixed with review log, HTTP tests, root Makefile delegation, packaged app source layout, and browser run-dir cleanup. |
| 2026-07-01 | P1 | Hilbert | Found optional browser false pass, synthetic CDP interaction, startup cleanup leak, ambiguous artifacts, and stale low-authority card risk. | Made browser mandatory by default, added visible hit-tested mouse/input events, fixed startup cleanup, wrote browser replay artifacts, and waits for the new candidate card. |
| 2026-07-01 | P1 | Sagan | Found premature P1 status, missing live restart proof, weak denial evidence, and replay artifacts written before browser controls. | Added actual stop/start restart check, real low-authority denial, browser-generated replay export before reset, and review log entries. |

## Open Risks

| Risk | Phase | Mitigation |
|---|---|---|
| App bundle launch needs end-to-end app-open verification. | P2 | Launch built `.app`, confirm the local server opens, then run critical dogfood workflow through it. |
| Real provider/OAuth behavior is not included in fixture dogfood. | P2 | Keep fixture gate explicit and require manual credential setup only when scope expands. |
