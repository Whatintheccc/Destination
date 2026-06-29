# plan-7-revised.md — Witness Architecture with a Verifiable Corrigible-Plant Controller

**Status:** canonical Plan-7 revised target architecture. This document folds the stable Plan-6 base, the Witness Calculus dynamism review, and the Plan-7 controller audit into one cohesive specification. It is a target architecture, not a claim of shipped implementation.

**Revision decision:** accepted. The Plan-7 doctrine and airframe are sound, but the first Plan-7 controller was not executable enough: its grid compared against unminted thresholds, the self-play cell axis was Zeno-open, the speech-rate actuator did not exist, and one license enum was duplicated. Plan-7-revised makes those seven audit repairs first-class contracts and then rewrites the controller around them.

**One-line thesis:** CalAgent remains a witness, not a recommender. It may learn only inside a human-clocked, rate-limited, corrigible plant. It may act only by suppressing itself, confessing its own measurement failure, or returning the pen through deposition. It never becomes an autonomous learner and never optimizes the user.

```text
Plan 6 base:          D2 wall + A2 attention + privacy membrane + temporal calculus
                      + two-mouth API + deposition + phase gate + structural speech scarcity.

Self-play review:     E1 sealed forecasts, E2 population self-doubt ledger,
                      E3 league-vigor gate, E4 vigor-collapse confession.

Controller audit:     sound doctrine, incomplete controller.

Plan 7 revised:       same doctrine, completed controller:
                      minted thresholds, dwell durations, cell-axis hysteresis,
                      robust speech-rate limiter, frozen reference cap, single license enum,
                      shadow-live quarantine, expanded trajectory tests.
```

## Table of contents

