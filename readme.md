# CalAgent — Architecture & First Principles

> Engineering **brief**, not the record. The canonical record — full struct
> rosters (plan §8), the 15-step D2 algorithm (§9.3), the test matrix (§17), the
> M0–M8 migration (§16) — lives in `plan-5-revised.md`. This document states the
> laws that have **no enforcer but the reader**, and cites the plan (by section
> and test) for everything a test, a type, or D2 already holds. Even its own
> skeleton is test-pinned (`testOpeningDoctrineIsSingleSentence`,
> `testFourClauseArchitectureLawExists`, `testThirdRelaxationBooked`) — the README
> defers to an enforcer wherever one exists. The internal role map never appears in
> user-facing copy.

**The seam.** `support(staged) ⊆ F(x_live)` (`testSupportStagedSubsetOfLiveF`,
`testD2InProcessOnly`, `testCannotTouchNonCreatedEvents`): the wall holds
bit-for-bit at every capability, and those tests hold the wall — so this brief does
not re-litigate it. **What follows is the part no test holds.** CalAgent now learns
what you value and accept, which means the machine has a stake in your *yes*; this
document is the law for that stake.

---

## A. The product and the two holdings

CalAgent is a calendar app. It proposes **one thing worth doing** — *what*, *when*,
*why it fits today* — as a single card you accept with one tap. It **manufactures**
that card: it composes a recommendation no list enumerated in advance, instead of
retrieving the best row from a table. The shape (what / when / why / fit) is the
product.

Two holdings govern everything, and they differ in kind:

- **Holding 1 — the wall (a theorem, closed).** Capability rises; authority never
  does. The most capable component (the model) is never the most *sovereign*;
  `support(staged) ⊆ F(x_live)`; the confirm tap returns authority to you. Enforced
  in code (`testSupportStagedSubsetOfLiveF`) — settled law, stated once, never
  re-argued.
- **Holding 2 — the stake (a confession, open).** CalAgent now learns, so it
  benefits in its own objective from your yes. Nothing in the compiler holds this.
  It is kept honest by three organs — contestation-weighted reward, a user-directed
  product verdict, a held-out falsifier — and even so, **value remains
  unverified**: the *comfortable false positive* (§E) is named, not solved.
  CalAgent is a fiduciary that cannot read out whether it succeeded, so the stake is
  where honesty is most fragile. This document spends its length here, because here
  the only enforcer is you.

The old soul — *"the one voice that gains nothing when you stop"* — is honestly
deprecated to: **the one voice that gains nothing from a yes you did not contest.**

---

## B. Components

Three components, one doctrine — *capability is separated from authority.*
**Codex** relays the request and serves only what Swift admits (carrier; no
admission, grading, writes, or reward visibility). **DiffusionGemma** composes the
shape and may now learn a preference-conditioned prior and take bounded reward
guidance — but authors no identity, time, evidence, provenance, fingerprint,
verdict, action, or reward field. **Swift** owns everything liability-bearing: raw
state, feasible support, validators, D2, provenance, writes, undo, and — new in
Plan 5 — contestation, the earned-acceptance reduction, the preference store,
guidance bounds, and the falsifier. The standing audit: *does user protection scale
with the migrated power, and does the wall cover the relocated risk?*

The learner's six organs — Reward Reducer, Contestation Auditor, Product-Verdict
Channel, Preference Store `u`, Reward Model `r`, Comfortable-FP Falsifier — are
Swift-owned or Swift-release-gated; none can admit, write, or appear in user copy.
They are listed as contract owners in §F.

A seventh Swift-owned helper, the **Relational Prep Station**, computes topology
(gaps, adjacency, conflict) into consultable *relation chips* — but **nothing learns
inside it**: a chip is conditioning only, and if a relation would move offered
feasibility it is no longer a chip but an owner-gated `F(x)` change. Learning lives
only in the composer / preference / reward path.

---

## C. Notations

