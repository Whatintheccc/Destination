# P12–P17 Compression Roadmap

An architectural design document for distilling CalendarPilot to its humane core.

Status: design specification
Scope: CalendarPilot after the P12 stage-1 audit — the target architecture and the sequence that reaches it
Design disciplines: **structure** (the objects a person thinks in), **safety** (verified control envelopes for every change), **evidence** (variance-aware proof that a change improved rather than merely differed)

---

## 1. Purpose

This document specifies the architecture CalendarPilot compresses *toward*, and the discipline by which each step is taken. The objective is distillation: remove everything that is not the humane learning loop until what remains is only that loop — trustworthy, legible, governed, reversible, and still learning.

The controlled variable is **conceptual mass** — the number of things a person must hold in their head to predict what the system does next. Line count is an *output* of that, reported and bounded (§7, §8), never the target. The audit that precedes this work verdicted 41 flow-clusters and found **KEEP-B 36 · CONSOLIDATE 12 · DEFER 4 · KEEP-I 2 · DELETE 1 · ARCHIVE 0**, with 18 humane clusters and zero humane deletions. Almost nothing is dead. The mass is not waste; it is the tax paid for a small number of objects the system has not yet named. The work is to name them — then most of the mass becomes impossible to have written.

---

## 2. What CalendarPilot is

The product fits in one sentence:

> CalendarPilot is a small, legible, human-governed learning loop that **believes only what it can cite**, **hands the user control of every belief**, **acts only under revocable authority**, **always undoes**, and **earns autonomy only by beating its own incumbent on real behavior.**

That sentence is six objects. Everything else in the tree is a *projection* of them, an *adapter* behind them, or a *method* that belongs on one of them. A line of code that cannot be phrased as a message to one of the six is not product; it is exception-management, and it does not survive compression.

| Object | Is | Load-bearing messages | The humane wall it makes structural |
|---|---|---|---|
| **`Trajectory`** | the substrate: `TraceEvent + ActionEnvelope + ReplayRecord + Scorecard` as one append-only, self-describing composite | `observe · propose · stage · commit · verify · undo · reward · project · reduce` | undo is a method, not a feature; every truth is a replay row |
| **`Stream`** | `Action \| World \| Biography \| Derived`, each an object with behavior — not a string tag | `Action.reward_reduce()` exists; `Biography.reward_reduce()` does not exist | B4 (reward from ActionStream only) and B2 are *messages that do not exist on the wrong object* |
| **`Frontier`** | the protocol "give me typed candidate futures with provenance" | `generate(observation) -> [Candidate]`, each candidate stamped with provenance and rejection/quality telemetry | Codex, NIM, and the fixture are three respondents to one protocol — one polymorphism, not two products |
| **`Authority`** | the Swift-issued, revocable capability | `grant · exercise · revoke · receipt` — accepts no `Signal` and no `Belief` as input | B2 (no signal gates authority) is a type signature: a signal cannot reach authority because no message accepts one |
| **`Belief`** | a `DerivedSignal` that owns its own evidence, confidence, half-life, controls, and version | `value · evidence · confidence · half_life · activate/disable(by:user) · explain · version` | an un-citeable scalar is unconstructible — this is why `notification_fatigue` cannot exist and `interruption_tolerance_v1` can |
| **`Provider`** | the five-method transaction truth | `read_observation · preview · commit · verify · rollback` | write/verify/rollback truth; a provider that cannot honor the contract is an absent respondent, never a stub |

**Legibility is a message, not a screen.** Every belief-bearing object answers one protocol:

```text
explain(question) -> Answer{ claim, evidence:[trajectory rows], confidence, controls:[activate/disable/correct] }
```

`Belief.explain` ("why do you think I tolerate interruptions at 0.3?"), `Authority.explain` ("why was this denied?" → the exact validation that failed), `Candidate.explain` ("why ranked here?" → the active signals and their versions). The answer is **honest by construction**: the trajectory is the only place it can be sourced. A surface — CLI, Mac app, web shell, or test harness — *renders* `explain` answers; it does not hold the honesty. That is the property that makes any single surface replaceable without eroding trust.

