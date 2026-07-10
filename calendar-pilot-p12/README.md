

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

P12 instrument and historical compression bootstrap:

```bash
make p12-release
jq -e '.decision == "pass" and .ok == true' runs/p12_release/p12_release_report.json

make cvar-report
make b-migrate
```

The unversioned C-VAR and `B_migrate` targets remain P12 shape/replay checks. They are
not accepted by the P13 promotion gate.

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

Scenario-set v2 has no fixed scenario-count ceiling and binds target requirements only
from a verified pre-wave manifest:

```bash
make architecture-eval-v2-test
make architecture-evals-v2 WAVE=<wave> \
  P13_VERIFY_KEY="$P13_DEV_KEY_DIR/signing-public.pem"
```

The v2 command fails before evidence collection if the signature, expiry,
InstrumentBundle, scope source, or evaluator-derived affectedness is invalid. Required
target IDs become `gate_mode=required` in the report; a required `not_reached` is hold.

The report separates binding preservation evals from target-conformance evals.
`pass`, `fail`, `hold`, and `not_reached` are distinct: `not_reached` never counts as
pass and preservation non-pass results block. The v1 target `binding_trigger` fields are
historical prose, not executable switches; those targets cannot certify a P13 migration.
Scenario-set v2 plus a signed BindingManifest makes target selection executable.
This baseline is deterministic and does not invoke live Codex, live NIM, or mutating
EventKit; it neither completes P13.0 nor begins a vertical migration or earns
compression credit. See
[`../compression-roadmap.md`](../compression-roadmap.md), §4.6 and §8.5.

Each run writes a fresh non-overwriting report/artifact directory under
`runs/architecture_evals/<run-id>/` and refreshes
`runs/architecture_evals/architecture_eval_report.json` as the latest pointer. Reports
record committed and dirty-worktree identity plus hashes for the runner, adapter,
predicates, scenario set, and schema. The gate validates both the Draft 2020-12 schema
and derived decisions/artifact hashes before it can return success.

The legacy v2 fields `report_paths.immutable` and console `immutable_out` mean only
that the runner chose a fresh per-run destination and refused overwrite at creation
time. They prove no write protection, retention, or post-run tamper resistance. Renaming
them requires a future versioned report-contract ruler wave.

P13 ruler identity and pre-wave binding:

```bash
make p13-ruler-test
make p13-loc-report

# Owner-controlled wave key.
P13_WAVE_KEY_DIR="$HOME/.config/calendar-pilot/p13-wave"
mkdir -p "$P13_WAVE_KEY_DIR"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 \
  -out "$P13_WAVE_KEY_DIR/signing-private.pem"
openssl pkey -in "$P13_WAVE_KEY_DIR/signing-private.pem" -pubout \
  -out "$P13_WAVE_KEY_DIR/signing-public.pem"
chmod 600 "$P13_WAVE_KEY_DIR/signing-private.pem"

make p13-instrument \
  P13_VERIFY_KEY="$P13_WAVE_KEY_DIR/signing-public.pem"
```

Before candidate edits, commit a scope file at
`experiments/waves/<wave>.scope.json` using the versioned template, then bind it:

```bash
make wave-bind WAVE=<wave> CHANGE_CLASS=<ruler|migration|compression|learning> \
  P13_SIGNING_KEY="$P13_WAVE_KEY_DIR/signing-private.pem" \
  P13_VERIFY_KEY="$P13_WAVE_KEY_DIR/signing-public.pem"

make binding-manifest-verify WAVE=<wave> \
  P13_VERIFY_KEY="$P13_WAVE_KEY_DIR/signing-public.pem"

make wave-harness WAVE=<wave> \
  P13_VERIFY_KEY="$P13_WAVE_KEY_DIR/signing-public.pem"

jq -e '
  .decision == "pass" and .ok == true and
  ([.gates[] | select(. != "pass")] | length) == 0
' runs/p13_wave_gate_report.json
```

Binding verifies signature, expiry, InstrumentBundle hashes, scope-source identity,
and locally verifier-derived affectedness from committed, staged, unstaged, and untracked paths.
Any undeclared path/category or changed instrument artifact fails closed.

