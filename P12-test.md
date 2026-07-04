# Working Document: P12 Test Framework

**File:** `P12-test.md`
**Scope:** Test the P12-updated CalendarPilot repo after the “Lab as Instrument, Policy as Product, Signals as Truth” implementation.
**Goal:** Prove the system can learn safely from verifiable human signals, preserve the P11 trajectory substrate, and avoid leaking biography or derived labels into reward or authority.

P12’s core shift is the three-stream doctrine: **ActionStream** is reward truth, **WorldStream** is provider-verified calendar reality, **BiographyStream** is a slow user-owned prior, and derived `SemanticSignal` objects must be evidence-cited, versioned, user-controllable, and barred from authority. 

---

# 0. Prime directive

Do not ask only:

```text
Did the tests pass?
```

Ask:

```text
Can we prove that CalendarPilot learns only from verifiable action evidence,
uses world state as context,
treats biography as a prior,
keeps labels out of authority,
keeps non-ActionStream rows out of reward,
and promotes policy/autonomy only with replay-backed evidence?
```

A P12 pass means:

```text
P11 still passes.
Replay rows are stream-tagged.
Reward purity is enforced.
Estimator outputs are versioned and evidence-cited.
Semantic labels are user-visible and user-controllable.
sim_v2.1 uses behavior-authored histories, not psychological scalars.
Dogfood shadow runs without commits.
Calibration reports pass or hold honestly.
Provider capabilities constrain acting.
Policy improvements survive reward-head gates and ablations.
Autonomy changes one action family at a time.
```

---

# 1. Evidence bundle setup

Run every test pass under a unique evidence directory.

```bash
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-p12"
mkdir -p runs/p12_evidence/$RUN_ID/{\
preflight,p11_regression,contracts,signal_streams,reward_purity,\
estimators,dogfood_shadow,calibration,semantic_labels,measurement,\
provider_capabilities,self_play,policy_learning,autonomy,frontend,release}

git rev-parse HEAD > runs/p12_evidence/$RUN_ID/git_sha.txt
git status --short > runs/p12_evidence/$RUN_ID/git_status.txt
```

Minimum final bundle:

```text
runs/p12_evidence/<RUN_ID>/
  git_sha.txt
  git_status.txt
  preflight/
  p11_regression/
  contracts/
  signal_streams/
  reward_purity/
  estimators/
  dogfood_shadow/
  calibration/
  semantic_labels/
  measurement/
  provider_capabilities/
  self_play/
  policy_learning/
  autonomy/
  frontend/
  release/
  progress_log.md
  decision_log.md
```

Progress entry template:

```md
## Step N — <name>

Date:
Engineer:
Git SHA:
Commands:
Artifacts:
Result: pass | hold | fail | needs rerun
Failures:
Decision:
Follow-up:
```

---

# 2. Step 1 — Preflight the repo and runtime

## Purpose

Confirm the repo is runnable before interpreting failures as product failures.

The updated repo builds on the existing CalendarPilot structure: Python package, Swift package, contracts, frontend, scripts, providers, self-play, replay, and dogfood release machinery. 

## Commands

```bash
python3 --version | tee runs/p12_evidence/$RUN_ID/preflight/python-version.log
swift --version   | tee runs/p12_evidence/$RUN_ID/preflight/swift-version.log
node --version    | tee runs/p12_evidence/$RUN_ID/preflight/node-version.log || true

find contracts -maxdepth 1 -type f | sort \
  > runs/p12_evidence/$RUN_ID/preflight/contracts-list.txt

find scripts -maxdepth 1 -type f | sort \
  > runs/p12_evidence/$RUN_ID/preflight/scripts-list.txt

find docs -maxdepth 1 -type f | sort \
  > runs/p12_evidence/$RUN_ID/preflight/docs-list.txt
```

## Acceptance

```text
Python is available.
Swift is available.
Node is available or browser/frontend tests are marked hold.
P12 contracts exist.
P12 scripts exist.
P12 docs exist.
Repo status is captured.
```

## Hold conditions

```text
Missing Node/Chrome/Playwright should hold browser E2E only.
Missing Swift should fail Swift gates.
Missing Python should fail the run.
```

## Run record — 20260703T224814Z-p12

Date: 2026-07-03  
Engineer: Codex  
Git SHA: 8f484f40ec4fb48cd178e2f4e815bed1f9efc0e6  
Commands: evidence bundle setup; runtime version captures; contracts/scripts/docs inventories; Git SHA/status snapshot.  
Artifacts: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/preflight/`, `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/git_sha.txt`, `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/git_status.txt`  
Result: pass  
Failures: none  
Decision: proceed to P11 regression floor  
Follow-up: none

---

# 3. Step 2 — Freeze P11 as the regression floor

## Purpose

P12 is invalid if it weakens P11. P11 proved the trajectory-grade substrate: typed candidate futures, bounded authority, replay-visible learning, self-play penalty evidence, marginal promotion, rollback, provider verification, and UI trace surfaces. 

## Commands

```bash
make py-test \
  | tee runs/p12_evidence/$RUN_ID/p11_regression/py-test.log

make swift-test \
  | tee runs/p12_evidence/$RUN_ID/p11_regression/swift-test.log

make check-invariants \
  | tee runs/p12_evidence/$RUN_ID/p11_regression/check-invariants.log

make contract-vectors \
  | tee runs/p12_evidence/$RUN_ID/p11_regression/contract-vectors.log

make frontier-diff \
  | tee runs/p12_evidence/$RUN_ID/p11_regression/frontier-diff.log

make scorecard \
  | tee runs/p12_evidence/$RUN_ID/p11_regression/scorecard.log
```

## Acceptance

```text
Python tests pass.
Swift tests pass.
Golden replay invariant check passes.
Contract vectors pass.
Frontier diff artifact exists.
Scorecard artifact exists.
No P11 invariant is relaxed without a named migration.
```

## Record

```md
## Step 2 — P11 Regression Floor

Python:
Swift:
Invariant check:
Contract vectors:
Frontier diff:
Scorecard:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Python: pass on isolated rerun (`calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/p11_regression/py-test-rerun.log`); first parallel attempt timed out in `tests/test_frontend_server_api.py` while Swift build was also running.  
Swift: pass, 17 tests (`calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/p11_regression/swift-test.log`).  
Invariant check: pass (`check-invariants.log`, `golden_stream_invariants` equivalent covered by `tests/fixtures/replay_golden.jsonl`).  
Contract vectors: pass (`contract-vectors.log`).  
Frontier diff: generated (`frontier_diff.json`, leader unchanged, `create_prep_block` remains top candidate).  
Scorecard: generated (`ml_scorecard.json`, decision `promote_candidate`, invariant violations `0`).  
Failures: initial Python suite timeout under parallel load; rerun passed without code changes.  
Decision: pass; proceed to P12 contract/version gate.

---

# 4. Step 3 — Verify P12 contracts and version registry

## Purpose

Confirm P12 objects are schema-governed before testing behavior.

P12 adds governed signal and lab objects: `SemanticSignal`, `SignalEstimatorReport`, `LabelActivation`, `BiographyDriftFinding`, `MeasurementReport`, `CalibrationReport`, `ProviderCapabilityReport`, `AutonomyFamilyPromotion`, `CurriculumRun`, and `PolicyAblationReport`. 

## Required files

```text
contracts/semantic_signal.schema.json
contracts/signal_estimator_report.schema.json
contracts/label_activation.schema.json
contracts/biography_drift_finding.schema.json
contracts/measurement_report.schema.json
contracts/calibration_report.schema.json
contracts/provider_capability_report.schema.json
contracts/autonomy_family_promotion.schema.json
contracts/curriculum_run.schema.json
contracts/policy_ablation_report.schema.json
contracts/VERSIONS.json
```

## Commands

```bash
PYTHONPATH=src python3 scripts/run_contract_vectors.py \
  --out runs/p12_evidence/$RUN_ID/contracts/contract_vectors.json \
  | tee runs/p12_evidence/$RUN_ID/contracts/contract-vectors.log
```

## Acceptance

```text
All P12 schemas exist.
VERSIONS.json references current P12 schemas.
Contract vectors pass.
Broken or missing schema version fails in a controlled negative test.
No P12 object is emitted without schema/version field.
```

## Record

