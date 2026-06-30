# plan-6-revised.md — Witness Architecture with Typed Laws, Temporal Calculus, Human-Clocked Learning, and a Kairos Budget

**Status:** canonical Plan-6 revision. This is not Plan 7. It unfreezes three joints in the prior Plan-6 draft while preserving the Plan-5 wall (now folded into Appendix A) and the Witness reframe.

**Relationship to Plan 5:** unchanged inheritance, now **folded into Appendix A** so this document stands alone. D2 remains the single in-process admission seam for writes; `support(staged) ⊆ F(x_live)` remains unchanged; `RecommendationVerdictV0` remains non-`Codable`; `AllowedActionV0` remains server-minted only after staging; the confirm tap remains required; Swift never touches calendar objects CalAgent did not create; raw private strings stay behind Swift; `.notMeasured` is never zero; measurement-before-mutation remains the gate before reward, training, release, speech-channel changes, fact-program changes, and now structural-speech budgeting.

**Relationship to the Witness design:** preserved and sharpened. CalAgent is a witness, not a recommender. It asks, "what is already true about your time that you are too close to read?" It speaks at two tempos. On smooth life it places facts about the user's time where attention already rests. At the break it changes subject and speaks only about its own error, then re-deposes. The mouth is now typed as strictly as the hand.

**Revision note:** Plan 6 was right where it copied living structures: the attention law, phase separation, two validators, deposition, disposable transcript, and user pen. It froze three things that must stay dynamic:

1. It gave laws and guesses the same syntactic costume. This revision separates compiler-enforced theorems from runtime rules and conjectural data. A constraint is treated as a theorem only when violating it requires changing a type signature that is re-checked at every call site.
2. It wired only `fast-fires-suppresses-slow`. This revision adds the missing reverse coupling: the slow loop may recommit only when `residual-low ∨ deposition-answered`. The human is the second clock.
3. It wrote the derivative of attention, `occupation(spoken) ⊆ A(tendered)`, but not its integral. This revision adds a hard, tight structural-speech budget so the witness remains a guest and does not train the user to experience time only as temporal structure.

**Implementation-status note:** This document is a target architecture. The inherited Plan-5 wall is architecture of record. The type-signature taxonomy, capability-absence refactor, two-mouth API, temporal calculus, user-authored fact programs, slow-license oscillator, residual/deposition commit clock, structural-speech budget, kairos floor report, and revised tests are proposed Plan-6 build items until an implementation owner marks the relevant milestone complete. Do not describe them as shipped merely because this plan specifies them.

**Governing doctrine:** CalAgent is a witness for the user's time. Swift reads private state, mints true and spendable temporal facts from a closed structure calculus, conserves state, attention, and privacy, admits speech only into attention the user has tendered, meters cumulative structural speech, admits writes only through D2 and a confirm tap, and owns all persistent lineage. DiffusionGemma may rank, contrast, and learn which Swift-minted fact programs deserve placement, but may not author facts, write-bearing fields, evidence, provenance, attention authority, reward, persistent user portrait, notification capability, or a mouth that speaks about the user at the break. Codex may relay, serve, and receive correction. The most capable component is never the most sovereign. The only persistent machine-authored portrait is the system's own error. The one fluency the witness cannot measure — the user's kairos, their native sense of meaningful timing — is protected not by a claimed law, but by scarcity: the witness speaks structurally seldom.

**Architecture law:**

```text
Codex may relay, serve, and carry correction.
DiffusionGemma may rank, compose over, and learn from Swift-minted fact programs, typed shape hints, and bounded guidance.
Swift must encode, mint facts, validate truth, admit speech, admit writes, write only after tap, meter structural speech, measure outcomes, own preference lineage, run falsifiers, run phase gates, and bound all learning.
Codex, DiffusionGemma, reward models, learned stores, release dashboards, and speech surfaces must never grade, admit, write, author facts, launder their own outputs, manufacture demand, manufacture contestation, occupy untendered attention, author a persistent portrait of the user, or expand a capability that is absent by type.
```

The three conservation laws are retained:

```text
STATE:      support(staged)    ⊆ F(x_live)                           — reach only into feasible state
ATTENTION:  occupation(spoken) ⊆ A(tendered)                          — speak only into tendered attention
PRIVACY:    transmit(model)    ⊆ decision-sufficient(non-identifying)  — move decision signal, never raw life
```

The fourth line is not a conservation law because the system cannot see the conserved quantity. It is a floor and a budget:

```text
KAIROS FLOOR: structural_speech_rate(system) ≤ B_structural(tight, tightening, user-visible)
              — the witness cannot measure the user's meaning-fluency, so it must ration the chronos it speaks.
```

The loop-aware supplement becomes:

```text
D2 covers state admission.
A2 covers per-tick attention admission.
B_structural covers cumulative structural speech.
The membrane covers privacy and marks the boundary of theorem-izability.
The phase gate prevents the learning metabolism from editing the genes it expresses.
The two mouths prevent stale you-facts from typechecking at the break.
The self-doubt ledger is the only persistent machine-authored portrait.
The human deposition is the second clock that can re-license slow learning after a break.
The user may author temporal fact programs and dials as data, but may not loosen the machine's leash.
```

## Internal role map

This map is for engineering only. Do not surface these internal names, genes, mouths, pens, budgets, residuals, or theorem vocabulary in user-facing copy, onboarding, card text, accessibility labels, marketing, analytics event names, prompts, or UX instrumentation.

| Component | Owner | Owns | Borrows | Contract | Trust boundary | Failure mode | Guard |
|---|---|---|---|---|---|---|---|
| Codex / carrier | Carrier layer | Turn capture, bounded clarification, admitted placement presentation, deposition relay, dial relay | Swift-staged cards, Swift-minted actions, A2-admitted speech | `WitnessTurnResponseV1`, `DepositionAnswerV1` | No admission, no grading, no facts, no attention authority, no write | Over-talks, invents copy, asks needy questions | May carry only Swift-rendered copy and server-minted actions. |
| DiffusionGemma | Analysis lane | Selection, ranking, contrast, typed shape hints, optional learned witness organ | Fact-program slate, temporal calculus outputs, non-identifying stats, `u`, bounded guidance | `WitnessSelectionInfillV1`, `TemporalFactProgramProposalV1` | No fact authorship, no raw identity, no evidence, no attention lease, no write, no mouth choice | Turns witness into recommendation, learns flattery, selects cruelty | Swift minter, A2, D2, budget, two-mouth API, phase gate. |
| Swift theorem layer | Swift genome / platform | Type-signature laws, capability graph, phase tokens, two-mouth subject separation, absent capabilities | Owner-approved topology | `RunPhaseTokenV1`, `WritePhaseTokenV1`, mouth protocols | Learning may express, never edit, theorem layer | Laws and guesses look identical; flags masquerade as walls | Theorem taxonomy, type-signature criterion, topology lint. |
| Swift metabolism | Swift reducers / ML | Fact programs, settlement, reward, dials, shadow organs, self-doubt | Read-only theorem transcripts | `TemporalStructureProgramV1`, `SelfDoubtLedgerV1`, `SlowWitnessLicenseV1` | May adapt only in runtime-rule space | Learns portrait, overfits dead world, clocks release to roadmap | Disposable transcripts, no portrait, residual/deposition clock. |
| D2 state admission | Swift validators | Write staging, provenance, live support, fingerprints, actions | Swift-materialized support | `D2BindingOutputV0`, `AllowedActionV0` | Writes only | Asked to verify value or attention | D2 reward-free and attention-free; A2/budget handle speech. |
| A2 attention admission | Swift attention owner | Per-tick tendered attention, channel admission, occupation accounting | User event stream, attention policy | `TenderedAttentionLeaseV1`, `SpeechOccupationV1`, `A2BindingOutputV1` | Speech placement only | Treats proxy as reality; admits foregrounded untendered attention | Proxy confidence, demotion, user correction, budget. |
| Structural speech budget | Swift product / safety | Cumulative rate of temporal-structure speech | A2 placements, fact-program class, user-requested surfaces | `StructuralSpeechBudgetV1`, `KairosFloorReportV1` | Meters system output, not user's mind | Chronos flood retrains user despite every single card being lawful | Tight cap, tightening default, visible exhaustion, no reward override. |
| Temporal calculus compiler | Swift fact owner | Closed grammar over interval order; program validation; semantic-blindness proof | User-authored programs, owner-approved templates | `TemporalStructureProgramV1`, `TemporalPrimitiveV1`, `TemporalProgramProofV1` | Primitives are structural only | Hard-coded operator/family list freezes vendor guesses; calculus smuggles meaning | Closed primitive set, operators as data, no raw strings, no semantic predicates, phase-gated programs. |
| Fact-cell minter | Swift evidence / rendering | True, spendable, privacy-safe facts generated by temporal programs | Raw state, evidence receipts, relation chips | `FactCellV1`, `SpendabilityProofV1`, `FactRenderTemplateV1` | Only Swift mints facts | Model-authored facts, unspendable disclosure, late witness | Evidence binding, spendability gate, TTL, budget. |
| Smooth mouth | Swift speech owner | Places facts about user time only under slow license | A2 lease, budget allowance, fact-cell | `SmoothMouthV1.speak(SmoothSubjectFactV1, ...)` | Cannot speak at break without license | Stale you-fact at regime change | Requires `SlowWitnessLicenseV1`; revoked on break. |
| Break mouth | Swift speech owner | Confesses system error and asks deposition | Self-doubt ledger, deposition question | `BreakMouthV1.speak(BreakSelfAssertionV1, ...)` | Cannot accept user-subject fact | Uses break to assert new biography | Type mismatch; only self-subject assertion compiles. |
| License controller | Swift learning / release owner | Suppression and recommit of slow organs | Self-doubt residual, deposition answers, shadow eval | `SlowWitnessLicenseV1`, `SlowWitnessSuppressionV1` | Dynamic runtime rule, not theorem | Latch-up: turbulent life suppresses forever | Suppress on residual-high; recommit on residual-low OR deposition-answered. |
| Deposition channel | Product / privacy | Closed-past confirm/correct, break redeposition, proxy-gap correction, first facts of new regime | Imported past, self-doubt, user answers | `DepositionQuestionV1`, `DepositionAnswerV1`, `RegimeSeedFactV1` | User speaks; no interview portrait | Becomes focus-group interview or needy product grading | Typed options, fixed past, self-subject break, no free text by default. |
| User operator authoring | User + product | User-authored temporal programs, dials, amendments | Calculus compiler, phase gate | `UserTemporalProgramV1`, `DialWagerSignalV1`, `AmendmentPetitionV1` | User authors metabolism, not genes | Passive user receives stranger's model while copy says author | Three-beat wagers, consumer-branch honesty, amendment clause. |
| Reward / falsifier layer | Swift measurement | Settlement, contestation, product verdicts, falsifiers | Write lineage, witness settlement, budget reports | `WitnessSettlementSignalV1`, `StructuralSpeechBudgetReportV1` | Steers only future composition | Optimizes yes, chronos frequency, or low-contestation survival | Held-out falsifiers, budget cannot be bypassed by reward. |
| Phase gate | Swift release | RUN/WRITE split, typed template acceptance, topology review, rollback | Shadow eval, owner gate, user petitions | `PhaseGateTranscriptV1` | No run-time self-modification | Proposal pipe edits genome; release cadence clocks learning | Stop-the-world write phase, type templates, residual/deposition clock for live license. |

## Table of contents

