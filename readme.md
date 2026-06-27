# CalAgent — Architecture & First Principles

> This document is the engineering reference for CalAgent. It explains what the
> system is, how it is built, the first principles it is built on, and the
> standardized contracts and notations adopted in `plan-4-revised(10).md`.
> The intended reader is an engineer or technically-literate contributor
> joining the project.

CalAgent is a calendar app. It looks at your calendar and proposes **one thing
worth doing** — *what*, *when*, and *why it fits today* — as a single card you
accept with a single tap.

The crucial part is *how* it gets that one thing. CalAgent **manufactures** the
proposal rather than picking it from a prebuilt list. It composes a
recommendation that no list had to enumerate in advance. It does this by
separating three concerns across three named components:

- **Swift** is the **framework / infrastructure** — the application and calendar
  backend that owns every liability-bearing mechanic (inventory, evidence,
  feasible support, validation, provenance, admission, writes, measurement).
- **DiffusionGemma** is the **calculator** — the expensive, high-FLOP model that
  composes meaning (the recommendation *shape*) but owns no authority.
- **Codex** is the **server / order-taker** — the carrier and dialogue layer
  that relays the request and serves only what Swift admits.

If a waiter/cook/restaurant intuition helps you remember the asymmetry —
Codex waits tables, DiffusionGemma cooks, Swift *is* the restaurant — keep it as
a mnemonic. The architecture does not rest on it. Below, components are named
directly.

---

## 1. What CalAgent is

CalAgent is an **information-manufacturing system**, not a retrieval system.

The output is not a slot and not a pre-enumerated cell. It is a **composed
recommendation**: *what* to do, *when* it will land, *why it fits today*, and how
well it *fits* — "why this, now, for this user, under this calendar state, with
this evidence basis." The **shape** of that recommendation (what / when / why /
fit) is the product. It is staged as a single card, accepted with a single tap.

