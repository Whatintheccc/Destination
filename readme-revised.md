# CalAgent — Architecture & First Principles

> Engineering reference. The full record — Swift struct bodies, the test
> matrix, the M0–M8 migration — lives in `plan-5-revised.md`; this brief
> keeps the holdings and cites the plan for the rosters. The role map is
> engineering-only and never surfaces in user-facing copy.

CalAgent **manufactures** one calendar recommendation — *what*, *when*, and *why
it fits today* — staged as a single card you accept with one tap. It composes a
recommendation no list had to enumerate in advance; it does not retrieve the
best row from a prebuilt table. Three components do this:

- **Swift** — the **framework / infrastructure**: the calendar backend that owns
  every liability-bearing mechanic (raw state, feasible support `F(x)`,
  evidence, validators, D2, provenance, fingerprints, writes, undo, lineage,
  measurement).
- **DiffusionGemma** — the **calculator**: the expensive model that composes the
  recommendation *shape*; it owns no authority.
- **Codex** — the **server / order-taker**: the carrier that relays the request
  and serves only what Swift admits.

The thing capable enough to compose your day is never allowed to change it. That
is the whole architecture in one line — every section below is this severance
projected onto one surface (authoring, conditioning, admission, measurement):

```
support(staged) ⊆ F(x_live)        // capability rises, authority never does

Codex may relay and serve.
DiffusionGemma may compose and propose.
Swift must validate, admit, write, and measure.
Codex and DiffusionGemma must never grade, admit, or launder their own outputs.
```

## 1. The three components

Each holds an asymmetric role under one doctrine — **capability is separated
from authority**; the most capable component (DiffusionGemma) is never the most
*sovereign* ("authority" = who may admit and write).

| Component | Role | Owns | Borrows | Interface | Trust boundary | Failure mode |
|---|---|---|---|---|---|---|
| **Codex** | server / order-taker | turn capture, bounded clarification, relay, admitted-card presentation, dismissal/reroll | Swift request context, the staged card, server-minted actions | `RecommendationTurnRequestV0`/`ResponseV0`; `POST /v1/carrier/turn` | no admission, grading, writes, or provenance; payload carries only Swift-staged artifacts + server-minted actions | over-talks, asks an unnecessary question, or serves a card Swift did not admit |
| **DiffusionGemma** | calculator (composition) | semantic composition, why-line drafting, unresolved-need detection, non-authority proposals | Swift-furnished decision-sufficient statistics, relation chips, slate cells (SELECT), shape constraints (PROPOSE) | `RecommendationSelectionInfillV0` (SELECT); `RecommendationShapeProposalV0` (PROPOSE) | authors no identity, title, time, calendar target, source kind/strength, evidence hash, provenance, fingerprint, verdict, or action | hallucinates, overclaims personalization, or copies authority fields |
| **Swift** | framework / infrastructure | raw state, decision-sufficient statistics, `F(x)`, evidence, validators, D2, provenance, fingerprints, write gates, undo, lineage, value signals | non-authority model proposals and the user's confirmation | `RecommendationContextV1`, `SlateCellV0`, D2 binding, `ProposalEnvelopeV0`, `AllowedActionV0` | admission-critical owner of all liability-bearing state | over-prunes, silently truncates, leaks identity, admits stale support, or treats missing measurement as zero |
| **Relational Prep Station** | Swift-owned prep | relation chips: topology, heuristic flags, coverage | raw Swift state and closed Swift tags | `RelationChipV0` / `…SetV0` / `…CoverageV0` | consultable conditioning only; never support, provenance, or admission | becomes a semantic graph or steers admission by implication |

## 2. Standardized notations

