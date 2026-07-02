
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

## Working Status Ledger

Last committed baseline reviewed here: `31ff2b9 Make auto assistant the dogfood default`.

Status legend:

- `Complete`: exercised with an artifact or test result.
- `Partial`: some path is proven, but the intended end-to-end product path is not complete.
- `Open`: not yet dogfooded end to end.
- `Blocked`: requires credentials, permissions, account setup, or product contract work not present in the current environment.

### Confirmed Complete Or Partial Criteria

| Area | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Python/Swift/Swift IPC contract gates | Complete | Current local run: `python3 -m pytest -q`, `swift build --package-path packages/CalendarPilotKernel --product CalendarPilotMacApp`, `node --check frontend/static/app.js`, `git diff --check` | Current uncommitted diff was checked locally with `116 passed, 9 skipped`. The older `runs/release/dogfood_release_report.json` is useful baseline evidence, but it predates the latest macOS supervisor, receipt ID, denial, and replay export changes. |
| Fixture browser E2E | Complete | `runs/browser_e2e/artifacts/browser_success.png`, `runs/browser_e2e/artifacts/health.json`, replay export artifacts | Proves fixture UI loop, visible denial/undo/feedback/replay, and restart persistence. |
| Release dogfood gate | Partial | `runs/release/dogfood_release_report.json` with `"ok": true` | Covered tests, browser E2E, mac app build/sanity, Swift IPC app sanity, LaunchServices smoke, occupied-port launch, artifact validation, and secret scans. It is not current-diff evidence for the latest undo/client reconciliation patch; rerun before release. EventKit mutating probe was intentionally skipped. |
| Live Codex calendar-planning path | Complete | `runs/live_codex_e2e/artifacts/live_plan_state.json` | Shows `runtime_mode=live_codex`, `planner_backend=live_codex_app_server`, `model_reached=true`, live response/thread/turn IDs, five planned tool calls, six candidate cards, and replay evidence. |
| Auto assistant launch default | Complete | `runs/auto_fresh_ui_2_artifacts/hello_metadata.json` | Fresh no-env app launch used `runtime_mode=auto`, `planner_backend=live_codex_app_server`, `kernel_backend=SwiftKernelIPCClient`, `model_reached=true`, and `live_blockers=[]`. |
| Smalltalk through live Codex without pressing `Live Codex` | Complete | `runs/auto_fresh_ui_2_artifacts/hello_metadata.json` | First `hello` returned `Codex answered` with live response/thread/turn metadata. |
| Optional auto-mode fallback reporting | Complete | `runs/auto_fresh_ui_2_artifacts/hello_metadata.json` | Heuristic DiffusionGemma and deterministic provider local modes are `setup_notes`, not `live_blockers`; the assistant did not describe them as broken endpoints. |
| Mac app bundle launch and health contract | Complete | `runs/release/dogfood_release_report.json`, `runs/auto_fresh_ui_2/launch_state.json`, `runs/manual_auto_computer_use_final_artifacts/state_after_ui_conversation_undo.json` | App launches from the bundle, serves `/api/health`, reports launch/run/session IDs, and the runtime report matches the visible UI in auto mode. |
| macOS plan/commit/undo slice | Complete | `runs/manual_auto_computer_use_final_artifacts/state_after_ui_conversation_undo.json` | Fresh packaged app on `127.0.0.1:8806`: Computer Use sent `Make next week less chaotic`, committed the top candidate, then sent `undo the last change` through the composer. The final turn reached live Codex and produced a Swift/provider rollback receipt. |
| Manual macOS conversational dogfood suite | Complete for default `auto` runtime | `runs/manual_auto_remaining_tools_artifacts/`, `runs/manual_auto_remaining_tools_postfix_artifacts/` | Computer Use exercised the packaged app through plan, commit, feedback, replay query, profile proposal/apply, self-play, denial creation/explanation, replay export, New Chat/session switching, and restart/idempotency. Credentialed NIM, EventKit, and production all-live remain separate blocked tracks. |
| Live composer undo through Codex/Swift/provider rollback | Complete | `runs/manual_auto_computer_use_final_artifacts/state_after_ui_commit.json`, `runs/manual_auto_computer_use_final_artifacts/state_after_ui_conversation_undo.json` | Final metadata shows `response_source=live_codex_conversation`, `model_reached=true`, `tool_sequence=['request_undo']`, live response/thread/turn IDs, `status=reverted`, `sync_status=reverted`, and `rollback_verified=true`. The action queue shows `Reverted calendar change` and suppresses the stale committed row. |
| Composer operational tools | Complete for default `auto` runtime | `runs/manual_auto_remaining_tools_artifacts/state_after_replay_query.json`, `state_after_profile_apply.json`, `state_after_self_play.json`, `runs/manual_auto_remaining_tools_postfix_artifacts/state_after_denial_explain_postfix.json`, `state_after_ui_session_switch_back.json` | Replay query, profile repair proposal/apply, self-play, denial explanation, feedback, replay export, undo, and session switching are proven through the composer/UI against live Codex + Swift IPC with local DiffusionGemma/provider setup notes. The earlier `state_after_denial_explain.json` artifact was pre-fix and is superseded. |
| Frontend state reconciliation after acting | Complete | `runs/manual_auto_computer_use_final_artifacts/state_after_ui_conversation_undo.json` and Computer Use transcript | Static assets are now served no-store, the composer polls persisted assistant state while POSTs are pending, and the viewport-bound layout keeps the composer reachable after long transcripts. |
| Swift authority boundary | Partial | Swift IPC tests, release gate, browser E2E denial/undo artifacts | Swift IPC grant/undo behavior is tested; provider-backed materialization and higher-tier product-policy paths still need end-to-end dogfood. |
| Swift stable identifier hardening | Complete for Swift IPC/local provider | `runs/manual_auto_remaining_tools_postfix_artifacts/state_after_controlled_denial.json`, `state_after_restart.json`, tests `test_receipt_id_distinguishes_authority_outcomes` and `test_commit_receipt_id_distinguishes_authority_outcomes` | Same-candidate committed and denied outcomes now produce distinct deterministic receipt IDs. Restart restored the same session with replay count 23, provider event count 4, idempotency key count 1, and no restore error. External provider IDs still require EventKit dogfood. |
| Mac process lifecycle cleanup | Complete for packaged app | `runs/manual_auto_remaining_tools_postfix_artifacts/shutdown_after_supervisor_tree_kill.json` | `SIGINT`/`SIGTERM` now synchronously stop the Python child process, recursively kill descendants if needed, free port 8808, and leave no run-dir or kernel processes behind. |
| Credentialed NIM DiffusionGemma generation | Complete | `runs/live_diffusiongemma_e2e/artifacts/nim_policy_preflight.json`, `runs/live_diffusiongemma_e2e/artifacts/live_policy_state.json`, `runs/manual_auto_eventkit_ui_current/artifacts/state_after_stageable_live_eventkit_plan.json` | The old `.env` key was transferred into the active repo-local `.env` without committing it. The app now loads parent `.env` files from packaged resources, NIM health is configured from `NVIDIA_API_KEY`, and live NIM generated typed frontier candidates used by the macOS composer plan. Current UI artifact shows `nvidia_nim_diffusiongemma_policy`, NIM `response_id`, and three generated candidate futures. |
| Apple EventKit/provider materialization | Complete for reversible synthetic probes; staged in UI | `runs/eventkit_e2e/eventkit_materialization.json`, `runs/eventkit_tier_policy_e2e/tier_policy_materialization.json`, `runs/eventkit_no_window_storm/no_window_storm_probe.json`, `runs/manual_auto_eventkit_ui_current/artifacts/state_after_stageable_live_eventkit_plan.json` | EventKit reported `full_access`, created real provider events, returned external IDs/idempotency keys/rollback handles, and verified rollback. Probes are synthetic and immediately rolled back. Current macOS UI path staged a live EventKit-backed candidate and stopped at user-confirmation boundary before actual provider commit. The bridge-path window-storm regression is covered by a non-mutating repeated status/read probe. |
| Production all-live runtime | Complete for preflight and planning | `runs/production_preflight_after_nim_eventkit/health.json`, `runs/production_preflight_current/health.json`, `runs/manual_auto_eventkit_ui_current/artifacts/health_after_stageable_live_eventkit_plan.json` | Strict `production` now reports live Codex, NIM DiffusionGemma, Swift IPC, Apple EventKit, provider observation loaded, and no blockers. The macOS `auto` launch also showed all four active backends and no setup notes. |
| Tier 5/Tier 6 product policy | Complete for synthetic provider probes; Partial for real social invites | `runs/eventkit_tier_policy_e2e/tier_policy_materialization.json` | Tier 5 moved an EventKit event under `commit_social`/`move_people_meeting` authority and rolled back. Tier 6 expanded `auto_apply_plan` into two provider writes and rolled both back. This did not send real attendee invitations, so true social-send UX remains open. |
| Canonical action envelope | Complete for Codex/Swift/provider act receipts | `runs/eventkit_e2e/eventkit_materialization.json`, `runs/macos_nim_eventkit_ui_final_readyroot/state_after_composer_message.json`, `tests/test_frontend_server_api.py` | Commit/undo receipts now include `calendar_action_envelope.v1` with trace, tool, candidate, authority grant, action digest, Swift receipt, provider receipt, external IDs, rollback handle, and provider transaction fields. |
| Full production self-play | Partial | `runs/production_self_play_nim_eventkit_retry/state_after_self_play.json`, `runs/production_self_play_nim_eventkit_retry/replay_export.json` | Production self-play now succeeds with live NIM and Swift IPC while EventKit is configured. The self-play runner still materializes through the kernel path only; it does not yet invoke EventKit provider commits inside each episode. |
| Replay -> offline tuning -> next NIM generation | Complete | `runs/replay_offline_tuning_loop/artifacts/diff_summary.json`, `runs/replay_offline_tuning_loop/artifacts/{self_play_metrics,offline_policy_report,frontier_untuned,frontier_tuned}.json`, `runs/replay_offline_tuning_loop/{replay.jsonl,policy_tuning.json}` | Closed a real code gap, not just a missing pass: `PolicyTuning` was previously wired only into the deterministic `DiffusionGemmaPolicy` and had zero runtime entry point anywhere (no CLI flag, no live-policy support). Extracted the tuning math into a shared `apply_policy_tuning()` (`src/calendar_pilot/diffusiongemma/policy.py`) and threaded it into `LiveDiffusionGemmaPolicy` (`src/calendar_pilot/diffusiongemma/live.py`) with a re-sort after tuning. New script `scripts/run_replay_offline_tuning_loop.py` (`make replay-offline-tuning-loop`) runs live-NIM self-play, reduces the replay with the existing `train_offline_policy.py` reducer, regenerates a live NIM frontier with the derived `PolicyTuning`, and proves the leading candidate changed (`cand_001` -> `cand_protect_deep_work_003`). Two new unit tests cover reward-bias and denied-intent reordering on the NIM frontier path. |

