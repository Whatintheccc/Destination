# CalendarPilot E2E Dogfooding Framework

This framework tests CalendarPilot as a full app, not as isolated modules. The product loop under test is:

```text
raw calendar observation
-> DiffusionGemma candidate frontier
-> Codex tool deliberation
-> Swift authority grant, stage, commit, denial, or undo
-> feedback and adversary findings
-> replay export
-> offline policy tuning
-> next run
```

Run every command from the repo snapshot:

```bash
cd "calendar-pilot-updated 2"
```

## Current Goal: One Conversational Access Point

The migration commit `4a2c06b calendar-pilot-updated 2` moved the previous `calendar-pilot-frontend 2` tree into `Do-not-reference/` and added `calendar-pilot-updated 2` as the active app. The updated tree added the right ingredients for a single assistant entry point: runtime profiles, live Codex planning, live DiffusionGemma policy, Swift IPC, EventKit/provider adapters, app-bundle launch state, replay, and a chat-first frontend.

The remaining product goal is not just that those features exist. The first user-visible access point must behave like one conversational assistant that can route to the right backend, expose whether a live endpoint was reached, and fall back transparently when a live dependency is unavailable.

### Gap Review

1. Conversation routing was split by implementation path. Fixture chat could be handled locally, calendar goals could enter the deterministic or live planner, but non-calendar turns in live modes did not have a Codex conversation path.
2. Runtime controls exposed feature modes, but the latest turn metadata was buried in the last chat message. Testers had to know where to look to prove whether Codex, DiffusionGemma, Swift, or the provider participated.
3. `production` mode is the only profile that attempts to load Codex, DiffusionGemma, Swift IPC, and the live provider together, but it is credential-gated and too strict to be the default launch path. The product needs an `auto` assistant runtime that enables every healthy live backend, keeps deterministic fallbacks only for unavailable dependencies, and reports those fallbacks clearly.
4. Live Codex planning had endpoint metadata for calendar plans, but there was no equivalent conversation result contract for metadata/smalltalk/status questions.
5. DiffusionGemma live generation previously had a hard-coded generic goal; the runtime must forward the user goal into policy generation so candidate futures are tied to the conversation.
6. The composer posts every turn to `/api/plans`, and the app now has a conversation tool bridge for replay, profile, self-play, authority, denial, and undo. Inspector buttons remain useful secondary affordances, but the composer has to stay the primary dogfood path.
7. Runtime modes are still partitioned. `live_codex`, `live_diffusiongemma`, and `live_provider` each enable one live subsystem; only `production` composes all live backends. The first assistant turn now reports active backends and blockers, but production still needs a full healthy-backend acceptance pass.
8. Conversations now have create/list/switch APIs with separate run directories and replay identities. Session summaries are read without hydrating inactive runtimes, the last active session survives restart, and browser requests carry `session_id` so separate windows do not steal each other's conversation context.
9. Computer Use review of the current CalendarPilot transcript showed why the initial experience felt hard coded: the first `hello` and `what ru` turns were handled in fixture/local mode, then pressing `Live Codex` switched the active session to `live_codex`. The current chip can truthfully show Live Codex while older fixture messages remain in history, but this is bad UX unless the app labels historical runtime and launches into the ready assistant automatically. New chats can also regress to the fixture launch default because the macOS launcher and Python launch defaults still start from fixture.

### Deliverables

