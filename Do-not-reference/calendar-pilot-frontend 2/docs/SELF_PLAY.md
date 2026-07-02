# Self-play

The self-play loop is now the main pressure-test surface for the agentic optimizer.

The runner does not merely sample a reward. It generates the policy frontier, previews adversarial penalties, chooses a robust candidate, simulates a user response, and records the failure modes that would otherwise be hidden inside a scalar.

## Flow

```text
raw calendar observation
  -> DiffusionGemmaPolicy.generate_candidates
  -> CalendarWorldModel attaches counterfactual sketches
  -> RewardModel attaches reward anatomy
  -> RightMomentModel chooses act/notify/draft/wait timing
  -> SelfPlayRunner adversarially previews the top-k frontier
  -> SwiftKernelStub authorizes/materializes
  -> UserSimulator responds
  -> adversaries emit named findings
  -> SelfPlayEpisode recorded
  -> ReplayBuffer persists frontier, receipt, reward, episode, and adversary findings
```

## Adversaries

| Adversary | Failure mode | What it catches |
|---|---|---|
| `ConflictAdversary` | `social_conflict` | Candidate leans too hard on other people's calendar reality. |
| `FatigueAdversary` | `notification_fatigue` | Right action, bad dose or bad moment. |
| `RegretAdversary` | `undo_regret` | Auto-write candidate carries enough regret probability to stress rollback. |
| `EngagementAdversary` | `engagement_over_utility` | Engagement is beating utility. |
| Swift denial | `denied_actuation` | Policy asked for authority Swift did not grant. |

## Metrics

`SelfPlayMetrics` records:

```text
episode count;
accept/reject/undo/ignore counts;
average reward;
adversarial delta;
failure modes;
chosen intents;
episode log.
```

Codex can summarize the run:

```python
from calendar_pilot.codex import CodexExecutiveAgent
summary = CodexExecutiveAgent().summarize_self_play(metrics)
```

## Design note

The product requested here is explicitly the inversion of the witness architecture: it learns, acts, predicts right moments, writes under authority, and optimizes reward. The self-play loop is therefore not a witness-safety controller. It is the optimizer's laboratory: it discovers when apparently useful autonomy becomes interruption, regret, social conflict, or engagement gaming.


## Replay and training

Self-play can now be wired to a replay buffer:

```python
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.diffusiongemma import SelfPlayRunner

replay = ReplayBuffer()
metrics = SelfPlayRunner(replay=replay).run(observation, biography, episodes=20)
replay.save_jsonl("runs/replay.jsonl")
```

Then reduce the replay into a policy report:

```bash
PYTHONPATH=src python3 scripts/train_offline_policy.py --replay runs/replay.jsonl --out runs/offline_policy_report.json
```

The report aggregates observed reward residuals, denial rates, and failure penalties by intent. It is deliberately small, but it is no longer a placeholder: it consumes the records that self-play emits.