### Not Yet Dogfooded End To End

1. **Self-play through provider materialization:** Production self-play now uses live NIM and Swift IPC under an EventKit-configured runtime, but `SelfPlayRunner.run_episode` calls `kernel.authorize_and_materialize` directly (`src/calendar_pilot/diffusiongemma/self_play.py:229`), bypassing the provider-adapter commit path that only `CodexToolRuntime.execute(REQUEST_COMMIT)` has. Making self-play provider-aware is a safety-relevant default change (self-play defaults to 10 episodes and would start mutating real Calendar state each run unless explicitly gated), not just a wiring task — needs an explicit opt-in design before implementation.
2. **True social-send UX:** Tier 5 authority was proven with a synthetic move and no attendee invitations. A real people-affecting calendar update still needs explicit UX, confirmation, provider behavior, and rollback dogfood before it should be considered complete. Implementing this means the app can contact real third parties (attendee invitations) — treat as a scoped product/safety decision, not a routine dogfood task.
3. **Production UI commit/undo with live EventKit:** Provider writes are proven by scripts and the macOS UI planning path is proven with all live backends. Current UI artifact has a stageable Swift packet for a private focus block on July 7, 2026 09:00-11:00 UTC, but the actual `Commit with Swift` click is intentionally paused for action-time confirmation because it will write a real Apple Calendar event.
4. **Restart/idempotency with live EventKit:** EventKit rollback/idempotency is tested in-process, including the fixed post-rollback idempotency bug, but a packaged app restart with live EventKit undo ledger restoration still needs a dedicated artifact after the visible UI commit/undo path completes.
5. **Provider OAuth beyond EventKit:** Apple EventKit OS permission is configured. Google/Microsoft OAuth-style provider adapters remain outside this dogfood pass.

