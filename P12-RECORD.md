# P12 Record — Lab as Instrument, Policy as Product, Signals as Truth

**Status: FROZEN.** P12 is closed (Step E complete, run `20260706T220150Z-step-e-complete`).
This document is the canonical, append-only record of P12 — its direction, its proof,
its stage-1 audit, and the Step E instrument gate that closed it. It does not change.

**Forward plan:** [compression-roadmap.md](compression-roadmap.md) — the single living
architecture document (Step E → P17). If you are here to do new work, go there; come
back here only for evidence.

**This document merges and replaces three originals**, archived verbatim (tombstones in §10):

- `P12-direction.md` → `Do-not-reference/P12-direction.md` (why P12: three streams, three lenses)
- `P12-test.md` → `Do-not-reference/P12-test.md` (how P12 was proven: baseline run `20260703T224814Z-p12`)
- `P12-next.md` → `Do-not-reference/P12-next.md` (stage-1 audit: lineage, Stage A→D, Step E)

---

## 1. P12 in one page

**One-sentence direction (as set):** P12 turns CalendarPilot's P11 trajectory substrate
into an experimental engine that can safely learn from reality — by separating
interpretable human actions, calendar world data, and human biography into three
governed signal streams, calibrating simulation against dogfood behavior, and promoting
autonomy one action family at a time.

P11 answered: *Can we trust the loop?* Yes.
P12 answered: *Can the trusted loop learn safely from reality, from signals we can
actually verify?* Yes — proven by the baseline run, then audited and instrumented.

**The three streams** (the P12 architectural correction; runtime home is now
`calendar-pilot-p12/docs/SIGNAL_STREAMS.md`):

```text
ActionStream    fast, verifiable human actions — the ONLY reward truth,
                and the measurement stream for estimators
WorldStream     provider-verified calendar reality — generation/ranking context,
                never a silent preference source
BiographyStream slow, fluid, user-owned self-description — a capped-weight,
                decaying PRIOR, never reward truth
```

Between fast and slow sits the derived layer: versioned estimators
(`interruption_tolerance_v1`) and evidence-cited `SemanticSignal` labels, user-visible
and user-controllable, barred from authority (invariants B1–B6, §2.4).

**What happened, in order:**

1. **Proven** — baseline run `20260703T224814Z-p12` (2026-07-03, Git SHA
   `8f484f40ec4fb48cd178e2f4e815bed1f9efc0e6`): overall decision **pass**; all 19 test
   steps pass or hold-by-design; `make p12-release` `ok: true` (§3).
2. **Audited** — the stage-1 lineage audit reconstructed phase provenance for the whole
   tree from the `/Do-not-reference` archive (Stage A→C readiness → line provenance →
   C₀ framework → C₁ verdicts). **C₁ verdict distribution (run
   `20260705T021039Z-p12-next-stage-c1-verdicts`, by flow-cluster): KEEP-B 36 ·
   CONSOLIDATE 12 · DEFER 4 · KEEP-I 2 · DELETE 1 · ARCHIVE 0 — 18 humane clusters,
   0 humane DELETE/ARCHIVE.** Almost nothing was dead (§4.8).
3. **Compressed (narrowly)** — Stage D landed Wave 1 plus blocker-fix, session-brain,
   EventKit, and official-pipeline passes: one clean DELETE, legacy-state/`app.js`/
   `sim_v1`/fatigue-residue/envelope-v1 retirements, `session.py` 2222 → 1316 by
   decomposition, live EventKit write/rollback proven (§5).
4. **Instrumented and closed** — Step E made the release ruler truthful (de-placeboed
   `reward_heads`, `policy_ablation`, `calibration`), pinned the instrument
   (SHA `84fd6bd0da17f0f1aed4d6222f56373732757caf`; final pin in the run bundle's
   `INSTRUMENT.sha`), shipped `Belief` + object-level `explain()`, proved app-bundled
   EventKit mutation with `full_access`, and finished at
   `20260706T220150Z-step-e-complete` with `make p12-release` → `decision: pass`.
   Blocker B-004 resolved. The wave harness (eight-field experiment record, C-VAR,
   B_migrate) landed as the follow-up (§6).

**Known-red data-quality flags**, pinned at instrument time so no future wave is blamed
for them or allowed to worsen them silently (§8.3):

```text
OTHER_intent_rate: 0.1429        (above the 0.10 promotion gate at fixture scale)
expected_intent_hit_rate: 0.0
```

**Open at freeze** (inherited by the roadmap, not by this record): B-002 — Program A
cold-start evidence volume (`create_prep_block` promotion held on matched examples and
explicit feedback); B-003 — the two frontier data-quality flags above (§8.2).

---

## 2. Direction (canonical narrative, from `P12-direction.md`)

### 2.1 The fatigue critique — why the streams exist

`UserBiography.notification_fatigue: float` was the emblem: a scalar living on the
biography as declared fact, nudged by reward events, mixed with dismissal counts in
pressure reads, conditioning sim acceptance as "seed ground truth", and leaking into
Codex prompts as a magic number. But "fatigue" is an unobservable psychological state —
there is no sensor for it. A learning system whose reward and timing depend on a made-up
scalar is learning about its own fiction. The escape was already in the code
(`recent_dismissals` — behavioral, timestamped, replay-visible), so the rule became:
**internal states are never declared; they are estimated from verifiable behavior, and
the estimator is versioned, evidence-cited, and calibrated.** The system never polls the
user for internal state; evidence-cited reconciliation questions are the only questions
allowed.

### 2.2 The three-stream rules and B-invariants (as shipped)

```text
R1. Reward is computed from ActionStream rows only.                      (invariant B4)
R2. Every derived SemanticSignal cites ActionStream/WorldStream evidence. (invariant B1)
R3. No signal or label influences authority tier, scope, or grants.       (invariant B2)
R4. Label activation changes are user-attributed audit rows.              (invariant B3)
R5. Declared biography and derived signals never overwrite each other
    silently; persistent conflict emits a BiographyDriftFinding.          (invariant B5)
R6. Estimators are versioned; the same estimator version runs on
    synthetic and real streams.                                           (invariant B6)
R7. The system never prompts the user for internal state; evidence-cited
    reconciliation questions are allowed, affect polling is not.
```

### 2.3 The derived layer

- **`interruption_tolerance_v1`** — the first estimator: a pure, deterministic,
  version-stamped function over ActionStream/WorldStream windows (dismissal streaks,
  hourly dismissal rates, response-latency trends, undo-after-accept), replacing the
  declared fatigue scalar. Seeds and self-play scenarios author *behavior* (dense
  dismissed histories), never psychology; `sim_v2.1` conditions on estimator output
  computed from authored histories through the same code path as production (B6).
- **Codex as semantic annotator** — proposes typed, evidence-cited `SemanticSignal`
  labels ("dismisses evening suggestions", evidence: replay row ids) with confidence
  and half-life; proposals are replay rows; nothing activates silently.
- **Swift-patterned label registry** — users see and control which labels are active
  (disable / correct / "not me"); activation changes are user-attributed audit rows;
  a user disable is itself a first-class ActionStream negative signal; disabled labels
  never auto-reactivate; registry state is invisible to grant issuance (B2).

### 2.4 The three-lens synthesis (canonical home — the roadmap cites this section)