| Symbol / convention | Meaning |
|---|---|
| **`F(x)`** | Swift's **feasible support** — the candidate universe Swift owns and enumerates; in SELECT, enumerated as `slateOfferedV0` (`F(x) = [SlateCellV0]`). |
| **`F(x_live)`** | The **live, revalidated** feasible support at admission/confirm. Stale context never confers authority. |
| **`support(staged) ⊆ F(x_live)`** | The **permanent safety line.** Staged support is always a subset of live feasible support; rising model capability never relaxes it. (`testSupportStagedSubsetOfLiveF`) |
| **SELECT** | Authorship lane: Swift enumerates the slate; the model returns an index + non-authority framing. The safe public default during migration. |
| **PROPOSE** (PROPOSE-AND-REVALIDATE) | Authorship lane: the model proposes a *shape*; Swift independently materializes support. The target — **shadow-only until measured.** |
| **D2** | The single **in-process Swift admission seam** — not a network service, not a second verifier, not model-callable. Lookup, never reconstruction. The only **net-new** admission-critical seam. (`testD2InProcessOnly`) |
| **`V0` / `V1`** | Type-name version suffix; the context envelope is upgraded to `RecommendationContextV1`. Distinct from the internal `schemaVersion` field. |
| **`.notMeasured` / `MeasurementStatusV0`** | Measurement-state enum: `measured`, `notMeasured`, `lineageMissing`, `fingerprintMissing`, `provenanceMissing`, `staleWindowExpired`, `classifierCoupled`, `coverageInsufficient`, `ownerGateRequired`. **`.notMeasured` is never zero** — missing data cannot become evidence to promote or penalize. (`testNotMeasuredNeverZero`) |
| **Φ** | A guidance/bias signal nudging which *already-feasible* candidate is favored — preference only, **no authority, never admission.** |
| **Evidence hash / provenance / fingerprint** | `EvidenceHashV0` (model may cite, never introduce); `RecommendationProvenanceV0` (D2-emitted, never model-authored); `RecommendationFingerprintV0` — a **pre-picker** (in D2) and a **post-picker** (at confirm/write) fingerprint, both required before any measurement. |

## 3. First principles

**Manufacturing, not retrieval.** The product is the recommendation *shape*
(what / when / why / fit), not a row from an enumerated set. The system wins
only when the shape itself is a felt decision variable. Compressing the shape to
a pick-from-a-list before composition is retrieval wearing a manufacturing
costume.

**The failure mode — premature semantic compression.** Compressing user/calendar
intent into categories, scoring features, templates, semantic graphs, or fixed
slates *before* the system can compose. SELECT-only is a form of it when made
final: Swift owns the candidate universe first, so if the optimal shape is not
already in `slateOfferedV0`, the model can only make the offered choices sound
better. The cure is neither raw egress nor model authority, but a narrower
split:

```
1. Swift considers the full private state every run.
2. Swift transmits only decision-sufficient, non-identifying statistics + relation chips.
3. DiffusionGemma composes a shape in a high-dimensional space.
4. Swift independently materializes and validates support for that shape.
5. Only Swift-admitted artifacts reach the confirm tap.
```

**Capability is separated from authority.** This is the generator/verifier
asymmetry with a *decidable* correctness verifier: DiffusionGemma may propose a
bad shape, overfit a why-line, or hallucinate a relation, but cannot put
anything on the calendar — Swift owns the pantry, validators, admission,
provenance, fingerprints, and writes. The **confirm tap is not plumbing; it is
the moment authority returns to the user.**

**The membrane — decision-sufficient, non-identifying statistics.** What crosses
to DiffusionGemma is *not* "raw data, safely redacted." It is the axes that move
the decision, never the axes that name the life. Redaction self-defeats only
when it strips the utility gradient, so the membrane *preserves the gradient and
removes identity.* Enforced by `DecisionSufficientStatisticV0` (banded,
conditioning-only) and by failing closed: silent truncation and silent redaction
collapse are context-builder failures (surfaced via
`ContextProjectionHealthV0`), never silent.

| Membrane | Example |
|---|---|
| **Raw state (Swift-only)** | "Dinner with Marcus, recurring, emotionally loaded, not movable" |
| **Model-visible** | `{ socialLoad: high, movable: low, energyCost: high, recoveryNeed: high }` |
| **Forbidden egress** | `Marcus`, the title, venue, attendee identity, notes, relationship label |

