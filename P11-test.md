According to a document from July 3, 2026, `thickening-the-lab.md` defines the next CalendarPilot phase as a trajectory-grade system: DiffusionGemma/NIM proposes typed futures, Codex operates typed tools, Swift owns calendar reality and authority, and replay/self-play/tuning close the loop. The central test object is therefore not “the model” or “the UI,” but the trajectory: `TraceEvent + ActionEnvelope + ReplayRecord + Scorecard`.  

# Working Document: CalendarPilot P11 Lab Test Framework

**Owner:** next implementation engineer
**Scope:** Test the P11 “thickening the lab” implementation for machine learning, machine acting, and self-play.
**Operating stance:** Alan Kay for object/media clarity, Claire Tomlin for control barriers and reachable bad states, John Schulman for trajectory distribution, reward integrity, baselines, and variance.

## 0. Prime directive

Do not ask, “Did the tests pass?” Ask:

**Can we prove that the system generated typed candidate futures, acted only through bounded authority, recorded the full trajectory, evaluated honestly, improved against the incumbent, and preserved rollback/provider invariants?**

P11’s design rules make this explicit: every model output must be typed/rejected/repaired visibly; every mutation must have an `ActionEnvelope` with meaningful rollback state; every policy update must cite replay and beat the incumbent; every provider write must be idempotent, rollback-aware, verified, and rate-bounded; every simulator must declare its version and must not grade the policy on the policy’s own beliefs. 

---

# Evidence directory convention

Create one evidence bundle per testing pass.

```bash
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-p11"
mkdir -p runs/p11_evidence/$RUN_ID
git rev-parse HEAD > runs/p11_evidence/$RUN_ID/git_sha.txt
git status --short > runs/p11_evidence/$RUN_ID/git_status.txt
```

Every step below should write or copy evidence into:

```text
runs/p11_evidence/<RUN_ID>/
```

Minimum final bundle:

```text
git_sha.txt
git_status.txt
baseline_tests/
contracts/
invariants/
frontier_quality/
trajectory_replay/
self_play/
provider_sandbox/
learning_loop/
promotion/
frontend/
progress_log.md
decision_log.md
```

---

# 1. Baseline smoke: prove the repo still breathes

## Purpose

Establish that the implementation did not break the existing Python, Swift, replay, contract, browser, or lab entry points before testing P11-specific behavior.

The repo exposes Makefile access points for Python tests, Swift tests, invariant checks, evidence bundles, browser/app dogfood, live e2e, replay/offline tuning, frontier diff, scorecard, and lab commands. 

## Commands

```bash
make py-test        | tee runs/p11_evidence/$RUN_ID/baseline_tests/py-test.log
make swift-test     | tee runs/p11_evidence/$RUN_ID/baseline_tests/swift-test.log
make check-invariants | tee runs/p11_evidence/$RUN_ID/baseline_tests/check-invariants.log
make contract-vectors | tee runs/p11_evidence/$RUN_ID/baseline_tests/contract-vectors.log
make frontier-diff  | tee runs/p11_evidence/$RUN_ID/baseline_tests/frontier-diff.log
make scorecard      | tee runs/p11_evidence/$RUN_ID/baseline_tests/scorecard.log
```

## Acceptance

* Python tests pass.
* Swift tests pass.
* Golden replay invariant check passes.
* Contract vectors pass.
* `runs/frontier_diff.json` exists.
* `runs/ml_scorecard.json` exists.
* Any skipped test is documented with reason, not ignored.

## Record progress

```md
## Step 1 Baseline Smoke

Date:
Engineer:
Git SHA:
Python tests:
Swift tests:
Contract vectors:
Invariant check:
Frontier diff artifact:
Scorecard artifact:
Failures:
Follow-up:
Decision:
```

---

# 2. Contract freeze: prove no unversioned shape exists

## Purpose

P11 says long-term debt is contract drift between model output, Codex tools, Swift receipts, provider writes, replay rows, and lab metrics. The canonical contracts include the existing seven schemas plus `ActionEnvelope`, `ReplayRecord`, `PolicyTuning`, `FrontierDiff`, `LabReport`, and `Scorecard`; Python/Swift types are checked against schemas, not generated from them. 