The product sentence therefore reduces to five type signatures — `Belief.evidence`, `Belief.explain`+`controls`, `Authority` (no-signal-input), `Trajectory.undo`, and promotion-gated-on-`reduce`-vs-incumbent — plus four runtime monitors for the properties types cannot reach (§6.4, §9).

---

## 3. Design objective and metrics

Four metrics govern the work. LOC is reported as a consequence of moving them, with its binding constraint named (§7, §8).

```text
M1  load-bearing objects                    target: 6        conceptual mass, not text mass
M2  exceptions to "everything is a           target: 0        the real cost is special cases —
    trajectory"                                              r0/r1/v1/v2 strata, 7 runtime modes,
                                                             2 live model paths, legacy_state
M3  honesty-diameter                         target: 1 hop   gesture -> cited answer, via explain()
M4  promotion-decision variance              non-inflating   a change may not make the promote/hold
                                                             decision noisier (§6.3, C-VAR)
```

---

## 4. System state at the start of this work

The architecture builds from the post-P12 tree. Three properties of the current build are load-bearing for the sequence and are stated as fact.

### The release gate certifies the deterministic set only

`make p12-release` runs `scripts/run_p12_release.py`: nine fixture checks — `check_invariants` (on `tests/fixtures/replay_golden.jsonl`), `signal_estimators`, `measurement`, `calibration`, `provider_capability`, `reward_heads`, `curriculum` (on `experiments/curricula/p12_base.json`), `policy_ablation`, `secret_scan`. It does not invoke any live leg; `live-codex-e2e`, `live-diffusiongemma-e2e`, `live-eventkit-e2e`, `swift-ipc-test`, and `browser-e2e` are separate Make targets. A green gate therefore certifies the deterministic reachable set and is blind to the live behaviors it must protect. Extending it to run-or-explicitly-root-list every live leg is the first task of P12.5.

### Three gate legs emit constants

- `make_reward_head_report.py:11,19` — every gate is literal `True`; `reward_purity_violations: 0` is a constant; `decision: 'pass'`. Nothing is loaded. The B4 reward-purity check is a hardcoded zero.
- `run_policy_ablation.py:10` — every ablation returns `{'promotion_decision':'pass'}`; candidate/current are bare strings; no replay is read. The `no_semantic_labels` ablation that promotion requires a candidate to survive asserts nothing.
- `make_calibration_report.py` — returns `decision:'hold'`, `matched_examples:0`, gaps `None`; the harness keys `ok` on `returncode==0`, so a permanent `hold` counts as a passing leg.

As they stand, these three legs cannot fail. The instrument meant to detect reward leakage, failed ablation, and miscalibration reads a constant. No "no regression" claim is trustworthy until P12.5 makes them compute.

### What has landed, and where the mass is

`legacy_state` is out of the served JS; `app.js` and `frontend_state.sample.json` are deleted; envelopes are v2/r1-only; `sim_v2.1` is the default; the fatigue residue is gone; `session.py` is decomposed 2,222 → 1,316 (decomposition, not deletion). Current src mass by organ:

```text
frontend 3,923   diffusiongemma 2,727   codex 2,161   environment 1,689
top-level 1,656 (types 733 + replay 514)   providers 962   swift_bridge 832
```

The largest masses are product commitment, not dead code: the live Codex path (`codex/live.py` 1,111), the live NIM path (`diffusiongemma/live.py` 942), the frontend session organism (3,923), and 40 scripts (~5,299). Each sits directly on a missing object (§6.2).

---

## 5. Compression and autonomy are one act

Granting the system authority to act and removing the system's ability to behave are the same operation: an envelope expansion that changes what the system can do. Both are irreversible writes. Both must beat the incumbent on real evidence and be reversible by construction.

```text
                     autonomy promotion            compression wave
incumbent            CURRENT policy                CURRENT behavior set
the write            grant a new action family     delete / merge / migrate a behavior
must beat or tie     CURRENT on frontier diffs     CURRENT on the certificates of §6
evidence             replay-backed, calibrated     dual-run equivalence + variance + rows
reversibility        revocable grant               tombstone + archive (Do-not-reference)
forbidden shortcut   engagement gaming, social     placebo gate, deterministic-coverage
                     creep                          illusion, LOC reward-hacking
exogenous gate       calendar-time cold-start      calendar-time equivalence window
```

Every wave carries the same eight-field **experiment record** and does not merge without all eight populated with numbers:

```text
Δ            exact LOC spans + cluster ids removed/merged
fixed        git SHA of the frozen instrument (INSTRUMENT@sha, §6.3) — proves the ruler did not move
rows         the replay_golden line-ids the reducer trained/graded on, before and after
baseline     the pre-wave metric vector, committed
effect       Δmetric / seed-resample stddev — the ratio, not the sign
regressed    the metric that got worse (there is always one; naming it is the anti-gaming check)
ablation     re-run with the removed code stubbed; the decision must be stable
rollback     revert SHA + proof it restores the baseline vector
```

A wave that touches behavior is a promotion of a smaller system, routed through the promotion harness, or it does not ship.

---

## 6. The certificate catalog

Three disciplines, three kinds of guarantee. Structure makes a violation unconstructible (zero runtime lines). Safety proves the new agrees with the old at every intermediate state. Evidence proves the change did not get noisier or start believing what it cannot calibrate. All three are required; none implies the others.

### 6.1 Structure — walls that are type signatures

B1–B4 and redaction live in the *shapes* of the objects, not in an external checker. The wall is the constructor; the checker's corresponding arms are then unnecessary rather than removed.

```text
B1  Belief requires >=1 evidence row to construct        -> unconstructible if uncited
B2  Authority accepts no Signal/Belief input             -> a signal cannot reach authority
B4  reward_reduce exists only on Action                  -> reward from ActionStream only
B3  label activation API requires user-attribution       -> activation is always an audit row
redaction  a single typed egress chokepoint accepts      -> no unredacted egress path exists
           only redacted types
```

### 6.2 Safety — barrier certificates for migration and contraction

The kernel is built behind the freeze as a *shadow*. Each organ migrates by **shadow → dual-run under `B_migrate` → equivalence over N dogfood windows → authority handoff (the single irreversible step, with verified rollback) → retire with a tombstone.** Retire order follows observability: `frontend` and `codex` (mostly deterministic-reachable) before `diffusiongemma`, `providers`, `swift_bridge` (heavy live-reachable).

**`B_migrate`** — on every trajectory while old (`O`) and new (`K`) coexist:

```text
π_auth(K(o)) = π_auth(O(o))          same tier, scope, grant-id, reversibility, rollback-handle
π_reward(K(o)) = π_reward(O(o))      same stream, same rows, same reduction result
provenance(K(o)) ⊇ provenance(O(o))  the kernel may cite more evidence, never less
```

Organs may differ on presentation, latency, phrasing, and ranking cosmetics — outside the barrier. They may not differ on *who can write, what counts as reward, or what evidence is cited*. Intermediate-state invariant: at every coexistence state, exactly one of `{K, O}` holds authority, and their auth/reward/provenance projections are identical. Divergence in those projections halts the wave.

**Contraction certificates** — a collapse is admissible only when it is a bisimulation on the safety sublattice: the merged object reaches every safety-relevant state of its sources and no new one.

- **`B_frontier`** — `Frontier` carries `(provenance, failure_mode:enum, variance, cost, latency)`. Test: replay a corpus through both live paths, record the observable set; replay through `Frontier`; assert set-equality on the safety sublattice. Both models are kept; the duplication is removed. If the merged object can no longer exhibit "NIM-schema-reject" as a distinct observable, the abstraction is lossy and the lab is measuring a fiction.
- **`B_schema`** — r0/r1/v1/v2 → one schema is a verified total migration on safety fields (authority, reward-source, provenance, rollback state), loss-annotated on the rest; every dropped field named in a tombstone; a row that cannot migrate becomes an explicit denial receipt, never a silent skip. Old-schema runtime support is removed only after this is discharged.
- **`B_runtime`** — 7 modes → one runtime + injected backends requires the live backends injectable and *exercised*, not compiled into an unobserved "production" mode.

### 6.3 Evidence — instrument, variance, calibration

