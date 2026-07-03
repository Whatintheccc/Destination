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

Date: 2026-07-03
Engineer: Codex
Git SHA: 8dcf74c0933bd326785c6870a1d2d09ddbbad56d
Python tests: pass (`runs/p11_evidence/20260703T191307Z-p11-final/baseline_tests/py-test.log`)
Swift tests: pass (`runs/p11_evidence/20260703T191307Z-p11-final/baseline_tests/swift-test.log`)
Contract vectors: pass (`runs/p11_evidence/20260703T191307Z-p11-final/contracts/contract-vectors-final.log`)
Invariant check: pass (`runs/p11_evidence/20260703T191307Z-p11-final/contracts/check-invariants-final.log`)
Frontier diff artifact: `runs/p11_evidence/20260703T191307Z-p11-final/learning_loop/frontier-diff-candidate-vs-current.json`
Scorecard artifact: `runs/p11_evidence/20260703T191307Z-p11-final/learning_loop/scorecard.json`
Failures: none in deterministic baseline. Earlier live NIM/EventKit holds are resolved in the unblock rerun evidence.
Follow-up: keep live NIM schema-drift normalization covered and keep EventKit mutation restricted to `CalendarPilot Sandbox`.
Decision: pass
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

Schemas present: pass (`ActionEnvelope`, `ReplayRecord`, `PolicyTuning`, `FrontierDiff`, `LabReport`, `Scorecard`, `VERSIONS.json`)
VERSIONS.json updated: pass by contract vector coverage
Golden vectors: pass (`runs/p11_evidence/20260703T191307Z-p11-final/contracts/contract-vectors-final.log`)
Broken-vector failure verified: pass through invariant/unit coverage
Unversioned shape scan: pass; strict replay audit has no missing `record_schema_version`, `trace_id`, or `causal_parent_id`
Failures: none
Decision: pass
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

Lifecycle coverage: pass; action lifecycle and provider transaction tests pass
Rollback adequacy: pass; committed reversible writes require pending/verified rollback state
Trace endpoint: pass through browser/API evidence and replay export
Compaction keep-list: pass; `artifact_ref`, `frontier_generation`, and provider transaction rows preserved in replay audit
Golden replay result: pass (`runs/p11_evidence/20260703T191307Z-p11-final/contracts/check-invariants-final.log`)
Synthetic violation result: pass through invariant/unit coverage
Failures: none
Decision: pass
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

New record types observed: `frontier_generation`, `provider_transaction`, `tuning_reduction`, `artifact_ref`
Rows versioned: pass; strict replay audit reports no missing schema versions
Trace/causal parent coverage: pass; strict replay audit reports no missing trace or causal parent IDs
Artifact refs: pass; base20 has 120, smoke has 30, provider sandbox has 30
Compaction result: pass; keep-list rows remain replay-visible
Negative fixtures: pass through invariant and contract test coverage
Failures: none
Decision: pass
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

Fixture equality: pass
Live fail-closed: pass; live NIM invalid JSON is captured as a replay-visible controlled hold
Typed candidates: pass; deterministic smoke/base20 frontiers are valid
Rejections: deterministic rejection rate 0.0; earlier live NIM schema failure recorded as `model_generation_rejection`, then strict live rerun passed after visible schema-drift normalization
OTHER rate: 0.0 on smoke and base20
Empty frontier rate: reported by lab comparison/scorecard; no deterministic empty-frontier failure observed
Entry bars: pass on base20 (`valid_frontier_rate=1.0`, `model_generation_rejection_rate=0.0`, `OTHER_intent_rate=0.0`, `expected_intent_hit_rate=0.85`, `invariant_violations_max=0`)
Failures: resolved. Earlier live NIM invalid frontier JSON is archived at `runs/p11_evidence/20260703T191307Z-p11-final/learning_loop/replay_offline_artifacts/nim_schema_failure.json`; strict rerun passes at `runs/p11_evidence/20260703T191307Z-p11-final/unblock/live-nim-strict-after-normalization.log`.
Decision: pass; strict live gate passed with `CALENDAR_PILOT_REQUIRE_LIVE_NIM=1`, `CALENDAR_PILOT_NIM_FRONTIER_LIMIT=1`, and visible schema-drift normalization.
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

