According to documents from **July 2–3, 2026**, the right testing framework is an evidence ladder: every feature should prove not just “the code path runs,” but that it emits replay, invariants, scorecards, and UI/contract artifacts. The current ML-E2E notes already define the core ladder: unit + Swift baseline, deterministic replay, invariant report, offline tuning, frontier diff, and scorecard.  The System Framework also defines the target substrate: `ActionLifecycle`, `SessionStore`/`ReplayJournal`, `TraceBus`, `SelfPlayLab`, `FrontendProjector`, and `view_state.v2`/SSE-based Glass Cockpit surfaces. 

# Deferred-Work Test Framework

## 0. Create one run directory per validation pass

Use a clean run dir so every artifact is tied to one test pass.

```bash
export RUN_ID=deferred_pass_001
export RUN_DIR=runs/$RUN_ID
mkdir -p "$RUN_DIR"
```

For every step below, preserve:

```text
$RUN_DIR/session_state.json
$RUN_DIR/latest_session.json
$RUN_DIR/session_manifest.json
$RUN_DIR/replay.jsonl
$RUN_DIR/invariant_report.json
$RUN_DIR/frontier_diff.json
$RUN_DIR/scorecard.json
$RUN_DIR/evidence_bundle/
```

Global pass rule:

```text
No invariant violations.
No corrupted state/replay.
No provider mutation without an ActionEnvelope.
No committed action missing rollback_state.
No regression in canonical intent/taxonomy health.
No UI surface showing stale state_version after mutation.
```

The ML-E2E daily dogfood criteria use the same evidence posture: no invariant violations, no corrupted replay/state, no provider mutation without envelope, no missing rollback state, and no rising `OTHER` intent rate. 

---

## 1. Baseline repo validation

Purpose: prove the repo is healthy before testing the deferred work.

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python3 scripts/check_invariants.py \
  --replay tests/fixtures/replay_golden.jsonl \
  --out "$RUN_DIR/invariant_report_baseline.json"
```

Then run the deterministic ML ladder:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Make next week less chaotic" \
  --self-play 5 \
  --replay-out "$RUN_DIR/replay.jsonl" \
  --commit

PYTHONPATH=src python3 scripts/check_invariants.py \
  --replay "$RUN_DIR/replay.jsonl" \
  --out "$RUN_DIR/invariant_report.json"

PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay "$RUN_DIR/replay.jsonl" \
  --out "$RUN_DIR/offline_policy_report.json" \
  --tuning-out "$RUN_DIR/policy_tuning.json"

PYTHONPATH=src python3 scripts/run_frontier_diff.py \
  --tuning "$RUN_DIR/policy_tuning.json" \
  --out "$RUN_DIR/frontier_diff.json"

PYTHONPATH=src python3 scripts/make_scorecard.py \
  --run-dir "$RUN_DIR" \
  --out "$RUN_DIR/scorecard.json"
```

Pass criteria:

```text
Python tests pass.
Swift tests pass.
Golden replay invariants pass.
Deterministic replay generated.
Offline tuning generated.
Frontier diff generated.
Scorecard generated.
scorecard.decision is promote or hold, not fail.
```

This mirrors the recommended first-run ladder in ML-E2E. 

---

## 2. Test full `ActionLifecycle` extraction

Purpose: prove all machine-acting transitions now run through the lifecycle spine, not scattered Codex/session/kernel calls.

### 2.1 Static import/API test

Run or add a test that imports:

```python
from calendar_pilot.environment.action_lifecycle import ActionLifecycle
from calendar_pilot.environment.envelope import ActionEnvelope
```

Assert the lifecycle exposes:

```text
prepare
simulate
stage
commit
verify
reward
undo
```

The System Framework defines `ActionLifecycle` as the single path every calendar mutation takes, and self-play is expected to use it too. 

### 2.2 Transition-path test

Create one private reversible candidate, then exercise:

```text
prepare → simulate → stage → commit → verify → reward → undo
```

Expected envelope states:

```text
prepared
simulated
staged or stageable
committed
verified
reward_recorded
reverted
```

Required assertions:

```python
assert envelope.envelope_id
assert envelope.trace_id
assert envelope.candidate_id
assert envelope.observation_fingerprint
assert envelope.provider["rollback_state"] in {
    "verified", "pending", "failed", "impossible", "unsupported"
}
assert len(envelope.lifecycle) >= 6
```

### 2.3 Replay assertions

Inspect `$RUN_DIR/replay.jsonl`:

```bash
grep '"record_type": "envelope_transition"' "$RUN_DIR/replay.jsonl"
```

Pass criteria:

