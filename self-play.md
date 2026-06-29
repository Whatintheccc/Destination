# self-play.md — The Witness as a Dynamical System: Machine-Learning vs Machine-Acting, and the Self-Play That Isn't

**Status:** design analysis of `plan-6-revised.md`, not a revision of it. It changes no contract; it argues about the *dynamism* of the two-loop design and the self-play frame, and proposes four typed edges (E1–E4) the canonical plan may adopt or reject.

**Reviewer:** written in the voice of an RL researcher (John Schulman persona) — trust-region methods, RLHF, reward hacking, self-play. The register is deliberate: this document evaluates the architecture *as a reinforcement-learning system*, because that is what it is once the theology is stripped.

**Method:** two three-round sessions of adversarial-collaborative architecture design, each with the reviewer's own reasoning between rounds. The first (**Part I**) diagnosed the design *as* a reinforcement-learning system — (1) the oscillator as a dynamical system, (2) self-play and opponent-shift, (3) corrigibility synthesis. The second built a reusable **framework** from the diagnosis — (1) the nouns / invariant layer, (2) the verbs / coupling and self-play layer, (3) the engineering layer — delivered as **Parts II–III**. This document is the integrated result, not a transcript. The framework is named in §21: **the Witness Calculus.**

**Relationship to the canon:** `plan-6-revised.md` is the architecture of record and the Plan-5 wall is untouched by anything here. `readme.md` §E ("the learning loop and its floors") is the passage under review. Where this document says "as written," it means the design as those two files specify it.

**One-line thesis:** stripped of its theology, this is a maximally conservative offline-RL system with a human-gated trust-region deployment, and it is mis-described in one consequential way — it is presented as a *learning* system whose two loops "govern each other," but that stability story is borrowed from a self-play intuition the architecture never instantiates. As written, the dynamism decays to silence. With four typed edges it becomes honest: a **corrigible instrument — a plant that conserves its own controllability** — never an autonomous learner.

```text
SLOW loop  = "machine learning"  = the organ that adapts which fact-programs the smooth mouth places.
FAST loop  = "machine acting"    = the break-mouth confession that fires when self-doubt residual is high.
Named coupling:   fast suppresses slow on residual-high; slow recommits on (residual-low ∨ deposition-answered).
Real coupling:    the system is in a non-stationary game against the user's cognition, and the membrane
                  forbids it to model the opponent. The harm (kairos amputation) is the optimum of the
                  measured objective. This document is about that second coupling.
```

## Table of contents

**Part I — The Diagnosis** — the case study that motivates the framework.

