# P12–P17 Compression Roadmap

Status: planning document (rewritten)
Scope: CalendarPilot after the P12 stage-1 audit — distillation of the code to the humane learning loop it already proved
Provenance of this rewrite: three successive design passes — **structure** (objects/medium), **safety** (verified control envelopes), **evidence** (marginal, variance-aware improvement) — reconciled into one discipline, plus two findings verified in the working tree (§3).

Prior target under discussion: reduce `calendar-pilot-p12/src/calendar_pilot` from ~13,950 LOC toward a ~3,000 LOC core.
Reframed target: reduce the system's **conceptual mass** to its six load-bearing objects, without weakening a humane wall or making the promotion decision noisier. The line count is the *shadow* of that; it is reported, never decreed (§7, §8).

---

## 0. Why this document was rewritten

The previous roadmap opened with `~13,949 → ~3,000 LOC, ~78% reduction`. That is specifying a product by its price. A number is not a vision, and the previous document knew it — it disclaimed "not by quota pressure" on line one and then quoted the quota for twelve sections. That contradiction was the architecture of the thinking, not a wording slip: when success is measured as *subtraction of text*, every design move is scored by the wrong instrument, and the plan systematically prefers **deleting a feature** over **finding the primitive that made the feature free**.

The stage-1 audit already said this in its own words — the ≥50% cut is *"a refactor-and-sequence problem, not deletion"* — and the old roadmap heard it as "delete more carefully." It is the opposite. The audit's C₁ pass verdicted 41 flow-clusters: **KEEP-B 36 · CONSOLIDATE 12 · DEFER 4 · KEEP-I 2 · DELETE 1 · ARCHIVE 0**, with **18 humane clusters and zero humane deletions**. Only one clean piece of dead code existed. **Almost nothing is dead.** That is not bad news — it is the best possible news: the mass is not waste, it is **tax on a handful of missing objects**. You do not cut 10,000 lines. You reify the objects that make 10,000 lines impossible to have written.

This rewrite therefore does four things the old one did not:

1. Replaces the LOC goal with **conceptual mass under preserved safety and non-inflated decision variance** (§2).
2. States what CalendarPilot **is** — six objects — so that "does this line phone home to one of the six?" becomes the compression test (§1).
3. Corrects the current read with **two verified findings**: the safety gate is deterministic-fixture-only, and three of its legs are hardcoded constant emitters (§3).
4. Unifies compression and autonomy under **one evidence discipline**: every wave is a write, graded like a policy promotion (§4–§5).

---

## 1. What CalendarPilot is (the product, not the line count)

One sentence, because the product has to fit in one:

> CalendarPilot is a small, legible, human-governed learning loop that **believes only what it can cite**, **hands you control of every belief**, **acts only under revocable authority**, **always undoes**, and **earns autonomy only by beating its own incumbent on your real behavior.**

That sentence is six objects. Everything else in the tree is a *projection* of them, an *adapter* behind them, or a *method* that was exiled to a script and comes home. If a line of code cannot be phrased as a message to one of these six, it is not product — it is exception-management, and it dies **by homelessness** (not by quota).

| Object | Is | Load-bearing message | The humane wall it makes structural |
|---|---|---|---|
| **`Trajectory`** | the substrate: `TraceEvent + ActionEnvelope + ReplayRecord + Scorecard` as one append-only, self-describing composite | `observe · propose · stage · commit · verify · undo · reward · project · reduce` | undo is a method, not a feature; every truth is a replay row |
| **`Stream`** | `Action \| World \| Biography \| Derived`, each an object with behavior — **not** a string tag | `Action.reward_reduce()` exists; `Biography.reward_reduce()` **does not exist** | B4 (reward from ActionStream only) and B2 become *messages that don't exist on the wrong object* |
| **`Frontier`** | the protocol "give me typed candidate futures with provenance" | `generate(observation) -> [Candidate]`, each candidate stamped with provenance and rejection/quality telemetry | Codex, NIM, and the fixture are three respondents to **one** protocol — the two live "stacks" are a missing polymorphism, not two products |
| **`Authority`** | the Swift-issued, revocable **capability** | `grant · exercise · revoke · receipt` — accepts **no** `Signal` and **no** `Belief` as input, ever | B2 (no signal gates authority) is a *type signature*: a signal cannot reach authority because no message accepts one |
| **`Belief`** | *(the object that was missing)* a `DerivedSignal` that owns its own evidence, confidence, half-life, controls, and version | `value · evidence · confidence · half_life · activate/disable(by:user) · explain · version` | makes an un-citeable scalar **unconstructible** — this is *why* `notification_fatigue` died and `interruption_tolerance_v1` lived |
| **`Provider`** | the five-method transaction truth | `read_observation · preview · commit · verify · rollback` | write/verify/rollback truth; a provider you cannot honor is an **absent respondent**, never a stub |