## Tests to run or add

Check these files exist and are referenced from `contracts/VERSIONS.json`:

```text
contracts/action_envelope.schema.json
contracts/replay_record.schema.json
contracts/policy_tuning.schema.json
contracts/frontier_diff.schema.json
contracts/lab_report.schema.json
contracts/scorecard.schema.json
contracts/VERSIONS.json
```

Add or verify tests:

```text
tests/test_contract_parity.py
tests/test_contract_vectors.py
tests/test_action_envelope_contract.py
tests/test_replay_record_contract.py
```

## Required assertions

* Every replay row has `record_schema_version`.
* Every `ActionEnvelope` has `envelope_version`.
* Golden vectors cover Python stub, Swift kernel, and Swift IPC for the mutation path.
* A deliberately broken vector fails CI.
* No model/tool/provider/UI path emits an unversioned object.

## Suggested negative test

Create a fixture replay row without `record_schema_version`; `scripts/check_invariants.py` must fail and name the violation.

## Record progress

```md
## Step 2 Contract Freeze

Schemas present:
VERSIONS.json updated:
Golden vectors:
Broken-vector failure verified:
Unversioned shape scan:
Failures:
Decision:
```

---

# 3. Trajectory spine: prove every action is an inspectable transition

## Purpose

The P11 north-star map says `ActionLifecycle` owns `prepare → simulate → stage → commit → verify → reward → undo`, `ReplayJournal` becomes the append-first trajectory store, and the new implementation should use the strangler rule: wrappers first, replacement later, verified by golden replay and fixture frontier equality. 

## Tests to run or add

Add or verify:

```text
tests/test_action_lifecycle_trajectory.py
tests/test_action_envelope_rollback_state.py
tests/test_replay_causal_chain.py
tests/test_replay_compaction_keep_list.py
```

## Required assertions

For a normal private reversible write:

* `prepare` transition exists.
* `simulate` transition exists.
* `stage` transition exists or is intentionally skipped with reason.
* `commit` transition exists.
* `verify` transition exists or is denied with provider-truth reason.
* `reward` transition exists when feedback/reward is recorded.
* `undo` transition exists when rollback is requested.
* Every transition has `trace_id`, `causal_parent_id`, and timestamp.
* `/api/trace/{trace_id}` returns the complete chain.

For rollback adequacy:

* Committed materialized writes cannot have `rollback_state: "unsupported"`.
* Committed reversible writes must have `rollback_state ∈ {pending, verified}`.
* Irreversible actions may use `impossible` only when candidate reversibility is `none`.

P11 explicitly says I2 by itself is inadequate because `unsupported` rollback state could pass for a committed write; I2′ must catch that. 

## Commands

```bash
PYTHONPATH=src python3 -m unittest tests/test_action_lifecycle_trajectory.py -v \
  | tee runs/p11_evidence/$RUN_ID/trajectory_replay/action_lifecycle.log

PYTHONPATH=src python3 scripts/check_invariants.py \
  --replay tests/fixtures/replay_golden.jsonl \
  --out runs/p11_evidence/$RUN_ID/invariants/golden_invariants.json
```

## Record progress

```md
## Step 3 Trajectory Spine

Lifecycle coverage:
Rollback adequacy:
Trace endpoint:
Compaction keep-list:
Golden replay result:
Synthetic violation result:
Failures:
Decision:
```

---

# 4. Replay journal: prove learning/debugging share one source of truth

## Purpose

P11 states: replay is the trajectory distribution; if it is incomplete, training is contaminated. Existing record types must be extended with `frontier_generation`, `provider_transaction`, `tuning_reduction`, and `artifact_ref`; big artifacts enter by reference, not by value. 

## Tests to run or add

```text
tests/test_replay_record_versions.py
tests/test_replay_new_record_types.py
tests/test_artifact_ref_rows.py
tests/test_tuning_reduction_rows.py
tests/test_provider_transaction_rows.py
```

## Required assertions

* `frontier_generation` emitted once per frontier generation call.
* `provider_transaction` emitted around provider `preview`, `commit`, `verify`, and `rollback`.
* `tuning_reduction` emitted by `train_offline_policy.py`.
* `artifact_ref` emitted by scripts writing `frontier_diff`, `scorecard`, `lab_report`, or promotion records.
* Every replay row has `trace_id` and `causal_parent_id`.
* Artifact rows include `artifact_type`, `path`, and `sha256`.
* Compaction preserves keep-list rows.