### Current Live UI Findings: July 2, 2026

Runtime under test: packaged macOS app launched directly from `dist/CalendarPilot.app/Contents/MacOS/CalendarPilot` on `127.0.0.1:8822`, `runtime_mode=auto`, live Codex from auth cache, credentialed NIM DiffusionGemma, Swift IPC, Apple EventKit `full_access`.

Confirmed in this pass:

- Live Codex quota had reset by 12:44 PM PDT. Health showed `live_codex_app_server`, `nvidia_nim_diffusiongemma_policy`, `SwiftKernelIPCClient`, `apple_eventkit`, and `live_blockers=[]`.
- `runs/production_preflight_current/health.json` shows strict production preflight with all four live backends and no blockers.
- `runs/eventkit_e2e/eventkit_materialization.json` was regenerated after the bridge fix and proves EventKit create -> external ID/idempotency key/rollback handle -> verified rollback.
- `runs/manual_auto_eventkit_ui_current/artifacts/state_after_stageable_live_eventkit_plan.json` proves the macOS composer sent a calendar goal through live Codex, live NIM generated a typed frontier, Codex compared and simulated candidates, Swift staged a `stageable` packet, and the action queue requires confirmation before provider commit.
- The first UI prompt correctly reached live Codex/NIM/EventKit but Swift denied the proposed July 3 focus block with `conflict_detected_before_stage` because EventKit had an all-day holiday-style event on that day. This is useful denial evidence, but the product still needs a decision on whether all-day holidays should block intra-day focus blocks.
- The second UI prompt exposed a real macOS runtime bug: NIM frontier normalization used `isinstance(value, int | float)`, which fails under the app-bundled Python 3.9 with `unsupported operand type(s) for |: 'type' and 'type'`. Fixed by switching runtime checks to tuple form and verified the numeric-right-moment parser regression under the Xcode Python 3.9 interpreter.
- The same second prompt also exposed a UX bug: failed live Codex plans were titled `I found a plan`. The session now titles validation failures as `Codex plan unavailable` and carries `plan_failed`, `plan_failure_tool`, `plan_failure_category`, and recovery metadata.
- A bridge-path regression could explain the window storm: when the EventKit bridge executable path pointed inside `CalendarPilot.app`, provider code identified the parent `CalendarPilot.app` as the bridge app and launched it with `open -W -n`. That could repeatedly open the main CalendarPilot app. Fixed by canonicalizing bare bridge paths to the sibling `CalendarPilotEventKitBridge.app` executable and only treating `CalendarPilotEventKitBridge.app` as app-bridge launchable.
- No-window-storm proof: `runs/eventkit_no_window_storm/no_window_storm_probe.json` deliberately used the formerly dangerous bare bridge path for repeated EventKit status/read calls. It recorded `app_bundle_for_bare=null`, canonical bridge app path under `CalendarPilotEventKitBridge.app`, and `no_main_app_spawned=true`.

