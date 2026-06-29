# CalAgent — Architecture & First Principles

> Engineering **brief**, not the record. The canonical record is now
> `plan-7-revised.md`: the stable Plan-6 base, the Witness Calculus dynamism
> review, and the Plan-7 controller audit folded into one target architecture.
> This document states the product laws at briefing level and records which
> companion files are active evidence versus archive. The internal role map never
> appears in user-facing copy.

## Corpus status

**The verb.** CalAgent is no longer a recommender. It does not ask *what should we
put in your time?* — a value question, and value cannot be verified from behavior.
It asks *what is already true about your time that you are too close to read?* — a
**witness**. A recommendation asserts value; a disclosure asserts a fact, and a fact
is checkable against evidence, copy budget, and live state. The pivot from Plan 5 is
the verb; almost everything below follows from it.

**Three walls and a floor.** Two harms the system can see are walled by types; one
it cannot see is named and rationed. `support(staged) ⊆ F(x_live)` walls the
**hand** (the write); `occupation(spoken) ⊆ A(tendered)` walls the **mouth** (the
speech); `transmit ⊆ decision-sufficient` walls the **membrane** (the portrait).
Each is a theorem a type holds, and those tests hold them — so this brief does not
re-litigate them. **What follows is the part no test holds:** the deepest cost is
that a witness which can speak only temporal *structure* may, over years, train you
out of your own felt sense of *timing*. The system cannot see that, so it cannot
type it. It is a **floor** — rationed by a budget and a speech-rate limiter, never closed by a law. This document spends
its length on the floor, because there the only enforcer is you.

---

## A. The product and the holdings

CalAgent is a calendar app. It discloses **one thing already true** about your time
and places it where your attention already rests — never sent, never pushed. The
witness card replaces the recommender card:

```
recommender:  what / when / why-it-fits-today                       (asserts value — unverifiable)
witness:      what's-true / why-you-can't-see-it / what-you-can-do-once   (asserts a fact — checkable)
```

The third line is the **mercy clause**: a fact placed at a self who can no longer
act on it is not a witness, it is a sentence passed (`SpendabilityProofV1`). An
empty Saturday is no longer valueless — it is among the highest-value surfaces,
because the fact to disclose there is not *fill this* but *you kept this open, and
the last three Saturdays filled by Thursday.*

Two holdings govern everything, and they differ in kind:

- **Holding 1 — the walls (theorems, closed).** Three conservation laws, each held
  by a type: state, attention, privacy. Capability rises; authority never does. The
  most capable component (the model) is never the most *sovereign*; the confirm tap
  returns write-authority to you; the attention you tendered governs what may be
  said to you. Settled law, stated once, never re-argued.
- **Holding 2 — the floors (named, open).** Three harms live on *your* side of the
  membrane, past the skull, where no type can reach: the **proxy gap** (the app is
  foregrounded ≠ your attention is tendered), the **comfortable false positive** (a
  true card you accept, never regret, never needed), and the **kairos amputation**
  (the medium's structural vocabulary, integrated over years, dulling your own sense
  of meaningful timing). None is solved. Each is named, shrunk, and handed to you to
  correct.

The deepest structural fact: **the membrane is the boundary of theorem-izability.**
Harms the system can see become types; harms it cannot see become floors. The same
wall that keeps it from building a portrait of you is the wall that keeps it from
typing the harms that matter most. Its virtue and its tragedy are one wall.

---

## B. Components and the discipline that keeps a guess from posing as a law

Three components, one doctrine — *capability is separated from authority.* **Codex**
relays and serves only what Swift admits (carrier; no admission, grading, writes,
facts, or attention authority). **DiffusionGemma** ranks and selects Swift-minted
facts and may learn which deserve placement — but authors no fact, copy, evidence,
attention lease, mouth choice, write, or reward field (*blind composer, Swift
cantor*). **Swift** owns everything liability-bearing: raw state, the fact minter,
the copy renderer, D2, the AttentionGate, writes, measurement, the temporal
calculus, the two mouths, the corrigible-plant controller (margin, cell axes, dwell,
grid), the budget and rate limiter, and the phase gate.

The central discipline (`plan-7-revised.md §20.1`, folded from Plan 6) is a criterion
for telling a **law** from a **guess**, because Swift's `enum` makes them look
identical on the page:

