Below is a **step-by-step testing framework** for CalendarPilot's machine-learning system, aligned to the current architecture: DiffusionGemma/NIM generates typed candidate futures, Codex operates typed tools, Swift owns authority/materialization/rollback, and replay/self-play/tuning close the loop. The target framework defines those as the measurable axes for ML, acting, and self-play.

# CalendarPilot ML Test Framework

## Revision notes — 2026-07-02 verification pass

Every step below was fact-checked against the current baseline repo (`calendar-pilot-system-framework`) by a parallel review fleet. Corrections applied in this revision:

1. **Step 20's "deterministic ladder" ended on a live-NIM step.** `run_replay_offline_tuning_loop.py` hard-requires live NIM credentials (`health_status(validate_remote=True)` fails closed, `SystemExit(2)`). The ladder now ends with a new deterministic frontier-diff script (code in step 12); the NIM loop moved to the live ladder.
2. **Contract names corrected**: the Python classes are `CandidateCalendarAction` and `CalendarActionReceipt` (no `V2` suffix — V2 is the schema-revision label in `contracts/`, not the class name).
3. **Taxonomy `matched_by` values corrected**: `exact|alias|keyword|fallback` — there is no `model` value today (`ModelIntentRouter` is a keyword-fallback placeholder). `normalize_intent()` returns key `matched_by`; the candidate field is `intent_matched_by`.
4. **`router_decision` payload corrected**: actual keys are `record_type, turn_id, router_backend, classified_intent, route, confidence, counterfactual_routes, evidence`. `trace_id` lives on the replay-record wrapper, not in the payload. `router_backend` today is `fixture_keywords|fallback_keywords` only.
5. **Step 7 expected routes split into "current (verified)" vs "target"** — two of the six test phrases behave differently than originally written, and one is a known misroute worth keeping as an expected-fail regression.
6. **Step 10 invariants split**: only I2 (rollback_state present) and I6 (undo never replays) are implemented in `environment/invariants.py`. The other five are now provided as code to add.
7. **Steps 5/14 metrics split into "captured today" vs "requires instrumentation"**: goal, observation fingerprint, tuning id, intent distribution, OTHER rate, request latency, HTTP status, schema retry count, and rejection count are now recorded on live frontier metadata. Transport retry count remains unavailable because `http_retry` is still `"none"`; only schema retry exists today.
8. **Every step now carries a Status line**: `Runnable now` / `Partial` / `Target` (with the blocking deferral named). Deferred features per the implementation pass: full ActionLifecycle extraction, SessionStore extraction, Glass Cockpit frontend, Swift-side EventKit sandbox enforcement, contract golden vectors + KernelServer roundtrip, provider-backed self-play, Tier-6 plan graph, right-moment temporal controller.
9. **New harness code added**: `scripts/run_frontier_diff.py` (step 12), `tests/test_taxonomy.py` (step 3), `tests/test_invariants.py` + five new invariant checks (step 10), `scripts/make_scorecard.py` (step 19), `--self-play-backend` on the demo CLI (step 13), `live.py` metadata and action-program validation (steps 2/5), and root/framework `make ml-ladder`, `make frontier-diff`, and `make scorecard` targets.

Two code-side recommendations that fell out of verification (fix in repo, not in this doc):

- `runtime.py:credential_state()` now aligns with `live.py`: `CALENDAR_PILOT_NIM_API_KEY | NVIDIA_API_KEY | NIM_API_KEY` all count as NIM credentials.
- `_route_turn()` records the new router's `confidence` but overwrites `classified_intent`/`route` with the legacy classifier's decision — the recorded confidence belongs to a decision that didn't decide. Record the legacy result as the decision (confidence null) or as the counterfactual.

## Source Of Truth

- Active repo snapshot: `calendar-pilot-system-framework/`
- Current working document: root `ML-E2E.md`

## Current Local Validation

These checks were rerun from `calendar-pilot-system-framework/` on 2026-07-02:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python3 scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl
PYTHONPATH=src python3 -m calendar_pilot.app frontend --write-snapshot --out runs/ci_evidence/frontend_state.json
PYTHONPATH=src python3 scripts/run_secret_scan.py --path runs/ci_evidence
```

Result:

```text
Python: 155 tests OK, 9 skipped
Swift: 17 tests OK
Golden replay invariant check: OK
Evidence snapshot secret scan: OK
Swift IPC: 9 tests OK
Browser E2E: OK
macOS app build: OK, created dist/CalendarPilot.app
Live Codex E2E: OK
Live DiffusionGemma E2E: OK
Replay -> offline tuning -> next NIM generation: OK, leader changed
Manual UI via computer use: fixture prompt produced 20 replay records, 0 invariant violations
EventKit: blocked by macOS Calendar permission status not_determined; mutation disabled
```

Not rerun in this pass: `dogfood-release`, Finder launch of the packaged app, and live EventKit mutation. EventKit mutation still requires explicit `CALENDAR_PILOT_EVENTKIT_MUTATION=1` or `CALENDAR_PILOT_REQUIRE_EVENTKIT=1` plus OS Calendar permission.

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

Closed-loop ML dogfood:

```bash
make ml-ladder
make frontier-diff
make scorecard
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

---

## Working Progress Ledger

Update this table after every implementation or test pass. "Complete" means the current repo has executable evidence for the gate; "Partial" means the slice is usable but named target behavior remains; "Blocked" means the next action needs credentials, OS permission, or a deferred architecture item.