**`INSTRUMENT@<sha>`** — the ruler is frozen before it grades anything. Pinned, version-locked, before any destructive wave: `replay_golden.jsonl`, `p12_base.json`, `promotion_thresholds.json`, `CURRENT.json`, `sim_v2.1`. Every experiment record cites this SHA in `fixed`. A change that edits both the instrument and the product is rejected mechanically. Refactoring the lab (scripts → methods) runs as its own graded wave that must produce bit-identical reports on the pinned fixtures. The two known-red data-quality flags (`OTHER_intent_rate 0.1429 > 0.10`, `expected_intent_hit_rate 0.0`) are recorded as known-failing at pin time, so a wave that improves them counts and a wave that worsens them cannot hide behind an already-red metric.

**`C-VAR`** — a wave may not increase the variance of the promotion decision. A fixed candidate set spanning promote/reject/borderline is graded against pinned `CURRENT.json` on a pinned seed matrix; the statistic per candidate is the marginal frontier delta and the binary promote/hold. Bootstrap over seeds yields `Var[Δ]` and the **flip rate**. The wave passes only if `Var_1 ≤ Var_0·(1+ε)` and `flip_1 ≤ flip_0` on every borderline candidate, at a pre-registered ε. A consolidation that thins the reducer's training data preserves every safety field yet widens the decision distribution — borderline candidates begin to flip, and the wave fails before the degradation reaches production. `B_migrate` proves agreement; `C-VAR` proves the decision did not get noisier; both are required.

**Calibration gates** — a cited belief is not yet a calibrated belief. Any `Belief` the system ships clears, at the same estimator version on synthetic and real (B6):

- **estimator-calibration-gap** = |predicted head − realized outcome| on matched replay rows; blocks release above a pre-registered band. Below the matched-example floor, the Belief ships `explain`-visible but non-autonomous — shown to the user with its confidence, unable to gate an authority grant. An un-calibrated belief is a cold-start belief, resolved by calendar time.
- **sim-vs-real-acceptance-gap** = accept/undo under `sim_v2.1` minus the same under dogfood-shadow, per family; blocks promotion when the simulator is systematically optimistic.
- **`C-B6`** — a wave that touches estimator code re-emits both calibration reports at the new version and shows the gaps did not widen. "Same version on synthetic and real" is a diff-able invariant.

### 6.4 The four runtime monitors

Some walls are liveness or statistical properties that types cannot reach. They cost runtime lines and are enumerated at repo root, exempt from harvest; removing one is a promotion that must beat CURRENT on detectability, which it cannot.

```text
reward-leakage monitor      scans consumed rows for non-ActionStream provenance   (B4 over time)
biography-drift monitor     emits BiographyDriftFinding on declared-vs-derived     (B5 liveness)
                            conflict — never a silent overwrite
undo/revoke-effectiveness   a revoke must eventually take effect; rollback is      (provider verify)
                            itself verified
calibration monitor         estimator-calibration + sim-vs-real gaps              (§6.3)
```

### 6.5 Design principles for change

- **Unrepresentable, not disposable.** A surface holding hidden truth (`DogfoodSessionState`, `legacy_state`) is retired by making its truth projectable — `view_state = project(trajectory)` — so the hidden state has nowhere to live, then replacing the shell. "Disposable" is a product judgment; "unrepresentable" is a reachability judgment; only the second is safe.
- **Live-set removal is the slowest write.** Removing a behavior from the live-reachable set is the least-observed and least-safe change; it happens earlier and slower than deterministic-set change, each with its own equivalence window, never batched.
- **The monitors are the eyes.** The four runtime monitors and the calibration harness are the last lines eligible for removal, because deleting them removes the system's ability to detect the regressions the rest of the discipline forbids.

---

## 7. Phase model

The kernel is built and made to run first; the tree is strangled *toward* it. A line that cannot phone home to one of the six objects is left behind and tombstoned rather than migrated.

```text
P12.5   Fix the instrument, install the eyes, ship the missing object   (blocking; adds lines)
P13     Kernel behind the freeze + organ migration + frontend reset      (shadow -> equivalence -> retire)
P16     Verified contractions (Frontier, one runtime, one schema)        (one polymorphism, not amputation)
P17     Emergent-floor harvest                                           (graded waves; monitors exempt)
```

### P12.5 — De-placebo, pin, and reify (blocking)

Nothing destructive lands until the instrument computes and the missing object exists. This phase adds LOC; the eyes cannot be paid for out of the harvest.