**Alan Kay — make better objects.** The lab objects are the product language. P12 added
the signal objects to the P11 set:

```text
Seed, Scenario, RuntimeProfile, TraceEvent, ActionEnvelope, ProviderTransaction,
ReplayRecord, RewardEvent, SelfPlayEpisode, DogfoodObservation, HumanFeedbackEvent,
PolicyTuning, FrontierDiff, Scorecard, CalibrationReport, PromotionRecord,
AutonomyMatrixEntry, ProviderCapability,
SemanticSignal, SignalEstimatorReport, LabelActivation, BiographyDriftFinding   (new)
```

If an experiment cannot be expressed in these objects, the lab language is incomplete.
The end state: the lab as a **calendar autonomy wind tunnel** — seeded worlds (authored
as behavior) → typed candidates → simulated/provider-backed trajectories → invariant
checks → decomposed reward (ActionStream only) → variance → frontier diff vs CURRENT →
promotion or hold → rollback path.

**Claire Tomlin — expand autonomy through verified control envelopes.** Expand the safe
reachable set without losing control of the unsafe set. Every action family defines
state space, control input, required authority, disturbances, bad reachable states,
barrier certificates, rate caps, rollback. P12 added the signal envelope: every signal
declares stream, estimator version, evidence requirement, decay — and B2
(labels-never-gate-authority) plus B4 (reward purity) are barriers, not conventions.
Disturbances gained biography drift, label churn, and estimator lag.

**John Schulman — trust only marginal, variance-aware improvement.** Every policy update
answers: what changed, what stayed fixed, which replay rows trained it, what baseline it
beat, effect size vs noise, which reward head improved/regressed, survival on
adversarial seeds, rollback — plus which stream fed each feature, and whether the win
survives `no_semantic_labels` / `no_derived_signals` ablation. The policy must win for a
reason that survives ablation, and never grades itself or eats its own fiction.

### 2.5 The autonomy ladder (as set)

```text
1. create_prep_block            5. move_private_flexible_hold
2. add_buffer                   6. social_shadow_move_meeting
3. protect_deep_work            7. auto_apply_plan_sandbox_only
4. batch_admin                  8. limited_real_auto_apply_plan
```

One family at a time; the autonomy matrix is a promotion target, not a static config;
labels inform the promotion record but never justify the tier.

### 2.6 Promotion gates (as shipped)

```text
Policy tuning:   valid_frontier_rate >= 0.95; model_generation_rejection_rate <= 0.15;
                 OTHER_intent_rate <= 0.10; expected_intent_hit_rate >= 0.80;
                 hard_invariant_violations = 0; beats CURRENT on marginal diff;
                 reward-head gates pass (ActionStream-only, B4); variance probe;
                 ablation report incl. signal-layer ablations; rollback plan.

Reward heads:    utility_delta >= 0; regret/interruption/social_risk/undo_regret/
                 explicit_wrong deltas <= 0; engagement cannot be the only positive;
                 anti-gaming: engagement_gaming, social_creep, regret_regression,
                 reward_purity (any non-ActionStream row in reward → hold).

Autonomy family: family seed pass >= 0.95; curriculum pass >= 0.95; provider sandbox
                 pass = 1.0; rollback pass = 1.0; human-feedback and sim-vs-real gaps
                 measured or insufficient-data HOLD; matrix diff changes exactly one
                 family; no label/signal in authority justification (B2).

Signal/label:    label_evidence_coverage = 1.0 for active derived labels (B1);
                 zero label reads in authority paths (B2, test-enforced); 100%
                 user-attributed activation rows (B3); reward purity (B4); drift
                 surfaced not resolved (B5); estimator parity (B6); churn bounded;
                 no user-disabled label auto-reactivates.
```

Insufficient data returns **hold**, never pass — the cold-start hold is the system
working as designed.

### 2.7 The framework P12 set for itself

The direction doc specified 17 implementation steps with per-step artifacts, acceptance,
and progress templates; the test doc turned them into 19 test steps. Both step lists
survive here only as the executed results in §3 — the full specifications, command
blocks, and templates are in the archived originals. The direction's own phase plan:

```text
P12.0 stabilize P11 gates → P12.1 measurement → P12.2 streams + estimators
→ P12.3 dogfood shadow + calibration → P12.4 annotator + label registry
→ [autonomy family promotion] → P12.6 self-play curriculum → P12.7 provider capabilities
```

(Naming note: the archived direction doc labels the autonomy-family-promotion slot
"Step E". That is unrelated to the Step E **instrument gate** that closed P12 (§6),
which was defined later by the stage-1 audit.)

Non-goals held throughout: no broad `auto_apply_plan`, no social mutation beyond shadow
without family evidence, no separate analytics state beside replay, no tuning on
schema-failing live NIM output, no aggregate-reward promotion, no affect polling, no
derived signals stored as biography, no labels gating authority, no psychological
scalars in seeds or scenarios.

---

## 3. Proof — baseline run `20260703T224814Z-p12` (from `P12-test.md`)

**Run header:** Date 2026-07-03 · Engineer Codex · Git SHA
`8f484f40ec4fb48cd178e2f4e815bed1f9efc0e6` · Branch `codex/dogfood-macos-app` ·
Evidence bundle `calendar-pilot-p12/runs/p12_evidence/20260703T224814Z-p12/`
(subdirs: preflight, p11_regression, contracts, signal_streams, reward_purity,
estimators, dogfood_shadow, calibration, semantic_labels, measurement,
provider_capabilities, self_play, policy_learning, autonomy, frontend, release).

**Overall decision: pass** — all required deterministic, fixture, browser, release, and
invariant gates passed; remaining live/calibration/autonomy conditions were explicit
holds allowed by the P12 standard.

### 3.1 Per-step results