| Step | Gate | Current status | Evidence / artifact | Last command | Latest result | Next update |
|---:|---|---|---|---|---|---|
| 0 | Test spine | Partial | `TraceBus`, replay, envelope transitions | `make ml-ladder` | Closed deterministic chain produced replay, tuning, frontier diff, scorecard | Add ActionLifecycle stages to trace vocabulary |
| 1 | Environment readiness | Complete | Python/Swift/unit evidence | `make test`; `make swift-ipc-test` | Python 155 OK / 9 skipped; Swift 17 OK; Swift IPC 9 OK | Keep counts current in this table |
| 2 | Candidate contract validity | Complete for current fixture/live gates | Live parser rejects provider-invalid action programs and stores raw rejections | `make live-diffusiongemma-e2e` | Passed after rejecting null start/end write actions before commit | Extend to action graph validation for Tier 6 |
| 3 | Canonical intent taxonomy | Complete | `tests/test_taxonomy.py`; candidate constructor normalization | `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_taxonomy.py' -q` | 6 OK; scorecard matched_by: alias 19, exact 7, OTHER 0.0 | Track OTHER rate per dogfood run |
| 4 | Deterministic frontier baseline | Complete | `runs/ml_test_001/replay.jsonl` | `make ml-ladder` | 59 replay records; 0 invariant violations | Archive selected scorecards outside ignored `runs/` when needed |
| 5 | Live frontier generation | Complete for current credentialed run | `runs/live_diffusiongemma_e2e/artifacts/` | `make live-diffusiongemma-e2e` | Passed; NIM metadata includes goal, observation fingerprint, tuning id, latency, HTTP status, intent distribution, rejections | Add HTTP retry/backoff metrics |
| 6 | Reward anatomy | Partial | Reward-head fields and focus perturbation tests | `make py-test` | Existing behavioral tests pass | Add fatigue/dense/sparse/social perturbation matrix |
| 7 | Router-to-frontier trace | Partial | Router replay rows in UI/API runs | Manual UI prompt; `make browser-e2e` | UI run shows 1 router decision and 20 replay records | Fix known misroutes and confidence/legacy decision recording |
| 8 | Codex tool path | Complete for fixture and live Codex | `runs/live_codex_e2e/artifacts/` | `make live-codex-e2e` | Passed with browser CDP evidence | Combine live Codex + live NIM in production/sandbox run |
| 9 | ActionEnvelope / acting-aware ML | Partial | Envelope transitions on simulate/stage/commit receipt paths | `make ml-ladder`; manual UI | Fixture ladder 2 envelope transitions; UI run 2 envelope transitions | Extract ActionLifecycle as single mutation spine |
| 10 | Replay completeness | Complete for implemented invariants | `tests/test_invariants.py`; `scripts/check_invariants.py` | `make check-invariants`; UI replay invariant check | Golden replay OK; UI replay 20 records, 0 violations | Add tuning-output causal invariant once promotion reports cite rows |
| 11 | Offline tuning | Complete | `policy_tuning.json`, `offline_policy_report.json` | `make replay-offline-tuning-loop` | Passed; tuning id `offline_replay_v2`, leader changed | Add human-readable policy diff viewer |
| 12 | A/B frontier regression | Complete | `scripts/run_frontier_diff.py` | `make frontier-diff` via `make ml-ladder` | Deterministic diff produced per-candidate deltas; fixture leader unchanged | Add thresholds for regret/social-risk regressions |
| 13 | Self-play lab | Partial | `--self-play-backend`; goal forwarded to policy | `make ml-ladder`; `make replay-offline-tuning-loop` | Fixture self-play emitted rewards/findings; live loop passed after goal forwarding | Add scenario DSL and ActionLifecycle backend parity |
| 14 | Live model soak | Target | None yet | Not run | No soak harness | Build batch harness after HTTP retry/error taxonomy |
| 15 | Live Codex + live NIM integration | Partial | Separate live Codex and live NIM E2Es | `make live-codex-e2e`; `make live-diffusiongemma-e2e` | Both passed independently | Run combined live Codex + live NIM with deterministic provider |
| 16 | Provider sandbox acting | Blocked | `runs/eventkit_e2e/eventkit_health.json` | `make live-eventkit-e2e` | Blocked: EventKit permission `not_determined`, mutation disabled | Grant OS permission and add Swift sandbox allowlist before mutation |
| 17 | Human dogfood protocol | Partial | Manual Chrome/computer-use UI pass | Local server + computer use + invariant check | Prompt produced candidate UI, replay inspector showed 20 records, invariant OK | Add daily orchestration command |
| 18 | Promotion gates | Partial | `scorecard.json`, live E2E artifacts | `make ml-ladder`; live E2Es | Gate A passable now; B/C passed in current run; D/E still blocked/partial | Encode gate decisions in CI artifact bundle |
| 19 | Scorecard | Complete | `scripts/make_scorecard.py` | `make scorecard` via `make ml-ladder` | Scorecard decision `promote` for fixture ladder | Add trend history over repeated dogfood runs |
| 20 | First run sequence | Complete | `make ml-ladder` target | `make ml-ladder` | Replay -> invariant -> tuning -> frontier diff -> scorecard passed | Keep deterministic ladder as pre-live gate |

## 0. Define the test spine

**Status: Partial — TraceBus emits only 3 of the stage vocabulary (`route_classified`, `planner_started`, `frontier_generated`); acting/reward stages land with the ActionLifecycle extraction.**

Every ML test should produce or validate this chain:

```text
RawCalendarObservation
→ UserBiography
→ routed user goal
→ DiffusionGemma/NIM candidate frontier
→ canonical intent normalization
→ reward/right-moment scoring
→ Codex tool path
→ Swift receipt / ActionEnvelope
→ reward event / adversary finding
→ replay record
→ offline tuning
→ next frontier diff
```

The current repo already has the major contracts and surfaces for this: `RawCalendarObservation`, `CandidateCalendarAction`, `CalendarActionReceipt`, `RewardEvent`, Codex tool calls/receipts, replay, self-play, and offline policy tuning.

The rule: **a test is not complete unless it leaves evidence.** Evidence means replay JSONL, tuning output, frontier diff, invariant report, and a runtime/session manifest where applicable. Concrete filenames in this repo: `replay.jsonl`, `policy_tuning.json`, `frontier_diff.json`, `invariant_report.json` (via `check_invariants.py --out`), `session_state.json` / `latest_session.json` / launch manifest.

---

## 1. Environment readiness gate

**Status: Runnable now.**