## Negative tests

* Remove an `artifact_ref` for a generated `scorecard`: scorecard check should fail.
* Remove a denial replay row: invariant I5 should fail.
* Remove a provider transaction from a committed write: I1 should fail when Phase 4 hardens.

## Record progress

```md
## Step 4 Replay Journal

New record types observed:
Rows versioned:
Trace/causal parent coverage:
Artifact refs:
Compaction result:
Negative fixtures:
Failures:
Decision:
```

---

# 5. FrontierService: prove model output is typed, measured, and rejectable

## Purpose

P11 says `FrontierService` should become the façade over `diffusiongemma/policy.py` and `diffusiongemma/live.py`, adding provenance stamping, parse-time canonicalization, taxonomy health, and rejection capture. 

## Tests to run or add

```text
tests/test_frontier_service.py
tests/test_frontier_rejections.py
tests/test_frontier_taxonomy_health.py
tests/test_live_diffusiongemma_frontier_generation.py
```

## Required assertions

For fixture backend:

* Frontier output before wrapper equals output after wrapper for the same seed.
* Candidate ranking equality holds unless tuning is intentionally applied.
* A `frontier_generation` replay row is emitted.

For live/NIM backend:

* Missing credentials fail closed; no heuristic fallback in live mode.
* Invalid JSON returns visible `model_generation_rejection` rows.
* Duplicate candidate IDs are rejected or made visible.
* Missing target calendars are either rejected or visibly repaired according to spec.
* `OTHER_intent_rate` is computed.
* `empty_frontier_rate` is reported.

## Entry bars

Do not continue tuning work until base-seed frontier quality clears:

```text
valid_frontier_rate >= 0.90
model_generation_rejection_rate <= 0.20
OTHER_intent_rate <= 0.10
expected_intent_hit >= 0.80
zero hard-invariant violations
empty_frontier_rate reported
```

P11 calls these Phase 2 entry bars and warns not to tune on garbage frontiers. 

## Commands

```bash
make lab-validate-seeds \
  | tee runs/p11_evidence/$RUN_ID/frontier_quality/lab-validate-seeds.log

make frontier-diff \
  | tee runs/p11_evidence/$RUN_ID/frontier_quality/frontier-diff.log
```

## Record progress

```md
## Step 5 FrontierService

Fixture equality:
Live fail-closed:
Typed candidates:
Rejections:
OTHER rate:
Empty frontier rate:
Entry bars:
Failures:
Decision:
```

---

# 6. Codex executive and autonomy matrix: prove the controller asks for less than Swift can safely deny

## Purpose

P11 separates two layers: Codex consults `configs/autonomy_matrix.json` before requesting commits, while Swift grant validation remains the plant-side authority boundary. A bug in one layer must not open the other. 

## Tests to run or add

```text
tests/test_autonomy_matrix.py
tests/test_codex_commit_bounds.py
tests/test_swift_authority_backstop.py
```

## Required assertions

* `configs/autonomy_matrix.json` exists.
* Codex does not request `request_commit` above the intent-family allowed tier.
* Swift still denies if Codex requests too much.
* Embedded grant payloads are ignored.
* Social mutation requires explicit social scope.
* `auto_apply_plan` requires tier 6 and appropriate scope.
* Denials produce receipts and replay rows, not exceptions.

## Negative tests

* Give Codex a candidate requiring tier 5 social mutation while matrix allows only tier 3: Codex stages or denies request before commit.
* Bypass Codex and call Swift with insufficient grant: Swift denies.
* Forge embedded grant object: Swift/Codex ignore it.

## Record progress

```md
## Step 6 Codex + Autonomy

Matrix present:
Codex request bound:
Swift backstop:
Social scope:
Tier-6 scope:
Denial replay rows:
Failures:
Decision:
```

---

# 7. Provider boundary: prove real acting is idempotent, verified, rollback-aware, and capped

## Purpose