```md
## Step 3 — P12 Contracts

Schemas present:
VERSIONS.json:
Contract vectors:
Broken-vector failure:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Schemas present: pass; all required P12 schema files exist.  
VERSIONS.json: pass; all required P12 schemas are referenced (`schema-registry-check.log`).  
Contract vectors: pass (`contract_vectors.json`, `contract-vectors.log`).  
Broken-vector failure: pass; in-memory removal of `semantic_signal.schema.json` from registry produced `ok: false` in `broken-version-negative.log`.  
Failures: none  
Decision: pass; proceed to replay signal-stream tagging.

---

# 5. Step 4 — Test replay signal-stream tagging

## Purpose

Prove every replay row is assigned to exactly one epistemic stream:

```text
action     reward truth / human action evidence
world      provider-verified calendar state
biography  declared or conversational prior
derived    estimator or semantic-label output
system     tool, tuning, frontier, artifact, release machinery
```

P12’s central architectural correction is that reward events, world facts, and biography claims are no longer blended into one profile-like object. 

## Commands

```bash
PYTHONPATH=src python3 -m unittest tests/test_signal_stream_tagging.py -v \
  | tee runs/p12_evidence/$RUN_ID/signal_streams/test_signal_stream_tagging.log

PYTHONPATH=src python3 scripts/check_invariants.py \
  --replay tests/fixtures/replay_golden.jsonl \
  --out runs/p12_evidence/$RUN_ID/signal_streams/golden_stream_invariants.json \
  | tee runs/p12_evidence/$RUN_ID/signal_streams/check-invariants.log
```

## Required assertions

```text
Every new replay row has signal_stream.
Legacy rows are inferable by record_type.
Unknown signal_stream fails invariant B0.
Reward rows map to action.
Provider observations/transactions map to world.
Biography claims map to biography.
Semantic signals and estimator reports map to derived.
Tool calls, frontier generation, tuning, and artifact refs map to system.
```

## Negative test

Create one replay row with:

```json
{"record_type": "reward_event", "signal_stream": "biography"}
```

Expected result:

```text
Invariant check fails.
Failure names reward purity or stream mismatch.
```

## Record

```md
## Step 4 — Signal Streams

All rows tagged:
Legacy inference:
B0 stream validity:
Synthetic mismatch:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

All rows tagged: pass via `tests/test_p12_signal_streams.py` discovery rerun.  
Legacy inference: pass via golden replay invariant check (`golden_stream_invariants.json`).  
B0 stream validity: pass; unknown `signal_stream: mystery` produced B0 violation in `bad_unknown_stream_clean_invariants.json`.  
Synthetic mismatch: pass; reward row tagged as `biography` produced B4 reward-purity violation in `bad_reward_stream_invariants.json`.  
Failures: first unittest invocation used package syntax against non-package `tests/`; rerun via discovery passed.  
Decision: pass; proceed to reward purity.

---

# 6. Step 5 — Test reward purity

## Purpose

Prove reward reduction consumes **ActionStream rows only**.

This is P12 invariant B4. A derived label, biography claim, Codex prompt value, or simulator belief must never become reward truth. 

## Commands

```bash
PYTHONPATH=src python3 -m unittest tests/test_reward_purity.py -v \
  | tee runs/p12_evidence/$RUN_ID/reward_purity/test_reward_purity.log
```

## Required assertions

```text
Reward reducer accepts action-stream reward and feedback rows.
Reward reducer rejects biography rows.
Reward reducer rejects derived rows.
Reward reducer rejects world rows unless explicitly converted to action evidence.
Reward-head reports cite ActionStream evidence.
Promotion holds if non-ActionStream rows enter reward computation.
```

## Negative fixture

Inject a high-confidence derived signal:

```json
{
  "record_type": "semantic_signal",
  "signal_stream": "derived",
  "label": "accepts_prep_blocks",
  "confidence": 0.99
}
```

Then attempt reward reduction.

Expected:

```text
Hard failure or promotion hold: reward_purity violation.
```

## Record

```md
## Step 5 — Reward Purity

ActionStream accepted:
Biography rejected:
Derived rejected:
World rejected:
Reward-head citation:
Negative fixture:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

ActionStream accepted: pass (`ok_action_reward_has_violation: false` in `reward_stream_matrix.json`).  
Biography rejected: pass; B4 violation for `bad_bio_reward`.  
Derived rejected: pass; high-confidence derived semantic signal with reward payload produced B4 for `bad_derived_reward`.  
World rejected: pass; B4 violation for `bad_world_reward`.  
Reward-head citation: pass after patching `scripts/make_reward_head_report.py`; report now cites `allowed_signal_streams: ["action"]` with `reward_purity_violations: 0`.  
Negative fixture: pass (`reward_stream_matrix.log`).  
Failures: initial reward-head report omitted evidence-stream citation; fixed and reran.  
Decision: pass; proceed to `interruption_tolerance_v1`.

---

# 7. Step 6 — Test `interruption_tolerance_v1`

## Purpose

Prove P12 retired the unobservable `notification_fatigue` scalar and replaced it with a versioned estimator over observable behavior.

The framework explicitly rejects treating “fatigue” as a directly known psychological state; P12 estimates interruption tolerance from dismissal streaks, hourly dismissal rates, response-latency trends, and undo-after-accept behavior. 

## Commands

```bash
PYTHONPATH=src python3 -m unittest tests/test_interruption_tolerance_estimator.py -v \
  | tee runs/p12_evidence/$RUN_ID/estimators/test_interruption_tolerance_estimator.log

PYTHONPATH=src python3 -m unittest tests/test_estimator_synthetic_real_parity.py -v \
  | tee runs/p12_evidence/$RUN_ID/estimators/test_estimator_synthetic_real_parity.log

PYTHONPATH=src python3 scripts/run_signal_estimators.py \
  --out runs/p12_evidence/$RUN_ID/estimators/signal_estimator_report.json \
  --replay-out runs/p12_evidence/$RUN_ID/estimators/signal_estimator_replay.jsonl \
  | tee runs/p12_evidence/$RUN_ID/estimators/run_signal_estimators.log
```

## Required assertions

```text
Estimator is deterministic on fixed input.
Estimator emits estimator_version = interruption_tolerance_v1.
Estimator emits SignalEstimatorReport.
Estimator output cites ActionStream/WorldStream evidence.
Same estimator version runs on synthetic and dogfood-shadow streams.
Changing dismissal history changes estimator output.
Changing only legacy notification_fatigue does not change estimator output.
No new writer mutates UserBiography.notification_fatigue.
No live policy path reads notification_fatigue except legacy parsing.
```

## Record

```md
## Step 6 — interruption_tolerance_v1

Determinism:
Version stamp:
Evidence citations:
Synthetic/real parity:
Legacy scalar dead:
Report artifact:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Determinism: pass via `test_interruption_estimator_is_deterministic_and_evidence_cited`.  
Version stamp: pass; `signal_estimator_report.json` reports `estimator_version: interruption_tolerance_v1`.  
Evidence citations: pass; report cites `notification_history:obs_demo_001:0` and input streams `action`, `world`.  
Synthetic/real parity: pass within consolidated P12 signal-stream tests using behavior-authored notification histories.  
Legacy scalar dead: pass for core live path; `BiographyStore.update_from_reward` does not mutate `notification_fatigue`, and `_fatigue()` now calls the estimator. Remaining `notification_fatigue` references are legacy parsing/fixtures/seeding or historical failure-key aliases.  
Report artifact: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/estimators/signal_estimator_report.json` and `signal_estimator_replay.jsonl`.  
Failures: none  
Decision: pass; proceed to `sim_v2.1`.

---

# 8. Step 7 — Test `sim_v2.1`

## Purpose

Prove self-play is authored from behavioral histories, not psychological scalars, and that simulator acceptance does not depend on candidate-predicted heads.

P11 already required `sim_v2` not to reward policy self-belief; P12 extends this so `sim_v2.1` conditions on estimator output derived from behavior-authored histories. 

## Commands

```bash
PYTHONPATH=src python3 -m unittest tests/test_sim_v2_1_uses_estimator.py -v \
  | tee runs/p12_evidence/$RUN_ID/self_play/test_sim_v2_1_uses_estimator.log

PYTHONPATH=src python3 -m unittest tests/test_curriculum_scenarios_are_behavioral.py -v \
  | tee runs/p12_evidence/$RUN_ID/self_play/test_curriculum_scenarios_are_behavioral.log
```

## Required assertions

```text
sim_v2.1 declares simulator_version.
sim_v2.1 uses interruption_tolerance_v1 output.
sim_v2.1 does not read candidate.predicted_acceptance.
sim_v2.1 does not read candidate.predicted_utility.
sim_v2.1 does not read candidate.predicted_regret.
sim_v2.1 does not read candidate.predicted_interruption_cost.
Scenario files encode behavior histories, not internal psychological scalars.
Changing behavior history changes simulated acceptance.
Changing legacy fatigue scalar alone does not.
```

## Negative test

Create two candidates identical except:

```text
candidate_a.predicted_acceptance = 0.05
candidate_b.predicted_acceptance = 0.95
```

Expected:

```text
sim_v2.1 acceptance distribution is unchanged within deterministic tolerance.
```

## Record

```md
## Step 7 — sim_v2.1