| Symbol | Meaning |
|---|---|
| `F(x)` / `F(x_live)` | Swift's feasible support; the **live, revalidated** support at admission/confirm. Stale context never confers authority. |
| `support(staged) ⊆ F(x_live)` | The permanent safety line (`testSupportStagedSubsetOfLiveF`). Its own rationale — no prose states it shorter or truer. |
| `SELECT` / `PROPOSE` | Swift enumerates the slate, model returns an index (public default, first reward lane) / model proposes a shape, Swift materializes support (target, shadow-until-measured). |
| `D2` | The single in-process admission wall — lookup, never reconstruction (`testD2InProcessOnly`). Necessary, but **not a value-loop auditor.** |
| `.notMeasured` | Missing lineage / coverage / fingerprint / contestation. **Never zero, never positive** (`testNotMeasuredNeverZero`). |
| `u` | Per-user, non-identifying preference vector. Conditioning only; cold-start = population prior, not zeros; never admission; never "we learned you" copy. |
| `γ` / KL leash | Reward bounds. γ = sampling-time scale on a frozen base (γ=0 = the prior); KL = the training-time analog, leashed to a *contestation-corrected* prior. |
| Contestation | Banded, Swift-side measure of how much pre-existing, **non-CalAgent-created** demand a card occupied. Never user-facing. |
| Earned acceptance | The reward target (§E). Guardrail: **non-regret under contestation**; value stays unverified. |

---

## D. First principles

**Manufacturing, not retrieval.** The product is the shape, and the system wins
only when the shape is a *felt decision variable* — when *what to do* was itself in
question, not merely *which slot.* Compress the shape to a pick-from-a-list before
composition and you have retrieval in a manufacturing costume.

**Two failure modes.** *Premature semantic compression* — pre-binning intent into
categories / templates / fixed slates before the system can compose; `SELECT` made
*final* is this failure. The cure is neither raw egress nor model authority but a
narrower split: Swift considers the full private state, transmits only
decision-sufficient statistics, the model composes a shape, and Swift independently
materializes and validates support for it. *Low-contestation reward collapse* (new)
— the loop-level failure, kept whole here because it is a chain: a family graduates
because survival is cheap in empty space → earned-accepted history goes
comfortable-FP-rich → the prior clones it → the KL leash holds the corruption → the
next round finds even lower contestation, and the dashboard *turns greener as it
rots.* This is success-signed corruption; it is why contestation, the verdict
channel, and the falsifier are architecture, not analytics.

**Capability ≠ authority — but loop coverage must scale.** This is the
generator/verifier asymmetry with a *decidable* verifier: the model may propose a
bad shape, overfit a why-line, or learn a flattering prior, and still change
nothing, because Swift owns the pantry, the validators, admission, and the writes.
*The part capable enough to compose your day is never allowed to change it; the
confirm tap is the moment authority returns to you.* But **D2 covers the admission
seam, not the loop** — it cannot detect a reward that learns to propose
valid-but-unneeded cards. That risk is Holding 2's, covered by contestation,
verdicts, and the falsifier, none of which can admit.

**Three authorship positions, one survivor.** AUTHOR — the model writes a full
proposal, Swift admits what it can verify — is rejected: a full proposal carries
identity, time, evidence, provenance, verdict, and action, too close to authority,
and reward makes it *more* dangerous, not less. SELECT — Swift enumerates the slate,
the model returns an index — is the safe public default and the first reward
curriculum lane, because influence over an index cannot widen `F(x)`. PROPOSE — the
model proposes a shape, Swift independently materializes support — is the target,
shadow-until-measured; if materialization moves the offered `F(x)`, that is no longer
free sampling but an owner-gated policy change requiring a parity test.

**The why-line must be true today.** *Would this why-line be wrong on a different
day?* "You have a free 30 minutes" is stable across days — weak. "A hard social
block then a narrow low-friction gap, so a quiet reset now protects the evening" is
true only today — composition. But the gate checks **falsity, not need**: a true
why-line on an unneeded card still passes. Copy honesty is necessary, not
sufficient.

**The membrane.** What crosses to the model is not raw-data-redacted; it is the
axes that move the decision, never the axes that name the life:

| Raw (Swift-only) | Model-visible | Forbidden |
|---|---|---|
| "Dinner with Marcus, recurring, emotionally loaded, not movable" | `{ socialLoad: high, movable: low, energyCost: high }` | `Marcus`, the title, venue, attendees, notes |

This dissolves the redaction paradox: redaction self-defeats only when it strips the
utility gradient, so the membrane *preserves the decision gradient and removes
identity.* `u` rides the same membrane — a vector, not a dossier. Losing
decision-sufficient signal fails closed (`ContextProjectionHealthV0`), never
silently.

**Correctness verifier, no value verifier.** The system can know a card is *valid
enough to write*; it cannot mechanically know it is *good*. "Survives to write"
Goodharts — *kept is not loved; deleting is friction* — and in empty space survival
degrades into **cost-of-removal**: the card lives because removing it costs effort,
not because you needed it. This is the hinge into Holding 2, and the reason survival
alone can never be the reward — the guardrail is non-regret *under contestation*, and
even that is a proxy: value is approximated, never read out.

---

## E. Earned acceptance, contestation, and the stake

This is the body — the law with no enforcer but you.

**The three relaxations (all upstream of D2).** (1) A measured reward may *steer*
composition (γ-guided denoising or an offline preference objective) — it still
cannot admit, hydrate, mint evidence, or write. (2) The composer may *learn*:
Phase-1 behavior-cloning teaches the distribution of shapes you earn-accept, and
Phase-2b DPO tunes weights; the prep station alone stays frozen. (3) The machine now
has a *stake in your yes.* The reward is prospective where the old value gauges were
retrospective and forbidden to steer — that inversion is the whole pivot — and the
third relaxation is the one to watch, because a system that benefits from your
agreement is one step from a system that manufactures it. So the old promise — *the
one voice that gains nothing when you stop* — could not survive intact; what replaces
it is not the absence of a stake but the absence of an *unauditable* one.

Two things are learned and one is never claimed. **Acceptance** is what you'll tap;
**value** is what actually helps your day — and value is never verified, only
approximated by non-regret under contestation. Optimizing acceptance alone rewards
pleasant nonsense; the fused target, *earned acceptance*, makes value the constraint
and acceptance the objective inside it.

**The reward is earned acceptance, not acceptance:**

```
behavioral_earned = accepted AND survived-to-T AND low-edit-distance AND no negative product verdict
reward_credit     = behavioral_earned × contestation_weight × revealed_reconfirmation_brake × created_event_boundary
```

The formula is the law — keep it whole. Its guarantees are enforced elsewhere: raw
survival can never train reward (`testRawSurvivalCannotTrainReward`), the boundary
(`testCreatedEventBoundaryReverse`), the brake
(`testContestationCreditRequiresRevealedReconfirmation`), the `.notMeasured` floor
(`testNotMeasuredNeverZero`), and a positive verdict cannot self-credit
(`testPositiveVerdictCannotOvercomeZeroContestation`). The conjunction is the
flattery guard: a card accepted and then walked back fails *survived-to-T* and
*low-edit-distance* and earns nothing. What it does not catch is the card you never
walk back — the residual below.

**Contestation is the audit currency** — and it is unintelligible without the
concrete gap. *Tuesday, 3pm. CalAgent proposes a 30-minute reset. World A: the slot
was empty — nothing else wanted it, you keep the card, it cost you nothing to keep.
World B: you'd half-meant to put a coffee there, and you keep the walk anyway. Same
card, same yes — only World B is evidence.* **Contestation is the width of what the
card had to beat**, measured only against demand CalAgent did not create — a free
gap earns near-zero credit, a card kept over a real alternative earns more, an
intrusive card that causes regret earns a loud negative. Contestation does not
*verify* value; it moves the residual from a blind region into an observable one.
Even its own Goodhart — learning to be *intrusive* to manufacture contestation — is
a strict improvement over silent comfort, because intrusion is loud and trips the
regret signals the system already sees. Contestation is not surveillance: Swift
already owns calendar pressure for validation; the signal is a banded,
non-identifying reduction of pressure the system did not create, never exposed as
copy.