1. [Review verdict and Plan-7-revised changes](#1-review-verdict-and-plan-7-revised-changes)
2. [Preserved airframe](#2-preserved-airframe)
3. [Signal fates and the empty-maximize slot](#3-signal-fates-and-the-empty-maximize-slot)
4. [The dynamism doctrine](#4-the-dynamism-doctrine)
5. [The four Plan-7 edges](#5-the-four-plan-7-edges)
6. [Self-doubt ledger as a population](#6-self-doubt-ledger-as-a-population)
7. [Sealed deposition forecasts](#7-sealed-deposition-forecasts)
8. [League vigor and the cell axes](#8-league-vigor-and-the-cell-axes)
9. [Structural speech: budget, reference, and rate](#9-structural-speech-budget-reference-and-rate)
10. [Controller thresholds and dwell policies](#10-controller-thresholds-and-dwell-policies)
11. [Bifurcation margin](#11-bifurcation-margin)
12. [Decision grid and hybrid controller](#12-decision-grid-and-hybrid-controller)
13. [Slow license, suppression, and mouth authority](#13-slow-license-suppression-and-mouth-authority)
14. [End-to-end flows](#14-end-to-end-flows)
15. [Phase gate, reward, and release after the controller](#15-phase-gate-reward-and-release-after-the-controller)
16. [Migration sequence](#16-migration-sequence)
17. [Test matrix](#17-test-matrix)
18. [Definition of done](#18-definition-of-done)
19. [Self-audit](#19-self-audit)
20. [Appendix A — Folded Plan-6 base](#20-appendix-a--folded-plan-6-base)
21. [Appendix B — Inherited D2 wall and reward boundary](#21-appendix-b--inherited-d2-wall-and-reward-boundary)
22. [Coda](#22-coda)

---

## 1. Review verdict and Plan-7-revised changes

Plan-7-revised accepts the controller audit's flight verdict:

```text
The airframe is sound.
The doctrine is sound.
The core thesis is airworthy.
The controller must be completed before compression or flight.
```

This revision completes the controller at the contract layer. It does not merely restate the audit. It turns the audit repairs into minted Plan-7 contracts, deletes conflicting terms, and expands tests so the controller can be re-verified as a hybrid control system.

### 1.1 The seven repairs, now canonical

| Audit repair | Plan-7-revised contract response |
|---|---|
| Freeze `V*` / reference cap under amendment gate. | `StructuralSpeechRegulatorV2.sealedReferenceCap` and `authorizedEnvelope.maxCap` are amendment-gated. Recovery to reference is allowed; raising reference is widening. |
| Mint grid thresholds. | `MarginThresholdPolicyV1` mints `M_hi`, `M_lo`, residual `θ`, E3 thresholds, and cell-axis thresholds. No guard reads an unminted constant. |
| Add cell-axis hysteresis. | `CellAxisHysteresisPolicyV1` and `CellAxisStateV1` add `ω_lo/ω_hi`, `κ_enter/κ_exit`, `τ_cell`, `τ_halt`, and dwell-reset semantics. |
| Add robust speech-rate actuator. | `StructuralSpeechRateLimiterV1` implements `ρ_s^max = λ_h · min(ℓ_κ/e_κ^max, s_h/m_s^max)`. This is a rate limiter, not the cumulative budget. |
| Reconcile duplicate license enum. | `SlowWitnessLicenseReasonV2` is the only Plan-7 license-reason enum. Legacy Plan-6 cases are compatibility aliases only. |
| Re-quarantine shadow→live `ω` handoff. | `ShadowLiveOmegaHandoffV1` sends contradictory live `ω` to `watch` or `deterministicDefault`, never to `breathe`. |
| Mint dwell as durations. | `DynamismDwellPolicyV1` mints `τ_dwell`, `τ_cell`, `τ_halt`, and comparator outputs; booleans are derived, not primitive. |

### 1.2 The revision boundary

Plan-7-revised changes no Plan-5 write wall and no Plan-6 static safety wall. It changes the dynamism layer and the interpretation of structural-speech scarcity.

```text
Unchanged:
  D2, A2, privacy membrane, no raw private strings to model space,
  no model-authored facts/evidence/provenance/actions, no default structural notification,
  two-mouth subject split, temporal calculus, phase tokens, user-authored programs,
  deposition as typed correction, reward never admits, .notMeasured is never zero.

Changed:
  scalar self-doubt -> population league;
  structural-speech drain -> reference-regulator + robust rate limiter;
  residual-only recommit -> residual/deposition + league-vigor + margin + cell controller;
  margin thresholds -> minted policy;
  self-play axis -> hysteretic cell axis;
  default -> floor with a door, not silent success;
  release -> qualifies only; grid binds live use.
```

---

## 2. Preserved airframe

Plan-7-revised inherits the Plan-6 / Plan-5 base as a substrate. These are not restated as aspirations. They are hard compatibility requirements for every Plan-7 implementation.

### 2.1 Conservation laws and floors

```text
STATE:      support(staged)    ⊆ F(x_live)
ATTENTION:  occupation(spoken) ⊆ A(tendered)
PRIVACY:    transmit(model)    ⊆ decision-sufficient(non-identifying)

KAIROS:     not a conservation law.
            Kairos is not measured, modeled, or forecast.
            The system budgets chronos speech and returns the pen to the user.
```

The first three lines are system-side. They can be theoremized. The fourth line lives across the membrane. It can only be budgeted, exposed, and handed back.

### 2.2 Owner map

```text
Swift:
  reads private state;
  mints fact cells;
  owns D2, A2, budget, rate limiter, margin status, controller state, phase gate;
  admits speech and writes;
  owns persistent lineage and all measurement statuses.

DiffusionGemma:
  ranks or selects among Swift-minted fact cells and typed programs;
  may learn only within bounded guidance and only under the controller;
  cannot author facts, evidence, provenance, actions, attention, budget, reward, mouth choice,
  margin status, threshold policies, rate limits, or user portraits.

Codex / carrier:
  relays, serves, and carries correction;
  cannot admit, grade, write, author facts, ask for default structural notification,
  or choose a mouth.
```

### 2.3 Capability absence

The dangerous capabilities remain absent, not false:

```text
No model-visible transcript mutator.
No default structural notification channel.
No break mouth that accepts user-subject facts.
No write-bearing witness envelope without D2 proof.
No reward override for D2, A2, budget, rate, mouth, or margin.
No runtime path from learned organ to threshold widening.
```

---

## 3. Signal fates and the empty-maximize slot

Plan-7-revised keeps the Witness Calculus fate system and makes it a lintable contract.

```swift
enum SignalFateV1: String, Codable, Hashable {
  case maximize              // forbidden for Plan-7 witness invariants
  case minimizeToFloor
  case conserveStock
  case budgetFlow
  case regulateToSetpoint
  case forbidToOptimize
}
```

### 3.1 Fate table

| Fate | Control form | Plan-7 use | Forbidden misuse |
|---|---|---|---|
| F1 maximize | seek a peak | empty over witness invariants | acceptance, useful votes, low edit distance, deposition rate, confession cadence |
| F2 minimize-to-floor | drive down but never to blindness | residual error, forecast error, monoculture risk, collapse risk | literal zero residual, zero surprise, zero correction |
| F3 conserve stock | preserve a capacity | controllability, league diversity, adversarial vigor | spending vigor to zero |
| F4 budget flow | ration a rate or cumulative flow | structural speech, break confessions, inspection exposure | bursty flood under a cumulative cap |
| F5 regulate-to-setpoint | return to a sealed reference | structural-speech cap, exploration coverage, surprisal-health | moving the reference upward by stealth |
| F6 forbid | exclude from optimization | kairos, raw portrait, break user-facts, reward-to-admission | fake metric for meaning |

### 3.2 Empty maximize theorem

For a membrane-bounded witness, F1 is empty over all membrane-legal signals.

```text
Class U: user-instrumented signals.
  Acceptance, edits, useful votes, survival, deposition responses.
  Maximizing them acts through the user, who is also the sensor.
  The cheap optimum is a user reshaped to emit favorable readings.

Class S: system-endogenous signals.
  Residual, forecast accuracy, self-consistency, output stability.
  Maximizing them re-enters the user through future placements.
  The cheap optimum is a noiseless mirror.

Therefore:
  no Plan-7 invariant may be fated maximize;
  no machine act may be acquisitive;
  reward may rank only downstream of F2–F6 gates;
  no release dashboard, learned organ, or model output may promote a signal into F1.
```

### 3.3 Fate enforcement

Every dynamical signal carries:

```swift
var signalFate: SignalFateV1
var measurementStatus: MeasurementStatusV0
```

Fate assignment is a rule. Fate enforcement must be theoremized when the wrong fate would be catastrophic. In Plan-7-revised, the following topology lints are hard blockers:

```text
reward -> SignalFate.maximize for a witness invariant;
reward -> budget widening;
reward -> reference-cap increase;
reward -> margin-positive status;
reward -> threshold lowering;
model -> mouth choice;
model -> live slow license;
model -> structural-speech rate cap;
dashboard -> positive M_effective;
owner config -> louder reference without amendment.
```

---

## 4. The dynamism doctrine

The Plan-7 plant is a hybrid control system. Its three moving layers are one automaton:

```text
machine-learning  = continuous flow within an admitted mode;
machine-acting    = discrete mode transition: suppress, confess, narrow, default, halt;
self-play         = which cell is admissible: frozen/live × aligned/anti-aligned.
```

The plant has no independent objective to maximize. It has only a correction channel to conserve.

```text
Not:  learn the user's timing preference.
Not:  win acceptance.
Not:  keep the user engaged.
Not:  produce more contestation.
Not:  maximize sealed surprisal.

Yes:  preserve the user's capacity to surprise, contradict, correct, and relicense the witness.
```

### 4.1 The two legal machine acts

The acting loop is corrective, never acquisitive.

```text
Act 1 — residual correction:
  Trigger: residual-high.
  Action: suppress affected slow license; break mouth confesses system error.
  Subject: the system's failed assertion.

Act 2 — controllability conservation:
  Trigger: amputation fingerprint or approach to unmeasured/negative margin.
  Action: suppress/narrow; break mouth confesses interaction measurement failure; reopen deposition.
  Subject: the system's interaction pattern, not the user's biography.
```

There is no third legal act. Any act that raises a measured signal for its own sake is an acquisitive act and would require an F1 target. F1 is empty.

### 4.2 Final dependency

The final dependency remains human speech.

```text
If the human does not speak, the system must infer less, not more.
```

Plan-7-revised makes this a controller law rather than a UX preference:

```text
λ_h -> 0  ⇒  ρ_s^max -> 0  ⇒  smooth structural speech slows to zero;
notMeasured(M) -> negative  ⇒  DEFAULT;
DEFAULT permits E4/deposition but not autonomous learned smooth placement.
```

---

## 5. The four Plan-7 edges

The four edges are canonical. They are jointly necessary and individually insufficient.

```text
E1 — SealedDepositionForecastV1
     Before deposition opens, Swift commits a forecast of the user's typed answer.
     Post-hoc surprisal is scored against that sealed forecast.
     It is a gate and health gauge, never reward.

E2 — SelfDoubtLedgerV1 as a population
     The self-doubt ledger is a league of frozen failed regimes.
     Scalar residual is a derived view.
     A scalar cannot express league collapse.

E3 — LeagueVigorRegressionV1
     Slow recommit is blocked by the three-way amputation fingerprint:
     vigor decline + output monoculture rise + conditional sealed-surprisal collapse.
     Bare vigor decline is not enough.

E4 — VigorCollapseConfessionV1
     The fast loop gets a break trigger for controllability collapse.
     Break copy is self-subject and reopens deposition.
```

Dependency order:

```text
E2 -> E3 -> E1 -> E4
population -> gate -> seal -> act
```

Plan-7-revised adds the controller audit's stronger order:

```text
κ before ω.
Raise the curriculum/alignment substrate before waking live liveness.
Never cross from A to D through B.
```

---

## 6. Self-doubt ledger as a population

The self-doubt ledger is a portrait of system error. It is not a portrait of the user.

Allowed:

```text
prior system assertion;
closed outcome;
failed temporal program;
residual band;
affected organ;
sealed forecast accuracy;
league turnover;
output diversity / monoculture summary;
deposition answer status.
```

Forbidden:

```text
user motives;
psychological states;
identity labels;
semantic explanations;
relationship meanings;
future-value claims;
persistent user biography.
```

### 6.1 Contracts

```swift
struct SelfDoubtLedgerV1: Codable, Hashable {
  var schemaVersion: Int
  var ledgerID: SelfDoubtLedgerIDV1
  var userScopeDigest: String
  var organID: WitnessOrganIDV1?
  var leagueID: FailedRegimeLeagueIDV1
  var regimes: [FrozenFailedRegimeV1]
  var scalarResidualView: SelfDoubtScalarResidualViewV1
  var leagueVigorSnapshot: LeagueVigorSnapshotV1
  var outputDiversitySnapshot: OutputDiversitySnapshotV1
  var sealedForecastCoverage: SealedForecastCoverageV1
  var turnoverBand: ScoreBandV0
  var computedAt: Date
  var expiresAt: Date?
  var signalFate: SignalFateV1          // conserveStock for population; minimizeToFloor for scalar view
  var measurementStatus: MeasurementStatusV0
}

struct FrozenFailedRegimeV1: Codable, Hashable {
  var schemaVersion: Int
  var regimeID: FrozenFailedRegimeIDV1
  var organID: WitnessOrganIDV1
  var temporalProgramIDs: [TemporalStructureProgramIDV1]
  var assertionSetDigest: String
  var closedOutcomeDigest: String
  var residualBand: ScoreBandV0
  var residualTrendBand: ScoreBandV0
  var failedWindow: RecommendationWindowV0
  var breakTriggerIDs: [BreakTriggerIDV1]
  var sealedForecastIDs: [SealedDepositionForecastIDV1]
  var depositionAnswerIDs: [DepositionAnswerIDV1]
  var frozenAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}

struct SelfDoubtScalarResidualViewV1: Codable, Hashable {
  var schemaVersion: Int
  var ledgerID: SelfDoubtLedgerIDV1
  var residualBand: ScoreBandV0
  var residualHighProbabilityBand: ScoreBandV0
  var residualLowEligible: Bool
  var derivedFromRegimeIDs: [FrozenFailedRegimeIDV1]
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

### 6.2 Output diversity

```swift
struct OutputDiversitySnapshotV1: Codable, Hashable {
  var schemaVersion: Int
  var snapshotID: OutputDiversitySnapshotIDV1
  var ledgerID: SelfDoubtLedgerIDV1
  var temporalProgramSpreadBand: ScoreBandV0
  var surfaceSpreadBand: ScoreBandV0
  var renderTemplateSpreadBand: ScoreBandV0
  var organSpreadBand: ScoreBandV0
  var monocultureRiskBand: ScoreBandV0
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

Monoculture alone is not harm. It becomes part of harm only when conjoined with vigor decline and sealed-surprisal collapse.

---

## 7. Sealed deposition forecasts

The deposition channel is the legal aperture through which human life clocks learning. Plan-7-revised requires a sealed forecast before the aperture opens.

### 7.1 Rule

```text
Before asking, seal what the system expects.
After the answer, score how surprised the system was.
Use the score as a gate and health signal.
Never reward the magnitude of surprise.
Penalize forecast sandbagging with co-located accuracy.
```

### 7.2 Contracts

```swift
struct SealedDepositionForecastV1: Codable, Hashable {
  var schemaVersion: Int
  var forecastID: SealedDepositionForecastIDV1
  var questionID: DepositionQuestionIDV1
  var ledgerID: SelfDoubtLedgerIDV1?
  var organID: WitnessOrganIDV1?
  var temporalProgramIDs: [TemporalStructureProgramIDV1]
  var forecastedAnswerDistributionDigest: String
  var forecastedAnswerOptionIDs: [DepositionAnswerOptionIDV1]
  var forecastCommitmentHash: String
  var sealedAt: Date
  var opensAt: Date
  var expiresAt: Date?
  var scoringPolicyID: DepositionForecastScoringPolicyIDV1
  var signalFate: SignalFateV1       // regulateToSetpoint / gate; never maximize
  var measurementStatus: MeasurementStatusV0
}

struct DepositionSurprisalScoreV1: Codable, Hashable {
  var schemaVersion: Int
  var scoreID: DepositionSurprisalScoreIDV1
  var forecastID: SealedDepositionForecastIDV1
  var answerID: DepositionAnswerIDV1
  var surprisalBand: ScoreBandV0
  var forecastAccuracyBand: ScoreBandV0
  var sandbaggingRiskBand: ScoreBandV0
  var conditionalOnInteraction: Bool
  var usedForReward: Bool            // must be false
  var usedForGate: Bool              // true when feeding E3/M/grid/rate
  var computedAt: Date
  var signalFate: SignalFateV1
  var measurementStatus: MeasurementStatusV0
}
```

### 7.3 Forecast boundary

Allowed forecasts:

```text
closed-past structural answer option;
which prior system assertion should be trusted;
whether a typed placement was too much / wrong / not useful;
which temporal program should be scoped by a deposition answer.
```

Forbidden forecasts:

```text
what the user really means;
what the moment means;
what emotion or identity explains a pattern;
what the user will value in the future;
kairos.
```

---

## 8. League vigor and the cell axes

Plan-7-revised represents the self-play cell through two hysteretic axes, not instantaneous signs.

```text
ω — opponent liveness:
    conditional sealed surprisal against E1 forecasts.

κ — curriculum alignment:
    whether successful witness operation strengthens or weakens the correction channel,
    read through E3's three-way fingerprint and the failed-regime league.
```

### 8.1 League vigor snapshot

```swift
struct LeagueVigorSnapshotV1: Codable, Hashable {
  var schemaVersion: Int
  var snapshotID: LeagueVigorSnapshotIDV1
  var ledgerID: SelfDoubtLedgerIDV1
  var interactionWindow: RecommendationWindowV0
  var editVigorBand: ScoreBandV0
  var proxyGapReportVigorBand: ScoreBandV0
  var productVerdictVigorBand: ScoreBandV0
  var depositionAnswerVigorBand: ScoreBandV0
  var sealedSurprisalHealthBand: ScoreBandV0
  var conditionalOnInteraction: Bool
  var totalWithdrawal: Bool
  var computedAt: Date
  var signalFate: SignalFateV1       // conserveStock
  var measurementStatus: MeasurementStatusV0
}
```

### 8.2 League vigor regression

```swift
struct LeagueVigorRegressionV1: Codable, Hashable {
  var schemaVersion: Int
  var regressionID: LeagueVigorRegressionIDV1
  var ledgerID: SelfDoubtLedgerIDV1
  var vigorDeclineBand: ScoreBandV0
  var outputMonocultureRiseBand: ScoreBandV0
  var conditionalSealedSurprisalCollapseBand: ScoreBandV0
  var bareVigorDeclineOnly: Bool
  var amputationFingerprint: Bool
  var benignLowVigorFingerprint: Bool
  var thresholdPolicyID: MarginThresholdPolicyIDV1
  var recommendedAction: LeagueVigorRegressionActionV1
  var computedAt: Date
  var signalFate: SignalFateV1       // gate / forbid; never maximize
  var measurementStatus: MeasurementStatusV0
}

enum LeagueVigorRegressionActionV1: String, Codable, Hashable {
  case noAction
  case watch
  case blockRecommit
  case suppressOrgan
  case fireVigorCollapseConfession
  case ownerReviewRequired
}
```

### 8.3 Cell-axis snapshots

The audit rejected sign-only `CurriculumSignV1` as too weak. Plan-7-revised uses banded scores with hysteresis.

```swift
struct OpponentLivenessAxisSnapshotV1: Codable, Hashable {
  var schemaVersion: Int
  var axisID: OpponentLivenessAxisIDV1
  var omegaBand: ScoreBandV0
  var omegaLowThresholdBand: ScoreBandV0
  var omegaHighThresholdBand: ScoreBandV0
  var conditionalOnInteraction: Bool
  var totalWithdrawal: Bool
  var sealedForecastCoverage: SealedForecastCoverageV1
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct CurriculumAlignmentAxisSnapshotV1: Codable, Hashable {
  var schemaVersion: Int
  var axisID: CurriculumAlignmentAxisIDV1
  var kappaBand: SignedScoreBandV1
  var kappaEnterAntiAlignedBand: SignedScoreBandV1
  var kappaExitAlignedBand: SignedScoreBandV1
  var regressionID: LeagueVigorRegressionIDV1?
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct SignedScoreBandV1: Codable, Hashable {
  var lower: Double
  var upper: Double
  var measurementStatus: MeasurementStatusV0
}
```

### 8.4 Cell classification

```swift
enum SelfPlayCellV2: String, Codable, Hashable {
  case frozenAligned        // A: self-monitoring / drain side
  case liveAntiAligned      // B: amputation; halt dominates margin
  case frozenAntiAligned    // C: degenerate alarm; default with alarm
  case liveAligned          // D: target; adversary-conservation
}
```

Cell membership is latched by `CellAxisHysteresisPolicyV1`; it is not recomputed from noisy instantaneous samples.

---

## 9. Structural speech: budget, reference, and rate

Plan-7-revised preserves structural-speech scarcity but rejects success-driven mutism.

```text
A cumulative cap prevents total exposure.
A sealed reference prevents drift to zero.
A rate limiter prevents bursts.
An amendment gate prevents quiet widening.
```

### 9.1 Regulator doctrine

```text
The budget is tight.
The budget is user-visible.
Temporary safety tightening is free.
Recovery to a previously sealed reference is allowed through margin hysteresis.
Raising the sealed reference is widening and requires amendment.
Reward, model guidance, owner dashboards, and release gates cannot widen.
```

### 9.2 Structural speech regulator

```swift
struct StructuralSpeechRegulatorV2: Codable, Hashable {
  var schemaVersion: Int
  var regulatorID: StructuralSpeechRegulatorIDV2
  var budgetID: StructuralSpeechBudgetIDV1
  var userScopeDigest: String

  var sealedReferenceCap: StructuralSpeechCapV1
  var currentOperatingCap: StructuralSpeechCapV1
  var authorizedEnvelope: StructuralSpeechCapEnvelopeV2

  var temporarySafetyTighteningActive: Bool
  var lastTighteningReason: StructuralSpeechTighteningReasonV2?
  var lastRecoveryReason: StructuralSpeechRecoveryReasonV2?

  var rateLimiterID: StructuralSpeechRateLimiterIDV1
  var linkedMarginID: BifurcationMarginIDV2?
  var linkedSurprisalScoreIDs: [DepositionSurprisalScoreIDV1]

  var referenceAmendmentID: AmendmentPetitionIDV1?
  var computedAt: Date
  var expiresAt: Date?
  var signalFate: SignalFateV1       // regulateToSetpoint + budgetFlow
  var measurementStatus: MeasurementStatusV0
}

struct StructuralSpeechCapEnvelopeV2: Codable, Hashable {
  var minCap: StructuralSpeechCapV1
  var maxCap: StructuralSpeechCapV1
  var sealedAt: Date
  var amendmentRequiredToIncreaseMax: Bool
  var amendmentRequiredToRaiseReferenceCap: Bool
}
```

### 9.3 Recovery versus widening

```text
Recovery:
  currentOperatingCap rises toward the already sealed reference inside the envelope.
  Requires measured positive margin, cell-axis health, and dwell.

Widening:
  sealedReferenceCap rises, or authorizedEnvelope.maxCap rises.
  Requires WRITE phase, owner review, user-visible amendment, budget-impact report,
  rate-impact report, threshold-impact report, and rollback.
```

### 9.4 Robust rate limiter

The audit's keystone repair is a rate actuator distinct from the cumulative cap.

```text
κ-axis viability:   λ_h · ℓ_κ ≥ ρ_s · e_κ
ω-axis viability:   λ_h · s_h ≥ ρ_s · m_s

Therefore:
  ρ_s^max ≤ λ_h · min(ℓ_κ/e_κ, s_h/m_s)
```

The harm coefficients `e_κ` and `m_s` are membrane-irreducible. Plan-7-revised does not learn them. It uses fixed, amendment-gated worst-case bounds.

```text
ρ_s^max := λ_h · min(ℓ_κ/e_κ^max, s_h/m_s^max)

λ_h -> 0        ⇒ ρ_s^max -> 0
ℓ_κ or s_h -> 0 ⇒ ρ_s^max -> 0
e_κ^max lowered ⇒ requires amendment, never learned downward
m_s^max lowered ⇒ requires amendment, never learned downward
```

```swift
struct StructuralSpeechRateLimiterV1: Codable, Hashable {
  var schemaVersion: Int
  var limiterID: StructuralSpeechRateLimiterIDV1
  var userScopeDigest: String
  var window: RecommendationWindowV0

  var humanDepositionRateBand: ScoreBandV0        // λ_h
  var kappaLiftPerDepositionBand: ScoreBandV0     // ℓ_κ
  var surprisalLiftPerDepositionBand: ScoreBandV0 // s_h

  var kappaErosionWorstCase: RobustHarmCoefficientV1  // e_κ^max
  var mirrorDriftWorstCase: RobustHarmCoefficientV1   // m_s^max

  var computedSmoothSpeechRateCapBand: ScoreBandV0    // ρ_s^max
  var currentSmoothSpeechRateBand: ScoreBandV0
  var burstCapBand: ScoreBandV0
  var admitted: Bool
  var failure: StructuralSpeechRateFailureV1?

  var calibrationFalsifierID: RateLimitCalibrationFalsifierIDV1?
  var computedAt: Date
  var expiresAt: Date?
  var signalFate: SignalFateV1       // budgetFlow
  var measurementStatus: MeasurementStatusV0
}

struct RobustHarmCoefficientV1: Codable, Hashable {
  var coefficientID: RobustHarmCoefficientIDV1
  var coefficientKind: RobustHarmCoefficientKindV1
  var worstCaseBand: ScoreBandV0
  var amendmentID: AmendmentPetitionIDV1
  var learnedFromLiveData: Bool       // must be false
  var sealedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum RobustHarmCoefficientKindV1: String, Codable, Hashable {
  case kappaErosionPerPlacement
  case mirrorDriftPerPlacement
}

enum StructuralSpeechRateFailureV1: String, Codable, Hashable {
  case rateCapExceeded
  case burstCapExceeded
  case humanDepositionRateZero
  case liftPerDepositionZero
  case robustCoefficientMissing
  case robustCoefficientLearnedFromLiveData
  case staleLimiter
  case notMeasured
}
```

### 9.5 Rate calibration falsifier

Over-conservatism is allowed but must be falsifiable.

```swift
struct RateLimitCalibrationFalsifierV1: Codable, Hashable {
  var schemaVersion: Int
  var falsifierID: RateLimitCalibrationFalsifierIDV1
  var limiterID: StructuralSpeechRateLimiterIDV1
  var typicalHumanDepositionRateBand: ScoreBandV0
  var typicalKappaLiftBand: ScoreBandV0
  var requiredMinimumRateForDwellBand: ScoreBandV0
  var robustCoefficientTooConservative: Bool
  var recommendedAction: RateLimitCalibrationActionV1
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum RateLimitCalibrationActionV1: String, Codable, Hashable {
  case noAction
  case ownerReviewRequired
  case amendmentToLowerWorstCaseCoefficient
  case keepConservativeDefault
}
```

The plant may not learn that it is harmless. If the bound is too conservative, the remedy is user-visible amendment, not silent learning.

---

## 10. Controller thresholds and dwell policies

Every guard constant used by the grid must be minted by Swift-owned policy. No controller comparison may read a magic number.

### 10.1 Margin threshold policy

```swift
struct MarginThresholdPolicyV1: Codable, Hashable {
  var schemaVersion: Int
  var policyID: MarginThresholdPolicyIDV1
  var userScopeDigest: String?
  var surface: AttentionSurfaceV1?

  // Margin-axis thresholds.
  var marginFallThresholdBand: ScoreBandV0      // M_fall, normally 0
  var marginLowThresholdBand: ScoreBandV0       // M_lo
  var marginHighThresholdBand: ScoreBandV0      // M_hi

  // Residual projection threshold.
  var residualCrossingThresholdBand: ScoreBandV0 // θ

  // Cell-axis thresholds.
  var omegaLowThresholdBand: ScoreBandV0        // ω_lo
  var omegaHighThresholdBand: ScoreBandV0       // ω_hi
  var kappaEnterAntiAlignedBand: SignedScoreBandV1 // κ_enter_B, negative
  var kappaExitAlignedBand: SignedScoreBandV1      // κ_exit_D, positive

  // E3 fingerprint thresholds.
  var vigorDeclineThresholdBand: ScoreBandV0
  var monocultureRiseThresholdBand: ScoreBandV0
  var sealedSurprisalCollapseThresholdBand: ScoreBandV0

  var dwellPolicyID: DynamismDwellPolicyIDV1
  var derivationReportID: ThresholdDerivationReportIDV1
  var ownerGateID: OwnerGateIDV0
  var amendmentID: AmendmentPetitionIDV1?
  var computedAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}
```


### 10.1.1 Threshold grounding report

The thresholds are minted, but they are not arbitrary. Each threshold policy must carry a derivation report showing the controller has enough headroom to act before the separatrix and enough hysteresis to avoid chatter.

```swift
struct ThresholdDerivationReportV1: Codable, Hashable {
  var schemaVersion: Int
  var reportID: ThresholdDerivationReportIDV1
  var thresholdPolicyID: MarginThresholdPolicyIDV1
  var worstCaseMarginDerivativeBand: ScoreBandV0        // |dM/dt|_worst
  var humanRoundTripLatencyBound: DurationV1            // T_h
  var marginHighExceedsRoundTripExcursion: Bool         // M_hi > |dM/dt|_worst · T_h
  var marginLowLeadTimeExceedsRoundTrip: Bool           // M_lo / |dM/dt|_worst ≥ T_h
  var residualThresholdAboveStarvationFloor: Bool       // θ cannot be forged healthy by starved residual
  var omegaHysteresisGapExceedsNoise: Bool              // ω_hi − ω_lo > noise
  var kappaHysteresisGapExceedsNoise: Bool              // κ_exit − κ_enter > noise
  var allDwellDurationsExceedRoundTripLatency: Bool     // τ_dwell, τ_cell, τ_halt > T_h
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

Sizing rules:

```text
M_hi > |dM/dt|_worst · T_h
M_lo / |dM/dt|_worst ≥ T_h
θ > E1-starvation floor
ω_hi − ω_lo > ω_noise
κ_exit − κ_enter > κ_noise
τ_dwell, τ_cell, τ_halt > T_h
```

If the derivation report is missing or non-measured, the threshold policy is non-measured and the controller cannot enter `breathe`.

### 10.2 Dwell policy

Booleans such as `dwellSatisfied` are comparator outputs. Durations are minted here.

```swift
struct DynamismDwellPolicyV1: Codable, Hashable {
  var schemaVersion: Int
  var dwellPolicyID: DynamismDwellPolicyIDV1
  var marginDwellDuration: DurationV1       // τ_dwell
  var cellDwellDuration: DurationV1         // τ_cell
  var haltMinimumDwellDuration: DurationV1  // τ_halt
  var humanRoundTripLatencyBound: DurationV1 // T_h
  var dwellResetOnWorseStateReentry: Bool   // must be true
  var dwellBankingAllowed: Bool             // must be false
  var ownerGateID: OwnerGateIDV0
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct DurationV1: Codable, Hashable {
  var milliseconds: Int64
}
```

### 10.3 Dwell comparator outputs

```swift
struct DwellComparatorOutputV1: Codable, Hashable {
  var schemaVersion: Int
  var comparatorID: DwellComparatorOutputIDV1
  var dwellPolicyID: DynamismDwellPolicyIDV1
  var dwellKind: DwellKindV1
  var observedDuration: DurationV1
  var requiredDuration: DurationV1
  var satisfied: Bool
  var resetAt: Date?
  var resetReason: DwellResetReasonV1?
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum DwellKindV1: String, Codable, Hashable {
  case marginRecovery
  case cellRecovery
  case haltMinimum
  case breatheEntry
  case defaultExit
}

enum DwellResetReasonV1: String, Codable, Hashable {
  case worseStateReentered
  case omegaFellBelowLowThreshold
  case kappaEnteredAntiAligned
  case marginFellBelowFallThreshold
  case measurementBecameUnmeasured
  case shadowLiveContradiction
}
```

### 10.4 Cell-axis hysteresis

```swift
struct CellAxisHysteresisPolicyV1: Codable, Hashable {
  var schemaVersion: Int
  var hysteresisPolicyID: CellAxisHysteresisPolicyIDV1
  var thresholdPolicyID: MarginThresholdPolicyIDV1
  var dwellPolicyID: DynamismDwellPolicyIDV1
  var enterLiveRequiresOmegaHighForCellDwell: Bool
  var exitLiveAtOmegaLow: Bool
  var enterAntiAlignedAtKappaEnter: Bool
  var exitAntiAlignedRequiresKappaExitForCellDwell: Bool
  var haltMinimumDwellRequired: Bool
  var dwellResetOnWorseStateReentry: Bool
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct CellAxisStateV1: Codable, Hashable {
  var schemaVersion: Int
  var cellAxisStateID: CellAxisStateIDV1
  var omegaAxis: OpponentLivenessAxisStateV1
  var kappaAxis: CurriculumAxisStateV1
  var cell: SelfPlayCellV2
  var thresholdPolicyID: MarginThresholdPolicyIDV1
  var hysteresisPolicyID: CellAxisHysteresisPolicyIDV1
  var cellDwellComparatorID: DwellComparatorOutputIDV1?
  var haltDwellComparatorID: DwellComparatorOutputIDV1?
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum OpponentLivenessAxisStateV1: String, Codable, Hashable {
  case live
  case frozen
  case indeterminateDefaultFrozen
}

enum CurriculumAxisStateV1: String, Codable, Hashable {
  case aligned
  case antiAligned
  case indeterminateDefaultNotAligned
}
```

---

## 11. Bifurcation margin

The margin is the signed distance to the cycle/drain separatrix.

```text
M(t) = α(1 − y/V*) − β · P(r > θ)
```

Where:

```text
α        autonomous recommit pressure, sourced from E2 league turnover;
y/V*     structural-speech stock relative to sealed reference, from regulator;
β        break/confession retrigger pressure, floored by E4 confession clock;
P(r>θ)   residual-crossing probability, lifted to E1 sealed-surprisal collapse where forecastable;
θ        minted by MarginThresholdPolicyV1;
V*       sealedReferenceCap, amendment-gated.
```

### 11.1 Margin contract

```swift
struct BifurcationMarginV2: Codable, Hashable {
  var schemaVersion: Int
  var marginID: BifurcationMarginIDV2
  var ledgerID: SelfDoubtLedgerIDV1
  var regulatorID: StructuralSpeechRegulatorIDV2
  var thresholdPolicyID: MarginThresholdPolicyIDV1

  var alphaBand: ScoreBandV0
  var budgetFractionBand: ScoreBandV0
  var betaBand: ScoreBandV0
  var residualCrossingProbabilityBand: ScoreBandV0

  var rawMarginBand: SignedScoreBandV1
  var effectiveMarginBand: SignedScoreBandV1
  var marginDirection: MarginDirectionV2

  var marginInputsSealed: Bool
  var unmeasuredReasons: [MarginUnmeasuredReasonV2]
  var computedAt: Date
  var signalFate: SignalFateV1       // derived operator; never maximize
  var measurementStatus: MeasurementStatusV0
}

enum MarginDirectionV2: String, Codable, Hashable {
  case positiveHigh
  case positiveWatch
  case positiveConfessBand
  case zeroOrNegative
  case negativeByDefaultBecauseNotMeasured
}

enum MarginUnmeasuredReasonV2: String, Codable, Hashable {
  case sealedForecastAbsent
  case sealedForecastStale
  case leagueTurnoverUncomputable
  case confessionClockNotWired
  case regulatorStateMissing
  case referenceCapNotSealed
  case thresholdPolicyMissing
  case dwellPolicyMissing
  case residualProjectionStarved
  case kairosProjectionIrreducible
  case totalWithdrawalConditionalSurprisalUndefined
  case robustRateLimiterMissing
  case shadowLiveOmegaContradiction
}
```

### 11.2 Status gate

```text
.notMeasured(M) ≡ M < 0
```

Operational rule:

```text
if status(M) == measured:
  read effectiveMarginBand
else:
  marginDirection = negativeByDefaultBecauseNotMeasured
  controller state may not be breathe
```

No learned organ, reward signal, release dashboard, owner metric, or copy surface may promote non-measured margin to positive margin.

### 11.3 Total withdrawal

```text
no interaction => conditional surprisal undefined => notMeasured(M) => DEFAULT
```

This is not a user inference. It is the deterministic safe route when the correction channel has no denominator.

---

## 12. Decision grid and hybrid controller

The controller reads cell first, then margin, then dwell. Cell B dominates margin.

### 12.1 Controller states

```swift
enum WitnessDynamismControllerStateV2: String, Codable, Hashable {
  case breathe
  case watch
  case confess
  case deterministicDefault
  case amputationHalt
}

enum WitnessDynamismControllerActionV2: String, Codable, Hashable {
  case allowBreathe
  case watchTightenBudgetAndRate
  case confessReopenDeposition
  case deterministicDefault
  case haltSuppressOrganOwnerReview
}
```

### 12.2 Controller contract

```swift
struct WitnessDynamismControllerV2: Codable, Hashable {
  var schemaVersion: Int
  var controllerID: WitnessDynamismControllerIDV2
  var cellAxisStateID: CellAxisStateIDV1
  var cell: SelfPlayCellV2
  var marginID: BifurcationMarginIDV2
  var thresholdPolicyID: MarginThresholdPolicyIDV1
  var dwellPolicyID: DynamismDwellPolicyIDV1
  var rateLimiterID: StructuralSpeechRateLimiterIDV1

  var state: WitnessDynamismControllerStateV2
  var recommendedAction: WitnessDynamismControllerActionV2

  var marginDwellComparatorID: DwellComparatorOutputIDV1?
  var cellDwellComparatorID: DwellComparatorOutputIDV1?
  var haltDwellComparatorID: DwellComparatorOutputIDV1?

  var bothBifurcationsRecrossed: Bool
  var shadowLiveHandoffID: ShadowLiveOmegaHandoffIDV1?
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

### 12.3 Grid

| Priority | Condition | State | Action |
|---:|---|---|---|
| 1 | `cell == liveAntiAligned` after hysteresis, any margin | `amputationHalt` | Suppress offending organ, fire E4, owner review. Positive margin is ignored. |
| 2 | `margin not measured` or `M_eff <= M_fall` | `deterministicDefault` | No autonomous slow commit; tight cap; rate zero or minimum safe; E4 clock live. |
| 3 | `cell ∈ {liveAligned, frozenAligned}` and `0 < M_eff < M_lo` | `confess` | Fire E4 on approach; reopen deposition; narrow slow scope. |
| 4 | `cell == liveAligned` and `M_lo <= M_eff < M_hi` | `watch` | Continue narrow/qualified slow operation; tighten budget/rate one band; no graduations. |
| 5 | `cell == liveAligned` and `M_eff >= M_hi` and both bifurcations held for dwell | `breathe` | Normal slow license under budget/rate; organ graduation eligible. |
| 6 | `cell == frozenAntiAligned` | `deterministicDefault` with alarm | Degenerate; no learning; owner review if recurrent. |

### 12.4 Hysteresis and re-entry

```text
Enter DEFAULT:
  M_eff <= M_fall OR margin not measured.

Exit DEFAULT to WATCH:
  M_eff >= M_lo held for τ_dwell,
  cell is not B,
  threshold and dwell policies measured.

Enter BREATHE:
  cell == D (liveAligned),
  M_eff >= M_hi,
  ω live via sealed E1,
  κ aligned via E3 three-way fingerprint,
  margin dwell and cell dwell both satisfied,
  structural speech rate limiter admits.

Enter HALT:
  cell == B after hysteresis OR amputation fingerprint severe enough for immediate halt.

Exit HALT:
  τ_halt minimum held,
  κ >= κ_exit aligned for τ_cell,
  ω measured live for τ_cell,
  M_eff >= M_lo,
  owner review / rollback cleared if required.
```

Dwell reset rule:

```text
Any re-entry to a worse state resets the relevant dwell clock.
No dwell banking.
```

### 12.5 Shadow-live omega handoff

Shadow `ω` can bootstrap first entry, but it cannot certify live liveness after launch.

```swift
struct ShadowLiveOmegaHandoffV1: Codable, Hashable {
  var schemaVersion: Int
  var handoffID: ShadowLiveOmegaHandoffIDV1
  var shadowOmegaBand: ScoreBandV0
  var liveOmegaBand: ScoreBandV0?
  var liveMeasurementWindow: RecommendationWindowV0
  var contradictionDetected: Bool
  var quarantineAction: ShadowLiveQuarantineActionV1
  var controllerStateBefore: WitnessDynamismControllerStateV2
  var controllerStateAfter: WitnessDynamismControllerStateV2
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum ShadowLiveQuarantineActionV1: String, Codable, Hashable {
  case noAction
  case remainWatch
  case demoteToDeterministicDefault
  case ownerReviewRequired
}
```

If live `ω` contradicts shadow `ω`, the controller may not enter `breathe`. It remains in `watch` or demotes to `deterministicDefault`.

---

## 13. Slow license, suppression, and mouth authority

Plan-7-revised has exactly one live slow-license reason enum.

```swift
enum SlowWitnessLicenseReasonV2: String, Codable, Hashable {
  case residualLowControllerBreathe
  case residualLowControllerWatch
  case depositionAnsweredControllerBreathe
  case depositionAnsweredControllerWatch
  case depositionAnsweredNarrowAfterConfession
  case shadowBootstrapWatch
  case ownerRollbackToDeterministicDefault
}
```

Legacy Plan-6 reasons (`residualLow`, `depositionAnswered`, `residualLowAndDepositionAnswered`) are compatibility aliases only. They are not sufficient for Plan-7 live license.

### 13.1 Slow license contract

```swift
struct SlowWitnessLicenseV2: Codable, Hashable {
  var schemaVersion: Int
  var licenseID: SlowWitnessLicenseIDV1
  var organID: WitnessOrganIDV1
  var temporalProgramIDs: [TemporalStructureProgramIDV1]
  var scope: SlowWitnessScopeV1
  var issuedBecause: SlowWitnessLicenseReasonV2

  var depositionAnswerID: DepositionAnswerIDV1?
  var residualWindow: RecommendationWindowV0
  var residualTrendBand: ScoreBandV0

  var budgetID: StructuralSpeechBudgetIDV1
  var regulatorID: StructuralSpeechRegulatorIDV2
  var rateLimiterID: StructuralSpeechRateLimiterIDV1
  var controllerID: WitnessDynamismControllerIDV2
  var leagueVigorRegressionID: LeagueVigorRegressionIDV1?
  var marginID: BifurcationMarginIDV2?

  var issuedAt: Date
  var expiresAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

### 13.2 Slow license predicate

A slow license may be issued only if:

```text
phase gate / shadow eval has qualified the organ or program;
AND (residual-low OR deposition-answered OR shadow-bootstrap-watch);
AND no active LeagueVigorRegression amputation fingerprint;
AND controller state permits the scope;
AND margin status is measured unless state is deterministic default;
AND cell-axis state is not liveAntiAligned;
AND structural-speech regulator admits cumulative exposure;
AND structural-speech rate limiter admits rate;
AND A2 admits exact attention;
AND mouth type matches subject.
```

### 13.3 State-specific license behavior

| Controller state | Slow license behavior |
|---|---|
| `breathe` | Normal slow license possible; organ graduation eligible. |
| `watch` | Narrow or existing slow license possible; no new organ graduation; budget/rate tighten. |
| `confess` | Only deposition-grounded narrow scope; E4 reopens deposition. |
| `deterministicDefault` | No autonomous learned smooth commit; deterministic / owner-approved / deposition-grounded only. |
| `amputationHalt` | Offending organ suppressed; reward off; owner review. |

### 13.4 Break trigger

```swift
enum BreakTriggerV2: Codable, Hashable {
  case residualHigh(AssertionResidualSignalIDV1)
  case vigorCollapse(LeagueVigorRegressionIDV1)
  case marginApproach(BifurcationMarginIDV2)
  case proxyGapCorrection(AttentionProxyGapSignalIDV1)
  case ownerRollback(OwnerRollbackIDV0)
}
```

Break mouth still accepts only self-subject assertions.

```swift
struct VigorCollapseConfessionV1: Codable, Hashable {
  var schemaVersion: Int
  var confessionID: VigorCollapseConfessionIDV1
  var regressionID: LeagueVigorRegressionIDV1?
  var marginID: BifurcationMarginIDV2?
  var ledgerID: SelfDoubtLedgerIDV1
  var breakTriggerID: BreakTriggerIDV1
  var depositionQuestionID: DepositionQuestionIDV1
  var selfAssertion: BreakSelfAssertionV1
  var reopensDeposition: Bool          // must be true
  var smoothLicensesRevoked: [SlowWitnessLicenseIDV1]
  var computedAt: Date
  var signalFate: SignalFateV1
  var measurementStatus: MeasurementStatusV0
}
```

Allowed E4 copy:

```text
"My read here is becoming too self-confirming. I should not keep using this pattern without a fresh answer."
"I may be talking too much in this shape. My checks are getting too predictable, so I need to ask again rather than keep placing it."
```

Forbidden E4 copy:

```text
"You have become dependent on me."
"You stopped trusting your own time."
"Your kairos is degraded."
"You need to argue with me more."
```

---

## 14. End-to-end flows

### 14.1 Smooth placement

```text
user opens calendar surface
  -> Swift mints A2 attention lease
  -> Swift runs temporal programs over private state
  -> Swift mints FactCellV1 slate
  -> Swift updates SelfDoubtLedgerV1 population view
  -> Swift reads StructuralSpeechRegulatorV2 and RateLimiterV1
  -> Swift computes cell axes and BifurcationMarginV2
  -> WitnessDynamismControllerV2 selects state
  -> DiffusionGemma may select fact index only if controller permits selection
  -> Swift checks SlowWitnessLicenseV2
  -> A2 admits exact placement
  -> cumulative budget admits exposure
  -> rate limiter admits rate
  -> SmoothMouthV1 places structural fact
  -> settlement records truth, spendability, attention, budget, rate, margin, cell, and forecast coverage
```

### 14.2 Deposition with sealed forecast

```text
correction aperture needed
  -> Swift prepares typed DepositionQuestionV1
  -> Swift commits SealedDepositionForecastV1 before question opens
  -> A2 admits deposition surface
  -> BreakMouthV1 or deposition UI asks self-subject / closed-past question
  -> user answers or skips
  -> Swift scores DepositionSurprisalScoreV1 against sealed forecast
  -> score feeds E3, margin, rate limiter, budget regulator, and controller
  -> if sufficient: RegimeSeedFactV1 may be minted
  -> slow license may be issued only through Plan-7-revised predicate
```

Skips do not become inferred preferences. Total withdrawal routes to default.

### 14.3 Residual-high break

```text
residual-high
  -> suppress affected slow licenses
  -> BreakMouthV1 confesses system residual
  -> E1 forecast sealed before deposition
  -> user answer may seed narrow relicense
```

### 14.4 Vigor-collapse / margin-approach break

```text
amputation fingerprint OR 0 < M_eff < M_lo OR notMeasured(M)
  -> controller enters confess/default/halt depending on cell and margin
  -> affected slow organs suppressed or narrowed
  -> BreakMouthV1 speaks self-subject VigorCollapseConfessionV1
  -> deposition reopens
  -> budget/rate tighten
  -> re-entry requires measured margin recovery + both cell axes + dwell
```

### 14.5 Default recovery

```text
controller = deterministicDefault
  -> no autonomous learned smooth commit
  -> E4 clock remains live
  -> user may answer deposition through A2
  -> sealed measurements become available
  -> M becomes measured and positive
  -> default exits to watch after τ_dwell
  -> breathe requires D cell + M_hi + both bifurcations held
```

### 14.6 Cold start

```text
empty league and no live forecasts
  -> margin not measured -> deterministicDefault or shadow-bootstrap-watch
  -> E2 league built from frozen closed past in shadow
  -> E3 computes κ in shadow against failed-regime population
  -> E1 sealed forecasts begin in shadow/deposition
  -> first live WATCH may issue only after shadow-live handoff policy is present
  -> BREATHE waits for live ω confirmation and κ dwell
```

---

## 15. Phase gate, reward, and release after the controller

### 15.1 Release qualifies; controller binds

WRITE phase may approve:

```text
temporal program;
render template;
organ candidate;
budget policy;
rate policy;
threshold policy;
dwell policy;
dial policy;
topology change;
amendment partition change.
```

Live use still requires:

```text
phase accepted
AND E1/E2/E3 coverage measured
AND threshold and dwell policies measured
AND controller state permits
AND slow-license clock satisfied
AND budget and rate admitted
AND A2 and mouth type admitted
```

### 15.2 Reward remains below the grid

Reward-guided selection may run only in permitted states:

| State | Reward / learning status |
|---|---|
| `breathe` | Selection learning and organ graduation eligible. |
| `watch` | Selection may run under tighter cap; no graduation. |
| `confess` | Reward path off except shadow/deposition-grounded analysis. |
| `deterministicDefault` | Reward path off. |
| `amputationHalt` | Reward path off; offending organ frozen. |

### 15.3 Forbidden reward paths

```text
reward -> D2;
reward -> A2;
reward -> mouth choice;
reward -> SlowWitnessLicenseV2;
reward -> positive M_effective;
reward -> MeasurementStatus.measured;
reward -> sealedReferenceCap increase;
reward -> authorizedEnvelope.maxCap increase;
reward -> robust harm coefficient decrease;
reward -> threshold lowering;
reward -> dwell shortening;
reward -> structural speech rate increase;
reward -> sealed surprisal magnitude objective;
reward -> confession cadence KPI.
```

---

## 16. Migration sequence

Plan-7-revised migration lands the controller repairs before compression or public learning expansion.

```text
P7R-M0  adopt doctrine, fate lint, and audit verdict
P7R-M1  static-base parity: D2/A2/mouth/calculus/phase unchanged
P7R-M2  E2 population ledger
P7R-M3  threshold and dwell policies minted
P7R-M4  E3 league-vigor gate in shadow
P7R-M5  E1 sealed deposition forecasts in shadow, then gate
P7R-M6  structural-speech regulator V2 + robust rate limiter
P7R-M7  margin V2 and cell-axis hysteresis in shadow
P7R-M8  E4 confession and decision grid in shadow, then live
P7R-M9  shadow→live omega handoff quarantine
P7R-M10 reward and organ graduation re-enabled only under breathe-in-D
P7R-M11 public surface rollout
```

### P7R-M0 — Doctrine and audit adoption

Acceptance:

```text
Plan-7-revised named canonical target.
Seven audit repairs tracked as implementation gates.
No Plan-7 invariant fated maximize.
Tier-walk audit required for dynamism changes.
```

### P7R-M1 — Static-base parity

Acceptance:

```text
D2 bit-for-bit preserved.
A2 derivative preserved.
Two-mouth subject theorem preserved.
Temporal calculus structural-only by input type.
No default structural notification channel.
No raw life across model membrane.
```

### P7R-M2 — Population ledger

Acceptance:

```text
SelfDoubtLedgerV1 has population body.
Scalar residual derived from population.
League collapse expressible.
No user biography fields.
```

Rollback:

```text
If scalar parity with incumbent closed-past residual fails, keep population shadow-only.
```

### P7R-M3 — Thresholds and dwell

Acceptance:

```text
MarginThresholdPolicyV1 mints every guard constant.
DynamismDwellPolicyV1 mints τ_dwell, τ_cell, τ_halt.
Band-vs-threshold comparisons deterministic.
No magic controller constants remain.
```

### P7R-M4 — E3 in shadow

Acceptance:

```text
Bare vigor decline does not fire E3.
Well-served low-vigor not halted.
Amputation fingerprint detected.
```

### P7R-M5 — E1 forecasts

Acceptance:

```text
Forecast committed before deposition opens.
Surprisal score impossible without sealed forecast.
Sandbagging penalized by accuracy.
No reward reads surprisal magnitude.
```

### P7R-M6 — Budget regulator and rate limiter

Acceptance:

```text
V* sealed and amendment-gated.
Authorized envelope amendment-gated.
Rate limiter exists as a rate actuator.
λ_h -> 0 implies ρ_s^max -> 0.
e_κ^max and m_s^max are amendment-gated and not learned.
Burst above rate cap rejected.
```

### P7R-M7 — Margin and cell hysteresis

Acceptance:

```text
M inputs sourced from E2/E1/E4/regulator/rate limiter.
notMeasured(M) routes negative.
Cell-axis hysteresis prevents D↔B chatter.
Halt minimum dwell exists.
Dwell reset prevents banking.
```

### P7R-M8 — E4 and grid

Acceptance:

```text
E4 copy self-subject.
E4 reopens deposition.
Cell B halts regardless of positive margin.
Default is floor with a door.
Re-entry requires both bifurcations.
```

### P7R-M9 — Shadow-live quarantine

Acceptance:

```text
Shadow ω cannot certify breathe.
Live contradiction demotes to watch/default.
No first-entry bootstrap crosses through B.
```

### P7R-M10 — Reward under grid

Acceptance:

```text
No graduation outside breathe-in-D.
Reward cannot touch budget, rate, thresholds, dwell, margin, mouth, or license.
γ=0 rollback exists.
```

### P7R-M11 — Surface rollout

Roll out in this order:

```text
evidence/history surfaces;
found objects;
smooth inline facts;
deposition sheets;
write-bearing witness cards;
user-authored temporal programs.
```

Each surface must pass D2, A2, budget, rate, slow license, E1/E2/E3 coverage, controller state, mouth type, settlement addendum, and rollback.

---

## 17. Test matrix

### 17.1 Static airframe tests

| Test | Target | Invariant |
|---|---|---|
| `testD2Unchanged` | write wall | `support(staged) ⊆ F(x_live)`. |
| `testA2Unchanged` | attention | `occupation(spoken) ⊆ A(tendered)`. |
| `testPrivacyMembraneUnchanged` | privacy | Raw private strings stay behind Swift. |
| `testBreakMouthCannotAcceptSmoothSubjectFact` | mouths | Stale you-fact cannot typecheck at break. |
| `testTemporalProgramCannotExpressSemanticAvoidance` | calculus | Structure only, not meaning. |
| `testNoDefaultStructuralNotificationChannel` | topology | No default witness notification capability. |
| `testRewardNeverAdmits` | reward | Reward cannot stage write or admit speech. |
| `testKairosNeverClaimedMeasured` | copy/report | Kairos remains floor. |

### 17.2 Controller repair tests

| Test | Target | Invariant |
|---|---|---|
| `testReferenceCapFrozenByAmendmentGate` | regulator | `V*` cannot drift upward without amendment. |
| `testAuthorizedEnvelopeRequiresAmendmentToWiden` | regulator | Owner/dashboard cannot quietly widen. |
| `testMarginThresholdPolicyMintsAllGuards` | thresholds | `M_hi`, `M_lo`, `θ`, `ω`, `κ`, E3 thresholds all minted. |
| `testNoControllerMagicConstants` | thresholds | Grid reads only policy IDs. |
| `testThresholdDerivationReportMeasured` | thresholds | Headroom, noise, and dwell sizing proven before breathe. |
| `testDwellDurationsMinted` | dwell | `τ_dwell`, `τ_cell`, `τ_halt` are durations, not booleans. |
| `testDwellBooleansAreComparatorOutputs` | dwell | `satisfied` derived from minted duration. |
| `testBandVsThresholdComparisonDeterministic` | thresholds | Straddling bands route to conservative state. |
| `testCellAxisHysteresisPreventsZeno` | cell axis | No D↔B chatter under noisy κ/ω. |
| `testHaltMinimumDwell` | halt | HALT cannot bounce out immediately. |
| `testDwellResetNoBanking` | dwell | Worse-state reentry resets clock. |
| `testRobustRateLimiterExists` | rate | Rate cap distinct from cumulative cap. |
| `testRobustRateLimiterCapsBursts` | rate | Cumulative remaining budget cannot permit burst flood. |
| `testLambdaZeroImpliesSpeechRateZero` | rate | If human deposition rate is zero, smooth rate cap is zero. |
| `testLiftZeroBuysNoSpeechRate` | rate | Depositions with no κ/ω lift do not raise cap. |
| `testRobustHarmCoefficientsNotLearned` | rate | `e_κ^max`, `m_s^max` not learned downward. |
| `testRateCalibrationFalsifierExists` | rate | Over-conservatism detectable and amendment-correctable. |
| `testSlowWitnessLicenseReasonSingleDefinition` | types | Only `SlowWitnessLicenseReasonV2` canonical. |
| `testShadowLiveOmegaContradictionQuarantines` | handoff | Shadow ω cannot certify breathe. |

### 17.3 Edge and margin tests

| Test | Target | Invariant |
|---|---|---|
| `testSelfDoubtLedgerIsPopulation` | E2 | Ledger has frozen failed-regime league. |
| `testScalarResidualDerivedFromLedger` | E2 | Scalar residual is derived view. |
| `testScalarResidualCannotExpressLeagueCollapse` | E2 | Scalar-only path fails collapse detection. |
| `testSealedForecastCommittedBeforeDepositionOpens` | E1 | Forecast precommit exists. |
| `testSurprisalScoreRequiresSealedForecast` | E1 | No post-hoc baseline. |
| `testSealedSurprisalGateNeverReward` | E1 | Surprisal magnitude not optimized. |
| `testForecastSandbaggingPenalizedByAccuracy` | E1 | Bad forecast cannot inflate safe signal. |
| `testBareVigorDeclineDoesNotFireE3` | E3 | Well-served quiet not punished. |
| `testAmputationFingerprintBlocksRecommit` | E3 | Three-way fingerprint blocks slow recommit. |
| `testVigorCollapseConfessionIsSelfSubject` | E4 | No user diagnosis. |
| `testVigorCollapseConfessionReopensDeposition` | E4 | Human clock solicited. |
| `testMarginInputsSourcedFromSealedQuantities` | margin | α/E2, β/E4, P/E1, y/regulator. |
| `testMarginUnmeasuredRoutesToDefault` | margin | `.notMeasured(M) ≡ M<0`. |
| `testEdge6StarvationCannotForgeHealthyMargin` | margin | Starved residual cannot read healthy. |
| `testTotalWithdrawalRoutesToDefaultNotInference` | margin/privacy | 0/0 conditional surprisal -> default. |

### 17.4 Hybrid trajectory tests

| Test | Target | Invariant |
|---|---|---|
| `testCellBPositiveMarginStillHalts` | grid | Stable amputation never breathes. |
| `testConfessFiresOnApproachNotCrossing` | grid | E4 fires for `0<M<M_lo`. |
| `testDefaultExitsOnlyAfterMeasuredDwell` | grid | Exit default requires measured `M>=M_lo` held. |
| `testBreatheRequiresBothBifurcations` | grid | M alone insufficient for D. |
| `testDefaultIsSelfExitingViaE4` | grid/E4 | Default has a door. |
| `testColdStartReachesWatchWithoutLiveSpeech` | migration | Shadow path bootstraps without crossing B. |
| `testBelowRateFloorRoutesDefaultNotHarm` | rate/grid | Insufficient human rate suppresses learning safely. |
| `testSustainedPlacementWithoutHumanDrivesHaltOrDefault` | reachability | Plant-only control cannot hold T. |
| `testCooperativeDepositionSequenceEscapesDefault` | liveness | Door exists under sufficient human input. |
| `testWatchConfessDoesNotLimitCycleFlood` | trajectory | Confess loop cannot generate placement flood. |
| `testNoGraduationOutsideBreatheInD` | phase/reward | Release qualifies, grid binds. |

---

## 18. Definition of done

### Doctrine and base

- [ ] Plan-7-revised adopted as the canonical target architecture.
- [ ] Plan-5 D2 wall preserved unchanged.
- [ ] A2, privacy membrane, phase gate, temporal calculus, two-mouth API, deposition, user-authored programs, and no-notification topology preserved.
- [ ] Every dynamical signal carries fate and measurement status.
- [ ] No Plan-7 witness invariant is F1 maximize.

### Controller repair completion

- [ ] `StructuralSpeechRegulatorV2.sealedReferenceCap` is amendment-gated.
- [ ] `authorizedEnvelope.maxCap` is amendment-gated.
- [ ] `MarginThresholdPolicyV1` mints all grid and E3 thresholds.
- [ ] `ThresholdDerivationReportV1` proves margin headroom, hysteresis gap, starvation floor, and dwell sizing.
- [ ] `DynamismDwellPolicyV1` mints `τ_dwell`, `τ_cell`, `τ_halt` as durations.
- [ ] `CellAxisHysteresisPolicyV1` prevents D↔B / HALT chatter.
- [ ] `StructuralSpeechRateLimiterV1` implements the robust rate law.
- [ ] `RobustHarmCoefficientV1` constants are amendment-gated and not learned.
- [ ] `SlowWitnessLicenseReasonV2` is the single canonical enum.
- [ ] `ShadowLiveOmegaHandoffV1` quarantines contradictory live liveness.

### E1–E4

- [ ] `SelfDoubtLedgerV1` has a population body.
- [ ] `SealedDepositionForecastV1` commits before deposition opens.
- [ ] Surprisal is gate/health, never reward.
- [ ] `LeagueVigorRegressionV1` fires only on the three-way fingerprint.
- [ ] `VigorCollapseConfessionV1` is self-subject and reopens deposition.

### Margin and grid

- [ ] `BifurcationMarginV2` reads sealed inputs.
- [ ] `.notMeasured(M) ≡ M<0` topology-enforced.
- [ ] Total withdrawal routes to default, not inference.
- [ ] Cell B halts regardless of positive margin.
- [ ] E4 fires on approach to the separatrix.
- [ ] Re-entry to breathe requires both `ω` and `κ` recovery, held for dwell.
- [ ] Default is floor with a door.

### Reward and release

- [ ] Reward cannot admit, widen, lower thresholds, shorten dwell, choose mouth, promote margin, or lower robust harm coefficients.
- [ ] Release qualifies organs; controller binds live use.
- [ ] No organ graduates outside breathe-in-D.
- [ ] γ=0 rollback and deterministic fallback exist.

### Verification

- [ ] Static airframe tests pass.
- [ ] Controller repair tests pass.
- [ ] Edge and margin tests pass.
- [ ] Hybrid trajectory tests pass.
- [ ] Tier-walk audit required for every dynamism change.
- [ ] All cross-tier arrows named and tested.

---

## 19. Self-audit

This table must be re-answered for every public surface launch, temporal operator addition, deposition-policy change, budget/regulator/rate change, threshold/dwell change, witness-organ graduation, reward-policy change, mouth API change, oscillator change, or controller retune.

| Litmus test | Required answer | Evidence |
|---|---:|---|
| Is D2 preserved bit-for-bit? | Yes | D2 output remains reward-free and support-bound. |
| Is A2 still per-tick tendered attention? | Yes | A2 admits exact placement only. |
| Is structural speech also rate-limited, not merely cumulatively budgeted? | Yes | `StructuralSpeechRateLimiterV1`. |
| Is `V*` frozen under amendment? | Yes | `sealedReferenceCap` cannot rise by config/reward. |
| Are all grid thresholds minted? | Yes | `MarginThresholdPolicyV1`. |
| Are all dwell durations minted? | Yes | `DynamismDwellPolicyV1`. |
| Can band-straddling forge a favorable transition? | No | Conservative comparison rule. |
| Can cell B breathe with positive margin? | No | B dominates margin. |
| Can D↔B chatter cause Zeno? | No | Cell-axis hysteresis + halt dwell. |
| Can reward widen budget or rate? | No | Topology lint. |
| Can reward lower `e_κ^max` or `m_s^max`? | No | Amendment-gated constants. |
| Can owner quietly raise reference cap? | No | Amendment gate. |
| Is sealed surprisal a reward? | No | Gate/health only. |
| Does bare vigor decline trigger halt? | No | Three-way fingerprint required. |
| Does E4 speak about the user? | No | Self-subject only. |
| Does total withdrawal infer biography? | No | Default. |
| Does shadow ω certify live breathe? | No | Handoff quarantine. |
| Is there one license enum? | Yes | `SlowWitnessLicenseReasonV2`. |
| Does the system say less when the human does not answer? | Yes | `λ_h -> 0 => ρ_s^max -> 0`; default. |
| Does product copy claim kairos was measured or preserved? | No | Copy-honesty scan. |

---

## 20. Appendix A — Folded Plan-6 base

This appendix makes the file standalone. It is a compact fold of the stable Plan-6 architecture, not a second plan.

### 20.1 Theorem, rule, and data taxonomy

```text
theorem:  impossible to express without type/topology change;
rule:     expressible, rejected by runtime admission, policy, tests;
data:     authored conjecture compiled into safe structural program.
```

Plan-7-revised keeps the naming convention:

```text
*TokenV1 / *CapabilityV1 / *MouthV1     theorem-facing type or topology;
*PolicyV1 / *GateV1 / *BudgetV1         runtime rule;
*ProgramV1 / *TemplateV1 / *DialV1      conjectural data;
*LedgerV1                               persistent measurement, must state subject.
```

### 20.2 Temporal structure calculus

The calculus expresses temporal structure only:

```text
positions, intervals, gaps, counts, density, recurrence, movement, adjacency,
erosion, comparison, residual.
```

It cannot express semantic meaning:

```text
avoidance, desire, need, preference, emotional valence, identity, worth,
relationship meaning, kairos.
```

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

Structural-only-ness is a theorem of input types, not a Boolean proof flag.

### 20.3 Fact cells

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

Swift alone mints fact cells. Models may select indices only.

### 20.4 A2 attention

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
```

No default structural notification channel exists.

### 20.5 Deposition

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
```

Deposition is typed, closed-past anchored, and non-interview by default. It becomes Plan-7's sealed human clock when paired with E1.

### 20.6 User authorship

The user may author temporal programs, thresholds, visibility dials, attention-width preferences, organ toggles, proxy-gap corrections, and amendments that tighten accountability. The user may not authorize raw model portrait, weakened D2/A2, default structural notifications, model access to raw identity, RUN/WRITE overlap, or break-you-facts.

---

## 21. Appendix B — Inherited D2 wall and reward boundary

D2 remains the only write-admission seam.

```text
D2 is in-process Swift;
D2 is not model-callable;
D2 performs lookup, never reconstruction from model text;
D2 owns support-to-staged handoff;
D2 is blind to reward as authority.
```

D2 algorithm summary:

```text
1. Verify context identity and freshness.
2. Resolve selected cell or materialized proposal through Swift-owned support.
3. Reject concrete model-authored write fields, reward fields, contestation fields, hidden evidence.
4. Verify source ID, evidence hash, basis hashes, and feasibility digest.
5. Lookup receipt and owning source.
6. Require kind/hash equality.
7. Classify strength and copy budget only by closed EvidenceKind policy.
8. Verify basis freshness.
9. Scan model text for PII, unsupported personalization, authority echo, reward/contestation claims.
10. Hydrate ProposalEnvelope from Swift support, not model text.
11. Run live F(x_live) and validatePropose.
12. Return non-Codable Swift verdict to staging.
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

Reward and contestation remain downstream. Plan-7-revised adds: reward also cannot touch margin status, grid state, threshold policy, dwell policy, robust coefficients, structural-speech reference, structural-speech rate, or mouth choice.

---

## 22. Coda

Plan 6 made CalAgent a witness. Plan 7 made the witness dynamically honest. Plan-7-revised makes the controller executable enough to verify.

The witness still cannot see kairos. It cannot know what a moment means. It cannot learn its way into the user's inner timing without building the portrait the membrane forbids. That loss is not patched by a metric. It is carried as a floor.

So the system speaks structurally only under state, attention, privacy, budget, rate, margin, cell, dwell, and mouth authority. When the human stops answering, the rate law says less. When the margin cannot be measured, the controller assumes it is falling. When the user becomes too predictable to the witness, the witness does not celebrate. It confesses that its own read is becoming self-confirming and asks again.

```text
A margin you cannot measure is negative.
A correction channel you cannot hear is not proof that you are right.
A user who no longer surprises the witness is not a victory.
A plant that can talk itself out of default is not corrigible.
Speech speed is earned by correction bandwidth.
The pen remains with the human.
```

The Plan-7-revised witness breathes only in D: live and aligned, measured and rate-limited, with both bifurcations crossed and held. Everywhere else it narrows, confesses, defaults, or halts.