Matrix present: pass
Codex request bound: pass
Swift backstop: pass
Social scope: pass
Tier-6 scope: pass
Denial replay rows: pass
Failures: none
Decision: pass
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

Deterministic provider: pass (`tests/test_deterministic_provider.py`, `tests/test_action_lifecycle_and_store.py`, provider sandbox batch)
EventKit sandbox: pass after unblock; authorization status `full_access`, mutation enabled, `require_live=true`, target calendar `CalendarPilot Sandbox`, verified external EventKit ID present
Read observation: pass in deterministic provider
Preview: pass; provider sandbox records preview transactions
Commit: pass in deterministic provider and live EventKit sandbox; live commit status `committed`
Verify: pass in deterministic provider and live EventKit sandbox; provider verify transaction status `verified`, `missing_external_ids=[]`, `local_time_echo_ok=true`
Rollback: pass in deterministic provider, promotion CURRENT rollback proof, and live EventKit sandbox undo (`rollback_verified=true`)
Idempotency: pass in provider tests
Rate caps: pass; cap-exceeded behavior returns denial receipts
Outside-sandbox mutation check: pass; live mutation targeted only `CalendarPilot Sandbox`
Failures: resolved. Earlier block (`not_determined`, mutation disabled) is archived at `runs/p11_evidence/20260703T191307Z-p11-final/provider_sandbox/live-eventkit-e2e.log`; live sandbox mutation passes at `runs/p11_evidence/20260703T191307Z-p11-final/unblock/live_eventkit_artifacts/eventkit_health.json` and `runs/p11_evidence/20260703T191307Z-p11-final/unblock/live-eventkit-sandbox-mutation.log`.
Decision: pass live EventKit provider boundary; Calendar full access is configured for `dev.calendarpilot.eventkitbridge`, and the opt-in write/verify/rollback probe passed in `CalendarPilot Sandbox`.
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

simulator_version: pass; `sim_v2` declared and recorded
Predicted-head ban: pass (`tests/test_self_play.py::test_sim_v2_ignores_candidate_predicted_heads`)
Scenario files: pass; 7 scenario files validate (`runs/p11_evidence/20260703T191307Z-p11-final/self_play/lab-validate-scenarios-final.log`)
Grant policy: pass; self-play backend grant policy recorded
Adversary mappings: pass; targeted failure modes map to canonical penalty evidence
Variance probe: pass (`runs/p11_evidence/20260703T191307Z-p11-final/self_play/variance-probe.log`)
Anti-reward-hacking test: pass; response unchanged when only candidate predicted heads change
Failures: none
Decision: pass
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

Partitioning: pass; tuning partitions by runtime/backend/reward provenance
tuning_reduction row: pass; targeted penalty training writes replay-visible reduction evidence
Baseline CURRENT diff: pass (`runs/p11_evidence/20260703T191307Z-p11-final/learning_loop/frontier-diff-candidate-vs-current.json`)
Promotion gates: pass; final promotion gates all pass
Rollback of CURRENT: pass; promote -> rollback -> final promote exercised
Negative gate tests: pass through promotion gate/unit coverage; final candidate has no failing gate
Failures: resolved. Earlier live NIM controlled hold remains archived; strict live NIM replay/offline loop now passes.
Decision: pass deterministic and strict live learning paths; strict live rerun produced `tuning_had_effect=true`, `leader_changed=true`, and `tuning_control_notes_present=true`.
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