**Legibility is a message, not a screen.** Every belief-bearing object answers one protocol:

```text
explain(question) -> Answer{ claim, evidence:[trajectory rows], confidence, controls:[activate/disable/correct] }
```

`Belief.explain` ("why do you think I tolerate interruptions at 0.3?"), `Authority.explain` ("why was this denied?" → the exact validation that failed), `Candidate.explain` ("why ranked here?" → the active signals and their versions). The answer is **honest by construction** because the trajectory is the only place it can get one. This is the deepest form of the product sentence: the frontend does not *hold* the honesty, it *renders* it — which is the only reason the frontend is safe to replace (§6, P13). **`explain` ships before any frontend is touched.**

Jobs' five demands are therefore not features to preserve across compression. They are five type signatures — `Belief.evidence`, `Belief.explain`+`controls`, `Authority` (no-signal-input), `Trajectory.undo`, and promotion-gated-on-`reduce`-vs-incumbent — plus four runtime monitors for the properties types cannot reach (§5, §9). You cannot compress them away, because there would be nothing left.

---

## 2. What we actually optimize

LOC is an **output** `y = h(x)`, not the controlled variable. The controlled variable is the tuple of behaviors the system can still exhibit and the discipline that keeps them honest. Four metrics replace the quota:

```text
M1  load-bearing objects            target: 6           (Kay: conceptual mass, not text mass)
M2  exceptions to "everything is a  target: 0           the real cost is special cases —
    trajectory"                                         r0/r1/v1/v2 strata, 7 runtime modes,
                                                        2 live stacks, legacy_state
M3  honesty-diameter                target: 1 hop       gesture -> cited answer, via explain()
M4  promotion-decision variance     non-inflating       a wave may not make the promote/hold
                                                        decision noisier (§5, C-VAR)
```

LOC is reported as a **consequence** of moving M1–M4, with its binding constraint named (§7, §8). The floor is discovered, not chosen. If you ever find yourself optimizing `y` directly — deleting a monitor to make the number fall — you are reward-hacking the ruler; see §5's failure modes.

---

## 3. Corrected current read (two findings verified in the tree)

The old §3 "current read" was directionally right about the strangler and the frontend. It was wrong about the one thing that matters most: **the safety spine.** Both findings below were confirmed by reading the code, not the docs.

### Finding 1 — the release gate is a certificate over the *deterministic* set only

`make p12-release` runs `scripts/run_p12_release.py`, which is **nine fixture checks**: `check_invariants` (on `tests/fixtures/replay_golden.jsonl`), `signal_estimators`, `measurement`, `calibration`, `provider_capability`, `reward_heads`, `curriculum` (on `experiments/curricula/p12_base.json`), `policy_ablation`, `secret_scan`. **None** invoke a live leg — `live-codex-e2e`, `live-diffusiongemma-e2e`, `live-eventkit-e2e`, `swift-ipc-test`, `browser-e2e` are *separate Make targets the gate never calls*.

The audit's own rule L4 warns that a deterministic-only coverage run will mark env-gated live paths as dead. The roadmap then named "p12-release green after every wave" as its safety spine. **The spine is the L4 trap in costume:** a green gate cannot observe the live behaviors whose deletion it is meant to prevent. This is a reachability hole, not a convention gap.

### Finding 2 — three of the nine legs are hardcoded constant emitters

