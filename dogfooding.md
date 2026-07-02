# CalendarPilot Dogfood Working Document

Updated: 2026-07-02

This is the root working document for CalendarPilot dogfooding. It replaces the
old root dogfood ledger and treats `calendar-pilot-system-framework/` as the
active app. `Do-not-reference/` is historical context only; do not run product
dogfood from it unless the task is explicitly comparative archaeology.

## Goal

CalendarPilot is being tested as one closed learning and acting loop:

```text
raw calendar observation
-> DiffusionGemma/NIM candidate frontier
-> Codex tool deliberation
-> Swift authority, stage, commit, denial, or undo
-> feedback and adversary findings
-> replay export
-> offline policy tuning
-> next run
```

The system has moved past "is the stack wired?" into "is the evidence path
trustworthy?" The current framework is not fully implemented. The first
implementation slice landed evidence integrity, canonical learning keys, replay
visibility, and object-substrate seams. The full ActionLifecycle, Glass Cockpit
frontend, provider-backed self-play, contract vectors, and EventKit sandboxing
are still dogfood targets.

## Source Of Truth

- Active repo snapshot: `calendar-pilot-system-framework/`
- Target framework: `calendar-pilot-system-framework/SYSTEM_FRAMEWORK.md`
- Current implementation pass: `calendar-pilot-system-framework/docs/SYSTEM_FRAMEWORK_IMPLEMENTATION_PASS.md`
- Current validation record: `calendar-pilot-system-framework/VALIDATION.md`
- Historical previous snapshot: `Do-not-reference/calendar-pilot-updated 2/`

The active tree was generated from the previous `calendar-pilot-updated 2`
snapshot plus `SYSTEM_FRAMEWORK.md`. The old root `calendar-pilot-updated 2/`
tree has been removed from the active root and preserved under
`Do-not-reference/`.

## Current Local Validation

These checks were rerun from `calendar-pilot-system-framework/` on 2026-07-02:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python3 scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl
PYTHONPATH=src python3 -m calendar_pilot.app frontend --write-snapshot --out /tmp/calendarpilot_ci_evidence/frontend_state.json
PYTHONPATH=src python3 scripts/run_secret_scan.py --path /tmp/calendarpilot_ci_evidence
```

Result:

```text
Python: 140 tests OK, 9 skipped
Swift: 17 tests OK
Golden replay invariant check: OK
Evidence snapshot secret scan: OK
```

Not rerun in this pass: browser E2E, Finder/macOS packaged launch, live Codex,
live NIM, and live EventKit mutation.

## Access Points

Run these from repo root unless noted. The root `Makefile` delegates into the
active framework tree.

```bash
make py-test
make swift-test
make check-invariants
make evidence-bundle
make test
```

Browser and app dogfood:

```bash
make browser-e2e
make mac-app-build
make dogfood-release
```

Live and learning-loop dogfood:

```bash
make live-codex-e2e
make live-diffusiongemma-e2e
make live-eventkit-e2e
make replay-offline-tuning-loop
```

Manual local server:

```bash
cd calendar-pilot-system-framework
PYTHONPATH=src python3 -m calendar_pilot.app frontend \
  --serve \
  --host 127.0.0.1 \
  --port 8787 \
  --run-dir runs/dogfood/manual
