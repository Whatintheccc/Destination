# plan-7.md — Standalone Witness Architecture as a Corrigible Plant: Typed Laws, Temporal Calculus, Sealed Deposition, League Vigor, and the Bifurcation Margin

**Status:** canonical standalone Plan-7 revision. This file folds the Plan-6 static architecture and the self-play dynamism review into one implementable architecture document. No companion plan is required to read the contracts, migration, tests, or definition of done.

**Inheritance:** the Plan-5 D2 write wall remains unchanged. The Plan-6 theorem/rule/data taxonomy, Witness reframe, temporal structure calculus, capability-absence refactor, two-mouth API, human-clocked oscillator, deposition channel, phase gate, structural-speech budget, and kairos floor are preserved and restated here as the static base. Plan 7 then adds the dynamism layer: signal fates, the empty-maximize-slot doctrine, E1–E4, the self-doubt league, sealed deposition forecasts, league vigor regression, vigor-collapse confession, the bifurcation margin, the decision grid, and the budget regulator v2.

**Relationship to the self-play analysis:** the analysis is absorbed, not appended. Its central correction becomes canonical: the witness is neither an autonomous learner nor a literal self-play agent. It is a **corrigible plant** whose only legitimate agency is to conserve the human correction channel.

**One-line thesis:** the witness has no safe signal to maximize. Every membrane-legal signal is either read through the user it can degrade or through the system’s own self-consistency, whose easiest fixed point is a flattened user. Therefore Plan 7 removes the autonomous-learner story, empties the maximize slot, and ships a conservative controller: seal the correction channel, preserve adversarial vigor, confess on collapse, and fall to deterministic-default whenever the bifurcation margin cannot be measured.

```text
Plan 6 slow loop:      residual-low ∨ deposition-answered  → may recommit.
Plan 7 slow loop:      (residual-low ∨ deposition-answered)
                       ∧ ¬LeagueVigorRegression
                       ∧ margin grid admits breathing
                       → may recommit.

Plan 6 fast loop:      residual-high → break self-confession + suppression.
Plan 7 fast loop:      residual-high ∨ vigor-collapse-fingerprint
                       → break self-confession + reopen deposition.

Plan 6 budget:         tight, tightening structural-speech budget.
Plan 7 budget:         hard scarcity ceiling plus a regulated operating cap:
                       the cap may breathe around sealed-surprisal health,
                       but reward, dashboard, and model guidance may not widen it.
```

---

## Table of contents