Worse than thin — **green by construction, independent of system state:**

- `make_reward_head_report.py:11,19` — every gate literal `True`; **`reward_purity_violations: 0`** as a constant; `decision: 'pass'`. Nothing is loaded. *The B4 reward-purity check the roadmap calls non-negotiable is a hardcoded zero.*
- `run_policy_ablation.py:10` — every ablation returns `{'promotion_decision':'pass'}` from a comprehension; candidate/current are bare strings; no replay read. *The `no_semantic_labels` ablation the promotion rule requires a candidate to survive is a string key mapping to `{}`.*
- `make_calibration_report.py` — honestly returns `decision:'hold'`, `matched_examples:0`, gaps `None`; but the harness computes `ok = (returncode==0)`, the script exits 0, so **a permanent `hold` is counted as a passing leg.**

`run_p12_release.py` reports `ok = all(c['ok'])`. None of these three can fail on the fixture. **The instrument that is supposed to detect reward leakage, failed ablation, and miscalibration reads a constant.** You cannot trust a single "no regression" claim in P13–P17 until this is fixed. This is why P12.5 exists and blocks everything (§6).

### What is otherwise true (carried from the audit)

- `legacy_state` was woven back out of the served JS; `app.js` + `frontend_state.sample.json` deleted; envelopes are v2/r1-only; `sim_v2.1` is default; fatigue residue is gone; `session.py` decomposed 2,222 → 1,316 (decomposition, not deletion — total LOC ~flat).
- Current src mass by organ: **frontend 3,923 · diffusiongemma 2,727 · codex 2,161 · environment 1,689 · top-level 1,656** (`types.py` 733 + `replay.py` 514) **· providers 962 · swift_bridge 832.**
- The largest masses are **real product commitment**, not waste: the live Codex path (`codex/live.py` 1,111), the live NIM path (`diffusiongemma/live.py` 942), the frontend session organism (3,923), and 40 scripts (~5,299). Each sits directly on a missing object (§4).

---

## 4. The unifying law: a compression wave is a promotion

The single most important correction. The old roadmap treated **autonomy** as dangerous (cold-start holds, ≥20 matched examples, conservative promotion) and **compression** as housekeeping ("mostly mechanical if P16 was explicit"). This is backwards. Both are the **same act: an envelope expansion that grants the system a new capability** — in one case the capability to *act*, in the other the capability to *no longer exhibit a behavior*. Both are irreversible writes to what the system can do. Both must beat the incumbent on real evidence.

```text
                     autonomy promotion            compression wave
incumbent            CURRENT policy                CURRENT behavior set
the write            grant a new action family     delete / merge / migrate a behavior
must beat/tie        CURRENT on frontier diffs     CURRENT on the certificates of §5
evidence             replay-backed, calibrated     dual-run equivalence + variance + rows
reversibility        revocable grant               tombstone + archive (Do-not-reference)
forbidden shortcut   engagement gaming, social     placebo gate, deterministic-coverage
                     creep                          illusion, LOC reward-hacking
exogenous gate       calendar-time cold-start      calendar-time equivalence window
```

**Consequence:** every wave carries the same eight-field **experiment record**, and does not merge without all eight populated with numbers, not prose:

```text
Δ            exact LOC spans + cluster ids removed/merged
fixed        git SHA of the frozen instrument (INSTRUMENT@sha, §5) — proves ruler ≠ object
rows         the specific replay_golden line-ids the reducer trained/graded on, before & after
baseline     the pre-wave metric vector, committed (no "improved" without a referent)
effect       Δmetric / seed-resample stddev — the ratio, not the sign
regressed    the metric that got worse (there is always one; naming it is anti-reward-hacking)
ablation     re-run with the removed code stubbed; the decision must be stable
rollback     revert SHA + proof it restores the baseline vector
```

There is **no mechanical write to what the system can do.** The phrase "mostly mechanical P17" is deleted. A wave that touches behavior is a promotion of a smaller system, or it does not ship (§5, D-J7).

---

## 5. The certificate catalog