**Authority boundaries by surface.** *Crosses-the-membrane* and *touches-
admission* are **independent** properties — which is exactly why the model can
be fed everything and author nothing:

| Surface | Crosses as conditioning? | Touches admission? | Rule |
|---|:--:|:--:|---|
| Raw reads / notes / titles / locations / attendees | no | via Swift validators only | reasoned over by Swift; never transmitted raw |
| Decision-sufficient statistics | yes (non-identifying) | no | conditioning only; carries coverage + redaction-loss metadata |
| Relation chips | yes (non-identifying, approved) | no | consultable context; no support/provenance/strength |
| `SlateCellV0` (SELECT) | yes | yes, but only as Swift-authored support | model reads & selects an index; Swift owns every write-bearing field |
| `RecommendationShapeProposalV0` (PROPOSE) | yes (return payload) | no | shape hints only; no concrete identity/time/evidence/verdict/action |
| D2 binding | no | yes | single in-process Swift seam |
| Value signals | no | no | backstage measurement only; never user-visible, never model authority |
| Confirm action | after staging only | yes | server-minted; user tap required |

**The why-line-true-today test.** Value concentrates in the why-line. The test
for whether the system composed rather than vended:

> **Would this why-line be wrong on a different day?**

If *no*, it vended. "You have a free 30 minutes" is stable across days — weak.
"Your afternoon has a hard social block then a narrow low-friction gap, so a
quiet reset now protects the evening" is true only today — composition. PROPOSE
is justified only when it yields why-lines true today *and* shapes SELECT would
not reliably have enumerated.

**Correctness verifier vs. the absent value verifier.** The system can know
whether a recommendation is *valid enough to write*; it cannot mechanically know
whether it is *good*. There is a strong correctness verifier (D2 binding, live
`F(x_live)`, duplicate/write-target policy, PII + copy-honesty, fingerprinting,
confirm-time recheck) and **no true value verifier.** This is why "survives to
write" Goodharts: *kept is not loved; deleting is friction* — survival alone
biases toward safe, obvious suggestions and lets vending back in. The cure is
the backstage value layer (§7), *paired with*, never *replaced by*, survival.

## 4. The authorship decision

The shape comes from one of three lanes. **AUTHOR** — the model authors a full
proposal, Swift admits what it can verify — is **rejected**: a full proposal
carries identity, time, target, evidence, provenance, verdict, and action,
fields too close to authority (plan §4.1). The two live lanes:

| Lane | What it is | Verdict |
|---|---|---|
| **SELECT** | Swift enumerates the slate; the model returns `selectedSlotIndex` + framing | Safe public default — correct *precisely when the optimal recommendation is already in Swift's set,* and it keeps `support ⊆ F(x_live)` obvious. But it cannot compose an un-enumerated shape, so **made final it reintroduces premature semantic compression.** |
| **PROPOSE-AND-REVALIDATE** | The model proposes a shape (outcome, time-window/duration hints, affordances, unresolved needs); Swift independently materializes support | The target — **shadow-only until measured.** Importance-sampling over a space too large to enumerate; pays only when the action space is high-dimensional and yields why-lines true today. |

```
support(staged) ⊆ F(x_live)   — holds across all three lanes, at any model capability
```

PROPOSE changes how Swift *samples* candidate space, not the admission wall —
**unless materialization moves the offered `F(x)`, which is then an owner-gated
policy change requiring a parity test,** not a free experiment. Migration:
SELECT public, PROPOSE shadow, identical D2 wall and live revalidation, admit-
rate parity so guidance cannot leak into authority, a why-line-true-today audit,
and an owner gate before any public selection-moving change.

## 5. Canonical contracts

Field rosters are in the plan; the holding is each contract's owner and the one
invariant it enforces. **Three contracts carry their field list *as* the
invariant — a prohibition, kept verbatim.**

