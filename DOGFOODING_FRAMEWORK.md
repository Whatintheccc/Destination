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

## Production Integration Gap

Observed after opening the desktop app on `http://127.0.0.1:8787/` on 2026-07-01:

- The desktop shortcut is current and points to `calendar-pilot-frontend 2/dist/CalendarPilot.app`.
- The running process is from that v2 app bundle, not the archived predecessor.
- The bundle is explicitly fixture-scoped: `CFBundleIdentifier` is `dev.calendarpilot.fixture`, and the app packages `data/sample_calendar.json`, `data/sample_profile.json`, `frontend`, and `src`.
- The frontend is dynamic against `/api/*`, but it falls back to `frontend_state.sample.json` when `/api/state` fails.
- The backend session defaults to sample calendar/profile fixtures and constructs `SwiftKernelStub`, `DiffusionGemmaPolicy`, and local `CodexToolRuntime`.
- `Codex` is currently a deterministic local planner/runtime contract, not a live model-backed Codex/OpenAI endpoint.
- `DiffusionGemma` is currently a deterministic heuristic policy, not NVIDIA NIM or another model-serving endpoint.
- `SwiftKernelIPCClient` exists, but the app path does not select it and the IPC surface is not yet drop-in compatible with the stub-shaped kernel interface used by `CodexToolRuntime`.
- Provider adapters are stubs. Real OAuth, provider sync, conflict truth, external IDs, idempotency, and write execution are not implemented.
- The UI truthfully reports `local_stub` and `real_oauth: False`.
- The desktop launcher uses fixed port `8787` and opens the browser after a sleep, so a stale server on that port can be shown if launch ownership is ambiguous.

Conclusion: P0-P2 certify a working local fixture macOS app. They do not certify production-integrated Codex, DiffusionGemma/NIM, Swift IPC, or real provider behavior. P3 and later phases exist to close that gap.

## Dogfood Principles

1. Validate the product that exists, not a presumed product direction.
2. Every phase must leave runnable evidence: tests, browser/API checks, app build artifacts, replay exports, or logs.
3. Prefer deterministic fixture state until provider truth, idempotency, and rollback checks are proven.
4. Credential setup is manual and user-owned. When Codex Auth, OAuth, or DiffusionGemma/NVIDIA NIM keys are required, open the browser for the user and pause at the credential field.
5. Do not proceed from one phase to the next until the completed phase is committed and reviewed by one architecture-focused subagent.
6. Reviews are blockers only for correctness, data loss, broken launch, hidden failures, unsafe authority, or missing phase acceptance criteria.
7. Keep this document current when a phase starts, when evidence is collected, and when a gate changes.

## Phase Protocol

For each phase:

1. Mark the phase `In progress`.
2. Implement the smallest changes needed to satisfy that phase.
3. Run the phase checks.
4. Update this document with evidence and remaining risks.
5. Commit the completed phase.
6. Ask one subagent to read the repository and review the committed phase from an architectural design perspective.
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

Status: Done
Owner: Codex
Goal: deliver a local macOS app bundle that can run the same dogfood workflows as the browser.

Scope note: P2 release readiness means fixture release readiness. It does not mean production integrations are live.

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

## P3 Runtime Mode Truth

Status: Done
Owner: dogfood team
Goal: make the app impossible to mistake for a production-integrated build when it is running fixture or local-stub dependencies.

### P3.1 Runtime Mode Contract

Status: Done

Required work:

- Add an explicit runtime mode model with at least: `fixture`, `swift_ipc`, `live_codex`, `live_diffusiongemma`, `live_provider`, and `production`.
- Add a backend health/config endpoint that reports active mode, active kernel backend, Codex backend, DiffusionGemma backend, provider backend, credential readiness, fixture paths, run directory, app bundle path, build identifier, and server process identity.
- Persist the selected mode in run state or launch config so browser reloads, app relaunches, and replay exports agree.
- Make fixture fallbacks explicit. Static `frontend_state.sample.json` fallback must only appear as `offline_fixture_fallback`, not as a normal production path.

