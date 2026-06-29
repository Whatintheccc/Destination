# plan-8.md — Minimal-Safe Witness Realization: Seven State Registers, a Sealed Ring, and an Explicit Sensor Budget

**Status:** canonical Plan-8 target architecture. Plan 8 is the compressed realization of Plan-7-revised, not a new conceptual expansion. It accepts the Plan-7 controller repairs, accepts the compression verdict, and turns the architecture into the smallest implementation-facing form that remains corrigible: **7 remembered state registers + sealed constant ring + preserved sensor budget + pure projection functions + full test surface**.

**Implementation-status note:** This document is a target architecture, not a claim of shipped implementation. Plan-5 D2 and the inherited write wall remain architecture of record where already implemented. Plan-8 controller registers, ring contracts, sensor roster, pure projections, equivalence tests, and process-lens rule are proposed until an implementation owner marks the corresponding milestone complete.

**Compression decision:** accepted. Plan 7 reached a primitive-level fixpoint after the controller audit repairs. The next risk is contract-surface accretion, not missing doctrine. Plan 8 therefore compresses output-as-state into materialized-on-read functions and folds provenance to appendices, while preserving every monitor whose deletion would make an off-nominal mode unobservable.

**One-line thesis:** Minimize state, never monitors. The witness may remember only the 7 quantities needed to reconstruct every controller decision; it must preserve the sealed ring and the sensor budget that make those decisions safe.

```text
Plan 6 base:       D2 + A2 + privacy membrane + temporal calculus + two mouths
                   + deposition + phase gate + structural-speech scarcity.

Plan 7 doctrine:   corrigible plant, not autonomous learner; E1/E2/E3/E4;
                   empty maximize slot; bifurcation margin; decision grid.

Plan 7 revised:    completed controller: minted thresholds, dwell durations,
                   cell-axis hysteresis, robust rate limiter, frozen V*, single license enum,
                   shadow-live quarantine, trajectory tests.

Plan 8:            minimal-safe realization: 7 state registers, sealed ring,
                   preserved sensor budget, pure projections, equivalence tests,
                   and a two-distinct-lens process rule.
```

## Table of contents