```text
Every simulate/stage/commit/verify/reward/undo transition emits envelope_transition.
Every Swift receipt reachable from an envelope has matching candidate_id.
Every committed envelope has rollback_state.
Every undo consumes one rollback handle.
No Codex commit/undo path bypasses ActionLifecycle.
```

### 2.4 API integration test

Run the frontend server:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend \
  --serve \
  --run-dir "$RUN_DIR"
```

Then issue:

```bash
curl -s -X POST http://127.0.0.1:8787/api/plans \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Create prep before my client call","commit":false}' \
  > "$RUN_DIR/api_plan.json"

CANDIDATE_ID=$(python3 - <<'PY'
import json
state=json.load(open("runs/deferred_pass_001/api_plan.json"))
print(state["chat"]["candidate_cards"][0]["candidate_id"])
PY
)

curl -s -X POST "http://127.0.0.1:8787/api/candidates/$CANDIDATE_ID/simulate" > "$RUN_DIR/api_simulate.json"
curl -s -X POST "http://127.0.0.1:8787/api/candidates/$CANDIDATE_ID/stage" > "$RUN_DIR/api_stage.json"
curl -s -X POST "http://127.0.0.1:8787/api/candidates/$CANDIDATE_ID/commit" \
  -H 'Content-Type: application/json' \
  -d '{"confirmed":true}' \
  > "$RUN_DIR/api_commit.json"
```

Pass criteria:

```text
api_commit.json contains an ActionEnvelope or envelope reference.
Replay contains envelope_transition for simulate/stage/commit.
Committed action has rollback_state.
latest_session.json and /api/view agree on action state.
```

---

## 3. Test full `SessionStore` extraction

Purpose: prove persistence/restore is centralized, atomic, monotonic, and restartable.

### 3.1 Static extraction test

Confirm the repo imports:

```python
from calendar_pilot.environment.session_store import SessionStore
```

Expected responsibilities:

```text
load state
save state
save latest snapshot
save manifest
append replay
compact replay
restore session
state_version management or coordination
```

### 3.2 Atomic write test

Simulate an interrupted write:

```python
from pathlib import Path
from calendar_pilot.environment.session_store import SessionStore

store = SessionStore(run_dir=Path("runs/sessionstore_test"))
store.save_state({"session_id": "sess_test", "state_version": 1})
assert (Path("runs/sessionstore_test") / "session_state.json").exists()
assert not list(Path("runs/sessionstore_test").glob("*.tmp*"))
```

Pass criteria:

```text
No partial JSON files survive normal write.
Existing valid session_state.json remains valid after simulated write failure.
Restore either returns last complete state or a structured recovery error.
```

### 3.3 Restart/restore test

Run:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Create prep before my client call" \
  --replay-out "$RUN_DIR/replay_restore.jsonl" \
  --commit
```

Then start a new session object pointed at the same `run_dir`.

Pass criteria:

```text
session_id restored.
state_version restored and increments on next mutation.
latest_plan restored or explicitly absent with recovery note.
active undo ledger restored.
replay length unchanged after restore.
session_manifest.json exists and names runtime/backends.
```

### 3.4 Concurrency regression

Run one slow plan request while polling state:

```text
Thread A: POST /api/plans with injected slow planner/model
Thread B: repeated GET /api/view or /api/state
```

Pass criteria:

```text
state_version is monotonic.
No JSON decode errors.
No torn committed receipt.
No committed action missing rollback_state.
No duplicate replay records from concurrent persist.
```

The System Framework identified `state_version` and per-session locking as the ordering/staleness mechanism for the Glass Cockpit and backend state. 

---

## 4. Test the Glass Cockpit ES-module frontend

Purpose: prove the new UI is a live replay reader, not a static inspector.

The System Framework defines the Glass Cockpit around five surfaces — Operate, Observe, Learn, Lab, Authority — plus an Envelope Viewer. It also defines `GET /api/view` as checkpoint state, `GET /api/events` as SSE deltas, and `state_version` as ordering/staleness metadata. 

### 4.1 Static frontend structure test

Assert:

```text
frontend/static/index.html loads <script type="module" src="js/main.js">
frontend/static/js/h.js exists
frontend/static/js/api.js exists
frontend/static/js/bus.js exists
frontend/static/js/store.js exists
frontend/static/js/views/operate.js exists
frontend/static/js/views/observe.js exists
frontend/static/js/views/learn.js exists
frontend/static/js/views/lab.js exists
frontend/static/js/views/authority.js exists
```

Pass criteria:

```text
No dynamic app code depends on legacy app.js.
No dynamic rendering uses string-templated innerHTML.
DOM builder creates text nodes for model/user/provider strings.
Legacy app.js can remain, but index.html loads the ES module entrypoint.
```