Acceptance criteria:

- `/api/health` or equivalent returns a machine-readable runtime report.
- The UI shows the active mode in a first-viewport signal.
- Replay exports include runtime mode and backend provenance.
- Release checks fail if a production-targeted run silently uses fixture data, `SwiftKernelStub`, local heuristic policy, or provider stubs.

### P3.2 Fixture Boundary Warnings

Status: Done

Required work:

- Rename fixture app identifiers, titles, and provider rows so fixture mode is visible in the app, bundle metadata, and release report.
- Add copy for missing integrations that is factual and concise: Codex live endpoint missing, DiffusionGemma/NIM missing, Swift IPC not selected, provider OAuth missing.
- Add a dogfood bug-report field that records whether the report was captured from fixture or live mode.

Acceptance criteria:

- A screenshot of the launched app is enough to tell whether the user is in fixture mode.
- The provider inspector cannot say or imply that real OAuth/provider sync is active when it is not.
- A fixture-mode release report cannot be confused with a production-mode release report.

## P4 Swift IPC Runtime

Status: In review
Owner: runtime engineering
Goal: run planner stage, commit, and undo paths through compiled Swift instead of the Python stub.

### P4.1 Kernel Interface Adapter

Status: In review

Required work:

- Define a shared Python kernel protocol used by `CodexToolRuntime`.
- Make `SwiftKernelStub` and `SwiftKernelIPCClient` satisfy the same protocol, or add an adapter that translates the current stub-shaped calls into IPC calls.
- Cover `issue_authority_grant`, `resolve_authority_grant`, `preview_candidate`, `stage_candidate`, `authorize_and_materialize`, `request_undo`, authority grant liveness, and undo ledger behavior.
- Preserve structured receipts, denial reasons, rollback handles, staged IDs, generated event IDs, provider IDs, and correlation IDs across the IPC boundary.

Acceptance criteria:

- Tests can run the same planner scenario against stub and IPC backends.
- IPC receipts identify `CalendarPilotKernelServer` or another compiled Swift executable, not `SwiftKernelStub`.
- Missing/failed Swift IPC startup produces visible UI and release-report failures.

### P4.2 App Packaging And Lifecycle

Status: In review

Required work:

- Package or prebuild the Swift kernel server for the macOS app.
- Launch, monitor, and terminate the Swift IPC process with the app server.
- Keep kernel process logs out of git and scan them for secrets.
- Add release checks proving the app bundle can use Swift IPC without relying on a source checkout.

Acceptance criteria:

- `make dogfood-release` has a Swift IPC mode and fails if the app falls back to `SwiftKernelStub`.
- Stage, commit, undo, and denial flows work through the packaged app bundle using Swift IPC.
- Restarting the app does not leave orphaned Swift kernel processes.

## P5 Live Codex Executive

Status: Not started
Owner: product engineering and model integration
Goal: replace the deterministic local Codex planner/explainer path with a live model-backed executive while preserving the existing tool, authority, replay, and safety contracts.

### P5.1 Codex Client And Credential Gate

Status: Not started

Required work:

- Add a Codex/OpenAI client abstraction behind the existing planner/runtime boundary.
- Add manual credential setup. When credentials are needed, open the browser or credential UI for the user and pause at the credential field.
- Store credentials only in user-owned secure storage or environment configuration, never in git, replay, logs, screenshots, release reports, or bug reports.
- Add health checks that distinguish: missing credential, invalid credential, network failure, model/tool schema failure, and safety refusal.

Acceptance criteria:

- Fixture mode still runs without credentials and labels itself as fixture.
- Live Codex mode refuses to start or clearly degrades when credentials are missing.
- Secret scan covers committed files, generated run artifacts, logs, release reports, and replay exports.