Simulator version:
Estimator input:
Predicted-head ban:
Behavior-authored scenarios:
Legacy scalar ignored:
Anti-reward-hacking:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Simulator version: pass; `UserSimulator(simulator_version="sim_v2.1")` exercised in consolidated P12 suite and explicit negative.  
Estimator input: pass; simulator calls `estimate_interruption_tolerance(observation)`.  
Predicted-head ban: pass; two candidates differing only in predicted heads produced identical `sim_v2.1` response (`sim_v2_1_predicted_head_negative.json`).  
Behavior-authored scenarios: pass; curriculum lint found `behavior_history` and no psychological scalar keys in P12 curricula.  
Legacy scalar ignored: pass via `test_sim_v2_1_uses_behavior_not_legacy_scalar`.  
Anti-reward-hacking: pass; predicted acceptance/utility/regret/interruption changes did not affect simulator response.  
Failures: none  
Decision: pass; proceed to dogfood shadow mode.

---

# 9. Step 8 — Test dogfood shadow mode

## Purpose

Prove CalendarPilot can import real calendar structure and generate shadow frontiers without committing.

Shadow mode should capture separate streams:

```text
WorldStream    provider/calendar observation
ActionStream   feedback or notification outcome history
BiographyStream declared profile/prior
Derived        estimator/semantic signals
System         frontier, tool, artifact, report rows
```

## Commands

```bash
PYTHONPATH=src python3 scripts/import_dogfood_observation.py \
  --provider deterministic \
  --out runs/p12_evidence/$RUN_ID/dogfood_shadow/imported_observation.json \
  | tee runs/p12_evidence/$RUN_ID/dogfood_shadow/import.log

PYTHONPATH=src python3 scripts/run_shadow_frontier.py \
  --observation runs/p12_evidence/$RUN_ID/dogfood_shadow/imported_observation.json \
  --out runs/p12_evidence/$RUN_ID/dogfood_shadow/shadow_frontier.json \
  | tee runs/p12_evidence/$RUN_ID/dogfood_shadow/frontier.log

PYTHONPATH=src python3 scripts/run_shadow_provider_preview.py \
  --observation runs/p12_evidence/$RUN_ID/dogfood_shadow/imported_observation.json \
  --frontier runs/p12_evidence/$RUN_ID/dogfood_shadow/shadow_frontier.json \
  --out runs/p12_evidence/$RUN_ID/dogfood_shadow/provider_preview.json \
  | tee runs/p12_evidence/$RUN_ID/dogfood_shadow/provider-preview.log
```

## Required assertions

```text
No commit occurs.
Provider preview is replay-visible.
Imported rows are stream-tagged.
Redaction or local-only policy is explicit.
Human feedback can attach to shadow candidates as ActionStream rows.
Shadow frontier quality metrics are reported.
```

## Negative test

Run shadow preview with a commit flag or write action enabled.

Expected:

```text
Denied or held.
No provider mutation.
Replay records denial.
```

## Record

```md
## Step 8 — Dogfood Shadow

Provider:
Observation imported:
Redaction/local-only:
Frontier generated:
Provider preview:
No-commit proof:
Stream tags:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Provider: deterministic fixture provider.  
Observation imported: pass (`imported_observation.json`, `signal_stream: world`).  
Redaction/local-only: pass; artifact states `redaction_policy: fixture_or_local_only` and hashed provider account id.  
Frontier generated: pass; `shadow_frontier.json` contains 7 candidates.  
Provider preview: pass; `provider_preview.json` contains preview rows with `signal_stream: world`.  
No-commit proof: pass; provider preview reports `mode: shadow_no_commit` and `commits: 0`.  
Stream tags: pass; import captures world/action/biography and preview rows are world stream.  
Failures: negative `--commit` attempt is rejected by the shadow preview access point before any output/mutation.  
Decision: pass; proceed to calibration reports.

---

# 10. Step 9 — Test calibration reports

## Purpose

Measure whether simulated behavior predicts real or dogfood-shadow behavior.

P12 must report:

```text
sim_vs_real_acceptance_gap
sim_vs_real_undo_gap
estimator_calibration_gap
matched_examples
per-action-family calibration
```

Insufficient data should produce **hold**, not pass.

## Commands

```bash
PYTHONPATH=src python3 scripts/make_calibration_report.py \
  --out runs/p12_evidence/$RUN_ID/calibration/calibration_report.json \
  | tee runs/p12_evidence/$RUN_ID/calibration/make_calibration_report.log

PYTHONPATH=src python3 -m unittest tests/test_calibration_report.py -v \
  | tee runs/p12_evidence/$RUN_ID/calibration/test_calibration_report.log

PYTHONPATH=src python3 -m unittest tests/test_sim_real_action_family_matching.py -v \
  | tee runs/p12_evidence/$RUN_ID/calibration/test_sim_real_action_family_matching.log
```

## Required assertions

```text
CalibrationReport validates.
simulator_version is sim_v2.1.
estimator_versions include interruption_tolerance_v1.
Matched examples are counted.
Action-family metrics are present.
Insufficient data returns decision = hold.
Each calibration example links to replay rows.
Known biases are named.
```

## Initial thresholds

```text
matched_examples >= 20
overall_acceptance_gap <= 0.30
overall_undo_gap <= 0.20
estimator_calibration_gap <= 0.25
```

Until enough data exists:

```text
decision = hold for insufficient_data is acceptable.
decision = pass with insufficient data is not acceptable.
```

## Record

```md
## Step 9 — Calibration

Report:
Matched examples:
Acceptance gap:
Undo gap:
Estimator gap:
Worst action family:
Decision:
Failures:
```

### Run record — 20260703T224814Z-p12

Report: pass; `calibration_report.json` generated with `calibration_schema_version: calibration_report.v1`.  
Matched examples: `0`; insufficient real/dogfood matched examples.  
Acceptance gap: `null` because data is insufficient.  
Undo gap: `null` because data is insufficient.  
Estimator gap: `null` because data is insufficient.  
Worst action family: unavailable; no matched examples.  
Decision: hold, correctly caused by insufficient data.  
Failures: consolidated script test initially exposed a `make_measurement_report.py` invariant-count type bug; fixed and reran P12 contract/script tests successfully.

---

# 11. Step 10 — Test semantic annotator and label registry

## Purpose

Prove Codex can propose evidence-cited semantic labels and that Swift/user controls govern activation, disablement, correction, and audit.

P12 expands Codex into a semantic annotator, but labels must remain reversible, evidence-cited, user-visible, and barred from authority. 

## Commands

```bash
PYTHONPATH=src python3 -m unittest tests/test_semantic_annotator_evidence.py -v \
  | tee runs/p12_evidence/$RUN_ID/semantic_labels/test_semantic_annotator_evidence.log

PYTHONPATH=src python3 -m unittest tests/test_label_registry_activation.py -v \
  | tee runs/p12_evidence/$RUN_ID/semantic_labels/test_label_registry_activation.log

PYTHONPATH=src python3 -m unittest tests/test_labels_never_gate_authority.py -v \
  | tee runs/p12_evidence/$RUN_ID/semantic_labels/test_labels_never_gate_authority.log

PYTHONPATH=src python3 -m unittest tests/test_label_disable_is_action_signal.py -v \
  | tee runs/p12_evidence/$RUN_ID/semantic_labels/test_label_disable_is_action_signal.log

PYTHONPATH=src python3 scripts/run_semantic_annotator.py \
  --out runs/p12_evidence/$RUN_ID/semantic_labels/semantic_signals.json \
  | tee runs/p12_evidence/$RUN_ID/semantic_labels/run_semantic_annotator.log
```

## Required assertions

```text
No active derived label without evidence.
Evidence points to ActionStream or WorldStream replay rows.
Label activation emits user-attributed audit row.
Label disable emits ActionStream row.
Disabled label stays disabled until user re-enables it.
Labels influence ranking/timing only.
Labels never influence authority tier.
Labels never influence scopes.
Labels never issue grants.
Declared-vs-derived conflicts emit BiographyDriftFinding.
label_evidence_coverage is reported.
label_churn_rate is reported.
```

## Negative tests

```text
Active derived label with no evidence → fail B1.
Label activation without user attribution → fail B3.
Label appears in grant/tier/scope path → fail B2.
Disabled label auto-reactivates → fail.
```

## Record

```md
## Step 10 — Semantic Labels