The loop in plain words: Swift looks at everything private, hands the model only
non-identifying summaries, the model proposes the *shape* of a recommendation,
and Swift independently rebuilds and re-checks it before anything can be written.
This loop is named **Evidence-Ledger Composition behind PROPOSE-AND-REVALIDATE**;
the choice it embodies — and the two alternatives it beats (`AUTHOR` and
`SELECT`) — is explained in [§5](#5-the-authorship-decision).

The distinction that defines everything below: this is **manufacturing, not
retrieval**. Retrieval picks the best row from a table someone already built.
Manufacturing composes a shape that no table had to enumerate in advance.

---

## 2. The three components

The system assigns each component an asymmetric role under a single governing
doctrine: **capability is separated from authority**, and *the most capable
component (DiffusionGemma) is never the one allowed to commit anything to the
real calendar* — never the most *sovereign*. ("Authority" / "sovereignty"
throughout means exactly this: who is allowed to admit and write.) This role
map is **engineering-only** and must never surface in user-facing copy.

| Component | Role (mnemonic) | Owns | Borrows | Interface / contract | Trust boundary | Failure mode |
|---|---|---|---|---|---|---|
| **Codex** | **Server / order-taker** (carrier / dialogue) | Turn capture, bounded clarification, request relay, admitted-card presentation, dismissal/reroll relay | Swift request context, the Swift-staged card, server-minted actions | `POST /v1/carrier/turn`, `RecommendationTurnRequestV0`, `RecommendationTurnResponseV0` | No admission, no grading, no writes, no provenance, no source strength. Response payload may carry only Swift-staged artifacts and server-minted actions | Over-talks, asks an unnecessary question, echoes authority-looking text, or serves a card Swift did not admit |
| **DiffusionGemma** | **Calculator** (expensive composition; model provider / analysis lane) | Semantic composition, contrast, why-line drafting, unresolved-need detection, non-authority proposal payloads, optional shadow telemetry | Swift-furnished decision-sufficient statistics, relation chips, feasible slate cells (SELECT), shape constraints (PROPOSE) | `RecommendationSelectionInfillV0` (SELECT); `RecommendationShapeProposalV0` (PROPOSE shadow); optional `RecommendationCompositionTelemetryV0` | No identity, no title, no write time, no calendar target, no source kind/strength, no evidence hash, no provenance, no fingerprint, no verdict, no action | Hallucinates, overclaims personalization, proposes an unsupported shape, or copies authority fields |
| **Swift** | **Framework / infrastructure** (application / calendar backend) | Raw user & calendar state, decision-sufficient statistics, feasible support `F(x)`, evidence receipts, source registry, validators, D2, provenance, fingerprints, write gates, undo, lineage, value signals, metrics (the pantry, equipment, health-code, and register) | Non-authority model proposals and user confirmation | `RecommendationContextV1`, `SlateCellV0`, `D2BindingInputV0` / `D2BindingOutputV0`, `ProposalEnvelopeV0`, `AllowedActionV0`, `RecommendationValueSignalV0` | Admission-critical owner of all liability-bearing state | Over-prunes, silently truncates, leaks identifying data, admits stale support, or treats missing measurement as zero |
| **Relational Prep Station** | Swift-owned prep table | Relation chips among events & candidate windows; topology; heuristic flags; coverage & suppression metadata | Raw Swift state and closed Swift tags | `RelationChipV0`, `RelationChipSetV0`, `RelationChipCoverageV0` | Consultable conditioning only, unless an owner-gated `F(x)` change explicitly promotes a predicate | Becomes a semantic graph, fingerprints a standing meeting, or steers admission by implication |

### Governing doctrine

> The cook composes recommendations from a Swift-furnished pantry; Swift owns
> every liability-bearing mechanic — inventory, evidence, feasible support,
> validation, provenance, admission, writes, and invisible measurement; the
> waiter only takes the order and serves what Swift admits; and the most capable
> component is never the most sovereign.

### The four-clause architecture law

```
Codex may relay and serve.
DiffusionGemma may compose and propose.
Swift must validate, admit, write, and measure.
Codex and DiffusionGemma must never grade, admit, or launder their own outputs.
```

The essence: **Swift furnishes and owns, DiffusionGemma composes, Codex serves.**

---

## 3. Standardized notations & conventions

These symbols and conventions are defined first because the first-principles
material in [§4](#4-first-principles) and the authorship decision in
[§5](#5-the-authorship-decision) use them throughout. The full canonical
contracts table is in [§7](#7-canonical-contracts). All names are used verbatim
as defined in `plan-4-revised(10).md`.

| Symbol / convention | Meaning |
|---|---|
| **`F(x)`** | Swift's **feasible support** — the candidate universe Swift owns and enumerates. In `SELECT` it is enumerated as `slateOfferedV0` (`F(x) = [SlateCellV0]`). Swift is its sole owner. |
| **`F(x_live)`** | The **live, revalidated** feasible support at admission / confirm time. Stale context may never confer authority. |
| **`support(staged) ⊆ F(x_live)`** | The **permanent safety line.** Staged support must be a subset of the live, revalidated feasible support. Increased model capability never relaxes it. Tested by `testSupportStagedSubsetOfLiveF`. |
| **`SELECT`** | Authorship position where Swift enumerates the slate and the model returns only an index plus non-authority framing. The safe public default during migration. See [§5](#5-the-authorship-decision). |
| **`PROPOSE`** (PROPOSE-AND-REVALIDATE) | Authorship position where the model proposes a recommendation *shape* and Swift independently materializes support. The target posture, shadow-only until measured. See [§5](#5-the-authorship-decision). |
| **D2** | The single in-process Swift **admission seam / wall**. *Not* a network service, *not* a second verifier, *not* a model-callable tool. Performs **lookup, never reconstruction** (receipt → owning source → closed `EvidenceKindV0` → strength/copy budget → `validatePropose`). The only net-new admission-critical seam. Tested by `testD2InProcessOnly`. |
| **`V0` / `V1` suffix** | Type-name **version suffix**. Most contracts are `V0`; the context envelope is upgraded to `RecommendationContextV1` (predecessor `RecommendationContextV0` replaced). Distinct from the internal `schemaVersion: Int` field some structs also carry. |
| **`.notMeasured` / `MeasurementStatusV0`** | Measurement-state enum: `measured`, `notMeasured`, `lineageMissing`, `fingerprintMissing`, `provenanceMissing`, `staleWindowExpired`, `classifierCoupled`, `coverageInsufficient`, `ownerGateRequired`. Governing rule: **`.notMeasured` is never zero** — missing lineage, coverage, classifier independence, fingerprints, and counterfactuals never promote or penalize. Tested by `testNotMeasuredNeverZero`. |
| **Φ (Phi)** | A **guidance / bias signal** that nudges which already-feasible candidate the model favors. It only influences *preference*; it has **no authority** and **never participates in admission** — Swift validators and D2 are the only equipment. Previously modeled as Swift "stove / equipment"; now demoted to advisory "recipe / guidance bias," enacting *capability can rise without authority rising.* (Touched types: `PickDiscriminatorV0`, `GuidanceParityTests`.) |
| **Evidence hash** | `EvidenceHashV0`, carried on receipts/cells (e.g. `SlateCellV0.sourceEvidenceHash`, `EvidenceReceiptV0.summaryHash`). Swift-owned; the model may **cite but never introduce** hashes. |
| **Provenance** | `RecommendationProvenanceV0`, emitted by D2 in `D2BindingOutputV0`. Swift-owned; never model-authored. |
| **Fingerprint** | `RecommendationFingerprintV0`. The architecture distinguishes a **pre-picker fingerprint** computed inside D2 from a **post-picker fingerprint** computed at confirm/write. Both are required for measurement: value signals stay `.notMeasured` until lineage and *both* fingerprints exist. |

---

## 4. First principles

### 4.1 Manufacturing, not retrieval — the shape is the product

The product is the recommendation *shape* (what / when / why / fit), not a row
selected from an enumerated set. The system wins only when the recommendation
shape itself becomes a *felt decision variable*. Anything that compresses the
shape down to a pick-from-a-list problem before composition has happened is, by
definition, retrieval wearing a manufacturing costume.

### 4.2 The named failure mode — premature semantic compression

**Premature semantic compression** is the design failure where Swift compresses
user/calendar intent into categories, candidate universes, scoring features,
templates, semantic graphs, or fixed slates *before* the system has room to
compose the best recommendation.

Selection-only (`SELECT`) is a form of this failure **when it becomes the final
architecture**: in `SELECT`, Swift owns the candidate universe before
DiffusionGemma composes, so if the optimal shape is not already in
`slateOfferedV0`, the model can only "make the available choices sound better"
— retrieval, not manufacturing.

The cure is **not** raw data egress and **not** model authority. It is a
narrower, stronger split:

```
1. Swift considers the full private state every run.
2. Swift transmits only decision-sufficient, non-identifying statistics
   and relation chips.
3. DiffusionGemma composes a shape in a high-dimensional recommendation space.
4. Swift independently materializes and validates support for that shape.
5. Only Swift-admitted artifacts can reach the confirm tap.
```

This preserves ambiguity long enough for composition while keeping identity and
authority behind the membrane.

### 4.3 Capability is separated from authority

The load-bearing property is not that DiffusionGemma is limited; it is that
**capability and authority are deliberately separated**. The high-FLOP actor is
allowed to compose meaning and is denied sovereignty. *The cheap exact wall owns
correctness.*

This is the **generator/verifier asymmetry with a decidable correctness
verifier**: DiffusionGemma can propose a bad shape, overfit a why-line, or
hallucinate a relation, but it **cannot** put garbage on the real calendar,
because Swift owns the pantry, validation equipment, admission, provenance,
fingerprints, and writes. *The part brilliant enough to compose the user's day
is never allowed to change it.* That is the trust feature: it is why a user can
hand over calendar context without dread.

The **confirm tap is not plumbing — it is the moment authority returns to the
user.** Everything before the tap earns it; nothing after the tap asks for
attention except instant undo and clear failure recovery.

#### Authority boundaries by surface

The principle is enforced per surface. Each surface answers four questions: is it
free Swift-side computation? does it cross the membrane as conditioning? does it
touch admission authority? is it admission-critical? — followed by the rule.

| Surface | Free Swift-side computation? | Crosses membrane as conditioning? | Touches admission authority? | Admission-critical? | Rule |
|---|:--:|:--:|:--:|:--:|---|
| Raw calendar reads, notes, titles, locations, attendees | yes | no | yes, through Swift validators only | yes when used for support | Stored and reasoned over by Swift; never transmitted raw. |
| Decision-sufficient statistics | yes | yes, when non-identifying | no | no | Conditioning only; must carry coverage and redaction-loss metadata. |
| Relation chips | yes | yes, when non-identifying and approved | no | no | Consultable context only; no support / provenance / source strength. |
| `SlateCellV0` in SELECT | yes | yes | yes, but only as Swift-authored support | yes in D2 | Model may read and select an index; Swift owns every write-bearing field. |
| `RecommendationShapeProposalV0` in PROPOSE | no, model-authored | yes, as return payload | no | no | Shape hints only; no concrete identity, time, evidence, provenance, verdict, or action. |
| D2 binding | yes | no | yes | yes | Single in-process Swift seam. |
| Value signals | yes | no | no direct admission | no | Backstage measurement only; never user-visible and never model authority. |
| Confirm action | yes | served by Codex/UI only after staging | yes | yes | Server-minted; user tap required. |

### 4.4 The why-line-true-today test

Value is concentrated in the **why-line**. The acceptance test for whether the
system composed rather than vended:

> **Would this why-line be wrong on a different day?**

If *no*, the system vended. A why-line like "You have a free 30 minutes" is
stable across days and therefore weak. A why-line like "Your afternoon has a hard
social block followed by a narrow low-friction gap, so a quiet reset now protects
the evening" is true only under today's state — true today, false tomorrow. That
is composition. `PROPOSE` is justified only when it produces why-lines true today
*and* shapes Swift would not reliably have enumerated in `SELECT`.

### 4.5 The membrane — decision-sufficient, non-identifying statistics

Swift considers all user/calendar data every run, but what crosses the membrane
to DiffusionGemma is **not** "raw data, safely redacted." It is the set of
**decision-sufficient, non-identifying statistics**: *the axes that move the
recommendation, never the axes that name the user's life.*

| | Example |
|---|---|
| **Raw state (Swift-only)** | "Dinner with Marcus, recurring, emotionally loaded, not movable" |
| **Model-visible statistics** | `{ socialLoad: high, movable: low, energyCost: high, recoveryNeed: high }` |
| **Forbidden egress** | `Marcus`, dinner title, venue, attendee identity, notes, exact relationship label |

This **dissolves the redaction paradox**. Redaction is self-defeating only when
it removes the axes that carry the utility gradient. The membrane must
*preserve the decision gradient while removing identity.* It is not a privacy tax
on a fuller pantry; it is the discipline of transmitting sufficient statistics
for the decision and nothing that names a life. Enforced by
`DecisionSufficientStatisticV0` (a banded, non-identifying projection;
conditioning only) and the rule that **missing coverage is `.notMeasured`, never
zero.**

The membrane **fails closed.** If the model-visible packet loses
decision-sufficient signal, that is a context-builder *failure*, not telemetry:
both **silent truncation** and **silent redaction collapse** are failures, and
the builder must fail closed or emit a typed measurement (`ContextProjectionHealthV0`).
`redactionLossBand` may be computed Swift-side without becoming model-visible; a
new model-visible band requires owner approval, copy-honesty coverage, and PII
review.

### 4.6 Correctness verifier vs. the absent value verifier

The system has a strong **correctness verifier** and **no true value verifier**.

> It can know whether a recommendation is *valid enough to write*.
> It cannot mechanically know whether the recommendation is *good*.

The correctness verifier is decidable and admission-critical (D2 receipt/source
binding, live `F(x_live)` revalidation, duplicate policy, write-target policy,
PII and copy-honesty scan, fingerprinting, server-minted confirm action,
confirm-time live recheck). It answers: *May this staged artifact be shown and
written if the user taps?*

The value layer answers the weaker question: *Did this recommendation appear to
fit after user interaction?* This is why **"survives to write" Goodharts** —
i.e. optimizing the survival metric corrupts it, because *kept is not loved;
deleting is friction.* Survival alone biases toward safe, obvious suggestions,
lets vending return through the back door, discards the gradient in rejected
proposals, and confounds recommendation quality with calendar drift. The cure is
a backstage value-signal layer ([§9](#9-backstage-measurement)) that is *paired
with*, never *replaced by*, survival.

---

## 5. The authorship decision

Where does the recommendation shape come from? Three positions were considered.

| Position | What it is | Verdict |
|---|---|---|
| **AUTHOR (A)** | The model authors a full proposal; Swift admits only what it can mechanically verify | **Rejected.** A full calendar proposal carries identity, concrete time, title, calendar target, evidence basis, source classification, provenance, fingerprint, verdict, and action — fields too close to authority. Relying on rejection "would train engineers to route life-state through the wrong owner." |
| **SELECT (B)** | Swift enumerates the slate; the model returns `selectedSlotIndex` plus non-authority framing | **Safe public default.** Correct *precisely when the optimal recommendation is already in Swift's enumerated set.* Keeps `support(staged) ⊆ F(x_live)` obvious and testable — but cannot compose a shape that was not pre-enumerated, so it "cures hallucination by reintroducing premature semantic compression through the back door." |
| **PROPOSE-AND-REVALIDATE (C)** | The model proposes a shape (outcome, time-window / duration hints, affordances, evidence-to-consider, unresolved needs); Swift independently materializes support | **The target.** Treats the shape as *importance sampling* over a search space too large to enumerate. Pays only when the action space is high-dimensional and the shape is a felt decision variable — i.e., when it yields why-lines true today ([§4.4](#44-the-why-line-true-today-test)). |

The permanent safety line holds across all three, regardless of model capability:

```
support(staged) ⊆ F(x_live)
```

Staged support must always be a subset of the live, revalidated feasible
support. `PROPOSE` changes **how Swift samples** candidate space; it does **not**
change the admission wall — **but only so long as materialization does not move
the offered `F(x)`.** If Swift's materialization in `PROPOSE` changes the offered
feasible support, that is no longer free shape sampling: it is an **owner-gated
`F(x)` policy change requiring an explicit parity test**, not a free shape
experiment.

Migration discipline: `SELECT` stays the public default, `PROPOSE` runs
shadow-only, both pass the same D2 wall and the same live `F(x_live)`
revalidation, with **admit-rate parity** (P3 / admit-rate parity applies to
guided, pinned, or shape-proposed candidates, so guidance can never leak into
authority by changing validation semantics), a why-line-true-today audit, and an
owner gate before any public selection-moving change.

---

## 6. The Relational Prep Station

A distinct *model-authored* semantic substrate ("Substrate 2.5") remains
rejected. A **Swift-owned relational prep station is allowed.** It computes
relations among events, gaps, and candidate windows and hands DiffusionGemma
**relation chips** as consultable context.

The load-bearing distinction: relation chips are **feature engineering over a
frozen model, not representation learning.** *Nothing learns inside this layer.*
It computes, suppresses, expires, and reports coverage — and never becomes a
model-authored semantic graph. Relation chips never carry support, provenance,
source strength, admission, verdicts, fingerprints, actions, or writes.

**The chip → `F(x)` promotion seam.** A relation chip is consultable
conditioning only. *If a topology relation changes offered feasibility, it is no
longer a chip — it is an owner-gated `F(x)` policy change.* This is the single
rule that prevents a consultable chip from silently moving the admission frontier
by implication; any `F(x)`-moving promotion is owner-gated and parity-tested.

**Build priority (and why):**

- **P1 — `nonSemanticToNonSemantic`** (time/space/conflict topology: gaps,
  adjacency, travel buffers, recurrence rigidity, density, conflict windows,
  fragmentation, candidate-window geometry). Reliably computable Swift-side *and*
  decision-relevant. **Build first.** These chips can move composition but cannot
  admit support.
- **P2 — `semanticToNonSemantic`** (e.g. "this kind of event tends to need a
  buffer"). Potentially high value, but it is a **learned claim and there is no
  learner today.** It therefore ships *only* as an explicitly flagged heuristic:
  `heuristic: true`; `coverage: notMeasured` / `coverageInsufficient` until
  measured; **non-citable in copy** unless D2 and `CopyHonestyGate` approve; and
  **no admission path may depend on it.** No prose may dress it up as learned
  truth.
- **P3 — `semanticToSemantic`** (mostly decoration; the model already handles
  semantic↔semantic association from text). **Build last or not at all.**
  Suppressed by default, never model-authored, and never used to infer source
  strength or user preference without coverage.

---

## 7. Canonical contracts

| Contract | What it carries | Owner |
|---|---|---|
| **`RecommendationContextV1`** | The context envelope handed to DiffusionGemma: identity/run fields (`contextID`, `runID`, `requestID`, `spinIndex`, `seedHash`), intent/time/window, `decisionStats`, `relationChips`, summaries, `evidence`, `slateOfferedV0` (SELECT lane only), `shapeConstraints` (PROPOSE lane), `projectionHealth`, `loopState`, `redactionPolicyDigest`, `basisPackHash`. `contextID` folds request/spin/seed/intent/evidence/relation/projection/redaction/basis digests but **deliberately excludes any ambient wall-clock freshness authority** (and model prior-analysis text and raw calendar strings) — precisely so that **no frozen context can confer admission.** Freshness is established only by live `F(x_live)` revalidation at admission and confirm. | Swift |
| **`SlateCellV0`** | The `SELECT` cut-line object — "model-visible but Swift-owned." Carries `slotIndex`, `cellID`, `titleTemplateID`, `titlePreview`, `start`/`end`, `isAllDay`, `calendarTarget`, `feasibilityDigest`, `availabilityClass`, gap/travel digests, `sourceID`, `sourceEvidenceHash`, `basisEvidenceHashes`, `candidateKindHint`, `softScoreBand`, `preferenceBands`, `semanticAffordances`, `relationChipIDs`, plan-atom digest/count. `slotIndex` equals the array index. **Capability ≠ authority on the soft fields:** `softScoreBand` / `preferenceBands` / `semanticAffordances` / `relationChipIDs` are **conditioning and ordering only, never admission-bearing**; staged title uses `titleTemplateID` hydration for fingerprint stability; the model may **cite selected-cell basis hashes only when sanitizer and copy-honesty permit, and may never introduce new hashes.** | Swift |
| **`RecommendationSelectionInfillV0`** | The `SELECT` model return payload: `selectedSlotIndex: Int?`, `why: String?`, `semanticHints`, `unresolvedNeeds`, `confidence`. Cannot author identity, time, title, calendar target, evidence hashes, source kind, source strength, provenance, fingerprint, verdict, or action. | DiffusionGemma (non-authority fields only, post-sanitizer) |
| **`RecommendationShapeProposalV0`** | The `PROPOSE` payload — a recommendation **shape, not a write artifact**: `schemaVersion`, `proposalID`, `contextID`, `desiredOutcome`, `timeWindowHint?`, `durationHint?`, `affordanceHints`, `decisionAxesToRespect`, `evidenceDimensionsToConsider`, `relationChipIDsToConsider`, `unresolvedNeeds`, `whyLineDraft?`, `confidence`. **Forbidden fields:** concrete title, concrete write start/end, calendar target, calendar object ID, source kind, source strength, evidence hash, provenance, fingerprint, validation verdict, allowed action, raw attendee/place/private-title/note strings. | DiffusionGemma (shape hints only; `proposalID`/`contextID` bridge-stamped). Swift may ignore any hint and must independently materialize, D2-bind, hydrate, and revalidate live |
| **`DecisionSufficientStatisticV0`** (+ `DecisionAxisV0`, `DecisionValueBandV0`) | The membrane contract: `schemaVersion`, `statisticID`, `sourceReceiptHashes`, `axis` (e.g. `energyCost`, `socialLoad`, `mobility`, `setupFriction`, `recoveryNeed`, `deadlinePressure`, `gapTopology`, `travelRisk`, `recurrenceRigidity`, `interruptionRisk`, `calendarDensity`, `daypartFit`, `durationFit`, `userStatedConstraint`), `valueBand` (`unavailable`/`low`/`medium`/`high`/`mixed`/`notMeasured`), `coverage`, `redactionRisk`, `computedAt`, `expiresAt?`, `owner`. **Conditioning only** — cannot mint support, provenance, source strength, or admission. | Swift (reducers & validators) |
| **`RelationChipV0`** (+ `RelationClassV0`) | A consultable relation chip: `schemaVersion`, `chipID`, `relationClass`, `subjects`, `relationKind`, `valueBand`, `evidenceHashes`, `coverage`, `visibility`, `heuristic`, `computedAt`, `expiresAt?`. Feature engineering over a **frozen model — nothing learns here.** Build priority `nonSemanticToNonSemantic` (P1, topology, first) → `semanticToNonSemantic` (P2, flagged heuristic) → `semanticToSemantic` (P3, suppressed by default). **Never carries support, provenance, source strength, admission, verdicts, fingerprints, actions, or writes;** any feasibility-moving promotion is an owner-gated `F(x)` change, not a chip ([§6](#6-the-relational-prep-station)). | Swift |
| **`EvidenceReceiptV0`** (+ `EvidenceKindV0`) | Swift evidence bound to a candidate source: `kind` (closed `CaseIterable` enum: `freeBusy`, `eventRead`, `history`, `researchEvent`, `userAnswer`, `deterministicValidation`), `issuer`, `summaryHash`, `dimensionsResolved`, `issuedAt`, `expiresAt?`, `owningSourceID`. D2 requires `receipt.summaryHash == owningSource.evidenceHash` and `receipt.kind == owningSource.evidenceKind` — a lookup, never reconstruction. | Swift |
| **`D2BindingOutputV0`** | What D2 returns to the staging path: `proposal: ProposalEnvelopeV0`, `provenance`, `inFlightSelection`, `prePickerFingerprint`, `supportReceiptKinds`, `copyBudget`. Hydrated from Swift cell/materialized support, not from model fields. | Swift |
| **`ProposalEnvelopeV0`** | The Swift-hydrated staged proposal envelope (first field of `D2BindingOutputV0`). Hydrated from Swift support, not model fields; a shape proposal cannot hydrate write fields. | Swift |
| **`PickDiscriminatorV0`** | A small Swift-owned **ranking layer over already-admitted candidates** — *not* a second LLM verifier and never admission-critical. Allowed features (gated by coverage / owner): D2 admission success, live staleness outcome, copy-honesty pass, selected-cell soft score band, decision-stat & relation-chip coverage, source-kind outcome rates, edit-distance / undo / survival-at-T risk bands, deterministic baseline delta, diversity penalty, stale-risk bands. **Forbidden features (anti-laundering firewall):** model confidence as feasibility; model self-rank as usefulness; model-authored source strength or evidence kind; sampler / re-noising confidence as quality; raw PII; unmeasured metrics as zero; **any value signal visible to the user.** | Swift |
| **`RecommendationValueSignalV0`** (+ `RecommendationEditDistanceV0`, `CounterfactualSlateLogV0`, `SurvivalAtTSignalV0`) | The backstage value-signal container: `requestID`, `contextID`, `analysisID?`, `proposalID?`, `shapeProposalID?`, `prePickerFingerprint?`, `postPickerFingerprint?`, `editDistance?`, `rejectionSet?`, `survivalAtT?`, `outcomeReason`, `measurementStatus`. Never user-surfaced, never model-visible authority. | Swift |
| **`AllowedActionV0`** | The server-minted confirm action. **Ordering invariant:** it is minted **only after staging** (never before), is short-lived, scoped to the staged card, and invalidated by changed support; D2 hydrates it **last** in the hydration list. Forbidden in a shape proposal. | Swift |
| **`RecommendationVerdictV0`** | The Swift verdict object — **non-`Codable`**; no model, bridge, or carrier may transport it. Tested by `testRecommendationVerdictNonCodable`. | Swift |
| **`ContextProjectionHealthV0`** | Makes no-silent-truncation / no-silent-redaction-collapse testable and **fail-closed**: `rawCandidateCount`, `projectedCandidateCount`, `retainedStatisticCount`, `droppedStatisticCountByReason`, `redactionCollisionGroupCount`, `redactionLossBand`, `compactionOverflowBand`, `measurementStatus`. Carried at `RecommendationContextV1.projectionHealth`. | Swift |

---

## 8. How a recommendation is manufactured

The end-to-end pipeline (Evidence-Ledger Composition behind
PROPOSE-AND-REVALIDATE):

```
Swift considers all user/calendar state
  → Swift emits decision-sufficient, non-identifying statistics + relation chips
  → DiffusionGemma proposes a recommendation SHAPE (not a write artifact)
  → Swift independently materializes candidate support
  → Swift validates, admits, hydrates, fingerprints, stages, and writes
      only after user confirmation
  → Swift measures correctness and value backstage
```

### 8.1 The SELECT flow (public default)

```
User → Codex (recommendation request) → Swift (bounded turn payload)
Swift reads all private state, computes decision stats, enumerates F(x) as slateOfferedV0
Swift → RecommendationContextV1 (decision stats + slate) → DiffusionGemma
DiffusionGemma → RecommendationSelectionInfillV0 (selectedSlotIndex + non-authority framing)
Swift sanitizes / strips authority echoes
Swift → selected cell + evidence registry → D2 + validators
  (D2 lookup + live F(x_live) revalidation → Swift-hydrated staged card OR typed no-rec)
Swift → admitted card + server-minted confirm/dismiss actions → Codex → User
On confirm tap / reject: Swift writes / undoes / records rejection lineage;
  the write tail emits backstage value signals.
```

`SELECT` remains the public default until `PROPOSE` passes shadow gates.

### 8.2 The PROPOSE flow (shadow)

```
User → Codex → Swift (bounded turn payload)
Swift reads all private state, computes decision stats + relation chips
Swift → RecommendationContextV1 (WITHOUT raw private identity) → DiffusionGemma
DiffusionGemma → RecommendationShapeProposalV0
Swift rejects concrete fields, scans the why-line draft
Swift materializer → Swift-owned SlateCellV0 candidates from private state
Swift → D2 lookup + live F(x_live) revalidation → admitted staged card OR typed failure
Swift → value-signal layer (compare against SELECT / deterministic counterfactuals, backstage)
```

`PROPOSE` shadow results do not change public traffic until measured. **Every
admitted shadow card passes the same D2 wall and live revalidation as `SELECT`.**
`PROPOSE` changes how Swift *samples* candidate space, not the wall — *unless
materialization moves the offered `F(x)`*, in which case the experiment requires
an explicit parity test and owner gate ([§5](#5-the-authorship-decision)).

### 8.3 The D2 admission wall

D2 is the single in-process Swift admission seam — **the only net-new
admission-critical seam.** It performs **lookup, not reconstruction**. Its
algorithm, abbreviated:

```
1.  Verify context identity and freshness.
2.  SELECT: resolve the selected cell by selectedSlotIndex,
        requiring cell.slotIndex == selectedSlotIndex.
3.  PROPOSE: reject all concrete write fields, then ask the Swift materializer
        for candidate cells.
4.  Verify every candidate has source ID, source evidence hash, basis hashes,
        and a feasibility digest — all minted by Swift.
5.  Lookup receipt by summaryHash == sourceEvidenceHash.
6.  Lookup owning source by receipt.owningSourceID and sourceIDByEvidenceHash.
7.  Require receipt/source kind equality and hash equality.
8.  Classify strength / copy budget ONLY by closed EvidenceKindV0 + source factory policy.
9.  Verify every basis hash is a fresh context or materializer receipt.
10. Scan model text for PII / unsupported personalization / authority echo / hidden-field copying.
11. Hydrate ProposalEnvelopeV0 from Swift support, NOT model fields.
12. Re-mint inFlightSelection from the selected cell's owning source.
13. Run live F(x_live) and validatePropose.
14. Compute the pre-picker fingerprint.
15. Return a non-Codable Swift verdict to the staging path.
```

Step 13 is where the permanent safety line `support(staged) ⊆ F(x_live)` is
enforced. `PROPOSE` changes how Swift *samples* candidate space; it does not
change this wall. One exact wall is easier to audit than several soft walls.

### 8.4 Confirm, write, and undo

```
staged card → user confirm tap → live support recheck → post-picker fingerprint
  → write → undo / edit / delete / survival-at-T measurement
```

The confirm action (`AllowedActionV0`) is **server-minted, minted only after
staging**, short-lived, scoped to the staged card, and invalidated by changed
support. **The tap is consent.** There is **no auto-write** — felt safety does
not earn it. Swift **never touches calendar objects it did not create.**
Everything before the tap earns it; after the tap, nothing asks for attention
except instant undo and clear failure recovery.

---

## 9. Backstage measurement

Because correctness ≠ value ([§4.6](#46-correctness-verifier-vs-the-absent-value-verifier)),
Swift owns a **backstage value-signal layer** (`RecommendationValueSignalV0`)
whose signals are *paired with* survival, never *replaced by* it.

| Signal | What it measures |
|---|---|
| **Edit-distance** (`RecommendationEditDistanceV0`) | The **dense quality signal** — how much the user had to *finish the system's job*. Compares the proposed card to the written card across `titleChanged`, start/end/duration delta bands, `calendarTargetChanged`, `userAddedDetailsBand`, and an aggregate band. Cheap, dense, available far earlier than long-horizon retention. |
| **Counterfactual slate** (`CounterfactualSlateLogV0`) | The gradient in **rejected proposals** — offered/rejected/selected candidate digests, rejection reason, `staleAtRejection`. A dismissal, reroll, "not this," or edit tells the system what kind of composition missed. Stale support is separated from genuine user rejection. |
| **Survival-at-T** (`SurvivalAtTSignalV0`) | Whether the written recommendation **remains until ~24h before the event** (`tMinusHours` default 24) — `survived`, `deleted`, `edited`, `moved`, `staleWindowExpired`. Measured near the event horizon, **not** at the confirm tap. |

Three rules govern the entire layer:

- **Measurement before mutation.** No adaptive ranking, preference update,
  relation-chip promotion, or `PROPOSE` public launch occurs until lineage and
  *both* fingerprints exist (lineage ties request → context → proposal → confirm
  → write → edit/undo/delete → survival window).
- **`.notMeasured` is never zero.** Missing lineage, coverage, classifier
  independence, fingerprints, or counterfactuals never promote or penalize. No
  value signal can make an invalid artifact valid.
- **The loop improves in the dark.** *The model has no authority. Measurement
  has no visibility.* All value signals are Swift-side, never user-surfaced,
  never model-visible authority, never phrased as a user grade. The instant a
  user can feel they are being measured, the calendar becomes surveillance.

---

## 10. Safety & privacy invariants

These invariants are deliberately preserved across all migration; capability may
rise without authority rising.

### 10.1 Authority firewall

The model never authors identity, time, title, evidence hashes, source kind,
strength, provenance, fingerprint, verdict, or action. Swift hydrates and
revalidates live, with `support(staged) ⊆ F(x_live)`. `PROPOSE` changes
sampling, not authority. **`PickDiscriminatorV0`** may rank already-admitted
candidates but is firewalled from laundering any model signal (confidence,
self-rank, model-authored strength/kind, sampler confidence, or any
user-visible value signal) into authority.

### 10.2 Single admission wall

D2 remains the only net-new admission-critical seam, in-process Swift — **no
second verifier, no admission RPC, no model-authored ontology, no D2 network
service.** `RecommendationVerdictV0` is non-`Codable` so it cannot be transported
by any model, bridge, or carrier. **P3 / admit-rate parity** is a standing
invariant: it applies to guided, pinned, or shape-proposed candidates so guidance
can never leak into authority by changing validation semantics. Model-authored
semantic graphs remain rejected (a model-authored edge can launder source
strength, identity, or admission facts); the prep station is Swift-owned and
non-authoritative instead.

### 10.3 Privacy floor

These **never cross the model membrane by default**: raw event titles; free-text
notes or descriptions; attendee names, emails, or identities; exact locations or
addresses; raw user-history strings; and low-cardinality facts that identify a
person, place, or recurring event. Swift may *read* these to compute
decision-sufficient statistics but may not transmit them raw. **Free-text notes
never cross the membrane** — a closed-vocabulary notes affordance extractor stays
owner-gated and may emit only audited flags with coverage/redaction-risk
metadata, never substrings. Losing decision-sufficient signal is a **fail-closed
context-builder failure**, not telemetry: silent truncation and silent redaction
collapse are each a failure, surfaced via `ContextProjectionHealthV0`.

### 10.4 Copy honesty

The why-line is the permission slip: it must be **true today** and **supported by
admitted evidence.** `CopyHonestyGate` blocks unsupported preference claims,
claims naming people or places that never crossed safely, claims that imply
source strength the model cannot know, claims that **cite heuristic relation
chips as learned truth** (the P2 heuristic-honesty rule from
[§6](#6-the-relational-prep-station)), and copy that uses backstage measurement
or user behavior. A valid time with an unsupported why-line is still a
user-visible false claim, so copy honesty is part of staging.

### 10.5 Sacred calendar invariants

The unforgivable acts are inviolable invariants, not preferences:

- **Never write without the confirm tap.**
- **Never edit, move, delete, or overwrite anything the system did not create.**
- **Never leak who / where / raw private strings across the membrane.**
- **Never let measurement become visible surveillance.**

User-facing copy may not use the internal restaurant metaphor, may not imply the
system knows more than it safely exposes, and may not say or imply "we learned
you do X" from backstage value signals.

### 10.6 Felt safety

Felt safety is not a banner that says "validated" or "no conflicts." It is the
*absence of dread at the tap*: the block lands where expected; undo is instant;
the system never touches anything it did not create; no private person/place
details leak into the card; conflict failures are typed and calm; and no
auto-write exists.