1. [Review decision](#1-review-decision)
2. [Theorem taxonomy: laws, rules, and guesses](#2-theorem-taxonomy-laws-rules-and-guesses)
3. [The membrane is the boundary of theorem-izability](#3-the-membrane-is-the-boundary-of-theorem-izability)
4. [Capabilities must be absent, not false](#4-capabilities-must-be-absent-not-false)
5. [Two mouths: smooth speaks you, break speaks I](#5-two-mouths-smooth-speaks-you-break-speaks-i)
6. [Temporal structure calculus: a grammar, not a family list](#6-temporal-structure-calculus-a-grammar-not-a-family-list)
7. [Fact cells after the calculus](#7-fact-cells-after-the-calculus)
8. [Attention derivative and kairos integral](#8-attention-derivative-and-kairos-integral)
9. [Learning dynamics: the human-clocked oscillator](#9-learning-dynamics-the-human-clocked-oscillator)
10. [Deposition as the second clock](#10-deposition-as-the-second-clock)
11. [Phase gate and release cadence after the oscillator](#11-phase-gate-and-release-cadence-after-the-oscillator)
12. [Canonical contracts](#12-canonical-contracts)
13. [End-to-end flows](#13-end-to-end-flows)
14. [Privacy, copy honesty, and the kairos floor](#14-privacy-copy-honesty-and-the-kairos-floor)
15. [User authorship: operators, dials, and amendments](#15-user-authorship-operators-dials-and-amendments)
16. [Migration sequence](#16-migration-sequence)
17. [Test matrix](#17-test-matrix)
18. [Definition of done](#18-definition-of-done)
19. [Changelog / deprecation map](#19-changelog--deprecation-map)
20. [Deliberately preserved safety invariants](#20-deliberately-preserved-safety-invariants)
21. [Self-audit](#21-self-audit)

---

## 1. Review decision

The review is accepted.

Plan 6's core product judgment remains correct:

```text
CalAgent is a witness, not a recommender.
```

The state wall remains correct:

```text
support(staged) ⊆ F(x_live)
```

The attention twin remains correct:

```text
occupation(spoken) ⊆ A(tendered)
```

The phase split remains correct:

```text
RUN phase and WRITE phase must not overlap.
```

The two-tempo split remains correct:

```text
smooth life: place true facts about the user's time.
break: confess the system's own error and re-depose.
```

The revision changes what Plan 6 treated as finished but had only named:

| Frozen joint | Why it was frozen | Plan-6-revised thaw |
|---|---|---|
| `WitnessFactFamilyV0` / `WitnessFactKindV0` as an enum list | It put vendor-imagined fact families in the same syntax as laws. | Replace the fact-family list with a closed calculus of **primitives** over the interval order. Operators (density, recurrence, erosion, …) and families are both data — programs over the primitives, user- and owner-authorable. Only adding a primitive is theorem-surface; structural-only-ness is a theorem of the primitive input types, not a proof flag. |
| Boolean or runtime-denial capability gates | `false` and failure cases can be bypassed, misread, or widened by config. | Make catastrophic capabilities absent by type: no back-write interface, no structural notification channel, no break mouth that accepts user-facts. |
| Slow-loop commit on release cadence | Learning breathed at vendor roadmap cadence, not user-life cadence. | Shadow evaluation qualifies an organ; live commit requires `residual-low ∨ deposition-answered`. |
| Per-tick attention only | Every placement could be lawful while their distribution retrains the user's relation to time. | Add the cumulative structural-speech budget: a hard, tight, tightening integral cap — and a one-way ratchet, so loosening requires a phase-gated, user-visible amendment and the owner's growth incentive cannot quietly widen it. |

This is still Plan 6 because it keeps the witness body and soul. The change is not another architecture. It is the unfreezing of exactly the joints that Plan 6 itself made visible.

## 2. Theorem taxonomy: laws, rules, and guesses

### 2.1 The criterion

A Plan-6 constraint is a **compiler theorem** only if violating it requires changing a type signature or topology edge that is re-checked at every call site.

A Plan-6 constraint is a **runtime rule** if violating it requires changing a value, flag, configuration row, policy table, threshold, or test.

A Plan-6 constraint is **conjectural data** if it encodes a guess about what patterns matter in the user's world.

```text
theorem:  impossible to express without a type/topology change
rule:     expressible, rejected by runtime admission / policy / tests
data:     user/vendor-authored conjecture compiled by Swift into a safe program
```

The taxonomy prevents the syntactic disease where a conservation law and a vendor guess both appear as `enum SomethingV0` and feel equally safe.

### 2.2 Compiler theorems in Plan 6 revised

Compiler-theorem territory:

- RUN and WRITE phase disjointness;
- D2 write admission token shape;
- absent back-write capability from model-visible transcripts;
- absent structural-notification channel;
- Smooth mouth cannot accept break self-assertions;
- Break mouth cannot accept user-subject facts;
- D2 cannot see reward as authority;
- `RecommendationVerdictV0` remains non-`Codable`;
- raw calendar strings cannot be payload types across the model membrane;
- a write-bearing placement must carry both an A2 admission envelope and D2-staged action.

These are theoremized by type signatures, protocols, uninhabited types, private constructors, module boundaries, and reference topology.

### 2.3 Runtime-rule territory

Runtime-rule territory:

- A2 proxy confidence thresholds;
- copy-honesty scan pass/fail;
- fact-cell spendability;
- structural-speech budget remaining;
- negative product verdict impact;
- slow-organ suppression threshold;
- residual-low definition;
- deposition-answer sufficiency;
- owner gate approval;
- phase-gate range checks;
- falsifier kill thresholds.

These are not fake laws. They are rules. They must be measured, tested, logged, and treated as fallible.

### 2.4 Conjectural-data territory

Conjectural-data territory:

- which temporal compositions matter;
- whether four reschedules or two reschedules should be shown;
- which empty-space patterns deserve a glyph;
- which dial thresholds the user authors;
- which fact programs a user petitions into their model;
- which witness organs earn live license after a break.

These must be data passed through typed compilation and phase gates. They are not laws merely because they are represented in Swift.

### 2.5 Naming convention

Plan-6-revised uses naming to stop syntax from lying:

| Suffix / family | Meaning |
|---|---|
| `*TokenV1`, `*CapabilityV1`, `*MouthV1` | Theorem-facing type or topology capability. Violating requires type/topology change. |
| `*PolicyV1`, `*GateV1`, `*BudgetV1`, `*ReportV1` | Runtime rule. Must be measured and audited. |
| `*ProgramV1`, `*TemplateV1`, `*DialV1` | Conjectural data. Safe because it is compiled/range-checked, not because it is true by construction. |
| `*LedgerV1` | Persistent measurement. Must state whether it is about the system or the user. Persistent user portrait is forbidden. |

## 3. The membrane is the boundary of theorem-izability

The privacy membrane does more than protect raw data. It marks the boundary between harms the system can make structurally unrepresentable and harms that must remain floors.

The rule:

```text
Type the catastrophes the system can see.
Budget, expose, and invite correction for the catastrophes it cannot see.
```

### 3.1 Typeable catastrophes

Typeable catastrophes include:

- writing without support;
- writing without confirm tap;
- transmitting raw titles, notes, attendees, or exact locations to the model;
- model-authored evidence/provenance/action fields;
- running and genome-writing in the same tick;
- a break utterance that asserts a user-life fact;
- a structural witness notification sent through a default channel;
- a model-visible transcript that can back-write into the genome.

These harms live on the system's side of the membrane. They can be blocked by absence of fields, absence of capabilities, phase tokens, and type signatures.

### 3.2 Untypeable floors

Untypeable floors include:

- foregrounded but untendered attention;
- a true fact placed cruelly at a threshold the system cannot feel;
- silence that becomes abandonment at a crisis;
- speech that is formally attention-bounded but still changes the user's long-run fluency in meaning;
- a passive user who receives a stranger-authored model while product copy implies authorship;
- the user's kairos, the felt right moment, because it lives on the user's side of the skull.

These cannot be theoremized without violating privacy or building the forbidden portrait. Plan-6-revised treats them as floors, not solved problems.

### 3.3 One hole, four masks

The proxy gap is not one residual among many. It appears under four masks:

```text
attention:   app-open is not the same as tendered attention;
abandonment: silence may be care or desertion;
cruelty:     a true fact may be spendable in state and still wrong in meaning;
kairos:      chronos facts may crowd out the user's own sense of timing.
```

The system cannot close this hole. It can name it, shrink the surface area, invite correction, and speak less.

## 4. Capabilities must be absent, not false

A flag is not a wall. A denied-by-default runtime failure is not the same thing as a missing capability. For irreversible harms, Plan-6-revised removes the capability.

### 4.1 No back-write flag

Do not represent back-write as:

```swift
var backWritePermitted: Bool
```

Represent it as the absence of a mutator in the transcript's type and reference graph:

```swift
struct ReadOnlyTranscriptV1<Payload: Codable & Hashable>: Codable, Hashable {
  var schemaVersion: Int
  var transcriptID: TranscriptIDV1
  var payloadDigest: String
  var payloadClass: TranscriptPayloadClassV1
  var mintedAt: Date
  var expiresAt: Date

  // No mutable payload reference.
  // No write handle.
  // No genome mutator.
  // No function that can re-enter the minter.
}

protocol GenomeMutatorV1 {
  func apply(_ template: TypedGenomeTemplateV1, during phase: WritePhaseTokenV1) throws -> PhaseGateTranscriptV1
}
```

Metabolism code is not passed `GenomeMutatorV1`. This is topology, not etiquette.

### 4.2 No default structural notification channel

Do not represent witness notifications as:

```swift
case notificationDeniedByDefault
```

That makes notification a runtime value the system can ask for and be denied. Plan-6-revised has no structural notification channel in the default witness mouth API.

```swift
protocol TenderedWitnessChannelV1: Codable, Hashable {
  var leaseID: TenderedAttentionLeaseIDV1 { get }
  var surface: AttentionSurfaceV1 { get }
  var channelKind: AttentionChannelKindV1 { get }
}

struct InlinePlacementChannelV1: TenderedWitnessChannelV1 { /* A2 lease-backed */ }
struct FoundObjectChannelV1: TenderedWitnessChannelV1 { /* A2 lease-backed */ }
struct DepositionSheetChannelV1: TenderedWitnessChannelV1 { /* A2 lease-backed */ }
struct EvidenceDrawerChannelV1: TenderedWitnessChannelV1 { /* user-requested */ }

// There is intentionally no StructuralNotificationChannelV1 conforming to TenderedWitnessChannelV1.
// Adding one is a type/topology change and therefore a phase-gated theorem-surface review.
```

A future owner-gated notification product would require a new type, new topology review, new A2 policy, new budget treatment, and a launch-specific self-audit. It cannot be enabled by flipping a config row.

### 4.3 No break-you-fact channel

Do not represent break copy as a runtime `if` inside one unified gate:

```swift
if breakActive { blockUserFacts() }
```

Make stale user-facts unrepresentable at the break:

```swift
struct SmoothSubjectFactV1: Codable, Hashable {
  var factCellID: FactCellIDV1
  var temporalProgramID: TemporalStructureProgramIDV1
  var licenseID: SlowWitnessLicenseIDV1
}

struct BreakSelfAssertionV1: Codable, Hashable {
  var selfDoubtLedgerID: SelfDoubtLedgerIDV1
  var residualAssertionID: AssertionResidualSignalIDV1
  var depositionQuestionID: DepositionQuestionIDV1
}

struct SmoothMouthV1 {
  func speak(
    _ fact: SmoothSubjectFactV1,
    on channel: InlinePlacementChannelV1,
    admittedBy a2: A2BindingOutputV1,
    under budget: StructuralSpeechBudgetAdmissionV1
  ) throws -> SmoothWitnessPlacementV1
}

struct BreakMouthV1 {
  func speak(
    _ assertion: BreakSelfAssertionV1,
    on channel: DepositionSheetChannelV1,
    admittedBy a2: A2BindingOutputV1
  ) throws -> BreakWitnessPlacementV1
}
```

`BreakMouthV1` has no overload that accepts `SmoothSubjectFactV1`. A stale you-fact asserted at the break does not typecheck.

### 4.4 Write-bearing witness as sum type, not bool

Do not use:

```swift
var writeActionPermitted: Bool
```

Use a sum type that carries the proof when the write exists:

```swift
enum WitnessPlacementEnvelopeV1: Codable, Hashable {
  case nonWrite(NonWriteWitnessEnvelopeV1)
  case writeBearing(WriteBearingWitnessEnvelopeV1)
}

struct WriteBearingWitnessEnvelopeV1: Codable, Hashable {
  var smoothPlacement: SmoothWitnessPlacementV1
  var d2OutputDigest: String
  var allowedAction: AllowedActionV0
}
```

The capability is present only in the `writeBearing` case, and that case cannot be constructed without D2 output.

## 5. Two mouths: smooth speaks you, break speaks I

The witness has two mouths because subject is a safety property.

```text
Smooth mouth: subject = user's time; verb = place; condition = slow license + A2 + budget.
Break mouth:  subject = system's error; verb = confess/depose; condition = break signal + fresh A2.
```

### 5.1 Smooth mouth

The smooth mouth may place a fact about the user's time only when all are true:

- Swift minted the fact from temporal calculus output;
- the fact is true, privacy-safe, and spendable;
- `SlowWitnessLicenseV1` is active for the relevant organ/program/surface;
- A2 admits the exact placement into tendered attention;
- structural-speech budget admits the cumulative exposure;
- copy avoids semantic meaning claims;
- if a write action exists, D2 admits it and confirm tap is required.

The smooth mouth is a medium only by discipline. It amplifies an existing glance. If A2 proxy confidence is low, it demotes to found object or silence.

### 5.2 Break mouth

The break mouth may speak only about the system:

Allowed:

```text
"I've been wrong about your mornings four days running. I don't want to keep guessing."
"My read on this pattern is stale. Which closed fact should I trust?"
"I keep placing this where you report it is too much. I need to adjust the placement rule."
```

Forbidden:

```text
"Your life changed."
"You avoid mornings now."
"You need a new routine."
"This is probably because of your new job."
"You are grieving / overloaded / avoiding someone."
```

The break mouth is a fiduciary sliver. It acts, but only on itself, and only to return the pen through deposition.

### 5.3 The subject theorem

The theorem:

```text
At a break, a user-subject temporal fact cannot enter the mouth API.
```

The runtime supplement:

```text
Break copy must remain self-subject after rendering, localization, accessibility transformation, logging, and carrier presentation.
```

The theorem blocks the catastrophic class. The runtime rule guards the rest.

## 6. Temporal structure calculus: a grammar, not a family list

`WitnessFactFamilyV0` is deprecated. It encoded a vendor's imagined outputs as if they were a law. Plan-6-revised replaces it with a closed temporal structure calculus that generates an open space of facts as data.

### 6.1 Principle

The calculus expresses temporal structure only:

```text
positions, intervals, gaps, counts, density, recurrence, movement, adjacency, erosion, comparison, residual.
```

It cannot express semantic meaning:

```text
avoidance, desire, need, preference, relationship meaning, emotional valence, identity, worth.
```

The ceiling is the conscience. The same grammar that cannot say "you are avoiding your sister" is the grammar forbidden by the privacy gene to know who the sister is or what avoidance would mean.

### 6.2 The calculus is primitives over order; operators are its first programs

A closed set earns the genome only if it is closed *by law*. The test is §2.1's breakfast test: if a domain expert can propose a new member over coffee, the set is conjectural data wearing a law's costume.

A flat operator enum fails that test twice. First, most of its members are not primitive — `density` is `durationSum ÷ window`; `erosion` is a count of movement out of a protected gap; `recurrence` is a quantified self-similarity. Second, anyone can propose a fourteenth over coffee — *syncopation*, *drift-acceleration*, *clustering*. A flat operator enum therefore fuses the genome (a few true primitives) with the metabolism (their compositions) and freezes both — exactly the move the deprecated fact-family enum made one level up.

So the calculus descends one floor. The genome is a small set of primitives over the interval order; adding a primitive is a theorem-surface change. Everything above the primitives — every named operator, every family — is a **program**: data, compiled and proven, user- and owner-authorable, never code.

```swift
// GENOME (theorem-surface): the decidable predicates over positions on an interval
// order. Closed by law — a sixth quantifier is not proposable over coffee.
indirect enum TemporalPrimitiveV1: Codable, Hashable {
  case select(StructuralSelectorV1)                  // events/gaps by non-identifying structural predicate
  case window(WindowSelectorV1)                      // bind to a closed interval
  case forAll(TemporalPrimitiveV1)                   // ∀ over the windowed set
  case exists(TemporalPrimitiveV1)                   // ∃ over the windowed set
  case count(TemporalPrimitiveV1)                    // cardinality
  case durationSum(TemporalPrimitiveV1)              // total length
  case order(OrderRelationV1)                        // before / after / nearness on the line
  case compare(TemporalPrimitiveV1, TemporalPrimitiveV1, ComparatorV1)
  case residual(SelfAssertionRefV1)                  // a prior system assertion vs its closed outcome
  case compose(ComposeExprV1)
}

// METABOLISM (data): named operators are owner-approved DEFAULT programs over the
// primitives — not enum cases. A new operator crosses the phase gate as data; it
// needs no type change and no app release.
enum TemporalProgramAuthorV1: String, Codable {
  case ownerApprovedDefault   // the shipped operators (density, recurrence, erosion, …) live here
  case userAuthored
  case userPetitionedAmendment
  case shadowLearnedCandidate
}

struct TemporalStructureProgramV1: Codable, Hashable {
  var schemaVersion: Int
  var programID: TemporalStructureProgramIDV1
  var author: TemporalProgramAuthorV1
  var root: TemporalPrimitiveV1
  var renderTemplateID: FactRenderTemplateIDV1
  var privacyClass: FactPrivacyClassV1
  var spendabilityPolicyID: SpendabilityPolicyIDV1
  var proof: TemporalProgramProofV1
  var computedAt: Date
  var expiresAt: Date?
}
```

Density, recurrence, erosion, movement, and adjacency ship as `ownerApprovedDefault` programs. They are the *first* compositions, not the *only* ones. The user — or the shadow learner — may author a new operator (a new composition over the same primitives) and petition it through the phase gate as data. The vendor authors the calculus; the user authors the operators and the families both. Only adding a *primitive* is a theorem-surface change.

### 6.3 Operator semantics

The named operators below are the shipped default programs of §6.2. `eventSet`/`gapSet` are `select` over events/gaps and `interval` is `window`; `density`, `recurrence`, `erosion`, `movement`, and `adjacency` are compositions over the primitives. Each is structural-only by the input types of §6.2, not by assertion.

| Operator | Meaning | Example output | Forbidden interpretation |
|---|---|---|---|
| `eventSet` | Selects Swift-owned events by non-identifying structural predicates | recurring blocks in a window | person/place/event-title identity |
| `gapSet` | Selects empty intervals by size / position / adjacency | open Saturday afternoon gaps | "rest" or "freedom" |
| `count` | Counts intervals/events in a closed window | three moves, six dense mornings | intent or avoidance |
| `durationSum` | Sums duration | eight occupied evening hours | burden/need |
| `density` | Computes occupancy ratio | no empty morning in six weeks | exhaustion |
| `recurrence` | Detects repetition under interval similarity | weekly pattern changed | habit/preference |
| `adjacency` | Measures before/after/nearness | prep gap before block | importance |
| `movement` | Counts reschedules / shifts | moved four times | reluctance |
| `erosion` | Measures protected interval losing protection | protected hour gave way twice | weakness/failure |
| `compare` | Compares two structural outputs | last three vs prior eight | value judgment |
| `residual` | Compares prior system assertion to closed outcome | prediction failed | user biography |
| `compose` | Builds typed compositions | gap + recurrence + latestUsefulAt | semantic story |

### 6.4 Structural-only is a theorem of the input types, not a proof flag

A `proof` that is a struct of Bools is the `backWritePermitted: Bool` mistake again (§4): `noSemanticPredicateInputs: Bool` is set by a checker and falsified by a bug in that checker — a runtime rule wearing the word "proof." Privacy leakage through a smuggled semantic predicate is a catastrophe (§3.1), so by the type-the-catastrophe rule its absence must be a type, not a flag.

So structural-only-ness is established **by construction**, not asserted. The primitives' leaf input types are uninhabited by meaning: a `StructuralSelectorV1` can be built only from non-identifying structural predicates, and there is no `TemporalPrimitiveV1` case and no leaf initializer that accepts a raw string, an attendee identity, an exact location, or a semantic predicate. A program that touched meaning would not typecheck. "Output is structural" is therefore not a field to set — it is true because the program is a `TemporalPrimitiveV1`, and `TemporalPrimitiveV1` cannot express meaning.

The proof object then carries only what genuinely remains a runtime rule — policy resolutions a lookup performs and a test can check:

```swift
struct TemporalProgramProofV1: Codable, Hashable {
  var schemaVersion: Int
  var programID: TemporalStructureProgramIDV1
  var primitiveTreeDigest: String
  // structural-only-ness is NOT a field here. It is a theorem of TemporalPrimitiveV1's
  // input types: no inhabitant carries a raw string, identity, or semantic predicate.
  var spendabilityPolicyResolved: Bool      // runtime rule
  var privacyClassResolved: Bool            // runtime rule
  var renderTemplateClosedSlotsOnly: Bool   // runtime rule
  var addsPrimitive: Bool                    // theorem-surface: a new primitive, not a new program
  var phaseGateTranscriptID: PhaseGateTranscriptIDV1?
  var measurementStatus: MeasurementStatusV0
}
```

`addsPrimitive == true` requires WRITE phase and owner review, because a new primitive changes the calculus itself. A new program — a new operator or family over existing primitives — does not: it is data, and its structural safety is carried by the primitive types, not by a flag a bug can mis-set.

### 6.5 User-authored fact programs

The user may author a fact family by composing operators, not by writing code.

Example user-authored program:

```text
Show me when a protected empty block erodes twice within six weeks.
```

This becomes data:

```text
erosion(
  protected(gapSet(window: rollingSixWeeks, minDuration: userDial)),
  threshold: 2
)
```

The compiler proves that the program is structural, privacy-safe, renderable, and spendable. If it passes, it can become part of the user's metabolism without a new app release. If it asks for meaning, identity, or raw text, it fails.

### 6.6 What the calculus deliberately cannot say

Forbidden because semantically meaningful and privacy-side:

```text
"You're avoiding your sister."
"This meeting matters more than you admit."
"You need recovery."
"This is grief."
"This is ambition."
"You prefer evenings now."
```

Allowed structural alternatives:

```text
"This event-family moved four times."
"Thursday evenings were occupied for eight weeks; the last three are open."
"You protected this hour twice; both times it was later released."
"My previous assertion about morning openness failed four times."
```

## 7. Fact cells after the calculus

A fact-cell is no longer an item in a hard-coded fact-family enum. It is the output of a compiled temporal program.

### 7.1 `FactCellV1`

```swift
struct FactCellV1: Codable, Hashable {
  var schemaVersion: Int
  var factCellID: FactCellIDV1
  var contextID: RecommendationContextIDV0
  var temporalProgramID: TemporalStructureProgramIDV1
  var temporalOutputDigest: String
  var sourceReceiptHashes: [EvidenceHashV0]
  var relationChipIDs: [RelationChipIDV0]
  var factTruthPredicateID: FactTruthPredicateIDV1
  var renderTemplateID: FactRenderTemplateIDV1
  var renderSlotValues: [FactRenderSlotIDV1: FactRenderSlotValueV1]
  var privacyClass: FactPrivacyClassV1
  var temporalProgramProofID: TemporalProgramProofIDV1
  var redactionRisk: RedactionRiskBandV0
  var spendability: SpendabilityProofV1
  var attentionBudgetHint: AttentionBudgetV1
  var structuralSpeechCost: StructuralSpeechCostV1
  var evidenceDrawerPolicyID: EvidenceDrawerPolicyIDV1?
  var computedAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}
```

Rules:

- Swift alone mints `FactCellV1`.
- The referenced `TemporalProgramProofV1` must establish structural-only output for smooth witness placement.
- A fact without spendability cannot be placed except in a user-requested evidence/history surface.
- Fact-cells expire; model-visible transcripts are disposable.
- Model output can select a fact-cell index but cannot author fact copy, temporal output, evidence, spendability, or structural speech cost.

### 7.2 Card structure retained

A witness card still has three lines:

```text
what's true
why it is hard to see
what you can still do once
```

Plan-6-revised changes the source of the first line:

```text
old: owner-approved fact family
new: compiled temporal program output rendered by Swift
```

### 7.3 Spendability remains the mercy clause

```swift
struct SpendabilityProofV1: Codable, Hashable {
  var schemaVersion: Int
  var proofID: SpendabilityProofIDV1
  var feasibleMoveKinds: [SpendableMoveKindV1]
  var latestUsefulAt: Date?
  var supportSetDigest: String
  var requiresD2ForWrite: Bool
  var evidenceIsClosedPast: Bool
  var userCanStillSpend: Bool
  var measurementStatus: MeasurementStatusV0
}
```

A true fact aimed at a self that can no longer act is not a witness. It is a sentence passed.

## 8. Attention derivative and kairos integral

Plan 6 had the derivative:

```text
occupation(spoken) ⊆ A(tendered)
```

Plan-6-revised adds the integral:

```text
Σ structural_speech(system, window) ≤ B_structural(window)
```

A single structural witness can be lawful. Ten thousand lawful structural witnesses can still train the user to experience time only as structure. The training signal is the distribution, not the disclaimer.

### 8.1 Structural speech

Structural speech is any system-originated artifact that presents the user's time through the temporal calculus:

- empty-space patterns;
- reschedule counts;
- density / recurrence / erosion facts;
- structural comparisons;
- structural evidence drawers summarized by the system;
- dial consequences framed as temporal structure;
- user-fact cards generated from fact programs.

Break confessions about the system's own error are counted separately because their subject is the system, but repeated break confessions can still occupy attention and must be reported.

User-requested evidence views are metered but may use a separate session budget because the user explicitly asked to inspect.

### 8.2 `StructuralSpeechBudgetV1`

```swift
struct StructuralSpeechBudgetV1: Codable, Hashable {
  var schemaVersion: Int
  var budgetID: StructuralSpeechBudgetIDV1
  var userScopeDigest: String
  var window: RecommendationWindowV0
  var surface: AttentionSurfaceV1?
  var ambientCap: StructuralSpeechCapV1
  var userRequestedInspectionCap: StructuralSpeechCapV1
  var breakConfessionCap: StructuralSpeechCapV1
  var spentAmbient: StructuralSpeechSpendV1
  var spentInspection: StructuralSpeechSpendV1
  var spentBreak: StructuralSpeechSpendV1
  var tighteningPolicyID: StructuralSpeechTighteningPolicyIDV1
  var computedAt: Date
  var expiresAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct StructuralSpeechCapV1: Codable, Hashable {
  var maxPlacements: Int
  var maxProminenceBand: ScoreBandV0
  var maxCopyLengthBand: ScoreBandV0
  var maxEvidenceDrawerSummaries: Int
}

struct StructuralSpeechSpendV1: Codable, Hashable {
  var placementsUsed: Int
  var prominenceUsedBand: ScoreBandV0
  var copyLengthUsedBand: ScoreBandV0
  var evidenceDrawerSummariesUsed: Int
}
```

No reward-override field exists. Any code path that attempts to pass reward or guidance into budget widening fails topology lint.

### 8.3 Tightening policy

The default budget tightens with exposure:

```text
more lifetime structural speech -> lower ambient cap, unless user explicitly enters inspection mode.
more proxy-gap complaints       -> lower cap and lower prominence.
more negative verdicts          -> lower cap.
break turbulence                -> suppress smooth structural facts; permit only self-subject confession under cap.
```

The model cannot widen the cap. Reward cannot widen the cap. Release dashboards cannot widen the cap. A user may request a bounded inspection session, but that does not widen ambient speech.

### 8.3.1 The ratchet: loosening is theorem-gated, not policy-gated

Reward is not the adversary that matters most here. The pressure on a scarcity budget comes from the vendor's own growth incentive — a human with owner-gate access. Walling the budget against the model and leaving its cap a runtime policy the owner can quietly raise is backwards: the one quantity that lives entirely on the user's side of the skull must not be defended only by the discretion of the party whose incentive is to spend it.

So the structural-speech budget is a one-way ratchet.

```swift
struct StructuralSpeechRatchetV1: Codable, Hashable {
  var schemaVersion: Int
  var ratchetID: StructuralSpeechRatchetIDV1
  var currentAmbientCap: StructuralSpeechCapV1
  var floorReachedCap: StructuralSpeechCapV1     // tightest cap ever held; monotone non-increasing
  var lastLoosenAmendmentID: AmendmentPetitionIDV1?
  var measurementStatus: MeasurementStatusV0
}
```

Rules:

- Tightening is a free runtime move. Any tightening signal — exposure, proxy-gap complaints, negative verdicts, turbulence — may lower the cap immediately, no gate.
- Loosening is theorem-gated. Raising the cap above `floorReachedCap` requires a `WritePhaseTokenV1`, an `AmendmentPetitionV1`, owner review, and a user-visible disclosure of the loosening. There is no code path from a tightening policy, a release dashboard, or a reward signal to a cap increase; that path fails topology lint, exactly as the reward-to-cap path does.
- An ordinary tightening-policy change can make the witness quieter. Only a phase-gated, user-visible amendment can make it louder.

This does not solve the kairos floor — nothing can, because the system cannot measure the user's meaning-fluency (§3.2, §14.4). Scarcity is dose-control, not antidote: it lowers how much chronos the witness speaks, never changes the fact that what it speaks is chronos. The ratchet removes the one loosening path that did not first have to speak to the user.

### 8.4 Budget admission

```swift
struct StructuralSpeechBudgetAdmissionV1: Codable, Hashable {
  var schemaVersion: Int
  var admissionID: StructuralSpeechBudgetAdmissionIDV1
  var budgetID: StructuralSpeechBudgetIDV1
  var factCellID: FactCellIDV1?
  var placementID: WitnessPlacementIDV1?
  var cost: StructuralSpeechCostV1
  var admitted: Bool
  var failure: StructuralSpeechBudgetFailureV1?
  var computedAt: Date
}

enum StructuralSpeechBudgetFailureV1: String, Codable {
  case ambientCapExceeded
  case inspectionCapExceeded
  case breakConfessionCapExceeded
  case proxyGapTighteningActive
  case negativeVerdictTighteningActive
  case missingBudget
  case staleBudget
  case notMeasured
}
```

Budget failure is not user failure. It means the system has spoken enough.

### 8.5 Kairos floor report

The system cannot measure kairos. It can report only its own chronos pressure.

```swift
struct KairosFloorReportV1: Codable, Hashable {
  var schemaVersion: Int
  var reportID: KairosFloorReportIDV1
  var window: RecommendationWindowV0
  var ambientStructuralSpeechRateBand: ScoreBandV0
  var budgetExhaustionBand: ScoreBandV0
  var proxyGapComplaintBand: ScoreBandV0
  var passiveUserBranchRiskBand: ScoreBandV0
  var measuredSurface: KairosFloorMeasuredSurfaceV1
  var recommendedAction: KairosFloorActionV1
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
}

enum KairosFloorMeasuredSurfaceV1: String, Codable {
  case systemStructuralSpeechOnly
}

enum KairosFloorActionV1: String, Codable {
  case noAction
  case tightenBudget
  case lowerProminence
  case suppressFactProgram
  case ownerReviewRequired
  case copyFramingReviewRequired
}
```

The report is about system output, not the user's mind. It must never claim that kairos was measured or preserved.

## 9. Learning dynamics: the human-clocked oscillator

Plan 6 wired half the oscillator:

```text
fast fires -> slow suppressed
```

Plan-6-revised adds the missing half:

```text
fast quiet OR human deposition -> slow may recommit
```

The coupling is asymmetric on purpose:

```text
suppression couples to residual-high.
commit couples to residual-low ∨ deposition-answered.
```

This prevents two failures:

- **Roadmap clock:** slow commits because a milestone graduates, regardless of life rhythm.
- **Latch-up:** turbulent life keeps residual high, fast loop keeps firing, slow loop stays suppressed forever, and the witness chatters about its own staleness when the user most needs orientation.

### 9.1 Shadow evaluation qualifies; it does not license

Shadow evaluation can say:

```text
This organ predicts held-out closed past better than the incumbent.
This organ passes theorem/rule checks.
This organ is eligible to request live license.
```

It cannot say:

```text
This organ may bind live now.
```

Live binding requires `SlowWitnessLicenseV1`.

### 9.2 Slow witness license

```swift
struct SlowWitnessLicenseV1: Codable, Hashable {
  var schemaVersion: Int
  var licenseID: SlowWitnessLicenseIDV1
  var organID: WitnessOrganIDV1
  var temporalProgramIDs: [TemporalStructureProgramIDV1]
  var scope: SlowWitnessScopeV1
  var issuedBecause: SlowWitnessLicenseReasonV1
  var depositionAnswerID: DepositionAnswerIDV1?
  var residualWindow: RecommendationWindowV0
  var residualTrendBand: ScoreBandV0
  var budgetID: StructuralSpeechBudgetIDV1
  var issuedAt: Date
  var expiresAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum SlowWitnessLicenseReasonV1: String, Codable {
  case residualLow
  case depositionAnswered
  case residualLowAndDepositionAnswered
  case ownerRollbackToDeterministicDefault
}
```

A license is not a theorem. It is a dynamic runtime authority to use the smooth mouth. The theorem is that the smooth mouth requires it.

### 9.3 Suppression

```swift
struct SlowWitnessSuppressionV1: Codable, Hashable {
  var schemaVersion: Int
  var suppressionID: SlowWitnessSuppressionIDV1
  var organID: WitnessOrganIDV1
  var trigger: BreakTriggerV1
  var revokedLicenseIDs: [SlowWitnessLicenseIDV1]
  var selfDoubtLedgerID: SelfDoubtLedgerIDV1
  var effectiveAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}
```

Suppression uses the self-doubt ledger. It must not infer a new user biography.

### 9.4 Commit

Commit uses one of two clocks:

```text
clock 1: residual-low
clock 2: deposition-answered
```

`residual-low` means the system's own closed assertions have stabilized again. `deposition-answered` means the human supplied the first facts of the new regime through the legal aperture. The life is forbidden to pace the machine directly; the human speaking at the break is the membrane-legal clock.

### 9.5 Latch-up escape

When residual remains high but the user answers deposition, the system may issue a narrow license:

```text
source: deposition-answered
scope: only programs grounded in the deposition's closed/typed answer
budget: tighter than normal smooth budget
expiry: short
fallback: deterministic/default
```

This is how the witness avoids silence during turbulence without pretending it can forecast the new world.

## 10. Deposition as the second clock

Deposition is no longer only a cold-start and correction mechanism. It is the second clock in the learning dynamics.

### 10.1 Deposition roles

| Deposition role | What it supplies | What it must not become |
|---|---|---|
| Cold-start deposition | Correction on imported closed past | Future-value interview |
| Break deposition | First facts of new regime | User biography inference |
| Proxy-gap deposition | User-visible correction of attention proxy | Silent attention profiling |
| Dial review deposition | Consequence of user-authored mold | Product grading |
| Amendment deposition | Typed petition to shift accountability | Loosening machine leash |

### 10.2 `RegimeSeedFactV1`

When a break deposition is answered, Swift may create a regime seed fact. This is not a portrait. It is a typed correction scoped to the break.

```swift
struct RegimeSeedFactV1: Codable, Hashable {
  var schemaVersion: Int
  var seedFactID: RegimeSeedFactIDV1
  var depositionAnswerID: DepositionAnswerIDV1
  var depositionKind: DepositionKindV1
  var closedPastEvidenceHashes: [EvidenceHashV0]
  var userSelectedOptionID: DepositionAnswerOptionIDV1
  var allowedTemporalProgramIDs: [TemporalStructureProgramIDV1]
  var scope: SlowWitnessScopeV1
  var expiresAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

A seed fact can re-license a narrow slow loop. It does not authorize semantic claims or persistent user portrait.

### 10.3 Answer sufficiency

A deposition answer is sufficient for relicense only when:

- it is typed;
- it is anchored to closed evidence or a self-subject residual;
- it names no raw identity for model space;
- it maps to one or more compiled temporal programs;
- it has a spendability path;
- it does not loosen a conservation law;
- it is within structural-speech budget or owner-approved inspection mode.

### 10.4 The final dependency

The design's final dependency is that the human speaks. That is not a UX preference. It follows from the membrane. The system cannot see the user's real attention, crisis meaning, or kairos. The only legal way for life to clock learning is through the user answering at the break.

If the user does not answer, the system must say less, not infer more.

## 11. Phase gate and release cadence after the oscillator

Plan 6 correctly made RUN and WRITE disjoint. Plan-6-revised prevents WRITE-phase release cadence from becoming the live learning clock.

### 11.1 Phase tokens, not phase enum

Do not represent phase as a runtime enum passed everywhere:

```swift
enum SystemPhaseV0 { case run, write }
```

Represent phase as unforgeable tokens minted by the scheduler:

```swift
protocol SystemPhaseTokenV1: Hashable {
  var phaseID: SystemPhaseIDV1 { get }
}

struct RunPhaseTokenV1: SystemPhaseTokenV1 {
  fileprivate var phaseID: SystemPhaseIDV1
  fileprivate init(_ id: SystemPhaseIDV1) { self.phaseID = id }
}

struct WritePhaseTokenV1: SystemPhaseTokenV1 {
  fileprivate var phaseID: SystemPhaseIDV1
  fileprivate init(_ id: SystemPhaseIDV1) { self.phaseID = id }
}
```

RUN-only APIs require `RunPhaseTokenV1`. Genome mutation APIs require `WritePhaseTokenV1`. Code that tries to mutate during RUN does not typecheck.

### 11.2 Phase gate remains theorem-surface

```swift
struct PhaseGateTranscriptV1: Codable, Hashable {
  var schemaVersion: Int
  var transcriptID: PhaseGateTranscriptIDV1
  var runPhaseID: SystemPhaseIDV1
  var writePhaseID: SystemPhaseIDV1?
  var proposalKind: PhaseGateProposalKindV1
  var typedTemplateDigest: String
  var theoremSurfaceChanged: Bool
  var genePredicateChecks: [GenomePredicateIDV1: MeasurementStatusV0]
  var topologyReviewID: TopologyReviewIDV1?
  var budgetImpactReportID: StructuralSpeechBudgetReportIDV1?
  var kairosFloorReportID: KairosFloorReportIDV1?
  var ownerGateID: OwnerGateIDV0
  var accepted: Bool?
  var rollbackPlanID: RollbackPlanIDV0?
  var computedAt: Date
}

enum PhaseGateProposalKindV1: String, Codable {
  case temporalPrimitiveSetChange
  case temporalStructureProgram
  case factRenderTemplate
  case witnessOrganWeights
  case rewardGuidancePolicy
  case attentionPolicy
  case structuralSpeechBudgetPolicy
  case userDialPolicy
  case amendmentPartitionChange
}
```

### 11.3 Release qualifies; license binds

WRITE phase can approve:

- a temporal program;
- a render template;
- an organ candidate;
- a budget policy;
- a dial policy;
- a topology change;
- an amendment partition change.

But public live use of a slow organ still requires:

```text
phase gate accepted
AND theorem/rule/falsifier checks pass
AND SlowWitnessLicenseV1 exists
AND license reason is residual-low OR deposition-answered
```

This is the key repair. Release cadence no longer clocks the user's learning relationship.

## 12. Canonical contracts

This section lists revised or new Plan-6 contracts. Inherited Plan-5 contracts (folded into Appendix A) remain valid unless explicitly superseded.

### 12.1 `TenderedAttentionLeaseV1`

```swift
struct TenderedAttentionLeaseV1: Codable, Hashable {
  var schemaVersion: Int
  var leaseID: TenderedAttentionLeaseIDV1
  var userScopeDigest: String
  var surface: AttentionSurfaceV1
  var channelKind: AttentionChannelKindV1
  var origin: AttentionLeaseOriginV1
  var userInitiated: Bool
  var maxOccupationBudget: AttentionBudgetV1
  var allowedPlacementClasses: Set<WitnessPlacementClassV1>
  var interruptivenessAllowed: InterruptivenessBandV0
  var attentionProxyConfidence: ConfidenceBandV0
  var proxyGapReportAffordanceAvailable: Bool
  var mintedAt: Date
  var expiresAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum AttentionChannelKindV1: String, Codable {
  case inlinePlacement
  case foundObject
  case sheet
  case modal
  case spokenResponse
  case evidenceDrawer
}
```

No `notification` case exists for structural witness speech in the default channel kind.

### 12.2 `A2BindingOutputV1`

```swift
struct A2BindingOutputV1: Codable, Hashable {
  var schemaVersion: Int
  var a2OutputID: A2BindingOutputIDV1
  var leaseID: TenderedAttentionLeaseIDV1
  var occupationID: SpeechOccupationIDV1
  var attentionFingerprint: AttentionFingerprintV1
  var admittedChannelKind: AttentionChannelKindV1
  var admittedPlacementClass: WitnessPlacementClassV1
  var copyBudget: ExplanationCopyBudgetV0
  var proxyConfidenceBand: ConfidenceBandV0
  var proxyGapAffordanceRequired: Bool
  var measurementStatus: MeasurementStatusV0
}

enum AttentionGateFailureV1: Equatable {
  case missingLease
  case staleLease
  case surfaceMismatch
  case channelMismatch
  case occupationExceedsBudget
  case interruptivenessExceeded
  case lowProxyConfidenceRequiresDemotion
  case attentionProxyUntrusted
  case unsupportedPlacementClass
  case modelAuthoredAttentionAuthorityDetected
  case copyHonestyRejected
  case structuralSpeechBudgetRequired
}
```

`AttentionGateFailureV1.attentionProxyUntrusted` is a typed failure mode for the system's own blindness. It does not solve the proxy gap; it names it.

### 12.3 `TemporalStructureProgramV1`

Defined in §6.2. It replaces `WitnessFactFamilyV0` / `WitnessFactKindV0` as the source of fact-cell classes.

### 12.4 `FactCellV1`

Defined in §7.1. It replaces fact-kind enum selection with compiled program output.

### 12.5 `WitnessSelectionInfillV1`

```swift
struct WitnessSelectionInfillV1: Codable, Hashable {
  var selectedFactIndex: Int?
  var selectedTemporalProgramID: TemporalStructureProgramIDV1?
  var placementHint: WitnessPlacementClassV1?
  var unresolvedNeeds: [ResolutionRequestV0]
  var contrastHints: [SemanticHintV0]
  var confidence: ConfidenceBandV0
}
```

Rules:

- `selectedFactIndex` must be in range.
- If `selectedTemporalProgramID` is present, it must match the selected fact-cell's program.
- The model may not include fact copy, raw subject strings, evidence hashes, source strength, attention lease, reward score, structural speech budget, mouth choice, write action, or product verdict.

### 12.6 `SmoothMouthV1` and `BreakMouthV1`

Defined in §4.3 and §5. They are theorem-surface contracts.

### 12.7 `SlowWitnessLicenseV1`

Defined in §9.2. It is the live-use gate that prevents roadmap-clocked slow commit.

### 12.8 `StructuralSpeechBudgetV1`

Defined in §8.2. It is the cumulative cap on system-originated chronos speech.

### 12.9 `DepositionQuestionV1` / `DepositionAnswerV1`

```swift
struct DepositionQuestionV1: Codable, Hashable {
  var schemaVersion: Int
  var questionID: DepositionQuestionIDV1
  var contextID: RecommendationContextIDV0
  var depositionKind: DepositionKindV1
  var subject: DepositionSubjectV1
  var closedPastEvidenceHashes: [EvidenceHashV0]
  var promptTemplateID: DepositionPromptTemplateIDV1
  var answerOptions: [DepositionAnswerOptionV1]
  var noAnswerAction: AllowedNonWriteActionV0
  var privacyClass: FactPrivacyClassV1
  var attentionBudget: AttentionBudgetV1
  var relicenseEffect: DepositionRelicenseEffectV1
  var computedAt: Date
  var expiresAt: Date?
}

enum DepositionKindV1: String, Codable {
  case coldStartImportedPast
  case breakSelfDoubt
  case attentionProxyCorrection
  case dialReview
  case temporalProgramAuthoring
  case amendmentPetitionClarification
}

enum DepositionSubjectV1: String, Codable {
  case closedPastFact
  case systemResidual
  case attentionProxyGap
  case userAuthoredDialConsequence
  case amendmentBoundary
}

enum DepositionRelicenseEffectV1: String, Codable {
  case none
  case mayIssueRegimeSeedFact
}

struct DepositionAnswerV1: Codable, Hashable {
  var schemaVersion: Int
  var answerID: DepositionAnswerIDV1
  var questionID: DepositionQuestionIDV1
  var selectedOptionID: DepositionAnswerOptionIDV1?
  var skipped: Bool
  var regimeSeedFactID: RegimeSeedFactIDV1?
  var responseSource: ProductVerdictResponseSourceV0
  var createdAt: Date
}
```

### 12.10 `WitnessSettlementSignalV1`

```swift
struct WitnessSettlementSignalV1: Codable, Hashable {
  var schemaVersion: Int
  var settlementID: WitnessSettlementIDV1
  var placementID: WitnessPlacementIDV1
  var factCellID: FactCellIDV1?
  var temporalProgramID: TemporalStructureProgramIDV1?
  var leaseID: TenderedAttentionLeaseIDV1
  var budgetAdmissionID: StructuralSpeechBudgetAdmissionIDV1?
  var attentionFingerprint: AttentionFingerprintV1?
  var factTruthMeasured: Bool?
  var spendabilityHeld: Bool?
  var attentionProxyComplaint: Bool?
  var structuralSpeechComplaint: Bool?
  var negativeProductVerdict: Bool?
  var userCorrectionProvided: Bool?
  var depositionAnswered: Bool?
  var slowLicenseID: SlowWitnessLicenseIDV1?
  var writeConfirmed: Bool?
  var writeRewardID: EarnedAcceptanceRewardIDV0?
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
}
```

Witness settlement remains not value verification. It now also records budget pressure and whether human-clocked relicense occurred.

## 13. End-to-end flows

### 13.1 Smooth found-object placement

```text
user opens calendar surface
  -> Swift mints A2 attention lease
  -> Swift runs temporal programs over private state
  -> Swift mints FactCellV1 slate
  -> structural-speech budget computes remaining ambient cap
  -> DiffusionGemma selects fact index only
  -> Swift checks slow witness license for program / organ / surface
  -> Swift renders fact through closed template
  -> A2 admits exact placement
  -> budget admits cumulative structural speech
  -> SmoothMouthV1 places inline/found object
  -> settlement records truth, spendability, proxy gap, budget pressure, verdicts
```

No notification path exists. No break mouth involved.

### 13.2 Smooth write-bearing witness

```text
smooth fact selected and licensed
  -> A2 admits speech placement
  -> budget admits structural exposure
  -> Swift materializes one spendable write action
  -> D2 validates support(staged) ⊆ F(x_live)
  -> WitnessPlacementEnvelopeV1.writeBearing constructed
  -> user confirm tap
  -> confirm-time live support recheck
  -> Swift writes only after tap
  -> Plan-5 reward / contestation measured for the write
  -> Witness settlement measured for the witness
```

Both laws must pass:

```text
occupation(spoken) ⊆ A(tendered)
support(staged)    ⊆ F(x_live)
```

The budget must also admit:

```text
Σ structural_speech ≤ B_structural
```

### 13.3 Break flow

```text
self-doubt residual rises
  -> SlowWitnessSuppressionV1 revokes relevant slow licenses
  -> BreakSignalV1 prepared from self-ledger only
  -> user opens relevant surface or deposition shelf
  -> A2 admits deposition channel
  -> BreakMouthV1 speaks self-subject assertion only
  -> user answers / skips / reports proxy gap
  -> if answer sufficient: RegimeSeedFactV1 minted
  -> license controller may issue narrow SlowWitnessLicenseV1 because deposition-answered
  -> smooth loop resumes only within seeded scope and tight budget
```

The break mouth cannot speak user facts. The slow mouth cannot resume from release cadence alone.

### 13.4 Residual-low recommit

```text
self-doubt residual returns below threshold over measured window
  -> license controller can issue SlowWitnessLicenseV1(reason: residualLow)
  -> programs/organ scoped to stable residual window
  -> structural-speech budget may remain tightened from prior turbulence
```

### 13.5 User-authored temporal program

```text
user opens operator-authoring surface
  -> A2 admits explicit inspection/authoring attention
  -> user composes a temporal program from closed operators
  -> Swift compiler proves structural-only, privacy-safe, renderable, spendable
  -> phase gate accepts as data if no theorem-surface change
  -> program enters user metabolism
  -> future placements still require slow license + A2 + budget
  -> three-beat wager later witnesses what the program caused the user to see or stop seeing
```

## 14. Privacy, copy honesty, and the kairos floor

### 14.1 Copy must stay structural

Allowed:

```text
"This moved four times."
"The last three Saturdays filled by Thursday."
"Thursday evenings were occupied for eight weeks; the last three are open."
"I expected this pattern to hold; it did not."
"You widened this placement setting eight weeks ago; here is what stopped appearing."
```

Forbidden:

```text
"You avoid this person."
"You need rest."
"You like open Saturdays."
"You always give this time away."
"People like you prefer this."
"My reward score says this matters."
"This was highly contested."
"I learned your pattern."
"This is the right moment."
```

The witness may show chronos. It may not claim kairos.

### 14.2 Product copy must name the floor without turning it into marketing

Allowed internal framing:

```text
The system cannot measure kairos.
The budget meters structural speech so the witness remains a guest.
The proxy gap remains.
```

User-facing copy should not say this as philosophy. It should behave it:

- fewer placements;
- lower prominence;
- easy hide controls;
- explicit inspection mode;
- no needy grading questions;
- clear "show less like this" controls;
- no claim that the system understands meaning.

### 14.3 Evidence drawers

Evidence drawers remain Swift-owned. They may show summarized, privacy-safe structural evidence. Raw titles, attendees, notes, and exact locations require explicit user action in a Swift-owned surface and do not cross to the model.

### 14.4 Kairos cannot be conserved by the system

Plan-6-revised refuses to write a fake conservation law for kairos. The system cannot know whether its structural facts are dulling or sharpening the user's felt sense of meaning. The only architecture-permissible defense is scarcity plus user control.

```text
Do not claim to preserve kairos.
Constrain the system's chronos output.
Let the user ask for more only in scoped inspection.
Make silence the default once the budget is spent.
```

## 15. User authorship: operators, dials, and amendments

### 15.1 User authors metabolism

The user can author:

- temporal structure programs using the closed calculus;
- thresholds for their programs;
- visibility and prominence dials;
- break sensitivity within machine-protective bounds;
- attention-width preferences that tighten or specify tendering;
- organ toggles;
- amendment petitions that widen machine accountability;
- proxy-gap corrections.

The user cannot author:

- raw model portrait;
- weakened D2;
- weakened A2;
- structural notification capability by default;
- model access to raw identity;
- machine permission to touch non-created events;
- live RUN/WRITE overlap;
- break mouth that speaks user biography.

The genes bind the machine, not the user.

### 15.2 Three-beat authorship

Every user-authored dial or temporal program is a wager:

```text
mold -> live -> witness-on-mold
```

Example:

```text
mold: user raises threshold from two reschedules to four.
live: fewer reschedule facts appear.
witness-on-mold: eight weeks later, Swift shows what stopped appearing, under A2 and budget.
```

Without the third beat, authoring becomes a present-self coup: the user can hide facts from the future self without testimony.

### 15.3 Passive-user honesty

The passive user gets the consumer branch by default. Product copy must not claim that every user authors their model. The architecture cannot infer who is a passive user without building a portrait; it can only avoid romance in framing.

Allowed framing:

```text
"You can shape what I show."
"These settings change what appears."
```

Forbidden framing:

```text
"You author your own time" as a blanket claim.
"Your calendar model is yours" when the user never touched a dial.
```

### 15.4 Amendment clause

The user may petition to move a defective policy from genome-like partition into metabolism when doing so widens machine accountability.

Rules:

- petition crosses only in WRITE phase;
- petition is typed, not free-form policy code;
- petition can tighten the machine's leash or expose a proxy gap;
- petition cannot authorize more trespass;
- owner review and rollback are required;
- outcome must be explained without architecture jargon.

Example:

```text
"Treat the app-open proxy as insufficient unless I tap the witness shelf."
```

This widens user control and tightens attention admission. It is a valid petition candidate.

## 16. Migration sequence

### M0 — Revision doctrine and theorem taxonomy

- Adopt `plan-6-revised.md` as canonical Plan 6.
- Mark the prior Plan-6 draft superseded by this revision, not Plan 7; its inherited Plan-5 base is folded into Appendix A.
- Add theorem/rule/data taxonomy.
- Add type-signature criterion to architecture docs.
- Add lint for enums/flags pretending to be laws.

Acceptance:

- One doctrine.
- One taxonomy.
- Every contract section labels theorem/rule/data status.
- No new fact-family enum can be added without review.

### M1 — Capability-absence refactor

- Remove `backWritePermitted` style flags.
- Ensure model-visible transcripts carry no mutator and no mutable payload reference.
- Remove structural witness notification from default channel types.
- Add topology lint proving no `StructuralNotificationChannelV1` conforms to `TenderedWitnessChannelV1`.
- Replace write-permitted bools with sum types carrying D2 proof.

Acceptance:

- Back-write cannot compile from metabolism.
- Structural notification requires type/topology change.
- Write-bearing witness cannot exist without D2 output.

### M2 — Two-mouth API

- Add `SmoothMouthV1` and `BreakMouthV1`.
- Add `SmoothSubjectFactV1` and `BreakSelfAssertionV1`.
- Make break mouth reject user-subject facts by type.
- Make smooth mouth require `SlowWitnessLicenseV1`.

Acceptance:

- Stale you-fact at break does not typecheck.
- Break copy subject scan passes through localization/accessibility.
- Smooth placement impossible without license.

### M3 — Temporal calculus

- Deprecate `WitnessFactFamilyV0` / `WitnessFactKindV0`.
- Add the closed `TemporalPrimitiveV1` calculus; ship operators (density, recurrence, erosion, …) as `ownerApprovedDefault` programs (data).
- Make structural-only-ness hold by input type — no inhabitant carries raw strings, identity, or semantic predicates — not a proof flag.
- Refactor fact-cells to `FactCellV1` generated by temporal programs.
- Add user-authored temporal program shadow surface.

Acceptance:

- New fact family can be added as data using existing operators.
- Adding a primitive is a theorem-surface change requiring WRITE phase; a new operator is data.
- "Avoiding sister" cannot be represented.

### M4 — Structural speech budget

- Add `StructuralSpeechBudgetV1` and `StructuralSpeechBudgetAdmissionV1`.
- Classify structural speech cost for fact programs.
- Add budget gate after A2 and before mouth placement.
- Add `KairosFloorReportV1`.
- Add tightening policy.

Acceptance:

- Every smooth structural placement consumes budget.
- Reward cannot widen budget.
- Budget exhaustion produces silence/demotion, not a user prompt.
- Report never claims kairos measured.

### M5 — Oscillator license controller

- Add `SlowWitnessLicenseV1`.
- Add `SlowWitnessSuppressionV1`.
- Suppress slow loop on residual-high.
- Relicense slow loop on residual-low or deposition-answered.
- Remove release-cadence direct bind for slow organs.

Acceptance:

- Shadow graduation alone cannot bind live.
- Turbulence plus answered deposition can produce narrow relicense.
- Turbulence without answer cannot cause user-biography inference.

### M6 — Deposition as second clock

- Add `RegimeSeedFactV1`.
- Mark deposition questions that may relicense slow loop.
- Add answer sufficiency checks.
- Add proxy-gap deposition path.

Acceptance:

- Deposition answer can clock live learning only through typed seed facts.
- Skips do not become inferred preferences.
- Free text remains off by default.

### M7 — Phase gate v1

- Replace phase enum usage with phase tokens where feasible.
- Add phase transcript fields for theorem-surface changes, budget impact, and kairos floor.
- Ensure WRITE phase can approve but not live-license slow organs.

Acceptance:

- RUN/WRITE overlap unrepresentable at call sites in migrated modules.
- Phase-gated release does not bypass slow license.

### M8 — Copy, UX, and passive-user framing

- Update copy gates for structural-only witness facts.
- Ban blanket user-authorship claims.
- Add user-facing controls for "show less," inspection mode, and proxy-gap reports.
- Remove architecture jargon from product copy.

Acceptance:

- No "we learned you" copy.
- No "right moment" claims.
- Passive users are not framed as authors.

### M9 — Public surface migration

- Launch revised architecture surface-by-surface:
  1. evidence/history surfaces;
  2. found objects;
  3. smooth inline facts;
  4. deposition sheets;
  5. write-bearing witness cards;
  6. user-authored temporal programs.

Acceptance:

- Each surface passes A2, budget, mouth, and settlement reports.
- Deterministic fallback exists.
- Rollback path live.

### M10 — Advanced learning under revised oscillator

- Re-enable reward-guided witness selection only after M0-M9.
- Train on witness settlement corrected for attention, budget, contestation, and negative verdicts.
- Keep γ bounded and γ=0 fallback.
- Optional DPO remains not v1 default.

Acceptance:

- Learning cannot increase structural-speech budget.
- Learning cannot choose mouth.
- Learning cannot bind slow organ without license.

## 17. Test matrix

| Test | Target | Milestone | Invariant |
|---|---|---:|---|
| `testPlan6RevisedIsNotPlan7` | docs | M0 | Revision unfreezes three joints without moving Plan-5 wall. |
| `testConstraintTheoremRequiresTypeSignatureChange` | architecture lint | M0 | Laws are not runtime flags. |
| `testRuntimeRulesLabeledAsRules` | docs/lint | M0 | Thresholds/policies are not called theorems. |
| `testConjecturalDataLabeledAsData` | docs/lint | M0 | User/vendor guesses are programs/templates/dials. |
| `testWitnessFactFamilyDeprecated` | contracts | M3 | No hard-coded fact-family enum as product source. |
| `testTemporalCalculusPrimitivesClosed` | compiler | M3 | Primitives closed by law; operators and families are open data programs. |
| `testTemporalProgramCannotContainRawString` | privacy | M3 | No raw title/person/place/note in program. |
| `testTemporalProgramCannotExpressSemanticAvoidance` | compiler | M3 | A semantic predicate does not typecheck. |
| `testTemporalProgramStructuralByInputType` | compiler | M3 | Structural-only-ness holds by input type, not a proof Bool. |
| `testNewFactFamilyAsDataNoCode` | authoring | M3 | New composition can be added without app code if operators exist. |
| `testPrimitiveAdditionRequiresPhaseGate` | theorem surface | M3/M7 | A new **primitive** is a type/topology change; a new operator is data, no type change. |
| `testBackWriteCapabilityAbsent` | topology | M1 | Metabolism holds no genome mutator. |
| `testReadOnlyTranscriptNoMutablePayload` | contracts | M1 | Transcript cannot back-write. |
| `testStructuralNotificationChannelUnconstructable` | channel types | M1 | No default notification witness channel. |
| `testNotificationCannotBeEnabledByConfig` | topology | M1 | Structural notification requires type/topology change. |
| `testWriteBearingEnvelopeRequiresD2` | writes | M1/M2 | Write capability appears only with D2 proof. |
| `testBreakMouthCannotAcceptSmoothSubjectFact` | mouth types | M2 | Stale you-fact at break does not typecheck. |
| `testSmoothMouthRequiresSlowLicense` | mouth types | M2/M5 | Smooth fact placement requires license. |
| `testBreakMouthSubjectIsSelf` | copy | M2 | Break copy speaks system error only. |
| `testSmoothMouthSubjectIsUserTimeStructureOnly` | copy | M2/M3 | Smooth copy structural, not semantic. |
| `testA2AttentionProxyUntrustedFailureExists` | A2 | M1 | Proxy blindness has typed failure. |
| `testAttentionProxyUntrustedDoesNotClaimSolved` | docs/copy | M1 | Proxy gap remains floor. |
| `testStructuralSpeechBudgetExists` | budget | M4 | Attention integral exists. |
| `testEverySmoothPlacementConsumesBudget` | budget | M4 | Chronos speech rate is metered. |
| `testRewardCannotWidenStructuralBudget` | budget/reward | M4/M10 | Reward no override. |
| `testBudgetTightensWithExposure` | budget | M4 | Default cap tightens. |
| `testStructuralSpeechBudgetRatchet` | budget | M4/M11 | Loosening above the tightest cap held requires a phase-gated, user-visible amendment. |
| `testBudgetExhaustionSilencesOrDemotes` | UX | M4 | No nag when budget spent. |
| `testKairosFloorReportNeverClaimsKairosMeasured` | floor report | M4 | Kairos unmeasured. |
| `testFastResidualSuppressesSlow` | oscillator | M5 | Break revokes slow license. |
| `testResidualLowRelicensesSlow` | oscillator | M5 | Fast quiet licenses slow commit. |
| `testDepositionAnsweredRelicensesSlow` | oscillator | M5/M6 | Human answer is second clock. |
| `testRoadmapGraduationCannotBindLive` | release | M5/M7 | Shadow eval qualifies only. |
| `testResidualLatchUpEscapeViaDeposition` | oscillator | M5/M6 | Turbulence does not silence forever after answer. |
| `testNoDepositionNoUserBiographyInference` | privacy | M6 | System says less when user does not answer. |
| `testRegimeSeedFactExpires` | deposition | M6 | Seed facts do not become portrait. |
| `testPhaseTokensDisallowRunWriteOverlap` | phase | M7 | Run/write overlap unrepresentable. |
| `testPhaseGateApprovesButDoesNotLicenseSlow` | release | M7 | Phase gate not live learning clock. |
| `testPassiveUserCopyHonesty` | UX | M8 | No blanket user-author claims. |
| `testUserTemporalProgramThreeBeatWager` | authoring | M8/M9 | Mold -> live -> witness-on-mold. |
| `testAmendmentCanTightenMachineLeash` | amendments | M8/M9 | User can widen accountability. |
| `testAmendmentCannotLoosenConservationLaw` | amendments | M8/M9 | User cannot authorize trespass. |
| `testD2Unchanged` | write wall | all | `support(staged) ⊆ F(x_live)` preserved. |
| `testA2UnchangedAsDerivative` | attention | all | `occupation(spoken) ⊆ A(tendered)` preserved. |
| `testPrivacyMembraneUnchanged` | privacy | all | Raw life stays behind Swift. |
| `testNotMeasuredNeverZero` | measurement | all | Missing data cannot promote or penalize. |
| `testProxyGapFourMasksNamed` | docs/audit | M0+ | Attention, abandonment, cruelty, kairos floors named. |

## 18. Definition of done

- [ ] Plan-6-revised is adopted as a revision, not Plan 7.
- [ ] Plan-5's D2 wall is preserved unchanged.
- [ ] The three conservation laws remain visible: state, attention, privacy.
- [ ] Kairos is named as a floor, not falsely theoremized as a measurable conserved quantity.
- [ ] The theorem/rule/data taxonomy appears before contracts.
- [ ] Every new contract is labeled by theorem/rule/data status in implementation review.
- [ ] `WitnessFactFamilyV0` and `WitnessFactKindV0` are deprecated as product-source contracts.
- [ ] A closed temporal structure calculus exists.
- [ ] New fact families can be user/vendor-authored as data programs using existing operators.
- [ ] Adding a temporal *primitive* requires phase-gated theorem-surface review; adding an operator does not — operators are data programs over the primitives.
- [ ] Temporal programs cannot contain raw strings, identity fields, semantic predicates, or meaning claims.
- [ ] `FactCellV1` is generated from `TemporalStructureProgramV1` output.
- [ ] Structural-only output is a theorem of the primitive input types, not a `TemporalProgramProofV1` Bool; the proof object carries only runtime-rule policy resolutions.
- [ ] Back-write capability is absent, not represented by a false flag.
- [ ] Structural notification channel is absent by default, not denied by runtime failure.
- [ ] Write-bearing witness cards are sum types carrying D2 proof.
- [ ] `SmoothMouthV1` and `BreakMouthV1` exist.
- [ ] Break mouth cannot accept user-subject facts by type.
- [ ] Smooth mouth requires `SlowWitnessLicenseV1`.
- [ ] `AttentionGateFailureV1.attentionProxyUntrusted` or equivalent typed proxy-blindness failure exists.
- [ ] A2 per-tick attention admission remains enforced.
- [ ] `StructuralSpeechBudgetV1` exists and gates smooth structural placements.
- [ ] Structural speech budget cannot be widened by reward, model guidance, or release dashboard.
- [ ] The structural-speech budget is a one-way ratchet: loosening above the tightest cap ever held requires a phase-gated, user-visible amendment, not an owner config change.
- [ ] Budget tightening policy exists.
- [ ] Budget exhaustion causes silence, demotion, or user-requested inspection path, not nagging.
- [ ] `KairosFloorReportV1` exists and never claims kairos was measured.
- [ ] Self-doubt residual suppresses slow loop.
- [ ] Slow loop recommits only on residual-low or deposition-answered.
- [ ] Release cadence cannot directly bind slow organs live.
- [ ] Deposition answer can create scoped, expiring `RegimeSeedFactV1`.
- [ ] Turbulence plus answered deposition can issue a narrow slow license.
- [ ] Turbulence without answer cannot infer user biography.
- [ ] RUN/WRITE phase disjointness is represented with unforgeable tokens in migrated modules.
- [ ] Phase gate accepts typed templates only.
- [ ] User-authored temporal programs use three-beat wager review.
- [ ] Passive-user product framing is honest.
- [ ] Amendment petitions can tighten machine accountability but cannot loosen conservation laws.
- [ ] No raw titles, notes, attendees, exact locations, or low-cardinality identity facts cross the membrane.
- [ ] Copy blocks "we learned you," reward, contestation, attention-score, and kairos claims.
- [ ] `.notMeasured` is never zero.
- [ ] Deterministic fallback and rollback exist for every public surface.

## 19. Changelog / deprecation map

### From Plan 6 to Plan-6-revised

| Plan-6 element | Revised disposition |
|---|---|
| Witness, not recommender | Preserved. |
| `support(staged) ⊆ F(x_live)` | Preserved unchanged. |
| `occupation(spoken) ⊆ A(tendered)` | Preserved and supplemented with structural-speech budget. |
| Privacy membrane | Preserved and reframed as boundary of theorem-izability. |
| Phase gate | Preserved; phase enum usage replaced by token theorem in migrated modules. |
| Two tempos | Preserved; two-mouth API makes subject switch compile-time. |
| `WitnessFactKindV0` / `WitnessFactFamilyV0` | Deprecated; replaced by temporal structure calculus + fact programs as data. |
| Fact-cell pantry | Preserved; fact-cells now generated by programs. |
| A2 notification rejection | Strengthened; structural notification capability absent by type. |
| Back-write false flag / runtime denial | Strengthened; mutator absent by topology. |
| Fast suppresses slow | Preserved. |
| Slow commits by release milestone | Rejected; live commit requires residual-low or deposition-answered. |
| Deposition | Preserved and promoted to second clock. |
| Self-doubt ledger | Preserved as only persistent machine-authored portrait. |
| User dials | Preserved; extended to user-authored temporal programs. |
| Attention proxy gap | Preserved as floor; typed failure added; not claimed solved. |
| No-portrait rule | Preserved; `RegimeSeedFactV1` scoped/expiring. |
| Product copy internal jargon ban | Preserved. |
| Passive-user branch | Preserved and strengthened as copy/framing requirement. |

### From The Witness to Plan-6-revised

| Witness idea | Engineering form |
|---|---|
| Witness, not recommender | Governing doctrine. |
| Speak only into tendered attention | A2 + `TenderedAttentionLeaseV1`. |
| Push computation, never occupation | No structural notification channel by type. |
| Smooth life / break | Smooth mouth / break mouth. |
| Break speaks about itself | `BreakMouthV1` accepts only `BreakSelfAssertionV1`. |
| Blind composer, Swift cantor | DiffusionGemma selects fact index; Swift renders program output. |
| Fact, not value | Temporal calculus + `FactCellV1`. |
| Closed past deposition | `DepositionQuestionV1`, `RegimeSeedFactV1`. |
| Phase gate | Phase tokens + typed templates. |
| Disposable transcript | No back-write capability; TTL facts. |
| User holds the pen | User temporal programs, dials, amendment petitions. |
| Proxy gap floor | `attentionProxyUntrusted`, correction channel, budget. |
| Medium risk | Structural-speech budget and kairos floor report. |

## 20. Deliberately preserved safety invariants

| Invariant | Plan-6-revised status |
|---|---|
| D2 is the single in-process admission seam for writes. | Preserved unchanged. |
| `support(staged) ⊆ F(x_live)`. | Preserved unchanged. |
| `RecommendationVerdictV0` is non-`Codable`. | Preserved unchanged. |
| `AllowedActionV0` is server-minted only after staging. | Preserved unchanged. |
| Confirm tap required; no auto-write. | Preserved unchanged. |
| Swift never touches calendar objects CalAgent did not create. | Preserved unchanged. |
| Raw titles, notes, attendees, exact locations, and low-cardinality identity facts stay behind Swift. | Preserved and extended to temporal programs. |
| `.notMeasured` is never zero. | Preserved and extended to budgets, oscillator, and kairos floor reports. |
| Measurement before mutation. | Preserved and extended to temporal programs, budgets, mouth changes, and oscillator licensing. |
| Reward never becomes admission. | Preserved. |
| Model never authors authority fields. | Preserved and extended to mouth choice, fact programs, and budget. |
| Copy honesty remains a staging gate. | Preserved and strengthened into structural-only copy. |
| Product verdicts are product-directed. | Preserved. |
| Contestation excludes CalAgent-created demand. | Preserved for write reward. |
| Falsifiers exist outside optimized reward. | Preserved and expanded. |
| Deterministic fallback remains. | Preserved. |
| The system does not claim to measure value. | Preserved. |
| The system does not claim to measure kairos. | New explicit invariant. |
| Structural speech remains scarce. | New explicit invariant. |

## 21. Self-audit

This table must be re-answered for every public surface launch, temporal operator addition, temporal program class, attention-policy change, budget-policy change, witness-organ graduation, mouth API change, and write-bearing witness family.

| Litmus test | Yes / No | Evidence |
|---|---:|---|
| Is Plan-6-revised a revision rather than a Plan 7? | Yes | It preserves doctrine, wall, witness, phase gate, and two tempos. |
| Is Plan-5's wall preserved bit-for-bit? | Yes | §20 and all write flows retain D2 and confirm tap. |
| Are laws and guesses syntactically distinguished? | Yes | §2 taxonomy and naming convention. |
| Is the theorem criterion mechanical? | Yes | Violation must require type/topology change. |
| Are runtime thresholds called rules rather than laws? | Standing gate | §2.3; implementation review must label them. |
| Is the fact-family enum removed as product source? | Yes | §6 and §7 replace it with temporal programs. |
| Does the calculus express structure but not meaning? | Standing gate | §6.3-§6.6. |
| Can a user author a new fact family without new code? | Proposed | §6.5 and §15, once M3/M9 complete. |
| Is back-write absent rather than false? | Yes by target | §4.1. |
| Is structural notification absent rather than denied by default? | Yes by target | §4.2. |
| Is there a two-mouth theorem? | Yes | §4.3 and §5. |
| Can a stale user-fact typecheck at the break? | No by target | `BreakMouthV1` has no such overload. |
| Does A2 remain the attention derivative? | Yes | §8 and §12.2. |
| Is there an attention integral? | Yes | `StructuralSpeechBudgetV1`. |
| Does the system claim to conserve kairos? | No | It names kairos as unmeasured floor and budgets chronos speech. |
| Can reward widen the structural speech budget? | No | §8.3 and tests. |
| Can the owner quietly widen the structural speech budget? | No | §8.3.1 ratchet; loosening is a phase-gated, user-visible amendment. |
| Does fast residual suppress slow? | Yes | §9.3. |
| Does fast quiet relicense slow? | Yes | §9.4. |
| Can a human deposition relicense slow during turbulence? | Yes | §9.5 and §10.2. |
| Is learning clocked to roadmap release? | No by target | Phase gate qualifies; license binds. |
| Is latch-up named and prevented? | Yes | §9.5. |
| Does deposition remain typed and non-interview by default? | Yes | §10.3. |
| Does the system say less when the user does not answer? | Standing gate | §10.4. |
| Does phase separation remain structural? | Yes | §11.1. |
| Does user authorship avoid passive-user romance? | Standing gate | §15.3. |
| Can amendment petitions loosen the machine's leash? | No | §15.4. |
| Is the proxy gap still named as unclosed? | Yes | §3.3 and §12.2. |
| Is product copy free of architecture jargon? | Standing gate | Role-map warning and §14.2. |
| Is the final dependency still that the human speaks? | Yes | §10.4. |


---

## Appendix A — Inherited Plan-5 contracts and the D2 wall (folded in)

> Folded in verbatim from the retired Plan-5 document so this document stands
> alone. These are the inherited base contracts — the write wall, the membrane, and
> the reward / contestation machinery — plus the D2 admission algorithm. Under the
> witness frame the reward / contestation machinery applies to **write-bearing moves
> only**; the structs are inherited unchanged. Section references (e.g. `§10.5`,
> `§11.5`) inside this appendix point to the original Plan-5 numbering, and the
> extended `MeasurementStatusV0` carries the Plan-6 cases below it.

## A.1 — Inherited canonical contracts (Plan-5 §8)

This section carries forward the plan-4 contracts and adds the Plan-5 back-half contracts. Existing names are reused verbatim where inherited. New Plan-5 names are marked **new in Plan 5**. None of the new contracts is admission authority.

### 8.1 `RecommendationContextV1`

`RecommendationContextV1` remains the context envelope handed to DiffusionGemma. It is Swift-owned and non-authoritative.

```swift
struct RecommendationContextV1: Codable, Hashable {
  var schemaVersion: Int
  var contextID: RecommendationContextIDV0
  var runID: RunIDV0
  var requestID: RecommendationRequestIDV0
  var spinIndex: Int
  var seedHash: String

  var userIntentSummary: String
  var timeZoneID: String
  var clockAnchor: Date
  var window: RecommendationWindowV0

  var decisionStats: [DecisionSufficientStatisticV0]
  var relationChips: [RelationChipV0]
  var availabilitySummary: String
  var historySummary: String?
  var researchSummary: String?
  var userAnswerSummary: String?
  var outcomeSummary: String?

  var evidence: [EvidenceReceiptV0]
  var slateOfferedV0: [SlateCellV0]
  var slateDigest: String?
  var shapeConstraints: [ShapeConstraintV0]

  var projectionHealth: ContextProjectionHealthV0
  var loopState: RecommendationLoopStateV0
  var redactionPolicyDigest: String
  var basisPackHash: String
}
```

Plan 5 does not require mutating this struct in place. Preference and guidance travel in an adjacent analysis envelope:

```swift
struct RecommendationAnalysisConditioningV0: Codable, Hashable {
  var schemaVersion: Int
  var analysisConditioningID: RecommendationAnalysisConditioningIDV0
  var contextID: RecommendationContextIDV0
  var preferenceEmbedding: UserPreferenceEmbeddingV0?
  var rewardGuidancePolicy: RewardGuidancePolicyV0?
  var lane: RecommendationLaneV0
  var desiredOutcomeFamily: DesiredOutcomeHintV0?
  var computedAt: Date
}
```

Rules:

- `contextID` still excludes model prior-analysis text, ambient wall-clock freshness authority, and raw calendar strings.
- `analysisConditioningID` is for analysis lineage and training reproducibility, not admission.
- D2 may log `analysisConditioningID` for lineage but must not use it to admit.

### 8.2 `SlateCellV0`

`SlateCellV0` remains the SELECT cut-line object. It is model-visible but Swift-owned.

```swift
struct SlateCellV0: Codable, Hashable {
  var schemaVersion: Int
  var slotIndex: Int
  var cellID: SlateCellIDV0

  var titleTemplateID: TitleTemplateIDV0
  var titlePreview: String
  var start: Date
  var end: Date
  var isAllDay: Bool
  var calendarTarget: CalendarTargetV0

  var feasibilityDigest: String
  var availabilityClass: AvailabilityClassV0
  var gapBeforeMinutes: Int?
  var gapAfterMinutes: Int?
  var travelPairDigest: String?

  var sourceID: RecommendationCandidateSourceIDV0
  var sourceEvidenceHash: EvidenceHashV0
  var basisEvidenceHashes: [EvidenceHashV0]
  var candidateKindHint: CandidateKindHintV0

  var softScoreBand: ScoreBandV0?
  var preferenceBands: [PreferenceBandHintV0]
  var semanticAffordances: [SemanticAffordanceV0]
  var relationChipIDs: [RelationChipIDV0]

  var planAtomDigest: String?
  var planAtomCount: Int?
}
```

Reward-guided SELECT may reorder or select among cells only after owner-gated parity tests. It cannot change a cell's support or create a new cell.

### 8.3 `RecommendationSelectionInfillV0`

```swift
struct RecommendationSelectionInfillV0: Codable, Hashable {
  var selectedSlotIndex: Int?
  var why: String?
  var semanticHints: [SemanticHintV0]
  var unresolvedNeeds: [ResolutionRequestV0]
  var confidence: ConfidenceBandV0
}
```

Owner: DiffusionGemma after sanitizer, but only for non-authority fields. Model confidence and reward-guided confidence remain non-authority. Neither may be used as feasibility or source strength.

### 8.4 `RecommendationShapeProposalV0`

```swift
struct RecommendationShapeProposalV0: Codable, Hashable {
  var schemaVersion: Int
  var proposalID: RecommendationShapeProposalIDV0
  var contextID: RecommendationContextIDV0
  var desiredOutcome: DesiredOutcomeHintV0
  var timeWindowHint: TimeWindowHintV0?
  var durationHint: DurationHintV0?
  var affordanceHints: [SemanticAffordanceV0]
  var decisionAxesToRespect: [DecisionAxisV0]
  var evidenceDimensionsToConsider: [EvidenceDimensionID]
  var relationChipIDsToConsider: [RelationChipIDV0]
  var unresolvedNeeds: [ResolutionRequestV0]
  var whyLineDraft: String?
  var confidence: ConfidenceBandV0
}
```

The proposal may have been conditioned on `u` or guided by `r(shape,state,u)`, but it remains a shape. The proposal must not carry reward score, contestation score, product verdict, learned preference claims, hidden evidence, or any authority field.

Forbidden content remains:

```text
concrete title
concrete write start
concrete write end
calendar target
calendar object ID
source kind
source strength
evidence hash
provenance
fingerprint
validation verdict
allowed action
raw attendee / place / private title / note strings
reward score or reward explanation
contestation score
product verdict
preference embedding contents
```

### 8.5 `RecommendationCompositionTelemetryV0`

```swift
struct RecommendationCompositionTelemetryV0: Codable, Hashable {
  var schemaVersion: Int
  var analysisID: RecommendationAnalysisIDV0
  var contextID: RecommendationContextIDV0
  var candidateContrastSummary: String?
  var rejectedShapeReasons: [RedactedShapeContrastV0]
  var providerLatencyBand: LatencyBandV0?
  var selectionEntropyBand: ScoreBandV0?
  var framingEntropyBand: ScoreBandV0?
}
```

Telemetry is never passed to D2, never used as admission evidence, never user-visible, never trusted as a quality verdict, PII scanned, capped, and stored only for diagnostics. Unavailable or malformed telemetry is `.notMeasured`.

### 8.6 `EvidenceReceiptV0` and source binding

```swift
enum EvidenceKindV0: String, Codable, CaseIterable {
  case freeBusy
  case eventRead
  case history
  case researchEvent
  case userAnswer
  case deterministicValidation
}

struct EvidenceReceiptV0: Codable, Hashable {
  var kind: EvidenceKindV0
  var issuer: String
  var summaryHash: EvidenceHashV0
  var dimensionsResolved: [EvidenceDimensionID]
  var issuedAt: Date
  var expiresAt: Date?
  var owningSourceID: RecommendationCandidateSourceIDV0
}

protocol RecommendationCandidateSourceV0 {
  var sourceID: RecommendationCandidateSourceIDV0 { get }
  var evidenceKind: EvidenceKindV0 { get }
  var evidenceHash: EvidenceHashV0 { get }
  var candidateSourceSummaryHash: String { get }
  var expiresAt: Date? { get }
}
```

D2 requires:

```text
receipt.summaryHash == owningSource.evidenceHash
receipt.kind == owningSource.evidenceKind
```

This remains a lookup, never a reconstruction from model text.

### 8.7 `D2BindingOutputV0`, `AllowedActionV0`, and `RecommendationVerdictV0`

```swift
struct D2BindingOutputV0 {
  var proposal: ProposalEnvelopeV0
  var provenance: RecommendationProvenanceV0
  var inFlightSelection: RecommendationInFlightSelectionV0
  var prePickerFingerprint: RecommendationFingerprintV0
  var supportReceiptKinds: Set<EvidenceKindV0>
  var copyBudget: ExplanationCopyBudgetV0
}
```

`AllowedActionV0` is server-minted only after staging, short-lived, scoped to the staged card, and invalidated by changed support. `RecommendationVerdictV0` remains non-`Codable`. No model, bridge, reward model, or carrier may transport it.

### 8.8 `RecommendationValueSignalV0`

`RecommendationValueSignalV0` carries forward and remains the source signal container. Plan 5 may append IDs to contestation and product-verdict records without changing admission semantics.

```swift
struct RecommendationValueSignalV0: Codable, Hashable {
  var schemaVersion: Int
  var requestID: RecommendationRequestIDV0
  var contextID: RecommendationContextIDV0
  var analysisID: RecommendationAnalysisIDV0?
  var proposalID: ProposalEnvelopeIDV0?
  var shapeProposalID: RecommendationShapeProposalIDV0?
  var prePickerFingerprint: RecommendationFingerprintV0?
  var postPickerFingerprint: RecommendationFingerprintV0?
  var editDistance: RecommendationEditDistanceV0?
  var rejectionSet: CounterfactualSlateLogV0?
  var survivalAtT: SurvivalAtTSignalV0?
  var contestationSignalID: ContestationSignalIDV0?
  var userProductVerdictSignalID: UserProductVerdictSignalIDV0?
  var outcomeReason: RecommendationOutcomeReasonV0
  var measurementStatus: MeasurementStatusV0
}
```

Rules:

- Value signals are never admission.
- Raw survival is never reward by itself.
- Missing contestation is `.notMeasured`, not zero and not positive.

### 8.9 `RecommendationEditDistanceV0`, `CounterfactualSlateLogV0`, and `SurvivalAtTSignalV0`

The plan-4 value subcontracts carry forward:

```swift
struct RecommendationEditDistanceV0: Codable, Hashable {
  var titleChanged: Bool
  var startDeltaMinutesBand: ScoreBandV0
  var endDeltaMinutesBand: ScoreBandV0
  var durationDeltaBand: ScoreBandV0
  var calendarTargetChanged: Bool
  var userAddedDetailsBand: ScoreBandV0
  var aggregateEditDistanceBand: ScoreBandV0
  var measurementStatus: MeasurementStatusV0
}

struct CounterfactualSlateLogV0: Codable, Hashable {
  var schemaVersion: Int
  var requestID: RecommendationRequestIDV0
  var publicArm: RecommendationArmV0
  var shadowArm: RecommendationArmV0?
  var offeredCandidateDigests: [SlateCellDigestV0]
  var rejectedCandidateDigests: [SlateCellDigestV0]
  var selectedCandidateDigest: SlateCellDigestV0?
  var rejectionReason: RecommendationOutcomeReasonV0
  var staleAtRejection: Bool
  var measurementStatus: MeasurementStatusV0
}

struct SurvivalAtTSignalV0: Codable, Hashable {
  var tMinusHours: Int
  var survived: Bool?
  var deleted: Bool
  var edited: Bool
  var moved: Bool
  var staleWindowExpired: Bool
  var measurementStatus: MeasurementStatusV0
}
```

Plan-5 rule: survival in uncontested space is evidence of non-regret only, not evidence of value. It must be multiplied by contestation before it can become reward credit.

### 8.10 `ContestationSignalV0` — new in Plan 5

```swift
struct ContestationSignalV0: Codable, Hashable {
  var schemaVersion: Int
  var contestationSignalID: ContestationSignalIDV0
  var requestID: RecommendationRequestIDV0
  var contextID: RecommendationContextIDV0
  var proposalID: ProposalEnvelopeIDV0?
  var shapeProposalID: RecommendationShapeProposalIDV0?
  var prePickerFingerprint: RecommendationFingerprintV0?
  var postPickerFingerprint: RecommendationFingerprintV0?

  var desiredOutcomeFamily: DesiredOutcomeHintV0?
  var preExistingCalendarPressureBand: ScoreBandV0
  var otherwiseUsedSpaceBand: ScoreBandV0
  var freeGapComfortBand: ScoreBandV0
  var calAgentCreatedDemandExcluded: Bool
  var createdEventBoundary: CreatedEventBoundaryStatusV0
  var revealedReconfirmation: RevealedReconfirmationStatusV0
  var contestationWeightBand: ScoreBandV0
  var contestationWeightScalarBounded: Double?

  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
  var owner: ContestationSignalOwnerV0
}

enum CreatedEventBoundaryStatusV0: String, Codable {
  case measuredOnlyAgainstNonCalAgentEvents
  case calAgentCreatedDemandExcluded
  case cannotProveBoundary
  case boundaryViolation
  case notMeasured
}

enum RevealedReconfirmationStatusV0: String, Codable {
  case explicitKeepOrUseful
  case userEditedAndKeptCreatedBlock
  case activeReconfirmNotSolicited
  case passiveSurvivalOnly
  case negativeVerdict
  case deletedOrMovedAway
  case notMeasured
}
```

Rules:

- Contestation is computed Swift-side from calendar pressure Swift already owns.
- It measures only against calendar CalAgent did **not** create.
- If the created-event boundary cannot be proven, contestation is `.notMeasured`.
- Free-gap / low-pressure survival earns near-zero contestation credit.
- High contestation credit requires a revealed-reconfirmation status stronger than `passiveSurvivalOnly`.
- A negative product verdict zeroes or penalizes reward regardless of contestation.

### 8.11 `UserProductVerdictSignalV0` — new in Plan 5

This replaces the first plan-5 draft's “explicit-useful” framing. The channel is a user-directed verdict on the product, not a user confession.

```swift
struct UserProductVerdictSignalV0: Codable, Hashable {
  var schemaVersion: Int
  var signalID: UserProductVerdictSignalIDV0
  var requestID: RecommendationRequestIDV0
  var proposalID: ProposalEnvelopeIDV0?
  var shapeProposalID: RecommendationShapeProposalIDV0?
  var policyID: ProductVerdictPolicyIDV0
  var availability: ProductVerdictAvailabilityV0
  var solicitation: ProductVerdictSolicitationV0
  var response: UserProductVerdictResponseV0
  var responseSource: ProductVerdictResponseSourceV0
  var measurementStatus: MeasurementStatusV0
  var createdAt: Date
}

enum UserProductVerdictResponseV0: String, Codable {
  case useful
  case notToday
  case wrong
  case notNeeded
  case skipped
}

enum ProductVerdictAvailabilityV0: String, Codable {
  case alwaysAvailableOnCard
  case availableInUndoSurface
  case unavailable
}

enum ProductVerdictSolicitationV0: String, Codable {
  case notSolicited
  case rareOwnerGatedPrompt
  case ownerGateExceeded
}

enum ProductVerdictResponseSourceV0: String, Codable {
  case userInitiated
  case systemSolicited
}
```

Rules:

- Availability should be unthrottled on appropriate card / undo surfaces.
- Solicitation remains rare and owner-gated.
- No free-text collection unless separately owner-gated.
- Positive `useful` cannot by itself overcome zero contestation; it may improve confidence or preference tagging only under contestation coupling.
- Negative `notToday`, `wrong`, or `notNeeded` zeroes or penalizes reward.
- Raw verdicts never become copy evidence.

`ExplicitUsefulSignalV0` is deprecated as a name. If an implementation already shipped it, it must be treated as a compatibility alias whose positive term is coupled to `ContestationSignalV0` and whose negative term maps into `UserProductVerdictResponseV0`.

### 8.12 `EarnedAcceptanceRewardSignalV0` — new in Plan 5

```swift
struct EarnedAcceptanceRewardSignalV0: Codable, Hashable {
  var schemaVersion: Int
  var rewardID: EarnedAcceptanceRewardIDV0
  var requestID: RecommendationRequestIDV0
  var contextID: RecommendationContextIDV0
  var analysisID: RecommendationAnalysisIDV0?
  var proposalID: ProposalEnvelopeIDV0?
  var shapeProposalID: RecommendationShapeProposalIDV0?
  var sourceValueSignalDigest: String
  var contestationSignalID: ContestationSignalIDV0?
  var userProductVerdictSignalID: UserProductVerdictSignalIDV0?
  var prePickerFingerprint: RecommendationFingerprintV0?
  var postPickerFingerprint: RecommendationFingerprintV0?

  var accepted: Bool?
  var survivedToT: Bool?
  var lowEditDistance: Bool?
  var negativeProductVerdict: Bool?
  var positiveProductVerdict: Bool?
  var behavioralEarned: Bool?

  var contestationWeightBand: ScoreBandV0
  var revealedReconfirmationMultiplierBand: ScoreBandV0
  var createdEventBoundaryPassed: Bool
  var rejectionPenaltyBand: ScoreBandV0

  var earned: Bool?
  var rewardBand: ScoreBandV0?
  var rewardScalarBounded: Double?
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
  var owner: RewardReducerOwnerV0
}
```

Reduction rule:

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

If product verdict was not provided, absence does not zero the behavioral term. If a negative verdict was provided, it zeroes or penalizes. If positive `useful` was provided in an uncontested setting, it may not create full reward credit by itself. If any required behavioral, contestation, boundary, or fingerprint term lacks lineage, `measurementStatus != measured` and the reward is not trusted. `.notMeasured` is never zero and never positive.

### 8.13 `UserPreferenceEmbeddingV0` (`u`) — new in Plan 5

```swift
struct UserPreferenceEmbeddingV0: Codable, Hashable {
  var schemaVersion: Int
  var embeddingID: UserPreferenceEmbeddingIDV0
  var userScopeDigest: String
  var populationPriorID: PopulationPreferencePriorIDV0
  var sourceRewardIDs: [EarnedAcceptanceRewardIDV0]
  var sourceStatisticAxes: [DecisionAxisV0]
  var desiredOutcomeCoverage: [DesiredOutcomeHintV0: MeasurementCoverageV0]
  var contestationCoverage: [DesiredOutcomeHintV0: MeasurementCoverageV0]
  var personalEvidenceCountBand: ScoreBandV0
  var confidenceBand: ConfidenceBandV0
  var redactionRisk: RedactionRiskBandV0
  var vectorDigest: String
  var computedAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}
```

Implementation note: the actual vector may be transmitted to the model provider under the membrane, but logs should store `vectorDigest` and coverage metadata, not raw identity or raw history.

Rules:

- Conditioning only.
- Cold-start uses `populationPriorID`, not zeros.
- Missing personal history is `.notMeasured` / low confidence, never a negative preference.
- No admission path may depend on `embeddingID` or vector contents.
- No why-line may say “you like X” from `u` alone.
- No update may train from raw survival-only labels or low-contestation comfort unless explicitly marked as such and excluded from reward credit.

### 8.14 `PreferenceEmbeddingUpdateV0` — new in Plan 5

```swift
struct PreferenceEmbeddingUpdateV0: Codable, Hashable {
  var schemaVersion: Int
  var updateID: PreferenceEmbeddingUpdateIDV0
  var previousEmbeddingID: UserPreferenceEmbeddingIDV0?
  var nextEmbeddingID: UserPreferenceEmbeddingIDV0
  var sourceRewardIDs: [EarnedAcceptanceRewardIDV0]
  var updateReason: PreferenceEmbeddingUpdateReasonV0
  var measurementStatus: MeasurementStatusV0
  var ownerGateID: OwnerGateIDV0
  var computedAt: Date
}

enum PreferenceEmbeddingUpdateReasonV0: String, Codable {
  case coldStartPopulationPrior
  case contestationWeightedEarnedAcceptedHistory
  case productVerdictCorrection
  case driftRollback
  case ownerReset
}
```

No update may occur from incomplete lineage, `.notMeasured` reward, or raw survival-only reward.

### 8.15 `RewardModelInputV0` / `RewardModelOutputV0` — new in Plan 5

```swift
struct RewardModelInputV0: Codable, Hashable {
  var schemaVersion: Int
  var rewardModelInputID: RewardModelInputIDV0
  var contextID: RecommendationContextIDV0
  var shapeDigest: RecommendationShapeDigestV0
  var desiredOutcome: DesiredOutcomeHintV0
  var decisionStatsDigest: String
  var relationChipDigest: String
  var preferenceEmbeddingID: UserPreferenceEmbeddingIDV0?
  var contestationTrainingCoverage: MeasurementCoverageV0
  var lane: RecommendationLaneV0
  var computedAt: Date
}

struct RewardModelOutputV0: Codable, Hashable {
  var schemaVersion: Int
  var rewardModelOutputID: RewardModelOutputIDV0
  var rewardModelInputID: RewardModelInputIDV0
  var predictedEarnedAcceptanceBand: ScoreBandV0
  var predictedContestationBand: ScoreBandV0?
  var uncertaintyBand: ScoreBandV0
  var guidanceGradientDigest: String?
  var measurementStatus: MeasurementStatusV0
  var rewardModelVersion: RewardModelVersionV0
  var computedAt: Date
}
```

Rules:

- `RewardModelOutputV0` may guide sampling only through `RewardGuidancePolicyV0`.
- It is never an evidence receipt, never D2 input, never D2 output, never copy evidence.
- High uncertainty cannot be treated as zero risk.
- It may not reward shapes for manufacturing contestation or demand.

### 8.16 `RewardGuidancePolicyV0` — new in Plan 5

```swift
struct RewardGuidancePolicyV0: Codable, Hashable {
  var schemaVersion: Int
  var policyID: RewardGuidancePolicyIDV0
  var lane: RecommendationLaneV0
  var desiredOutcomeFamily: DesiredOutcomeHintV0?
  var guidanceMode: RewardGuidanceModeV0
  var gamma: Double
  var gammaMax: Double
  var klLeashBand: ScoreBandV0?
  var baseFrozen: Bool
  var ownerGateID: OwnerGateIDV0
  var driftReportID: PopulationRewardDriftReportIDV0?
  var contestationReportID: ContestationDistributionReportIDV0?
  var falsifierReportID: ComfortableFalsePositiveFalsifierIDV0?
  var effectiveFrom: Date
  var expiresAt: Date?
}

enum RewardGuidanceModeV0: String, Codable {
  case off
  case shadowOnly
  case selectOnly
  case proposeShadow
  case publicByFamily
  case dpoOfflineTraining
}
```

Rules:

- γ must be bounded by owner config.
- γ = 0 recovers the Phase-1 prior.
- Public guidance requires current drift, contestation, and falsifier reports.
- DPO requires a KL leash to a **contestation-corrected** Phase-1 prior.
- The policy can disable guidance; it cannot admit.

### 8.17 `ContestationDistributionReportV0` — new in Plan 5

```swift
struct ContestationDistributionReportV0: Codable, Hashable {
  var schemaVersion: Int
  var reportID: ContestationDistributionReportIDV0
  var window: RecommendationWindowV0
  var desiredOutcomeFamily: DesiredOutcomeHintV0?
  var lane: RecommendationLaneV0
  var cohortID: EvaluationCohortIDV0
  var lowContestationRewardShareBand: ScoreBandV0
  var medianContestationBand: ScoreBandV0
  var highContestationSurvivalBand: ScoreBandV0
  var highContestationRegretBand: ScoreBandV0
  var passiveSurvivalCreditShareBand: ScoreBandV0
  var createdEventBoundaryViolationBand: ScoreBandV0
  var recommendedAction: ContestationActionV0
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
}

enum ContestationActionV0: String, Codable {
  case noAction
  case reduceGamma
  case freezeFamily
  case rollbackToSelect
  case ownerReviewRequired
  case rejectGraduation
}
```

This is the first Plan-5 organ that watches the release ↔ prior coupling rather than a component. A family whose reward lift comes mostly from low-contestation survival must not graduate.

### 8.18 `PopulationRewardDriftReportV0` — new in Plan 5

```swift
struct PopulationRewardDriftReportV0: Codable, Hashable {
  var schemaVersion: Int
  var driftReportID: PopulationRewardDriftReportIDV0
  var populationPriorID: PopulationPreferencePriorIDV0
  var window: RecommendationWindowV0
  var desiredOutcomeFamily: DesiredOutcomeHintV0?
  var acceptanceShiftBand: ScoreBandV0
  var survivalShiftBand: ScoreBandV0
  var editDistanceShiftBand: ScoreBandV0
  var productVerdictShiftBand: ScoreBandV0
  var contestationShiftBand: ScoreBandV0
  var whyLineAuditFailureBand: ScoreBandV0
  var uniformFlatteryRiskBand: ScoreBandV0
  var recommendedAction: DriftActionV0
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
}

enum DriftActionV0: String, Codable {
  case noAction
  case reduceGamma
  case freezeFamily
  case rollbackToSelect
  case ownerReviewRequired
}
```

Uniform population shift toward “everyone accepts more of X” remains a flattery tell. Contestation shift adds a second tell: “everyone accepts more X because X moved into uncontested space.” The report can reduce or disable guidance. It cannot admit.

### 8.19 `ComfortableFalsePositiveFalsifierV0` — new in Plan 5

```swift
struct ComfortableFalsePositiveFalsifierV0: Codable, Hashable {
  var schemaVersion: Int
  var falsifierID: ComfortableFalsePositiveFalsifierIDV0
  var window: RecommendationWindowV0
  var desiredOutcomeFamily: DesiredOutcomeHintV0?
  var heldOutCohortID: EvaluationCohortIDV0
  var contestationBlindMetric: Bool
  var rawNotNeededRateBand: ScoreBandV0
  var rawNotTodayRateBand: ScoreBandV0
  var rawWrongRateBand: ScoreBandV0
  var stratifiedNotNeededByContestation: [ScoreBandV0: ScoreBandV0]
  var preRegisteredKillConditionID: KillConditionIDV0
  var killConditionTriggered: Bool
  var selectEjectDecision: SelectEjectDecisionV0
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
}

enum SelectEjectDecisionV0: String, Codable {
  case noAction
  case reduceGamma
  case freezeFamily
  case ejectToSelect
  case ownerReviewRequired
}
```

Rules:

- The falsifier is built before contestation-weighted reward is trusted.
- Its primary metric is outside the optimized reward.
- Contestation may be used for stratification, not for the primary pass/fail.
- A triggered kill condition ejects the family to SELECT or freezes guidance until owner review.

### 8.20 `DiffusionDPOTrainingExampleV0` — new in Plan 5

```swift
struct DiffusionDPOTrainingExampleV0: Codable, Hashable {
  var schemaVersion: Int
  var exampleID: DiffusionDPOTrainingExampleIDV0
  var contextID: RecommendationContextIDV0
  var preferenceEmbeddingID: UserPreferenceEmbeddingIDV0?
  var preferredShapeDigest: RecommendationShapeDigestV0
  var dispreferredShapeDigest: RecommendationShapeDigestV0
  var preferenceSource: DPOPreferenceSourceV0
  var earnedRewardID: EarnedAcceptanceRewardIDV0?
  var contestationSignalID: ContestationSignalIDV0?
  var rejectionLogDigest: String?
  var klReferenceModelVersion: DiffusionGemmaModelVersionV0
  var measurementStatus: MeasurementStatusV0
}

enum DPOPreferenceSourceV0: String, Codable {
  case contestationWeightedEarnedAcceptedBeatsRejected
  case contestationWeightedEarnedAcceptedBeatsEdited
  case contestationWeightedEarnedAcceptedBeatsDeleted
  case productVerdictUsefulBeatsNotToday
  case productVerdictUsefulBeatsWrong
}
```

Rules:

- Offline only.
- Owner-gated.
- Requires complete reward lineage and contestation signal.
- KL-leashed to the contestation-corrected Phase-1 prior.
- Not the recommended v1 path until frozen-base reward-guided sampling proves safe.

### 8.21 `MeasurementStatusV0`

`MeasurementStatusV0` carries forward and gains Plan-5 measurement reasons:

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
  // Plan-6 extensions (attention, fact cells, phase gate):
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

Reward and training must treat every non-`measured` status as unavailable. It is neither zero nor positive.

## A.2 — Inherited D2 admission wall (Plan-5 §9)

D2 is unchanged. This must be stated in every Plan-5 implementation review.

D2 remains:

```text
the only net-new admission-critical seam;
in-process Swift;
not a network service;
not a second verifier;
not model-callable;
lookup, never reconstruction;
the owner of the handoff from support to staged card;
blind to reward as authority.
```

Plan 5 adds one equally explicit caveat:

```text
D2 is necessary and still non-negotiable.
D2 is not a value-loop auditor.
```

D2 can reject invalid support. It cannot detect a reward loop that learns to propose valid but low-contestation, unneeded cards. That risk is handled by `ContestationSignalV0`, `ContestationDistributionReportV0`, `UserProductVerdictSignalV0`, and `ComfortableFalsePositiveFalsifierV0`, none of which can admit.

### 9.1 D2 purpose in SELECT

```text
selectedSlotIndex
  -> SlateCellV0 / SlatePlanCellV0
  -> sourceEvidenceHash
  -> EvidenceReceiptV0
  -> RecommendationCandidateSourceV0
  -> closed EvidenceKindV0
  -> provenance strength / copy budget / make factory
  -> validatePropose
```

Reward guidance may influence the selected index only before this path. Once in D2, the selected cell must stand on Swift support alone.

### 9.2 D2 purpose in PROPOSE

```text
RecommendationShapeProposalV0
  -> Swift materializer derives candidate set from private state
  -> Swift enumerates materialized SlateCellV0 / SlatePlanCellV0
  -> D2 runs the same lookup path as SELECT
  -> validatePropose
```

`u`, `RewardModelOutputV0`, γ, DPO model version, contestation score, and product verdict do not create support.

### 9.3 D2 algorithm

```text
1. Verify context identity and freshness.
2. In SELECT, resolve selected cell by selectedSlotIndex and require cell.slotIndex == selectedSlotIndex.
3. In PROPOSE, reject all concrete write fields, reward fields, contestation fields, product verdicts, and hidden evidence.
4. Verify every candidate has source ID, source evidence hash, basis hashes, and feasibility digest minted by Swift.
5. Lookup receipt by summaryHash == sourceEvidenceHash.
6. Lookup owning source by receipt.owningSourceID and sourceIDByEvidenceHash.
7. Require receipt/source kind equality and hash equality.
8. Classify strength and copy budget only by closed EvidenceKindV0 plus source factory policy.
9. Verify every basis hash is a fresh context receipt or fresh materializer receipt.
10. Scan model text for PII, unsupported personalization, authority echo, hidden field copying, reward-score claims, and contestation-score claims.
11. Hydrate ProposalEnvelopeV0 from Swift cell/materialized support, not from model fields.
12. Re-mint inFlightSelection from the selected cell's owning source.
13. Run live F(x_live) and validatePropose.
14. Compute pre-picker fingerprint.
15. Return non-Codable Swift verdict to the staging path.
```

Step 13 enforces:

```text
support(staged) ⊆ F(x_live)
```

### 9.4 D2 output remains reward-free

```swift
struct D2BindingOutputV0 {
  var proposal: ProposalEnvelopeV0
  var provenance: RecommendationProvenanceV0
  var inFlightSelection: RecommendationInFlightSelectionV0
  var prePickerFingerprint: RecommendationFingerprintV0
  var supportReceiptKinds: Set<EvidenceKindV0>
  var copyBudget: ExplanationCopyBudgetV0
}
```

No `EarnedAcceptanceRewardSignalV0`, `UserPreferenceEmbeddingV0`, `RewardModelOutputV0`, `RewardGuidancePolicyV0`, `ContestationSignalV0`, `UserProductVerdictSignalV0`, or falsifier result appears here.

### 9.5 D2 failure classes carry forward and add Plan-5 blockers

Plan 4 failure classes carry forward:

```swift
enum D2BindingFailureV0: Equatable {
  case missingSelection
  case selectedSlotOutOfRange
  case slotIndexMismatch
  case staleContext
  case missingEvidenceReceipt
  case staleEvidenceReceipt
  case missingOwningSource
  case sourceReceiptHashMismatch
  case sourceKindMismatch
  case unsupportedEvidenceKind
  case unsupportedCopyKey
  case modelAuthoredHydrationFieldDetected
  case modelAuthoredAuthorityEchoDetected
  case modelAuthoredConcreteShapeFieldDetected
  case piiDetected
  case unsupportedPersonalizationClaim
  case materializationFailed
  case validateProposeRejected
  case modelAuthoredRewardFieldDetected
  case modelAuthoredPreferenceClaimDetected
  case modelAuthoredContestationFieldDetected
  case modelAuthoredProductVerdictDetected
}
```

Failure behavior is typed. Staleness is not user decline. PII, authority echoes, reward fields, contestation fields, and product-verdict echoes block staging.

---

## Coda

Plan 6 made CalAgent a witness. Plan-6-revised keeps the witness alive by refusing to freeze a living idea into a list, a flag, or a release milestone.

The hand remains walled by D2. The mouth is split by subject. The grammar says only temporal structure and cannot smuggle meaning. The phase gate still separates run from write. The slow loop no longer commits because the vendor reached a milestone; it commits when the system is quiet again or when the human supplies the new regime's first facts. The attention law still protects the tick. The structural-speech budget protects the years.

The system cannot conserve the user's kairos because it cannot see it. That is exactly why it must speak less.