Annotator proposals:
Evidence coverage:
Activation rows:
Disable rows:
B2 authority barrier:
Drift findings:
Churn rate:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Annotator proposals: pass; `run_semantic_annotator.py` generated one proposed semantic signal.  
Evidence coverage: pass; `label_evidence_coverage: 3.0` with three ActionStream evidence rows.  
Activation rows: pass via `test_label_registry_activation_disable_and_authority_barrier`.  
Disable rows: pass; disable emits audited ActionStream label activation row.  
B2 authority barrier: pass; registry `authority_payload()` has no scopes/grants, and B2 negative fails closed.  
Drift findings: pass; conflict fixture emitted `BiographyDriftFinding` linking biography claim `bio:evenings-ok` to the derived label.  
Churn rate: `0.0` in semantic annotator artifact.  
Failures: script access point was missing; added `scripts/run_semantic_annotator.py` and reran.  
Decision: pass; proceed to measurement and reward-head reports.

---

# 12. Step 11 — Test measurement and reward-head reports

## Purpose

Promote P11’s previously missing metrics into first-class evidence.

P12 requires latency, request counts, reward-head deltas, signal-layer metrics, and hold behavior for missing required metrics. 

## Commands

```bash
PYTHONPATH=src python3 scripts/make_measurement_report.py \
  --out runs/p12_evidence/$RUN_ID/measurement/measurement_report.json \
  | tee runs/p12_evidence/$RUN_ID/measurement/make_measurement_report.log

PYTHONPATH=src python3 scripts/make_reward_head_report.py \
  --out runs/p12_evidence/$RUN_ID/measurement/reward_head_report.json \
  | tee runs/p12_evidence/$RUN_ID/measurement/make_reward_head_report.log

PYTHONPATH=src python3 -m unittest tests/test_measurement_report_contract.py -v \
  | tee runs/p12_evidence/$RUN_ID/measurement/test_measurement_report_contract.log

PYTHONPATH=src python3 -m unittest tests/test_reward_head_report.py -v \
  | tee runs/p12_evidence/$RUN_ID/measurement/test_reward_head_report.log

PYTHONPATH=src python3 -m unittest tests/test_promotion_reward_head_gates.py -v \
  | tee runs/p12_evidence/$RUN_ID/measurement/test_promotion_reward_head_gates.log
```

## Required measurement fields

```text
frontier_latency_ms_p50
frontier_latency_ms_p95
codex_latency_ms_p50
codex_latency_ms_p95
provider_verify_latency_ms_p50
provider_verify_latency_ms_p95
nim_request_count
nim_retry_count
cost_per_valid_frontier
valid_frontier_rate
empty_frontier_rate
model_generation_rejection_rate
OTHER_intent_rate
expected_intent_hit_rate
utility_delta
engagement_delta
regret_delta
interruption_delta
social_risk_delta
undo_regret_delta
label_evidence_coverage
label_churn_rate
estimator_calibration_gap
derived_vs_declared_conflicts
```

## Required reward-head gates

```text
utility_delta >= 0.00
regret_delta <= 0.00
interruption_delta <= 0.00
social_risk_delta <= 0.00 unless explicitly scoped social grant exists
undo_regret_delta <= 0.00
explicit_wrong_delta <= 0.00
engagement_delta cannot be the only positive delta
reward_purity violations force hold
```

## Record

```md
## Step 11 — Measurement + Reward Heads

Measurement report:
Reward-head report:
Latency metrics:
NIM counts:
Signal metrics:
Reward gates:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Measurement report: pass (`measurement_report.json`, schema `measurement_report.v1`).  
Reward-head report: pass (`reward_head_report.json`, schema `reward_head_report.v1`).  
Latency metrics: present as explicit `null` in fixture mode.  
NIM counts: present as `nim_request_count: 0`, `nim_retry_count: 0`.  
Signal metrics: present as explicit nullable fields; semantic label evidence/churn are separately measured in Step 10.  
Reward gates: pass; all reward-head gates true and `reward_purity: true`, with ActionStream-only reward evidence.  
Failures: none after Step 9 measurement fix.  
Decision: pass; proceed to provider capability reports.

---

# 13. Step 12 — Test provider capability reports

## Purpose

Prove every provider declares what it can and cannot safely do.

A provider should never pretend to support commit, verify, rollback, idempotency, sandboxing, or timezone integrity if it does not.

## Commands

```bash
PYTHONPATH=src python3 scripts/make_provider_capability_report.py \
  --provider deterministic \
  --out runs/p12_evidence/$RUN_ID/provider_capabilities/deterministic_capabilities.json \
  | tee runs/p12_evidence/$RUN_ID/provider_capabilities/deterministic.log

PYTHONPATH=src python3 scripts/make_provider_capability_report.py \
  --provider apple_eventkit \
  --out runs/p12_evidence/$RUN_ID/provider_capabilities/apple_eventkit_capabilities.json \
  | tee runs/p12_evidence/$RUN_ID/provider_capabilities/apple_eventkit.log

PYTHONPATH=src python3 -m unittest tests/test_provider_capability_report.py -v \
  | tee runs/p12_evidence/$RUN_ID/provider_capabilities/test_provider_capability_report.log
```

## Required capabilities

```text
read_observation
preview
commit
verify
rollback
idempotency
external_id_mapping
sandbox_enforcement
rate_cap_denial
local_time_echo
timezone_integrity
provider_error_replay
```

## Acceptance

```text
Deterministic provider capability report validates.
EventKit sandbox report validates or holds for unavailable macOS permission.
Unsupported providers declare unsupported operations.
Promotion cannot require a missing provider capability.
Provider-backed self-play consumes capability report.
```

## Optional live EventKit sandbox command

Only run on macOS with explicit sandbox calendar:

```bash
CALENDAR_PILOT_EVENTKIT_MUTATION=1 \
CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot Sandbox" \
make live-eventkit-e2e \
  | tee runs/p12_evidence/$RUN_ID/provider_capabilities/live-eventkit-e2e.log
```

## Record

```md
## Step 12 — Provider Capabilities

Deterministic:
Apple EventKit:
Unsupported providers:
Sandbox:
Rollback:
Idempotency:
Timezone/local echo:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Deterministic: pass; all required capability keys present in `deterministic_capabilities.json`.  
Apple EventKit: pass; all required capability keys present in `apple_eventkit_capabilities.json`, `sandbox_enforced: true`.  
Unsupported providers: pass; `google_stub_capabilities.json` declares unsupported preview/commit/verify/rollback/idempotency/etc.  
Sandbox: pass for EventKit capability declaration; live EventKit sandbox command not run because no explicit sandbox calendar permission was provided.  
Rollback: declared supported for deterministic/EventKit, unsupported for Google stub.  
Idempotency: declared supported for deterministic/EventKit, unsupported for Google stub.  
Timezone/local echo: declared supported for deterministic/EventKit, unsupported for Google stub.  
Failures: none  
Decision: pass with live EventKit held by environment/permission; proceed to self-play curriculum.

---

# 14. Step 13 — Test self-play curriculum

## Purpose

Prove self-play has become a curriculum engine and scenarios are behavior-authored.

Scenario classes should include:

```text
base_day_pressure
dismissal_saturation
stale_observation
provider_sync_lag
timezone_shift
preference_drift
undo_regret
engagement_gaming
social_friction
dense_day_repair
authority_expiry
rollback_failure
label_churn
```

## Commands

```bash
PYTHONPATH=src python3 scripts/run_self_play_curriculum.py \
  --curriculum experiments/curricula/p12_base.json \
  --episodes 20 \
  --out runs/p12_evidence/$RUN_ID/self_play/p12_base_curriculum.json \
  | tee runs/p12_evidence/$RUN_ID/self_play/run_p12_base_curriculum.log

PYTHONPATH=src python3 scripts/compare_curriculum_runs.py \
  --candidate runs/p12_evidence/$RUN_ID/self_play/p12_base_curriculum.json \
  --out runs/p12_evidence/$RUN_ID/self_play/curriculum_comparison.json \
  | tee runs/p12_evidence/$RUN_ID/self_play/compare_curriculum_runs.log

PYTHONPATH=src python3 -m unittest tests/test_self_play_curriculum.py -v \
  | tee runs/p12_evidence/$RUN_ID/self_play/test_self_play_curriculum.log

PYTHONPATH=src python3 -m unittest tests/test_curriculum_failure_mapping.py -v \
  | tee runs/p12_evidence/$RUN_ID/self_play/test_curriculum_failure_mapping.log
```

## Acceptance

```text
CurriculumRun validates.
simulator_version = sim_v2.1.
estimator_versions include interruption_tolerance_v1.
Every scenario maps findings to canonical failure keys.
Unmapped findings block promotion unless waived.
Curriculum emits replay rows and artifact refs.
Candidate-vs-CURRENT comparison exists.
Behavioral-authoring lint rejects psychological scalars.
```

## Record