| Class | Test | Violating it requires |
|---|---|---|
| **theorem** | a compiler-enforced law | changing a *type signature / topology edge*, re-checked at every call site |
| **rule** | a runtime guard | changing a *value, flag, threshold, or policy* |
| **data** | conjecture, compiled & proven | nothing — it is authored, gate-checked, never code |

A flag is not a wall. Back-write is absent *as a capability*, not denied by a
`Bool` (`testBackWriteCapabilityAbsent`); a stale you-fact at the break does not
*typecheck*, it is not suppressed by an `if` (`testBreakMouthCannotAcceptSmoothSubjectFact`).
The breakfast test sorts the two: if a domain expert can propose a new member over
coffee, the set is **data**, not law. By it, the temporal *operators* are data (§D)
and only the *primitives* are genome.

---

## C. Notations

| Symbol | Meaning |
|---|---|
| `support(staged) ⊆ F(x_live)` | **STATE law** — write only into live, revalidated feasible support (`testSupportStagedSubsetOfLiveF`, `testD2Unchanged`). |
| `occupation(spoken) ⊆ A(tendered)` | **ATTENTION law** — speak only into attention you opened. `A(tendered)` is typed, short-lived, surface-specific; foreground alone is not consent (`testOccupationSubsetTenderedAttention`, `testForegroundAloneNotWideTender`). |
| `transmit ⊆ decision-sufficient` | **PRIVACY law / membrane** — move the decision signal, never the raw life. |
| `D2` / `A2` | Two independent gates: **D2** admits writes (the hand), **A2 / AttentionGate** admits speech (the mouth). Neither launders the other (`testAttentionGateSeparateFromD2`). |
| `B_structural` / regulator | The **kairos budget** — the *integral* of the attention law. In `plan-7-revised.md` it is no longer a one-way drain: a cumulative cap against a **sealed reference** (`StructuralSpeechRegulatorV2`) that tightens for free, *recovers* to the reference through margin hysteresis, and widens only by amendment — scarcity without success-driven mutism (§E). |
| `ρ_s^max` | The **robust speech-rate law** (`StructuralSpeechRateLimiterV1`): speak no faster than the human can correct you — `ρ_s^max = λ_h·min(ℓ_κ/e_κ^max, s_h/m_s^max)`, so `λ_h → 0 ⇒ ρ_s^max → 0`. The harm coefficients are amendment-gated worst-case bounds the plant may never learn downward (§E). |
| `M` | The **bifurcation margin** — signed distance to the cycle/drain separatrix, `M = α(1 − y/V*) − β·P(r>θ)`. The decision grid reads it; `.notMeasured(M) ≡ M < 0` (a margin you cannot measure is assumed negative). |
| `ω` / `κ` | The **self-play cell axes** — opponent *liveness* (are you still surprising a sealed forecast?) and curriculum *sign* (does your success strengthen or flatten the user?). Cell B (live × anti-aligned = amputation) dominates the margin; cell membership is hysteretic, not recomputed from noise. |
| primitives / operators | The calculus genome (closed by law) vs the operators and families composed from it (data). A new operator is data; a new *primitive* is theorem-surface (`testTemporalCalculusPrimitivesClosed`, `testPrimitiveAdditionRequiresPhaseGate`). |
| two mouths | **Smooth** (subject = your time, places facts) vs **break** (subject = the system's own error, confesses). The subject-switch is a type, not a flag. |
| residual / break | The self-doubt ledger — the only persistent machine-authored portrait, *of the system's own error*, now a **population** (a league of frozen failed regimes, so it can see league collapse a scalar cannot). A **break** = its prior assertions stopped holding. |
| `u` / `γ` / contestation / earned acceptance | Inherited Plan-5 reward machinery, now scoped to **write-bearing** moves only (§E). |

---

## D. First principles

**Witness, not recommender.** The product is a fact made legible, sourced from your
own evidence returned in a useful shape. Its authority is decidable truth, not the
system's taste about you. *Truth is not enough* — a true fact can be cruel, late, or
useless — but truth is a substrate a wall can reason about, and value is not.

**The membrane is the boundary of theorem-izability.** *Type the catastrophes the
system can see; budget, expose, and invite correction for the ones it cannot.*
Writing without support, speaking into untendered attention, a portrait persisting,
a stale you-fact at the break — typeable, and typed. The proxy gap, the cruel-true
fact, the abandonment at a crisis, the slow dulling of your own kairos — un-typeable,
because each is defined in a quantity past the skull.

**The temporal calculus — a grammar, not a list.** Facts are generated by a closed
set of **primitives** over the interval order — selection, windowing, the
quantifiers (∀/∃/count, duration-sum), the order relation, comparison, residual
against the system's own ledger, compose. The primitives are the genome (closed *by
law* — a sixth quantifier is not proposable over coffee). Everything above them —
density, recurrence, erosion, *and any operator the user or the shadow learner
authors* — is a **program**: data, compiled and proven, gate-checked, never code.
The calculus's ceiling is its conscience: it can express temporal **structure** and
*cannot* express semantic **meaning** — and that unsayable class is exactly the
class the privacy gene forbids it to know. "You're avoiding your sister" is unsayable
for the same reason it is forbidden. Structural-only-ness holds **by the input
types**, not by a proof flag (`testTemporalProgramStructuralByInputType`): a program
that touched meaning would not typecheck.

