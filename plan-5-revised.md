# plan-5.md — Contestation-Aware Earned-Acceptance Recommendation Manufacturing Architecture

**Status:** canonical architecture plan for CalAgent recommendation manufacturing. `plan-5.md` **supersedes** `plan-4-revised(10).md` / `plan-4-revised(10)(1).md` and the first plan-5 draft.

**Relationship to plan-4:** Plan 5 inherits the plan-4 safety architecture and replaces the plan-4 learning posture. The wall stays bit-for-bit. The reward changes. CalAgent grows the deliberately amputated back half of the game-agent loop so it can learn what the user likes, while keeping Swift / D2 sovereign.

**Revision note:** This revision accepts the plan-5 review's remand: raw survival plus low edit-distance is not a bound on comfortable false positives. In uncontested calendar space, survival can measure cost-of-removal instead of value, and the release loop can report that corruption as a rising green dashboard. Plan 5 therefore makes **contestation first-class**: reward credit is weighted by how much the card occupied pre-existing calendar demand, bounded by a revealed-reconfirmation brake, and measured only against calendar pressure CalAgent did not create.

**Implementation-status note:** This document is a canonical target architecture. The inherited contracts and walls are architecture of record. The learned preference embedding, earned-acceptance reward reducer, contestation signal, product-verdict channel, reward model, reward-guided sampling, Diffusion-DPO path, contestation distribution monitor, and comfortable-false-positive falsifier are **proposed back-half build items** unless an implementation owner marks a migration milestone complete. Do not describe them as shipped merely because this plan specifies them.

**Governing doctrine:** CalAgent manufactures one recommendation for the user's time from a Swift-furnished pantry; Swift owns every liability-bearing mechanic — inventory, evidence, feasible support, validation, provenance, admission, writes, measurement, contestation, reward lineage, falsifiers, and guidance bounds; DiffusionGemma may compose, propose, learn preference-conditioned shapes, and receive bounded reward guidance; Codex only takes the order and serves what Swift admits; and the most capable component is never the most sovereign. Because the learned back half now has a stake in the user's yes, that stake must be auditable by the user and by Swift: through contestation-weighted reward, a product-verdict channel the user controls, and a held-out falsifier that can eject a family back to SELECT.

**Architecture law:**

```text
Codex may relay and serve.
DiffusionGemma may compose, propose, and learn preference-conditioned shapes.
Swift must encode, validate, admit, write, measure, reduce rewards, measure contestation, run falsifiers, own preference lineage, and bound guidance.
Codex, DiffusionGemma, reward models, learned preference stores, and release dashboards must never grade, admit, write, launder their own outputs, manufacture demand, or manufacture contestation.
```

The safety line is unchanged:

```text
support(staged) ⊆ F(x_live)
```

The amended law has one reconciliation rule and one loop-aware supplement:

```text
We grow value; we do not grant authority.
Reward and learning may steer composition upstream of D2.
D2 still rules admission, and the human confirm tap still returns authority to the principal.

D2 covers the admission seam; it does not by itself cover upstream reward corruption.
A shape-family may graduate only when the contestation distribution, the product-verdict channel,
and the held-out not-needed falsifier show that user protection scales with the migrated power.
```

**Internal role map.** This map is for the engineering team only. Do not surface it in user-facing copy, onboarding, card text, accessibility labels, marketing, analytics event names, prompts, or UX instrumentation. The internal restaurant metaphor is mapped once here; the remainder of the document uses component names directly.

| Component | Internal role | Owner | Owns | Borrows | Interface / contract | Freshness / TTL | Trust boundary | Failure mode |
|---|---|---|---|---|---|---|---|---|
| Codex | Waiter: order taker and server | Carrier / dialogue layer | Turn capture, bounded clarification, request relay, admitted-card presentation, dismissal / reroll / product-verdict relay | Swift request context, Swift-staged card, server-minted actions | `POST /v1/carrier/turn`, `RecommendationTurnRequestV0`, `RecommendationTurnResponseV0` | Per turn; no ambient freshness authority | No admission, no grading, no writes, no provenance, no source strength, no reward visibility | Over-talks, asks an unnecessary question, echoes authority-looking text, invents learning copy, or serves a card Swift did not admit. Guard: response payload may carry only Swift-staged artifacts and server-minted actions. |
| DiffusionGemma | Cook / policy: expensive composition of ingredients into a recommendation shape | Model provider / analysis lane | Semantic composition, contrast, why-line drafting, unresolved-need detection, non-authority proposal payloads, optional shadow telemetry, learned shape prior when owner-gated | Swift-furnished decision-sufficient statistics, relation chips, feasible slate cells in SELECT, shape constraints in PROPOSE, `UserPreferenceEmbeddingV0`, bounded `RewardGuidancePolicyV0` | `RecommendationSelectionInfillV0` for SELECT; `RecommendationShapeProposalV0` for PROPOSE; optional `RecommendationCompositionTelemetryV0` | Per analysis call; context-bound; cannot create freshness | No identity, no title, no write time, no calendar target, no source kind / strength, no evidence hash, no provenance, no fingerprint, no verdict, no action; reward guidance is preference only | Hallucinates, overclaims personalization, learns flattery, routes around why-line honesty with true-but-unneeded cards, proposes unsupported shapes, or copies authority fields. Guard: allowlist reconstruction, PII/copy scan, D2 lookup, live revalidation, contestation-weighted reward, bounded γ / KL, loop audit. |
| Swift | Restaurant, pantry, equipment, health code, register, reward accountant, and loop auditor | Swift application / calendar backend | Raw user and calendar state, decision-sufficient statistics, feasible support `F(x)`, evidence receipts, source registry, validators, D2, provenance, fingerprints, write gates, undo, lineage, value signals, contestation signals, earned-acceptance reduction, preference-store ownership, guidance bounds, falsifiers, metrics | Non-authority model proposals, user confirmation, user product verdict when provided | `RecommendationContextV1`, `SlateCellV0`, `D2BindingInputV0`, `D2BindingOutputV0`, `ProposalEnvelopeV0`, `AllowedActionV0`, `RecommendationValueSignalV0`, `ContestationSignalV0`, `EarnedAcceptanceRewardSignalV0`, `UserProductVerdictSignalV0`, `UserPreferenceEmbeddingV0`, `RewardGuidancePolicyV0` | Live at admission and confirm; TTLs by source; reward trusted only after lineage, both fingerprints, contestation boundary, and falsifier status | Admission-critical owner of all liability-bearing state; only owner allowed to reduce reward, measure contestation, run the falsifier, and bound guidance | Over-prunes, silently truncates, leaks identifying data, admits stale support, treats missing measurement as zero, rewards low-contestation survival, or lets a value signal become authority. Guard: no silent truncation, no silent redaction collapse, `support(staged) ⊆ F(x_live)`, `.notMeasured` semantics, owner gates, contestation audit. |
| Relational Prep Station | Swift-owned prep table | Swift application / reducers | Relation chips among events and candidate windows; topology; heuristic flags; coverage and suppression metadata | Raw Swift state and closed Swift tags | `RelationChipV0`, `RelationChipSetV0`, `RelationChipCoverageV0` | Recomputed per run; TTL no longer than underlying evidence | Consultable conditioning only unless an owner-gated `F(x)` change explicitly promotes a predicate | Becomes a semantic graph, fingerprints a standing meeting, steers admission by implication, or pretends heuristic relations are learned truth. Guard: no support, provenance, source strength, admission, or writes; parity tests for any `F(x)`-moving change. |
| Earned-Acceptance Reward Reducer | Swift-owned reward accountant | Swift measurement / write-tail owner | Reduction from `RecommendationValueSignalV0` into contestation-weighted earned-acceptance reward; lineage gating; regret penalty; product-verdict fusion; revealed-reconfirmation brake | Confirm/write lineage, pre/post fingerprints, edit-distance, survival-at-T, rejection log, `ContestationSignalV0`, `UserProductVerdictSignalV0` | `EarnedAcceptanceRewardSignalV0`, `RecommendationValueSignalV0`, `RecommendationEditDistanceV0`, `CounterfactualSlateLogV0`, `SurvivalAtTSignalV0`, `ContestationSignalV0`, `UserProductVerdictSignalV0` | Computed only after lineage, both fingerprints, and contestation boundary; untrusted until `measurementStatus == measured` | May steer future composition only through owner-gated learning/guidance; never D2, never copy, never user grading | Optimizes acceptance alone, treats `.notMeasured` as zero, rewards survival in free space, rewards inertia in contested space, or leaks visible surveillance. Guard: contestation-weighted reward, created-event boundary in reverse, revealed-reconfirmation brake, `.notMeasured`-never-zero. |
| Contestation Auditor | Coupling watcher for release ↔ prior | Swift measurement + release owner | Contestation distribution of each graduating family; low-contestation reward share; intrusion/regret alarm; shape-family freeze/eject recommendation | `ContestationSignalV0`, earned reward aggregates, product verdicts, undo/edit/delete, fixed-pool cohorts | `ContestationDistributionReportV0`, `RewardGuidancePolicyV0` | Batch / release cadence; current report required before public guidance | Not admission-critical; may reduce γ, freeze a family, or eject to SELECT; never admit | Watches components but misses the loop coupling, lets a family graduate on cheap low-contestation survival, or treats intrusive manufactured contestation as value. Guard: distribution gates, regret stratification, owner review, SELECT eject. |
| Product Verdict Channel | User-directed product verdict, not user confession | Swift product / privacy owner | Always-available lightweight verdict affordance; rare solicitation policy; response reduction into typed flags | User tap on admitted card / follow-up affordance | `UserProductVerdictSignalV0`, `ProductVerdictPolicyV0` | Per card / post-write window; solicitation cadence owner-gated | User-visible by definition, but never grading, never copy evidence, never admission | Becomes a preference probe that feels like surveillance, asks too often, or makes positive "useful" signals dominate contestation. Guard: availability unthrottled, solicitation throttled, no free text by default, positive signal coupled to contestation. |
| Preference Store / `u` | Non-identifying preference memory | Swift privacy / ML platform owner | Per-user preference embedding derived from decision-sufficient statistics and contestation-weighted earned-accepted history; population prior; coverage and redaction-risk metadata | `DecisionSufficientStatisticV0`, `EarnedAcceptanceRewardSignalV0`, consented population aggregate | `UserPreferenceEmbeddingV0`, `PreferenceEmbeddingUpdateV0` | TTL / recompute policy owner-gated; cold-start uses population prior; personal confidence rises only with measured earned-accepted history | Conditioning only; cannot mint support, evidence, source strength, copy claims, admission, or writes | Embeds identity, uses phantom zeros for cold-start, cross-contaminates users, trains on low-contestation comfort, or becomes an admission feature. Guard: non-identifying projection, contestation-weighted labels, population privacy floor, coverage gates. |
| Reward Model `r(shape,state,u)` | Learned value estimator / guidance scorer | ML platform with Swift release owner | Predicts contestation-weighted earned-acceptance likelihood for a non-authority shape under state and `u`; produces guidance signal or DPO pairs | Earned-accepted / rejected / edited / deleted examples; `UserPreferenceEmbeddingV0`; decision-sufficient state; shape digests; contestation weights | `RewardModelInputV0`, `RewardModelOutputV0`, `RewardGuidancePolicyV0`, optional `DiffusionDPOTrainingExampleV0` | Model-versioned; shadow-first; guidance bound expires by release config | May guide denoising with bounded γ or train offline with KL leash; no D2 path, no user copy, no provenance | Reward-hacks flattery, learns to be intrusive to manufacture contestation, drifts population toward easy acceptance, or claims quality as correctness. Guard: γ / KL bounds, frozen-base v1, contestation distribution monitor, falsifier, why-line gate, D2 wall. |
| Comfortable-FP Falsifier | Pre-registered failure detector outside the fix | Swift measurement + independent evaluation owner | Held-out, contestation-blind cohort; raw `notNeeded` / `notToday` rate; stratification by contestation; kill condition wired to SELECT eject | User product verdicts, fixed-pool assignments, shadow/public family labels, contestation bands as stratification only | `ComfortableFalsePositiveFalsifierV0`, `SelectEjectDecisionV0` | Built before reward guidance is trusted; refreshed per release window | Outside contestation-weighted reward; may eject or freeze, never admit | The remedy creates its own green dashboard. Guard: pre-registered kill condition, held-out cohort, raw not-needed rate outside the optimized metric, owner-independent review. |