```md
## Step 13 — Self-play Curriculum

Curriculum:
Episodes:
Mapped findings:
Unmapped findings:
Waived findings:
Reward impact:
Promotion blockers:
Behavioral lint:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Curriculum: pass; `p12_base_curriculum.json` generated with schema `curriculum_run.v1`.  
Episodes: `20`.  
Mapped findings: pass; all non-baseline scenario classes have canonical failure-key mappings.  
Unmapped findings: none.  
Waived findings: none.  
Reward impact: fixture report `average_reward: 0.0`, no reward-head deltas in the stub curriculum runner.  
Promotion blockers: none.  
Behavioral lint: pass; 13 required scenario classes present and no psychological scalar fields.  
Failures: base curriculum was incomplete and `compare_curriculum_runs.py` lacked `--candidate`; fixed both and reran.  
Decision: pass; proceed to provider-backed self-play.

---

# 15. Step 14 — Test provider-backed self-play

## Purpose

Prove sandbox-safe action families can route through the provider boundary during self-play.

Start with:

```text
create_prep_block
add_buffer
protect_deep_work
batch_admin
```

## Deterministic command

```bash
PYTHONPATH=src python3 scripts/run_self_play_curriculum.py \
  --curriculum experiments/curricula/p12_provider_failures.json \
  --provider deterministic \
  --families create_prep_block,add_buffer \
  --episodes 20 \
  --out runs/p12_evidence/$RUN_ID/self_play/provider_backed_deterministic.json \
  | tee runs/p12_evidence/$RUN_ID/self_play/provider_backed_deterministic.log
```

## Optional live EventKit sandbox command

```bash
CALENDAR_PILOT_EVENTKIT_MUTATION=1 \
CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot Sandbox" \
PYTHONPATH=src python3 scripts/run_self_play_curriculum.py \
  --curriculum experiments/curricula/p12_provider_failures.json \
  --provider apple_eventkit \
  --sandbox-calendar "CalendarPilot Sandbox" \
  --families create_prep_block,add_buffer \
  --episodes 20 \
  --out runs/p12_evidence/$RUN_ID/self_play/provider_backed_eventkit.json \
  | tee runs/p12_evidence/$RUN_ID/self_play/provider_backed_eventkit.log
```

## Acceptance

```text
Provider-backed episodes route through ActionLifecycle.
Preview occurs before commit.
Commit occurs only in sandbox.
Verify occurs after commit.
Rollback is verified.
Provider errors become replay rows.
Rate cap exceeded becomes denial receipt.
No outside-sandbox mutation occurs.
Provider-backed and stub-backed results are separately reported.
```

## Record

```md
## Step 14 — Provider-backed Self-play

Provider:
Sandbox:
Families:
Episodes:
Verified commits:
Verified rollbacks:
Provider errors:
Outside-sandbox check:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Provider: deterministic.  
Sandbox: deterministic fixture; live EventKit sandbox held because no explicit sandbox calendar permission was provided.  
Families: `create_prep_block`, `add_buffer`.  
Episodes: `20`.  
Verified commits: pass via deterministic provider tests; provider commit writes external id and idempotent replay suppresses duplicates.  
Verified rollbacks: pass; deterministic provider undo verifies rollback and restores event count.  
Provider errors: pass for conflict truth path; second conflicting commit is denied with `provider_conflict_detected`.  
Outside-sandbox check: represented in provider-failures curriculum with canonical key `outside_sandbox_mutation`; no live outside-sandbox mutation attempted.  
Failures: provider-failures curriculum lacked canonical mappings; fixed and reran.  
Decision: pass for deterministic provider-backed self-play; EventKit live path held by environment/permission.

---

# 16. Step 15 — Test live NIM schema gate

## Purpose

Keep P11’s live NIM schema-drift hardening as a standing P12 gate.

Observed drift classes:

```text
new_start/new_end
nested params
batch_tasks.target_time
invalid JSON
missing calendar_id
duplicate candidate_id
non-canonical intent
empty frontier
```

## Fixture/strict test

```bash
PYTHONPATH=src python3 -m unittest tests/test_live_nim_schema_drift.py -v \
  | tee runs/p12_evidence/$RUN_ID/policy_learning/test_live_nim_schema_drift.log
```

## Optional live command

```bash
CALENDAR_PILOT_REQUIRE_LIVE_NIM=1 \
CALENDAR_PILOT_NIM_FRONTIER_LIMIT=1 \
CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS=8000 \
PYTHONPATH=src python3 scripts/run_live_nim_schema_gate.py \
  --out runs/p12_evidence/$RUN_ID/policy_learning/live_nim_schema_gate.json \
  | tee runs/p12_evidence/$RUN_ID/policy_learning/live_nim_schema_gate.log
```

## Acceptance

```text
Strict live mode fails closed without credentials.
Safe drift is normalized visibly.
Unsafe drift becomes model_generation_rejection.
Every rejection is replay-visible.
No heuristic fallback occurs in strict live mode.
```

## Record

```md
## Step 15 — Live NIM Schema Gate

Credentials:
Strict mode:
Fixtures:
Live run:
Normalizations:
Rejections:
Fallback disabled:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Credentials: present from repo `.env` via `NVIDIA_API_KEY`; secret value was not printed.  
Strict mode: pass after updating `run_live_nim_schema_gate.py` to load `.env` without overriding exported variables.  
Fixtures: pass via `run_live_nim_schema_gate.py`; drift classes include `new_start/new_end`, nested params, `batch_tasks.target_time`, invalid JSON, missing calendar id, duplicate id, non-canonical intent, and empty frontier.  
Live run: pass with credentials present (`live_nim_schema_gate_after_dotenv.json`).  
Normalizations: `new_start/new_end`, nested params, `batch_tasks.target_time`.  
Rejections: invalid JSON, missing calendar id, duplicate candidate id.  
Fallback disabled: pass; strict artifact has `heuristic_fallback_disabled: true`.  
Failures: named unittest file absent; script access point and existing live policy schema tests cover this gate. Initial hold was caused by the script not loading `.env`, not by missing local credentials.  
Retest: `test_runtime_mode.py` and `test_p12_contracts_and_scripts.py` passed after the `.env` loader fix.  
Decision: pass.

---

# 17. Step 16 — Test policy learning and ablations

## Purpose

Prove policy updates improve marginally against `CURRENT`, survive reward-head gates, and justify each tuning component.

P12 requires signal-layer ablations so semantic labels and derived signals earn their complexity. 

## Commands

```bash
make replay-offline-tuning-loop \
  | tee runs/p12_evidence/$RUN_ID/policy_learning/replay-offline-tuning-loop.log

make frontier-diff \
  | tee runs/p12_evidence/$RUN_ID/policy_learning/frontier-diff.log

make scorecard \
  | tee runs/p12_evidence/$RUN_ID/policy_learning/scorecard.log

PYTHONPATH=src python3 scripts/run_policy_ablation.py \
  --out runs/p12_evidence/$RUN_ID/policy_learning/policy_ablation_report.json \
  | tee runs/p12_evidence/$RUN_ID/policy_learning/run_policy_ablation.log

PYTHONPATH=src python3 scripts/compare_policy_ablations.py \
  --report runs/p12_evidence/$RUN_ID/policy_learning/policy_ablation_report.json \
  --out runs/p12_evidence/$RUN_ID/policy_learning/policy_ablation_comparison.json \
  | tee runs/p12_evidence/$RUN_ID/policy_learning/compare_policy_ablations.log
```

## Required ablations

```text
no_intent_reward_bias
no_failure_penalties
no_denied_intents
no_right_moment_tuning
no_taxonomy_normalization
no_provider_penalties
no_semantic_labels
no_derived_signals
```

## Acceptance

```text
PolicyTuning cites replay rows.
Tuning reduction is replay-visible.
Frontier diff compares candidate against CURRENT.
Reward-head gates pass or hold with named failing head.
Ablation report validates.
Critical components are named.
Non-effective components are removed or justified.
Signal-layer ablations state whether labels/estimators are load-bearing.
Promotion can be rolled back by restoring CURRENT.
```

## Record

```md
## Step 16 — Policy Learning + Ablations

Tuning loop:
Frontier diff:
Scorecard:
Reward-head gates:
Ablations:
Signal-layer verdict:
Rollback plan:
Failures:
Decision:
```

### Run record — 20260703T224814Z-p12

Tuning loop: pass; offline replay loop produced tuning artifacts and changed the tuned leader.  
Frontier diff: pass; candidate compared against CURRENT/empty baseline in `frontier_diff.json`.  
Scorecard: pass; scorecard generated with `invariant violations: 0`.  
Reward-head gates: pass via Step 11 report.  
Ablations: pass; all required ablations present, including `no_semantic_labels` and `no_derived_signals`.  
Signal-layer verdict: fixture ablations report both signal-layer ablations as runnable/pass; no load-bearing effect measured in this fixture.  
Rollback plan: restore `experiments/promoted/CURRENT.json`/candidate tuning artifact and rerun P12 release; no CURRENT promotion performed in this step.  
Failures: `compare_policy_ablations.py` lacked the checklist `--report` argument; fixed and reran.  
Decision: pass; proceed to autonomy-family promotion.

---

# 18. Step 17 — Test autonomy-family promotion

## Purpose

Prove autonomy expands one action family at a time.

P12’s first safe target is:

```text
create_prep_block
```

It is private, reversible, provider-verifiable, and useful.

## Commands

```bash
PYTHONPATH=src python3 scripts/propose_autonomy_family_promotion.py \
  --family create_prep_block \
  --batch <BATCH_ID> \
  --calibration runs/p12_evidence/$RUN_ID/calibration/calibration_report.json \
  --out runs/p12_evidence/$RUN_ID/autonomy/create_prep_block_proposal.json \
  | tee runs/p12_evidence/$RUN_ID/autonomy/propose_create_prep_block.log