Three disciplines, three kinds of guarantee. **Structure** makes violations unconstructible (free, zero runtime lines). **Safety** proves the new agrees with the old at every intermediate state. **Evidence** proves the change didn't get noisier or start believing things it can't calibrate. All three are required; none implies the others.

### 5.1 Structure — the walls that become type signatures (free)

Move B1–B4 and redaction out of the invariant-checker's arms and into the *shapes* of the objects (§1). This is the one place the "never remove a wall for LOC" rule and the LOC goal stop fighting: the wall moves into the constructor, and the checker *shrinks* without weakening anything.

```text
B1  every Belief requires >=1 evidence row to construct        -> unconstructible if uncited
B2  Authority accepts no Signal/Belief input                   -> a signal cannot reach authority
B4  reward_reduce exists only on Action; not on Biography       -> reward from ActionStream only
B3  label activation API only reachable with user-attribution   -> activation is always an audit row
redaction  egress accepts only redacted types at one chokepoint -> no unredacted egress path exists
```

### 5.2 Safety — the barrier certificates for migration and contraction

**`B_migrate` (per organ, at every coexistence state).** Build the kernel behind the freeze as a *shadow*, dual-run each organ through both old (`O`) and new (`K`), and require on **every** trajectory:

```text
π_auth(K(o)) = π_auth(O(o))          same tier, scope, grant-id, reversibility, rollback-handle
π_reward(K(o)) = π_reward(O(o))      same stream, same rows, same reduction result
provenance(K(o)) ⊇ provenance(O(o))  the kernel may cite MORE evidence, never less
```

Organs may differ on presentation, latency, phrasing, ranking cosmetics — outside the barrier. They may **not** differ on *who can write, what counts as reward, what evidence is cited*. Divergence in those projections is an immediate unsafe transition and halts the wave. **Intermediate-state invariant:** at every coexistence state, exactly one of `{K, O}` holds authority, and their auth/reward/provenance projections are identical.

**Contraction certificates — collapse only what you can prove is a bisimulation on the safety sublattice** (the merged object reaches every safety-relevant state of its sources, and no new one):

- **`B_frontier`** — `Frontier` must carry `(provenance, failure_mode:enum, variance, cost, latency)`, not provenance alone. Test: replay a corpus through both live stacks, record the observable set; replay through `Frontier`; assert set-equality on the safety sublattice. If the merged object can no longer exhibit "NIM-schema-reject" as a distinct observable, you performed a lossy abstraction and the lab is measuring a fiction. **Keep both models; delete the duplication.**
- **`B_schema`** — r0/r1/v1/v2 → one schema is a **verified total migration** on safety fields (authority, reward-source, provenance, rollback state), loss-annotated on the rest; every dropped field named in a tombstone; a row that cannot migrate becomes an explicit **denial receipt**, never a silent skip. D-09 is a *proof obligation*, not a toggle. (The "skip unsupported version" behavior is a safety feature — it prevents silent evidence thinning — and may only be removed once the migration is discharged.)
- **`B_runtime`** — 7 modes → 1 runtime + injected backends requires the live backends **injectable and exercised**, not compiled into an unobserved "production" mode. Injection is necessary but not sufficient; the injected live backends must also be run-or-root-listed (Finding 1).

### 5.3 Evidence — variance, instrument, calibration

**`INSTRUMENT@<sha>` — freeze the ruler before you trust it.** Pin, version-locked, before any destructive wave: `replay_golden.jsonl`, `p12_base.json`, `promotion_thresholds.json`, `CURRENT.json`, `sim_v2.1`. Every experiment record cites this SHA in `fixed`. **A change that edits both the instrument and the product is rejected mechanically.** Kay's "40 scripts → methods" refactor is allowed *only after* the instrument is fixed and pinned, and it runs as its own graded wave proving bit-identical reports on the pinned fixtures.