### Current Next Steps

1. With action-time confirmation, click the visible `Commit with Swift` control for the staged July 7 focus block, verify EventKit external IDs/provider transaction fields, then undo through the composer and verify provider rollback.
2. Restart the packaged app against the same run directory and prove live EventKit rollback handles, idempotency records, provider snapshots, replay records, and session state restore without duplication.
3. Run a fresh failed-plan UI case to prove the new `Codex plan unavailable` title in persisted artifacts; the current saved run still contains an older pre-fix failed turn titled `I found a plan`.
4. Decide and scope the self-play provider-materialization opt-in (default-off flag, episode cap, and rollback-per-episode guarantee) before implementing it.
5. Define the real social-send UX for Tier 5 before sending attendee-affecting updates; keep current Tier 5 evidence scoped to synthetic no-invite movement.
6. Split quota/rate-limit failures from `model_tool_schema_failure` so account exhaustion does not read as a malformed-model-plan defect.

### GPT-5.5 XHigh Review: July 2, 2026

The reviewer read `docs/`, this working document, the current-pass changed files, and the latest artifacts. Confirmed:

- The EventKit window-storm fix is plausible and guarded: bare bridge paths inside `CalendarPilot.app` canonicalize to `CalendarPilotEventKitBridge.app`, and only that bridge app is launchable by the provider adapter.
- The Python 3.9 NIM normalization issue is fixed in source and packaged `dist`; the existing numeric `right_moment_decision` parser test covers the failing branch.
- Failed-plan labeling is fixed in code/tests, but the current saved UI artifact still contains one pre-fix historical turn titled `I found a plan`.
- The macOS UI path reached live Codex, live NIM, Swift IPC, and EventKit, then stopped correctly at a `stageable`/`requires_confirmation=true` boundary before a real provider write.
- Synthetic EventKit E2E did commit and undo a real provider event, and production preflight is healthy.

