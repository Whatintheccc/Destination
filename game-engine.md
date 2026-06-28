# CalAgent as a Game Engine

> Engineering reference for the lens, the pivot, and the 0-to-1 build. Grounded in
> `readme.md`, `readme-revised.md`, and `plan-4-revised(10).md`; all contract and
> test names are used verbatim. The intended reader is an engineer building the
> back half described here.

CalAgent is the **front half of a game-agent loop with the validator made sovereign.**
The canonical loop — observation → state encoder → policy → value → planner → world
model → action decoder, closed by reward — exists in CalAgent only up to the policy and
the action validator; the back half (value function, reward loop, online trainer) was
**deliberately amputated**, and the one power relation that defines a game agent is
**inverted**: the policy is not sovereign, the validator (Swift / D2 /
`support(staged) ⊆ F(x_live)`) is. This document is where the amputated back half is
grown — carefully — so the system can **learn what the user likes**. The pivot is
**two scoped deltas**, not one: (1) a measured, bounded reward MAY now steer composition
— relaxing the visibility posture of plan §10.5 ("the loop improves in the dark"), §10.2,
and §11.5; and (2) the composer MAY be trained on earned-accepted history — relaxing the
plan's stated *no-learner / frozen-model* posture (plan §6, readme §6 P2: "there is no
learner today"; the prep station is "feature engineering over a frozen model… nothing
learns"). Both trade a maximally-dark, never-learning posture for personalization while
holding the trust wall bit-for-bit. We grow value; we do not grant authority. The reward
steers composition; D2 still rules admission.

A standing honesty note carried through every section: CalAgent is a game engine *for a
game with no verifiable reward.* That is not a quibble — it is the governing constraint
on how the loop may be closed.

---

## 1. The agent loop

A canonical game agent is a closed loop:

```text
            ┌──────────────────────────────────────────────────────────────┐
            │                                                              ↓
  observation ─→ state encoder ─→ policy π(a|s) ─→ action decoder ─→ env.step()
                      │               ↑                                  │
                      └─→ value V(s) ─┘   (planner / search over a       │
                              ↑           world model M: ŝ', r̂)         │
                              │                                          │
                              └──────────────── reward r ←──────────────┘
                                      (online trainer updates π, V)
```

In a game agent the **policy/value network is sovereign**: it chooses the action, the
value function steers it toward future return, a planner rolls the world model forward,
and `env.step()` commits the action autonomously while reward flows straight back into a
trainer that updates the weights online.