**`C-VAR` — compression must not increase the variance of the promotion decision.** Freeze a candidate set spanning promote/reject/borderline against pinned `CURRENT.json` on a pinned seed matrix. Per candidate, the statistic is the marginal frontier delta and the binary promote/hold. Bootstrap over seeds → `Var[Δ]` and **flip rate**. Run before the wave (`Var_0, flip_0`) and after (`Var_1, flip_1`). The wave passes only if `Var_1 ≤ Var_0·(1+ε)` **and** `flip_1 ≤ flip_0` on every borderline candidate, at a pre-registered ε. This is the certificate `B_migrate` cannot give: a "safe" consolidation that thins the reducer's training data can preserve every safety field (equivalence holds) and still widen the decision distribution (borderline candidates start flipping) — **that is the signal, and it fails the wave before the degradation reaches production.**

**Calibration gates — cited is not calibrated.** Any `Belief` the compressed system ships must clear, at the same estimator version on synthetic and real (B6 operationalized):

- **estimator-calibration-gap** = |predicted head − realized outcome| on matched replay rows; blocks release above a pre-registered band. Below the matched-example floor, the Belief ships **`explain`-visible but non-autonomous** — shown to the user with its confidence, but it cannot gate an authority grant. *An un-calibrated Belief is a cold-start Belief, resolved by calendar time (Program A), not by shipping it anyway.*
- **sim-vs-real-acceptance-gap** = accept/undo under `sim_v2.1` minus the same under dogfood-shadow, per family; blocks promotion if the simulator is systematically optimistic.
- **`C-B6`** — a wave may not change an estimator version silently; if it touches estimator code it re-emits both calibration reports at the new version and shows the gaps did not widen. "Same version on synthetic and real" becomes a diff-able invariant, not a doc promise.

### 5.4 The four runtime monitors (the eyes — root-listed, exempt from harvest)

Some walls are **liveness or statistical** properties types cannot reach. They cost runtime lines, look like overhead, and are the most tempting deletions in a LOC harvest — so they are enumerated at repo root and exempt. Deleting one is a promotion that must beat CURRENT on *detectability*, which it cannot.

```text
reward-leakage monitor    scans consumed rows for non-ActionStream provenance    (B4 over time)
biography-drift monitor    emits BiographyDriftFinding on declared-vs-derived     (B5 liveness)
                           conflict — never silent overwrite
undo/revoke-effectiveness  a revoke must eventually take effect; rollback is       (provider verify)
                           itself verified
calibration monitor        estimator-calibration + sim-vs-real gaps               (§5.3)
```

### Where the roadmap must be MORE conservative than before

1. **"Frontend is disposable" is the most dangerous line in the old document.** The frontend is a *parallel state engine* holding hidden truth (`DogfoodSessionState`, `legacy_state`) — deleting it before its truth is projectable is unsafe. Rewrite: **"frontend hidden-truth is made unrepresentable via `view_state = project(trajectory)`, dual-run to `B_migrate`, then the shell is replaced."** "Disposable" is a product judgment; "unrepresentable" is a reachability judgment; only the second is safe.
2. **Behavior removal from the live set is the least-safe write in the whole program** and must be *earlier and slower*, each with its own equivalence window — never batched into a "mechanical" P17.
3. **Program A protection is a checked invariant, not a courtesy** (§11).

---

## 6. Phase model

The old P13/P16/P17 sequence survives, but P12-next gains a blocking predecessor and P13 is re-founded on the kernel. **You build the small kernel that runs and strangle *toward* it; you do not diet away from 13,950 hoping to arrive somewhere good.**

```text
P12.5   Fix the ruler, install the eyes, ship the missing object   (blocking; adds lines)
P13     Kernel-behind-freeze + organ migration + frontend reset     (shadow -> equivalence -> retire)
P16     Verified contractions (Frontier, one runtime, one schema)   (missing-polymorphism, not amputation)
P17     Emergent floor harvest                                      (NOT mechanical; monitors exempt)
```

### P12.5 — De-placebo, pin, and reify (NEW, blocking)

Nothing destructive lands until the instrument computes something and the missing object exists. This phase **adds** LOC; that is correct — you cannot pay for the eyes out of the harvest.