### P5.2 Model-Backed Tool Planning

Status: Not started

Required work:

- Route user goals through the live Codex model to produce structured tool calls, while keeping Swift/provider writes behind the kernel boundary.
- Validate all model-produced tool calls against the existing contract before execution.
- Keep tool receipts deterministic and replayable even when planning is model-backed.
- Add redaction for prompts, user calendar payloads, model responses, and trace summaries.

Acceptance criteria:

- A live-mode browser E2E proves that the executive plan came from the live model path, not `CodexToolPlanner` hardcoding.
- Invalid model tool calls are rejected with visible recovery guidance and replay evidence.
- Denial, undo, feedback, and profile repair still work with live Codex planning.

## P6 DiffusionGemma / NVIDIA NIM Policy Serving

Status: Not started
Owner: model integration
Goal: replace or augment the heuristic `DiffusionGemmaPolicy` with a real served policy endpoint.

### P6.1 Policy Client And Endpoint Configuration

Status: Not started

Required work:

- Add a model-serving client for DiffusionGemma/NVIDIA NIM or the selected production policy endpoint.
- Add manual NVIDIA NIM/API-key setup when live policy serving is enabled.
- Make endpoint URL, model name, timeout, retry policy, and fallback behavior explicit in health/config output.
- Keep local heuristic policy available only as an explicit fixture or fallback mode.

Acceptance criteria:

- Health checks distinguish local heuristic policy from live DiffusionGemma/NIM policy.
- Missing or invalid NIM credentials block live policy mode and produce actionable UI.
- Release reports record policy backend provenance without recording secrets.

### P6.2 Candidate Frontier Provenance

Status: Not started

Required work:

- Validate model-produced candidates against `CandidateCalendarAction` contracts before scoring or acting.
- Preserve candidate provenance: model backend, model version, prompt/template version, decoding settings, fallback state, and validation errors.
- Add tests that prove live policy candidates are not silently replaced by heuristic candidates in live mode.

Acceptance criteria:

- Candidate cards show policy provenance in the inspector.
- Replay exports include enough policy metadata to reproduce or debug a frontier.
- Live policy failures do not create provider writes and do not masquerade as successful heuristic output.

## P7 Provider Truth And OAuth

Status: Not started
Owner: provider/runtime engineering
Goal: replace provider stubs with truthful calendar read/write behavior while preserving authority, idempotency, rollback, and conflict guarantees.

### P7.1 Deterministic Provider State

Status: Not started

Required work:

- Before real OAuth rollout, add a deterministic provider adapter with persisted calendar state.
- Track external IDs, idempotency keys, conflict truth, generated events, moved events, deleted events, and rollback verification.
- Make provider state visible in the inspector and replay.

Acceptance criteria:

- Commit creates a provider object with an external ID and idempotency key.
- Undo verifies provider rollback, not just local receipt mutation.
- Conflict tests use provider truth instead of only sample-calendar heuristics.

### P7.2 Real Provider OAuth

Status: Not started

Required work:

- Implement at least one real provider path end to end: OAuth, token refresh, read observation, write, move/delete where supported, conflict check, rollback, and error recovery.
- Store provider tokens outside git, replay, logs, screenshots, and release reports.
- Add a manual credential setup flow where the browser is opened for the user to authenticate.
- Add provider-specific denial and recovery states for expired tokens, revoked grants, network failures, conflicts, duplicate writes, and partial rollbacks.

Acceptance criteria:

- A dogfood user can connect a real calendar account and see a real observation.
- A safe private commit writes to the provider, returns an external ID, and can be undone.
- Real provider dogfood is separated from fixture dogfood in UI, release reports, and replay exports.

## P8 Production Desktop Launch And Distribution

Status: Not started
Owner: product engineering and release engineering
Goal: make the desktop app launch the intended server/runtime and fail visibly when it cannot.

### P8.1 Port Ownership And Startup Handshake

Status: Not started

