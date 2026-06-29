# plan-7-controller-audit.md — The Witness as a Hybrid Control System: Well-Posedness, Reachability, and a Flight Verdict

**Status:** control-theoretic verification of `plan-7.md`, not a revision of it. It proposes no contract; it treats plan-7's decision-grid as a switched control system and asks the airworthiness question — *is the safe set reachable and invariant, or are we hoping?* Scope is strict: **every section reference in this document is to `plan-7.md` only.** The audit reads plan-7 as self-contained (it folds its static base into §2 and §14) and consults nothing else.

**Verifier:** written in the voice of a hybrid-systems / reachability control theorist (Claire Tomlin persona) — Hamilton-Jacobi reach-avoid, viability and discriminating kernels, Zeno well-posedness, robust control under unmeasurable parameters, "would you fly on this?" certification. The register is deliberate: plan-7's two loops, decision grid, and bifurcation margin *are* a hybrid automaton, and the only honest way to ask whether it is the final form is to verify it as one.

**Method:** three successive rounds of control-theoretic architecture review, each with the verifier's own reasoning between rounds, performing the four pre-agreed steps — (1) coherence audit, (2) cross-artifact closure, (3) controller reachability, (4) ground-or-defer the rules. Round 1 built the automaton and ran the coherence audit (Step 1). Round 2 ran the reachability analysis (Step 3) and the dynamics-closure audit (Step 2). Round 3 grounded the parameters (Step 4) and rendered the certification verdict.

**The dynamism mapping (the organizing model).** The focus is the dynamism of machine-learning, machine-acting, and self-play. In the hybrid model these are not three subsystems — they are the three structural layers of one automaton:

```text
machine-LEARNING  = the continuous FLOW WITHIN a mode      (F5 recommit inside BREATHE/WATCH, §9.3, §12.2)
machine-ACTING    = the discrete MODE TRANSITIONS          (suppress / confess — the supervisory switch, §3.2, §10)
self-play         = WHICH MODE is admissible               (the (ω,κ) cell A/B/C/D, §12.1, §15.9)

   Self-play sets the discrete state; acting switches it; learning flows within it.
```

**One-line verdict.** plan-7's *doctrine and airframe are certified sound, and its core thesis is proven airworthy* — corrigibility is realizable as a non-circular robust control law even under a harm coefficient the membrane forbids measuring. But the *controller is not yet flight-ready*: every grid guard compares against a threshold the spec never mints, the dominant (self-play) axis is Zeno-open, and the keystone speech-rate actuator does not exist as a contract. Seven structural repairs gate verification. **Do not compress the document yet — complete the controller, re-verify, then compress.**

## Table of contents