| step | scope | result | load-bearing evidence |
|---|---|---|---|
| 1 | Preflight | pass | runtime versions, contracts/scripts/docs inventories captured |
| 2 | P11 regression floor | pass | Swift 17 tests; Python pass on isolated rerun (first parallel attempt timed out); invariants pass on `replay_golden.jsonl`; frontier diff leader unchanged (`create_prep_block` top); scorecard `promote_candidate`, 0 violations |
| 3 | P12 contracts + versions | pass | all P12 schemas present; `VERSIONS.json` complete; broken-vector negative produced `ok: false` |
| 4 | Signal-stream tagging | pass | unknown stream → B0 violation; reward row tagged `biography` → B4 violation |
| 5 | Reward purity | pass | matrix: action accepted; bio/derived/world rewards each fail B4; reward-head report cites `allowed_signal_streams: ["action"]`, `reward_purity_violations: 0` (after adding the evidence citation) |
| 6 | `interruption_tolerance_v1` | pass | deterministic, version-stamped; cites `notification_history:obs_demo_001:0`, streams `action`+`world`; `BiographyStore.update_from_reward` no longer mutates fatigue; `_fatigue()` calls the estimator |
| 7 | `sim_v2.1` | pass | predicted-head negative: candidates differing only in predicted heads got identical responses; behavioral-authoring lint clean |
| 8 | Dogfood shadow | pass | 7-candidate shadow frontier; `mode: shadow_no_commit`, `commits: 0`; `--commit` rejected at the access point; redaction policy explicit |
| 9 | Calibration | hold (by design) | `matched_examples: 0` → `decision: hold`; gaps null on insufficient data |
| 10 | Annotator + label registry | pass | 1 proposed signal; `label_evidence_coverage: 3.0` (3 ActionStream rows); drift finding links `bio:evenings-ok` to the derived label; B2 negative fails closed; churn 0.0 |
| 11 | Measurement + reward heads | pass | `measurement_report.v1` + `reward_head_report.v1` emitted; latency fields explicit-null in fixture mode; all reward-head gates true |
| 12 | Provider capabilities | pass / EventKit held | deterministic + `apple_eventkit` reports complete (`sandbox_enforced: true`); Google stub declares unsupported ops; live EventKit held on permission |
| 13 | Self-play curriculum | pass | `curriculum_run.v1`, 20 episodes, 13 scenario classes, all findings canonically mapped, none unmapped/waived |
| 14 | Provider-backed self-play | pass (deterministic) | families `create_prep_block`+`add_buffer`, 20 episodes; idempotent commits; verified rollbacks; conflict denial `provider_conflict_detected`; EventKit live held |
| 15 | Live NIM schema gate | pass | strict live run passed once the script loaded `.env` (`NVIDIA_API_KEY`); normalizations `new_start/new_end`, nested params, `batch_tasks.target_time`; rejections invalid JSON, missing calendar id, duplicate id; `heuristic_fallback_disabled: true` |
| 16 | Policy learning + ablations | pass | offline tuning changed the tuned leader; all 8 required ablations incl. `no_semantic_labels`/`no_derived_signals`; rollback = restore `experiments/promoted/CURRENT.json` |
| 17 | Autonomy promotion | hold (by design) | `create_prep_block` proposal → hold on `insufficient_human_feedback` + `insufficient_sim_real_calibration`; matrix hash unchanged; rollback command recorded |
| 18 | Frontend surfaces | pass | Learn/Lab/Authority/Signals verified via browser E2E + Computer Use; UI disable of `sig_dismisses_evening_suggestions_6b4ec5c9226b` emitted a `label_activation` ActionStream row; `/api/view` and `/api/replay` agree (records 5, rewards 3, semantic_signals 1, label_activations 1) |
| 19 | P12 release gate | pass | `make p12-release` → `runs/p12_release/p12_release_report.json` `ok: true`; secret scan pass |

### 3.2 Metrics snapshot (verbatim)

```text
valid_frontier_rate: 1.0                 model_generation_rejection_rate: 0.0
OTHER_intent_rate: 0.1429                expected_intent_hit_rate: 0.0
empty_frontier_rate: 0.0

frontier/codex/provider-verify latency p50/p95: unsupported/null (fixture mode)
nim_request_count: 0                     nim_retry_count: 0
cost_per_valid_frontier: unsupported/null

utility/acceptance/engagement/long_horizon/regret/interruption/social_risk/
undo_regret/ignored/explicit_wrong deltas: all 0.0

sim_vs_real_acceptance_gap: hold/null    sim_vs_real_undo_gap: hold/null
matched_examples: 0                      estimator_calibration_gap: hold/null

label_evidence_coverage: 3.0             label_churn_rate: 0.0
derived_vs_declared_conflicts: 1 drift finding
label_disable_events: 1 UI disable round-trip

rollback_pass_rate: 1.0 for autonomy decision; 0.0 in fixture measurement report
provider_idempotency_pass: true
hard_invariant_violations: 0   soft_invariant_violations: 0   stream_purity_violations: 0
```

### 3.3 Failures found and fixed during the run (verbatim)

| Step | Failure | Fix | Rerun required |
|---|---|---|---|
| 2 | First parallel Python suite timed out while Swift built | Reran isolated | No |
| 5 | Reward-head report did not cite ActionStream reward evidence | Added `reward_evidence` block | No |
| 9 | Measurement report assumed invariant violations were list-shaped; crashed on int | Added `violation_count` helper | No |
| 10 | Semantic annotator script missing | Added `scripts/run_semantic_annotator.py` + drift detection | No |
| 13 | Base curriculum lacked required scenario classes; compare CLI lacked `--candidate` | Expanded `p12_base.json`, fixed CLI | No |
| 18 | First Signals disable left B1/I3 violations (missing imported evidence) | Imported reward evidence as ActionStream root rows | No |

### 3.4 Decisions (verbatim)

| Decision | Reason | Evidence |
|---|---|---|
| Pass P12 release gate | All release checks `ok: true` | `release/p12_release_report.json` |
| Hold calibration gaps | `matched_examples: 0` | `calibration/calibration_report.json` |
| Hold `create_prep_block` promotion | Human-feedback + sim-real gates insufficient | `autonomy/create_prep_block_decision.json` |
| Hold live EventKit checks | No explicit sandbox calendar permission | `provider_capabilities/apple_eventkit_capabilities.json` |
| Pass strict live NIM gate | `.env` loader fix; credentials present, no secrets printed | `policy_learning/live_nim_schema_gate_after_dotenv.json` |

### 3.5 Blockers at baseline

| Item | Status at run end | Later resolution |
|---|---|---|
| Strict live NIM schema gate | resolved in-run (`.env` loader) | — |
| Calibration matched examples | blocked on data | B-002; still open at freeze (Program A) |
| Live EventKit sandbox | blocked on macOS permission | B-001; resolved `20260705T174108Z` (§5.5) |
| `create_prep_block` promotion | held by gates | held at freeze; Program A decides with data |

---

## 4. Audit — the stage-1 lineage audit (from `P12-next.md`)

P12-next ran two programs in one window: **Program A** (cold-start runway: collect
`create_prep_block` shadow examples + explicit feedback in the background, protected
from all cleanup) and **Program B** (debt erasure: reconstruct lineage from the archive,
verdict everything, then delete/consolidate under a frozen gate). The freeze
(`make p12-release` from the baseline run) is what made aggression safe; the archive is
what made deletion reversible by construction.

### 4.1 The lineage method

The repo has no continuous git history across phases — each phase was a snapshot
folder, now in `/Do-not-reference`. That archive is the tree's `git blame`:

```text
1. Sort snapshot repos + implementation docs by date → phase timeline.
2. Diff successive snapshots → attribute every current file/flow to the phase
   that introduced it and the phases that modified it.
3. Label flows with inline LINEAGE tags (scaffolding — zero remain at phase end).
4. Trace backwards from ML through backend to frontend; every flow not reachable
   from a frozen root is a deletion candidate by default.
5. Delete or consolidate lineage-by-lineage, re-running the frozen gate per wave.
```

Binding rules (abridged; L1–L8 in the archived original): snapshot diffing is scripted;
Stage A/B discovery assigns **no** retention verdicts (discovery and judgment are
separate phases); coverage runs must include env-gated live legs or explicitly
root-list them — *a deterministic-only coverage run WILL mark live code as dead*;
every deletion records a tombstone naming what died, which phase built it, and which
snapshot still contains it; tests die only with their feature; static references
(tests, docs, examples, parent-module imports) never prove KEEP by themselves.

### 4.2 The phase timeline (canonical archaeology)

Dated by folder/document mtimes, anchored by pass documents (where mtime and pass-doc
disagree, the pass doc wins). Stage A findings are grouped per phase as `SA-*` rows.

