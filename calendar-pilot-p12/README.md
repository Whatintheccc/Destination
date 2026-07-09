

# CalendarPilot

Agentic calendar optimizer built from first principles around three components:

- **Swift / CalendarPilotKernel**: raw calendar kernel, write authority broker, action materializer, undo ledger, reward telemetry.
- **DiffusionGemma / Python policy layer**: raw-context modeling, persistent user biography, candidate action generation, right-moment prediction, reward scoring, and self-play.
- **Codex / Python executive layer**: goal dialogue, explanations, profile repair, clarification, and user-facing orchestration.

This repo intentionally implements the **agentic optimizer inversion** rather than the witness architecture. It allows raw-context modeling, persistent biography, proactive recommendations, calendar write authority, right-moment prediction, reward-driven recommendation, and self-play.

## What is in this repo

```text
calendar-pilot-p12/
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
cd calendar-pilot-p12
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m calendar_pilot.app demo --observation data/sample_calendar.json --replay-out runs/replay.jsonl
PYTHONPATH=src python3 scripts/train_offline_policy.py --replay runs/replay.jsonl --out runs/offline_policy_report.json
swift test --package-path packages/CalendarPilotKernel
swift run --package-path packages/CalendarPilotKernel CalendarPilotDemo
```

## Access Points

Run these from this active app root (`Destination/calendar-pilot-p12`) or through
the repaired workspace-level `Destination/Makefile`, which delegates to this subtree.
The canonical P13-P17 gate selection, run order,
evidence bundle, and live-app procedure are in
[`../compression-roadmap.md`](../compression-roadmap.md), §4.4–§4.9.

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

P12 instrument and compression bootstrap:

```bash
make p12-release
jq -e '.decision == "pass" and .ok == true' runs/p12_release/p12_release_report.json

make cvar-report
make b-migrate
make wave-harness
```

Deterministic architecture-eval baseline:

```bash
python3 -m pip install -e '.[evals]'  # once per development environment
make architecture-eval-test
make architecture-evals
jq -e '
  .decision == "pass" and
  .rails.preservation.decision == "pass" and
  .rails.preservation.scenario_count == 11
' runs/architecture_evals/architecture_eval_report.json
```

The report separates binding preservation evals from target-conformance evals.
`pass`, `fail`, `hold`, and `not_reached` are distinct: `not_reached` never counts as
pass and preservation non-pass results block. The v1 target `binding_trigger` fields are
historical prose, not executable switches; those targets cannot certify a P13 migration.
Scenario-set v2 plus a signed BindingManifest will make target selection executable.
This baseline is deterministic and does not invoke live Codex, live NIM, or mutating
EventKit; it neither completes P13.0 nor begins a vertical migration or earns
compression credit. See
[`../compression-roadmap.md`](../compression-roadmap.md), §4.6 and §8.5.

Each run writes an immutable report/artifact directory under
`runs/architecture_evals/<run-id>/` and refreshes
`runs/architecture_evals/architecture_eval_report.json` as the latest pointer. Reports
record committed and dirty-worktree identity plus hashes for the runner, adapter,
predicates, scenario set, and schema. The gate validates both the Draft 2020-12 schema
and derived decisions/artifact hashes before it can return success.

P13 ruler identity and pre-wave binding:

```bash
make p13-ruler-test
make p13-loc-report

# Generate this operator-owned keypair outside the repository once.
P13_KEY_DIR="$HOME/.config/calendar-pilot/p13-ruler"
mkdir -p "$P13_KEY_DIR"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 \
  -out "$P13_KEY_DIR/signing-private.pem"
openssl pkey -in "$P13_KEY_DIR/signing-private.pem" -pubout \
  -out "$P13_KEY_DIR/signing-public.pem"
chmod 600 "$P13_KEY_DIR/signing-private.pem"

make p13-instrument \
  P13_VERIFY_KEY="$P13_KEY_DIR/signing-public.pem"
```

Before candidate edits, commit a scope file at
`experiments/waves/<wave>.scope.json` using the versioned template, then bind it:

```bash
make wave-bind WAVE=<wave> CHANGE_CLASS=<ruler|migration|compression|learning> \
  P13_SIGNING_KEY="$P13_KEY_DIR/signing-private.pem" \
  P13_VERIFY_KEY="$P13_KEY_DIR/signing-public.pem"

make binding-manifest-verify WAVE=<wave> \
  P13_VERIFY_KEY="$P13_KEY_DIR/signing-public.pem"
```

Binding verifies signature, expiry, InstrumentBundle hashes, scope-source identity,
and evaluator-derived affectedness from committed, staged, unstaged, and untracked paths.
Any undeclared path/category or changed instrument artifact fails closed.

`make test` is Python + Swift only. `make ml-ladder` is deterministic ML smoke
only. `make p12-release` does not run browser, app-bundle, Swift IPC, or live
backend legs. The C-VAR/`B_migrate`/wave targets are bootstrap checks until the
P13.0 requirements in the compression roadmap are complete.

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

- `../P12-RECORD.md` is the frozen P12 evidence record.
- `../compression-roadmap.md` is the living P13-P17 architecture and validation control document.

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

- `docs/SIGNAL_STREAMS.md`
- `../P12-RECORD.md`
- `../compression-roadmap.md`

P12 separates `ActionStream`, `WorldStream`, `BiographyStream`, derived semantic signals, and system rows. Reward reduction consumes ActionStream rows only; semantic labels can affect ranking/timing but never authority tiers, scopes, or grants.