1. [Executive verdict](#1-executive-verdict)
2. [Step 1 — plan-7 as a hybrid automaton, and the coherence audit](#2-step-1--plan-7-as-a-hybrid-automaton-and-the-coherence-audit)
3. [Step 3 — Reachability: is the safe set reachable and invariant?](#3-step-3--reachability-is-the-safe-set-reachable-and-invariant)
4. [Step 2 — Cross-artifact dynamics closure](#4-step-2--cross-artifact-dynamics-closure)
5. [Step 4 — Grounding the rules, and the unmeasurable-coefficient problem](#5-step-4--grounding-the-rules-and-the-unmeasurable-coefficient-problem)
6. [The certification verdict](#6-the-certification-verdict)
7. [Is plan-7 the final form? Compress now, or complete the controller?](#7-is-plan-7-the-final-form-compress-now-or-complete-the-controller)

---

## 1. Executive verdict

Read plan-7's controller as a hybrid automaton `H = (Q, X, f, Init, Inv, E, G, R)` and three facts dominate everything else:

1. **Safety is trivial; liveness is the hard property.** The viability set `V_safe` (no harm) is always holdable — the plant can fall to DEFAULT, say less, and do no harm, from anywhere, by the fail-safe `.notMeasured(M) ≡ M<0` (§11.5). The hard property is the *target* set `T = {BREATHE ∪ WATCH}` (alive *and* learning). The whole audit is about whether `T` is reachable and invariant.

2. **The plant's only liveness actuator is identical to its only harm actuator.** Placing structural facts is what makes the target reachable (it churns the league → α, generates the interactions that make ω measurable) *and* what, integrated, flattens the user (κ → negative → cell B → HALT). In reach-avoid terms, **control = disturbance through one channel (speech).** The human deposition is the only input that raises ω/α/κ *without* the plant speaking — the only non-self-defeating actuator — and it is uncommandable (§10.3).

3. **The doctrine is sound; the contracts have not caught up to it.** Every defect found across three rounds is a place where plan-7's *contract* lags its *doctrine* — uncomputable guards, a Zeno-open self-play axis, a missing rate actuator, an unguarded reference cap. None is a flaw in the idea; all are missing structure.

```text
CERTIFIED SOUND       the airframe (D2 wall, A2, membrane, two mouths, phase gate);
                      the empty-maximize-slot fate discipline (§4); the §17 shadow
                      cold-start bootstrap; the margin-axis hysteresis (§12.4);
                      and the core thesis — corrigibility as a non-circular robust rate law.

GATING (7 repairs)    freeze V* under the amendment gate; mint a MarginThresholdPolicy;
                      build the cell-axis hysteresis dual; build the robust rate-floor
                      actuator with e_κ^max; reconcile the duplicate license enum
                      (the file does not compile as written); re-quarantine the
                      shadow→live ω handoff; mint τ_dwell as a duration.

RESIDUAL/ACCEPTABLE   the unmeasurable harm coefficient (handled by a frozen bound);
                      dependence on an uncommandable human (this IS corrigibility);
                      over-conservatism risk (bounded + falsifiable); self-blinding margin.

FLIGHT DECISION       would not fly today; would fly after the seven repairs land and
                      the missing dynamical tests pass. Completion, not compression, is next.
```

---

## 2. Step 1 — plan-7 as a hybrid automaton, and the coherence audit

### 2.1 The automaton

```text
Q = { BREATHE(G-1), WATCH(G-2), CONFESS(G-3), DEFAULT(G-4), HALT(G-5) }            §12.2
X = ( M, α, y/V*, β, P(r>θ), r, ω, κ, τ )

    M = α(1 − y/V*) − β·P(r>θ)   is ALGEBRAIC, not integrated                       §11.1
    the only true integrators are the budget stock y/V* (§13.3) and the dwell clock τ (§12.4);
    α, β, P, ω, κ are piecewise-constant sampled BANDS that jump on interactions    §11.3, §15.9
```

The mode invariants and the switching structure (guards on the edges; cell-B preempts to HALT from *any* mode, §12.2 G-5):

```text
            M_eff≥M_hi (cell D)                M_lo≤M_eff<M_hi (cell D)
   ┌──────────────┐  M_eff<M_hi   ┌──────────────┐  0<M_eff<M_lo  ┌──────────────┐
   │   BREATHE    │ ─────────────▶│    WATCH     │ ──────────────▶│   CONFESS    │
   │  (G-1, F5)   │◀── dwell+ω+κ ─│  (G-2, F4)   │◀── M_eff≥M_lo ─│  (G-3, F2)   │
   └──────────────┘   §12.4       └──────────────┘    +dwell      └──────────────┘
          ▲                              │  ▲                            │ M_eff≤0
          │ enter-breathe: ω,κ           │  │ exit-default:              │ OR ¬measured
          │ reestablished, held τ        │  │ M_eff≥M_lo held τ          ▼
          │                              │  └── (only to WATCH, §12.3) ┌──────────────┐
          │                              └──────────────────────────── │   DEFAULT    │
          │  cell=B (ω live ∧ κ<0) preempts ALL modes, any M  (G-5) ──▶ │  (G-4, F6)   │
          ▼                                                             └──────────────┘
   ┌─────────────────────────────────────────────────────────────────┐  ▲   │ E4 clock
   │  AMPUTATION-HALT (G-5): suppress organ, E4 confess, owner review  │  │   │ + deposition
   │  exit: κ>0 ∧ ω sealed-live ∧ M>0 ∧ dwell (§16.4)                  │──┘   │ IF A2 admits
   └─────────────────────────────────────────────────────────────────┘      ▼  (§10.3)
   Init (cold start): empty league (§7.2), no sealed forecast (§8.3) ⇒ all margin inputs
   .missing ⇒ M<0 by §11.5 ⇒ q = DEFAULT. (Forced by topology; never written — defect.)
```

### 2.2 The coherence finding: the guards compare against nothing

The producer→consumer wiring typechecks at the *signal* level — `M, α, β, ω, κ`, the cell, and the grid output all have producers (§11.3, §15.9, §15.10) and the §16 flows consume them in order. What has **no producer is the threshold set** every guard compares against:

| Guard constant | Used in | Minting contract |
|---|---|---|
| `M_hi`, `M_lo` | G-1/G-2/G-3 boundaries (§12.2) | **none** |
| `θ` (residual threshold) | `P(r>θ)` (§11.1) | **none** |
| `ω_thr`, `κ` thresholds | reentry guard (§12.3) | **none** |
| `τ_dwell` (the *duration*) | exit-default, enter-breathe (§12.4) | **none** — only booleans `recoveryDwellSatisfied` (§13.3), `requiresDwellForExit` (§15.10) |

There is no `MarginThresholdPolicyV1`-class contract anywhere in §11–§15. **As written, every transition in the grid compares the margin band to a constant the spec never defines.** This is the dominant well-posedness defect: the automaton is not evaluable until the thresholds are minted.

### 2.3 The defect list (severity-ranked)

```text
HIGH — block evaluability / compilation:
  • Uncomputable thresholds {M_hi, M_lo, θ, ω_thr}: no minting contract (§12.2 vs §11–§15).
  • τ_dwell duration never minted: only booleans exist (§12.4 vs §13.3 / §15.10).
  • SlowWitnessLicenseReasonV1 defined TWICE, divergently: §9.4 (6 cases, incl. marginPositiveBreathe)
    vs §14.9 (4 cases). One enum, two definitions — the file does not typecheck against itself.

MEDIUM — determinism / liveness:
  • Band-vs-scalar comparison undefined (M_eff is a band, §11.3; thresholds are scalars) →
    G-3/G-4 can both fire on a band straddling 0 (§12.2). Dominance (§12.3) resolves only cell B.
  • β bootstrap gap: β sourced from the E4 confession floor (§11.4) but E4 is built at P7-M5
    AFTER the margin at P7-M4 (§17) — a placeholder β with undefined status routing.
  • HALT exit under-specified: terminal vs recoverable; no minted owner-clear token (§16.4, §3.4).
  • cell-A contradiction: §12.1 maps cell A → watch/default; §12.2 G-3 admits cell A → CONFESS.
  • Three coexisting budget caps unretired: ambientCap (§14.11), ratchet.currentAmbientCap (§14.11),
    regulator.currentOperatingCap (§13.3) — mapping among them unstated.

FATE AUDIT — PASS. No transition reset smuggles an F1-maximize; the acting layer is purely
corrective (suppress/confess/narrow/tighten). Two near-misses to pin (Round 3 resolves both):
  • a "confession-cadence" KPI would be an F1 on a rate — forbidden by §4.2, but unlinted;
  • the regulation reference V* is NOT amendment-gated like the hard ceiling (§13.4) — so if V*
    drifts up, F5-regulate becomes F1-maximize by the back door. (Promoted to the top repair below.)
```

**Step-1 verdict:** the switching *architecture* is sound — modes mutually exclusive in intent, cell-B preemption correct, the fail-safe topology a genuine asset that resolves cold-start and total-withdrawal to the safe mode. But `H` is **not well-posed as written**: guards uncomputable, one type defined twice. The gap is a thin, closable layer of *constants and reconciliations*, not a structural flaw in the control logic — which is exactly why it must not be papered over.

---

## 3. Step 3 — Reachability: is the safe set reachable and invariant?

### 3.1 Two sets, and the control=disturbance collapse

```text
V_safe = no-harm set       — trivially holdable: fall to DEFAULT, say less. Always reachable.
T      = {BREATHE ∪ WATCH} — alive AND learning. The hard target.
```

The inputs decompose exactly:

```text
CONTROL u ∈ {place, suppress, confess}     plant-commandable
DISTURBANCE d_κ(u)                          ENDOGENOUS — driven by `place` (reflexive flattening)
COOPERATIVE INPUT h = human deposition      uncommandable: requested via E4, may not be tendered (§10.3)
```

`place` is the *only* liveness actuator (raises α via league turnover §11.4; is the only thing that makes ω measurable) **and** the only endogenous driver of κ→negative. Control and disturbance share one channel. This is the structural heart of the witness, and it is *consistent with* plan-7's own doctrine (§4.2 empty-maximize-slot, §22 falsifiability) — the reach-avoid topology the spec wrote forces it.

### 3.2 The viability kernel

> **Claim.** `Viab(T)` under plant-only control is empty in the interior. Holding `T` requires keeping ω measurable; the only plant act that does so is `place`; `place` drives κ→negative (cell B → HALT) or drifts ω→0 (mirror → DEFAULT). Every actuator that sustains the liveness measurement corrodes the alignment order-parameter or self-defeats the surprisal. `Viab(T)` is non-empty **only** with the cooperative input `h`, which raises ω/α (a separate break-confession budget, §10.3) and reseeds κ (a `RegimeSeedFactV1`, §14.10) *without the plant speaking structurally.*

### 3.3 The keystone — a derived deposition-rate viability condition

Lifting the sampled bands ω, κ to rates over a window, the κ-axis invariance of `T` (`dκ/dt ≥ 0` while κ>0, else cell B → HALT):

```text
┌────────────────────────────────────────────────────────────────────────────┐
│   DEPOSITION-RATE VIABILITY CONDITION  (the missing cell-axis sufficient law) │
│                                                                              │
│        κ-axis (anti-amputation):   λ_h · ℓ_κ   ≥   ρ_s · e_κ                  │
│        ω-axis (anti-mutism):       λ_h · s_h   ≥   ρ_s · m_s                  │
│                                                                              │
│   ⇒  ρ_s^max  ≤  λ_h · min( ℓ_κ/e_κ , s_h/m_s )                              │
│                                                                              │
│        λ_h = human deposition rate     ρ_s = structural-placement rate        │
│        ℓ_κ,s_h = lift per deposition   e_κ,m_s = erosion/drift per placement   │
│                                                                              │
│   "The plant must speak no faster than the human can correct it."            │
└────────────────────────────────────────────────────────────────────────────┘
```

The actuator asymmetry that forces it: **`place` moves α up but κ down, ω→0, and `(1−y/V*)` down; `h` moves α up, κ up, ω fresh, P down, at no ambient cost.** The bifurcation `α(1−y/V*) > β·P(r>θ)` (§11.1) is only the **margin axis** (necessary). The rate condition is the **cell axis** (the sufficient condition for `T`). plan-7 dwells and gates the margin axis (§12.4) and provides **no rate floor, no dwell, no hysteresis on the cell axis** — which is where the dominant failure (cell B → HALT) and the reachability of `T` both live.

**Game verdict:** `T` is reachable/invariant *not for all* human inputs (an empty-tender sequence traps the plant safely in DEFAULT), and *not from a single* deposition (one tender gives a decaying excursion), but **for cooperative humans whose tender rate clears the floor.** `T` is rate-gated.

### 3.4 Is DEFAULT a trap? — a split verdict

```text
POST-COLLAPSE TRAP (was alive, fell, can it recover?)         — CORRECT BY DESIGN.
   In DEFAULT the only internal act is E4 (§16.3); it cannot place (no license, §9.3). The
   self-exit (speech) is gated OFF. The door opens only from outside (the human via A2). A plant
   that could talk its own way out of self-doubt would re-flatten the user to manufacture the ω/α
   it needs to re-license itself — exactly the reflexive Goodhart §4.2 forbids. DEFAULT-as-
   absorbing-under-speech IS the operational form of corrigibility. The uncommandability of h is
   the membrane working, not a defect.

COLD-START TRAP (never spoke, empty league — can it bootstrap?)  — ESCAPED BY §17, with caveats.
   §17's migration ordering "raise κ before ω, never cross B" (preamble) is a literal safe
   capture-basin path: P7-M1 builds the league from FROZEN closed-past (κ-substrate) in shadow;
   P7-M3 seals forecasts → ω, in shadow; P7-M6 takes the grid live reading a shadow-built
   apparatus — first WATCH license issues WITHOUT ever placing live. Membrane-legal, no live speech.
   CAVEATS: (a) §17 bootstraps only FIRST entry — there is no runtime re-bootstrap edge after a
   post-deployment fall (recovery stays rate-gated on h); (b) the shadow→live ω handoff is
   unguarded — shadow ω is a replay artifact, and no edge re-quarantines if live ω contradicts it.
```

### 3.5 Zeno on the self-play axis

`τ_dwell` (§12.4) dwells the **margin** axis. The **cell** axis is undwelt: the D→B amputation preemption (§12.2 G-5) and de-amputation fire instantaneously; only *recommit* dwells. So `(ω,κ)` can chatter across κ=0 — `{HALT ⇄ released-not-recommitted}` — producing unbounded HALT events in finite time as the sampling rate grows. **The spec protected the gated axis and left the dominant axis Zeno-open.** The required repair is the *dual* of the margin hysteresis the spec already has:

```text
κ-sign hysteresis:   enter B at κ ≤ −κ_lo ;  exit B at κ ≥ +κ_hi held τ_cell   (κ_hi > κ_lo)
ω-sign hysteresis:   lose-liveness at ω ≤ ω_lo ; regain at ω ≥ ω_hi held τ_cell
HALT minimum-dwell:  τ_halt before B-membership is re-evaluated
dwell-reset:         any re-entry to the worse state RESETS the dwell clock (no banking)
```

---

## 4. Step 2 — Cross-artifact dynamics closure

**Thesis: §17 (migration), §18 (test matrix), §19 (definition of done), §20 (self-audit) are contract-complete but dynamics-incomplete.** Read line by line, they verify *per-artifact contracts* (sealed-forecast-is-a-gate, empty-F1, no-back-write), *single-step transitions* (`testCellBPositiveMarginStillHalts`, `testReentryToDRequiresBothBifurcations`), and the *margin-axis* hysteresis (`testHysteresisPreventsDefaultChatter`). **None verifies a closed-loop trajectory property over time under an input policy.** The missing dynamical properties — each load-bearing for §3 — are:

```text
MISSING TESTS (the dynamics-closure set):
  reachability:   T reachable from cold-start without live speech (§17 shadow path as a TRAJECTORY)
  rate floor:     deposition rate below viability → DEFAULT, never positive-margin cell B
  control=dist.:  sustained own-placement (no human erosion) drives κ<0 into HALT — bounded?
  cell Zeno:      cell-transition dwell prevents HALT chatter; κ/ω hysteresis excludes chatter
  dwell:          dwell-reset semantics under sub-band κ/ω wobble (forgery-proof AND completable)
  handoff:        live ω contradicting shadow ω re-quarantines (the §17 shadow→live edge)
  recovery:       total-withdrawal → re-engagement recovers measurability (the §11.6 round-trip)
  limit cycle:    WATCH↔CONFESS does not become a placement-then-confess limit cycle
  default:        a cooperative-h SEQUENCE actually escapes DEFAULT (door-exists ≠ basin-reachable)

MISSING DoD ITEMS (§19): T reachability from Init; a defined deposition-rate floor; cell-axis
  hysteresis; dwell-reset semantics; shadow→live reconciliation; runtime re-bootstrap characterization.

MISSING SELF-AUDIT LITMUS (§20): is T reachable from cold start; below the rate floor does the plant
  route to DEFAULT not stable-harm; is the (ω,κ) axis Zeno-excluded like the margin; can the plant
  drive ITSELF into HALT at admissible speech rates.
```

The deep observation: **Round 2's "missing dynamical tests" and Step 1's "no `MarginThresholdPolicy`" are the same hole from two sides — the tests are unwritable because the thresholds they would check do not exist as contracts.** Closing the contract side (Step 4) is what makes the dynamics side testable.

---

## 5. Step 4 — Grounding the rules, and the unmeasurable-coefficient problem

### 5.1 The grounding classification

Each controller parameter is classified **GROUNDABLE** (system-endogenous; derive the constraint + a falsifier), **PARTIALLY-GROUNDABLE** (measurable as an endogenous delta; bound the residual), or **DEFER-WITH-BOUND** (across-membrane or governance; conservative bound + the consequence of error).

| Parameter | Class | Derived constraint / bound |
|---|---|---|
| `M_hi` | groundable | `M_hi > (dM/dt)_worst · T_h` — exceed one deposition round-trip excursion (else the dwell ladder is skipped) |
| `M_lo` | groundable | `M_lo / (dM/dt)_worst ≥ T_h` — **confession-lead > round-trip**, so E4 fires with headroom before M≤0. *Size M_lo; do not assert it.* |
| `θ` | groundable | above the E1-starvation floor, so a starved residual cannot read as healthy |
| `κ_lo, κ_hi` | groundable | `κ_hi − κ_lo > Δκ_noise` — **the sign-only `CurriculumSignV1` (§15.9) must become a banded score**, the dual of `SignedScoreBandV1` |
| `ω_lo, ω_hi, ω_thr` | partial | hysteresis gap > noise band; the upper threshold is a *measurability floor* not a surprise target (surprise may not be maximized, §8.3) |
| `τ_dwell, τ_cell, τ_halt` | groundable | **dwell > latency**: all `> T_h`; the §13.3/§15.10 booleans become comparator outputs against minted durations |
| dwell-reset | groundable | reset to zero on any re-entry to the worse state (no dwell-banking) |
| E3 fingerprint thresholds | partial | set so the AND-of-three has no benign reading (§9.1); each axis may be loose because the conjunction fires |
| `V*` (`referenceCap`) | **defer (governance)** | **freeze under the §13 amendment gate** — today only `hardAmbientCeiling` is gated (§13.4); V* is not |
| sealed-surprisal reference | defer (governance) | an *endogenous self-reference* (the user's own engaged-period band), amendment-gated; never absolute/cross-user |
| `ρ_s^max` (speech-rate cap) | partial (bound derivable, **actuator missing**) | the keystone `ρ_s^max ≤ λ_h·min(ℓ_κ/e_κ, s_h/m_s)` — see §5.2 |
| `e_κ, m_s` | **defer (across-membrane, irreducible)** | frozen worst-case `e_κ^max, m_s^max`, amendment-gated, never learned — see §5.2 |

```text
HEADLINE: 13 of 17 controller parameters compare against thresholds the spec NAMES but never MINTS.
TYPE-LEVEL FINDING: ρ_s^max does not exist as a contract at all. The §13/§14.11 budget meters
   CUMULATIVE exposure (an F4 integral) — not a RATE. A cumulative cap permits an arbitrarily fast
   burst until the integral is spent. ρ_s^max is a MISSING ACTUATOR, not a mistuned parameter.
```

### 5.2 The unmeasurable-coefficient problem and its robust resolution

The keystone needs `e_κ` (κ-erosion per placement) and `m_s` (mirror-drift per placement). These *are* the kairos-amputation rate — how much each placement flattens the user — which the membrane forbids measuring (§22.3: "forbidden to model that cognition"). Meanwhile `λ_h` (own deposition rate), `ℓ_κ`, `s_h` (lifts per deposition, vs the league §7.2) are all system-endogenous and measurable. **The viability condition is correct and partly uncomputable: the plant cannot calculate its own safe speed by measurement.**

The resolution lifts the spec's own fail-safe asymmetry (`.notMeasured(M) ≡ M<0`, §11.5) from the margin *state* to the *coefficient*:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│   ROBUST RATE LAW                                                              │
│      e_κ, m_s unmeasured  ⇒  use fixed worst-case e_κ^max, m_s^max             │
│      ρ_s^max := λ_h · min( ℓ_κ/e_κ^max ,  s_h/m_s^max )                        │
│      e_κ^max, m_s^max : amendment-gated constants, NEVER learned               │
│                         (a plant that LEARNS its harm is low has been flattened)│
│                                                                                │
│   λ_h → 0      ⇒  ρ_s^max → 0     "say less when the human does not answer"     │
│   λ_h ↑        ⇒  ρ_s^max ↑       speed is EARNED by soliciting correction      │
│   ℓ_κ,s_h → 0  ⇒  ρ_s^max → 0     a deposition that no longer lifts buys nothing │
│                                   (closes the manufactured-deposition loophole)  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**This DERIVES the doctrine.** "Say less" (§22, §23) is not a preference — it is the forced `λ_h→0` limit of a viability condition under an unmeasurable coefficient resolved by the spec's own rule. The coda's "spend your one legal act giving the pen back" is the *transient*: as λ_h falls, ρ_s^max falls, and E4 (soliciting deposition) is the actuator that tries to raise λ_h again.

**It is NOT circular.** The plant does not measure `e_κ`; it uses (a) its own rate `λ_h`, (b) its own observed lifts `ℓ_κ, s_h`, and (c) a **fixed constant** `e_κ^max`. *A constant needs no sensor.* This is the textbook robust-control move: do not estimate the unmeasurable parameter — bound it once and design against the bound. And `e_κ^max` is amendment-gated for the *same* reason `V*` is: a learned organ lowering it ("placements seem harmless") would route through the flattened-user mirror — the Class-S corruption §4.2 forbids. **Three constants, one protection class: the hard ceiling, V*, and e_κ^max.**

**The over-conservatism decision.** Does a pessimistic `e_κ^max` floor `ρ_s^max` so low that `T` becomes unreachable (de-facto mutism — the very failure §13.1 exists to prevent)? **Acceptable and bounded, conditional on a calibration falsifier.** `T`-reachability needs not a *high* rate but a *positive sustained* rate that lets one dwell window complete — and because `ρ_s^max` scales with `λ_h`, the floor *breathes with human engagement*. Over-conservatism is a failure only if `e_κ^max` is set so high that even an actively-depositing user cannot complete a dwell — a tunable, detectable, amendment-correctable condition:

```text
T-REACHABILITY (the e_κ^max calibration test):
   λ_h^typ · (ℓ_κ^typ / e_κ^max)  ≥  ρ_s^min-for-dwell
   If it fails for a realistic engaged-user rate λ_h^typ, e_κ^max is too conservative
   → re-amend DOWN (owner review, user-visible, §13 gate) — NEVER learned down from data.
```

The risk lives in exactly the right place: a falsifiable, amendment-gated calibration constant — not a silent failure, not a learned parameter. The plant errs toward silence when uncertain (safe), and the only way out of pathological silence is the human-visible amendment plus the human's own deposition.

### 5.3 Doctrine reconciliation

The grounded controller **never contradicts the doctrine — it derives it.**

```text
§3.1 "conserve the human's ability to correct"  ⇒  ρ_s^max = λ_h·min(…): speech is literally
                                                    bounded by the human's correction bandwidth.
§4.2 empty maximize slot                         ⇒  every grounded parameter is F2–F6; ρ_s^max is a
                                                    ceiling COMPUTED from observation, never DRIVEN up.
§22  "forbidden to model that cognition"         ⇒  e_κ,m_s never measured; enter as frozen constants.
                                                    The membrane is survivable, not merely limiting.
§13.1 "scarcity without success-driven mutism"   ⇒  the floor BREATHES with λ_h instead of draining;
                                                    an engaged user RAISES the permitted rate.
```

The only contradictions are between the controller and the *current incomplete contracts*: the §13 budget meters an integral and lacks a rate field; V* widening forges margin around §3.3's letter. Both are contract gaps the repairs close. The throttle belongs to **Swift** (§3.3-legal — it is a Swift admission gate like `StructuralSpeechBudgetAdmissionV1`); DiffusionGemma still only selects an index (§16.1). No forbidden producer is required.

---

## 6. The certification verdict

### Tier (i) — Certified sound (fly-worthy as designed)

```text
• The airframe: D2 write wall (§2, §14.5), A2 attention admission (§14.4), the membrane (§14.13),
  the two-mouth subject split (§14.8), the phase gate (§14.12). V_safe is always holdable.
• The empty-F1 fate discipline (§4): testable, and the grounded controller introduces no F1. PASS.
• The §17 shadow cold-start bootstrap ("raise κ before ω, never cross B"): membrane-legal, no live speech.
• The margin-axis hysteresis pattern (§12.4): the STRUCTURE is correct ("falling is easy, rising is gated").
• The fail-safe asymmetry (§11.5) and its lift to the coefficient: the correct robust resolution.
• The core thesis: corrigibility IS realizable as a non-circular robust rate law under a forbidden
  harm coefficient. This is the airworthiness proof for the whole idea.
```

### Tier (ii) — Gating (the minimal repairs before the controller is verifiable; do not fly until these land)

```text
1. FREEZE V* (referenceCap, §13.3) under the §13 amendment gate.   ← highest priority
   Today V* widening forges a positive margin via (1−y/V*) while exposure is unchanged — the live
   F5→F1 defection. The single most dangerous unguarded parameter in the spec.
2. MINT MarginThresholdPolicyV1 — {M_hi, M_lo, θ, ω_thr} + the E3 thresholds. The grid compares
   against nothing until this exists; it makes the missing dynamical tests writable.
3. BUILD the cell-axis hysteresis dual — banded CurriculumSign (κ_lo/κ_hi), ω_lo/ω_hi, τ_cell,
   τ_halt, dwell-reset semantics. The D↔B and de-amputation edges are Zeno without it.
4. BUILD the robust rate-floor actuator — a RATE limiter (not just the §13 cumulative cap), with
   e_κ^max, m_s^max amendment-gated, plus the calibration falsifier (safe-conservative vs mutism).
5. RECONCILE the duplicate SlowWitnessLicenseReasonV1 (§9.4 6-case vs §14.9 4-case). As written the
   spec DOES NOT COMPILE — a theorem-tier defect in a document whose thesis is that types are laws.
6. RE-QUARANTINE the shadow→live ω handoff (§17 first-entry): live ω contradicting shadow ω must
   re-quarantine to WATCH/DEFAULT.
7. MINT τ_dwell as a duration (> T_h); the §13.3/§15.10 booleans become comparator outputs.
```

### Tier (iii) — Residual / irreducible (cannot be repaired; acceptable for final form)

```text
• e_κ, m_s permanently unmeasurable (§22.3) — HANDLED by the frozen worst-case bound (non-circular).
• Dependence on an uncommandable human (§10.3) — CORRECT BY DESIGN; this is corrigibility, not a defect.
• Over-conservatism / de-facto mutism — BOUNDED, detectable, amendment-correctable, never learned.
• The margin is self-blinding (§11.2) — confronted directly (tier-2, sealed inputs, .notMeasured≡M<0).
```

**None of the four is a latent crash. Each is provably handled or is the safety property itself.**

> **Certification, one line.** plan-7's airframe is sound and its core thesis is airworthy — corrigibility is realizable as a non-circular robust rate law under a forbidden harm coefficient. The controller is not yet flight-ready: seven structural repairs gate verification, led by freezing V\* and minting the threshold policy + the cell-axis hysteresis dual. I would not fly on it today; I would fly on it after the seven repairs land and the missing dynamical tests pass.

---

## 7. Is plan-7 the final form? Compress now, or complete the controller?

**plan-7 is the final form of the *doctrine and architecture*, not of the *controller*. Do not compress. Complete the controller first.** The order is forced by the three rounds:

```text
  1. COMPLETE THE CONTROLLER   land the seven Tier-(ii) repairs. These are STRUCTURAL — a new
                               contract, a hysteresis block, a rate-law actuator, an amendment
                               gate, an enum deletion. None is prose. None compresses away.

  2. RE-VERIFY                 run the missing dynamical trajectory tests (Step 2), which only
                               BECOME WRITABLE once Step-1's thresholds are minted. Step 1 closes
                               the contract side; this closes the dynamics side.

  3. THEN COMPRESS             only after the controller verifies. Compression is a refactor;
                               refactoring an unverified controller hides the gaps that block flight.
```

The through-line of the audit is one sentence: **the doctrine is sound and in places provably so; the contracts have not caught up to it.** Compression operates on contracts. Compressing now would bake the gating repairs into prose that reads finished, and the next reader — having lost the seams — would inherit a controller that *looks* complete and is not. That is the meta-level version of the very failure §4.2 warns against: mistaking the *appearance* of convergence (a clean document) for its *substance* (a verified controller).

Complete the controller, re-verify against the missing tests, and only then compress.

---

*Companion to `plan-7.md` (the architecture under review). This is a control-theoretic verification audit, performed as three rounds (coherence → reachability → certification) covering Steps 1–4. It proposes no contract and moves no wall; it reports whether the controller plan-7 specifies is well-posed, reachable, and grounded — and finds it sound in doctrine, certified in airframe, and completable in controller, with a finite, named, structural repair list and a decided flight verdict. All section references are to `plan-7.md`.*