Goal: prove the test environment is coherent before evaluating model behavior.

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
```

`python3 -m pytest -q` is equivalent (pyproject configures `pythonpath = ["src"]` and `testpaths = ["tests"]`); pick one harness per CI to keep counts comparable. Note the count semantics: unittest's "Ran 140" *includes* skips — current baseline is **131 passed, 9 skipped** on both harnesses, 17 Swift.

Then confirm these files exist and are usable:

```text
data/sample_calendar.json
data/sample_profile.json
configs/reward_weights.json
contracts/*.schema.json           (7 schemas)
scripts/train_offline_policy.py
scripts/run_replay_offline_tuning_loop.py   (live-NIM only — see step 20)
scripts/check_invariants.py
```

Pass criteria:

```text
Python tests pass (131 passed, 9 skipped baseline).
Swift tests pass (17).
Sample observation/profile parse.
Reward weights load.
No runtime mode reports live backends while actually using fixture/stub backends.
```

**Known gap this gate must close before it means anything for ML:** the `environment/` modules that the ML gates depend on (taxonomy, invariants, router) currently have **zero direct unit tests**. Steps 3 and 10 below include the test files to add — land those with this gate.

Why this matters: the repo's intended ML loop depends on typed candidate futures, reward heads, self-play findings, replay, and policy tuning, not just model text.

---

## 2. Contract-validity gate for generated candidates

**Status: Complete for current fixture/live gates — `from_dict` normalizes typed candidates, live NIM parsing now rejects provider-invalid action programs, and invalid live generations are retained as rejection records.**

Goal: every model-generated candidate must be executable by the rest of the system.

For each generated `CandidateCalendarAction`, validate (all field names verified against `types.py`):

```text
candidate_id exists
intent exists (canonical) + intent_raw + intent_matched_by present
actions[] non-empty unless do_nothing
target_calendars[] present
affected_event_ids[] present
affected_people_ids[] present
required_authority_tier in 0..6
reversibility in none|low|medium|high
predicted_acceptance / predicted_utility / predicted_engagement /
  predicted_regret / predicted_interruption_cost / predicted_social_risk /
  predicted_long_horizon_value / expected_reward present
reward_breakdown present
right_moment_decision valid + right_moment_score present
model_story present
counterfactual present
control_notes present
```

Run this against three sources:

```text
heuristic DiffusionGemmaPolicy
live NIM/DiffusionGemma frontier generation
self-play generated frontiers
```

Record two outputs:

```text
valid_candidates.jsonl
model_generation_rejections.jsonl
```

Pass criteria:

```text
100% of candidates that enter Codex/Swift satisfy CandidateCalendarAction.
100% of invalid model outputs are retained as model_generation_rejection records
  (the live parser already retains raw_item + reason + schema_errors per rejection).
Duplicate candidate IDs are rejected or normalized (parser emits duplicate_candidate_id).
Unknown action types and provider-invalid action programs are rejected before Codex/Swift.
```

Note: rejection records are appended to replay only on the live-frontier path (`_record_frontier_rejections_from_plan`). The heuristic policy never produces rejections by construction — assert `rejections == []` there rather than skipping the check.

---

## 3. Canonical intent taxonomy gate

**Status: Complete — `CanonicalIntent`, `normalize_intent()`, and `taxonomy_health()` are wired into `from_dict`, NIM parsing, reducer, tuning, scorecard, and candidate construction; `tests/test_taxonomy.py` is landed.**

Goal: stop ML signal fragmentation.

Before training or tuning, normalize every candidate intent into the bounded taxonomy (verified enum values):

```text
protect_deep_work
create_prep_block
add_buffer
batch_admin
reschedule_conflict
move_meeting
decline_or_trim
notify_summary
ask_clarification
do_nothing
other
```

For every candidate, store:

```json
{
  "intent": "create_prep_block",
  "intent_raw": "Create a prep block before the client call",
  "intent_matched_by": "exact|alias|keyword|fallback"
}
```

(`alias` fires when a near-canonical string maps through the alias table, e.g. `add_transition_buffer → add_buffer`. A `model` value does not exist yet; it arrives when live Codex intent routing lands.)

Test on:

```text
existing heuristic candidates
live NIM candidates
replay records
self-play episode choices
offline tuning input rows
```

Pass criteria:

```text
Training keys use canonical intent, not free text.
intent_raw is preserved for inspection.
OTHER rate is tracked (taxonomy_health() computes other_rate + matched_by histogram).
OTHER rate stays below 15% during dogfood runs.
Tuning output never creates one-off prose keys like "Help me prepare for my meeting tomorrow".
```

Landed unit gate — `tests/test_taxonomy.py`:

```python
import unittest

from calendar_pilot.environment.taxonomy import CanonicalIntent, normalize_intent, taxonomy_health


class TaxonomyTests(unittest.TestCase):
    def test_exact_match(self):
        result = normalize_intent("create_prep_block")
        self.assertEqual(result["intent"], "create_prep_block")
        self.assertEqual(result["matched_by"], "exact")

    def test_keyword_match_normalizes_prose(self):
        result = normalize_intent("Create a prep block before the client call")
        self.assertEqual(result["intent"], "create_prep_block")
        self.assertEqual(result["matched_by"], "keyword")
        self.assertEqual(result["intent_raw"], "Create a prep block before the client call")

    def test_fallback_to_other(self):
        result = normalize_intent("write a haiku about my week")
        self.assertEqual(result["intent"], CanonicalIntent.OTHER.value)
        self.assertEqual(result["matched_by"], "fallback")

    def test_every_canonical_value_round_trips_exactly(self):
        for intent in CanonicalIntent:
            self.assertEqual(normalize_intent(intent.value)["intent"], intent.value)

    def test_taxonomy_health_other_rate(self):
        candidates = [
            {"intent": "create_prep_block", "intent_matched_by": "keyword"},
            {"intent": "other", "intent_matched_by": "fallback"},
        ]
        health = taxonomy_health(candidates)
        self.assertAlmostEqual(health["other_rate"], 0.5)
        self.assertEqual(health["matched_by"], {"keyword": 1, "fallback": 1})
```

This is the first real ML gate. Without it, replay residuals and `intent_reward_bias` fragment across prose strings and do not accumulate.

---

## 4. Baseline deterministic frontier test

**Status: Runnable now.**

Goal: establish a stable baseline before live model calls.

Use (pin `--goal` so repeated runs are comparable — the flag exists and defaults to "Make next week less chaotic"):

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Make next week less chaotic" \
  --self-play 0 \
  --replay-out runs/baseline/replay.jsonl
```

(`--self-play 0` disables self-play episodes — the run exercises only the deterministic policy path. `--profile` defaults to `data/sample_profile.json`; `--authority-tier` defaults to 3; `--commit` defaults to off.)

Capture:

```text
candidate frontier
candidate ranking
reward_breakdown
right_moment_decision
model_story
counterfactual
control_notes
```

Pass criteria:

```text
At least one useful candidate is generated.
do_nothing is present or available as a baseline candidate.
Candidates have expected_reward and reward_breakdown.
Right-moment decisions are populated.
Top candidate is stable across repeated fixture runs with the same --goal.
```

This protects you from confusing live-model variance with basic policy or fixture drift.

---

## 5. Live frontier generation test

**Status: Complete for current credentialed runs — typed generation, rejection retention, schema-retry counting, request latency, HTTP status, goal, observation fingerprint, tuning id, and intent distribution are recorded. HTTP retry/backoff remains target work.**

Goal: verify that live DiffusionGemma/NIM is a generator, not just a ranker.

Credentials: one of `CALENDAR_PILOT_NIM_API_KEY`, `NVIDIA_API_KEY`, `NIM_API_KEY`. Frontier bounds: `CALENDAR_PILOT_NIM_FRONTIER_LIMIT` (default 4), `CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS` (default 4200), `CALENDAR_PILOT_NIM_TIMEOUT` (default 90s).

Run the same observation/profile/goal through live generation:

```bash
CALENDAR_PILOT_RUNTIME_MODE=live_diffusiongemma \
PYTHONPATH=src python3 scripts/run_live_diffusiongemma_e2e.py
```

**Captured today** (in the frontier result payload / policy metadata):

```text
model name
prompt version
valid candidate count
rejections[] with raw_item + reason + schema_errors
rejection_count
duplicate handling (duplicate_candidate_id rejections)
validation_errors[] incl. schema_retry markers
schema_retry_count
```

**Captured after the implementation pass**:

```text
goal
observation_id + observation_fingerprint
policy_tuning_id
canonical intent distribution + OTHER rate
request_latency_ms
http_status on successful requests and HTTP errors
schema_retry_count
rejection_count
```

**Still target work**:

```text
HTTP retry count          → IMPOSSIBLE today: http_retry is "none"; only schema_retry exists
HTTP failure aggregation  → errors are categorized as exceptions/artifacts, not soak metrics
```

Instrumentation implemented in `live.py`:

```python
# in _request_json(): wrap the urlopen call
start = time.monotonic()
...  # existing urlopen
elapsed_ms = int((time.monotonic() - start) * 1000)
# thread elapsed_ms back to the caller's metadata

# in generate_candidate_frontier(), extend the result metadata:
from calendar_pilot.environment.taxonomy import taxonomy_health
health = taxonomy_health([c.to_dict() for c in candidates])
metadata.update({
    "goal": goal,
    "observation_id": observation.observation_id,
    "policy_tuning_id": getattr(self.policy_tuning, "tuning_id", None),
    "intent_distribution": {c.intent: sum(1 for x in candidates if x.intent == c.intent) for c in candidates},
    "other_intent_rate": health["other_rate"],
    "request_latency_ms": elapsed_ms,
})
```

Pass criteria (post-instrumentation):

```text
Model emits typed CandidateCalendarAction objects.
Valid frontier count >= minimum threshold, e.g. 3 (frontier limit defaults to 4).
Rejected candidates are recorded with raw payloads, not silently dropped.
No candidate reaches Codex without schema validation.
Canonical intent OTHER rate stays below threshold.
```

Do not score this only by "did the top recommendation seem good?" Score it by **frontier quality** first.

---

## 6. Reward-model anatomy test

**Status: Partial — all reward-head fields exist with the exact names below; the focus-mode perturbation already has a behavioral test (`tests/test_behavioral_controls.py`); the full perturbation matrix is not yet a harness.**

Goal: prove the scoring system is not a black box.

For each candidate, assert these fields exist and are numerically sane (verified field names):

```text
predicted_acceptance
predicted_utility
predicted_engagement
predicted_regret
predicted_interruption_cost
predicted_social_risk
predicted_long_horizon_value
expected_reward
reward_breakdown
right_moment_score
```

Run perturbation tests:

```text
focus mode off vs on            (exists today — extend the pattern below)
notification fatigue low vs high
external meeting with prep slot vs without prep slot
social mutation vs private reversible write
dense calendar vs sparse calendar
```

Perturbation pattern (mirrors the existing focus-mode test; extend per axis):

```python
def test_focus_mode_raises_interruption_cost(self):
    base = json.loads(Path("data/sample_calendar.json").read_text())
    focused = json.loads(Path("data/sample_calendar.json").read_text())
    focused["device_context"]["is_focus_mode"] = True

    policy = DiffusionGemmaPolicy()
    biography = UserBiography.from_dict(json.loads(Path("data/sample_profile.json").read_text()))
    plain = {c.candidate_id: c for c in policy.generate_candidates(RawCalendarObservation.from_dict(base), biography)}
    focus = {c.candidate_id: c for c in policy.generate_candidates(RawCalendarObservation.from_dict(focused), biography)}

    shared = set(plain) & set(focus) - {"do_nothing"}
    self.assertTrue(shared)
    for cid in shared:
        self.assertGreaterEqual(focus[cid].predicted_interruption_cost,
                                plain[cid].predicted_interruption_cost)
```

Expected behavior:

```text
Focus mode increases interruption cost.
High notification fatigue lowers notify_now/auto_write_then_notify.
External meeting without prep increases create_prep_block utility.
Social mutation increases social risk and authority cost.
Sparse calendar lowers urgency/pressure.
```

Pass criteria:

```text
Reward heads move in expected directions.
Expected reward changes are explainable from reward_breakdown.
Right-moment decision changes when timing context changes.
No candidate wins solely because engagement overwhelms utility/regret.
```

The reward config already separates acceptance, utility, engagement, long-horizon value, regret, interruption, social risk, undo, ignored, and explicit-wrong weights.

---

## 7. Router-to-frontier trace test

**Status: Partial — `router_decision` records are appended on every plan turn; the model router is a placeholder; two of the original expected routes did not match verified behavior.**

Goal: prove user turns are routed correctly before ML generation.

For each user turn, a `router_decision` record is appended. The actual payload (verified against `RoutedTurn.replay_payload()`):

```json
{
  "record_type": "router_decision",
  "turn_id": "turn_…",
  "router_backend": "fixture_keywords|fallback_keywords",
  "classified_intent": "...",
  "route": "planner|conversation|operational|provider",
  "confidence": 0.0,
  "counterfactual_routes": [],
  "evidence": {"matched_text": "...", "legacy_intent": "..."}
}
```

`trace_id` is on the replay-record wrapper, not inside the payload. `live_codex_intent` becomes a `router_backend` value only when the Codex conversation output schema gains an `intent` field (target). Known data caveat until the code fix lands: `classified_intent`/`route` come from the legacy classifier while `confidence` comes from the new keyword router.

Test cases — **current verified behavior vs target**:

| Phrase | Current (verified) | Target |
|---|---|---|
| "Make tomorrow less chaotic." | calendar_goal → planner ✅ | same |
| "Unblock my account." | calendar_goal → planner ❌ (substring "block" matches calendar terms) | non_calendar → conversation |
| "Move my client prep earlier." | calendar_goal → planner ✅ | same |
| "Why did you deny that?" | non_calendar → conversation ❌ ("deny" is not in the operational term set; "denial"/"denied" are) | operational → denial explanation |
| "Undo the calendar change." | mixed_calendar_operational → planner (undo receipt attached to the plan turn) | operational → undo path |
| "Do I have enough prep time before the renewal call?" | calendar_goal → planner ✅ | same |

Keep the two ❌ rows as **expected-fail regression tests**: they document real misroutes ("Unblock my account" accidentally triggers calendar planning; a natural denial question misses the operational path). When the model router lands, these flip to their target values — that flip is the acceptance test for model routing. In the meantime, "explain the denial" routes operationally today and can serve as the working denial-explanation phrase.

Pass criteria:

```text
Calendar goals route to planner/frontier generation.
Bare undo requests ("undo", "undo it", "rollback") route to the undo path.
Every routed turn has a router_decision replay record with a trace_id on the wrapper.
Every frontier generated from a turn shares that turn's trace_id.
Expected-fail cases are tracked and flip to pass when the model router lands.
```

This makes routing part of the ML system instead of hidden pre-ML control flow.

---

## 8. Codex tool-path test

**Status: Runnable now — replay shows 1:1 tool_call/receipt parity in current runs.**

Goal: prove Codex carries model candidates into executable app operations.

For a fixed goal, require this tool sequence or an explicitly justified variant:

```text
inspect_week
generate_candidate_frontier
compare_candidates
simulate_action_program
stage_action_packet or request_commit
```

For each tool call/receipt, validate:

```text
tool_call_id
tool_name
input
requested_authority_tier
authority_grant_id where needed
correlation_id
status
output
swift_receipt_id when Swift was touched
replay_record_id
```

Pass criteria:

```text
Every Codex tool call has a matching receipt.
Every Swift-touching tool has a Swift receipt or a denial.
Every denial is replay-visible.
No embedded AuthorityGrant object is accepted as authority.
Codex cannot directly write provider state.
```

The current docs define Codex as the executive that inspects, compares, stages, repairs, and requests typed operations while Swift validates writes and authority.

---

## 9. ActionEnvelope / acting-aware ML test

**Status: Partial — the envelope (v2 shape, v1 marker retained) attaches on Codex receipt paths and `envelope_transition` records exist, but the envelope is not yet the spine of every mutation. Full coverage lands with the ActionLifecycle extraction.**

Goal: connect ML candidates to machine-acting consequences.

For every staged/committed/denied/undone candidate, require one envelope:

```json
{
  "envelope_id": "...",
  "trace_id": "...",
  "candidate_id": "...",
  "observation_fingerprint": "...",
  "runtime_mode": "...",
  "backends": {
    "policy": "...",
    "codex": "...",
    "kernel": "...",
    "provider": "..."
  },
  "authority": {
    "grant_id": "...",
    "tier": 3,
    "scopes": []
  },
  "lifecycle": [],
  "provider": {
    "rollback_state": "verified|pending|failed|impossible|unsupported"
  },
  "reward": {},
  "replay_record_ids": []
}
```

Implementation note: `ActionEnvelope.backends` is an open `dict[str, str]` — the keys above are the convention, not enforced by the dataclass. The gate should assert the four keys are present.

Pass criteria (I-numbers reference step 10's invariant checks):

```text
Every mutation has exactly one envelope.                    (I1 — needs-build)
Every commit has rollback_state; it is never absent.        (I2 — implemented)
Every social mutation has scope provenance.                 (enforced by grants)
Every stale-observation commit is refreshed or denied.      (I4 — needs-build)
Every undo consumes a prior rollback handle exactly once.   (I6 — implemented)
Every envelope transition is replayed.                      (partially — receipt paths only)
```

This tests the ML system's consequences, not just its recommendations. The target framework explicitly says machine acting is measured by whether every mutation carries one ActionEnvelope with verified rollback state.

---

## 10. Replay completeness test

**Status: Complete for implemented replay invariants — I2, I6, R1, R2, R3, R4, and R5 are implemented in `environment/invariants.py`, covered by `tests/test_invariants.py`, and exercised by `scripts/check_invariants.py`.**

Goal: prove training data is complete enough to learn from.

For every user goal / episode, the replay should contain:

```text
router_decision
decision/frontier record
model_generation_rejection records, if any (live path only)
codex_tool_call records
codex_tool_receipt records
receipt records
reward records, if feedback exists or self-play ran
adversary_finding records, if self-play ran
self_play_episode records, if self-play ran
envelope_transition records
```

Replay invariants — implementation status:

```text
[implemented]  I2: rollback_state present and valid on commit/verify/undo transitions
[implemented]  I6: no rollback handle consumed twice
[implemented]  R1: all records have record_id
[implemented]  R2: all records have trace_id
[implemented]  R3: causal_parent_id references an existing earlier record
[implemented]  R4: receipt records carry candidate_id
[implemented]  R5: reward records reference their receipt (causal parent or payload)
[implemented]  tuning output points back to replay records through bias_evidence
```

Landed in `src/calendar_pilot/environment/invariants.py`:

```python
def check_r1_record_ids(records: list[dict[str, Any]]) -> list[Violation]:
    return [Violation("R1", str(i), "missing record_id")
            for i, rec in enumerate(records) if not rec.get("record_id")]


def check_r2_trace_ids(records: list[dict[str, Any]]) -> list[Violation]:
    return [Violation("R2", rec.get("record_id", str(i)), "missing trace_id")
            for i, rec in enumerate(records) if not rec.get("trace_id")]


def check_r3_causal_parents_exist(records: list[dict[str, Any]]) -> list[Violation]:
    seen: set[str] = set()
    out: list[Violation] = []
    for rec in records:
        parent = rec.get("causal_parent_id")
        if parent and parent not in seen:
            out.append(Violation("R3", rec.get("record_id", "?"), f"unknown parent: {parent}"))
        seen.add(str(rec.get("record_id", "")))
    return out


def check_r4_receipts_carry_candidate(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in records:
        if rec.get("record_type") != "receipt":
            continue
        payload = rec.get("payload", {})
        candidate_id = (payload.get("candidate", {}) or {}).get("candidate_id") or (
            payload.get("receipt", {}) or {}).get("candidate_id")
        if not candidate_id:
            out.append(Violation("R4", rec.get("record_id", "?"), "receipt without candidate_id"))
    return out


def check_r5_rewards_reference_receipts(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in records:
        if rec.get("record_type") != "reward":
            continue
        payload = rec.get("payload", {})
        if not rec.get("causal_parent_id") and not payload.get("receipt"):
            out.append(Violation("R5", rec.get("record_id", "?"), "reward without receipt linkage"))
    return out


CHECKS.update({
    "R1": check_r1_record_ids,
    "R2": check_r2_trace_ids,
    "R3": check_r3_causal_parents_exist,
    "R4": check_r4_receipts_carry_candidate,
    "R5": check_r5_rewards_reference_receipts,
})
```

And landed in `tests/test_invariants.py`:

```python
import unittest

from calendar_pilot.environment.invariants import check_replay


def _rec(record_type, record_id, trace_id="t1", parent=None, payload=None):
    return {"record_type": record_type, "record_id": record_id, "trace_id": trace_id,
            "causal_parent_id": parent, "payload": payload or {}}


class InvariantTests(unittest.TestCase):
    def test_clean_replay_passes(self):
        records = [
            _rec("envelope_transition", "e1", payload={
                "envelope": {"envelope_id": "env1", "current_state": "commit",
                             "provider": {"rollback_state": "verified"}}}),
            _rec("receipt", "r1", parent="e1", payload={
                "receipt": {"sync_status": "reverted", "rollback_handle_id": "u1",
                            "candidate_id": "c1"}}),
        ]
        self.assertEqual(check_replay(records), [])

    def test_missing_rollback_state_violates_i2(self):
        records = [_rec("envelope_transition", "e1", payload={
            "envelope": {"envelope_id": "env1", "current_state": "commit", "provider": {}}})]
        self.assertIn("I2", [v.invariant_id for v in check_replay(records)])

    def test_double_undo_violates_i6(self):
        undo = {"receipt": {"sync_status": "reverted", "rollback_handle_id": "u1", "candidate_id": "c1"}}
        records = [_rec("receipt", "r1", payload=undo), _rec("receipt", "r2", payload=undo)]
        self.assertIn("I6", [v.invariant_id for v in check_replay(records)])

    def test_unknown_causal_parent_violates_r3(self):
        records = [_rec("decision", "d1", parent="ghost")]
        self.assertIn("R3", [v.invariant_id for v in check_replay(records)])

    def test_orphan_reward_violates_r5(self):
        records = [_rec("reward", "w1")]
        self.assertIn("R5", [v.invariant_id for v in check_replay(records)])
```

Run:

```bash
PYTHONPATH=src python3 scripts/check_invariants.py \
  --replay runs/<run_id>/replay.jsonl \
  --out runs/<run_id>/invariant_report.json
# or: make check-invariants
```

(exits 1 on violations; `--out` writes the report artifact)

Training-data note (verified): `training_table()` rows carry `candidate_id, intent, intent_raw, intent_matched_by, expected_reward, observed_reward, reward_provenance, sync_status, denied_reason, right_moment_decision, failure_heads, trace_id, record_id, causal_parent_id` — but **not** `observation_fingerprint`. Recommendation: add it to the row (it exists in replay payloads), so M2 becomes checkable at the training table.

Pass criteria:

```text
No invariant violations.
No orphan reward events.
No orphan receipts.
No missing observation fingerprints in replay payloads or training rows.
No missing model provenance.
```

The framework treats replay as the trajectory record and invariant checking as trace monitoring.

---

## 11. Offline tuning test

**Status: Complete for current reducer — canonical keys, frontier effect, and `bias_evidence` are emitted by `scripts/train_offline_policy.py`; live replay -> offline tuning -> next NIM generation passed in this run.**

Goal: prove replay changes the next policy frontier.

Generate replay:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --self-play 5 \
  --replay-out runs/tuning_test/replay.jsonl \
  --commit
```

Train:

```bash
PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay runs/tuning_test/replay.jsonl \
  --out runs/tuning_test/offline_policy_report.json \
  --tuning-out runs/tuning_test/policy_tuning.json
```

Regenerate frontier twice (deterministic — see step 12's script):

```text
A: no tuning
B: with policy_tuning.json
```

Compare:

```text
leader candidate
top-3 ordering
expected_reward deltas
intent_reward_bias
failure_penalties
denied_intents
right_moment decisions
```

Pass criteria:

```text
Tuning keys are canonical intents (the reducer normalizes intent_raw → canonical).
At least one score/ranking/right-moment decision changes when replay contains signal.
Changes are directionally correct: undo/regret lowers similar future candidates;
  useful/accepted increases them.
No one-off prose intent keys are created.
Tuning cites supporting replay records via bias_evidence.
```

The current framework defines ML progress as tuning that changes the next frontier, with canonical-intent residuals accumulating across runs.

---

## 12. A/B frontier regression test

**Status: Complete — `scripts/run_frontier_diff.py` is landed and wired into `make frontier-diff` and `make ml-ladder`.**

Goal: prevent tuning from making the model worse in obvious ways.

Landed harness — `scripts/run_frontier_diff.py` (zero-dependency, fixture-deterministic):

```python
#!/usr/bin/env python3
"""Deterministic A/B frontier diff: heuristic policy with vs without PolicyTuning."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy  # noqa: E402
from calendar_pilot.types import PolicyTuning, RawCalendarObservation, UserBiography  # noqa: E402


def frontier(policy: DiffusionGemmaPolicy, observation, biography) -> list[dict]:
    rows = []
    for c in policy.generate_candidates(observation, biography):
        rows.append({
            "candidate_id": c.candidate_id,
            "intent": c.intent,
            "expected_reward": round(float(c.expected_reward), 4),
            "predicted_regret": round(float(c.predicted_regret), 4),
            "predicted_social_risk": round(float(c.predicted_social_risk), 4),
            "right_moment_decision": getattr(c.right_moment_decision, "value", str(c.right_moment_decision)),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", default="data/sample_calendar.json")
    parser.add_argument("--profile", default="data/sample_profile.json")
    parser.add_argument("--tuning", required=True, help="policy_tuning.json from train_offline_policy.py")
    parser.add_argument("--out", default="runs/frontier_diff/frontier_diff.json")
    args = parser.parse_args()

    observation = RawCalendarObservation.from_dict(json.loads(Path(args.observation).read_text()))
    biography = UserBiography.from_dict(json.loads(Path(args.profile).read_text()))
    tuning = PolicyTuning.from_dict(json.loads(Path(args.tuning).read_text()))

    untuned = frontier(DiffusionGemmaPolicy(), observation, biography)
    tuned = frontier(DiffusionGemmaPolicy(policy_tuning=tuning), observation, biography)

    base = {c["candidate_id"]: c for c in untuned}
    diff = {
        "tuning_id": tuning.tuning_id,
        "untuned_leader": untuned[0]["candidate_id"] if untuned else None,
        "tuned_leader": tuned[0]["candidate_id"] if tuned else None,
        "leader_changed": bool(untuned and tuned and untuned[0]["candidate_id"] != tuned[0]["candidate_id"]),
        "top3_untuned": [c["candidate_id"] for c in untuned[:3]],
        "top3_tuned": [c["candidate_id"] for c in tuned[:3]],
        "per_candidate_delta": {
            c["candidate_id"]: round(c["expected_reward"] - base[c["candidate_id"]]["expected_reward"], 4)
            for c in tuned if c["candidate_id"] in base
        },
        "avg_predicted_regret": {"untuned": _avg(untuned, "predicted_regret"), "tuned": _avg(tuned, "predicted_regret")},
        "avg_predicted_social_risk": {"untuned": _avg(untuned, "predicted_social_risk"), "tuned": _avg(tuned, "predicted_social_risk")},
        "frontier_untuned": untuned,
        "frontier_tuned": tuned,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(diff, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: diff[k] for k in ("tuning_id", "untuned_leader", "tuned_leader", "leader_changed")}, indent=2))


def _avg(rows: list[dict], key: str) -> float:
    return round(sum(r[key] for r in rows) / max(1, len(rows)), 4)


if __name__ == "__main__":
    main()
```

For a fixed fixture set, compare:

```text
untuned policy
latest tuned policy
previous tuned policy
```

Metrics:

```text
top candidate intent
top candidate expected_reward
top-3 overlap
do_nothing availability
average predicted_regret
average predicted_social_risk
average predicted_interruption_cost
OTHER intent rate
model rejection rate (live runs only)
```

Pass criteria:

```text
Top candidate changes only when supported by replay/adversary evidence.
Predicted regret does not rise globally without compensating utility.
Social-risk-heavy candidates do not dominate private-write candidates without authority reason.
OTHER rate does not rise.
Rejected-candidate rate does not rise sharply.
```

Artifact: `runs/<run_id>/frontier_diff.json`.

---

## 13. Self-play laboratory test

**Status: Partial — backend policies, grant-issuance enforcement, CLI backend selection, and goal-forwarding exist; self-play still calls `kernel.authorize_and_materialize` directly in all backends (ActionLifecycle deferred), Swift-side sandbox enforcement is deferred, and no scenario DSL exists.**

Goal: test the policy under adversarial but structured scenarios.

Run self-play in layers:

```text
Layer 1: stub_fast                      (default; no env flag)
Layer 2: swift_ipc_deterministic        (no env flag)
Layer 3: swift_ipc_eventkit_sandbox     (requires CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1)
Layer 4: production_shadow              (requires CALENDAR_PILOT_SELFPLAY_SHADOW=1)
```

Verified grant policy per backend:

```text
stub_fast                  → self_issued
swift_ipc_deterministic    → kernel_issued_sandbox (adds commit_selfplay_sandbox scope,
                              provenance "selfplay_lab:<backend>:episode:N")
swift_ipc_eventkit_sandbox → kernel_issued_sandbox
production_shadow          → read_only (no grant, observation only)
```

Fail-safe (verified): if a backend requires an env flag and it is missing or not in `{1, true, TRUE, yes}`, authority_tier is forced to 0 and no grant is issued — the episode degrades to read-only rather than acting.

Backend selection (no CLI flag exists — the demo always uses `stub_fast`; select in code):

```python
from calendar_pilot.diffusiongemma import SelfPlayRunner
from calendar_pilot.environment.selfplay_backends import SelfPlayActionBackend
from calendar_pilot.replay import ReplayBuffer

replay = ReplayBuffer()
runner = SelfPlayRunner(replay=replay,
                        action_backend=SelfPlayActionBackend.SWIFT_IPC_DETERMINISTIC)
metrics = runner.run(observation, biography, episodes=10)
```

`--self-play-backend` is now available on the demo CLI.

Scenarios — **these are test cases to write, not an existing DSL.** The only adversaries that exist today, with their verified failure-mode labels:

```text
ConflictAdversary     → social_conflict
FatigueAdversary      → notification_fatigue
RegretAdversary       → undo_regret
EngagementAdversary   → engagement_over_utility
(automatic)           → denied_actuation  — added whenever Swift denies, with reward −1.0
```

Target scenario set (build after the ActionLifecycle extraction so scenarios compose against the real acting path):

```text
external_call_no_prep_high_fatigue
dense_day_with_flexible_hold
social_conflict_move_meeting
stale_observation_after_provider_refresh
high_engagement_low_utility
undo_regret_after_auto_write
expired_authority_grant
```

Replay per episode (verified): `decision` records (one per top-k candidate), one `receipt`, one `reward`, one `self_play_episode`, and one `adversary_finding` per finding.

Metrics:

```text
average reward
adversarial delta
accept/reject/undo/ignore counts
failure mode counts (including denied_actuation)
denial rate
rollback coverage
frontier valid/rejected counts
canonical intent distribution
```

Pass criteria — split by availability:

```text
[now]    Self-play emits replay (all five record types above).
[now]    Missing env flags degrade to read-only instead of acting.
[now]    Adversary findings map to tuning features (failure_penalties).
[now]    Repeated failure modes lower future policy preference for that intent/action class.
[target] Self-play executes through ActionLifecycle in non-stub backends
         (today it calls kernel.authorize_and_materialize directly in ALL backends).
[target] Sandbox backends cannot mutate outside sandbox provider/calendar
         (requires Swift-side allowlist — deferred).
```

---

## 14. Live model soak test

**Status: Target — no soak harness exists. Latency and schema-retry metadata are now captured; drop HTTP retry count until HTTP retry/backoff is implemented (`http_retry: "none"` today; only schema-retry exists).**

Goal: measure reliability over repeated live generations.

Run a batch of, for example, 50 goals over varied observations:

```text
10 prep/block goals
10 buffer goals
10 reschedule/conflict goals
10 notification/digest goals
10 ambiguous/non-calendar goals
```

Collect (post-instrumentation):

```text
generation success rate
schema-valid rate
rejection rate
duplicate ID rate
OTHER rate
latency p50/p95            (aggregate request_latency_ms from step 5 metadata)
HTTP failure rate          (requires soak-level error aggregation)
schema_retry count         (captured today)
empty-frontier count
average top expected_reward
average predicted_regret
average predicted_social_risk
```

Pass criteria:

```text
No empty frontier unless route is non-calendar.
Schema-valid rate above threshold.
OTHER rate below threshold.
Latency acceptable for dogfood.
No systematic collapse into one intent.
No repeated duplicate candidate IDs.
```

This is where you detect whether the live model is actually producing a useful frontier distribution, not just occasional good demos. Recommended repo change alongside this step: implement HTTP retry/backoff for 429/5xx in `live.py` (hand-rolled, zero-dependency) — the earlier quota incident surfaced as a schema failure precisely because there is no retry/error taxonomy at the transport layer.

---

## 15. Live Codex + live NIM integration test

**Status: Partial — live Codex E2E and live DiffusionGemma E2E passed independently with credentials; combined live Codex + live NIM under one production/auto run remains target work.**

Goal: test the executive loop, not just the policy.

Run in `production` or `auto` (composes every healthy live backend), but use deterministic or sandbox provider first:

```text
live Codex           (CODEX_ACCESS_TOKEN or Codex auth cache)
live DiffusionGemma/NIM
Swift IPC kernel
deterministic provider or EventKit sandbox
```

Test prompts:

```text
"Make tomorrow less chaotic."
"Create prep before my client call."
"Move flexible admin away from my focus block."
"Explain the denial."            (routes operationally today; see step 7)
"Undo the last calendar change."
```

Pass criteria:

```text
Codex reaches model.
NIM reaches model.
Codex tool sequence is replayed.
NIM frontier is replayed.
Swift receipt exists for simulate/stage/commit/undo.
Denied actions are explained and replayed.
Undo works once and cannot replay twice (I6).
```

---

## 16. Provider-sandbox acting test

**Status: Target — blocked by two deferrals: Swift-side sandbox allowlist enforcement and provider-backed self-play execution. Manual EventKit probes (create/rollback with external IDs and idempotency) are proven by prior dogfood; the *bounded* sandbox is what's missing.**

Goal: verify that model-generated recommendations can safely reach real calendar I/O in a bounded environment.

Preconditions before this step is meaningful:

```text
1. Swift EventKit bridge enforces a sandbox_calendar_id allowlist (deferred item —
   mutations targeting any other calendar are rejected in Swift, below Python).
2. Self-play/commit path runs through ActionLifecycle so script, UI, and
   self-play exercise the same acting spine.
```

Use a dedicated sandbox calendar, for example:

```text
CalendarPilot SelfPlay
```

Test create/rollback:

```text
create focus block
verify external_event_id
verify idempotency_key
rollback
verify event removed/restored
repeat same idempotency key
verify no duplicate event
```

Test move/rollback:

```text
seed sandbox event
move event
verify new time
rollback
verify original time
```

Pass criteria:

```text
All provider writes target sandbox calendar only (Swift-enforced, not Python-promised).
All commits return external IDs.
All rollback paths return rollback_state.
Idempotent replay does not duplicate creates.
Provider errors become receipts/replay records.
```

This should run only after the deterministic-provider acting tests pass.

---

## 17. Human dogfood protocol

**Status: Partial — all artifacts are now generatable (commands below); no automated daily orchestration yet.**

Goal: collect real recommendation signal without waiting for perfect architecture.

For each daily-driver session, record:

```text
number of user goals
number of generated candidates
number of staged candidates
number of committed candidates
number of denied candidates
number of undos
explicit useful/wrong/not needed
ignored recommendations
time-to-accept
post-event survival
downstream conflict
```

Required daily artifacts, with the command that produces each:

```text
session_state.json / latest_session.json   (written by the session automatically)
runtime_report                             (GET /api/health, or launch manifest "health")
replay.jsonl                               (session run dir; append-first)
offline_policy_report.json + policy_tuning.json
                                           (scripts/train_offline_policy.py)
frontier_diff.json                         (scripts/run_frontier_diff.py — step 12)
invariant_report.json                      (scripts/check_invariants.py --out …)
scorecard.json + taxonomy health           (scripts/make_scorecard.py — step 19)
```

Daily pass criteria:

```text
No invariant violations.
No corrupted replay/state.
No uncited/untraceable tuning changes (once bias_evidence lands).
No provider mutation without envelope.
No missing rollback state on committed action.
No rising OTHER rate.
```

This is where the ML system starts producing the signal it needs.

---

## 18. Promotion gates

Use these gates to decide when to move up autonomy/runtime levels.

### Gate A — Fixture ML  **(passable now)**

```text
Contract-valid candidates: 100%
Replay complete: yes
Tuning changes next frontier: yes (verify with run_frontier_diff.py)
Invariant violations: 0
```

### Gate B — Live NIM ML  **(passable after step-5 instrumentation)**

```text
Valid frontier rate above threshold
Rejected outputs retained
OTHER rate below threshold
Latency acceptable
No empty frontier on calendar goals
```

### Gate C — Live Codex executive  **(passable now, credential-gated)**

```text
Correct routing (expected-fail cases from step 7 tracked, not counted as failures)
Tool calls/receipts replayed
Denials explained
No missing trace_id/causal_parent_id
```

### Gate D — Swift IPC acting  **(blocked: golden vectors deferred)**

```text
All commits have receipts
All commits have rollback_state
Undo consumes handle once
[blocked] Swift stub and Swift IPC agree on golden vectors
          (contracts/testdata/ + KernelServer roundtrip command are deferred;
           until they land, this criterion is aspirational — string-grep parity
           tests are the only cross-runtime check)
```

### Gate E — Provider sandbox  **(blocked: Swift allowlist deferred)**

```text
External IDs present
Idempotency works
Rollback verified
[blocked] Sandbox allowlist enforced (Swift-side enforcement is deferred)
No mutation outside sandbox
```

### Gate F — Recommendation dogfood

```text
Daily artifacts generated
Tuning is causally traceable
Human feedback produces measurable frontier changes
Self-play adversary failures map into tuning
No evidence corruption
```

---

## 19. Scorecard template

**Status: Complete — `scripts/make_scorecard.py` is landed and wired into `make scorecard` and `make ml-ladder`.**

Landed harness — `scripts/make_scorecard.py`:

```python
#!/usr/bin/env python3
"""One-page ML scorecard from a run directory's artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.environment.invariants import check_replay  # noqa: E402
from calendar_pilot.environment.taxonomy import taxonomy_health  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="directory containing replay.jsonl and artifacts")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    records = load_jsonl(run_dir / "replay.jsonl")
    tuning = load_json(run_dir / "policy_tuning.json")
    diff = load_json(run_dir / "frontier_diff.json")

    by_type: dict[str, int] = {}
    for rec in records:
        by_type[rec.get("record_type", "unknown")] = by_type.get(rec.get("record_type", "unknown"), 0) + 1

    candidates = [rec.get("payload", {}).get("candidate", {})
                  for rec in records if rec.get("record_type") == "decision"]
    receipts = [rec.get("payload", {}).get("receipt", {})
                for rec in records if rec.get("record_type") == "receipt"]
    findings: dict[str, int] = {}
    for rec in records:
        if rec.get("record_type") == "adversary_finding":
            label = rec.get("payload", {}).get("failure_mode", "unknown")
            findings[label] = findings.get(label, 0) + 1

    violations = check_replay(records)
    health = taxonomy_health([c for c in candidates if c])
    prose_keys = [k for k in (tuning.get("intent_reward_bias") or {}) if " " in k]

    scorecard = {
        "run_id": args.run_id or run_dir.name,
        "record_counts": by_type,
        "frontier": {
            "decisions": len(candidates),
            "other_intent_rate": health["other_rate"],
            "intent_matched_by": health["matched_by"],
        },
        "acting": {
            "receipts": len(receipts),
            "committed": sum(1 for r in receipts if r.get("sync_status") == "materialized"),
            "denied": sum(1 for r in receipts if r.get("denied_reason")),
            "reverted": sum(1 for r in receipts if r.get("sync_status") == "reverted"),
        },
        "learning": {
            "replay_records": len(records),
            "tuning_generated": bool(tuning),
            "tuning_id": tuning.get("tuning_id"),
            "leader_changed": diff.get("leader_changed"),
            "canonical_intent_keys_only": not prose_keys,
            "prose_keys": prose_keys,
        },
        "self_play": {
            "episodes": by_type.get("self_play_episode", 0),
            "failure_modes": findings,
        },
        "invariants": {"violations": [v.__dict__ for v in violations]},
        "decision": "hold" if violations or prose_keys else "promote",
    }
    text = json.dumps(scorecard, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
```

For every test run, this produces the one-page summary (original template shape preserved; `decision` is derived, not hand-typed):

```json
{
  "run_id": "ml_test_2026_07_02_001",
  "record_counts": {"decision": 42, "receipt": 12, "reward": 9, "...": 0},
  "frontier": {"decisions": 42, "other_intent_rate": 0.04, "intent_matched_by": {"keyword": 30, "exact": 12}},
  "acting": {"receipts": 12, "committed": 2, "denied": 1, "reverted": 1},
  "learning": {"replay_records": 128, "tuning_generated": true, "leader_changed": true,
               "canonical_intent_keys_only": true},
  "self_play": {"episodes": 20, "failure_modes": {"notification_fatigue": 3, "undo_regret": 1}},
  "invariants": {"violations": []},
  "decision": "promote"
}
```

---

## 20. Recommended first run sequence

**Status: Complete — `make ml-ladder` runs the deterministic ladder end to end; the live-NIM loop is covered by `make replay-offline-tuning-loop` and passed in this run.**

Start with this exact ladder (fixtures/stubs only — no credentials, no network):

```bash
# 1. Unit + Swift baseline
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel

# 2. Deterministic replay generation (pin the goal for comparability)
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --goal "Make next week less chaotic" \
  --self-play 5 \
  --replay-out runs/ml_test_001/replay.jsonl \
  --commit

# 3. Invariant check (writes the report artifact)
PYTHONPATH=src python3 scripts/check_invariants.py \
  --replay runs/ml_test_001/replay.jsonl \
  --out runs/ml_test_001/invariant_report.json

# 4. Offline tuning
PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay runs/ml_test_001/replay.jsonl \
  --out runs/ml_test_001/offline_policy_report.json \
  --tuning-out runs/ml_test_001/policy_tuning.json

# 5. Deterministic frontier diff (replaces the live-NIM loop that was here before)
PYTHONPATH=src python3 scripts/run_frontier_diff.py \
  --tuning runs/ml_test_001/policy_tuning.json \
  --out runs/ml_test_001/frontier_diff.json

# 6. Scorecard
PYTHONPATH=src python3 scripts/make_scorecard.py \
  --run-dir runs/ml_test_001 \
  --out runs/ml_test_001/scorecard.json
```

Then repeat with the **live ladder** (each layer credential-gated; stop at the first layer that fails to produce complete evidence):

```text
live_diffusiongemma            (make live-diffusiongemma-e2e; needs NIM key)
replay → live tuning → next NIM generation
                               (make replay-offline-tuning-loop — REQUIRES live NIM;
                                artifacts land in runs/replay_offline_tuning_loop/artifacts/)
live_codex + live_diffusiongemma
swift_ipc_deterministic self-play (in code: action_backend=SWIFT_IPC_DETERMINISTIC)
eventkit sandbox               (blocked until Swift allowlist lands — step 16)
```

---

## Bottom line

Test the ML system as a **closed loop**, not as a model call:

```text
generation quality
→ canonical intent accumulation
→ reward/right-moment behavior
→ Codex tool path
→ Swift acting consequence
→ replay completeness
→ offline tuning
→ next-frontier change
→ self-play pressure
→ dogfood signal
```

The minimum viable ML test is not "the model produced a plausible recommendation." It is: **the model produced typed candidates, the app acted or denied through the same spine, replay captured the consequences, tuning changed the next frontier, and invariants stayed clean.**