The target says the frontend should use native ES modules, no framework/no npm/no build step, and close XSS by construction with no `innerHTML` templating of dynamic strings. 

### 4.2 `/api/view` checkpoint test

Run:

```bash
curl -s http://127.0.0.1:8787/api/view > "$RUN_DIR/view_state.json"
```

Assert:

```text
view_version == "view_state.v2"
state_version exists
session exists
runtime exists
conversation exists
frontier exists
actions exists
authority exists
learning exists
lab exists
pipeline exists
invariants exists
```

Pass criteria:

```text
/api/view contains all top-level Glass Cockpit regions.
state_version matches or exceeds /api/state state_version.
actions.queue references envelope_id when action exists.
learning exposes tuning/frontier/taxonomy fields, even if empty.
```

### 4.3 `/api/events` SSE test

Run:

```bash
curl -N http://127.0.0.1:8787/api/events > "$RUN_DIR/events.sse" &
SSE_PID=$!

curl -s -X POST http://127.0.0.1:8787/api/plans \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Make tomorrow less chaotic"}' \
  > "$RUN_DIR/sse_plan_response.json"

sleep 2
kill "$SSE_PID"
```

Pass criteria:

```text
events.sse contains event frames.
Events include seq.
Events include state_version.
Events include trace_id.
Events include stage names such as route_classified, planner_started, frontier_generated.
After ActionLifecycle commit, events include simulate/stage/commit/provider_verify/rollback as applicable.
```

### 4.4 Browser smoke test

Run:

```bash
PYTHONPATH=src python3 scripts/run_browser_e2e.py \
  --run-dir "$RUN_DIR" \
  --artifact-dir "$RUN_DIR/browser"
```

Pass criteria:

```text
Operate surface loads.
Goal submission produces candidate cards.
Observe surface shows pipeline stages.
Learn surface shows frontier/taxonomy/tuning areas.
Lab surface shows self-play backend policy.
Authority surface shows grants/undo ledger.
Envelope Viewer opens from candidate/receipt/action card.
No console errors.
```

If Playwright/Chromium is unavailable locally, run the same test in CI or with the external browser flow; record that browser E2E was skipped only for environment/tooling, not product logic.

---

## 5. Test EventKit self-play sandbox enforcement in Swift

Purpose: prove sandboxing is enforced below Python, in Swift/EventKit.

ML-E2E defines the provider sandbox target: all provider writes must target the sandbox calendar only, commits must return external IDs, rollback paths must return rollback state, idempotent replay must not duplicate events, and provider errors must become receipts/replay records. 

### 5.1 Build Swift bridge

On macOS:

```bash
swift build --package-path packages/CalendarPilotKernel \
  --product CalendarPilotEventKitBridge
```

Pass criteria:

```text
Bridge builds on macOS.
Linux CI still builds placeholder without EventKit failure.
```

### 5.2 Sandbox deny test

Configure a sandbox calendar:

```bash
export CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1
export CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"
```

Send a commit payload targeting a non-sandbox calendar.

Pass criteria:

```text
Swift bridge rejects before EventKit mutation.
Receipt sync_status == denied.
denied_reason mentions sandbox calendar allowlist.
Replay records provider error/denial.
No external event is created.
```

### 5.3 Sandbox allow test

Send a create action targeting only the sandbox calendar.

Pass criteria:

```text
Commit succeeds.
external_event_id exists.
provider_transaction_id exists.
idempotency_key exists.
rollback_handle_id exists.
rollback_state is pending or verified.
```

### 5.4 Sandbox rollback test

Run:

```text
create focus block in CalendarPilot SelfPlay
verify external_event_id exists
rollback
verify event removed/restored
repeat same idempotency key
verify no duplicate event
```

Pass criteria:

```text
Rollback verified.
No duplicate creates on idempotent replay.
Rollback sweep touches only sandbox calendar.
All provider errors become receipts/replay.
```

ML-E2E names this exact create/rollback and move/rollback pattern for provider-sandbox acting. 

---

## 6. Test contract golden vectors and KernelServer roundtrip

Purpose: replace string-grep parity with executable contract parity.

The System Framework carries forward contract execution parity as a required consolidation item: golden vectors under `contracts/testdata/`, pytest against `SwiftKernelStub`, Swift tests against `CalendarKernel`, and a `contract_roundtrip` command on `CalendarPilotKernelServer`. 

### 6.1 Golden vector file shape

Each file in `contracts/testdata/*.json` should contain:

```json
{
  "name": "private_create_commit",
  "operation": "commit",
  "observation": {},
  "candidate": {},
  "grant": {},
  "expected": {
    "sync_status": "materialized",
    "stage_state": "committed",
    "actuation_mode": "materialized_write",
    "rollback_state": "pending",
    "generated_event_ids_count": 1
  }
}
```

### 6.2 Python stub vector runner

Run:

```bash
PYTHONPATH=src python3 scripts/run_contract_vectors.py \
  --backend python_stub \
  --vectors contracts/testdata \
  --out "$RUN_DIR/contract_vectors_python.json"
```

Pass criteria:

```text
All vectors pass against Python SwiftKernelStub.
Expected receipt fields match.
Denied vectors include denied_reason.
Undo replay vector proves handle cannot be consumed twice.
```

### 6.3 Swift KernelServer roundtrip

Build:

```bash
swift build --package-path packages/CalendarPilotKernel \
  --product CalendarPilotKernelServer
```

Run:

```bash
PYTHONPATH=src python3 scripts/run_contract_vectors.py \
  --backend swift_ipc \
  --vectors contracts/testdata \
  --out "$RUN_DIR/contract_vectors_swift.json"
```

Pass criteria:

```text
KernelServer accepts contract_roundtrip command.
Python JSON → Swift decode → Swift encode → Python compare succeeds.
Swift receipt fields match expected vector fields.
Python and Swift vector summaries agree.
```

### 6.4 Required vector set

Minimum vectors:

```text
private_create_commit
private_create_stage_only
people_affecting_without_commit_social_denied
tier5_social_with_commit_social_committed
tier6_auto_apply_plan_without_scope_denied
tier6_auto_apply_plan_with_scope_committed
undo_once_succeeds
undo_twice_denied
stale_observation_commit_denied_or_refreshed
provider_sandbox_outside_calendar_denied
```

Pass criteria:

```text
All vectors pass in Python and Swift.
String-grep parity tests can remain as smoke, but vector parity is the gate.
```

---

## 7. Test provider-backed self-play execution

Purpose: prove self-play no longer bypasses the production acting spine.

ML-E2E defines self-play layers: `stub_fast`, `swift_ipc_deterministic`, `swift_ipc_eventkit_sandbox`, and `production_shadow`, with different grant policies. 

### 7.1 Backend policy matrix test

Assert:

```text
stub_fast → self_issued
swift_ipc_deterministic → kernel_issued_sandbox
swift_ipc_eventkit_sandbox → kernel_issued_sandbox
production_shadow → read_only
```

Pass criteria:

```text
Missing env flags force read-only/no grant for gated backends.
production_shadow never obtains write grant.
swift_ipc_* grants include commit_selfplay_sandbox.
grant provenance includes selfplay_lab:<backend>:episode:N.
```

### 7.2 Stub-fast control run

Run:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Make next week less chaotic" \
  --self-play 5 \
  --self-play-backend stub_fast \
  --replay-out "$RUN_DIR/selfplay_stub_fast.jsonl"
```

Pass criteria:

```text
Replay contains decision records.
Replay contains one receipt per episode.
Replay contains reward records.
Replay contains self_play_episode records.
Replay contains adversary_finding records.
```

### 7.3 Swift IPC deterministic backend

Run:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Make next week less chaotic" \
  --self-play 5 \
  --self-play-backend swift_ipc_deterministic \
  --replay-out "$RUN_DIR/selfplay_swift_ipc.jsonl"
```

Pass criteria:

```text
Self-play uses ActionLifecycle for non-stub backend.
Replay includes envelope_transition rows.
Grant is kernel-issued, not self-minted.
Receipts come from Swift IPC path.
denied_actuation findings appear when Swift denies.
```

ML-E2E previously identified direct `kernel.authorize_and_materialize` in all self-play backends as a target gap; this test proves that gap is closed. 

### 7.4 EventKit sandbox backend

Run only on macOS with sandbox env:

```bash
export CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1
export CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"

PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Make next week less chaotic" \
  --self-play 3 \
  --self-play-backend swift_ipc_eventkit_sandbox \
  --replay-out "$RUN_DIR/selfplay_eventkit_sandbox.jsonl"
```

Pass criteria:

```text
All provider writes target sandbox calendar only.
All commits return external IDs.
Rollback_state present for every commit.
Provider errors become receipts/replay records.
Replay passes invariants.
```

---

## 8. Test Tier-6 plan graph with compound rollback ordering

Purpose: prove `auto_apply_plan` is a real compound action path, not nested metadata with accidental ordering.

### 8.1 Plan graph contract test

Create a Tier-6 candidate:

```json
{
  "candidate_id": "cand_tier6_compound",
  "intent": "full_optimizer",
  "required_authority_tier": 6,
  "actions": [
    {
      "action_type": "auto_apply_plan",
      "metadata": {
        "plan_graph": "{\"steps\":[{\"step_id\":\"s1\",\"action\":{\"action_type\":\"create_focus_block\"}},{\"step_id\":\"s2\",\"depends_on\":[\"s1\"],\"action\":{\"action_type\":\"add_buffer\"}}],\"rollback_order\":[\"s2\",\"s1\"]}"
      }
    }
  ]
}
```

Pass criteria:

```text
Plan graph parses.
Every step has step_id.
Dependencies reference known step_id values.
Graph is acyclic.
rollback_order contains every materialized step exactly once.
```

### 8.2 Authority test

Run with insufficient authority:

```text
tier < 6
or missing auto_apply_plan scope
```

Pass criteria:

```text
Commit denied.
denied_reason mentions tier 6 or auto_apply_plan scope.
No provider mutation.
Envelope exists with rollback_state = impossible or unsupported only if denial path requires it; otherwise denied envelope is replayed.
```

Run with Tier 6 grant:

```text
max_authority_tier = 6
scopes include auto_apply_plan
confirmed_by_user = true
```

Pass criteria:

```text
Compound commit succeeds or fails stepwise with structured failure.
Each step receives a receipt or provider sub-receipt.
Compound envelope lists step order.
Compound envelope lists rollback_order.
```

### 8.3 Compound rollback test

After compound commit:

```bash
curl -s -X POST http://127.0.0.1:8787/api/undo \
  -H 'Content-Type: application/json' \
  -d '{"rollback_handle_id":"<compound_rollback_handle>"}' \
  > "$RUN_DIR/tier6_undo.json"
```

Pass criteria:

```text
Rollback executes in reverse dependency order.
If step s2 depends on s1, rollback order is s2 → s1.
Partial rollback failure records failed step and remaining rollback state.
Replay records each rollback transition.
Undo cannot be replayed twice.
```

---

## 9. Test right-moment temporal controller

Purpose: prove timing is a control decision over exposure/stage/commit timing, not just a score attached to a candidate.

The repo already treats right-moment prediction as part of the policy loop, using response windows, fatigue, focus mode, authority tier, reversibility, and urgency.  The deferred target is a temporal controller with explicit modes.

### 9.1 Static/controller API test

Import:

```python
from calendar_pilot.diffusiongemma.temporal_controller import RightMomentTemporalController
```

Expected modes:

```text
act_now
stage_now_commit_later
bundle_into_digest
wait_for_context_refresh
ask_for_authority
do_nothing
```

### 9.2 Perturbation tests

Run the same candidate under different contexts:

```text
focus_mode = false vs true
notification_fatigue = 0.1 vs 0.8
best_response_hour vs bad_response_hour
authority grant fresh vs near-expired
observation fresh vs stale
private reversible write vs social mutation
```

Pass criteria:

```text
Focus mode increases exposure/interruption cost.
High fatigue shifts notify_now → bundle_into_digest or wait.
Bad response hour shifts act_now → stage_now_commit_later or wait.
Stale observation shifts commit → wait_for_context_refresh.
Near-expired authority shifts delayed commit → ask_for_authority.
Social mutation shifts auto-write → stage/ask/authority path unless scoped.
```

### 9.3 Replay test

For every candidate, assert:

```text
right_moment_decision present
right_moment_score present
temporal_control_mode present
staleness_risk present
exposure_cost present
authority_expiry_risk present
```

Pass criteria:

```text
Temporal-control fields are visible in candidate, replay, /api/view, and Learn surface.
Offline tuning can change timing decisions, not only candidate ranking.
Frontier diff reports timing changes.
```

---

## 10. Test tuning/frontier viewer polish

Purpose: prove the Learn surface makes policy change inspectable.

### 10.1 Generate frontier diff

Run:

```bash
PYTHONPATH=src python3 scripts/run_frontier_diff.py \
  --tuning "$RUN_DIR/policy_tuning.json" \
  --out "$RUN_DIR/frontier_diff.json"
```

Pass criteria:

```text
frontier_diff.json contains untuned_leader.
frontier_diff.json contains tuned_leader.
frontier_diff.json contains leader_changed.
frontier_diff.json contains per_candidate_delta.
frontier_diff.json contains intent/timing deltas.
```

### 10.2 Generate scorecard

Run:

```bash
PYTHONPATH=src python3 scripts/make_scorecard.py \
  --run-dir "$RUN_DIR" \
  --out "$RUN_DIR/scorecard.json"
```