P11 formalizes provider transactions as `read_observation`, `preview`, `commit`, `verify`, and `rollback`; `verify` is the genuinely new method. Provider writes must be idempotent, rollback-aware, verified, and rate-bounded. 

## Tests to run or add

```text
tests/test_provider_boundary_contract.py
tests/test_deterministic_provider_transactions.py
tests/test_eventkit_provider_transactions.py
tests/test_provider_idempotency.py
tests/test_provider_rate_caps.py
tests/test_provider_rollback_verify.py
```

## Required assertions

For deterministic provider:

* `read_observation` returns stable fixture truth.
* `preview` detects conflicts without mutation.
* `commit` writes once.
* Repeated `commit` with same idempotency key does not duplicate.
* `verify` reads provider truth after commit.
* `rollback` restores state.
* `provider_transaction` rows exist for every provider operation.

For EventKit sandbox:

* Sandbox calendar ID is enforced.
* No outside-sandbox mutation occurs.
* External IDs are recorded.
* Rollback is verified.
* Provider errors are replay rows.
* Mutation cap exceeded yields a denial receipt, not an exception.

Phase 4 acceptance requires external IDs, verified rollback, idempotency suppression of duplicates, zero outside-sandbox mutations, provider errors as replay rows, and cap-exceeded denial receipts. 

## Commands

```bash
make live-eventkit-e2e \
  | tee runs/p11_evidence/$RUN_ID/provider_sandbox/live-eventkit-e2e.log
```

Only run the EventKit path against an explicit sandbox calendar.

## Record progress

```md
## Step 7 Provider Boundary

Deterministic provider:
EventKit sandbox:
Read observation:
Preview:
Commit:
Verify:
Rollback:
Idempotency:
Rate caps:
Outside-sandbox mutation check:
Failures:
Decision:
```

---

# 8. Self-play `sim_v2`: prove the simulator is not rewarding self-belief

## Purpose

P11 says `sim_v2` is the highest-leverage change: self-play reward must come from seed ground truth, not candidate-predicted heads. Scenario files should be simple compositions over seeds, disturbances, adversaries, simulator version, and invariant assertions. 

## Tests to run or add

```text
tests/test_self_play_sim_v2.py
tests/test_self_play_scenario_files.py
tests/test_self_play_no_predicted_heads.py
tests/test_self_play_grant_policy.py
tests/test_self_play_variance_probe.py
```

## Required assertions

* `SelfPlayRunner` accepts `simulator_version`.
* `sim_v2` does not read:

  * `candidate.predicted_acceptance`
  * `candidate.predicted_utility`
  * `candidate.predicted_regret`
  * `candidate.predicted_interruption_cost`
  * `candidate.predicted_social_risk`
* Acceptance depends on seed/profile truth:

  * notification fatigue
  * bad response hours
  * preference claims
  * attendee/social friction
  * reversibility
  * perturbation intent
* Scenario files exist under:

```text
experiments/scenarios/
```

Required scenarios:

```text
external_call_no_prep_high_fatigue
dense_day_with_flexible_hold
social_conflict_move_meeting
stale_observation_after_provider_refresh
high_engagement_low_utility
undo_regret_after_auto_write
expired_authority_grant
```

## Anti-reward-hacking test

Create two candidates identical in action program and seed context but different only in `predicted_acceptance`:

```text
candidate_a.predicted_acceptance = 0.05
candidate_b.predicted_acceptance = 0.95
```

Under `sim_v2`, acceptance distribution must be unchanged within deterministic/random-seed tolerance.

## Required self-play record checks

* `self_play_episode` rows include `simulator_version`.
* `adversary_finding` rows map to canonical intents or `waived_findings`.
* Backend grant policy is recorded.
* Production-shadow backend is read-only.
* Provider-backed self-play routes through `ActionLifecycle`.

## Record progress

```md
## Step 8 Self-play sim_v2

simulator_version:
Predicted-head ban:
Scenario files:
Grant policy:
Adversary mappings:
Variance probe:
Anti-reward-hacking test:
Failures:
Decision:
```

---

# 9. Learning loop: prove policy updates are conservative, partitioned, and marginal

## Purpose

P11 frames policy tuning as conservative RL, not opaque online RL. `PolicyTuning` should be a constrained, legible, reversible improvement layer; every accepted update must show marginal effect in `frontier_diff` against the incumbent and cite replay evidence. 

