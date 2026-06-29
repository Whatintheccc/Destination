# plan-6.md — Witness-First Attention-Conserving Calendar Architecture

**Status:** canonical architecture plan for CalAgent after the plan-5 remand and the Witness counter-argument. `plan-6.md` **supersedes** `plan-5-revised.md` as the product and architecture target. It inherits plan-5's safety mechanics bit-for-bit and replaces the product verb: CalAgent is no longer primarily a recommender. CalAgent is a **witness** for the user's time.

**Relationship to plan-5:** Plan 6 keeps the plan-5 wall, membrane, D2 seam, contestation-aware reward reducer, product-verdict channel, preference store, reward-guided composition constraints, falsifier, migration discipline, and implementation-status honesty. Plan 6 adds the missing channel law: speech can harm by occupying attention before it changes state. Therefore state conservation is joined by attention conservation.

**Relationship to `the-witness.md`:** Plan 6 accepts the Witness critique as a design remand: the recommendation frame forces CalAgent to assert unverifiable value, which makes the product either mute or manipulable. The same safety architecture supports a better product if the output is a fact made legible, not a value claim. Plan 6 operationalizes the witness frame as contracts, gates, flows, migration steps, tests, and release criteria.

**Implementation-status note:** This document is a target architecture. The plan-5 wall is architecture of record. The new witness-specific pieces — `WitnessFactCellV0`, `AttentionTenderV0`, `SpeechOccupationV0`, `AttentionGateV0`, `DepositionPromptV0`, `SelfDoubtLedgerV0`, `BreakSignalV0`, disposable transcripts, phase-gated typed templates, user-authored time-model dials, amendment petitions, witness organs, and the full attention-conservation release gate — are **proposed build items** until an implementation owner marks the relevant milestone complete. Do not describe these pieces as shipped merely because this plan specifies them.

**Governing doctrine:** CalAgent witnesses what is already true about the user's time, places that truth only where the user has tendered attention, offers at most one spendable next move, and never lets the machine that can compose, learn, or confess become the machine that admits, writes, manufactures demand, manufactures attention, or edits the laws that bind it.

**Architecture law:**

```text
Codex may relay and serve.
DiffusionGemma may rank, compose, contrast, and learn non-authority shapes or fact selections.
Swift must encode, validate, admit, write, measure, render facts, gate speech, reduce rewards,
measure contestation, own preference lineage, run falsifiers, enforce phase boundaries,
and bound every guidance path.
The machine may persist a model of its own residual; it must not persist a portrait of the user.
The user may author the metabolism of their time model through dials and deposition;
no one may waive the genome that binds the agent.
```

**The three conservation lines:**

```text
WRITE:    support(staged)      ⊆ F(x_live)
SPEECH:   occupation(spoken)   ⊆ A(tendered)
PRIVACY:  transmit(payload)    ⊆ decision-sufficient(non-identifying)
```

**Persistence law:**

```text
User facts crossing into the metabolism are disposable transcripts.
They expire, are read-only, and cannot become a private portrait.
The only machine-authored persistent model is the self-doubt ledger: a model of CalAgent's own error.
User-authored dials may persist because the user holds that pen.
Preference embeddings may persist only as non-identifying, coverage-carrying conditioning vectors,
not as raw facts, private strings, or user-visible claims.
```

**Loop-aware supplement:**

```text
D2 covers admission.
AttentionGate covers speech occupation.
Contestation covers the reward loop from low-contestation survival.
The falsifier covers the remedy from grading itself.
The phase gate covers metabolism from editing its own genome.
The deposition covers the blind spot only when the human speaks.
```

**Internal role map.** This map is for the engineering team only. Do not surface internal metaphors, role labels, reward terms, contestation terms, witness organs, self-doubt ledgers, or training machinery in user-facing copy, onboarding, accessibility labels, marketing, prompts, analytics event names, or product education.

| Component | Internal role | Owner | Owns | Borrows | Interface / contract | Freshness / TTL | Trust boundary | Failure mode |
|---|---|---|---|---|---|---|---|---|
| Codex | Carrier / dialogue layer | Carrier owner | Turn capture, bounded clarification, request relay, admitted-card presentation, dismissal / reroll / verdict relay | Swift-staged artifacts, server-minted actions | `POST /v1/carrier/turn`, `RecommendationTurnRequestV0`, `RecommendationTurnResponseV0` | Per turn | No admission, no grading, no writes, no provenance, no reward, no attention-gate override | Over-talks, pushes witness copy, invents learning language, or serves unstaged text. Guard: response payload may carry only Swift-staged artifacts and allowed actions. |
| DiffusionGemma | Non-authority composer / selector | Model provider + analysis lane | Ranking, contrast, non-authority shape proposals, optional witness fact selection, uncertainty hints, learned priors | Swift-furnished decision stats, relation chips, feasible slate cells, fact cells, `u`, bounded guidance | `RecommendationSelectionInfillV0`, `RecommendationShapeProposalV0`, `WitnessSelectionInfillV0` | Per analysis call | Cannot author facts, concrete write fields, evidence, provenance, reward, contestation, attention tender, speech permission, product verdict, or user copy unless explicitly marked diagnostic and rejected by default | Hallucinates fact, overclaims personalization, flatters, selects an accusation, or copies authority fields. Guard: Swift fact-cell pantry, Swift cantor, D2, AttentionGate, PII scan, contestation gates. |
| Swift | Sovereign application / backend | Swift application owner | Raw state, evidence, feasible support, fact-cell minter, copy renderer, D2, AttentionGate, writes, undo, measurement, reward reduction, contestation, falsifiers, phase gate, topology audit | Non-authority model proposals / selections, user taps, user verdicts, user dials | `RecommendationContextV1`, `WitnessFactCellV0`, `D2BindingOutputV0`, `AttentionGateOutputV0`, `EarnedAcceptanceRewardSignalV0`, `SelfDoubtLedgerV0` | Live at admission and speech; TTL by source | Sole owner of liability-bearing state and attention-bearing speech gates | Over-prunes, leaks private facts, treats attention proxy as real attention, silently truncates context, or lets reward become authority. Guard: no silent collapse, `.notMeasured`, D2, AttentionGate, phase-gated templates. |
| D2 | Admission seam for state | Swift validators | Support lookup, provenance, hydration, live `F(x_live)` recheck, pre-picker fingerprint | Swift evidence registry, staged candidate | `D2BindingInputV0`, `D2BindingOutputV0` | Live | Admission-critical only for state | Mistakenly asked to judge value or speech. Guard: D2 remains reward-free and speech-free. |
| AttentionGate | Admission seam for speech occupation | Swift product + platform | Tendered attention state, speech occupation budget, placement permission, pre-speech fingerprint | UI event stream, user attention dials, product policy | `AttentionTenderV0`, `SpeechOccupationV0`, `AttentionGateOutputV0` | Live / short TTL | Speech-critical, not state-critical | Treats foreground as consent, permits push as placement, or lets a true fact become an interrupt. Guard: `occupation(spoken) ⊆ A(tendered)`, deny-by-default push, user dials, audit. |
| Fact Cell Minter / Swift Cantor | Swift-rendered fact pantry | Swift application + copy owner | Typed facts, evidence binding, spendability checks, copy templates, final wording | Raw Swift state, receipts, relation chips | `WitnessFactCellV0`, `WitnessDisclosureCardV0`, `CopyHonestyGateV0` | TTL no longer than underlying evidence | Facts and wording are Swift-owned; model may select, not invent | True fact becomes accusation, raw private strings leak, actionability absent. Guard: spendability gate, evidence receipt, copy budget, attention gate. |
| Relational Prep Station | Swift-owned prep reducer | Swift reducers | Relation chips, topology, heuristic coverage | Raw Swift state and closed tags | `RelationChipV0` | Recomputed per run | Conditioning only | Becomes semantic graph or support. Guard: no support/provenance/source strength/admission. |
| Deposition Channel | Enactive correction port | Swift product + privacy | Closed-past confirm/correct prompts, typed answers, gene-proxy correction reports, cold-start narrowing | Swift facts, self-doubt ledger, user answer | `DepositionPromptV0`, `DepositionAnswerV0`, `DepositionOutcomeV0` | Per prompt; answer lineage persists as typed flags | User corrects the product; product must not interview for a self-theory | Becomes focus-group interview, charm, free-text extraction, or preference confession. Guard: falsifiable fact only, closed past by default, typed answers, no generalization. |
| Self-Doubt Ledger / Break Detector | Persistent self-model | Swift measurement + ML owner | Ledger of CalAgent's own assertions, prediction residuals, break signals, fast-loop confession trigger | Prior witness outputs, observed outcomes | `SelfDoubtLedgerV0`, `BreakSignalV0`, `ConfessionCardV0` | Persistent by version | May persist because subject is the system's own error, not the user's portrait | Infers “your life changed,” diagnoses user, or retreats silently. Guard: subject-switch to self, no user-portrait predicates, deposition opens correction. |
| Earned-Acceptance Reward Reducer | Reward accountant | Swift measurement owner | Contestation-weighted reward reduction, product-verdict fusion, reconfirmation brake, created-event boundary | Value signals, contestation, product verdicts, fingerprints | `RecommendationValueSignalV0`, `ContestationSignalV0`, `EarnedAcceptanceRewardSignalV0` | After lineage and windows | May steer future composition only through owner-gated guidance; never D2 or AttentionGate | Rewards free-space survival, inertia, or attention capture. Guard: contestation weighting, negative verdict penalties, attention-regret tests. |
| Contestation Auditor | Release-loop watcher | Swift release owner | Contestation distribution, low-contestation reward share, intrusion / regret alarms | Reward aggregates, verdicts, edits, undo/delete | `ContestationDistributionReportV0` | Batch / release | Gates guidance, not admission | Misses coupling between release and prior. Guard: per-family distribution gates and SELECT eject. |
| Product Verdict Channel | User-directed product audit | Swift product + privacy | Always-available typed verdicts, rare solicitation policy | User taps | `UserProductVerdictSignalV0`, `ProductVerdictPolicyV0` | Per card / undo window | User-visible by definition; never a confession or admission input | Asks to be graded, surveils, or lets useful dominate contestation. Guard: availability broad, solicitation rare, no default free text. |
| Preference Store / `u` | Non-identifying conditioning memory | Swift privacy + ML platform | Per-user preference vector, coverage, redaction risk, population prior | Contestation-weighted earned history, user dials where allowed | `UserPreferenceEmbeddingV0`, `PreferenceEmbeddingUpdateV0` | Owner-gated TTL | Conditioning only; no copy claims or admission | Becomes a portrait or visible “we learned” language. Guard: non-identifying projection, coverage metadata, no raw strings. |
| Phase Gate / Genome Controller | Run/write separation | Platform architecture owner | Stop-the-world write phase, typed template admission, topology audit, disposable transcript enforcement | Proposal queue from metabolism, owner gates | `PhaseGateV0`, `GenomeTemplateProposalV0`, `DisposableTranscriptV0` | Release cadence | Learning may express genes but never edit them live | Proposal pipe becomes mutator, arbitrary code/weights cross, or live loop rewrites law. Guard: disjoint phases, typed templates, fixed dimensions, no code payloads. |
| User Time-Model Dial Store | User-authored metabolism | Swift product + privacy | Dials for thresholds, attention widths, witness families, organ enablement, amendment petitions, three-beat audits | User enactive adjustments, deposition outcomes | `UserTimeModelDialV0`, `DialWagerAuditV0`, `AmendmentPetitionV0` | Persistent until user changes / owner policy | User may author metabolism; cannot loosen agent genome | Present self hides information from future self, or product frames passive users as authors. Guard: mold-live-witness three-beat, disclosures against dials, passive-user honesty. |
| Shadow Organ Lab | Growth without live culling | ML platform + Swift eval | Slow witness-of-you organs by held-out past-fit; fast witness-of-itself organs by residual calibration | Closed past, self-doubt ledger, typed templates | `WitnessOrganV0`, `ShadowOrganEvaluationV0` | Batch / release | Shadow only until phase-gated; no live variants on a life | Overfits dead world, graduates slow organ at a break. Guard: two validators, suppress slow organ when residual rises. |
| Comfortable-FP Falsifier | External kill condition | Independent evaluation owner | Held-out raw not-needed / not-today / wrong metrics outside optimized reward | Product verdicts, fixed cohorts, contestation strata | `ComfortableFalsePositiveFalsifierV0` | Release window | Can freeze/eject; never admit | Remedy grades itself green. Guard: pre-registered kill condition and SELECT eject. |