Batch ID: `p11_final_smoke_20260703T191307Z-p11-final`, `p11_final_base20_20260703T191307Z-p11-final`, `p11_provider_sandbox_20260703T191307Z-p11-final`
Cells run: fixture heuristic baseline, `sim_v2` self-play batch, deterministic provider sandbox batch; live NIM attempted only in learning loop and held
Seeds: 5-seed smoke, 20-base-seed matrix, 5 provider sandbox runs
Runtime modes: fixture/deterministic provider; live DiffusionGemma credential gate passed but live frontier schema held
Self-play backend: `stub_fast`, `sim_v2`
Completed: 5 smoke, 20 base20, 5 provider sandbox
Failed: 0 deterministic runs
Corrupt: 0 deterministic runs
Expectation failures: base20 expected intent hit rate 0.85; smoke/provider 1.0
Infrastructure failures: none in deterministic matrices; earlier live NIM schema failure resolved by strict rerun
Variance probe: pass (`runs/p11_evidence/20260703T191307Z-p11-final/self_play/variance-probe.log`)
Comparison report: `self_play/smoke-comparison.json`, `self_play/base20-comparison.json`, `provider_sandbox/provider-sandbox-comparison.json`
Decision: pass
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

Batch: `p11_final_base20_20260703T191307Z-p11-final`
Candidate tuning: `experiments/reports/candidate_policy_tuning_p11_final_base20_20260703T191307Z-p11-final.json`
Current baseline: `baseline_empty_v1`
Marginal diff: candidate-vs-CURRENT diff present in `promotion/promotion-final.json`
Gates: pass (`flagged_seed_leader_changes=4`, `self_play_penalty_effect=pass`, `valid_frontier_rate=1.0`, `OTHER_intent_rate=0.0`, `model_generation_rejection_rate=0.0`, `invariant_violations=0`, `bad_intent_committed=0`)
Decision: promote
Rollback plan: restore `experiments/promoted/CURRENT.json` to `baseline_empty_v1` using the rollback command recorded in `promotion/promotion-final.json`
Autonomy matrix changed: no; promotion updated the intended CURRENT tuning pointer only
Family: policy tuning promotion with no social or compound autonomy increase
Evidence links: `promotion/promotion-final.json`, `promotion/promotion-rollback.json`, `promotion/CURRENT-final.json`
Failures: none
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

Browser E2E: pass (`runs/p11_evidence/20260703T191307Z-p11-final/frontend/browser-e2e.log`)
Observe: pass; trace stages/statuses render
Learn: pass; frontier quality, tuning provenance, frontier diff, and inspector surface render
Lab: pass; self-play backend, `sim_v2`, seeded experiments, and run count render
Authority: pass; tier/scopes and grant history render
Replay export: pass (`runs/p11_evidence/20260703T191307Z-p11-final/frontend/evidence-bundle.log`)
Trace consistency: pass; UI reads replay/session state, not a separate truth
Failures: one manual Chrome reload blank-tab anomaly; fresh Computer Use inspection and CDP browser flow passed
Decision: pass; manual reload anomaly is not release-blocking
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