**Two tempos.** On **smooth life** the witness reports on *you* — it places true
facts where attention already rests, learns continuity, and stays otherwise silent.
At the **break** it changes subject to *itself* — *"I've been wrong about your
mornings four days running"* — and re-deposes. The subject-switch is the safety
property, and it is a **type**: a you-fact cannot enter the break mouth, the way a
`String` cannot enter a slot typed for an `Int`. A break is detected from the
system's *own residual*, never inferred as a portrait of you ("your life changed"
dies at the membrane).

**Capability ≠ authority — across both verbs.** The model may rank a cruel fact, learn
a flattering selection, or misjudge attention, and still change nothing, because
Swift mints the facts, renders the copy, owns D2 and the AttentionGate, and owns the
writes. *The part capable enough to read your time is never allowed to occupy it or
change it.* D2 walls the hand; A2 walls the mouth; the membrane walls the portrait.

**The witness is a corrigible plant — it has no maximand.** `plan-7-revised.md` (§3–§4)
makes this doctrine: the plant has no independent objective to maximize, only a
correction channel to conserve. **No membrane-legal signal may be maximized** — F1 is
empty. A *user-instrumented* signal pushed to a peak acts through the user, who is also
the sensor, and its cheap optimum is a user reshaped to emit favorable readings; a
*system-endogenous* signal pushed to a peak re-enters the user as a noiseless mirror.
So the acting loop is **corrective, never acquisitive** — it suppresses, confesses,
narrows, defaults, or halts, but never acts to raise a number — and the one reflex is
corrigibility: *preserve your capacity to surprise, contradict, correct, and relicense
it.* Compliance is not victory; silence is not proof.

**The fact must be true today, and structural.** *Would it be false on a different
day?* "You have a free 30 minutes" is stable — weak. "Thursday evenings were occupied
eight weeks; the last three are open" is true only now — composition. But the gate
checks **falsity, not need**, and it speaks **chronos, never kairos**: the witness
may show the structure of your time; it may never claim *this is the right moment.*
Copy honesty is necessary, not sufficient.

**The membrane.** What crosses to the model is not raw-data-redacted; it is the axes
that move the decision, never the axes that name the life:

| Raw (Swift-only) | Model-visible | Forbidden |
|---|---|---|
| "Dinner with Marcus, recurring, emotionally loaded, not movable" | `{ socialLoad: high, movable: low }`, a fact-cell index | `Marcus`, the title, venue, attendees, notes, any semantic predicate |

User facts cross as **disposable transcripts** — read-only, expiring, no back-write
path — so the model-visible lane cannot silently accrete a portrait. The only
persistent machine-authored model is the self-doubt ledger, *about the system's own
error.*

---

## E. The learning loop and its floors

This is the body — the law with no enforcer but you.

**The dynamism: a corrigible plant.** Machine *learning* is still the slow loop
(the witness of you); machine *acting* is still the fast loop (the break confession).
Plan-7-revised adds the controller between them. A slow license is no longer issued
by residual-low or deposition-answered alone: those old clocks are compatibility
inputs under `SlowWitnessLicenseReasonV2`, and live use also requires the league
vigor gate, sealed forecast health, margin state, cell-axis hysteresis, structural
speech regulator, robust rate limiter, A2, and the mouth type. Release qualifies an
organ; the controller binds live use. The system's final dependency is unchanged:
if you do not speak, it says less, never infers more. In controller terms:
`lambda_h -> 0 => rho_s^max -> 0`, `.notMeasured(M)` routes negative, and default
permits deposition/confession but not autonomous learned smooth placement.