Accepted follow-up from the review:

- Production health was confusing because `fixture_paths.uses_sample_fixtures` stayed `true` after EventKit supplied `obs_apple_eventkit`. Fixed in `DogfoodSessionState.runtime_report()` so provider-loaded observations report `uses_sample_fixtures=false`, with coverage in `tests/test_apple_eventkit_provider.py`.
- Added `runs/eventkit_no_window_storm/no_window_storm_probe.json` to prove repeated non-mutating EventKit bridge calls do not spawn the main `CalendarPilot.app`.

### Latest Live Integration Pass: July 2, 2026

Runtime under test: packaged macOS app, `runtime_mode=auto`, live Codex from auth cache, credentialed NIM DiffusionGemma, Swift IPC, Apple EventKit with `full_access`.

Confirmed complete in this pass:

- `.env` transfer: copied the old `NVIDIA_API_KEY` into the active repo-local `.env` without committing the secret. `calendar_pilot.env.load_local_env()` now searches parent directories so packaged resources can discover the repo-root `.env`.
- Credentialed NIM: `runs/live_diffusiongemma_e2e/artifacts/nim_policy_preflight.json` and `live_policy_state.json` prove `nvidia_nim_diffusiongemma_policy` is configured and generated typed candidate frontiers. NIM parser normalization now handles common model schema drift and skips invalid candidates when valid typed candidates remain.
- macOS UI pipeline: Computer Use opened the packaged app on `127.0.0.1:8814`, set the composer to `make tomorrow less chaotic`, and clicked Send. `runs/macos_nim_eventkit_ui_final_readyroot/state_after_composer_message.json` shows `response_source=planner`, `model_reached=true`, live Codex response/thread/turn IDs, `policy_backend=nvidia_nim_diffusiongemma_policy`, `provider_backend=apple_eventkit`, no live blockers, five tool calls, three candidate cards, and one staged Swift receipt.
- macOS startup UX: the app no longer hard-loads a blank WKWebView after a fixed delay. `CalendarPilotMacApp` waits for the static root server to bind, keeps polling if the backend is slow, and then loads the app. This avoids the stale `about:blank` / “still starting” dead end seen during live startup.
- Production preflight: `runs/production_preflight_after_nim_eventkit/health.json` shows strict `production` mode with live Codex, NIM remote health `ok`, Swift IPC, Apple EventKit configured, provider observation loaded, and `live_blockers=[]`.
- EventKit materialization: `runs/eventkit_e2e/eventkit_materialization.json` created a real EventKit focus block, returned an external event ID, provider transaction/idempotency key, Swift rollback handle, and verified rollback.
- Tier 5/Tier 6 provider policy: `runs/eventkit_tier_policy_e2e/tier_policy_materialization.json` proves Tier 5 scoped social move and Tier 6 `auto_apply_plan` provider materialization with rollback verification. The Tier 6 provider adapter now expands nested `plan_actions` before calling EventKit.
- EventKit idempotency fix: rolled-back EventKit idempotency records no longer return stale external IDs on later replay; post-rollback replays rematerialize instead of pointing at deleted provider events.
- Production self-play: `runs/production_self_play_nim_eventkit_retry/state_after_self_play.json` shows live NIM + Swift IPC production self-play succeeded with `release_decision=hold_autonomy`. The NIM frontier limit is now bounded by `CALENDAR_PILOT_NIM_FRONTIER_LIMIT` defaulting to 4 and `CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS` defaulting to 4200 to reduce malformed/truncated JSON.
- Canonical envelope: provider-backed commit artifacts include `calendar_action_envelope.v1` with trace/tool/candidate/grant/action digest/Swift/provider/external ID/rollback fields.

### Latest Dogfood Pass: July 2, 2026