---

## Table of contents

1. [Executive decision](#1-executive-decision)
2. [Product pivot: from recommender to witness](#2-product-pivot-from-recommender-to-witness)
3. [The three conserved quantities and the persistence law](#3-the-three-conserved-quantities-and-the-persistence-law)
4. [The witness card and output grammar](#4-the-witness-card-and-output-grammar)
5. [Attention law and the speech gate](#5-attention-law-and-the-speech-gate)
6. [Two tempos: smooth life and the break](#6-two-tempos-smooth-life-and-the-break)
7. [Pantry membrane, fact cells, and Swift cantor](#7-pantry-membrane-fact-cells-and-swift-cantor)
8. [Canonical contracts](#8-canonical-contracts)
9. [D2 and the state admission wall](#9-d2-and-the-state-admission-wall)
10. [End-to-end flows](#10-end-to-end-flows)
11. [Learning, reward, contestation, and value under witness](#11-learning-reward-contestation-and-value-under-witness)
12. [Privacy, redaction, and copy honesty](#12-privacy-redaction-and-copy-honesty)
13. [User authorship, dials, and the amendment clause](#13-user-authorship-dials-and-the-amendment-clause)
14. [Phase gate, disposable transcripts, and shadow growth](#14-phase-gate-disposable-transcripts-and-shadow-growth)
15. [User experience invariants](#15-user-experience-invariants)
16. [Migration sequence](#16-migration-sequence)
17. [Test matrix](#17-test-matrix)
18. [Definition of done](#18-definition-of-done)
19. [Changelog / deprecation map](#19-changelog--deprecation-map)
20. [Deliberately preserved safety invariants](#20-deliberately-preserved-safety-invariants)
21. [Self-audit](#21-self-audit)

---

## 1. Executive decision

CalAgent remains an information-manufacturing system, not retrieval. Plan 6 changes what is manufactured.

Plan 5 manufactured one recommendation for the user's time. Plan 6 manufactures one **witnessed disclosure**:

```text
what is already true about the user's time;
why the user may be too close to see it;
what the user can still do with that fact, once.
```

The product is no longer primarily:

```text
What should we put in your time?
```

It is:

```text
What is already true about your time that you cannot see from inside it?
```

That is a load-bearing reframe. A recommendation asserts value. Value remains unverifiable from behavior. A disclosure asserts a fact. A fact can be checked against evidence receipts, copy budgets, and live state. This does not solve every design problem, but it moves the product's center from unverifiable taste to decidable truth.

The plan-5 state wall remains untouched:

```text
support(staged) ⊆ F(x_live)
```

Plan 6 adds the speech twin:

```text
occupation(spoken) ⊆ A(tendered)
```

A system can violate the user before it writes anything. It can do so by occupying attention the user did not spend. D2 walls the hand. AttentionGate walls the mouth by guarding the ear.

The new high-level flow is:

```text
Swift reads all private state
  -> Swift emits decision-sufficient, non-identifying state, feasible support, and Swift-minted fact cells
  -> Swift computes tendered attention A(tendered) from user action, product policy, and user dials
  -> DiffusionGemma selects or contrasts non-authority fact cells / shapes, conditioned by u and bounded guidance
  -> Swift renders the fact, checks spendability, copy honesty, privacy, and speech occupation
  -> AttentionGate admits speech only if occupation(spoken) ⊆ A(tendered)
  -> if the disclosure carries a write-bearing next move, D2 independently validates support(staged) ⊆ F(x_live)
  -> user tap returns authority for writes; user verdicts and dials return authorship for the model of time
  -> Swift measures outcomes, attention regret, contestation, product verdicts, self-doubt, and falsifier cohorts
  -> only measured, contestation-corrected, attention-safe outcomes may steer future composition
```

Plan 6 keeps plan-5 learning with sharper boundaries. The composer may learn. Reward may steer composition. The machine still has a stake in acceptance. But the stake is narrowed to witnessed facts and spendable moves, checked by contestation, attention, verdicts, falsifiers, and a phase gate that prevents the metabolism from rewriting its own laws.

The public safety default remains SELECT. Public PROPOSE remains per-family, owner-gated, and reversible. The new default product surface is **fact-cell SELECT**: DiffusionGemma may select among Swift-minted, evidence-bound facts; Swift renders and gates the final speech.

## 2. Product pivot: from recommender to witness

### 2.1 The recommendation trap

Plan 5 correctly states that value is not directly verified. It then builds a disciplined proxy stack: acceptance, survival, edit distance, product verdicts, contestation, reconfirmation, falsifiers. That stack is necessary for learning, but it does not make a recommendation's value decidable.

The dangerous loop is not only an invalid write. It is a valid, pleasant, unneeded card. In plan-5 language, this is the comfortable false positive. In plan-6 language, it is what happens when the product asks an unverifiable question and then tries to instrument its way into truth.

```text
A recommender asks the system to choose what is good.
A witness asks the system to reveal what is true.
```

Truth is not enough. A true fact can still be cruel, late, intrusive, or useless. But truth is the substrate a wall can reason about. Value is not.

### 2.2 The witness frame

The witness output is a disclosure, not advice. Its authority comes from the user's own evidence returned in a useful shape.

Examples:

```text
You've rescheduled this person four times.
You have not had an empty morning in six weeks.
The last three Saturdays looked empty until Thursday, then filled.
Your first open hour today is also the last one before the deadline cluster.
```

Each sentence is true or false under Swift evidence. None requires the model to know whether the user should care. The user's feeling is sourced from their own time.

### 2.3 The one place taste remains

The witness does not eliminate taste. It relocates taste to one decision:

```text
where a fact crosses from private to urgent.
```

Four reschedules, not two. Six weeks, not one. A blank Saturday with a three-week pattern, not any blank. That threshold is product authorship. Plan 6 does not pretend it can fully mechanize that. It makes the threshold inspectable, dialable by the user where safe, testable through closed-past shadow runs, and bounded by attention.

### 2.4 Empty space is no longer valueless

Plan 5's contestation reward prices a free gap low because survival there is cheap. That remains correct for reward. But product value is not the same as reward credit.

An empty Saturday can be the highest-value witness surface because the fact to disclose is not “fill this.” It may be:

```text
What's true: You kept this open. The last three Saturdays, something landed here by Thursday.
Why you might miss it: Blank space looks like available space, but this blank has been absorbing overflow.
What you might do once: Protect the blank until Thursday.
```

The action defends emptiness. The product added nothing to the user's Saturday except legibility and an optional shield.

### 2.5 The product still has actions

Witness does not mean passive analytics. The third line may carry a next move:

```text
protect the blank;
hold this hour;
ask before scheduling over this gap;
prepare now;
call once;
move a system-created hold;
dismiss this pattern.
```

If the move writes calendar state, D2 and the confirm tap apply. If the move only changes presentation or a user-authored dial, the relevant user action and phase gate apply. If the move is just seeing, no write occurs.

## 3. The three conserved quantities and the persistence law

### 3.1 Conservation of state

Plan 6 preserves the plan-5 state law:

```text
support(staged) ⊆ F(x_live)
```

A write-bearing card may be staged only if Swift can independently support it against live feasible state. DiffusionGemma, reward, preference embeddings, user dials, product verdicts, self-doubt, and attention do not create `F(x)`.

### 3.2 Conservation of attention

Plan 6 adds the speech law:

```text
occupation(spoken) ⊆ A(tendered)
```

`A(tendered)` is the attention the user has opened to the product. It is not merely device foreground, not merely notification permission, not merely a business desire to be seen. It is a typed, short-lived, surface-specific budget inferred from user action and constrained by user dials and product policy.

`occupation(spoken)` is the attention the proposed speech would occupy: channel, surface, interruption level, visual prominence, persistence, modal force, CTA load, and duration.

The same sentence can pass or fail depending on channel:

```text
Inline glyph on the Saturday the user opened: maybe allowed.
Push notification with the same sentence: denied by default.
Modal on app open: allowed only under a wider tender and stricter policy.
```

Rule:

```text
Push the computation, never the occupation.
```

The system may compute in the background. It may place facts where the user's eye already rests. It may not originate attention merely because it found a true fact.

### 3.3 Conservation of privacy

Plan 6 preserves the plan-5 membrane:

```text
transmit(payload) ⊆ decision-sufficient(non-identifying)
```

Swift may read all private state. What crosses to model providers or learned components is a decision-sufficient, non-identifying reduction with coverage and redaction-risk metadata. Raw event titles, notes, attendees, exact locations, raw product-verdict text, raw attention preimages, and raw fact-cell preimages remain Swift-only by default.

### 3.4 Persistence law

The witness frame adds a storage rule. The analysis lane must not accumulate a private portrait of the user.

```text
User facts cross as disposable transcripts.
Self-error may persist.
User-authored dials may persist.
Non-identifying preference embeddings may persist with coverage and redaction metadata.
Raw fact history may not persist in the metabolism.
```

A disposable transcript is:

```text
read-only;
templated;
evidence-bound;
expiring;
not back-written into the model-visible store;
not sufficient to reconstruct raw identity.
```

The self-doubt ledger is allowed to persist because its subject is CalAgent's own error:

```text
I predicted / asserted X.
X did or did not hold.
My residual rose.
My slow witness may now be stale.
```

It must not say:

```text
the user changed jobs;
the user is avoiding someone;
the user is depressed;
the user's life changed.
```

Those are portraits. They die at the membrane.

### 3.5 Genome and metabolism

Plan 6 uses a genome/metabolism split as an engineering discipline, not as user copy.

```text
Genome: state conservation, attention conservation, privacy conservation, no-portrait persistence, D2, AttentionGate, phase gate.
Metabolism: learning, preference, reward, fact selection, witness organs, user-authored dials, γ, u.
```

The metabolism may express the genome. It may not edit it. Any change to a gene or to the genome/metabolism partition requires an owner-gated write phase and, where user-accountability widens, a typed amendment petition.

## 4. The witness card and output grammar

### 4.1 Canonical card

A witness card has three lines:

```text
what's true
why you may not see it
what you can still do with it once
```

Compatibility aliases may map this into existing `what / when / why / action` UI, but the product grammar is different. The card begins from a fact, not a proposed value.

### 4.2 Example: protect the blank

```text
What's true
You kept Saturday open. The last three Saturdays, something landed there by Thursday.

Why you may not see it
The blank looks free, but recently it has been absorbing overflow.

What you can do once
Hold it open until Thursday.

[Protect the blank] [Dismiss] [Not needed]
```

The write-bearing action stages a Swift-authored hold only after D2 validates support and the user taps confirm. The fact itself may be placed only after AttentionGate admits the speech occupation.

### 4.3 Example: reschedule pattern

```text
What's true
This is the fourth time this conversation has moved.

Why you may not see it
Each move looked small by itself; the pattern only appears in the sequence.

What you can do once
Send a short note now or stop trying this week.
```

The fact must be evidence-bound. If naming the person exceeds copy budget or identity policy, Swift must render a safer version or suppress the cell.

### 4.4 Example: break confession

```text
I've been wrong about your mornings four days running.
I do not want to keep guessing.
Which is real?

[Mornings are booked solid now] [This is temporary] [You're misreading]
```

The subject is the system, not the user. The source is the self-doubt ledger, not a portrait.

### 4.5 No system-worth questions

The product should not ask the user to reassure the system.

Avoid:

```text
Was this useful?
Help us learn your preferences.
Did I do a good job?
```

Allowed as product-directed controls:

```text
Useful
Not today
Wrong
Not needed
```

Allowed as a statement of consequence:

```text
I'll learn from what you keep.
```

Even that statement is user-facing only when product-approved and copy-reviewed; the system must not imply that every tap trains a model or that the user is being watched.

### 4.6 Spendability rule

A fact may be true and still fail staging because the user cannot spend it.

```text
A fact is spendable if there remains a feasible, low-cost next move, or if the user has explicitly opened a reflective surface where seeing without acting is the purpose.
```

A true fact placed after all moves are gone is not a witness. It is a sentence passed.

## 5. Attention law and the speech gate

### 5.1 Why speech needs a wall

State changes are safe-able because the user tap gates the write. Speech changes the user's attention before any tap. A true sentence can still take something.

Therefore the mouth is not guarded by grammar alone. Grammar cannot decide whether a sentence is a disclosure or a cruelty. The ear is guarded by a typed attention budget.

### 5.2 `A(tendered)`

`A(tendered)` is a Swift-owned function over:

```text
current surface;
user-originating action;
explicit attention dials;
session state;
modal depth;
notification subscription scope;
recent speech load;
accessibility settings;
time since attention was tendered;
product policy.
```

Examples of tendered attention bands:

| Surface | Tender default | Notes |
|---|---:|---|
| Calendar grid opened by user | low / medium | Inline glyphs and small cards may fit; modal confession usually does not. |
| Detail panel opened by user | medium | More explanatory copy allowed for facts about that item. |
| User asks a direct question | high for the answer | Still no raw private leakage or unsupported claims. |
| Undo surface after a write | medium | Product verdicts and corrections allowed. |
| Settings / reflection view | high within scope | Dial consequences and audits allowed. |
| Push notification | zero by default | Requires explicit user-authored tender, narrow scope, and low frequency. |
| Background computation | no occupation | Always allowed if privacy and resource policies pass. |

### 5.3 `occupation(spoken)`

`occupation(spoken)` measures the speech act's load:

```text
channel;
surface;
interruptiveness;
visual prominence;
copy length;
CTA count;
persistence;
modal force;
emotional salience;
identity sensitivity;
frequency / recency load;
whether the subject is user or system;
whether the fact is spendable.
```

The AttentionGate admits only if the occupation is within the tendered budget.

### 5.4 Push and placement

Default rule:

```text
place, do not send.
```

A fact may be computed in advance and placed on a surface the user later opens. It must not be sent merely because it exists. A pushed disclosure requires a user-authored attention dial that explicitly tenders that channel and scope, plus stricter frequency and sensitivity gates.

### 5.5 Attention proxy blind spot

Plan 6 does not claim to solve true attention. The machine observes proxies: foregrounded app, opened grid, scroll, click, dwell, explicit setting. Real tendered attention lives partly on the user's side of the skull.

Residual risk:

```text
The app can be foregrounded while attention is not truly tendered.
An inline placement can still feel like an interrupt.
The system may not be able to detect that from its own residual.
```

The mitigation is not self-surveillance. It is user-authored correction through deposition, dials, and product verdicts. The residual remains and must be named in release review.

## 6. Two tempos: smooth life and the break

### 6.1 Smooth life

Smooth life is the slow loop.

```text
Subject: the user's time.
Behavior: silent placement of facts where attention already rests.
Learning: continuity, preference, thresholds, witness organs.
Validation: held-out closed-past world-fit and live non-regret.
```

The slow witness can say:

```text
This blank tends to fill by Thursday.
This type of gap has been your first real pause in six weeks.
This meeting chain keeps pushing into prep time.
```

It must not speak outside tendered attention, claim hidden preference, or continue through a break.

### 6.2 The break

The break is the fast loop.

```text
Subject: CalAgent itself.
Behavior: confession and re-deposition.
Learning: residual calibration.
Validation: self-doubt ledger, not a user portrait.
```

A break is not detected as:

```text
your life changed;
you got a new job;
you are avoiding mornings;
you are burned out.
```

A break is detected as:

```text
my prior assertions about this region stopped holding;
my residual has crossed a calibrated threshold;
my slow witness is stale here.
```

### 6.3 Subject switch

At the break, the system must change subject from user to itself.

Allowed:

```text
I've been wrong about your mornings four days running.
I don't want to keep guessing.
```

Forbidden:

```text
Your life changed.
You no longer like mornings.
You have a new pattern.
```

The confession opens deposition. It does not assert a new portrait.

### 6.4 Cold start as first break

Cold start is total self-doubt. The system has no personal evidence yet. If an imported or connected past exists, the system may depose a single falsifiable fact from that past:

```text
Before I say anything about your time, let me make sure I'm reading it right.
Thursday evenings were blocked for two months; the last three are open.
Did something change, or am I misreading?
```

The deposition narrows cold start. It does not solve it. If there is no past to depose, the system falls back to a population prior with low confidence and no personalized copy.

### 6.5 Suppression at the break

When the break signal fires for a region, the slow witness-of-you organ loses license to place facts in that region until re-deposition or sufficient new evidence restores calibration.

The fast witness-of-itself may still confess, because it is the only claim still validated:

```text
I am stale here.
```

That confession is still subject to AttentionGate.

## 7. Pantry membrane, fact cells, and Swift cantor

### 7.1 Nouns, not verbs

Do not give DiffusionGemma a list of things to say. Give it a closed pantry of Swift-minted nouns: fact cells.

```text
Swift mints fact cells.
DiffusionGemma may select, rank, or contrast fact cells.
Swift renders the final copy.
```

This is SELECT over `F(x)` moved to speech.

### 7.2 Fact-cell requirements

A fact cell must be:

```text
evidence-bound;
truth-checkable;
privacy-budgeted;
copy-budgeted;
attention-budgeted;
spendability-checked;
TTL-bound;
non-identifying in model-visible form;
rendered by Swift, not by the model.
```

A fact cell may refer to a pattern, gap, event relation, reschedule count, density band, pressure band, or recurrence change. It may not expose raw titles, notes, attendees, locations, or low-cardinality identifying strings unless a Swift copy budget and privacy policy explicitly allow the rendered phrase.

### 7.3 Swift cantor

The model may select the cell. Swift sings it.

`Swift cantor` means:

```text
final user-facing witness copy is rendered from Swift-owned templates and evidence;
model drafts are diagnostic only and rejected by default;
copy budget is derived from evidence kind and privacy risk;
unsupported personalization claims fail staging;
reward, contestation, and attention metrics never become copy.
```

### 7.4 Fact families

Initial fact families:

| Family | Example | Spendable next move |
|---|---|---|
| Blank protection | Empty Saturday usually fills by Thursday | Protect blank / hold until date |
| Reschedule chain | Same person/event moved repeatedly | Send note / stop trying / hold one slot |
| Density cliff | First open hour before deadline cluster | Prep now / leave open |
| Recovery gap | No empty morning in six weeks | Keep the first one / decline a system-created hold |
| Transition risk | Back-to-back with travel or setup friction | Insert buffer if supported |
| Prep debt | Meeting chain lacks prep slot | Add prep block |
| Social drift | Recurring relation has fallen out of cadence | Surface fact only if copy budget and spendability pass |
| Staleness confession | System's assertions stopped holding | Re-depose |

Each family must graduate independently.

## 8. Canonical contracts

Plan 6 inherits the plan-5 contracts unless explicitly extended below. The inherited contracts remain architecture of record for state admission, reward reduction, contestation, product verdicts, preference embeddings, reward guidance, falsifiers, and measurement statuses.

### 8.1 Inherited plan-5 contracts

Carried forward unchanged in force:

```text
RecommendationContextV1
DecisionSufficientStatisticV0
ContextProjectionHealthV0
RelationChipV0
SlateCellV0
RecommendationSelectionInfillV0
RecommendationShapeProposalV0
RecommendationCompositionTelemetryV0
EvidenceReceiptV0
RecommendationCandidateSourceV0
D2BindingOutputV0
AllowedActionV0
RecommendationVerdictV0 non-Codable
RecommendationValueSignalV0
RecommendationEditDistanceV0
CounterfactualSlateLogV0
SurvivalAtTSignalV0
ContestationSignalV0
UserProductVerdictSignalV0
EarnedAcceptanceRewardSignalV0
UserPreferenceEmbeddingV0
PreferenceEmbeddingUpdateV0
RewardModelInputV0
RewardModelOutputV0
RewardGuidancePolicyV0
ContestationDistributionReportV0
PopulationRewardDriftReportV0
ComfortableFalsePositiveFalsifierV0
DiffusionDPOTrainingExampleV0
MeasurementStatusV0
```

Compatibility note: names containing `Recommendation` may remain in code while Plan 6 migrates product language to witness/disclosure. Do not use naming compatibility to carry recommender copy into user-facing surfaces.

### 8.2 `WitnessFactCellV0` — new in Plan 6

```swift
struct WitnessFactCellV0: Codable, Hashable {
  var schemaVersion: Int
  var factCellID: WitnessFactCellIDV0
  var contextID: RecommendationContextIDV0
  var factFamily: WitnessFactFamilyV0
  var factKind: WitnessFactKindV0

  var evidenceReceiptHashes: [EvidenceHashV0]
  var owningSourceIDs: [RecommendationCandidateSourceIDV0]
  var relationChipIDs: [RelationChipIDV0]
  var decisionStatisticIDs: [DecisionStatisticIDV0]

  var truthPredicateDigest: String
  var renderedTemplateID: WitnessCopyTemplateIDV0
  var modelVisibleSummary: String
  var privacyRisk: RedactionRiskBandV0
  var copyBudget: ExplanationCopyBudgetV0

  var spendability: FactSpendabilityV0
  var possibleNextMoveKinds: [WitnessNextMoveKindV0]
  var attentionSensitivity: AttentionSensitivityBandV0
  var emotionalSalienceBand: ScoreBandV0

  var computedAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
  var owner: FactCellOwnerV0
}

enum WitnessFactFamilyV0: String, Codable {
  case blankProtection
  case rescheduleChain
  case densityCliff
  case recoveryGap
  case transitionRisk
  case prepDebt
  case cadenceDrift
  case stalenessConfession
  case userDialAudit
}

enum FactSpendabilityV0: String, Codable {
  case spendableNow
  case spendableInOpenedSurface
  case reflectiveOnly
  case noMoveLeft
  case notMeasured
}

enum WitnessNextMoveKindV0: String, Codable {
  case protectBlank
  case holdWindow
  case addPrepBlock
  case addBuffer
  case sendNote
  case dismissPattern
  case adjustDial
  case depose
  case noWriteSeeOnly
}

enum AttentionSensitivityBandV0: String, Codable {
  case low
  case medium
  case high
  case suppressed
  case notMeasured
}
```

Rules:

- `modelVisibleSummary` must be non-identifying and insufficient to reconstruct raw private strings.
- `truthPredicateDigest` is for lineage, not model reconstruction.
- The model may select by `factCellID` or index; it may not author the fact.
- `spendability == noMoveLeft` blocks ordinary witness placement unless the user opened a reflective/audit surface.
- Fact cells expire no later than their evidence.

### 8.3 `WitnessSelectionInfillV0` — new in Plan 6

```swift
struct WitnessSelectionInfillV0: Codable, Hashable {
  var schemaVersion: Int
  var selectedFactCellIndex: Int?
  var selectedFactCellID: WitnessFactCellIDV0?
  var placementHint: WitnessPlacementHintV0?
  var contrastReasons: [RedactedShapeContrastV0]
  var unresolvedNeeds: [ResolutionRequestV0]
  var confidence: ConfidenceBandV0
}

enum WitnessPlacementHintV0: String, Codable {
  case inlineGlyph
  case inlineCard
  case detailPanel
  case reflectionView
  case confessionPanel
  case doNotPlace
}
```

Rules:

- Selection confidence is not truth, attention permission, value, or support.
- `selectedFactCellIndex` must be in range and match `selectedFactCellID` when both are provided.
- `placementHint` is advisory only. AttentionGate decides.
- The model may not return user-facing copy, reward fields, contestation fields, attention fields, product verdicts, evidence hashes, or raw identity.

### 8.4 `WitnessDisclosureCardV0` — new in Plan 6

```swift
struct WitnessDisclosureCardV0: Codable, Hashable {
  var schemaVersion: Int
  var disclosureID: WitnessDisclosureIDV0
  var contextID: RecommendationContextIDV0
  var factCellID: WitnessFactCellIDV0
  var attentionGateID: AttentionGateIDV0
  var d2BindingOutputID: D2BindingOutputIDV0?

  var whatsTrue: String
  var whyYouMayNotSeeIt: String?
  var oneTimeMove: WitnessOneTimeMoveV0?
  var allowedActions: [AllowedActionV0]
  var productVerdictPolicyID: ProductVerdictPolicyIDV0?

  var preSpeechFingerprint: SpeechFingerprintV0
  var copyHonestyStatus: CopyHonestyStatusV0
  var measurementStatus: MeasurementStatusV0
  var stagedAt: Date
  var expiresAt: Date?
}

struct WitnessOneTimeMoveV0: Codable, Hashable {
  var moveKind: WitnessNextMoveKindV0
  var label: String
  var writeBearing: Bool
  var requiresConfirmTap: Bool
  var supportDigest: String?
}
```

Rules:

- `whatsTrue` and `whyYouMayNotSeeIt` are Swift-rendered.
- If `oneTimeMove.writeBearing == true`, D2 output and confirm tap are required.
- A card may be speech-valid but state-invalid; in that case it can disclose the fact without write action only if spendability remains honest.
- A card may be state-valid but speech-invalid; in that case it must not be shown until attention is tendered.

### 8.5 `AttentionTenderV0` — new in Plan 6

```swift
struct AttentionTenderV0: Codable, Hashable {
  var schemaVersion: Int
  var attentionTenderID: AttentionTenderIDV0
  var userScopeDigest: String
  var surface: AttentionSurfaceV0
  var channel: AttentionChannelV0
  var tenderSource: AttentionTenderSourceV0
  var tenderWidthBand: AttentionWidthBandV0
  var subjectScope: AttentionSubjectScopeV0
  var openedAt: Date
  var expiresAt: Date
  var userDialIDs: [UserTimeModelDialIDV0]
  var policyID: AttentionPolicyIDV0
  var measurementStatus: MeasurementStatusV0
}

enum AttentionSurfaceV0: String, Codable {
  case calendarGrid
  case eventDetail
  case recommendationCard
  case witnessCard
  case undoSurface
  case reflectionView
  case settings
  case chatTurn
  case notification
  case background
}

enum AttentionChannelV0: String, Codable {
  case inlinePlacement
  case detailPanel
  case modal
  case chatResponse
  case notificationPush
  case badgeOrGlyph
  case backgroundOnly
}

enum AttentionTenderSourceV0: String, Codable {
  case userOpenedSurface
  case userAskedQuestion
  case userTappedDetail
  case userOpenedReflection
  case userConfiguredSubscription
  case systemInferredForeground
  case notTendered
}

enum AttentionWidthBandV0: String, Codable {
  case none
  case narrow
  case medium
  case wide
  case notMeasured
}

enum AttentionSubjectScopeV0: String, Codable {
  case currentVisibleRange
  case selectedEvent
  case currentCard
  case systemConfession
  case settingsAndDials
  case explicitlySubscribedDigest
  case none
}
```

Rules:

- `systemInferredForeground` cannot by itself create more than narrow tender and may be zero by policy.
- `notificationPush` requires `userConfiguredSubscription` and a narrow subject scope.
- Tender expires quickly and is surface-specific.
- Missing tender is not zero reward; it is no speech permission.

### 8.6 `SpeechOccupationV0` — new in Plan 6

```swift
struct SpeechOccupationV0: Codable, Hashable {
  var schemaVersion: Int
  var speechOccupationID: SpeechOccupationIDV0
  var disclosureID: WitnessDisclosureIDV0?
  var factCellID: WitnessFactCellIDV0?
  var proposedSurface: AttentionSurfaceV0
  var proposedChannel: AttentionChannelV0
  var copyLengthBand: ScoreBandV0
  var visualProminenceBand: ScoreBandV0
  var interruptivenessBand: ScoreBandV0
  var modalForceBand: ScoreBandV0
  var persistenceBand: ScoreBandV0
  var ctaCountBand: ScoreBandV0
  var emotionalSalienceBand: ScoreBandV0
  var identitySensitivityBand: RedactionRiskBandV0
  var frequencyLoadBand: ScoreBandV0
  var subjectScope: AttentionSubjectScopeV0
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

### 8.7 `AttentionGateOutputV0` — new in Plan 6

```swift
struct AttentionGateOutputV0: Codable, Hashable {
  var schemaVersion: Int
  var attentionGateID: AttentionGateIDV0
  var attentionTenderID: AttentionTenderIDV0
  var speechOccupationID: SpeechOccupationIDV0
  var admitted: Bool
  var failure: AttentionGateFailureV0?
  var preSpeechFingerprint: SpeechFingerprintV0?
  var admittedSurface: AttentionSurfaceV0?
  var admittedChannel: AttentionChannelV0?
  var copyBudget: ExplanationCopyBudgetV0?
  var computedAt: Date
}

enum AttentionGateFailureV0: String, Codable {
  case noTenderedAttention
  case tenderExpired
  case surfaceScopeMismatch
  case channelNotTendered
  case occupationExceedsTender
  case notificationDeniedByDefault
  case frequencyLoadExceeded
  case emotionalSalienceTooHigh
  case identitySensitivityTooHigh
  case spendabilityMissing
  case noMoveLeft
  case userDialDenied
  case attentionProxyUntrusted
  case copyHonestyRejected
  case measurementStatusNotMeasured
}
```

Rules:

- AttentionGate output never admits state writes.
- D2 output never admits speech occupation.
- A staged witness card requires both gates when it speaks and writes.

### 8.8 `DepositionPromptV0` / `DepositionAnswerV0` — new in Plan 6

```swift
struct DepositionPromptV0: Codable, Hashable {
  var schemaVersion: Int
  var depositionID: DepositionIDV0
  var promptKind: DepositionPromptKindV0
  var subject: DepositionSubjectV0
  var factCellID: WitnessFactCellIDV0?
  var breakSignalID: BreakSignalIDV0?
  var closedPastOnly: Bool
  var questionCopy: String
  var answerOptions: [DepositionAnswerOptionV0]
  var attentionGateID: AttentionGateIDV0
  var measurementStatus: MeasurementStatusV0
  var createdAt: Date
  var expiresAt: Date?
}

enum DepositionPromptKindV0: String, Codable {
  case coldStartPastAdjudication
  case breakSelfConfession
  case attentionProxyCorrection
  case dialConsequenceReview
  case factMisreadCorrection
}

enum DepositionSubjectV0: String, Codable {
  case systemReadingOfPast
  case systemResidual
  case attentionProxy
  case userAuthoredDial
  case factCellTruth
}

struct DepositionAnswerOptionV0: Codable, Hashable {
  var optionID: DepositionAnswerOptionIDV0
  var label: String
  var reducedMeaning: DepositionReducedMeaningV0
}

enum DepositionReducedMeaningV0: String, Codable {
  case readingConfirmed
  case systemMisread
  case changedButDoNotGeneralize
  case temporaryStretch
  case stableNewConstraint
  case attentionNotActuallyTendered
  case attentionTenderAccepted
  case dialTooLoose
  case dialTooStrict
  case skip
}

struct DepositionAnswerV0: Codable, Hashable {
  var schemaVersion: Int
  var answerID: DepositionAnswerIDV0
  var depositionID: DepositionIDV0
  var selectedOptionID: DepositionAnswerOptionIDV0
  var responseSource: ProductVerdictResponseSourceV0
  var freeTextIncluded: Bool
  var measurementStatus: MeasurementStatusV0
  var createdAt: Date
}
```

Rules:

- Deposition is not an interview. It adjudicates a fact or the system's own error.
- Default answers are closed and typed.
- Free text is off by default and separately owner-gated.
- `changedButDoNotGeneralize` and `temporaryStretch` prevent the system from turning a correction into a broad portrait.

### 8.9 `SelfDoubtLedgerV0`, `BreakSignalV0`, and `ConfessionCardV0` — new in Plan 6

```swift
struct SelfDoubtLedgerV0: Codable, Hashable {
  var schemaVersion: Int
  var ledgerID: SelfDoubtLedgerIDV0
  var userScopeDigest: String
  var regionDigest: TimeRegionDigestV0
  var assertionDigests: [WitnessAssertionDigestV0]
  var predictedHoldBands: [ScoreBandV0]
  var observedHoldBands: [ScoreBandV0]
  var residualBand: ScoreBandV0
  var residualTrendBand: ScoreBandV0
  var calibrationVersion: SelfDoubtCalibrationVersionV0
  var lastUpdatedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct BreakSignalV0: Codable, Hashable {
  var schemaVersion: Int
  var breakSignalID: BreakSignalIDV0
  var ledgerID: SelfDoubtLedgerIDV0
  var regionDigest: TimeRegionDigestV0
  var residualBand: ScoreBandV0
  var thresholdBand: ScoreBandV0
  var slowWitnessSuppression: SlowWitnessSuppressionV0
  var triggerReason: BreakTriggerReasonV0
  var userPortraitFree: Bool
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum SlowWitnessSuppressionV0: String, Codable {
  case notSuppressed
  case suppressRegion
  case suppressFamily
  case suppressUntilDeposition
  case suppressUntilNewEvidence
}

enum BreakTriggerReasonV0: String, Codable {
  case ownAssertionResidualRise
  case repeatedFactCellMisread
  case attentionProxyCorrection
  case dialAuditFailure
  case notMeasured
}

struct ConfessionCardV0: Codable, Hashable {
  var schemaVersion: Int
  var confessionID: ConfessionIDV0
  var breakSignalID: BreakSignalIDV0
  var attentionGateID: AttentionGateIDV0
  var subject: DepositionSubjectV0
  var confessionCopy: String
  var depositionID: DepositionIDV0?
  var measurementStatus: MeasurementStatusV0
  var createdAt: Date
  var expiresAt: Date?
}
```

Rules:

- `userPortraitFree` must be true for public confession.
- Confession copy must use first-person system subject.
- A break signal suppresses slow witness placement in scope until resolved by policy.

### 8.10 `DisposableTranscriptV0` — new in Plan 6

```swift
struct DisposableTranscriptV0: Codable, Hashable {
  var schemaVersion: Int
  var transcriptID: DisposableTranscriptIDV0
  var sourceFactCellIDs: [WitnessFactCellIDV0]
  var contextID: RecommendationContextIDV0
  var modelVisiblePayloadDigest: String
  var readOnly: Bool
  var templated: Bool
  var backWritePermitted: Bool
  var expiresAt: Date
  var destroyedAt: Date?
  var measurementStatus: MeasurementStatusV0
}
```

Rules:

- `readOnly == true`.
- `templated == true`.
- `backWritePermitted == false`.
- Expiry is enforced; expired transcripts cannot condition future calls.
- Logs retain digests and lineage, not raw model-visible user facts, unless separately approved for privacy-safe audit.

### 8.11 `PhaseGateV0` and `GenomeTemplateProposalV0` — new in Plan 6

```swift
struct PhaseGateV0: Codable, Hashable {
  var schemaVersion: Int
  var phaseGateID: PhaseGateIDV0
  var currentPhase: SystemPhaseV0
  var runQuiesced: Bool
  var proposalQueueDigest: String
  var ownerGateID: OwnerGateIDV0
  var topologyAuditID: TopologyAuditIDV0
  var startedAt: Date
  var completedAt: Date?
  var measurementStatus: MeasurementStatusV0
}

enum SystemPhaseV0: String, Codable {
  case run
  case writeQuiesce
  case writeTemplateReview
  case writeApply
  case rollback
}

struct GenomeTemplateProposalV0: Codable, Hashable {
  var schemaVersion: Int
  var templateProposalID: GenomeTemplateProposalIDV0
  var proposalKind: GenomeTemplateProposalKindV0
  var source: TemplateProposalSourceV0
  var typedPayloadDigest: String
  var arbitraryCodeIncluded: Bool
  var fixedDimension: Bool
  var rangeCheckStatus: RangeCheckStatusV0
  var geneImpact: [GenomeGeneV0]
  var ownerGateID: OwnerGateIDV0?
  var measurementStatus: MeasurementStatusV0
  var createdAt: Date
}

enum GenomeTemplateProposalKindV0: String, Codable {
  case factCellSchema
  case organWeightVector
  case gammaBound
  case preferenceProjection
  case attentionPolicyDial
  case userAccountabilityWidening
}

enum TemplateProposalSourceV0: String, Codable {
  case shadowOrganLab
  case releaseOwner
  case userAmendmentPetition
  case rollback
}

enum GenomeGeneV0: String, Codable {
  case stateConservation
  case attentionConservation
  case privacyConservation
  case noPortraitPersistence
  case phaseSeparation
}

enum RangeCheckStatusV0: String, Codable {
  case passed
  case failed
  case ownerReviewRequired
  case notMeasured
}
```

Rules:

- Run phase and write phase are disjoint.
- Metabolism may queue proposals; it cannot apply them.
- Proposals are typed templates, not arbitrary code.
- Weight vectors must be fixed-dimension and range-checked.
- Any gene-impacting change requires owner review; user petitions can widen accountability, not loosen machine obligations.

### 8.12 `UserTimeModelDialV0` and `DialWagerAuditV0` — new in Plan 6

```swift
struct UserTimeModelDialV0: Codable, Hashable {
  var schemaVersion: Int
  var dialID: UserTimeModelDialIDV0
  var userScopeDigest: String
  var dialKind: UserTimeModelDialKindV0
  var currentSettingBand: ScoreBandV0
  var authoredByUser: Bool
  var sourceDepositionID: DepositionIDV0?
  var affectsGenome: Bool
  var affectsMetabolism: Bool
  var effectiveFrom: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}

enum UserTimeModelDialKindV0: String, Codable {
  case breakThreshold
  case attentionWidth
  case witnessFamilyEnablement
  case notificationSubscriptionScope
  case spendabilityStrictness
  case identityCopyStrictness
  case dialAuditCadence
}

struct DialWagerAuditV0: Codable, Hashable {
  var schemaVersion: Int
  var auditID: DialWagerAuditIDV0
  var dialID: UserTimeModelDialIDV0
  var moldTime: Date
  var liveWindow: RecommendationWindowV0
  var consequenceFactCellID: WitnessFactCellIDV0?
  var witnessedToUser: Bool
  var attentionGateID: AttentionGateIDV0?
  var userKeptDial: Bool?
  var measurementStatus: MeasurementStatusV0
}
```

Rules:

- Dials author the metabolism, not the genome.
- A dial change must have a future audit opportunity unless it is a pure immediate preference toggle.
- The system must be able to show what the dial caused the user to stop seeing or see more often.
- User cannot loosen state, attention, privacy, no-portrait, or phase-separation genes.

### 8.13 `AmendmentPetitionV0` — new in Plan 6

```swift
struct AmendmentPetitionV0: Codable, Hashable {
  var schemaVersion: Int
  var petitionID: AmendmentPetitionIDV0
  var userScopeDigest: String
  var requestedPartitionChange: PartitionChangeV0
  var rationaleReduced: AmendmentRationaleV0
  var widensMachineAccountability: Bool
  var loosensMachineObligation: Bool
  var phaseGateID: PhaseGateIDV0?
  var ownerGateID: OwnerGateIDV0?
  var decision: AmendmentDecisionV0
  var measurementStatus: MeasurementStatusV0
  var createdAt: Date
}

enum PartitionChangeV0: String, Codable {
  case moveAttentionProxyFromGenomeToDial
  case makeWitnessFamilyUserDialable
  case makeSpeechCadenceStricter
  case makeCopyIdentityBudgetStricter
  case requestDataDeletionOrReset
  case unsupported
}

enum AmendmentRationaleV0: String, Codable {
  case attentionProxyWrong
  case tooMuchSpeech
  case tooLittleSpeech
  case identityTooSpecific
  case resetModel
  case otherTyped
}

enum AmendmentDecisionV0: String, Codable {
  case pending
  case accepted
  case rejectedWouldLoosenLeash
  case rejectedUnsafe
  case ownerReviewRequired
}
```

Rules:

- Amendment petitions are not hidden settings churn. They are phase-gated accountability changes.
- Petitions may make the machine stricter or move safe dials into user control.
- Petitions may not let the user authorize the agent to bypass confirm taps, attention conservation, privacy floor, or no-portrait persistence.

### 8.14 `WitnessOrganV0` and `ShadowOrganEvaluationV0` — new in Plan 6

```swift
struct WitnessOrganV0: Codable, Hashable {
  var schemaVersion: Int
  var organID: WitnessOrganIDV0
  var organKind: WitnessOrganKindV0
  var factFamilies: [WitnessFactFamilyV0]
  var modelVersion: String
  var guidancePolicyID: RewardGuidancePolicyIDV0?
  var phaseGateID: PhaseGateIDV0?
  var effectiveFrom: Date?
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}

enum WitnessOrganKindV0: String, Codable {
  case witnessOfYouSlow
  case witnessOfItselfFast
}

struct ShadowOrganEvaluationV0: Codable, Hashable {
  var schemaVersion: Int
  var evaluationID: ShadowOrganEvaluationIDV0
  var organID: WitnessOrganIDV0
  var validatorKind: WitnessOrganValidatorKindV0
  var closedPastWindow: RecommendationWindowV0
  var heldOutCohortID: EvaluationCohortIDV0
  var worldFitLiftBand: ScoreBandV0?
  var residualCalibrationBand: ScoreBandV0?
  var falseAlarmBand: ScoreBandV0?
  var missedBreakBand: ScoreBandV0?
  var attentionRegretBand: ScoreBandV0?
  var recommendedAction: WitnessOrganActionV0
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
}

enum WitnessOrganValidatorKindV0: String, Codable {
  case closedPastWorldFit
  case closedPastResidualCalibration
}

enum WitnessOrganActionV0: String, Codable {
  case noAction
  case promoteShadow
  case reduceGamma
  case suppressAtBreak
  case rollback
  case ownerReviewRequired
}
```

Rules:

- Slow organs graduate by held-out past world-fit and live non-regret.
- Fast organs graduate by residual calibration, false-alarm control, and missed-break control.
- At a break, slow organs are suppressed; fast confession remains possible if AttentionGate admits.

### 8.15 `MeasurementStatusV0` additions

Plan 6 extends measurement statuses:

```swift
enum MeasurementStatusV0: String, Codable {
  case measured
  case notMeasured
  case lineageMissing
  case fingerprintMissing
  case provenanceMissing
  case staleWindowExpired
  case classifierCoupled
  case coverageInsufficient
  case ownerGateRequired
  case contestationMissing
  case createdEventBoundaryViolation
  case revealedReconfirmationMissing
  case falsifierMissing
  case falsifierKillTriggered
  case attentionTenderMissing
  case attentionGateRejected
  case attentionProxyUntrusted
  case speechFingerprintMissing
  case factCellExpired
  case factCellTruthUnproven
  case spendabilityMissing
  case noMoveLeft
  case disposableTranscriptExpired
  case phaseGateRequired
  case phaseOverlapDetected
  case arbitraryTemplatePayloadDetected
  case userPortraitRisk
}
```

Non-`measured` status is never zero, never positive, and never permission.

## 9. D2 and the state admission wall

D2 is unchanged. Plan 6 adds AttentionGate beside it, not inside it.

```text
D2 answers: may this state-bearing artifact be staged and written if the user taps?
AttentionGate answers: may this speech occupy this attention now?
```

The gates are independent:

| Case | D2 | AttentionGate | Result |
|---|---:|---:|---|
| Valid write, no tendered attention | pass | fail | Do not show. |
| Valid speech, invalid write | fail | pass | May show fact without write action only if spendable/honest. |
| Invalid fact, valid attention | n/a | fail via copy/truth | Do not show. |
| Valid fact, valid write, valid attention | pass | pass | Show staged witness card with confirm action. |

### 9.1 D2 remains reward-free and attention-free

D2 input/output must not include:

```text
RewardModelOutputV0
EarnedAcceptanceRewardSignalV0
ContestationSignalV0 as authority
UserProductVerdictSignalV0 as authority
UserPreferenceEmbeddingV0 as authority
AttentionTenderV0 as state support
AttentionGateOutputV0 as state support
SelfDoubtLedgerV0 as state support
```

D2 may log IDs for lineage. It may not use them to admit.

### 9.2 AttentionGate remains state-free

AttentionGate input/output must not mint:

```text
AllowedActionV0
RecommendationVerdictV0
EvidenceReceiptV0
RecommendationCandidateSourceV0
Calendar write target
D2 provenance
```

AttentionGate can deny speech. It cannot make a write valid.

### 9.3 Hydration firewall extends to witness speech

The hydration firewall blocks model-authored:

```text
facts;
raw titles;
raw notes;
attendee / location strings;
concrete write fields;
evidence hashes;
source kind / strength;
provenance;
fingerprint;
verdict;
actions;
reward / contestation / attention scores;
product verdicts;
preference claims;
self-diagnoses about the user;
```

For witness cards, the model may select or rank cells. Swift hydrates the words.

## 10. End-to-end flows

### 10.1 Smooth witness placement flow

```mermaid
sequenceDiagram
  participant U as User
  participant C as Codex/UI
  participant S as Swift
  participant A as AttentionGate
  participant D as DiffusionGemma
  participant B as D2
  participant W as Write Tail
  participant M as Measurement

  U->>C: opens calendar grid / asks for current surface
  C->>S: bounded request + surface event
  S->>S: read private state; compute decision stats, relation chips, F(x)
  S->>S: mint WitnessFactCellV0 pantry from evidence
  S->>S: compute AttentionTenderV0 for opened surface
  S->>D: disposable transcript with non-identifying fact-cell summaries
  D-->>S: WitnessSelectionInfillV0
  S->>S: verify selected fact, spendability, copy honesty, expiry
  S->>A: SpeechOccupationV0 + AttentionTenderV0
  A-->>S: AttentionGateOutputV0 admitted / denied
  alt write-bearing one-time move
    S->>B: D2 validate support(staged) ⊆ F(x_live)
    B-->>S: D2BindingOutputV0 or typed failure
  end
  S-->>C: Swift-rendered WitnessDisclosureCardV0 if gates pass
  C-->>U: placed fact, not pushed
  U->>S: confirm / dismiss / verdict / dial adjustment
  S->>W: write only after confirm tap
  W->>M: outcome, contestation, attention regret, verdicts
```

### 10.2 Empty Saturday protect flow

```text
1. User opens Saturday in grid.
2. Swift computes narrow/medium A(tendered) for that visible date.
3. Swift detects a closed-past pattern: last three Saturdays filled by Thursday.
4. Swift mints a blank-protection fact cell.
5. DiffusionGemma selects the fact cell from the pantry.
6. Swift renders the witness card.
7. AttentionGate admits inline placement, denies push.
8. D2 validates optional hold/protect action.
9. User taps Protect, Dismiss, or Not needed.
10. Reward credit is contestation-aware; the main product win is a true fact placed without attention theft.
```

### 10.3 Cold-start deposition flow

```mermaid
sequenceDiagram
  participant U as User
  participant S as Swift
  participant A as AttentionGate
  participant D as Deposition
  participant P as Preference Store

  U->>S: first-run opens calendar / imports past
  S->>S: find one falsifiable closed-past fact; no interview
  S->>A: check attention tender for onboarding surface
  A-->>S: admitted / denied
  S->>D: DepositionPromptV0
  D-->>U: confirm-or-correct prompt
  U->>D: typed answer
  D->>P: update coverage / cold-start prior only within reduced meaning
  D->>S: no broad portrait, no copy claim
```

If no imported past exists, skip deposition and use population prior with low confidence.

### 10.4 Break confession flow

```mermaid
sequenceDiagram
  participant S as Swift
  participant L as Self-Doubt Ledger
  participant A as AttentionGate
  participant U as User
  participant D as Deposition Channel

  S->>L: update outcomes for previous witness assertions
  L-->>S: BreakSignalV0 if residual crosses threshold
  S->>S: suppress slow witness in affected region
  S->>A: request speech permission for system-subject confession
  A-->>S: admitted / denied
  alt admitted
    S-->>U: ConfessionCardV0 in tendered surface
    U->>D: typed correction / skip
    D-->>S: update self-doubt calibration, dials, or coverage
  else denied
    S->>S: keep suppression; wait for tendered attention
  end
```

### 10.5 Phase-gated growth flow

```text
RUN phase:
  live metabolism selects facts, composes non-authority shapes, updates self-doubt ledger,
  and queues typed proposals.

QUIESCE:
  live metabolism stops. No run-time loop can apply a genome or organ change.

WRITE phase:
  Genome Controller drains proposal queue.
  It checks template shape before content.
  It rejects arbitrary code, unfixed weight dimensions, gene-loosening changes, and portrait risk.
  It applies only owner-gated, range-checked templates.
  It re-instantiates metabolism.

RUN resumes.
```

### 10.6 User dial three-beat flow

```text
MOLD:
  User adjusts a dial enactively, inside a tendered surface.

LIVE:
  The dial affects witness placement, attention width, family enablement, or thresholds.

WITNESS THE MOLD:
  After a window, Swift may show a fact about the dial's consequence:
  "You widened this; over eight weeks, you saw fewer blank-protection witnesses."
```

The third beat prevents the present self from silently hiding information from the future self.

## 11. Learning, reward, contestation, and value under witness

### 11.1 What Plan 6 keeps from Plan 5

Plan 6 keeps:

```text
contestation-weighted earned acceptance;
revealed-reconfirmation brake;
created-event boundary in reverse;
product-verdict channel;
pre-registered comfortable-FP falsifier;
preference embedding u as non-identifying conditioning;
reward-guided sampling with bounded γ;
Diffusion-DPO as optional, offline, KL-leashed, non-v1-default;
measurement-before-mutation;
.notMeasured never zero.
```

### 11.2 What changes under witness

The primary output is not valued as “was this recommendation good?” It is evaluated along three axes:

```text
truth: was the fact true under admitted evidence?
attention: was the fact placed only into tendered attention?
spendability: could the user still do something with it, or was the surface explicitly reflective?
```

Reward can steer fact selection or shape composition only after those axes pass and lineage is measured.

### 11.3 Earned acceptance still matters for write-bearing moves

If a witness card offers a write-bearing move, plan-5 earned acceptance applies:

```text
behavioral_earned = accepted
                  AND survived-to-T
                  AND low edit-distance
                  AND no negative product verdict

reward_credit = behavioral_earned
              × contestation_weight
              × revealed_reconfirmation_multiplier
              × created_event_boundary
```

Witness does not let a valid fact launder an unearned write.

### 11.4 Attention regret

Plan 6 adds attention-specific measurement.

```swift
struct AttentionRegretSignalV0: Codable, Hashable {
  var schemaVersion: Int
  var signalID: AttentionRegretSignalIDV0
  var disclosureID: WitnessDisclosureIDV0
  var attentionTenderID: AttentionTenderIDV0
  var speechOccupationID: SpeechOccupationIDV0
  var immediateDismissal: Bool
  var negativeProductVerdict: Bool
  var attentionProxyCorrection: Bool
  var mutedFamilyAfterSpeech: Bool
  var disabledChannelAfterSpeech: Bool
  var repeatedSurfaceAvoidanceBand: ScoreBandV0
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
}
```

Rules:

- Attention regret can reduce γ, suppress a fact family, or tighten AttentionGate.
- It cannot train a user portrait.
- Missing attention regret is not positive evidence.
- Negative attention corrections are stronger than raw dwell or lack of dismissal.

### 11.5 Useful is not reassurance

Product verdicts remain typed controls, not system-worth questions. Positive `useful` may improve confidence only when truth, attention, spendability, and contestation coupling pass. Negative `notToday`, `wrong`, `notNeeded`, or attention-proxy correction zeroes or penalizes relevant reward.

### 11.6 Comfortable false positive under witness

Witness reduces but does not eliminate comfortable false positives. A true fact can still be unneeded. The residual becomes:

```text
a true, attention-admitted, spendable fact that the user accepts or ignores without regret,
but that did not actually help them see or do anything they needed.
```

No behavioral system fully identifies that. Plan 6 keeps the held-out falsifier and adds attention-regret stratification. The residual remains named.

### 11.7 Reward model scope

`RewardModelOutputV0` may score:

```text
predicted earned acceptance of write-bearing moves;
predicted non-regret of fact placement;
predicted attention regret;
predicted contestation / spendability bands;
```

It may not score:

```text
truth;
state validity;
speech permission;
source strength;
copy entitlement;
user worth;
```

High predicted reward cannot admit a false fact or occupy untendered attention.

## 12. Privacy, redaction, and copy honesty

### 12.1 Raw-content floor

Never crosses the model membrane by default:

```text
raw event titles;
free-text notes or descriptions;
attendee names, emails, identities;
exact locations or addresses;
raw user-history strings;
raw fact-cell truth preimages;
raw attention preimages;
raw self-doubt assertion text if identity-bearing;
raw product-verdict free text;
raw deposition free text;
raw reward lineage rows;
raw falsifier cohort membership.
```

### 12.2 No portrait of the user

Forbidden persisted machine claims:

```text
the user is avoiding someone;
the user dislikes mornings;
the user changed jobs;
the user values deep work;
the user is burned out;
the user is socially overloaded as an identity claim.
```

Allowed reduced, expiring, or user-authored forms:

```text
calendarDensity: high for this window;
socialLoad: high band for this day;
user dial says breakThreshold: stricter;
self-doubt ledger says my morning assertions failed four days running;
preference embedding vector digest with coverage and redaction risk.
```

### 12.3 Copy honesty for witness

Copy must pass all questions:

```text
Is the fact true under Swift evidence?
Would the fact be false on a different day or range?
Is every identity-bearing phrase inside copy budget?
Is the user able to spend the fact, or did they open a reflective surface?
Is the speech admitted by AttentionGate?
Does the copy avoid reward, contestation, learning, and surveillance claims?
Does the copy avoid converting self-doubt into a portrait of the user?
```

### 12.4 Forbidden user-facing claims

Forbidden unless explicitly supported by user-stated evidence and copy budget, and usually forbidden even then:

```text
We learned you like X.
You usually accept X.
People like you prefer X.
This has a high reward score.
This was highly contested.
You kept this over alternatives.
This is optimized for acceptance.
Your answer trains the system.
Your life changed.
You are avoiding this.
```

Allowed witness style:

```text
This moved four times.
The blank has filled late three Saturdays in a row.
I've been wrong about this region lately.
I'll stop using this pattern unless you correct me.
```

## 13. User authorship, dials, and the amendment clause

### 13.1 Who holds which pen

Plan 6 separates pens:

```text
Genome author: holds the topology / phase-gate pen, writes once under review, and leaves an auditable graph.
Machine: holds the pen over its own self-doubt, and nothing user-portrait-like that persists.
User: holds the pen over the metabolism of their time model: dials, thresholds, attention widths, enabled families, corrections.
```

The user's pen does not loosen the agent's leash. It shapes the medium within the leash.

### 13.2 User dials are not interviews

Dials are enactive. They are changed in use, in context, with consequence. They are not abstract self-theory prompts.

Good:

```text
Show fewer witnesses about blank protection.
Only place break confessions in the reflection view.
Treat attention as narrow unless I open details.
Make identity copy stricter.
```

Bad:

```text
Tell us what kind of person you are.
What do you value most in your calendar?
Do you prefer deep work?
```

### 13.3 Three-beat wager

Every consequential dial follows:

```text
mold -> live -> witness the mold
```

The future self must be able to collect from the present self's adjustment. If a dial made the system quieter, the system must be able to show, in a tendered audit surface, what became quieter.

### 13.4 Genome is not user-editable

The user cannot authorize:

```text
auto-write without confirm;
writing unsupported state;
speech into untendered attention;
raw private leakage;
persistent user portraits;
live metabolism rewriting genes;
reward becoming admission.
```

This is not paternalism over the user. The genome binds the agent, not the user. A fiduciary's loyalty cannot be waived mid-con by the party being protected.

### 13.5 Amendment clause

The partition between genome and metabolism is authored power. Plan 6 therefore adds petitions:

```text
The user may petition to move safe accountability surfaces into dials.
The petition crosses only in write phase.
It must widen machine accountability or user control.
It must not loosen machine obligations.
```

Example accepted petitions:

```text
Make attention proxy stricter and user-dialable.
Make identity copy budget stricter.
Disable a witness family globally.
Reset preference embedding.
```

Example rejected petitions:

```text
Allow push witnesses without explicit tender.
Let the system write automatically.
Let model drafts appear directly.
Let private notes cross to improve personalization.
```

### 13.6 Passive-user residual

Plan 6 does not pretend every user becomes an author. Many users will never touch a dial. They receive the consumer branch by default: a carefully authored witness whose thresholds were set by product owners and adjusted by safe measurement.

It is forbidden to tell passive users they authored their own model. The product may offer authorship. It may not claim uptake.

## 14. Phase gate, disposable transcripts, and shadow growth

### 14.1 Capability security is necessary but insufficient

The model and reward path must not hold references to:

```text
fact-cell minter;
gene table;
D2 verdict mutators;
AttentionGate overrides;
calendar write mutators;
phase-gate apply function;
raw private state stores.
```

But withholding references is not enough. The proposal pipe can become a mutator if it carries arbitrary behavior. Therefore Plan 6 adds phase separation and typed templates.

### 14.2 Run phase

In run phase, the metabolism may:

```text
select fact cells;
compose non-authority shapes;
compute reward predictions;
update self-doubt ledger;
queue typed template proposals;
record measurement lineage;
```

It may not:

```text
mint fact cells;
change genes;
apply weights to public model;
change D2 or AttentionGate;
write calendar;
persist raw user facts;
```

### 14.3 Write phase

In write phase, live metabolism is quiesced. The genome controller may review typed templates:

```text
fact-cell schemas;
fixed-dimension organ weights;
γ bounds;
preference projection changes;
attention policy dials;
user-accountability-widening petitions;
rollbacks.
```

Rejection is mandatory for:

```text
arbitrary code;
free-form model prompts that act as policy;
unfixed weight dimensions;
gene-loosening changes;
portrait risk;
missing owner gate;
missing falsifier / contestation / attention reports;
phase overlap;
```

### 14.4 Disposable transcripts

Any user fact crossing from Swift to model-visible metabolism is a disposable transcript. Expiry is not a cleanup optimization; it is a privacy and no-portrait requirement.

If transcripts do not expire, the model-visible lane accumulates a user portrait. That is a plan-6 violation.

### 14.5 Shadow growth has two validators

Slow witness-of-you organs are validated by held-out closed-past world-fit. They are legitimate only while the world is smooth.

Fast witness-of-itself organs are validated by residual calibration. They do not predict the new world. They predict when CalAgent's own old assertions are failing.

At a break:

```text
slow organ suppressed;
fast confession may run if AttentionGate admits;
re-deposition begins new evidence collection;
no organ pretends to know the new regime before the user or outcomes supply it.
```

### 14.6 Closed past is not a free lunch

The closed past is safe because it cannot be harmed. It is not automatically representative. Any evaluation using closed past must state whether it validates continuity or error calibration. Do not graduate a slow organ for a break surface because it fit a dead regime.

## 15. User experience invariants

### 15.1 Felt safety

The user should feel:

```text
the product sees patterns without naming more than it must;
the product places facts only where the user is already looking;
the product does not beg for usefulness judgments;
the product can admit when it is stale;
the product never writes without a tap;
the product never touches non-created calendar objects;
the product can be corrected without requiring a self-theory.
```

### 15.2 Place, never send by default

Default witness delivery is placement in a tendered surface:

```text
calendar glyph;
inline card;
detail panel;
reflection view;
undo surface;
chat answer to a user question.
```

Default denied delivery:

```text
push notification;
modal interruption;
badge designed to create anxiety;
email digest not explicitly subscribed;
copy that says the system withheld a thought to advertise restraint.
```

### 15.3 One card, one fact, one move

A witness card should avoid bundles. Bundles become persuasion. Default:

```text
one fact;
one explanation of why it is easy to miss;
one optional next move;
clear dismiss / verdict / dial controls.
```

### 15.4 No accusation design

A fact about the user can feel accusatory even when true. Mitigations:

```text
prefer pattern over blame;
use system-subject confession at breaks;
ensure spendability;
avoid identity unless essential and budgeted;
allow Not needed / Wrong / Stop showing this family;
never infer motive.
```

### 15.5 Deposition UX

Deposition prompts should be:

```text
short;
falsifiable;
about one closed-past fact or the system's own residual;
typed-answer by default;
non-charming;
non-generalizing;
optional to skip.
```

### 15.6 Dial UX

Dials should be shown in context, not as personality setup. When a user changes a dial, record a future audit opportunity. A dial with no consequence witness is a silent lever and should not be considered authoring.

## 16. Migration sequence

Plan 6 replaces plan-5 §16 with a witness-safe sequence. Plan-5 reward and learning milestones are preserved, but speech and fact-cell milestones come first because the product verb changes.

### M0 — Doctrine, wall freeze, and compatibility aliases

- Adopt Plan 6 as canonical.
- Mark `plan-5-revised.md` superseded but inherited for safety mechanics.
- Add state, speech, privacy, and persistence laws to architecture docs.
- Add compatibility map from `Recommendation*` code names to witness product language.
- Add lints that reward, contestation, attention, self-doubt, and learning terms cannot appear in user copy.
- Assert D2 unchanged and AttentionGate separate.

Acceptance:

```text
one locatable doctrine;
three conservation lines;
persistence law;
role map;
D2 unchanged;
AttentionGate specified;
no user-facing recommender/value copy in new surfaces.
```

### M1 — Attention instrumentation and speech gate shadow

- Implement `AttentionTenderV0`, `SpeechOccupationV0`, and `AttentionGateOutputV0` shadow-only.
- Classify surfaces and default tender widths.
- Deny push by default.
- Add pre-speech fingerprints.
- Add attention-regret signal skeleton.

Acceptance:

```text
speech admission can be replayed from event stream;
foreground alone does not create broad tender;
missing tender denies speech;
attention gate cannot mint writes;
D2 cannot mint speech permission.
```

### M2 — Fact-cell pantry and Swift cantor shadow

- Implement `WitnessFactCellV0` for initial families.
- Implement Swift-rendered templates.
- Build fact truth, copy, privacy, spendability, and TTL checks.
- Feed DiffusionGemma only disposable, non-identifying summaries.
- Model selects fact-cell index only.

Acceptance:

```text
model cannot author facts or final copy;
fact cells bind to evidence receipts;
raw private strings do not cross;
expired facts cannot be selected;
noMoveLeft blocks ordinary placement.
```

### M3 — Public smooth witness placement in SELECT

- Launch one low-risk family, such as blank protection, in opened calendar surfaces only.
- Place, never send.
- If write-bearing, D2 and confirm tap are required.
- Add typed product verdicts and family mute controls.

Acceptance:

```text
AttentionGate pass required for every shown fact;
D2 pass required for every write action;
negative verdicts and attention corrections suppress family;
no push;
copy honesty audit pass.
```

### M4 — Cold-start deposition

- Build `DepositionPromptV0` for imported closed-past facts.
- Use typed answer options only.
- No generic preference interview.
- If no past exists, use population prior with low confidence.

Acceptance:

```text
deposition narrows cold start but does not claim to solve it;
answers reduce to typed meanings;
no free text by default;
no broad portrait update;
user can skip.
```

### M5 — Self-doubt ledger and break shadow

- Implement `SelfDoubtLedgerV0` and `BreakSignalV0` shadow-only.
- Track prior witness assertions and outcomes.
- Calibrate residual thresholds on closed past.
- Suppress slow witness in shadow when residual crosses threshold.

Acceptance:

```text
break detection uses only system's own assertion ledger;
no user-portrait predicates;
false alarm / missed break metrics reported;
slow-family suppression can be replayed.
```

### M6 — Public break confession in tendered surfaces

- Add `ConfessionCardV0` with system-subject copy.
- Display only when AttentionGate admits.
- Open deposition for correction.
- Keep slow witness suppressed in affected scope until policy resolves.

Acceptance:

```text
confession copy says what the system got wrong;
no claim that the user's life changed;
no notification push by default;
deposition answers update calibration or dials, not a portrait.
```

### M7 — Plan-5 reward and contestation under witness

- Connect attention-regret signals to plan-5 reward reduction.
- Preserve `ContestationSignalV0`, `EarnedAcceptanceRewardSignalV0`, product verdicts, and falsifier.
- Train `u` from measured, contestation-corrected, attention-safe outcomes only.
- Shadow reward-guided fact selection with bounded γ.

Acceptance:

```text
raw survival cannot train reward;
positive useful cannot overcome zero contestation or attention regret;
negative product verdicts penalize;
γ=0 recovers unguided witness selection;
RewardModelOutput absent from D2 and AttentionGate authority.
```

### M8 — Phase gate and disposable transcript enforcement

- Implement `DisposableTranscriptV0` expiry and audit.
- Implement `PhaseGateV0` and typed template proposal review.
- Add topology audit for forbidden references.
- Quiesce run phase before applying organ/guidance/schema changes.

Acceptance:

```text
no live run/write overlap;
model/reward path holds no minter or gene-table reference;
arbitrary code templates rejected;
fixed-dimension weight vectors range-checked;
expired transcripts cannot condition future calls.
```

### M9 — Shadow organs and two-validator growth

- Add `WitnessOrganV0` and `ShadowOrganEvaluationV0`.
- Evaluate slow organs by closed-past world-fit.
- Evaluate fast organs by residual calibration.
- Require slow suppression at break.

Acceptance:

```text
slow organ not graduated for break behavior;
fast organ does not predict new regime, only error;
closed-past fit report states validator kind;
owner gate required for promotion.
```

### M10 — User dials and three-beat wager

- Implement `UserTimeModelDialV0`, `DialWagerAuditV0`, and family controls.
- Expose dials in context.
- Show dial consequence audits in tendered reflection surfaces.
- Add passive-user framing rules.

Acceptance:

```text
dials affect metabolism only;
genes cannot be loosened;
consequences can be witnessed later;
passive users are not told they authored their model.
```

### M11 — Amendment petitions

- Implement `AmendmentPetitionV0` for safe partition changes.
- Owner-gate petitions through write phase.
- Accept only changes that widen accountability or user control without loosening the agent's obligations.

Acceptance:

```text
petition cannot allow auto-write, untendered speech, raw leakage, model-authored copy, or reward-as-authority;
accepted petitions are phase-gated;
rejections are typed.
```

### M12 — Public per-family PROPOSE / guidance

- Promote one witness family at a time.
- Require current D2 parity, AttentionGate report, contestation distribution, drift report, attention-regret report, and falsifier.
- Keep SELECT fallback and γ=0 rollback.

Acceptance:

```text
public guidance cannot widen F(x), invent facts, or occupy untendered attention;
low-contestation reward share below threshold;
attention-regret rate below threshold;
held-out not-needed falsifier not tripped;
owner-approved rollback path.
```

## 17. Test matrix

| Test | Target | Milestone | Invariant |
|---|---|---:|---|
| `testPlan6SupersedesPlan5Revised` | docs | M0 | Plan 6 canonical; plan 5 inherited for safety. |
| `testThreeConservationLinesExist` | docs | M0 | State, speech, privacy laws present. |
| `testPersistenceLawExists` | docs | M0 | User facts disposable; self residual persistent. |
| `testD2Unchanged` | D2 | all | State wall preserved. |
| `testAttentionGateSeparateFromD2` | architecture | M1+ | Speech and state gates cannot launder each other. |
| `testOccupationSubsetTenderedAttention` | attention | M1+ | Speech denied without sufficient tender. |
| `testForegroundAloneNotWideTender` | attention | M1+ | Foreground proxy is not broad consent. |
| `testPushDeniedByDefault` | attention | M1+ | Placement default, no send. |
| `testAttentionTenderExpires` | attention | M1+ | Speech permission short-lived. |
| `testSpeechOccupationIncludesModalForce` | attention | M1+ | Occupation models force, not just text. |
| `testFactCellEvidenceBound` | fact cells | M2+ | Every fact binds to receipts. |
| `testFactCellNoRawIdentityModelVisible` | privacy | M2+ | Fact summaries are non-identifying. |
| `testSwiftRendersWitnessCopy` | copy | M2+ | Model does not write final copy. |
| `testWitnessSelectionIndexInRange` | model output | M2+ | SELECT-style fact selection integrity. |
| `testExpiredFactCellRejected` | fact cells | M2+ | TTL enforced. |
| `testNoMoveLeftBlocksPlacement` | spendability | M2+ | True facts without spendable move suppressed outside reflection. |
| `testWitnessCardRequiresAttentionGate` | UI | M3+ | Every shown fact has speech admission. |
| `testWriteBearingWitnessRequiresD2` | state | M3+ | Every write action passes D2. |
| `testProtectBlankWritesOnlyAfterTap` | write | M3+ | No auto-write. |
| `testProductVerdictProductDirected` | UX | M3+ | Verdict labels audit product, not user. |
| `testNoWasThisUsefulPromptByDefault` | UX | M3+ | System does not ask for reassurance. |
| `testDepositionClosedPastOnly` | deposition | M4+ | Cold-start prompt adjudicates past fact. |
| `testDepositionNotInterview` | deposition | M4+ | No abstract self-theory questions. |
| `testDepositionTypedAnswersDefault` | privacy | M4+ | No free text by default. |
| `testColdStartNoPastFallsBackLowConfidence` | personalization | M4+ | Deposition narrows; does not solve empty-handed cold start. |
| `testSelfDoubtLedgerSubjectIsSystem` | break | M5+ | Persistent self-model is about CalAgent error. |
| `testBreakSignalNoUserPortraitPredicates` | break | M5+ | No “life changed” inference. |
| `testSlowWitnessSuppressedAtBreak` | break | M5+ | Stale slow organ loses license. |
| `testConfessionFirstPersonSystemSubject` | copy | M6+ | Break copy confesses system error. |
| `testConfessionRequiresTenderedAttention` | attention | M6+ | No pushed confession by default. |
| `testAttentionProxyCorrectionUpdatesPolicyNotPortrait` | deposition | M6+ | User reports proxy gap without portrait learning. |
| `testRawSurvivalCannotTrainWitnessReward` | reward | M7+ | Contestation and attention required. |
| `testPositiveUsefulCannotOvercomeAttentionRegret` | reward | M7+ | Useful does not launder attention theft. |
| `testNegativeVerdictPenalizesReward` | reward | M7+ | Not today / wrong / not needed suppress. |
| `testRewardModelOutputAbsentFromD2AndAttentionGateAuthority` | reward | M7+ | Reward cannot admit state or speech. |
| `testGammaZeroRecoversUnguidedWitness` | sampler | M7+ | Guidance reversible. |
| `testDisposableTranscriptExpires` | transcript | M8+ | Model-visible user facts do not persist. |
| `testDisposableTranscriptReadOnly` | transcript | M8+ | No back-write. |
| `testMetabolismNoMinterReference` | topology | M8+ | Capability graph withholds fact minter. |
| `testMetabolismNoGeneTableReference` | topology | M8+ | Learning cannot edit laws live. |
| `testRunWritePhaseDisjoint` | phase gate | M8+ | No live run/write overlap. |
| `testArbitraryTemplatePayloadRejected` | phase gate | M8+ | Proposal pipe cannot carry code. |
| `testFixedDimensionOrganWeights` | phase gate | M8+ | Weight templates range-checkable. |
| `testSlowOrganValidatedByWorldFitOnly` | shadow | M9+ | Slow organ not certified for breaks. |
| `testFastOrganValidatedByResidualCalibration` | shadow | M9+ | Fast organ predicts own error, not user regime. |
| `testClosedPastEvaluationStatesValidatorKind` | eval | M9+ | No ambiguous “past fit” claims. |
| `testUserDialAffectsMetabolismOnly` | dials | M10+ | Dials cannot loosen genes. |
| `testDialWagerAuditExists` | dials | M10+ | Mold-live-witness enforced. |
| `testPassiveUserNotFramedAsAuthor` | UX | M10+ | Authorship claims require uptake. |
| `testAmendmentCannotLoosenLeash` | amendment | M11+ | User cannot waive agent obligations. |
| `testAcceptedAmendmentPhaseGated` | amendment | M11+ | Partition changes cross write phase. |
| `testPublicFamilyRequiresAttentionReport` | release | M12 | Speech loop review current. |
| `testPublicFamilyRequiresContestationReport` | release | M12 | Plan-5 loop review current. |
| `testPublicFamilyRequiresFalsifier` | release | M12 | Remedy can fail outside metric. |
| `testPublicGuidanceCannotInventFacts` | release | M12 | Model remains selector/composer, not fact author. |
| `testCopyHonestyBlocksLearningClaims` | copy | all | No “we learned you” language. |
| `testCopyHonestyBlocksRewardContestationAttentionScores` | copy | all | Internal metrics never surface. |
| `testNotMeasuredNeverZero` | measurement | all | Missing data cannot promote or penalize. |
| `testComfortableFalsePositiveResidualNamed` | docs | all | Residual not claimed solved. |
| `testAttentionProxyBlindSpotNamed` | docs | all | Real attention gap disclosed in architecture. |

## 18. Definition of done

- [ ] Plan 6 opens with one doctrine, one architecture law, three conservation lines, and a persistence law.
- [ ] Plan 5's state wall, D2, hydration firewall, confirm tap, no-auto-write, no-touch-non-created-events, privacy floor, contestation reward, product verdict, and falsifier remain unchanged in force.
- [ ] AttentionGate exists and enforces `occupation(spoken) ⊆ A(tendered)`.
- [ ] D2 and AttentionGate cannot launder authority into each other.
- [ ] Witness product grammar is `what's true / why you may not see it / what you can still do once`.
- [ ] Default delivery is placement, not push.
- [ ] Push witnesses are denied by default and require user-authored tender plus stricter policy.
- [ ] `WitnessFactCellV0` exists and is evidence-bound, privacy-budgeted, spendability-checked, TTL-bound, and Swift-rendered.
- [ ] DiffusionGemma may select/rank fact cells but cannot author facts or final witness copy.
- [ ] Swift cantor renders final copy from templates and evidence.
- [ ] A fact with no spendable move is suppressed outside explicitly reflective surfaces.
- [ ] Deposition exists as a closed-past or system-residual adjudication channel, not an interview.
- [ ] Cold start uses deposition only when there is an imported past; otherwise population prior remains low-confidence.
- [ ] Self-doubt ledger persists only system-error claims, not user portraits.
- [ ] Break signals are triggered by CalAgent's own residual, not inferred life changes.
- [ ] At a break, slow witness-of-you organs are suppressed and only system-subject confession may run.
- [ ] Confession requires tendered attention and opens deposition.
- [ ] Disposable transcripts are read-only, templated, expiring, and not back-written.
- [ ] Phase gate separates run and write phases; proposals are typed templates, not arbitrary behavior.
- [ ] Capability topology withholds fact minter, gene table, D2 mutators, AttentionGate overrides, and write mutators from metabolism.
- [ ] Shadow growth uses two validators: world-fit for slow organs and residual calibration for fast organs.
- [ ] User dials author metabolism only and follow the mold-live-witness three-beat.
- [ ] Amendment petitions can widen accountability or user control but cannot loosen the agent's obligations.
- [ ] Passive users are not framed as authors of their model.
- [ ] Attention regret is measured and can suppress families or guidance.
- [ ] Positive product verdicts cannot overcome zero contestation or attention regret.
- [ ] Negative product verdicts and attention-proxy corrections penalize reward.
- [ ] Reward outputs cannot appear as D2 authority, AttentionGate authority, or user copy.
- [ ] Public guidance requires current D2 parity, AttentionGate report, contestation distribution, drift report, attention-regret report, and comfortable-FP falsifier.
- [ ] `.notMeasured` is never zero.
- [ ] The comfortable false positive and attention-proxy blind spot remain named residual risks.

## 19. Changelog / deprecation map

### 19.1 Plan-5-revised.md map

| Plan-5 area | Plan-6 disposition | Kept | Changed / superseded |
|---|---|---|---|
| Governing doctrine | Rewritten | Capability separated from authority; Swift sovereign | Product verb changes from recommendation manufacturing to witness disclosure. |
| D2 wall | Kept bit-for-bit | `support(staged) ⊆ F(x_live)` | Adds AttentionGate beside D2, not inside it. |
| Value proposition | Superseded | Learning under unverified value remains honest | Product no longer asserts value first; it discloses facts first. |
| SELECT / PROPOSE | Kept and extended | SELECT as low-blast-radius curriculum; PROPOSE target | Adds fact-cell SELECT as default speech lane. |
| Pantry membrane | Kept | Decision-sufficient, non-identifying projection | Adds disposable transcripts and no-portrait persistence. |
| Relational Prep Station | Kept | Swift-owned, non-learning | May feed fact-cell minter; remains non-authoritative. |
| Canonical contracts | Expanded | All plan-5 contracts remain | Adds witness, attention, deposition, self-doubt, phase-gate, dials, shadow-organ contracts. |
| Reward and contestation | Kept | Contestation-weighted earned acceptance | Adds attention-regret and truth/attention/spendability axes. |
| Product verdict | Kept and reframed | Typed useful / not today / wrong / not needed | No default “Was this useful?” solicitation; verdict is product-directed control. |
| Comfortable-FP falsifier | Kept | External kill condition | Adds attention-regret stratification. |
| Migration | Replaced | Shadow-first, owner-gated, SELECT fallback | New M0-M12 sequence starts with attention and fact cells. |
| Test matrix | Expanded | D2, membrane, reward, `.notMeasured`, falsifier tests | Adds AttentionGate, fact-cell, deposition, self-doubt, phase-gate, dial, amendment tests. |
| Self-audit | Expanded | Wall coverage and loop coverage | Adds attention coverage, no-portrait persistence, phase gate, user authorship, passive-user honesty. |

### 19.2 Witness document map

| Witness claim | Plan-6 disposition |
|---|---|
| Stop recommending; start witnessing | Canonized as product verb. |
| `occupation(spoken) ⊆ A(tendered)` | Canonized as AttentionGate. |
| Place, never send | Canonized as default delivery policy. |
| Changed card: what's true / why can't see it / what might do once | Canonized as `WitnessDisclosureCardV0`. |
| Deposition, not interview | Canonized as `DepositionPromptV0`. |
| Cold start narrows, does not solve | Canonized in M4 and §6.4. |
| Two tempos | Canonized as smooth witness and break confession. |
| Break detected by system's own residual | Canonized as `SelfDoubtLedgerV0` and `BreakSignalV0`. |
| No portrait of the user | Canonized as persistence law. |
| Disposable transcripts | Canonized as `DisposableTranscriptV0`. |
| Phase gate / typed templates | Canonized as `PhaseGateV0` and `GenomeTemplateProposalV0`. |
| Shadow growth needs two validators | Canonized as `WitnessOrganV0` / `ShadowOrganEvaluationV0`. |
| User holds the pen | Canonized as user dials and amendment petitions. |
| Passive-user and attention-proxy residuals | Canonized as named residual risks. |

### 19.3 Product language deprecations

| Deprecated | Replacement |
|---|---|
| Recommendation-first framing | Witness/disclosure-first framing. |
| “What should we put in your time?” | “What is already true about your time that you cannot see?” |
| “Was this useful?” as default prompt | Product-directed controls: Useful / Not today / Wrong / Not needed. |
| “We learned you like X” | No equivalent. Use evidence-bound facts or remain silent. |
| “Permission to rest” as north star | Facts that make time legible; rest may be one spendable move. |
| Push notification for withheld card | Found object in tendered surface, or nothing. |
| Generic onboarding preference interview | Closed-past deposition when evidence exists. |

## 20. Deliberately preserved safety invariants

| Preserved invariant | Plan-6 statement |
|---|---|
| Model never authors authority fields | Still true for state; extended to fact and speech fields. |
| D2 is single in-process admission seam for state | Unchanged. |
| `RecommendationVerdictV0` non-Codable | Unchanged. |
| `AllowedActionV0` server-minted only after staging | Unchanged. |
| Confirm tap required for writes | Unchanged. |
| No auto-write | Unchanged. |
| Never touch calendar objects CalAgent did not create | Unchanged. |
| Decision-sufficient membrane | Unchanged and extended to fact-cell / attention / deposition preimages. |
| Free-text notes never cross by default | Unchanged. |
| Copy honesty | Unchanged and extended to witness facts. |
| Why-line true today | Reframed as fact true under evidence; truth still not need. |
| `.notMeasured` never zero | Unchanged. |
| Reward never admission | Unchanged and extended: reward never speech permission. |
| Raw survival cannot train reward | Unchanged. |
| Contestation excludes CalAgent-created demand | Unchanged. |
| Product verdicts are product-directed | Unchanged and less needy in copy. |
| Comfortable false positive named | Unchanged. |
| Falsifier outside optimized reward | Unchanged. |
| SELECT fallback | Unchanged. |
| Capability may rise without sovereignty rising | Unchanged and extended to speech and phase-gated growth. |

New plan-6 invariants:

```text
Speech may occupy only tendered attention.
Fact cells are Swift-minted; the model may select, not invent.
User facts crossing the model-visible metabolism are disposable transcripts.
The machine may persist only its own residual, not a user portrait.
Run and write phases are disjoint for genome/metabolism changes.
The user may author dials in the metabolism but cannot loosen the agent's genome.
A consequential dial must later testify against the molder.
```

## 21. Self-audit

This table must be re-answered for every public witness-family graduation, every guidance release, and every phase-gated organ promotion.

| Litmus test | Yes / No | Evidence |
|---|---:|---|
| Is there one locatable governing doctrine and architecture law? | Yes | Opening blocks. |
| Are the three conservation lines present? | Yes | Opening and §3. |
| Is plan-5's state wall preserved? | Yes | §§1, 3, 9, 20. |
| Is D2 still the only state admission seam? | Yes | §9. |
| Is AttentionGate separate from D2? | Yes | §§5, 8.5-8.7, 9. |
| Does every public witness speech pass `occupation(spoken) ⊆ A(tendered)`? | Standing gate | Must be shown by AttentionGate logs per release. |
| Does the release default to place, not send? | Standing gate | Delivery report must show no push unless user-authored tender exists. |
| Are facts Swift-minted and evidence-bound? | Standing gate | Fact-cell lineage and receipts. |
| Does DiffusionGemma select rather than invent facts? | Standing gate | Model-output contract and sanitizer logs. |
| Does Swift render final witness copy? | Standing gate | Copy renderer lineage. |
| Are true facts checked for spendability? | Standing gate | Fact-cell spendability reports. |
| Is cold start deposition used only for closed-past adjudication? | Standing gate | Deposition prompt audit. |
| Is the product avoiding generic preference interviews? | Standing gate | Onboarding / deposition copy review. |
| Does break detection use only CalAgent's own residual? | Standing gate | Self-doubt ledger audit. |
| Does break copy speak about the system, not a portrait of the user? | Standing gate | Confession copy audit. |
| Are slow witness organs suppressed when residual rises? | Standing gate | Break suppression report. |
| Are disposable transcripts expiring and read-only? | Standing gate | Transcript lifecycle audit. |
| Does any model-visible store accumulate raw user facts? | No required | Privacy audit. |
| Is the phase gate enforcing run/write separation? | Standing gate | PhaseGate logs and topology audit. |
| Are proposals typed templates, not arbitrary code? | Standing gate | Template review logs. |
| Are slow and fast witness organs evaluated by distinct validators? | Standing gate | ShadowOrganEvaluation reports. |
| Are user dials metabolism-only? | Standing gate | Dial impact audit. |
| Does each consequential dial have a future consequence witness? | Standing gate | DialWagerAudit coverage. |
| Are passive users not framed as authors? | Standing gate | UX copy review. |
| Can users petition to widen accountability? | Standing gate after M11 | Amendment petition availability and decision logs. |
| Can users loosen the agent's leash? | No | Amendment rejection tests. |
| Is reward absent from D2 and AttentionGate authority? | Yes / standing | Contract tests. |
| Are contestation and falsifier reports current? | Standing gate | Release artifacts. |
| Are attention-regret reports current? | Standing gate | Release artifacts. |
| Is the comfortable false positive still named as residual? | Yes | §§11.6 and 18. |
| Is the attention-proxy blind spot still named as residual? | Yes | §§5.5 and 18. |
| Does user protection scale with migrated power? | Standing gate | Must be re-answered per family: state wall, speech wall, reward loop, phase gate, and user correction all reviewed. |