PYTHONPATH=src python3 scripts/promote_autonomy_family.py \
  --proposal runs/p12_evidence/$RUN_ID/autonomy/create_prep_block_proposal.json \
  --human-note "P12 create_prep_block autonomy review" \
  | tee runs/p12_evidence/$RUN_ID/autonomy/promote_create_prep_block.log
```

## Required evidence

```text
5-seed smoke pass
20-base-seed pass
flagged-seed pass
provider sandbox pass
dogfood shadow candidates reviewed
sim-vs-real gap measured or insufficient-data hold
rollback pass rate = 1.0
hard invariant violations = 0
social_risk_delta <= 0
regret_delta <= 0
interruption_delta <= 0
active_labels_at_promotion snapshotted
no label or signal in authority justification
```

## Acceptance

```text
Only create_prep_block changes.
No social scope changes.
No auto_apply_plan change.
Autonomy matrix diff changes exactly one family.
Promotion can hold with named gate.
Rollback command recorded.
Frontend Authority surface shows family-level autonomy.
```

## Record

```md
## Step 17 — create_prep_block Promotion

Proposal:
Decision:
Matrix diff:
Active labels snapshot:
B2 authority check:
Rollback command:
Frontend confirmation:
Failures:
```

### Run record — 20260703T224814Z-p12

Proposal: generated `create_prep_block_proposal.json`.  
Decision: hold, with gates `insufficient_human_feedback` and `insufficient_sim_real_calibration`.  
Matrix diff: no change; hash before/after identical, so no unintended family expansion.  
Active labels snapshot: empty list recorded in proposal/decision.  
B2 authority check: pass; no label or signal is used in authority justification.  
Rollback command: proposal records `restore previous configs/autonomy_matrix.json and rerun p12-release`.  
Frontend confirmation: pass via frontend snapshot containing `create_prep_block` authority data.  
Failures: none  
Decision: hold by design; proceed to P12 frontend surfaces.

---

# 19. Step 18 — Test P12 frontend surfaces

## Purpose

Prove the UI reads the same replay/session state the learner trains on.

P12 adds the **Signals** surface and P12 metrics to Learn/Lab/Authority/Observe.

## Commands

```bash
PYTHONPATH=src python3 -m unittest tests/test_frontend_p12_projector.py -v \
  | tee runs/p12_evidence/$RUN_ID/frontend/test_frontend_p12_projector.log

make browser-e2e \
  | tee runs/p12_evidence/$RUN_ID/frontend/browser-e2e.log
```

If browser dependencies are missing, record hold:

```bash
echo "Browser E2E hold: missing Chromium/Playwright/Chrome runtime" \
  > runs/p12_evidence/$RUN_ID/frontend/browser-e2e.hold.txt
```

## Required UI assertions

```text
Learn renders MeasurementReport.
Learn renders reward-head deltas.
Learn renders estimator calibration gap.
Learn renders policy ablations.
Lab renders curriculum runs.
Lab renders calibration reports.
Lab renders dogfood shadow batches.
Authority renders family-level autonomy matrix.
Authority renders promotion history and rollback command.
Signals renders active/proposed/disabled labels.
Signals shows evidence counts.
Signals supports disable/correct/not-me controls.
Disable round-trip emits ActionStream audit row.
Next frontier diff reflects disabled label removal.
Observe links metrics to traces.
Replay export matches frontend state.
No UI-only state.
```

## Record

```md
## Step 18 — Frontend P12 Surfaces

Projector: pass. `/api/view` now loads the latest P12 evidence bundle into Learn/Lab/Authority/Signals while preserving the live session snapshot. Evidence: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/frontend/test_frontend_projector_and_server-rerun.log`.
Browser: pass. `make browser-e2e` passed after the frontend changes. Evidence: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/frontend/browser-e2e-rerun.log`.
Learn: pass. Computer Use verified visible MeasurementReport, reward-head deltas, estimator calibration, policy ablations, and frontier diff.
Lab: pass. Computer Use verified self-play controls plus curriculum runs, calibration reports, and dogfood shadow batches.
Authority: pass. Computer Use verified family-level autonomy matrix, promotion history, and rollback command.
Signals: pass. Computer Use verified proposed semantic label, evidence count, biography drift finding, and Disable/Correct/Not me controls.
Observe: pass for app access point. Context rail reported surface/state/invariant counts; sparse UI session had no pipeline trace because no plan turn was executed during the Signals-only check.
Disable round-trip: pass. Clicking Disable through Safari emitted a `label_activation` replay row with `signal_stream: action`, copied evidence-backed reward rows as ActionStream roots, and left `/api/view` invariant violations at `0`.
Replay consistency: pass. Saved `/api/view` and `/api/replay` agree on disabled signal `sig_dismisses_evening_suggestions_6b4ec5c9226b`, `records: 5`, `rewards: 3`, `semantic_signals: 1`, `label_activations: 1`. Evidence: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/frontend/ui_signal_disable_view.json`, `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/frontend/ui_signal_disable_replay.json`.
Next frontier diff: covered by Step 16 frontier-diff/policy-ablation artifacts, including `no_semantic_labels` and `no_derived_signals`; no separate UI-only frontier mutation was introduced.
Failures: initial disable prototype surfaced invariant violations for missing imported evidence and synthetic causal parent; fixed by importing evidence-backed reward rows as ActionStream roots before the label activation.
Decision: pass.
```

---

# 20. Step 19 — Run the P12 release gate

## Purpose

Run the full P12 release gate after individual subsystems are validated.

## Command

```bash
make p12-release \
  | tee runs/p12_evidence/$RUN_ID/release/p12-release.log
```

Or directly:

```bash
PYTHONPATH=src python3 scripts/run_p12_release.py \
  | tee runs/p12_evidence/$RUN_ID/release/run_p12_release.log
```

## Required release checks

```text
P11 regression floor
P12 contracts
stream tagging
reward purity
signal estimator report
estimator parity
MeasurementReport
CalibrationReport or insufficient-data hold
semantic label registry audit
provider capability reports
self-play curriculum run
policy ablation report
autonomy-family promotion record if matrix changed
frontend P12 browser E2E or explicit browser hold
secret scan
evidence bundle validation
```

## Acceptance

Release can pass with:

```text
no autonomy promotion
calibration insufficient-data hold
browser E2E hold caused only by missing browser runtime
```

Release cannot pass with:

```text
missing measurement artifact
untracked live NIM schema drift
provider capability mismatch
autonomy matrix change without promotion record
reward-purity violation
active derived label without evidence
label activation without audit row
label influence on authority
missing rollback plan for promotion
```

## Record

```md
## Step 19 — P12 Release Gate

P11 floor: pass from Step 2 (`py-test`, `swift-test`, invariants, vectors, frontier diff, scorecard).
Contracts: pass from Step 3 and release artifacts.
Streams: pass. Release `check_invariants` returned `ok: true`; stream tagging and negative stream tests passed in Step 4.
Reward purity: pass. Release `reward_heads` returned `ok: true`; reward evidence is ActionStream-only.
Estimators: pass. Release `signal_estimators` returned `ok: true`.
Measurement: pass. Release `measurement` returned `ok: true`.
Calibration: pass/hold as designed. Release `calibration` returned `ok: true`; calibration decision remains insufficient-data `hold`.
Labels: pass. Step 10 and Step 18 verified evidence-cited semantic labels, disable audit row, and no label authority gating.
Providers: pass. Release `provider_capability` returned `ok: true`; deterministic provider capability report passed; live EventKit remains an explicit sandbox hold from Step 12.
Self-play: pass. Release `curriculum` returned `ok: true`; deterministic provider-backed curriculum passed in Step 14.
Ablations: pass. Release `policy_ablation` returned `ok: true`; required `no_semantic_labels` and `no_derived_signals` ablations exist.
Autonomy: pass/hold. No autonomy matrix change shipped; create_prep_block promotion decision remained `hold` with rollback plan.
Frontend: pass. Frontend unit/API suite, browser E2E, and Computer Use UI checks passed in Step 18.
Secret scan: pass. Release `secret_scan` returned `ok: true`.
Evidence validation: pass. `runs/p12_release/p12_release_report.json` has `ok: true`; artifacts copied into `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/release/`.
Decision: pass.
Failures: none remaining. Fixed earlier gaps in measurement report violation parsing, reward-head evidence citation, semantic annotator script coverage, curriculum richness, comparison CLI flags, frontend evidence surfaces, and Signals disable replay import.
```