1. **Conversation gateway:** In `live_codex` and `production`, every non-calendar turn must route to a Codex app-server conversation call and return response/thread/turn metadata. Fixture mode may keep local deterministic handling, but must label it as local.
2. **Calendar planning gateway:** Calendar goals must still route through the bounded planner: Codex plans tool calls, DiffusionGemma generates/ranks candidates, Swift validates stage/commit/undo, and provider writes stay behind adapters.
3. **Latest-turn metadata:** `/api/state` must expose the latest assistant turn metadata at a stable summary path, in addition to the rendered chat message.
4. **Goal propagation:** Candidate-frontier generation must receive the user's actual goal, including live DiffusionGemma mode.
5. **Dogfood proof:** Automated tests and a UI run must show one local fixture turn and one live-Codex-routable turn with clear `model_reached`, backend, response ID, tool sequence, replay count, and candidate/action state.
6. **Composer tool coverage:** Codex must be able to route replay query, profile inspection/repair proposal, self-play, authority inspection, denial explanation, and undo requests from the composer, with the same receipt/authority checks as inspector actions.
7. **Ready-assistant runtime:** Add a user-facing assistant-ready mode or production preflight that composes every healthy backend and explains unavailable live capabilities in chat.
8. **Real sessions:** Add session create/list/switch APIs so sidebar conversations are not only a reset affordance.
9. **Launch health contract:** `launch_state.json` and `/api/health` must agree after macOS/Finder launch.
10. **Auto assistant default:** macOS/Finder launches with no runtime env must resolve to an assistant-ready `auto` runtime. If Codex auth is configured, the first conversational turn must reach live Codex without requiring the tester to press `Live Codex`; Swift IPC should be used when bundled; optional DiffusionGemma/provider local modes must be visible as setup notes, while true blockers are reserved for required broken paths.
11. **Fresh-launch proof:** A clean, isolated launch with no `CALENDAR_PILOT_RUNTIME_MODE` must show the ready assistant state, submit `hello`, and persist metadata proving `model_reached=true`, `response_source=live_codex_conversation`, and live Codex response/thread/turn IDs when auth is available.
12. **Runtime history clarity:** Restored transcripts must make it clear which turns were fixture/local and which were live. The top runtime chip may show the current runtime, but message metadata and state summaries must explain mixed history so testers do not mistake old local turns for a live endpoint failure.

### Implementation Status