Pass criteria:

```text
scorecard contains record_counts.
scorecard contains frontier metrics.
scorecard contains acting metrics.
scorecard contains learning metrics.
scorecard contains self_play metrics.
scorecard contains invariant violations.
scorecard contains promote|hold|rollback decision.
```

ML-E2E defines the scorecard shape around record counts, frontier `OTHER` rate, acting receipts, learning/tuning, self-play failures, invariants, and final decision. 

### 10.3 Learn surface UI test

Open the Glass Cockpit Learn surface.

Pass criteria:

```text
Shows current frontier.
Shows tuned vs untuned leader.
Shows per-candidate reward delta.
Shows taxonomy health and OTHER rate.
Shows model-generation rejection counts.
Shows tuning provenance / supporting replay records.
Shows right-moment timing changes.
Can open Envelope Viewer or trace from a candidate.
```

### 10.4 Regression guard

After feedback or self-play failure, rerun:

```bash
PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay "$RUN_DIR/replay.jsonl" \
  --out "$RUN_DIR/offline_policy_report_after.json" \
  --tuning-out "$RUN_DIR/policy_tuning_after.json"

PYTHONPATH=src python3 scripts/run_frontier_diff.py \
  --tuning "$RUN_DIR/policy_tuning_after.json" \
  --out "$RUN_DIR/frontier_diff_after.json"
```

Pass criteria:

```text
Tuning cites replay records.
Policy change is explainable.
No one-off prose intent keys appear.
Canonical intent keys only.
Frontier changes are visible in Learn surface.
```

---

# Integrated end-to-end deferred-work ladder

Once each component passes individually, run the full ladder.

## Layer 1 — deterministic fixture

```bash
make ml-ladder
```

Or explicitly:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Make next week less chaotic" \
  --self-play 5 \
  --replay-out "$RUN_DIR/replay.jsonl" \
  --commit
PYTHONPATH=src python3 scripts/check_invariants.py \
  --replay "$RUN_DIR/replay.jsonl" \
  --out "$RUN_DIR/invariant_report.json"
PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay "$RUN_DIR/replay.jsonl" \
  --out "$RUN_DIR/offline_policy_report.json" \
  --tuning-out "$RUN_DIR/policy_tuning.json"
PYTHONPATH=src python3 scripts/run_frontier_diff.py \
  --tuning "$RUN_DIR/policy_tuning.json" \
  --out "$RUN_DIR/frontier_diff.json"
PYTHONPATH=src python3 scripts/make_scorecard.py \
  --run-dir "$RUN_DIR" \
  --out "$RUN_DIR/scorecard.json"
```

Pass criteria:

```text
ActionLifecycle transitions present.
SessionStore artifacts valid.
Replay invariants pass.
Frontier diff generated.
Scorecard generated.
Glass Cockpit /api/view renders same state.
```

## Layer 2 — Swift IPC deterministic

```bash
swift build --package-path packages/CalendarPilotKernel \
  --product CalendarPilotKernelServer

CALENDAR_PILOT_RUNTIME_MODE=swift_ipc \
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Create prep before my client call" \
  --self-play 5 \
  --self-play-backend swift_ipc_deterministic \
  --replay-out "$RUN_DIR/replay_swift_ipc.jsonl" \
  --commit
```

Pass criteria:

```text
Swift receipts present.
Golden vectors pass Python + Swift.
Undo once succeeds.
Undo twice denied.
Self-play uses kernel-issued sandbox grant.
```

## Layer 3 — live model/executive, deterministic provider

```bash
CALENDAR_PILOT_RUNTIME_MODE=production \
CALENDAR_PILOT_PROVIDER_BACKEND=deterministic \
PYTHONPATH=src python3 scripts/run_live_codex_e2e.py

CALENDAR_PILOT_RUNTIME_MODE=live_diffusiongemma \
PYTHONPATH=src python3 scripts/run_live_diffusiongemma_e2e.py
```

Pass criteria:

```text
Codex reaches model.
NIM reaches model.
NIM frontier validates.
Rejected model generations retained.
Codex tool sequence replayed.
No missing trace_id/causal_parent_id.
```

ML-E2E defines the live Codex/NIM integration expectations this way: Codex and NIM must both reach their models, tool sequence and frontier must enter replay, Swift receipts must exist for acting, and undo must work once but not twice. 

## Layer 4 — EventKit sandbox

```bash
export CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1
export CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"

CALENDAR_PILOT_RUNTIME_MODE=live_provider \
CALENDAR_PILOT_PROVIDER_BACKEND=apple_eventkit \
PYTHONPATH=src python3 scripts/run_live_eventkit_e2e.py \
  --sandbox-calendar "CalendarPilot SelfPlay" \
  --run-dir "$RUN_DIR/eventkit"