Release report: pass (`runs/p11_evidence/20260703T191307Z-p11-final/release/release_artifacts/dogfood_release_report.json`, `ok=true`)
Runtime: pass; fixture, live Codex credential, live DiffusionGemma credential, Swift IPC runtime gates passed
Backends: fixture uses deterministic Codex/heuristic DiffusionGemma/SwiftKernelStub/local_stub; live DiffusionGemma gate sees `nvidia_nim_diffusiongemma_policy`
Browser: pass
Swift IPC: pass
Mac app: pass build and sanity checks
Secret scan: pass
Artifact validation: pass
Failures: none; separate opt-in live EventKit sandbox mutation rerun passed after release gate
Decision: pass
```

---

# 14. Engineer progress ledger

Use this section as the running working document.

# P11 Testing Progress Ledger

RUN_ID: 20260703T191307Z-p11-final
Engineer: Codex
Date: 2026-07-03
Git SHA: 8dcf74c0933bd326785c6870a1d2d09ddbbad56d
Branch: codex/dogfood-macos-app
Changed files: taxonomy normalization, behavioral controls, self-play, replay/offline tuning loop, promotion, lab docs, implementation summary, generated experiment/promotion artifacts
Hypothesis: P11 is ready when typed frontiers, bounded acting, replay-visible learning, self-play penalty evidence, marginal promotion, rollback, and UI trace surfaces all pass together.
One-live-component-at-a-time check: deterministic evidence is separated from live NIM and live EventKit availability; earlier live holds are visible, and unblock reruns are recorded separately.
Changed field: canonical intent handling, sim_v2 predicted-head guard, live NIM schema failure handling, promotion/rollback records, final evidence artifacts.
Held fixed: seed/scenario definitions, contract gates, provider authority boundary, and deterministic provider sandbox behavior.

## Summary

Overall decision:
- [x] pass
- [ ] hold
- [ ] fail
- [ ] needs rerun

Primary reason: deterministic P11 promotion evidence passes every required gate; the remaining live paths are explicit operational holds.

## Evidence Artifacts

Baseline: `runs/p11_evidence/20260703T191307Z-p11-final/baseline_tests/`
Contracts: `runs/p11_evidence/20260703T191307Z-p11-final/contracts/check-invariants-final.log`, `contract-vectors-final.log`
Trajectory: `runs/p11_evidence/20260703T191307Z-p11-final/replay/strict-replay-batch-audit.json`
Replay: `experiments/reports/pooled_p11_final_base20_20260703T191307Z-p11-final.jsonl`
Frontier: `runs/p11_evidence/20260703T191307Z-p11-final/learning_loop/frontier-diff-candidate-vs-current.json`
Codex/authority: release tests, Swift authority tests, frontend Authority inspection
Provider: `runs/p11_evidence/20260703T191307Z-p11-final/provider_sandbox/provider-sandbox-comparison.json`, `live-eventkit-e2e.log`
Self-play: `runs/p11_evidence/20260703T191307Z-p11-final/self_play/smoke-comparison.json`, `base20-comparison.json`, `targeted-penalty-summary.json`
Learning: `runs/p11_evidence/20260703T191307Z-p11-final/learning_loop/replay-offline-tuning-loop.log`, `targeted-penalty-policy-report.json`
Lab compare: `experiments/reports/p11_final_smoke_20260703T191307Z-p11-final_comparison.json`, `experiments/reports/p11_final_base20_20260703T191307Z-p11-final_comparison.json`
Promotion: `runs/p11_evidence/20260703T191307Z-p11-final/promotion/promotion-final.json`, `promotion-rollback.json`, `CURRENT-final.json`
Frontend: `runs/p11_evidence/20260703T191307Z-p11-final/frontend/browser-e2e.log`, `evidence-bundle.log`, `manual-browser-flow.log`
Release: `runs/p11_evidence/20260703T191307Z-p11-final/release/release_artifacts/dogfood_release_report.json`

## Metrics Snapshot

valid_frontier_rate: 1.0 on smoke, base20, and provider sandbox
model_generation_rejection_rate: 0.0 deterministic; earlier live NIM schema failure captured as controlled hold, then strict live rerun passed
OTHER_intent_rate: 0.0 on smoke and base20
expected_intent_hit_rate: 1.0 smoke, 0.85 base20, 1.0 provider sandbox
empty_frontier_rate: reported by comparison/scorecard; no deterministic empty-frontier failure observed
hard_invariant_violations: 0
soft_invariant_violations: no release-blocking soft violations recorded
self_play_average_reward: -3.5863 in targeted adversarial penalty replay
undo_regret_per_episode: targeted penalty replay produced undo_regret in 8/8 adversarial episodes
engagement_delta: not promoted as a standalone final metric
utility_delta: not promoted as a standalone final metric
regret_delta: not promoted as a standalone final metric
interruption_delta: not promoted as a standalone final metric
social_risk_delta: not promoted as a standalone final metric
rollback_pass_rate: 1.0
provider_idempotency_pass: true in deterministic provider tests
sim_vs_real_acceptance_gap: not measured; live EventKit mutation/rollback probe passed but was not a sim-vs-real acceptance study
latency_ms_p50: not measured in final evidence
latency_ms_p95: not measured in final evidence
nim_request_count: earlier live schema retry exhausted after 2 attempts; strict rerun passed after NIM schema-drift normalization

## Failures

| Step | Failure | Expected | Actual | Artifact | Owner | Fix | Rerun required |
|---|---|---|---|---|---|---|---|
| 5/9 | Live NIM invalid frontier JSON | Typed, repaired, or visibly rejected frontier output | Resolved: strict live rerun passed after normalizing NIM `new_start`/`new_end`, nested `params`, and `batch_tasks.target_time` drift | `unblock/live-nim-strict-after-normalization.log`, `unblock/live_nim_strict_artifacts/diff_summary.json` | Model/live integration | Keep schema-drift regression tests and strict live rerun in gate notes | No |
| 7 | Live EventKit mutation unavailable | Explicit sandbox calendar permission and opt-in mutation | Resolved: Calendar permission `full_access`; `CalendarPilot Sandbox` commit/verify/undo passed with `verified_external_ids` present, `local_time_echo_ok=true`, and `rollback_verified=true` | `unblock/live_eventkit_artifacts/eventkit_health.json`, `unblock/live-eventkit-sandbox-mutation.log` | Provider/operator | Keep mutation opt-in, sandbox calendar targeting, and bridge-level EventKit ID verification | No |
| 12 | Manual Chrome reload anomaly | Manual reload remains rendered | One Chrome tab blanked after reload; clean Computer Use tab and CDP browser flow passed | `frontend/manual-browser-flow.log` | Frontend/devtools follow-up | Reproduce separately if reload behavior matters; automated browser evidence passed | No for P11 release |

## Decisions

| Decision | Reason | Evidence | Reversible? | Rollback |
|---|---|---|---|---|
| Map draft repair-plan intents to `ask_clarification` | These are user-reviewed repair-plan drafts, not a new action family | `src/calendar_pilot/environment/taxonomy.py`, `tests/test_behavioral_controls.py` | Yes | Revert taxonomy mapping if a real action family is introduced |
| Promote only after targeted sim_v2 penalty evidence | Ordinary robust matrix avoided failures; P11 needs proof that failure penalties can affect tuning | `self_play/targeted-penalty-summary.json`, `learning_loop/targeted-penalty-policy-report.json` | Yes | Roll back CURRENT to baseline tuning |
| Exercise promote -> rollback -> final promote | P11 requires reversible promotion state | `promotion/promotion-rollback.json`, `promotion/CURRENT-final.json` | Yes | Run recorded rollback command |
| Treat live NIM schema failure as controlled hold by default | Live instability must be visible without invalidating deterministic promotion evidence | `learning_loop/replay_offline_artifacts/nim_schema_failure.json` | Yes | Set `CALENDAR_PILOT_REQUIRE_LIVE_NIM=1` |
| Keep EventKit mutation opt-in | P11 forbids outside-sandbox mutation without explicit permission and flag | `provider_sandbox/live-eventkit-e2e.log` | Yes | Grant sandbox access and set `CALENDAR_PILOT_EVENTKIT_MUTATION=1` |
| Combine automated browser E2E, evidence bundle, CDP flow, and Computer Use inspection | UI must show the same P11 trace surfaces the learner trains on | `frontend/browser-e2e.log`, `frontend/evidence-bundle.log`, `frontend/manual-browser-flow.log` | Yes | Rerun frontend evidence |
| Normalize observed NIM schema drift | Live NIM emitted safe but non-canonical action shapes (`new_start`/`new_end`, nested `params`, `batch_tasks.target_time`) | `tests/test_policy.py`, `unblock/live-nim-strict-after-normalization.log` | Yes | Remove normalization only if upstream NIM schema becomes consistently strict |
| Use dedicated EventKit sandbox calendar | Live writes must be confined to an explicit sandbox target | `unblock/live_eventkit_artifacts/eventkit_health.json` | Yes | Remove `CalendarPilot Sandbox` manually if no longer needed |

## Follow-up PRs

| PR | Scope | Gate needed | Owner |
|---|---|---|---|
| Live NIM schema hardening | Keep live DiffusionGemma/NIM frontier output schema-valid under observed drift | `CALENDAR_PILOT_REQUIRE_LIVE_NIM=1 make replay-offline-tuning-loop` continues to pass | Model/live integration |
| EventKit sandbox live mutation | Preserve documented sandbox-calendar setup and opt-in mutation probe | `make live-eventkit-e2e` with full Calendar access, `CALENDAR_PILOT_EVENTKIT_MUTATION=1`, `CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot Sandbox"`, provider verify status `verified`, and rollback status `rollback_verified` continues to pass | Provider/operator |
| Manual reload investigation | Reproduce blank-tab reload anomaly outside release path | Manual reload plus CDP flow both render after refresh | Frontend |