- Done: fixture/local turns now expose trace metadata in chat.
- Done: user goals are forwarded into DiffusionGemma policy generation.
- Done: live Codex non-calendar turns now have a conversation endpoint path in code.
- Done: `/api/state` now exposes `summary.latest_turn` and `chat.latest_message_metadata`.
- Done: Launch manifests now persist runtime health, and the release smoke rereads launch state after HTTP readiness.
- Done after subagent review: restored sessions also write launch health, failed live Codex chat attempts are titled `Codex unavailable`, and live DiffusionGemma goal forwarding has a direct NIM-wrapper regression test.
- Done in this pass: live Codex conversation responses can return audited `tool_calls` for replay query, profile inspection/repair proposal, self-play, authority inspection, denial explanation, and undo. Python executes those through the local `CodexToolRuntime`, attaches receipt cards to the same assistant message, and preserves response/thread/turn metadata when the model was reached.
- Done in this pass: fixture mode has deterministic composer routing for replay/profile/self-play/denial/authority/undo so dogfood can prove the single access point without relying on live model variability.
- Done in this pass: operational intent classification now lets explicit profile/replay/self-play/denial/scope/undo requests win, while calendar/action/commit goals still route to planning.
- Done in this pass: the initial assistant message is runtime-aware and reports active Codex, DiffusionGemma, Swift, and provider backends plus live blockers.
- Done in this pass: button/inspector receipt actions now attach normalized latest-turn metadata instead of leaving receipt turns metadata-empty.
- Done after final subagent review: failed composer self-play probes now record `probe_failed` instead of a passing release gate, restored non-fixture sessions refresh top-level `launch_state.json` runtime mode to match `/api/health`, and feedback turns now expose latest-turn metadata.
- Done in this pass: `New chat` now creates a durable session instead of resetting the active run, `/api/sessions` lists sessions, `/api/sessions/switch` restores a prior run, sidebar rows switch between sessions while preserving separate replay state, and normal frontend actions route with a `session_id`.
- Done after session subagent review: session launch manifests preserve the actual server host/port, sidebar summaries no longer instantiate inactive sessions, the active-session pointer persists across restart, and session summary reads hold the manager lock.
- Done in this pass: explicit composer confirmation can apply the latest profile patch, and composer requests can propose a bounded autonomy scope for the latest candidate while still returning a confirmation-required receipt.
- Done after session re-review: targeted POST error responses now return the requested session state instead of drifting to the global active session.
- Done after final subagent review: composer profile apply now fails closed when there is no valid proposed patch, failed or malformed profile proposals cannot unlock apply, autonomy-scope requests without a selected/latest candidate report failure instead of a misleading proposal, and top-level `launch_state.json` mirrors active child runtime changes plus health after restore.
- Done in this pass: mixed calendar plus operational turns, including profile repair and undo requests, now keep the calendar planner as the primary route, attach requested operational evidence receipts to the same assistant message, preserve candidate cards, and expose planner/conversation tool metadata together. Bare composer undo requests such as `undo`, `undo it`, `rollback`, and `revert` route to Swift undo receipts.
- Done in this pass: session labels and archived state now persist, `/api/sessions/rename` and `/api/sessions/archive` back sidebar controls, archived sessions are hidden from normal summaries, and archiving the active conversation switches to an unarchived session.
- Verified: full Python suite passed with 114 tests and 8 skips after the composer-tool and session fixes; targeted live/session/server tests, `make swift-test`, `make swift-ipc-test`, `py_compile` for the touched Python modules, `node --check frontend/static/app.js`, `node --check scripts/browser_cdp_e2e.mjs`, `git diff --check`, and `make browser-e2e` passed. The browser e2e now includes New Chat, rename, archive, and switch-back checks.
- Verified in this pass: `make dogfood-release` passed and wrote `runs/release/dogfood_release_report.json`; it covered Python tests, Swift tests, Swift IPC tests, browser e2e, mac app build, mac app sanity, Swift IPC app sanity, LaunchServices smoke, occupied-port launch, artifact validation, and secret scans. The live EventKit mutating release probe remained intentionally opt-in/skipped.
- Verified in this pass: `make live-codex-e2e` passed with `runs/live_codex_e2e/artifacts/live_plan_state.json` showing `runtime_mode=live_codex`, `planner_backend=live_codex_app_server`, `model_reached=true`, live `response_id`, `thread_id`, `turn_id`, six candidate cards, and replay evidence.
- Verified with Computer Use and API state: rebuilt macOS app launched in `live_codex` mode on `127.0.0.1:8791`; prompt `hello metadata check` persisted in `runs/one-access-ui-test-final/latest_session.json` with `title=Codex answered`, `response_source=live_codex_conversation`, `model_reached=true`, `planner_backend=live_codex_app_server`, `kernel_backend=SwiftKernelIPCClient`, and live `response_id`, `thread_id`, and `turn_id`.
- Diagnosed with Computer Use and subagent review: the current CalendarPilot conversation required pressing `Live Codex` because fresh macOS launch still defaulted to fixture. The transcript confirms the early `hello` and `what ru` turns were local fixture responses, then the runtime changed to `live_codex` and later turns reached the Codex app-server path. This is a default-runtime and runtime-history UX gap, not evidence that the live Codex endpoint is unreachable after the switch.
- Done in this pass: implemented `auto` as the macOS/Finder/Python launch default. It routes conversational turns to live Codex when Codex auth is present, uses Swift IPC when bundled, keeps heuristic DiffusionGemma and deterministic provider adapters as optional local modes, and exposes those local modes through `setup_notes` rather than `live_blockers`.
- Fixed in this pass: the bad `DiffusionGemma is using heuristic... because diffusiongemma_nim is missing` style answer came from our own runtime context. `auto` had marked optional NIM/provider credentials as required blockers, `_conversation_prompt()` told Codex to be explicit about active backends, and `_conversation_runtime_context()` exposed absent optional credentials. Smalltalk now hides optional credential/setup diagnostics; metadata questions still show them, but as setup notes and not endpoint failures.
- Verified with Computer Use and API metadata: rebuilt macOS app launched with no runtime env on `127.0.0.1:8798`; prompt `hello` returned `Codex answered` with body `Hello. How can I help?`, `response_source=live_codex_conversation`, `model_reached=true`, live response/thread/turn IDs, `runtime_mode=auto`, `planner_backend=live_codex_app_server`, `kernel_backend=SwiftKernelIPCClient`, and `live_blockers=[]`. The only fallback evidence was `setup_notes` for local heuristic DiffusionGemma and deterministic provider mode.
- Current production preflight evidence: `production` composes `live_codex_app_server`, `nvidia_nim_diffusiongemma_policy`, `SwiftKernelIPCClient`, and `apple_eventkit`; Codex subscription auth is configured from the auth cache, but this environment still reports blockers for missing DiffusionGemma NIM credentials, missing provider OAuth/permission, sample fixture data, and EventKit `not_determined` authorization. That strict production gate is separate from the default `auto` UX.
- Remaining P0: production healthy-backend acceptance must be rerun in an environment with NIM credentials and provider authorization, and must prove Codex, DiffusionGemma, Swift IPC, and live provider are all active together with no blockers.
- Remaining P1: run credentialed/live integration validation for actual NIM DiffusionGemma, EventKit, and provider OAuth paths. The default `auto` experience can use local modes, but production/live gates still need proof that those external integrations work when credentials and permissions are present.
- Remaining P1: keep expanding restore and mixed-history coverage so clean launches, prior-fixture restores, prior-live restores, and New Chat all preserve the assistant-ready runtime and make historical fixture messages understandable.
- Remaining P2: label historical message runtime in the UI/state summary so a restored Live Codex session with earlier fixture turns is understandable.