| phase | snapshot repo in /Do-not-reference | anchor document(s) | introduced | SA rows |
|---|---|---|---|---|
| P5–P6 (Jun 29) | — (plans only) | `plan-6-revised.md` … `plan-9.md`, `readme.md` | kernel/policy/executive split, demo loop | — |
| P6.5 (Jun 30) | `calendar-pilot-revised` | `AGENT_LOOP_REVISION.md` | signals pressure read, world model, reward anatomy, right-moment, first self-play adversaries | `SA-P6.5-001..006` |
| P7 (Jun 30) | `calendar-pilot-updated` (+ `…updated 2`) | `NEXT_FOCUS_REVISION.md` | contract reconciliation, snake_case CodingKeys, staging depth, biography provenance, provider stubs | `SA-P7-001..005`, `SA-P7-DUP-001` |
| P7.5 (Jun 30) | `calendar-pilot-executive` (+ dup) | `CODEX_TOOL_EXECUTIVE.md` | CodexToolRuntime/Planner, tool contracts, deliberation replay | `SA-P7.5-001..003`, `SA-P7.5-DUP-001` |
| P8 (Jul 1) | `calendar-pilot-frontend` (×2) | `FRONTEND_AND_AUTHORITY_REVISION.md`, `FRONTEND_SURFACES.md`, `CHAT_FIRST_FRONTEND_REDESIGN.md` | static frontend, snapshot surfaces, grant registry, Swift IPC server, chat-first panels | `SA-P8-001..003`, `SA-P8-DUP-001` |
| P8.5 (Jul 1) | `dogfooding`, `calendar-pilot` | `DOGFOODING_FRAMEWORK.md`, `SAFETY_CONTRACT_PASS.md` | dogfood session state, AuthorityGrant hardening, live Codex path, release script | `SA-P8.5-000..004` |
| P9 (Jul 2) | `calendar-pilot-system-framework` | `SYSTEM_FRAMEWORK.md`, `SYSTEM_FRAMEWORK_IMPLEMENTATION_PASS.md` | environment/ substrate: trace, envelope, router, taxonomy, invariants, fsio, session locking | `SA-P9-001..004` |
| P10 (Jul 2–3) | `calendar-pilot-deferred-pass` | `DEFERRED_WORK_IMPLEMENTATION_PASS.md`, `thin-lab.md` | ActionLifecycle/SessionStore extraction, ES-module frontend, EventKit sandbox, plan graph, temporal controller, lab shell + seeds | `SA-P10-001..007` |
| P11 (Jul 3) | `calendar-pilot-p11` | `thickening-the-lab.md`, `P11-test.md` | FrontierService provenance, sim_v2, autonomy matrix, marginal promotion, provider transactions, B-precursors | `SA-P11-001..006` |
| P12 (current) | `calendar-pilot-p12` | this record (was `P12-direction.md`, `P12-test.md`) | three streams, estimators, semantic labels/registry, calibration, measurement, curricula, capability reports | `SA-P12-NF-001..002` |

Loose-document intake: phase plans (`plan-*.md`, `readme.md`) anchor P5–P9 timeline
rows; dogfood/safety docs (`DOGFOODING_FRAMEWORK.md`, `dogfooding*.md`, `thin-lab.md`,
`thickening-the-lab.md`) are doc/runway evidence; framework/test docs
(`SYSTEM_FRAMEWORK.md`, `ML-E2E.md`, `ML-testing.md`, `P11-test.md`) are gate/test
anchors — never retention or root proof.

### 4.3 Stage A — lineage discovery

Runs: `20260704T015059Z-p12-next-stage-a` + repair
`20260704T024144Z-p12-next-stage-a-ledger-repair`. (An earlier artifact set,
`20260704T013457Z-p12-next-lineage`, produced premature retention verdicts and was
quarantined as non-evidence.)

**44 findings.** Phase distribution: P6.5 6 · P7 6 · P7.5 3 · P6.5/P7 overlap 1 · P8 4 ·
P8.5 doc/runway 5 · P9 4 · P10 7 · P11 6 · P12 current 2. Three blockers opened on
duplicate-folder ambiguity: `B-SA-001` (P7 `updated 2`), `B-SA-002` (P8 frontend pair),
`B-SA-003` (P8.5 dogfood/safety folder). Detailed rows live in
`…/20260704T015059Z-p12-next-stage-a/lineage/stage_a_findings.jsonl` and the repair
run's `stage_a_review_summary.{md,json}`, `duplicate_delta_summary.md`,
`loose_doc_intake_review.md`, `symbol_expansion_queue.jsonl`,
`ignored_retention_artifacts.md`.

### 4.4 Stage B — acceptance (historical; superseded for readiness)

Run: `20260704T032235Z-p12-next-stage-b-acceptance` (Git SHA `906cc68`, the
`chore: checkpoint p12 workspace` checkpoint). Of 44 findings: **39 accepted,
2 corrected** (`SA-P12-NF-001/002` normalized to explicit "P12 current / not found"),
**3 blocked** (the B-SA trio). Symbol/file expansion judged **INSUFFICIENT**:
core-symbol coverage 20.8% (169/813 AST symbols); 0/62 module constants and 0/667
class-level/dataclass fields represented or waived. Artifacts:
`…/20260704T032235Z-p12-next-stage-b-acceptance/review/stage_b_acceptance_matrix.jsonl`
(+ summary), `lineage/symbol_expansion_manifest.jsonl`, `file_expansion_status.md`,
`blockers_remaining.md`, `ast_coverage_raw.json`.

### 4.5 Structural expansion → Stage C readiness ACHIEVED

Expansion run `20260704T034739Z-p12-next-symbol-expansion` (Git SHA `906cc68`):
**100% structural coverage** — 814 AST symbols + 69 module constants + 549 dataclass
fields rowed; 119 non-dataclass class attributes waived; non-src carriers 21 contract
schemas + 10 frontend carriers + 30 scripts rowed, 8 scripts waived; 1,493 rows + 127
waivers. AST reconciliation: 813 vs 814 = nested `frontend/server.py::Handler`. Initial
status **partial** — 27/54 files ready, 27 blocked (16 by the B-SA trio, 11 mixed-phase).

Readiness run `20260704T041118Z-p12-next-stage-c-readiness`: an archive-level
per-symbol diff (`archive_index.py`) across all 11 snapshots cleared both causes —
**54/54 files expansion-ready, 1,506 rows all `stage_c_ready: true`, 119 waivers,
0 open blockers, 100% source-symbol coverage.** `B-SA-001/002/003` resolved:
`updated 2` and `frontend 2` proven P8-era accumulated snapshots (P8 files present,
P9 `environment/` absent); **0 current symbols depend on an ambiguous folder alone;
0 first-seen in the P8.5 folder** (P8.5 confirmed doc/runway only). Refinements:
`BiographyStore`/`RawCalendarObservation` re-dated to P6.5 (not P7). Retention verdicts
still deferred — Stage C unblocked, not executed. Artifacts under
`…/20260704T041118Z-p12-next-stage-c-readiness/lineage/`:
`expanded_symbol_lineage.jsonl`, `waivers.jsonl`, `blocker_resolution.md`,
`coverage_report.json`, `expanded_file_status.md`, `review/stage_c_readiness_summary.md`.

Source census totals at this point: 54 Python source files; 136 classes; 132 top-level
functions; 532 methods; 14 nested definitions; 814 AST-level symbols. (The per-file
54-row assignment table lives in the archived original and, per-symbol, in
`expanded_symbol_lineage.jsonl` — see §9.)