- **De-placebo the three legs (Finding 2)** so a green gate asserts something: `reward_heads` actually loads candidate-vs-CURRENT heads and makes `reward_purity_violations` a real scan over consumed rows; `policy_ablation` actually stubs each component, re-grades, adds `--family` scoping, and returns `hold` when any ablation is unstable — the `no_semantic_labels` ablation must run a real re-grade; `calibration`'s `hold` must fail the gate (or be an explicit, tracked `allow_hold` exception, never silently swallowed by `returncode==0`).
- **Close L4 (Finding 1):** the release gate must **run-or-explicitly-root-list** every live leg. A root-listed leg is a signed exception with an owner, not a silent skip.
- **Pin `INSTRUMENT@<sha>`** (§5.3) and record the two known-failing data-quality flags (`OTHER_intent_rate 0.1429 > 0.10`, `expected_intent_hit_rate 0.0`) as **known-red at pin time**, so a wave that improves them counts and a wave that worsens them can't hide behind an already-red metric. Pin the red; don't launder it.
- **Ship `Belief` and the `explain` protocol** (§1) *before* P13 touches the frontend — the honesty must live in the objects before its renderer can be replaced.

Exit gate: the gate can fail; the instrument is pinned; `explain` answers with cited rows; no destructive verdict has landed. **LOC goes up. Report it honestly.**

### P13 — Kernel behind the freeze; organ migration; frontend reset

Build the six-object kernel as a shadow spine, then migrate each organ via **shadow → dual-run under `B_migrate` → equivalence over N dogfood windows → authority handoff (the one irreversible step, narrow, with verified rollback) → retire by homelessness with a tombstone.** Retire order by observability: `frontend` and `codex` (mostly deterministic-reachable) before `diffusiongemma`, `providers`, `swift_bridge` (heavy live-reachable).

The frontend reset is the session organism dying of homelessness: `view_state = project(trajectory)` is a pure reduction sharing the lab's reducers, so `DogfoodSessionState` / `legacy_state` / static-snapshot become **unrepresentable, not "weaned."** The replacement shell renders `explain` answers; the honesty was already moved to the objects in P12.5, which is the only thing that makes the shell safe to throw away.

Preserved by the migration (now as object messages, not UI panels): feedback capture as ActionStream rows, label activate/disable/correct, biography-drift visibility, authority tier/scope + grant/denial explanations, replay export, trace visibility, runtime-blocker visibility, dogfood/cold-start evidence capture.

Exit gate: kernel holds authority for migrated organs; `B_migrate` held across every overlap; old organism removed with tombstones or explicitly retained; B-invariants intact; `explain` renders the same cited truth in every surface.

### P16 — Verified contractions (missing polymorphism, not amputation)

The old P16 framed the big levers as product amputations. They are not — they are missing objects, and they cost **no features** once the object exists:

- **Two live stacks → one `Frontier`, keep both models** — gated by `B_frontier`. (~2,053 LOC of duplication → one protocol + three thin adapters.)
- **7 runtime modes → one runtime + injected backends** — gated by `B_runtime`; live backends injectable *and exercised*.
- **r0/r1/v1/v2 → one schema** — gated by `B_schema`; verified total migration with denial receipts.
- **`providers/stubs` (Google/Microsoft) → absent respondents** — a `Provider` you cannot honor is a falsehood the type system will let you believe; remove until the transaction contract can be executed.
- **40 scripts → methods on the kernel + a ~100-line CLI** — the scripts are `trajectory.train()`, `frontier.diff()`, `policy.promote()`, `evidence.measure()` exiled to the filesystem; each is graded against `INSTRUMENT@<sha>` and must produce bit-identical reports.

Exit gate: each contraction carries its certificate; the frozen metric vector is beaten-or-tied; `no_semantic_labels` survived; C-VAR passed; no dropped feature is silently relied on by Program A or a humane surface.

### P17 — The emergent floor

Not a mechanical harvest — the tail of the same discipline. Remove structure that only existed to support discarded variation, each removal a graded wave. **The floor is wherever the next removal fails a certificate**, reported with its binding constraint (§8). The four runtime monitors are root-listed and exempt; P16/P17 "move lab outside core" / "remove until needed" is re-scoped to *cosmetic/presentation* lab code only — the statistical monitors stay, and the floor rises to include them, deliberately.