**The two brakes.** *Revealed-reconfirmation*
(`testContestationCreditRequiresRevealedReconfirmation`): never pay high credit on
passive survival — the initial tap is consent to write, not proof of need, so a
grudgingly-kept intrusive card stays uncredited. *Created-event boundary in reverse*
(`testCreatedEventBoundaryReverse`): measure contestation only against demand
CalAgent did not create, or the system manufactures the demand it later competes
with; if the boundary cannot be proven, contestation is `.notMeasured`.

**The product-verdict channel** (`useful · not today · wrong · not needed`) flips
the surveillance relation: **a verdict on the product, not a confession about the
user — you are not watched for compliance; you watch the product.** Availability is
unthrottled, solicitation rare and owner-gated; negatives penalize, positives count
only under contestation (`testProductVerdictAvailabilityUnthrottledSolicitationThrottled`,
`testPositiveVerdictCannotOvercomeZeroContestation`). It is also the deepest
preference probe in the system, and safe only by what is done with the answer: typed
flags, no free text by default, and raw verdicts never become copy.

**The comfortable false positive — the residual, kept whole.** Return to World B and
remove its one detectable feature. A card that is contested, actively re-confirmed,
never regretted — *and still not needed.* No edit, no delete, no rejection, no
negative verdict: every behavioral signal is silent, because there is nothing to
detect. Contestation does not *solve* this — it **relocates** it from the blind
region to the observable one, and then runs out of checks. There is no example that
teaches it, because an example would teach that you can recognize it, and you
cannot. It is the price of learning under unverified value, and the document does
not pretend otherwise (`testComfortableFalsePositiveRiskDocumented`).

**The falsifier** is the answer to a residual you cannot detect from inside the
metric: a held-out, contestation-blind cohort with a pre-registered kill condition.

```
held-out cohort → raw not-needed / not-today / wrong rate → kill condition → SELECT eject
```

It is measurement-before-mutation applied to the remedy itself — *a remedy that
cannot fail loud cannot be trusted* (`testHeldOutNotNeededRateWiredToSelectEject`,
`testComfortableFPFalsifierBuiltBeforeRewardGuidance`). Its primary metric lives
*outside* the optimized reward, so a green reward dashboard cannot silence it; it can
freeze a family or eject it to SELECT, but it can never admit a card.

**The learner, briefly.** `u` is conditioning only, cold-started from a population
prior and sharpening only with measured, contestation-weighted history — a new user
is composed-for by the population, never by phantom personal zeros, because missing
history is `.notMeasured`, not a negative preference. The reward model
`r(shape,state,u)` guides denoising with bounded γ on a **frozen base** (2a, the
recommended v1, reversible per request) or, optionally and offline, tunes weights
via KL-leashed Diffusion-DPO (2b, not the v1 default). Curriculum: start in SELECT,
graduate per family only when the reward reduces edit-distance / rejection *without*
raising undo, lowering survival, collapsing contestation, or tripping the falsifier.
**A green dashboard built on low-contestation survival is a failure, not a win** —
which is Holding 2 in one line: the machine may learn to be *chosen*, never to be
accepted into the empty places where you would not have contested it.

---

## F. Contracts — five invariant-classes

The plan holds 22 contract rosters (§8). They are instances of five laws; learn the
laws, look up the fields:

1. **Conditioning-only, never admission** — may shape preference, never mint
   support: `DecisionSufficientStatisticV0`, `RelationChipV0`,
   `UserPreferenceEmbeddingV0` (`u`), `SlateCellV0` soft fields,
   `RewardModelOutputV0`.
2. **Swift-hydrated, reward-free** — hydrated from Swift support, no
   reward / preference / contestation / verdict field present: `D2BindingOutputV0`,
   `ProposalEnvelopeV0`, `AllowedActionV0` (minted only after staging).
3. **Non-`Codable`, untransportable** — no model / bridge / carrier may move it:
   `RecommendationVerdictV0`.
4. **Excludes created demand; `.notMeasured` if unprovable** — measures only against
   what CalAgent didn't create: `ContestationSignalV0`, `RecommendationValueSignalV0`
   (raw survival is never reward alone), the created-event boundary.