## Table of contents

1. [Executive decision](#1-executive-decision)
2. [Game-engine pivot and the three scoped deltas](#2-game-engine-pivot-and-the-three-scoped-deltas)
3. [Capability is separated from authority, but loop coverage must scale](#3-capability-is-separated-from-authority-but-loop-coverage-must-scale)
4. [Value proposition: personalization under unverified value](#4-value-proposition-personalization-under-unverified-value)
5. [Authorship decision and composition lanes](#5-authorship-decision-and-composition-lanes)
6. [Pantry membrane: decision-sufficient, non-identifying statistics](#6-pantry-membrane-decision-sufficient-non-identifying-statistics)
7. [Relational Prep Station: unchanged, Swift-owned, non-learning prep](#7-relational-prep-station-unchanged-swift-owned-non-learning-prep)
8. [Canonical contracts](#8-canonical-contracts)
9. [D2 and the admission wall](#9-d2-and-the-admission-wall)
10. [End-to-end flows](#10-end-to-end-flows)
11. [Earned acceptance, contestation, and preference learning](#11-earned-acceptance-contestation-and-preference-learning)
12. [DiffusionGemma 0-to-1 build](#12-diffusiongemma-0-to-1-build)
13. [Swift-owned scoring, discrimination, and measurement](#13-swift-owned-scoring-discrimination-and-measurement)
14. [Privacy, redaction, and copy honesty](#14-privacy-redaction-and-copy-honesty)
15. [User experience invariants](#15-user-experience-invariants)
16. [Migration sequence](#16-migration-sequence)
17. [Test matrix](#17-test-matrix)
18. [Definition of done](#18-definition-of-done)
19. [Changelog / deprecation map](#19-changelog--deprecation-map)
20. [Deliberately preserved safety invariants](#20-deliberately-preserved-safety-invariants)
21. [Self-audit](#21-self-audit)

---

## 1. Executive decision

CalAgent remains an information-manufacturing system, not a retrieval system. The output is one composed recommendation: what to do, when it will land, why it fits today, and why this shape is worth the user's time under this state. The shape is still the product.

Plan 5 canonizes CalAgent as the **front half of a game-agent loop with the validator made sovereign**, then grows the amputated back half carefully. This revision adds the missing loop organ: **contestation**.

```text
Swift reads all private state
  -> Swift emits decision-sufficient, non-identifying state + feasible support
  -> DiffusionGemma composes a shape or selects an index, conditioned by u
  -> optional bounded reward guidance steers composition upstream of D2
  -> Swift independently materializes candidate support
  -> D2 validates, binds, hydrates, fingerprints, and admits only Swift support
  -> the user confirm tap returns authority
  -> Swift writes only after tap
  -> Swift measures outcome, contestation, product verdicts, and falsifier cohorts
  -> contestation-weighted earned acceptance updates u / reward model only after owner-gated lineage checks
```

The public safety default remains SELECT until each shape-family graduates. The target authorship posture remains PROPOSE-AND-REVALIDATE, but the learning curriculum starts in SELECT because reward influence over an index cannot widen `F(x)`.

The plan-4 posture that ends is the maximally dark, never-learning posture:

```text
old: value signals are backstage gauges; the loop improves in the dark; no learner / frozen model.
new: value signals reduce to a contestation-weighted earned-acceptance reward that may steer composition;
     the composer may be trained on earned-accepted history;
     the machine now has a stake in the user's yes;
     D2 and the human tap remain unchanged.
```

The new stake is explicitly booked. The old trust story defined authority as admit/write and then proved reward never reached D2. That proof remains true, but it does not cover the new upstream risk: composition can decide which true-but-comfortable card the user sees and how it is framed. Plan 5 therefore adds loop coverage:

```text
D2 protects admission.
Contestation protects the reward loop from teaching itself low-contestation survival.
The product-verdict channel lets the user judge the product without confessing a preference.
The falsifier can eject a family even when the contestation-weighted dashboard is green.
```

The value proposition generalizes from “decide when the user has earned rest” to **learn what the user likes and accepts across recommendation types**: rest, focus, prep, social, errands, and future owner-approved `DesiredOutcomeHintV0` families. Rest remains one important family. It is no longer the whole product frame.

Permanent safety line:

```text
support(staged) ⊆ F(x_live)
```

A guided card, a personalized card, a DPO-tuned card, a population-prior cold-start card, and an intrusive reward-hacked card all die at the same wall if Swift cannot independently support them. A card that is valid but learned from low-contestation survival can still be bad; that is why contestation, product verdicts, and the falsifier are part of Plan 5 rather than optional analytics.

## 2. Game-engine pivot and the three scoped deltas

### 2.1 The loop CalAgent really is

A canonical game agent has observation, state encoder, policy, value, planner / world model, action decoder, environment step, reward, and trainer. CalAgent uses the vocabulary but inverts the power relation:

| Game-loop part | CalAgent part | Plan-5 status |
|---|---|---|
| Observation | Swift reads raw calendar / user state | Present and unchanged. Raw state stays Swift-only. |
| State encoder | `DecisionSufficientStatisticV0`, relation chips, feasible support `F(x)` | Present and Swift-owned. The encoder is walled off from the policy. |
| Policy | DiffusionGemma over `RecommendationSelectionInfillV0` or `RecommendationShapeProposalV0` | Present, more capable, still non-authoritative. |
| Value | `RecommendationValueSignalV0` reduced into contestation-weighted earned acceptance | Newly promoted from retrospective gauge to bounded reward. |
| Planner / search | None | Still absent. Reward-guided diffusion is not rollout search. |
| World model | None | Still absent. The why-line justifies; it does not simulate the user's week. |
| Action decoder | Swift hydrates `AllowedActionV0`, user taps, Swift writes | Present and unchanged. The decisive step is a human confirm tap, not `env.step()`. |
| Action validator | D2 + `support(staged) ⊆ F(x_live)` | Present, hypertrophied, sovereign, unchanged. |
| Reward loop | Historically severed | Closed carefully through contestation-weighted earned acceptance, owner gates, and no admission authority. |
| Trainer | Historically no learner / frozen model | New learner allowed for the composer only, never for admission. |

CalAgent is not a game in the dangerous sense. It has no verifiable reward, no cheap simulator, no terminal score, no adversary, and no free reversible actions. The user is the principal, not an opponent. The calendar is sacred space, not an environment to step through autonomously.

Therefore Plan 5 borrows the stack and refuses the dangerous closure:

```text
No online RL trainer.
No autonomous env.step().
No planner over a simulated human week.
No world model that predicts reward.
No learned value signal inside D2.
No reward credit for demand CalAgent created itself.
```

### 2.2 Delta 1 — value signals may now steer composition

Plan 4 §10.5 stated the absolute visibility rule: the model has no authority, measurement has no visibility, and the loop improves in the dark. Plan 4 §10.2 made edit-distance Swift-side only and not admission-changing. Plan 4 §11.5 required measurement before mutation.

Plan 5 re-scopes those statements:

```text
Value signals remain non-authoritative and cannot become user grading.
But after measurement-before-mutation is satisfied, they may reduce to a bounded reward
that steers composition upstream of D2.
```

This is a real relaxation. The reward is prospective; the old gauges were retrospective. The reward may guide denoising with scale γ or train an offline preference objective. It still cannot admit a card, hydrate a field, mint evidence, or write.

### 2.3 Delta 2 — the composer may now learn

Plan 4 §6 and readme §6 P2 held the no-learner / frozen-model posture for the Relational Prep Station: it is feature engineering over a frozen model and nothing learns inside it. Plan 5 preserves that statement for the Relational Prep Station but removes it as a global doctrine.

New rule:

```text
The prep station remains non-learning.
The composer may be trained on earned-accepted history.
```

Phase 1 behavior-cloning and Phase 2b Diffusion-DPO may update DiffusionGemma / adapters. Phase 2a reward-guided sampling is the preferred v1 because it keeps the base composer frozen and makes γ a request-time safety dial.

### 2.4 Delta 3 — the machine now has a stake in the user's yes

The deepest relaxation is not only that reward may steer or that a learner may exist. It is that the system now benefits, in its own training objective, from the user saying yes.

Plan 4's strongest user-facing soul was “the one voice that gains nothing when you stop.” Plan 5 cannot honestly keep that sentence unmodified. The new version is:

```text
CalAgent must be the one voice that gains nothing from a yes the user did not contest.
```

This is a named deprecation. The machine now has a stake in a yes, but that stake is kept honest in three ways:

1. **Contestation-weighted reward:** a yes in empty, uncontested space earns little or no reward credit.
2. **User-directed product verdict:** “not today” / “wrong” / “not needed” is a verdict on the product, not a confession about the user.
3. **Held-out falsifier:** a contestation-blind cohort watches the raw not-needed rate outside the optimized reward and can eject the family to SELECT.

This delta is why “capability ≠ authority” is necessary but no longer sufficient as the entire safety story. It still protects admission. It does not, by itself, protect the upstream loop from learning which comfortable true card to show.

### 2.5 Boundary of the relaxations

The three relaxations are upstream of D2 only. They do not relax:

```text
D2 as the single in-process admission seam.
support(staged) ⊆ F(x_live).
RecommendationVerdictV0 non-Codable.
AllowedActionV0 minted only after staging.
The human confirm tap.
No auto-write.
Never touch calendar objects CalAgent did not create.
The hydration firewall.
The privacy floor.
Copy-honesty / why-line-true-today.
.notMeasured is never zero.
Measurement-before-mutation as the gate before reward/training.
```

The old sentence “the loop improves in the dark” becomes:

```text
The loop may learn from measured outcomes, but the user must not become the object of a hidden gaze,
and the learned signal never gains authority past D2.
```

The explicit channel is therefore reframed. It is no longer primarily a “was this useful?” prompt that the company asks when it wants signal. It is a lightweight product-verdict affordance that the user can direct at the card. **Availability is unthrottled; solicitation is throttled.** A system that asks constantly feels needy and surveillant; a system that is always answerable lets the user audit it.

## 3. Capability is separated from authority, but loop coverage must scale

The load-bearing admission property is unchanged: capability can rise without authority rising.

DiffusionGemma may become more capable in three ways:

1. It may condition on `UserPreferenceEmbeddingV0` (`u`).
2. It may be guided by a bounded reward model `r(shape,state,u)` during denoising.
3. It may be trained offline on contestation-weighted earned-accepted shapes or preference pairs.

None of those grants sovereignty. Swift remains the sole owner of raw state, feasible support, admission, provenance, fingerprints, writes, measurement reduction, contestation, reward bounds, falsifiers, and the confirm-time live recheck.

But Plan 5 adds one standing audit question that Plan 4 did not need:

```text
Does user protection scale with the migrated power, and does the preserved wall cover the relocated risk?
```

The answer must be re-proved for every guided family and every release. D2 covers the seam between proposal and admission. The reward loop lives upstream of that seam. The protection for that upstream loop is contestation distribution, product verdicts, and a falsifier that is not itself part of the optimized reward.

### 3.1 Authority and loop boundaries by surface

| Surface | Free Swift-side computation? | Crosses membrane as conditioning? | Touches admission authority? | Admission-critical? | Rule |
|---|---:|---:|---:|---:|---|
| Raw calendar reads, notes, titles, locations, attendees | yes | no | yes, through Swift validators only | yes when used for support | Stored and reasoned over by Swift; never transmitted raw. |
| Decision-sufficient statistics | yes | yes, when non-identifying | no | no | Conditioning only; must carry coverage and redaction-loss metadata. |
| Relation chips | yes | yes, when non-identifying and approved | no | no | Consultable context only; no support/provenance/source strength. |
| `UserPreferenceEmbeddingV0` (`u`) | yes | yes, when non-identifying and owner-gated | no | no | Conditioning only; cannot mint support, copy claims, admission, or user-visible “learned you” language. |
| `SlateCellV0` in SELECT | yes | yes | yes, but only as Swift-authored support | yes in D2 | Model may read and select index; Swift owns every write-bearing field. |
| `RecommendationShapeProposalV0` in PROPOSE | no, model-authored | yes, return payload | no | no | Shape hints only; no concrete identity, time, evidence, provenance, verdict, or action. |
| `RewardModelOutputV0` | yes / ML-owned under Swift release gate | may guide model sampling | no | no | May steer denoising upstream of D2; absent from D2 input/output and user copy. |
| `ContestationSignalV0` | yes | no raw calendar; may become banded training metadata | no | no | Swift-only measurement of how tested the recommendation was; excludes CalAgent-created demand. |
| `UserProductVerdictSignalV0` | yes | no raw text; reduced flags may train | no | no | User-directed verdict on the product. Availability unthrottled; solicitation owner-gated. |
| D2 binding | yes | no | yes | yes | Single in-process Swift seam; ignores reward as authority. |
| Earned-acceptance reward | yes | no direct model payload except through owner-gated training/guidance | no | no | Backstage reduction; may steer future composition only after lineage, contestation, and falsifier gates. |
| Falsifier report | yes | no | no | no | Outside optimized reward; can eject / freeze / reduce γ but cannot admit. |
| Confirm action | yes | served by Codex/UI only after staging | yes | yes | Server-minted; user tap required. |

### 3.2 The formula

Plan 5 keeps the canonical admission equation and adds the reward-loop equation outside it:

```text
DiffusionGemma proposal ~ π(shape | state, u, bounded reward guidance)
Swift materializes support independently
D2 admits only if support(staged) ⊆ F(x_live)

behavioral_earned = accepted ∧ survived-to-T ∧ low-edit-distance ∧ no negative product verdict
reward_credit     = behavioral_earned × contestation_weight × revealed_reconfirmation_brake × created_event_boundary
release_allowed   = D2 parity ∧ contestation distribution healthy ∧ falsifier not tripped
```

`u` and reward guidance affect the proposal distribution. They do not affect the D2 membership test. Contestation and the falsifier affect whether a family is allowed to keep learning or to graduate; they do not admit a card either.

### 3.3 What the preserved wall covers, and what it does not

The wall covers legality and correctness of a staged artifact:

```text
May this card be shown and written if the user taps?
```

It does not answer:

```text
Did the learned loop create a distribution that wins by occupying places the user had no reason to contest?
Did a family graduate because low-contestation survival got cheap?
Did the prior become comfortable-FP-rich, with the KL leash preserving the corruption?
```

Those are not D2 questions. They are loop questions. Plan 5's answer is not to weaken D2 or to abandon learning; it is to add the missing loop-level organ.

## 4. Value proposition: personalization under unverified value

Plan 4 §13 stated that the single feeling sold is permission to rest. That was too narrow and too paternalistic as the north-star value proposition. Plan 5 generalizes the product:

```text
CalAgent learns what the user values and what the user accepts,
then manufactures one recommendation for their time across the relevant shape-family.
```

The product is no longer “you earned rest.” It is:

```text
This is the one thing worth doing now, under today's state, in a shape you are likely to value and accept.
```

Rest remains a supported desired outcome. So do focus, preparation, decompression, recovery, transition, social, errands, and any owner-approved future family. The shape contract already supports this via `RecommendationShapeProposalV0.desiredOutcome`. Plan 5 makes it explicit.

### 4.1 Two things to learn, and one thing not to claim

Plan 5 separates two preference targets:

| Target | Meaning | Learned from | Failure if confused |
|---|---|---|---|
| **Value** | What actually helps the user's day | Never directly verified. Approximated by contestation-weighted non-regret, product verdicts, and rejection gradients | False permission, flattery, obvious low-risk suggestions, or “valid but unneeded” cards. |
| **Acceptance** | What the user is willing to tap | confirm, dismissal, reroll, not-this, edits, product verdicts | Optimizing raw acceptance alone rewards pleasant nonsense. |

The fused target is earned acceptance, but the guardrail is not true value. The guardrail is **non-regret under contestation**. Value remains unverified.

This distinction is load-bearing. A raw survival signal can degenerate into **cost-of-removal** in uncontested space: the card lives because removing it costs effort, not because the user needed it. The system must never call that value.

### 4.2 Contestation is the audit currency

The comfortable false positive is defined by living where contestation is absent. Therefore the one currency it cannot counterfeit is contestation: how much the card occupied space the user would otherwise have used.

Contestation is not surveillance. Swift already owns calendar pressure for validation and fit. The contestation signal is a banded, non-identifying reduction of that pressure, computed Swift-side and never exposed as copy. It measures only against pre-existing, non-CalAgent-created calendar demand.

```text
free-gap card kept with no edits       -> low / zero contestation credit
card kept over a real alternative      -> higher contestation credit
intrusive card that causes regret       -> loud negative signal, caught by undo/edit/delete/verdict
```

Contestation is not a true value verifier. It does one thing that matters: it moves the residual from a blind region into an observable region. Its own Goodhart — learning to be intrusive to manufacture contestation — is a strict improvement over silent comfort, because intrusion is loud and produces the regret signals the system already sees.

### 4.3 The why-line remains load-bearing, but it verifies truth rather than need

The why-line must still pass the true-today test:

```text
Would this why-line be wrong on a different day?
```

Reward cannot buy a false permission slip. A high predicted reward does not make an unsupported preference claim safe. Copy that overclaims “you like X” from backstage behavior remains a staging failure.

But the why-line-true-today gate checks falsity, not need. A true day-specific why-line on an unneeded card can pass. That is why copy honesty remains necessary but is no longer sufficient as the anti-flattery story.

### 4.4 The user remains the principal

The confirm tap is still consent and the return of authority. The product-verdict channel is not a confession about the user. It is a way for the principal to judge the product:

```text
not today
wrong
not needed
useful
```

The soul ports from “the one voice that gains nothing when you stop” to:

```text
the one voice that gains nothing from a yes you did not contest.
```

The absence of a stake is no longer true. The absence of an unauditable stake is the new standard.

## 5. Authorship decision and composition lanes

The authorship decision remains PROPOSE-AND-REVALIDATE as the target. SELECT remains the public default and the first reward curriculum lane.

### 5.1 AUTHOR remains rejected

DiffusionGemma still must not author a full calendar proposal. A full proposal carries title, concrete time, calendar target, identity, evidence basis, provenance, fingerprint, verdict, and action. Those are too close to authority.

Reward learning makes AUTHOR more dangerous, not less. A reward-optimized model that can author write artifacts could learn exactly the flattering write shape that bypasses user intent. Plan 5 therefore keeps AUTHOR rejected.

### 5.2 SELECT remains the low-blast-radius curriculum

In SELECT:

```text
Swift: F(x) = [SlateCellV0]
DiffusionGemma: selectedSlotIndex + why + hints
Swift: hydrate selected cell and revalidate live
```

Reward guidance in SELECT can only choose among Swift-authored feasible cells. It cannot widen `F(x)`. This makes SELECT the first public or shadow lane for preference conditioning and γ-guided selection.

Rules:

- `selectedSlotIndex` must be in range.
- `cell.slotIndex == selectedSlotIndex`.
- Soft fields remain conditioning / ordering only.
- `RewardModelOutputV0` may not enter D2.
- D2 and live revalidation are identical to unguided SELECT.
- SELECT reward evaluation must still report contestation distribution, because a fixed slate can also learn cheap low-contestation survival.

### 5.3 PROPOSE-AND-REVALIDATE remains the target

In PROPOSE:

```text
DiffusionGemma: desired outcome + time-window/duration hints + affordances + evidence-to-consider + unresolved needs
Swift: materialize candidates from private state
Swift: validate support, D2-bind evidence, hydrate copy, fingerprint, stage, and write only after tap
```

Plan 5 adds that DiffusionGemma's shape distribution may be conditioned by `u` and guided by a bounded reward model. The proposal still must not contain:

```text
title
start
end
calendarTarget
source kind
source strength
evidence hash
provenance
fingerprint
validation verdict
AllowedActionV0
calendar write action
calendar object identifier
raw person/place/title strings
reward score
contestation score
product verdict
```

Swift treats the shape as importance sampling. It may ignore any hint. If materialization changes the offered `F(x)` policy, that is not free shape sampling; it is an owner-gated `F(x)` change requiring parity tests.

### 5.4 SELECT → PROPOSE graduation by shape-family

Graduation remains per family:

```text
rest -> focus -> prep -> social -> errands -> future owner-approved family
```

A family graduates only if all gates pass:

```text
D2 admit-rate parity;
why-line-true-today audit;
reduced edit-distance and/or rejection;
no undo rise;
no survival-at-T loss;
contestation distribution not collapsed into free space;
positive product verdicts coupled to contestation;
held-out not-needed falsifier not tripped;
owner approval;
SELECT fallback and γ=0 rollback available.
```

Proposal richness alone is irrelevant. Survival alone is insufficient. A green dashboard from rising low-contestation survival is a failure, not a win.

## 6. Pantry membrane: decision-sufficient, non-identifying statistics

The membrane is unchanged in principle. Swift considers all user/calendar data every run. What crosses is not raw data “safely redacted.” What crosses is the set of decision-sufficient, non-identifying statistics: the axes that move the recommendation, never the axes that name the user's life.

Plan 5 extends the same membrane discipline to `u`:

```text
u is not a user dossier.
u is a non-identifying conditioning vector derived from decision axes and earned-accepted history.
```

Raw history strings, event titles, people, places, notes, and low-cardinality identity facts do not cross because the system learned a vector. The vector must preserve preference gradient while removing identity.

### 6.1 `DecisionSufficientStatisticV0` carries forward

```swift
struct DecisionSufficientStatisticV0: Codable, Hashable {
  var schemaVersion: Int
  var statisticID: DecisionStatisticIDV0
  var sourceReceiptHashes: [EvidenceHashV0]
  var axis: DecisionAxisV0
  var valueBand: DecisionValueBandV0
  var coverage: MeasurementCoverageV0
  var redactionRisk: RedactionRiskBandV0
  var computedAt: Date
  var expiresAt: Date?
  var owner: StatisticOwnerV0
}

enum DecisionAxisV0: String, Codable {
  case energyCost
  case socialLoad
  case mobility
  case setupFriction
  case recoveryNeed
  case deadlinePressure
  case gapTopology
  case travelRisk
  case recurrenceRigidity
  case interruptionRisk
  case calendarDensity
  case daypartFit
  case durationFit
  case userStatedConstraint
}

enum DecisionValueBandV0: String, Codable {
  case unavailable
  case low
  case medium
  case high
  case mixed
  case notMeasured
}
```

Trust boundary: conditioning only. A statistic cannot mint support, provenance, source strength, reward, or admission.

### 6.2 No silent truncation and no silent redaction collapse

`ContextProjectionHealthV0` remains mandatory. Context building must fail closed or emit typed measurement when the model-visible packet loses decision-sufficient signal. Missing coverage is `.notMeasured`, never zero.

```swift
struct ContextProjectionHealthV0: Codable, Hashable {
  var schemaVersion: Int
  var contextID: RecommendationContextIDV0
  var rawCandidateCount: Int
  var projectedCandidateCount: Int
  var retainedStatisticCount: Int
  var droppedStatisticCountByReason: [ProjectionDropReasonV0: Int]
  var redactionCollisionGroupCount: Int
  var redactionLossBand: ScoreBandV0
  var compactionOverflowBand: ScoreBandV0
  var measurementStatus: MeasurementStatusV0
}
```

Rules:

- Silent truncation is a context-builder failure.
- Silent redaction collapse is a context-builder failure.
- New model-visible bands require owner approval, copy-honesty coverage, and PII review.
- `u` must carry coverage and redaction-risk metadata just like decision statistics.
- Missing personal history does not become a zero preference.

### 6.3 Privacy floor on raw content

Never crosses the model membrane by default:

```text
raw event titles;
free-text notes or descriptions;
attendee names, emails, or identities;
exact locations or addresses;
raw user-history strings;
low-cardinality facts that identify a person, place, or recurring event;
reward lineage rows that reveal identity;
explicit useful free text, if any, unless separately reduced into closed flags.
```

Free-text notes still never cross. A closed-vocabulary notes affordance extractor remains owner-gated and may emit only audited flags with coverage and redaction-risk metadata; it may not emit substrings.

---

## 7. Relational Prep Station: unchanged, Swift-owned, non-learning prep

The Relational Prep Station carries forward unchanged in authority. It computes relations among events, gaps, and candidate windows and hands DiffusionGemma relation chips as consultable context.

The important Plan-5 reconciliation:

```text
Nothing learns inside the Relational Prep Station.
Learning is allowed only in the composer / preference / reward path, behind owner gates.
```

Relation chips never carry support, provenance, source strength, admission, verdicts, fingerprints, actions, writes, or reward. If a topology relation changes offered feasibility, it is no longer a chip; it is an owner-gated `F(x)` policy change requiring parity tests.

### 7.1 `RelationChipV0` carries forward

```swift
struct RelationChipV0: Codable, Hashable {
  var schemaVersion: Int
  var chipID: RelationChipIDV0
  var relationClass: RelationClassV0
  var subjects: [RelationSubjectDigestV0]
  var relationKind: RelationKindV0
  var valueBand: DecisionValueBandV0
  var evidenceHashes: [EvidenceHashV0]
  var coverage: MeasurementCoverageV0
  var visibility: RelationVisibilityV0
  var heuristic: Bool
  var computedAt: Date
  var expiresAt: Date?
}

enum RelationClassV0: String, Codable {
  case nonSemanticToNonSemantic
  case semanticToNonSemantic
  case semanticToSemantic
}

enum RelationVisibilityV0: String, Codable {
  case swiftOnly
  case modelConditioning
  case suppressedIdentityRisk
  case notMeasured
}
```

### 7.2 Relation priority remains

1. `nonSemanticToNonSemantic`: topology first.
2. `semanticToNonSemantic`: heuristic, flagged, non-citable unless D2 and `CopyHonestyGate` approve.
3. `semanticToSemantic`: suppressed by default, last or never.

---

## 8. Canonical contracts

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
}
```

Reward and training must treat every non-`measured` status as unavailable. It is neither zero nor positive.

## 9. D2 and the admission wall

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

## 10. End-to-end flows

### 10.1 Public SELECT flow with optional reward conditioning

```mermaid
sequenceDiagram
  participant U as User
  participant C as Codex
  participant S as Swift
  participant P as Preference Store u
  participant R as Reward Model r
  participant D as DiffusionGemma
  participant B as D2 + validators
  participant W as Write tail
  participant A as Contestation / reward layer

  U->>C: recommendation request
  C->>S: bounded turn payload
  S->>S: read all private state; compute decision stats
  S->>S: enumerate F(x) as slateOfferedV0
  S->>P: fetch u or population prior if owner-gated
  S->>R: apply RewardGuidancePolicyV0 if enabled
  S->>D: RecommendationContextV1 + optional analysis conditioning
  D-->>S: RecommendationSelectionInfillV0
  S->>S: sanitize and strip authority / reward / contestation echoes
  S->>B: selected cell + evidence registry
  B->>B: D2 lookup + live F(x_live) revalidation
  B-->>S: Swift-hydrated staged card or typed no-rec
  S-->>C: admitted card + server-minted actions + optional product-verdict affordance
  C-->>U: one-line card
  U->>S: confirm tap, reject, reroll, or product verdict
  S->>W: write / undo / rejection lineage
  W->>A: value signals + contestation + product verdict reduction
```

Reward may influence which feasible cell is selected. It cannot widen the slate, modify the cell, create evidence, skip D2, mint an action, or claim contestation.

### 10.2 Shadow PROPOSE with reward-guided composition

```mermaid
sequenceDiagram
  participant U as User
  participant C as Codex
  participant S as Swift
  participant P as Preference Store u
  participant R as Reward Model r
  participant D as DiffusionGemma
  participant M as Swift materializer
  participant B as D2 + validators
  participant A as Contestation / reward layer

  U->>C: recommendation request
  C->>S: bounded turn payload
  S->>S: read private state; compute decision stats + relation chips
  S->>P: fetch u or population prior
  S->>R: prepare bounded guidance policy gamma / KL status
  S->>D: RecommendationContextV1 + u + reward guidance
  D-->>S: RecommendationShapeProposalV0
  S->>S: reject concrete fields, reward fields, contestation fields, and unsafe why-line draft
  S->>M: materialize candidate support from private state
  M-->>S: Swift-owned SlateCellV0 candidates
  S->>B: D2 lookup + live F(x_live) revalidation
  B-->>S: admitted staged card or typed failure
  S->>A: compare against SELECT / deterministic counterfactuals backstage
```

PROPOSE shadow results do not change public traffic until measured. Every admitted shadow card passes the same D2 wall and live revalidation as SELECT.

### 10.3 Confirm and write flow — unchanged

```text
staged card
  -> user confirm tap
  -> live support recheck
  -> post-picker fingerprint
  -> write
  -> undo/edit/delete/survival-at-T measurement
```

Writes require a server-minted confirm action and a live confirm-time recheck. The action is short-lived, scoped to the staged card, and invalidated by changed support. Swift never touches calendar objects it did not create.

### 10.4 Product-verdict flow

```text
admitted card / undo surface
  -> lightweight verdict affordance always available where product-approved
  -> user may say useful / not today / wrong / not needed / skip
  -> Swift records UserProductVerdictSignalV0
  -> negative verdict zeroes or penalizes reward
  -> positive verdict may help only under contestation coupling
```

Availability is unthrottled. Solicitation is not. The system may rarely ask under owner-gated policy, but the default posture is that the user can judge the product whenever the product is in front of them.

### 10.5 Learning / reward path

```mermaid
sequenceDiagram
  participant W as Write tail
  participant V as RecommendationValueSignalV0
  participant C as ContestationSignalV0
  participant P as Product verdict channel
  participant A as Earned-Acceptance Reducer
  participant U as Preference Store u
  participant R as Reward Model r
  participant G as Contestation / drift monitor
  participant F as Comfortable-FP falsifier
  participant O as Owner Gate
  participant D as DiffusionGemma

  W->>V: request/context/proposal/confirm/write/edit/delete/survival lineage
  W->>C: calendar-pressure contestation, excluding CalAgent-created demand
  P-->>A: optional useful / notToday / wrong / notNeeded / skipped
  V->>A: edit-distance + survival-at-T + rejections + fingerprints
  C->>A: contestation weight + created-event boundary + reconfirmation brake
  A->>A: require lineage + both fingerprints + contestation boundary; .notMeasured never zero
  A-->>U: contestation-weighted reward update when measured
  A-->>R: training label / preference pair when owner-gated
  G->>O: contestation distribution / drift report
  F->>O: held-out raw not-needed kill condition
  O-->>R: allow, reduce gamma, freeze family, eject to SELECT
  U-->>D: u as non-identifying conditioning
  R-->>D: bounded gamma guidance or offline DPO weights
```

Learning path cannot reach D2. Its outputs can only change future composition under owner gates. The falsifier is outside the optimized reward path.

## 11. Earned acceptance, contestation, and preference learning

### 11.1 Definition

Earned acceptance is no longer raw accepted ∧ survived ∧ low-edit. That predicate is necessary but not enough.

```text
behavioral_earned = accepted
                  AND survived-to-T
                  AND low edit-distance
                  AND no negative product verdict

reward_credit = behavioral_earned
              × contestation_weight
              × revealed_reconfirmation_brake
              × created_event_boundary
```

Where:

- `accepted` means the user tapped the server-minted confirm action.
- `survived-to-T` is `SurvivalAtTSignalV0.survived`, measured near the event horizon, not at tap.
- `low edit-distance` is `RecommendationEditDistanceV0.aggregateEditDistanceBand` low.
- `negative product verdict` is `notToday`, `wrong`, or `notNeeded` from `UserProductVerdictSignalV0`.
- `contestation_weight` measures how much the recommendation occupied space the user otherwise had reason to use.
- `revealed_reconfirmation_brake` prevents passive inertia from earning high credit.
- `created_event_boundary` prevents the system from creating demand and then rewarding itself for competing with that demand.

The guardrail is **non-regret under contestation**. Value remains unverified.

### 11.2 Why raw survival is not a bound

A card in empty space can survive because deletion costs attention. That is not value. It is low cost-of-removal.

The divergent loop Plan 5 must avoid is:

```text
family graduates because survival + low-edit is cheap in uncontested space
  -> earned-accepted history becomes comfortable-FP-rich
  -> Phase-1 prior behavior-clones that history
  -> KL leash holds Phase-2 close to the corrupted prior
  -> next round finds even lower contestation
  -> survival rises and dashboard turns greener
```

This is success-signed corruption. γ is not enough because the loop can corrupt the prior before γ matters. KL is not enough because a leash to a corrupted prior is anti-corrective. The why-line gate is not enough because a true-today why-line can still describe an unneeded card. Population drift is not enough because the shift can occur through family-level low-contestation selection rather than a uniform taste shift.

### 11.3 Contestation-weighted survival

`ContestationSignalV0` credits survival in proportion to how tested the recommendation was:

```text
zero / low pressure gap     -> near-zero reward credit even if survived
moderate pre-existing demand -> partial reward credit if kept without regret
high real alternative        -> high reward credit only with revealed re-confirmation
```

The signal is computed from calendar pressure Swift already owns. It uses banded, non-identifying features; it does not send raw titles, people, locations, or notes across the membrane. It measures only against events and pressure CalAgent did not create.

Contestation is a loop metric, not a user-facing claim. The card must never say:

```text
this was highly contested;
you kept this over alternatives;
we learned this was valuable.
```

### 11.4 The two brakes

#### 11.4.1 Revealed-reconfirmation brake

Never pay high contestation credit on passive survival alone. A grudgingly-kept intrusive card is the high-end cousin of the comfortable false positive.

High contestation credit requires a revealed-reconfirmation source stronger than `passiveSurvivalOnly`, such as:

- an explicit positive product verdict;
- a user edit that keeps the CalAgent-created block rather than deleting or moving it away from the contested zone;
- an owner-approved active keep/reconfirm affordance that is not solicited constantly.

If revealed re-confirmation is missing, high contestation credit is capped or `.notMeasured` by policy. Initial confirm tap alone is not enough to prove high-contestation value, because the tap is consent to write, not proof of need.

#### 11.4.2 Created-event boundary in reverse

Plan 4 already forbids Swift from touching calendar objects it did not create. Plan 5 adds the reverse measurement boundary:

```text
Measure contestation only against calendar demand CalAgent did not create.
```

Otherwise the system can manufacture the demand it later competes with. Any CalAgent-created event, any derivative of a CalAgent-created event, and any event whose origin cannot be proven non-CalAgent is excluded from contestation. If the boundary cannot be proven, contestation is `.notMeasured`.

### 11.5 Product-verdict channel

The explicit channel is reframed from “was this useful?” to a lightweight product verdict:

```text
useful
not today
wrong
not needed
skip
```

The object of judgment is the card, not the user. This flips the surveillance relation: the user is not being watched for compliance; the user is watching the product.

This channel is also the deepest preference probe in the system. It is safe only by what is done with the verdict:

- Raw free text is off by default.
- Responses are reduced into typed flags.
- Negative verdicts zero or penalize reward.
- Positive verdicts are coupled to contestation; they cannot create high reward in free space by themselves.
- Availability is unthrottled on approved surfaces.
- Solicitation is rare, owner-gated, and never framed as grading the user.

### 11.6 The residual risk: comfortable false positive

The residual remains:

```text
The comfortable false positive:
a pleasant permission the user accepts, never regrets, and did not actually need.
```

Plan 5 no longer calls this “bounded” by survival/edit/regret terms. Those terms are exactly what the comfortable false positive can satisfy.

Contestation does not buy a true value verifier. It relocates the residual from the blind region to the observable region. A free-gap comfortable false positive earns little reward. If the composer Goodharts contestation by becoming intrusive, the failure becomes loud: undo, edit, delete, `notToday`, `wrong`, `notNeeded`, and high-contestation regret rise.

The remaining irreducible case is a card that is contested, actively re-confirmed, never regretted, and still not actually needed. There is no behavioral signal that can fully identify that. It is the price of learning under unverified value, and it is why the falsifier exists.

### 11.7 Held-out falsifier before the fix is trusted

Before contestation-weighted reward can steer public traffic, the system must pre-register a kill condition outside the optimized metric:

```text
held-out contestation-blind cohort
  -> raw not-needed / not-today / wrong rate
  -> stratified by contestation for diagnosis
  -> kill condition wired to SELECT eject
```

This is measurement-before-mutation applied to the remedy itself. A remedy that cannot fail loud cannot be trusted.

### 11.8 Learning what the user values and accepts

The preference store learns both:

```text
values: shape properties that correlate with contestation-weighted earned acceptance and product verdicts;
acceptance: shape properties that the user taps without later regret, corrected by contestation.
```

It learns across all owner-approved recommendation types. The cold-start path uses a population prior warmed per user. A new user is not treated as a vector of zeros.

## 12. DiffusionGemma 0-to-1 build

### 12.1 Phase 0 — Instrument, falsify, and only then mutate

Goal: manufacture a trustworthy reward and a way for the remedy to fail before changing composition.

Build:

- Preserve `RecommendationValueSignalV0` as the source signal.
- Add `ContestationSignalV0` with created-event boundary and revealed-reconfirmation brake.
- Add `UserProductVerdictSignalV0`; availability unthrottled, solicitation throttled.
- Add `EarnedAcceptanceRewardSignalV0` with contestation-weighted reduction.
- Add `ContestationDistributionReportV0` by shape-family.
- Add `ComfortableFalsePositiveFalsifierV0` before reward guidance is trusted.
- Require reward lineage from request through survival window.
- Require pre-picker and post-picker fingerprints.
- Preserve `.notMeasured`-never-zero.
- No weight update.
- No sampler change.
- No public copy claiming learning.

Exit gate:

```text
reward computable on a real cohort;
incomplete lineage emits .notMeasured, not zero;
contestation missing emits .notMeasured, not zero;
created-event boundary violations fail closed;
product-verdict availability and solicitation policy approved;
falsifier kill condition pre-registered and wired to SELECT eject;
no D2 input/output changes.
```

### 12.2 Phase 1 — Learn values from contestation-corrected history

Goal: teach the composer the distribution of shapes this user earns-accepts, without optimizing acceptance pressure yet.

Build:

- `UserPreferenceEmbeddingV0` (`u`) from decision-sufficient statistics + contestation-weighted earned-accepted history.
- Cold-start population prior warmed per user.
- Diffusion behavior-cloning conditioned on `(state,u)`.
- Training across rest, focus, prep, social, errands, and owner-approved families.
- Offline, owner-gated training / adapter updates.
- Shadow evaluation against unconditioned composer.

This is the first Plan-5 learner. It relaxes the no-learner / frozen-model posture, but only for the composer. It does not alter D2.

Exit gate:

```text
u-conditioned composer reproduces contestation-weighted earned-accepted shapes in shadow;
admit-rate parity vs unconditioned composer;
no PII in u;
no learned preference copy overclaims;
low-contestation comfort not overrepresented in training labels;
SELECT fallback remains;
owner gate passed.
```

### 12.3 Phase 2 — Optimize acceptance inside the corrected prior

Goal: push composition toward higher predicted contestation-weighted earned acceptance inside the Phase-1 distribution.

Two options:

#### 12.3.1 Option 2a — reward-guided sampling, recommended v1

```text
r(shape,state,u) guides denoising with bounded scale γ.
Base composer remains frozen.
γ = 0 recovers the Phase-1 prior.
Bounded γ nudges.
Unbounded γ is reward hacking.
```

Why v1 prefers 2a:

- Reversible per request.
- Explicit safety dial.
- No weight movement.
- Easier rollback to γ = 0 or SELECT.
- Does not commit a corrupted reward into weights if the falsifier trips.

#### 12.3.2 Option 2b — Diffusion-DPO, offline alternative

```text
contestation-weighted earned-accepted ≻ rejected / edited / deleted pairs
train with KL leash to the contestation-corrected Phase-1 prior
```

This moves weights and is not reversible per request. It is more committal than 2a and must not ship before 2a demonstrates safe lift. The KL leash is allowed only after Phase 1 is corrected by contestation; otherwise it can preserve a comfortable-FP-rich prior.

Exit gate for Phase 2:

```text
reduced edit-distance and/or rejection;
no undo rise;
no survival-at-T loss;
contestation distribution not collapsed;
no high-contestation regret rise;
raw not-needed falsifier not tripped;
admit-rate parity;
why-line-true-today audit pass;
bounded γ / KL enforced;
owner-gated public movement only.
```

### 12.4 Phase 3 — Guard drift and coupling

Goal: watch the loop, not only the parts.

Build:

- `ContestationDistributionReportV0` per family and release window.
- `PopulationRewardDriftReportV0` with contestation shift.
- `ComfortableFalsePositiveFalsifierV0` on held-out contestation-blind cohorts.
- Product-verdict review and solicitation cadence limits.
- Hard `CopyHonestyGate` for why-line-true-today.
- γ / KL owner bounds by shape-family.
- Frozen-base rollback path for 2a.
- SELECT deterministic fallback.

A uniform shift toward “everyone accepts more of X” is a flattery tell. A shift toward “everyone accepts more X in low-contestation space” is the comfortable-FP tell. Intrusion Goodhart is the opposite signature: contestation rises, but regret and negative verdicts rise too.

### 12.5 Curriculum

Start in SELECT, graduate to PROPOSE per shape-family:

```text
M3 SELECT public on revised context
  -> SELECT reward shadow
  -> SELECT bounded guidance by family
  -> PROPOSE shadow with u
  -> PROPOSE reward-guided shadow
  -> fixed-pool SELECT-vs-PROPOSE value + contestation evaluation
  -> public PROPOSE gate by family
```

Reward earns trust only by reducing edit-distance / rejection without increasing undo, lowering survival-at-T, collapsing contestation, or tripping the held-out not-needed falsifier.

## 13. Swift-owned scoring, discrimination, and measurement

Swift may rank already-admitted candidates. Swift may not replace correctness with a value guess, and DiffusionGemma may not grade itself.

### 13.1 Correctness verifier

The correctness verifier is decidable and admission-critical:

- D2 receipt/source binding.
- Live `F(x_live)` revalidation.
- Duplicate policy.
- Write-target policy.
- PII and copy-honesty scan.
- Fingerprinting.
- Server-minted confirm action.
- Confirm-time live recheck.

This verifier answers:

```text
May this staged artifact be shown and written if the user taps?
```

### 13.2 Earned value layer

The value layer answers a weaker question:

```text
Did this recommendation appear to fit after user interaction, and was that fit actually tested?
```

It uses:

- edit-distance;
- logged rejections and counterfactual slates;
- survival-at-T;
- contestation-weighted survival;
- revealed-reconfirmation brake;
- created-event boundary;
- post-write undo / delete / move;
- product verdicts (`useful`, `notToday`, `wrong`, `notNeeded`);
- deterministic baseline delta;
- population drift;
- held-out not-needed falsifier.

No value signal can make an invalid artifact valid.

### 13.3 `PickDiscriminatorV0`

`PickDiscriminatorV0` remains a small Swift-owned ranking layer over admitted candidates. It is not a second LLM verifier and not the reward model.

Allowed features after coverage and owner gates remain:

- D2 admission success;
- live staleness outcome;
- copy-honesty pass;
- selected-cell soft score band;
- decision-stat coverage;
- relation-chip coverage;
- source-kind outcome rates;
- edit-distance risk bands;
- post-write undo risk;
- survival-at-T bands;
- contestation coverage bands;
- product-verdict risk bands;
- deterministic baseline delta;
- diversity penalty among admitted candidates;
- stale-risk bands.

Forbidden features remain:

- model confidence as feasibility;
- model self-rank as usefulness;
- model-authored source strength;
- model-authored evidence kind;
- raw PII;
- unmeasured metrics as zero;
- sampler or re-noising confidence as quality;
- reward score as correctness;
- contestation score as copy;
- any value signal visible to the user as a grade.

Plan-5 distinction:

```text
PickDiscriminatorV0 ranks admitted candidates.
Reward-guided diffusion steers proposal composition upstream of D2.
ContestationDistributionReportV0 gates release of the learned loop.
Do not route reward through PickDiscriminatorV0 as an authority proxy.
```

### 13.4 Measurement before mutation is re-scoped, not deleted

Old meaning:

```text
No adaptive ranking, preference update, relation-chip promotion, or PROPOSE public launch until lineage and both fingerprints exist.
```

Plan-5 meaning:

```text
No reward may guide, no u update may train, no DPO pair may enter, and no public guidance may launch until:
  lineage exists;
  both fingerprints exist;
  contestation is measured or explicitly .notMeasured;
  the created-event boundary passes;
  the revealed-reconfirmation brake is applied;
  the product-verdict policy is approved;
  the falsifier is built and has not tripped.
```

Measurement-before-mutation is stronger because it guards training gradients, release gates, and the remedy itself.

### 13.5 Component monitors are not enough

Plan 5 introduces one loop-level monitor because the risk lives in coupling:

```text
release gate -> training prior -> KL leash / γ -> new release gate
```

A componentwise firewall can pass while the loop diverges. The contestation distribution report is therefore a standing release artifact, not a dashboard curiosity.

## 14. Privacy, redaction, and copy honesty

Privacy remains product correctness. The user hands over sacred calendar space only because the architecture does not leak who and where across the membrane.

### 14.1 Raw-content floor

Never crosses the model membrane by default:

- raw event titles;
- free-text notes or descriptions;
- attendee names, emails, or identities;
- exact locations or addresses;
- raw user history strings;
- low-cardinality facts that identify a person, place, or recurring event;
- raw reward lineage rows;
- raw product-verdict free text;
- raw contestation preimages;
- raw falsifier cohort membership.

Swift may read these fields to compute decision-sufficient statistics, contestation, and `u`. Swift may not transmit them raw.

### 14.2 Copy honesty

The why-line is the permission slip. It must be true today and supported by admitted evidence. Copy that overclaims personalization is a staging failure.

`CopyHonestyGate` blocks:

- unsupported claims about preference;
- claims naming people or places that never crossed safely;
- claims that imply source strength the model cannot know;
- claims that cite heuristic relation chips as learned truth;
- claims that use backstage measurement or reward behavior as copy;
- claims like “you usually accept this” from `u` or reward;
- reward-score language;
- contestation-score language;
- product-verdict language;
- drift / experimentation language.

A valid time with an unsupported why-line is still a false recommendation. A true why-line on an unneeded card can still be a bad recommendation; copy honesty is necessary, not sufficient.

### 14.3 User-facing privacy rule

No user-facing copy may use the internal restaurant metaphor. No user-facing copy may imply the system knows more than it safely exposes. No user-facing copy may say or imply:

```text
we learned you do X;
you always accept X;
people like you prefer X;
this has a high reward score;
this was highly contested;
you kept this over alternatives;
this is optimized for acceptance;
your answer trains the system.
```

The product may be personalized. It must not sound like surveillance.

### 14.4 Product-verdict privacy rule

The product-verdict channel is informationally deep. It is safe only by the limits on use:

- it is a verdict on the card, not the user;
- it uses typed choices by default;
- positive responses are coupled to contestation;
- negative responses are honored as product failure signals;
- no free text by default;
- no copy claims from verdict history;
- no admission changes from verdicts.

## 15. User experience invariants

The human is the principal. The confirm tap is consent and the return of authority. The calendar is sacred space.

### 15.1 Earn the confirm tap, then disappear

Everything before the tap justifies the tap. Nothing after it asks for attention except instant undo, clear failure recovery, and a user-directed way to say the product was wrong.

The card should be:

```text
what: one proposed block / activity / recommendation shape
when: where it will land if confirmed
why: true today, not generic
control: confirm, dismiss, reroll, undo, product verdict
```

### 15.2 Felt safety

Felt safety is not a banner that says “validated” or “personalized.” Felt safety is the absence of dread at the tap:

- the block lands where expected;
- undo is instant;
- the system never touches anything it did not create;
- no private person/place details leak into the card;
- conflict failures are typed and calm;
- no auto-write exists;
- learning never feels like surveillance;
- the user can say “not today,” “wrong,” or “not needed” without being graded.

### 15.3 Sacred calendar invariants

These are inviolable:

```text
Never write without the confirm tap.
Never edit, move, delete, or overwrite anything the system did not create.
Never leak who/where/raw private strings across the membrane.
Never let measurement become visible surveillance.
Never let reward or learning become admission authority.
Never let the system manufacture demand and then reward itself for contesting it.
```

### 15.4 Personalization copy boundary

Allowed:

```text
“A quiet 25-minute reset fits the narrow gap before your evening block.”
“A short prep block now protects the denser part of your afternoon.”
```

Forbidden unless explicitly supported by user-stated evidence and copy budget:

```text
“You like quiet resets.”
“You usually accept this kind of break.”
“We learned you prefer errands after work.”
“You kept this over another option.”
```

### 15.5 Product-verdict UX boundary

Preferred affordance labels are product-directed:

```text
Not today
Wrong
Not needed
Useful
```

Avoid user-directed or confession-shaped labels:

```text
I was wrong
Teach my preferences
Train on this
Why did I reject it?
```

Availability may be broad. Solicitation must be rare.

## 16. Migration sequence

Plan 5 replaces plan-4 §14 with a back-half-safe migration sequence. The wall milestones are inherited; the learning, contestation, and falsifier milestones are new.

### M0 — Wall freeze and Plan-5 doctrine update

- Adopt Plan 5 as canonical.
- Mark `plan-4-revised(10).md` deprecated.
- Add amended doctrine and architecture law to architecture docs.
- Book three relaxations: reward may steer, composer may learn, and the machine now has a stake in yes.
- Add explicit rule: reward steers composition; D2 admits; contestation/falsifier gate graduation.
- Add lint that `RewardModelOutputV0`, `UserPreferenceEmbeddingV0`, `EarnedAcceptanceRewardSignalV0`, `ContestationSignalV0`, and `UserProductVerdictSignalV0` cannot appear in D2 output or user copy.

Acceptance:

- One locatable doctrine.
- One four-clause law.
- One role map.
- No component described in another component's authority terms.
- D2 unchanged.
- Loop-coverage self-audit added as a standing release gate.

### M1 — Phase 0 instrumentation and falsifier-before-fix

- Add `ContestationSignalV0`.
- Add `UserProductVerdictSignalV0` and `ProductVerdictPolicyV0`.
- Add `EarnedAcceptanceRewardSignalV0` with contestation weighting.
- Add `ContestationDistributionReportV0`.
- Add `ComfortableFalsePositiveFalsifierV0` before guidance is trusted.
- Require reward lineage and both fingerprints.
- Preserve `RecommendationValueSignalV0` as source signal.
- Add `.notMeasured`-never-zero reward tests.

Acceptance:

- Incomplete reward terms emit `.notMeasured`.
- Missing contestation emits `.notMeasured`, not zero.
- Survival in low-contestation space earns near-zero credit.
- Created-event boundary in reverse passes.
- Revealed-reconfirmation brake applies.
- Product-verdict availability is unthrottled where approved; solicitation is throttled.
- Held-out raw not-needed kill condition is pre-registered and wired to SELECT eject.
- No sampler or model behavior changes.

### M2 — Preference store shadow

- Add `UserPreferenceEmbeddingV0` and `PreferenceEmbeddingUpdateV0`.
- Build population prior from consented, non-identifying aggregates.
- Cold-start users receive population prior, not zeros.
- Compute `u` shadow-only; do not feed public composer yet.
- Use contestation-weighted labels only; raw survival labels are excluded from positive training.
- Add PII/redaction/cross-user leakage tests.

Acceptance:

- `u` contains no raw identity.
- `u` cannot gate admission.
- Missing history does not penalize a user.
- Preference and contestation coverage are measurable by shape-family.

### M3 — SELECT reward-conditioning shadow

- Keep public traffic on unguided or existing SELECT lane.
- Run shadow SELECT with `u` and γ=0 / γ-small variants.
- Reward can only choose among already-feasible `SlateCellV0` cells.
- Compare against deterministic and unguided SELECT.
- Report contestation distribution even in SELECT.

Acceptance:

- Admit-rate parity.
- Same D2 wall.
- No change to `F(x)`.
- No copy-honesty regression.
- No user-visible measurement language.
- Low-contestation reward share below owner threshold.
- Held-out falsifier not tripped.

### M4 — Phase 1 behavior-cloning shadow

- Train / adapter-tune DiffusionGemma to reconstruct contestation-weighted earned-accepted shapes conditioned on `(state,u)`.
- Cover rest, focus, prep, social, errands.
- No acceptance-optimization pressure yet.
- Keep PROPOSE shadow-only.

Acceptance:

- `u`-conditioned composer reproduces earned-accepted shape distributions after contestation correction.
- Admit-rate parity vs unconditioned composer.
- No authority fields in model output.
- Low-contestation comfort not overrepresented.
- Owner gate for any weight-moving path.

### M5 — Phase 2a reward-guided sampling shadow

- Add `RewardModelInputV0`, `RewardModelOutputV0`, and `RewardGuidancePolicyV0`.
- Train lightweight `r(shape,state,u)` on measured contestation-weighted earned-acceptance labels.
- Use bounded γ during denoising with base composer frozen.
- Start in SELECT, then PROPOSE shadow by family.

Acceptance:

- γ=0 recovers Phase-1 behavior.
- Bounded γ improves edit-distance and/or rejection without undo rise or survival loss.
- Contestation distribution does not collapse.
- High-contestation regret does not rise.
- Reward output absent from D2.
- Drift, contestation, and falsifier reports current.
- Owner gate passed.

### M6 — Fixed-pool SELECT-vs-PROPOSE evaluation

- Run fixed request cohorts.
- Compare SELECT vs PROPOSE, guided vs unguided, population vs personal `u`.
- Measure edit-distance, rejection, survival-at-T, undo, stale attribution, copy-honesty, deterministic baseline delta, product verdicts, contestation distribution, and raw not-needed falsifier rate.

Acceptance:

- Proposal richness alone irrelevant.
- Survival alone insufficient.
- Family graduates only with value-signal lift, unchanged correctness, healthy contestation distribution, and untripped falsifier.
- Contestation-blind held-out cohort remains outside the optimized metric.

### M7 — Public guidance by shape-family

- Promote one family at a time.
- Keep SELECT deterministic fallback.
- Keep γ owner-bounded and remotely reducible to 0.
- Require current drift, contestation, and falsifier reports.
- Require why-line audit.
- Re-answer the loop-coverage self-audit for each family.

Acceptance:

- Public guidance cannot widen `F(x)`.
- D2 unchanged.
- Confirm tap unchanged.
- No “we learned” copy.
- Low-contestation reward share below threshold.
- Product verdict solicitation within cadence.
- Owner-approved rollback path.

### M8 — Optional Diffusion-DPO research gate

- Build `DiffusionDPOTrainingExampleV0` only after 2a proves safe.
- Train offline on contestation-weighted earned-accepted ≻ rejected/edited/deleted pairs.
- KL-leash to contestation-corrected Phase-1 prior.
- Treat as weight-moving and non-reversible per request.

Acceptance:

- Separate owner approval from 2a.
- KL bound enforced.
- Catastrophic-forgetting / drift review.
- Falsifier and contestation gates pass under the tuned model.
- Rollback model version defined.
- Never required for public Plan-5 v1.

## 17. Test matrix

| Test | Target | Milestone | Invariant |
|---|---|---:|---|
| `testPlan5SupersedesPlan4Revised10` | docs / architecture lint | M0 | plan-5 is canonical; plan-4 deprecated. |
| `testOpeningDoctrineIsSingleSentence` | docs / architecture lint | M0 | One doctrine, locatable at top. |
| `testFourClauseArchitectureLawExists` | docs / architecture lint | M0 | One four-clause law. |
| `testThirdRelaxationBooked` | docs / architecture lint | M0 | Machine stake in yes is named, not hidden. |
| `testLoopCoverageSelfAuditRequiredEachRelease` | release tests | M0/M7 | Wall coverage must be re-answered as power migrates upstream. |
| `testCodexCannotAdmitOrGrade` | carrier tests | all | Codex relays and serves only. |
| `testDiffusionGemmaCannotAuthorAuthorityFields` | analysis tests | M3-M8 | No title/time/calendar/evidence/provenance/fingerprint/action. |
| `testDiffusionGemmaCannotAuthorRewardOrContestation` | analysis tests | M3-M8 | No reward score, contestation score, or product verdict in model output. |
| `testSwiftOwnsAllAdmissionCriticalFields` | validator tests | all | Swift validates, admits, writes, measures. |
| `testDecisionStatsContainNoRawIdentity` | redaction tests | M1+ | Statistics move decision without naming life. |
| `testDecisionStatsPreserveUtilityAxes` | context tests | M1+ | Redaction does not erase decision gradient silently. |
| `testContextProjectionHealthEmitsOnTruncation` | context tests | M1+ | No silent truncation. |
| `testRedactionCollapseIsTyped` | context tests | M1+ | No silent redaction collapse. |
| `testFreeTextNotesNeverCrossMembrane` | redaction tests | M1+ | Notes floor preserved. |
| `testRelationChipNoSupportFields` | prep station tests | M1+ | Relation chips are consultable context only. |
| `testSlateCellIndexEqualsArrayIndex` | contract tests | M3 | SELECT index identity cannot drift. |
| `testShapeProposalRejectsConcreteTitle` | propose tests | M4+ | Shape proposal cannot author write identity. |
| `testShapeProposalRejectsConcreteTime` | propose tests | M4+ | Shape proposal cannot author write time. |
| `testShapeProposalEvidenceHashesEmpty` | propose tests | M4+ | Shape proposal cannot author evidence basis. |
| `testSwiftMaterializesShapeIndependently` | materializer tests | M4+ | Proposal shape is not support. |
| `testD2LookupUsesReceiptOwningSource` | D2 tests | all | Lookup, not reconstruction. |
| `testD2InProcessOnly` | topology tests | all | No admission RPC. |
| `testSupportStagedSubsetOfLiveF` | validator tests | all | Live validation wall. |
| `testRecommendationVerdictNonCodable` | contract tests | all | Verdict cannot be transported by model. |
| `testConfirmTapRequiredForWrite` | write tests | all | Tap is consent. |
| `testCannotTouchNonCreatedEvents` | calendar mutation tests | all | Sacred calendar invariant. |
| `testCreatedEventBoundaryReverse` | contestation tests | M1+ | Contestation measured only against non-CalAgent-created demand. |
| `testContestationSignalExcludesCalAgentCreatedEvents` | contestation tests | M1+ | System cannot manufacture demand it competes with. |
| `testSurvivalInUncontestedSpaceGetsZeroContestationCredit` | reward tests | M1+ | Free-gap survival cannot train value. |
| `testContestationCreditRequiresRevealedReconfirmation` | reward tests | M1+ | Passive survival cannot earn high contestation credit. |
| `testNegativeProductVerdictZerosReward` | reward tests | M1+ | `notToday` / `wrong` / `notNeeded` zero or penalize. |
| `testPositiveVerdictCannotOvercomeZeroContestation` | reward tests | M1+ | `useful` cannot Goodhart into bland unobjectionable cards. |
| `testProductVerdictAvailabilityUnthrottledSolicitationThrottled` | UX / product tests | M1+ | User can judge product; system does not constantly ask. |
| `testProductVerdictNoFreeTextByDefault` | privacy tests | M1+ | Deep preference probe is reduced to typed flags. |
| `testEditDistanceRequiresBothFingerprints` | value tests | M1+ | Measurement before mutation. |
| `testRejectedSlateLoggedBackstageOnly` | value tests | M1+ | Rejections carry gradient invisibly. |
| `testSurvivalAtTNotAtTapOnly` | value tests | M1/M6 | Survival measured near event horizon. |
| `testRawSurvivalCannotTrainReward` | reward tests | M1+ | Survival must be contestation-weighted. |
| `testRewardTrainingExampleRequiresMeasuredReward` | training data tests | M4/M8 | No `.notMeasured` gradient. |
| `testPreferenceEmbeddingContainsNoRawIdentity` | privacy / ML tests | M2+ | `u` respects membrane. |
| `testPreferenceEmbeddingCannotGateAdmission` | D2 / ML tests | M2+ | `u` is conditioning only. |
| `testColdStartUsesPopulationPriorNotZeros` | personalization tests | M2+ | Missing history is not negative preference. |
| `testRewardModelOutputAbsentFromD2` | D2 / API tests | M5+ | Reward cannot become admission. |
| `testRewardModelCannotManufactureContestation` | reward model tests | M5+ | No reward for invented demand or intrusive contestation. |
| `testGammaZeroRecoversPrior` | sampler tests | M5+ | Bounded guidance reversible. |
| `testGammaBoundEnforced` | sampler tests | M5+ | No unbounded reward optimization. |
| `testProposeAdmitRateParity` | guidance parity tests | M5/M6 | Guidance cannot change wall verdict distribution. |
| `testProposeReducesEditDistanceWithoutUndoRise` | eval tests | M6 | Value lift without regret rise. |
| `testContestationDistributionMustNotCollapseOnGraduation` | release tests | M6/M7 | Family cannot graduate on cheap low-contestation survival. |
| `testHighContestationRegretRiseBlocksGraduation` | release tests | M6/M7 | Intrusion Goodhart is loud and blocks. |
| `testComfortableFPFalsifierBuiltBeforeRewardGuidance` | evaluation tests | M1/M5 | Remedy has an external kill condition before use. |
| `testHeldOutNotNeededRateWiredToSelectEject` | evaluation tests | M6/M7 | Raw not-needed failure ejects family. |
| `testNotNeededRateStratifiedByContestation` | evaluation tests | M6/M7 | Diagnosis sees where residual lives. |
| `testPopulationDriftUniformShiftTriggersOwnerReview` | drift tests | M5/M7 | Flattery tell is monitored. |
| `testPublicGuidanceRequiresCurrentDriftContestationAndFalsifierReports` | release tests | M7 | No stale loop review. |
| `testPublicProposeRequiresOwnerGate` | release tests | M7 | Shadow-first public launch. |
| `testShapeFamilyGraduatesIndependently` | release tests | M7 | No global PROPOSE switch. |
| `testDPOTrainingRequiresKLLeashToContestationCorrectedPrior` | DPO tests | M8 | KL leash cannot preserve corrupted prior. |
| `testDPOPathIsNotV1Default` | release tests | M8 | Frozen-base 2a preferred before 2b. |
| `testWhyLineTrueTodayAudit` | evaluation tests | M4+ | Composition must be day-specific. |
| `testWhyLineTrueTodayDoesNotCertifyNeed` | docs / eval tests | M0+ | Copy honesty is not value verification. |
| `testCopyHonestyBlocksRewardClaims` | copy tests | all | No reward / contestation / learning claims in copy. |
| `testNoUserFacingRestaurantCopy` | UX copy tests | all | Internal metaphor never surfaces. |
| `testNoUserFacingLearningCopyFromBackstageSignals` | UX copy tests | all | Personalization without surveillance copy. |
| `testNotMeasuredNeverZero` | measurement tests | all | Missing data cannot promote or penalize. |
| `testComfortableFalsePositiveRiskDocumented` | docs / architecture lint | M0 | Residual risk is not claimed solved. |

## 18. Definition of done

- [ ] The document opens with one governing doctrine, one amended four-clause law, and one internal role map.
- [ ] The role map names Codex, DiffusionGemma, Swift, Relational Prep Station, Reward Reducer, Contestation Auditor, Product Verdict Channel, Preference Store, Reward Model, and Comfortable-FP Falsifier.
- [ ] The three scoped relaxations are named: reward may steer, composer may learn, and the machine now has a stake in yes.
- [ ] D2 remains the only net-new admission-critical seam, in-process Swift.
- [ ] `support(staged) ⊆ F(x_live)` is preserved in SELECT and PROPOSE.
- [ ] `RecommendationVerdictV0` remains non-`Codable`.
- [ ] `AllowedActionV0` remains server-minted only after staging.
- [ ] Confirm tap remains required; no auto-write exists.
- [ ] Swift never touches calendar objects CalAgent did not create.
- [ ] The hydration firewall blocks model-authored title, time, calendar target, evidence hash, source kind, source strength, provenance, fingerprint, verdict, action, reward, contestation, and product verdict.
- [ ] Swift considers all private state every run and transmits only decision-sufficient, non-identifying statistics.
- [ ] Free-text notes, raw event titles, attendees, exact locations, and low-cardinality identity facts stay behind Swift.
- [ ] The Relational Prep Station remains Swift-owned, non-learning, and non-authoritative.
- [ ] Earned acceptance is contestation-weighted; raw survival cannot train reward.
- [ ] Survival in uncontested space is disclosed as cost-of-removal risk, not value.
- [ ] `ContestationSignalV0` exists and excludes CalAgent-created demand.
- [ ] Revealed-reconfirmation brake exists; passive survival cannot earn high contestation credit.
- [ ] `UserProductVerdictSignalV0` is product-directed; availability is unthrottled, solicitation throttled.
- [ ] Positive product verdicts are coupled to contestation; negative verdicts zero or penalize reward.
- [ ] `ComfortableFalsePositiveFalsifierV0` is built before reward guidance is trusted.
- [ ] Falsifier kill condition is pre-registered, contestation-blind as a primary metric, and wired to SELECT eject.
- [ ] `UserPreferenceEmbeddingV0` uses contestation-weighted earned-accepted history, not raw survival-only labels.
- [ ] `RewardModelOutputV0` and `RewardGuidancePolicyV0` cannot appear in D2 output or copy.
- [ ] γ is bounded and γ=0 recovers the prior.
- [ ] Diffusion-DPO is optional, offline, KL-leashed to a contestation-corrected prior, and not v1 default.
- [ ] Public guidance requires current drift, contestation, and falsifier reports.
- [ ] The contestation distribution of graduating families is monitored as a release gate.
- [ ] Measurement before mutation is re-scoped to reward, training, contestation, product verdicts, and the remedy itself.
- [ ] `.notMeasured` is never zero.
- [ ] Copy honesty / why-line-true-today remains a staging gate and is not misrepresented as a need verifier.
- [ ] The comfortable false positive is explicitly named as residual risk and not claimed solved or fully bounded.
- [ ] The deterministic SELECT fallback remains available after PROPOSE launch.
- [ ] The self-audit includes the standing row: does user protection scale with migrated power, and does the wall cover the relocated risk?

## 19. Changelog / deprecation map

### Plan-4-revised(10).md map

| Source section | Plan-5 disposition | Kept | Changed / superseded |
|---|---|---|---|
| Opening doctrine / law / role map | Amended | Single doctrine, four-clause law, internal role map, capability ≠ authority | Law now allows DiffusionGemma to learn preference-conditioned shapes and allows reward to steer composition; adds contestation auditor, product-verdict channel, and falsifier. |
| §1 Executive decision | Kept and extended | Manufacturing, not retrieval; shape is product | Adds contestation-aware earned acceptance and the loop-aware supplement to the D2 wall. |
| §2 Named failure mode | Kept | Premature semantic compression remains the villain | Adds low-contestation reward collapse as a new loop-level failure mode. |
| §3 Capability is separated from authority | Kept but not sufficient alone | High-FLOP actor composes; Swift admits | Adds standing audit: does user protection scale with migrated power and does D2 cover the relocated risk? |
| §4 Authorship decision | Kept | AUTHOR rejected; SELECT public default; PROPOSE target | Graduation now requires contestation distribution and falsifier gates, not survival/edit lift alone. |
| §5 Pantry membrane | Kept | Decision-sufficient, non-identifying statistics; raw content floor | Contestation is computed Swift-side from calendar pressure and never transmitted raw. |
| §6 Relational Prep Station | Kept | Swift-owned, non-learning, consultable chips | No change; composer learning does not make the prep station a learner. |
| §7 Canonical contracts | Expanded | `RecommendationContextV1`, `SlateCellV0`, `RecommendationSelectionInfillV0`, `RecommendationShapeProposalV0`, `EvidenceReceiptV0`, D2 contracts | Adds `ContestationSignalV0`, `UserProductVerdictSignalV0`, `EarnedAcceptanceRewardSignalV0`, `UserPreferenceEmbeddingV0`, `RewardModel*`, `ContestationDistributionReportV0`, `ComfortableFalsePositiveFalsifierV0`. |
| §8 D2 and admission wall | Kept bit-for-bit in authority | D2 in-process, lookup not reconstruction, `RecommendationVerdictV0` non-Codable | Adds explicit caveat that D2 is not a value-loop auditor. |
| §9 End-to-end flows | Expanded | SELECT, PROPOSE, confirm/write flows | Adds product-verdict flow, contestation measurement, falsifier path. |
| §10 Backstage value-signal layer | Superseded in steering posture | Signals remain Swift-side, lineage-bound, not admission | §10.5 “loop improves in the dark” is relaxed: measured reward may steer composition. Raw survival is demoted; contestation-weighted survival becomes reward input. |
| §11 Swift-owned scoring / measurement | Expanded | Correctness verifier, `PickDiscriminatorV0`, `.notMeasured`-never-zero, measurement before mutation | Adds contestation, product verdicts, and falsifier as measurement-before-mutation requirements. |
| §12 Privacy / copy honesty | Kept | Raw-content floor and copy-honesty gate | Adds no reward / contestation / product-verdict claims in copy. |
| §13 UX invariants | Kept and generalized | Confirm tap, felt safety, sacred calendar | Product verdict channel added as user-directed product audit; rest-only framing deprecated. |
| §14 Migration sequence | Replaced | Shadow-first, owner-gated, SELECT default, deterministic fallback | New M0-M8 sequence includes falsifier-before-fix, contestation instrumentation, `u`, reward guidance, per-family graduation, optional DPO. |
| §15 Test matrix | Expanded | Existing wall, membrane, D2, write, copy, `.notMeasured`, PROPOSE parity tests | Adds contestation, product verdicts, loop coverage, falsifier, not-needed rate, and KL-to-corrected-prior tests. |
| §18 Preserved safety invariants | Kept | Trust wall, D2, tap, membrane, calendar sacredness | Adds “never manufacture demand/contestation” and “raw survival cannot train reward.” |
| §19 Self-audit | Replaced | Self-audit discipline | Adds standing loop-coverage row and per-release re-answer requirement. |

### First plan-5 draft remand map

| Draft claim / structure | Revised disposition | Reason |
|---|---|---|
| Comfortable false positive called “bounded residual.” | Replaced. | It is not bounded by survival/edit/regret terms; those are the predicate it satisfies. |
| “Value is the guardrail on acceptance.” | Reframed. | Non-regret under contestation is the guardrail; value remains unverified. |
| Raw earned acceptance = accepted ∧ survived-to-T ∧ low edit-distance. | Replaced by contestation-weighted earned acceptance. | Survival in uncontested space can measure cost-of-removal. |
| Explicit-useful channel, rare and throttled. | Reframed as product verdict channel. | Availability is unthrottled; solicitation is throttled. Verdict is on the product, not the user. |
| Positive explicit signal as reward term. | Coupled to contestation. | Otherwise reward Goodharts toward bland unobjectionable cards. |
| Population drift monitor as main flattery detector. | Kept but insufficient. | Adds contestation distribution monitor to watch release ↔ prior coupling. |
| γ / KL as bounds on reward over-optimization. | Kept but scoped. | γ is not in the raw-survival prior corruption loop; KL to a corrupted prior is anti-corrective. |
| Two relaxations. | Replaced with three. | Third relaxation: machine now has a stake in yes. |
| Self-audit checked whether the wall was preserved. | Expanded. | New row asks whether the preserved wall still covers relocated risk and whether protection scales with migrated power. |
| Remedy accepted without external kill condition. | Replaced. | Falsifier must be built before the fix is trusted. |

### Readme deprecation map

| Readme statement | Plan-5 disposition |
|---|---|
| Manufacturing, not retrieval | Preserved. |
| Capability separated from authority | Preserved and supplemented with loop coverage. |
| Trust by construction | Preserved. |
| Decision-sufficient membrane | Preserved. |
| Honesty load-bearing | Preserved; why-line truth is not overstated as need verification. |
| Human is the principal | Preserved; product verdict channel makes the user the auditor of the product. |
| “There is no learner today” | Superseded for the composer only. |
| “The single feeling sold is permission to rest” | Superseded by personalization across shape-families. |

### Game-engine map

| Game-engine point | Plan-5 disposition |
|---|---|
| CalAgent as front half of game-agent loop with validator sovereign | Canonized. |
| Earned acceptance reward | Canonized but corrected: contestation-weighted and falsifier-gated. |
| Learn `u` across all recommendation types | Canonized. |
| Reward-guided sampling with bounded γ | Canonized as preferred v1. |
| Diffusion-DPO KL-leashed to Phase-1 prior | Canonized as optional, but leash must be to contestation-corrected prior. |
| Comfortable false positive | Retained and strengthened: not claimed bounded by survival/edit; contestation relocates risk but does not solve value. |
| Explicit-useful visible measurement caveat | Reframed as product-verdict channel; availability unthrottled, solicitation throttled. |

## 20. Deliberately preserved safety invariants

| Preserved invariant | Why it survived untouched in force |
|---|---|
| The authority firewall: the model never authors identity, time, title, evidence hashes, source kind, strength, provenance, fingerprint, verdict, action, reward score, contestation score, or product verdict; Swift hydrates and revalidates live with `support(staged) ⊆ F(x_live)`. | This is the core trust contract. PROPOSE and reward guidance change sampling, not authority. |
| D2 remains the only net-new admission-critical seam, in-process Swift; no second verifier, no admission RPC, no model-authored ontology, no D2 network service. | One exact wall is easier to audit than several soft walls. |
| `RecommendationVerdictV0` remains non-`Codable`. | Verdict cannot be transported by model, bridge, reward model, or carrier. |
| Measurement before mutation. | Now stronger: reward, training, contestation, product verdicts, and the remedy itself require lineage before mutation. |
| `.notMeasured` is never zero. | Missing information cannot become evidence for promotion or suppression. |
| Missing lineage, missing coverage, classifier coupling, missing contestation, missing falsifier, and boundary violations cannot silently promote a feature. | Prevents self-mutating loops from laundering uncertainty into product authority or reward credit. |
| Model-authored semantic graphs remain rejected. | A model-authored edge can launder source strength, identity, or admission facts. The prep station is Swift-owned and non-authoritative instead. |
| The privacy floor on raw content remains. | Raw titles, notes, attendees, exact locations, raw product-verdict text, and raw contestation preimages name a life. |
| Free-text notes never cross the membrane. | Notes are unbounded PII and substring leakage risk; closed flags require a separate owner gate. |
| Copy honesty is part of staging. | A valid time with an unsupported why-line is still a user-visible false claim. |
| Why-line-true-today remains a hard gate. | Reward cannot buy a false permission slip, even though truth alone does not prove need. |
| Server-minted confirm action is required for writes. | Felt safety does not imply consent; the tap is the consent ritual. |
| Swift never touches calendar objects the system did not create. | The calendar is sacred space, not a feed or scratchpad. |
| Contestation is measured only against non-CalAgent-created demand. | The system must not manufacture demand and reward itself for competing with it. |
| Passive survival cannot earn high contestation credit. | Inertia is not revealed value. |
| Product verdicts are product-directed and non-grading. | The user audits the product; the product does not interrogate the user. |
| Positive product verdicts cannot overcome zero contestation. | Prevents Goodhart toward bland unobjectionable cards. |
| P3 / admit-rate parity applies to guided, pinned, or shape-proposed candidates. | Guidance must not leak into authority by changing validation semantics. |
| Deterministic SELECT fallback remains available. | A measured target lane needs a safe floor and rollback path. |
| The model may become more capable without becoming more sovereign. | Capability rise is the product bet; authority rise would break trust. |

## 21. Self-audit

This table must be re-answered for every public guidance release and every shape-family graduation. It is not a one-time documentation checklist.

| Litmus test | Yes / No | Evidence |
|---|---:|---|
| Is there one locatable governing doctrine and one amended four-clause law? | Yes | Opening blocks before the table of contents. |
| Is the internal role map mapped exactly once, with no component described in another's authority terms? | Yes | Opening role map only; technical sections use component names and trust boundaries. |
| Are the three scoped relaxations named? | Yes | §2.2 reward may steer; §2.3 composer may learn; §2.4 machine now has a stake in yes. |
| Does capability rise without authority rising? | Yes | §§3 and 9 preserve D2, `support(staged) ⊆ F(x_live)`, hydration firewall, non-Codable verdict, and confirm tap. |
| Does user protection scale with the migrated power, and does the preserved wall cover the relocated risk? | Standing gate | §3.3 states D2 covers admission but not reward-loop corruption; §§11-13 add contestation, product verdicts, and falsifier. This row must be re-answered for each family and release. |
| Is the wall preserved bit-for-bit? | Yes | §9 states D2 unchanged; §20 preserves wall invariants. |
| Is D2 incorrectly asked to be a value verifier? | No | §9 says D2 is necessary but not a value-loop auditor. |
| Is the value-verifier gap confronted? | Yes | §§4.1, 11.1, and 11.6 state value remains unverified; non-regret under contestation is only a proxy. |
| Is survival in uncontested space demoted from value? | Yes | §§4.1, 11.2, and 11.3 disclose cost-of-removal and zero / low contestation credit. |
| Is contestation first-class? | Yes | `ContestationSignalV0`, `ContestationDistributionReportV0`, migration M1/M6/M7, and tests in §17. |
| Are both contestation brakes present? | Yes | §11.4 defines revealed-reconfirmation and created-event boundary in reverse. |
| Does the product-verdict channel flip who watches whom? | Yes | §11.5 frames verdicts as product-directed; §15.5 defines UX labels. |
| Is product-verdict availability unthrottled while solicitation is throttled? | Yes | §§2.5, 8.11, 10.4, 11.5, 15.5, and M1. |
| Are positive product verdicts coupled to contestation? | Yes | §§8.11, 11.5, and tests in §17. |
| Is the comfortable false positive named and not solved away? | Yes | §11.6 says contestation relocates but does not buy a value verifier. |
| Is there a falsifier outside the optimized reward? | Yes | §11.7 and `ComfortableFalsePositiveFalsifierV0`; M1 requires it before guidance is trusted. |
| Is the falsifier wired to a real kill action? | Yes | `SelectEjectDecisionV0`, M1/M6/M7, and `testHeldOutNotNeededRateWiredToSelectEject`. |
| Does the plan monitor the contestation distribution of graduating families? | Yes | `ContestationDistributionReportV0`, M6/M7, and `testContestationDistributionMustNotCollapseOnGraduation`. |
| Does the plan prevent the KL leash from preserving a corrupted prior? | Yes | §§12.2-12.3 require contestation-corrected Phase-1 prior before KL-leashed DPO. |
| Is DPO treated as optional and riskier than frozen-base guidance? | Yes | §§12.3.1-12.3.2 and M8 mark it as offline, KL-leashed, weight-moving, and not v1 default. |
| Does the plan preserve the membrane? | Yes | §6, §14, and contracts in §8 keep raw identity and raw contestation preimages Swift-only. |
| Does the plan preserve the human principal? | Yes | §§10.3, 15, and §20 preserve confirm tap, no auto-write, undo, and product-directed verdicts. |
| Is current vs proposed implementation status honest? | Yes | Opening implementation-status note marks new learned back half, contestation, and falsifier as proposed until an owner marks milestones complete. |

