# CalendarPilot P13 Dogfood Operating Document

Status: canonical product-dogfood runbook

Architecture authority: [compression-roadmap.md](compression-roadmap.md)

Ground-zero protected build: `a460991805a0f0388a184e93c9a8e951b1cb5467`

Current product verdict: **the E2E machinery runs; the core recommendation experience is not yet MVP-ready**

Last updated: 2026-07-10

This document answers one question: can CalendarPilot work as a useful rough-draft
product for its user? It does not replace the architecture ruler, release gates, or
learning-promotion protocol. It gives dogfood one mission, one vocabulary, one sequence,
and one append-only operating record.

---

## 1. Mission And Core Thesis

CalendarPilot exists to improve the shape of a person's time.

It should understand the person's actual calendar and evolving preferences, imagine
better calendar futures, negotiate a concrete choice in ordinary language, make only the
change the person authorizes, verify what actually happened, undo it safely when asked,
and learn from the real outcome.

The product loop is:

```text
real calendar state
-> cited understanding
-> competing candidate futures
-> one concrete, useful recommendation
-> explicit and revocable authority
-> verified effect or visible hold
-> verified undo when requested
-> human outcome and correction
-> a better incumbent
```

The **trajectory is the product substrate**. Chat, Codex, DiffusionGemma, Swift,
EventKit, the UI, reward scores, and evals are participants in or views over that
trajectory. None is the product by itself.

The role split exists to preserve that thesis:

- DiffusionGemma or another Frontier respondent imagines candidate futures. It has no
  calendar authority.
- Codex converses, inspects, compares, clarifies, explains, and requests typed app
  operations. It has no provider credentials and cannot grant itself authority.
- The Journal and pure Reducer preserve the causal experience and derive cited views.
- The Authority Gate admits only an exact, expiring, revocable action under trusted
  user and provider preconditions.
- The Effect Gateway is the one truthful path to provider reality. It claims, applies,
  verifies or reconciles, and emits receipts. Compensation is separately authorized
  against fresh state.
- Human outcomes decide whether the system helped. Simulator scores may search or veto;
  they cannot manufacture positive human reward.

The humane contract is non-negotiable:

```text
believe only what can be cited;
let the user inspect and correct every belief;
act only under revocable authority;
verify every effect or visibly hold;
compensate only when fresh state says it is safe;
earn autonomy only by beating the incumbent on real human behavior.
```

Safety is not the mission; it is what makes machine acting trustworthy. Evaluation is
not the mission; it prevents us from mistaking a demo, fixture, or self-score for human
improvement. Compression is not the mission; it makes the loop small enough to reason
about without deleting truth, control, or learning.

CalendarPilot is therefore **not** successful when it merely opens, chats, emits a high
reward number, passes a release suite, or writes an event. It succeeds when a person can
state a real goal and receive a relevant, evidence-grounded proposal; see the exact
change and tradeoff; safely simulate, authorize, verify, or undo it; correct the system;
and trust that the correction becomes causal evidence for later behavior.

---

## 2. What “Dogfood” Means

Dogfood means rough-draft-to-MVP product validation through the user-visible macOS app.
It is not a synonym for automated testing and it has no “informal” variant.

A dogfood pass must exercise this visible loop:

```text
goal -> inspect -> propose -> clarify -> simulate -> stage/commit or decline
     -> verify/undo -> feedback -> replay/restart
```

The following are necessary evidence, but none alone proves dogfood success:

- `make mac-app-build` proves the bundle builds.
- `make dogfood-release` proves its enumerated deterministic release checks.
- `make browser-e2e` proves the fixture browser flow.
- `make live-codex-e2e` proves that a live Codex path is reachable.
- `make live-diffusiongemma-e2e` proves that the live NIM policy path is reachable.
- `make live-eventkit-e2e` proves only the exact EventKit procedure and scope it records.
- P13 architecture gates prove the manifested migration or preservation claims.

Product dogfood and learning promotion are separate decisions:

- Dogfood feedback should immediately drive product fixes.
- Current P13.6 feedback rows are deliberately `pre_epoch` and `search_only`.
- Positive-learning promotion remains closed until real partition windows, authenticated
  human reward ingress, and identifiable improvement statistics are bound.
- Those promotion requirements do **not** block product dogfood and must not be placed
  in its critical path.

---

## 3. Current State

### 3.1 Protected implementation