Required work:

- Replace blind fixed-port launch with owned-port locking or free-port selection.
- Add a startup handshake proving that the opened browser URL belongs to the process launched by the app bundle.
- If port `8787` is already occupied, either attach only after process identity is verified or choose another port and open that URL.
- Do not open the browser until `/api/health` confirms the launched process, runtime mode, and session ID.

Acceptance criteria:

- Double-clicking the app cannot silently show a stale CalendarPilot server.
- Launch failures are visible to the user and recorded in app logs.
- Release checks cover occupied-port and stale-server scenarios.

### P8.2 Production Release Gate

Status: Not started

Required work:

- Add release targets for fixture, Swift IPC, live Codex, live DiffusionGemma/NIM, live provider, and production modes.
- Require mode-specific checks rather than one generic green release report.
- Add signed/notarized app distribution checks if the app leaves local dogfood.

Acceptance criteria:

- Production release cannot pass if any live backend is silently replaced by fixture/stub behavior.
- Generated artifacts clearly separate fixture, live-model, live-provider, and production evidence.
- A dogfood team member can identify the app version, backend mode, credential state, and launch process from the UI and release report.

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

Run these additional scenarios as P3-P8 come online:

1. Mode truth: launch fixture and live-targeted modes, then verify UI, `/api/health`, replay export, and release report agree on backend mode.
2. Static fallback: break `/api/state` intentionally and verify the app labels the state as offline fixture fallback rather than live product state.
3. Swift IPC: stage, commit, deny, and undo through compiled Swift; verify receipts identify the IPC server.
4. Live Codex: submit a goal and verify the executive plan came from the live model client, with validated tool calls and redacted replay traces.
5. Live policy: generate a candidate frontier from DiffusionGemma/NIM and verify model provenance appears in the inspector and replay.
6. Provider fixture: write, detect duplicate write, conflict, undo, and rollback against persisted deterministic provider state.
7. Real provider: OAuth into one calendar provider, read an observation, write a safe private event, undo it, and verify external state.
8. Desktop stale-port: start a stale server on `8787`, double-click the app, and verify the launched app either owns the URL or fails visibly.

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

## Production Integration Scorecard