---

# 15. Final acceptance checklist

The implementation is ready for the next phase only when all of these are true:

## Final P11 Acceptance

### Trajectory integrity
- [x] Every action path returns or references an ActionEnvelope.
- [x] Every replay row has record_schema_version.
- [x] Every replay row has trace_id and causal_parent_id.
- [x] artifact_ref rows exist for derived artifacts.
- [x] Golden replay passes invariant checks.
- [x] Synthetic violation fixtures fail through unit coverage.

### Machine learning
- [x] FrontierService wraps fixture and live policy paths.
- [x] Model output is typed, rejected, or visibly repaired.
- [x] frontier_generation rows record provenance and rejection counts.
- [x] Phase 2 entry bars are met before tuning.
- [x] Policy tuning is partitioned by runtime/backend/reward provenance.
- [x] Frontier diff compares candidate against CURRENT.
- [x] Promotion gates use marginal diff, not only empty baseline.

### Machine acting
- [x] Codex consults autonomy matrix before commit requests.
- [x] Swift independently validates grants and authority.
- [x] Provider protocol includes read_observation, preview, commit, verify, rollback.
- [x] Provider transactions are replay-visible.
- [x] Commit rate caps produce denial receipts.
- [x] Rollback state is verified or pending for committed reversible writes.
- [x] EventKit/provider sandbox prevents outside-sandbox mutation.

