# CalendarPilot Architecture

CalendarPilot is an agentic calendar optimizer. It is organized around three components.

## Swift: CalendarPilotKernel

Swift owns calendar reality:

- raw calendar observation ingestion;
- event/entity normalization;
- write authority broker;
- action materialization;
- conflict checks;
- undo handles;
- reward telemetry receipts;
- replay records for offline learning.

The Swift kernel is intentionally deterministic. It should never ask the language model whether a write is valid; it receives typed candidate action programs and accepts or rejects them according to authority tier, reversibility, social scope, and conflicts.

## DiffusionGemma

DiffusionGemma owns the generative policy:

- candidate action generation;
- right-moment prediction;
- reward/value scoring;
- persistent biography update;
- counterfactual evaluation;
- self-play.

The included implementation is a heuristic reference policy. Replace `DiffusionGemmaPolicy.generate_candidates` and `RewardModel.score` with model calls when serving a real model.

## Codex

Codex owns the executive dialogue:

- explain the proposed action;
- ask clarifying questions;
- negotiate autonomy tiers;
- summarize profile updates;
- repair bad actions with undo context.

Codex should be able to express why an action was proposed, what authority tier it needs, and how to undo it.

## Control loop

```text
RawCalendarObservation
  -> BiographyStore.update
  -> DiffusionGemmaPolicy.generate_candidates
  -> RewardModel.score + RightMomentModel.choose
  -> Swift WriteAuthorityBroker.authorize
  -> ActionMaterializer.apply or stage
  -> CodexExecutiveAgent.explain
  -> RewardLogger.observe
  -> ReplayBuffer.append
  -> SelfPlayRunner trains/evaluates next policy
```

## Authority principle

The system is allowed to act, but authority is explicit:

```text
candidate.required_authority_tier <= granted_authority_tier
AND conflicts acceptable
AND reversibility acceptable for tier
AND affected people allowed for tier
```

## Reward decomposition

CalendarPilot does not collapse everything into a single opaque score. It stores separate heads:

- predicted acceptance;
- predicted utility;
- predicted engagement;
- predicted regret;
- predicted interruption cost;
- predicted social risk;
- long-horizon schedule value.

This allows product strategy to tune the objective without hiding the fact that engagement is being optimized.