---

## 7. The LOC trajectory is a sawtooth, not a slide

A *safe* migration temporarily **increases** LOC, because kernel and organ must coexist and be dual-run to equivalence before the old organ retires. The old monotone-decreasing table budgeted for a shape that forces the unsafe cut-over. The honest curve peaks **above** 13,950 before it falls, and every floor names the constraint that binds it.

| point | expected `/src` LOC | binding constraint at this floor |
|---|---:|---|
| now | ~13,950 | — |
| after P12.5 | ~14,300–14,700 | +gate/instrument/`Belief`/`explain` lines — paid deliberately |
| P13 peak (kernel+organ overlap) | ~15,500–16,500 | shadow spine coexisting with organs under `B_migrate` |
| after P13 retire | ~8,500–11,000 | session organism unrepresentable; organs behind kernel |
| after P16 contractions | ~5,000–7,500 | `Frontier`/schema/runtime bisimulations discharged |
| after P17 | **> 3,000, reported** | root-listed monitors + calibration harness + `Belief` lines — the last lines you may cut |

The `~3,000` architecture is achievable **only if** you delete the monitors — i.e., blind the instrument. So the realistic floor is stated as **above 3,000, bound by monitor lines**, which is exactly consistent with the audit's "zero humane deletions." A single number is a placebo; the interval-with-binding-constraint is the honest deliverable.

---

## 8. The 3,000-line question, answered honestly

You do not decree 3,000. You **discover** where the certificates stop discharging and report that number with what binds it. Example of the only acceptable form of the claim:

> "We reached 4,600 LOC. The next ~400 would delete the reward-leakage monitor (§5.4), a root-listed liveness check, so the floor is 4,600, bound by reward-purity monitoring."

That sentence is worth more than "3,000," because it is true, falsifiable, and names the price of going lower. Report per-phase intervals with a binding-constraint column; relabel the old "3,000 LOC architecture" as **"the architecture *if* these monitors are deleted — here is the detectability each deletion costs."** The number is the shadow of the product (§1); optimize the product and read the shadow.

---

## 9. Non-negotiables, re-sorted

The old §13 listed eleven walls flat, as if all were the same kind of thing. They are not — and the flat list is what invites a LOC harvest to treat a running monitor as overhead. Sorted by what actually enforces each:

**Type-enforced (free; zero runtime lines; unconstructible to violate):**
```text
B1  Belief requires evidence to construct
B2  Authority accepts no signal/belief input
B4  reward_reduce exists only on Action
B3  label activation requires user-attribution
redaction at a single typed egress chokepoint
```

**Runtime-monitored (costs lines; the eyes; root-listed; exempt from harvest):**
```text
reward-leakage over trajectories        biography-drift finding (B5)
undo/revoke effectiveness + verified     estimator calibration + sim-vs-real (B6, §5.3)
  rollback
```

**Discipline (process, enforced by the gate):**
```text
ActionStream/WorldStream/BiographyStream separation
replay rows + causal chains remain legible
promotion beats CURRENT beyond noise, survives no_semantic_labels
cold-start holds that honestly require real data (Program A, §11)
```

These can be **redesigned or consolidated**. They cannot **disappear**, and the runtime monitors specifically cannot be "harvested."

---

## 10. Decision register (updated)

The register survives; several decisions are re-typed from "product amputation" to "missing-polymorphism / proof-obligation," which changes their answer.

