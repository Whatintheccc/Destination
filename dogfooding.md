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

## 0. Run Rules

1. Start with fixture mode. Live Codex, live DiffusionGemma, provider, and production modes are release-expansion gates, not the baseline.
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

Open `http://127.0.0.1:8787` and perform this script:

1. Confirm the runtime chip says fixture mode.
2. Submit `Make next week less chaotic`.
3. Inspect the first candidate future. It must show why the policy chose it, what happens if nothing changes, reward/regret anatomy, and timing decision.
4. Stage the candidate. Confirm a receipt appears in the acting queue.
5. Commit the candidate. Confirm a rollback handle or undo control appears for committed private writes.
6. Click undo. Confirm the transcript records an undo request.
7. Mark feedback as useful. Confirm feedback appears in inspector state.
8. Open replay and export it. Confirm records are visible.
9. Propose and apply a profile repair such as `Prefer planning blocks before lunch.`
10. Lower authority to tier 0 or tier 2 without confirmation, then attempt a commit. Confirm Swift denial is visible and explainable.
11. Run self-play from the inspector. Confirm failure modes are summarized.
12. Reset fixture state and confirm the reset message.

Pass criteria:

- No action silently mutates state without a receipt.
- A denial explains the missing authority or scope.
- Profile repair requires an explicit apply step.
- Replay can reconstruct the dogfood path.

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