| Metric | P3 Target | P4 Target | P5 Target | P6 Target | P7 Target | P8 Target |
|---|---|---|---|---|---|---|
| Runtime mode truth | visible and in `/api/health` | shows IPC backend | shows live Codex state | shows live policy state | shows provider state | shown in launched app |
| Fixture fallback | explicit only | cannot hide IPC failure | cannot hide Codex failure | cannot hide NIM failure | cannot hide provider failure | cannot hide stale launch |
| Swift backend | labeled stub or IPC | compiled IPC receipts | live Codex routes through kernel | live policy routes through kernel | provider writes behind kernel | packaged lifecycle managed |
| Codex backend | deterministic labeled | deterministic labeled | live model-backed planner | live planner compatible | live planner compatible | production-gated |
| DiffusionGemma backend | heuristic labeled | heuristic labeled | heuristic or live labeled | live NIM/model provenance | live or provider-safe fallback | production-gated |
| Provider backend | `local_stub` labeled | `local_stub` labeled | `local_stub` labeled | `local_stub` labeled | deterministic and real OAuth paths | production-gated |
| Credentials | none required in fixture | none unless IPC packaging needs local toolchain | Codex/OpenAI gate | NVIDIA NIM gate | OAuth gate | all gates visible |
| Secret hygiene | scan artifacts | scan IPC logs | scan model traces | scan NIM traces | scan provider traces | scan launch logs |
| Release evidence | mode report | IPC report | live Codex report | live policy report | provider report | production app report |

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
| 2026-07-01 | P2 release gate | Added `scripts/run_dogfood_release.py` and `make dogfood-release` to run Python tests, Swift tests, mandatory browser E2E, macOS app build, app bundle rendered-browser sanity, LaunchServices smoke, artifact validation, and tracked/generated secret scan. | Release report passed at `calendar-pilot-frontend 2/runs/release/dogfood_release_report.json`. |
| 2026-07-01 | P2 app bundle | Built `dist/CalendarPilot.app`, verified bundled source/static/data layout, launched the bundle executable on a free port with run state outside the bundle, ran the rendered browser workflow against the bundled app server, and smoke-tested `open -n CalendarPilot.app` on default port `8787`. | `mac_app_sanity` and `launchservices_smoke` passed in the release report. |
| 2026-07-01 | P2 desktop shortcut | Updated `/Users/temp/Desktop/CalendarPilot.app` to point at `calendar-pilot-frontend 2/dist/CalendarPilot.app`. | Shortcut target verified with `readlink`. |
| 2026-07-01 | P2 credentials | Confirmed local fixture dogfood requires no Codex Auth, provider OAuth, or DiffusionGemma/NVIDIA NIM credentials. | `secret_scan` passed in the release report. |
| 2026-07-01 | P2 final release hardening | Added timeout bounds to release-gate subprocesses, made timeout log capture bytes-safe, validated logs and current release report artifacts, and added a release-report secret scan. | `make dogfood-release` passed with `artifact_validation`, `secret_scan`, `release_report_validation`, and `release_report_secret_scan` all true. |
| 2026-07-01 | P3+ gap audit | Inspected the desktop-launched `http://127.0.0.1:8787/` app and verified it is the current v2 bundle, but fixture-backed: `dev.calendarpilot.fixture`, sample calendar/profile data, `SwiftKernelStub`, deterministic `CodexToolPlanner`, heuristic `DiffusionGemmaPolicy`, provider stubs, and fixed-port launch. | Added P3-P8 gates for runtime mode truth, Swift IPC, live Codex, DiffusionGemma/NIM, provider OAuth, and production desktop launch. |
| 2026-07-01 | P3 runtime mode truth | Added explicit runtime reporting, `/api/health`, first-viewport runtime chip, runtime inspector rows, replay runtime provenance, `health.json` browser artifact, and release `runtime_mode_gate`. Production-targeted mode now fails when still backed by fixtures/stubs. | `make py-test`, `make browser-e2e`, and `make dogfood-release` passed in fixture mode; production gate probe returned blockers for sample fixtures, `SwiftKernelStub`, deterministic planner, heuristic policy, and `local_stub`. |
| 2026-07-01 | P4 Swift IPC runtime | Added a shared Python kernel protocol, made `SwiftKernelIPCClient` match the stub-shaped planner interface, added Swift `preview` RPC support, selected IPC in `swift_ipc` runtime mode, packaged a release-built `CalendarPilotKernelServer` binary in the app, and added Swift IPC release lanes. | `make py-test`, `make swift-test`, `make swift-ipc-test`, `make browser-e2e`, `make mac-app-build`, and `make dogfood-release` passed. Release report shows `mac_app_swift_ipc_sanity` passed with runtime `swift_ipc`, kernel `SwiftKernelIPCClient`, no live blockers, and no orphaned `CalendarPilotKernelServer` process. |
| 2026-07-01 | P4 architectural review fixes | Addressed review blockers by serializing and id-checking IPC RPCs, propagating correlation IDs through Python and Swift receipts, and restoring persisted Swift IPC authority grants plus active rollback handles after app restart. | `make py-test`, `make swift-test`, `make swift-ipc-test`, and `make browser-e2e` passed. `test_swift_ipc_runtime.py` now covers restart undo rehydration, receipt correlation provenance, and concurrent RPC calls. |

## Review Log