```

Key HTTP endpoints while the server is running:

```text
GET  /api/health
GET  /api/state              legacy UI snapshot
GET  /api/view               view_state.v2 checkpoint
GET  /api/events             Server-Sent Events trace stream
GET  /api/trace/{trace_id}   causal replay chain plus action envelope
POST /api/plans
POST /api/candidates/{id}/simulate
POST /api/candidates/{id}/stage
POST /api/candidates/{id}/commit
POST /api/undo
POST /api/self-play
POST /api/feedback
POST /api/runtime
```

## Working Status Ledger

Status legend:

- `Complete`: current code path has a passing test or current artifact.
- `Partial`: useful path exists, but intended product path is not end to end.
- `Open`: target framework work is not implemented or not dogfooded.
- `Blocked`: requires credentials, OS permission, or product-safety decision.

| Area | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Active repo selection | Complete | Root `Makefile` delegates to `calendar-pilot-system-framework/` | `Do-not-reference/` remains excluded from active dogfood and commit scope. |
| Python/Swift unit contract gates | Complete | 140 Python tests, 9 skipped; 17 Swift tests | Current local validation passed. |
| Evidence snapshot and secret scan | Complete | `frontend --write-snapshot`; `run_secret_scan.py` | Validates generated evidence can be archived without obvious secrets. |
| Active `runs/dogfood/` evidence | Complete for fixture/local path only | Current generated session/replay files under `calendar-pilot-system-framework/runs/dogfood/` | Proves deterministic planner, heuristic policy, stub/local provider path, replay rows, and action-envelope emission; does not prove live Codex/NIM/EventKit. |
| Historical live evidence | Useful migration evidence, not current proof | `Do-not-reference/calendar-pilot-updated 2/runs/` | Prior snapshot includes live Codex, NIM, EventKit, production preflight, and replay/offline-tuning artifacts. Rerun in the active tree before treating as current evidence. |
| Session lock and state version | Complete for current server object | `DogfoodSessionState` wraps public methods with `RLock` and emits `state_version` | This is a protective shell around the existing god object, not full decomposition. |
| Atomic state writes and append-capable replay | Complete for current persistence path | `environment/fsio.py`, `ReplayBuffer.set_jsonl_path()` | `persist()` still compacts/re-saves replay for compatibility. |
| Router decisions in replay | Partial | `router_decision` records append on turns | Live model-router schema is still pending; live modes currently fall back to keyword routing. |
| Canonical intent taxonomy | Complete for parser/reducer code | `environment/taxonomy.py`, `train_offline_policy.py` | Needs repeated dogfood to prove residuals accumulate rather than fragment. |
| Model-generation rejection records | Partial | `model_generation_rejection` replay path exists | Need live NIM dogfood that asserts rejected raw generations are visible in replay and Learn UI. |
| ActionEnvelope | Partial | Codex receipts carry v2-compatible envelope fields | Full `ActionLifecycle` object does not yet own prepare/simulate/stage/commit/verify/reward/undo. |
| Invariant checking | Partial | Golden replay check covers I2/I6 only | I1/I3/I4/I5 and ML/self-play invariants still need executable checks. |
| `/api/view`, `/api/events`, `/api/trace` | Partial | Endpoints exist | Need browser/SSE tests and a real frontend consumer. |
| Glass Cockpit frontend | Open | Existing static frontend still uses `app.js` and `innerHTML` | ES-module frontend, live pipeline strip, Observe/Learn/Lab/Authority surfaces are not implemented. |
| Replay -> offline tuning -> next NIM frontier | Partial for current root | Script and reducer exist; prior historical pass proved leader change | Rerun `make replay-offline-tuning-loop` in the active tree with current credentials. |
| Self-play backend policy | Partial | Backend policy enum exists | Runner still calls `kernel.authorize_and_materialize` directly. Provider-backed sandbox self-play is not implemented. |
| EventKit provider materialization | Partial | Provider code and historical synthetic probes exist | Current pass did not click live UI commit/undo against EventKit. |
| Tier 5/Tier 6 product policy | Partial | Swift tests cover product paths | Real social-send UX and compound rollback graph are still product/safety work. |
| Root CI | Open | Workflow exists under active subdir, not repo root | GitHub only runs workflows from root `.github/`; move/copy when CI is in scope. |

## Current Stop Conditions

Stop dogfood and file a P0 if any of these occur:

- A provider mutation has no action envelope or no replay-visible receipt.
- A committed or reverted provider mutation has an absent rollback state.
- A replay export cannot causally link observation, candidate, Codex receipt,
  Swift receipt, provider receipt, reward, and tuning input.
- A live provider write happens outside Swift authority or without a scoped grant.
- Live NIM/Codex fallback is silent or mislabeled as a successful live path.
- A generated evidence bundle contains secrets.

## Next Steps

### P0 - Rebaseline The Active Root

1. Run the root access-point checks:

   ```bash
   make py-test
   make swift-test
   make swift-ipc-test
   make check-invariants
   make evidence-bundle
   git diff --check
   ```

2. Run the fixture browser path:

   ```bash
   make browser-e2e
   ```

3. Build and smoke the macOS app on macOS:

   ```bash
   make mac-app-build
   ```

   No-runtime-env packaged launch probe:

   ```bash
   cd calendar-pilot-system-framework
   rm -rf runs/dogfood/auto-fresh
   CALENDAR_PILOT_OPEN_BROWSER=0 \
   CALENDAR_PILOT_RUN_DIR="$PWD/runs/dogfood/auto-fresh" \
   dist/CalendarPilot.app/Contents/MacOS/CalendarPilot
   ```

   Pass criteria: launch resolves to `auto` or another assistant-ready runtime,
   not fixture; `/api/health` and `launch_state.json` agree; with Codex auth
   configured, the first smalltalk turn reaches live Codex and records response,
   thread, and turn metadata.

4. Decide whether to move CI to the actual git root now. The active app has
   `.github/workflows/ci.yml` under `calendar-pilot-system-framework/`, but that
   is not a GitHub entry point while the repo root is `Destination/`.

### P1 - Test The New Machine Learning Architecture

The ML dogfood question is not "does a candidate appear?" It is "can replay
change the next frontier in a causally inspectable way?"

1. Canonical-intent reducer test:

   ```bash
   cd calendar-pilot-system-framework
   PYTHONPATH=src python3 scripts/train_offline_policy.py \
     --replay tests/fixtures/replay_golden.jsonl \
     --out runs/ml_taxonomy_probe/offline_policy_report.json \
     --tuning-out runs/ml_taxonomy_probe/policy_tuning.json
   ```

   Pass criteria: report includes `policy_tuning.taxonomy_health`; intent keys
   are canonical values such as `create_prep_block`, `protect_deep_work`, or
   `other`, not model prose.

2. Live NIM frontier and rejection visibility:

   ```bash
   make live-diffusiongemma-e2e
   ```

   Pass criteria: artifact shows `nvidia_nim_diffusiongemma_policy`, typed
   candidates, canonical `intent`, `intent_raw`, `intent_matched_by`, and any
   parser skips appear as `model_generation_rejection` replay rows.

3. Closed replay-tuning loop:

   ```bash
   make replay-offline-tuning-loop
   ```

   Pass criteria:

   ```text
   replay.jsonl exists
   offline_policy_report.json exists
   policy_tuning.json exists
   frontier_untuned.json exists
   frontier_tuned.json exists
   diff_summary.json shows whether leader changed and whether tuning_had_effect is true
   tuned candidates carry offline_tuning control notes
   ```

4. Learning observability gap to close:

   Add or verify a Learn-surface read model that exposes:

   ```text
   tuning_id
   frontier_diff
   bias_evidence
   taxonomy OTHER-rate
   model_generation_rejection count and reasons
   reward stream by provenance
   ```

5. Repeat over at least two sessions. One successful tuning pass proves wiring;
   two consecutive sessions with stable canonical keys prove the learning table
   is not fragmenting.

### P2 - Test The New Frontend Architecture

The frontend target is a live replay reader. The current frontend is still the
legacy static app, so testing splits into API substrate first, then UI rewrite.

1. API substrate probe:

   ```bash
   cd calendar-pilot-system-framework
   PYTHONPATH=src python3 -m calendar_pilot.app frontend \
     --serve \
     --host 127.0.0.1 \
     --port 8787 \
     --run-dir runs/frontend_substrate_probe
   ```

   In another terminal:

   ```bash
   curl -s http://127.0.0.1:8787/api/view > runs/frontend_substrate_probe/view.json
   curl -N http://127.0.0.1:8787/api/events
   ```

   Pass criteria: `/api/view` returns `view_state.v2`; event stream emits trace
   events with `seq`, `state_version`, `trace_id`, object, stage, and status.

2. Causal trace probe:

   Use the browser or API to create a plan, stage or commit a candidate, then:

   ```bash
   curl -s http://127.0.0.1:8787/api/trace/{trace_id}
   ```

   Pass criteria: records include router decision, Codex tool call/receipt,
   candidate frontier decision, envelope transition, Swift/provider receipt if
   committed, and reward after feedback.

3. Frontend rewrite F1:

   Replace `frontend/static/app.js` with zero-dependency ES modules that render
   Operate from `/api/view` and `/api/events`. Preserve existing E2E test IDs for
   candidate cards, commit, feedback, undo, and composer flow.

   Pass criteria:

   ```bash
   rg "innerHTML" calendar-pilot-system-framework/frontend/static
   make browser-e2e
   ```

   `innerHTML` must be gone from dynamic rendering code, and browser E2E must
   still pass.

4. Frontend rewrite F2:

   Add Observe and Envelope Viewer.

   Pass criteria: after a commit, a dogfooder can open one trace and see route,
   model/frontier, grant, Swift receipt, provider transaction, rollback state,
   and replay rows without reading raw JSON files.

5. Frontend rewrite F3:

   Add Learn, Lab, and Authority.

   Pass criteria:

   ```text
   Learn: frontier diff, tuning provenance, rejection count, OTHER-rate
   Lab: backend policy, self-play episodes, adversary findings, release gate
   Authority: grants, scopes, expiry, denial history, undo ledger
   ```

### P3 - Prove Live Provider Acting Without Losing Evidence

1. Run live production preflight:

   ```bash
   make live-codex-e2e
   make live-diffusiongemma-e2e
   make live-eventkit-e2e
   ```

2. Launch the packaged app with live EventKit available.

3. Create a private reversible focus block through the UI, stop at the action
   confirmation boundary, then click commit only with explicit human approval.

4. Verify:

   ```text
   provider_transaction_id or idempotency_key present
   external_event_ids present
   rollback_handle_id present
   rollback_state is verified or pending, never absent
   replay export contains envelope transition rows
   /api/trace/{trace_id} shows the full chain
   ```

5. Undo through the composer, then restart the packaged app against the same run
   directory and prove provider state, idempotency records, undo ledger, replay,
   and session state restore without duplication.

### P4 - Make Acting And Self-Play Share The Same Path

1. Extract `ActionLifecycle` from the current Codex tool runtime paths.

2. Make every mutation use:

   ```text
   prepare -> simulate -> stage -> commit -> provider_materialize -> verify -> reward -> undo -> replay
   ```

3. Expand invariant checks:

   ```text
   I1 one envelope per provider mutation
   I2 rollback state never absent
   I3 social mutation has grant scope provenance
   I4 stale observation commit refreshed or denied
   I5 every denial is training-visible
   I6 undo cannot replay twice
   M1-M5 model provenance and rejection visibility
   S1-S4 self-play parity and promotion evidence
   ```

4. Implement provider-aware self-play only behind explicit backend policy:

   ```text
   STUB_FAST
   SWIFT_IPC_DETERMINISTIC
   SWIFT_IPC_EVENTKIT_SANDBOX
   PRODUCTION_SHADOW
   ```

5. Enforce EventKit sandbox allowlisting below Python before enabling provider
   writes from self-play.

### P5 - Product Decisions Before Autonomy Promotion

These are not routine engineering cleanup:

- Define real Tier 5 social-send UX before sending attendee-affecting updates.
- Define Tier 6 compound plan graph and rollback order before treating
  `auto_apply_plan` as a product path.
- Decide how all-day holidays should affect intra-day focus-block conflict
  checks.
- Split quota/rate-limit failures from schema failures so live-account exhaustion
  does not look like malformed model output.

## Commit Hygiene

Commit active work from root while excluding `Do-not-reference/`.

Recommended staging pattern:

```bash
git add Makefile dogfooding.md calendar-pilot-system-framework
git add -u -- ':!Do-not-reference/**'
git status --short
```

Before committing, verify no ignored/generated or secret-bearing files are
staged:

```bash
git status --short --ignored
git diff --cached --name-only | rg '(^|/)(\\.env|runs|\\.build|__pycache__|\\.DS_Store)'
```

Expected: no matches from the second command.

## Dogfood Rule

Every new dogfood pass must leave behind one of:

```text
evidence artifact path
replay export path
trace id
test command and result
explicit blocked reason
```

If it cannot be replayed, inspected, or explained through the action envelope,
it is not evidence yet.
