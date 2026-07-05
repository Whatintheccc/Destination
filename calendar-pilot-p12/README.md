

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

## Access Points

Run these from repo root unless noted. The root `Makefile` delegates into the
active framework tree.

```bash
make py-test
make swift-test
make check-invariants
make evidence-bundle
make test
```

Browser and app dogfood:

```bash
make browser-e2e
make mac-app-build
make dogfood-release
```

Live and learning-loop dogfood:

```bash
make live-codex-e2e
make live-diffusiongemma-e2e
make live-eventkit-e2e
make replay-offline-tuning-loop
```

Closed-loop ML dogfood:

```bash
make ml-ladder
make frontier-diff
make scorecard
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
- self-play adversaries search for high-regret and low-interruption-tolerance policies;
- social actuation is gated separately from reversible user-owned writes;
- staged-vs-materialized receipts make non-write actions explicit;
- contract tests keep Python dataclasses, JSON schemas, and Swift Codable mirrors aligned.

## Current architecture docs

Start with `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/LAB.md`, `docs/PROVIDER_BOUNDARY.md`, and `docs/SELF_PLAY.md`. Prior pass notes live under `docs/history/`.

- `docs/P11_IMPLEMENTATION_SUMMARY.md` records the implemented P11 slice and validation commands.

## P12 signal-plane access points

P12 adds governed signal streams and evidence-cited human signals:

```bash
make p12-signals
make p12-measurement
make p12-calibration
make p12-provider-capabilities
make p12-release
```

Core P12 docs:

- `p12-direction.md`
- `docs/P12_TEST_FRAMEWORK.md`
- `docs/SIGNAL_STREAMS.md`
- `docs/P12_IMPLEMENTATION_SUMMARY.md`

P12 separates `ActionStream`, `WorldStream`, `BiographyStream`, derived semantic signals, and system rows. Reward reduction consumes ActionStream rows only; semantic labels can affect ranking/timing but never authority tiers, scopes, or grants.