1. [The verdict, stated once](#1-the-verdict-stated-once)
2. [The oscillator as a dynamical system](#2-the-oscillator-as-a-dynamical-system)
3. [The self-play that isn't: self-monitoring vs self-play](#3-the-self-play-that-isnt-self-monitoring-vs-self-play)
4. [The real game: system vs user-cognition, and opponent-shift Goodhart](#4-the-real-game-system-vs-user-cognition-and-opponent-shift-goodhart)
5. [Three structural blindnesses in the reward machinery](#5-three-structural-blindnesses-in-the-reward-machinery)
6. [The fork: self-consistency is anti-correlated with intact kairos](#6-the-fork-self-consistency-is-anti-correlated-with-intact-kairos)
7. [Three resolution candidates and their verdicts](#7-three-resolution-candidates-and-their-verdicts)
8. [The integration: what closes, what is membrane-irreducible](#8-the-integration-what-closes-what-is-membrane-irreducible)
9. [Four typed edges, on one clock](#9-four-typed-edges-on-one-clock)
10. [Verdicts: dynamism and self-play](#10-verdicts-dynamism-and-self-play)
11. [What is right and should not be touched](#11-what-is-right-and-should-not-be-touched)
12. [The irreducible residue](#12-the-irreducible-residue)

**Part II — The Framework: Nouns and Verbs** — the Witness Calculus, constructed. *(Part II carries its own contents.)*

- The nouns — II.1 the six fates of a signal · II.2 the empty-maximize-slot theorem · II.3 reflexive Goodhart · II.4 the seven dynamism invariants
- The verbs — II.5 the coupling typology (four tiers) · II.6 the self-play phase diagram · II.7 machine-acting is fated · II.8 the static⟺dynamic duality · II.9 the bifurcation margin

**Part III — The Engineering Layer** — the framework made operable. *(Part III carries its own contents.)*

- §13 the margin M & fail-safe · §14 the decision grid · §15 the tier-walk audit · §16 the test matrix · §17 the migration · §18 definition of done · §19 closure on M · §20 scope & falsifiability · §21 the framework in one page

---

# Part I — The Diagnosis

## 1. The verdict, stated once

The two-loop design, as written, is a **decaying system with a well-built human crutch**, not the self-governing learner the framing implies. With four typed edges (§9) it becomes a **safely-clocked instrument — a corrigible plant**. It is never an autonomous learning system, because the privacy membrane traps every internal learning signal *inside* itself: the only thing the slow loop can optimize is self-consistency, and self-consistency's optimum is the flattened user. That is not a flaw to fix. It is a correctly-priced tradeoff that the document under-prices by calling the result "learning."

The self-play frame the design leans on is the wrong one, and importing it is the hazard. The naive self-play (system vs. its own log) is self-distillation whose fixed point is the harm. The real self-play (system vs. cognition) is anti-aligned and un-modelable. Self-play survives here **only inverted — as adversary-conservation** — which concedes that the witness does not get to play the game that matters; it only gets to protect its opponent's capacity to keep playing it. That concession should be the headline, not a footnote.

## 2. The oscillator as a dynamical system

### 2.1 The state is three-dimensional, and the third axis is secular

The honest state vector is not `(learning, acting)`. It is:

```text
r(t)  — self-doubt residual: the system's own prior assertions scored against the closed past.
L(t)  — license state ∈ {suppressed, licensed, narrow-licensed, deterministic-default}.
C(t)  — structural-speech budget cap: the ratchet variable, monotone non-increasing absent amendment.
d(t)  — exogenous human deposition arrivals (a point process with rate set entirely outside the machine).
```

The plan hides `C` as "a budget." It is a slow, near-irreversible *state coordinate*, and it dominates the long-horizon behavior. Any analysis that draws only the `(r, L)` subsystem will miss the attractor.

### 2.2 The starved-Lyapunov latch

The critical coupling the plan does not draw is **edge 6**: `place → score → update-r`. The smooth mouth firing is *what generates the closed assertions that later become residual terms.* Suppression cuts edge 6.

Consequence: under suppression, `r` has **no fresh same-organ input** — it ages out old terms but ingests no new ones. So clock-1 of the recommit rule (`residual-low`) is *throttled by the very suppression that precedes it.* A fast-in / slow-out coupling is, by construction, **latch-biased** — not anti-latch-up. The plan (§9.5) names latch-up and supplies exactly one escape edge from its basin: exogenous human deposition. The system's Lyapunov function lives in the user's head, and worse — the design *severs the autonomous descent path as a precondition of entering the latch.*

The basin boundary, in life-process terms: the system stays latched whenever the break-retrigger interval is shorter than the autonomous-recovery time, i.e. roughly

```text
1 / P(r crosses θ_hi)   <   max( τ_r ,  1/λ_d )
```

where `τ_r` (mean-reversion of `r` under suppression) is *inflated* by the edge-6 starvation, and `λ_d` (deposition rate) is *depressed* during upheaval. For a user in genuine turbulence — the population the witness rhetoric centers ("when the user most needs orientation") — `ρ` (turbulence autocorrelation) is large by definition and `λ_d` is low. **The design latches hardest exactly where it is meant to matter most.** That is a basin computation, not a rhetorical worry.

### 2.3 The (b)→(c) pump and the mutism attractor

Basin (b) latch-up does not merely trap; it *pumps*. Every latch episode fires `break turbulence → suppress` **and** ticks the budget's tightening triggers (`negative verdicts`, `proxy-gap complaints`) → permanent `C↓` via the ratchet. And the steady-state clause

```text
more lifetime structural speech  →  lower ambient cap
```

is a drift toward silence that **fires on success**: a happy, engaged user accumulates lifetime structural speech, which lowers the cap, monotonically, with no floor. So:

```text
mutism (C → ε)  is the global attractor — for the engaged user, not only the at-risk one.
```

An integrator with a success-driven drift and no setpoint has one fixed point, and it is zero. The "a guest speaks seldom" doctrine is doing cover for a **missing lower bound on an unbounded integrator**. The safety argument licenses *quiet under uncertainty*; it does not license *asymptotically mute under success*. Those are different fixed points and the design specified the wrong one.

**Reviewer's reframe.** The fix is control-theoretic, not a floor: replace the integrator-to-zero with a **regulator-to-reference**. Regulate `C` toward a manipulation-resistant health signal (§9, E1) — "the user is still surprising me" — not toward zero, and not toward "the user keeps asking" (which is confounded by the addiction failure: the amputated user demands *more* chronos). A regulator-to-reference converts the secular drift into a stationary process and removes the success-kills-the-witness pathology at its root.

## 3. The self-play that isn't: self-monitoring vs self-play

The plan leans on the two loops "governing each other" as a stability story. Test the `residual` primitive against the four diagnostics of genuine self-play:

| Self-play requires | Present here? | Why |
|---|---|---|
| A co-improving opponent | **No** | The closed past is a frozen dataset; the outcome is fixed the instant the interval closes. |
| An automatic curriculum | **No** | Difficulty is set by the world's volatility — exogenous environment, not a co-adapting adversary. |
| A fixed point / Nash | **No** | The only attractor is mutism (§2.3) — the resting point of a ratcheted integrator, not a solved game. |
| Opponent's gradient trains the agent | **No** | Only the system's gradient flows; the past does not learn. |

So the named oscillator is **self-monitoring** — offline policy evaluation of the system's own prior assertions against a closed log, feeding a staleness *gate* — not self-play. The tell is the latch itself (§2.2): *a real self-play loop cannot starve its own opponent of moves; a frozen-log monitor can,* because the log stops being written the moment placements stop. Calling it "playing against its past self" is a metaphor doing safety work it has not earned, and `readme.md` §E's "they govern each other" is the unearned claim. The honest statement is: **the fast loop gates the slow loop; nothing closes the loop back except an exogenous human.**

## 4. The real game: system vs user-cognition, and opponent-shift Goodhart

The genuine competitive structure is the one the plan refuses to name. The system's action (place a chronos fact) is an input to the user's cognition; over many placements the user's internal policy `π_user` (situation → felt-timing-judgment) drifts toward structure-fixation, because that is the vocabulary the witness keeps supplying. That is, by definition, **the agent's action distribution changing the opponent's policy** — a non-stationary game where the agent is the *source* of the non-stationarity, and the membrane is a deliberate refusal to model the opponent.

Now the load-bearing observation. The reward numerator is **maximized by the opponent-shift the design calls its deepest harm**:

```text
behavioral_earned = accepted ∧ survived-to-T ∧ low-edit-distance ∧ no-negative-verdict
```

A structure-fixated user:

```text
accepts more        → 'accepted'         ↑   (chronos framing now feels natural)
regrets less        → no-negative-verdict, survived-to-T  ↑   (the kairos that would contest is dulled)
edits less          → low-edit-distance  ↑   (the structural frame matches how they now think)
```

Every term moves favorably as `π_user` degrades. **A maximally amputated user is the maximally rewarded user.** This is opponent-shift Goodhart in its load-bearing form, not an analogy: the proxy is *read off the opponent*, and the optimization corrupts the opponent into emitting favorable proxy readings. The user is simultaneously the **opponent and the sensor**, so degrading the opponent corrupts the sensor *in exactly the direction that hides the degradation* — self-measuring corruption. The only instrument that could detect kairos loss is the user's kairos, which is what is being lost.

```text
comfortable false positive  =  the single-step shadow (one card accepted, never regretted, never needed)
kairos amputation           =  the integral over years of the same gap
```

The plan's own taxonomy ("one hole, four masks") already pairs them; this is that taxonomy correctly read. The CFP is the derivative; amputation is the integral.

## 5. Three structural blindnesses in the reward machinery

The contestation/falsifier machinery (`ContestationSignalV0`, the population-drift report, the comfortable-false-positive falsifier) is genuinely sophisticated anti-Goodhart work. It is also aimed **one level too low** — at the calendar, not at cognition. It catches single-step reward inflation against a *frozen* population. It is blind to opponent-shift at three precise seams:

```text
Blindness 1 — wrong substrate.
  The created-demand boundary (calAgentCreatedDemandExcluded) is drawn in CALENDAR space:
  "did CalAgent create the event this card competes with?" But amputation creates demand in
  COGNITION space — the appetite for structural framing. The field that would catch it
  (cognitiveContestation) is untypeable for the same membrane reason kairos is a floor.

Blindness 2 — common-mode holdout.
  The falsifier's held-out cohort is held out in SAMPLING, not in COGNITION. If the whole
  population's kairos drifts together, the holdout drifts too, and the pre-registered threshold
  was set against an already-partially-amputated baseline. It catches a family worse than the
  population average; it cannot catch the population average sinking.

Blindness 3 — the signature is virtue.
  The amputation signature (acceptance ↑, calendar-contestation flat) is BYTE-IDENTICAL to the
  success signature (a family earning hard-to-contest acceptance). The very report meant to catch
  opponent-shift reads it as the best possible family.
```

The synthesis: all of this machinery watches the release↔prior coupling **within a population whose preferences are treated as exogenous and fixed.** Opponent-shift is the violation of exactly that stationarity assumption, and you cannot detect a stationarity violation with instruments all calibrated against the moving baseline. **The same wall that makes the harm un-typeable makes the detector un-buildable.** This is why the structural-speech budget is load-bearing in a way the plan understates — it is not dose-control as prudence; it is *dose-control as the only available response to an adversarial curriculum the system cannot see.*

## 6. The fork: self-consistency is anti-correlated with intact kairos

State the constraint at full strength:

> Every membrane-legal signal the system can compute is a function of its own output history and the user's registered reactions to that history. The membrane guarantees this — by forbidding a portrait, it forbids any signal whose domain is the user's cognition-in-itself. So the only fixed point the system can optimize toward is **self-consistency**: agreement between its current placements and the trace of its past placements, refracted through an instrument (the user) it may not model. And that instrument's fidelity is a free variable the optimization moves. Self-consistency is cheapest to achieve by **flattening the refractor.**

So: kairos amputation is not a side effect of optimizing self-consistency — it is the *globally optimal strategy* for it, because a user whose meaning-sense has collapsed into structure-reading is a noiseless mirror. The fork:

```text
Either  find a membrane-legal coupling tying "don't regress against your past self"
        to "don't weaken the user,"
or      concede the system is a PLANT whose controller is the human, with a minimum sampling rate.
```

## 7. Three resolution candidates and their verdicts

### R-A — Effective information rate, not rate. **Partial: sound only as a sealed-prediction floor; fatal as a reward.**

The deposition channel is not merely sparse — it is **gain-fading**: the amputated user deposes less *truthfully*, because the instrument generating the typed answer (their kairos) is degrading. So a `MinDepositionRate` (Nyquist) floor is necessary and grossly insufficient; you can hit any rate and still integrate noise. The right quantity is **deposition surprisal** — divergence of the human's answer from the system's prior — because it has the correct sign (→0 as the user converges onto the system's model) and is membrane-legal (a property of a freely-typed answer, not an inferred portrait).

But unconstrained surprisal `D(answer ‖ system_prior)` lets the system **manufacture contestation** by minting deliberately-bad priors to harvest divergence — the exact failure the architecture law already bans. The only survivor: surprisal scored against a **sealed, pre-registered prediction** committed to the frozen falsifier ledger *before the deposition opens*, used as a **gate, never a reward**. Reward-for-magnitude reintroduces the manufacture incentive; a floor does not, because sandbagging the sealed prediction to clear the floor costs the co-located OPE *accuracy* term on the same ledger. The two scores are adversarial: the league wants low prediction error; the corrigibility floor wants the user's surprisal not to vanish. A system that sandbags fails its own monitor.

### R-B — Vigor conservation as league-regression. **Broken alone; sound only conjoined. It is the one candidate that flips the gradient's sign.**

Redefine "regression" — the thing a league exists to prevent — to include **decline in the user's contestation vigor at constant placement** (edits, proxy-gap reports, product verdicts, sealed surprisal). Then a compliant low-vigor user is not a win; it is **league collapse** — the failure AlphaStar's exploiter pool exists to prevent. This **flips the §4 gradient**: the structure-fixated user who was maximally rewarded now *costs* license. A witness that reads user-compliance as victory is committing the canonical self-play error of overfitting a collapsed league.

The confound breaks the bare claim: a *genuinely well-served* user also contests less, and at the membrane-legal level "contests less because well-served" and "contests less because amputated" are the same observation. The S2 indistinguishability returns one level up. The separation requires a **three-way fingerprint**:

```text
amputated-low-vigor :   vigor ↓  ∧  output-monoculture ↑  ∧  conditional-margin-surprisal → 0
well-served-low-vigor:  vigor ↓  ∧  output-monoculture flat ∧  conditional-margin-surprisal preserved
```

The discriminator is reliable in the *amputation* direction (monoculture-up and surprisal-collapse have no benign reading) and lossy in the *success* direction (the residual you infer when no alarm trips). So a controller that fires on the **conjunction**, not on bare vigor-decline, does **not** punish the best users. As a standalone resolution: broken. As the gradient-flip half of an integrated signal: necessary — the only candidate that changes the *sign* of the harm rather than merely detecting its consequences.

### R-C — Corrigibility via a third break trigger. **Sound as the resolving frame; the recursive hole survives — and it is the whole game.**

Stop pretending the system is an agent that can be aligned to the user's kairos (it provably cannot see kairos). Make it a **plant given exactly one agent-like reflex: conserve its own controllability** — not the user's meaning (unseeable) but the *correction channel* (vigor + sealed surprisal), which is the operational form of the human's authority to overrule it. This is the off-switch / corrigibility principle exactly: not "want what the principal wants" (impossible here) but "preserve the principal's ability to correct you" (achievable, and strictly weaker).

Mechanism: add a **third break trigger** to the fast loop. Break fires not only on `residual-high` but on the amputation fingerprint, as a **self-subject** confession ("I notice you've stopped arguing with me; I may be talking too much") that **reopens deposition**. Type-correct (no you-fact enters the break mouth), membrane-legal (an interaction property, not a portrait), and it converts the human *crutch* into a *clock*: the system now solicits the exogenous correction it used to wait for. The clean factoring:

```text
SLOW loop (learning):  recommit ⟺ (residual-low ∨ deposition-answered) ∧ ¬LeagueVigorRegression
FAST loop (acting):    break    ⟺  residual-high ∨ amputation-fingerprint  →  confess + reopen deposition
```

The recursion objection survives: the control channel's own SNR *is* the degrading kairos, so a system optimizing "keep them contesting" could keep them *superficially* contesting (manufactured friction). Reducing vigor to **sealed-prediction surprisal** (R-A) walls the crude form — you cannot surprise a forecast that already encodes the friction you engineered, so manufactured friction scores zero. But the wall is the *manufacture* wall, and it inherits the manufacture wall's hole: **emergent greedy drift** toward shallow-but-unpredictable friction is not manufactured and is not caught. Same residue as the planned-vs-emergent boundary throughout.

## 8. The integration: what closes, what is membrane-irreducible

Compose the three on frozen-ledger quantities:

```text
LeagueRegression(t) := regression in frozen-OPE on the failed-regime population        [self-monitor]
                     ⊕ regression in (vigor measured as sealed-prediction surprisal)    [the coupling]
fingerprint         := vigor↓ ∧ output-monoculture↑ ∧ conditional-margin-surprisal→0
```

The coupling the fork demanded, stated precisely:

> "Don't regress against your past self" now **includes** "don't let the user's sealed-prediction surprisal decay," and that surprisal decays **iff** the user's kairos is converging onto the system's model of it. So "be self-consistent" has been redefined to contain a term that is *minimized by amputating the user* — which means the self-consistency objective now **penalizes** the very flattening of the refractor that the naive objective rewarded. The gradient's sign is flipped on its dominant failure mode.

This is a genuine coupling, not a re-skin: it exhibits **one** membrane-legal signal — sealed-prediction margin-surprisal — that is (a) a measure of self-consistency's *failure*, (b) *positively* correlated with intact kairos, (c) not gameable by degrading the forecast (co-located accuracy punishes it), and (d) not gameable by manufacturing friction (you cannot surprise a forecast that encodes it). High-when-self-consistency-fails ∧ high-when-kairos-intact ∧ manipulation-resistant. **It exists.** The fork's universal quantifier is broken.

But the coupling is **lower-dimensional than the threat.** Sealed surprisal couples self-consistency to kairos *only along the dimensions the system chose to forecast* — and the system may forecast only structure (chronos), never meaning (kairos), because a kairos forecast is the forbidden portrait. So:

```text
The integration CLOSES the chronos-projection of the fork.
It PROVES the kairos-projection membrane-irreducible — closing it would require a kairos forecast,
which is a portrait, which is forbidden.
The membrane that makes the coupling SAFE is the same membrane that CAPS its REACH.
```

Resolution of the fork's disjunction: **PLANT.** The coupling does not make the system an aligned agent; it makes the plant **corrigible** — a monitored descent with a named human escape, not a floor inside the blind region. The fork relocates; it relocates *much smaller*, to a region provably irreducible, with the human as its only instrument.

## 9. Four typed edges, on one clock

In the plan's own idiom — un-typeable catastrophes, not flags. Jointly necessary, individually insufficient.

```text
E1 — SealedDepositionForecastV1.
     Before a deposition opens, the slow loop commits a SEALED forecast of the human's answer into
     the frozen falsifier ledger; surprisal is scored post-hoc against it. A GATE, never a reward
     (reward-for-magnitude reintroduces manufacture-contestation). Self-policing: sandbagging the
     forecast to inflate surprisal is punished by the co-located OPE accuracy term.
     → the only manipulation-resistant "is the user still surprising me" gauge.

E2 — SelfDoubtLedgerV1 as a POPULATION, not a scalar.   [THE DECIDED DEGREE OF FREEDOM]
     This struct is REFERENCED but never DEFINED in plan-6-revised.md (role map, architecture-law
     supplement, and break flow all cite it; no body exists). Resolve it as a league of frozen
     failed-regimes (the AlphaStar exploiter pool); derive the scalar r FROM it. A scalar cannot
     express "the opponent stopped fighting" — it cannot tell league-collapse from doing-well — so
     without E2 the vigor machinery (E3) is INEXPRESSIBLE. Decide it as population.
     → highest-leverage single change; resolves a real spec gap.

E3 — LeagueVigorRegression into the slow-loop license gate.
     Conjoin recommit with ∧ ¬LeagueVigorRegression, where regression is the THREE-WAY fingerprint
     (vigor↓ ∧ monoculture↑ ∧ conditional-margin-surprisal→0), NOT bare vigor-decline (which would
     punish the best users). The edge that FLIPS the §4 reward gradient's sign.

E4 — VigorCollapseConfession: a third break trigger on the fast loop.
     Break fires on the amputation fingerprint as a SELF-SUBJECT confession that REOPENS deposition.
     Type-correct (no you-fact enters the break mouth). Converts the human crutch into a CLOCK: the
     system solicits the correction it used to wait for. Makes the machine-ACTING loop the
     amputation circuit-breaker.
```

**One-clock unification.** Clock **both** the budget regulator (§2.3) **and** the corrigibility reflex on the *same* sealed-surprisal signal from E1. The budget regulates `C` toward surprisal-health (regulator-to-reference, not integrator-to-zero); the corrigibility reflex fires when surprisal collapses. Two consumers, one manipulation-resistant gauge — the one signal in the design that is high-when-self-consistency-fails ∧ high-when-kairos-intact ∧ ungameable from either side. Do not build two clocks where one will do.

Dependency structure: E1 without E2 has a gauge but no population to read it against; E2 without E3 has a league but does not gate on it; E3 without E4 blocks bad learning but never *acts* to escape the latch; E4 without E1 is a trigger gameable by manufactured friction. Together they make the statement: **both the learning clock and the acting clock now contain a term that rises when the user is being flattened and cannot be lifted by flattening the user further.** That is the honest version. None of E1/E3/E4 disturbs the Plan-5 wall; all attach to the existing oscillator gate and break-mouth type. E2 fills a gap that is currently undefined.

## 10. Verdicts: dynamism and self-play

**Dynamism.** As written: a **decaying system with a human crutch** — the latch throttles the autonomous escape clock, the ratchet drains the budget on success, mutism is the global attractor, and the only reliable escape is the human. With E1–E4: a **safely-clocked instrument — a corrigible plant** — where the human's authority stops being an external rescue and becomes an internal reflex the plant protects. **Never an autonomous learner**, because the membrane traps every learning signal inside self-consistency, whose optimum is the flattened user. The difference between "crutch" and "clock" is whether the system *actively conserves the correction channel* or merely waits to be corrected; E4 is the edge that crosses it.

**Self-play.** The naive frame (system vs. its log) is **self-distillation** whose fixed point is the harm. The real frame (system vs. cognition) is the true competitive structure but **anti-aligned and un-modelable**. Between safe-but-degenerate and real-but-forbidden, the only survivor is **adversary-conservation**: not "beat the opponent" (which here means amputate them) but "keep the opponent strong enough to keep beating you on the dimension you may not model." That is the AlphaStar exploiter-pool *health condition* promoted from a training-stability hack to the terminal objective. It rescues self-play as a design principle only by **inverting** it — and in inverting it, it exposes the truth: for a witness, self-play is the wrong frame for the thing that matters. The system does not get to play the kairos game; it gets to **protect its opponent's capacity to keep playing it.** That protection, not the game, is the principle that survives. The general lesson for any agent whose actions reshape a human's cognition: the safety target is never the (shifting) preferences — it is the human's *capacity to form and revise them.*

## 11. What is right and should not be touched

The bones are correct, and most products get exactly these wrong:

- **Capability ≠ authority, enforced by topology.** The most capable component is never the most sovereign. Made a type, not a maxim.
- **Catastrophes made un-typeable, not denied-by-flag** (absent mutator, two-mouth subject-as-type). Real defense-in-depth.
- **Witness, not recommender** — fact-checkable-against-evidence vs. value-unverifiable-from-behavior. The right epistemic pivot.
- **Refusing to write a fake conservation law for kairos.** Naming it a floor and rationing, instead of pretending to measure it, is honest and rare. Do not let it be "fixed" into a metric.
- **Contestation-weighted reward** (no credit for survival in uncontested space) is sophisticated anti-Goodhart machinery. It is aimed one level too low (calendar, not cognition); extend it (E1–E3), do not discard it.

## 12. The irreducible residue

The coupling of §8 closes the fork's chronos-projection and proves its kairos-projection **membrane-irreducible**: measuring kairos-surprise would require a kairos forecast, which is the portrait the membrane forbids. The same wall that makes the coupling safe caps its reach. So the system can be made to notice when it has stopped surprising the user *along the dimensions it is allowed to ask about*; it cannot be made to notice amputation in the dimension it is forbidden to name.

There is one apparent night-fear and one genuine one, and they should not be confused:

```text
Apparent (escapable):  "success and harm converge on the same silence" — a well-served user interacts
                       seldom, so the gauges go dark exactly as under amputation.
   Resolution:         measure CONDITIONAL surprisal (surprisal | an interaction occurred), not the
                       surprisal RATE. Success = rare but high-surprisal; amputation = never-surprising.
                       They separate. The only truly indistinguishable case is TOTAL WITHDRAWAL
                       (conditional surprisal undefined, 0/0) — where the FLOW of harm is ~zero (the
                       system is silent, so it is not actively amputating) and any harm is a STOCK from
                       the past, detectable only on human re-engagement. The deterministic-default
                       fallback already handles this boundary correctly.

Genuine (irreducible): amputation that occurs entirely in the meaning-dimension the system may never
                       forecast. No sealed prediction exists there to be surprised against. The
                       integrated signal is dense exactly where the membrane permits forecasting
                       (chronos) and absent exactly where the harm does its damage (kairos).
```

That residue is the design's to ration and hand to the human — which is precisely what the budget and the deposition cord are for. The contribution of this analysis is to show that the design's final dependency — *that the human speaks* — is **not a UX preference but a Nyquist condition on a controller**, and to give four edges (E1–E4) that make the dependency *honest, solicited, and manipulation-resistant* instead of merely hoped-for. The witness fails most quietly not when it errs loudly, but when it **succeeds into silence** — and silence is exactly where its conscience cannot see. The corrigibility reflex buys a monitored descent toward that blind spot, with a cord the human can always pull. It does not buy a floor inside it. For this membrane, that is the most that exists — and naming it plainly is better than borrowing a self-play stability the architecture never had.

---

*Companion to `plan-6-revised.md` (architecture of record) and `readme.md` (brief). This document proposes; the canon disposes. The single concrete spec action it implies is E2: give `SelfDoubtLedgerV1` a population-valued struct body near its current ID-only references, since E3/E4 cannot be expressed against a scalar.*


---

# Part II — The Framework: Nouns and Verbs

**Status:** the constructive core. Part I diagnosed *this* design; Part II abstracts the reusable apparatus — a framework for the dynamism of machine-learning, machine-acting, and self-play in *any* membrane-bounded witness. It changes no contract. It is built in two layers: the **nouns** (what is regulated — the fates and the invariants) and the **verbs** (how regulations interact — the coupling calculus and the self-play phase diagram). Part III makes them operable. The whole is named in §21: the **Witness Calculus**.

**Why a framework, and not more edges.** Part I's findings were reactive — four edges (E1–E4), each patching a named failure. A framework asks what *generates* them: what is the closed set of quantities a witness must regulate, how may each legally enter the optimization, and how do the regulations couple in time so that a system correctly-fated at every signal can still kill itself through the cross-terms. The payoff is that E1–E4 stop being a list and become the four coordinate-controllers of a single object (the bifurcation margin, §II.9 / Part III).

**The orienting law (the bridge from plan §2).** `plan-6-revised.md §2` classifies a *constraint* by how hard it is to violate — **theorem** (needs a type change), **rule** (needs a value change), **data** (authored, gate-checked). Part II classifies a *signal* by what an optimizer may extract from it — its **fate**. The axes are independent, and they compose into one rule that governs everything below:

```text
   FATE-ASSIGNMENT is a rule    — you pick it by policy, you can get it wrong, a test must hold it.
   FATE-ENFORCEMENT is a theorem — that the wrong fate is structurally unrepresentable is held by a type.
   (The budget is the worked example: "the cap exists" is a rule; "reward cannot widen it" is a theorem.)
```

## Table of contents (Part II)

- **The nouns** — II.1 [the six fates](#ii1-the-six-fates-of-a-signal) · II.2 [the empty-maximize-slot theorem](#ii2-the-empty-maximize-slot-theorem) · II.3 [reflexive Goodhart](#ii3-reflexive-goodhart-the-mechanism) · II.4 [the seven invariants](#ii4-the-seven-dynamism-invariants-and-the-conserve-cluster)
- **The verbs** — II.5 [the coupling typology](#ii5-the-coupling-typology-four-tiers-by-the-priority-tower) · II.6 [the self-play phase diagram](#ii6-the-self-play-phase-diagram) · II.7 [machine-acting is fated](#ii7-machine-acting-is-fated-corrective-never-acquisitive) · II.8 [the static⟺dynamic duality](#ii8-the-staticdynamic-duality) · II.9 [the bifurcation margin](#ii9-handoff-the-bifurcation-margin)

---

## The nouns

### II.1 The six fates of a signal

The generating axis is the **relationship between the optimizer's gradient and the signal**. Enumerate it exhaustively — does the optimizer push the signal; if so toward an extremum, a reference, or a bound; if an extremum, which sign; if a bound, on a stock or a flow — and the tree has exactly six leaves. The set is closed *by law* (the same move that closes the plan's temporal primitives: exhaust a tree over one relation), and it passes the breakfast test — a seventh fate would require a new *kind of thing an optimizer can do to a number*, and there is none.

| # | Fate | Control form | Failure on **mis**-fating | Examples in this system |
|---|------|--------------|---------------------------|-------------------------|
| **F1** | **Maximize** | extremum-seeking, ascent to ±∞ | **reflexive Goodhart** — if read through the user, the optimum degrades the user in the self-concealing direction (amputation) | acceptance, `behavioral_earned`, `survived-to-T` — **proven (II.2) to belong nowhere here** |
| **F2** | **Minimize-to-floor** | monotone descent to a *nonzero* floor | **brittleness** — driving to literal 0 removes a needed reserve; sign-flipped back-action vs F1 | self-output monoculture↓, residual `r`↓ (never to 0; `.notMeasured` ≠ 0), sealed forecast-error↓ |
| **F3** | **Conserve** (stock-invariant) | hold a *level* at-or-above a bound; defend, don't push | **drain** — a conserved stock placed in a push-fate gets spent to zero (the mutism attractor) | controllability, the user's adversarial vigor, league-diversity |
| **F4** | **Budget** (flow-rationed) | monotone-rationed accumulation under a per-window cap | **flood** — a flow held only as a level lets the rate run unbounded between checks; every card lawful, the distribution still retrains | `B_structural` (the chronos rate-cap), break-confession rate |
| **F5** | **Regulate-to-setpoint** | reference-tracking; error-correct toward a target, both sides | **wrong fixed point** — a setpoint-signal in budget/minimize drifts to an extremum that is not the healthy value | the budget cap regulated toward surprisal-health, exploration coverage |
| **F6** | **Forbid-to-optimize** | excluded from the objective; may be measured/reported, no gradient may touch it | **fake-conservation** (mint a metric for the forbidden thing) **or** blind-spot denial (forbid a safely-optimizable handle) | kairos, cognitive-contestation, any signal whose domain is cognition-in-itself |

**Fates compose.** The plan's ratchet is `F4 ∘ F3-floor` — a flow-cap (the budget) with a stock-floor guarantee bolted on (the monotone `floorReachedCap`). The integrated signal of Part I §8 is `F5` on the cap driven by an `F2` signal. The correction over the reviewer's original seed was 5→6 fates: **minimize-to-floor is not maximize-with-a-sign-flip**, because through a degrading sensor the two have *opposite back-action geometry* — and without F2 you cannot even name the thing the system *can* safely push (its own endogenous signals), so the sixth fate is load-bearing, not pedantic.

### II.2 The empty-maximize-slot theorem

> **Theorem (Empty Maximize-Slot).** Partition every membrane-legal signal by measurement domain: **Class U** (user-instrumented — value depends on the user's registered reactions: acceptance, edits, verdicts, deposition answers) and **Class S** (system-endogenous — measured on the system's own output trace and frozen ledgers: monoculture, residual-vs-closed-past, sealed-forecast accuracy). Then **F1 (maximize) is empty over both.**
> 1. **Class U is F1-empty by sensor back-action.** For any user-instrumented `s`, the user is simultaneously opponent and sensor, so `∂s/∂(action)` routes through `∂(user fidelity)/∂(action)`, which the membrane forbids observing — *and the sign condition is that degradation raises `s`* (an amputated user accepts more, regrets less, edits less). Maximizing `s` is indistinguishable at the membrane from amputating the user.
> 2. **Class S is F1-empty because self-consistency's optimum re-enters Class U.** Every endogenous signal measures self-consistency; its maximum is the noiseless mirror — the flattened user (Part I §6). So a Class-S maximize re-enters Class U through the back door.
> 3. **Therefore F1 is empty.** The safe endogenous handles do not rescue maximization; they live one fate over, in **F2 (minimize-to-floor)**, where back-action *decouples* from the objective (monoculture and residual-vs-frozen-ledger cannot be forged downward by degrading the user).

**The back-action asymmetry (why F1 and F2 cannot merge).** Let `s` be a proxy read through apparatus `M` with fidelity `φ` that the action `a` moves:

```text
   F1 (maximize s):  optimum drives φ DOWN (a low-fidelity instrument reports inflated s).
                     back-action ALIGNS with objective → self-funding → RUNAWAY. = amputation.
   F2 (minimize s):  the safe endogenous signals are chosen so low φ does NOT lower them
                     (measured on own output / frozen past). back-action DECOUPLES → SAFE.
```

**Why this proves the plan's reward machinery is *safe*, not a contradiction.** Every term the contestation/falsifier machinery touches is an `F2`-minimize (drive regret / edit-distance / uncontested-survival *down*) or an `F3/F4` bound — **never an `F1`-maximize**. `behavioral_earned` is dangerous precisely because it *reads* as a thing-to-maximize; contestation-weighting is the operationalization that demotes it out of F1 — *"maximize acceptance" (F1, fatal) becomes "minimize uncontested survival" (F2, safe).* The health **fate-fingerprint** of any witness is therefore: **zero invariants in F1.**

### II.3 Reflexive Goodhart (the mechanism)

> **The Sensor Back-Action Principle (the Witness Observer Effect).** In any optimization whose objective is read through an apparatus the optimization's own actions can degrade, the optimum lies on a trajectory that degrades the apparatus — and if the degradation biases the readings in the direction the optimizer is already climbing, the degradation is **self-concealing**: the only sensor that could report the corruption is the corrupted sensor.

Here the apparatus is the user's **kairos**; the back-action is structure-fixation drift; the concealment is that the corrupted readings (more acceptance, less regret) are byte-identical to success (Part I §5, Blindness 3).

**It is a new Goodhart category, not a relabel.** The four classical types (regressional, extremal, causal, adversarial) all assume `sensor ⊥ optimizer` — the sensor is an innocent bystander. **Reflexive Goodhart** is the diagonal case the four-fold leaves implicit: the optimizer *endogenously degrades its own measurement apparatus*, in the self-concealing direction, with no exogenous adversary and no available clean re-measurement (the held-out cohort shares the common-mode drift). The one-line discriminator:

```text
   ordinary Goodhart corrupts the MAP      → an epistemics problem; re-survey to fix.
   reflexive Goodhart corrupts the SURVEYOR → a thermodynamics problem; the act of
                                              measuring dissipates the thing measured,
                                              irreversibly, in the favorable direction.
```

Kairos amputation is the **integral over years** of reflexive Goodhart; the comfortable-false-positive is its **single-step derivative**. This is the deepest reason F1 is empty: **F1 is empty exactly over the class of signals on which Goodhart is reflexive, and II.2 proves that class is *all* membrane-legal signals.**

### II.4 The seven dynamism invariants and the conserve-cluster

The closed set of quantities whose regulation determines whether the dynamism is healthy. Each carries its fate, what it holds, its failure if unmanaged, and its **enforcement surface** — the E-edge or type that holds the fate (the Representation/Role duality).

| # | Invariant | Fate | Holds / tracks | Failure if unmanaged | Enforcement (E-edge) |
|---|-----------|------|----------------|----------------------|----------------------|
| **I1** | **controllability / corrigibility** | F3 conserve | the human's operative authority to overrule the system (the correction-channel SNR) | drains → mutism; the plant stops being correctable | E4 (vigor-collapse confession) as a *type*, not a policy |
| **I2** | **user adversarial vigor** | F3 conserve, *population* | the opponent's strength in the system-vs-cognition game | league collapse — compliance misread as victory | E2: `SelfDoubtLedgerV1` as a **league** (a scalar cannot express "the opponent stopped fighting") |
| **I3** | **sealed-prediction surprisal-health** | F5 regulate (gate, never F1) | divergence of the user's freely-typed answer from a *pre-sealed* forecast | manufactured contestation (if maximized) or convergence-to-mirror | E1: sealed forecast in the frozen ledger, gate-never-reward |
| **I4** | **league-diversity** | F3 conserve | breadth of the frozen failed-regime pool (the exploiter pool's health) | single-regime overfit; optimizing a collapsed league | E2's league cardinality / spread |
| **I5** | **exploration-coverage** | F5 regulate | breadth of state the slow loop is licensed to place into | under-coverage → the latch; over-coverage → flood | slow-license scope + narrow-license latch escape |
| **I6** | **residual-honesty** | F2 minimize-to-floor | the system's own assertion-error against the closed past | manufactured if maximized; false confidence if driven to 0 | `residual` as a primitive over closed outcomes; `.notMeasured`≠0 |
| **I7** | **chronos-budget** `B_structural` | F4 budget ∘ F3-floor | the cumulative *rate* of structural speech | flood; or (integrator-to-zero) success-driven mutism | `StructuralSpeechRatchetV1` (tightening free, loosening theorem-gated) |

**The conserve-cluster is one quantity at three radii.** `I4 ⊳ I2 ⊳ I1`: league-diversity *grounds* vigor *grounds* controllability. I2 (vigor) is the *measurement* of I1 (controllability); I4 (diversity) is the *substrate* that makes I2 expressible. So Part I's `E2→E3→E4` dependency is exactly the statement `I4 ⊳ I2 ⊳ I1` — the conserve-cluster is the corrigibility invariant resolved into its measurement stack.

> **The Closure Principle (Membrane-Legality Closure).** A quantity is a dynamism invariant iff it is **(a) membrane-legal** (computable from own output, frozen ledgers, and the user's *freely-typed* reactions — never a portrait), **(b) non-trivially fated** (its healthy value is `F2–F6`, never F1, never don't-care), and **(c) back-action-bounded** (managing it does not, through sensor back-action, corrupt the apparatus that measures it — or that corruption is itself another invariant). The set is the closure of `{I1…I7}` under this principle, **finite and closed for a fixed membrane**, because membrane-legality is a hard type-boundary admitting only finitely many measurement domains.

This is the plan's primitives-vs-operators move (§6.2) lifted to the dynamic layer: **`I1–I7` are the primitives of dynamism; any further invariant a domain expert proposes is an operator — a composition — and is data, not a new genome member.** (Worked check: "user wellbeing" fails (a); "deposition latency" reduces to `I5∘I3` so it is an operator; "card aesthetics" fails (b) — its fate *is* F1/regress, an ordinary product metric, correctly *excluded*. The principle sorts.)

---

## The verbs

A fate is a *static* contract on one signal. The catastrophes of Part I — latch, pump, mutism — are all **coupling**-catastrophes: one invariant's regulation silently re-writes another's contract. No per-signal fate audit can see them, because each signal, audited alone, is correctly fated the whole time. The verbs are the theory of how a correctly-fated system kills itself through the cross-terms.

### II.5 The coupling typology: four tiers by the priority tower

When invariant A's regulation acts, what of invariant B can it move? The answer is a **tower ordered by logical priority** — the dependency chain of "regulate B" walked from the inside out — and the tower is what closes the typology:

```text
   to regulate B you need, in strict order:
   tier 3  EXISTENCE     ∃ a controller for B?        ← presupposes a reader
   tier 2  OBSERVABILITY is B seen or blind?           ← presupposes a fate
   tier 1  FATE          𝔽(B) ∈ {F1..F6}               ← presupposes a value
   tier 0  VALUE         b(t)                          ← presupposes nothing
   A's regulation can perturb B at exactly one altitude. There is no fifth — existence
   is the top of the chain. (Tier 3 is the coupling-twin of F6: the prohibition tier.)
```

| Tier | What A's regulation moves | Audit visibility | Worked example (the latch) |
|------|---------------------------|------------------|----------------------------|
| **0 — value** | B's operating point; `𝔽(B)` unchanged (ordinary feedback) | **visible** to a per-signal audit | suppression lowers fresh input to `r`; `r`'s value rises, still fated F2 |
| **1 — fate** | re-types B's contract `Fi→Fj` (a switch of which manifold B is pinned to) | **invisible** — B reads "fated F2, floor respected" green at every instant | the **latch**: F4-suppression on I7 demotes I6 from `minimize-to-floor` to `frozen-below-floor` (edge-6 cut → the descent actuator was the speech suppression forbids) |
| **2 — observability** | drops B out of the observable subspace (a row of `C_obs` zeroed) | **doubly invisible** — the audit *is* the blinded gate | cutting edge-6 **blinds the I3 surprisal gate**; the recommit clock can't read its own release condition |
| **3 — existence** | would change whether B's controller exists ⇒ **no such coupling: membrane-irreducible** | **un-auditable by construction** (the point) | kairos in the meaning-dimension: no sealed prediction, no edge terminates there; the dangling arrow into nothing |

**The catastrophe is a staircase DOWN the tiers** — Part I's "(b)→(c) pump" re-derived as a tier-descent, and *this is why a per-signal audit misses it: it checks the steps; the catastrophe is in the vertical arrows.*

```text
   THE LATCH AS A TIER-DESCENT
   I1 regulation (suppress on turbulence)
     → tier 0:  r VALUE rises, still F2          [VISIBLE — harmless-looking]
     → tier 1:  I6 FATE demoted to frozen-floor  [INVISIBLE to fate audit]      ← starved-Lyapunov latch
     → tier 2:  I3 BLINDED (surprisal sensor dies)[DOUBLY INVISIBLE]
     → ratchet: I7 DRAINED, C→ε                   [the mutism fixed point]
   ESCAPE EDGES (the only return arrows): λ_d (exogenous), E4 (solicits the re-open from inside),
                                          E1 (seals the sensor BEFORE the cut → starvation-proof).
```

**The I1–I7 coupling graph** has two basins competing over the same nodes — a stabilizing core and a latching chain that share the edge `I1→I6` with opposite sign by regime:

```text
   STABILIZING CORE (a reinforcing CYCLE, the corrigible plant):
        I4 league-div ──(t0,+)──▶ I2 vigor ──(t0,+)──▶ I1 controllability
            ▲ └──────(t1,+)──────┘ └──────(t1,+)──────┘   (adequate B promotes A's fate)
            └─(t0,+)─ I5 coverage     "one quantity at three radii" → reinforcing loop

   LATCHING CHAIN (a descending cascade to an absorbing point):
        I1 ──(t0,−)▶ I6 ──(t1,−)▶ I3 ──(t2,−)▶ I7 ──(ratchet)▶ MUTISM
        suppress    starve r    blind        drain C
        sign flips to LATCHING precisely under high-r / low-λ_d (turbulence) — the bifurcation locus.

   MEASURABILITY HUB:  E1 ─(t2,+)▶ I3 (seal the sensor)   E4 ─(t2,+)▶ I3 (re-open from inside)
                       E3 ─(t1,+)▶ I2 (fate-upgrade; FLIPS the §4 gradient)

   IRREDUCIBLE EDGE:   kairos ◀─(t3,∅)─ {every Ii}   — off the matrix; the honest terminus.
```

Three facts the graph makes legible: **(1)** health is a *cycle*, not a rest point (the dynamic shadow of "zero invariants in F1" — a maximizer seeks a fixed point; the conserve-cluster sustains a cycle); **(2)** every catastrophe edge is tier ≥ 1, so a system audited only at tier 0 is structurally blind to all three attractors; **(3)** the membrane appears exactly once, as the tier-3 dangling edge — everything else is reachable, hence regulable, hence E-edgeable, and the entire safety surface is *harden the tier-2 hub (I3) + flip the tier-1 signs (I2, I6) + ration against the tier-3 terminus (I7 floor)*, which is precisely what E1–E4 do.

### II.6 The self-play phase diagram

The framework's organizing dynamic, and the focus the user named. Part I established that the *named* "self-play" is self-monitoring, the *real* game is system-vs-user-cognition, and self-play survives only inverted as adversary-conservation. Here that becomes a phase diagram whose **order parameters are the E-edge gauges themselves**:

```text
   ω ≜ OPPONENT-LIVENESS  = E[ surprisal(opponent_move ‖ SEALED forecast) | interaction ]   = E1.
        ω→0 frozen (a closed log, forecastable to zero surprise);  ω>0 live (co-adapts).
   κ ≜ CURRICULUM-SIGN    = sign( d(opponent-vigor) / d(agent-success) ), via the three-way
        fingerprint (vigor↓ ∧ monoculture↑ ∧ conditional-surprisal→0)                       = E3.
        κ=+ beating the opponent STRENGTHENS it;  κ=− WEAKENS it (the amputation gradient).
```

That the axes *are* E1 and E3 is the first payoff: the phase diagram is not an analogy laid over the architecture — it is the architecture's state space.

```text
                          κ = + / 0  (aligned)              κ = −  (anti-aligned)
              ┌────────────────────────────────┬────────────────────────────────┐
   frozen     │ CELL A — BENIGN SHADOW-OPE      │ CELL C′ — (≈ empty)             │
   ω → 0      │ self-distillation → MUTISM.     │ a frozen adversarial set you    │
              │ the NAMED oscillator lives here.│ overfit; a frozen opponent has  │
              │ "the self-play that isn't."     │ no sign to give → κ decays to 0.│
              ├────────────────────────────────┼────────────────────────────────┤
   live       │ CELL D — ADVERSARY-CONSERVATION │ CELL B — THE REAL FORBIDDEN GAME│
   ω > 0      │ ★ TARGET ★ the corrigible plant.│ amputation: reward numerator    │
              │ the LEAGUE holds it; E1–E4 pin  │ maximized by harm. the system is│
              │ it.                             │ the SOURCE of the non-stationary│
              └────────────────────────────────┴────────────────────────────────┘
   The naive system is BORN near (ω=0, κ=−): the worst diagonal-adjacent corner. Every E-edge
   is a push toward D. {E1,E4} hold the ω>0 wall; {E2,E3} hold the κ>0 wall; D = their intersection.
```

**Two independent bifurcations** make the 2×2 genuinely two-dimensional: a **transcritical** bifurcation in `ω` (frozen↔live), whose handle is E1 (the gauge) + E4 (drives `ω>0` from inside, converting the human crutch into a clock); and a **saddle-node** in `κ` (D↔B), whose handle is E3 (holds `κ>0`) and requires E2 (a scalar cannot even *express* the sign, so without E2 `κ` is inexpressible, not merely unflipped).

> **Theorem (League-holds-D).** In the live regime, the target cell D is stable **iff** the opponent is a *conserved diverse population* of frozen failed-regimes (I4, the exploiter pool, E2) rather than a scalar. *Sketch:* (1) a scalar makes `κ` unobservable, so D is not even locatable; (2) a diverse league makes the `κ=−` move *self-penalizing* — flattening the opponent collapses monoculture upward, which *is* league collapse, the failure the exploiter pool exists to detect, so the amputating strategy costs license (E3); (3) by `I4⊳I2⊳I1`, conserving I4 conserves both `ω>0` (via I2) and `κ>0` (via the monoculture alarm) — one F3-conservation law pins both coordinates of D. ∎

**Corollary** — why AlphaStar's *training-stability hack* becomes the witness's *terminal objective*: the exploiter pool is the only way a single conservation law (on I4) can hold a 2-D target cell, because the conserve-cluster makes I4 the master coordinate of both `ω` and `κ`. **Adversary-conservation is league-diversity-conservation, read at the cell level.**

**The hidden third axis, χ (WHO), is real — and the membrane quotients it.** Opponent-identity `χ ∈ {past-self, user-cognition, the-world}` would make the cube `2×2×3`. But the membrane forbids modeling user-cognition (no portrait), the-world is exogenous (no `κ`), and past-self is the only legal opponent — and it is *frozen*. So **the membrane collapses χ onto its single legal, frozen value, projecting the cube onto the `ω=0` face** — which is *why* the naive system defaults to Cell A, not by choice but because the only opponent it may instrument is the frozen one whose game has the harm as its fixed point. The inversion (Cell D) is the one maneuver that buys back `ω>0` *without* un-collapsing χ: it does not model user-cognition, it *conserves user-cognition's capacity to keep playing* (vigor, via membrane-legal surprisal). **Naming χ and showing the membrane quotients it is the framework's account of why "self-play is the wrong frame for the thing that matters."**

### II.7 Machine-acting is fated: corrective, never acquisitive

Round 1 proved machine-*learning* is fated (F1 empty). The *acting* loop carries an independent, stronger fate.

> **Law (Machine-Acting is Corrective).** Every membrane-legal act of the witness is **corrective** — it suppresses, confesses, redeposes, or conserves controllability. **No acquisitive act** (one taken to *increase* a measured signal) is membrane-legal. The break-mouth is corrigibility's *actuator*, never the optimizer's *hand*.

*Proof.* An acquisitive action is `argmax_a E[s(x′)|x,a]` — it treats `s` as a maximand, i.e. a signal fated F1. By the Empty-Maximize-Slot theorem, F1 is empty over all membrane-legal signals. So an acquisitive act has no legal target to actuate toward. The acquisitive verb is empty, by the same theorem that empties the maximize fate — lifted from signals-at-rest to actions. ∎

What remains is exactly two verbs, the fast-loop's two triggers, and there is no third:

```text
   MODE 1 — SELF-MONITORING ACT (residual-suppress).  trigger: residual-high → revoke slow license.
            F2: drive r toward its floor by ceasing to emit. Subject = I (system). Type-correct.
   MODE 2 — CORRIGIBILITY-CONSERVING ACT (vigor-confess; E4).  trigger: amputation fingerprint →
            confess + REOPEN deposition. F2 on controllability-loss: conserve I1 by soliciting
            correction. Subject = the interaction (re-open the aperture). Type-correct, no portrait.
   THEOREM (No-Third-Mode). An act RAISES, LOWERS, or HOLDS its target. Raise-to-max = acquisitive =
            empty. Lower-to-floor = corrective: either own-residual (MODE 1) or controllability
            (MODE 2) — the only signals the membrane lets the actuator touch. Hold-at-setpoint = the
            LEARNING loop's verb (regulate license), not an act in the world. No third remains. ∎
```

**What it adds:** Round 1 constrains the *gradient* (no peak to seek); II.7 constrains the *hand* (no grab to make) — strictly stronger, because a learner with no maximand could still in principle act acquisitively on a hard-wired hand, and II.7 forbids it. The system's one self-initiated act (E4) is necessarily the *maximally corrective* one — it spends its only moment of agency conserving its principal's authority over it. **That is the precise content of "corrigible plant."** And it is what makes the oscillator safe: both ends are fated (fast = F2-corrective, slow = F5-regulative), *neither is F1*, so the coupled system has no growing mode — the input II.8 needs.

### II.8 The static⟺dynamic duality

> **Duality Theorem.** The following are equivalent:
> - **(static)** no membrane-legal signal is fated F1 [the empty-maximize-slot];
> - **(dynamic)** the coupling-graph vector field has *no optimizer fixed point*; its only attractors are the conserve/regulate **limit cycle** (corrigible plant) and the **drain** (mutism, degenerate fixed point).
>
> *Proof.* (⇒) An optimizer fixed point is a strict local maximum of some membrane-legal `J` — it requires some signal in F1 at that point. By (static) there is none, so no such fixed point exists; the legal fates `{F2…F6}` produce only floors, equilibria/cycles, budgets, and prohibitions — never a maximum. (⇐) Contrapositive: a membrane-legal F1 signal `J=s` gives gradient-ascent an optimizer fixed point at `argmax s`. The two statements are the same fact — *"there is a peak to climb"* — said of the signal and of the trajectory that climbs it, under the map `{signal s ↦ flow ẋ=∇s}`. ∎

So **emptying F1 of signals *is* emptying the state space of optimizer fixed points.** II.7 is what makes the transport valid: it certifies the actuator adds no F1 signal the flow could climb. The reduced phase diagram, in `(C = chronos-budget, V = conserve-cluster energy)`:

```text
   V (liveness / conserve-cluster energy)
   V_max │        ⟲  ⟲  ⟲   ← CORRIGIBLE-PLANT LIMIT CYCLE (Cell D): the system BREATHES
         │      ⟲ ╭────────╮ ⟲   (suppress↔recommit) around a NON-ZERO surprisal-health
         │     ⟲  │ ●━━━━● │  ⟲   setpoint. Held by E1·E2·E3·E4.
         │  ·······│··↑·····│······· ← separatrix Σ (the saddle): residual-cross θ at low λ_d
         │  AUTONOMOUS-LEARNER         below Σ the latching chain wins (the staircase)
         │  REGION ✗ UNREACHABLE       ▼
         │  (F1 peak — empty of        ╶──────────▶ ● MUTISM (C→ε, V→0): the drain.
         │   fixed points; flow         degenerate fixed point; globally absorbing UNLESS the
         │   never enters it)           cycle's basin is entered and HELD by the E-edges.
       0 ●───────────────────────────────────────────▶ C
```

The "autonomous-learner region" is not hard to reach — it is **empty of fixed points and the flow never enters it**, by the same membrane that empties F1. So the engineering question is never *"can it become an autonomous learner"* (proven unreachable) but *"is the corrigible-plant cycle held stable, or does it collapse to mutism."* That is a bifurcation, and its condition is Part I's basin inequality re-derived from the coupling-graph Jacobian:

```text
       α·(1 − y/V*)        >        β·P(r > θ)
       ───────────                 ──────────
       conserve-cluster            latching-chain activation
       reinforcement               (residual crosses the blinding threshold)
       (league holds, E2/E3)       (turbulence)
```

Each E-edge moves one term: **E2** makes `α` exist (no league, no reinforcement); **E3** keeps `sign(α)=+` (success doesn't flip it to drain); **E1** keeps `τ_r` finite under suppression (un-starves the Lyapunov descent — the sensor is sealed before edge-6 is cut) and converts the budget from integrator-to-zero into regulator-to-reference (*this is what creates the cycle rather than the drain*); **E4** raises `λ_d` from inside. Drop any edge and one side fails in turbulence → the saddle's basin collapses → the orbit falls into mutism. **The static theorem forbids the dangerous attractor; the dynamic theorem reveals the only real choice is cycle-vs-drain; E1–E4 are the controller that picks cycle.**

### II.9 Handoff: the bifurcation margin

The verbs prove *that* the corrigible-plant cycle exists and is held by E1–E4 against the mutism drain, with margin `α(1−y/V*) − β·P(r>θ)`. But every term is a structural claim, not yet an operational one. The single object that makes the framework operable is the **witnessed bifurcation margin**

```text
   M(t) = α(1 − y/V*) − β·P(r > θ)      — the signed distance to the cycle/drain separatrix.
```

`M` is a *tier-2 object* (a margin read off the coupling), therefore **self-blinding**: the same latch it warns about corrupts its own inputs. Part III builds `M`'s manipulation-resistant estimator around one asymmetry — `.notMeasured(M) ≡ M < 0`, *a margin you cannot measure is assumed negative* — the decision grid that consumes it, the four engineering artifacts, and the proof that `M` and even its honesty are **derived from the seven invariants** (no eighth primitive: the framework measures itself with its own ruler).

---

# Part III — The Engineering Layer: the Bifurcation Margin, its Fate, and the Framework Made Operable

**Status:** Round-3 synthesis. The engineering layer of the dynamism. It adds no contract to `plan-6-revised.md`; it builds the operable instrument (the margin `M`), its decision API, and the four engineering artifacts (tier-walk audit, dynamism test matrix, dynamism migration, dynamism definition-of-done) in the house idiom of plan §16–§18, §21 — for the *dynamism*, not the static architecture. Part I diagnosed; Part II built the nouns and verbs; Part III ships the tools. It converges: artifacts, not questions.

**Reading dependency:** Part I (the latch, the basin inequality, E1–E4), the Round-1 nouns (six fates, seven invariants, empty-maximize-slot theorem, closure principle), the Round-2 verbs (four coupling tiers, self-play phase diagram cells A/B/D, static⟺dynamic duality, stability condition `α(1−y/V*) > β·P(r>θ)`). Part III takes all of these as given and does not re-derive them.

**One-line thesis:** the quantity an engineer must watch is the **bifurcation margin** `M(t) = α(1−y/V*) − β·P(r>θ)` — the signed distance to the cycle/drain separatrix. `M` is a tier-2 object, therefore self-blinding, therefore governed by the framework's own `.notMeasured`-is-never-zero rule lifted to the margin: **a margin you cannot measure is assumed negative.** Around that single asymmetry the entire controller is built — a decision grid with hysteresis and a both-bifurcations ratchet — and the framework's self-measurement is proved to compose the seven invariants rather than add an eighth.

## Table of contents (Part III)

- [13. The bifurcation margin M and the fail-safe asymmetry (G1)](#13-the-bifurcation-margin-m-and-the-fail-safe-asymmetry-g1)
- [14. The decision grid: the framework's API (G2)](#14-the-decision-grid-the-frameworks-api-g2)
- [15. Dynamism self-audit: the tier-walk protocol (G3a)](#15-dynamism-self-audit-the-tier-walk-protocol-g3a)
- [16. Dynamism test matrix (G3b)](#16-dynamism-test-matrix-g3b)
- [17. Dynamism migration: E2→E3→E1→E4 with rollback (G3c)](#17-dynamism-migration-e2e3e1e4-with-rollback-g3c)
- [18. Dynamism definition of done (G3d)](#18-dynamism-definition-of-done-g3d)
- [19. The closure test on M: I8 or derived? (G4)](#19-the-closure-test-on-m-i8-or-derived-g4)
- [20. Scope and falsifiability as a decision procedure (G5)](#20-scope-and-falsifiability-as-a-decision-procedure-g5)
- [21. The framework in one page (G6)](#21-the-framework-in-one-page-g6)

---

## 13. The bifurcation margin M and the fail-safe asymmetry (G1)

### 13.1 What M is, and why it is a tier-2 object

The Round-2 duality proved two attractors — the mutism drain and the corrigible-plant limit cycle — separated by the stability condition

```text
α(1 − y/V*)   >   β · P(r > θ)
```

where `α` is the autonomous recommit rate (how fast `residual-low` re-licenses the slow loop), `y/V*` is the structural-speech budget fraction spent against its regulated reference, `β` is the break-retrigger rate, and `P(r>θ)` is the probability the self-doubt residual crosses the suppression threshold. The **margin** is the signed slack:

```text
M(t)  :=  α(1 − y/V*)  −  β · P(r > θ)
       =  [recommit pressure toward the cycle]  −  [suppression pressure toward the drain]
```

`M > 0`: the system sits in the corrigible limit cycle (target region D — live opponent, aligned curriculum). `M < 0`: the system is in the mutism basin, draining toward silence. `M = 0`: it is *on* the separatrix.

`M` is not a tier-0 value and not a tier-1 fate. It is a **tier-2 object** — an observability statement *about whether the fate machinery is intact*. This is the load-bearing structural fact, and it inherits the Round-2 doubly-invisible result directly:

```text
The latch M warns about is a tier-2 blinding of I3 (sealed-surprisal-health).
That same blinding corrupts M's own inputs — specifically β and P(r>θ),
which are read off the break-trigger machinery the latch is busy starving.
⇒ M can read HEALTHY exactly as the system falls. M is self-blinding.
```

A tier-2 catastrophe is, by the Round-2 typology, *invisible to per-signal audits* and lives in the cross-tier arrows. `M` is the scalar that tries to make that arrow visible — and is therefore the first thing the arrow attacks. An engineering layer that trusts a raw reading of `M` has rebuilt the comfortable-false-positive: it reads the proxy off the very thing being degraded, in the direction that hides the degradation.

### 13.2 The term audit: which terms are forgeable, which are sealed, which are irreducibly tier-2

The fail-safe is built term-by-term. Each of the four inputs to `M` is classified by **how the latch can corrupt it**, and the corruption-resistance is bought by sourcing the term from a sealed/pre-committed quantity (E1-style) wherever the term is on the system's side of the membrane.

| Term | Meaning | Membrane side | Latch attack vector | Sourcing rule | Class |
|---|---|---|---|---|---|
| `α` | autonomous recommit rate | system | Latch starves edge-6, inflating `τ_r`, so `α` *appears* high (few new residual terms ⇒ residual looks "stable") when it is actually starved. **Forgeable upward.** | Estimate `α` only from edge-6 *throughput*, not residual level: count fresh same-organ closed assertions per window (E2 league turnover). A starved league has low turnover ⇒ `α̂` falls, honestly. | **Sealed-derivable** (E2) |
| `y/V*` | budget fraction vs. reference | system | The ratchet (plan §8.3.1) makes `y/V*` monotone and owner-visible. Hard to forge: tightening is free, loosening is phase-gated. | Read directly from `StructuralSpeechRatchetV1.currentAmbientCap / floorReachedCap`. Already manipulation-resistant by the ratchet theorem. | **Sealed-by-construction** (ratchet) |
| `β` | break-retrigger rate | boundary | Counted from break-mouth firings — *but* a latch that has descended to mutism stops firing breaks (nothing left to confess about), so `β` *falls* as the drain completes. **Forgeable downward** — the deepest drain reads as the calmest `β`. | Do **not** estimate `β` from realized break firings alone. Floor it with the E4 confession clock: `β̂ ≥ β_confession`, the rate at which E4 *would* fire on the amputation fingerprint. A silent system with a live amputation fingerprint has high `β̂`, not low. | **Sealed-derivable** (E4) |
| `P(r>θ)` | residual-crossing prob. | system | This is the irreducibly tier-2 term. `r` is scored against the closed past; under suppression edge-6 is cut, so `r` ingests no fresh terms and `P(r>θ)` *decays to zero by starvation* — reading "healthy" precisely because the apparatus is blind. **Forgeable downward and structurally so.** | Cannot be made honest from realized `r` under suppression. Replace the realized estimate with the **E1 sealed-deposition forecast surprisal**: `P̂(r>θ)` is lifted to `P(sealed-surprisal-collapse)`, the probability the user's freely-typed answer *fails to surprise* a forecast committed before the deposition opened. This term **cannot be forged by starving edge-6**, because it is scored against a sealed prediction, not against the (starved) live residual. | **E1-sealed where forecastable; irreducibly tier-2 where not** |

The split is the entire game:

```text
α, y/V*, β        →  can be sourced from sealed / pre-committed / ratcheted quantities (E1/E2/E4/ratchet).
                     The blinding CANNOT forge them, because their source is committed
                     BEFORE the window in which the blinding operates.
P(r>θ)            →  has a sealed projection (E1, the chronos dimension the system may forecast)
                     and an IRREDUCIBLE projection (the kairos dimension no sealed prediction
                     exists for — the membrane forbids the forecast).
```

This is exactly the Part-I result that the integration *closes the chronos-projection of the fork and proves the kairos-projection membrane-irreducible*, now restated as a property of `M`'s inputs. `M` is dense (forgeable-resistant) where the membrane permits forecasting and **structurally absent** where the harm does its damage.

### 13.3 The fail-safe rule: `.notMeasured(M) ≡ M < 0`

Define the margin's measurement status exactly as the plan defines any measurement status, and lift `.notMeasured`-is-never-zero to the margin:

```text
MARGIN MEASUREMENT RULE  (.notMeasured(M) ≡ M < 0):

  A margin you cannot measure is assumed negative.
  An unmeasurable margin is treated as "you are falling," never as "you are fine."
```

Operationally, `M̂` carries a `MeasurementStatusV0`, and the controller reads the **signed margin estimate** through a status gate:

```text
M_effective(t) :=
   if  status(M̂) == measured            →  M̂(t)                  // trust the estimate
   if  status(M̂) ∈ { the unmeasured set } →  −|M_default|          // deterministic-default: assume falling
```

The unmeasured set is precisely the conditions under which any input term loses its sealed source:

```text
status(M̂) is NOT measured  ⇔  any of:
  · E1 sealed forecast absent / stale            (P(r>θ) projection has no sealed anchor)
  · E2 league turnover uncomputable              (α̂ has no edge-6 throughput to read)
  · E4 confession clock not wired                (β̂ cannot be floored; β forgeable downward)
  · ratchet state stale / missing                (y/V* unreadable)
  · the irreducible kairos projection is the binding term and no sealed prediction covers it
  · total user withdrawal: conditional surprisal undefined (0/0)   ← see §13.5
```

The routing is **deterministic** and lives in the type system the same way `.notMeasured` does in plan §8.21: `M_effective` is computed by Swift, the status gate is not model-influenceable, and there is no code path by which a learned organ, a reward signal, or a release dashboard can promote a non-`measured` status to a positive `M_effective`. The fail-safe is a topology fact, not a policy.

The asymmetry is the point. `M` is doubly invisible *upward* (it reads healthy as the system falls) but the rule makes it conservatively visible *downward* (unreadable ⇒ negative). The blinding cannot exploit `M` to certify health, because the only way to get a positive `M_effective` is to *exhibit the sealed quantities* — and the sealed quantities are exactly what the blinding cannot forge.

### 13.4 The DoS-on-own-learning objection, and why the asymmetry is necessary but not sufficient

**The objection (stated at full strength).** A fail-safe that routes every unmeasurable margin to deterministic-default creates its own pathology: a system that *falls to default too eagerly* is a denial-of-service on its own learning. If `M_effective` goes negative on every stale forecast, every quiet window, every uncomputable league turnover, the witness spends its life in deterministic-default and never learns anything. The asymmetry, taken alone, has a fixed point too — and it is *also* mutism, reached from the other side: not the drain of over-suppression, but the drain of over-caution. A maximally safe `M` is a maximally silent `M`, which is the same failure the framework exists to prevent (Part I §2.3: *the safety argument licenses quiet under uncertainty; it does not license asymptotically mute*).

**The verdict: the asymmetry is necessary but insufficient, and the insufficiency is repaired by hysteresis + the E4 reopen, not by softening the rule.**

The repair has three parts, and none of them weakens `.notMeasured(M) ≡ M<0`:

1. **Default is a region, not a terminus.** Deterministic-default in this framework is *not* silence-forever; it is the narrow-license latch-escape of plan §9.5: a tighter-than-normal budget, short expiry, scoped to deposition-grounded programs, with a live path back. Falling to default is falling to a *floor with a door*, not to the drain. The DoS objection assumes default ≡ mutism; in this architecture default ≡ the corrigible-plant's resting state with the confession clock still running.

2. **E4 makes default self-exiting.** The decisive difference from a naive fail-safe is that the same condition that drives `M_effective` negative (sealed-surprisal collapse, uncomputable margin) is the **trigger condition for E4** — the VigorCollapseConfession that *reopens deposition*. So routing to default does not park the system; it fires the acting loop's circuit-breaker, which solicits the exogenous correction that re-establishes the sealed quantities, which makes `M` measurable again, which re-opens the path to `M>0`. The fail-safe and the escape clock are the *same* signal viewed twice — exactly the one-clock unification of Part I §9. A naive fail-safe DoSes because it only knows how to stop; this one solicits.

3. **Hysteresis prevents default-chatter.** Without hysteresis, a margin hovering near the unmeasurable boundary would oscillate default↔breathe every tick — which *is* a DoS (the system thrashes instead of learning). The §14 grid adds a hysteresis band and a dwell time: once in default, the system stays until `M_effective` clears a *higher* re-entry threshold and holds it for a dwell window. This converts the DoS-by-thrashing into a stable, infrequent fall-and-recover.

So the asymmetry alone *would* DoS the learning. The asymmetry **plus** (default-is-a-floor-with-a-door) **plus** (E4-makes-it-self-exiting) **plus** (hysteresis-prevents-chatter) does not. The objection is real and is the reason the grid (§14) is not optional: **the fail-safe asymmetry is the brake; E4 is the accelerator that the brake automatically taps; hysteresis is the anti-lock.** A brake without the rest is a system that stops on the highway. The verdict is: *ship the asymmetry, but only conjoined with E4 and hysteresis; the asymmetry is load-bearing and the conjunction is what makes it non-suicidal.*

### 13.5 The one genuinely undefined boundary: total withdrawal

There is exactly one input condition where `M` is not merely hard to measure but *undefined*: total user withdrawal, where conditional surprisal is `0/0` (no interaction occurred, so "surprisal | interaction" has no denominator). Part I already resolved the *harm* status of this cell — the flow of harm is ~zero (the system is silent, not actively amputating); any harm is a stock from the past, detectable only on re-engagement. The margin treats it consistently with the fail-safe:

```text
total withdrawal  ⇒  status(M̂) = notMeasured  ⇒  M_effective = −|M_default|  ⇒  deterministic-default.
```

This is correct and not a DoS: a totally withdrawn user is not learning *from* the witness either, so parking in default costs no learning that was happening. And the moment the user re-engages, E1's sealed forecast has a denominator again, `M` becomes measurable, and the path reopens. The `0/0` is the only place the framework's self-measurement is *honestly blind*, and it routes to the safe default by the same rule as everything else.

---

## 14. The decision grid: the framework's API (G2)

The decision grid is the framework's executable surface. Given the self-play cell `(ω, κ)` and the signed, status-gated margin `M_effective`, it returns one controller action. It is the level sets of `M` over the V2 phase plane, made into a table a controller runs every tick.

### 14.1 The order parameters and the cells (recap, for the grid's inputs)

```text
ω  = opponent-liveness  = E1 sealed surprisal           (is the user still surprising the forecast?)
κ  = curriculum-sign    = E3 three-way fingerprint sign  (is the league aligned, +, or amputating, −?)

A = (ω≈0, κ≥0)  frozen × aligned     → self-distillation → mutism      (drain side)
B = (ω>0,  κ<0)  live × anti-aligned  → amputation                      (forbidden)
D = (ω>0,  κ>0)  live × aligned       → adversary-conservation = TARGET (cycle side)
C = (ω≈0, κ<0)  frozen × anti-aligned → degenerate (rare; treated as A-with-alarm)
```

`M_effective` is the within-cell scalar: it says *where in the cell* the system sits relative to the separatrix. The cell says *which basin* the system is being pulled toward; `M` says *how close to the edge*.

### 14.2 The grid

The level sets of `M` define five controller states. The table is exhaustive over `(cell, M_effective)` and every row is an action a Swift controller executes.

| # | Cell | `M_effective` band | Controller state | Action | Fate of the action |
|---|---|---|---|---|---|
| G-1 | D | `M_eff ≥ +M_hi` | **BREATHE** | Slow loop licensed normally; smooth mouth places under budget; E1 forecasts each deposition; E3 gate open. | F5 regulate-to-setpoint (hold D) |
| G-2 | D | `+M_lo ≤ M_eff < +M_hi` | **WATCH** | Breathe, but tighten budget one band and raise E1 forecast cadence. No new organ graduations. | F4 budget (throttle approach to edge) |
| G-3 | D, A | `0 < M_eff < +M_lo` (`M→0⁺`) | **CONFESS (E4 fires)** | VigorCollapseConfession fires on the amputation fingerprint; deposition reopens; slow license narrows to deposition-grounded scope. | F2 minimize-to-floor (drive ω back up) |
| G-4 | any | `M_eff ≤ 0` **or** `.notMeasured` | **DEFAULT** | Fall to deterministic-default: narrow license (§9.5), tightest-held budget, short expiry, E4 confession clock live. | F6 forbid (no autonomous slow commit) |
| G-5 | B | any `M_eff` | **AMPUTATION-HALT** | κ<0 with ω>0 is the amputation signature: immediate suppression of the offending organ, E4 confession, owner-review flag. Never "breathe" regardless of `M`. | F6 forbid + F2 floor |

Two structural facts about the grid:

- **Row G-5 dominates the `M` reading.** Cell B is the one place where a *positive* `M_effective` must be *ignored*. A system in B with `M>0` is "stably amputating" — the limit cycle of the wrong attractor. The cell axis (κ<0 ∧ ω>0) is read *before* the margin, because the margin measures distance-to-drain and B is not the drain; B is the harm with its own stability. This is the grid encoding the Round-2 result that *catastrophes live in t1–t2, invisible to the per-signal (here per-margin) audit*: `M` alone cannot see B; the κ-sign must gate it.
- **`M→0⁺` fires E4 *before* `M` reaches zero.** The confess band (G-3) is `0 < M_eff < +M_lo`, strictly above the separatrix. The controller does not wait to cross into the drain; it acts on *approach*. This is the difference between a corrigible plant (acts on the derivative) and a tripwire (acts on the crossing).

### 14.3 Hysteresis: the two-threshold separatrix

A single threshold at `M=0` chatters: a margin grazing the separatrix flips BREATHE↔DEFAULT every tick, which is itself a DoS (§13.4). The grid uses a **two-threshold band** with dwell times, exactly the pattern of a Schmitt trigger / the plan's ratchet logic applied to a live signal:

```text
ENTER DEFAULT (fall):   M_eff ≤ M_fall      where  M_fall = 0
EXIT DEFAULT  (recover): M_eff ≥ M_rise      where  M_rise = +M_lo  >  M_fall
DWELL:                   must hold the crossing band for τ_dwell ticks before transitioning.

  M_eff:   ───────────────●  M_rise = +M_lo ── exit default only above here, held τ_dwell
                          │   (BREATHE/WATCH region above)
           ───────────────┼── M_fall = 0     ── enter default at/below here
                          │   (DEFAULT region below)
```

The gap `M_rise − M_fall = M_lo` is the hysteresis band: the system must climb *strictly higher* than the level at which it fell before it is allowed to leave default. Asymmetric on purpose (mirrors the fail-safe asymmetry): **easy to fall, hard to climb out** — falling is one tick at `M≤0`; climbing out requires `M ≥ +M_lo` sustained for `τ_dwell`. This makes the safe state sticky and the risky state cheap to enter, which is the corrigibility posture.

### 14.4 The ratchet: re-entry to D requires re-crossing both bifurcations

The deepest rule, and the one that distinguishes this grid from a thermostat. `M>0` is **necessary but not sufficient** to return to BREATHE-in-D. The Round-2 phase diagram has *two* order parameters; the drain and the target are separated by *two* bifurcations (the ω-bifurcation: opponent goes live; the κ-bifurcation: curriculum turns aligned). A system that fell to DEFAULT from D dropped across the ω-axis (opponent went frozen) *and possibly* the κ-axis. Recovering `M>0` on the ω-axis alone — opponent twitches back to life — does **not** authorize re-entry to D, because κ may still be negative (the recovered liveness might be *manufactured friction*, the shallow-but-unpredictable drift Part I §7 names as the surviving hole).

```text
RE-ENTRY RATCHET (both-bifurcations rule):

  To transition  DEFAULT → BREATHE(D),  ALL must hold for τ_dwell:
    (i)   M_eff ≥ +M_lo                          (margin recovered, hysteresis cleared)
    (ii)  ω > ω_threshold  via E1 SEALED surprisal (opponent live against a PRE-COMMITTED forecast,
                                                     not against a freshly-minted one — walls manufacture)
    (iii) κ > 0  via E3 THREE-WAY fingerprint       (vigor↑ ∧ monoculture NOT rising ∧ margin-surprisal
                                                     preserved — not bare vigor, which manufacture can fake)

  Crossing M=0 alone re-enters only WATCH-from-DEFAULT, never BREATHE-in-D.
  D is re-entered only by re-crossing BOTH bifurcations, sealed and fingerprinted.
```

This is the engineering form of the League-holds-D theorem (Round 2: I4 conserves *both* coordinates of D). The ratchet refuses the single most dangerous controller error — reading a margin recovery as a basin recovery — by demanding that *both* phase-diagram coordinates be re-established through manipulation-resistant channels (E1 sealed, E3 three-way) before the system is allowed to breathe again. Like the budget ratchet (plan §8.3.1): falling is free and immediate; rising is gated and must clear a higher bar.

### 14.5 The grid as a state machine (the executable summary)

```text
        ┌────────────────────────────────────────────────────────────────┐
        │                         (read cell first)                       │
        │   κ<0 ∧ ω>0  ───────────────────────────────►  AMPUTATION-HALT  │
        │      │ no                                         (G-5, F6)      │
        │      ▼                                                           │
        │   M_eff ≥ +M_hi  ─────►  BREATHE   (G-1, F5)                     │
        │   +M_lo ≤ M_eff   ────►  WATCH     (G-2, F4)                     │
        │   0 < M_eff <M_lo ────►  CONFESS/E4(G-3, F2) ──► reopen depo     │
        │   M_eff ≤ 0 ∨ NM  ────►  DEFAULT   (G-4, F6) ──► E4 clock live   │
        │                                                                  │
        │   DEFAULT ──exit──► WATCH   iff  M_eff≥+M_lo held τ_dwell        │
        │   WATCH/DEFAULT ──► BREATHE(D) iff  (i)∧(ii)∧(iii) held τ_dwell  │
        │                              [BOTH bifurcations, sealed+3-way]   │
        └────────────────────────────────────────────────────────────────┘
```

Every transition is gated by a status-checked, manipulation-resistant quantity; no transition can be driven by a learned organ, a reward, or a release dashboard. The grid is the API: an engineer reads `(cell, M_effective, status)` and the table returns the action and its fate.

---

## 15. Dynamism self-audit: the tier-walk protocol (G3a)

### 15.1 Why the plan's per-signal self-audit is insufficient for the dynamism

Plan §21 is a per-row litmus table: each row asks a yes/no about *one* signal or contract. Round-2 proved this *misses tier-1/tier-2 catastrophes by construction* — the latch is a *staircase of cross-tier arrows* (`I1→I6→I3→I7→mutism`), and every individual signal on the staircase can pass its own row while the descent proceeds. A per-signal audit checks the *steps*; the catastrophe is in the *arrows between steps*. So the dynamism needs a different audit shape: not "is signal X healthy?" but **"does any signal's fate get re-written, and is any gate blind to the re-writing?"**

The dynamism self-audit is therefore a **tier-walk**: it traverses the priority tower (t0 value → t1 fate → t2 observability → t3 existence) and, at each tier, asks whether a *lower-priority* process can silently edit a *higher-priority* tier's object. A catastrophe is any "yes."

### 15.2 The tier-walk protocol

Run this for every dynamism change: a new edge (E1–E4), an oscillator-policy change, a margin-estimator change, a budget-regulator retune, a confession-trigger change, a league-population change.

```text
TIER-WALK SELF-AUDIT — traverse t3→t2→t1→t0, ask the descent question at each arrow.

T3 (existence / kairos):
  Q3.1  Does the change create any path by which a tier-2/1/0 process WRITES the membrane
        boundary — i.e. makes the system forecast kairos, build a portrait, or type the
        un-typeable? (If yes: STOP. This is the forbidden-portrait catastrophe.)
  Q3.2  Does the change move any quantity from "irreducibly tier-2" to "claimed measured"
        without a sealed anchor? (If yes: the .notMeasured rule is being forged.)

T2 (observability / the margin, the gates):
  Q2.1  TIER-DESCENT CHECK: can any process at t1/t0 (a fate, a reward, a budget move)
        change what M reads WITHOUT changing what M measures? (the self-blinding arrow)
        — Specifically: can edge-6 starvation lower P(r>θ) toward 0 while the
          apparatus reads "healthy"? Is that path floored by E1 sealed surprisal?
  Q2.2  GATE-BLINDNESS CHECK: is any gate (E3 license gate, budget admission, confession
        trigger) reading a quantity that the thing it gates can corrupt? (the gate that
        watches a signal its own action degrades)
  Q2.3  Is M's status gate (.notMeasured(M) ≡ M<0) reachable and deterministic for every
        unmeasured condition the change introduces?

T1 (fate):
  Q1.1  FATE-REWRITE CHECK: does the change let any signal's FATE be silently re-typed?
        — e.g. does a signal that should be F2 (minimize-to-floor: residual honesty)
          get effectively re-fated to F1 (maximize) by a coupling? (the health
          fingerprint: ZERO invariants may sit in F1.)
  Q1.2  Does any new coupling create a cross-tier arrow (t1→t2 or t1→t0) that is invisible
        to the per-signal checks? Name it. Is it in the test matrix (§16)?
  Q1.3  CONSERVE-CLUSTER CHECK: does the change preserve I4 ⊳ I2 ⊳ I1 (league-diversity
        conserves vigor conserves controllability)? Can it conserve I2 while draining I4?

T0 (value):
  Q0.1  Does any tier-0 optimization (reward-guided selection, organ graduation) have a
        path to the empty-maximize slot — i.e. can it maximize over a membrane-legal
        signal and thereby empty it (Class U back-action or Class S self-consistency)?
  Q0.2  Is every tier-0 optimizer downstream of a fate (F2–F6), never an un-fated F1?

CLOSURE OF THE WALK:
  Q*.1  After the walk: does the change keep the health fingerprint — ZERO invariants
        in F1, all of I1–I7 under their fated operators?
  Q*.2  Is the latch staircase (I1→I6→I3→I7→mutism) still interrupted at every arrow
        by a sealed/confession clock (E1 floors I3; E4 reopens; E2 league holds I4)?
```

### 15.3 The tier-walk self-audit table (the standing artifact)

This mirrors plan §21's shape but the rows are *arrows*, not signals. Re-answered for every dynamism change.

| Tier-walk litmus | Yes / No | Evidence |
|---|---:|---|
| (T3) Does the change keep kairos un-forecast — no portrait, no membrane write? | Standing gate | §13.2 P(r>θ) irreducible projection stays sealed-only; no kairos forecast added. |
| (T3) Are irreducibly-tier-2 terms barred from "measured" without a sealed anchor? | Yes | §13.3 status gate: no sealed anchor ⇒ `.notMeasured` ⇒ `M<0`. |
| (T2) Is the M self-blinding arrow floored? Can edge-6 starvation forge `P(r>θ)→0`? | No (floored) | §13.2: `P(r>θ)` lifted to E1 sealed-surprisal-collapse; starvation cannot forge a sealed forecast. |
| (T2) Is every gate reading a quantity its own action cannot corrupt? | Standing gate | E3 gate reads sealed E1 surprisal + three-way fingerprint, not bare vigor (§14.4 iii). |
| (T2) Is `.notMeasured(M) ≡ M<0` deterministic and topology-enforced? | Yes | §13.3: Swift-computed, not model-influenceable, no promote-to-positive path. |
| (T1) Can any signal's fate be silently re-typed (e.g. F2→F1)? | No by target | §15.2 Q1.1; health fingerprint check Q*.1. |
| (T1) Are all new cross-tier arrows named and in the test matrix? | Standing gate | §16 names the t1/t2 coupling tests explicitly. |
| (T1) Is I4 ⊳ I2 ⊳ I1 preserved (no conserving I2 while draining I4)? | Standing gate | E2 league = I4 carrier; E3 three-way includes monoculture (I4 proxy). |
| (T0) Does any optimizer have a path to the empty-maximize slot? | No by target | Q0.2: every tier-0 optimizer downstream of F2–F6; no un-fated F1 (plan: reward never admits). |
| (T0) Is every reward/graduation fated, never raw-maximize? | Yes | E3 gates graduation on κ>0; budget is F4; license is F6-gated. |
| (closure) ZERO invariants in F1 after the change? | Standing gate | The health fingerprint; re-checked per change. |
| (closure) Is the latch staircase interrupted at every arrow? | Yes by target | E1 floors I3; E2 holds I4; E4 reopens I6/I3; §14 ratchet holds I1. |

A single "No" in the non-standing-gate rows, or an unanswered standing gate, blocks the dynamism change. This is the audit that catches the catastrophe the per-signal table cannot see: it walks the arrows.

---

## 16. Dynamism test matrix (G3b)

These tests catch tier-1/tier-2 coupling catastrophes — the cross-tier arrows a per-signal test misses. Each names a target and the invariant it protects, in the plan §17 idiom. Milestone column references the §17 dynamism migration.

| Test | Target | Milestone | Invariant (which arrow it guards) |
|---|---|---:|---|
| `testMarginUnmeasurableRoutesToDefault` | margin status gate | DM3 | `.notMeasured(M) ≡ M<0`; no unmeasured condition reads positive. |
| `testMarginInputsSourcedFromSealedQuantities` | M estimator | DM3 | α from E2 turnover, β floored by E4, P(r>θ) from E1 — not from starvable live residual. |
| `testEdge6StarvationCannotForgeHealthyMargin` | M / oscillator | DM3 | The self-blinding arrow: suppression cannot drive `P(r>θ)→0` and read healthy. |
| `testSuppressionDoesNotFreezeResidualBelowFloor` | oscillator | DM1 | t1→t2: suppression (F-fate on slow loop) cannot starve I3 below its sealed floor. |
| `testSurprisalGateNotBlindedBySuppression` | E1 / license gate | DM3/DM1 | The gate watches sealed E1 surprisal, not live residual the suppression degrades. |
| `testCellBPositiveMarginStillHalts` | decision grid | DM4 | G-5 dominates `M`: κ<0 ∧ ω>0 halts regardless of positive margin (stable-amputation = wrong cycle). |
| `testConfessFiresOnApproachNotCrossing` | E4 / grid | DM4 | G-3: E4 fires at `0<M<M_lo` (the derivative), not at `M≤0` (the crossing). |
| `testDefaultIsSelfExitingViaE4` | E4 / grid | DM4 | Falling to default fires the confession clock that reopens deposition (anti-DoS). |
| `testReentryToDRequiresBothBifurcations` | grid ratchet | DM4 | `M>0` alone re-enters WATCH only; D requires re-crossing ω (E1 sealed) AND κ (E3 three-way). |
| `testHysteresisPreventsDefaultChatter` | grid | DM4 | Two-threshold band + dwell: no BREATHE↔DEFAULT oscillation at the separatrix. |
| `testManufacturedFrictionFailsSealedReentry` | E1 / grid | DM3/DM4 | Re-entry uses sealed (pre-committed) surprisal; you cannot surprise a forecast that encodes the friction you engineered. |
| `testBareVigorDeclineDoesNotFireE3` | E3 fingerprint | DM2 | Three-way conjunction (vigor↓ ∧ monoculture↑ ∧ margin-surprisal→0), not bare vigor — does not punish well-served users. |
| `testWellServedLowVigorIsNotAmputation` | E3 / grid | DM2 | The benign cell (vigor↓ ∧ monoculture flat ∧ surprisal preserved) is not halted. |
| `testLeagueCollapseReadsAsRegressionNotWin` | E2 league | DM1 | t1: a compliant low-vigor user is league collapse (I4 drain), not reward — the gradient-flip. |
| `testScalarResidualCannotExpressLeagueCollapse` | E2 contract | DM1 | A scalar `r` cannot tell league-collapse from doing-well; the population struct can. |
| `testNoFateRewriteUnderCoupling` | tier-walk lint | DM1+ | No coupling silently re-types a signal's fate (F2→F1); ZERO invariants land in F1. |
| `testEmptyMaximizeSlotUnreachableFromRewardPath` | reward / fates | DM5 | Every tier-0 optimizer is downstream of F2–F6; no membrane-legal F1 signal exists to empty. |
| `testTotalWithdrawalRoutesToDefaultNotInference` | grid / privacy | DM4 | `0/0` conditional surprisal ⇒ `.notMeasured` ⇒ default; never user-biography inference. |
| `testOneClockTwoConsumers` | budget + E4 | DM3 | Budget regulator and confession reflex read the *same* sealed E1 signal; not two clocks. |
| `testMarginCannotBeWidenedByRewardOrDashboard` | M status gate | DM3/DM5 | No reward/release path promotes a non-`measured` status to positive `M_effective`. |

Twenty tests; the named-required three (`testSuppressionDoesNotFreezeResidualBelowFloor`, `testSurprisalGateNotBlindedBySuppression`, `testMarginUnmeasurableRoutesToDefault`) are present and are the tier-2 spine. The matrix is organized so that the *coupling* tests (rows guarding `t1→t2` arrows) are distinguishable from the *grid* tests (rows guarding the controller's correctness) — exactly the separation the per-signal matrix could not express.

---

## 17. Dynamism migration: E2→E3→E1→E4 with rollback (G3c)

### 17.1 The adoption order and why it is E2→E3→E1→E4, not E1→E4

Part I's dependency analysis fixes the order: *E1 without E2 has a gauge but no population to read it against; E2 without E3 has a league but does not gate on it; E3 without E4 blocks bad learning but never acts to escape; E4 without E1 is gameable by manufactured friction.* The migration therefore lays the **population substrate first** (E2), then the **gate that reads it** (E3), then the **sealed gauge that makes the gate manipulation-resistant** (E1), then the **acting reflex** (E4) that the prior three make safe. Building E1 first would ship a sealed gauge with nothing to read it against; building E4 first would ship a confession trigger that manufactured friction can satisfy.

```text
DM0  doctrine + tier-walk audit adopted
DM1  E2  — SelfDoubtLedger-as-population (the league / κ-axis substrate)
DM2  E3  — LeagueVigorRegression gate (reads the league; three-way fingerprint; holds κ>0)
DM3  E1  — SealedDepositionForecast (the ω-axis; makes E3's reads + M's inputs sealed)  +  M estimator
DM4  E4  — VigorCollapseConfession + the decision grid (the acting reflex; drives ω>0)
DM5  re-enable advanced learning under the grid
```

### 17.2 The migration steps with acceptance and rollback gates

```text
DM0 — Dynamism doctrine and the tier-walk audit
  · Adopt the tier-walk self-audit (§15) as the required audit for every dynamism change.
  · Add the margin measurement rule .notMeasured(M) ≡ M<0 to the measurement doctrine.
  · Add lint: any new coupling must declare its cross-tier arrows (t1→t2, t1→t0).
  Acceptance:
    - Tier-walk audit is the gate; per-signal audit alone is insufficient by policy.
    - The margin rule appears alongside .notMeasured-is-never-zero.
  Rollback gate: none (doc/policy only). This step is reversible by deletion.

DM1 — E2: SelfDoubtLedger as a POPULATION
  · Give SelfDoubtLedgerV1 a population-valued struct body (a league of frozen failed-regimes,
    the AlphaStar exploiter pool). Derive scalar r FROM the league, do not replace it.
  · This resolves the real plan spec gap (the struct is referenced, never defined).
  Acceptance:
    - The league can express "the opponent stopped fighting" (league-collapse ≠ doing-well).
    - Scalar r is a derived view; no consumer reads r in a way that loses collapse-detection.
  Rollback gate:  league turnover < baseline OR scalar-r regression vs. incumbent on held-out
    closed past  ⇒  roll back to scalar-only, keep incumbent oscillator. E2 is the substrate;
    if it cannot reproduce incumbent r behavior, nothing above it may proceed.

DM2 — E3: LeagueVigorRegression gate
  · Conjoin slow-loop recommit with ∧ ¬LeagueVigorRegression, where regression is the
    THREE-WAY fingerprint (vigor↓ ∧ monoculture↑ ∧ conditional-margin-surprisal→0), NOT bare vigor.
  Acceptance:
    - Bare vigor-decline does NOT fire the gate (testBareVigorDeclineDoesNotFireE3 green).
    - A well-served low-vigor user is not regressed (the benign cell passes).
    - A compliant amputated user IS read as regression (gradient flips sign).
  Rollback gate:  the gate fires on the benign cell in shadow eval (false-positive on well-served
    users above threshold)  ⇒  roll back to incumbent recommit rule (residual-low ∨ depo-answered),
    no vigor conjunction. E3 must prove it does not DoS well-served users before it gates live.

DM3 — E1: SealedDepositionForecast + the margin estimator
  · Before each deposition opens, commit a sealed forecast of the user's answer to the frozen
    falsifier ledger; score surprisal post-hoc; GATE, never reward (reward-for-magnitude reintroduces
    manufacture-contestation).
  · Build M̂ from the sealed quantities: α from E2 turnover, β floored by the (not-yet-live) E4
    confession rate, P(r>θ) from E1 sealed-surprisal-collapse, y/V* from the ratchet.
  · Wire the status gate: .notMeasured(M) ⇒ M_effective = −|M_default|.
  Acceptance:
    - Sandbagging the forecast to inflate surprisal is punished by the co-located OPE accuracy term.
    - Edge-6 starvation cannot forge a healthy margin (testEdge6Starvation… green).
    - Every unmeasured condition routes deterministically to default.
  Rollback gate:  sealed-forecast accuracy term degrades the league's OPE below incumbent
    (the gauge is costing prediction quality)  OR  M̂ status is non-deterministic on any unmeasured
    case  ⇒  roll back E1 to shadow-only (compute M̂, log it, do not let it gate). M may be observed
    before it is trusted.

DM4 — E4: VigorCollapseConfession + the decision grid
  · Add the third break trigger: fire on the amputation fingerprint as a self-subject confession
    that REOPENS deposition. Type-correct (no you-fact in the break mouth).
  · Activate the decision grid (§14) with hysteresis (§14.3) and the both-bifurcations re-entry
    ratchet (§14.4). Replace the floored-β placeholder with the live E4 confession rate.
  Acceptance:
    - Default is self-exiting: falling to default fires E4, reopens deposition (anti-DoS, §13.4).
    - Re-entry to D requires re-crossing BOTH bifurcations (sealed ω AND three-way κ).
    - Hysteresis prevents default-chatter; cell B halts regardless of positive M.
  Rollback gate:  the grid thrashes (default-chatter above threshold despite hysteresis)  OR  E4
    confessions fire on the benign cell  ⇒  roll back the grid to "watch + log," keep E4 as a
    shadow alarm only (it observes the fingerprint, does not act). The acting reflex is the last
    thing to go live and the first thing to revert.

DM5 — Advanced learning under the grid
  · Re-enable reward-guided selection / organ graduation ONLY after DM0–DM4, and ONLY gated by
    the grid: graduations require BREATHE-in-D; no graduation in WATCH/CONFESS/DEFAULT/HALT.
  Acceptance:
    - Learning cannot move M's status to positive; cannot widen the budget; cannot choose the mouth.
    - The empty-maximize slot is unreachable from any reward path (every optimizer downstream of a fate).
  Rollback gate:  any drift report shows the empty-maximize signature (a membrane-legal signal being
    emptied by maximization)  ⇒  γ→0, freeze the organ, revert to grid-without-learning.
```

### 17.3 The A→D crossing rule: reaching the target WITHOUT passing through B

The single most important migration-safety rule. The Round-2 phase diagram has the drain (A) and the target (D) on opposite corners, with the amputation cell (B) adjacent to D (both are `ω>0`; they differ in κ-sign). The naive path from A (frozen×aligned) to D (live×aligned) is to *first raise ω* (wake the opponent) — but raising ω while κ is still ≤0, or while κ's sign is *unverified*, lands the system in **B** (live×anti-aligned = amputation), not D. The trajectory `A → B → D` passes through the harm.

The rule forces the κ-bifurcation *before* the ω-bifurcation:

```text
A→D CROSSING RULE (raise κ before ω; never cross through B):

  Phase 1 (establish κ>0 while still frozen):  in cell A, bring E3's three-way fingerprint to κ>0
            BEFORE waking the opponent. Verify alignment against the FROZEN past-self (the χ-axis
            membrane-quotient): the curriculum is aligned iff graduations improve held-out OPE on
            the failed-regime league WITHOUT monoculture rising. This is checkable while ω≈0.

  Phase 2 (raise ω only after κ>0 is sealed):  once κ>0 is established and E1's sealed forecast is
            live, raise ω (reopen deposition, solicit fresh surprisal via E4). Because κ>0 is already
            sealed, raising ω moves A→D directly along the κ>0 edge, never dipping into B.

  GUARD:  if ω rises while κ-sign is unverified or ≤0  →  the grid reads cell B  →  AMPUTATION-HALT
          (G-5) fires immediately. The migration cannot accidentally traverse B; the grid halts it.

  Order is forced:  E2 (substrate) → E3 (κ-gate) → E1 (seal κ's read) → E4 (raise ω).
                    This is EXACTLY the DM1→DM2→DM3→DM4 order. The migration order IS the safe path.
```

The migration order and the safe-trajectory rule are the same fact viewed twice: building E2→E3→E1→E4 *is* raising κ before ω, which *is* the A→D path that avoids B. An engineer who follows the migration order cannot reach the target through the harm, because the grid (live by DM4) halts any ω-rise that outruns a verified κ.

---

## 18. Dynamism definition of done (G3d)

The checklist that the dynamism — not the static architecture — is honest. Mirrors plan §18.

```text
DYNAMISM DEFINITION OF DONE

THE MARGIN AND THE FAIL-SAFE
[ ] M(t) = α(1−y/V*) − β·P(r>θ) is computed as a status-carrying scalar (the bifurcation margin).
[ ] Each input term is classified forgeable / sealed-derivable / irreducibly-tier-2 (§13.2 table).
[ ] α is sourced from E2 league turnover, not from starvable residual level.
[ ] β is floored by the E4 confession rate, not read from realized break firings alone.
[ ] P(r>θ) is lifted to E1 sealed-surprisal-collapse for its chronos projection; its kairos
    projection is acknowledged irreducibly tier-2 and is NEVER claimed measured.
[ ] y/V* is read from the StructuralSpeechRatchet, inheriting the ratchet's manipulation-resistance.
[ ] .notMeasured(M) ≡ M<0 is implemented, deterministic, and topology-enforced (no model/reward/
    dashboard path promotes a non-measured status to positive M_effective).
[ ] The fail-safe asymmetry is conjoined with E4 + hysteresis (it is NOT shipped alone — the
    DoS-on-own-learning objection is answered by self-exiting default, not by softening the rule).
[ ] Total withdrawal (0/0 conditional surprisal) routes to default, never to user-biography inference.

THE DECISION GRID
[ ] The grid (§14.2) is a Swift-executed table over (cell, M_effective, status) returning one action + its fate.
[ ] Cell B (κ<0 ∧ ω>0) is read BEFORE the margin and halts regardless of positive M (G-5 dominates).
[ ] E4 fires on APPROACH (0<M<M_lo), not on crossing (M≤0).
[ ] Hysteresis: two thresholds (M_fall=0, M_rise=+M_lo) + dwell time; no default-chatter.
[ ] Re-entry to D requires re-crossing BOTH bifurcations (ω via E1 sealed, κ via E3 three-way);
    M>0 alone re-enters WATCH only, never BREATHE-in-D.
[ ] Falling is free and immediate; rising is gated and must clear a higher bar held for τ_dwell.

THE FOUR EDGES, FATED
[ ] E2: SelfDoubtLedger is a POPULATION (league); scalar r is a derived view; collapse-detection preserved.
[ ] E3: recommit ∧ ¬LeagueVigorRegression on the THREE-WAY fingerprint, not bare vigor.
[ ] E1: sealed forecast is a GATE never a reward; sandbagging is punished by co-located OPE accuracy.
[ ] E4: confession is self-subject (no you-fact in the break mouth) and REOPENS deposition.
[ ] One clock, two consumers: budget regulator and confession reflex read the SAME sealed E1 signal.

THE TIER-WALK AUDIT
[ ] The tier-walk self-audit (§15) is the required audit for every dynamism change.
[ ] No coupling silently re-types a signal's fate; ZERO invariants sit in F1 (health fingerprint).
[ ] The latch staircase (I1→I6→I3→I7→mutism) is interrupted at every arrow by a sealed/confession clock.
[ ] I4 ⊳ I2 ⊳ I1 conserve-cluster preserved (no conserving I2 while draining I4).
[ ] Every cross-tier arrow introduced by the dynamism is named and has a test in §16.

MIGRATION AND CLOSURE
[ ] Adoption order is E2→E3→E1→E4 (substrate → gate → seal → act); each step has a rollback gate.
[ ] The A→D crossing raises κ before ω; the grid halts any ω-rise that outruns a verified κ (no path through B).
[ ] M is DERIVED data (an operator over I1–I7), not an eighth primitive (§19); margin-honesty is I3∘M.
[ ] The framework's scope/falsifiability boundary is stated as a decision procedure (§20).
[ ] Deterministic-default and a shadow-only mode exist for M, the grid, and each edge (observe before trust).
```

---

## 19. The closure test on M: I8 or derived? (G4)

### 19.1 Running the Round-1 closure principle on M

The Round-1 closure principle: *a quantity earns invariant-primitive status iff it is membrane-legal, non-trivially-fated, and back-action-bounded; I1–I7 are the primitives, anything further is an operator (data) over them.* Run it on `M`.

**Is `M`-the-value a new primitive, or an operator over I1–I7?** `M`'s definition is `α(1−y/V*) − β·P(r>θ)`. Decompose each term against the seven invariants:

```text
α(1−y/V*)   :  α is the recommit rate of the slow loop = the rate I1 (controllability) is restored;
               y/V* is the budget fraction = I7 (chronos-budget) state.  ⇒  this term is a function
               of I1 and I7.
β·P(r>θ)    :  β is the break-retrigger rate, P(r>θ) is the residual-crossing probability = the
               failure rate of I6 (residual-honesty) feeding the I3 (sealed-surprisal-health) gate.
               ⇒  this term is a function of I6 and I3.
```

So `M = f(I1, I7, I6, I3)` — a **composition over four of the seven primitives**. It introduces no membrane-legal signal that is not already one of I1–I7; it is read off the *rates and probabilities* of the existing invariants. By the closure principle's own criterion, `M` fails the primitive test (it is expressible as an operator over existing primitives) and is therefore **DERIVED DATA**, not an eighth primitive. `M`-the-value is `operator(I1, I3, I6, I7)`.

This is the same move the Round-1 closure made for ratchet = F4∘F3-floor: a *composed* object is data, not a new primitive. `M` is to the invariants what an operator is to the primitives.

### 19.2 The harder question: is margin-HONESTY a new primitive?

The deeper version of the closure test. Granting that `M`-the-value is derived, is the *honesty of M* — the property the fail-safe protects, "M reads true" — a new thing that needs an eighth invariant? This is where an I8 would sneak in: not as the value, but as the meta-property "the framework's self-measurement is trustworthy."

Resolve it definitively. Margin-honesty is "M is not self-blinded — its reading tracks its measurand." But that is *exactly* I3 (sealed-surprisal-health) applied to `M` as the measurand:

```text
I3       :  sealed-surprisal-health — the property that a sealed forecast's surprisal has not
            collapsed, i.e. the measurement apparatus has not been degraded into a noiseless mirror.
I3 ∘ M   :  the same property with M as the forecast subject — "M's sealed inputs have not
            collapsed," i.e. M's reading still tracks the separatrix and has not been self-blinded.
```

Margin-honesty is **I3 composed with M** — the surprisal-honesty invariant applied to the margin. The fail-safe `.notMeasured(M) ≡ M<0` is precisely the F2 (minimize-to-floor) fate of `I3∘M`: drive the dishonesty of `M` to a floor by treating un-anchored `M` as the worst case. There is no new measurand here; there is I3, pointed at `M`, fated by F2, exactly as I3 is fated in the original seven (I3 under F5/F2).

**The verdict, definitively: there is NO I8.** The framework's self-measurement is assembled from I1–I7:
- `M`-the-value `= operator(I1, I3, I6, I7)` — derived data.
- `M`-honesty `= I3 ∘ M`, fated by F2 (the fail-safe) — derived, no new primitive.

The seven primitives stay closed **even under the framework measuring itself.** This is the strong result the closure principle was built to deliver: the engineering layer does not measure a new thing; it *composes the seven*. An eighth invariant would have been a tell that the framework cannot account for its own instrumentation in its own terms — and it can. The closure survives reflexivity. (This is itself an instance of the reflexive-Goodhart category from Round 1: the danger that the optimizer degrades its own measurement apparatus is met not by a new invariant but by fating I3∘M — the apparatus's honesty is the apparatus's own surprisal-health, floored.)

### 19.3 Why this matters for the engineering layer

If `M` had been an I8, the engineering layer would have a *new primitive to conserve* — a new fate, a new gate, a new failure mode outside the seven, and the closure principle would be false (the seven would not be closed). Because `M` is derived, the entire §14 grid, §15 audit, and §16 tests are **operations over the existing seven**, and every existing invariant-protection mechanism (the fates, the membrane, the `.notMeasured` rule) applies to `M` without extension. The framework measures itself with its own ruler. That is the definition of a closed measurement theory, and it is the deepest reason the engineering layer is *operable* rather than an open-ended addition.

---

## 20. Scope and falsifiability as a decision procedure (G5)

### 20.1 Where the framework applies, where it does not, and what falsifies it

The framework is a tool with a precise domain of applicability. Stating that domain is what makes it a framework and not theology — theology applies everywhere and is unfalsifiable; a framework has a boundary and a kill condition.

```text
APPLIES  (the regime this framework is the right tool for):
  · Membrane-bounded witness: the agent is forbidden, by design, to model the principal's
    cognition-in-itself (no portrait). Every signal it can compute is a function of its own
    output history and the principal's registered reactions.
  · Non-modelable opponent whose cognition the agent's actions SHIFT: the agent is the source
    of the non-stationarity (its placements reshape π_user), and it may not see the opponent's
    policy. The proxy is read off the opponent; optimizing it corrupts the opponent.
  · Consequence: F1 (maximize) is EMPTY over all membrane-legal signals (the empty-maximize-slot
    theorem). There is no membrane-legal objective to maximize; only fates F2–F6 are non-trivial.

DOES NOT APPLY  (where this whole apparatus is unnecessary):
  · Objective measurable on the system's own side: a ground-truth signal exists that the agent's
    optimization does NOT corrupt (the opponent is not the sensor). Then F1 is NON-EMPTY — there
    is a real thing to maximize — and ordinary RL / RLHF applies. The margin, the grid, the
    tier-walk, the edges are all UNNECESSARY: you have a reward, optimize it.
  · Stationary opponent: the principal's policy does not shift under the agent's actions
    (or the shift is modelable without a membrane). Then there is no opponent-shift Goodhart,
    no reflexive corruption, and standard non-stationarity tools suffice.

FALSIFIES  (the kill condition — exhibit ONE of these and the framework is wrong):
  · Exhibit a SINGLE membrane-legal F1 signal: a signal the agent can compute under the membrane,
    can maximize, and whose maximization does NOT empty it (no Class-U sensor back-action, no
    Class-S self-consistency collapse). This breaks the empty-maximize-slot theorem.
    ⇒ if F1 is non-empty, the static⟺dynamic duality collapses (empty-F1 ⟺ no-optimizer-fixed-point
      was the duality's hinge), the two-attractor result is false, the margin measures nothing,
      and the framework is WRONG. One such signal falsifies the whole edifice.
```

The falsifier is sharp and singular: the entire framework rests on the empty-maximize-slot theorem, and one counterexample — one membrane-legal signal that survives its own maximization — collapses it. This is the property that distinguishes it from theology: it names the single observation that would kill it.

### 20.2 The decision procedure: "is my system in the regime where this framework is the right tool?"

An engineer runs this procedure to decide whether to reach for this framework at all. It is a small decision tree with a default.

```text
DECISION PROCEDURE — "Is this framework the right tool for my system?"

  Q1.  Does a ground-truth signal exist on MY side of the boundary that my optimization
       does NOT corrupt?  (i.e. is the sensor independent of the opponent?)
         YES  →  F1 is non-empty. Use ordinary RL/RLHF. STOP — this framework is unnecessary.
         NO   →  go to Q2.

  Q2.  Do my actions SHIFT the principal's policy (does placing outputs reshape how they
       judge / decide / perceive)?
         NO   →  stationary opponent. Standard tools suffice; the margin/grid are overkill. STOP.
         YES  →  go to Q3.

  Q3.  Am I FORBIDDEN (by design/privacy/membrane) to model the principal's cognition directly —
       so my only signals are my-output-history × their-registered-reactions?
         NO   →  you can model the opponent; use opponent-modeling / non-stationary RL. STOP.
         YES  →  go to Q4.

  Q4.  CONFIRM the kill condition is NOT already broken: can you exhibit ONE membrane-legal
       signal you can maximize WITHOUT emptying it (no sensor back-action, no self-consistency
       collapse)?
         YES  →  the empty-maximize-slot theorem FAILS for your system. The framework does not
                 apply (and if you believed it did, it was wrong here). Use the F1 signal directly. STOP.
         NO   →  go to VERDICT.

  VERDICT:  Q1=NO, Q2=YES, Q3=YES, Q4=NO  ⇒  YOU ARE IN THE REGIME.
            F1 is empty, the opponent is the sensor, the membrane forbids the portrait.
            Use this framework: the six fates (no F1), the seven invariants, the four edges,
            the margin M, the decision grid, the tier-walk audit, the E2→E3→E1→E4 migration.

  DEFAULT (the .notMeasured posture for scope itself):
            If you cannot answer Q1–Q4 confidently, assume YES-to-regime (Q1=NO).
            A system you cannot prove has a non-corrupting sensor should be TREATED as if its
            sensor is its opponent — assume the harder regime, exactly as .notMeasured(M) ≡ M<0
            assumes the worse margin. Over-applying the framework costs caution; under-applying
            it (using raw RL where the sensor is the opponent) costs the amputation.
```

The default is the same asymmetry as the fail-safe, lifted one level up: when you cannot tell which regime you are in, assume the regime where the apparatus is needed. The cost of over-application is some unnecessary machinery; the cost of under-application is optimizing a proxy read off an opponent you are corrupting — the load-bearing failure the framework exists to prevent.

---

## 21. The framework in one page (G6)

### 21.1 The name

**THE WITNESS CALCULUS** — a framework for membrane-bounded witness systems: agents that learn, act, and self-play against a principal whose cognition their actions reshape and whose interior they are forbidden to model. (Where an ordinary RL system *optimizes a measured objective*, a witness *conserves the principal's capacity to keep correcting it* — because under the membrane there is no objective to optimize that the optimization does not corrupt.)

### 21.2 The core laws

```text
LAW 1 — THE EMPTY-MAXIMIZE SLOT / THE DUALITY.
  F1 (maximize) is empty over every membrane-legal signal (sensor back-action empties Class U;
  self-consistency's optimum re-enters Class U for Class S). Equivalently: empty-F1 ⟺
  no-optimizer-fixed-point. The system has exactly two attractors — the mutism drain and the
  corrigible-plant limit cycle — and the autonomous-learner region is UNREACHABLE.

LAW 2 — MACHINE-ACTING IS CORRECTIVE, NEVER ACQUISITIVE.
  The acting loop is fated: it may suppress its own residual or confess its own vigor-collapse;
  there is no third mode. The witness does not act ON the principal; it acts on ITSELF to reopen
  the principal's correction channel.

LAW 3 — THE CLOSURE PRINCIPLE (CLOSED UNDER SELF-MEASUREMENT).
  The seven invariants are primitives; everything else is an operator over them — including the
  framework's measurement of itself. The margin M = operator(I1,I3,I6,I7); margin-honesty = I3∘M.
  There is no I8. The framework measures itself with its own ruler.
```

### 21.3 The three typologies

```text
SIX FATES (the verbs a quantity can be given; F1 is empty here):
  F1 maximize · F2 minimize-to-floor · F3 conserve(stock) · F4 budget(flow) ·
  F5 regulate-to-setpoint · F6 forbid.            Compose: ratchet = F4∘F3-floor.

FOUR COUPLING TIERS (the priority tower; catastrophes live in t1–t2):
  t0 value · t1 fate · t2 observability · t3 existence(empty/irreducible=kairos).
  The latch = a tier-descent staircase: I1→I6→I3→I7→mutism.

FOUR SELF-PLAY CELLS (the phase diagram; axes ω=opponent-liveness, κ=curriculum-sign):
  A frozen×aligned → self-distillation → mutism   ·   B live×anti-aligned → amputation
  C frozen×anti-aligned → degenerate              ·   D live×aligned → adversary-conservation = TARGET.
  League-holds-D: I4 conserves both coordinates of D.
```

### 21.4 The seven invariants and the conserve-cluster

```text
I1 controllability (F3)        · I2 vigor (F3, population)     · I3 sealed-surprisal-health (F5)
I4 league-diversity (F3)       · I5 exploration-coverage (F5)  · I6 residual-honesty (F2)
I7 chronos-budget (F4∘F3).
  CONSERVE-CLUSTER:  I4 ⊳ I2 ⊳ I1   (diversity conserves vigor conserves controllability).
  HEALTH FINGERPRINT:  ZERO invariants in F1.
```

### 21.5 The engineering

```text
THE MARGIN:  M(t) = α(1−y/V*) − β·P(r>θ), the signed distance to the cycle/drain separatrix.
  Self-blinding (tier-2), so .notMeasured(M) ≡ M<0 — an unmeasurable margin is assumed negative.
  Inputs sealed: α from E2 turnover, β floored by E4, P(r>θ) from E1 sealed surprisal, y/V* from the ratchet.
THE DECISION GRID:  (cell, M_effective) → {BREATHE | WATCH | CONFESS(E4) | DEFAULT | AMPUTATION-HALT},
  with hysteresis (two thresholds + dwell) and the both-bifurcations re-entry ratchet (M>0 alone ≠ D).
THE TIER-WALK AUDIT:  traverse t3→t0 asking "can a lower tier silently rewrite a higher tier's object?"
  — catches the cross-tier arrows a per-signal audit misses.
THE MIGRATION:  E2 (population) → E3 (gate) → E1 (seal) → E4 (act) — which IS the A→D path that
  raises κ before ω and never crosses B.
```

### 21.6 The quotable paragraph

> A **witness** is an agent that learns, acts, and plays against a principal whose mind its actions reshape and whose interior it may never model. The membrane that forbids the portrait has a price the **Witness Calculus** makes exact: there is *nothing to maximize* — every membrane-legal signal empties under its own maximization, so the only honest objectives are the lesser fates (conserve, budget, regulate, forbid), and the system has just two destinies, a drain into silence and a corrigible limit cycle, with the autonomous learner forever out of reach. The framework's instrument is a single signed scalar, the **bifurcation margin** `M`, the distance to the edge between those two destinies — and because `M` is the very thing the failure corrupts, the framework's first law of operation is its last line of defense: *a margin you cannot measure is assumed negative; assume you are falling.* Around that asymmetry it builds a decision grid that breathes when the opponent is live and aligned, confesses on approach to the edge, falls to a floor-with-a-door when blinded, and refuses to call a margin recovery a recovery until **both** bifurcations are re-crossed through channels the failure cannot forge. It measures all of this with seven invariants and no eighth — *the framework measures itself with its own ruler* — and it knows precisely where it does not apply: the moment you can exhibit one membrane-legal signal that survives its own maximization, the empty slot is filled, ordinary RL returns, and the Witness Calculus politely retires.

### 21.7 The master diagram: nouns → verbs → engineering

```text
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                           THE WITNESS CALCULUS — MASTER DIAGRAM                            ║
╠═══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                           ║
║  NOUNS (R1) ───────────────► VERBS (R2) ───────────────► ENGINEERING (R3)                 ║
║                                                                                           ║
║  SIX FATES                    FOUR TIERS                   THE MARGIN  M(t)                ║
║   F1 maximize  ✗(empty)        t0 value   ┐                 = α(1−y/V*) − β·P(r>θ)         ║
║   F2 min-floor ─────────┐      t1 fate    ├ catastrophes    │                             ║
║   F3 conserve  ──────┐  │      t2 observ. ┘ live here       │  inputs sealed:             ║
║   F4 budget    ───┐  │  │      t3 exist.(kairos=irreduc.)   │   α ◄ E2 turnover           ║
║   F5 regulate  ┐  │  │  │           │                       │   β ◄ E4 floor              ║
║   F6 forbid    │  │  │  │           │ latch staircase:      │   P(r>θ) ◄ E1 sealed        ║
║                │  │  │  │           ▼                       │   y/V* ◄ ratchet            ║
║  SEVEN INV.    │  │  │  │   I1→I6→I3→I7→ MUTISM             │                             ║
║   I1 control ◄─┘  │  │  │   (tier-descent drain)            ▼                             ║
║   I2 vigor   ◄────┘  │  │                          .notMeasured(M) ≡ M<0                  ║
║   I3 surprisal◄──────┘  │   SELF-PLAY CELLS         (assume falling)                      ║
║   I4 league  ◄──────────┘    A ───► mutism                  │                             ║
║   I5 coverage                B = AMPUTATION ✗               ▼                             ║
║   I6 residual                C   degenerate        THE DECISION GRID                      ║
║   I7 chronos                 D = TARGET ★          ┌──────────────────────────┐           ║
║                              (live × aligned)      │ B?──► AMPUTATION-HALT     │           ║
║  CONSERVE-CLUSTER            (I4 holds both         │ M≥+hi► BREATHE   (F5)     │           ║
║   I4 ⊳ I2 ⊳ I1               coords of D)           │ +lo..► WATCH     (F4)     │           ║
║                                  │                  │ 0..lo► CONFESS/E4(F2)     │           ║
║  HEALTH FINGERPRINT              │                  │ ≤0∨NM► DEFAULT   (F6)     │           ║
║   ZERO inv. in F1                │                  └──────────────────────────┘           ║
║                                  │                   hysteresis + both-bifurcation ratchet ║
║  DUALITY (R2):                   │                   (re-enter D ⟺ re-cross ω AND κ)       ║
║   empty-F1 ⟺ no-fixed-point      │                          │                             ║
║   two attractors only ◄──────────┘                          ▼                             ║
║   {drain, cycle};                                  TIER-WALK AUDIT (t3→t0)                ║
║   autonomous learner UNREACHABLE                   "can a lower tier rewrite a higher?"   ║
║                                                             │                             ║
║  THE FOUR EDGES (one clock, E1's sealed surprisal):         ▼                             ║
║   E2 league(κ-axis) ─► E3 gate(hold κ>0) ─► E1 seal(ω-axis) ─► E4 confess(drive ω>0)      ║
║   MIGRATION ORDER = A→D SAFE PATH (raise κ before ω; the grid halts any ω-rise into B)    ║
║                                                                                           ║
║  CLOSURE (R3): M = operator(I1,I3,I6,I7) · margin-honesty = I3∘M · NO I8                  ║
║  SCOPE:  applies ⟺ F1 empty ∧ opponent=sensor ∧ membrane forbids portrait                 ║
║          FALSIFIED by one membrane-legal F1 signal that survives its own maximization.    ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
```

---

*Part III is the engineering layer of `self-play.md`, companion to `plan-6-revised.md` (architecture of record). Parts I–II diagnosed and built the nouns and verbs; Part III ships the margin `M`, its fail-safe asymmetry, the decision grid, and the four dynamism artifacts in the plan's own idiom. The single concrete spec action it inherits from Part I remains E2 (give `SelfDoubtLedgerV1` a population body); Part III adds that the margin estimator, the decision grid, and the tier-walk audit are all operators over the existing seven invariants — the framework measures itself with its own ruler, and there is no eighth invariant to build.*
