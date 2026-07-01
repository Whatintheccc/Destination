# Codex Tool Executive Revision

This revision makes Codex a bounded tool-using executive rather than an explanation-only layer.

The operating split is now:

```text
DiffusionGemma learns, imagines, predicts, proposes, and self-plays.
Codex inspects, deliberates, compares, stages, asks, repairs, and requests.
Swift validates, writes, syncs, rolls back, denies, and audits.
```

Codex does not get provider tokens and does not directly mutate Google, Apple, or Microsoft calendars. It operates the app through typed tool calls and receipts.

As of the authority-grant pass, Codex also does not get to self-assign authority tiers. Swift issues `AuthorityGrant` objects with max tier, scope, expiry, and confirmation provenance. Codex carries those grants through tool calls; Swift validates them again for stage, commit, and undo.

## New Python modules

```text
src/calendar_pilot/codex/tools.py
  CodexToolRuntime
  tools for inspect/generate/simulate/compare/stage/commit/undo/replay/profile/autonomy/self-play

src/calendar_pilot/codex/planner.py
  CodexToolPlanner
  deterministic executive plan: inspect -> frontier -> compare -> simulate -> stage/commit
```

## New canonical contracts

```text
CodexToolCall
CodexToolReceipt
AuthorityGrant
CodexAutonomyScopeProposal
PolicyTuning
```

The JSON schemas live in:

```text
contracts/codex_tool_call.schema.json
contracts/codex_tool_receipt.schema.json
```

Swift mirrors the tool boundary in:

```text
packages/CalendarPilotKernel/Sources/CalendarPilotKernel/CodexToolContracts.swift
packages/CalendarPilotKernel/Sources/CalendarPilotKernel/CodexToolBridge.swift
```

## Tool categories

Read-only / inspection:

```text
inspect_week
inspect_event
inspect_open_slots
inspect_authority_scope
inspect_profile_claims
query_replay_trace
```

Learning / imagination:

```text
generate_candidate_frontier
simulate_action_program
compare_candidates
run_self_play_probe
```

Acting through Swift:

```text
stage_action_packet
request_commit
request_undo
explain_swift_denial
```

Profile and authority repair:

```text
propose_profile_patch
apply_profile_patch
propose_autonomy_scope
```

## Why this matters

The earlier repo had strong DiffusionGemma and Swift roles, but Codex mostly narrated them. That created a dead zone between machine learning and machine acting. The tool executive layer makes Codex responsible for the transition from "this seems valuable" to "this is a legitimate app operation under current authority."

## Machine-learning vs machine-acting boundary

DiffusionGemma is allowed to learn hidden regularities and generate candidate futures. It should not be the unchecked tool user because its policy is shaped by reward.

Swift is allowed to change calendar reality. It should not be the language-level deliberator because its job is deterministic validation and rollback.

Codex sits between them. It chooses app operations and presents receipts. It can request commits, but Swift can deny them.

## Replay

Every Codex tool call and receipt is persisted into replay:

```text
codex_tool_call
codex_tool_receipt
```

This means offline learning can now see not only the winning candidate and reward, but the deliberative path: what Codex inspected, which candidates it compared, whether it simulated first, whether Swift staged or denied, and which profile/authority repairs were proposed.