**Write-bearing reward (inherited, now scoped).** When a witness card carries a
write-bearing move, Plan 5's machinery applies, unchanged in force:

```
behavioral_earned = accepted AND survived-to-T AND low-edit-distance AND no negative product verdict
reward_credit     = behavioral_earned × contestation_weight × revealed_reconfirmation_brake × created_event_boundary
```

Contestation is the audit currency — *the width of what the card had to beat*,
measured only against demand CalAgent did not create; a free gap earns near-zero
credit (`testRawSurvivalCannotTrainReward`, `testCreatedEventBoundaryReverse`). The
product-verdict channel (`useful · not today · wrong · not needed`) flips the
surveillance relation — *a verdict on the product, not a confession about you* — and
attention-regret penalizes a fact that was technically admitted but felt like an
interrupt. None of it can widen `F(x)` or occupy attention; reward never becomes
admission, and never speech permission.

**The comfortable false positive** — the residual no behavioral signal can catch: a
true, attention-admitted, spendable fact you accept, never regret, *and never
needed.* Contestation **relocates** it from the blind region to the observable one
and then runs out of checks. The held-out, contestation-blind **falsifier** (a
pre-registered raw not-needed rate wired to a SELECT eject) is the answer to a
residual you cannot detect from inside the metric — *a remedy that cannot fail loud
cannot be trusted.* It is named, not solved (`testComfortableFalsePositiveResidualNamed`).

**The kairos amputation — the deepest floor.** Every structural fact, however true,
trains structure-only cognition; integrated over years the medium can dull your own
sense of *meaningful* timing — the felt right-moment the witness is correctly blind
to. There is no antidote inside the grammar. Plan-7-revised keeps scarcity but
removes success-driven mutism: `StructuralSpeechRegulatorV2` holds a cumulative cap
against a sealed reference, while `StructuralSpeechRateLimiterV1` caps speech speed
by the human deposition rate and worst-case harm coefficients the plant may not
learn downward. Recovery to a sealed reference is allowed; raising the reference or
the authorized envelope is widening and requires amendment. The system never claims
to measure or conserve kairos — the budget and rate law report only system output.

**One hole, four masks.** The proxy gap is not one residual among many: attention
(foreground ≠ tendered), abandonment (silence may be care or desertion), cruelty (a
fact spendable in state, wrong in meaning), and kairos (chronos crowding out your
timing) are the same un-typeable gap, seen four ways. The system cannot close it. It
can name it, shrink it, invite correction, and speak less.

---

## F. Contracts — invariant classes

The plan holds the full rosters; they are instances of a few laws. Learn the laws,
look up the fields. The class is marked **theorem** (a type holds it), **rule** (a
test holds it), or **data** (compiled and proven, never trusted-by-construction).

| Contract(s) | Holds | Class |
|---|---|:--:|
| `TemporalPrimitiveV1` | the closed calculus over the interval order; structural-only by input type | theorem |
| `TemporalStructureProgramV1`, `FactCellV1`, render templates | operators and families as data; Swift-minted, evidence-bound, spendable | data |
| `SmoothMouthV1` / `BreakMouthV1` | subject is a type; a you-fact at the break does not typecheck | theorem |
| `ReadOnlyTranscriptV1`, phase tokens, absent push channel | back-write / live genome-edit / structural notification are absent capabilities | theorem |
| `TenderedAttentionLeaseV1`, `A2BindingOutputV1` | `occupation ⊆ A(tendered)`; proxy blindness has a typed failure, not a claimed fix | rule (+ floor) |
| `StructuralSpeechRegulatorV2`, `StructuralSpeechRateLimiterV1` | scarcity without mutism; sealed reference, robust rate cap, amendment-gated widening | rule |
| `SelfDoubtLedgerV1`, `SealedDepositionForecastV1`, `LeagueVigorRegressionV1`, `VigorCollapseConfessionV1` | E1-E4; the plant conserves the correction channel before it learns | rule |
| `MarginThresholdPolicyV1`, `DynamismDwellPolicyV1`, `CellAxisHysteresisPolicyV1`, `WitnessDynamismControllerV2` | minted guards, dwell, hysteresis, and state-specific authority | rule |
| `SlowWitnessLicenseV2` | Plan-6 clocks plus controller, margin, league, budget/rate, A2, and mouth authority | rule |
| `DepositionQuestionV1`, sealed forecasts, regime-seed facts | the human as second clock; typed, closed-past, no portrait | rule |
| `ContestationSignalV0`, `EarnedAcceptanceRewardSignalV0`, the falsifier | write-bearing reward; excludes created demand; `.notMeasured` if unprovable; never admits | rule |
| `D2BindingOutputV0`, `AllowedActionV0` | Swift-hydrated, reward-free, minted only after staging | theorem |
| `RecommendationVerdictV0` | non-`Codable` — no model / bridge / carrier may transport it | theorem |