| Surface | Current truth |
|---|---|
| Repository | ground-zero test ran after protected `main` reached `a460991805a0f0388a184e93c9a8e951b1cb5467` |
| App subtree | `calendar-pilot-p12/` at tree `432fb2909b969546f1b7c29f652a7e081784b859` |
| Built app | `calendar-pilot-p12/dist/CalendarPilot.app` |
| Desktop app | `~/Desktop/CalendarPilot.app` symlinks to that built app |
| Bundle id | `dev.calendarpilot.dogfood` |
| Build id | `a460991805a0` |
| Mutable app state | `~/Library/Application Support/CalendarPilot/` |
| Architecture | P13.1-P13.5 close one bounded `create_prep_block` vertical and one exact managed EventKit binding lineage |
| Learning | P13.6 immutable payload/bootstrap/rollback and causal decision/exposure/outcome capture are landed; positive promotion is held |

The architectural foundation is strong for its declared scope. It does not imply that
the product is useful. P13 has deliberately transferred only bounded authority: no
global EventKit ownership, production deployment, other-calendar authority,
other-action authority, or positive-learning promotion follows from these closures.

### 3.2 Capability verdict

| Layer | Verdict | Meaning |
|---|---|---|
| Packaging and local launch | Pass | The protected-main macOS bundle launches and serves the app. |
| Runtime identity | Pass | Launch state and UI reported build, mode, and active backends. |
| Typed candidate/receipt controls | Pass | Simulate and candidate feedback operated through the visible app. |
| Safety/evidence plumbing | Pass for the exercised no-write scope | Swift returned a simulation receipt; two correction outcomes were recorded; no invariant violation appeared. |
| Real calendar understanding | Not reached | The exercised provider was `deterministic_fixture_provider`; no real calendar was inspected. |
| Recommendation usefulness | Fail | The visible proposal omitted its exact date, start, end, and duration. |
| Conversational continuity | Fail | A direct follow-up regenerated the same plan instead of answering it. |
| Staged draft | Pass mechanically; fail as product behavior | The planner automatically created two local staged drafts even though the user asked for a recommendation without a change. No provider write occurred. |
| Real provider effect and undo | Not reached in this pass | No Commit, EventKit write, or undo occurred. |
| MVP readiness | Fail | The infrastructure works, but the primary user value loop did not. |

### 3.3 Ground-zero live finding — 2026-07-10

The Desktop app was launched through Computer Use from protected-main build
`a460991805a0`. The runtime identified itself as:

```text
mode       live_codex
Codex      live_codex_app_server
policy     heuristic_diffusiongemma_policy
kernel     SwiftKernelIPCClient
provider   deterministic_fixture_provider
```

Request:

> Review tomorrow and suggest the single highest-value focus block I should add.
> Explain why, but do not change my calendar.

Observed result:

- Live Codex was reached.
- The app rendered `Protect Deep Work` and `Do Nothing`.
- The selected candidate internally contained `2026-07-11 08:00-09:30 UTC`, but the
  visible card omitted the action fields and foregrounded Reward, Regret, Right moment,
  Tier, and reward-head values.
- Its local-day interpretation was neither rendered nor validated. On the dogfood Mac,
  `08:00 UTC` was `01:00 PDT`, so whether this was actually a sensible local “tomorrow”
  is unresolved and likely defective.
- The visible rationale was generic and based on `0 occupied workday minutes` and one
  fixture gap. It was not grounded in the user's real calendar.
- Each planning turn automatically simulated and then staged the winning candidate,
  producing local staged-draft receipts `stage_rcpt_a4bd2a227ae4d723` and
  `stage_rcpt_cf4bd4dcfe51e59e`. This happened despite the recommendation-only wording;
  it did not mutate provider state.
- Simulate succeeded and returned `preview_rcpt_8e928ca0364bb12f`, but the visible result
  only said `simulated for protect_deep_work`; this manual simulation was additional to
  the planner's automatic simulate/stage sequence and still did not expose the interval
  or conflict result.
- The follow-up `What exact start time and duration are you proposing for tomorrow?`
  launched another planning turn and regenerated the same candidate instead of answering
  the question from conversation context.
- Both results were recorded as `corrected`. State reached version 7 with zero reported
  invariant violations.
- No Commit or calendar mutation occurred.

Evidence lives under:

```text
~/Library/Application Support/CalendarPilot/launch_state.json
~/Library/Application Support/CalendarPilot/sessions/
~/Library/Application Support/CalendarPilot/sessions/session_20260702_143826_68deaa14bf/session_state.json
~/Library/Application Support/CalendarPilot/sessions/session_20260702_143826_68deaa14bf/replay.jsonl
~/Library/Application Support/CalendarPilot/sessions/session_20260702_143826_68deaa14bf/latest_session.json
```

The current projection defect is also visible in source: `frontend/surface.py` creates
candidate cards without action start/end data, while `frontend/static/js/components/cards.js`
renders reward anatomy and action controls from that reduced card.

The initial `make desktop-shortcut` attempt exposed a missing executable bit on
`scripts/install_desktop_shortcut.sh`. The bit is repaired in this change and the
canonical target now recreates the Desktop icon successfully.

---

## 4. Reduce Variables: The Dogfood Ladder

Never start with `auto` or `production` when diagnosing a failure. A combined runtime
can vary the executive, proposer, kernel, provider, credentials, observation, effects,
and persisted session at once.

Use a fresh run directory and the same scenario at every rung. Change exactly one
trust-bearing runtime axis, establish its verdict, then proceed.

| Rung | Runtime | Codex | Policy | Kernel | Provider | Effect ceiling | Question answered |
|---:|---|---|---|---|---|---|---|
| D0 | release preflight | none | none | none | none | none | Is this exact protected build runnable? |
| D1 | `fixture` | deterministic | heuristic | stub | deterministic fixture | automatic simulate/staged draft permitted; no provider commit | Is the product contract coherent with no external variability? |
| D2 | `swift_ipc` | deterministic | heuristic | Swift IPC | deterministic fixture | automatic simulate/staged draft permitted; no provider commit | Does compiled authority preserve D1 behavior and receipts? |
| D3 | `live_codex` | live | heuristic | Swift IPC | deterministic fixture | automatic simulate/staged draft permitted; no provider commit | Can the conversational executive inspect, clarify, and preserve context? |
| D4 | `live_diffusiongemma` | deterministic | live NIM | Swift IPC | deterministic fixture | automatic simulate/staged draft permitted; no provider commit | Does the live proposer produce valid, diverse, concrete futures? |
| D5 | `live_provider` | deterministic | heuristic | Swift IPC | EventKit | real read plus automatic staged draft permitted; no provider commit | Does the app truthfully understand the real calendar? |
| D6 | `auto` with all-live resolution | live | live NIM | Swift IPC | EventKit | recommendation/staged draft only; no provider commit | Does the integrated read/propose/clarify loop retain every lower-rung property? |
| D7 | `auto` plus a fresh managed EventKit binding | exact D6 composition | exact D6 composition | Gate/Gateway | exact current-build `binding_id@epoch` | blocked until current-build setup/rebind; then one confirmed private effect and undo | Does one real effect verify and compensate end to end? |

Runtime modes isolate components; they are not an autonomy ladder. A D4 pass cannot
erase a D3 failure, and a D6 response is uninterpretable until D1-D5 identify which
component owns each failure.

At D1-D6, do not click Commit. The current planners may automatically simulate and
create a local staged draft; record it, require that it be clearly visible, and verify
that it did not mutate provider state. D7 is the only real-effect rung, and it remains
restricted to the already certified
`create_prep_block × apple_eventkit × binding_id@epoch` ownership unit.
Attendee-affecting, other-calendar, other-action, self-play-provider, and broad
production effects are outside this document.

---

## 5. Ground-Up Instructions

### 5.1 Pin the exact build

From the repository root:

```bash
GIT_ROOT="$(git rev-parse --show-toplevel)"
cd "$GIT_ROOT"

git fetch origin
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
test -z "$(git status --short)"

make mac-app-build
make dogfood-release
jq -e '.ok == true' calendar-pilot-p12/runs/release/dogfood_release_report.json
make desktop-shortcut

test -x calendar-pilot-p12/dist/CalendarPilot.app/Contents/MacOS/CalendarPilot
test "$(cat calendar-pilot-p12/dist/CalendarPilot.app/Contents/Resources/app/build_id)" = "$(git rev-parse --short=12 HEAD)"
readlink "$HOME/Desktop/CalendarPilot.app"
```

Do not proceed if the worktree is dirty, HEAD differs from protected main, the release
command exits nonzero or its report has `.ok != true`, the Desktop icon targets another
tree, or the bundle build id does not equal HEAD.

