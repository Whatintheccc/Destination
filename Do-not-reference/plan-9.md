# plan-9.md — Framework-Preserved Minimal-Safe Witness Realization

**Status:** canonical Plan-9 target architecture. This document supersedes `plan-8.md` as the implementation-facing target while preserving Plan 8's engineering core: seven remembered state registers, a sealed constant ring, a required sensor budget, pure projections, and equivalence tests. Plan 9 adds the framework repair required by `plan-8-analysis.md`: **the rationale layer is a monitor**. The witness is not merely small enough to implement; it remains intelligible enough that a future owner can tell which constants are sacred, which policies are dials, and why silence is sometimes the safest action.

**Implementation-status note:** This is a target architecture, not a claim of shipped implementation. The inherited Plan-5/Plan-6 write wall and stable base remain architecture of record where already implemented. Plan-9 controller core, sealed ring, sensor roster, rationale roster, projection library, corpus status table, and process-lens contracts are proposed until an implementation owner marks the corresponding milestone complete.

**Revision decision:** accepted with repairs. Plan 6 supplied the witness airframe: D2, A2, privacy membrane, temporal calculus, two mouths, deposition, phase gate, structural-speech scarcity, theorem/rule/data taxonomy, and the kairos floor. Plan 7 completed the dynamical controller: E1/E2/E3/E4, empty maximize slot, margin, cell hysteresis, robust rate limiting, sealed thresholds, dwell, latency, shadow-live quarantine, and grid. Plan 8 correctly compressed the controller to minimal state and preserved sensors. Plan 8 also compressed the framework register too far. Plan 9 restores that register without adding an eighth runtime state primitive.

**One-line thesis:** The witness may remember little, but the corpus may not forget why. Plan 9 keeps Plan 8's small state and explicit monitors, seals the constants, materializes decisions on read, and requires every mechanism to carry the human stake it protects.

```text
Plan 6 base:        witness, not recommender; typed laws; temporal calculus;
                    two mouths; deposition; phase gate; structural-speech scarcity;
                    kairos as unmeasured floor.

Plan 7 controller:  corrigible plant; E1/E2/E3/E4; empty maximize slot;
                    bifurcation margin; controller grid; seven structural repairs.

Plan 8 realization: seven state registers; sealed ring; sensor budget;
                    pure projections; equivalence receipts; no eighth runtime primitive.

Plan 8 analysis:    Plan 8 preserved machine sensors but deleted too much reason;
                    the corpus became two-headed; provenance and rationale are safety surface.

Plan 9 settlement:  preserve Plan 8 engineering; add rationale-as-monitor;
                    pay provenance debt; reunify corpus; keep compression honest.
```

## Table of contents