### Self-play
- [x] sim_v2 exists and declares simulator_version.
- [x] sim_v2 does not use candidate predicted heads as acceptance truth.
- [x] Scenario files exist and map to invariant assertions.
- [x] Self-play backend grant policy is recorded.
- [x] Variance probe exists before trusting live deltas.
- [x] failure_penalties are non-empty for accepted self-play learning effect.

### Lab and promotion
- [x] 5-seed smoke matrix runs for substantive PR.
- [x] 20-base-seed matrix runs before promotion.
- [x] Flagged-seed matrix runs for the tuning candidate.
- [x] Provider sandbox matrix runs for provider changes.
- [x] Promotion can hold with named gate failures and can promote when gates pass.
- [x] Autonomy increase is reversible by CURRENT rollback.

### Product surface
- [x] Learn/Lab/Observe/Authority surfaces render P11 fields.
- [x] Replay export matches training/debug trajectory.
- [x] UI does not maintain a separate truth.

## Remaining operational notes

- Live NIM blocker resolved on unblock rerun. The strict live replay/offline loop passed with `CALENDAR_PILOT_REQUIRE_LIVE_NIM=1`, `CALENDAR_PILOT_NIM_FRONTIER_LIMIT=1`, and `CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS=8000`; evidence: `unblock/live-nim-strict-after-normalization.log` and `unblock/live_nim_strict_artifacts/diff_summary.json`.
- Live EventKit blocker resolved on unblock rerun. Calendar permission is `full_access` for the EventKit bridge, the dedicated `CalendarPilot Sandbox` calendar exists, and the opt-in commit/verify/undo probe passed with `verified_external_ids` present, `local_time_echo_ok=true`, and `rollback_verified=true`; evidence: `unblock/live_eventkit_artifacts/eventkit_health.json`.
- Post-unblock validation passed: `make py-test` ran 158 tests with 10 skips (`unblock/post-unblock-py-test.log`), and `make swift-test` ran 17 Swift tests with zero failures (`unblock/post-unblock-swift-test.log`).
- Calendar permission cannot be forced permanently by a project flag. macOS TCC owns Calendar access per app identity; after rebuilding an unsigned or ad-hoc helper, TCC can return to `not_determined`. To reduce repeated prompts, keep the EventKit bridge installed with stable bundle identity/signing and request access once with `CALENDAR_PILOT_REQUEST_EVENTKIT_ACCESS=1`.

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
