# CalendarPilot Architecture

CalendarPilot is now organized as a controlled RL system over typed calendar actions. The central product substrate is the **trajectory**, not the model, UI, or provider adapter.

```text
TraceEvent + ActionEnvelope + ReplayRecord + Scorecard
```

A valid trajectory starts with a raw observation, routes through a typed frontier, moves through Codex tool calls, reaches Swift/provider actuation only through an ActionEnvelope, and returns evidence to replay. Every learning update must cite that trajectory and compare against the incumbent policy, not merely against an empty baseline.

## Runtime split

| Layer | Owns | Must not own |
|---|---|---|
| DiffusionGemma / NIM | Typed candidate futures, reward heads, right-moment scoring, frontier provenance | Calendar authority, provider writes, grants |
| Codex | Typed tool planning, comparison, explanation, repair, commit requests | Provider tokens, authority minting, direct mutation |
| Swift kernel | Reality, grants, validation, write admission, rollback ledger, audit receipts | Language-level deliberation or learned reward optimization |
| Provider boundary | Readback truth, preview/conflict truth, commit, verify, rollback | Policy choice or autonomy promotion |
| Replay/Lab | Trajectory evidence, reductions, scorecards, promotion records | Hidden state or unverifiable demo metrics |
| Frontend | `view_state.v2` and trace rendering | Deriving new hidden truth outside replay |

## Control loop

```text
RawCalendarObservation
  -> FrontierService.generate
  -> CodexToolPlanner / CodexToolRuntime
  -> ActionLifecycle.prepare/simulate/stage/commit/verify/reward/undo
  -> SwiftKernel + ProviderBoundary
  -> ReplayBuffer rows with record_schema_version
  -> train_offline_policy.py / run_frontier_diff.py / promote_policy.py
  -> PolicyTuning against CURRENT
```

## Trajectory objects

`ActionEnvelope` is the actuation trace for one candidate/action packet. It carries `envelope_version`, trace id, candidate id, observation fingerprint, authority, provider transaction state, lifecycle transitions, reward references, and replay record ids.

`ReplayRecord` is the durable row format. New rows append with `record_schema_version: "r1"`; absent versions are legacy `r0`. The replay journal accepts older rows, reports unknown skipped versions to reducers, and keeps denial, reward, adversary finding, model rejection, and envelope transition rows through compaction.

`Scorecard` is not embedded in replay. Large derived artifacts are referenced with `artifact_ref` rows carrying type, path, and SHA-256.

## Closed vocabularies

Canonical intents live in `calendar_pilot.environment.taxonomy`. Temporal scoring remains `RightMomentDecision`; actuation-facing timing plans remain `RightMomentTemporalController` modes. Provider transaction states live in `docs/PROVIDER_BOUNDARY.md` and `contracts/action_envelope.schema.json`.

## Authority principle

Codex carries a Swift-issued `AuthorityGrant` id. Swift resolves the id from its registry and validates max tier, scope, expiry, confirmation provenance, reversibility, conflict truth, social scope, and rollback requirements. The planner also consults `configs/autonomy_matrix.json` before requesting a commit; this is a controller-side bound, not a replacement for Swift validation.

## Evaluation principle

Promotion is conservative policy improvement:

```text
candidate policy must beat CURRENT on seeded marginal frontier diffs,
respect hard invariants,
avoid engagement gaming / social creep / regret regression,
and include replay-backed bias evidence.
```

The simulator is explicitly versioned. `sim_v1` is retained for continuity; `sim_v2` must not grade a candidate using that candidate's own predicted heads.

## P12 signal layer

P12 inserts a governed human-signal layer between raw replay and policy learning.

```text
ActionStream   -> reward truth and estimator measurements
WorldStream    -> provider/calendar state for generation and ranking
Biography      -> user-owned prior, never reward truth
DerivedSignals -> versioned, evidence-cited estimates consumed by ranking/timing
```

Codex may propose evidence-cited `SemanticSignal` labels; the label registry controls activation. Swift/authority paths remain independent: labels can shape ranking and timing, but never authority tier, scope, or grant issuance.