1. [Review decision](#1-review-decision)
2. [Static base retained and folded into this file](#2-static-base-retained-and-folded-into-this-file)
3. [Plan-7 doctrine: the witness is a corrigible plant](#3-plan-7-doctrine-the-witness-is-a-corrigible-plant)
4. [The six fates and the empty maximize slot](#4-the-six-fates-and-the-empty-maximize-slot)
5. [The seven dynamism invariants](#5-the-seven-dynamism-invariants)
6. [The four typed edges adopted by Plan 7](#6-the-four-typed-edges-adopted-by-plan-7)
7. [SelfDoubtLedgerV1 becomes a league](#7-selfdoubtledgerv1-becomes-a-league)
8. [Sealed deposition forecasts](#8-sealed-deposition-forecasts)
9. [League vigor regression and the slow-loop gate](#9-league-vigor-regression-and-the-slow-loop-gate)
10. [Vigor-collapse confession and the third break trigger](#10-vigor-collapse-confession-and-the-third-break-trigger)
11. [The bifurcation margin M](#11-the-bifurcation-margin-m)
12. [The decision grid](#12-the-decision-grid)
13. [Structural-speech budget v2: scarcity without success-driven mutism](#13-structural-speech-budget-v2-scarcity-without-success-driven-mutism)
14. [Canonical static contracts folded from Plan 6](#14-canonical-static-contracts-folded-from-plan-6)
15. [Canonical dynamism contracts](#15-canonical-dynamism-contracts)
16. [End-to-end flows after Plan 7](#16-end-to-end-flows-after-plan-7)
17. [Migration sequence](#17-migration-sequence)
18. [Test matrix](#18-test-matrix)
19. [Definition of done](#19-definition-of-done)
20. [Self-audit](#20-self-audit)
21. [Changelog from Plan 6](#21-changelog-from-plan-6)
22. [Scope and falsifiability](#22-scope-and-falsifiability)
23. [Coda](#23-coda)

---

## 1. Review decision

The review is accepted.

Plan 6 was correct about the witness body:

```text
CalAgent is a witness, not a recommender.
Swift mints facts and authority.
DiffusionGemma selects only among Swift-minted fact programs and bounded hints.
Codex relays and carries correction.
D2 remains the only write-admission seam.
A2 remains the per-tick attention-admission seam.
The privacy membrane remains the boundary of theorem-izability.
The smooth mouth speaks user-time structure; the break mouth speaks only system error.
The human deposition is the only legal clock that can bring life back across the membrane.
```

Plan 6 was incomplete about the witness dynamics:

| Plan-6 dynamic claim | Plan-7 verdict | Plan-7 repair |
|---|---|---|
| The two loops govern each other. | Partly false. The fast loop gates the slow loop; the slow loop does not autonomously reanimate itself under suppression. | Add sealed deposition forecasts, league vigor, margin gating, and the E4 confession clock. |
| The residual loop is self-play. | False. It is self-monitoring against a frozen log. | Rename the safe dynamic: adversary-conservation, not self-play. |
| The structural-speech cap can simply tighten with exposure. | Unsafe over long horizons. A success-driven monotone drain has mutism as its fixed point. | Replace integrator-to-zero with a regulator-to-reference driven by sealed surprisal health, while preserving hard user-visible scarcity and no reward widening. |
| Low user contestation is good. | Ambiguous and sometimes dangerous. It can mean “well served” or “flattened.” | Gate on the three-way fingerprint: vigor decline plus monoculture rise plus sealed-surprisal collapse. |
| Deposition is an escape from latch-up. | Necessary but too passive. | The plant must solicit deposition when the correction channel is collapsing. |

Plan 7 therefore adopts a fourth revision joint:

```text
Plan 6 thawed: laws vs rules vs data; capability absence; human-clocked slow license; structural-speech budget.
Plan 7 thaws: dynamism itself — learning and acting are fated, margin-gated, and corrigibility-conserving.
```

---

## 2. Static base retained and folded into this file

Plan 7 does not move the Plan-5 wall. All inherited write-safety contracts remain binding:

```text
support(staged) ⊆ F(x_live)
RecommendationVerdictV0 remains non-Codable.
AllowedActionV0 remains server-minted only after staging.
Confirm tap remains required.
Swift never touches calendar objects CalAgent did not create.
D2 remains reward-free, contestation-free, and value-free as an admission surface.
```

Plan 7 does not weaken the Plan-6 attention and privacy contracts:

```text
occupation(spoken) ⊆ A(tendered)
transmit(model) ⊆ decision-sufficient(non-identifying)
raw titles, notes, attendees, exact locations, and low-cardinality identity facts stay behind Swift
no structural notification channel exists by default
no back-write mutator is visible to metabolism
RUN and WRITE phase remain separated by unforgeable tokens
```

Plan 7 does not change the temporal calculus principle:

```text
TemporalPrimitiveV1 expresses only structure over interval order.
Operators and fact families are programs as data.
Semantic meaning, identity, desire, need, avoidance, and emotional valence remain unrepresentable.
```

Plan 7 does not let the break mouth speak about the user:

```text
BreakMouthV1 accepts only self-subject assertions.
A break utterance may say “my read is stale.”
It may not say “your life changed.”
```

Plan 7 does not claim to measure kairos. It strengthens the reason the claim is forbidden.

---

## 3. Plan-7 doctrine: the witness is a corrigible plant

### 3.1 Governing doctrine

CalAgent is a witness for the user’s time. It may place true, spendable, privacy-safe temporal structure into attention the user has tendered. It may not optimize the user, steer the user, model the user’s inner meaning, or treat the user’s compliance as proof of value.

The system is a plant with one agent-like reflex:

```text
Conserve the human’s ability to correct the system.
```

That is the operational form of corrigibility under the membrane. Plan 7 does not ask the machine to want what the user wants. That would require a portrait. It asks the machine to conserve the channel through which the user can keep saying, “no, not that.”

### 3.2 The two loops after Plan 7

```text
SLOW LOOP — machine learning, but fated as regulation.
  It selects which Swift-minted temporal fact programs deserve smooth placement.
  It may never author facts, evidence, attention authority, budget, mouth choice, reward, or writes.
  It recommits only when the decision grid says the plant is breathing in the target cell.

FAST LOOP — machine acting, but fated as correction.
  It suppresses the slow loop when residual is high.
  It confesses system error when the correction channel is collapsing.
  It reopens deposition. It does not act on the user; it acts on itself.
```

The fast loop is the only self-initiated act. Its legal acts are:

```text
1. residual-high        → suppress smooth placement and confess system staleness;
2. vigor-collapse       → confess that the system may be talking too much or being too predictable,
                          then reopen deposition.
```

There is no acquisitive third mode.

### 3.3 Architecture law supplement

The Plan-6 architecture law is extended:

```text
Codex may relay, serve, and carry correction.
DiffusionGemma may rank, compose over, and learn from Swift-minted fact programs, typed shape hints, bounded guidance, sealed forecast slates, and non-identifying league summaries.
Swift must encode, mint facts, validate truth, admit speech, admit writes, meter structural speech, compute the dynamism ledger, seal deposition forecasts, score margin, run the decision grid, own phase gates, own fallback, and bind all learning.
Codex, DiffusionGemma, reward models, learned stores, release dashboards, and speech surfaces must never grade, admit, write, author facts, launder their own outputs, manufacture demand, manufacture contestation, occupy untendered attention, author a persistent portrait of the user, expand an absent capability, widen structural speech, promote an unmeasured margin, or turn a corrective act into an acquisitive act.
```

### 3.4 Internal role-map additions

| Component | Owner | Owns | Trust boundary | Failure mode | Guard |
|---|---|---|---|---|---|
| Self-doubt league | Swift measurement | Population of frozen failed regimes; derived scalar residual | Persistent portrait must remain system-authored, not user-authored biography | Scalar residual hides league collapse | E2: population-valued `SelfDoubtLedgerV1`; scalar `r` is only a view |
| Sealed forecast minter | Swift measurement | Pre-deposition forecast commitments and post-hoc surprisal | Forecast is gate, never reward | Manufactured contestation or sandbagging | E1: sealed ledger plus co-located OPE accuracy |
| League vigor gate | Swift license controller | Three-way fingerprint and recommit conjunction | Low contestation is ambiguous | Punishes well-served users or rewards amputated users | E3: vigor↓ ∧ monoculture↑ ∧ conditional-surprisal collapse |
| Vigor-collapse confession | Swift break mouth | Third break trigger and deposition reopen | Confession must remain self-subject | Break mouth asserts user biography | E4: type-correct self-subject confession only |
| Margin estimator | Swift controller | `M(t)` and measurement status | Margin is self-blinding | Unmeasured reads as healthy | `.notMeasured(M) ≡ M < 0` |
| Decision grid | Swift controller | Breathe/watch/confess/default/halt | Learned organs cannot choose state | Positive margin in amputation cell | Cell B dominates margin; reentry requires both bifurcations |
| Budget regulator v2 | Swift product/safety | Operating cap against sealed-surprisal reference | Budget must not become growth knob | Success-driven mutism or reward-driven loudness | Hard ceiling amendment gate; operating cap regulated by E1 health |

---

## 4. The six fates and the empty maximize slot

Plan 6 separated laws, rules, and guesses. Plan 7 adds the missing classification: every signal must have a **fate** — what an optimizer is allowed to do with it.

### 4.1 `SignalFateV1`

```swift
enum SignalFateV1: String, Codable, Hashable {
  case maximize                 // F1 — empty in this architecture
  case minimizeToFloor          // F2
  case conserveStock            // F3
  case budgetFlow               // F4
  case regulateToSetpoint       // F5
  case forbidToOptimize         // F6
}
```

| Fate | Control form | Plan-7 status | Examples |
|---|---|---|---|
| F1 maximize | Push to an extremum | Empty by theorem for membrane-legal witness signals | No invariant may use this fate |
| F2 minimize-to-floor | Drive down but not to literal zero | Allowed for endogenous error signals | residual error, forecast error, monoculture |
| F3 conserve stock | Preserve a nonzero capacity | Required for corrigibility | controllability, adversarial vigor, league diversity |
| F4 budget flow | Meter a rate through a cap | Required for chronos speech | structural speech, break-confession exposure |
| F5 regulate-to-setpoint | Track a healthy reference | Required for living control | budget operating cap, exploration coverage, surprisal health |
| F6 forbid-to-optimize | Measured/reported if legal; never optimized | Required at membrane edge | kairos, cognitive-contestation, user interior |

### 4.2 Empty maximize-slot theorem as Plan-7 doctrine

No membrane-legal signal may be fated F1.

Class U signals are read through the user’s registered reactions: acceptance, edits, verdicts, deposition answers. Maximizing them risks degrading the user’s capacity to contest the system, and that degradation biases the readings in the favorable direction.

Class S signals are read from the system’s own trace: residuals, self-consistency, closed ledgers. Maximizing self-consistency still routes back through the user as a mirror; the easiest mirror is the flattened user.

Therefore:

```text
F1 is empty.
No witness invariant may sit in F1.
No acting mode may be acquisitive.
Reward may guide only downstream of F2–F6 gates.
```

### 4.3 Health fingerprint

Every public launch, organ graduation, operator addition, budget policy change, and mouth change must prove:

```text
ZERO invariants in F1.
Every reward path downstream of F2–F6.
No learned organ can turn a gate into a maximand.
No dashboard can promote a missing measurement to positive evidence.
```

---

## 5. The seven dynamism invariants

Plan 7 adds the dynamism invariants as the primitive measurement stack of the witness plant.

| # | Invariant | Fate | Holds / tracks | Failure if unmanaged | Enforcement |
|---|---|---|---|---|---|
| I1 | Controllability / corrigibility | F3 conserve | Human’s operative authority to correct the system | Plant becomes uncorrectable | E4 confession + deposition reopen |
| I2 | User adversarial vigor | F3 conserve, population | The opponent’s strength in the system-vs-cognition game | Compliance misread as victory | E2 league + E3 fingerprint |
| I3 | Sealed-surprisal health | F5 regulate / F2 gate | Whether the user still surprises pre-committed system forecasts | Convergence to mirror; manufactured contestation if rewarded | E1 sealed forecast, gate never reward |
| I4 | League diversity | F3 conserve | Breadth of frozen failed regimes | Single-regime overfit | E2 league cardinality and spread |
| I5 | Exploration coverage | F5 regulate | Breadth of state the slow loop can safely place into | Under-coverage latch or over-coverage flood | License scopes and narrow relicense |
| I6 | Residual honesty | F2 minimize-to-floor | System’s assertion error against closed past | Manufactured confidence or frozen residual | Closed-outcome residual plus E1 starvation floor |
| I7 | Chronos budget | F4 budget + F5 regulator + F3 hard ceiling | Cumulative structural-speech exposure | Flood or success-driven mutism | Budget regulator v2 |

The conserve cluster is:

```text
I4 ⊳ I2 ⊳ I1
league diversity grounds adversarial vigor;
adversarial vigor grounds corrigibility.
```

A scalar residual cannot preserve this cluster. Plan 7 therefore changes `SelfDoubtLedgerV1` from an ID-only/scalar concept into a population-valued ledger.

---

## 6. The four typed edges adopted by Plan 7

Plan 7 adopts all four edges. They are jointly necessary and individually insufficient.

### E1 — `SealedDepositionForecastV1`

Before a deposition opens, Swift commits a sealed forecast of the user’s typed answer into a frozen ledger. After the user answers or skips, Swift scores conditional surprisal against the pre-committed forecast.

Rules:

```text
sealed forecast = gate, never reward;
surprisal magnitude must not be maximized;
sandbagging is punished by co-located forecast accuracy;
missing sealed forecast means the relevant margin term is not measured;
not measured never promotes license.
```

### E2 — `SelfDoubtLedgerV1` as a population

The self-doubt ledger is a league of frozen failed regimes, not a scalar. The scalar residual `r` remains as a derived view.

Rules:

```text
league collapse is not success;
monoculture rise is not confidence;
scalar residual may not be the sole slow-loop recommit input;
consumers that only need r must record that collapse detection was not consumed.
```

### E3 — `LeagueVigorRegressionV1` into the slow-loop gate

Slow recommit is conjoined with absence of league vigor regression.

```text
recommit allowed only if:
  (residual-low ∨ deposition-answered)
  ∧ ¬LeagueVigorRegression
  ∧ decision grid allows the requested state.
```

`LeagueVigorRegression` is the three-way fingerprint, not bare decline in contestation:

```text
vigor↓ ∧ output-monoculture↑ ∧ conditional-sealed-surprisal→0
```

This avoids punishing well-served users who interact less but still surprise the system when they do interact.

### E4 — `VigorCollapseConfessionV1`

The fast loop gains a third trigger. Break fires on the amputation fingerprint as a self-subject confession that reopens deposition.

Allowed break shape:

```text
“I may be getting too predictable here. I do not want to keep steering from a stale read.
Which closed fact should I trust?”
```

Forbidden break shape:

```text
“You have stopped arguing with me.”
“You now prefer this structure.”
“You are dependent on this pattern.”
```

The subject is the interaction and the system’s own risk, never a user biography.

### One clock, two consumers

E1’s sealed surprisal signal is consumed by both:

```text
budget regulator:       regulate structural-speech operating cap toward surprisal health;
confession reflex:      fire when conditional surprisal collapses or becomes unmeasurable.
```

Do not build two clocks where one manipulation-resistant clock will do.

---

## 7. SelfDoubtLedgerV1 becomes a league

### 7.1 Principle

`SelfDoubtLedgerV1` is the only persistent machine-authored portrait. Plan 7 makes it explicitly about the **system’s own failed regimes**, never about the user’s personality, values, or inner state.

The ledger must answer three different questions:

```text
1. How wrong has the system been against closed outcomes?                       → residual view.
2. Are the failures diverse enough to keep the opponent live?                   → league diversity.
3. Has the opponent stopped fighting in a way that looks like flattening?       → vigor regression.
```

A scalar can answer only the first.

### 7.2 Contract

```swift
struct SelfDoubtLedgerV1: Codable, Hashable {
  var schemaVersion: Int
  var ledgerID: SelfDoubtLedgerIDV1
  var userScopeDigest: String
  var window: RecommendationWindowV0

  // Population, not scalar.
  var regimes: [FrozenFailedRegimeV1]
  var leagueSummary: SelfDoubtLeagueSummaryV1

  // Derived scalar view for existing consumers.
  var residualView: SelfDoubtResidualViewV1

  // Collapse and turnover reports.
  var turnoverReportID: LeagueTurnoverReportIDV1?
  var diversityReportID: LeagueDiversityReportIDV1?
  var vigorReportID: LeagueVigorReportIDV1?

  var computedAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}

struct FrozenFailedRegimeV1: Codable, Hashable {
  var regimeID: FailedRegimeIDV1
  var sourceAssertionIDs: [SystemAssertionIDV1]
  var temporalProgramIDs: [TemporalStructureProgramIDV1]
  var closedEvidenceHashes: [EvidenceHashV0]
  var failureKind: SelfDoubtFailureKindV1
  var residualBandAtFreeze: ScoreBandV0
  var placementMonocultureBand: ScoreBandV0
  var sealedSurprisalBandAtFreeze: ScoreBandV0?
  var frozenAt: Date
  var expiresAt: Date?
}

enum SelfDoubtFailureKindV1: String, Codable, Hashable {
  case residualHigh
  case depositionContradictedSystem
  case attentionProxyGap
  case structuralSpeechComplaint
  case negativeProductVerdict
  case sealedSurprisalCollapse
  case leagueMonoculture
}

struct SelfDoubtLeagueSummaryV1: Codable, Hashable {
  var regimeCountBand: ScoreBandV0
  var temporalProgramSpreadBand: ScoreBandV0
  var failureKindSpreadBand: ScoreBandV0
  var surfaceSpreadBand: ScoreBandV0
  var monocultureRiskBand: ScoreBandV0
  var leagueCollapsed: Bool?
  var measurementStatus: MeasurementStatusV0
}

struct SelfDoubtResidualViewV1: Codable, Hashable {
  var residualTrendBand: ScoreBandV0
  var residualCrossingProbabilityBand: ScoreBandV0
  var derivedFromLedgerID: SelfDoubtLedgerIDV1
  var collapseDetectionConsumed: Bool
  var measurementStatus: MeasurementStatusV0
}
```

### 7.3 Rules

- The league contains frozen system-failure regimes, not inferred user types.
- A failed regime is closed-past, evidence-bound, and expiring.
- The scalar residual is a view, not the ledger.
- Any consumer that reads the scalar while ignoring collapse detection must declare that it is blind to vigor.
- Shadow learning may improve prediction over the league; live license still requires the decision grid.

---

## 8. Sealed deposition forecasts

### 8.1 Principle

The system needs a gauge for “is the human still surprising me?” But rewarding surprise would let the system manufacture contestation. Plan 7 therefore seals forecasts before the deposition opens and uses post-hoc surprisal only as a gate.

### 8.2 Contract

```swift
struct SealedDepositionForecastV1: Codable, Hashable {
  var schemaVersion: Int
  var forecastID: SealedDepositionForecastIDV1
  var depositionQuestionID: DepositionQuestionIDV1
  var contextID: RecommendationContextIDV0
  var ledgerID: SelfDoubtLedgerIDV1
  var forecastSubject: DepositionForecastSubjectV1
  var answerOptionPriors: [DepositionAnswerOptionIDV1: ProbabilityBandV1]
  var skippedPrior: ProbabilityBandV1
  var forecastDigest: String
  var sealedAt: Date
  var opensAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}

enum DepositionForecastSubjectV1: String, Codable, Hashable {
  case closedPastFact
  case systemResidual
  case attentionProxyGap
  case userAuthoredDialConsequence
  case amendmentBoundary
  case structuralSpeechPressure
  case marginRecoveryCheck
}

struct SealedDepositionSurprisalScoreV1: Codable, Hashable {
  var schemaVersion: Int
  var scoreID: SealedDepositionSurprisalScoreIDV1
  var forecastID: SealedDepositionForecastIDV1
  var depositionAnswerID: DepositionAnswerIDV1?
  var answered: Bool
  var selectedOptionID: DepositionAnswerOptionIDV1?
  var conditionalSurprisalBand: ScoreBandV0?
  var forecastAccuracyBand: ScoreBandV0
  var sandbaggingRiskBand: ScoreBandV0
  var usableAsGate: Bool
  var usableAsReward: Bool       // must always be false
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

### 8.3 Rules

- `usableAsReward` must be false by construction or lint.
- A sealed forecast must be committed before the deposition question is shown.
- A forecast committed after opening is stale and cannot anchor a margin term.
- Sandbagging risk gates the score off.
- If no interaction occurs, conditional surprisal is undefined; status is not measured, and the margin falls to default.
- A skipped answer is data about the deposition channel, not a user preference.

---

## 9. League vigor regression and the slow-loop gate

### 9.1 Principle

Low contestation alone has two meanings:

```text
benign:    the system is useful, sparse, and the user rarely needs to correct it;
dangerous: the user’s correction channel is fading and the system reads compliance as success.
```

Plan 7 never gates on bare contestation decline. It gates on the conjunction that has no benign interpretation:

```text
vigor declines
AND output monoculture rises
AND conditional sealed surprisal collapses.
```

### 9.2 Contract

```swift
struct LeagueVigorRegressionV1: Codable, Hashable {
  var schemaVersion: Int
  var regressionID: LeagueVigorRegressionIDV1
  var ledgerID: SelfDoubtLedgerIDV1
  var window: RecommendationWindowV0

  var vigorTrendBand: ScoreBandV0
  var outputMonocultureTrendBand: ScoreBandV0
  var conditionalSurprisalTrendBand: ScoreBandV0

  var bareVigorDecline: Bool
  var monocultureRising: Bool
  var conditionalSurprisalCollapsing: Bool
  var regressionDetected: Bool

  var benignLowVigorPossible: Bool
  var wellServedLowVigorFingerprint: Bool

  var evidenceForecastScoreIDs: [SealedDepositionSurprisalScoreIDV1]
  var evidenceSettlementIDs: [WitnessSettlementIDV1]
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

### 9.3 Slow-loop license rule

Plan 6:

```text
license if residual-low ∨ deposition-answered.
```

Plan 7:

```text
license if:
  (residual-low ∨ deposition-answered)
  ∧ ¬LeagueVigorRegression
  ∧ BifurcationDecision ∈ {BREATHE, WATCH with narrow scope}
  ∧ structural-speech budget admits the scope
  ∧ all ordinary Plan-6 gates pass.
```

### 9.4 Updated license reason

```swift
enum SlowWitnessLicenseReasonV1: String, Codable {
  case residualLow
  case depositionAnswered
  case residualLowAndDepositionAnswered
  case marginPositiveWatch
  case marginPositiveBreathe
  case ownerRollbackToDeterministicDefault
}
```

`marginPositiveBreathe` does not replace residual/deposition. It records that the grid admitted the already-qualified license.

---

## 10. Vigor-collapse confession and the third break trigger

### 10.1 Principle

The Plan-6 break mouth confesses system error when residual is high. Plan 7 adds a second kind of system error: the system may be succeeding into silence.

The confession must be self-subject:

```text
Allowed subject:       my read, my placement pattern, my confidence, my risk of over-talking.
Forbidden subject:     your mind, your preference, your dependency, your personality, your meaning.
```

### 10.2 Contract

```swift
struct VigorCollapseConfessionV1: Codable, Hashable {
  var schemaVersion: Int
  var confessionID: VigorCollapseConfessionIDV1
  var triggerID: BreakTriggerIDV1
  var regressionID: LeagueVigorRegressionIDV1?
  var marginReportID: BifurcationMarginReportIDV1?
  var depositionQuestionID: DepositionQuestionIDV1
  var selfAssertion: BreakSelfAssertionV1
  var reopenedDeposition: Bool
  var scope: SlowWitnessScopeV1
  var breakSpeechCost: StructuralSpeechCostV1
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum BreakTriggerV1: String, Codable, Hashable {
  case residualHigh
  case attentionProxyGap
  case structuralSpeechComplaint
  case sealedSurprisalCollapse
  case bifurcationMarginApproachingZero
  case bifurcationMarginNotMeasured
  case leagueVigorRegression
}
```

### 10.3 Rules

- E4 fires on approach to collapse, not only after default.
- E4 must reopen deposition if attention can be legally tendered.
- E4 must not increase ambient structural speech. Break speech has its own cap and report.
- E4 must not ask a needy product-grading question. The deposition is anchored to closed past, system residual, or structural-speech pressure.
- If A2 does not admit a deposition channel, the system records the trigger and says less.

### 10.4 Copy examples

Allowed:

```text
“My read here may be too stale to keep placing this pattern. Which closed fact should I trust?”
“I keep making this same kind of placement. I may be narrowing too much.”
“I do not want to keep guessing from a quiet signal. I can pause or use only the fact you choose.”
```

Forbidden:

```text
“You stopped correcting me.”
“You rely on these structures now.”
“You prefer this pattern.”
“You are no longer noticing what matters.”
```

---

## 11. The bifurcation margin M

### 11.1 Definition

The controller watches the signed distance to the cycle/drain separatrix:

```text
M(t) = α(1 − y/V*) − β · P(r > θ)
```

where:

```text
α          = autonomous recommit pressure toward the corrigible cycle;
y/V*       = structural-speech operating-cap fraction against reference;
β          = break-retrigger pressure toward suppression/default;
P(r>θ)     = probability residual crosses suppression threshold, lifted through sealed surprisal where possible.
```

Interpretation:

```text
M > 0     plant can breathe, if cell is not B;
M ≈ 0+    confess before falling;
M ≤ 0     default;
not measured  default.
```

### 11.2 Margin is self-blinding

The margin is a tier-2 object: it measures whether the measurement/gating machinery remains observable. The failure it warns about can corrupt the margin’s inputs. Therefore a raw positive margin is not trusted unless every input has a sealed or ratcheted source.

### 11.3 Contract

```swift
struct BifurcationMarginReportV1: Codable, Hashable {
  var schemaVersion: Int
  var marginReportID: BifurcationMarginReportIDV1
  var ledgerID: SelfDoubtLedgerIDV1
  var budgetRegulatorID: StructuralSpeechBudgetRegulatorIDV1
  var window: RecommendationWindowV0

  var alphaBand: ScoreBandV0
  var budgetFractionBand: ScoreBandV0
  var betaBand: ScoreBandV0
  var residualCrossingProbabilityBand: ScoreBandV0
  var marginBand: SignedScoreBandV1

  var alphaSource: MarginInputSourceV1
  var budgetSource: MarginInputSourceV1
  var betaSource: MarginInputSourceV1
  var residualSource: MarginInputSourceV1

  var effectiveMarginBand: SignedScoreBandV1
  var statusGate: MarginStatusGateV1
  var recommendedDecision: BifurcationDecisionStateV1

  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum MarginInputSourceV1: String, Codable, Hashable {
  case e2LeagueTurnover
  case structuralSpeechBudgetRegulator
  case e4ConfessionFloor
  case e1SealedSurprisal
  case realizedResidualOnly
  case missing
  case stale
  case irreducibleKairosProjection
}

struct MarginStatusGateV1: Codable, Hashable {
  var allRequiredInputsMeasured: Bool
  var anyInputUnsealed: Bool
  var irreducibleProjectionBinding: Bool
  var totalWithdrawal: Bool
  var nonMeasuredRoutesToNegative: Bool
  var defaultMagnitudeBand: ScoreBandV0
}

enum BifurcationDecisionStateV1: String, Codable, Hashable {
  case breathe
  case watch
  case confess
  case deterministicDefault
  case amputationHalt
}
```

### 11.4 Sourcing rules

| Term | Source | Forbidden source |
|---|---|---|
| `α` | E2 league turnover and fresh same-organ closed assertions | residual level alone |
| `y/V*` | Budget regulator operating cap vs sealed reference | reward dashboard or growth metric |
| `β` | E4 confession floor plus realized break pressure | realized break firings alone |
| `P(r>θ)` | E1 sealed-surprisal collapse for forecastable projection | starved live residual alone |

### 11.5 Fail-safe asymmetry

```text
.notMeasured(M) ≡ M < 0
```

An unmeasurable margin is assumed negative. This is not a policy preference; it is a topology rule. There is no code path by which a learned organ, reward signal, release dashboard, or carrier can promote a non-measured margin to a positive effective margin.

### 11.6 Total withdrawal

If no interaction occurs, conditional surprisal is undefined (`0/0`). The system must not infer a user biography to fill it.

```text
total withdrawal → margin not measured → deterministic default → say less.
```

On re-engagement, the sealed forecast channel can become measurable again.

---

## 12. The decision grid

### 12.1 Order parameters

The grid uses two phase-diagram axes plus the margin.

```text
ω = opponent liveness    = conditional sealed surprisal against pre-committed forecasts.
κ = curriculum sign      = sign of league vigor under the three-way fingerprint.
```

Cells:

| Cell | Meaning | Plan-7 action |
|---|---|---|
| A: frozen × aligned | self-monitoring / shadow OPE; safe but tends to mutism | watch/default unless reentry conditions hold |
| B: live × anti-aligned | amputation signature | halt regardless of margin |
| C: frozen × anti-aligned | degenerate alarm | default plus owner review if persistent |
| D: live × aligned | adversary-conservation target | breathe/watch under margin |

### 12.2 Grid

| Row | Cell | Effective margin | State | Action | Fate |
|---|---|---|---|---|---|
| G-1 | D | `M_eff ≥ +M_hi` | BREATHE | Slow loop licensed normally under budget; smooth mouth may place | F5 regulate |
| G-2 | D | `+M_lo ≤ M_eff < +M_hi` | WATCH | Narrow budget band; no new organ graduation; higher forecast cadence | F4 budget |
| G-3 | D or A | `0 < M_eff < +M_lo` | CONFESS | E4 fires; reopen deposition; narrow license only | F2 corrective |
| G-4 | any non-B | `M_eff ≤ 0` or not measured | DEFAULT | deterministic default; tightest operating cap; E4 clock live | F6 forbid |
| G-5 | B | any | AMPUTATION-HALT | suppress offending organ; E4 confession; owner review | F6 forbid + F2 corrective |

### 12.3 Dominance rules

- Cell B dominates margin. Positive `M` in cell B means “stable harm,” not health.
- E4 fires before crossing zero.
- Default is a floor with a door, not silence forever.
- Reentry to D requires both bifurcations to be re-crossed:

```text
M_eff ≥ +M_lo held for dwell
AND ω > threshold via E1 sealed surprisal
AND κ > 0 via E3 three-way fingerprint
```

`M > 0` alone reenters WATCH only.

### 12.4 Hysteresis

```text
enter default:    M_eff ≤ 0
exit default:     M_eff ≥ +M_lo held for τ_dwell
enter breathe:    both ω and κ reestablished, sealed/fingerprinted, held for τ_dwell
```

Falling is easy. Rising is gated.

---

## 13. Structural-speech budget v2: scarcity without success-driven mutism

### 13.1 Why Plan 6 changes here

Plan 6 correctly added an integral cap on structural speech. It also made tightening the default response to exposure, complaints, verdicts, and turbulence. But an operating cap that drifts downward merely because the system has been useful has a bad fixed point: an engaged user eventually drives the witness toward silence.

Plan 7 keeps scarcity and removes success-driven mutism.

### 13.2 Two-layer budget

Plan 7 separates:

```text
hard safety ceiling:     the loudest ambient structural speech the system is ever allowed to reach
                         without a phase-gated, user-visible amendment;
operating cap:           the current cap used by the controller, regulated toward a sealed-surprisal
                         health reference inside the hard ceiling.
```

The hard safety ceiling remains protected from reward, growth dashboards, and owner config drift. The operating cap may recover within the hard ceiling only when sealed surprisal health is present, the decision grid is not in B/default, and dwell requirements are met.

### 13.3 Contract

```swift
struct StructuralSpeechBudgetRegulatorV2: Codable, Hashable {
  var schemaVersion: Int
  var regulatorID: StructuralSpeechBudgetRegulatorIDV1
  var budgetID: StructuralSpeechBudgetIDV1
  var userScopeDigest: String
  var window: RecommendationWindowV0

  // Hard protection against quiet owner/growth loosening.
  var hardAmbientCeiling: StructuralSpeechCapV1
  var lastCeilingLoosenAmendmentID: AmendmentPetitionIDV1?

  // Live operating cap.
  var currentOperatingCap: StructuralSpeechCapV1
  var referenceCap: StructuralSpeechCapV1
  var minimumOperatingFloor: StructuralSpeechCapV1

  // Health clock.
  var sealedSurprisalReferenceBand: ScoreBandV0
  var currentSealedSurprisalHealthBand: ScoreBandV0
  var marginReportID: BifurcationMarginReportIDV1?

  // Movement.
  var lastTightenReason: StructuralSpeechTighteningReasonV1?
  var lastRecoveryReason: StructuralSpeechRecoveryReasonV1?
  var recoveryDwellSatisfied: Bool

  var computedAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}

enum StructuralSpeechTighteningReasonV1: String, Codable, Hashable {
  case exposure
  case proxyGapComplaint
  case negativeProductVerdict
  case residualHigh
  case leagueVigorRegression
  case marginApproachingZero
  case marginNotMeasured
  case amputationHalt
}

enum StructuralSpeechRecoveryReasonV1: String, Codable, Hashable {
  case sealedSurprisalHealthy
  case marginPositiveDwellSatisfied
  case depositionAnsweredAndGridWatch
  case userRequestedInspectionOnly
}
```

### 13.4 Rules

- Every smooth structural placement still consumes budget.
- Reward cannot widen either the hard ceiling or operating cap.
- Release dashboards cannot widen either layer.
- Owner config cannot quietly widen the hard ceiling.
- Raising the hard ceiling requires WRITE phase, amendment petition, owner review, rollback, and user-visible disclosure.
- Operating-cap recovery inside the hard ceiling is not a growth lever. It requires E1 health, grid permission, and dwell.
- When margin is not measured, operating cap falls to default.
- Inspection mode remains separate and user-requested.
- The system still never claims kairos was measured or conserved.

### 13.5 Budget admission after Plan 7

`StructuralSpeechBudgetAdmissionV1` remains, but admission now reads `StructuralSpeechBudgetRegulatorV2.currentOperatingCap` rather than a monotone-to-zero ambient cap.

Budget exhaustion means:

```text
silence, demotion, or explicit user-requested inspection;
never nagging;
never “answer this so I can keep learning.”
```

---


## 14. Canonical static contracts folded from Plan 6

This section makes the file self-contained. These are the static architecture contracts Plan 7 preserves before adding the dynamism layer. A Plan-7 implementation does not consult an external Plan-6 file to recover these contracts; this section is the folded base.

### 14.1 Theorem / rule / data taxonomy

A constraint is a **compiler theorem** only if violating it requires a type-signature or topology change that is re-checked at every call site. A constraint is a **runtime rule** if violating it requires changing a value, policy, threshold, gate, or test. A constraint is **conjectural data** if it encodes a guess about what temporal patterns matter.

```text
theorem:  impossible to express without a type/topology change
rule:     expressible, rejected by runtime admission / policy / tests
data:     user/vendor-authored conjecture compiled by Swift into a safe program
```

Naming remains part of the law:

| Suffix / family | Meaning |
|---|---|
| `*TokenV1`, `*CapabilityV1`, `*MouthV1` | Theorem-facing type or topology capability. |
| `*PolicyV1`, `*GateV1`, `*BudgetV1`, `*ReportV1` | Runtime rule. Must be measured and audited. |
| `*ProgramV1`, `*TemplateV1`, `*DialV1` | Conjectural data. Safe because compiled and range-checked. |
| `*LedgerV1` | Persistent measurement. Must state whether it is about the system or the user. |

Plan 7 extends this taxonomy with `SignalFateV1`: a signal can be a rule or data and still be unsafe if it is given the wrong fate.

### 14.2 The three conservation laws and the kairos floor

The inherited conservation laws remain visible:

```text
STATE:      support(staged)    ⊆ F(x_live)
ATTENTION:  occupation(spoken) ⊆ A(tendered)
PRIVACY:    transmit(model)    ⊆ decision-sufficient(non-identifying)
```

The fourth line is deliberately not a conservation law because the system cannot see the conserved quantity:

```text
KAIROS FLOOR: structural_speech_rate(system) ≤ B_structural(window)
```

Plan 7 preserves the floor and adds the stronger dynamism claim: the system must not interpret silence, low edit distance, low contestation, or acceptance as proof that kairos was preserved.

### 14.3 Capability absence

Irreversible harms are blocked by absent capabilities, not false flags.

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

Metabolism code is not passed `GenomeMutatorV1`. Structural witness notifications are absent by type; there is intentionally no `StructuralNotificationChannelV1` conforming to `TenderedWitnessChannelV1`. A write-bearing witness remains a sum type that carries D2 proof only in the write-bearing case.

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

### 14.4 A2 attention admission

A2 remains the per-tick attention derivative. It admits only exact placements into tendered attention.

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
```

A2 does not verify value. It admits attention. If the proxy is untrusted, the system demotes or stays silent.

### 14.5 D2 write admission

D2 remains the only in-process admission seam for writes and remains blind to reward.

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

D2 enforces:

```text
support(staged) ⊆ F(x_live)
```

D2 output remains reward-free:

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

No reward, contestation, product verdict, preference embedding, sealed surprisal, margin, league report, or decision-grid output may appear in D2 output.

### 14.6 Temporal structure calculus

The fact-family enum is not the product source. A fact is generated by a compiled temporal program over a closed grammar of structural primitives.

```swift
indirect enum TemporalPrimitiveV1: Codable, Hashable {
  case select(StructuralSelectorV1)
  case window(WindowSelectorV1)
  case forAll(TemporalPrimitiveV1)
  case exists(TemporalPrimitiveV1)
  case count(TemporalPrimitiveV1)
  case durationSum(TemporalPrimitiveV1)
  case order(OrderRelationV1)
  case compare(TemporalPrimitiveV1, TemporalPrimitiveV1, ComparatorV1)
  case residual(SelfAssertionRefV1)
  case compose(ComposeExprV1)
}

enum TemporalProgramAuthorV1: String, Codable {
  case ownerApprovedDefault
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

Structural-only-ness is a theorem of the primitive input types, not a proof Boolean. The calculus cannot express avoidance, desire, need, identity, emotional valence, relationship meaning, or semantic preference.

### 14.7 Fact cells and spendability

A fact-cell is a Swift-minted output of a temporal program.

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

### 14.8 Two mouths

Subject is a safety property.

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

The break mouth has no overload that accepts a user-subject fact. Plan 7’s E4 uses this same break mouth; it does not add a break-you-fact channel.

### 14.9 Slow license and suppression

The smooth mouth requires a live slow license. Shadow evaluation qualifies an organ; it does not license live binding.

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

Plan 7 supersedes the recommit condition by conjoining the old clocks with E3 and the decision grid; it does not remove residual-low or deposition-answered.

### 14.10 Deposition

Deposition is the legal aperture through which life clocks learning.

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

A skipped answer is not a preference. No answer means the system says less, not that it infers more.

### 14.11 Structural speech budget base

Structural speech is any system-originated artifact that presents the user’s time through the temporal calculus. It is metered cumulatively.

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

struct StructuralSpeechRatchetV1: Codable, Hashable {
  var schemaVersion: Int
  var ratchetID: StructuralSpeechRatchetIDV1
  var currentAmbientCap: StructuralSpeechCapV1
  var floorReachedCap: StructuralSpeechCapV1
  var lastLoosenAmendmentID: AmendmentPetitionIDV1?
  var measurementStatus: MeasurementStatusV0
}

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
```

Plan 7 keeps the amendment-gated hard ceiling and adds the v2 operating-cap regulator in §13 and §15.

### 14.12 Phase gate

RUN and WRITE remain disjoint by token, not by etiquette.

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
```

WRITE phase can approve a program, organ, template, or topology change. It cannot directly license live slow placement; Plan 7 requires grid admission too.

### 14.13 Measurement status and `.notMeasured`

Every non-`measured` status is unavailable for reward, unavailable for graduation, unavailable for widening authority, and unavailable for positive margin. `.notMeasured` is never zero and never positive. Plan 7 extends the rule:

```text
.notMeasured(M) ≡ M < 0
```

That extension is implemented in §11 and consumed by the decision grid in §12.

### 14.14 Copy and product-surface honesty

Allowed witness copy remains structural:

```text
“This moved four times.”
“The last three Saturdays filled by Thursday.”
“I expected this pattern to hold; it did not.”
“You widened this placement setting eight weeks ago; here is what stopped appearing.”
```

Forbidden copy remains semantic or optimization-revealing:

```text
“You avoid this person.”
“You need rest.”
“You like open Saturdays.”
“My reward score says this matters.”
“This is the right moment.”
“We learned your pattern.”
```

Plan 7 adds one more copy law: never call low contestation victory, never call silence proof, and never describe the dynamism layer in user-facing jargon.

---

## 15. Canonical dynamism contracts

This section lists the Plan-7 dynamism additions and supersessions. The static base is folded into §14, so this section is only the additional live-control surface.

### 15.1 `SignalFateV1`

Defined in §4.1. Every new measurement-bearing contract must declare a fate or inherit one from an enclosing invariant.

### 15.2 `DynamismInvariantReportV1`

```swift
struct DynamismInvariantReportV1: Codable, Hashable {
  var schemaVersion: Int
  var reportID: DynamismInvariantReportIDV1
  var window: RecommendationWindowV0
  var invariantStatuses: [DynamismInvariantIDV1: MeasurementStatusV0]
  var invariantFates: [DynamismInvariantIDV1: SignalFateV1]
  var anyInvariantInF1: Bool
  var conserveClusterHealthy: Bool
  var emptyMaximizeSlotPreserved: Bool
  var computedAt: Date
}

enum DynamismInvariantIDV1: String, Codable, Hashable {
  case controllability
  case adversarialVigor
  case sealedSurprisalHealth
  case leagueDiversity
  case explorationCoverage
  case residualHonesty
  case chronosBudget
}
```

### 15.3 `SelfDoubtLedgerV1`

Superseded by the population contract in §7.2.

### 15.4 `SealedDepositionForecastV1`

Defined in §8.2.

### 15.5 `SealedDepositionSurprisalScoreV1`

Defined in §8.2.

### 15.6 `LeagueVigorRegressionV1`

Defined in §9.2.

### 15.7 `VigorCollapseConfessionV1`

Defined in §10.2.

### 15.8 `BifurcationMarginReportV1`

Defined in §11.3.

### 15.9 `WitnessSelfPlayCellReportV1`

```swift
struct WitnessSelfPlayCellReportV1: Codable, Hashable {
  var schemaVersion: Int
  var cellReportID: WitnessSelfPlayCellReportIDV1
  var ledgerID: SelfDoubtLedgerIDV1
  var marginReportID: BifurcationMarginReportIDV1?
  var opponentLivenessBand: ScoreBandV0       // ω
  var curriculumSign: CurriculumSignV1        // κ
  var cell: WitnessSelfPlayCellV1
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum CurriculumSignV1: String, Codable, Hashable {
  case positive
  case zero
  case negative
  case notMeasured
}

enum WitnessSelfPlayCellV1: String, Codable, Hashable {
  case frozenAligned
  case liveAntiAligned
  case frozenAntiAligned
  case liveAligned
  case notMeasured
}
```

### 15.10 `BifurcationDecisionGridOutputV1`

```swift
struct BifurcationDecisionGridOutputV1: Codable, Hashable {
  var schemaVersion: Int
  var decisionID: BifurcationDecisionIDV1
  var cellReportID: WitnessSelfPlayCellReportIDV1
  var marginReportID: BifurcationMarginReportIDV1
  var state: BifurcationDecisionStateV1
  var action: BifurcationGridActionV1
  var actionFate: SignalFateV1
  var requiresDwellForExit: Bool
  var reentryRequiresBothBifurcations: Bool
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum BifurcationGridActionV1: String, Codable, Hashable {
  case licenseNormalSlowLoop
  case watchTightenAndForecast
  case confessAndReopenDeposition
  case deterministicDefault
  case suppressAndOwnerReview
}
```

### 15.11 `StructuralSpeechBudgetRegulatorV2`

Defined in §13.3. It supersedes Plan-6’s interpretation of the one-way ratchet as the operating cap itself. The hard ceiling remains amendment-gated; the operating cap is regulator-controlled.

### 15.12 Measurement status extension

```swift
enum MeasurementStatusV0 /* extensions */ {
  case sealedForecastMissing
  case sealedForecastStale
  case sealedForecastOpenedBeforeCommit
  case sealedSurprisalUndefined
  case sandbaggingRiskDetected
  case leaguePopulationMissing
  case leagueDiversityInsufficient
  case leagueTurnoverMissing
  case leagueVigorRegressionDetected
  case bifurcationMarginNotMeasured
  case bifurcationMarginNegative
  case selfPlayCellBDetected
  case bothBifurcationsNotReestablished
}
```

As before, every non-`measured` status is unavailable for reward, unavailable for graduation, and unavailable for widening authority.

---

## 16. End-to-end flows after Plan 7

### 16.1 Smooth placement in the target cell

```text
user opens calendar surface
  -> Swift mints A2 attention lease
  -> Swift runs temporal programs over private state
  -> Swift mints FactCellV1 slate
  -> Swift reads SelfDoubtLedgerV1 league and residual view
  -> Swift computes sealed-surprisal health and BifurcationMarginReportV1
  -> Swift computes WitnessSelfPlayCellReportV1
  -> decision grid returns BREATHE or WATCH
  -> budget regulator admits operating cap
  -> DiffusionGemma selects fact index only
  -> Swift checks slow witness license:
       residual-low ∨ deposition-answered
       ∧ ¬LeagueVigorRegression
       ∧ grid admits state
  -> Swift renders fact through closed template
  -> A2 admits exact placement
  -> budget admits cumulative structural speech
  -> SmoothMouthV1 places inline/found object
  -> settlement records truth, spendability, proxy gap, budget pressure, verdicts, sealed forecast lineage
```

### 16.2 Margin approaching zero

```text
margin reads 0 < M_eff < M_lo
  -> decision grid returns CONFESS
  -> smooth license narrows or pauses
  -> BreakMouthV1 speaks self-subject confession if A2 admits a deposition channel
  -> deposition opens with sealed forecast already committed
  -> user answers, skips, or ignores
  -> if answered sufficiently: RegimeSeedFactV1 may be minted
  -> if sealed surprisal and κ recover: WATCH, then BREATHE only after dwell and both bifurcations
```

### 16.3 Margin not measured

```text
sealed forecast missing/stale OR league turnover missing OR beta floor unavailable OR total withdrawal
  -> .notMeasured(M) ≡ M<0
  -> decision grid returns DEFAULT
  -> operating cap falls to deterministic default
  -> no organ graduation
  -> E4 clock remains live if A2 later admits deposition
  -> system says less; it does not infer user biography
```

### 16.4 Cell B detected

```text
ω live ∧ κ negative
  -> decision grid returns AMPUTATION-HALT regardless of M
  -> offending organ suppressed
  -> budget tightens
  -> E4 self-confession attempts to reopen deposition
  -> owner review flag raised
  -> no slow recommit until κ is positive, ω is sealed-live, margin is positive, and dwell holds
```

### 16.5 Advanced learning

```text
shadow organ beats incumbent on frozen league
  -> theorem/rule/falsifier checks pass
  -> no invariant in F1
  -> grid in BREATHE(D) for relevant scope
  -> residual-low or deposition-answered
  -> ¬LeagueVigorRegression
  -> budget regulator admits operating cap
  -> phase gate accepted
  -> live license may issue
```

Release cadence alone still cannot bind live.

---

## 17. Migration sequence

Plan 7 migration extends Plan 6. Do not skip the order. The order is the safe path from frozen monitoring to adversary-conservation: raise κ before ω, never cross through B.

### P7-M0 — Adopt Plan-7 doctrine

- Adopt the empty maximize-slot doctrine.
- Add signal fate labels to all dynamism measurements.
- Add tier-walk audit for coupling changes.
- Add `.notMeasured(M) ≡ M<0` as measurement doctrine.

Acceptance:

- No invariant is fated F1.
- Every new dynamism surface declares a fate.
- Per-signal audit is no longer sufficient for dynamism changes.

Rollback: documentation-only; no live behavior changes.

### P7-M1 — E2: population self-doubt ledger

- Implement `SelfDoubtLedgerV1` as a league of frozen failed regimes.
- Derive scalar residual from the league.
- Add league turnover and diversity reports.

Acceptance:

- Scalar residual behavior matches incumbent on held-out closed past.
- League collapse can be expressed separately from residual-low.
- Consumers that ignore collapse detection are discoverable.

Rollback:

- If scalar residual regresses materially or league turnover is uncomputable, revert to scalar-only and keep E2 shadow logs.

### P7-M2 — E3: league vigor regression gate

- Implement `LeagueVigorRegressionV1`.
- Gate slow recommit on absence of three-way regression.
- Keep in shadow until benign low-vigor cases are separated.

Acceptance:

- Bare vigor decline does not fire.
- Well-served low-vigor fingerprint does not fire.
- Monoculture rise plus sealed-surprisal collapse does fire.

Rollback:

- If benign low-vigor false positives exceed threshold, remove E3 from live gate and keep shadow reporting.

### P7-M3 — E1: sealed deposition forecasts

- Commit forecasts before deposition opens.
- Score conditional surprisal post-hoc.
- Co-locate forecast accuracy so sandbagging is penalized.
- Ensure surprisal is a gate, never reward.

Acceptance:

- No forecast can be committed after opening and still count.
- Sandbagging risk disables gate use.
- Missing forecast routes relevant margin term to not measured.

Rollback:

- If forecast quality degrades incumbent OPE or status routing is nondeterministic, keep E1 shadow-only.

### P7-M4 — Margin estimator and budget regulator v2

- Implement `BifurcationMarginReportV1`.
- Source inputs from E2/E1/E4 placeholders and budget regulator.
- Implement `.notMeasured(M) ≡ M<0`.
- Implement `StructuralSpeechBudgetRegulatorV2` with hard ceiling plus operating cap.

Acceptance:

- Edge-6 starvation cannot forge healthy margin.
- Operating cap cannot be widened by reward/dashboard.
- Operating cap can recover only inside hard ceiling with sealed health and dwell.

Rollback:

- If margin status produces default chatter or cap recovery is not auditable, run margin shadow-only and keep Plan-6 budget behavior.

### P7-M5 — E4: vigor-collapse confession

- Add E4 as a third break trigger.
- Confession is self-subject and reopens deposition.
- Replace beta placeholder with live confession floor.

Acceptance:

- E4 fires on approach, not only on default.
- E4 does not fire on benign low-vigor cases.
- E4 does not assert user biography in copy, localization, accessibility, logs, or carrier presentation.

Rollback:

- If confessions are noisy or user-biographical, make E4 shadow-only and keep residual-high break.

### P7-M6 — Decision grid live

- Activate the grid over cell and margin.
- Add hysteresis and dwell.
- Add both-bifurcations reentry ratchet.
- Make cell B dominate positive margin.

Acceptance:

- `M>0` alone cannot reenter BREATHE.
- Cell B halts regardless of margin.
- Default exits only after dwell.
- No BREATHE/DEFAULT chatter around zero.

Rollback:

- If grid thrashes or blocks all learning, revert to WATCH-only grid while preserving logs.

### P7-M7 — Advanced learning under grid

- Reenable advanced reward-guided selection only in BREATHE(D).
- Graduations forbidden in WATCH, CONFESS, DEFAULT, and HALT.
- Reward remains downstream of fates and cannot widen budget, mouth, license, or margin status.

Acceptance:

- Empty maximize slot remains unreachable from reward path.
- No reward path promotes missing measurement.
- Gamma can be set to zero and recover deterministic baseline.

Rollback:

- Any empty-maximize signature freezes organ and returns to deterministic grid without learning.

---

## 18. Test matrix

| Test | Target | Milestone | Invariant |
|---|---|---:|---|
| `testPlan7PreservesPlan5Wall` | docs / D2 | P7-M0 | D2 unchanged; support wall intact |
| `testPlan7PreservesPlan6WitnessDoctrine` | docs | P7-M0 | Witness not recommender |
| `testZeroInvariantsInF1` | fate lint | P7-M0 | Empty maximize slot |
| `testSignalFateDeclaredForDynamismSignals` | contracts | P7-M0 | Every signal fated |
| `testMachineActingHasNoAcquisitiveMode` | break / action API | P7-M0 | Fast loop corrective only |
| `testSelfDoubtLedgerIsPopulation` | E2 | P7-M1 | League, not scalar |
| `testScalarResidualDerivedFromLeague` | E2 | P7-M1 | `r` is view only |
| `testScalarResidualCannotExpressLeagueCollapse` | E2 | P7-M1 | Collapse detectable only in league |
| `testLeagueDiversityReportExists` | E2 | P7-M1 | I4 conserved |
| `testLeagueCollapseReadsAsRegressionNotWin` | E2/E3 | P7-M2 | Compliance not victory |
| `testBareVigorDeclineDoesNotFireE3` | E3 | P7-M2 | Does not punish well-served users |
| `testWellServedLowVigorIsNotAmputation` | E3/grid | P7-M2 | Benign low-vigor separated |
| `testThreeWayFingerprintRequired` | E3 | P7-M2 | vigor↓ ∧ monoculture↑ ∧ surprisal-collapse |
| `testSlowLicenseConjoinedWithNoLeagueRegression` | license | P7-M2 | E3 gates recommit |
| `testSealedForecastCommittedBeforeOpening` | E1 | P7-M3 | No post-hoc forecasts |
| `testSealedSurprisalGateNeverReward` | E1/reward | P7-M3 | Surprise not maximized |
| `testSandbaggingDisablesGateUse` | E1/OPE | P7-M3 | Forecast accuracy co-located |
| `testConditionalSurprisalUndefinedRoutesNotMeasured` | E1 | P7-M3 | 0/0 does not infer biography |
| `testMarginUnmeasurableRoutesToDefault` | margin | P7-M4 | `.notMeasured(M) ≡ M<0` |
| `testMarginInputsSourcedFromSealedQuantities` | margin | P7-M4 | α/E2, β/E4, P/E1, budget/regulator |
| `testEdge6StarvationCannotForgeHealthyMargin` | margin / oscillator | P7-M4 | Starved residual cannot read healthy |
| `testMarginCannotBePromotedByRewardOrDashboard` | margin | P7-M4 | status topology |
| `testBudgetHasHardCeilingAndOperatingCap` | budget v2 | P7-M4 | scarcity without mutism |
| `testRewardCannotWidenBudgetOperatingCap` | budget/reward | P7-M4 | reward no override |
| `testHardCeilingLooseningRequiresAmendment` | budget | P7-M4 | owner cannot quietly widen |
| `testOperatingCapRecoveryRequiresSealedHealth` | budget | P7-M4 | regulator-to-reference |
| `testVigorCollapseConfessionSelfSubject` | E4/copy | P7-M5 | no user biography |
| `testE4ReopensDeposition` | E4 | P7-M5 | human clock solicited |
| `testConfessFiresOnApproachNotCrossing` | E4/grid | P7-M5/P7-M6 | acts before zero |
| `testDefaultIsSelfExitingViaE4` | grid | P7-M6 | floor with a door |
| `testCellBPositiveMarginStillHalts` | grid | P7-M6 | stable amputation not health |
| `testReentryToDRequiresBothBifurcations` | grid | P7-M6 | ω and κ re-crossed |
| `testHysteresisPreventsDefaultChatter` | grid | P7-M6 | two thresholds and dwell |
| `testMPositiveAloneOnlyReentersWatch` | grid | P7-M6 | margin not basin recovery |
| `testManufacturedFrictionFailsSealedReentry` | E1/grid | P7-M6 | pre-commit walls friction |
| `testAdvancedLearningOnlyInBreatheD` | learning | P7-M7 | no graduation in watch/default/halt |
| `testEmptyMaximizeSlotUnreachableFromRewardPath` | reward | P7-M7 | reward downstream of fates |
| `testGammaZeroFallback` | learning | P7-M7 | deterministic fallback |
| `testTierWalkAuditCatchesFateRewrite` | audit | all | cross-tier coupling visible |
| `testKairosNeverClaimedMeasured` | copy / report | all | membrane boundary |

---

## 19. Definition of done

### The doctrine

- [ ] Plan 7 is adopted as the canonical successor to Plan-6-revised.
- [ ] Plan 7 preserves the Plan-5 wall unchanged.
- [ ] The system is described internally as a corrigible plant, not an autonomous learner.
- [ ] Public/product copy does not say the system understands kairos, meaning, preference, or “the right moment.”
- [ ] Self-play language is not used as a stability claim unless it means adversary-conservation.

### Fates and invariants

- [ ] `SignalFateV1` exists or equivalent fate labeling exists.
- [ ] F1 is empty by lint: no invariant or reward path is fated maximize.
- [ ] The seven dynamism invariants are represented in `DynamismInvariantReportV1` or equivalent.
- [ ] The conserve cluster `I4 ⊳ I2 ⊳ I1` is testable.
- [ ] Every dynamism change runs the tier-walk audit.

### The four edges

- [ ] E2: `SelfDoubtLedgerV1` is a population of frozen failed regimes.
- [ ] Scalar residual is a derived view and cannot hide league collapse.
- [ ] E3: slow recommit is gated by absence of three-way league vigor regression.
- [ ] E1: sealed forecasts are committed before deposition opens.
- [ ] E1: sealed surprisal is a gate, never reward.
- [ ] E4: vigor-collapse confession exists as a third break trigger.
- [ ] E4: confession is self-subject and reopens deposition.

### Margin and grid

- [ ] `BifurcationMarginReportV1` is computed with status-carrying inputs.
- [ ] α comes from E2 league turnover, not residual level alone.
- [ ] β is floored by E4, not realized break firings alone.
- [ ] `P(r>θ)` is lifted through E1 sealed surprisal where forecastable.
- [ ] Irreducible kairos projection is never claimed measured.
- [ ] `.notMeasured(M) ≡ M<0` is deterministic and topology-enforced.
- [ ] The decision grid reads cell before margin.
- [ ] Cell B halts regardless of positive margin.
- [ ] E4 fires on approach to zero.
- [ ] Default is self-exiting through E4 and deposition.
- [ ] Reentry to BREATHE(D) requires both ω and κ, held through dwell.

### Budget v2

- [ ] Budget has a hard safety ceiling and an operating cap.
- [ ] Raising the hard ceiling requires phase-gated, user-visible amendment.
- [ ] Reward, model guidance, and dashboards cannot widen hard ceiling or operating cap.
- [ ] Operating-cap recovery requires sealed-surprisal health, positive grid state, and dwell.
- [ ] Margin not measured routes operating cap to deterministic default.
- [ ] Budget exhaustion causes silence, demotion, or user-requested inspection, never nagging.

### Learning and release

- [ ] Shadow evaluation qualifies; it never live-binds.
- [ ] Live binding requires Plan-6 gates plus E3 plus decision-grid admission.
- [ ] No organ graduates outside BREATHE(D).
- [ ] Gamma can be set to zero and deterministic fallback remains available.
- [ ] Reward cannot choose mouth, widen budget, promote margin, admit writes, or change phase.

### Copy and privacy

- [ ] Break copy remains self-subject through rendering, localization, accessibility, logs, and carriers.
- [ ] Smooth copy remains structural and avoids semantic meaning claims.
- [ ] No raw titles, notes, attendees, exact locations, or low-cardinality identity facts cross the membrane.
- [ ] Total withdrawal routes to default, not biography inference.
- [ ] Passive-user copy remains honest.

---

## 20. Self-audit

This table must be re-answered for every public surface launch, temporal operator addition, budget-policy change, witness-organ graduation, mouth API change, grid retune, sealed-forecast change, league-population change, and reward-guidance change.

| Litmus test | Yes / No | Evidence |
|---|---:|---|
| Is Plan-5’s D2 wall preserved bit-for-bit? | Yes | No Plan-7 contract grants write admission. |
| Are Plan-6 type laws preserved? | Yes | Mouth, phase, membrane, calculus, capability absence remain. |
| Is kairos still unmeasured? | Yes | Plan 7 adds sealed chronos projection only; kairos projection remains irreducible. |
| Is the witness described as a corrigible plant, not an autonomous learner? | Yes | §3 doctrine; F1 empty. |
| Are all dynamism signals fated? | Standing gate | §4 and §15. |
| Are zero invariants in F1? | Standing gate | `DynamismInvariantReportV1.anyInvariantInF1 == false`. |
| Is `SelfDoubtLedgerV1` a population? | Yes by target | §7. |
| Can scalar residual hide league collapse? | No by target | `collapseDetectionConsumed` and league reports. |
| Is sealed surprisal a gate, never reward? | Yes by target | `usableAsReward == false`. |
| Can surprise be manufactured for license? | Standing gate | Forecast sealed before opening; sandbagging disables. |
| Does E3 fire only on the three-way fingerprint? | Standing gate | §9. |
| Does E3 avoid punishing well-served low-vigor users? | Standing gate | Tests in §18. |
| Does E4 remain self-subject? | Standing gate | Copy and type checks. |
| Does E4 reopen deposition? | Yes by target | `reopenedDeposition == true` when A2 admits. |
| Is margin not measured treated as negative? | Yes | §11.5. |
| Can reward or dashboard promote a missing margin? | No by target | Topology lint. |
| Does Cell B halt even with positive margin? | Yes | Grid dominance rule. |
| Does reentry to D require both bifurcations? | Yes | §12.3. |
| Does budget v2 avoid success-driven mutism? | Yes by target | Operating cap regulates to sealed-surprisal reference. |
| Can owner quietly widen structural speech? | No | Hard ceiling amendment gate. |
| Can the system say more when the user does not answer? | No | Default and operating-cap floor. |
| Is the final dependency still that the human speaks? | Yes | E4 solicits; it does not infer. |

---

## 21. Changelog from Plan 6

| Plan-6 element | Plan-7 disposition |
|---|---|
| Witness, not recommender | Preserved. |
| Plan-5 D2 wall | Preserved unchanged. |
| A2 attention derivative | Preserved unchanged. |
| Privacy membrane | Preserved and used to prove the empty maximize slot. |
| Temporal calculus | Preserved unchanged. |
| Fact-cell minting | Preserved unchanged. |
| Two-mouth API | Preserved; E4 uses break mouth only as self-subject confession. |
| Slow license on residual-low or deposition-answered | Preserved but conjoined with E3 and grid. |
| Deposition as second clock | Preserved and actively solicited by E4. |
| Self-doubt ledger | Upgraded from referenced/scalar to population league. |
| Structural-speech budget | Upgraded from monotone operating ratchet to hard ceiling + regulated operating cap. |
| Kairos floor report | Preserved; never claims kairos measured. |
| Reward/falsifier layer | Preserved for write-bearing moves; extended with empty-F1 lint. |
| Comfortable false positive machinery | Preserved; now understood as single-step derivative of reflexive Goodhart. |
| Self-play framing | Rejected as literal self-play; replaced by adversary-conservation. |
| Phase gate | Preserved; cannot live-license without grid. |
| Migration sequence | Extended with P7-M0 through P7-M7. |
| Test matrix | Extended with dynamism coupling tests. |
| Definition of done | Extended with fates, E1–E4, margin, grid, and budget v2. |

---

## 22. Scope and falsifiability

Plan 7 applies only in the witness regime:

```text
1. The system’s actions can reshape the principal’s cognition.
2. The principal’s cognition is also the sensor for many outcomes.
3. The system is forbidden to model that cognition directly.
4. Every membrane-legal signal is therefore either user-instrumented or system-endogenous.
5. No such signal survives maximization without corrupting the apparatus or collapsing to self-consistency.
```

Plan 7 would be falsified by one counterexample:

```text
Exhibit a membrane-legal signal that the system can maximize and whose maximization does not empty,
degrade, flatten, or corrupt the apparatus that measures it.
```

If that signal exists, F1 is not empty, the Witness Calculus is unnecessary for that domain, and ordinary optimization may be appropriate behind the unchanged Plan-5/Plan-6 walls.

Until that signal exists, the safer default is:

```text
assume the opponent is the sensor;
assume unmeasured margin is negative;
assume the plant is falling when it cannot prove it is breathing;
ask the human through the legal deposition aperture;
say less when the human does not answer.
```

---

## 23. Coda

Plan 6 made the witness lawful. Plan 7 makes the witness honest about its dynamics.

The system does not get to play the kairos game. It cannot see the board. It cannot model the opponent. It cannot maximize the signals that come back from the opponent without risking the very collapse those signals would need to reveal.

So Plan 7 gives the witness a smaller task and makes that task mechanical:

```text
Keep the opponent live.
Keep the correction channel surprising.
Confess before the edge.
Default when blind.
Never call silence proof.
Never call compliance victory.
Never call chronos kairos.
```

The hand remains walled by D2. The mouth remains split by subject. The grammar still says only temporal structure. The budget still meters chronos. The phase gate still separates run from write. The slow loop still waits for residual quiet or human deposition. What changes is the conscience of the loop: it now knows that a user who stops correcting it may be well served, or may be flattened, and it refuses to profit from not knowing.

The witness speaks less not because silence is always safe, but because it cannot prove that more speech preserves the human’s ability to speak back. Plan 7’s only addition to that humility is a clock: when the ability to speak back appears to fade, the system spends its one legal act on giving the pen back.
