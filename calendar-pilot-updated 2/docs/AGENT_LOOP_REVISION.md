
# Agent-loop revision: DiffusionGemma + Codex

This patch focuses on the area that felt dry in the first repo: the learning / acting / self-play loop.

The first pass had the right folders, but the code behaved like a demo policy: a few fixed candidates, one scalar score, and explanations that echoed the fields. This revision gives the loop a more product-shaped inner life without adding external dependencies.

## Revised area

```text
src/calendar_pilot/diffusiongemma/
  signals.py       raw-context pressure read
  world_model.py   candidate future sketch + counterfactual
  policy.py        richer action generation and score shaping
  reward.py        visible reward anatomy
  right_moment.py  contextual timing decision
  self_play.py     adversarial episodes and failure modes

src/calendar_pilot/codex/
  agent.py         narrative action explanation + self-play summary

tests/
  test_agent_loop.py
```

## What changed

### 1. Raw-context signal extraction

`extract_signals(...)` turns the calendar into an inspectable pressure sketch:

```text
open slots;
external/internal meeting counts;
flexible user-owned holds;
admin/prep task pressure;
workday density;
notification fatigue;
risk cliffs;
narrative lines.
```

This gives the policy a calendar read rather than a pile of one-off if-statements.

### 2. Candidate futures, not just candidates

`CalendarWorldModel` attaches:

```text
hypothesis;
counterfactual;
upside;
risk cliffs;
control notes.
```

A candidate now says not only “create prep block” but also “what future this creates and what happens if nothing changes.”

### 3. Reward anatomy

`RewardModel.score(...)` now writes `candidate.reward_breakdown`, with heads for:

```text
acceptance;
utility;
engagement;
long horizon;
regret;
interruption;
social risk;
authority cost;
reversibility;
model story.
```

Codex and self-play can now point at the reason the policy won instead of repeating a single scalar.

### 4. Right-moment prediction as actuation policy

`RightMomentModel` now computes a timing score and leaves a reason:

```text
auto_write_then_notify;
notify_now;
silently_draft;
bundle_into_digest;
ask_clarification;
wait;
do_nothing.
```

It uses learned response windows, fatigue, focus mode, authority tier, reversibility, and urgency.

### 5. Self-play that can argue

`SelfPlayRunner` now logs full `SelfPlayEpisode` objects. Adversaries emit named findings:

```text
social_conflict;
notification_fatigue;
undo_regret;
engagement_over_utility;
denied_actuation.
```

The runner chooses from the top policy candidates using an adversarial preview, not just raw expected reward.

### 6. Codex explains the decision, not the data structure

`CodexExecutiveAgent.explain(...)` now returns an explanation with:

```text
chosen intent;
model story;
counterfactual;
actuation path;
reward anatomy;
timing decision;
control notes;
rollback handle.
```

## Demo

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo --self-play 3
```

Expected shape:

```text
I chose `create_prep_block`...
Counterfactual: Without a prep block...
Reward anatomy: +[utility..., acceptance...] / -[authority_cost..., interruption...]
Timing: auto_write_then_notify...
Self-play ran 3 episodes... Failure modes: notification_fatigue:3
```

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Current result after this patch:

```text
10 tests passing
```
