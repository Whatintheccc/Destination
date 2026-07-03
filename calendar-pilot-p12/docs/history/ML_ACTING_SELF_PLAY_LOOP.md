> Historical note: this document is retained as implementation archaeology. The current contract truth lives in `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/LAB.md`, `docs/PROVIDER_BOUNDARY.md`, and `docs/SELF_PLAY.md`.



# Machine Learning, Machine Acting, and Self-Play Loop

This repo is now organized around a closed loop:

```text
raw calendar observation
-> DiffusionGemma candidate frontier
-> Codex tool deliberation
-> Swift staging/commit/denial/undo
-> reward + adversary findings
-> replay
-> offline policy tuning
-> next DiffusionGemma generation
```

## Machine learning

DiffusionGemma currently appears as a deterministic reference policy, but the contract shape is ML-native:

```text
raw-context signals
candidate action programs
world-model counterfactuals
reward heads
right-moment score
self-play failure modes
offline PolicyTuning
```

`PolicyTuning` is the first explicit bridge from replay to future policy behavior. `train_offline_policy.py` now emits:

```json
{
  "intent_reward_bias": {},
  "failure_penalties": {},
  "denied_intents": []
}
```

`DiffusionGemmaPolicy(policy_tuning=...)` consumes that object and changes ranking behavior.

## Machine acting

Machine acting is still owned by Swift. Python can propose, simulate, and request; Swift is the authority boundary.

Acting receipts now distinguish:

```text
materialized_write
staged_draft
staged_notification
denied
reverted
```

Codex can stage packets and request commits. It cannot bypass social-actuation denial, conflict checks, rollback requirements, or provider ownership.

## Self-play

Self-play now feeds replay with:

```text
candidate decisions
Swift receipts
reward events
self-play episodes
adversary findings
Codex tool calls and receipts
```

Adversaries currently probe:

```text
social conflict
notification fatigue
undo regret
engagement-over-utility
Swift authority denial
```

The policy update is intentionally simple but real: replay residuals become intent biases, repeated denials become intent filters, and adversary findings become failure penalties.

## Privacy posture

This branch intentionally deprioritizes privacy as the primary doctrine. Raw titles, attendees, and event details are available to Codex inspection tools and DiffusionGemma-style context modeling in the reference implementation.

The remaining privacy-like boundaries are control-theoretic:

```text
provider tokens stay behind Swift;
Codex cannot directly write providers;
social mutation has an explicit boundary;
profile patches require confirmation;
replay makes acting paths debuggable;
rollback handles are first-class.
```

The point is not to minimize data. It is to make high-authority acting recoverable and inspectable.