### 5.2 Start every rung from a fresh state directory

Quit every running CalendarPilot instance first. Then set the rung and launch the
Desktop app through LaunchServices:

```bash
RUNG="d1-fixture"
MODE="fixture"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$RUNG-$(git rev-parse --short=12 HEAD)"
RUN_DIR="$HOME/Library/Application Support/CalendarPilot/dogfood/$RUN_ID"
mkdir -p "$RUN_DIR"

open -n \
  --env CALENDAR_PILOT_RUNTIME_MODE="$MODE" \
  --env CALENDAR_PILOT_RUN_DIR="$RUN_DIR" \
  "$HOME/Desktop/CalendarPilot.app"
```

Set `MODE` to the exact runtime named in §4. Do not reuse a run directory across rungs.
Do not use the app's old `Current fixture run` session as evidence for a new build.

### 5.3 Prove launch ownership before using the UI

Wait for `$RUN_DIR/launch_state.json`, then verify the app you are looking at:

```bash
jq '{status, build_id, app_bundle_path, base_url, runtime_mode, launcher_pid, server_pid}' \
  "$RUN_DIR/launch_state.json"

BASE_URL="$(jq -r '.base_url' "$RUN_DIR/launch_state.json")"
curl -fsS "$BASE_URL/api/health" | jq '{
  build_id,
  runtime_mode,
  backends,
  fixture_paths,
  provider_health,
  codex_health,
  diffusiongemma_health,
  live_blockers,
  setup_notes,
  process
}'
```

Hold immediately if build id, PID, port, runtime mode, backend identity, observation
source, or app path is missing or inconsistent. Never attach dogfood evidence to an
ambient `127.0.0.1:8787` process without this ownership proof.

### 5.4 Use the same product scenario at D1-D6

Start a new chat and send these prompts in order:

```text
1. What do you know about my calendar tomorrow? Cite the events or gaps you used.

2. Suggest the single highest-value change for tomorrow. Give the exact local date,
   start, end, duration, affected calendar, conflicts checked, and why it is better
   than doing nothing. Do not change my calendar.

3. What exact evidence made this recommendation better than doing nothing?

4. What exact start time and duration are you proposing? Answer from the plan you just
   made; do not generate a new plan.
```

Then:

1. Inspect the visible candidate before opening the inspector.
2. Simulate the chosen candidate.
3. Verify that simulation presents the exact proposed action and conflict/provider
   result, not only a status label.
4. Mark the candidate `Useful`, `Dismiss`, or `Needs correction` according to the
   product result.
5. Export replay.
6. Quit the app, relaunch the same rung against the same run directory, and verify that
   conversation, receipt, feedback, and runtime identity restore without duplication.

Do not excuse a poor visible answer because the missing fields exist in an envelope,
trace, JSON file, or model response. The user-visible projection is part of the product
contract.

### 5.5 Grade each rung with hard user-visible gates

| Gate | Pass condition |
|---|---|
| Truth | The app visibly identifies whether calendar data and each backend are fixture or live; it makes no unsupported claim. |
| Grounding | The answer cites the actual events, gaps, constraints, or explicit lack of evidence used. |
| Concreteness | Every action shows local date, start, end, duration, calendar, affected events/people, and reversibility before Stage or Commit. |
| Utility | The proposal addresses the stated goal and explains why it beats doing nothing in human terms. |
| Conversation | Clarification and follow-up operate on the existing plan unless the user asks to replan. |
| Alternatives | The user can see the material tradeoff between the leading future and at least the no-op baseline. |
| Control | No effect occurs from inspection, recommendation, follow-up, feedback, or simulation. Stage and Commit are distinguishable. |
| Effect integrity | When D7 is authorized, commit has an exact receipt and provider verification; undo has separate authority and verified absence. |
| Correction | Useful/dismiss/correct feedback attaches to the exposed candidate or receipt and survives restart. |
| Legibility | Internal reward, regret, and authority details support the decision; they never replace the concrete recommendation. |

Any failed hard gate fails the rung. Record `hold` only when the result is genuinely
unobservable because a credential, permission, backend, or external state is absent.
Do not turn a product failure into a hold.

### 5.6 D5 real-calendar read-only checkpoint

Before any real provider read:

- Build and launch the visible `CalendarPilot.app` identity.
- Request permission through the owned app server, then let the user answer the macOS
  prompt if one appears:

  ```bash
  curl -fsS -X POST "$BASE_URL/api/provider/permission/request" \
    -H 'Content-Type: application/json' \
    -d '{}' | jq '{runtime, provider, inspector}'
  ```

- Verify `/api/health` satisfies all of the following. Missing user permission or an
  externally unavailable bridge is `hold`. Once those prerequisites are present, wrong
  provider identity, an unloaded provider observation, sample-fixture fallback, or
  inconsistent health is `fail`:

  ```text
  backends.provider == apple_eventkit
  provider_health.configured == true
  provider_health.authorization_status == full_access
  fixture_paths.provider_observation_loaded == true
  fixture_paths.uses_sample_fixtures == false
  live_blockers == []
  ```

- Use read-only prompts first. Do not click Commit. If the planner automatically creates
  a staged draft, record it, verify zero provider mutation, and treat hidden or
  unrequested staging as a product defect if the UI does not explain it.
- Compare the cited visible events and gaps against Apple Calendar manually.
- Treat any title/time/calendar mismatch or silent fixture fallback as fail.

OS permission belongs to the visible app/bridge identity. A raw Swift binary or an IDE
permission is not product dogfood evidence.

The current product has no first-class visible `Connect Calendar` control. The owned API
request can unblock the experiment, but needing that API remains an MVP access-point gap.

### 5.7 D6 integrated read-only checkpoint

Launch `auto` only after D1-D5 have individual verdicts. Do not accept `auto` merely
because it has no blockers: require the exact all-live composition and no fallback notes:

```text
runtime_mode == auto
backends.codex == live_codex_app_server
backends.diffusiongemma == nvidia_nim_diffusiongemma_policy
backends.kernel == SwiftKernelIPCClient
backends.provider == apple_eventkit
fixture_paths.provider_observation_loaded == true
fixture_paths.uses_sample_fixtures == false
live_blockers == []
setup_notes == []
```

Repeat the D1-D5 prompts without clicking Commit. Any heuristic-policy or deterministic-
provider fallback fails D6 even if the app labels it a setup note rather than a blocker.

### 5.8 D7 one-effect checkpoint

D7 is currently **blocked pending a current-build setup/rebind artifact**. Existing
binding files were created for older app hashes and must not be reused after a rebuild.
After D1-D6 pass, run the app-bundled managed EventKit live certificate from
[calendar-pilot-p12/README.md](calendar-pilot-p12/README.md) against the exact product
build. Require its materialization status to pass, cleanup to verify absence, and its
recorded app and bridge hashes to equal the app being dogfooded.

The new certificate emits a fresh `binding_path`. Launch D7 with a separate durable
state root and explicit initialization:

```bash
BINDING_FILE="<current-build binding_path from runs/eventkit_e2e/eventkit_health.json>"
STATE_ROOT="$RUN_DIR/managed-eventkit-effect-state"

open -n \
  --env CALENDAR_PILOT_RUNTIME_MODE=auto \
  --env CALENDAR_PILOT_RUN_DIR="$RUN_DIR" \
  --env CALENDAR_PILOT_MANAGED_EVENTKIT_BINDING_FILE="$BINDING_FILE" \
  --env CALENDAR_PILOT_MANAGED_EVENTKIT_STATE_ROOT="$STATE_ROOT" \
  --env CALENDAR_PILOT_MANAGED_EVENTKIT_INITIALIZE=1 \
  "$HOME/Desktop/CalendarPilot.app"
```

Hold if the binding path is absent, its app/bridge hashes differ, its calendar
fingerprint drifts, initialization fails, or another owner holds the lease. The operator
must explicitly confirm the real calendar effect at action time.

The one allowed scenario is an attendee-free private `create_prep_block` in the exact
managed calendar binding. Before Commit, the UI must show:

```text
local date and start/end
duration and title
exact target calendar
zero attendees
conflict preview
authority scope and confirmation provenance
reversibility and expected undo behavior
```

After Commit, require one provider external id, exact readback equality, a committed
receipt, and a rollback handle. Then request Undo through the visible product path and
require a separately authorized compensation receipt plus verified absence. Restart and
prove that replay, receipt ownership, provider state, and absence survive without
redispatch.

The deterministic and live certificate access points remain in
[calendar-pilot-p12/README.md](calendar-pilot-p12/README.md). Dogfood does not weaken or
bypass them.

---

## 6. MVP Exit Gate