The local fail-closed wave harness verifies the manifest, runs scenario-set v2, compares two
separately materialized C-VAR frontier artifacts, invokes the manifest's separately
named old/new `B_migrate` producer commands, runs P12 release, verifies content-addressed
reward-occurrence identity, declared source/reference shape, and direct simulator-credit
screening, validates signed live-leg/root-list entries and expiry, writes
`experiment_record.v2`, and then reads every JSON decision. This screen does not claim
authenticated ingress or transitive simulator noninterference; those remain target debt.
Both `hold` and `fail` return a nonzero shell status. Behavior-bearing waves must pass a
clean pre-wave C-VAR artifact with `CVAR_BEFORE=<path>`; the harness will not regenerate
their baseline after candidate work.

Local key paths are caller inputs and local reports are ignored artifacts. The checked-in
root workflow runs the deterministic Python ruler with an explicit stub kernel on pull
requests and protected `main`, generates a wave key inside the job, and uploads a fixed
checksummed evidence bundle for 90 days. [Run 29076097058](https://github.com/Whatintheccc/Destination/actions/runs/29076097058)
is the exact-main hosted replay for implementation commit
`def14738de5befff611b14c8371b29a47677b59c`; its retained evidence and limitations are
recorded in [`../compression-roadmap.md`](../compression-roadmap.md), §8.5. Swift and
app-bundled EventKit remain separate access points and are not implied by this Linux
Python replay. Effect-capable waves pass only when the owner-signed manifest, composite
wave, and every affected app/live leg pass together.

The P13.1 no-effect vertical has one focused root access point:

```bash
make p13-no-effect-test
```

It proves the `create_prep_block` ProductCore path is deterministic, cited, independently
comparable to the incumbent preview, and structurally unable to construct tickets,
`EffectAttempt`s, dispatches, or provider mutations. It does not cut over the frontend or
authorize an effect.

The P13.2 cited read-side cutover has one focused root access point:

```bash
make p13-cited-read-side-test
```

It pins the exact candidate-card field manifest, proves the cited card is reconstructed
from persisted ProductCore Journal rows across restart, preserves every incumbent visible
field, and keeps simulate/stage/commit controls routed to the incumbent Swift-owned effect
path. The `incumbent` compatibility selector is the tested rollback path; this target does
not authorize a ticket, dispatch, provider mutation, or P13.3 handoff.

The P13.3 owner-controlled deterministic sandbox has one focused access point:

```bash
make p13-deterministic-sandbox-test
```

It exercises the frozen ticket/Gateway evaluator over `create_prep_block`, including
exact apply and compensation binding, atomic one-use claim/outbox, duplicate delivery,
crash/restart, unknown-outcome reconciliation, revocation races, and compensation
conflict. Its adapter has no credentials or external-I/O capability, the selector
defaults to the incumbent outside an explicit sandbox invocation, and every artifact
states `authorizes_production: false`. It cannot authorize EventKit, deployment,
retirement, or promotion.

The closed P13.4 EventKit sandbox certificate has one focused deterministic access point:

```bash
make p13-eventkit-sandbox-test
```

Its live access point remains explicit and app-bundled:

```bash
CALENDAR_PILOT_EVENTKIT_BRIDGE="$PWD/dist/CalendarPilot.app/Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge" \
CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID=<exact-calendar-id> \
CALENDAR_PILOT_P13_EVENTKIT_SANDBOX=1 \
CALENDAR_PILOT_EVENTKIT_MUTATION=1 \
CALENDAR_PILOT_REQUIRE_EVENTKIT=1 \
make live-eventkit-e2e
```

The recorded exact-candidate run used full EventKit access and calendar
`09B50C6A-826E-4030-9908-D25DC900AC59`; one probe reconciled from
`applying_unknown` to `verified`, a separately ticketed compensation verified, and
cleanup proved the calendar empty. The selector still defaults to the incumbent and
every report states `authorizes_production: false`. P13.5 is the separate retirement
wave; P13.4 did not retire, deploy, promote, or transfer production ownership.

The first P13.5 retirement has one focused access point:

```bash
make p13-deterministic-retirement-test
```

For `create_prep_block × deterministic_sandbox`, the normal
`CodexToolRuntime.REQUEST_COMMIT` and `REQUEST_UNDO` routes now use EffectKernel
Gate/Gateway. The focused certificate proves one effect owner, zero legacy mutation
calls, a separately ticketed compensation, restart reconciliation without redispatch,
and an owner-frozen rollback selector. This backend remains non-production. EventKit,
all production modes, and every other action/backend pair remain incumbent-owned until
their own signed retirement waves pass.

The separately bound managed EventKit retirement has one focused deterministic access
point:

```bash
make p13-eventkit-retirement-test
```

Its ownership unit is exactly
`create_prep_block × apple_eventkit × binding_id@epoch`. An opaque setup binding captures
the exact EventKit store/calendar/source fingerprint and canonical app/bridge identities;
title is a drift tripwire, never a locator. Any binding reference or expanded action that
targets the managed calendar is classified as managed. Missing metadata, mixed targets,
permission loss, identity drift, or corrupt/missing durable state holds inside
EffectKernel without incumbent fallback. Every normal commit and undo requires exact
person-confirmation provenance, and historical undo routes to its creating receipt and
epoch.

The affected live certificate remains explicit and app-bundled:

```bash
CALENDAR_PILOT_EVENTKIT_BRIDGE="$PWD/dist/CalendarPilot.app/Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge" \
CALENDAR_PILOT_MANAGED_EVENTKIT_CALENDAR_ID=<exact-calendar-id> \
CALENDAR_PILOT_MANAGED_EVENTKIT_SETUP_CONFIRM=1 \
CALENDAR_PILOT_P13_EVENTKIT_RETIREMENT=1 \
CALENDAR_PILOT_EVENTKIT_MUTATION=1 \
CALENDAR_PILOT_REQUIRE_EVENTKIT=1 \
make live-eventkit-e2e
```

The live run creates a new binding lineage, calls the normal `REQUEST_COMMIT` path,
restarts and reconciles an injected post-dispatch unknown without redispatch, calls the
normal receipt-owned `REQUEST_UNDO` path, and verifies exact-calendar absence. This wave
remains `authorizes_production: false`; every other EventKit scope and production mode
stays incumbent-owned.

`make lab-promote` has one P13.6 aperture: `RECORD=...` may apply a content-addressed,
promoter-signed `bootstrap` or `rollback` record whose previous-`CURRENT` precondition,
instrument epoch, manifest/evidence hashes, payload hash, and pinned signer all verify.
Direct, automatic, `--decide promote`, unsigned override, and positive-learning calls
still return blocking hold before writes. The repository `CURRENT` remains on its legacy
empty-baseline semantics through a signed `current_policy_pointer.v1`; it no longer uses
the legacy direct tuning pointer.

The control-plane access sequence is explicit:

```bash
make p13-learning-ruler-test

make learning-propose \
  SEARCH=<sanitized-search.jsonl> HOLDOUT=<sealed-holdout.jsonl> \
  FORWARD_SHADOW=<sealed-forward-shadow.jsonl> \
  POLICY_PARAMETERS=<declarative-policy.json> PAYLOAD_ID=<id> \
  PROPOSAL_DIR=<repo-local-proposal-dir> P13_MANIFEST=<bound-manifest>

make learning-evaluate \
  PAYLOAD=<policy-payload.json> OPTIMIZER_REPORT=<optimizer-report.json> \
  PARTITIONS=<partition-manifest.json> P13_MANIFEST=<bound-manifest> \
  P13_INSTRUMENT=<instrument-bundle.json> \
  P13_VERIFY_KEY=<pinned-public.pem> P13_SIGNING_KEY=<external-private.pem> \
  TRANSITION=bootstrap PROMOTER_OUT=<repo-local-promoter-dir>

make lab-promote RECORD=<promoter-dir/promotion_record.json>
```

`learning-propose` is macOS-only and fails closed if `sandbox-exec` is unavailable or
cannot apply its deny-by-default profile. The optimizer may read sanitized search and
write its proposal directory; sealed holdout/forward-shadow reads and evaluator,
manifest, `CURRENT`, and effect-TCB write opens must return `EPERM`/`EACCES`. A normal
positive-learning `TRANSITION=promote` is intentionally still hold until the improvement
statistics contract and real partition evidence are bound.

`make test` is Python + Swift only. `make ml-ladder` is deterministic ML smoke
only. `make p12-release` does not run browser, app-bundle, Swift IPC, or live
backend legs. The legacy C-VAR and `B_migrate` targets are bootstrap checks; only the
manifest-bound `wave-harness` is a P13 wave decision.

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
