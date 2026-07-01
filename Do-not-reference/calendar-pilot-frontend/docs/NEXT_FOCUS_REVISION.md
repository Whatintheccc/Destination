# Next Focus Revision

This revision continues the agentic optimizer track and addresses the requested next focus areas.

## 1. Contract reconciliation

The rich agent fields are now canonical cross-runtime fields, not Python-local annotations:

```text
model_story
counterfactual
control_notes
reward_breakdown
right_moment_score
simulated_outcomes
predicted_long_horizon_value
recommended_execution_time
right_moment_decision
```

They are present in:

```text
Python: calendar_pilot.types.CandidateCalendarAction
JSON:   contracts/candidate_calendar_action.schema.json
Swift:  CalendarContracts.swift / CandidateCalendarAction
```

Swift now uses explicit snake_case `CodingKeys` so Python JSON and Swift Codable agree at the contract boundary. Atomic action enum raw values are also snake_case (`create_focus_block`, `draft_schedule_plan`, etc.). Metadata is restricted to `string:string` across runtimes; Python policy code serializes compound metadata before crossing the boundary.

## 2. Focus-mode ordering bug

`policy.py` no longer checks `right_moment_decision` before right-moment prediction has run. The policy-shaping stage applies the focus-mode interruption penalty by candidate intent:

```python
if observation.device_context.is_focus_mode and candidate.intent != "do_nothing":
    candidate.predicted_interruption_cost += 0.20
```

Right-moment prediction still applies its own contextual timing penalty after reward scoring. The behavioral test compares identical candidate IDs with and without focus mode to prove the score changes before ranking.

## 3. Swift actuation and staging depth

Swift now distinguishes:

```text
materialized_write: create_event, create_focus_block, add_buffer, batch_tasks, move/resize/delete own event
staged_draft:      draft_schedule_plan and clarification-class actions
staged_notification: notify
no_op:             do_nothing
denied:            authority/conflict/social boundary failures
```

`batch_tasks` materializes as a `task_batch` event. `create_focus_block` materializes as a `focus` event. `draft_schedule_plan` is staged rather than silently ignored. `auto_apply_plan` is explicitly denied in kernel-v1 unless a future product policy implements it. People-affecting mutations are denied by the social-actuation boundary even with high general authority, because they need a separate explicit confirmation path.

## 4. Replay and learning loop

Replay now persists more than candidate/receipt pairs:

```text
decision frontier records;
Swift receipts;
reward events;
self-play episodes;
adversary findings;
denial receipts.
```

`SelfPlayRunner(replay=ReplayBuffer())` records all of these during simulation. `scripts/train_offline_policy.py` now consumes replay JSONL and emits an `offline_policy_report.json` with per-intent reward residuals, denial rates, and failure penalties.

## 5. Test quality

New tests cover:

```text
schema parity;
Python contract round-trips;
Swift source contract parity;
Swift snake_case JSON round-trip;
focus-mode scoring;
authority denial receipts;
social actuation boundary;
staging behavior;
self-play replay persistence;
biography provenance and correction flow;
provider boundary stubs.
```

## 6. Provider boundary

Provider interfaces now exist without OAuth implementation:

```text
Python: calendar_pilot.providers.CalendarProviderAdapter
Swift:  CalendarProviderAdapter protocol
Stubs:  Google / Apple / Microsoft adapters
```

These clarify ownership: Python proposes and simulates; Swift/provider adapters own real calendar sync and writes.

## 7. Biography maturation

The biography store now records explicit profile update events with provenance, confidence deltas, correction surfaces, and staleness decay. Codex profile repair now returns an inspectable repair proposal instead of simply echoing a correction.

## 8. Hygiene

`.gitignore` protects Python caches, Swift `.build`, coverage, run outputs, and generated archives. Before packaging, generated `.build` and `__pycache__` directories are removed.