Full active contracts, migration, tests, and definition of done: `plan-7-revised.md`.
Older field rosters in `plan-6-revised.md` are provenance unless explicitly named
as compatibility surfaces in the revised plan.

---

## G. How a witness card is made

```
SMOOTH (place, never send):
  you open a surface → Swift mints A2 attention lease
    → Swift runs temporal programs over private state → mints fact-cells
    → Swift reads E1/E2/E3 coverage, margin, dwell, budget, and rate state
    → DiffusionGemma selects a fact INDEX only → Swift renders copy from a closed template
    → controller permits breathe/watch scope → A2 admits the exact placement
    → budget admits cumulative exposure → rate limiter admits speech speed
    → smooth mouth places it inline / as a found object
    → (if write-bearing) D2 validates support → confirm tap → live recheck → write
    → settlement records truth, spendability, proxy-gap, budget pressure, verdict

BREAK (confess, then hand back the pen):
  residual, vigor collapse, or margin approach triggers break
    → slow license revoked → E4 break mouth speaks self-subject only
    → you answer a typed, closed-past deposition → a scoped, expiring regime-seed fact
    → sealed forecast scored → narrow license may return only through the controller
```

No notification path exists; the break mouth cannot speak a you-fact; the slow mouth
cannot resume from release cadence alone. `u`, reward output, gamma, attention
lease, margin, grid state, and budget **do not create support** — D2 is reward-free
and attention-free, A2 is state-free, and the learning path can reach neither.

---

## H. Safety, privacy, and felt safety

The sacred invariants — the *nevers* — are the law; each is cited, not re-argued:

- Never write without the confirm tap (`testWriteBearingWitnessRequiresD2`); never
  touch what the system did not create; no auto-write.
- Never speak into untendered attention; **place, never send** — a structural
  notification channel does not exist as a type (`testStructuralNotificationChannelUnconstructable`).
- Never leak who / where / raw strings or any semantic predicate across the membrane;
  free-text notes never cross; the model-visible lane holds no persistent user
  portrait, only disposable transcripts.
- Never speak about *you* at the break; never claim *the right moment*; never claim
  *we learned you*, a reward score, or that a fact was contested. The witness shows
  chronos and may not claim kairos.

**Felt safety** is the absence of dread: the system sees patterns without naming more
than it must; places facts only where you are already looking; does not beg for
usefulness judgments; can admit when it is **stale**; never writes without a tap;
speaks structurally **seldom**; and can be corrected without your having to confess a
self-theory. Passive users are told they *can* shape the model — never that they
*did* (`testPassiveUserCopyHonesty`). This is the UX the whole architecture exists to
earn.

---

## I. Migration

Shadow-first, owner-gated, deterministic fallback kept permanently. The active
sequence is P7R-M0 through P7R-M11 in `plan-7-revised.md`: adopt doctrine and audit,
prove static-base parity, build the population ledger, mint thresholds and dwell,
run E3/E1 in shadow, land the regulator and rate limiter, shadow margin and cell
hysteresis, bring E4/grid live, quarantine shadow-live omega handoff, re-enable
reward only under breathe-in-D, then roll out surfaces. The standing self-audit is
re-answered every public surface and every operator, budget, rate, threshold, dwell,
or mouth change: *does user protection scale with the migrated power, and does the
wall still cover the relocated risk?* **The hand is walled by D2; the mouth by
attention; the years by budget and rate — and what no wall can hold is named,
rationed, and handed to you.**