Runtime under test: packaged macOS app, `runtime_mode=auto`, live Codex from auth cache, Swift IPC, heuristic DiffusionGemma setup note, deterministic provider setup note.

Confirmed complete in this pass:

- Plan path: Computer Use sent `Make next week less chaotic`; `state_after_plan.json` shows `response_source=planner`, `model_reached=true`, live Codex metadata, tool sequence `inspect_week -> generate_candidate_frontier -> compare_candidates -> simulate_action_program -> stage_action_packet`, six candidate cards, and 17 replay records.
- Commit path: `state_after_commit.json` shows `request_commit`, `status=committed`, `sync_status=materialized`, Swift receipt `rcpt_d51e0fedb73c6f32`, rollback handle `undo_4a5448c4e915aa3b`, provider event count 4, and one idempotency key.
- Feedback path: `state_after_feedback.json` records `response_source=ui_feedback`, receipt feedback `useful`, and a reward event attached to replay.
- Replay query: `state_after_replay_query.json` shows live Codex conversation metadata with `tool_sequence=["query_replay_trace"]`.
- Profile repair: `state_after_profile_propose.json` produced a confirmation-required patch, and `state_after_profile_apply.json` applied the confirmed patch through `apply_profile_patch`.
- Self-play: `state_after_self_play.json` ran two self-play episodes, recorded failure mode `notification_fatigue`, and produced replay episode/adversary records.
- Denial path: `state_after_controlled_denial.json` proves same-candidate denied commit receipt `rcpt_acbe709c0aed5823` differs from prior committed receipt `rcpt_d51e0fedb73c6f32`; visible action cards now carry `required authority tier exceeds Swift-issued grant`.
- Denial explanation: `runs/manual_auto_remaining_tools_postfix_artifacts/state_after_denial_explain_postfix.json` and regression tests verify Codex placeholders like `latest denial in current session` are replaced with the latest real Swift denial reason before tool execution. The latest assistant metadata shows `response_source=live_codex_conversation`, `model_reached=true`, and `tool_sequence=["explain_swift_denial"]`; the explanation uses `required authority tier exceeds Swift-issued grant` instead of a placeholder.
- Replay export: `replay_export_with_active_plan.json` contains 23 records, runtime metadata, active plan `plan_a71c18f2fded`, live Codex `response_id`, and trace tools through both commit attempts.
- Restart/idempotency: `state_after_restart.json` confirms same session after relaunch, 23 records before/after, provider events 4 before/after, idempotency keys 1 before/after, no restore error, and requested port 8808 retained.
- Session switching: `state_after_new_chat.json` confirms New Chat creates a clean 0-record session; `state_after_ui_session_switch_back.json` confirms the UI switches back to the 23-record run with candidate cards and stageable/committed/denied action queue restored.
- Mac supervisor cleanup: `shutdown_after_supervisor_tree_kill.json` proves Ctrl-C of the packaged app handles `SIGINT`, synchronously stops the Python child, frees port 8808, and leaves no run-dir or kernel process behind.
- Runtime robustness: `runtime_report` now falls back to `CALENDAR_PILOT_APP_ROOT` if `os.getcwd()` fails because a packaged app resource directory was replaced during rebuild-heavy dogfooding.
- GPT-5.5 xhigh subagent review: the reviewer read `docs/`, this document, and the artifacts, confirmed the plan/commit/feedback/replay/profile/self-play/replay export/restart/session-switching evidence, and flagged two missing closure artifacts. Those are now closed by `state_after_denial_explain_postfix.json` and `shutdown_after_supervisor_tree_kill.json`.

Validation after fixes:

- `python3 -m pytest -q`: `116 passed, 9 skipped`
- `swift build --package-path packages/CalendarPilotKernel --product CalendarPilotMacApp`: passed
- `scripts/build_macos_app.sh`: passed
- `node --check frontend/static/app.js`: passed
- `git diff --check`: passed

### Architecture Direction To Preserve

Hardening means making the acting substrate deterministic enough for agency, not keeping the model passive. The intended product split is:

```text
DiffusionGemma/NIM generates typed candidate frontiers.
Codex inspects, compares, repairs, and converts choices into typed tool operations.
Swift owns calendar reality, authority grants, provider writes, rollback, and audit.
Replay/training converts receipts, rewards, and adversary findings into future policy behavior.
```