### Current Conversation Diagnosis And Next Steps

- UI evidence: Computer Use showed the current app running from `calendar-pilot-updated 2/dist/CalendarPilot.app` with the chip in `Live Codex mode`, but the transcript itself began with fixture/local assistant messages. The `hello` and `what ru` turns were titled `Conversation handled locally`; only after the runtime-change message did `what r u` produce `Codex answered` with live Codex metadata.
- Code root cause: the macOS launcher still defaults `CALENDAR_PILOT_RUNTIME_MODE` to `fixture`, and Python launch/session defaults also fall back to fixture. Pressing `Live Codex` updates the active session, but it does not prove the first-launch path is assistant-ready, and a new conversation can still inherit the original fixture launch default.
- Subagent review: the reviewer agreed this is not a live Codex endpoint outage after the switch. It is a startup runtime and product-routing gap. `production` is too credential-gated for the default, while `live_codex` is too narrow because DiffusionGemma/provider readiness remains implicit.
- Current bad-output diagnosis: the assistant did not independently discover that DiffusionGemma or provider endpoints were broken. CalendarPilot supplied a runtime report that mislabeled optional auto-mode local adapters as missing required credentials, then instructed Codex to be explicit about active backends. Codex repeated that diagnostic context in a normal chat answer.
- Next implementation deliverables: validate credentialed NIM DiffusionGemma, EventKit, and provider OAuth paths in an environment where those credentials are intentionally configured; keep default `auto` smalltalk free of backend diagnostics unless the user asks for metadata/status; add regression coverage that optional auto setup notes are not surfaced as live blockers.

## 0. Run Rules

1. Product dogfood starts with the macOS/Finder auto assistant runtime. Fixture mode is an explicit regression/offline gate, not the first user-visible path.
2. Treat Swift as the authority boundary. A passing test must show grant IDs, staged or committed receipts, denial reasons, and rollback handles where applicable.
3. Keep evidence for every run under `runs/`. Do not judge a dogfood pass from terminal output alone.
4. Stop on any P0 failure: tests fail, browser cannot complete the action loop, replay is empty, authority denial is missing, undo is unavailable after a committed write, or artifacts leak credentials.
5. File every product issue with the artifact path, runtime mode, action taken, expected result, actual result, and replay/session IDs.

## 1. Prerequisite Check

```bash
python3 --version
swift --version
node --version
test -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" || python3 -m pip show playwright
```

Pass criteria:

- Python and Swift are available.
- Browser automation can use Chrome plus Node, or Playwright.
- For mac app checks, the host is macOS.
- For live DiffusionGemma, one of `CALENDAR_PILOT_NIM_API_KEY`, `NVIDIA_API_KEY`, or `NIM_API_KEY` is configured.
- For live Codex, ChatGPT subscription auth is available through `CODEX_ACCESS_TOKEN` or the Codex auth cache.
- For live provider checks, `CALENDAR_PILOT_REQUIRE_EVENTKIT=1` is used only when Apple Calendar/EventKit is intentionally configured.

## 2. Clean Test Workspace

```bash
rm -rf runs/dogfood runs/browser_e2e runs/live_codex_e2e runs/live_diffusiongemma_e2e runs/eventkit_e2e runs/release
mkdir -p runs/dogfood/logs
```

Record:

- current git commit or build ID;
- runtime mode;
- OS version;
- credential modes intentionally enabled.

## 3. Contract And Unit Gates

```bash
make py-test 2>&1 | tee runs/dogfood/logs/py-test.log
make swift-test 2>&1 | tee runs/dogfood/logs/swift-test.log
make swift-ipc-test 2>&1 | tee runs/dogfood/logs/swift-ipc-test.log
```

Pass criteria:

- Python tests pass.
- Swift package tests pass.
- Swift IPC tests pass.
- Contract parity holds across Python dataclasses, JSON schemas, and Swift Codable models.
- Authority-grant tests prove Codex cannot self-assign authority with embedded grant payloads.

## 4. CLI Product Loop

Run the default Codex-executive app path with commit enabled:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --profile data/sample_profile.json \
  --authority-tier 3 \
  --self-play 2 \
  --replay-out runs/dogfood/replay.jsonl \
  --commit \
  2>&1 | tee runs/dogfood/logs/cli-demo.log
```

Pass criteria:

- Output includes `Codex executive plan`.
- The trace follows inspect, candidate frontier, compare, simulate, stage, and commit or denial.
- The Swift-facing receipt has explicit status such as `committed`, `stageable`, `requires_confirmation`, or `denied`.
- Safe private writes produce rollback handles when committed.
- Self-play emits metrics and named failure modes.
- `runs/dogfood/replay.jsonl` exists and is non-empty.

Reduce the replay into policy evidence:

```bash
PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay runs/dogfood/replay.jsonl \
  --out runs/dogfood/offline_policy_report.json \
  --tuning-out runs/dogfood/policy_tuning.json \
  2>&1 | tee runs/dogfood/logs/offline-policy.log
```

Pass criteria:

- `offline_policy_report.json` contains reward residuals, denial rates, or failure penalties by intent.
- `policy_tuning.json` is valid JSON and can feed a future policy run.

## 5. Frontend Snapshot Gate

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend \
  --write-snapshot \
  --out runs/dogfood/frontend_state.sample.json \
  2>&1 | tee runs/dogfood/logs/frontend-snapshot.log
```

Pass criteria:

- Snapshot contains `chat.messages`, `chat.candidate_cards`, receipt cards, `inspector.authority`, `inspector.profile`, `inspector.replay`, `inspector.self_play`, provider/debug state, and runtime metadata.
- Candidate cards expose model story, counterfactual, reward anatomy, regret, social risk, and right-moment decision.
- Acting queue state distinguishes simulation, staged draft/notification, committed write, denial, and undo.

## 6. Fixture Browser E2E Gate

Run the canonical rendered app test:

```bash
make browser-e2e 2>&1 | tee runs/dogfood/logs/browser-e2e.log
```

This script verifies:

1. static frontend markers exist;
2. `/api/state`, `/api/health`, `/api/plans`, candidate simulate/stage/confirm, feedback, profile repair, self-play, authority update, denial explanation, undo, replay, replay export, invalid POST handling, and reset;
3. state persists across server restart;
4. a real browser completes the visible chat/action flow;
5. artifacts are written to `runs/browser_e2e/artifacts/`.

Pass criteria:

- The script prints `browser e2e passed`.
- `runs/browser_e2e/artifacts/browser_success.png` exists.
- `runs/browser_e2e/artifacts/replay_export.json` and `browser_replay_export.json` contain records.
- `runs/browser_e2e/artifacts/health.json` reports `runtime_mode: fixture` and `kernel: SwiftKernelStub`.
- The low-authority commit path produces a visible Swift denial.
- Undo and feedback are visible in chat or inspector state.

## 7. Manual Browser Dogfood Pass

Start the app:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend \
  --serve \
  --host 127.0.0.1 \
  --port 8787 \
  --run-dir runs/dogfood/manual-server
```

Do not set `CALENDAR_PILOT_RUNTIME_MODE` for this product-path check. If the app reports fixture mode here while Codex auth is configured, stop and fix the auto assistant default before continuing. Fixture behavior is covered by section 6.

Open `http://127.0.0.1:8787` and perform this script:

1. Confirm the runtime chip says `auto assistant` or `Live Codex`, not fixture, when Codex auth is configured. The ready message must list Codex, DiffusionGemma, Swift, and provider backends; optional auto-mode local adapters appear as setup notes, not live blockers.
2. Submit `hello`. Confirm it reaches live Codex without pressing `Live Codex`; latest-turn metadata must include `model_reached=true`, `response_source=live_codex_conversation`, and response/thread/turn IDs when auth is available.
3. Submit `Make next week less chaotic`.
4. Inspect the first candidate future. It must show why the policy chose it, what happens if nothing changes, reward/regret anatomy, and timing decision.
5. Stage the candidate. Confirm a receipt appears in the acting queue.
6. Commit the candidate. Confirm a rollback handle or undo control appears for committed private writes.
7. Submit `show replay trace` in the composer. Confirm the assistant attaches a `query_replay_trace` receipt and latest-turn metadata lists that tool.
8. Submit `repair my profile: Prefer planning blocks before lunch.` Confirm the assistant attaches a `propose_profile_patch` receipt and the patch still requires explicit apply confirmation.
9. Submit `run self-play 2` in the composer. Confirm the assistant attaches a `run_self_play_probe` receipt and self-play history updates.
10. Submit `undo the last change` in the composer. Confirm Swift returns a `request_undo` receipt with `sync_status: reverted`.
11. Mark feedback as useful. Confirm feedback appears in inspector state.
12. Open replay and export it. Confirm records are visible.
13. Lower authority to tier 0 or tier 2 without confirmation, then attempt a commit. Confirm Swift denial is visible, then submit `explain the denial` in the composer.
14. Start a new chat and confirm it remains in the assistant-ready runtime instead of reverting to fixture.

Pass criteria:

- The first smalltalk turn reaches live Codex without any runtime button press when Codex auth is configured.
- Auto mode reports optional local DiffusionGemma/provider adapters as setup notes; only missing Codex/Swift requirements or explicitly selected live/production backend failures become blockers.
- No action silently mutates state without a receipt.
- A denial explains the missing authority or scope.
- Profile repair requires an explicit apply step.
- Replay can reconstruct the dogfood path.
- Composer prompts can exercise replay, profile repair proposal, self-play, denial explanation, and undo without using inspector buttons as the primary path.

## 8. Swift IPC Runtime Gate

Use Swift IPC when validating the real grant registry and undo ledger process:

```bash
CALENDAR_PILOT_RUNTIME_MODE=swift_ipc \
PYTHONPATH=src python3 -m calendar_pilot.app frontend \
  --serve \
  --host 127.0.0.1 \
  --port 8788 \
  --run-dir runs/dogfood/swift-ipc-server
```

Then run the same browser script against `http://127.0.0.1:8788`, or run the release script in section 12.

Pass criteria:

- `/api/health` reports `runtime_mode: swift_ipc`.
- Kernel backend is `SwiftKernelIPCClient`.
- No orphaned `CalendarPilotKernelServer` process remains after shutdown.
- Commit and undo still require live, confirmed, scoped Swift-issued grants.

## 9. Mac App Bundle Gate

```bash
make mac-app-build 2>&1 | tee runs/dogfood/logs/mac-app-build.log
```

Pass criteria:

- `dist/CalendarPilot.app/Contents/MacOS/CalendarPilot` exists and is executable.
- Bundled Python source, static frontend assets, `CalendarPilotKernelServer`, and `CalendarPilotEventKitBridge` exist.
- The app can launch a local server, serve `/`, `/app.js`, `/api/health`, and write `launch_state.json`.
- Runtime mode and server port in health match `launch_state.json`.

Manual launch check:

```bash
CALENDAR_PILOT_OPEN_BROWSER=0 open -n dist/CalendarPilot.app
```

Then inspect the generated run directory and close the app process.

Fresh auto-assistant launch check:

```bash
rm -rf runs/dogfood/auto-fresh
CALENDAR_PILOT_OPEN_BROWSER=0 \
CALENDAR_PILOT_RUN_DIR="$PWD/runs/dogfood/auto-fresh" \
dist/CalendarPilot.app/Contents/MacOS/CalendarPilot
```

Do not set `CALENDAR_PILOT_RUNTIME_MODE` for this check. After the app serves `/`, submit `hello` in the UI or through `/api/plans`, then inspect `runs/dogfood/auto-fresh/launch_state.json`, `/api/health`, and the active session state.

Pass criteria:

- The launch default is `auto` or another assistant-ready runtime, not `fixture`.
- `launch_state.json` and `/api/health` agree on runtime, active backends, setup notes, and true blockers.
- With Codex auth configured, the first `hello` response is titled `Codex answered` or equivalent, includes live response/thread/turn metadata, and does not volunteer optional fallback or endpoint details unless the prompt asks for metadata/status.
- When Codex and Swift are healthy, `/api/health` has `live_blockers: []`; unavailable optional DiffusionGemma/provider integrations appear under `setup_notes`.
- New Chat keeps the assistant-ready runtime.
- Restored mixed-history sessions distinguish fixture/local historical turns from current live turns.