### 4.6 Line-level provenance

Run: `20260704T060917Z-p12-next-line-provenance`. Structural lineage upgraded to line
spans: **170 scoped files, 29,888 current lines — 20,279 mapped to accepted structural
rows, 3,358 waived (3,001 blank; 357 comment/docstring; 0 generated), 6,251 blocked
across 41 files.** Blockers confined to `examples`, `tests`, `packages` (in current
scope but absent from the accepted structural lineage artifact); they do not block
runtime verdicts. No retention verdicts assigned. Artifacts:
`…/20260704T060917Z-p12-next-line-provenance/lineage/{line_inventory.jsonl,
line_span_manifest.jsonl, line_span_coverage.json, line_span_gaps.md,
line_span_waivers.jsonl}`, `review/line_provenance_summary.md`.

### 4.7 Stage C₀ — retention framework (instrument built, verdicts deferred)

Run: `20260704T221313Z-p12-next-stage-c0-framework` (Git SHA `a058bb2`). Built the
retention framework from direct code reading (~35 runtime files, `path:line`-cited);
no verdicts, no code touched. Load-bearing findings that redirected C₁:

- The served frontend still consumed the legacy snapshot via
  `view_state.v2.legacy_state` (`projector.py:60` → `frontend/static/js/main.js`), so
  `session.py` compression had to sequence behind a JS weaning.
- Three of nine `p12-release` legs were placebo emitters (`policy_ablation`,
  `reward_heads`, `calibration` — the protected calibration script also lacked the
  documented `--family` flag), so they could anchor interface-keeps only.
- D1/D3 (fatigue) largely done in behavior; D2 (`sim_v1`) a one-line default flip that
  contradicted `ARCHITECTURE.md`'s retention note; D5 (`app.js`) confirmed dead from
  the served entry; ~54 statically-dead provider-plumbing lines at
  `codex/tools.py:390-443`.
- Several §6 consolidation hints did not survive reading (swift client+ipc "shared
  framing", right_moment→temporal-controller fold, "3 browser E2E implementations",
  per-script duplication estimates).
- C₁ must verdict ~26–41 flow-clusters, not 1,506 symbols; live legs run or DEFER —
  never default-delete (`run_live_nim_schema_gate.py` is not a make target and must be
  root-listed); humane exception: B-invariant/legibility surfaces may consolidate,
  never delete.

Framework artifacts under `…/20260704T221313Z-p12-next-stage-c0-framework/framework/`:
`organ_map.md`, `root_model.md`, `language_primitives.md`, `invariant_map.md`,
`code_reading_notes.md`, `complexity_duplication_map.md`,
`proposed_retention_taxonomy.md`, `evidence_requirements.md`, `prior_stage_c_risks.md`,
`candidate_pressure_map.md`, `recommended_next_pass.md`, and
`review/retention_framework_review.md`.

### 4.8 Stage C₁ — retention verdicts (canonical home of the distribution)

Run: `20260705T021039Z-p12-next-stage-c1-verdicts` (Git SHA `8cec9d4`; runtime source
byte-identical to C₀ `a058bb2`). No implementation code changed.

**Method:** verdicted flow-clusters — 41 home clusters partitioning all 128 files /
1,506 accepted structural rows exactly once (0 orphans/overlaps, verified) + 14
span-scoped carve-outs = **55 verdict rows** under `retention_verdict.v1`. Ran **6 real
coverage legs** — py-test 159✓, check-invariants 0 violations, p12-release `ok: true`,
swift-ipc-test 9✓, swift-test 17✓, browser-e2e ✓ — plus static dispatch/JS audit. A
prebuilt Swift kernel-server binary and Chrome were present, so the Swift IPC client
and served JS app were proven live (pulled out of DEFER into KEEP-B).

**Distribution (by cluster): KEEP-B 36 · CONSOLIDATE 12 · DEFER 4 · KEEP-I 2 ·
DELETE 1 · ARCHIVE 0. 18 humane clusters; 0 humane DELETE/ARCHIVE.**

Load-bearing outcomes:

1. **One clean DELETE** — the dispatch-dead provider quartet `codex/tools.py:390-443`
   (survivor `action_lifecycle.py:456-489`).
2. `legacy_state` was **live product** (browser-E2E-proven) — the
   `frontend.legacy_state_bridge` CONSOLIDATE became the root of the frontend order;
   `session.py` compression sequenced behind the JS weaning (2 genuine v2 gaps:
   `sidebar.sessions`/`recent_runs`).
3. `app.js` **not** deletion-ready as-is — `run_dogfood_release.py:185-186` fetched
   `/app.js`; release-harness migration was the prerequisite.
4. `sim_v1` was **reached** (`test_self_play.py:17`) → CONSOLIDATE (flip default to
   `sim_v2.1`, pin fixtures, fix `ARCHITECTURE.md:62` / `SELF_PLAY.md:19-21`).
5. 4 placebo/thin gates → KEEP-I (calibration protected — thinness reported, not fixed;
   missing `--family`).
6. 4 DEFER verdicts plus one deferred live-NIM span inside a KEEP-B cluster.

Quota honesty (current `/src` 13,949 at C₁): immediate deletions ~low-single-digit
percent, low-teens after the strangler — the ≥50% total-LOC target was a
refactor-and-sequence problem, not deletion. Stage D readiness: **yes for Wave 1 only**
(quartet DELETE + four independent structural folds: `codex.auth_state_dup`,
`codex.redact_secret_dup`, `scripts.lab_hub_structure`,
`scripts.browser_e2e_pipeline_fold`); prerequisites for the CONSOLIDATE chains; no for
quota-bearing frontend work and the DEFERs.

Artifacts under `…/20260705T021039Z-p12-next-stage-c1-verdicts/`:
`reachability/{root_set.md, coverage_union.json, dispatch_grep.txt,
js_legacy_state_audit.md}`, `framework-verdicts/{cluster_inventory.jsonl,
verdict_rows.jsonl, defer_ledger.md, placebo_gates.md}`,
`review/{c1_verdict_review.md, consolidation_order.md, quota_honesty.md}`.

---

## 5. Stage D — landed waves

Every wave kept the frozen gate green; validation lists are per-run logs.

### 5.1 Wave 1 — `20260705T035713Z-p12-next-stage-d-wave1`

Implemented only the accepted Wave 1 rows: `codex.provider_quartet_dead` (deleted from
`CodexToolRuntime` with an inverted quarantine test), `codex.auth_state_dup` (auth-state
truth → `frontend.runtime`), `codex.redact_secret_dup` (shared redaction primitive,
distinct key sets), `scripts.lab_hub_structure` (lab hub imports via
`scripts.lab_modules`), `scripts.browser_e2e_pipeline_fold` (implementation in
`run_browser_e2e.py`; `run_external_browser_flow.py` kept as compatibility shim;
`browser_e2e.spec.mjs` explicitly retained as optional Node-runner coverage).
Validation: py-test 160✓ (10 skipped), check-invariants 0, p12-release `ok: true`,
browser-e2e (CDP), swift-test 17✓, swift-ipc-test 9✓; fixture app exercised
goal→stage→commit→undo→feedback→replay export with 87 replay records, no live writes.
`make dogfood-release` remained red outside Wave 1 scope (bundle-CDP + occupied-port +
artifact-validation issues). Report: `step_d_wave1_report.md`.