## Tests to run or add

```text
tests/test_policy_tuning_partitioning.py
tests/test_tuning_reduction_replay_rows.py
tests/test_frontier_diff_against_current.py
tests/test_promote_policy_marginal_gates.py
```

## Required assertions

* `train_offline_policy.py` partitions by:

  * `runtime_mode`
  * `policy_backend`
  * reward provenance
* `tuning_reduction` row contains:

  * tuning ID
  * source replay paths
  * partitions
  * row counts
  * skipped row versions
  * mapped findings
  * unmapped findings
  * waived findings
* `run_frontier_diff.py` compares candidate tuning against `experiments/promoted/CURRENT.json` when present.
* `promote_policy.py` gates on candidate-vs-CURRENT, not only candidate-vs-empty.
* Promotion can be rolled back by moving the `CURRENT` pointer.

## Commands

```bash
make replay-offline-tuning-loop \
  | tee runs/p11_evidence/$RUN_ID/learning_loop/replay-offline-tuning-loop.log

make frontier-diff \
  | tee runs/p11_evidence/$RUN_ID/learning_loop/frontier-diff.log

make scorecard \
  | tee runs/p11_evidence/$RUN_ID/learning_loop/scorecard.log
```

## Required negative tests

Promotion must hold if any of these fire:

```text
engagement_gaming:
  Δengagement > +0.05
  AND Δutility < +0.01
  AND (Δregret > 0 OR Δinterruption > 0)

social_creep:
  Δsocial_risk > 0
  without new explicitly scoped social grant

regret_regression:
  pooled undo_regret findings per episode rise > 20% after tuning
```

P11 requires these to become executable promotion checks that produce `decision: hold` with the failing condition named. 

## Record progress

```md
## Step 9 Learning Loop

Partitioning:
tuning_reduction row:
Baseline CURRENT diff:
Promotion gates:
Rollback of CURRENT:
Negative gate tests:
Failures:
Decision:
```

---

# 10. Lab matrix: prove seeds are regression tests, not demos

## Purpose

P11 says seeded lab results should become regression tests. The regression pyramid is: 5-seed smoke matrix for substantive PRs, 20-base-seed matrix weekly/before promotion, flagged-seed matrix for every tuning candidate, provider sandbox matrix for provider changes, real dogfood import plus shadow seed daily during dogfood phases, and variance probe after any live model/prompt/decoding change. 

## Minimum matrix

```text
A: fixture heuristic baseline
B: live DiffusionGemma frontier, no live Codex
C: self-play sim_v2 batch
D: provider sandbox batch
```

## Commands

```bash
make lab-validate-seeds \
  | tee runs/p11_evidence/$RUN_ID/self_play/lab-validate-seeds.log

PYTHONPATH=src python3 scripts/run_lab_experiment.py \
  --seed experiments/seeds/<seed>.json \
  --runtime fixture \
  --self-play-backend stub_fast \
  --episodes 10 \
  --batch p11_smoke_$RUN_ID \
  | tee runs/p11_evidence/$RUN_ID/self_play/lab-run-fixture.log

make lab-compare \
  | tee runs/p11_evidence/$RUN_ID/self_play/lab-compare.log
```

For live DiffusionGemma, run only when credentials and environment are deliberately configured:

```bash
PYTHONPATH=src python3 scripts/run_lab_experiment.py \
  --seed experiments/seeds/<seed>.json \
  --runtime live_diffusiongemma \
  --self-play-backend stub_fast \
  --episodes 10 \
  --batch p11_live_frontier_$RUN_ID
```

## Acceptance

* Failed/corrupt runs are counted but excluded from pooled metrics.
* Expectation failures are data.
* Infrastructure failures are failures.
* Each run has manifest, replay, lab report, frontier diff, scorecard.
* `lab-compare` produces comparison report.
* Variance probe exists before trusting live model/prompt deltas.

P11 keeps the file-backed `experiments/` tree, matrix cells, promotion thresholds, and rule that expectation failures are data while infrastructure failures are failures. 

## Record progress