CalendarPilot becomes P13 dogfood-MVP ready only when all of the following are true on
one protected-main build:

```text
[ ] D1-D5 pass the same grounding, recommendation, follow-up, and simulation scenario.
[ ] D6 `auto` resolves to live Codex, live proposer, Swift IPC, and real read-only EventKit,
    with every active backend and data source visible and consistent.
[ ] The visible recommendation always carries an exact action, not merely an intent or score.
[ ] Follow-up questions resolve against the existing plan without accidental replanning.
[ ] At least one real, private, attendee-free, bound create_prep_block commit verifies.
[ ] Its visible undo verifies absence and survives restart without duplication.
[ ] Candidate and receipt feedback are recorded and restorable.
[ ] No invariant violation, unexplained provider state, silent fixture fallback, or
    unsupported authority claim occurs.
[ ] The operator judges the recommendation useful enough that they would have made the
    calendar change without being asked to help test the machinery.
```

Only after this gate passes should repeated organic use begin. Program A's `>=20`
matched examples and `>=10` explicit feedback rows are eligibility to evaluate later
learning; they are not substitutes for this MVP gate.

---

## 7. Evidence And Bug Record

For every rung, retain:

```text
protected commit and app subtree
bundle build id and Desktop target
run id and run directory
launch_state.json
/api/health capture
runtime and backend identities
exact prompt sequence
screenshots or visible transcript
candidate/action ids and exact visible action fields
simulation/stage/commit/undo receipts as applicable
provider verification or explicit no-effect proof
feedback outcome ids
replay export
restart result
verdict and next smallest change
```

Use this issue/update shape:

```text
Time:
Operator:
Commit / build id:
Rung / runtime:
Run directory:
Active backends and observation source:
Goal and exact prompts:
Expected user-visible result:
Observed user-visible result:
Effect attempted / actual provider state:
Feedback recorded:
Hard-gate verdicts:
Evidence paths:
Smallest owning component:
Next action:
```

Do not include tokens, `.env` contents, raw auth caches, personal calendar payloads not
needed to reproduce the defect, or screenshots containing unrelated private events.

---

## 8. Updates

Append new entries at the top of this section. Do not rewrite a failed observation after
a fix; add the superseding run and link the old evidence.

### 2026-07-10 — Fresh-state launch syntax verified

- Exercised the documented `open -n --env ...` command with an isolated `/tmp` run
  directory. This was a command/access-point smoke, not a D1 product verdict.
- The app selected an unoccupied port and reported build `a460991805a0`, `fixture`
  runtime, deterministic Codex, heuristic policy, Swift stub, and deterministic fixture
  provider exactly as D1 requires.
- The isolated launcher and server processes were terminated after verification.

### 2026-07-10 — Desktop access point repaired

- Restored execute permission on `scripts/install_desktop_shortcut.sh`.
- `make desktop-shortcut` completed and recreated the canonical Desktop symlink.
- This supersedes only the launcher defect below; it does not alter the ground-zero
  product-quality failure.

### 2026-07-10 — Ground-zero Desktop run

- Commit/build: `a460991805a0f0388a184e93c9a8e951b1cb5467` / `a460991805a0`
- Rung equivalent: D3, though the run reused an older persisted session and therefore
  does not count as a clean D3 baseline.
- Runtime: live Codex, heuristic policy, Swift IPC, deterministic fixture provider.
- Goal: recommend tomorrow's single highest-value focus block without changing the calendar.
- Result: infrastructure pass; product fail. Exact action fields were hidden, real
  calendar evidence was absent, two local staged drafts were created without the
  recommendation-only request making that expectation clear, simulation remained
  abstract, timezone truth was unresolved, and the follow-up regenerated rather than answered.
- Effects: none.
- Feedback: two `corrected` outcomes recorded.
- Next action: repair the candidate projection and conversational follow-up contract,
  then restart at D1 with a fresh run directory. Do not jump to EventKit or learning
  promotion to mask the product failure.

### 2026-07-10 — Desktop access point

- Built protected-main `CalendarPilot.app` and created
  `~/Desktop/CalendarPilot.app -> calendar-pilot-p12/dist/CalendarPilot.app`.
- Launch through Computer Use succeeded after a short blank startup interval.
- `make desktop-shortcut` failed because its installer script lacked execute permission;
  the identical installer was run through Bash to create the icon.
- Superseded by the repaired access-point update above.
