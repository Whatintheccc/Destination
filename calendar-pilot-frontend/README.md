# CalendarPilot

Agentic calendar optimizer built from first principles around three components:

- **Swift / CalendarPilotKernel**: raw calendar kernel, write authority broker, action materializer, undo ledger, reward telemetry.
- **DiffusionGemma / Python policy layer**: raw-context modeling, persistent user biography, candidate action generation, right-moment prediction, reward scoring, and self-play.
- **Codex / Python executive layer**: goal dialogue, explanations, profile repair, clarification, and user-facing orchestration.

This repo intentionally implements the **agentic optimizer inversion** rather than the witness architecture. It allows raw-context modeling, persistent biography, proactive recommendations, calendar write authority, right-moment prediction, reward-driven recommendation, and self-play.

## What is in this repo

```text
calendar-pilot/
  packages/CalendarPilotKernel/     Swift package: calendar authority + actuation/staging kernel
  src/calendar_pilot/               Python package: DiffusionGemma + Codex + simulator
  src/calendar_pilot/providers/     Provider adapter interfaces for Google/Apple/Microsoft
  contracts/                        Canonical snake_case JSON contracts shared with Swift/Python
  tests/                            Python unit tests
  examples/                         Demo scripts and sample scenarios
  data/                             Sample calendar/profile fixtures
  docs/                             Architecture, API, self-play, and revision notes
  configs/                          Reward and autonomy config
```

## Quickstart

```bash
cd calendar-pilot
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m calendar_pilot.app demo --observation data/sample_calendar.json --replay-out runs/replay.jsonl
PYTHONPATH=src python3 scripts/train_offline_policy.py --replay runs/replay.jsonl --out runs/offline_policy_report.json
swift test --package-path packages/CalendarPilotKernel
swift run --package-path packages/CalendarPilotKernel CalendarPilotDemo
```

The demo performs this loop and can write replay JSONL for offline policy reduction:

```text
raw calendar observation
→ biography update
→ candidate action generation
→ reward/right-moment scoring
→ authority check
→ Swift-style materialization receipt
→ Codex explanation
→ synthetic reward event
```

## Architecture stance

CalendarPilot optimizes over candidate calendar futures:

```text
state S_t = raw calendar graph
          + event/entity graph
          + persistent biography
          + interaction history
          + notification/action/reward history
          + current context signals
          + future schedule forecast
```

The policy loop is:

```text
observe → model → imagine → act → learn
```

Swift acts as the deterministic kernel. DiffusionGemma models and proposes. Codex explains and negotiates.

## Autonomy tiers

| Tier | Name | Behavior |
|---:|---|---|
| 0 | Observe | Read state and build biography. |
| 1 | Recommend | Suggest actions only. |
| 2 | Draft | Stage changes for confirmation. |
| 3 | Auto-write reversible | Create/move low-risk user-owned blocks with undo. |
| 4 | Auto-write scoped | Act inside declared scopes. |
| 5 | Social actuation | RSVP/decline/negotiate/move meetings involving others. |
| 6 | Full optimizer | Broad delegated management. |

## Safety/control posture

Privacy is not the primary product doctrine here. The repo treats data access as an engineering/control surface:

- authority tiers bound blast radius;
- write receipts and undo handles make action recoverable;
- reward is decomposed into utility, acceptance, engagement, regret, interruption, and social risk;
- self-play adversaries search for high-regret and notification-fatigue policies;
- social actuation is gated separately from reversible user-owned writes;
- staged-vs-materialized receipts make non-write actions explicit;
- contract tests keep Python dataclasses, JSON schemas, and Swift Codable mirrors aligned.

## Status

This is a runnable reference implementation skeleton. It has working contracts, heuristics, self-play, tests, and a Swift kernel. It does **not** include production calendar provider OAuth, provider sync, real ML model serving, or external API credentials.


## Latest revision

See `docs/NEXT_FOCUS_REVISION.md` for the contract reconciliation, focus-mode policy bug fix, Swift actuation/staging depth, replay/training loop, provider boundary, biography maturation, and hygiene changes.


## Latest revision: Codex as tool-using executive

The current repo focuses on machine learning, machine acting, and self-play. The major change is that Codex is no longer just an explainer. It now has a bounded tool runtime:

```text
DiffusionGemma learns and proposes candidate futures.
Codex inspects, simulates, compares, stages, repairs, and requests.
Swift validates, writes, syncs, rolls back, denies, and audits.
```

New entry points:

```bash
PYTHONPATH=src python3 -m calendar_pilot.app demo \
  --observation data/sample_calendar.json \
  --codex-tools \
  --self-play 3 \
  --replay-out runs/replay.jsonl

PYTHONPATH=src python3 scripts/train_offline_policy.py \
  --replay runs/replay.jsonl \
  --out runs/offline_policy_report.json \
  --tuning-out runs/policy_tuning.json
```

Read `docs/CODEX_TOOL_EXECUTIVE.md` and `docs/ML_ACTING_SELF_PLAY_LOOP.md` for the new architecture.
