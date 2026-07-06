According to a document from **July 3, 2026**, P11 is complete: the final report marks the overall decision as **pass**, with deterministic P11 promotion evidence passing required gates, trajectory/replay/contract/provider/self-play/frontend/release checks complete, and remaining live NIM/EventKit issues resolved through unblock reruns.

Post-D2 correction from **July 5, 2026**: the P12-next EventKit/provider-backed self-play path is now proven on this machine. The recent sandbox setup is `CalendarPilot SelfPlay` with `CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1` and `CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"`; P11's older unblock used the same shape with `CalendarPilot Sandbox`. The current bridge now refuses unavailable explicit calendar ids/titles instead of falling back to `default`, exposes an explicit `ensure_calendar` setup command, verifies EventKit writes through fresh provider readback with stable created IDs, and passed a five-episode `swift_ipc_eventkit_sandbox` `create_prep_block` run with verified rollback cleanup. This dogfood Mac had no local EventKit source exposed, so `CalendarPilot SelfPlay` was created with explicit `source_policy: default_if_no_local`; all writes still targeted only that sandbox title. The remaining hold is evidence volume for `create_prep_block` promotion, not EventKit plumbing.

# What's next

P11 proved that CalendarPilot has a trustworthy **trajectory substrate**. P12 should prove that the substrate produces a compounding learning system.

The next phase is not "add more features." It is:

> **Turn the lab from a correctness gate into an experimental engine that can safely discover, measure, promote, and roll back increasingly autonomous calendar behavior — fed by honestly separated human signals.**

The P11 judgment standard is already the right north star: typed frontier quality improves; bounded acting remains recoverable; self-play does not flatter policy self-belief; training rows have provenance; promotion beats the incumbent beyond measured noise; every claim is backed by replay.

I would name the next phase:

# P12 — Lab as Instrument, Policy as Product, Signals as Truth

P11 made the loop valid. P12 should make the loop **scientific, scaled, economically useful — and honest about where its human signals come from.**

---

# The data-framework rethink: three streams, not one blob

This is the P12 architectural correction, and it comes before any new feature. It is the direct result of a first-principles review of what the system actually *knows* about the human, versus what it *pretends* to know.

## The critique, in one field

`UserBiography.notification_fatigue: float` is the emblem. Today that scalar:

```text
- lives on the biography as if it were a declared fact         (types.py)
- gets nudged by reward events through an ad-hoc rule           (biography.py update_from_reward)
- gets mixed with recent-dismissal counts inside pressure reads (signals.py: fatigue + 0.06 * recent_dismissals)
- conditions sim_v2 acceptance as "seed ground truth"           (self_play.py)
- leaks into Codex prompts as a magic number                    ("Current notification fatigue=0.62")
```

But "fatigue" is an **unobservable psychological state**. There is no sensor for it. In production the only ways to obtain it are: ask the user ("what's your energy level today?" — terrible UX, and the answer would still be unreliable), or make it up. A learning system whose reward and timing decisions depend on a made-up scalar is not learning about the user; it is learning about its own fiction.

The escape is already visible in the code's own embryo: `recent_dismissals` in `signals.py` is a *behavioral* quantity — verifiable, timestamped, replay-visible. The correction is to make that the rule, not the buried exception: **internal states are never declared; they are estimated from verifiable behavior, and the estimator is versioned, evidence-cited, and calibrated.** "Fatigue" the word is banned as a data field; "dismissal streak length," "hourly dismissal rate," "response latency trend" are the measurables. What the policy consumes is a derived signal (e.g., `interruption_tolerance`) with citations.

## The three streams

The deeper problem the fatigue field exposes: the current data framework does not separate three epistemically different sources. P12 separates them everywhere — contracts, replay, reducers, simulators, UI:

```text
Stream A — ActionStream (interpretable human actions on the app)
  accept, undo, dismiss, ignore, edit, explicit_wrong, explicit_not_needed,
  label_disabled, snooze, feedback text acts.
  Nature: discrete, timestamped, verifiable, high-trust, FAST-moving.
  Role:   the ONLY reward truth. Also the measurement stream for estimators.

Stream B — WorldStream (human calendar data)
  events, attendees, tasks, free/busy structure, provider truth, device context.
  Nature: dense, factual, provider-verifiable (Swift-owned), medium-trust.
  Role:   state estimation and candidate generation. It is the WORLD,
          not a preference source. Preferences read off the world must
          arrive as evidence-cited derived signals, never as silent assumptions.

Stream C — BiographyStream (human self-description)
  profile settings, conversations with Codex, corrections, declared preferences.
  Nature: self-reported or conversational, SLOW, fluid, least predictable,
          legitimately revisable by the user at any time.
  Role:   a PRIOR over the policy — shapes generation and ranking,
          decays, is user-editable — and is NEVER reward truth.
```

Each stream gets its own flow because each has different dynamics and different failure modes:

```text
             latency      trust    drift model                update flow
ActionStream minutes      highest  noisy but unbiased-ish     per-event reward attribution
Derived      days–weeks   high     smoothed estimate w/ drift windowed estimator + decay
  signals                          (innovation-monitored)
Biography    weeks–months lowest   adversarially wrong is     user edits + evidence-backed
  priors                           allowed (people change,     reconciliation, capped weight
                                   misreport, aspire)
```

Control-theory reading: this is observer design. Fast measurements (Stream A) correct slow state estimates (derived signals) the way innovations correct a filter; the biography is the prior, and a persistent gap between prior and measurement is not an error to silently resolve — it is a **drift finding** to surface. RL reading: Stream A is the reward channel; Streams B and C are features; letting features leak into the reward function is how a policy learns to satisfy its own inputs. Systems reading: three streams means three message types with different contracts and lifecycles — collapsing them into one "profile" object was the original sin.

## Fast, slow, and prior — the indicator system

```text
FAST indicators   (per event):    accepted / dismissed / undone / edited / label_disabled
                                  → reward events, streak features, immediate policy evidence
SLOW indicators   (per window):   derived semantic signals with confidence + half-life
                                  → e.g. interruption_tolerance, evening_protection,
                                    prep_affinity, batching_preference
PRIORS            (per human):    declared/conversational biography claims
                                  → capped-weight ranking features; reconciled against
                                    evidence when they conflict; never in reward
```

The biography being "less predictable" is not a bug to engineer away — it is the honest property of self-description. We control it with **enough data and fluidity**: evidence accumulates in the fast stream, slow signals track it with explicit lag, and the prior is allowed to be wrong, editable, and decaying.

## Codex's expanded role: the semantic annotator

Codex is the right layer to **autonomously create semantic signals**: it reads ActionStream + WorldStream windows and proposes typed labels —

```text
"dismisses evening suggestions"        evidence: 9 dismissal rows after 20:00 across 3 weeks
"accepts prep blocks near client calls" evidence: 6 accepted create_prep_block rows adjacent to external events
"protects Tuesday mornings"            evidence: 4 moved/declined intrusions on Tue 09:00–11:00
```

— as `SemanticSignal` objects with citations, confidence, and a half-life. This is M3 discipline (every tuning cites replay) extended to the human model: **no label without evidence.** Proposals are cheap and reversible; activation is governed (below). This turns the dead zone between "raw feedback" and "biography" into an inspectable pipeline, and it is better UX than interrogation: Codex may ask the user a question only to *reconcile a contradiction it can cite* ("You said you like morning focus blocks, but you've moved five of the last six — should I stop suggesting them?"), never to poll internal state.

## Swift's expanded role: the label authority surface

Users must be able to **see and control which semantic labels are used in recommendations**. That control is an authority surface, so it follows the grant pattern, which the architecture already trusts:

```text
Codex proposes a SemanticSignal            (like proposing an action)
The user activates/disables/corrects it     through a Swift-owned settings surface
The registry holds activation state         (like the grant registry)
The policy consumes ACTIVE labels by id     (like carrying grant ids)
Every activation change is an audit row     (replay-visible, user-attributed)
```

And one hard rule with a barrier invariant behind it: **a semantic label can influence ranking and timing, never authority.** "User seems to love automation" must never raise a tier or widen a scope.