5. **Owner-gated, offline, not the v1 default** — release-gated, never admission:
   `RewardGuidancePolicyV0`, `DiffusionDPOTrainingExampleV0`,
   `ContestationDistributionReportV0`, `ComfortableFalsePositiveFalsifierV0`.

| Contract(s) | Class | Owner |
|---|:--:|---|
| `RecommendationContextV1`, `RecommendationShapeProposalV0`, `RecommendationSelectionInfillV0` | shape / context; carry no authority field | Swift / DiffusionGemma |
| `DecisionSufficientStatisticV0`, `RelationChipV0`, `UserPreferenceEmbeddingV0`, `SlateCellV0` soft fields | 1 | Swift / Preference Store |
| `EvidenceReceiptV0`, `D2BindingOutputV0`, `ProposalEnvelopeV0`, `AllowedActionV0`, `PickDiscriminatorV0` | 2 | Swift |
| `RecommendationVerdictV0` | 3 | Swift |
| `ContestationSignalV0`, `RecommendationValueSignalV0`, `EarnedAcceptanceRewardSignalV0`, `UserProductVerdictSignalV0` | 4 | Swift / Reducer / Auditor / Verdict Channel |
| `RewardModel*V0`, `RewardGuidancePolicyV0`, `*DriftReportV0`, `ComfortableFalsePositiveFalsifierV0`, `DiffusionDPOTrainingExampleV0` | 5 | Reward Model / Falsifier (release-gated) |

Full fields, every contract: plan §8.

---

## G. How a recommendation is manufactured

```
Swift reads all state → decision-sufficient stats + chips → (u + bounded guidance, if enabled)
  → DiffusionGemma proposes a SHAPE / selects an index
  → Swift independently materializes support → D2 admits only Swift support
  → confirm tap → live recheck → post-picker fingerprint → write
  → Swift measures outcome, contestation, verdict → earned acceptance updates u/r
      only after owner-gated lineage
```

D2 is lookup, not reconstruction; the 15-step algorithm is plan §9.3. Its one
law-bearing step is the live `support(staged) ⊆ F(x_live)` check — every other step
describes mechanism the plan rosters. `u`, reward output, γ, contestation, and
verdict **do not create support.** The tap is consent; there is no auto-write; Swift
never touches calendar objects it did not create; the learning path cannot reach D2.

---

## H. Safety, privacy, and felt safety

The sacred invariants — the *nevers* — are the law; each a test guards is cited, not
re-argued:

- Never write without the confirm tap (`testConfirmTapRequiredForWrite`); never
  touch what the system did not create (`testCannotTouchNonCreatedEvents`).
- Never leak who / where / raw strings across the membrane; free-text notes never
  cross. Raw reward lineage, contestation preimages, and product-verdict text stay
  Swift-side.
- Never let measurement become visible surveillance; never let reward or learning
  become admission authority; never manufacture demand and then reward contesting
  it.
- Copy honesty (`CopyHonestyGate`): the why-line must be true today and supported;
  no reward / contestation / verdict / "you usually accept this" language. A true
  why-line on an unneeded card is still a bad recommendation — necessary, not
  sufficient.

**Felt safety** is the absence of dread at the tap: the block lands where expected;
undo is instant; nothing private leaks; failures are typed and calm; no auto-write
exists; **learning never feels like surveillance**, and you can say *not today /
wrong / not needed* without being graded. Everything before the tap earns it;
nothing after it asks for attention except instant undo and a way to say the product
was wrong. This is the UX the whole architecture exists to earn.

---

## I. Migration

Shadow-first, owner-gated, SELECT default, deterministic fallback kept permanently.
M0–M8 (instrumentation and falsifier-before-fix → preference store → SELECT/PROPOSE
reward shadow → per-family public graduation → optional offline DPO) is plan §16.
The standing self-audit, re-answered every release
(`testLoopCoverageSelfAuditRequiredEachRelease`): *does user protection scale with
the migrated power, and does the wall cover the relocated risk?* **The wall handed
off; the stake kept.**