The ordered build path remains:

```text
Swift/macOS session substrate
-> one app/session/kernel entry point
-> runtime/session registry truth
-> provider-backed materialization
-> model-generated candidate frontier
-> Codex tool loop
-> self-play/replay/training loop
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
- Verified earlier: full Python suite passed after the composer-tool and session fixes; targeted live/session/server tests, `make swift-test`, `make swift-ipc-test`, `py_compile` for the touched Python modules, `node --check frontend/static/app.js`, `node --check scripts/browser_cdp_e2e.mjs`, `git diff --check`, and `make browser-e2e` passed. The browser e2e now includes New Chat, rename, archive, and switch-back checks. See the latest dogfood pass above for the current uncommitted diff verification count.
- Earlier baseline: `make dogfood-release` passed and wrote `runs/release/dogfood_release_report.json`; it covered Python tests, Swift tests, Swift IPC tests, browser e2e, mac app build, mac app sanity, Swift IPC app sanity, LaunchServices smoke, occupied-port launch, artifact validation, and secret scans. The live EventKit mutating release probe remained intentionally opt-in/skipped. This report predates the latest undo/client reconciliation patch and must be rerun before release.
- Verified in this pass: `make live-codex-e2e` passed with `runs/live_codex_e2e/artifacts/live_plan_state.json` showing `runtime_mode=live_codex`, `planner_backend=live_codex_app_server`, `model_reached=true`, live `response_id`, `thread_id`, `turn_id`, six candidate cards, and replay evidence.
- Verified with Computer Use and API state: rebuilt macOS app launched in `live_codex` mode on `127.0.0.1:8791`; prompt `hello metadata check` persisted in `runs/one-access-ui-test-final/latest_session.json` with `title=Codex answered`, `response_source=live_codex_conversation`, `model_reached=true`, `planner_backend=live_codex_app_server`, `kernel_backend=SwiftKernelIPCClient`, and live `response_id`, `thread_id`, and `turn_id`.
- Historical diagnosis with Computer Use and subagent review: the earlier CalendarPilot conversation required pressing `Live Codex` because that launch defaulted to fixture. The transcript confirmed early `hello` and `what ru` turns were local fixture responses, then the runtime changed to `live_codex` and later turns reached the Codex app-server path. That was a default-runtime and runtime-history UX gap, not evidence that the live Codex endpoint was unreachable after the switch.
- Done in this pass: implemented `auto` as the macOS/Finder/Python launch default. It routes conversational turns to live Codex when Codex auth is present, uses Swift IPC when bundled, keeps heuristic DiffusionGemma and deterministic provider adapters as optional local modes, and exposes those local modes through `setup_notes` rather than `live_blockers`.
- Fixed in this pass: the bad `DiffusionGemma is using heuristic... because diffusiongemma_nim is missing` style answer came from our own runtime context. `auto` had marked optional NIM/provider credentials as required blockers, `_conversation_prompt()` told Codex to be explicit about active backends, and `_conversation_runtime_context()` exposed absent optional credentials. Smalltalk now hides optional credential/setup diagnostics; metadata questions still show them, but as setup notes and not endpoint failures.
- Verified with Computer Use and API metadata: rebuilt macOS app launched with no runtime env on `127.0.0.1:8798`; prompt `hello` returned `Codex answered` with body `Hello. How can I help?`, `response_source=live_codex_conversation`, `model_reached=true`, live response/thread/turn IDs, `runtime_mode=auto`, `planner_backend=live_codex_app_server`, `kernel_backend=SwiftKernelIPCClient`, and `live_blockers=[]`. The only fallback evidence was `setup_notes` for local heuristic DiffusionGemma and deterministic provider mode.
- Done in this pass: successful `request_undo` receipts now use `status=reverted` across the Python enum, JSON schema, Swift Codable contract, Swift bridge, frontend card normalization, and tests. Undo metadata now includes Swift receipt ID, sync status, provider rollback status, rollback handle, and rollback verification.
- Done in this pass: composer-executed operational tool receipts that materialize or revert calendar state are appended to the latest plan, so the action queue reflects the true Swift/provider state instead of retaining stale committed rows after undo.
- Done in this pass: frontend state reconciliation was hardened. `/api` and static frontend assets are served no-store, the composer polls persisted assistant turns while a long POST is pending, and the app shell is viewport-bound so the composer remains reachable after long transcripts.
- Verified with Computer Use and API metadata: rebuilt packaged app launched on `127.0.0.1:8806`; Computer Use sent `Make next week less chaotic`, committed the top candidate, then sent `undo the last change` through the composer. Final artifact `runs/manual_auto_computer_use_final_artifacts/state_after_ui_conversation_undo.json` shows `response_source=live_codex_conversation`, `model_reached=true`, live response/thread/turn IDs, `tool_sequence=['request_undo']`, `status=reverted`, `sync_status=reverted`, `provider_rollback_status=rollback_verified`, and `rollback_verified=true`. The visible UI showed `Undo completed` and `Reverted calendar change`.
- Done after GPT-5.5 xhigh review: failed provider rollback projection no longer hides the original committed action. The action queue now suppresses a committed row only after a verified rollback, renders failed rollback receipts as `Rollback needs review`, and includes a regression for an unverified provider rollback.
- Current local verification after the review fix: `tests/test_frontend_session_persistence.py` passed with 23 tests; full `python3 -m pytest -q` passed with `116 passed, 9 skipped`; `node --check frontend/static/app.js`, `git diff --check`, `scripts/build_macos_app.sh`, and `swift build --package-path packages/CalendarPilotKernel --product CalendarPilotMacApp` passed.
- Current production preflight evidence: `runs/production_preflight_after_nim_eventkit/health.json` shows `production` composing `live_codex_app_server`, `nvidia_nim_diffusiongemma_policy`, `SwiftKernelIPCClient`, and `apple_eventkit` with Codex auth configured, NIM remote health `ok`, EventKit `full_access`, provider observation loaded, and `live_blockers=[]`.
- Current live-provider evidence: `runs/eventkit_e2e/eventkit_materialization.json` and `runs/eventkit_tier_policy_e2e/tier_policy_materialization.json` prove EventKit create/move/compound writes, external IDs, rollback handles, and verified rollback. Apple EventKit OS permission is covered; Google/Microsoft OAuth-style providers are not.
- Remaining P0: packaged-app UI commit/undo against live EventKit and restart/idempotency restoration for live EventKit still need dedicated artifacts.
- Remaining P1: keep expanding restore and mixed-history coverage so clean launches, prior-fixture restores, prior-live restores, and New Chat all preserve the assistant-ready runtime and make historical fixture messages understandable.
- Remaining P2: label historical message runtime in the UI/state summary so a restored Live Codex session with earlier fixture turns is understandable.

### Current Conversation Diagnosis And Next Steps

- UI evidence: Computer Use showed the current app running from `calendar-pilot-updated 2/dist/CalendarPilot.app` with the chip in `Live Codex mode`, but the transcript itself began with fixture/local assistant messages. The `hello` and `what ru` turns were titled `Conversation handled locally`; only after the runtime-change message did `what r u` produce `Codex answered` with live Codex metadata.
- Resolved root cause: the old macOS and Python launch defaults started from fixture. The current default is `auto`, which routes the first conversational turn to live Codex when auth is present, uses Swift IPC when bundled, and reports local DiffusionGemma/provider adapters as setup notes rather than endpoint failures.
- Subagent review: the reviewer agreed this is not a live Codex endpoint outage after the switch. It is a startup runtime and product-routing gap. `production` is too credential-gated for the default, while `live_codex` is too narrow because DiffusionGemma/provider readiness remains implicit.
- Current bad-output diagnosis: the assistant did not independently discover that DiffusionGemma or provider endpoints were broken. CalendarPilot supplied a runtime report that mislabeled optional auto-mode local adapters as missing required credentials, then instructed Codex to be explicit about active backends. Codex repeated that diagnostic context in a normal chat answer.
- Remaining implementation deliverables: provider-aware self-play materialization, packaged-app live EventKit commit/undo, restart/idempotency restoration for live EventKit, fresh failed-plan UI evidence for the new title, no-window-storm evidence, and true social-send UX for attendee-affecting updates. Replay reduction into `PolicyTuning` followed by a subsequent NIM generation pass is now complete. The canonical action envelope now exists for act receipts, but replay/export/UI consumers should continue converging on it as the single lifecycle representation.

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