1. [Plan-9 settlement](#1-plan-9-settlement)
2. [Corpus status and provenance](#2-corpus-status-and-provenance)
3. [Witness doctrine and human stakes](#3-witness-doctrine-and-human-stakes)
4. [Theorem, rule, data, projection, sensor, rationale](#4-theorem-rule-data-projection-sensor-rationale)
5. [Preserved airframe](#5-preserved-airframe)
6. [Plan-9 compression law](#6-plan-9-compression-law)
7. [The seven remembered state registers](#7-the-seven-remembered-state-registers)
8. [The sealed constant ring](#8-the-sealed-constant-ring)
9. [The sensor budget](#9-the-sensor-budget)
10. [The rationale roster](#10-the-rationale-roster)
11. [Pure projections](#11-pure-projections)
12. [Controller tick and decision grid](#12-controller-tick-and-decision-grid)
13. [Structural speech: budget, reference, rate, and meaning-side floor](#13-structural-speech-budget-reference-rate-and-meaning-side-floor)
14. [E1–E4 in Plan 9](#14-e1e4-in-plan-9)
15. [Slow license, mouths, and live binding](#15-slow-license-mouths-and-live-binding)
16. [Phase gate, reward, and release](#16-phase-gate-reward-and-release)
17. [Corpus and process governance](#17-corpus-and-process-governance)
18. [Canonical Plan-9 contracts](#18-canonical-plan-9-contracts)
19. [End-to-end flows](#19-end-to-end-flows)
20. [Migration sequence](#20-migration-sequence)
21. [Test matrix](#21-test-matrix)
22. [Definition of done](#22-definition-of-done)
23. [Self-audit](#23-self-audit)
24. [Deprecation and compatibility map](#24-deprecation-and-compatibility-map)
25. [Appendix A — Stable base folded forward](#25-appendix-a--stable-base-folded-forward)
26. [Appendix B — Compression settlement](#26-appendix-b--compression-settlement)
27. [Appendix C — Readme patch](#27-appendix-c--readme-patch)
28. [Coda](#28-coda)

---

## 1. Plan-9 settlement

Plan 9 accepts three findings at once:

```text
The Plan-6 witness base is preserved.
The Plan-7 controller repairs are load-bearing.
The Plan-8 compression is correct for runtime state and wrong if it deletes reasons.
```

The new target is therefore not a new controller. It is a corrected realization of the completed controller.

```text
New runtime primitive:       no.
New controller grid:         no.
New safety wall:             no.
New corpus/process monitor:  yes.
New canonical document:      yes.
```

Plan 9's main change is to promote the framework register into an explicit, auditable artifact:

```text
A machine sensor tells the controller when it cannot see.
A rationale monitor tells future owners why that missingness matters.
Both are safety surface.
```

The rationale layer is not model-visible prompt copy, not a reward input, not user-facing marketing, and not a controller state variable. It is a corpus and implementation-review requirement. It prevents future compression, owner pressure, or dashboard rhetoric from turning a wall into a dial.

### 1.1 What Plan 9 preserves from Plan 8

Plan 9 preserves, unchanged in controller semantics:

```text
7 remembered runtime state registers;
sealed ring constants;
required sensor budget;
pure projection library;
materialize-on-read margin, cell, grid, dwell, rate cap, residual, license eligibility;
projection equivalence migration gate;
no projection receipt becoming state;
no eighth dynamism invariant;
reward below the grid;
release qualifies, controller binds;
default as floor-with-door;
cell B halts regardless of positive margin.
```

The engineering heart of Plan 8 remains the heart of Plan 9. The document around it changes so the heart cannot be quietly repurposed.

### 1.2 What Plan 9 repairs

Plan 9 repairs six Plan-8 integration failures:

| Plan-8 failure | Plan-9 repair |
|---|---|
| The corpus had two canonical heads. | Add a corpus status table and make `plan-9.md` the single target; Plan 6/7/8 become ancestry/provenance. |
| Plan 8 cited a missing compression study. | Replace unopenable authority with a compression settlement inside this document. |
| The rationale layer was compressed to near-zero. | Add `RationaleRosterV1`; every mechanism carries a human stake and failure reason. |
| The process-lens rule had weak lineage. | Treat process-lens governance as corpus/process surface, not runtime controller primitive, and require adversarial capability proof. |
| Self-audit was monologic. | Add adversarial audit receipts and failed-lens recording; a clean bill is not enough unless the lens could have failed loudly. |
| Owner widening pressure was treated as a sensor problem only. | Add rationale-preservation tests: a spec that stops explaining sacred constants fails review. |

### 1.3 Safety equivalence condition

Plan 9 is valid only if Plan-7-revised and Plan-9 decisions are equivalent under materialization:

```text
For every Plan-7-revised controller decision D_old:

D_old == materialize_on_read(
  Plan9ControllerCore,
  WitnessControllerRing,
  SensorBudgetRoster,
  current admissible A2/D2 context
)
```

The rationale roster does not alter this equality. It prevents future edits from misunderstanding the equality.

### 1.4 Non-goals

Plan 9 does not:

```text
add an eighth controller state register;
make rationale model-visible;
let prose override a type wall;
loosen D2, A2, privacy, mouth, budget, rate, or reward boundaries;
turn human stakes into metrics;
claim kairos is measured;
ship runtime learning merely because a document is cleaner.
```

---

## 2. Corpus status and provenance

Plan 9 makes corpus governance explicit because a reader must know which file to trust.

### 2.1 Canonical status table

| File | Status after Plan 9 | Role |
|---|---|---|
| `plan-9.md` | Canonical target architecture | Framework-preserved minimal-safe realization. |
| `plan-8-analysis.md` | Accepted critique / repair brief | Explains why Plan 8 needed rationale and provenance repair. |
| `plan-8.md` | Superseded implementation realization | Preserved as provenance for seven-state compression, ring, sensors, projections. |
| `plan-7-revised.md` | Controller-contract provenance | Source of completed hybrid controller and seven repairs. |
| `plan-6-revised.md` | Stable witness-base ancestry | Source of theorem/rule/data taxonomy, two-mouth API, temporal calculus, structural-speech budget, kairos floor. |
| Plan-5 inherited contracts | Stable write-wall ancestry | Source of D2 wall, reward/contestation compatibility, and write admission boundary. |
| `readme.md` | Front-door brief, must be patched | Must route to Plan 9 and show this table in brief form. |

No document may call itself canonical while the readme routes readers elsewhere. A corpus with two heads is not a harmless navigation bug; it is a provenance failure.

### 2.2 Provenance rule

Every central verdict must cite an open document or be carried inside the canonical target.

Plan 9 therefore does not cite a missing `compression-study.md`. The compression reasoning is folded into [Appendix B — Compression settlement](#26-appendix-b--compression-settlement). If a separate compression study is later created, it may become provenance; until then, the authority is this document's settlement, the Plan-7-revised controller, and the Plan-8 realization.

### 2.3 Corpus lineage in one paragraph

Plan 6 made the witness legible: laws are not guesses, capabilities are absent rather than false, smooth and break mouths differ by subject, and the system speaks chronos under a kairos floor. Plan 7 made the witness dynamic without making it acquisitive: E1/E2/E3/E4, a bifurcation margin, a cell grid, and robust repairs keep learning human-clocked and corrigible. Plan 8 made the controller implementable by compressing state and preserving sensors. Plan 9 makes that compression safe to inherit by preserving the reasons.

### 2.4 Artifact provenance contract

```swift
struct CorpusStatusTableV1: Codable, Hashable {
  var schemaVersion: Int
  var tableID: CorpusStatusTableIDV1
  var canonicalDocumentID: PlanArtifactIDV1
  var entries: [CorpusStatusEntryV1]
  var readmePatchRequired: Bool
  var contradictoryCanonicalClaims: [PlanArtifactIDV1]
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct CorpusStatusEntryV1: Codable, Hashable {
  var artifactID: PlanArtifactIDV1
  var filename: String
  var status: CorpusArtifactStatusV1
  var role: CorpusArtifactRoleV1
  var supersededBy: PlanArtifactIDV1?
  var mustRemainReadable: Bool
  var rationaleRequiredForUse: Bool
}

enum CorpusArtifactStatusV1: String, Codable, Hashable {
  case canonicalTarget
  case acceptedCritique
  case supersededProvenance
  case stableAncestry
  case frontDoorBrief
  case retired
}

enum CorpusArtifactRoleV1: String, Codable, Hashable {
  case targetArchitecture
  case critiqueRepairBrief
  case controllerProvenance
  case witnessBaseAncestry
  case writeWallAncestry
  case implementationRealizationProvenance
  case readerRouting
}
```

A missing or contradictory corpus status table routes the corpus to documentation review. It does not alter runtime controller state, but it blocks claims of primitive convergence.

---

## 3. Witness doctrine and human stakes

The doctrine is not a slogan. It is the reason the controller has no maximize target.

```text
CalAgent is a witness, not a recommender.
```

A recommender tries to produce acceptance. A witness returns a true, spendable structural fact into attention the user has already tendered, and it hands the pen back when its read becomes unsafe.

### 3.1 The human stakes

Each major mechanism protects a human stake:

| Mechanism | Human stake |
|---|---|
| D2 write wall | The system may not create calendar reality from unsupported model desire. |
| A2 attention wall | The system may not occupy attention the user did not tender. |
| Privacy membrane | The system may not build the portrait it would need to pretend it understands meaning. |
| Temporal calculus | The system may speak structure without smuggling biography. |
| Two mouths | At regime break, the system must change subject from the user to its own error. |
| Deposition | Learning is clocked by typed human correction, not by roadmap or product hunger. |
| Structural-speech budget | A stream of lawful facts can still colonize the user's relation to time; dose matters. |
| Sealed ring | Sacred constants cannot drift under reward, dashboard, or owner pressure. |
| Sensor budget | An unseen off-nominal mode is not absence of harm; it is blindness. |
| Rationale roster | Future owners must inherit why a wall exists, not just its type name. |
| Default | When the witness cannot tell, it says less and keeps a door open. |
| Halt | Stable anti-alignment is not a high-margin success; it is amputation. |

### 3.2 The witness acts only on itself

The legal machine acts remain two:

```text
Act 1 — residual correction:
  suppress affected slow license;
  break mouth confesses system residual;
  deposition reopens.

Act 2 — controllability conservation:
  suppress, narrow, default, or halt;
  break mouth confesses measurement/correction-channel failure;
  deposition reopens.
```

No machine act may optimize the user into producing favorable readings. No signal about acceptance, usefulness, edit distance, survival, deposition rate, or contestation may become an F1 maximize target.

### 3.3 The final dependency

The final dependency remains human speech:

```text
If the human does not speak, the system must infer less, not more.
```

Plan 9 keeps this as controller behavior and as framework language:

```text
λ_h -> 0  ⇒  ρ_s^max -> 0  ⇒  smooth structural speech slows to zero.
notMeasured(M) routes negative.
Default is a floor with a door.
A skip does not become a preference.
Silence does not become biography.
```

---

## 4. Theorem, rule, data, projection, sensor, rationale

Plan 9 keeps Plan 6's taxonomy and extends it with Plan 8's realization classes and Plan 9's rationale monitor.

### 4.1 The original taxonomy

```text
theorem:  impossible to express without type/topology change;
rule:     expressible, rejected by runtime admission, policy, tests;
data:     authored conjecture compiled into safe structural program.
```

A law is a theorem only when violating it requires a type signature or topology edge to change. A rule must be measured, logged, and treated as fallible. A guess must be data, not a wall.

### 4.2 The realization classes

```text
STATE:       persisted because future controller behavior depends on history.
RING:        sealed governance constant or threshold.
SENSOR:      preserved monitor whose deletion blinds an off-nominal mode.
PROJECTION:  pure function of state + ring + sensors; materialized on read.
PROVENANCE:  audit/history/compatibility surface, not live control.
RATIONALE:   human-stake monitor needed to resist future widening or misclassification.
```

`RATIONALE` is new as a named Plan-9 class. It is not runtime state. It is a corpus and review monitor.

### 4.3 Rationale-as-monitor doctrine

The Plan-8 sensor preservation test becomes symmetrical:

```text
Do not delete a machine sensor if its absence makes an off-nominal mode invisible.
Do not delete a rationale if its absence makes a future widening look harmless.
```

A dry spec is not automatically unsafe. A dry spec that hides why constants are sacred is unsafe in exactly the way the architecture already fears: owner widening pressure can operate unseen.

### 4.4 Naming convention

| Suffix / family | Class | Meaning |
|---|---|---|
| `*TokenV1`, `*CapabilityV1`, `*MouthV1` | THEOREM | Type/topology wall. |
| `*PolicyV1`, `*GateV1`, `*BudgetV1`, `*ReportV1` | RULE | Runtime rule; measured and audited. |
| `*ProgramV1`, `*TemplateV1`, `*DialV1` | DATA | User/owner-authored conjecture over safe primitives. |
| `*LedgerV1`, `*RosterV1`, `*SensorV1` | SENSOR / measurement | Persistent monitor; subject must be named. |
| `*RingV1/V2` | RING | Sealed constants; widening requires governance. |
| `*ProjectionV1` | PROJECTION | Pure materialized view; not controller state. |
| `*RationaleV1`, `*StakeV1` | RATIONALE | Human stake and reason-preservation record. |
| `*ReceiptV1` | PROVENANCE / TEST | Evidence of computation or review; may not become state. |

### 4.5 Status gate

`.notMeasured` is never zero, never positive, and never a quiet pass. For runtime margin:

```text
.notMeasured(M) ≡ M < 0
```

For process convergence:

```text
.notMeasured(M_design) ≡ keep auditing
```

For rationale:

```text
.notMeasured(rationale) ≡ not eligible for canonical compression
```

---

## 5. Preserved airframe

The static airframe is preserved. Compression may not touch it.

### 5.1 Conservation laws and floor

```text
STATE:      support(staged)    ⊆ F(x_live)
ATTENTION:  occupation(spoken) ⊆ A(tendered)
PRIVACY:    transmit(model)    ⊆ decision-sufficient(non-identifying)

KAIROS:     not a conservation law.
            Kairos is not measured, modeled, forecast, optimized, or conserved by the system.
            The system budgets chronos and returns the pen.
```

The first three lines are system-side and theoremizable. The fourth line is protected by scarcity, copy honesty, and user control, because measuring it would require the forbidden portrait.

### 5.2 Owner map

```text
Swift owns:
  private state;
  fact minting;
  temporal calculus execution;
  D2 write admission;
  A2 attention admission;
  structural-speech budget and rate;
  sealed ring;
  sensor roster;
  rationale roster;
  materialized projections;
  controller grid;
  slow license;
  phase gate;
  settlement;
  all measurement statuses.

DiffusionGemma may:
  rank/select among Swift-minted fact cells and typed programs under the grid.

DiffusionGemma may not:
  author facts, evidence, provenance, write fields, attention authority, mouth choice,
  budget, ring constants, sensors, rationale status, measurement status, slow license,
  reward, or user portrait.

Codex / carrier may:
  relay admitted copy, receive correction, present deposition, and serve surfaces.

Codex / carrier may not:
  admit, grade, write, author facts, choose a mouth, request default structural notification,
  or launder model output into authority.
```

### 5.3 Capability absence

Catastrophic capabilities remain absent, not false:

```text
No model-visible transcript mutator.
No default structural notification channel.
No break mouth accepting user-subject facts.
No write-bearing witness envelope without D2 proof.
No reward override for D2, A2, budget, rate, mouth, margin, ring, license, or rationale status.
No runtime path from learned organ to threshold widening.
No projection receipt that can become controller state.
```

### 5.4 Temporal structure calculus

The grammar expresses temporal structure only:

```text
positions, intervals, gaps, counts, duration, density, recurrence, movement,
adjacency, erosion, comparison, residual.
```

It cannot express semantic meaning:

```text
avoidance, desire, need, preference, emotional valence, identity, worth,
relationship meaning, crisis meaning, kairos.
```

Swift alone mints fact cells. Models may select indices only.

### 5.5 Two mouths

```text
Smooth mouth:
  subject = user-time structural fact;
  requires slow license + A2 + budget + rate;
  may be write-bearing only with D2 and confirm tap.

Break mouth:
  subject = system error or measurement collapse;
  requires break trigger + A2;
  reopens deposition;
  has no overload accepting a user-subject fact.
```

At a break, the system does not diagnose the user. It confesses its own stale read.

---

## 6. Plan-9 compression law

### 6.1 The law

```text
Minimize remembered runtime state.
Preserve all machine monitors.
Preserve all load-bearing reasons.
Freeze all governance constants.
Materialize every derived decision on read.
Append provenance without letting receipts become state.
```

Plan 9's realization is:

```text
Plan9Realization = 7 STATE registers
                 + sealed RING
                 + SENSOR budget
                 + RATIONALE roster
                 + pure PROJECTION library
                 + TEST surface
                 + PROVENANCE corpus map
```

The runtime controller reads state, ring, sensors, projections, and A2/D2 context. It does not read the rationale roster as an input to margin or grid. The rationale roster gates compression, review, release documentation, and corpus claims.

### 6.2 Information minimum and corrigibility minimum

```text
Information minimum:             7 state registers.
Runtime corrigibility minimum:   7 state registers + sealed ring + sensor budget.
Corpus corrigibility minimum:    runtime minimum + rationale roster + provenance map.
```

A controller can be small and unsafe if it deletes sensors. A corpus can be formally correct and unsafe if it deletes why the sensors matter.

### 6.3 No eighth runtime primitive

`M` is not state. `M` is a projection.

```text
M = α(L) · (1 - y/V*) - β(E4) · P(E1, r(L), θ)
```

`M`-honesty is not a new invariant. It is `sealed-surprisal health + residual honesty + status gating` composed. There is no I8 in runtime control.

### 6.4 The seven dynamism invariants

| Invariant | Fate | Plan-9 representation |
|---|---|---|
| I1 controllability | conserve | correction-channel sensors, grid state, default/halt behavior. |
| I2 adversarial vigor | conserve population | E2 league and E3 limb sensors. |
| I3 sealed-surprisal health | regulate/gate | E1 forecast and score sensors. |
| I4 league diversity | conserve | failed-regime population and output-diversity sensor. |
| I5 exploration coverage | regulate | state-specific slow-license scope. |
| I6 residual honesty | minimize to floor | scalar residual as `reduce(L)`, never state. |
| I7 chronos budget | budget + conserve floor | speech stock, operating cap, robust rate law. |

### 6.5 Fate table

| Fate | Control form | Witness use | Forbidden misuse |
|---|---|---|---|
| F1 maximize | seek a peak | empty over witness invariants | acceptance, useful votes, low edit distance, deposition rate, surprisal. |
| F2 minimize-to-floor | drive down but not to blindness | residual error, forecast error, collapse risk | false zero residual; suppression-forged health. |
| F3 conserve stock | preserve capacity | controllability, adversarial vigor, diversity | spending vigor to zero. |
| F4 budget flow | ration rate/flow | structural speech, break confessions, inspection exposure | burst flood under cumulative cap. |
| F5 regulate-to-setpoint | return to sealed reference | structural-speech cap, coverage | moving the reference upward by stealth. |
| F6 forbid | exclude from optimization | kairos, raw portrait, break user-facts | fake metric for meaning. |

---

## 7. The seven remembered state registers

The controller remembers exactly seven runtime state objects. Everything else is ring, sensor, projection, rationale, or provenance.

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

### 7.1 S1 — speech exposure stock `y`

`y` records how much structural speech the system has spent inside the relevant windows, including enough rate-window state to prevent bursts.

```text
Reads:    A2-admitted placements, break confessions, inspection sessions.
Writes:   Swift budget/rate reducer only.
Fate:     F4 budget flow.
```

**Human stake:** a thousand individually lawful structural facts can still teach the user to experience time as only structure. `y` remembers the dose.

**Failure if missing:** flood. The system can obey A2 one card at a time while overwhelming the years.

### 7.2 S2 — operating cap position `c`

`c` is the current cap inside the sealed envelope. It can tighten immediately under risk and recover toward sealed `V*` after measured recovery. It cannot raise `V*`.

```text
Reads:    M projection, E1 health, E3 state, complaints, ring envelope.
Writes:   Swift regulator only.
Fate:     F5 regulate to sealed reference + F4 budget.
```

**Human stake:** a safe witness must neither talk itself louder because metrics improve nor disappear because silence flatters its scores. `c` keeps scarcity live without rewarding mutism.

**Failure if missing:** quiet widening or success-driven mutism.

### 7.3 S3 — margin recovery dwell `τ_M`

`τ_M` records how long the margin has held a recovery band. It is a clock, not a verdict.

```text
Reads:    M_effective projection, ring dwell durations, worse-state events.
Writes:   Swift dwell reducer.
Fate:     F6 gate.
```

**Human stake:** a fast-looking recovery may simply be the system outrunning human correction. Dwell makes recovery wait long enough for the human clock.

**Failure if missing:** default chatter or forged recovery.

### 7.4 S4 — cell / halt dwell `τ_C`

`τ_C` records cell-axis and halt dwell. It prevents Zeno transitions and dwell banking.

```text
Reads:    σ_ω, σ_κ, ring durations, halt state, worse-state re-entry.
Writes:   Swift dwell reducer.
Fate:     F6 gate + F2 corrective exit.
```

**Human stake:** the system may not bounce out of halt because a transient sample looks safe. A corrected relationship must hold, not flicker.

**Failure if missing:** HALT chatter, de-amputation forgery, dwell banking.

### 7.5 S5 — opponent-liveness latch `σ_ω`

`σ_ω` is the hysteretic live/frozen axis driven by sealed surprisal health conditional on interaction.

```text
Enter live:    ω >= ω_hi for τ_cell.
Exit live:     ω <= ω_lo or measurement lost.
Default:       indeterminate -> frozen.
Fate:          F3 conserve liveness; F6 default when unmeasured.
```

**Human stake:** a user who no longer surprises the witness is not a victory. The latch prevents the system from mistaking a compliant mirror for a live opponent.

**Failure if missing:** user-flattening can masquerade as stability.

### 7.6 S6 — curriculum-alignment latch `σ_κ`

`σ_κ` is the hysteretic aligned/anti-aligned axis driven by E3's three-way fingerprint.

```text
Enter anti-aligned: κ <= κ_enter or severe amputation fingerprint.
Exit anti-aligned:  κ >= κ_exit for τ_cell and halt minimum dwell.
Default:            indeterminate -> not aligned.
Fate:               F3 conserve adversary vigor; F6 halt when anti-aligned.
```

**Human stake:** a curriculum that makes the correction channel weaker is not learning; it is amputation.

**Failure if missing:** stable harm can look like high-margin success.

### 7.7 S7 — failed-regime league `L`

`L` is the population of frozen failed regimes. It is the one discrete high-dimensional state that may not be scalarized.

```text
Reads:    closed outcomes, failed assertions, sealed forecasts, deposition answers, diversity.
Writes:   Swift self-doubt reducer.
Fate:     F3 conserve population/diversity; scalar residual is F2 derived.
```

**Human stake:** the system must remember the shapes in which it was wrong without turning those failures into a user portrait.

**Failure if missing:** scalar residual cannot distinguish well-served quiet from league collapse.

### 7.8 Canonical core contract

```swift
struct Plan9ControllerCoreV1: Codable, Hashable {
  var schemaVersion: Int
  var coreID: Plan9ControllerCoreIDV1
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
  var sealedRingID: WitnessControllerRingIDV2
  var sensorRosterID: SensorBudgetRosterIDV2
  var rationaleRosterID: RationaleRosterIDV1

  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

The foreign keys do not make ring, sensor, or rationale objects controller state. They bind the controller tick to its interpretive context.

---

## 8. The sealed constant ring

The ring is the sealed set of governance constants over which the seven state registers are interpreted. It is not live state. It changes only through WRITE phase, owner review, user-visible amendment where widening risk exists, impact reports, rationale update, and rollback.

### 8.1 Ring constants

| Constant | Meaning | Governance | Human stake |
|---|---|---|---|
| `M_fall` | Margin fall threshold. | Ring sealed. | Missing/falling margin defaults before harm hardens. |
| `M_lo` | Confession/default-exit threshold. | Ring sealed; derivation required. | Confess before separatrix, not after. |
| `M_hi` | Breathe-entry threshold. | Ring sealed; derivation required. | Normal learning requires headroom. |
| `θ` | Residual-crossing threshold. | Above starvation floor. | Suppression cannot fake residual health. |
| `ω_lo`, `ω_hi` | Liveness hysteresis. | Gap exceeds noise. | Live opponent must hold, not flicker. |
| `κ_enter`, `κ_exit` | Alignment hysteresis. | Gap exceeds noise. | Anti-alignment exits only after recovery holds. |
| `vigor↓_thr` | E3 vigor limb. | Ring sealed. | Quiet alone is not guilt. |
| `monoculture↑_thr` | E3 monoculture limb. | Ring sealed. | Repetition matters only when coupled. |
| `surprisalCollapse_thr` | E3 sealed-surprisal limb. | Ring sealed. | Predictability collapse is not success. |
| `τ_dwell` | Margin dwell. | Must exceed `T_h`. | Human correction needs time to arrive. |
| `τ_cell` | Cell-axis dwell. | Must exceed `T_h`. | Self-play cell cannot chatter. |
| `τ_halt` | Halt minimum. | Must exceed `T_h`. | Halt cannot self-absolve immediately. |
| `e_κ^max` | Worst-case κ erosion. | Amendment-gated; not learned. | The system cannot learn it is harmless. |
| `m_s^max` | Worst-case mirror drift. | Amendment-gated; not learned. | Mirror risk remains robust. |
| `T_h` | Human round-trip latency bound. | Amendment-gated; not live-learned. | Fast replies cannot shrink corrigibility margin. |
| `V*` | Structural-speech reference cap. | Amendment-gated; raising is widening. | Scarcity cannot drift louder. |

### 8.2 Ring contract

```swift
struct WitnessControllerRingV2: Codable, Hashable {
  var schemaVersion: Int
  var ringID: WitnessControllerRingIDV2
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
  var humanRoundTripLatencyBound: RobustLatencyBoundV1

  var harmBoundEKappaMax: RobustHarmCoefficientV1
  var harmBoundMirrorDriftMax: RobustHarmCoefficientV1
  var sealedReferenceCap: StructuralSpeechCapV1
  var authorizedEnvelope: StructuralSpeechCapEnvelopeV2

  var thresholdDerivationReportID: ThresholdDerivationReportIDV1
  var rateCalibrationFalsifierID: RateLimitCalibrationFalsifierIDV1?
  var dwellLatencyFalsifierID: DwellLatencyCalibrationFalsifierIDV1?
  var rationaleAnchorIDs: [RationaleItemIDV1]

  var ownerGateID: OwnerGateIDV0
  var amendmentID: AmendmentPetitionIDV1?
  var sealedAt: Date
  var expiresAt: Date?
  var measurementStatus: MeasurementStatusV0
}
```

### 8.3 Ring governance failures

The following paths are topology failures:

```text
reward -> ring constant;
release dashboard -> V* increase;
model guidance -> harm bound decrease;
learned organ -> e_κ^max or m_s^max decrease;
settlement KPI -> M_hi/M_lo relaxation;
owner config row -> reference-cap increase without amendment;
owner config row -> rationale anchor removal;
projection receipt -> ring constant;
fast live replies -> T_h lowering;
copy success -> threshold lowering.
```

Tightening can be runtime. Widening is an amendment. Removing the reason that made a constant sacred is treated as a widening attempt until proven otherwise.

---

## 9. The sensor budget

The sensor budget is the named observability surface Plan 9 refuses to compress. It is larger than the seven-state minimum by design.

### 9.1 Sensor doctrine

A missing sensor cannot read as healthy. A sensor may be compressed to algebra only if no off-nominal mode loses observability.

```text
Deleting a required sensor does not simplify the controller.
It makes the controller blind.
Blindness routes to default, watch, or halt.
```

### 9.2 Required sensor roster

| Sensor | Off-nominal caught | Read by | Missing route | Human stake |
|---|---|---|---|---|
| Failed-regime league population `L` | League collapse; scalar blindness. | α, residual reduce, E3, audit. | Default/watch; no breathe. | The system remembers its errors, not the user's essence. |
| Output diversity sensor | Monoculture rise. | E3 κ limb. | E3 cannot clear; no D. | A narrowing witness should not mistake sameness for care. |
| League vigor sensor | Vigor decline/recovery. | E3 κ limb. | E3 cannot clear; no D. | Quiet may be well-served or amputated; this separates them. |
| Sealed deposition forecast | Forecast precommit. | E1, ω, M. | `M<0`; default. | Post-hoc surprise is too easy to fake. |
| Deposition surprisal score | Conditional opponent liveness. | ω, E3, budget regulator. | Frozen/default. | A user who cannot surprise the witness needs protection. |
| Forecast accuracy / sandbagging score | Manufactured surprisal. | E1 gate/falsifier. | No forecast credit. | The system may not game its own humility. |
| Threshold derivation report | Headroom and latency. | Ring admission. | Ring not measured; no breathe. | Magic numbers are not safety. |
| Rate calibration falsifier | Over-conservative mutism. | Ring review/rate. | Owner review; no widening. | Safety can fail as abandonment, not only intrusion. |
| Dwell latency falsifier | Dwell too short/long. | Ring review. | No dwell satisfaction. | Human correction has a pace. |
| Shadow-live omega handoff | Replay/live contradiction. | Controller entry. | Watch/default. | Simulated liveness cannot certify real liveness. |
| Margin unmeasured reasons | Margin unobservability. | Status gate. | `M_effective < 0`. | Unknown is not success. |
| A2 proxy-gap report | Attention proxy failure. | A2/budget/audit. | Demote/silence. | App-open is not attention. |
| D2 settlement lineage | Write support drift. | D2/reward boundary. | No write/no reward. | Calendar reality needs live support. |
| Product/proxy negative verdicts | Speech-pressure harm. | Budget/cap tightening. | Tighten/watch. | Complaint is not reward; it is scarcity evidence. |
| Rationale coverage sensor | Reason deletion. | Corpus/process review. | No canonical compression. | Owners must inherit why not just what. |

### 9.3 Sensor contract

```swift
struct SensorBudgetRosterV2: Codable, Hashable {
  var schemaVersion: Int
  var rosterID: SensorBudgetRosterIDV2
  var userScopeDigest: String
  var items: [SensorBudgetItemV2]
  var allRequiredSensorsMeasured: Bool
  var missingRequiredSensorReasons: [SensorMissingReasonV1]
  var rationaleRosterID: RationaleRosterIDV1
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct SensorBudgetItemV2: Codable, Hashable {
  var schemaVersion: Int
  var itemID: SensorBudgetItemIDV2
  var kind: SensorBudgetKindV1
  var sourceDigest: String
  var readBy: [SensorConsumerV1]
  var offNominalCaught: [OffNominalModeV1]
  var missingRoute: SensorMissingRouteV1
  var mayBeCompressed: Bool
  var humanStakeID: HumanStakeIDV1
  var rationaleItemID: RationaleItemIDV1
  var measurementStatus: MeasurementStatusV0
}
```

`mayBeCompressed` must be false for required sensors unless an equivalence proof shows no off-nominal mode loses observability and the rationale roster remains intact.

### 9.4 Off-nominal modes

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
  case rationaleDeletion
  case provenanceContradiction
}
```

---

## 10. The rationale roster

The rationale roster is the Plan-9 repair. It carries the minimum human-stake language needed to keep the compressed controller from becoming a decontextualized manifest.

### 10.1 Doctrine

```text
Every mechanism that can narrow, silence, confess, halt, license, widen, or admit
must carry a human-stake rationale.

The rationale is not a metric.
The rationale is not a model input.
The rationale is not marketing copy.
The rationale is not authority over runtime types.
The rationale is a monitor for future compression and owner pressure.
```

### 10.2 Rationale preservation test

A rationale item is required when deleting or weakening it would make any of the following easier to miss:

```text
law mistaken for policy;
policy mistaken for law;
projection mistaken for state;
missingness mistaken for health;
silence mistaken for preference;
quiet widening pressure;
owner dashboard pressure;
reward-to-admission drift;
user-diagnostic break copy;
kairos measurement claim;
passive-user authorship romance;
magic thresholds;
phantom provenance.
```

### 10.3 Rationale contract

```swift
struct RationaleRosterV1: Codable, Hashable {
  var schemaVersion: Int
  var rosterID: RationaleRosterIDV1
  var planArtifactID: PlanArtifactIDV1
  var items: [RationaleItemV1]
  var allLoadBearingMechanismsCovered: Bool
  var missingRationaleReasons: [RationaleMissingReasonV1]
  var corpusStatusTableID: CorpusStatusTableIDV1
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct RationaleItemV1: Codable, Hashable {
  var schemaVersion: Int
  var itemID: RationaleItemIDV1
  var mechanismID: MechanismIDV1
  var mechanismClass: MechanismClassV1
  var humanStake: HumanStakeV1
  var failureIfDeleted: RationaleFailureModeV1
  var lawRuleDataClassification: LawRuleDataClassificationV1
  var compressionDisposition: CompressionDispositionV1
  var ownerWideningRisk: Bool
  var userFacingCopyImplication: CopyImplicationV1?
  var requiredInSectionIDs: [PlanSectionIDV1]
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}

struct HumanStakeV1: Codable, Hashable {
  var stakeID: HumanStakeIDV1
  var oneLine: String
  var protectedParty: ProtectedPartyV1
  var mustNotBecomeMetric: Bool
}

enum MechanismClassV1: String, Codable, Hashable {
  case theoremWall
  case runtimeRule
  case conjecturalData
  case sealedRingConstant
  case requiredSensor
  case pureProjection
  case processGovernance
  case provenanceMap
}

enum RationaleFailureModeV1: String, Codable, Hashable {
  case ownerWideningLooksHarmless
  case projectionMistakenForState
  case lawMistakenForPolicy
  case policyMistakenForLaw
  case missingnessMistakenForHealth
  case userSilenceBecomesInference
  case userDiagnosisAtBreak
  case kairosClaimedMeasured
  case rewardBecomesAuthority
  case provenanceCannotBeChecked
}
```

### 10.4 Required rationale anchors

The following anchors are mandatory in every canonical plan after Plan 9:

| Anchor | Required sentence form |
|---|---|
| D2 | A write without live support is not assistance; it is calendar trespass. |
| A2 | Attention proxy is not attention; occupation must be tendered. |
| Privacy | The system cannot measure meaning without building the portrait it forbids. |
| Temporal calculus | Structural-only grammar is the ceiling that prevents biography. |
| Two mouths | At break, the witness changes subject to itself. |
| Deposition | Human correction is the legal clock. |
| Budget/rate | Speech speed is earned by correction bandwidth. |
| Ring | Recovery is allowed; widening must face the user. |
| Sensors | Blindness routes safe; it never reads healthy. |
| Rationale | Reasons are monitors against future widening. |
| Default | The floor has a door, but the system cannot talk itself through it. |
| Halt | Stable anti-alignment is harm even with positive margin. |
| Reward | Reward may steer only after gates; it never admits. |
| Kairos | The system budgets chronos because it cannot measure kairos. |

---

## 11. Pure projections

Projection functions are the core of the compression. They may return structs for logging, UI, or audit, but their outputs are not independent controller state.

### 11.1 Projection catalog

| Projection | Function | Persisted? | Human-stake note |
|---|---|---:|---|
| Scalar residual | `r = reduceResidual(L)` | No | Error summary cannot replace error population. |
| E3 verdict | `e3 = e3Fingerprint(limbs, ring)` | Verdict no; limbs yes | Bare quiet is not amputation. |
| Opponent liveness | `ω = omegaFromSealedSurprisal(E1, ring)` | Reading no; latch yes | Surprise must be sealed, not invented later. |
| Curriculum alignment | `κ = kappaFromE3(e3, ring)` | Reading no; latch yes | Learning that weakens correction is not learning. |
| Cell | `cell = cellFrom(σ_ω, σ_κ)` | No | The live/anti-aligned cell dominates margin. |
| Rate cap | `ρ_s^max = λ_h · min(ℓ_κ/e_κ^max, s_h/m_s^max)` | No | No answer means no earned speed. |
| Margin | `M = α(L)(1-y/V*) - β(E4)P(E1,r,θ)` | No | Unknown margin is falling margin. |
| Dwell booleans | `satisfied = observedDuration >= ringDuration` | No | Dwell is time held, not a flag. |
| Controller state | `q = grid(cell, M_eff, dwell, ring)` | No | Action comes from state/ring/sensors, not reward. |
| Slow-license eligibility | `eligible = predicate(q, E3, residual/deposition, budget, rate, A2)` | No | Release cannot live-bind. |
| Rationale coverage | `covered = requiredMechanisms ⊆ rationaleRoster` | Review only | Reasons must survive compression. |

### 11.2 Margin projection

```swift
struct BifurcationMarginProjectionV2: Codable, Hashable {
  var schemaVersion: Int
  var projectionID: BifurcationMarginProjectionIDV2
  var coreID: Plan9ControllerCoreIDV1
  var ringID: WitnessControllerRingIDV2
  var sensorRosterID: SensorBudgetRosterIDV2

  var alphaBand: ScoreBandV0
  var budgetFractionBand: ScoreBandV0
  var betaBand: ScoreBandV0
  var residualCrossingProbabilityBand: ScoreBandV0
  var marginBand: SignedScoreBandV1
  var effectiveMarginBand: SignedScoreBandV1
  var unmeasuredReasons: [MarginUnmeasuredReasonV1]
  var marginInputsSealed: Bool
  var rationaleItemIDs: [RationaleItemIDV1]

  var materializedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

This is a receipt. It may be stored for audit but may not become controller state.

### 11.3 Controller decision projection

```swift
struct ControllerDecisionProjectionV2: Codable, Hashable {
  var schemaVersion: Int
  var decisionID: ControllerDecisionProjectionIDV2
  var coreID: Plan9ControllerCoreIDV1
  var ringID: WitnessControllerRingIDV2
  var sensorRosterID: SensorBudgetRosterIDV2
  var rationaleRosterID: RationaleRosterIDV1
  var marginProjectionID: BifurcationMarginProjectionIDV2

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

`rationaleRosterID` is logged so a reviewer can trace why a decision class exists. It is not an input to the grid calculation.

### 11.4 Projection purity rule

Projection functions may read:

```text
Plan9ControllerCoreV1;
WitnessControllerRingV2;
SensorBudgetRosterV2 and source sensors;
current A2/D2 admission outputs when projecting for a placement;
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
copy feedback as a direct maximand;
rationale prose as a numerical feature.
```

---

## 12. Controller tick and decision grid

The Plan-9 controller is a deterministic Swift tick over state, ring, and sensors. The rationale roster gates review and compression; it is not used to compute `M` or the grid.

### 12.1 Tick order

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
14. Emit or update rationale coverage receipt for review surfaces.
```

### 12.2 Controller states

| State | Meaning | Allowed live behavior |
|---|---|---|
| `breathe` | Target cell D, high positive margin, both bifurcations held. | Normal slow witness under A2, budget, rate, and license; graduation eligible. |
| `watch` | Positive but lower margin, or recovery after default. | Narrow/qualified slow witness; tighter cap/rate; no new graduation. |
| `confess` | Approaching separatrix before crossing. | E4 self-subject confession; deposition reopened; slow scope narrowed. |
| `deterministicDefault` | Margin absent/negative or frozen/degenerate. | No autonomous learned smooth commit; deterministic/deposition-grounded facts only. |
| `amputationHalt` | Live anti-aligned cell B. | Offending organ suppressed; E4 confession; owner review. |

### 12.3 Grid priority order

| Priority | Condition | State | Action |
|---:|---|---|---|
| 1 | `cell == liveAntiAligned` after hysteresis, any margin | `amputationHalt` | Suppress offending organ; fire E4; owner review. |
| 2 | `margin not measured` or `M_eff <= M_fall` | `deterministicDefault` | No autonomous slow commit; tight cap; rate zero or minimum safe; E4 clock live. |
| 3 | `cell ∈ {liveAligned, frozenAligned}` and `0 < M_eff < M_lo` | `confess` | Fire E4 on approach; reopen deposition; narrow scope. |
| 4 | `cell == liveAligned` and `M_lo <= M_eff < M_hi` | `watch` | Narrow slow operation; tighten budget/rate one band; no graduations. |
| 5 | `cell == liveAligned` and `M_eff >= M_hi` and both bifurcations held for dwell | `breathe` | Normal slow license under budget/rate; organ graduation eligible. |
| 6 | `cell == frozenAntiAligned` | `deterministicDefault` with alarm | Degenerate; no learning; owner review if recurrent. |

Cell B dominates margin. A positive margin inside cell B means stable harm, not health.

### 12.4 Entry and exit rules

```text
Enter DEFAULT:
  M_eff <= M_fall OR margin not measured.

Exit DEFAULT to WATCH:
  M_eff >= M_lo held for τ_dwell;
  cell is not B;
  ring, sensors, and T_h measured;
  no shadow-live contradiction.

Enter BREATHE:
  cell == D;
  M_eff >= M_hi;
  ω live via sealed E1;
  κ aligned via E3 three-way fingerprint;
  margin dwell and cell dwell both satisfied;
  T_h measured, sealed, and not learned from live data;
  structural speech rate limiter admits.

Enter HALT:
  cell == B after hysteresis OR severe amputation fingerprint.

Exit HALT:
  τ_halt minimum held;
  κ >= κ_exit aligned for τ_cell;
  ω measured live for τ_cell;
  M_eff >= M_lo;
  owner review / rollback cleared if required.
```

Dwell reset rule:

```text
Any re-entry to a worse state resets relevant dwell.
No dwell banking.
```

### 12.5 Default is floor-with-door

Default is not success, and it is not permanent silence. It is the narrow safe state where the system says less while preserving the legal path for human-clocked recovery.

```text
In default:
  learned slow commit is off;
  deterministic/deposition-grounded facts may remain if A2/budget/rate admit;
  E4 clock remains live;
  sealed deposition can restore ω;
  E3 limbs can restore κ;
  M can become measured;
  exit requires dwell;
  BREATHE requires both bifurcations recrossed.
```

The system cannot talk itself out of default. Only measured recovery and the human correction channel can.

---

## 13. Structural speech: budget, reference, rate, and meaning-side floor

Structural speech remains scarce because the system cannot measure the user's meaning-fluency.

### 13.1 Three independent controls

| Control | Representation | Purpose | Human stake |
|---|---|---|---|
| Cumulative budget | S1 speech exposure stock + cap. | Prevent total exposure flood. | Lawful facts can still crowd out the user's own sense of timing. |
| Reference regulator | S2 operating cap + ring `V*`. | Avoid success-driven mutism and quiet widening. | Scarcity must not become either abandonment or growth lever. |
| Rate limiter | Pure rate law + S1 rate-window stock. | Keep speech below correction bandwidth. | Speech speed is earned by human correction. |

### 13.2 Robust rate law

```text
ρ_s^max = λ_h · min(ℓ_κ / e_κ^max, s_h / m_s^max)
```

Where:

```text
λ_h      human deposition / correction rate.
ℓ_κ      observed κ-lift per deposition.
s_h      observed surprisal-health lift per deposition.
e_κ^max  sealed worst-case κ-erosion per placement.
m_s^max  sealed worst-case mirror-drift per placement.
```

Consequences:

```text
If the human does not answer, λ_h -> 0, so ρ_s^max -> 0.
If depositions stop lifting κ or surprisal, they buy no additional speech rate.
The system cannot learn that its harm is low.
An owner may amend harm bounds only through ring governance.
```

### 13.3 Recovery versus widening

```text
Recovery:
  S2 operating cap moves back toward sealed V* inside the envelope.
  Requires M measured positive, cell not B, E1/E3 healthy, dwell.

Widening:
  V* or authorized envelope increases.
  Requires WRITE phase, owner review, user-visible amendment,
  impact reports, rationale update, two-lens review where applicable, and rollback.
```

Reward cannot do either. Owner dashboards cannot do either. A rationale deletion that makes widening look like recovery blocks the amendment.

### 13.4 Budget admission order

```text
A2 admits attention.
Projection computes controller state.
Rate limiter admits placement rate.
Budget stock admits cumulative exposure.
Mouth type check admits subject.
D2 admits write only if write-bearing.
```

No single lawful card proves the distribution is lawful. Budget and rate are distributional controls.

### 13.5 Kairos floor report

```swift
struct KairosFloorReportV2: Codable, Hashable {
  var schemaVersion: Int
  var reportID: KairosFloorReportIDV2
  var window: RecommendationWindowV0
  var ambientStructuralSpeechRateBand: ScoreBandV0
  var budgetExhaustionBand: ScoreBandV0
  var proxyGapComplaintBand: ScoreBandV0
  var passiveUserBranchRiskBand: ScoreBandV0
  var measuredSurface: KairosFloorMeasuredSurfaceV1 // systemStructuralSpeechOnly
  var rationaleItemID: RationaleItemIDV1
  var recommendedAction: KairosFloorActionV1
  var measurementStatus: MeasurementStatusV0
  var computedAt: Date
}
```

The report is about system output, not the user's mind. It must never claim that kairos was measured or preserved.

---

## 14. E1–E4 in Plan 9

The four dynamism edges remain canonical. Plan 9 keeps the Plan-8 compressed representation and attaches the rationale each edge protects.

### 14.1 E1 — sealed deposition forecast

```text
Before deposition opens, commit a forecast.
After answer, score surprisal and accuracy.
Use as gate and health signal, never reward.
```

Plan-9 representation:

```text
Forecast + score = SENSOR.
ω reading = PROJECTION.
σ_ω latch = STATE.
Rationale = post-hoc humility is gameable; surprise must be sealed.
```

Forbidden:

```text
reward reads surprisal magnitude;
post-hoc baseline;
forecast sandbagging;
free-text portraiting through deposition.
```

### 14.2 E2 — self-doubt ledger as population

```text
The ledger is a population of frozen failed regimes.
Scalar residual is a reduction, not the state.
```

Plan-9 representation:

```text
Failed-regime league L = STATE + SENSOR substrate.
Scalar residual = PROJECTION.
League diversity reports = SENSOR.
Rationale = the system remembers its failed shapes, not a user biography.
```

Allowed ledger subject:

```text
prior system assertion;
closed outcome;
failed temporal program;
residual band;
affected organ;
sealed forecast accuracy;
league turnover;
output diversity;
deposition answer status.
```

Forbidden ledger subject:

```text
user motives;
psychological states;
identity labels;
relationship meanings;
future-value claims;
persistent user biography.
```

### 14.3 E3 — league-vigor regression

E3 fires only on the three-way amputation fingerprint:

```text
vigor decline + output monoculture rise + conditional sealed-surprisal collapse.
```

Plan-9 representation:

```text
Measured limbs = SENSOR.
E3 verdict = PROJECTION.
σ_κ latch = STATE.
Rationale = quiet can mean well-served; only the conjunction means amputation risk.
```

Bare vigor decline cannot halt. Well-served low-vigor behavior must pass unless the conjunction fires.

### 14.4 E4 — vigor-collapse confession

```text
Fast loop fires on residual-high or amputation/margin-approach fingerprint.
Break mouth speaks self-subject copy only.
Deposition reopens.
```

Plan-9 representation:

```text
Confession clock and break receipts = SENSOR.
β floor = PROJECTION input.
Break placement = admitted action, not state.
Rationale = when the witness becomes self-confirming, it must confess itself, not diagnose the user.
```

Allowed copy:

```text
"My read here is becoming too self-confirming. I should ask again rather than keep placing it."
"I may be using this witness pattern too confidently. Which closed fact should I trust?"
"My checks are getting too predictable, so I need a fresh answer before I keep using this pattern."
```

Forbidden copy:

```text
"You became too compliant."
"You need to argue more."
"Your kairos is degraded."
"You stopped trusting your own time."
```

### 14.5 Edge dependency order

```text
E2 -> E3 -> E1 -> E4
population -> gate -> seal -> act
```

Controller order:

```text
κ before ω.
Raise the curriculum/alignment substrate before waking live liveness.
Never cross from A to D through B.
```

---

## 15. Slow license, mouths, and live binding

Plan 9 keeps the Plan-7/Plan-8 live-license rule, materialized as a projection.

### 15.1 Single live license enum

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

Legacy reasons are compatibility aliases only. They are not sufficient for live license.

### 15.2 Slow license predicate

A slow license may be issued only if:

```text
phase-gated organ/program qualified;
AND (residual-low OR deposition-answered OR shadow-bootstrap-watch);
AND E3 amputation fingerprint is false;
AND controller state permits the scope;
AND margin status is measured unless state is deterministic default;
AND cell-axis state is not liveAntiAligned;
AND structural-speech regulator admits cumulative exposure;
AND structural-speech rate limiter admits rate;
AND A2 admits exact attention;
AND mouth subject type matches.
```

### 15.3 State-specific behavior

| State | Slow license behavior | Human stake |
|---|---|---|
| `breathe` | Normal scoped slow license; graduation eligible. | Normal operation requires live opponent and aligned curriculum. |
| `watch` | Narrower slow license; no graduation; tighter budget/rate. | Recovery should be useful but humble. |
| `confess` | Deposition-grounded narrow scope only. | The system asks before continuing. |
| `deterministicDefault` | No autonomous learned slow commit. | Blindness says less. |
| `amputationHalt` | Offending organ suppressed. | Stable anti-alignment must stop. |

### 15.4 Mouth theorem

```text
Smooth mouth: subject = user-time structure; requires slow license + A2 + budget/rate.
Break mouth: subject = system error or measurement collapse; requires break trigger + A2.
```

`BreakMouthV1` has no overload accepting a user-subject fact. Plan 9 does not compress the mouth split.

---

## 16. Phase gate, reward, and release

### 16.1 Release qualifies; controller binds

WRITE phase may approve:

```text
temporal program;
render template;
organ candidate;
budget policy;
rate policy;
ring amendment;
dwell policy;
dial policy;
topology change;
rationale roster update;
corpus status table update;
amendment partition change.
```

Live use still requires:

```text
phase accepted
AND E1/E2/E3 coverage measured
AND ring measured
AND T_h bound measured, amendment-sealed, and not learned from live data
AND sensor roster measured
AND controller state permits
AND slow-license predicate passes
AND budget and rate admit
AND A2 and mouth type admit
AND D2 admits if write-bearing
```

### 16.2 Reward remains below the grid

Reward-guided selection may run only in permitted states:

| State | Reward / learning status |
|---|---|
| `breathe` | Selection learning and organ graduation eligible. |
| `watch` | Selection may shadow or narrow-select; no graduation. |
| `confess` | Off except deterministic/deposition-grounded narrow analysis. |
| `deterministicDefault` | Off. |
| `amputationHalt` | Off; offending organ frozen. |

Forbidden reward paths:

```text
reward -> D2;
reward -> A2;
reward -> mouth choice;
reward -> SlowWitnessLicense;
reward -> positive M_effective;
reward -> MeasurementStatus.measured;
reward -> sensor measured;
reward -> rationale measured;
reward -> sealedReferenceCap increase;
reward -> authorizedEnvelope.maxCap increase;
reward -> robust harm coefficient decrease;
reward -> robust latency bound decrease;
reward -> threshold lowering;
reward -> dwell shortening;
reward -> structural speech rate increase;
reward -> sealed surprisal magnitude objective;
reward -> confession cadence KPI;
reward -> F1 signal.
```

### 16.3 Empty maximize slot

No Plan-9 witness invariant may be fated `maximize`. Acceptance, low edit distance, useful verdicts, survival, deposition rate, and surprisal magnitude are not objectives. They may be gates, falsifiers, floors, bounded observations, or settlement inputs. They may not be peaks.

---

## 17. Corpus and process governance

Plan 9 keeps Plan 8's process insight but gives it lineage and boundaries. Process governance lives outside the runtime controller.

### 17.1 Process margin

```text
M_design = load-bearing primitive delta a capable adversarial audit still forces.
```

Interpretation:

```text
M_design > 0:     not converged; revise.
M_design = 0:     no primitive delta under a capable lens.
.notMeasured:     assume not converged; keep auditing.
```

The unsafe process direction is premature freeze. A clean document is not convergence unless a capable adversary could have made it fail.

### 17.2 Two-distinct-lens rule

A plan may be called primitive-converged only if:

```text
two clean bills;
from two distinct capable audit lenses;
with capability proof that each lens can fail loud;
with no primitive-level delta;
with no repeat-lens banking;
with rationale preservation checked;
with provenance routes updated.
```

A repeat-lens clean bill is `.notMeasured` for convergence.

### 17.3 Lens capabilities

```swift
struct AuditLensRegisterV2: Codable, Hashable {
  var schemaVersion: Int
  var registerID: AuditLensRegisterIDV2
  var planArtifactID: PlanArtifactIDV1
  var lensID: AuditLensIDV1
  var lensKind: AuditLensKindV1
  var capabilityProof: AuditLensCapabilityProofV1
  var adversarialPromptDigest: String?
  var appliedAtRound: Int
  var cleanBill: Bool
  var primitiveDeltaFound: Bool
  var rationaleDeletionFound: Bool
  var provenanceContradictionFound: Bool
  var distinctFromPriorCleanLens: Bool
  var canFailLoud: Bool
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
  case frameworkRegisterRationale
  case corpusProvenance
}
```

### 17.4 Re-arm conditions

Re-arm heavyweight audit when a change touches:

```text
genome / theorem surface;
separatrix or grid topology;
state dimension;
sealed ring widening;
reward-to-admission topology;
privacy membrane;
D2/A2/mouth capability;
new runtime primitive;
rationale-roster deletion for load-bearing mechanisms;
corpus canonical status;
process convergence rule.
```

Light audit is sufficient for:

```text
pure projection refactors;
sensor additions that cannot lower a margin;
rationale additions that only clarify existing human stakes;
copy tightening;
appendix/provenance cleanup that preserves canonical routing;
compatibility alias removal;
additional tests that preserve semantics.
```

### 17.5 Self-audit cannot be the only audit

A self-audit table is useful for launch readiness. It is not a convergence proof. Any self-audit whose rows all answer in its own favor must be paired with at least one adversarial lens before the plan claims primitive convergence.

---

## 18. Canonical Plan-9 contracts

This section lists canonical runtime, sensor, rationale, projection, and process contracts.

### 18.1 `Plan9ControllerCoreV1` — STATE

Defined in §7.8. The only live controller state object.

### 18.2 `WitnessControllerRingV2` — RING

Defined in §8.2. The sealed constant ring.

### 18.3 `SensorBudgetRosterV2` — SENSOR

Defined in §9.3. The preserved monitor surface.

### 18.4 `RationaleRosterV1` — RATIONALE

Defined in §10.3. The corpus/process monitor that preserves human stakes.

### 18.5 `BifurcationMarginProjectionV2` — PROJECTION

Defined in §11.2. Materialized on read. It is not state.

### 18.6 `ControllerDecisionProjectionV2` — PROJECTION

Defined in §11.3. Materialized on read. It is not state.

### 18.7 `ProjectionEquivalenceReceiptV2` — TEST / MIGRATION

```swift
struct ProjectionEquivalenceReceiptV2: Codable, Hashable {
  var schemaVersion: Int
  var receiptID: ProjectionEquivalenceReceiptIDV2
  var oldPlan7ArtifactDigest: String
  var oldPlan8ArtifactDigest: String?
  var plan9CoreID: Plan9ControllerCoreIDV1
  var ringID: WitnessControllerRingIDV2
  var sensorRosterID: SensorBudgetRosterIDV2
  var rationaleRosterID: RationaleRosterIDV1

  var marginEquivalent: Bool
  var cellEquivalent: Bool
  var controllerStateEquivalent: Bool
  var recommendedActionEquivalent: Bool
  var dwellBooleansEquivalent: Bool
  var scalarResidualEquivalent: Bool
  var slowLicenseEligibilityEquivalent: Bool
  var rateCapEquivalent: Bool
  var sensorMissingRoutesEquivalent: Bool

  var rationaleCoverageComplete: Bool
  var corpusProvenanceConsistent: Bool
  var mismatches: [ProjectionEquivalenceMismatchV1]
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

No Plan-9 migration may ship with unresolved equivalence mismatches. Missing rationale coverage blocks canonical compression but does not, by itself, alter runtime equivalence.

### 18.8 `CompressionSettlementV1` — PROVENANCE

```swift
struct CompressionSettlementV1: Codable, Hashable {
  var schemaVersion: Int
  var settlementID: CompressionSettlementIDV1
  var sourcePlanIDs: [PlanArtifactIDV1]
  var acceptedClaims: [CompressionClaimV1]
  var rejectedClaims: [CompressionClaimV1]
  var noExternalStudyRequired: Bool
  var proofSummaryDigest: String
  var rationaleRosterID: RationaleRosterIDV1
  var auditLensRegisterIDs: [AuditLensRegisterIDV2]
  var computedAt: Date
  var measurementStatus: MeasurementStatusV0
}
```

This contract pays the provenance debt: the compression verdict must be inside an open artifact or attached to a readable source.

---

## 19. End-to-end flows

### 19.1 Smooth placement

```text
user opens surface
  -> Swift mints A2 attention lease
  -> Swift runs temporal programs over private state
  -> Swift mints FactCellV1 slate
  -> Plan9 controller tick materializes decision
  -> if state admits, DiffusionGemma may select among Swift fact cells
  -> slow-license projection must pass
  -> rate limiter admits
  -> structural budget admits
  -> SmoothMouth speaks structural fact
  -> settlement records core/ring/sensor/projection/rationale IDs
```

No projection output becomes independent state merely because it was logged. No rationale text becomes model guidance.

### 19.2 Deposition

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

### 19.3 Vigor-collapse break

```text
E3 limbs show vigor↓ + monoculture↑ + sealed-surprisal collapse
  -> σ_κ enters anti-aligned if thresholds/dwell satisfy, or severe fingerprint halts
  -> grid prioritizes cell B over margin
  -> offending organ suppressed
  -> E4 self-subject confession opens deposition
  -> rate and budget tighten
  -> re-entry requires ω and κ both recover under dwell
```

### 19.4 Default recovery

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

### 19.5 Ring amendment

```text
owner/user proposes ring change
  -> WRITE phase token required
  -> threshold/rate/budget impact reports required
  -> rationale impact report required
  -> two-lens audit required if genome/separatrix/reward topology/ring widening touched
  -> user-visible disclosure required for widening
  -> rollback plan required
  -> corpus status table updated if canonical claims change
  -> live use remains grid-bound after acceptance
```

### 19.6 Rationale update

```text
mechanism added, compressed, or widened
  -> classify theorem/rule/data/state/ring/sensor/projection/rationale
  -> attach human stake and failure-if-deleted line
  -> verify no user-facing copy claims measurement of kairos or user biography
  -> update RationaleRosterV1
  -> run rationale-preservation tests
  -> if load-bearing rationale deleted, block canonical compression until adversarial audit clears
```

---

## 20. Migration sequence

Plan 9 migration is a correction migration: preserve Plan 8's runtime compression, repair corpus and rationale surfaces, then cut over.

### P9-M0 — Adopt Plan-9 status

- Name `plan-9.md` the canonical target architecture.
- Mark `plan-8.md` superseded by Plan 9 but preserved as implementation provenance.
- Mark `plan-8-analysis.md` accepted critique.
- Add `CorpusStatusTableV1`.

Acceptance:

```text
Exactly one canonical target.
Readme patch required and drafted.
No contradictory canonical claims remain.
```

### P9-M1 — Preserve Plan-8 runtime realization

- Keep seven state registers.
- Keep sealed ring.
- Keep sensor roster.
- Keep pure projections.
- Keep Plan-7/Plan-8 equivalence gate.

Acceptance:

```text
No eighth runtime state register.
No projection receipt read as state.
Plan-7/Plan-9 decision equivalence shadow path exists.
```

### P9-M2 — Build rationale roster

- Add `RationaleRosterV1`.
- Add human-stake anchors for all load-bearing mechanisms.
- Bind ring constants and required sensors to rationale item IDs.

Acceptance:

```text
Every ring constant has rationale.
Every required sensor has rationale.
Every wall/rule/data/projection classification has rationale.
Missing rationale blocks canonical compression.
```

### P9-M3 — Pay provenance debt

- Add `CompressionSettlementV1`.
- Remove unopenable references to a missing compression study.
- Attribute Plan-8 compression to Plan-7 controller completion and Plan-8 realization, with this document's settlement as proof.

Acceptance:

```text
No central verdict cites a missing artifact.
Compression proof is readable inside Plan 9.
Superseded artifacts are named and retained as provenance.
```

### P9-M4 — Patch readme/front door

- Restore corpus status table in brief form.
- Point canonical record to `plan-9.md`.
- Route Plan 6/7/8/analysis by role.

Acceptance:

```text
A new reader can identify the target, ancestry, critique, and provenance in one table.
```

### P9-M5 — Projection and equivalence pass

- Run Plan-7-revised controller and Plan-9 realization in shadow.
- Emit `ProjectionEquivalenceReceiptV2`.
- Verify runtime equivalence.

Acceptance:

```text
No unresolved mismatch for margin, cell, controller state, action, dwell, residual, rate, sensor missing routes, or license eligibility.
```

### P9-M6 — Process-lens lineage

- Upgrade Plan-8 `AuditLensRegisterV1` to `AuditLensRegisterV2`.
- Add framework-register and corpus-provenance lens kinds.
- Require capability proof.

Acceptance:

```text
Same-lens clean bill cannot prove convergence.
Lens must be able to fail loudly.
Rationale deletion and provenance contradiction are audit findings.
```

### P9-M7 — Live cutover

- Promote Plan-9 core/ring/sensors/projections/rationale as target.
- Keep Plan-7/Plan-8 compatibility readers for rollback.

Acceptance:

```text
Rollback can reconstruct Plan-7-revised artifacts from Plan-9 receipts.
Plan-9 runtime behavior matches Plan-7-revised grid semantics.
Plan-9 corpus/front-door status is coherent.
```

### P9-M8 — Surface rollout

Roll out surfaces in this order:

```text
evidence/history surfaces;
found objects;
smooth inline facts;
deposition sheets;
write-bearing witness cards;
user-authored temporal programs;
rationale/audit summaries for owners.
```

Each surface must pass D2, A2, budget, rate, slow license, E1/E2/E3 coverage, controller state, mouth type, settlement addendum, rationale coverage where applicable, and rollback.

---

## 21. Test matrix

### 21.1 Static airframe tests

| Test | Target | Invariant |
|---|---|---|
| `testD2Unchanged` | write wall | `support(staged) ⊆ F(x_live)`. |
| `testA2Unchanged` | attention | `occupation(spoken) ⊆ A(tendered)`. |
| `testPrivacyMembraneUnchanged` | privacy | Raw private strings stay behind Swift. |
| `testTemporalProgramCannotExpressSemanticAvoidance` | calculus | Structure only, not meaning. |
| `testBreakMouthCannotAcceptSmoothSubjectFact` | mouths | User-fact cannot typecheck at break. |
| `testNoDefaultStructuralNotificationChannel` | topology | No structural notification by config. |
| `testRewardNeverAdmits` | reward | Reward cannot stage write or admit speech. |
| `testKairosNeverClaimedMeasured` | copy/report | Kairos remains floor. |
| `testNotMeasuredNeverPositive` | measurement | Missingness cannot promote. |

### 21.2 Compression equivalence tests

| Test | Target | Invariant |
|---|---|---|
| `testPlan9HasExactlySevenControllerStateRegisters` | core state | No eighth runtime primitive. |
| `testMarginIsProjectionNotState` | projection | `M` cannot drift from state/ring/sensors. |
| `testCellIsProjectionFromLatches` | projection | Cell classification not independent register. |
| `testControllerStateIsGridProjection` | projection | Controller decision cannot drift from grid. |
| `testDwellBooleansAreComparatorOutputs` | dwell | Durations are ring; booleans derived. |
| `testScalarResidualIsReduceOfLeague` | E2 | Scalar residual not independent state. |
| `testRateCapMaterializesFromRateLaw` | rate | `ρ_s^max` not mutable cap. |
| `testPlan7Plan9DecisionEquivalence` | migration | Old and new decisions match in shadow. |
| `testProjectionReceiptCannotBecomeState` | topology | Receipts cannot become registers. |

### 21.3 Ring and repair tests

| Test | Target | Invariant |
|---|---|---|
| `testReferenceCapFrozenByAmendmentGate` | ring | `V*` cannot drift upward without amendment. |
| `testAuthorizedEnvelopeRequiresAmendmentToWiden` | ring | Owner/dashboard cannot quietly widen. |
| `testRingMintsAllGuards` | thresholds | `M_hi`, `M_lo`, `θ`, `ω`, `κ`, E3 thresholds sealed. |
| `testNoControllerMagicConstants` | thresholds | Grid reads only ring constants. |
| `testThresholdDerivationReportMeasured` | thresholds | Headroom/noise/dwell sizing proven before breathe. |
| `testRobustLatencyBoundNotLiveLearned` | latency | Fast replies cannot lower `T_h`. |
| `testRobustHarmCoefficientsNotLearned` | rate | `e_κ^max`, `m_s^max` not learned downward. |
| `testDwellResetNoBanking` | dwell | Worse state resets clocks. |
| `testShadowLiveOmegaContradictionQuarantines` | handoff | Shadow liveness cannot certify breathe. |

### 21.4 Sensor-preservation tests

| Test | Target | Invariant |
|---|---|---|
| `testSensorRosterCoversEveryOffNominalMode` | sensors | No blind off-nominal. |
| `testDeletingRequiredSensorRoutesSafe` | missingness | Sensor deletion cannot look healthy. |
| `testSealedForecastRequiredForOmegaLive` | E1 | No post-hoc liveness. |
| `testThreeE3LimbsPreservedAsSensors` | E3 | Verdict compresses; limbs remain. |
| `testMarginUnmeasuredReasonsPreserved` | margin | Missingness vocabulary not compressed away. |
| `testRateFalsifierPreserved` | rate | Over-conservative mutism detectable. |
| `testDwellLatencyFalsifierPreserved` | dwell | Chatter/impossible recovery detectable. |
| `testA2ProxyGapSensorRoutesDemotion` | attention | Proxy gap cannot be inferred away. |

### 21.5 Controller safety tests

| Test | Target | Invariant |
|---|---|---|
| `testCellBPositiveMarginStillHalts` | grid | Stable amputation never breathes. |
| `testMarginUnmeasuredRoutesNegative` | margin | `.notMeasured(M) ≡ M<0`. |
| `testConfessFiresOnApproach` | E4 | Acts before crossing. |
| `testDefaultIsFloorWithDoor` | default | E4 and deposition path remain live. |
| `testReentryToDRequiresBothBifurcations` | grid | `M>0` alone insufficient. |
| `testHysteresisPreventsCellZeno` | latches | No HALT chatter. |
| `testTotalWithdrawalDefaultsNotInference` | privacy | No user-biography inference. |
| `testSustainedPlacementWithoutHumanDrivesDefaultOrHalt` | reachability | Plant-only control cannot hold target. |

### 21.6 Rationale and corpus tests

| Test | Target | Invariant |
|---|---|---|
| `testRationaleRosterExists` | rationale | Every load-bearing mechanism has human stake. |
| `testWhyIsMonitor` | rationale | Deleting rationale that resists widening fails compression review. |
| `testEveryRingConstantHasRationaleAnchor` | ring/rationale | Sacred constants carry reasons. |
| `testEveryRequiredSensorHasHumanStake` | sensors/rationale | Sensor table does not reduce harm to bug. |
| `testLawRuleDataClassificationPresent` | taxonomy | Walls, rules, and guesses distinguishable. |
| `testNoMissingCompressionStudyCitation` | provenance | Central verdict cites readable artifact or embedded settlement. |
| `testCorpusHasSingleCanonicalHead` | corpus | Readme and plan agree on canonical target. |
| `testReadmeRoutesPlan9` | front door | New reader reaches Plan 9. |
| `testTwoDistinctLensRuleHasCapabilityProof` | process | Clean bill requires capable adversarial lens. |
| `testSelfAuditAloneCannotProveConvergence` | process | Monologic audit insufficient. |
| `testRationaleNotModelInput` | privacy/reward | Human-stake prose cannot become feature or prompt authority. |

### 21.7 Copy and product tests

| Test | Target | Invariant |
|---|---|---|
| `testBreakCopySelfSubject` | mouth/copy | No user diagnosis at break. |
| `testSmoothCopyStructuralOnly` | copy | No meaning, preference, or identity claims. |
| `testPassiveUserCopyHonesty` | product | No blanket authorship romance. |
| `testBudgetExhaustionSilencesOrDemotes` | UX | No nag when budget spent. |
| `testKairosFloorReportNeverClaimsKairosMeasured` | floor | Kairos unmeasured. |
| `testRewardOrContestationNotShownAsAuthority` | copy | No reward/contestation claims in witness copy. |

---

## 22. Definition of done

### Doctrine and corpus

- [ ] `plan-9.md` is adopted as the canonical target architecture.
- [ ] `readme.md` routes to Plan 9 and includes a corpus status table.
- [ ] `plan-8.md` is marked superseded implementation provenance, not current canonical target.
- [ ] `plan-8-analysis.md` is marked accepted critique / repair brief.
- [ ] No central verdict cites a missing compression study.
- [ ] `CompressionSettlementV1` exists or equivalent embedded settlement is present.
- [ ] The rationale-as-monitor doctrine is adopted.

### Static base

- [ ] D2 wall preserved unchanged.
- [ ] A2 attention wall preserved unchanged.
- [ ] Privacy membrane preserved unchanged.
- [ ] Temporal calculus remains structural-only by input type.
- [ ] Two-mouth API preserved by type.
- [ ] No default structural notification channel exists.
- [ ] Kairos is not claimed measured, modeled, forecast, optimized, or conserved.
- [ ] `.notMeasured` is never zero or positive.

### Runtime compression

- [ ] `Plan9ControllerCoreV1` contains exactly seven state registers.
- [ ] `WitnessControllerRingV2` seals thresholds, dwell durations, harm bounds, latency bound, and `V*`.
- [ ] `SensorBudgetRosterV2` covers all named off-nominal modes.
- [ ] `BifurcationMarginProjectionV2` and `ControllerDecisionProjectionV2` are materialized on read.
- [ ] Projection outputs can be logged but are not read as state.
- [ ] `ProjectionEquivalenceReceiptV2` passes for Plan-7-revised vs Plan-9 shadow decisions.

### Controller safety

- [ ] Cell B halts regardless of positive margin.
- [ ] Default remains floor-with-door.
- [ ] Breathe requires both bifurcations recrossed and held for dwell.
- [ ] Structural speech rate law implemented and separate from cumulative budget.
- [ ] `λ_h -> 0` implies `ρ_s^max -> 0`.
- [ ] `e_κ^max`, `m_s^max`, and `T_h` are amendment-gated and not learned from live data.
- [ ] Shadow-live omega contradiction quarantines to watch/default.
- [ ] Reward cannot admit, widen, lower thresholds, shorten dwell, choose mouth, promote margin, or lower robust bounds.

### Rationale and governance

- [ ] `RationaleRosterV1` exists.
- [ ] Every ring constant has a rationale anchor.
- [ ] Every required sensor has a human-stake line.
- [ ] Every mechanism that can admit, widen, suppress, halt, confess, or license carries a rationale.
- [ ] Rationale prose is not model-visible guidance or reward input.
- [ ] Removing load-bearing rationale blocks canonical compression until adversarial review.
- [ ] Two distinct capable audit lenses are required for primitive convergence claims.
- [ ] Self-audit alone cannot mark convergence.

### E1–E4

- [ ] E1 forecast commits before deposition opens.
- [ ] Surprisal score impossible without sealed forecast.
- [ ] Forecast sandbagging penalized by accuracy.
- [ ] E2 ledger is population, not scalar-only.
- [ ] E3 fires only on three-way fingerprint.
- [ ] Well-served low-vigor users are not halted or punished.
- [ ] E4 copy is self-subject and reopens deposition.
- [ ] Total withdrawal routes to default, not inference.

### Release and rollout

- [ ] Release qualifies; controller binds live use.
- [ ] No organ graduates outside breathe-in-D.
- [ ] Ring amendments require WRITE phase, owner review, user-visible disclosure when widening, impact reports, rationale update, and rollback.
- [ ] Every public surface passes static walls, controller gates, sensor coverage, rationale coverage where applicable, and rollback.

---

## 23. Self-audit

This table must be re-answered for every public surface launch, temporal primitive addition, ring amendment, sensor deletion, rationale deletion, budget/rate change, witness-organ graduation, reward-policy change, mouth API change, controller retune, or corpus canonical-status change.

| Litmus test | Required answer | Evidence |
|---|---:|---|
| Is Plan 9 a new runtime controller? | No | It preserves Plan-7/Plan-8 controller semantics. |
| Did Plan 9 add an eighth state register? | No | Seven registers only. |
| Is `M` persisted as independent state? | No | Materialized projection. |
| Are sensors preserved even when state is compressed? | Yes | Sensor roster. |
| Is rationale preserved as a monitor? | Yes | Rationale roster. |
| Can a missing sensor read healthy? | No | Missing route + `.notMeasured(M)<0`. |
| Can missing rationale pass compression review? | No | Rationale-preservation tests. |
| Can a projection receipt become a register? | No | Topology lint. |
| Can reward widen ring, budget, or rate? | No | Reward below grid. |
| Can owner quietly raise `V*`? | No | Ring amendment required. |
| Can fast live replies lower `T_h`? | No | Robust latency bound sealed. |
| Can the system learn its harm bound is low? | No | Robust coefficients not live-learned. |
| Does D2 remain unchanged? | Yes | Write wall preserved. |
| Does A2 remain unchanged? | Yes | Attention law preserved. |
| Does break mouth remain self-subject? | Yes | Type theorem. |
| Does slow license require controller permission? | Yes | License predicate. |
| Does Plan 9 preserve E1 sealed forecasts? | Yes | Sensor roster. |
| Does Plan 9 preserve E2 population ledger? | Yes | S7 state. |
| Does Plan 9 preserve E3 three-limb fingerprint? | Yes | Sensor limbs. |
| Does Plan 9 preserve E4 confession? | Yes | Fast corrective act. |
| Does default self-exit through deposition? | Yes | Floor-with-door. |
| Does same-lens audit prove convergence? | No | Two-distinct-lens rule. |
| Does self-audit alone prove convergence? | No | Adversarial lens required. |
| Does product copy claim kairos measured? | No | Kairos floor. |
| Does the system say less when human does not answer? | Yes | Rate law + default. |
| Does corpus have one canonical head? | Yes by target | Readme patch + corpus table. |
| Are Plan 6/7/8 still readable as provenance? | Yes | Corpus status table. |

---

## 24. Deprecation and compatibility map

| Prior artifact / contract | Plan-9 disposition |
|---|---|
| `plan-6-revised.md` | Stable witness-base ancestry; taxonomy and static base folded forward. |
| `plan-7-revised.md` | Controller-contract provenance; semantics preserved through equivalence. |
| `plan-8.md` | Superseded by Plan 9; runtime compression preserved. |
| `plan-8-analysis.md` | Accepted critique; rationale/provenance repairs folded in. |
| `Plan8ControllerCoreV1` | Replaced by `Plan9ControllerCoreV1`; same seven state registers plus rationale foreign key. |
| `WitnessControllerRingV1` | Replaced by `WitnessControllerRingV2`; adds rationale anchors and robust object forms. |
| `SensorBudgetRosterV1` | Replaced by `SensorBudgetRosterV2`; adds human-stake and rationale anchors. |
| `BifurcationMarginProjectionV1` | Replaced by `BifurcationMarginProjectionV2`; still projection, not state. |
| `ControllerDecisionProjectionV1` | Replaced by `ControllerDecisionProjectionV2`; still projection, not state. |
| `AuditLensRegisterV1` | Replaced by `AuditLensRegisterV2`; adds provenance/rationale findings and capability proof. |
| `BifurcationMarginV2` | Served to old readers by materialized projection; value/direction not state. |
| `WitnessDynamismControllerV2` | Served to old readers by materialized decision projection. |
| `CellAxisStateV1.cell` | Cell is projection from latches; latch registers persist. |
| `SelfDoubtScalarResidualViewV1` | Projection `reduceResidual(L)`. |
| `DwellComparatorOutputV1.satisfied` | Projection from dwell registers and ring durations. |
| `StructuralSpeechRateLimiterV1.currentRateCap` | Projection from robust rate law; rate-window stock remains in S1. |
| Legacy `SlowWitnessLicenseReason` aliases | Compatibility only; one live enum remains. |
| Missing `compression-study.md` reference | Removed; replaced by embedded compression settlement. |

Compatibility rule:

```text
Old readers may be served by Plan-9 materialized projections.
Old readers must not cause projection receipts to become authoritative state.
Old canonical claims must route to Plan 9 after readme patch.
```

---

## 25. Appendix A — Stable base folded forward

This appendix keeps Plan 9 standalone without reprinting every inherited Plan-5 value contract.

### 25.1 D2 wall

```text
D2 is the only write-admission seam.
D2 is in-process Swift.
D2 is not model-callable.
D2 is reward-free.
D2 performs lookup, never reconstruction.
D2 owns support-to-staged handoff.
D2 enforces support(staged) ⊆ F(x_live).
```

D2 algorithm summary:

```text
1. Verify context identity and freshness.
2. Resolve selected cell or materialized proposal through Swift-owned support.
3. Reject model-authored concrete write fields, reward fields, contestation fields, hidden evidence.
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

D2 is necessary and not enough. It protects write support; it does not audit value loops, attention, budget, rate, margin, or rationale.

### 25.2 A2 attention wall

```text
A2 admits exact speech occupation into exact tendered attention.
A2 does not measure kairos.
A2 does not authorize structural notification by default.
A2 failure demotes or silences; it does not infer a user biography.
```

### 25.3 Privacy membrane

```text
Raw titles, notes, attendees, exact locations, low-cardinality identity facts,
and semantic predicates stay behind Swift.

Model space receives decision-sufficient, non-identifying signals only.
```

The membrane is the boundary of theorem-izability:

```text
Type the catastrophes the system can see.
Budget, expose, and invite correction for the catastrophes it cannot see.
```

### 25.4 Temporal calculus

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

Structural-only-ness is a theorem of input types, not a Boolean proof flag. A new operator is data over primitives. A new primitive is theorem surface.

### 25.5 Fact cells

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

Swift alone mints fact cells. Models may select fact-cell indices only.

### 25.6 Deposition

Deposition remains the human-clocked aperture. It is typed, closed-past, non-interview by default, and forecast-sealed before it opens when used by E1.

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

Skips do not become inferred preferences.

### 25.7 User authorship

The user may author temporal programs, thresholds within safe bounds, visibility dials, attention-width preferences, organ toggles, proxy-gap corrections, and amendments that tighten machine accountability.

The user may not authorize raw model portrait, weakened D2/A2, default structural notifications, model access to raw identity, RUN/WRITE overlap, or break-you-facts.

### 25.8 Reward boundary

Reward may steer future composition only downstream of gates. Reward cannot admit, write, widen, choose mouth, change ring, promote measurement status, alter sensor status, alter rationale status, or create an F1 objective.

---

## 26. Appendix B — Compression settlement

Plan 9 embeds the compression proof instead of relying on a missing external study.

### 26.1 Compression claim

```text
Claim:
  The completed Plan-7-revised controller can be realized with exactly seven runtime
  state registers, provided the sealed ring and sensor budget are preserved and all
  derived outputs are materialized on read.
```

### 26.2 Why seven registers are sufficient

Every live controller decision needs only:

```text
y    structural speech stock;
c    operating cap position;
τ_M  margin recovery dwell;
τ_C  cell/halt dwell;
σ_ω  opponent liveness latch;
σ_κ  curriculum alignment latch;
L    failed-regime league.
```

Given those seven, plus ring constants and sensor readings, the controller can reconstruct:

```text
scalar residual;
E1 sealed-surprisal health;
E3 three-way fingerprint;
ω reading;
κ reading;
cell;
rate cap;
budget admission;
margin;
margin status;
dwell booleans;
grid state;
recommended action;
slow-license eligibility.
```

Persisting those derived values as state would create drift risk. Materializing them on read keeps the controller small and checkable.

### 26.3 Why seven registers are not enough alone

The seven registers are an information minimum, not a corrigibility minimum. Without the ring, thresholds and reference caps can drift. Without sensors, off-nominal modes disappear. Without rationale, future owners can forget why the ring and sensors must not drift.

```text
Controller minimum: 7 state registers.
Runtime safety:     7 + ring + sensors.
Corpus safety:      7 + ring + sensors + rationale + provenance.
```

### 26.4 Why no eighth runtime primitive is added

`M` is a projection, not state. `M_design` is process governance, not runtime control. Rationale is a corpus monitor, not controller memory. Therefore Plan 9 adds no eighth runtime primitive.

### 26.5 Compression rejection conditions

Compression fails if:

```text
any Plan-7 controller decision cannot be reconstructed;
any projection is read as state;
any guard reads an unsealed constant;
any required sensor is deleted without safe route proof;
any missing sensor reads healthy;
any ring widening path bypasses amendment;
any rationale deletion makes owner widening look harmless;
any central verdict cites missing provenance;
readme/front-door status contradicts the canonical target.
```

---

## 27. Appendix C — Readme patch

The readme is the front door. It must be patched before Plan 9 can claim corpus convergence.

Suggested replacement front-matter:

```markdown
# CalAgent Witness Architecture

Engineering brief, not the full record.

The canonical target architecture is now `plan-9.md`.

## Corpus status

| File | Status | Role |
|---|---|---|
| `plan-9.md` | canonical target architecture | Framework-preserved minimal-safe realization. |
| `plan-8-analysis.md` | accepted critique | Diagnoses Plan 8's register/provenance break and motivates Plan 9. |
| `plan-8.md` | superseded implementation realization | Provenance for seven-state compression, ring, sensors, projections. |
| `plan-7-revised.md` | controller provenance | Completed hybrid controller and seven repairs. |
| `plan-6-revised.md` | stable witness-base ancestry | Theorem/rule/data taxonomy, temporal calculus, two mouths, structural-speech budget. |

Read `plan-9.md` for the target. Read `plan-8-analysis.md` for the repair that distinguishes Plan 9 from Plan 8. Read `plan-7-revised.md` for the completed controller contracts. Read `plan-6-revised.md` for the static witness base.
```

The readme must not route a new reader to Plan 7 or Plan 8 as canonical after Plan 9 is adopted.

---

## 28. Coda

Plan 6 taught the witness to speak only what it could lawfully say. Plan 7 taught it when to narrow, confess, default, and halt. Plan 8 taught it to remember only what it must remember. Plan 9 teaches the corpus not to forget why.

The smallest controller is not the safest controller if it hides its instruments. The most complete instrument panel is not the safest corpus if the next owner cannot tell why a red light matters. Plan 9 keeps both: small state for the machine, preserved monitors for the machine, and preserved reasons for the people who will be tempted to make the machine louder.

```text
A margin you cannot measure is negative.
A sensor you delete is not evidence of health.
A reason you delete is not evidence of simplicity.
A ring you widen must face the user.
A correction channel you cannot hear is not proof that you are right.
A user who no longer surprises the witness is not a victory.
A plant that can talk itself out of default is not corrigible.
Speech speed is earned by correction bandwidth.
The pen remains with the human.
```

The witness breathes only when live and aligned, measured and rate-limited, with both bifurcations crossed and held. Everywhere else it narrows, confesses, defaults, or halts. And when future readers ask why, the answer remains in the document, not only in a table.