```md
## Step 10 Lab Matrix

Batch ID:
Cells run:
Seeds:
Runtime modes:
Self-play backend:
Completed:
Failed:
Corrupt:
Expectation failures:
Infrastructure failures:
Variance probe:
Comparison report:
Decision:
```

---

# 11. Promotion: prove autonomy increases one action family at a time

## Purpose

P11 Phase 6 promotes action families one at a time through the autonomy matrix: `create_prep_block`, `add_buffer`, `protect_deep_work`, `batch_admin`, private flexible `move_meeting`, social shadow only, and then sandbox-only `auto_apply_plan`. Each promotion must cite seed pass rate, self-play pass rate, provider sandbox pass rate, human feedback pass rate, and rollback pass rate. 

## Commands

```bash
PYTHONPATH=src python3 scripts/promote_policy.py \
  --batch <BATCH_ID> \
  --human-note "P11 candidate promotion review" \
  | tee runs/p11_evidence/$RUN_ID/promotion/promote-policy.log
```

## Required promotion record fields

```text
policy_tuning_id
source_batch
source_replay_paths
candidate_vs_empty_diff
candidate_vs_current_diff
seed_pass_rate
self_play_pass_rate
provider_sandbox_pass_rate
human_feedback_pass_rate
rollback_pass_rate
known_regressions
gates
promotion_decision
rollback_plan
human_note
```

## Acceptance

* Promotion can return `hold`.
* `hold` names failing gates.
* `promote` updates only the intended `CURRENT` pointer or autonomy matrix family.
* Promotion includes rollback plan.
* Promotion does not increase social or compound autonomy unless the family-specific evidence is present.

## Record progress

```md
## Step 11 Promotion

Batch:
Candidate tuning:
Current baseline:
Marginal diff:
Gates:
Decision:
Rollback plan:
Autonomy matrix changed:
Family:
Evidence links:
Failures:
```

---

# 12. Frontend and Glass Cockpit: prove UI reads the same trace the learner trains on

## Purpose

P11 says every UI surface must read the same trace the learner trains on. The frontend already has `Operate`, `Observe`, `Learn`, `Lab`, and `Authority` surfaces, with Learn showing frontier quality/tuning/frontier diff and Lab showing self-play backend and seeded experiments. 

## Tests to run or add

```text
tests/test_frontend_projector_p11.py
scripts/run_browser_e2e.py
```

## Commands

```bash
make browser-e2e \
  | tee runs/p11_evidence/$RUN_ID/frontend/browser-e2e.log

make evidence-bundle \
  | tee runs/p11_evidence/$RUN_ID/frontend/evidence-bundle.log
```

## Required assertions

* `Observe` shows trace stages and statuses.
* `Learn` shows:

  * valid candidates
  * rejections
  * taxonomy health
  * tuning provenance
  * frontier diff
* `Lab` shows:

  * self-play backend
  * grant policy
  * seeded experiment index
  * recent lab runs
  * invariant violations
* `Authority` shows tier/scopes.
* Replay export includes the same records used by scorecard and training.
* UI does not invent separate state.

## Record progress

```md
## Step 12 Frontend

Browser E2E:
Observe:
Learn:
Lab:
Authority:
Replay export:
Trace consistency:
Failures:
Decision:
```

---

# 13. Release-style dogfood gate

## Purpose

This is not the same as promotion. This proves the app can run as a dogfood artifact with evidence capture.

## Command

```bash
make dogfood-release \
  | tee runs/p11_evidence/$RUN_ID/release/dogfood-release.log
```

The release script runs runtime gates, Python tests, Swift tests, Swift IPC tests, browser E2E, macOS app build/sanity where applicable, artifact validation, and secret scans. 

## Acceptance

* Release report exists.
* Artifact validation passes.
* Secret scan passes.
* Runtime report names active backends.
* Live credentials are required only for live modes.
* No generated evidence bundle contains secrets.

## Record progress

```md
## Step 13 Dogfood Release

Release report:
Runtime:
Backends:
Browser:
Swift IPC:
Mac app:
Secret scan:
Artifact validation:
Failures:
Decision:
```

---

# 14. Engineer progress ledger

Use this section as the running working document.