## 10. Credential-Gated Live Mode Gates

Run only when the credential preflight is intentionally satisfied.

Live Codex:

```bash
make live-codex-e2e 2>&1 | tee runs/dogfood/logs/live-codex-e2e.log
```

Pass criteria:

- `/api/health` reports `runtime_mode: live_codex`.
- Kernel backend is `SwiftKernelIPCClient`.
- Codex backend is `live_codex_app_server`.
- Plan metadata includes a live Codex response ID.
- Artifacts do not contain access tokens or API keys.

Live DiffusionGemma:

```bash
make live-diffusiongemma-e2e 2>&1 | tee runs/dogfood/logs/live-diffusiongemma-e2e.log
```

Pass criteria:

- `/api/health` reports `runtime_mode: live_diffusiongemma`.
- DiffusionGemma backend is `nvidia_nim_diffusiongemma_policy`.
- Candidate cards and replay contain NIM policy provenance.
- Artifacts do not contain NIM credentials.

Live EventKit/provider health:

```bash
make live-eventkit-e2e 2>&1 | tee runs/dogfood/logs/live-eventkit-e2e.log
```

Pass criteria:

- `runs/eventkit_e2e/eventkit_health.json` is written.
- If `CALENDAR_PILOT_REQUIRE_EVENTKIT=1`, provider health must be configured.
- Provider tokens and provider truth remain behind Swift/provider adapters.

## 11. Failure Injection Checks

Run these during manual dogfood or as focused API calls:

1. Low authority: set tier 0 or unconfirmed tier 2, then commit. Expected: denied.
2. Missing confirmation: commit with `confirmed=false`. Expected: denied.
3. Social mutation: try a people-affecting action without social scope. Expected: denied or staged, not silent commit.
4. Undo without valid rollback handle. Expected: denied/no-op with visible explanation.
5. Invalid API route. Expected: JSON error plus current state, not server crash.
6. Restart server after activity. Expected: replay, feedback, profile history, self-play history, and denial history restore.
7. Occupied port launch. Expected: app chooses or reports a valid owned port rather than attaching to an unrelated process.

## 12. Release Dogfood Gate

Use this when preparing a shareable build or declaring the snapshot e2e-clean:

```bash
make dogfood-release 2>&1 | tee runs/dogfood/logs/dogfood-release.log
```

The release script runs:

- runtime and credential gates;
- Python, Swift, and Swift IPC tests;
- fixture browser e2e;
- mac app build;
- app bundle sanity in fixture and Swift IPC modes;
- EventKit/provider health gate;
- LaunchServices smoke;
- occupied-port launch gate;
- artifact validation;
- secret scans.

Pass criteria:

- `runs/release/dogfood_release_report.json` has `"ok": true`.
- Every check has an artifact or log path.
- Secret scans pass.
- Browser and app screenshots/replay exports are present.

## 13. Evidence Packet

For each dogfood run, keep or attach:

```text
runs/dogfood/logs/*.log
runs/dogfood/replay.jsonl
runs/dogfood/offline_policy_report.json
runs/dogfood/policy_tuning.json
runs/browser_e2e/artifacts/browser_success.png
runs/browser_e2e/artifacts/replay_export.json
runs/browser_e2e/artifacts/browser_replay_export.json
runs/browser_e2e/artifacts/health.json
runs/release/dogfood_release_report.json
```

Minimum bug report fields:

```text
summary:
runtime_mode:
command_or_manual_step:
expected:
actual:
artifact_paths:
session_id:
trace_id_or_replay_record:
authority_tier:
rollback_handle:
credential_mode:
```

## 14. Exit Criteria

The app is e2e dogfood-clean when:

1. fixture tests, CLI loop, frontend snapshot, browser e2e, and offline policy tuning pass;
2. manual browser pass proves candidate, stage, commit/denial, undo, feedback, profile repair, self-play, replay export, and reset;
3. Swift IPC mode proves the grant registry and undo ledger remain enforced out of process;
4. mac app bundle launches and serves the same app state through `launch_state.json`;
5. credential-gated live modes either pass or produce explicit missing-credential reports;
6. release dogfood report is green for a build intended to be shared;
7. no artifacts leak credentials;
8. every calendar-changing path is recoverable, denied, or explicitly staged.