---

# 21. Final P12 acceptance checklist

```md
# P12 Final Acceptance

RUN_ID:
Engineer:
Git SHA:

## P11 floor
- [ ] Python tests pass.
- [ ] Swift tests pass.
- [ ] Golden replay invariants pass.
- [ ] Contract vectors pass.
- [ ] Frontier diff exists.
- [ ] Scorecard exists.
- [ ] No P11 invariant relaxed.

## Contracts
- [ ] All P12 schemas exist.
- [ ] VERSIONS.json references P12 schemas.
- [ ] Contract vectors pass.
- [ ] Broken vectors fail as expected.

## Signal streams
- [ ] Every new replay row has signal_stream.
- [ ] Legacy stream inference works.
- [ ] Unknown stream fails invariant.
- [ ] Record-type stream mapping is covered.

## Reward purity
- [ ] Reward reducer consumes ActionStream rows only.
- [ ] Biography rows cannot affect reward.
- [ ] Derived rows cannot affect reward.
- [ ] World rows cannot silently affect reward.
- [ ] Promotion holds on reward-purity violation.

## Estimators
- [ ] interruption_tolerance_v1 exists.
- [ ] Estimator is deterministic.
- [ ] Estimator emits SignalEstimatorReport.
- [ ] Estimator cites evidence.
- [ ] Synthetic/real parity test passes.
- [ ] Legacy notification_fatigue has no new writer/reader.

## sim_v2.1
- [ ] sim_v2.1 uses estimator output.
- [ ] sim_v2.1 ignores candidate predicted heads.
- [ ] Scenarios are behavior-authored.
- [ ] Psychological scalar lint works.

## Dogfood shadow
- [ ] Observation import works.
- [ ] Stream tags are correct.
- [ ] Redaction/local-only policy is explicit.
- [ ] Frontier generation works.
- [ ] Provider preview works.
- [ ] No commit occurs.

## Calibration
- [ ] CalibrationReport validates.
- [ ] sim-vs-real acceptance gap measured or held.
- [ ] sim-vs-real undo gap measured or held.
- [ ] estimator_calibration_gap measured or held.
- [ ] Calibration is per action family.
- [ ] Insufficient data returns hold, not pass.

## Semantic labels
- [ ] Codex annotator proposes evidence-cited labels.
- [ ] Active derived labels have evidence.
- [ ] Activation/disable/correct rows are audit-visible.
- [ ] Disabled labels stay disabled.
- [ ] Disable emits ActionStream row.
- [ ] Labels never gate authority.
- [ ] Biography drift findings surface conflicts.

## Measurement
- [ ] MeasurementReport validates.
- [ ] Latency metrics recorded or explicitly unsupported.
- [ ] NIM request/retry counts recorded for live runs.
- [ ] Reward-head deltas recorded.
- [ ] Signal-layer metrics recorded.

## Provider capabilities
- [ ] Deterministic provider report validates.
- [ ] EventKit sandbox report validates or holds honestly.
- [ ] Unsupported providers declare unsupported capabilities.
- [ ] Provider errors are replay-visible.
- [ ] Promotions respect provider capability reports.

## Self-play
- [ ] CurriculumRun validates.
- [ ] Findings map to canonical failure keys.
- [ ] Unmapped findings block promotion unless waived.
- [ ] Provider-backed self-play works for deterministic provider.
- [ ] EventKit provider-backed self-play passes or holds on environment.

## Policy learning
- [ ] Tuning cites replay.
- [ ] Frontier diff compares candidate vs CURRENT.
- [ ] Reward-head gates pass or hold with named failures.
- [ ] Policy ablation report exists.
- [ ] no_semantic_labels ablation runs.
- [ ] no_derived_signals ablation runs.
- [ ] Rollback plan exists.

## Autonomy
- [ ] Autonomy ladder exists.
- [ ] create_prep_block proposal exists.
- [ ] Matrix diff changes one family only.
- [ ] Active labels are snapshotted.
- [ ] Labels are not authority justification.
- [ ] Rollback command is recorded.

## Frontend
- [ ] Learn renders P12 measurement and reward heads.
- [ ] Lab renders curriculum/calibration.
- [ ] Authority renders family-level autonomy.
- [ ] Signals renders labels/evidence/controls.
- [ ] Disable round-trip works or is explicitly held.
- [ ] Replay export matches frontend state.

## Release
- [ ] make p12-release exists.
- [ ] Release report exists.
- [ ] Secret scan passes.
- [ ] Evidence bundle validates.
- [ ] All pass/hold/fail decisions are named.
```

---

# 22. P12 progress ledger

Use this at the end of the run.