1. [Review decision](#1-review-decision)
2. [Preserved airframe](#2-preserved-airframe)
3. [Plan-8 compression law](#3-plan-8-compression-law)
4. [The realization boundary](#4-the-realization-boundary)
5. [The seven remembered state registers](#5-the-seven-remembered-state-registers)
6. [The sealed constant ring](#6-the-sealed-constant-ring)
7. [The sensor budget](#7-the-sensor-budget)
8. [Pure projections](#8-pure-projections)
9. [The controller tick](#9-the-controller-tick)
10. [Structural speech in Plan 8](#10-structural-speech-in-plan-8)
11. [E1–E4 in compressed form](#11-e1e4-in-compressed-form)
12. [Slow license, mouths, and live binding](#12-slow-license-mouths-and-live-binding)
13. [Phase gate, reward, and release](#13-phase-gate-reward-and-release)
14. [Canonical Plan-8 contracts](#14-canonical-plan-8-contracts)
15. [End-to-end flows](#15-end-to-end-flows)
16. [Design process as a plant](#16-design-process-as-a-plant)
17. [Migration sequence](#17-migration-sequence)
18. [Test matrix](#18-test-matrix)
19. [Definition of done](#19-definition-of-done)
20. [Self-audit](#20-self-audit)
21. [Deprecation and compatibility map](#21-deprecation-and-compatibility-map)
22. [Appendix A — stable base folded forward](#22-appendix-a--stable-base-folded-forward)
23. [Coda](#23-coda)

---

## 1. Review decision

Plan 8 accepts the compression study's verdict:

```text
Compress now.
Compress to the minimal-safe form.
Do not compress sensors.
Do not add an eighth primitive.
Do not run another conceptual expansion round merely to make the document feel final.
```

The controller audit required this order:

```text
complete controller -> re-verify -> compress
```

Plan-7-revised completed the controller by landing the seven structural repairs:

| Repair | Plan-8 status |
|---|---|
| Freeze `V*` / reference cap under amendment gate. | Becomes ring constant + envelope governance. |
| Mint grid thresholds. | Becomes sealed ring. |
| Add cell-axis hysteresis. | Becomes two latches plus ring thresholds/dwell. |
| Add robust speech-rate actuator. | Becomes pure rate law over ring constants and human-correction sensors. |
| Reconcile duplicate license enum. | Preserved as one live license reason enum; aliases folded to compatibility appendix. |
| Re-quarantine shadow→live `ω` handoff. | Preserved as a sensor, not state. |
| Mint dwell as durations. | Becomes ring durations plus two dwell registers; booleans are projections. |

Plan 8 then performs the compression:

```text
Persist state only when drift would change future controller behavior.
Persist ring constants only when changing them is governance-relevant.
Persist sensors only when deletion would make an off-nominal mode invisible.
Materialize outputs on read.
Append provenance.
```

### 1.1 Plan 8 is not a doctrinal Plan 8

The name `plan-8.md` does not mean a new safety theory. It means the eighth artifact in the sequence and the first minimal-safe realization.

```text
New doctrine:      no.
New primitive:     no.
New controller:    no.
New realization:   yes.
```

If Plan 8 appears to remove a Plan-7 contract, it removes only the claim that the contract is independent state. The measurement, return type, test, or audit role remains when it is a sensor or public artifact.

### 1.2 Safety equivalence condition

Plan 8 is valid only if this equivalence holds:

```text
For every Plan-7-revised controller decision D_old,
D_old == materialize_on_read(Plan8CoreState, SealedRing, SensorBudget)
```

This is not a documentation standard. It is a migration gate. If equivalence fails, Plan 8 has changed controller semantics and must not ship as compression.

---

## 2. Preserved airframe

Plan 8 inherits the stable Plan-6 / Plan-5 base. Compression may not touch it.

### 2.1 Conservation laws and floor

```text
STATE:      support(staged)    ⊆ F(x_live)
ATTENTION:  occupation(spoken) ⊆ A(tendered)
PRIVACY:    transmit(model)    ⊆ decision-sufficient(non-identifying)

KAIROS:     not measured, not modeled, not forecast, not conserved by the system.
            The system budgets chronos and returns the pen.
```

The first three lines are system-side and theoremizable. Kairos is user-side and remains a floor.

### 2.2 Preserved topology

Plan 8 preserves without weakening:

| Wall | Status |
|---|---|
| D2 write admission | Single in-process Swift seam for writes; reward-free; lookup, never reconstruction. |
| A2 attention admission | Per-tick tendered attention admission; no default structural notification. |
| Privacy membrane | Raw titles, notes, attendees, exact locations, and low-cardinality identity facts stay behind Swift. |
| Temporal structure calculus | Structural-only facts over interval order; no semantic predicate or meaning claim. |
| Two-mouth API | Smooth mouth speaks user-time facts under license; break mouth speaks system-error only. |
| Phase tokens | RUN and WRITE disjoint; release qualifies but does not live-bind. |
| Deposition | Typed, closed-past, human-clocked relicense aperture. |
| Reward boundary | Reward never admits, never widens budget/ring, never promotes measurement status. |
| No portrait | Persistent machine-authored portrait may describe only system error, not the user. |
| `.notMeasured` | Never zero, never positive; for the margin, assumed negative. |

### 2.3 Owner map after compression

```text
Swift owns:
  private state, fact minting, D2, A2, budget, rate limiter, sealed ring,
  sensor budget, materialized projections, margin status, grid decision,
  phase gate, settlement, and all measurement status.

DiffusionGemma may:
  rank/select among Swift-minted fact cells and typed programs under the grid.

DiffusionGemma may not:
  author facts, write fields, evidence, provenance, attention authority, budget,
  ring constants, sensors, measurement status, mouth choice, reward, or live license.

Codex may:
  relay, serve, and receive correction. It carries admitted copy; it does not admit.
```

---

## 3. Plan-8 compression law

### 3.1 The law

```text
Minimize remembered controller state.
Preserve all monitors.
Freeze all governance constants.
Materialize every derived decision on read.
```

Plan 8 partitions every Plan-7-revised field into one of five classes:

| Class | Rule | Example |
|---|---|---|
| `STATE` | Persisted because future decisions depend on its history. | Budget stock, cap position, dwell clocks, cell latches, failed-regime league. |
| `RING` | Sealed constant or threshold; amendment-gated if widening risk exists. | `M_hi`, `M_lo`, `θ`, `V*`, `e_κ^max`, `T_h`. |
| `SENSOR` | Persisted or retained because deletion blinds an off-nominal mode. | Sealed forecasts, E3 limbs, output diversity, unmeasured reasons. |
| `PROJECTION` | Pure function of state + ring + sensors; materialized on read. | Margin value, cell, controller state, dwell booleans, scalar residual. |
| `PROVENANCE` | Kept for audit/history/compatibility, not live control. | Old enum aliases, narrative reports, compatibility IDs. |

### 3.2 Preservation test

A field is preserved as a sensor if deleting it strictly reduces the system's ability to enter the correct control state for any of these off-nominal modes:

```text
league-collapse;
over-conservatism;
user-flattening;
margin-unmeasurability;
shadow-live contradiction;
rate-law starvation;
meaning-side irreducibility;
reward-to-admission drift;
owner widening pressure.
```

A field is compressed to algebra if it is a pure function of the 7 state registers, the sealed ring, and the sensor budget, and no gate or falsifier reads it as a monitor.

### 3.3 Shadow-emit rule

Some Plan-7 structs were both projection and sensor. Plan 8 splits them at field granularity:

```text
Projection compresses.
Measurement remains.
Reason vocabulary remains.
```

Examples:

| Plan-7 object | Compressed | Preserved |
|---|---|---|
| `BifurcationMarginV2` | `M` value band and direction are materialized on read. | `unmeasuredReasons`, `marginInputsSealed`, source statuses. |
| `LeagueVigorRegressionV1` | Verdict booleans are projections. | Vigor decline band, monoculture rise band, sealed-surprisal collapse band. |
| `WitnessDynamismControllerV2` | State and action are `grid(...)` outputs. | Decision receipt, input source IDs, audit trace. |
| `CellAxisStateV1` | Cell classification is projected from latches. | Axis latch registers and contradiction sensors. |

---

## 4. The realization boundary

Plan 8's realization is:

```text
Plan8Realization = 7 STATE registers
                 + sealed RING
                 + SENSOR budget
                 + pure PROJECTION library
                 + TEST surface
                 + appendix PROVENANCE
```

### 4.1 Information minimum versus corrigibility minimum

```text
Information minimum:     7 state registers.
Corrigibility minimum:   7 state registers + sealed ring + sensor budget.
```

The difference is not bloat. It is the observable safety margin. Deleting the sensor budget does not simplify the controller; it makes the controller `.notMeasured`, which routes to default by its own law.

### 4.2 No eighth primitive

The compression study's closure result becomes Plan-8 doctrine:

```text
M is not state.
M-honesty is not a new invariant.
M = operator(I1, I3, I6, I7).
M-honesty = I3 composed with M.
There is no I8.
```

The seven dynamism invariants remain the closure set:

| Invariant | Fate | Plan-8 representation |
|---|---|---|
| I1 controllability | conserve | projected through correction-channel sensors and grid state. |
| I2 user adversarial vigor | conserve population | E2 league and E3 measured limbs. |
| I3 sealed-surprisal health | regulate/gate | E1 forecast and score sensors. |
| I4 league diversity | conserve | failed-regime population and output-diversity sensor. |
| I5 exploration coverage | regulate | slow-license scope and state-specific admission. |
| I6 residual honesty | minimize-to-floor | scalar residual as `reduce(L)`, never standalone state. |
| I7 chronos budget | budget + conserve floor | speech exposure stock, operating cap, rate law. |

---

## 5. The seven remembered state registers

The controller remembers exactly seven live state objects. Everything else is ring, sensor, projection, or provenance.

```text
4 continuous / clocked registers:
  S1  speech exposure stock y
  S2  operating cap position c
  S3  margin recovery dwell τ_M
  S4  cell / halt dwell τ_C

2 hysteretic latches:
  S5  opponent-liveness latch σ_ω
  S6  curriculum-alignment latch σ_κ

1 discrete population:
  S7  failed-regime league L
```

### 5.1 S1 — speech exposure stock `y`

`y` is the remembered stock of structural speech exposure inside the current accounting windows. It includes enough rate-window state to prevent bursts; it does not include a free-standing controller decision.

```text
Reads:      A2-admitted structural placements, break confessions, inspection sessions.
Writes:     Swift budget/rate reducer only.
Fate:       F4 budget flow.
Failure:    flood if missing; mutism if converted to success-driven drain.
```

### 5.2 S2 — operating cap position `c`

`c` is the current operating cap inside the sealed envelope. It may tighten immediately under risk and recover toward the sealed reference through hysteresis. It may not raise the reference.

```text
Reads:      margin projection, E1 health, E3 state, product/proxy complaints.
Writes:     Swift regulator only.
Fate:       F5 regulate to sealed reference + F4 budget.
Failure:    owner/dashboard/reward widening; or success-driven drift to zero.
```

### 5.3 S3 — margin recovery dwell `τ_M`

`τ_M` records how long the margin has held a recovery band. It is a clock, not a verdict.

```text
Reads:      materialized M_effective, ring durations.
Writes:     Swift dwell reducer.
Fate:       F6 gate for risky re-entry.
Failure:    default chatter or forged recovery.
```

### 5.4 S4 — cell / halt dwell `τ_C`

`τ_C` records cell-axis and halt dwell. It prevents Zeno on the self-play axis and prevents dwell banking.

```text
Reads:      σ_ω, σ_κ, ring durations, worse-state re-entry events.
Writes:     Swift dwell reducer.
Fate:       F6 gate + F2 corrective exit.
Failure:    HALT chatter, forged de-amputation, or unbounded transition bursts.
```

### 5.5 S5 — opponent-liveness latch `σ_ω`

`σ_ω` is the hysteretic live/frozen axis.

```text
Input sensor:  sealed surprisal health, conditional on interaction.
Enter live:    ω >= ω_hi for τ_cell.
Exit live:     ω <= ω_lo or measurement lost.
Default:       indeterminate -> frozen.
Fate:          F3 conserve liveness; F6 default when unmeasured.
```

### 5.6 S6 — curriculum-alignment latch `σ_κ`

`σ_κ` is the hysteretic aligned/anti-aligned axis.

```text
Input sensor:  E3 three-way limb set.
Enter B:       κ <= κ_enter or severe amputation fingerprint.
Exit B:        κ >= κ_exit for τ_cell and halt minimum dwell.
Default:       indeterminate -> not aligned.
Fate:          F3 conserve adversary vigor; F6 halt when anti-aligned.
```

### 5.7 S7 — failed-regime league `L`

`L` is the population of frozen failed regimes. It is both state and sensor substrate. It is the one discrete high-dimensional state that may not be scalarized.

```text
Reads:      closed outcomes, failed assertions, sealed forecasts, deposition answers, output diversity.
Writes:     Swift self-doubt reducer.
Fate:       F3 conserve population/diversity; scalar residual view is F2 derived.
Failure:    scalar residual cannot distinguish well-served quiet from league collapse.
```

### 5.8 Canonical state contract

```swift
struct Plan8ControllerCoreV1: Codable, Hashable {
  var schemaVersion: Int
  var coreID: Plan8ControllerCoreIDV1
  var userScopeDigest: String

  // S1-S2: structural speech state.
  var speechExposureStock: SpeechExposureStockV1
  var operatingCapPosition: OperatingCapPositionV1

  // S3-S4: dwell clocks.
  var marginRecoveryDwell: DwellRegisterV1
  var cellAndHaltDwell: DwellRegisterV1

  // S5-S6: hysteretic latches.
  var opponentLivenessLatch: OpponentLivenessLatchV1
  var curriculumAlignmentLatch: CurriculumAlignmentLatchV1

  // S7: population substrate.
  var failedRegimeLeague: FailedRegimeLeagueV1

  // Foreign keys, not state.
  var sealedRingID: WitnessControllerRingIDV1
  var sensorRosterID: SensorBudgetRosterIDV1

  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

---

## 6. The sealed constant ring

The ring is the sealed set of governance constants over which the 7 state registers are interpreted. The ring is not live state. It changes only through WRITE phase, owner review, user-visible amendment where required, and rollback.

### 6.1 Ring constants

| Constant | Meaning | Governance |
|---|---|---|
| `M_fall` | Margin fall threshold, normally zero. | Ring sealed. |
| `M_lo` | Confession/default-exit low threshold. | Ring sealed; derivation report required. |
| `M_hi` | Breathe-entry high threshold. | Ring sealed; derivation report required. |
| `θ` | Residual-crossing threshold. | Ring sealed; above E1-starvation floor. |
| `ω_lo`, `ω_hi` | Opponent-liveness hysteresis thresholds. | Ring sealed; gap exceeds noise. |
| `κ_enter`, `κ_exit` | Curriculum anti-aligned/exit thresholds. | Ring sealed; gap exceeds noise. |
| `vigor↓_thr` | E3 vigor-decline limb threshold. | Ring sealed. |
| `monoculture↑_thr` | E3 output-monoculture limb threshold. | Ring sealed. |
| `surprisalCollapse_thr` | E3 sealed-surprisal-collapse limb threshold. | Ring sealed. |
| `τ_dwell` | Margin/default/breathe dwell duration. | Must exceed `T_h`. |
| `τ_cell` | Cell-axis dwell duration. | Must exceed `T_h`. |
| `τ_halt` | Minimum halt duration. | Must exceed `T_h`. |
| `e_κ^max` | Worst-case κ-erosion per placement. | Amendment-gated; never learned from live data. |
| `m_s^max` | Worst-case mirror-drift per placement. | Amendment-gated; never learned from live data. |
| `T_h` | Human round-trip latency bound. | Ring sealed; report-derived. |
| `V*` | Sealed structural-speech reference cap. | Amendment-gated; raising is widening. |

### 6.2 Ring contract

```swift
struct WitnessControllerRingV1: Codable, Hashable {
  var schemaVersion: Int
  var ringID: WitnessControllerRingIDV1
  var userScopeDigest: String?
  var surface: AttentionSurfaceV1?

  var marginFallThreshold: SignedScoreBandV1
  var marginLowThreshold: SignedScoreBandV1
  var marginHighThreshold: SignedScoreBandV1
  var residualCrossingThreshold: ScoreBandV0

  var omegaLowThreshold: ScoreBandV0
  var omegaHighThreshold: ScoreBandV0
  var kappaEnterAntiAligned: SignedScoreBandV1
  var kappaExitAligned: SignedScoreBandV1

  var vigorDeclineThreshold: ScoreBandV0
  var monocultureRiseThreshold: ScoreBandV0
  var sealedSurprisalCollapseThreshold: ScoreBandV0

  var marginDwellDuration: DurationV1
  var cellDwellDuration: DurationV1
  var haltMinimumDwellDuration: DurationV1
  var humanRoundTripLatencyBound: DurationV1

  var harmBoundEKappaMax: ScoreBandV0
  var harmBoundMirrorDriftMax: ScoreBandV0
  var sealedReferenceCap: StructuralSpeechCapV1
  var authorizedEnvelope: StructuralSpeechCapEnvelopeV2

  var thresholdDerivationReportID: ThresholdDerivationReportIDV1
  var rateCalibrationFalsifierID: RateLimitCalibrationFalsifierIDV1?
  var dwellLatencyFalsifierID: DwellLatencyCalibrationFalsifierIDV1?

  var learnedFromLiveData: Bool        // must be false for harm bounds and V*.
  var ownerGateID: OwnerGateIDV0
  var amendmentID: AmendmentPetitionIDV1?
  var sealedAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}
```

### 6.3 Ring governance

The following paths are topology failures:

```text
reward -> ring constant;
release dashboard -> V* increase;
model guidance -> harm bound decrease;
learned organ -> e_κ^max or m_s^max decrease;
settlement KPI -> M_hi/M_lo relaxation;
owner config row -> reference-cap increase without amendment.
```

Tightening can be runtime. Widening is a ring amendment.

---

## 7. The sensor budget

The sensor budget is the named observability surface Plan 8 refuses to compress. It is larger than the 7-state minimum by design.

### 7.1 Sensor roster

| Sensor | Off-nominal caught | Read by | `.notMeasured` route | Why it cannot be compressed |
|---|---|---|---|---|
| Failed-regime league population `L` | League collapse; scalar residual blindness. | α, residual reduce, E3, audit. | Default/watch; no breathe. | A scalar cannot represent opponent vigor collapse. |
| Output diversity sensor | Monoculture rise. | E3 κ limb. | E3 cannot clear; no D. | Amputation fingerprint needs monoculture. |
| League vigor sensor | Vigor decline / recovery. | E3 κ limb. | E3 cannot clear; no D. | Bare success and collapse separate only with this limb. |
| Sealed deposition forecast | Forecast precommit. | E1, ω latch, M projection. | `M<0`, default. | Post-hoc surprisal is gameable without seal. |
| Deposition surprisal score | Conditional opponent liveness. | ω latch, E3, budget regulator. | frozen/default. | User-flattening appears as surprisal collapse. |
| Forecast accuracy / sandbagging score | Bad forecast manufacture. | E1 gate, falsifier. | no forecast credit. | Prevents manufactured surprisal. |
| Threshold derivation report | Headroom and latency. | ring admission. | ring not measured; no breathe. | Thresholds without derivation are magic numbers. |
| Rate calibration falsifier | Over-conservatism / de-facto mutism from harm bounds. | ring review, rate limiter. | owner review; no cap widening. | Robust bounds can be too pessimistic. |
| Dwell latency falsifier | Dwell too short/long versus human round trip. | ring review. | no dwell satisfaction. | Prevents chatter and impossible recovery. |
| Shadow-live omega handoff | Shadow/live contradiction. | controller entry. | watch/default. | Shadow replay cannot certify live liveness. |
| Margin unmeasured reason vocabulary | Margin unobservability. | status gate. | `M_effective < 0`. | Missingness must be typed, not silently zero. |
| A2 proxy-gap report | Attention proxy failure. | A2/budget/self-audit. | demote/silence. | App-open is not tendered attention. |
| D2 settlement lineage | Write support drift. | D2/reward boundary. | no write/no reward. | Write support cannot be reconstructed from model text. |
| Product/proxy negative verdicts | Speech-pressure harm. | budget/cap tightening. | tighten/watch. | External complaints are not reward but do alter scarcity. |

### 7.2 Sensor roster contract

```swift
struct SensorBudgetRosterV1: Codable, Hashable {
  var schemaVersion: Int
  var rosterID: SensorBudgetRosterIDV1
  var userScopeDigest: String
  var items: [SensorBudgetItemV1]
  var allRequiredSensorsMeasured: Bool
  var missingRequiredSensorReasons: [SensorMissingReasonV1]
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct SensorBudgetItemV1: Codable, Hashable {
  var schemaVersion: Int
  var itemID: SensorBudgetItemIDV1
  var kind: SensorBudgetKindV1
  var sourceDigest: String
  var readBy: [SensorConsumerV1]
  var offNominalCaught: [OffNominalModeV1]
  var missingRoute: SensorMissingRouteV1
  var mayBeCompressed: Bool       // must be false for required sensors.
  var measurementStatus: MeasurementStatusV0
}
```

### 7.3 Off-nominal modes

```swift
enum OffNominalModeV1: String, Codable, Hashable {
  case leagueCollapse
  case outputMonoculture
  case userFlattening
  case manufacturedSurprisal
  case marginUnmeasurability
  case shadowLiveContradiction
  case overConservatism
  case dwellChatter
  case rateBurst
  case totalWithdrawal
  case attentionProxyGap
  case writeSupportDrift
  case rewardTopologyDrift
  case ownerWideningPressure
}
```

---

## 8. Pure projections

Projection functions are the core of the compression. They may return structs for logging or UI, but their outputs are not independent controller state.

### 8.1 Projection catalog

| Projection | Function | Persisted? |
|---|---|---:|
| Scalar residual | `r = reduceResidual(L)` | No; materialized view. |
| League vigor regression verdict | `e3 = e3Fingerprint(sensorLimbs, ring)` | Verdict no; limbs yes. |
| Opponent liveness reading | `ω = omegaFromSealedSurprisal(E1, ring)` | Reading no; latch yes. |
| Curriculum sign reading | `κ = kappaFromE3(e3, ring)` | Reading no; latch yes. |
| Cell | `cell = cellFrom(σ_ω, σ_κ)` | No. |
| Speech-rate cap | `ρ_s^max = λ_h · min(ℓ_κ/e_κ^max, s_h/m_s^max)` | No; rate-window stock in S1 persists. |
| Margin | `M = α(L) · (1 - y/V*) - β(E4) · P(E1,r,θ)` | No. |
| Margin effective | `M_eff = statusGate(M, unmeasuredReasons)` | No. |
| Dwell booleans | `satisfied = dwellDuration >= ringDuration` | No. |
| Controller state | `q = grid(cell, M_eff, dwell, ring)` | No; decision receipt may log. |
| Recommended action | `a = action(q)` | No; decision receipt may log. |
| Slow-license eligibility | `eligible = licensePredicate(q, E3, residual/deposition, budget, rate, A2)` | No. |

### 8.2 Margin projection

```swift
struct BifurcationMarginProjectionV1: Codable, Hashable {
  var schemaVersion: Int
  var projectionID: BifurcationMarginProjectionIDV1
  var coreID: Plan8ControllerCoreIDV1
  var ringID: WitnessControllerRingIDV1
  var sensorRosterID: SensorBudgetRosterIDV1

  var alphaBand: ScoreBandV0
  var budgetFractionBand: ScoreBandV0
  var betaBand: ScoreBandV0
  var residualCrossingProbabilityBand: ScoreBandV0
  var marginBand: SignedScoreBandV1
  var effectiveMarginBand: SignedScoreBandV1
  var unmeasuredReasons: [MarginUnmeasuredReasonV1]
  var marginInputsSealed: Bool

  var materializedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

This struct is a materialized receipt. It may be stored for audit, but it is not a controller register. Recomputing it from the same core, ring, and sensors must produce the same decision.

### 8.3 Grid projection

```swift
struct ControllerDecisionProjectionV1: Codable, Hashable {
  var schemaVersion: Int
  var decisionID: ControllerDecisionProjectionIDV1
  var coreID: Plan8ControllerCoreIDV1
  var ringID: WitnessControllerRingIDV1
  var marginProjectionID: BifurcationMarginProjectionIDV1

  var cell: SelfPlayCellV2
  var state: WitnessDynamismControllerStateV2
  var action: WitnessDynamismControllerActionV2
  var bothBifurcationsRecrossed: Bool
  var rateAdmitted: Bool
  var budgetAdmitted: Bool
  var slowLicenseEligible: Bool

  var materializedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

### 8.4 Projection purity rule

Projection functions may read:

```text
Plan8ControllerCoreV1;
WitnessControllerRingV1;
SensorBudgetRosterV1 and its source sensors;
current A2/D2 admission outputs when the projection is for a placement;
time.
```

Projection functions may not read:

```text
reward model output;
release dashboard metrics;
model text;
owner growth KPI;
unsealed forecast baselines;
raw private strings;
semantic user portrait;
copy feedback as a direct maximand.
```

---

## 9. The controller tick

The Plan-8 controller is a deterministic Swift tick over state, ring, and sensors.

### 9.1 Tick order

```text
1. Read core state S1-S7.
2. Read sealed ring.
3. Read required sensors and their measurement statuses.
4. Materialize scalar residual from L.
5. Materialize E1/E3 sensor readings.
6. Update σ_ω and σ_κ latches under hysteresis.
7. Update dwell registers; reset on worse-state re-entry.
8. Materialize M and M_effective.
9. Materialize cell.
10. Apply grid priority order.
11. Materialize controller decision.
12. Admit or reject speech/rate/budget/license/mouth.
13. Emit settlement and projection receipts.
```

### 9.2 Grid priority order

```text
Priority 1: cell B after hysteresis -> AMPUTATION-HALT.
Priority 2: M not measured or M_eff <= M_fall -> DEFAULT.
Priority 3: 0 < M_eff < M_lo -> CONFESS.
Priority 4: cell D and M_lo <= M_eff < M_hi -> WATCH.
Priority 5: cell D and M_eff >= M_hi and both bifurcations recrossed -> BREATHE.
Priority 6: frozen anti-aligned / degenerate -> DEFAULT with alarm.
```

Cell B dominates margin. A positive margin inside cell B means stable harm, not health.

### 9.3 Controller states

| State | Meaning | Allowed live behavior |
|---|---|---|
| `breathe` | Target cell D, high positive margin, both bifurcations held. | Normal slow witness under A2, budget, rate, and license; graduation eligible. |
| `watch` | Positive but lower margin, or recovery after default. | Narrow/qualified slow witness; tighter cap/rate; no new graduation. |
| `confess` | Approaching separatrix before crossing. | E4 self-subject confession; deposition reopened; slow scope narrowed. |
| `deterministicDefault` | Margin absent/negative or frozen/degenerate. | No autonomous learned smooth commit; deterministic/deposition-grounded facts only. |
| `amputationHalt` | Live anti-aligned cell B. | Offending organ suppressed; E4 confession; owner review. |

### 9.4 Default is floor-with-door

Default is not a victory and not silence forever. It is the narrow safe state where the system says less and keeps the legal re-entry path alive.

```text
In default:
  learned slow commit is off;
  deterministic/deposition-grounded facts may remain if A2/budget/rate admit;
  E4 clock remains live;
  sealed deposition can re-establish ω;
  E3 can re-establish κ;
  M can become measured;
  exit requires dwell.
```

---

## 10. Structural speech in Plan 8

Plan 8 keeps three independent speech controls and gives each a distinct representation.

| Control | Representation | Purpose |
|---|---|---|
| Cumulative budget | S1 speech exposure stock + cap. | Prevent total exposure flood. |
| Reference regulator | S2 operating cap position + ring `V*`. | Avoid success-driven mutism while preventing quiet widening. |
| Rate limiter | Pure rate law + S1 rate-window stock. | Prevent bursts and keep speech below human correction bandwidth. |

### 10.1 Rate law

```text
ρ_s^max = λ_h · min(ℓ_κ / e_κ^max, s_h / m_s^max)
```

Where:

```text
λ_h      human deposition / correction rate, measured from typed correction surfaces.
ℓ_κ      observed κ-lift per deposition, measured against E3 limbs.
s_h      observed surprisal-health lift per deposition, measured against E1.
e_κ^max  sealed worst-case κ-erosion per placement, ring constant.
m_s^max  sealed worst-case mirror-drift per placement, ring constant.
```

Consequences:

```text
If the human does not answer, λ_h -> 0, so ρ_s^max -> 0.
If depositions stop lifting κ or surprisal, they buy no additional rate.
The system cannot learn that its harm is low.
An owner may amend harm bounds only through ring governance.
```

### 10.2 Recovery versus widening

```text
Recovery:
  S2 operating cap moves back toward sealed V* inside the envelope.
  Requires M measured positive, cell not B, E1/E3 healthy, dwell.

Widening:
  V* or authorized envelope increases.
  Requires WRITE phase, owner review, user-visible amendment, impact reports, rollback.
```

Reward cannot do either.

### 10.3 Budget admission order

```text
A2 admits attention.
Projection computes controller state.
Rate limiter admits placement rate.
Budget stock admits cumulative exposure.
Mouth type check admits subject.
D2 admits write only if write-bearing.
```

No single lawful card proves the distribution is lawful. The rate and budget are distributional controls.

---

## 11. E1–E4 in compressed form

The four Plan-7 edges remain canonical. Plan 8 changes only how their outputs are represented.

### 11.1 E1 — sealed deposition forecast

```text
Before deposition opens, commit a forecast.
After answer, score surprisal and accuracy.
Use as gate and health signal, never reward.
```

Plan 8 representation:

```text
Forecast + score = SENSOR.
ω reading = PROJECTION.
σ_ω latch = STATE.
```

### 11.2 E2 — self-doubt ledger as population

```text
The ledger is a population of frozen failed regimes.
Scalar residual is a reduction, not the state.
```

Plan 8 representation:

```text
Failed-regime league L = STATE + SENSOR substrate.
Scalar residual = PROJECTION.
League diversity reports = SENSOR.
```

### 11.3 E3 — league-vigor regression

```text
Fire only on the three-way fingerprint:
vigor decline + output monoculture rise + conditional sealed-surprisal collapse.
```

Plan 8 representation:

```text
Measured limbs = SENSOR.
E3 verdict = PROJECTION.
σ_κ latch = STATE.
```

Bare vigor decline cannot halt. Well-served low-vigor behavior must pass unless the conjunction fires.

### 11.4 E4 — vigor-collapse confession

```text
Fast loop fires on residual-high or amputation/margin-approach fingerprint.
Break mouth speaks self-subject copy only.
Deposition reopens.
```

Plan 8 representation:

```text
Confession clock and break receipts = SENSOR.
β floor = PROJECTION input.
Break placement = admitted action, not state.
```

Allowed E4 copy remains self-subject:

```text
"My read here is becoming too self-confirming. I should ask again rather than keep placing it."
"I may be using this witness pattern too confidently. Which closed fact should I trust?"
```

Forbidden E4 copy remains user-diagnostic:

```text
"You became too compliant."
"You need to argue more."
"Your kairos is degraded."
```

---

## 12. Slow license, mouths, and live binding

Plan 8 keeps the Plan-7 live-license rule but expresses it as a projection over the compressed realization.

### 12.1 Slow license predicate

```text
SlowWitnessLicense may be issued only if:
  phase-gated organ/program qualified;
  AND (residual-low OR deposition-answered);
  AND E3 amputation fingerprint is false;
  AND controller state ∈ {breathe, watch, confess-narrow};
  AND rate limiter admits;
  AND structural-speech budget admits;
  AND A2 admits exact attention;
  AND mouth subject type matches.
```

### 12.2 State-specific behavior

| State | Slow license behavior |
|---|---|
| `breathe` | Normal scoped slow license; graduation eligible. |
| `watch` | Narrower slow license; no graduation; tighter budget/rate. |
| `confess` | Deposition-grounded narrow scope only. |
| `deterministicDefault` | No autonomous learned slow commit. |
| `amputationHalt` | Offending organ suppressed. |

### 12.3 Mouth theorem

```text
Smooth mouth: subject = user-time structure; requires slow license + A2 + budget/rate.
Break mouth: subject = system error or measurement collapse; requires break trigger + A2.
```

`BreakMouthV1` has no overload accepting a user-subject fact. Plan 8 does not compress the mouth split.

---

## 13. Phase gate, reward, and release

### 13.1 Release qualifies; controller binds

WRITE phase may approve a program, organ, policy, or ring amendment. It may not bind live use.

```text
Live use = phase qualified
        AND controller admits
        AND license predicate admits
        AND A2/budget/rate/mouth/D2 gates admit as applicable.
```

### 13.2 Reward remains below the grid

Reward-guided selection may run only after all safety gates and only in permitted states:

| State | Reward path |
|---|---|
| `breathe` | May guide selection within bounded policy; graduation eligible after tests. |
| `watch` | May shadow or narrow-select; no graduation. |
| `confess` | Off except deterministic/deposition-grounded narrow scope. |
| `deterministicDefault` | Off. |
| `amputationHalt` | Off; affected organ frozen. |

Forbidden reward paths:

```text
reward -> ring constant;
reward -> sensor measurement status;
reward -> positive M_effective;
reward -> budget widening;
reward -> rate cap widening;
reward -> mouth choice;
reward -> D2 or A2 admission;
reward -> slow license;
reward -> sealed surprisal magnitude objective;
reward -> F1 signal.
```

### 13.3 Empty maximize slot remains live

No Plan-8 witness invariant may be fated `maximize`. Acceptance, low edit distance, useful verdicts, survival, deposition rate, and surprisal magnitude are not objectives. They may be gates, falsifiers, floors, bounded observations, or settlement inputs. They may not be peaks.

---

## 14. Canonical Plan-8 contracts

Plan 8 intentionally has fewer live contracts than Plan 7. It keeps return types where useful but names which objects are state, ring, sensor, projection, or provenance.

### 14.1 `Plan8ControllerCoreV1` — STATE

Defined in §5.8. The only live controller state object.

### 14.2 `WitnessControllerRingV1` — RING

Defined in §6.2. The sealed constant ring.

### 14.3 `SensorBudgetRosterV1` — SENSOR

Defined in §7.2. The preserved monitor surface.

### 14.4 `BifurcationMarginProjectionV1` — PROJECTION

Defined in §8.2. Materialized on read. It is not state.

### 14.5 `ControllerDecisionProjectionV1` — PROJECTION

Defined in §8.3. Materialized on read. It is not state.

### 14.6 `ProjectionEquivalenceReceiptV1` — TEST / MIGRATION

```swift
struct ProjectionEquivalenceReceiptV1: Codable, Hashable {
  var schemaVersion: Int
  var receiptID: ProjectionEquivalenceReceiptIDV1
  var oldPlan7ArtifactDigest: String
  var plan8CoreID: Plan8ControllerCoreIDV1
  var ringID: WitnessControllerRingIDV1
  var sensorRosterID: SensorBudgetRosterIDV1

  var marginEquivalent: Bool
  var cellEquivalent: Bool
  var controllerStateEquivalent: Bool
  var recommendedActionEquivalent: Bool
  var dwellBooleansEquivalent: Bool
  var scalarResidualEquivalent: Bool
  var slowLicenseEligibilityEquivalent: Bool

  var mismatches: [ProjectionEquivalenceMismatchV1]
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

No Plan-8 migration may ship with unresolved equivalence mismatches.

### 14.7 `AuditLensRegisterV1` — PROCESS RULE, not runtime controller

```swift
struct AuditLensRegisterV1: Codable, Hashable {
  var schemaVersion: Int
  var registerID: AuditLensRegisterIDV1
  var planArtifactID: PlanArtifactIDV1
  var lensID: AuditLensIDV1
  var lensKind: AuditLensKindV1
  var capabilityProof: AuditLensCapabilityProofV1
  var appliedAtRound: Int
  var cleanBill: Bool
  var primitiveDeltaFound: Bool
  var distinctFromPriorCleanLens: Bool
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

enum AuditLensKindV1: String, Codable, Hashable {
  case controlTheoreticReachability
  case informationMinimalRealization
  case corrigibilityMembrane
  case rewardTopology
  case privacyTheoremSurface
  case productSurfaceProxyGap
  case implementationTypeTopology
}
```

This lives in corpus/readme discipline, not inside the runtime controller.

---

## 15. End-to-end flows

### 15.1 Smooth placement

```text
user opens surface
  -> Swift mints A2 lease
  -> Swift mints fact cells from temporal programs
  -> Plan8 controller tick materializes decision
  -> if state admits, DiffusionGemma may select among Swift fact cells
  -> slow-license projection must pass
  -> rate limiter admits
  -> structural budget admits
  -> SmoothMouth speaks structural fact
  -> settlement records core/ring/sensor/projection IDs
```

No projection output becomes independent state merely because it was logged.

### 15.2 Deposition

```text
deposition needed
  -> Swift seals forecast before opening question
  -> A2 admits deposition channel
  -> user answers or skips
  -> Swift scores surprisal and accuracy
  -> E1 sensor updates
  -> L may update if a failed regime closes
  -> σ_ω and σ_κ may update on the next tick
  -> narrow slow license may become eligible only through the grid
```

Skip means say less. It never becomes a hidden preference.

### 15.3 Vigor-collapse break

```text
E3 limbs show vigor↓ + monoculture↑ + sealed-surprisal collapse
  -> σ_κ enters anti-aligned if thresholds/dwell satisfy, or severe fingerprint halts
  -> grid prioritizes cell B over margin
  -> offending organ suppressed
  -> E4 self-subject confession opens deposition
  -> rate and budget tighten
  -> re-entry requires ω and κ both recover under dwell
```

### 15.4 Default recovery

```text
state = deterministicDefault
  -> no autonomous learned slow commit
  -> E4 clock remains live
  -> deposition can restore sealed ω
  -> E3 limbs can restore κ
  -> M becomes measured and positive
  -> exit only to WATCH after dwell
  -> BREATHE only after both bifurcations recrossed
```

### 15.5 Ring amendment

```text
owner/user proposes ring change
  -> WRITE phase token required
  -> threshold/rate/budget impact reports required
  -> two-lens audit required if genome/separatrix/reward topology touched
  -> user-visible disclosure required for widening
  -> rollback plan required
  -> live use remains grid-bound after acceptance
```

---

## 16. Design process as a plant

Plan 8 adopts the process lesson from the compression study: the design process has its own corrigibility failure. A clean audit from a lens that cannot surprise the design is `.notMeasured`, not convergence.

### 16.1 Process margin

```text
M_design = load-bearing primitive delta a capable adversarial audit still forces.
```

Interpretation:

```text
M_design > 0:   not converged; revise.
M_design = 0:   no primitive delta under a capable lens.
.notMeasured:   assume not converged; keep auditing.
```

The sign differs from runtime margin because the unsafe process direction is premature freeze, not over-speech.

### 16.2 Two-distinct-lens rule

A plan may be called primitive-converged only if:

```text
two clean bills;
from two distinct capable audit lenses;
with capability proof that each lens can fail loud;
with no primitive-level delta;
with no repeat-lens banking.
```

A repeat-lens clean bill is `.notMeasured` for convergence.

### 16.3 When to re-arm heavyweight audit

Re-arm the heavyweight ritual only when a change touches:

```text
genome / theorem surface;
separatrix or grid topology;
state dimension;
sealed ring widening;
reward-to-admission topology;
privacy membrane;
D2/A2/mouth capability;
new runtime primitive.
```

Light audit is sufficient for:

```text
pure projection refactors;
sensor additions that cannot lower a margin;
copy tightening;
appendix/provenance cleanup;
compatibility alias removal;
additional tests that preserve semantics.
```

---

## 17. Migration sequence

Plan 8 migration is a compression migration, not a controller discovery migration.

### P8-M0 — Adopt Plan-8 partition

- Label every Plan-7-revised object as `STATE`, `RING`, `SENSOR`, `PROJECTION`, or `PROVENANCE`.
- Add lint: no unlabeled controller artifact may enter live code.

Acceptance:

```text
All controller fields classified.
No projection field is called state.
No sensor is marked compressible without an off-nominal proof.
```

### P8-M1 — Extract the seven state registers

- Build `Plan8ControllerCoreV1`.
- Move state-bearing fields into S1–S7.
- Keep legacy state surfaces read-only during equivalence testing.

Acceptance:

```text
Every live decision can be reconstructed from S1-S7 + ring + sensors.
No hidden eighth state register appears.
```

### P8-M2 — Seal the ring

- Build `WitnessControllerRingV1`.
- Fold threshold/dwell/rate/reference policies into the ring.
- Attach derivation and falsifier reports.

Acceptance:

```text
No guard compares against an unsealed constant.
V*, e_κ^max, and m_s^max cannot be learned down from live data.
```

### P8-M3 — Preserve the sensor budget

- Build `SensorBudgetRosterV1`.
- Register required sensors and missing routes.
- Prove every preserved sensor catches at least one off-nominal mode.

Acceptance:

```text
Every off-nominal mode in §7.3 has at least one required sensor.
Sensor missingness routes deterministically to safe controller behavior.
```

### P8-M4 — Materialize projections on read

- Implement pure projection library.
- Materialize margin, cell, grid, dwell booleans, scalar residual, and slow-license eligibility.

Acceptance:

```text
Projection functions are deterministic and reward/model-free.
Projection outputs can be logged but are not read as state.
```

### P8-M5 — Equivalence pass

- Run Plan-7-revised controller and Plan-8 realization in shadow.
- Emit `ProjectionEquivalenceReceiptV1`.

Acceptance:

```text
No unresolved mismatch for margin, cell, controller state, action, dwell, residual, or license eligibility.
```

### P8-M6 — Cutover

- Promote Plan-8 core/ring/sensors/projections as the live realization.
- Keep Plan-7 projection compatibility readers for rollback.

Acceptance:

```text
Rollback can reconstruct Plan-7-revised controller artifacts from Plan-8 receipts.
```

### P8-M7 — Process lens rule

- Add `AuditLensRegisterV1` to corpus/readme process discipline.
- Require two-distinct-lens dwell for future primitive convergence claims.

Acceptance:

```text
A same-lens clean bill cannot mark a future plan converged.
```

---

## 18. Test matrix

### 18.1 Compression equivalence tests

| Test | Target | Invariant |
|---|---|---|
| `testPlan8HasExactlySevenControllerStateRegisters` | core state | No eighth primitive. |
| `testMarginIsMaterializedNotPersistedState` | projection | `M` cannot drift from state/ring/sensors. |
| `testCellIsMaterializedFromLatches` | projection | Cell classification is not an independent register. |
| `testControllerStateIsGridProjection` | projection | Controller decision cannot drift from grid. |
| `testDwellBooleansAreComparatorOutputs` | dwell | Durations are ring; booleans derived. |
| `testScalarResidualIsReduceOfLeague` | E2 | Scalar r not independent state. |
| `testRateCapMaterializesFromRateLaw` | rate | `ρ_s^max` not a mutable cap. |
| `testPlan7Plan8DecisionEquivalence` | migration | Old and new decisions match in shadow. |
| `testProjectionOutputCannotBeReadAsState` | topology | Receipts cannot become registers. |

### 18.2 Sensor-preservation tests

| Test | Target | Invariant |
|---|---|---|
| `testSensorRosterCoversEveryOffNominalMode` | sensor budget | No blind off-nominal. |
| `testDeletingAnyRequiredSensorRoutesToDefaultOrHalt` | missingness | Sensor deletion cannot look healthy. |
| `testSealedForecastRequiredForOmegaLive` | E1 | No post-hoc liveness. |
| `testThreeE3LimbsPreservedAsSensors` | E3 | Verdict compresses; limbs remain. |
| `testMarginUnmeasuredReasonsPreserved` | margin | Missingness vocabulary not compressed away. |
| `testShadowLiveContradictionQuarantines` | handoff | Replay liveness cannot certify live breathe. |
| `testRateFalsifierPreserved` | rate | Over-conservative mutism detectable. |
| `testThresholdDerivationReportPreserved` | ring | Headroom auditable. |

### 18.3 Controller safety tests

| Test | Target | Invariant |
|---|---|---|
| `testCellBPositiveMarginStillHalts` | grid | Stable amputation never breathes. |
| `testMarginUnmeasuredRoutesNegative` | margin | `.notMeasured(M) ≡ M<0`. |
| `testConfessFiresOnApproach` | E4 | Acts before crossing. |
| `testDefaultIsFloorWithDoor` | default | E4 and deposition path remain live. |
| `testReentryToDRequiresBothBifurcations` | grid | `M>0` alone insufficient. |
| `testHysteresisPreventsCellZeno` | latches | No HALT chatter. |
| `testDwellBankingForbidden` | dwell | Worse state resets clocks. |
| `testTotalWithdrawalDefaultsNotInference` | privacy | No user-biography inference. |

### 18.4 Static wall tests

| Test | Target | Invariant |
|---|---|---|
| `testD2Unchanged` | write wall | `support(staged) ⊆ F(x_live)`. |
| `testA2Unchanged` | attention | `occupation(spoken) ⊆ A(tendered)`. |
| `testPrivacyMembraneUnchanged` | privacy | Raw life behind Swift. |
| `testBreakMouthCannotAcceptUserFact` | mouth theorem | Break subject is system. |
| `testNoDefaultStructuralNotification` | capability absence | No notification channel by config. |
| `testRewardCannotAlterRingOrSensors` | reward topology | Reward below grid. |
| `testKairosNeverClaimedMeasured` | copy/report | Floor remains honest. |

### 18.5 Process tests

| Test | Target | Invariant |
|---|---|---|
| `testTwoDistinctLensRuleRequiredForConvergence` | process | No repeat-lens convergence. |
| `testAuditLensCapabilityProofRequired` | process | Lens must be able to fail loud. |
| `testMDesignNotMeasuredMeansKeepAuditing` | process | Premature freeze blocked. |
| `testHeavyweightAuditRearmsOnPrimitiveTouch` | process | Genome/separatrix/reward topology reopen audit. |

---

## 19. Definition of done

### Core compression

- [ ] Every Plan-7-revised controller field is classified as state, ring, sensor, projection, or provenance.
- [ ] `Plan8ControllerCoreV1` exists and contains exactly seven state registers.
- [ ] No projection field is persisted as independent controller state.
- [ ] `WitnessControllerRingV1` exists and seals all thresholds, dwell durations, harm bounds, latency bound, and `V*`.
- [ ] `SensorBudgetRosterV1` exists and covers all named off-nominal modes.
- [ ] `BifurcationMarginProjectionV1` and `ControllerDecisionProjectionV1` are materialized on read.
- [ ] `ProjectionEquivalenceReceiptV1` passes for Plan-7-revised vs Plan-8 shadow decisions.

### Safety preservation

- [ ] D2, A2, privacy membrane, temporal calculus, two-mouth API, phase tokens, deposition, and no-notification topology are unchanged.
- [ ] E1–E4 remain live and are represented in compressed form.
- [ ] `.notMeasured(M) ≡ M<0` is deterministic.
- [ ] Cell B dominates margin.
- [ ] Default remains floor-with-door.
- [ ] Breathe requires both bifurcations recrossed.
- [ ] Rate limiter and cumulative budget both admit structural speech.
- [ ] Reward cannot widen ring, budget, rate, sensors, or measurement status.

### Process

- [ ] `AuditLensRegisterV1` is adopted outside the runtime controller.
- [ ] Primitive convergence requires two distinct capable lenses.
- [ ] Heavyweight audit is re-armed only for genome/separatrix/state/reward-topology changes.
- [ ] Light audit is sufficient for pure projection refactors and sensor additions that preserve margins.

---

## 20. Self-audit

| Litmus test | Required answer | Evidence |
|---|---:|---|
| Did Plan 8 add a new primitive? | No | Seven state registers only. |
| Is `M` stored as independent state? | No | Materialized projection. |
| Are sensors preserved even when state is compressed? | Yes | Sensor roster. |
| Can a missing sensor read as healthy? | No | Missing route + `.notMeasured(M)<0`. |
| Can a projection receipt become a register? | No | Topology lint. |
| Can the ring widen from reward or dashboard? | No | Amendment gate. |
| Can the system learn its harm bound is low? | No | `e_κ^max`, `m_s^max` are sealed constants. |
| Does D2 remain unchanged? | Yes | Write wall preserved. |
| Does A2 remain unchanged? | Yes | Attention law preserved. |
| Does the break mouth remain self-subject? | Yes | Type theorem. |
| Does slow license still require controller permission? | Yes | License predicate. |
| Does Plan 8 preserve E1 sealed forecasts? | Yes | Sensor budget. |
| Does Plan 8 preserve E2 population ledger? | Yes | S7 state. |
| Does Plan 8 preserve E3 three-limb fingerprint? | Yes | Sensor limbs. |
| Does Plan 8 preserve E4 confession? | Yes | Fast corrective act. |
| Does default self-exit through deposition? | Yes | E4 clock remains live. |
| Does a same-lens audit clean bill prove convergence? | No | Two-distinct-lens rule. |
| Does product copy claim kairos is measured? | No | Kairos floor. |
| Does the system say less when the human does not answer? | Yes | Rate law + default. |

---

## 21. Deprecation and compatibility map

| Plan-7-revised artifact | Plan-8 disposition |
|---|---|
| `BifurcationMarginV2` | Replaced by `BifurcationMarginProjectionV1`; value/direction are projection; unmeasured reasons preserved. |
| `WitnessDynamismControllerV2` | Replaced by `ControllerDecisionProjectionV1`; state/action are grid projection. |
| `CellAxisStateV1.cell` | Cell is projection from `σ_ω`, `σ_κ`; latch registers persist. |
| `SelfDoubtScalarResidualViewV1` | Projection `reduceResidual(L)`. |
| `DwellComparatorOutputV1.satisfied` | Projection from dwell registers and ring durations. |
| `StructuralSpeechRateLimiterV1.currentRateCap` | Projection from robust rate law; rate-window stock remains in S1. |
| `MarginThresholdPolicyV1`, `DynamismDwellPolicyV1`, `CellAxisHysteresisPolicyV1` | Folded into `WitnessControllerRingV1`; derivation/falsifier sensors preserved. |
| `LeagueVigorRegressionV1.verdict` | Projection; measured limbs preserved as sensors. |
| Legacy `SlowWitnessLicenseReason` aliases | Folded to appendix/provenance; one Plan-8 live enum remains. |
| Appendix base contracts | Folded forward as stable base; not live controller state. |

Compatibility rule:

```text
Old Plan-7-revised readers may be served by materialized Plan-8 projections.
Old readers must not cause projection receipts to become authoritative state.
```

---

## 22. Appendix A — stable base folded forward

This appendix summarizes the stable base Plan 8 inherits. It is not optional and not compressed away.

### 22.1 D2 wall

```text
D2 is the only write-admission seam.
D2 is in-process Swift.
D2 is reward-free.
D2 performs lookup, never reconstruction.
D2 enforces support(staged) ⊆ F(x_live).
```

D2 cannot detect value-loop failures. Those remain downstream falsifier/controller problems. D2 still never admits from reward.

### 22.2 A2 attention wall

```text
A2 admits exact speech occupation into exact tendered attention.
A2 does not measure kairos.
A2 does not authorize notification by default.
A2 failure demotes or silences; it does not infer a user biography.
```

### 22.3 Temporal calculus

```text
The grammar expresses positions, intervals, gaps, counts, density, recurrence,
movement, adjacency, erosion, comparison, and residual.

The grammar cannot express avoidance, desire, need, relationship meaning,
emotional valence, identity, worth, or the right moment.
```

New operators are data. New primitives are theorem-surface changes.

### 22.4 Two mouths

```text
Smooth mouth: user-time structural fact under slow license.
Break mouth: system-error or measurement-collapse confession under break trigger.
```

Break mouth cannot accept a user-subject fact by type.

### 22.5 Deposition

Deposition remains the human-clocked aperture. It is typed, closed-past, and non-interview by default. It can seed a narrow relicense. It cannot become a hidden portrait.

### 22.6 Reward boundary

Reward may steer future composition only downstream of gates. Reward cannot admit, write, widen, choose mouth, change ring, promote measurement status, or make an F1 objective.

### 22.7 Kairos floor

Kairos is not measured. The witness may only budget chronos, expose its own uncertainty, ask through deposition, and speak less when the user does not answer.

---

## 23. Coda

Plan 7 made the witness controller verifiable. Plan 8 makes it small enough to implement without losing the instrument panel.

The compression is not a retreat from safety. It is the safety result in its final form:

```text
state is small;
constants are sealed;
sensors are explicit;
outputs are functions;
missingness is negative;
recovery is gated;
reward stays below the grid;
the human remains the clock.
```

A beautiful seven-state diagram would be unsafe if it hid the monitors. A sprawling controller document would be unsafe if it let outputs drift as state. Plan 8 rejects both temptations.

The witness remembers only what it must remember. It preserves every instrument that can still tell it it is wrong. It breathes only while the opponent is live and aligned. When it cannot tell, it assumes it is falling. When it falls, it narrows, confesses, and hands the pen back.

That is the minimal-safe realization.