A user disabling a label is itself a first-class FAST signal — among the strongest negative evidence the system can receive, and it must flow back into the estimator and the reducer.

---

# The immediate next work

Close the measurement gaps P11 intentionally left visible, and land the stream separation:

1. **Separate the three streams** in contracts, replay, reducers, simulators, and UI (this page's rethink; Steps 2, 5, 7 below).
2. **Retire declared fatigue; ship the first signal estimator.** `interruption_tolerance_v1` derived from dismissal/response behavior, versioned and calibrated; the declared scalar becomes legacy input only (Step 5).
3. **Measure sim-vs-real acceptance gap.** P11 explicitly notes this was not measured (Step 6).
4. **Measure latency and cost.** `latency_ms_p50/p95`, request counts, cost-quality tradeoffs (Step 3).
5. **Promote decomposed reward deltas to first-class metrics** (Step 8).
6. **Harden live NIM schema drift into a standing gate** (Step 14).
7. **Keep EventKit sandbox mutation as a standing provider gate** (Steps 11, 13).
8. **Begin action-family autonomy promotion** through the autonomy matrix, with rollback (Steps 9–10).

# The end goal for the lab framework

Alan Kay's answer: **the lab should become the medium in which CalendarPilot is built** — every idea an object, every object with messages, every message leaving evidence, every experiment replayable.

The end state is a **calendar autonomy wind tunnel**:

```text
seeded worlds (authored as BEHAVIOR, not psychology)
→ policy candidates
→ simulated and provider-backed trajectories
→ invariant checks
→ reward decomposition (ActionStream truth only)
→ variance estimates
→ frontier diffs
→ promotion or hold
→ rollback path
```

The lab should make it easy to ask: *under what world, with what behavioral history, with which active labels, under what authority, using what model/backend/prompt/tuning, did this action become better than the incumbent?* — and answer with replay, not vibes.

# The end goal for machine learning

John Schulman's answer: **learn a policy over trajectories, not a preference for pretty candidates — and never let the policy grade itself or eat its own fiction.**

```text
observation (WorldStream + behavioral features)
→ typed frontier
→ action outcome
→ decomposed reward (ActionStream only)
→ replay reduction (provenance-partitioned)
→ candidate tuning
→ marginal diff against CURRENT
→ promotion or hold
```

The next ML milestone is **P12.1: calibrated marginal improvement** — add or harden:

```text
sim_vs_real_acceptance_gap          estimator_calibration_gap
frontier_latency_ms_p50/p95         per-intent regret/interruption/social/utility deltas
nim_request_count                   policy confidence calibration
label_evidence_coverage             ablation reports for each tuning component
```

The policy should not merely win a scorecard. It should win for a reason that survives ablation — including ablation of the semantic labels themselves.

# The end goal for machine acting

Claire Tomlin's answer: **expand the safe reachable set without losing control of the unsafe set.**

Promote one action family at a time (`create_prep_block` → `add_buffer` → `protect_deep_work` → `batch_admin` → private flexible `move_meeting` → social shadow → sandbox-only `auto_apply_plan` → limited real `auto_apply_plan`, much later). For each family define state space, control input, authority, disturbances, bad reachable states, and barrier certificates — with two P12 additions to the disturbance and barrier lists:

```text
disturbances += biography drift (declared preference no longer matches behavior),
                label churn (user toggles labels), estimator lag
barriers     += labels-never-gate-authority invariant (B2),
                reward-purity invariant (B4)
```

The machine-acting end goal remains **delegated autonomy with bounded blast radius**.

# The end goal for self-play

Self-play should become the system's adversarial imagination — and its user models must be built from the same material as reality: **behavioral histories, not psychological scalars.**

```text
1. Scenario curriculum      authored as notification/action histories, stale observations,
                            dense days, social risk, provider failures, sync lag,
                            timezone drift, preference drift, biography-vs-behavior conflict.
2. Adversarial user models  accepts-now-undoes-later, ignores repeated pings,
                            edits generated blocks, dislikes opaque autonomy,
                            disables labels after surprises, reacts badly to social movement.
3. Provider-backed simulation  actual preview/commit/verify/rollback through sandbox providers.
4. Sim-vs-real calibration  simulated acceptance/undo vs dogfood outcomes, per action family,
                            plus estimator calibration on held-out behavior windows.
5. Failure-to-training mapping  finding → canonical key → replay row → tuning reduction → diff.
6. Anti-reward-hacking gates    engagement gaming, social creep, regret regression —
                                and reward purity (no biography in the reward path).
```

The self-play end goal is unchanged: make the policy fail cheaply, repeatedly, and informatively before users experience the failure.

# The three-lens synthesis

## Alan Kay: make better objects

The lab objects are the product language. P12 adds the signal objects:

```text
Seed                Scenario            RuntimeProfile      TraceEvent
ActionEnvelope      ProviderTransaction ReplayRecord        RewardEvent
SelfPlayEpisode     DogfoodObservation  HumanFeedbackEvent  PolicyTuning
FrontierDiff        Scorecard           CalibrationReport   PromotionRecord
AutonomyMatrixEntry ProviderCapability  SemanticSignal      SignalEstimatorReport
LabelActivation     BiographyDriftFinding
```

If an experiment cannot be expressed in these objects, the lab language is incomplete.

## Claire Tomlin: expand autonomy through verified control envelopes

Every new capability defines allowed control input, required authority, provider truth check, rollback semantics, rate cap, reachable bad states, barrier invariant, promotion gate. P12 adds: every new *signal* defines its stream, estimator version, evidence requirement, decay, and the invariant that keeps it out of the authority path. No action family — and no signal — moves up without a proof artifact.

## John Schulman: trust only marginal, variance-aware improvement

Every model update answers: what changed, what stayed fixed, which replay rows trained it, what baseline it beat, effect size relative to noise, which reward head improved/regressed, does it survive adversarial seeds, can we roll it back — and now also: **which signals fed it, from which stream, with what evidence, and does the improvement survive removing the labels?**

# Recommended P12 roadmap

```text
P12.0 — Stabilize the completed P11 gates (permanent regression floor)
P12.1 — Add missing measurement (latency, cost, reward-head deltas, calibration scaffolding)
P12.2 — Separate the three streams; ship signal estimators; retire declared fatigue
P12.3 — Dogfood shadow import + sim-vs-real and estimator calibration
P12.4 — Codex semantic annotator + Swift label registry + user control surface
Step E — Autonomy family promotion (create_prep_block first), reward-head gates enforced
P12.6 — Self-play curriculum (behavior-authored) + provider-backed self-play
P12.7 — Provider capability reports; provider truth beyond EventKit sandbox
```

# The deeper end goal

```text
CalendarPilot observes your calendar state,
estimates your tolerance from what you verifiably did — not what it imagines you feel,
imagines typed candidate futures,
chooses a right-moment action,
acts only under explicit authority,
verifies provider reality,
learns from outcome and regret,
lets you see and control the labels it has learned about you,
stress-tests itself in self-play,
and promotes autonomy only when evidence beats the incumbent.
```

The engineering end state gains one line: every user-visible action is also a training example; every training example is also an audit record; every promotion is also a reversible experiment; every experiment is also a product lesson; **and every belief about the human is either evidence-cited or labeled as a prior.**

# Bottom line

P11 answered: **Can we trust the loop?** Yes.

P12 should answer: **Can the loop learn safely from reality — through honestly separated signals?**

The ML system improves typed frontier policy against a current baseline. The acting system expands the safe reachable set one action family at a time. The self-play system discovers failures before users do. And the data system stops pretending to read minds: fast verifiable actions are the reward, slow derived labels are the model of the person, and the biography is a fluid, user-owned prior.

---

# P12 Direction: Lab as Instrument, Policy as Product, Signals as Truth

**File:** `p12-direction.md`
**Phase:** P12
**Status:** working direction
**Owner:** next implementation engineer
**Precondition:** P11 final acceptance passed
**Operating lenses:** Alan Kay, Claire Tomlin, John Schulman

## 0. One-sentence direction

P12 turns CalendarPilot's P11 trajectory substrate into an experimental engine that can safely learn from reality — by separating interpretable human actions, calendar world data, and human biography into three governed signal streams, calibrating simulation against dogfood behavior, and promoting autonomy one action family at a time.

P11 answered: `Can we trust the loop?`
P12 must answer: `Can the trusted loop learn safely from reality, from signals we can actually verify?`

---

# 1. End goal

## 1.1 End goal for the lab framework

A **calendar autonomy wind tunnel**: seeded worlds (authored as behavior) → typed candidate futures → simulated/provider-backed trajectories → invariant checks → decomposed reward → variance and calibration → frontier diff against CURRENT → promotion or hold → rollback path. It answers "under what world, behavioral history, active labels, authority, and model config did this action beat the incumbent?" with replay, provider verification, reward decomposition, variance estimates, and rollback evidence.

## 1.2 End goal for machine learning

A conservative, auditable policy-improvement loop over typed calendar trajectories, with measured improvement under distribution shift: more valid candidates, fewer OTHER intents, fewer schema repairs, fewer empty frontiers, better expected-intent hit rate, better utility, lower regret/interruption/social risk, lower undo rate, better calibration against real dogfood behavior — and reward computed from the ActionStream only.

## 1.3 End goal for machine acting

Expand the **safe reachable set** without losing control of the unsafe set. Every action family carries: state space, allowed control input, required authority, provider truth check, rollback semantics, rate cap, bad reachable states, barrier invariant, promotion gate, rollback plan. Semantic labels shape ranking and timing inside the envelope; they never move the envelope.

## 1.4 End goal for self-play

Adversarial imagination that predicts real failure before users do: scenario curriculum → adversarial user models built from behavioral histories → provider-backed execution → sim-vs-real calibration → failure-to-training mapping → anti-reward-hacking gates.

## 1.5 End goal for the data framework (new)

Three governed streams with different flows, trust, and speed:

```text
ActionStream   fast, verifiable, reward truth + estimator measurements
WorldStream    factual state, provider-verified, generation/ranking context
BiographyStream slow, fluid, user-owned prior — capped weight, decays, reconciled on conflict
```

Between fast and slow sits the derived layer: **SemanticSignals** produced by versioned estimators and the Codex annotator, evidence-cited, user-controllable, replay-visible. "Enough data and fluidity" is the operating principle: the fast stream accumulates evidence, the slow layer tracks it with explicit lag and decay, and the prior is allowed to be wrong and editable without breaking anything.

---

# 2. P12 doctrine

## 2.1 Alan Kay: make the lab objects better

Canonical objects (additions in bold):

```text
Seed, Scenario, RuntimeProfile, TraceEvent, ActionEnvelope, ProviderTransaction,
ReplayRecord, RewardEvent, SelfPlayEpisode, DogfoodObservation, HumanFeedbackEvent,
PolicyTuning, FrontierDiff, Scorecard, CalibrationReport, PromotionRecord,
AutonomyMatrixEntry, ProviderCapability,
**SemanticSignal, SignalEstimatorReport, LabelActivation, BiographyDriftFinding**
```

If an experiment cannot be expressed with these objects, the lab language is incomplete.

## 2.2 Claire Tomlin: promote only inside verified control envelopes

Autonomy expands one action family at a time (`create_prep_block` … `limited_real_auto_apply_plan`), each with safe set, unsafe set, disturbances, barriers, rollback. P12 adds the signal envelope: every signal declares stream, estimator version, evidence requirement, decay — and invariant B2 (labels never gate authority) is a barrier, not a convention.

## 2.3 John Schulman: trust only marginal, variance-aware improvement

Every policy update answers: what changed; what stayed fixed; which replay rows trained it; what baseline it beat; effect size vs noise; which reward head improved/regressed; survival on adversarial seeds; rollback. Plus: which stream fed each feature, and does the win survive `no_semantic_labels` ablation. No update promotes because it "looks smarter."

## 2.4 Shared data doctrine: the three-stream rules

```text
R1. Reward is computed from ActionStream rows only.                      (invariant B4)
R2. Every derived SemanticSignal cites ActionStream/WorldStream evidence. (invariant B1)
R3. No signal or label influences authority tier, scope, or grants.       (invariant B2)
R4. Label activation changes are user-attributed audit rows.              (invariant B3)
R5. Declared biography and derived signals never overwrite each other
    silently; persistent conflict emits a BiographyDriftFinding.          (invariant B5)
R6. Estimators are versioned; the same estimator version runs on
    synthetic and real streams.                                           (invariant B6)
R7. The system never prompts the user for internal state
    ("what's your energy level today?"). Evidence-cited reconciliation
    questions are allowed; affect polling is not.
```

---

# 3. P12 evidence directory convention

```bash
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-p12"
mkdir -p runs/p12_evidence/$RUN_ID
git rev-parse HEAD > runs/p12_evidence/$RUN_ID/git_sha.txt
git status --short > runs/p12_evidence/$RUN_ID/git_status.txt
```

Minimum bundle:

```text
runs/p12_evidence/<RUN_ID>/
  git_sha.txt
  git_status.txt
  p11_regression/
  signal_streams/
  measurement/
  dogfood_shadow/
  estimators/
  sim_real_calibration/
  semantic_labels/
  autonomy_family/
  self_play_curriculum/
  provider_capabilities/
  policy_learning/
  frontend/
  release/
  progress_log.md
  decision_log.md
```

---

# 4. P12 step-by-step framework

---

## Step 1 — Freeze P11 as the permanent regression floor

### Purpose

P12 work is not allowed to weaken trajectory integrity, replay completeness, contract versioning, provider rollback, self-play `sim_v2`, promotion semantics, or frontend trace surfaces.

### Required commands

```bash
make py-test          | tee runs/p12_evidence/$RUN_ID/p11_regression/py-test.log
make swift-test       | tee runs/p12_evidence/$RUN_ID/p11_regression/swift-test.log
make check-invariants | tee runs/p12_evidence/$RUN_ID/p11_regression/check-invariants.log
make contract-vectors | tee runs/p12_evidence/$RUN_ID/p11_regression/contract-vectors.log
make frontier-diff    | tee runs/p12_evidence/$RUN_ID/p11_regression/frontier-diff.log
make scorecard        | tee runs/p12_evidence/$RUN_ID/p11_regression/scorecard.log
make browser-e2e      | tee runs/p12_evidence/$RUN_ID/p11_regression/browser-e2e.log
make dogfood-release  | tee runs/p12_evidence/$RUN_ID/p11_regression/dogfood-release.log
```

### Acceptance

Python/Swift/invariants/vectors/browser/release pass; frontier diff and scorecard artifacts exist; no P11 invariant is relaxed without a named migration.

### Progress template

```md
## Step 1 — P11 Regression Floor
Date: / Engineer: / Git SHA:
Python: / Swift: / Invariants: / Vectors: / Frontier diff: / Scorecard: / Browser: / Release:
Failures: / Decision:
```

---

## Step 2 — Separate the three signal streams (new)

### Purpose

Make the ActionStream / WorldStream / BiographyStream split real in contracts and replay, so every downstream consumer (reducer, estimator, simulator, UI) can filter by stream instead of guessing. Today the streams are conflated: reward events, calendar structure, and biography claims all shape behavior without a declared boundary, and `notification_fatigue` sits on the biography while being nudged by rewards and mixed with dismissal counts.

### New artifacts

```text
contracts/semantic_signal.schema.json
contracts/signal_estimator_report.schema.json
docs/SIGNAL_STREAMS.md                      the three-stream doctrine as repo truth
tests/test_signal_stream_tagging.py
tests/test_reward_purity.py
```

### Required changes

```text
1. Every replay row gains signal_stream: "action" | "world" | "biography" | "derived" | "system".
   Mapping is mechanical by record type:
     reward, human feedback, label activations            → action
     raw_calendar_observation, provider_transaction        → world
     biography claims/corrections/conversation extractions → biography
     semantic_signal, signal_estimator_report              → derived
     everything else (envelopes, tool calls, tuning, …)    → system
2. RewardEvent reducer path asserts B4: reward reduction reads action-stream rows only.
   A biography or derived row reaching the reward computation is a hard violation.
3. BiographyStore entries gain kind: "declared" | "conversational" | "derived_signal_ref".
   Derived signals are NOT stored as biography claims; the biography may hold references.
4. UserBiography.notification_fatigue is marked legacy: still parsed for old seeds,
   no new writer, no new reader (Step 5 provides the replacement).
```

### New invariants (B-series), soft in Step 2, hardened per later steps

```text
B1 every SemanticSignal with kind=derived cites ≥1 action/world replay row
B2 no signal/label appears in authority tier, scope, or grant issuance paths
B3 every label activation change is a user-attributed replay row
B4 reward reduction consumes action-stream rows only
B5 declared-vs-derived conflicts emit biography_drift findings, never silent overwrite
B6 estimator outputs carry estimator_version; same version runs on synthetic and real streams
```

### Acceptance

```text
Replay rows carry signal_stream; mapping test covers every record type.
test_reward_purity proves a planted biography row in the reward path fails.
Legacy fatigue field parses but has no new writers (grep-able assertion in tests).
docs/SIGNAL_STREAMS.md exists and names the B-invariants.
```

### Progress template

```md
## Step 2 — Stream Separation
Stream tagging: / Reward purity: / Biography kinds: / Legacy fatigue writers: 0?
B-invariants (soft): / Failures: / Decision:
```

---

## Step 3 — Add first-class measurement for the gaps P11 left visible

### Purpose

P11 passed but left unmeasured: `sim_vs_real_acceptance_gap`, `latency_ms_p50/p95`, `nim_request_count`, and standalone reward-head deltas. P12 promotes these into first-class metrics, and adds the signal-layer metrics.

### New artifacts

```text
contracts/measurement_report.schema.json
contracts/calibration_report.schema.json
scripts/make_measurement_report.py
scripts/compare_measurement_reports.py
tests/test_measurement_report_contract.py
tests/test_reward_head_deltas.py
```

### Required `MeasurementReport` fields

```json
{
  "measurement_schema_version": "measurement_report.v1",
  "run_id": "", "git_sha": "", "runtime_mode": "", "policy_backend": "",
  "provider_backend": "", "policy_tuning_id": "",
  "frontier_latency_ms_p50": 0, "frontier_latency_ms_p95": 0,
  "codex_latency_ms_p50": 0, "codex_latency_ms_p95": 0,
  "provider_verify_latency_ms_p50": 0, "provider_verify_latency_ms_p95": 0,
  "nim_request_count": 0, "nim_retry_count": 0, "cost_per_valid_frontier": null,
  "valid_frontier_rate": 0, "empty_frontier_rate": 0,
  "model_generation_rejection_rate": 0, "OTHER_intent_rate": 0,
  "expected_intent_hit_rate": 0,
  "utility_delta": 0, "engagement_delta": 0, "regret_delta": 0,
  "interruption_delta": 0, "social_risk_delta": 0, "undo_regret_delta": 0,
  "rollback_pass_rate": 0, "provider_idempotency_pass": true,
  "hard_invariant_violations": 0, "soft_invariant_violations": 0,
  "label_evidence_coverage": null, "label_churn_rate": null,
  "estimator_calibration_gap": null, "derived_vs_declared_conflicts": null
}
```

### Acceptance

```text
MeasurementReport validates against schema and is emitted by scorecard or release flow.
Latency metrics present (null only for unsupported fixture paths).
Reward-head deltas computed per action family.
NIM request/retry counts recorded for live runs.
Signal-layer fields present (null allowed until Steps 5/7 land, then required).
Missing required metrics produce hold, not silent omission.
```

### Progress template

```md
## Step 3 — Measurement Layer
Schema: / Script: / Reward-head deltas: / Latency p50/p95: / NIM counts: / Cost:
Signal-layer fields: / Report artifact: / Failures: / Decision:
```

---

## Step 4 — Build dogfood shadow import

### Purpose

Before broader autonomy, CalendarPilot must learn from real calendar structure in shadow mode — importing all three streams separately: the WorldStream snapshot, the ActionStream history (notification/feedback outcomes), and the BiographyStream (declared profile), each tagged.

Shadow mode: real observation import, typed frontier generation, provider preview, **no commit by default**, human feedback capture, replay export, privacy/redaction policy.

### New artifacts

```text
scripts/import_dogfood_observation.py
scripts/run_shadow_frontier.py
scripts/run_shadow_provider_preview.py
docs/DOGFOOD_SHADOW.md
tests/test_dogfood_import_redaction.py
tests/test_shadow_mode_no_commit.py
tests/test_dogfood_import_stream_tagging.py
```

### Required properties

`DogfoodObservation` records: `observation_id, source_provider, provider_account_hash, calendar_count, event_count, task_count, time_zone_id, observed_at, redaction_policy, redaction_hash_salt_id, imported_at, streams_captured: ["world","action","biography"]`.

Shadow replay includes: observation ref, `frontier_generation`, `provider_transaction.preview`, scorecard `artifact_ref`, human feedback events if collected — every row stream-tagged.

### Commands

```bash
PYTHONPATH=src python scripts/import_dogfood_observation.py \
  --provider apple_eventkit \
  --out runs/p12_evidence/$RUN_ID/dogfood_shadow/imported_observation.json

PYTHONPATH=src python scripts/run_shadow_frontier.py \
  --observation runs/p12_evidence/$RUN_ID/dogfood_shadow/imported_observation.json \
  --out runs/p12_evidence/$RUN_ID/dogfood_shadow/shadow_frontier.json

PYTHONPATH=src python scripts/run_shadow_provider_preview.py \
  --observation runs/p12_evidence/$RUN_ID/dogfood_shadow/imported_observation.json \
  --frontier runs/p12_evidence/$RUN_ID/dogfood_shadow/shadow_frontier.json \
  --out runs/p12_evidence/$RUN_ID/dogfood_shadow/provider_preview.json
```

### Acceptance

```text
No commit occurs in shadow mode.
Provider preview is replay-visible.
Imported observation is redacted or explicitly marked local-only.
Human feedback can be captured against shadow candidates (ActionStream rows).
Shadow frontier quality metrics are reported.
All imported rows carry correct signal_stream tags.
```

### Progress template

```md
## Step 4 — Dogfood Shadow Import
Provider: / Observation: / Redaction: / Frontier: / Preview: / No-commit proof:
Feedback rows: / Stream tags: / Failures: / Decision:
```

---

## Step 5 — Signal estimators: retire declared fatigue (new)

### Purpose

Replace the unobservable `notification_fatigue` scalar with a **versioned estimator over verifiable behavior**. This is the fatigue critique made executable: nobody can measure "energy level" without asking (terrible UX), but dismissal streaks, hourly dismissal rates, and response-latency trends are in the ActionStream already (`notification_history` outcomes, reward events).

### The first estimator

```text
interruption_tolerance_v1
  inputs (ActionStream/WorldStream only):
    notification_history outcomes by hour-of-day (14–28 day window)
    dismissal streak length (consecutive dismissed/ignored suggestions)
    response latency trend where timestamps allow
    undo-after-accept events on notification-class actions
  outputs (SemanticSignal, kind=derived):
    interruption_tolerance_by_hour: {hour: score 0..1}
    dismissal_streak: int
    overall_tolerance: 0..1, with evidence row ids and sample counts
  properties:
    pure function over replay/observation windows; estimator_version stamped;
    deterministic given the same window (B6);
    emits signal_estimator_report replay row with inputs-hash and coverage.
```

### Migration (honest, staged)

```text
1. Seeds author BEHAVIOR, not psychology: high-fatigue personas are expressed as
   dense dismissed notification_history (the seed lint already ties fatigue ≥ 0.5
   to ≥5 history entries — that precedent becomes the rule; the scalar becomes
   derived-not-declared).
2. signals.py pressure read consumes interruption_tolerance_v1 output instead of
   biography.notification_fatigue + ad-hoc dismissal increment.
3. sim_v2 → sim_v2.1: acceptance conditions on estimator output computed from the
   seed's authored behavioral history — same anti-circularity guarantee (still no
   candidate predicted heads), same estimator code path as production (B6).
4. RightMomentModel/temporal controller read the derived signal.
5. Codex prompts cite the signal with evidence counts, not a bare scalar
   ("user dismissed 7 of last 8 evening suggestions"), which is also a better
   explanation surface.
6. biography.update_from_reward stops nudging the legacy scalar; the estimator
   owns behavior-derived state. Declared biography keeps only what users actually
   declared.
```

### New artifacts

```text
src/calendar_pilot/environment/signal_estimators.py   (or diffusiongemma/ equivalent)
scripts/run_signal_estimators.py
tests/test_interruption_tolerance_estimator.py
tests/test_estimator_synthetic_real_parity.py
tests/test_sim_v2_1_uses_estimator.py
```

### Acceptance

```text
Estimator is deterministic on fixed windows; version stamped; report row emitted.
Same estimator code produces signals on a synthetic seed and an imported dogfood
  observation (parity test, B6).
sim_v2.1 acceptance shifts when authored dismissal history changes, and does NOT
  shift when only the legacy scalar changes (the scalar is dead as an input).
No new reader of biography.notification_fatigue exists outside legacy parsing.
Estimator calibration harness exists: predicted next-window dismissal rate vs
  observed on held-out windows → estimator_calibration_gap.
```

### Progress template

```md
## Step 5 — Signal Estimators
Estimator: interruption_tolerance_v1 / Determinism: / Parity synthetic-vs-real:
sim_v2.1 wiring: / Legacy scalar readers: 0? / Calibration gap: / Failures: / Decision:
```

---

## Step 6 — Measure sim-vs-real acceptance gap

### Purpose

P11 proved `sim_v2` does not reward policy self-belief. P12 must prove whether the simulator (now `sim_v2.1`) predicts real behavior — and whether the estimator predicts real dismissals. This is the central calibration problem.

### Definitions

```text
sim_vs_real_acceptance_gap = |simulated_acceptance_rate − observed_shadow_or_dogfood_acceptance_rate|
also: sim_vs_real_undo_gap, sim_vs_real_ignore_gap, sim_vs_real_explicit_wrong_gap
plus: estimator_calibration_gap (from Step 5's held-out windows)
```

### New artifacts

```text
scripts/make_calibration_report.py
experiments/calibration/
tests/test_calibration_report.py
tests/test_sim_real_action_family_matching.py
```

### Required `CalibrationReport` fields

```json
{
  "calibration_schema_version": "calibration_report.v1",
  "run_id": "", "policy_tuning_id": "",
  "simulator_version": "sim_v2.1",
  "estimator_versions": ["interruption_tolerance_v1"],
  "real_source": "dogfood_shadow|provider_observed|human_feedback",
  "matched_examples": 0,
  "action_family_metrics": {
    "create_prep_block": {
      "sim_acceptance_rate": 0, "real_acceptance_rate": 0, "acceptance_gap": 0,
      "sim_undo_rate": 0, "real_undo_rate": 0, "undo_gap": 0, "sample_count": 0
    }
  },
  "overall_acceptance_gap": 0, "overall_undo_gap": 0,
  "estimator_calibration_gap": 0,
  "known_biases": [], "decision": "pass|hold"
}
```

### Initial thresholds (loose until real data accumulates)

```text
matched_examples >= 20
overall_acceptance_gap <= 0.30
overall_undo_gap <= 0.20
no action family with sample_count >= 10 has acceptance_gap > 0.40
estimator_calibration_gap <= 0.25 on held-out windows
```

### Acceptance

```text
CalibrationReport exists; each compared example links to replay rows.
Known biases are named. Insufficient data returns hold, not pass.
Calibration is computed per action family, not only pooled.
Estimator calibration is reported alongside simulator calibration.
```

### Progress template

```md
## Step 6 — Sim-vs-Real Calibration
Sim batch: / Dogfood source: / Matched examples: / Acceptance gap: / Undo gap:
Estimator gap: / Worst family: / Known biases: / Decision: / Failures:
```

---

## Step 7 — Codex semantic annotator + Swift label registry (new)

### Purpose

Expand Codex's role: it autonomously **creates** semantic signals from the ActionStream and WorldStream — evidence-cited label proposals — and Swift owns the surface where users **control which labels are active in recommendations**. This replaces mind-reading with governed inference, and replaces buried heuristics with inspectable objects.

### Required `SemanticSignal` fields

```json
{
  "signal_schema_version": "semantic_signal.v1",
  "signal_id": "",
  "user_scope_id": "",
  "label": "dismisses_evening_suggestions",
  "statement": "Dismisses suggestion notifications sent after 20:00",
  "kind": "derived|declared|conversational",
  "created_by": "codex_annotator|user|import|estimator",
  "evidence": ["replay_record_id", "..."],
  "evidence_window": {"from": "", "to": ""},
  "confidence": 0.0,
  "half_life_days": 28,
  "status": "proposed|active|disabled|expired|corrected",
  "activation": {"actor": "user|default_policy", "at": "", "surface": ""},
  "estimator_version": null
}
```

### Annotator behavior (Codex)

```text
- Runs over stream-tagged replay windows; proposes labels with citations (B1).
- Never proposes from biography alone; declared claims are already priors.
- May ask the user ONLY evidence-cited reconciliation questions
  ("You said X; the last N actions show Y — keep X?") — recorded as
  BiographyStream conversation events. Affect polling is forbidden (R7).
- Proposals are replay rows; nothing activates silently.
```

### Registry and control (Swift-patterned, mirrors AuthorityGrant)

```text
- Registry holds signals + activation state; policy consumes ACTIVE labels by id.
- Activation default policy: derived labels above confidence 0.7 may auto-activate
  for ranking/timing ONLY; any label the user disables stays disabled until the
  user re-enables it (user action is terminal authority on labels).
- Activation/disable/correct events: user-attributed audit rows (B3) —
  and label_disabled is itself a strong ActionStream negative signal fed back
  to the annotator and reducer.
- Settings surface: users see each active label, its plain-language statement,
  its evidence count, and controls (disable / correct / "not me").
- Hard barrier: registry state is invisible to grant issuance and tier checks (B2).
```

### New artifacts

```text
src/calendar_pilot/codex/annotator.py
src/calendar_pilot/environment/label_registry.py
Swift settings surface + kernel command for label activation receipts
scripts/run_semantic_annotator.py
tests/test_semantic_annotator_evidence.py
tests/test_label_registry_activation.py
tests/test_labels_never_gate_authority.py
tests/test_label_disable_is_action_signal.py
```

### Acceptance

```text
Annotator proposes ≥1 label on a fixture window with correct citations; a label
  without evidence is rejected at the contract layer (B1 hard).
Activation changes produce user-attributed replay rows (B3 hard).
A planted "label influences grant" path fails tests (B2 hard).
Disabling a label removes its effect from the next frontier (diffable) and emits
  an ActionStream row.
Declared-vs-derived conflict on a fixture emits biography_drift finding (B5).
label_evidence_coverage = 1.0 for active derived labels; label_churn_rate reported.
```

### Progress template

```md
## Step 7 — Annotator + Label Registry
Proposals: / Evidence coverage: / Activation rows: / B2 authority barrier:
Disable-as-signal: / Drift findings: / Churn rate: / Failures: / Decision:
```

---

## Step 8 — Promote reward-head deltas into gates

### Purpose

No candidate should promote on aggregate reward while hiding regressions in regret, interruption, or social risk. Note: with Step 5 landed, interruption-class heads are grounded in behavioral evidence (dismissals/undo), not declared fatigue — the gates below now police measured behavior.

### Required reward heads

```text
utility_delta, acceptance_delta, engagement_delta, long_horizon_delta,
regret_delta, interruption_delta, social_risk_delta, undo_regret_delta,
ignored_delta, explicit_wrong_delta
```

### New artifacts

```text
scripts/make_reward_head_report.py
tests/test_reward_head_report.py
tests/test_promotion_reward_head_gates.py
```

### Required gates

```text
utility_delta >= 0.00
regret_delta <= 0.00
interruption_delta <= 0.00
social_risk_delta <= 0.00 unless explicitly scoped social grant exists
undo_regret_delta <= 0.00
explicit_wrong_delta <= 0.00
engagement_delta cannot be the only positive delta
```

### Required anti-gaming checks

```text
engagement_gaming: engagement_delta > +0.05 AND utility_delta < +0.01
                   AND (regret_delta > 0 OR interruption_delta > 0)
social_creep:      social_risk_delta > 0 without new explicitly scoped social grant
regret_regression: undo_regret per episode rises > 20%
reward_purity:     any non-ActionStream row in the reward computation (B4) → hold
```

### Acceptance

```text
Promotion record includes reward-head deltas; hold names the failing head.
Scorecard displays reward-head deltas; frontend Learn surface renders them.
```

### Progress template

```md
## Step 8 — Reward-Head Gates
Report: / Promotion integration: / Scorecard: / Frontend: / Anti-gaming: / Failures: / Decision:
```

---

## Step 9 — Define the P12 autonomy ladder

### Purpose

Autonomy increases one action family at a time; the autonomy matrix is a promotion target, not a static config.

### Action-family order

```text
1. create_prep_block            5. move_private_flexible_hold
2. add_buffer                   6. social_shadow_move_meeting
3. protect_deep_work            7. auto_apply_plan_sandbox_only
4. batch_admin                  8. limited_real_auto_apply_plan
```

### New artifacts

```text
configs/autonomy_ladder.p12.json
scripts/propose_autonomy_family_promotion.py
scripts/promote_autonomy_family.py
tests/test_autonomy_family_promotion.py
tests/test_autonomy_matrix_rollback.py
```

### Required `AutonomyFamilyPromotion` fields

```json
{
  "promotion_schema_version": "autonomy_family_promotion.v1",
  "family": "create_prep_block", "from_tier": 2, "to_tier": 3,
  "required_scopes": ["commit_private", "undo"],
  "source_batches": [],
  "seed_pass_rate": 0, "self_play_pass_rate": 0,
  "provider_sandbox_pass_rate": 0, "human_feedback_pass_rate": 0,
  "rollback_pass_rate": 0, "sim_vs_real_acceptance_gap": 0,
  "reward_head_deltas": {}, "active_labels_at_promotion": [],
  "known_regressions": [], "gates": {},
  "decision": "promote|hold", "rollback_plan": ""
}
```

### Acceptance

```text
Autonomy promotion changes exactly one action family; hold names failing gates;
rollback plan included; matrix rollback tested; no social/compound autonomy
without family-specific evidence; promotion record snapshots which semantic
labels were active (labels inform the record; they never justify the tier — B2).
```

### Progress template

```md
## Step 9 — Autonomy Ladder
Family: / Tiers: / Scopes: / Evidence batches: / Reward deltas: / Calibration:
Rollback rate: / Active labels snapshot: / Decision: / Rollback plan: / Failures:
```

---

## Step 10 — First autonomy-family promotion: `create_prep_block`

### Purpose

Start with the safest useful family: private, reversible, high-utility, provider-verifiable, well represented in P11 fixtures.

### Required evidence

```text
5-seed smoke pass; 20-base-seed pass; flagged-seed pass; provider sandbox pass;
dogfood shadow candidates reviewed; sim-vs-real gap measured or insufficient-data hold;
rollback pass rate = 1.0; hard invariant violations = 0;
social_risk_delta <= 0; regret_delta <= 0; interruption_delta <= 0.
```

### Commands

```bash
PYTHONPATH=src python scripts/propose_autonomy_family_promotion.py \
  --family create_prep_block --batch <BATCH_ID> \
  --calibration runs/p12_evidence/$RUN_ID/sim_real_calibration/calibration_report.json \
  --out runs/p12_evidence/$RUN_ID/autonomy_family/create_prep_block_proposal.json

PYTHONPATH=src python scripts/promote_autonomy_family.py \
  --proposal runs/p12_evidence/$RUN_ID/autonomy_family/create_prep_block_proposal.json \
  --human-note "P12 create_prep_block autonomy review" \
  | tee runs/p12_evidence/$RUN_ID/autonomy_family/create_prep_block_promotion.log
```

### Acceptance

```text
Only create_prep_block changes; no social scope changes; no auto_apply_plan changes;
rollback command recorded; frontend Authority surface shows family-level autonomy.
```

### Progress template

```md
## Step 10 — create_prep_block Promotion
Proposal: / Decision: / Matrix diff: / Rollback command: / Frontend: / Failures:
```

---

## Step 11 — Extend provider sandbox into provider capability reports

### Purpose

Every provider must declare what it can safely do; promotion cannot require a capability a provider lacks.

### New artifacts

```text
contracts/provider_capability_report.schema.json
scripts/make_provider_capability_report.py
docs/PROVIDER_CAPABILITIES.md
tests/test_provider_capability_report.py
```

### Required provider capabilities

```text
read_observation, preview, commit, verify, rollback, idempotency,
external_id_mapping, sandbox_enforcement, rate_cap_denial,
local_time_echo, timezone_integrity, provider_error_replay
```

### Required providers

```text
deterministic, apple_eventkit, google_stub_or_sandbox, microsoft_stub_or_sandbox
```

### Acceptance

```text
Reports emitted for deterministic and EventKit sandbox; unsupported providers
declare unsupported operations instead of pretending support; provider-backed
self-play consumes capability reports; promotion cannot require a missing capability.
```

### Progress template

```md
## Step 11 — Provider Capability Reports
Provider: / Capabilities: / Unsupported: / Sandbox: / Idempotency: / Rollback:
External IDs: / Time echo: / Decision: / Failures:
```

---

## Step 12 — Grow self-play into a curriculum engine (behavior-authored)

### Purpose

Turn fixed scenarios into a curriculum — with one P12 correction: **scenarios are authored as behavioral histories and world states, never as psychological scalars.** A "fatigue" scenario is a dense dismissed-notification history; the estimator turns it into signal, exactly as in production.

### Scenario classes

```text
base_day_pressure           preference_drift (declared claim vs recent behavior)
dismissal_saturation        undo_regret
stale_observation           engagement_gaming
provider_sync_lag           social_friction
timezone_shift              dense_day_repair
authority_expiry            rollback_failure
label_churn (user disables a load-bearing label mid-curriculum)
```

### New artifacts

```text
experiments/curricula/p12_base.json
experiments/curricula/p12_provider_failures.json
experiments/curricula/p12_social_shadow.json
experiments/curricula/p12_signal_drift.json
scripts/run_self_play_curriculum.py
scripts/compare_curriculum_runs.py
tests/test_self_play_curriculum.py
tests/test_curriculum_failure_mapping.py
tests/test_curriculum_scenarios_are_behavioral.py
```

### Required `CurriculumRun` fields

```json
{
  "curriculum_schema_version": "curriculum_run.v1",
  "curriculum_id": "", "simulator_version": "sim_v2.1",
  "estimator_versions": ["interruption_tolerance_v1"],
  "policy_tuning_id": "",
  "scenario_count": 0, "episode_count": 0,
  "failure_modes": {}, "mapped_findings": {}, "unmapped_findings": {},
  "waived_findings": {}, "average_reward": 0,
  "reward_head_deltas": {}, "promotion_blockers": []
}
```

### Acceptance

```text
Every scenario maps findings to canonical failure keys; unmapped findings block
promotion unless waived; curriculum runs emit replay rows and artifact refs;
candidate-vs-CURRENT curriculum comparison exists; the behavioral-authoring lint
rejects scenarios that declare internal states instead of histories.
```

### Progress template

```md
## Step 12 — Self-play Curriculum
Curriculum: / Scenarios: / Episodes: / Mapped: / Unmapped: / Waived:
Reward impact: / Blockers: / Behavioral-authoring lint: / Decision: / Failures:
```

---

## Step 13 — Add provider-backed self-play for sandbox-safe families

### Purpose

Self-play should not remain purely stubbed. For safe families (`create_prep_block`, `add_buffer`, `protect_deep_work`, `batch_admin`), route through the provider boundary.

### Required behavior

```text
ActionLifecycle; ProviderBoundary.preview; commit only in sandbox;
verify; rollback; provider_transaction replay rows; rate caps; denial receipts.
```

### Commands

```bash
export CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1
export CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"

PYTHONPATH=src python scripts/run_lab_experiment.py \
  --seed <CalendarPilot SelfPlay seed> \
  --runtime fixture \
  --self-play-backend swift_ipc_eventkit_sandbox \
  --episodes 5 \
  --batch <BATCH_ID>
```

Setup note: create or return the sandbox calendar through the EventKit bridge
`ensure_calendar` command. It is local-only by default. If a dogfood Mac exposes
no local EventKit source, `source_policy: default_if_no_local` is an explicit
setup override and the run report must record the non-local sandbox source.

### Acceptance

```text
No outside-sandbox mutation; every provider-backed episode verifies rollback;
provider errors become replay rows; cap exceeded becomes denial receipt;
provider-backed and stub-backed results separately reported.
```

Current D2 evidence satisfies this for `create_prep_block`: five
`swift_ipc_eventkit_sandbox` episodes targeted only `CalendarPilot SelfPlay`,
first commit materialized, provider verify was `verified` with
`local_time_echo_ok: true`, later write was idempotent, replay invariants passed,
and rollback cleanup left zero unverified rollback records. Promotion remains
held on matched examples/explicit feedback volume.

### Progress template

```md
## Step 13 — Provider-backed Self-play
Provider: / Sandbox: / Families: / Episodes: / Verified commits: / Verified rollbacks:
Provider errors: / Outside-sandbox check: / Decision: / Failures:
```

---

## Step 14 — Harden live NIM schema drift into a permanent live gate

### Purpose

P11 resolved live NIM schema drift with visible normalization and a strict rerun. P12 makes this a standing gate.

### Observed drift classes to retain

```text
new_start/new_end; nested params; batch_tasks.target_time; invalid JSON;
missing calendar_id; duplicate candidate_id; non-canonical intent; empty frontier
```

### New artifacts

```text
tests/test_live_nim_schema_drift.py
tests/fixtures/nim_schema_drift/
scripts/run_live_nim_schema_gate.py
```

### Command

```bash
CALENDAR_PILOT_REQUIRE_LIVE_NIM=1 \
CALENDAR_PILOT_NIM_FRONTIER_LIMIT=1 \
CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS=8000 \
PYTHONPATH=src python scripts/run_live_nim_schema_gate.py \
  --out runs/p12_evidence/$RUN_ID/policy_learning/live_nim_schema_gate.json
```

### Acceptance

```text
Strict live mode fails closed without credentials; drift normalized only when safe;
unsafe drift becomes model_generation_rejection; every rejection replay-visible;
no heuristic fallback in strict live mode.
```

### Progress template

```md
## Step 14 — Live NIM Schema Gate
Credentials: / Strict mode: / Drift fixtures: / Live run: / Rejections:
Normalizations: / Fallback disabled: / Decision: / Failures:
```

---

## Step 15 — Make policy updates ablation-aware

### Purpose

P11 proved tuning can affect ranking and promote against CURRENT. P12 proves **why** — including whether the semantic-signal layer is actually load-bearing.

### Required ablations

```text
no_intent_reward_bias        no_right_moment_tuning
no_failure_penalties         no_taxonomy_normalization
no_denied_intents            no_provider_penalties
no_semantic_labels           (frontier/ranking with the label registry emptied)
no_derived_signals           (estimator outputs zeroed; legacy-free check)
```

### New artifacts

```text
scripts/run_policy_ablation.py
scripts/compare_policy_ablations.py
tests/test_policy_ablation_report.py
```

### Required `PolicyAblationReport` fields

```json
{
  "ablation_schema_version": "policy_ablation_report.v1",
  "candidate_policy_tuning_id": "", "current_policy_tuning_id": "",
  "ablations": {
    "no_failure_penalties": {
      "frontier_diff": {}, "scorecard": {},
      "reward_head_deltas": {}, "promotion_decision": "pass|hold"
    }
  },
  "critical_components": [], "non_effective_components": [],
  "decision": "pass|hold"
}
```

### Acceptance

```text
Every promoted policy has an ablation report; promotion identifies which components
matter; non-effective components are removed or justified; ablation regression can
hold promotion; the signal-layer ablations state whether labels/estimators earned
their complexity.
```

### Progress template

```md
## Step 15 — Policy Ablations
Candidate: / Current: / Ablations run: / Critical: / Non-effective:
Signal-layer verdict: / Promotion impact: / Decision: / Failures:
```

---

## Step 16 — Upgrade frontend surfaces for P12 (including the Signals surface)

### Purpose

The UI shows the same P12 evidence the lab uses. No separate truth. P12 adds the user-facing **Signals** controls (Step 7's registry surface).

### Required frontend additions

```text
Learn:     MeasurementReport; reward-head deltas; latency/cost; ablations;
           candidate-vs-CURRENT diff; live NIM schema gate status;
           estimator calibration gap.
Lab:       curriculum runs; calibration reports; dogfood shadow batches;
           provider-backed self-play; variance probes.
Authority: family-level autonomy matrix; tier; promotion history; rollback command;
           provider capability constraints.
Signals:   active/proposed/disabled semantic labels with plain-language statements,
           evidence counts, and per-label controls (disable / correct / "not me");
           biography drift findings awaiting reconciliation.
Observe:   dogfood shadow trace; provider preview/verify/rollback chain;
           calibration example links; label activation audit rows.
```

### Tests

```text
tests/test_frontend_p12_projector.py
scripts/run_browser_e2e.py updates (including a label-disable round trip:
  disable in UI → ActionStream row → next frontier diff reflects removal)
```

### Acceptance

```text
Frontend renders P12 metrics; replay export contains the same records shown;
UI links metric → trace; Authority matrix is family-level; the Signals surface
round-trips a disable as an audit row and a frontier change; no UI-only state.
```

### Progress template

```md
## Step 16 — P12 Frontend Surfaces
Learn: / Lab: / Authority: / Signals: / Observe: / Replay consistency:
Label-disable round trip: / Browser E2E: / Failures: / Decision:
```

---

## Step 17 — Add P12 release gate

### Purpose

P12 release includes P11 plus measurement, streams, estimators, calibration, labels, provider capability, curriculum, and autonomy-family evidence.

### New make target

```make
p12-release:
	...
```

### Required release checks

```text
P11 regression floor
Stream tagging + reward purity (B4) check
MeasurementReport
Signal estimator report + parity check
CalibrationReport or insufficient-data hold
Semantic label registry audit (B1–B3, evidence coverage, churn)
ProviderCapabilityReport
Self-play curriculum run
Policy ablation report for tuning candidates
Autonomy-family promotion report if matrix changed
Frontend P12 browser E2E (incl. Signals surface)
Secret scan
Evidence bundle validation
```

### Acceptance

```text
Release can pass with no autonomy promotion.
Release cannot pass with: missing measurement artifacts; untracked live NIM schema
drift; provider capability mismatch; autonomy matrix change without promotion
record; reward-purity violation; active derived label without evidence;
label activation without audit row.
```

### Progress template

```md
## Step 17 — P12 Release Gate
P11 regression: / Streams: / Measurement: / Estimators: / Calibration: / Labels:
Provider capabilities: / Curriculum: / Ablations: / Autonomy diff: / Frontend:
Secret scan: / Evidence validation: / Decision: / Failures:
```

---

# 5. P12 promotion gates

## 5.1 Policy tuning promotion

```text
valid_frontier_rate >= 0.95
model_generation_rejection_rate <= 0.15
OTHER_intent_rate <= 0.10
expected_intent_hit_rate >= 0.80
hard_invariant_violations = 0        (including B-series hard invariants)
candidate beats CURRENT on marginal diff
reward-head gates pass               (computed from ActionStream only — B4)
variance probe passes
ablation report exists               (including no_semantic_labels / no_derived_signals)
rollback plan exists
```

## 5.2 Autonomy-family promotion

```text
family-specific seed pass rate >= 0.95
self-play curriculum pass rate >= 0.95
provider sandbox pass rate = 1.0 for required provider capabilities
rollback pass rate = 1.0 for reversible writes
human feedback pass rate >= threshold or insufficient-data hold
sim-vs-real acceptance gap <= threshold or insufficient-data hold
no unwaived social-risk increase
no regret/interruption regression
autonomy matrix diff changes only the intended family
no label or signal appears in the authority justification (B2)
rollback plan exists
```

## 5.3 Provider promotion

```text
read_observation, preview, sandbox commit, verify, rollback, idempotency pass;
external IDs recorded; provider errors are replay rows; rate caps produce denial
receipts; no outside-sandbox mutation; timezone/local-time echo passes.
```

## 5.4 Signal and label governance (new)

```text
label_evidence_coverage = 1.0 for active derived labels        (B1)
zero label/signal reads in authority paths                     (B2, test-enforced)
100% of activation changes have user-attributed audit rows     (B3)
reward purity: zero non-ActionStream rows in reward reduction  (B4)
biography drift findings are surfaced, not silently resolved   (B5)
estimator parity: same version on synthetic and real streams   (B6)
label_churn_rate within declared bound (default <= 5 changes/user/week)
estimator_calibration_gap <= threshold or insufficient-data hold
no user-disabled label is auto-reactivated
```

---

# 6. P12 non-goals

```text
Do not jump to broad auto_apply_plan autonomy.
Do not promote social mutation beyond shadow without family-specific evidence.
Do not replace replay with separate analytics state.
Do not tune on live NIM output that fails schema gates.
Do not treat aggregate reward as sufficient for promotion.
Do not treat self-play as sufficient without dogfood calibration.
Do not hide provider failures outside replay.
Do not make frontend state diverge from replay/session state.
Do not poll users for internal state ("what's your energy level today?") —
  derive from behavior or do without. Evidence-cited reconciliation only.
Do not store derived signals as biography claims, or biography as reward.
Do not let any semantic label or signal gate authority, tiers, scopes, or grants.
Do not auto-reactivate labels a user disabled.
Do not author scenarios or seeds with psychological scalars — behavior only.
```

---

# 7. P12 working ledger

```md
# P12 Progress Ledger

RUN_ID: / Engineer: / Date: / Git SHA: / Branch: / Changed files:

## Hypothesis
What are we trying to prove?

## One-live-component-at-a-time check
Changed component: / Held fixed: / Runtime mode: / Provider: / Policy backend:
Simulator version: / Estimator versions: / Prompt/model version: / Tuning ID:

## Summary
Overall decision: [ ] pass [ ] hold [ ] fail [ ] needs rerun
Primary reason:

## Evidence artifacts
P11 regression: / Stream separation: / Measurement: / Dogfood shadow: / Estimators:
Calibration: / Semantic labels: / Reward-head report: / Provider capabilities:
Self-play curriculum: / Provider-backed self-play: / Live NIM schema gate:
Policy ablations: / Autonomy-family proposal: / Frontend: / Release:

## Metrics snapshot
valid_frontier_rate: / model_generation_rejection_rate: / OTHER_intent_rate:
expected_intent_hit_rate: / empty_frontier_rate:

frontier_latency_ms_p50/p95: / codex_latency_ms_p50/p95:
provider_verify_latency_ms_p50/p95: / nim_request_count: / nim_retry_count:
cost_per_valid_frontier:

utility_delta: / acceptance_delta: / engagement_delta: / long_horizon_delta:
regret_delta: / interruption_delta: / social_risk_delta: / undo_regret_delta:
ignored_delta: / explicit_wrong_delta:

sim_vs_real_acceptance_gap: / sim_vs_real_undo_gap: / matched_examples:
estimator_calibration_gap: / label_evidence_coverage: / label_churn_rate:
derived_vs_declared_conflicts: / label_disable_events:

rollback_pass_rate: / provider_idempotency_pass:
hard_invariant_violations: / soft_invariant_violations: / stream_purity_violations:

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

# 8. P12 final acceptance checklist

```md
## P12 Final Acceptance

### P11 floor
- [ ] P11 regression suite passes.
- [ ] P11 contracts remain versioned.
- [ ] P11 replay invariants remain strict.
- [ ] P11 provider rollback/idempotency gates remain intact.
- [ ] P11 frontend trace surfaces still render.

### Signal streams (new)
- [ ] Every replay row carries a signal_stream tag.
- [ ] Reward reduction consumes ActionStream rows only (B4 test).
- [ ] Biography entries carry kind (declared/conversational/derived_signal_ref).
- [ ] Legacy notification_fatigue has zero new writers/readers.
- [ ] docs/SIGNAL_STREAMS.md exists and names the B-invariants.

### Estimators (new)
- [ ] interruption_tolerance_v1 exists, versioned, deterministic.
- [ ] Estimator parity holds across synthetic and real streams (B6).
- [ ] sim_v2.1 conditions on estimator output, not declared scalars.
- [ ] estimator_calibration_gap measured or insufficient-data hold.

### Semantic labels (new)
- [ ] Codex annotator proposes evidence-cited labels (B1).
- [ ] Swift-patterned registry governs activation; user controls work.
- [ ] Activation changes are user-attributed audit rows (B3).
- [ ] Labels never gate authority (B2 test).
- [ ] Disabled labels stay disabled; disable events are ActionStream signals.
- [ ] Biography drift findings surface declared-vs-derived conflicts (B5).

### Measurement
- [ ] MeasurementReport exists and validates.
- [ ] Latency p50/p95 recorded for applicable paths.
- [ ] NIM request/retry counts recorded for live runs.
- [ ] Reward-head deltas are first-class scorecard fields.
- [ ] Missing required metrics produce hold, not silent pass.

### Dogfood shadow
- [ ] Real dogfood observation import exists, streams tagged.
- [ ] Redaction/local-only policy is explicit.
- [ ] Shadow frontier generation works.
- [ ] Shadow provider preview works.
- [ ] Shadow mode proves no commit occurred.
- [ ] Human feedback can be attached to shadow candidates.

### Calibration
- [ ] CalibrationReport exists.
- [ ] sim-vs-real acceptance gap measured or insufficient-data hold.
- [ ] sim-vs-real undo gap measured or insufficient-data hold.
- [ ] Calibration is per action family.
- [ ] Calibration examples link to replay.

### Machine learning
- [ ] Policy promotion uses candidate-vs-CURRENT.
- [ ] Reward-head gates enforced.
- [ ] Ablation report exists (including signal-layer ablations).
- [ ] Live NIM schema gate passes or controlled hold is explicit.
- [ ] No heuristic fallback in strict live mode.

### Machine acting
- [ ] Autonomy ladder exists.
- [ ] At least one action family has a promotion proposal.
- [ ] Any autonomy matrix change has a promotion record.
- [ ] Autonomy rollback tested.
- [ ] Provider capability reports constrain promotion.

### Self-play
- [ ] Curriculum engine exists; scenarios are behavior-authored.
- [ ] Scenario findings map to canonical failure keys.
- [ ] Unmapped findings block promotion unless waived.
- [ ] Provider-backed self-play works for ≥1 sandbox-safe family.
- [ ] Self-play results compared against dogfood calibration.

### Provider
- [ ] Deterministic provider capability report exists.
- [ ] EventKit sandbox capability report exists.
- [ ] Unsupported capabilities are explicit.
- [ ] Provider errors are replay-visible.
- [ ] No outside-sandbox mutation.

### Product surface
- [ ] Learn renders measurement, reward-head deltas, estimator calibration.
- [ ] Lab renders curriculum and calibration reports.
- [ ] Authority renders family-level autonomy.
- [ ] Signals renders labels, evidence, and controls; disable round-trips.
- [ ] Observe links metrics to traces.
- [ ] Replay export matches frontend state.

### Release
- [ ] make p12-release exists.
- [ ] Evidence bundle validates.
- [ ] Secret scan passes.
- [ ] Release report names all pass/hold/fail decisions.
```

---

# 9. The P12 judgment standard

A passing P12 implementation is not one where CalendarPilot merely runs more experiments. It is one where:

```text
the lab measures what P11 left unmeasured,
human signals are separated by what they actually are —
  verifiable actions, world facts, and self-description —
internal states are estimated from behavior, never polled or invented,
labels about the user are evidence-cited, user-visible, and user-controlled,
simulation is calibrated against dogfood reality,
policy improvements are marginal and ablation-aware,
reward-head regressions block promotion,
provider capabilities constrain acting,
self-play finds failures before users do,
and autonomy expands one reversible action family at a time.
```

P11 made the loop trustworthy.

P12 makes the loop learn — from signals the user could audit themselves.