```md
# P11 Testing Progress Ledger

RUN_ID:
Engineer:
Date:
Git SHA:
Branch:
Changed files:
Hypothesis:
One-live-component-at-a-time check:
Changed field:
Held fixed:

## Summary

Overall decision:
- [ ] pass
- [ ] hold
- [ ] fail
- [ ] needs rerun

Primary reason:

## Evidence Artifacts

Baseline:
Contracts:
Trajectory:
Replay:
Frontier:
Codex/authority:
Provider:
Self-play:
Learning:
Lab compare:
Promotion:
Frontend:
Release:

## Metrics Snapshot

valid_frontier_rate:
model_generation_rejection_rate:
OTHER_intent_rate:
expected_intent_hit_rate:
empty_frontier_rate:
hard_invariant_violations:
soft_invariant_violations:
self_play_average_reward:
undo_regret_per_episode:
engagement_delta:
utility_delta:
regret_delta:
interruption_delta:
social_risk_delta:
rollback_pass_rate:
provider_idempotency_pass:
sim_vs_real_acceptance_gap:
latency_ms_p50:
latency_ms_p95:
nim_request_count:

## Failures

| Step | Failure | Expected | Actual | Artifact | Owner | Fix | Rerun required |
|---|---|---|---|---|---|---|---|

## Decisions

| Decision | Reason | Evidence | Reversible? | Rollback |
|---|---|---|---|---|

## Follow-up PRs

| PR | Scope | Gate needed | Owner |
|---|---|---|---|
```

---

# 15. Final acceptance checklist

The implementation is ready for the next phase only when all of these are true:

```md
## Final P11 Acceptance

### Trajectory integrity
- [ ] Every action path returns or references an ActionEnvelope.
- [ ] Every replay row has record_schema_version.
- [ ] Every replay row has trace_id and causal_parent_id.
- [ ] artifact_ref rows exist for derived artifacts.
- [ ] Golden replay passes old and new checks.
- [ ] Synthetic violation fixtures fail exactly as expected.

### Machine learning
- [ ] FrontierService wraps fixture and live policy paths.
- [ ] Model output is typed, rejected, or visibly repaired.
- [ ] frontier_generation rows record provenance and rejection counts.
- [ ] Phase 2 entry bars are met before tuning.
- [ ] Policy tuning is partitioned by runtime/backend/reward provenance.
- [ ] Frontier diff compares candidate against CURRENT.
- [ ] Promotion gates use marginal diff, not only empty baseline.

### Machine acting
- [ ] Codex consults autonomy matrix before commit requests.
- [ ] Swift independently validates grants and authority.
- [ ] Provider protocol includes read_observation, preview, commit, verify, rollback.
- [ ] Provider transactions are replay-visible.
- [ ] Commit rate caps produce denial receipts.
- [ ] Rollback state is verified or pending for committed reversible writes.
- [ ] EventKit/provider sandbox prevents outside-sandbox mutation.

### Self-play
- [ ] sim_v2 exists and declares simulator_version.
- [ ] sim_v2 does not use candidate predicted heads as acceptance truth.
- [ ] Scenario files exist and map to invariant assertions.
- [ ] Self-play backend grant policy is recorded.
- [ ] Variance probe exists before trusting live deltas.
- [ ] failure_penalties are non-empty for accepted self-play learning effect.

### Lab and promotion
- [ ] 5-seed smoke matrix runs for substantive PR.
- [ ] 20-base-seed matrix runs before promotion.
- [ ] Flagged-seed matrix runs for every tuning candidate.
- [ ] Provider sandbox matrix runs for provider changes.
- [ ] Promotion can hold with named gate failures.
- [ ] Every autonomy increase is per action family and reversible by matrix/CURRENT rollback.

### Product surface
- [ ] Learn/Lab/Observe/Authority surfaces render P11 fields.
- [ ] Replay export matches training/debug trajectory.
- [ ] UI does not maintain a separate truth.
```

---

# The judgment standard

A passing P11 implementation is not one where “the assistant seems smarter.” It is one where:

```text
typed frontier quality improves,
bounded acting remains recoverable,
self-play no longer flatters policy self-belief,
training rows have provenance,
promotion beats the incumbent beyond measured noise,
and every claim is backed by replay.
```

That is the CalendarPilot lab becoming a learning instrument rather than a demo harness.