CalAgent instantiates the **front half** of exactly this loop, then does two structural
things to it. First, it **amputates** the back half: there is no prospective value, no
planner, no world model, no auto-closing reward loop, no online RL trainer. Second, it
**inverts** the power structure: the most capable component (DiffusionGemma, the policy)
is the least sovereign, and the action **validator** (Swift's D2 wall) is sovereign and
hypertrophied. This is the literal enactment of the governing doctrine — *capability is
separated from authority; the most capable component is never the most sovereign*
(readme §2; plan §3).

CalAgent's instantiation, component by component:

```text
observation     Swift reads ALL raw user + calendar state every run        (readme §8, plan §9.1)
   ↓
state encoder   decision-sufficient statistics / F(x)  — OWNED BY INFRA     (DecisionSufficientStatisticV0;
   ↓            (model never sees the raw frame, only the encoded packet)    slateOfferedV0; readme §4.5)
   ↓
policy π(a|s)   DiffusionGemma                                              (RecommendationSelectionInfillV0 → index;
   ↓            SELECT: selectedSlotIndex over a Swift-enumerated slate      RecommendationShapeProposalV0 → shape;
   ↓            PROPOSE: a shape Swift must independently materialize        readme §5; capability ≠ authority §4.3)
   ↓
[value V(s)]    historically a PUN (retrospective, forbidden to steer);     ← THIS DOC GROWS IT
   ↓            being grown as the EARNED-ACCEPTANCE reward                  (plan §10.5; readme §9)
   ↓
[planner]       ABSENT — one card, no rollout, no tree                      (readme §1, §3; NOT built)
   ↓
[world model]   ABSENT — the why-line justifies, it does not predict        (readme §4.4; NOT built)
   ↓
action          Swift hydrates AllowedActionV0 → live recheck → HUMAN       (readme §8.4; AllowedActionV0;
  validator     CONFIRM TAP → post-picker fingerprint → write               plan §9.3)
   ↓                                            ↑
  D2 wall ──────────────────────────────────────┘
  SOVEREIGN, HYPERTROPHIED: support(staged) ⊆ F(x_live), in-process,        (readme §8.3 step 13, §8.4;
  lookup-never-reconstruction, confirm-time live recheck = TOCTOU hardening  testSupportStagedSubsetOfLiveF)
```

Two divergences from the canonical loop are load-bearing and recur below:

- The **decoder's decisive step is a human confirm tap, not `env.step()`.** Nothing
  auto-writes; the calendar is sacred space (readme §8.4, §10.5). The human tap is the
  consent gate that substitutes for an auto-closing reward loop.
- The **validator is the sovereign**, not a guardrail. A *hard legality-loop* replaces
  the absent *learned value-loop*; that hypertrophy is the deliberate substitute for the
  organ this document is about to grow back.

---

## 2. Component map

Each row maps a game-loop component to its CalAgent instantiation, marks whether it is
present / absent / inverted, marks whether the correspondence is **real** (structural
match) or a **pun** (right name, opposite role), and states whether this document grows
it.

| Game-loop component | CalAgent instantiation | Present / absent / inverted | Real / pun | Now being built? |
|---|---|---|---|---|
| **Observation** | Swift reads all raw user + calendar state at the start of every run (readme §8; plan §9.1) | Present | Real | No — unchanged |
| **State encoder** | Decision-sufficient statistics + feasible support; `DecisionSufficientStatisticV0` (banded, non-identifying axes), `F(x)` enumerated in SELECT as `slateOfferedV0`; **owned by infra (Swift), not the model** (readme §4.5; plan §5.1–§5.2) | Present (inversion-precursor: encoder is walled off from the policy) | Real | No — the per-user embedding `u` conditions *on top of* this encoder, not a replacement |
| **Policy π(a\|s)** | DiffusionGemma. SELECT: `RecommendationSelectionInfillV0.selectedSlotIndex` = genuine argmax-over-slate policy. PROPOSE: `RecommendationShapeProposalV0` = a proposal distribution over a too-large-to-enumerate space (readme §5; plan §7.3–§7.4) | Present but **non-authoritative** (the inversion lives here: capability ≠ authority, §4.3) | Real (a real policy; the inversion is real, not punned) | Yes — conditioning enriched by a learned preference embedding `u`; **authority unchanged** |
| **Value V(s)** | `RecommendationValueSignalV0` layer (`RecommendationEditDistanceV0`, `SurvivalAtTSignalV0`, `CounterfactualSlateLogV0`); retrospective, "the loop improves in the dark," **forbidden to steer** (readme §9; plan §10.5) | Present-but-**inverted** (prospective in a game; retrospective here) | **Pun** (right name, opposite role) | **Yes — the core of this doc.** Promoted to the earned-acceptance reward |
| **Planner / search** | None. One card, no rollout. `F(x)` is a **constraint set** admission checks against, not a searched tree (readme §1, §3) | Absent | Real (genuine absence) | **No** — reward-guided diffusion steers single-shot composition, it does not search a horizon |
| **World model** | None. The why-line **justifies** (true-today, supported by admitted evidence); it does not **predict** next-state + reward (readme §4.4, §10.4; plan §12.2) | Absent | Real (genuine absence) | **No** — and per the constraint it *should* not be (the human week is not simulable) |
| **Action decoder** | Swift hydrates `AllowedActionV0` (minted only after staging, short-lived, scoped) → human confirm tap → live recheck → post-picker fingerprint → write → undo/edit/delete (readme §8.4; plan §9.3) | Present, but **decisive step is a human tap, not `env.step()`** | Real (the human-tap divergence is structural) | No — stays the human confirm tap |
| **Action validator** | **D2** + `support(staged) ⊆ F(x_live)`: single in-process admission seam, lookup-never-reconstruction, confirm-time live recheck (= TOCTOU hardening), non-`Codable` `RecommendationVerdictV0` (readme §8.3–§8.4; plan §8; `testSupportStagedSubsetOfLiveF`, `testD2InProcessOnly`) | Present and **hypertrophied** — and **sovereign** (the inversion: validator rules, policy obeys) | **Real — the strongest correspondence** | No — **explicitly the load-bearing thing that does not move** |
| **Reward loop** | Historically **severed**: value signals never auto-close, improvement is owner-gated and offline (plan §10.5; readme §9) | Absent (severed) | Real | **Yes — closed *carefully* (§4–§5). The pivot's core delta** |
| **Trainer** | Historically offline, owner-gated, imitation-style; `PickDiscriminatorV0` ranks admitted candidates behind an anti-laundering firewall (plan §11.3; readme §7) | Present but offline / firewalled | Real | **Yes — gains reward-guided diffusion + per-user preference embedding; still authority-firewalled** |

Reading the table top to bottom: the front half (observation → encoder → policy →
validator → decoder) is **real as architecture and grounded in concretely specified
contracts** (the source docs define these contracts and treat SELECT as the public
migration default; they do not assert an implementation status — that is out of their
scope, so "specified," not "shipped"); the back half is one genuine pun (value), one
severed loop, one offline trainer — all three grown here — plus two genuine absences
(planner, world model) that are deliberately **not** grown.

---

## 3. The honest caveat — sound as architecture, hazardous as learning

The game-engine lens is a faithful *static-architecture decomposition*. It is a
dangerous *learning paradigm*. The reason is that **CalAgent is formally not a game.**

Of the six constituents of a game, CalAgent lacks five:

| Game constituent | Present in CalAgent? | Why |
|---|---|---|
| **Verifiable reward / identifiable utility** | **No** | Strong *correctness* verifier (D2, live `F(x_live)`, copy-honesty, fingerprints) but **no true value verifier** (readme §4.6; plan §10). The target is unidentifiable: *kept is not loved; deleting is friction*; "survives to write" Goodharts. |
| **Cheap simulator** | **No** | A human week is not roll-out-able; n=1 per user. You cannot synthesize experience. |
| **Win / terminal condition** | **No** | There is no terminal state and no score to maximize. |
| **Adversary** | **No** | The user is the **principal**, not an opponent. Self-play is meaningless. |
| **Free / reversible actions** | **No** | A write to sacred calendar space behind a human tap is neither free nor freely reversible (readme §8.4, §10.5). |
| **Repeated play** | Partially | Present only as **un-learnable n=1 repetition** — one user's week, once. |

The true category is a **fiduciary single-step recommender under unidentifiable
utility**, made safe by replacing the missing value-loop with a hard legality-loop
(D2) and a human consent gate (the tap). The recommender is a fiduciary: it acts in the
user's interest, and it cannot read out whether it succeeded.

The consequence governs the entire pivot:

> **Borrow the stack. Do not blindly close the loop.**

Borrowing the *architecture* (encoder / policy / value / reward as a vocabulary and a
component map) is sound — it is what §1–§2 do. Closing the *reward loop* the way a game
agent does — online RL on a true reward through an autonomous `env.step()` — is hazardous,
because there is no true reward to optimize and no cheap way to discover one. Therefore
the loop in this document is closed not on **acceptance** but on **earned acceptance**,
and even that is closed *carefully* (frozen base, bounded guidance, regret penalty,
explicit-value anchor, drift monitor, why-line gate, and the unchanged wall — §4, §7),
never turned into an online-RL game agent.

---

## 4. The reward: earned acceptance

The central architectural repair this document makes is to promote CalAgent's
retrospective value-signal layer into a **prospective reward that steers composition** —
the value-function organ the front-half loop was missing. (It is the central repair, not
the only one: growing the back half also introduces a *learner* — §6.2 Delta 2 — where the
plan has none.) The danger in promoting the reward is optimizing for the wrong thing: a
card accepted because it flatters, not because it helps. The reward is defined to make that
loss expensive.

### 4.1 Definition

**Earned acceptance** is a Swift-owned reduction over the existing
`RecommendationValueSignalV0` signals into a single bounded scalar/band:

```text
earned_acceptance =
      accepted
  AND survived-to-T            (SurvivalAtTSignalV0.survived)
  AND low edit-distance        (RecommendationEditDistanceV0.aggregateEditDistanceBand low)
  AND explicit-useful          (when the rarely-shown "was this useful?" channel is elicited)
```

This **promotes `SurvivalAtTSignalV0` from a backstage gauge to the reward target**, and
fuses it with edit-distance, the counterfactual/rejection gradient, and an explicit
channel. The reduction makes **value the constraint and acceptance the objective inside
it**: the thing being maximized is acceptance, but only acceptance that *also* survives
and *also* required little finishing work.

The reward is trusted only when **measurement-before-mutation** holds: lineage must tie
`request → context → proposal → confirm → write → edit/undo/delete → survival`, and
**both** the pre-picker and post-picker fingerprints must exist (plan §11.5;
`testEditDistanceRequiresBothFingerprints`). Until then the reward term is
`.notMeasured`, and **`.notMeasured` is never zero** (`MeasurementStatusV0`;
`testNotMeasuredNeverZero`) — an unmeasured sample neither promotes nor penalizes a
shape. This is the single most important correctness property carried into the learning
loop: **missing value data cannot launder into a training gradient.**

### 4.2 The flattery guard

A naive "optimize for acceptance" reward would reward flattery — a pleasant card the
user taps because it feels good. Earned acceptance **structurally zeroes** that case:

```text
flattering card → accepted → then deleted or heavily edited before T
   → SurvivalAtTSignalV0.survived = false        (zeroes the survival term)
   → RecommendationEditDistanceV0 aggregate high  (zeroes the edit-distance term)
   ⇒ earned_acceptance ≈ 0   →  flattery earns nothing
```

Because the reward is conjunctive over *survival* and *low edit-distance*, an accepted
card that the user later walks back contributes no positive gradient. Flattery that
produces any downstream regret is not rewarded. This is the regret penalty the bound and
the frozen base (§5, §6) then sit on top of.

### 4.3 The residual: the comfortable false positive

The guard in §4.2 catches flattery **that produces regret.** The irreducible residual is
flattery **that produces none**:

> **The comfortable false positive** — a pleasant permission the user accepts, never
> regrets, and never actually needed.

It survives to T (so `SurvivalAtTSignalV0` is satisfied), it is not edited (so
edit-distance is low), it is not rejected (so the counterfactual log is silent). Every
**behavioral** regret signal — edit-distance, survival, rejection — is structurally
**blind** to it, because *no regret is produced.* This is the systemic form of readme
§4.6's warning: promoting survival-at-T to the reward is exactly what gets Goodharted
here — *kept is not loved.* We do not have, and cannot cheaply buy, a true value verifier
(readme §4.6: "no true value verifier"). We must be honest that this risk is **bounded,
not eliminated.**

### 4.4 The mitigations

None is a cure; each is a bound. They are the only levers that exist:

| Mitigation | What it bounds | Mechanism |
|---|---|---|
| **Regret penalty** | Flattery that *does* produce regret | The conjunctive earned-acceptance definition (§4.2) zeroes accepted-then-walked-back cards |
| **The bound (γ / KL)** | Runaway reward optimization | Guidance scale γ (reward-guided sampling) or KL leash (Diffusion-DPO) held to an explicit owner-set bound (§5) |
| **Frozen base** | Drift of the composition prior | The Phase-1 imitation base is frozen under reward-guided sampling — no catastrophic forgetting, reversible (§5) |
| **Explicit elicitation** | The comfortable false positive (partially) | The rarely-shown, owner-gated "was this useful?" channel — the least-corruptible value sample, because it does not depend on behavioral regret. **Caveat: this mitigation is itself a partial relaxation of the sacred "measurement has no visibility" invariant (plan §10.5/§13.3) — asking is visible measurement.** Justified only as rare, owner-gated, non-grading; the felt-safety/frequency tradeoff is open (§7 row 5) |
| **Population-drift monitoring** | Systemic flattery | A **uniform, global** shift toward "everyone accepts more of X" is the flattery tell — detectable precisely because it is population-wide; a per-user reward can be Goodharted invisibly, a population cannot hide a global drift |
| **Why-line-true-today gate** | Dishonest persuasion | `CopyHonestyGate` still blocks unsupported preference claims, implied source strength, and copy built from backstage measurement (plan §12.2; readme §10.4) — guidance cannot buy a false permission slip |
| **The unchanged wall** | Anything past admission | D2 + `support(staged) ⊆ F(x_live)` + the confirm tap — a guided card is still only a *staged* card behind a human tap |

The honest summary: you cannot buy a true value verifier for free; you can buy a noisy
sample by asking (explicit elicitation) and a systemic alarm by watching the population
(drift monitoring). The comfortable false positive is the price of the pivot, marked and
bounded, not waved away.

---

## 5. The 0-to-1 on DiffusionGemma

> **Status.** This is a **proposed** 0-to-1 build, and its baseline is itself a *target*,
> not a shipped state. In the source docs DiffusionGemma's PROPOSE lane is "the target
> posture, shadow-only until measured" (readme §5; readme-revised) and the value-signal
> layer is migration milestone M2.5 (plan §14) — both are **specified contracts in the
> target architecture, not asserted as implemented.** The three files never claim any
> milestone is shipped; implementation status is out of their scope and therefore out of
> this document's. What is **new here** — beyond even that target — is (a) treating the
> value-signal layer as a *steering reward* (it is specified as a backstage gauge,
> "forbidden to steer," not a reward), (b) introducing a **learner** where the plan states
> there is none, and (c) the four moves below.

### 5.1 Why diffusion

The build needs four capabilities, and all four are native to a diffusion / bidirectional
model — so the back half can be grown without breaking the front half. Each maps to a
requirement of the pivot. (Honest caveat: these are properties of diffusion models
*generally*; whether DiffusionGemma's specific weights and interface expose a usable
reward-gradient hook and a classifier-free-guidance path is an engineering precondition
**Phase 0/1 must verify, not assume.**)

| Capability | Native diffusion mechanism | Serves |
|---|---|---|
| **Conditioning** | Classifier-free guidance (CFG) on a context vector — train conditioned + unconditioned, push toward the conditioned distribution at inference. Make the conditioning a learned per-user preference embedding `u`. CFG strength is itself a personalization dial (weak ≈ population, strong ≈ sharply personal). | **Learn values** |
| **Reward-guided sampling** | Steer the denoising trajectory with the gradient of a reward model `r(shape, state, u)`, **base frozen** — no weight update, no forgetting, no corruption of the composition prior. Guidance scale γ is a single safety dial: γ=0 recovers the imitation prior; small γ nudges; large γ over-optimizes. This is the same pattern as Φ (readme §3 — "nudges which already-feasible candidate the model favors… has no authority… never participates in admission"), moved upstream into composition. **γ-guidance is a stronger, learned Φ.** | **Optimize acceptance** (with a frozen base) |
| **Diffusion-DPO** | Direct Preference Optimization has a diffusion variant: preference-tune directly on (preferred, dispreferred) **pairs**, no separate reward model or RL rollouts. Earned acceptance yields exactly such pairs (earned-accepted > rejected/edited/deleted, from `CounterfactualSlateLogV0` + `RecommendationEditDistanceV0`). Offline pair-learning fits the data regime — **there is no cheap simulator** (§3). Note: unlike 2a it **moves weights** — it is the §6.2 Delta-2 learner, and so is not reversible the way frozen-base guidance is. | An **offline** alternative to reward-guided sampling |
| **Holistic whole-shape composition** | Diffusion denoises the whole object at once (bidirectional), balancing many preference axes simultaneously — the `DecisionAxisV0` set (`energyCost`, `socialLoad`, `recoveryNeed`, `gapTopology`, `daypartFit`, `durationFit`, …) — rather than committing early. Matches "the shape is the product" (readme §4.1) and why-lines composed against the whole day (readme §4.4). | One `u`-conditioned, γ-guided pass that jointly satisfies "rest-shaped AND low-setup AND fits the gap AND honest why-line" |

### 5.2 The four phases

```text
Phase 0  INSTRUMENT          Phase 1  LEARN VALUES        Phase 2  OPTIMIZE ACCEPT.    Phase 3  GUARD DRIFT
─────────────────────────    ─────────────────────────   ─────────────────────────   ─────────────────────────
promote the value-signal     per-user embedding u;        reward GUIDES composition:  bound the two failure
layer to a typed             diffusion behavior-clone     (2a) reward-guided sampling  modes Phase 2 introduces
earned-acceptance reward     of earned-accepted shapes,   [v1] frozen base, bounded γ  (comfortable FP +
with full lineage + a thin   conditioned on (state, u),   OR (2b) Diffusion-DPO,       reward over-optimization)
explicit-useful channel.     across ALL types.            KL-leashed to Phase-1 prior. with the §4.4 mitigations.
NO weight/sampler change.    DELTA 2 STARTS (BC trains    DELTA 1 (steering: §10.5/    Bounds, not cures.
(but explicit-useful is a    weights; the plan's "no      §10.2/§11.5). 2b also
visible-measurement          learner" relaxes here).      moves weights (DELTA 2);
relaxation — see Phase 0).   NO acceptance pressure yet.  2a [v1] stays frozen.
```

**Phase 0 — Instrument the reward.** Manufacture a trustworthy target before changing how
anything is composed. The signals already exist on `RecommendationValueSignalV0`
(`prePickerFingerprint`, `postPickerFingerprint`, `editDistance`, `rejectionSet`,
`survivalAtT`, `outcomeReason`, `measurementStatus`; plan §10.1–§10.4) but are
backstage-only and non-authoritative (plan §10.5). Phase 0 adds: (a) the typed
earned-acceptance reduction (§4.1); (b) a thin, rarely-shown, owner-gated
"was this useful?" channel as a typed reward term (the least-corruptible sample). **This
channel partially relaxes a third, sacred invariant by design** — *"Measurement has no
visibility"* / *"the instant the user can feel they are being measured, the calendar
becomes surveillance"* (plan §10.5, §13.3; readme §10.5). Asking the user a value question
**is itself visible measurement** — that is the precise thing the invariant forbids, not
merely a storage or frequency concern. It is judged acceptable only because it is *rare,
owner-gated, non-grading* (it never tells the user "we learned X"), and it still obeys the
no-surveillance storage posture; whether that judgment holds against §10.5/§13.3 is an open
question, not a settled one (§7 row 5). All *other* measurement stays invisible. (c) reward
lineage + the `.notMeasured`-never-zero discipline carried through, so an incomplete reward
term cannot enter a gradient. **Exit gate:** reward is computable, lineage-complete on a
real cohort, and demonstrably `.notMeasured` (not 0) when incomplete.

**Phase 1 — Learn values.** Teach the composer the distribution of shapes *this* user
earns-accepts, with **no** acceptance-optimization pressure yet (that is Phase 2).
Keeping the two phases separate is what makes the reconciliation auditable: Phase 1 fixes
*what distribution to imitate*; Phase 2 adds a *bounded push* toward acceptance inside it.
Mechanism: (a) a per-user preference embedding `u` derived Swift-side from
`DecisionSufficientStatisticV0` axes + Phase-0 earned-accepted history, crossing the
membrane only as a non-identifying conditioning vector (same discipline as
`decisionStats`/`relationChips`; plan §5, §6); (b) diffusion **behavior-cloning** —
train/adapter-tune DiffusionGemma to reconstruct earned-accepted shapes conditioned on
`(state, u)`. This **trains weights, and so is the first instance of the §6.2 Delta-2
learner** — the plan states "there is no learner today" (readme §6 P2) and that the prep
station is "feature engineering over a frozen model… nothing learns" (plan §6); Phase 1
relaxes that. It is imitation, not reward maximization, and sets the prior the Phase-2
KL leash / γ bound is measured against; (c) **generalize across all types** — rest,
focus, prep, social, errands (the `desiredOutcome` space already enumerated in plan §7.4:
"rest, reset, preparation, decompression, focus protection, recovery, or transition").
Nothing in `RecommendationShapeProposalV0` is rest-specific.

> **Product-change note (owned by this build, not asserted by the current plan).**
> plan §13 still says "the single feeling sold is permission to rest." Generalizing past
> rest — away from the narrow/paternalistic "decide when you've earned rest" toward
> general personalization across all shape-families — is a **deliberate product change
> this document owns.** The *contract surface* already supports it
> (`RecommendationShapeProposalV0.desiredOutcome`); the *product framing* in plan §13 does
> not. This is flagged, not glossed.

Phase-1 invariants: `u` and the cloned composer still produce only a **shape** (PROPOSE)
or an **index** (SELECT) — no authority fields. Swift still materializes, D2-binds, and
revalidates live. No public PROPOSE launch off Phase-1 learning until lineage + both
fingerprints exist (plan §11.5, §14 M2.5-before-M4). Training stays offline and
owner-gated. **Exit gate:** the `u`-conditioned composer reproduces earned-accepted
shapes across all type families in shadow, at **admit-rate parity** vs the unconditioned
composer (`testProposeAdmitRateParity`) — i.e. conditioning changed *preference*, not
*feasibility*.

**Phase 2 — Optimize acceptance.** Push composition toward higher predicted **earned**
acceptance, *inside* the Phase-1 distribution. **This phase is where Delta 1 (a reward may
steer composition — §10.5/§10.2/§11.5) activates**; option 2b additionally exercises Delta 2
(moving weights) while 2a [v1] keeps the base frozen — see §6.2. Two options, **2a
recommended for v1**:

- **(2a) Reward-guided sampling [v1].** A lightweight reward model `r(shape, state, u)`
  predicting earned-acceptance (trained on Phase-0 labels) is used as **bounded guidance
  with scale γ** during denoising; the base composer is **frozen**. Preferred for v1
  because base-frozen is reversible, the bound is an explicit lever, and it needs no new
  preference-pair pipeline. γ=0 = Phase-1 prior; bounded γ = nudge; unbounded γ =
  reward-hacking.
- **(2b) Diffusion-DPO.** Offline preference-tune on earned-accepted > rejected/edited/
  deleted pairs, **KL-leashed** to the Phase-1 imitation prior so the tuned model cannot
  drift arbitrarily from learned values. More committal (it **moves weights** — this is the
  §6.2 Delta-2 learner). The KL leash is its distance-from-prior analog of γ, with one
  load-bearing difference: γ is a **sampling-time dial on a frozen base, tunable or
  removable per request**, whereas the DPO KL leash is a **training-time regularizer
  committed into the tuned weights** — so 2b is **not reversible the way 2a is.**

**Exit gate:** in shadow (plan §14 M4/M5), guided/tuned PROPOSE must **reduce edit-distance
and/or rejection WITHOUT raising undo or lowering survival-at-T**
(`testProposeReducesEditDistanceWithoutUndoRise`), at admit-rate parity, before any
public selection-moving change — owner-gated (`testPublicProposeRequiresOwnerGate`).

**Phase 3 — Guard drift.** The four-part mitigation of §4.4 made operational: periodic
explicit elicitation; population-level drift monitoring (the uniform-global-shift tell);
the hard why-line-true-today gate (`CopyHonestyGate`); and bounded optimization (γ / KL
held to an owner-set bound, on top of the frozen base). Plus the unchanged structural
backstops (D2, `support(staged) ⊆ F(x_live)`, the confirm tap, `.notMeasured`-never-zero,
measurement-before-mutation). **Gate:** drift monitor + elicitation live and owner-reviewed
**before** Phase-2 guidance moves any public traffic (the spirit of plan §14 M6's "keep
all measurement invisible" + owner gate, extended to the new reward).

### 5.3 Cold-start — population prior warmed per-user

`u` (Phase 1) and `r(shape, state, u)` (Phase 2) need per-user earned-accepted history; a
new user has none, and n=1-with-no-simulator means you cannot synthesize it. Recommending
nothing or randomly both fail the felt-safety bar (readme §13.2). Solution: **initialize
`u` to a population prior** — the typical preference embedding learned across consented
users — and recommend from the population-conditioned composer. As the user accrues
earned-accepted outcomes (Phase-0 reward with complete lineage + both fingerprints), `u`
migrates from the population prior toward the individual and CFG strength on the personal
component can rise. This is natural for diffusion: weak/near-population conditioning at
first, sharpening as evidence accrues. Invariants: a cold user is composed-for by the
population prior, **not by phantom personal "zeros"** (`.notMeasured`-never-zero; plan
§11.4–§11.5; `testNotMeasuredNeverZero`); the population prior must itself respect the
membrane (built from non-identifying `DecisionSufficientStatisticV0`; plan §5), so
cold-start cannot leak one user's identity into another's conditioning. The same
population view that warms cold users also powers the Phase-3 drift monitor.

### 5.4 The SELECT → PROPOSE curriculum

Start where the blast radius is smallest; graduate per shape-family as the reward earns
trust. This maps almost one-to-one onto the migration the plan already defines (plan §14
M3–M6), with the reward threaded in as the thing being shadow-validated at each rung.

```text
SELECT (low blast radius)                          PROPOSE (higher blast radius)
─────────────────────────────────────             ─────────────────────────────────────────
Swift enumerates slateOfferedV0;                   model composes a shape Swift materializes.
model returns an INDEX.                            Promote ONE desiredOutcome family at a time:
Reward (u + bounded γ) can only REORDER /             rest → focus → prep → social → errands  (§7.4)
choose among already-feasible cells —              A family graduates only once its reward model shows
exactly the Φ / PickDiscriminatorV0               the M5 lift — reduced edit-distance/rejection without
preference-bias surface, already parity-gated.     undo rise or survival loss — at admit-rate parity,
Reward influence over an index CANNOT widen F(x).  passing the why-line audit, behind an owner gate.

         M3                M4                    M5                       M6
   SELECT public  →  PROPOSE shadow  →  fixed-pool SELECT-vs-  →  public PROPOSE gate, owner-
   on revised        (same D2 wall,     PROPOSE value-signal      approved; deterministic SELECT
   context           Swift materializes) evaluation               fallback kept PERMANENTLY
```

Tests at each rung: `testProposeAdmitRateParity`,
`testProposeReducesEditDistanceWithoutUndoRise`, `testWhyLineTrueTodayAudit`,
`testPublicProposeRequiresOwnerGate`. **Honesty:** the curriculum reuses the existing
safe-migration scaffold unchanged; what is genuinely new is only (i) the reward acting as
guidance *within* each rung and (ii) per-family graduation gated on that reward's measured
trust. **SELECT stays the deterministic floor even after a family graduates.**

---

## 6. What stays / what changes

The split is clean: the **wall stays bit-for-bit; the reward changes.** A reward-guided
card must still be materialized by Swift, admitted by D2, and tapped by a human — the
reward GUIDES which feasible shape DiffusionGemma composes; it **never gains authority
past D2.**

### 6.1 What stays — the wall (unchanged)

Every admission-critical mechanic in plan §8 / §11 / §13 / §18 is untouched:

| Stays unchanged | Statement | Source / test |
|---|---|---|
| **D2 single admission wall** | The single in-process Swift seam — not a network service, not a second verifier, not model-callable; lookup-never-reconstruction. A guided card enters D2 through the **same** 15-step path; guidance adds no seam and gives the reward no vote inside D2. `RecommendationVerdictV0` stays non-`Codable`. | plan §8, §8.3; `testD2InProcessOnly`, `testRecommendationVerdictNonCodable` |
| **`support(staged) ⊆ F(x_live)` + live recheck** | Staged support is a subset of live, revalidated feasible support, at admission (§8.3 step 13) and again at the confirm-time live recheck (TOCTOU hardening). This is exactly where a flattering-but-infeasible guided shape dies: Swift materializes independently and revalidates live. "Increased model capability never relaxes it" extends verbatim to increased reward capability. | plan §8.3 step 13, §9.3, §11.1; readme §3; `testSupportStagedSubsetOfLiveF` |
| **Confirm tap / no auto-write / sacred invariants** | Writes require a human tap on a server-minted `AllowedActionV0` (minted only-after-staging, short-lived, scoped, invalidated by changed support). The four sacred invariants hold. A reward-optimized card is still a *staged* card behind a tap — the decisive action is a human tap, not `env.step()`. | plan §9.3, §13.2–§13.3; readme §8.4, §10.5; `testConfirmTapRequiredForWrite`, `testCannotTouchNonCreatedEvents` |
| **Capability ≠ authority / hydration firewall** | The model authors no identity, time, title, evidence hash, source kind/strength, provenance, fingerprint, verdict, or action; Swift hydrates from its own support and revalidates live. This is the precise sense of "guides but no authority": the reward changes DiffusionGemma's *preference* over shapes (the Φ lane), nothing else. | plan §8.5, §18 rows 1 & 13; readme §3 (Φ), §4.3 |
| **Copy-honesty / why-line-true-today** | `CopyHonestyGate` blocks unsupported preference claims, unsafe names, implied source strength, heuristic-chips-as-learned-truth, and copy from backstage measurement. A reward that learns "flattery is accepted" still cannot **say** a false why-line — the persuasion surface is gated independently of the reward. | plan §12.2, §10.4, §14 M4; readme §4.4, §10.4; `testWhyLineTrueTodayAudit` |
| **Admit-rate parity on guided candidates** | Admit-rate parity "applies to guided, pinned, or shape-proposed candidates so guidance can never leak into authority by changing validation semantics." This invariant was written for exactly this pivot: a guided candidate must clear D2 at the same admit rate as an unguided one. If guidance starts moving offered `F(x)`/admit rate, that is no longer free guidance — it is an owner-gated `F(x)` policy change requiring a parity test. | plan §10.2, §18 row 11; readme §5/§10.2 (the "P3 / admit-rate parity" invariant — distinct from readme §3's relation-chip "P3" label); `testProposeAdmitRateParity` / `GuidanceParityTests` |
| **Measurement invisibility** | The reward steers **silently**; it is never surfaced as a user grade. "Never say or imply we learned you do X" (plan §12.3) and "never let measurement become visible surveillance" (§13.3) are untouched. | plan §12.3, §13.3 |

### 6.2 What changes — two scoped relaxations

The pivot relaxes **two** things, not one. Both are named here; nothing else in §18's
preserved-invariants table moves.

**Delta 1 — a measured reward may steer composition (relaxes the visibility/steering
posture).** *Today* (plan §10.5): *"The model has no authority. Measurement has no
visibility. The loop improves in the dark."* Value signals are retrospective and forbidden
to steer: edit-distance "never changes admission… may inform future Swift-owned ranking
only after coverage and owner gates" (§10.2); survival-at-T is a backstage gauge (§10.4);
measurement-before-mutation forbids any preference update that steers composition (§11.5,
§18 row 3). This document graduates those signals into a single prospective
**earned-acceptance** reward that **steers DiffusionGemma's composition** — via
reward-guided denoising (bounded γ, base frozen) or Diffusion-DPO (KL-leashed to the
Phase-1 imitation prior). This is the **prospective-vs-retrospective inversion**: a value
function steers; the backstage gauges were forbidden to. Marked explicitly: it contradicts
§10.5, the steering-adjacent posture of §10.2's "never changes admission," and §11.5
measurement-before-mutation **as currently worded.**

**Delta 2 — the composer may be trained (relaxes the no-learner / frozen-model posture).**
The plan states the system has **no learner** (readme §6 P2: "there is no learner today")
and that its only learning-adjacent layer is "feature engineering over a frozen model, not
representation learning… *nothing learns inside this layer*" (plan §6 / readme §6). This
build introduces a learner where the plan has none: **Phase 1 behavior-cloning** and
**Phase 2b Diffusion-DPO update DiffusionGemma's weights.** This is a materially distinct
second departure — it is *not* subsumed by "a value signal may now steer composition," and
it is why the recommended v1 (Phase 2a reward-guided sampling) deliberately keeps the base
**frozen**: only 2a avoids moving weights. Marked explicitly alongside Delta 1: the
no-learner posture of plan §6 / readme §6 is relaxed by Phase 1 and Phase 2b; Phase 2a
[v1] is the variant that does not relax it.

```text
            steers composition (NEW)
                     │
 reward r(shape,state,u) ──► DiffusionGemma π ──► shape
                                                   │  (still only a shape — no authority fields)
                                                   ▼
                          Swift materializes ──► D2 ──► support(staged) ⊆ F(x_live) ──► human tap ──► write
                          └──────────────────── UNCHANGED WALL (still rules admission) ─────────────────────┘
```

**The boundary of the two relaxations (to prevent over-reading them).** Both are scoped to
**composition upstream of D2 only** — steering it (Delta 1) and training the composer that
produces it (Delta 2). Together they do **not** relax: `support(staged) ⊆ F(x_live)`; D2
as sole seam; the human confirm tap; the hydration firewall; copy-honesty; the four sacred
invariants; or the user-facing invisibility of measurement. Measurement-before-mutation is
**not deleted but re-scoped**: lineage + both fingerprints + explicit-useful coverage must
exist before any reward is *trusted to steer* or any earned-accepted history is *trusted to
train on* (Phase 0). The relaxations are precisely: *(1) a measured, bounded,
regret-penalized reward MAY now steer composition;* and *(2) the composer MAY be trained on
earned-accepted history (frozen-base 2a needs no weight update; 2b moves weights).*
Everything else in §18's preserved-invariants table survives.

### 6.3 The trade (stated honestly, not glossed)

The pivot is **strictly more capable** (personalization across all shape-families,
conditioned on a learned `u`; optimized acceptance via native diffusion mechanisms) and
**strictly less maximally-safe** than the prior posture (which had zero value-signal
authority over composition *and* no learner at all). The trade **buys** personalization and
engagement; it has **two prices, both named, neither glossed**: (1) the residual
**comfortable false positive** (§4.3) — pleasant permission the user accepts, never
regrets, never needed, which regret signals structurally cannot catch — **mitigated, not
eliminated** by the seven guards of §4.4; and (2) **a learner where the plan had none**
(§6.2 Delta 2) — frozen-base v1 (2a) keeps this maximally contained and reversible, but the
2b path moves weights and is **not reversible per request**, carrying drift/forgetting risk
the no-learner posture never had to. This is a real pivot, not a copy edit.

### 6.4 Contract evolution

| Contract | Today | Under this build |
|---|---|---|
| `RecommendationValueSignalV0` (+ `RecommendationEditDistanceV0`, `CounterfactualSlateLogV0`, `SurvivalAtTSignalV0`) | Write-only backstage gauge, forbidden to steer (struct at plan §10.1; the "forbidden to steer / loop improves in the dark" rule at §10.5; measurement-before-mutation at §11.5) | Input to a **typed earned-acceptance reward** with lineage; `SurvivalAtTSignalV0` is the specific term **promoted from gauge to reward**. `.notMeasured`-never-zero carries forward **as the reward's gating** |
| **`u`** (per-user preference embedding) | — does not exist — | **New.** Derived from `DecisionSufficientStatisticV0` + earned-accepted history; CFG conditioning so the composer learns values; cold-start = population prior warmed per-user; lives in the Φ lane, **never authoritative**, membrane-respecting (plan §5, §12.1) |
| **`r(shape, state, u)`** (lightweight reward model) | — does not exist — | **New.** Predicts earned-acceptance; bounded γ guidance with base frozen (2a), or a Diffusion-DPO objective KL-leashed (2b); conditions **composition, never admission** |
| **explicit-useful channel** | — does not exist — | **New.** A thin, rarely-shown, owner-gated "was this useful?" term — the least-corruptible reward anchor (Phase 0) |
| `PickDiscriminatorV0` | Post-admission ranker behind an anti-laundering firewall (plan §11.3) | **Unchanged in role** — stays a post-admission ranker; its firewall still forbids "sampler/re-noising confidence as quality" and "any user-visible value signal." The reward is **not routed through `PickDiscriminatorV0`**; it steers the *sampler* pre-D2. The firewall **holds for D2/authority and for `PickDiscriminatorV0` itself**, and relaxes **only** for pre-D2 composition guidance |

A note on `PickDiscriminatorV0`, because it is the precedent that bends: `PickDiscriminatorV0`
ranks **admitted** candidates (post-D2, retrospective features); the reward steers
**proposal** candidates (pre-D2, prospective). The new reward does, *upstream* of D2, the
steering that §11.3/§10.5 forbade value signals from doing *downstream.* Conflating the two
— routing the reward through `PickDiscriminatorV0` — would launder a steering signal into
the ranking firewall §11.3 protects. They are kept distinct on purpose.

---

## 7. Risks & open questions

| # | Risk / open question | What we know | What is open |
|---|---|---|---|
| 1 | **The comfortable false positive** | Structurally invisible to all behavioral regret signals (§4.3); bounded by explicit elicitation + population-drift monitoring + the why-line gate + bounded γ/KL + frozen base + the wall | How noisy is the explicit-useful sample in practice? At what elicitation rate does it stop being "rare" and start feeling like surveillance? There is **no true value verifier** to validate against (readme §4.6) |
| 2 | **Preference drift toward flattery (reward hacking)** | Population-level monitoring detects the **uniform global shift** tell; per-user reward can be Goodharted invisibly, a population cannot hide drift (§4.4) | Threshold and cadence for the drift monitor; how to distinguish a genuine population taste shift from systemic flattery |
| 3 | **Introducing a learner (§6.2 Delta 2)** | The plan states there is **no learner today** and the model is **frozen** (plan §6; readme §6 P2); this build trains weights in Phase 1 (behavior-cloning) and Phase 2b (DPO). v1 (2a) keeps the base frozen specifically to avoid this; 2b is **not reversible** the way 2a is (KL is committed into weights, not a per-request dial) | Whether to ship 2b at all vs staying on frozen-base 2a; catastrophic-forgetting / drift risk once weights move; how to roll back a trained composer; the audit story for a learner the plan never scoped |
| 4 | **γ / KL tuning** | γ is a single safety dial (0 = imitation prior; bounded = nudge; unbounded = reward-hacking); frozen base makes 2a reversible per-request | The actual bound is empirical; how to set and audit it per shape-family; whether 2a (sampling) or 2b (DPO) is the right v1 commit beyond the recommendation of 2a |
| 5 | **Cold-start** | Population prior warmed per-user; `.notMeasured`-never-zero prevents phantom-zero personalization; weak→strong CFG as evidence accrues (§5.3) | Migration rate from population to personal; how much earned-accepted history before personal conditioning is trustworthy at n=1 |
| 6 | **Explicit-elicitation cost — a relaxation of "measurement has no visibility"** | The least-corruptible value sample, but **asking is itself visible measurement**, which §10.5/§13.3 name as the surveillance line — not merely a storage concern. Held acceptable only as rare, owner-gated, non-grading; storage still obeys the no-surveillance posture | Whether a visible value question is acceptable against §10.5/§13.3 at all; the felt-safety cost of asking; the frequency that maximizes signal without making the user feel measured |
| 7 | **DiffusionGemma interface preconditions** | The four diffusion capabilities (§5.1) are general properties of the model class | Whether DiffusionGemma's specific weights/interface expose a usable reward-gradient hook and a CFG path — **Phase 0/1 must verify, not assume** |
| 8 | **The product-framing change** | Generalizing past "permission to rest" is supported by the contract surface (`RecommendationShapeProposalV0.desiredOutcome`, plan §7.4) | plan §13 still asserts "the single feeling sold is permission to rest"; this build **owns** that change and must reconcile it with the product spec, not just the contracts (§5.2) |

**The one-line summary.** Borrow the stack, do not blindly close the loop: grow the value
organ as a measured, bounded, regret-penalized **earned-acceptance** reward that steers
composition; hold the trust wall bit-for-bit; mark the two scoped relaxations honestly
(reward-may-steer, §10.5/§10.2/§11.5; and a learner-now-exists, plan §6); and
be honest that the price of personalization is a comfortable false positive we can bound
but not buy away.