| id | decision | reframed answer |
|---|---|---|
| D-00 | Is the target LOC or conceptual mass? | **Conceptual mass (§2).** LOC is reported output with a binding constraint. |
| D-01 | Is the gate a spine? | **Not as written** (§3). Fix in P12.5 before it can be trusted. |
| D-02 | Is the frontend disposable? | Its **hidden truth** is made unrepresentable, then the shell is replaced (§6). Not "disposable." |
| D-03 | Humane controls mandatory in replacement? | Yes — as `explain` + object messages, shipped in P12.5 before P13. |
| D-04 | Keep live Codex? | **Keep — as a `Frontier` respondent.** Delete the duplication, not the model (`B_frontier`). |
| D-05 | Keep live NIM? | **Keep — as a `Frontier` respondent.** Same. |
| D-06 | Keep seven runtime modes? | Collapse to one runtime + injected+**exercised** backends (`B_runtime`). |
| D-07 | Keep dogfood-release as gate? | Fold live legs into the release gate's run-or-root-list set (P12.5, closes L4). |
| D-08 | Keep EventKit in core? | Keep as the one real `Provider` respondent; sandbox curriculum intact. |
| D-09 | Keep old replay schemas? | **Proof obligation, not a toggle** — verified total migration + denial receipts (`B_schema`). |
| D-10 | Keep provider-backed self-play in core? | Keep the statistical core; only cosmetic lab code may leave core. |
| D-11 | Keep Google/Microsoft stubs? | **Remove — absent respondents.** A stub that can't execute the transaction contract is a lie. |
| D-12 | Keep Mac app packaging in core? | Packaging may leave core; the EventKit `Provider` path stays. |
| D-13 | Keep rich explanatory fields in contracts? | Keep whatever `explain` and `Belief.evidence` require; cut the rest. |
| D-14 | Open tests/packages for cleanup? | Tests die only with their feature; never counted toward a number (anti-gaming). |
| D-15 | Accept a product break from P12? | No unproven break. A wave is a promotion; it beats-or-ties CURRENT or does not ship (§4). |

---

## 11. Program A is a checked invariant

The cold-start runway (`create_prep_block` autonomy: ≥20 matched examples, ≥10 explicit feedback) is resolved by **calendar time**, not engineering hours — engineers waiting on data are free to run Program B (compression) in the same window. But a compression wave that deletes a signal-capture path, a feedback row type, or a matched-example counter **resets Program A's clock to zero, and the LOC accounting will never show it.**

Therefore: the release gate counts matched-examples and explicit-feedback rows **before and after every wave; any decrease is an unsafe transition that halts the wave.** The old "protect; report thinness only" becomes "block on regression." Program A's runway is monotone non-decreasing, by gate, not by good intention.

---

## 12. Recommended path

```text
1. P12.5 first, and it is blocking.
   Fix the three placebo legs; close L4; pin INSTRUMENT@sha; ship Belief + explain.
   LOC goes UP. This buys the eyes. Do not skip it to protect a number.

2. Route every wave through the promotion harness (§4).
   Eight-field record; beat-or-tie the frozen vector; survive no_semantic_labels;
   pass C-VAR; roll back like a de-promotion.

3. P13 builds the kernel behind the freeze and migrates organs by
   shadow -> B_migrate -> equivalence -> handoff -> retire. Frontend truth becomes
   unrepresentable before the shell is replaced.

4. P16 collapses the missing-polymorphisms (Frontier, one runtime, one schema),
   each under its contraction certificate. Keep both models; delete duplication.

5. P17 harvests to the emergent floor and stops where a certificate stops
   discharging. Report the floor and its binding constraint. Monitors are exempt.
```

## 13. Bottom line

The stage-1 audit was right and the old roadmap half-heard it. Almost nothing is dead — which is the best news, because the mass is not waste, it is **tax on a handful of missing objects.** Reify the six, move the invariant walls into their types, keep the four monitors as the system's eyes, and 10,000 lines do not get *cut* — they become **impossible to have written.**

But before any of that: **the instrument is already lying.** The safety spine is a fixture-only gate, and three of its legs — including the B4 reward-purity check the roadmap calls non-negotiable — read hardcoded constants. Fix the ruler first. Then "3,000" stops being a wish and becomes whatever the certificates permit, reported with its binding constraint.

The strategic choice is unchanged in words and inverted in method: CalendarPilot becomes a **small governed calendar-autonomy core with a legible human-controlled learning loop** — not by dieting toward a number, but by building the six-object kernel that *is* the product and letting everything that cannot phone home to it fail to make the trip. Compression is not demolition. It is distillation, held to exactly the bar we hold autonomy: **beat the incumbent on real evidence, or it does not land.**