| Date | Phase | Reviewer | Result | Follow-up |
|---|---|---|---|---|
| 2026-07-01 | P0 | Bohr | Found string boolean authority confirmation risk, missing HTTP API coverage, incomplete persistence assertions, and corrupt-state risk. | Fixed with `body_bool`, `test_frontend_server_api.py`, stronger restart assertions, and visible corrupt restore recovery. |
| 2026-07-01 | P0 | Epicurus | Found premature review bookkeeping, missing HTTP API coverage, root command ambiguity, weak app bundle evidence, and stale browser run risk. | Fixed with review log, HTTP tests, root Makefile delegation, packaged app source layout, and browser run-dir cleanup. |
| 2026-07-01 | P1 | Hilbert | Found optional browser false pass, synthetic CDP interaction, startup cleanup leak, ambiguous artifacts, and stale low-authority card risk. | Made browser mandatory by default, added visible hit-tested mouse/input events, fixed startup cleanup, wrote browser replay artifacts, and waits for the new candidate card. |
| 2026-07-01 | P1 | Sagan | Found premature P1 status, missing live restart proof, weak denial evidence, and replay artifacts written before browser controls. | Added actual stop/start restart check, real low-authority denial, browser-generated replay export before reset, and review log entries. |
| 2026-07-01 | P2 | Volta | Found browser skip could leak into release, app sanity did not prove bundled UI, generated artifacts were not scanned, and expected artifacts were not validated. | Release gate clears skip env, runs bundled-app rendered browser workflow, validates artifacts, scans tracked plus generated `runs/` and `dist/`, and adds command timeouts. |
| 2026-07-01 | P2 | Boyle | Found LaunchServices path was not verified, app sanity did not exercise P1 workflows, credential gate was hardcoded, and desktop shortcut replacement was brittle. | Added `open -n` LaunchServices smoke, reused rendered browser workflow against bundled app, derives credential refs from runtime/frontend code, and backs up existing Desktop app directories before linking. |
| 2026-07-01 | P2 | Volta final | Found remaining timeout and current-report validation gaps in the release gate. | Added timeouts for `open`, `lsof`, `kill`, and `git ls-files`; made `TimeoutExpired` output bytes-safe; validated and secret-scanned the current release report. Volta and Boyle cleared P2. |
| 2026-07-01 | P3+ planning | Gauss | Independently confirmed P2 certifies fixture dogfood only; live Codex/OpenAI, DiffusionGemma/NIM, Swift IPC app selection, provider OAuth, and stale-port launch are not solved. | Incorporated the proposed P3-P8 phase gates into this framework. |
| 2026-07-01 | P3 | Locke | Found invalid runtime modes could be silently coerced to fixture-safe and noted weaker bundled build provenance plus fixture credential false-positive. | Fixed invalid-mode reporting/gating, persisted requested/effective mode, bundled `build_id`, and runtime-derived credential reporting. Locke re-reviewed and cleared P3. |

## Open Risks

| Risk | Phase | Mitigation |
|---|---|---|
| Fixture mode can be mistaken for production integration. | P3 | Add explicit runtime mode UI, health endpoint, replay provenance, and release-mode gates. |
| Swift IPC can regress to the Python stub if mode selection or app packaging breaks. | P4 | Shared kernel protocol, packaged IPC binary, `swift_ipc_runtime_mode_gate`, `swift-ipc-test`, and `mac_app_swift_ipc_sanity` now fail if Swift IPC falls back to `SwiftKernelStub`. |
| Live Codex/OpenAI planning is not integrated. | P5 | Add model-backed planner client, credential gate, tool-call validation, redaction, and live-mode E2E. |
| DiffusionGemma/NIM policy serving is not integrated. | P6 | Add NIM endpoint configuration, credential gate, health checks, candidate provenance, and failure behavior. |
| Real provider/OAuth behavior is not included in fixture dogfood. | P7 | Add deterministic provider state first, then one real OAuth provider with external IDs, idempotency, conflict truth, and rollback verification. |
| Fixed-port desktop launch can show a stale server. | P8 | Add port ownership or free-port launch, process identity handshake, and occupied-port release checks. |