- **De-placebo the three legs (§4):** `reward_heads` loads candidate-vs-CURRENT heads and makes `reward_purity_violations` a real scan over consumed rows; `policy_ablation` stubs each component, re-grades, adds `--family` scoping, and returns `hold` on any unstable ablation — `no_semantic_labels` runs a real re-grade; `calibration`'s `hold` fails the gate unless it is an explicit, tracked exception.
- **Close the live-leg gap:** the release gate runs-or-explicitly-root-lists every live leg; a root-listed leg is a signed exception with an owner.
- **Pin `INSTRUMENT@<sha>`** and record the known-red flags at pin time.
- **Ship `Belief` and the `explain` protocol** before P13 touches the frontend; the honesty lives in the objects before its renderer is replaced.

Exit: the gate can fail; the instrument is pinned; `explain` answers with cited rows; no destructive verdict has landed.

### P13 — Kernel behind the freeze; organ migration; frontend reset

The six-object kernel is a shadow spine. Each organ migrates via `B_migrate` (§6.2). The frontend reset is the session organism becoming unrepresentable: `view_state = project(trajectory)` is a pure reduction sharing the lab's reducers, so `DogfoodSessionState` / `legacy_state` / static-snapshot have nowhere to live, and the replacement shell renders `explain` answers. Preserved as object messages: feedback capture as ActionStream rows, label activate/disable/correct, biography-drift visibility, authority tier/scope and grant/denial explanations, replay export, trace visibility, runtime-blocker visibility, dogfood/cold-start evidence capture.

Exit: the kernel holds authority for migrated organs; `B_migrate` held across every overlap; old organism removed with tombstones or explicitly retained; B-invariants intact; `explain` renders the same cited truth on every surface.

### P16 — Verified contractions

Each contraction is one polymorphism replacing a duplicated implementation, and costs no features:

- **Two live paths → one `Frontier`, both models kept** — gated by `B_frontier`.
- **7 runtime modes → one runtime + injected backends** — gated by `B_runtime`; live backends injectable and exercised.
- **r0/r1/v1/v2 → one schema** — gated by `B_schema`; verified total migration with denial receipts.
- **`providers/stubs` (Google/Microsoft) → absent respondents** — a provider that cannot execute the transaction contract is removed until it can.
- **40 scripts → methods on the kernel + a ~100-line CLI** — each graded against `INSTRUMENT@<sha>` to bit-identical reports.

Exit: each contraction carries its certificate; the frozen metric vector is beaten or tied; `no_semantic_labels` survived; `C-VAR` passed; no dropped feature is silently relied on by Program A or a humane surface.

### P17 — The emergent floor

The tail of the same discipline: structure that existed only to support discarded variation is removed as graded waves. The floor is wherever the next removal fails a certificate, reported with its binding constraint (§8). The four runtime monitors are exempt; lab code eligible for relocation is cosmetic/presentation only.

---

## 8. LOC trajectory

A safe migration transiently *increases* LOC, because kernel and organ coexist and are dual-run to equivalence before the old organ retires. The curve is a sawtooth that peaks above the starting mass before it falls, and every floor names its binding constraint.

| point | expected `/src` LOC | binding constraint at this floor |
|---|---:|---|
| start | ~13,950 | — |
| after P12.5 | ~14,300–14,700 | gate/instrument/`Belief`/`explain` lines, paid deliberately |
| P13 peak (kernel + organ overlap) | ~15,500–16,500 | shadow spine coexisting with organs under `B_migrate` |
| after P13 retire | ~8,500–11,000 | session organism unrepresentable; organs behind the kernel |
| after P16 contractions | ~5,000–7,500 | `Frontier` / schema / runtime bisimulations discharged |
| after P17 | **> 3,000, reported** | root-listed monitors + calibration harness + `Belief` lines |

The number is the shadow of the architecture (§2). It is optimized by moving M1–M4 (§3) and read off, not chosen.

---

## 9. Invariant enforcement

The humane walls are enforced three ways. They can be redesigned or consolidated; they cannot disappear, and the runtime monitors cannot be harvested.

**Type-enforced (zero runtime lines; unconstructible to violate):**
```text
B1  Belief requires evidence to construct        B2  Authority accepts no signal/belief input
B4  reward_reduce exists only on Action          B3  label activation requires user-attribution
redaction at a single typed egress chokepoint
```