### 5.2 Blocker-fix pass — `20260705T043439Z-p12-next-stage-d-blocker-fixes`

Fixed the dogfood app-bundle CDP blocker and the occupied-port launch race; landed the
safe non-Wave-1 chains: `frontend.legacy_state_bridge`, `frontend.static_legacy`,
`dg.self_play.sim_v1`, `dg.fatigue_field_residue`, `env.envelope_v1_flatten`,
`codex.plan_ordering_triplication`. Result: served JS no longer reads `legacy_state`;
`app.js` + `frontend_state.sample.json` deleted; runtime envelopes v2/r1-only;
`sim_v2.1` default; fatigue residue replaced by interruption-tolerance vocabulary; one
shared plan-ordering validator. Validation: py-test, check-invariants, p12-release,
browser-e2e, dogfood-release, swift-test, swift-ipc-test, `run_live_nim_schema_gate.py`,
live-diffusiongemma-e2e, live-codex-e2e all passed. `live-eventkit-e2e` ran non-mutating
only (`authorization_status: write_only`, `mutation_enabled: false`). Report:
`step_d_blocker_fix_report.md`.

### 5.3 D2 session-brain decomposition — `20260705T053214Z-p12-next-stage-d2-session-brain`

Extracted the fixture/local conversation subsystem into
`frontend/session_conversation.py`; decomposed `DogfoodSessionState` through focused
snapshot/persistence controllers, keeping it as the public composition root.
**`session.py`: 2222 → 1316 lines** (decomposition, not global deletion: touched session
modules total 2,308 lines after seam overhead). Full gate set passed; fixture app CDP
validation passed at `http://127.0.0.1:8787`. Report: `step_d2_session_brain_report.md`.

### 5.4 EventKit blocker fix — `20260705T055514Z-p12-next-eventkit-blocker-fix`

With operator-granted Apple Calendar full access, the app-bundled EventKit bridge passed
the live materialization probe: commit `committed`/`materialized`, undo `reverted`,
provider rollback `rollback_verified`, 14 replay records. Dogfood release harness scopes
`CALENDAR_PILOT_EVENTKIT_RELEASE_BRIDGE` to the live sub-gate with
`CALENDAR_PILOT_REQUIRE_EVENTKIT=1`. EventKit permission hold resolved for this machine.
Report: `eventkit_blocker_fix_report.md`.

### 5.5 D2 official pipelines — `20260705T174108Z-p12-next-stage-d2-official-pipelines`

Generated and validated the locked 120-file seed corpus; `make lab-validate-seeds` and
`make lab-run SEED=experiments/seeds/seed_founder_baseline.json RUNTIME=fixture`
completed. Program A tooling caught up to its docs: `run_shadow_frontier.py` and
`make_calibration_report.py` gained additive `--family`; the shadow path ran end-to-end
(1 `create_prep_block` shadow candidate, 1 provider preview, 0 commits, calibration
`hold` with 0 matched examples). EventKit sandbox restored to P11-style env targeting:
bridge fails closed on unavailable explicit calendar ids/titles, explicit
`ensure_calendar` command added, verification via fresh provider readback with stable
created IDs. Sandbox: `CalendarPilot SelfPlay` with
`CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1` and
`…_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"`; this Mac exposed no local EventKit
source, so the calendar was created with explicit `source_policy: default_if_no_local`;
all writes targeted only that sandbox title. Provider-backed self-play: **5
`swift_ipc_eventkit_sandbox` episodes, all `create_prep_block`, 0 denials, first commit
`materialized`, verify `verified` with `local_time_echo_ok: true`, later write
idempotent, replay invariants `ok: true`, rollback cleanup `rollback_verified: true`,
0 unverified rollback records.** Full gate set incl. `make mac-app-build` and a
sandboxed live-EventKit-enabled `make dogfood-release` passed. **Blocker B-001
resolved.** Remaining holds evidence-only. Report:
`stage_d2_official_pipelines_report.md`.

---

## 6. Step E — the instrument gate that closed P12

Why it existed: Stage D2 proved the runway, but `make p12-release` was not yet a
sufficient ruler for compression — the release target exercised the deterministic spine
while live Codex / live NIM / live EventKit / Swift IPC / browser E2E / dogfood evidence
lived beside it, and three legs were placebo (`reward_heads` constant-zero purity,
`policy_ablation` pass-shaped constants, `calibration` hold counted as green). Step E's
mandate: make the ruler truthful, pin it, record known-red flags, ship `Belief` and
`explain()` — and only then allow destructive waves.