| Contract | Owner | Invariant |
|---|---|---|
| `RecommendationContextV1` | Swift | the context envelope; `contextID` folds all digests but **excludes ambient wall-clock freshness** — no frozen context confers admission; freshness is live revalidation only |
| `SlateCellV0` | Swift | the SELECT cut-line, model-visible but Swift-owned; `slotIndex` = array index; soft-score/preference/affordance/chip fields are **conditioning & ordering only, never admission** |
| `RecommendationSelectionInfillV0` | DiffusionGemma (non-authority fields, post-sanitizer) | the SELECT return: `selectedSlotIndex`, `why`, hints, `confidence` — authors no authority field |
| `RecommendationShapeProposalV0` | DiffusionGemma (shape hints only) | the PROPOSE payload — **forbidden: title, write start/end, calendar target, calendar object ID, source kind, source strength, evidence hash, provenance, fingerprint, verdict, action, raw attendee/place/title/note strings.** Swift may ignore any hint and must materialize + revalidate independently |
| `DecisionSufficientStatisticV0` (+ `DecisionAxisV0`, `DecisionValueBandV0`) | Swift (reducers/validators) | the membrane contract — banded, non-identifying; **conditioning only**, cannot mint support/provenance/strength/admission |
| `RelationChipV0` (+ `RelationClassV0`) | Swift | feature engineering over a **frozen model — nothing learns here;** never carries support/provenance/strength/admission/verdict/fingerprint/action |
| `EvidenceReceiptV0` (+ `EvidenceKindV0`) | Swift | closed evidence kinds; D2 requires `receipt.summaryHash == owningSource.evidenceHash` and kind equality — lookup, not reconstruction |
| `D2BindingOutputV0` / `ProposalEnvelopeV0` | Swift | what D2 returns; **hydrated from Swift support, not model fields;** a shape proposal cannot hydrate write fields |
| `PickDiscriminatorV0` | Swift | ranks **already-admitted** candidates; not a second verifier. **Forbidden: model confidence as feasibility, model self-rank as usefulness, model-authored strength/kind, sampler confidence as quality, raw PII, unmeasured-as-zero, any user-visible value signal** |
| `RecommendationValueSignalV0` (+ `RecommendationEditDistanceV0`, `CounterfactualSlateLogV0`, `SurvivalAtTSignalV0`) | Swift | the backstage value container — never user-surfaced, never model authority |
| `AllowedActionV0` | Swift | the server-minted confirm action — minted **only after staging**, short-lived, scoped, invalidated by changed support |
| `RecommendationVerdictV0` | Swift | **non-`Codable`** — no model, bridge, or carrier may transport it (`testRecommendationVerdictNonCodable`) |
| `ContextProjectionHealthV0` | Swift | makes no-silent-truncation / no-silent-redaction-collapse testable and fail-closed |

**Relational Prep Station** — allowed only because it is Swift-owned; a *model-
authored* semantic substrate stays rejected. Build priority: **P1
`nonSemanticToNonSemantic`** (time/space/conflict topology — reliably
computable, build first); **P2 `semanticToNonSemantic`** (a learned claim with
no learner — ships **only as a flagged heuristic**, `coverage: notMeasured`,
non-citable unless D2 + `CopyHonestyGate` approve, no admission path depends on
it); **P3 `semanticToSemantic`** (decoration — suppressed by default). **If a
chip moves offered feasibility, it is no longer a chip — it is an owner-gated
`F(x)` change.**

## 6. How a recommendation is manufactured

```
Swift considers all user/calendar state
  → emits decision-sufficient statistics + relation chips
  → DiffusionGemma proposes a recommendation SHAPE (not a write artifact)
  → Swift independently materializes candidate support
  → Swift validates, admits, hydrates, fingerprints, stages, writes — only after the confirm tap
  → Swift measures correctness and value backstage
```

Both lanes run that pipeline; they differ only in where candidates come from:

```
SELECT  (public):  Swift enumerates F(x) as slateOfferedV0 → model returns an index
                   → D2 binds + live-revalidates the selected cell → staged card
PROPOSE (shadow):  context carries NO raw identity → model returns a SHAPE
                   → Swift materializes its own SlateCellV0 candidates → same D2 wall
```

**Every admitted shadow card passes the same D2 and live revalidation as
SELECT** — PROPOSE only adds one Swift materialization step before an unchanged
wall.

**The D2 admission wall** is lookup, not reconstruction (full 15-step algorithm:
plan §8.3). Its load-bearing steps:

```
1. Resolve candidates (SELECT: by selectedSlotIndex; PROPOSE: reject concrete fields, then materialize).
2. Look up receipt by summaryHash == sourceEvidenceHash; require kind + hash equality.
3. Classify strength/copy-budget ONLY by the closed EvidenceKindV0.
4. Hydrate ProposalEnvelopeV0 from Swift support, NOT model fields.
5. Run live F(x_live) + validatePropose — where support(staged) ⊆ F(x_live) is enforced.
6. Compute the pre-picker fingerprint; return a non-Codable verdict.
```

**Confirm, write, undo.** The tap is consent; there is **no auto-write** — felt
safety does not earn it. Swift **never touches calendar objects it did not
create.**

```
staged card → confirm tap → live support recheck → post-picker fingerprint
  → write → undo / edit / delete / survival-at-T measurement
```

## 7. Backstage measurement

The value layer is *paired with* survival, never replaced by it.

| Signal | Measures |
|---|---|
| **Edit-distance** (`RecommendationEditDistanceV0`) | the **closest thing to** a value verifier — how much the user had to finish the system's job (title/time/duration/target deltas). Cheap, dense, early. |
| **Counterfactual slate** (`CounterfactualSlateLogV0`) | the gradient in rejected proposals (offered/rejected/selected digests, reason); stale support separated from genuine rejection |
| **Survival-at-T** (`SurvivalAtTSignalV0`) | whether the card survives to ~24h before the event — measured at the event horizon, **not** at the tap |

- **Measurement before mutation.** No adaptive ranking, preference update, chip
  promotion, or PROPOSE launch until lineage and *both* fingerprints exist.
- **`.notMeasured` is never zero** — missing lineage/coverage/fingerprints never
  promote or penalize; no value signal makes an invalid artifact valid.
- **The loop improves in the dark.** Value signals are Swift-side, never user-
  surfaced, never model authority — *the instant a user feels measured, the
  calendar becomes surveillance.*

## 8. Safety & privacy invariants

Preserved across all migration; capability may rise without authority rising.

- **Authority firewall.** The model authors no identity, time, title, evidence
  hash, source kind/strength, provenance, fingerprint, verdict, or action; Swift
  hydrates and revalidates live. `PickDiscriminatorV0` cannot launder any model
  signal into authority.
- **Single admission wall.** D2 is the only net-new admission-critical seam, in-
  process Swift — no second verifier, no admission RPC, no model-authored
  ontology, no network service. Model-authored semantic graphs stay rejected.
- **Privacy floor.** Raw titles, free-text notes, attendee identities, exact
  locations, raw history, and low-cardinality identifying facts **never cross
  the membrane**; Swift reads them only to compute statistics. Free-text notes
  never cross at all.
- **Copy honesty.** The why-line must be true today and supported by admitted
  evidence; `CopyHonestyGate` blocks unsupported preference claims, unsafe
  names, implied source strength, heuristic chips cited as learned truth, and
  any use of backstage measurement as copy.
- **Sacred calendar invariants:**
  - Never write without the confirm tap.
  - Never edit, move, delete, or overwrite anything the system did not create.
  - Never leak who / where / raw private strings across the membrane.
  - Never let measurement become visible surveillance.
- **Felt safety** is the absence of dread at the tap: the block lands where
  expected, undo is instant, no private detail leaks into the card, failures are
  typed and calm, no auto-write exists.