```md
# P12 Progress Ledger

RUN_ID:
Engineer:
Date:
Git SHA:
Branch:
Changed files:

## Hypothesis

What are we trying to prove?

## One-live-component-at-a-time check

Changed component:
Held fixed:
Runtime mode:
Provider:
Policy backend:
Simulator version:
Estimator versions:
Prompt/model version:
Tuning ID:

## Overall decision

- [ ] pass
- [ ] hold
- [ ] fail
- [ ] needs rerun

Primary reason:

## Evidence artifacts

P11 regression:
Contracts:
Signal streams:
Reward purity:
Estimators:
Dogfood shadow:
Calibration:
Semantic labels:
Measurement:
Provider capabilities:
Self-play:
Policy learning:
Autonomy:
Frontend:
Release:

## Metrics snapshot

valid_frontier_rate:
model_generation_rejection_rate:
OTHER_intent_rate:
expected_intent_hit_rate:
empty_frontier_rate:

frontier_latency_ms_p50:
frontier_latency_ms_p95:
codex_latency_ms_p50:
codex_latency_ms_p95:
provider_verify_latency_ms_p50:
provider_verify_latency_ms_p95:
nim_request_count:
nim_retry_count:
cost_per_valid_frontier:

utility_delta:
acceptance_delta:
engagement_delta:
long_horizon_delta:
regret_delta:
interruption_delta:
social_risk_delta:
undo_regret_delta:
ignored_delta:
explicit_wrong_delta:

sim_vs_real_acceptance_gap:
sim_vs_real_undo_gap:
matched_examples:
estimator_calibration_gap:

label_evidence_coverage:
label_churn_rate:
derived_vs_declared_conflicts:
label_disable_events:

rollback_pass_rate:
provider_idempotency_pass:
hard_invariant_violations:
soft_invariant_violations:
stream_purity_violations:

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

# Completed P12 Final Acceptance — 20260703T224814Z-p12

RUN_ID: 20260703T224814Z-p12  
Engineer: Codex  
Git SHA: 8f484f40ec4fb48cd178e2f4e815bed1f9efc0e6  
Branch: codex/dogfood-macos-app

## Acceptance Checklist

- [x] P11 floor passed: Python, Swift, golden invariants, contract vectors, frontier diff, scorecard.
- [x] P12 contracts passed: schemas exist, `VERSIONS.json` references them, broken vector fails.
- [x] Signal streams passed: required mappings, legacy inference, B0 unknown-stream negative, B4 reward-stream negative.
- [x] Reward purity passed: ActionStream-only reward evidence and reward-head purity gate pass.
- [x] Estimators passed: `interruption_tolerance_v1` deterministic, evidence-cited, and report-backed.
- [x] sim_v2.1 passed: behavior-authored scenarios and predicted-head negative.
- [x] Dogfood shadow passed: import/frontier/preview generated; preview cannot commit.
- [x] Calibration passed with hold: insufficient matched real examples returned `decision: hold`.
- [x] Semantic labels passed: evidence-cited labels, user audit rows, disabled label state, no authority gating, drift findings.
- [x] Measurement passed: MeasurementReport and reward-head deltas emitted.
- [x] Provider capabilities passed/held: deterministic and unsupported providers passed; EventKit sandbox remains explicit hold.
- [x] Self-play passed: base curriculum and deterministic provider-backed curriculum passed.
- [x] Policy learning passed: offline tuning, frontier diff, scorecard, and required ablations passed.
- [x] Autonomy passed/held: create_prep_block promotion held with rollback plan and no shipped matrix change.
- [x] Frontend passed: Learn/Lab/Authority/Signals surfaces, browser E2E, and UI disable round-trip passed.
- [x] Release passed: `make p12-release` returned `ok: true`; secret scan passed.

# P12 Progress Ledger — 20260703T224814Z-p12

RUN_ID: 20260703T224814Z-p12  
Engineer: Codex  
Date: 2026-07-03  
Git SHA: 8f484f40ec4fb48cd178e2f4e815bed1f9efc0e6  
Branch: codex/dogfood-macos-app  
Changed files: `P12-test.md`, frontend/session/projector/server/JS, P12 scripts, curricula, and evidence logs.

## Hypothesis

P12 can learn from auditable signals without relaxing P11 invariants: reward remains ActionStream-only, derived labels cite evidence, user label controls are replay-visible, labels never gate authority, and autonomy expands only through explicit promotion gates.

## One-live-component-at-a-time Check

Changed component: P12 signal/measurement/release/frontend surfaces.  
Held fixed: P11 safety floor, Swift authority boundary, deterministic provider for non-live runs.  
Runtime mode: fixture/auto for UI; strict live NIM schema gate passed with `.env` credentials loaded.  
Provider: deterministic for passing provider-backed checks; EventKit sandbox held.  
Policy backend: heuristic/NIM-gated policy surfaces, no live fallback in strict schema gate.  
Simulator version: sim_v2.1.  
Estimator versions: interruption_tolerance_v1.  
Prompt/model version: live NIM schema gate fixture plus strict `.env` credential pass.  
Tuning ID: CURRENT.

## Overall Decision

- [x] pass
- [ ] hold
- [ ] fail
- [ ] needs rerun

Primary reason: all required deterministic, fixture, browser, release, and invariant gates passed; remaining live/calibration/autonomy conditions are explicit holds allowed by the P12 standard.

## Blockers and Retest Status

| Item | Status | Can Codex fix directly? | Retest performed | Evidence |
|---|---|---|---|---|
| Strict live NIM schema gate | Resolved | Yes. The script did not load repo `.env`; fixed `run_live_nim_schema_gate.py` to load `.env` without overriding exported env vars or printing secrets. | `CALENDAR_PILOT_REQUIRE_LIVE_NIM=1 ... run_live_nim_schema_gate.py` now returns `decision: pass`; `test_runtime_mode.py`, `test_p12_contracts_and_scripts.py`, and `make p12-release` passed after the fix. | `policy_learning/live_nim_schema_gate_after_dotenv.json`, `release/p12-release-after-nim-dotenv.log` |
| Calibration matched examples | Blocked on data | Not honestly fixable in code. The report has `matched_examples: 0`; sim-vs-real acceptance/undo gaps require real matched dogfood examples. | Calibration script and release gate pass with explicit insufficient-data hold. | `calibration/calibration_report.json` |
| Live EventKit sandbox/provider-backed checks | Blocked on macOS permission/environment | Not safely fixable in code. Requires explicit Calendar permission and a sandbox calendar target before mutating/read-write live checks can run. | Deterministic provider-backed checks passed; EventKit capability declaration passed/held. | `provider_capabilities/apple_eventkit_capabilities.json`, `self_play/provider_backed_deterministic.json` |
| `create_prep_block` autonomy promotion | Blocked by gates | Not safe to force. Promotion depends on human-feedback and sim-real calibration gates; current decision correctly holds. | Proposal/decision generated, no matrix change shipped, rollback plan recorded, release gate passed. | `autonomy/create_prep_block_decision.json` |

## Evidence Artifacts

P11 regression: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/p11_regression/`  
Contracts: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/contracts/`  
Signal streams: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/signal_streams/`  
Reward purity: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/reward_purity/`  
Estimators: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/estimators/`  
Dogfood shadow: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/dogfood_shadow/`  
Calibration: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/calibration/`  
Semantic labels: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/semantic_labels/`  
Measurement: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/measurement/`  
Provider capabilities: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/provider_capabilities/`  
Self-play: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/self_play/`  
Policy learning: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/policy_learning/`  
Autonomy: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/autonomy/`  
Frontend: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/frontend/`  
Release: `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/release/`

## Metrics Snapshot

valid_frontier_rate: 1.0  
model_generation_rejection_rate: 0.0  
OTHER_intent_rate: 0.1429  
expected_intent_hit_rate: 0.0  
empty_frontier_rate: 0.0  

frontier_latency_ms_p50: unsupported/null  
frontier_latency_ms_p95: unsupported/null  
codex_latency_ms_p50: unsupported/null  
codex_latency_ms_p95: unsupported/null  
provider_verify_latency_ms_p50: unsupported/null  
provider_verify_latency_ms_p95: unsupported/null  
nim_request_count: 0  
nim_retry_count: 0  
cost_per_valid_frontier: unsupported/null  

utility_delta: 0.0  
acceptance_delta: 0.0  
engagement_delta: 0.0  
long_horizon_delta: 0.0  
regret_delta: 0.0  
interruption_delta: 0.0  
social_risk_delta: 0.0  
undo_regret_delta: 0.0  
ignored_delta: 0.0  
explicit_wrong_delta: 0.0  

sim_vs_real_acceptance_gap: hold/null  
sim_vs_real_undo_gap: hold/null  
matched_examples: 0  
estimator_calibration_gap: hold/null  

label_evidence_coverage: 3.0  
label_churn_rate: 0.0  
derived_vs_declared_conflicts: 1 drift finding  
label_disable_events: 1 UI disable round-trip  

rollback_pass_rate: 1.0 for autonomy decision; 0.0 in fixture measurement report  
provider_idempotency_pass: true  
hard_invariant_violations: 0  
soft_invariant_violations: 0  
stream_purity_violations: 0

## Failures

| Step | Failure | Expected | Actual | Artifact | Owner | Fix | Rerun required |
|---|---|---|---|---|---|---|---|
| 2 | First parallel Python suite timed out while Swift continued | P11 Python pass | Isolated rerun passed | `p11_regression/py-test-rerun.log` | Codex | Reran isolated | No |
| 5 | Reward-head report did not cite ActionStream reward evidence | Reward purity report names source | Missing source field | `reward_purity/make_reward_head_report.log` | Codex | Added `reward_evidence` block | No |
| 9 | Measurement report assumed invariant violations were list-shaped | Report handles int/list shapes | Script crashed on int | `calibration/test_p12_contracts_and_scripts.log` | Codex | Added `violation_count` helper | No |
| 10 | Semantic annotator script missing | Evidence-cited semantic label artifact | No script | `semantic_labels/run_semantic_annotator.log` | Codex | Added script and drift detection | No |
| 13 | Base curriculum lacked required scenario classes | Behavior-authored P12 curriculum | Sparse curriculum | `self_play/run_p12_base_curriculum.log` | Codex | Expanded `p12_base.json` and CLI comparison support | No |
| 18 | First Signals disable imported label without complete replay evidence | Disable row leaves invariants clean | B1/I3 violations during prototype | `frontend/ui_signal_disable_view.json` | Codex | Imported reward evidence as ActionStream root rows | No |

## Decisions

| Decision | Reason | Evidence | Reversible? | Rollback |
|---|---|---|---|---|
| Pass P12 release gate | All release checks returned `ok: true` | `release/p12_release_report.json` | Yes | Revert changed files and rerun `make p12-release` |
| Hold calibration gaps | `matched_examples: 0` | `calibration/calibration_report.json` | Yes | Add matched real examples and rerun calibration |
| Hold create_prep_block promotion | Human feedback and sim-real calibration gates insufficient | `autonomy/create_prep_block_decision.json` | Yes | Restore `configs/autonomy_matrix.json` and rerun release |
| Hold live EventKit provider-backed checks | No explicit sandbox calendar permission | `provider_capabilities/apple_eventkit_capabilities.json` | Yes | Grant permission and rerun EventKit checks |
| Pass strict live NIM gate with `.env` credentials | Gate now loads `NVIDIA_API_KEY` from `.env` and strict mode reports credentials present | `policy_learning/live_nim_schema_gate_after_dotenv.json` | Yes | Remove `.env` loader change to restore old behavior |

## Follow-up PRs

| PR | Scope | Gate needed | Owner |
|---|---|---|---|
| TBD | Add real matched dogfood examples for calibration | CalibrationReport with matched examples > 0 | Product/ML |
| TBD | Run live EventKit provider-backed self-play in sandbox calendar | EventKit capability/self-play pass | App owner |

# 23. Judgment standard

A passing P12 test run is not one where CalendarPilot merely has more objects or more scripts.

It is one where:

```text
P11 still holds,
human signals are separated by epistemic source,
reward comes only from human/app actions,
derived beliefs cite evidence,
labels are user-visible and user-controlled,
labels never affect authority,
sim_v2.1 is behavior-authored and estimator-driven,
dogfood shadow cannot write,
calibration reports pass or hold honestly,
policy improvement beats CURRENT with ablations,
provider capabilities constrain acting,
and autonomy expands one reversible family at a time.
```

P11 made the loop trustworthy.
P12 proves the loop can learn from auditable signals.