**Runtime-monitored (the eyes; root-listed; exempt from harvest):**
```text
reward-leakage over trajectories        biography-drift finding (B5)
undo/revoke effectiveness + verified     estimator calibration + sim-vs-real (B6)
  rollback
```

**Discipline (enforced by the gate and the eight-field record):**
```text
ActionStream / WorldStream / BiographyStream separation
replay rows + causal chains remain legible
promotion beats CURRENT beyond noise and survives no_semantic_labels
cold-start holds that honestly require real data (Program A, §11)
```

---

## 10. Decision register

| id | decision | resolution |
|---|---|---|
| D-00 | Target of the program | Conceptual mass (§3); LOC is reported output with a binding constraint |
| D-01 | Release gate reach | Certifies the deterministic set; P12.5 extends it to run-or-root-list live legs |
| D-02 | Frontend replacement | Hidden truth made unrepresentable via projection, then the shell is replaced |
| D-03 | Humane controls in the replacement | Mandatory, as `explain` + object messages, shipped in P12.5 before P13 |
| D-04 | Live Codex path | Kept as a `Frontier` respondent; the duplication is removed, not the model |
| D-05 | Live NIM path | Kept as a `Frontier` respondent |
| D-06 | Seven runtime modes | Collapsed to one runtime + injected and exercised backends (`B_runtime`) |
| D-07 | Dogfood-release / live legs | Folded into the release gate's run-or-root-list set (P12.5) |
| D-08 | EventKit in core | Kept as the one real `Provider` respondent; sandbox curriculum intact |
| D-09 | Old replay schemas | Verified total migration + denial receipts (`B_schema`) |
| D-10 | Provider-backed self-play | Statistical core kept in-repo; only cosmetic lab code may relocate |
| D-11 | Google/Microsoft stubs | Removed as absent respondents until the transaction contract is honored |
| D-12 | Mac app packaging | May relocate; the EventKit `Provider` path stays |
| D-13 | Explanatory contract fields | Kept where `explain` / `Belief.evidence` require; trimmed otherwise |
| D-14 | Tests / packages | Tests die only with their feature; never counted toward a number |
| D-15 | Product change from P12 | Only proven change ships; a wave beats or ties CURRENT (§5) |

---

## 11. Program A — the protected runway

The cold-start runway (`create_prep_block` autonomy: ≥20 matched examples, ≥10 explicit feedback) is resolved by calendar time, not engineering hours; compression runs in the same window. A wave that deletes a signal-capture path, a feedback row type, or a matched-example counter resets that runway's clock, and the LOC accounting will not show it. Therefore the release gate counts matched-example and explicit-feedback rows before and after every wave; any decrease halts the wave. Program A's runway is monotone non-decreasing by gate.

---

## 12. Build sequence

```text
1. P12.5 first, and blocking. De-placebo the three legs; close the live-leg gap;
   pin INSTRUMENT@sha; ship Belief + explain. LOC rises. This buys the eyes.

2. Route every wave through the promotion harness (§5): eight-field record;
   beat or tie the frozen vector; survive no_semantic_labels; pass C-VAR;
   roll back like a de-promotion.

3. P13 builds the kernel behind the freeze and migrates organs by
   shadow -> B_migrate -> equivalence -> handoff -> retire. Frontend truth
   becomes unrepresentable before the shell is replaced.

4. P16 collapses each polymorphism (Frontier, one runtime, one schema) under
   its contraction certificate. Both models kept; duplication removed.

5. P17 harvests to the emergent floor and stops where a certificate stops
   discharging. Report the floor and its binding constraint. Monitors exempt.
```

---

## 13. Summary

CalendarPilot is six objects: `Trajectory`, `Stream`, `Frontier`, `Authority`, `Belief`, `Provider`. The invariant walls live in their types; the four runtime monitors are the system's eyes; legibility is a message every belief answers. Compression is the act of making everything that is not those six unrepresentable — held to the same bar as granting autonomy: beat the incumbent on real evidence, prove equivalence across every intermediate state, keep the decision no noisier, and remain reversible by construction.

The instrument is fixed before it is trusted, the kernel is built before the tree is strangled toward it, and the line count is read off the result rather than chosen for it. The floor is reported with the constraint that binds it. Compression is not demolition; it is distillation to the humane core the system has already proved it can run.
