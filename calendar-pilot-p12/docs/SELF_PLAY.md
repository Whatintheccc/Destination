# Self-play

Self-play is the optimizer's laboratory. It perturbs the trajectory distribution, but it does not get to grade the policy using the policy's own beliefs.

## Flow

```text
RawCalendarObservation
  -> FrontierService / policy frontier
  -> robust top-k candidate selection
  -> ActionLifecycle through Swift/provider backend
  -> UserSimulator(simulator_version)
  -> adversaries
  -> RewardEvent + SelfPlayEpisode + adversary_finding rows
  -> training reducer / PolicyTuning
```

## Simulator versions

`sim_v1` is the historical stochastic simulator and can use candidate predicted heads. It remains available for regression continuity.

`sim_v2` is the default for new lab batches. It estimates outcomes from seed/profile truth: response windows, notification fatigue, user profile claims, action family, reversibility, social scope, and authority friction. It does **not** read `predicted_acceptance`, `predicted_utility`, `predicted_regret`, `predicted_interruption_cost`, or `predicted_social_risk`.

Every `SelfPlayEpisode` records `simulator_version` and `simulator_seed`.

## Adversaries

| Finding | Meaning |
|---|---|
| `social_conflict` | Candidate leans on other people's calendar reality. |
| `notification_fatigue` | Right action, bad moment or bad dose. |
| `undo_regret` | Auto-write deserves rollback stress. |
| `engagement_over_utility` | Attention is beating schedule quality. |
| `denied_actuation` | Policy asked for authority Swift did not grant. |

## Learning effect

A self-play tuning is useful only when `failure_penalties` are non-empty and frontier diffs show penalized candidates moving down beyond measured variance. Reducers tag simulator-derived rewards as `self_play_simulator` and weight them below human UI feedback.

## P12 simulator update: `sim_v2.1`

`sim_v2.1` keeps the P11 predicted-head ban and replaces psychological seed scalars with behavioral histories plus signal estimators. A fatigue-like scenario is authored as dismissal/ignore history; `interruption_tolerance_v1` estimates a derived signal from that history, and the simulator uses the same estimator path as production.