```

Pass criteria:

```text
Swift enforces sandbox allowlist.
Create/rollback verified.
Move/rollback verified.
Idempotency prevents duplicates.
Replay contains provider receipts.
Invariant report passes.
```

## Layer 5 — Glass Cockpit live loop

Run the app:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app frontend \
  --serve \
  --run-dir "$RUN_DIR/frontend_live"
```

Then exercise:

```text
Submit goal in Operate.
Watch pipeline in Observe.
Open candidate in Learn.
Commit/stage/undo from Operate.
Open Envelope Viewer.
Run Lab self-play.
Inspect Authority grant/undo ledger.
Generate frontier diff and scorecard.
```

Pass criteria:

```text
All surfaces update through /api/view or /api/events.
state_version monotonic.
No stale action after commit/undo.
Envelope Viewer shows full causal chain.
Learn surface shows tuning/frontier changes.
Lab surface shows backend policy and episode findings.
Authority surface shows grant scope/provenance/expiry.
```

---

# Final promotion checklist

You can promote the deferred pass when all of these are true:

```text
[ ] ActionLifecycle is the only path for simulate/stage/commit/verify/reward/undo.
[ ] Every mutation has exactly one ActionEnvelope.
[ ] Every committed envelope has rollback_state.
[ ] SessionStore owns state/snapshot/manifest/replay persistence.
[ ] Restore works after restart.
[ ] Concurrent poll/mutation does not corrupt state or replay.
[ ] Glass Cockpit loads ES modules, not legacy app.js.
[ ] /api/view, /api/events, and /api/trace work.
[ ] EventKit sandbox is enforced in Swift, not Python.
[ ] Contract golden vectors pass on Python stub and Swift kernel.
[ ] KernelServer contract_roundtrip works.
[ ] Non-stub self-play uses ActionLifecycle.
[ ] Provider-backed self-play cannot self-issue real write grants.
[ ] Tier-6 plan graph validates dependencies and rollback order.
[ ] Compound rollback executes in reverse dependency order.
[ ] Right-moment controller changes timing under perturbations.
[ ] Frontier/tuning viewer explains why the policy changed.
[ ] check_invariants.py passes on replay.
[ ] make_scorecard.py produces promote/hold/rollback decision.
```

The bottom line: test each deferred item as part of the same closed loop — **candidate → envelope → receipt → replay → invariant → tuning → frontier diff → UI evidence** — not as isolated unit behavior.

---

# Codex validation run log

## deferred_pass_codex_20260702

Started: 2026-07-02 18:59:19 PDT

Workspace commit checkpoint:

```text
7322977 Add calendar pilot deferred pass
```

Scope:

```text
Project under test: calendar-pilot-deferred-pass
Run directory: calendar-pilot-deferred-pass/runs/deferred_pass_codex_20260702
Do-not-reference directory left unstaged and uncommitted.
```

Progress:

```text
[2026-07-02 18:59 PDT] Read the deferred-work testing framework and Computer Use policy.
[2026-07-02 18:59 PDT] Committed the current non-Do-not-reference snapshot before starting validation.
[2026-07-02 18:59 PDT] Preparing run directory and starting baseline repo validation.
[2026-07-02 19:00 PDT] Baseline Python unit tests passed: 147 tests, 10 skipped.
[2026-07-02 19:00 PDT] Baseline Swift package tests passed: 17 XCTest tests, plus Swift Testing empty suite.
[2026-07-02 19:00 PDT] Golden replay invariants passed with no violations; artifact: runs/deferred_pass_codex_20260702/invariant_report_baseline.json.
[2026-07-02 19:00 PDT] Deterministic demo produced runs/deferred_pass_codex_20260702/replay.jsonl with 63 records, a committed SwiftKernelStub receipt, and 5 accepted self-play episodes.
[2026-07-02 19:00 PDT] Generated invariant_report.json with zero violations.
[2026-07-02 19:00 PDT] Generated offline_policy_report.json and policy_tuning.json; training_rows=5, taxonomy other_rate=0.0.
[2026-07-02 19:01 PDT] Generated frontier_diff.json; leader_changed=false, tuned_leader=cand_ce7cb50eb254, valid_candidates=6.
[2026-07-02 19:01 PDT] Generated scorecard.json using explicit replay/frontier/offline-report arguments; decision=promote_candidate.
[2026-07-02 19:02 PDT] Started frontend server on 127.0.0.1:8787 with run dir runs/deferred_pass_codex_20260702/frontend_live.
[2026-07-02 19:02 PDT] Exercised /api/health, /api/state, /api/view, /api/plans, candidate simulate/stage/commit, /api/replay, and /api/trace/cand_ce7cb50eb254. /api/view returned view_state.v2 with all required regions and state_version 6; trace returned 17 records and an envelope with rollback_state=pending.
[2026-07-02 19:03 PDT] Initial /api/events stream emitted router/planner/frontier frames but did not expose action lifecycle transitions after candidate actions.
[2026-07-02 19:06 PDT] Patched frontend session SSE emission to publish action-envelope lifecycle transitions as action_lifecycle trace events.
[2026-07-02 19:06 PDT] Focused frontend/session/action-lifecycle tests passed after the SSE patch.
[2026-07-02 19:07 PDT] Re-ran /api/events lifecycle capture; stream emitted 18 events with route_classified, planner_started, frontier_generated, prepare, simulate, stage, and commit stages. Every event had seq, state_version, and trace_id.
[2026-07-02 19:14 PDT] Updated browser CDP e2e coverage for the ES-module Glass Cockpit shell after it exposed stale legacy selectors and a leading-shebang parse issue.
[2026-07-02 19:15 PDT] Patched the client refresh path so POST responses update the active session view immediately instead of refreshing a stale session id.
[2026-07-02 19:16 PDT] Browser e2e passed through the app shell: prompt, simulate, stage, commit, undo, feedback, envelope overlay, surface navigation, Lab self-play, Authority denial, replay export, and New chat reset.
[2026-07-02 19:19 PDT] Computer Use visual testing exposed a real layout regression: Glass Cockpit tabs stretched vertically over the work surface and the composer was not reliably reachable.
[2026-07-02 19:20 PDT] Patched CSS grid/tab/composer sizing; Computer Use then showed reachable horizontal surface tabs, visible composer, and inspector rail.
[2026-07-02 19:21 PDT] Computer Use submitted "Computer Use smoke: create prep before client call" through Chrome. The app routed to Observe, state_version advanced to 2, route/planner/frontier events rendered, and Learn/Lab/Authority surfaces routed with matching inspector surface names.
[2026-07-02 19:22 PDT] Full Python unit suite passed after patches: 147 tests, 10 skipped.
[2026-07-02 19:22 PDT] Swift package tests passed after patches: 17 XCTest tests, plus Swift Testing empty suite.
[2026-07-02 19:22 PDT] Browser e2e re-run passed after layout/client patches; artifacts: runs/browser_e2e/artifacts/browser_success.png and browser_replay_export.json.
[2026-07-02 19:22 PDT] Rechecked deterministic replay invariants after patches; runs/deferred_pass_codex_20260702/invariant_report_after_patches.json is ok with 63 records and zero violations.
[2026-07-02 19:22 PDT] Contract golden vector passed on Python stub; artifact: runs/deferred_pass_codex_20260702/contract_vectors_python_kernel.json.
[2026-07-02 19:23 PDT] Built CalendarPilotKernelServer and ran the same contract golden vector through Swift IPC; artifact: runs/deferred_pass_codex_20260702/contract_vectors_swift_kernel.json.
[2026-07-02 19:23 PDT] Built CalendarPilotEventKitBridge successfully.
[2026-07-02 19:23 PDT] Ran swift_ipc_deterministic self-play for 5 episodes; accepted=5, rejected=0, replay artifact: runs/deferred_pass_codex_20260702/selfplay_swift_ipc.jsonl.
[2026-07-02 19:23 PDT] Invariants passed on swift_ipc_deterministic self-play replay; artifact: runs/deferred_pass_codex_20260702/invariant_report_selfplay_swift_ipc.json.
[2026-07-02 19:24 PDT] Ran swift_ipc_eventkit_sandbox without the required env flag; the lifecycle denied actuation with provider_not_configured and wrote a replay instead of touching a real provider.
[2026-07-02 19:24 PDT] Ran production_shadow without the required env flag; actuation was denied because no Swift-issued write grant was available. Invariants passed on the sandbox and shadow replays.
[2026-07-02 19:25 PDT] Focused ActionLifecycle, SessionStore persistence, Tier-6 plan graph, right-moment temporal controller, safety-contract, and Swift IPC runtime suites passed. Swift IPC was run with CALENDAR_PILOT_RUN_SWIFT_IPC_TESTS=1: 9 tests passed.
[2026-07-02 19:27 PDT] After a defensive SSE helper cleanup, re-ran frontend server API tests, session persistence tests, action-lifecycle/store tests, and browser e2e; all passed.
```