All Step E runs pinned instrument SHA `84fd6bd0da17f0f1aed4d6222f56373732757caf`
(the completing run re-pins in its own bundle's `INSTRUMENT.sha`); evidence under
`calendar-pilot-p12/runs/p12_next_evidence/<run>/instrument/`. No deletion or
compression landed in any Step E run.

| run | decision | what moved |
|---|---|---|
| `20260706T191434Z-step-e-instrument` | hold | De-placebo landed: `reward_heads` scans replay rows, holds on `consumed_action_rows: 0`, synthetic non-ActionStream reward fails with row ids; `policy_ablation` reuses named `frontier_diff`+`scorecard`+reward-head inputs, holds on empty/malformed; `calibration` preserves `matched_examples: 0`, family `create_prep_block`, `decision: hold`. Live codex + diffusiongemma legs ran and passed; EventKit root-listed (`write_only`, `configured: false`, `mutation_enabled: false`). Known-red flags pinned in `known_red_flags.json`. Belief/`explain()` explicitly held in `belief_explain_report.md`. |
| `20260706T193733Z-step-e-blocker-fix` | hold | `reward_heads` passes from a derived real ActionStream reward replay: 12 included action reward rows, 5 excluded non-ActionStream payload rows in the manifest; `policy_ablation` passes with 8 per-ablation frontier/scorecard reruns. `p12-release` correctly exits `decision: hold`. |
| `20260706T211543Z-step-e-current-blockers` | hold | EventKit rerun still root-listed (`write_only`, `configured: false`, `mutation_enabled: true`, `materialization.status: blocked`). Replay scan: 12 create-prep reward rows, 0 ActionStream feedback rows → no calibration pass claimed. |
| `20260706T212343Z-step-e-finish` | hold | Narrow instrument fix: stale `eventkit_materialization.json` overwritten on blocked/skipped probes. Same holds; full local gate set passed with `p12-release` hold. |
| `20260706T214346Z-step-e-retry` | hold | EventKit retry unchanged; reward_heads/policy_ablation stable at pass. |
| *(operator observation)* | — | The repeated EventKit retries were not exercising the user-visible app access point (no app/permission surface observed; the visible path landed in VS Code). Ruling: treat CLI-bridge evidence as root-list health only; require an app-access preflight artifact before claiming unblock. |
| `20260706T215430Z-step-e-app-access` | hold overall; EventKit cleared | Preflight named the frontmost app, then launched `dist/CalendarPilot.app` + a `live_provider` instance using the packaged `CalendarPilotEventKitBridge.app`: `authorization_status: full_access`, `configured: true`. Explicit `CalendarPilot SelfPlay` `make live-eventkit-e2e` with the packaged bridge **materialized, verified, and rolled back** the probe event (`materialization.status: passed`, commit `committed`, undo `reverted`). |
| `20260706T220150Z-step-e-complete` | **pass** | `make p12-release` → **`decision: pass`**, all checks green incl. calibration and `belief_explain`. Calibration consumes real ActionStream UI feedback for `create_prep_block` (`matched_examples: 1`, `real_source: human_feedback`) with the low-volume bias pinned (not autonomy-promotion volume). Belief/object-level `explain()` shipped as a versioned object contract with tests/report coverage for Belief, Authority denial/revocation, Candidate, Provider, and Trajectory. `reward_heads` pass with 13 ActionStream reward rows; `policy_ablation` pass with 8 per-ablation reruns. App-bundled EventKit mutation reran `full_access`/`configured: true`/`mutation_enabled: true`, materialization `passed`, commit `committed`, undo `reverted`, rollback verified. Gates: py-test, check-invariants, contract-vectors, p12-release, swift-ipc-test, browser-e2e, dogfood-release, explicit sandboxed live-eventkit-e2e. **Blocker B-004 resolved. Step E complete; P12 closed.** |

**Wave-harness follow-up** (landed with Step E; commits in §8.5): C-VAR report from a
frozen seed set + pinned `experiments/promoted/CURRENT.json` + seeded bootstrap variance
+ promotion-decision comparison + borderline top-candidate flip-rate
(`scripts/run_cvar_report.py`, `experiments/configs/cvar_seed_set.json`); B_migrate
dual-run assertion harness for old `DogfoodSessionState` snapshots vs projected
`view_state.v2` (`scripts/run_b_migrate_dual_run.py`); versioned eight-field
experiment-record schema/template (`contracts/experiment_record.schema.json`);
`interruption_tolerance_v1` now emits a real `Belief` object and replay row.
`make p12-release` includes `cvar` and `b_migrate` legs. **Blocker B-005 resolved.**
Every behavior-changing wave must cite those reports in its experiment record — the
standing discipline lives in the roadmap.

---

## 7. Program A state at freeze

The cold-start runway (protected throughout the audit — import/shadow/preview/
calibration/promotion scripts, the feedback capture path, the ActionStream reward path,
and all B-invariants were no-touch) remained data-bound, by design:

```text
target   matched_examples >= 20; explicit_feedback_events >= 10;
         provider_preview_examples >= 10; rollback_pass_rate = 1.0;
         hard_invariant_violations = 0; reward_purity_violations = 0;
         labels_in_authority_path = 0; sim-vs-real gaps measured or held
at close matched_examples = 1 (real human_feedback, low-volume bias pinned);
         create_prep_block promotion: hold; calibration: pass at Step E close
         with volume caveat pinned
```

The active runway gate and its resolution criteria live in the roadmap (§12 there);
this section is the freeze-time snapshot only.

---

## 8. Evidence tail (append-only; frozen at close)

### 8.1 Run ledger

| # | run id | git SHA | scope | decision |
|---|---|---|---|---|
| 1 | `20260703T224814Z-p12` | `8f484f40ec4fb48cd178e2f4e815bed1f9efc0e6` | P12 baseline test pass (19 steps) | pass |
| 2 | `20260704T013457Z-p12-next-lineage` | — | premature retention artifacts | quarantined (non-evidence) |
| 3 | `20260704T015059Z-p12-next-stage-a` | — | Stage A lineage discovery, 44 findings | review |
| 4 | `20260704T024144Z-p12-next-stage-a-ledger-repair` | — | Stage A/B ledger repair | review |
| 5 | `20260704T032235Z-p12-next-stage-b-acceptance` | `906cc68` | Stage B acceptance: 39/2/3; expansion INSUFFICIENT (20.8%) | accepted w/ blockers |
| 6 | `20260704T034739Z-p12-next-symbol-expansion` | `906cc68` | structural expansion: 1,493 rows + 127 waivers; 27/54 ready | partial |
| 7 | `20260704T041118Z-p12-next-stage-c-readiness` | — | readiness ACHIEVED: 54/54, 1,506 rows, 119 waivers, 0 blockers; B-SA-001/002/003 resolved | achieved |
| 8 | `20260704T060917Z-p12-next-line-provenance` | — | 29,888 lines: 20,279 mapped / 3,358 waived / 6,251 blocked (41 files) | review |
| 9 | `20260704T221313Z-p12-next-stage-c0-framework` | `a058bb2` | C₀ retention framework; no verdicts | done |
| 10 | `20260705T021039Z-p12-next-stage-c1-verdicts` | `8cec9d4` | C₁ verdicts: 55 rows; KEEP-B 36 / CONSOLIDATE 12 / DEFER 4 / KEEP-I 2 / DELETE 1 / ARCHIVE 0 | done |
| 11 | `20260705T035713Z-p12-next-stage-d-wave1` | — | Wave 1: quartet DELETE + 4 structural folds | landed |
| 12 | `20260705T043439Z-p12-next-stage-d-blocker-fixes` | — | dogfood/live gates green; legacy_state, app.js, sim_v1, fatigue residue, envelope v1 retired | landed |
| 13 | `20260705T053214Z-p12-next-stage-d2-session-brain` | — | session.py 2222 → 1316 decomposition | landed |
| 14 | `20260705T055514Z-p12-next-eventkit-blocker-fix` | — | live EventKit write/rollback probe unblocked | landed |
| 15 | `20260705T174108Z-p12-next-stage-d2-official-pipelines` | — | seeds/lab/runway end-to-end; EventKit sandbox self-play 5 episodes; B-001 resolved | complete |
| 16 | `20260706T191434Z-step-e-instrument` | instrument `84fd6bd0da17f0f1aed4d6222f56373732757caf` | de-placebo legs; flags pinned | hold |
| 17 | `20260706T193733Z-step-e-blocker-fix` | instrument `84fd6bd…` | reward_heads 12 rows pass; ablation 8 reruns pass | hold |
| 18 | `20260706T211543Z-step-e-current-blockers` | instrument `84fd6bd…` | EventKit still root-listed; 0 feedback rows | hold |
| 19 | `20260706T212343Z-step-e-finish` | instrument `84fd6bd…` | stale-artifact fix; gates pass w/ release hold | hold |
| 20 | `20260706T214346Z-step-e-retry` | instrument `84fd6bd…` | EventKit retry unchanged | hold |
| 21 | `20260706T215430Z-step-e-app-access` | instrument `84fd6bd…` | app-access preflight; EventKit materialization passed | hold (EventKit cleared) |
| 22 | `20260706T220150Z-step-e-complete` | pinned in bundle `INSTRUMENT.sha` | `p12-release` → `decision: pass`; Belief/explain shipped; B-004 resolved | **pass — P12 closed** |

Evidence roots: `calendar-pilot-p12/runs/p12_evidence/` (run 1) and
`calendar-pilot-p12/runs/p12_next_evidence/` (runs 2–22).

### 8.2 Blocker ledger (final states)

| id | type | resolution |
|---|---|---|
| B-001 | environment (live EventKit + provider-backed self-play) | **resolved** `20260705T174108Z`: `CalendarPilot SelfPlay` sandbox configured; probe targeted sandbox title; self-play with verified readback/idempotency/rollback cleanup; explicit `source_policy: default_if_no_local` on this Mac (no local EventKit source) |
| B-002 | data (cold-start runway) | **open at freeze**: matched examples and explicit feedback below threshold; resolved by calendar time + Program A collection, not engineering |
| B-003 | quality (frontier measurement) | **open at freeze**: `OTHER_intent_rate` and `expected_intent_hit_rate` are baseline flags; frozen at pin; deletion waves are not owner unless they worsen them; owned by a frontier-quality follow-up |
| B-004 | instrument (Step E final gate) | **resolved** `20260706T220150Z`: `p12-release` → `decision: pass`; real-row reward_heads; re-graded policy_ablation; human-feedback calibration; Belief/`explain()` contract; app-bundled EventKit `full_access` commit/verify/rollback |
| B-005 | instrument (C-VAR pre-wave certificate) | **resolved**: C-VAR report over frozen seed set + pinned `CURRENT.json`, seeded bootstrap variance, borderline flip-rate; `p12-release` includes the C-VAR leg |
| B-SA-001 | lineage (P7 `calendar-pilot-updated 2`) | **resolved** `20260704T041118Z`: proven P8-era accumulated snapshot (P8 files present, P9 `environment/` absent); 0 current symbols depend on it alone |
| B-SA-002 | lineage (P8 frontend duplicate pair) | **resolved** `20260704T041118Z`: `frontend 2` proven P8-era (same content test); 0 current symbols depend on it alone |
| B-SA-003 | lineage (P8.5 dogfood/safety row) | **resolved** `20260704T041118Z`: 0 current symbols first-seen in the P8.5 folder; session/live/release originate P8; P8.5 is doc/runway only |

### 8.3 Known-red data-quality flags (pinned at `INSTRUMENT@84fd6bd0…`, verbatim)

```json
{
  "OTHER_intent_rate": 0.1429,
  "expected_intent_hit_rate": 0.0,
  "matched_examples": 0,
  "create_prep_block_promotion": "hold",
  "calibration_decision": "hold"
}
```

Recorded in `known_red_flags.json` at pin time so future waves are judged against the
real before-state. Not owned by deletion waves unless a wave worsens them.
(`matched_examples` later moved 0 → 1 at `20260706T220150Z-step-e-complete`; the two
intent-rate flags were still red at freeze.)

### 8.4 Baseline measurements

Tracked LOC as measured 2026-07-03 (pre-audit "before"):

```text
src (Python)      13,949      frontend (js/html/css)  1,041
tests              4,025      contracts (json)        1,999
scripts            5,257      docs (md, incl. history) 1,329
Swift              3,659      TOTAL                  ~31,259
```

The audit's phase target (≤ 15,700 tracked, ≥ 50% cut) was corrected by C₁'s quota
honesty (§4.8) and superseded by the roadmap's LOC trajectory; recorded here as the
historical target only. Source census at expansion: 54 files / 136 classes / 132
top-level functions / 532 methods / 14 nested defs / 814 AST symbols (+ 69 module
constants, 549 dataclass fields rowed; 119 class-attr waivers).

### 8.5 Landed commits (workspace repo)

```text
4b6ffb2b6e39e10ba3a7a5a2296e01128ec7da6d  fix: complete p12 step e instrument
    (belief/calibration/explanation contracts + schemas, explain.py, de-placebo
     reward_heads/policy_ablation/calibration, run_p12_release extensions,
     test_step_e_instrument_reports.py; 21 files, +2185/−67)
7ce95cb2c98c3cc817dee0650f716e68f4592696  fix: add p12 wave harness
    (cvar/b_migrate/experiment_record schemas + scripts, cvar seed set + thresholds,
     promoted/CURRENT.json pin, test_wave_harness.py; 24 files, +816/−22)
906cc68   chore: checkpoint p12 workspace   (Stage B / expansion checkpoint)
a058bb2   Stage C₀ framework state          (runtime source at C₀)
8cec9d4   Stage C₁ verdict state            (runtime byte-identical to a058bb2)
```

Baseline run SHA `8f484f40ec4fb48cd178e2f4e815bed1f9efc0e6` is from the implementation
repo history (branch `codex/dogfood-macos-app`), predating the workspace checkpoints.

### 8.6 Sandbox / environment constants proven in evidence

```text
EventKit sandbox calendar   "CalendarPilot SelfPlay"
env                          CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1
                             CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"
source policy on this Mac    default_if_no_local (no local EventKit source exposed)
P11 precedent                "CalendarPilot Sandbox" unblock, same shape
release-gate scoping         CALENDAR_PILOT_EVENTKIT_RELEASE_BRIDGE (live sub-gate only),
                             CALENDAR_PILOT_REQUIRE_EVENTKIT=1
```

---

## 9. Dropped in consolidation (each with why; everything survives in the archive)

1. `P12-direction.md` Steps 1–17 full command blocks, artifact checklists, progress
   templates, and the working ledger / final-acceptance templates — framework
   scaffolding, superseded by the executed results (§3) and the wave harness.
2. `P12-direction.md` contract field listings (MeasurementReport, CalibrationReport,
   SemanticSignal, CurriculumRun, PolicyAblationReport, AutonomyFamilyPromotion JSON
   bodies) — now owned by `calendar-pilot-p12/contracts/*.schema.json` (versioned).
3. `P12-test.md` per-step command blocks, required-assertion lists, negative-test
   fixtures, and blank checklist/ledger templates — templates, not evidence; the
   executed run records are preserved in §3.
4. `P12-next.md` per-file 54-row source assignment table — workflow columns (owner/
   status) were uniform; totals kept in §4.5/§8.4; per-symbol truth is
   `…stage-c-readiness/lineage/expanded_symbol_lineage.jsonl`.
5. `P12-next.md` operational command blocks (evidence-bundle setup, daily runway
   procedure, lineage/reachability commands, Step E pin commands) and the §12 PR
   sequence — execution instructions, superseded by the wave harness + Makefile.
6. `P12-next.md` §6 per-area LOC quota rationale — planning content corrected by C₀
   (several hints did not survive code reading) and superseded by C₁ + the roadmap;
   baseline numbers kept verbatim (§8.4).
7. Repeated restatements of the three-stream doctrine, B-invariants, and status
   vocabulary across the three originals — merged into §2 (single home; runtime truth
   in `calendar-pilot-p12/docs/SIGNAL_STREAMS.md`).
8. P11 preamble notes at the top of `P12-direction.md` — the P11 completion claim is
   anchored by `Do-not-reference/P11-test.md`; the D2 sandbox correction is preserved
   in §5.5/§8.6.

Nothing else was intentionally dropped. Every run id, git SHA, verdict count, blocker
resolution, threshold, and named artifact path from the originals appears above.

## 10. Tombstones

| original | archived at | merged into |
|---|---|---|
| `P12-direction.md` (1,685 lines) | `Do-not-reference/P12-direction.md` | §1–§2 |
| `P12-test.md` (2,074 lines) | `Do-not-reference/P12-test.md` | §3 |
| `P12-next.md` (1,364 lines) | `Do-not-reference/P12-next.md` | §4–§8 |

The forward architecture formerly named `P12-P17-compression-roadmap.md` continues,
renamed, as [compression-roadmap.md](compression-roadmap.md).

*Frozen 2026-07-09. Append nothing; correct nothing in place. If P12 evidence turns out
wrong, record the correction in the living roadmap and cite this section.*
