# CalendarPilot System Framework — Object Substrate, Learning-Loop Readiness, and the Glass Cockpit Frontend

Status: canonical target framework. This document consolidates the July 2, 2026 direction/velocity analysis, the architecture review, and the reviewed external assessment into one build plan, and specifies the ground-up frontend redesign.

Implementation-status note: this is a target framework, not a claim of shipped implementation. Where a section builds on code that already exists, the existing path is cited. Everything else is proposed until an implementation owner marks the corresponding milestone complete.

Relationship to other documents:

- `dogfooding.md` remains the operating ledger and runbook. This document is the architecture and build-sequence record.
- `calendar-pilot-updated 2/docs/` remains the revision history. The docs-consolidation pass (section 2.6) will fold both into the four living documents.

Decision record: **build ahead of need — accepted.** The prior review recommended extracting objects only as the god-object split proceeded. The product owner overruled: the object taxonomy is built now, ahead of need. The mitigation that makes this safe is the strangler rule (section 3.4): every new object ships with an interface *and* a delegating implementation that wraps existing code, so ahead-of-need never means big-bang rewrite.

---

## 0. End goal, restated as measurable axes

The founding intent is unchanged since the inversion:

```text
machine learning, machine acting, and self-play
within Codex, DiffusionGemma, and Swift.
```

The operating split to preserve:

```text
DiffusionGemma/NIM generates typed candidate futures.        (machine learning)
Codex inspects, compares, repairs, and operates typed tools. (executive)
Swift owns calendar reality, grants, writes, rollback, audit.(machine acting)
Replay/self-play/tuning close the loop.                      (self-play)
```

Each axis gets a measurable definition so "progress" is falsifiable:

| Axis | Measured by | Today | Target |
|---|---|---|---|
| Machine learning | tuning changes the next frontier; intent-keyed residuals accumulate across runs | proven once (`runs/replay_offline_tuning_loop/artifacts/diff_summary.json`), but keys fragment on free text | canonical-intent residuals, per-generation frontier diffs, rejection-rate tracked |
| Machine acting | every mutation carries one ActionEnvelope with verified rollback state | envelope exists on commit/undo receipts (`codex/tools.py:_canonical_action_envelope`) | envelope is the lifecycle spine; invariants I1–I6 executable |
| Self-play | episodes run through the production ActionLifecycle against a sandboxed provider | bypasses it (`diffusiongemma/self_play.py:229` calls `kernel.authorize_and_materialize` directly, self-issuing confirmed grants) | backend-parameterized lab with grant policy; scenario assertions |

---

## 1. The object substrate

### 1.1 The environment object world

`DogfoodSessionState` (1,842 lines, ~70 methods) is decomposed into a small environment of message-passing objects. Each object emits **TraceEvents** while it works and **receipts/records** when it finishes. The frontend is a consumer of the same stream the training loop consumes — one data spine, two readers.

```text
CalendarPilotEnvironment                (composition root; owns lifecycle & lock)
├── RuntimeAssembly                     resolves RuntimeProfile -> concrete backends
├── SessionStore                        atomic persistence, restore, state_version
├── TraceBus                            live event pub/sub; SSE fan-out; replay feed
├── ConversationRouter                  turn -> RoutedTurn (intent, route, confidence)
├── FrontierService                     NIM/heuristic frontier + taxonomy + rejections
├── ActionLifecycle                     candidate -> ... -> undo; owns ActionEnvelope
├── ReplayJournal                       append-first JSONL + read model (trace joins)
├── SelfPlayLab                         backend-parameterized episodes & scenarios
├── LearningLoop                        replay -> PolicyTuning -> frontier diff
└── FrontendProjector                   environment state -> view_state.v2
```

New module layout:

```text
src/calendar_pilot/environment/
  __init__.py
  objects.py          Protocol definitions for every object above
  trace.py            TraceEvent + TraceBus
  envelope.py         ActionEnvelope + ActionLifecycle
  router.py           RoutedTurn + KeywordRouter + ModelIntentRouter
  taxonomy.py         CanonicalIntent + normalize_intent
  invariants.py       executable invariant checker
  selfplay_backends.py backend enum + grant policy
src/calendar_pilot/frontend/
  projector.py        FrontendProjector (evolves surface.py)
```

### 1.2 Object interfaces (Python)

`src/calendar_pilot/environment/objects.py`:

```python
from __future__ import annotations

from typing import Any, Protocol

from calendar_pilot.types import (
    AuthorityGrant,
    CandidateCalendarAction,
    RawCalendarObservation,
    RewardEvent,
    UserBiography,
)


class TraceSink(Protocol):
    """Anything that accepts live telemetry. TraceBus implements this."""

    def emit(self, *, obj: str, stage: str, status: str, trace_id: str,
             payload: dict[str, Any] | None = None,
             causal_parent_id: str | None = None) -> None: ...


class ConversationRouterProtocol(Protocol):
    def route(self, turn_text: str, *, context: dict[str, Any]) -> "RoutedTurn": ...


class FrontierServiceProtocol(Protocol):
    def generate(self, goal: str, observation: RawCalendarObservation,
                 biography: UserBiography, *, trace_id: str) -> "FrontierResult": ...


class ActionLifecycleProtocol(Protocol):
    """The single path every calendar mutation takes. Self-play uses this too (S1)."""

    def prepare(self, candidate: CandidateCalendarAction,
                observation: RawCalendarObservation,
                grant: AuthorityGrant | str | None, *, trace_id: str) -> "ActionEnvelope": ...
    def simulate(self, envelope: "ActionEnvelope") -> "ActionEnvelope": ...
    def stage(self, envelope: "ActionEnvelope") -> "ActionEnvelope": ...
    def commit(self, envelope: "ActionEnvelope", *, confirmed: bool) -> "ActionEnvelope": ...
    def verify(self, envelope: "ActionEnvelope") -> "ActionEnvelope": ...
    def reward(self, envelope: "ActionEnvelope", event: RewardEvent) -> "ActionEnvelope": ...
    def undo(self, rollback_handle_id: str, grant: AuthorityGrant | str | None,
             *, trace_id: str) -> "ActionEnvelope": ...


class ReplayJournalProtocol(Protocol):
    def append(self, record_type: str, payload: dict[str, Any], *,
               trace_id: str, causal_parent_id: str | None = None) -> str: ...
    def causal_chain(self, trace_id: str) -> list[dict[str, Any]]: ...
    def export(self) -> dict[str, Any]: ...


class FrontendProjectorProtocol(Protocol):
    def view(self) -> dict[str, Any]:
        """Full view_state.v2 snapshot (section 5.3)."""
        ...
```

The strangler rule: the first implementation of each protocol delegates to the code that exists today (`FrontierService` wraps `LiveDiffusionGemmaPolicy`/`DiffusionGemmaPolicy`; `ActionLifecycle` wraps `CodexToolRuntime` stage/commit/undo paths and promotes its `_canonical_action_envelope`; `FrontendProjector` wraps `build_frontend_snapshot`). Behavior does not change on extraction day; only the seams do.

---

## 2. Evidence integrity (P0 — do these first)

These protect the data every later section depends on. All are hours, not days.

### 2.1 Session lock + state_version

`ThreadingHTTPServer` serves concurrent requests into shared session state, and the UI deliberately polls during long POSTs. Today there is no lock (`session_manager.py` locks only the registry). Every public session method takes the session lock; every mutation bumps a monotonic version.

```python
# session.py (until the split lands; the environment root inherits this)
import threading

class DogfoodSessionState:
    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self.state_version = 0
        # ... existing __post_init__ ...

    def _bump(self) -> None:
        self.state_version += 1

    # pattern for every public method:
    def create_plan(self, goal: str, **kwargs) -> dict[str, Any]:
        with self._lock:
            self._bump()
            return self._create_plan_locked(goal, **kwargs)
```

`state_version` is embedded in every snapshot, every view_state, and every TraceEvent, so a poller (and the SSE store, section 6) can detect staleness and ordering for free.

Regression test (new `tests/test_concurrency.py`):

```python
def test_poll_during_slow_plan_returns_consistent_state(self):
    session = DogfoodSessionState(...)
    session.planner = SlowPlannerFake(delay_seconds=0.5)   # injected
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        plan = pool.submit(session.create_plan, "make tomorrow calm")
        versions = [session.snapshot()["state_version"] for _ in range(20)]
    plan.result()
    self.assertEqual(versions, sorted(versions))           # monotonic
    final = session.snapshot()
    for receipt in final["chat"]["receipt_cards"]:
        # no torn receipt: committed rows must carry rollback handles
        if receipt.get("status") == "committed":
            self.assertTrue(receipt.get("rollback_handle_id"))
```

### 2.2 Atomic writes + append-first replay

All state files are written non-atomically today, and `persist()` (19 call sites) rewrites the full replay JSONL each turn — O(n²) I/O and a corruption amplifier.

```python
# src/calendar_pilot/environment/fsio.py
import json, os
from pathlib import Path
from typing import Any

def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)   # atomic on POSIX

def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
```

`ReplayJournal` (section 1.1) appends each record at append-time via `append_jsonl` and keeps the in-memory list for read models. `save_jsonl` becomes a compaction command, not the persistence path. `session_state.json`, `latest_session.json`, and launch manifests move to `atomic_write_json`.

### 2.3 CI at the git root, producing evidence

The workflow at `calendar-pilot-updated 2/.github/workflows/ci.yml` never runs — GitHub reads workflows only from the repository root, and the git root is `Destination/`. Replace with a root workflow that produces the evidence bundle by default, secret-scanned before upload:

```yaml
# .github/workflows/ci.yml   (git root)
name: ci
on: [push, pull_request]
defaults:
  run:
    working-directory: calendar-pilot-updated 2
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.13'}
      - run: python -m pytest -q
      - run: PYTHONPATH=src python scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl
      - name: evidence bundle
        run: |
          mkdir -p ../ci_evidence
          PYTHONPATH=src python -m calendar_pilot.app frontend --write-snapshot --out ../ci_evidence/frontend_state.json
          PYTHONPATH=src python scripts/run_secret_scan.py --path ../ci_evidence
      - uses: actions/upload-artifact@v4
        with: {name: evidence, path: ci_evidence/}
  swift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: swift-actions/setup-swift@v2
        with: {swift-version: '6.0'}
      - run: swift test --package-path packages/CalendarPilotKernel
  macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - run: swift build --package-path packages/CalendarPilotKernel --product CalendarPilotMacApp
      - run: scripts/build_macos_app.sh
```

One harness: pytest everywhere (Makefile `py-test` target updates to `python3 -m pytest -q`).

---

## 3. Learning-loop prerequisites

### 3.1 Canonical intent taxonomy (P0 of the ML loop)

Evidence of the defect: `runs/replay_offline_tuning_loop/artifacts/diff_summary.json` keys `intent_reward_bias` by free-text sentences, and `scripts/train_offline_policy.py` buckets its entire training table by `row.get("intent")`. Tuning keyed on prose can never accumulate.

```python
# src/calendar_pilot/environment/taxonomy.py
from __future__ import annotations
from enum import Enum


class CanonicalIntent(str, Enum):
    PROTECT_DEEP_WORK = "protect_deep_work"
    CREATE_PREP_BLOCK = "create_prep_block"
    ADD_BUFFER = "add_buffer"
    BATCH_ADMIN = "batch_admin"
    RESCHEDULE_CONFLICT = "reschedule_conflict"
    MOVE_MEETING = "move_meeting"
    DECLINE_OR_TRIM = "decline_or_trim"
    NOTIFY_SUMMARY = "notify_summary"
    ASK_CLARIFICATION = "ask_clarification"
    DO_NOTHING = "do_nothing"
    OTHER = "other"


_KEYWORD_MAP: list[tuple[CanonicalIntent, tuple[str, ...]]] = [
    (CanonicalIntent.PROTECT_DEEP_WORK, ("deep work", "focus block", "protect", "focus time")),
    (CanonicalIntent.CREATE_PREP_BLOCK, ("prep", "prepare", "preparation")),
    (CanonicalIntent.ADD_BUFFER, ("buffer", "breathing room", "gap between")),
    (CanonicalIntent.BATCH_ADMIN, ("batch", "admin", "errand", "grouped tasks")),
    (CanonicalIntent.RESCHEDULE_CONFLICT, ("conflict", "overlap", "double book")),
    (CanonicalIntent.MOVE_MEETING, ("move", "reschedule", "shift")),
    (CanonicalIntent.DECLINE_OR_TRIM, ("decline", "shorten", "trim", "cancel")),
    (CanonicalIntent.NOTIFY_SUMMARY, ("notify", "digest", "summary")),
    (CanonicalIntent.ASK_CLARIFICATION, ("clarif", "confirm preference", "ask the user")),
    (CanonicalIntent.DO_NOTHING, ("do nothing", "no action")),
]


def normalize_intent(raw: str) -> dict[str, str]:
    """Map a model-supplied intent to the canonical taxonomy.

    Returns {"intent", "intent_raw", "matched_by"} so training keys on the
    canonical value while the original text stays inspectable.
    """
    text = " ".join(str(raw or "").lower().split())
    for enum_value in CanonicalIntent:
        if text == enum_value.value:
            return {"intent": enum_value.value, "intent_raw": raw, "matched_by": "exact"}
    for intent, needles in _KEYWORD_MAP:
        if any(needle in text for needle in needles):
            return {"intent": intent.value, "intent_raw": raw, "matched_by": "keyword"}
    return {"intent": CanonicalIntent.OTHER.value, "intent_raw": raw, "matched_by": "fallback"}
```

Wire-in points:

1. `NvidiaNIMPolicyClient._normalize_frontier_candidate` calls `normalize_intent` and stores both fields on the candidate; the frontier prompt also instructs the model to pick from the enum (reduce, don't just repair).
2. `train_offline_policy.py` keys `intent_adjustments` on the canonical value.
3. `apply_policy_tuning()` matches on canonical intent.
4. The `OTHER`-rate becomes a tracked metric on the Learn surface (section 5.2): a rising rate means the taxonomy or the prompt drifted.

### 3.2 Model-generation rejection records

The NIM parser already accumulates structured reasons (`live.py` `validation_errors`: `skipped_invalid_candidate`, `duplicate_candidate_id`, `missing_target_calendars`). Two additions finish the job:

```python
# in FrontierService, after parsing
for rejection in parsed["rejections"]:          # now retains the raw payload
    self.replay.append(
        "model_generation_rejection",
        {
            "model": self.model,
            "prompt_version": self.prompt_version,
            "raw_item": rejection["raw_item"],   # the rejected JSON as received
            "reason": rejection["reason"],
            "schema_errors": rejection.get("schema_errors", []),
        },
        trace_id=trace_id,
    )
```

Frontier quality (valid / rejected / duplicate counts per generation) becomes a first-class metric — a silently thinning frontier reads as "the model chose X" when it means "X survived parsing."

### 3.3 The router is a policy component

Routing decisions gate everything downstream and never enter replay today (`replay.py` has seven record types; none is routing). New contract:

```python
# src/calendar_pilot/environment/router.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoutedTurn:
    turn_id: str
    router_backend: str          # "fixture_keywords" | "live_codex_intent" | "fallback_keywords"
    classified_intent: str       # smalltalk|metadata_question|operational_tool|calendar_goal|mixed_calendar_operational|non_calendar
    route: str                   # planner|conversation|operational|provider
    confidence: float
    counterfactual_routes: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)   # matched terms / model rationale

    def replay_payload(self) -> dict[str, Any]:
        return {"record_type": "router_decision", **self.__dict__}
```

Implementations:

- `KeywordRouter` — the existing `_classify_chat_intent` logic extracted verbatim; the deterministic fixture path and the live fallback.
- `ModelIntentRouter` — live modes add `intent` to the Codex conversation output schema; the model classifies, the keyword result is recorded as the counterfactual.

Every turn appends a `router_decision` replay row and emits a `route_classified` TraceEvent. Self-play gains a router adversary later (section 4.3) — ambiguous turns, misleading corrections, vague undo references.

### 3.4 Reward provenance (field now, heads later)

`RewardEvent` gains one field:

```python
provenance: str = "observed"   # observed | provider | adversarial | model
```

Cheap now, future-proofs the data. The reducer stays single-headed until the daily-driver protocol produces volume; splitting training heads on today's signal density would fragment thin data.

### 3.5 Tuning provenance contract

`train_offline_policy.py` output gains a provenance block so the Learn surface (and a human) can answer "why did the policy change":

```json
{
  "tuning_id": "offline_replay_v2",
  "generated_at": "2026-07-02T18:00:00Z",
  "source_replay": {"path": "runs/.../replay.jsonl", "records": 61, "trace_ids": ["..."]},
  "intent_reward_bias": {"create_prep_block": -0.21},
  "bias_evidence": {
    "create_prep_block": {
      "reward_residual": -0.21,
      "supporting_records": ["reward:rwd_04", "adversary:ep2:1"],
      "narrative": "3 undo_regret findings across 5 episodes"
    }
  },
  "frontier_effect": {"untuned_leader": "cand_001", "tuned_leader": "cand_protect_deep_work_003", "leader_changed": true}
}
```

---

## 4. Machine acting: envelope, invariants, self-play lab

### 4.1 ActionEnvelope as the lifecycle spine

`calendar_action_envelope.v1` already exists as a receipt attachment (`codex/tools.py:_canonical_action_envelope`). Promotion: the envelope becomes the object that *moves through* the lifecycle, updated at each transition, persisted per transition to replay.

```python
# src/calendar_pilot/environment/envelope.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionEnvelope:
    envelope_id: str
    trace_id: str
    candidate_id: str
    observation_fingerprint: str
    runtime_mode: str
    backends: dict[str, str]                       # policy/codex/kernel/provider
    authority: dict[str, Any] = field(default_factory=dict)   # grant_id, tier, scopes
    lifecycle: list[dict[str, Any]] = field(default_factory=list)
    # each entry: {"transition": "prepare|simulate|stage|commit|verify|reward|undo",
    #              "at": iso8601, "status": "...", "swift_receipt_id": ..., "detail": {...}}
    provider: dict[str, Any] = field(default_factory=dict)
    # transaction_id, external_event_ids, idempotency_key,
    # rollback_state: "verified" | "pending" | "failed" | "impossible" | "unsupported"  (I2: never absent)
    reward: dict[str, Any] = field(default_factory=dict)       # reward_event_ids, provenance mix
    replay_record_ids: list[str] = field(default_factory=list)

    @property
    def current_state(self) -> str:
        return self.lifecycle[-1]["transition"] if self.lifecycle else "prepared"

    def to_dict(self) -> dict[str, Any]:
        return {"envelope_version": "calendar_action_envelope.v2", **self.__dict__}
```

Rules:

- `rollback_state` is a required tri-state-plus (`verified|pending|failed|impossible|unsupported`) — never absent (invariant I2). `impossible` is a product decision (e.g., an already-elapsed event); `unsupported` is a provider limitation. Both are visible states, not missing data.
- Every transition appends one replay record (`record_type="envelope_transition"`) carrying the envelope diff.
- UI action cards key on `envelope_id`; the Envelope Viewer (section 6.6) renders the whole object.

### 4.2 Invariants: triage, then execution

Triage of the reviewed invariant set against current code:

| Invariant | Status today | Action |
|---|---|---|
| I1 one envelope per provider mutation | envelope exists on commit/undo only | needs-build (lifecycle promotion) |
| I2 rollback state never absent | `rollback_verified` bool, absent on some paths | needs-build (tri-state) |
| I3 social mutation carries scope provenance | enforced (grants + scopes) | needs-test |
| I4 stale-observation commit refreshed or denied | partial (`_candidate_restore_allowed` fingerprints) | needs-build (deny path) |
| I5 every denial is a training-visible row | denial receipts enter replay | needs-test |
| I6 undo cannot replay twice | enforced both kernels (ledger pop) | needs-test (golden) |
| M1 candidate has model provenance | `policy_backend` present | needs-test |
| M2 training rows carry observation fingerprint | present on receipts | needs-test |
| M3 tuning traceable to replay records | needs 3.5 | needs-build |
| M4 NIM fallback state explicit | `setup_notes` vs `live_blockers` | enforced |
| M5 frontier retains rejected candidates | reasons only, no payloads | needs-build (3.2) |
| S1 self-play uses production ActionLifecycle | violated (`self_play.py:229`) | needs-build (4.3) |
| S2 provider-mutating self-play sandboxed | n/a yet | needs-build (4.3) |
| S3 adversary findings map to tuning features | `failure_penalties` | enforced |
| S4 autonomy promotion has before/after frontier diff | tuning loop artifact | needs-test |

Executable checker — replay is the trajectory record, so invariant checking is trace monitoring:

```python
# src/calendar_pilot/environment/invariants.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Violation:
    invariant_id: str
    record_id: str
    detail: str


Check = Callable[[list[dict[str, Any]]], list[Violation]]


def check_i2_rollback_state_never_absent(records: list[dict[str, Any]]) -> list[Violation]:
    out: list[Violation] = []
    for rec in records:
        if rec.get("record_type") != "envelope_transition":
            continue
        env = rec.get("payload", {}).get("envelope", {})
        if env.get("current_state") in {"commit", "verify", "undo"}:
            state = env.get("provider", {}).get("rollback_state")
            if state not in {"verified", "pending", "failed", "impossible", "unsupported"}:
                out.append(Violation("I2", rec.get("record_id", "?"), f"rollback_state={state!r}"))
    return out


def check_i6_undo_never_replays(records: list[dict[str, Any]]) -> list[Violation]:
    seen: set[str] = set()
    out: list[Violation] = []
    for rec in records:
        if rec.get("record_type") == "receipt" and rec.get("payload", {}).get("receipt", {}).get("sync_status") == "reverted":
            handle = rec["payload"]["receipt"].get("rollback_handle_id") or ""
            if handle in seen:
                out.append(Violation("I6", rec.get("record_id", "?"), f"handle replayed: {handle}"))
            seen.add(handle)
    return out


CHECKS: dict[str, Check] = {
    "I2": check_i2_rollback_state_never_absent,
    "I6": check_i6_undo_never_replays,
    # I1, I4, I5, M1, M2, M3, M5, S1, S2, S4 land with their features
}


def check_replay(records: list[dict[str, Any]]) -> list[Violation]:
    violations: list[Violation] = []
    for check in CHECKS.values():
        violations.extend(check(records))
    return violations
```

Run points: `scripts/check_invariants.py` (CLI), every `replay_export` (violations embedded in the export payload), and CI (section 2.3). A violation in dogfood is a P0 stop per the run rules in `dogfooding.md`.

### 4.3 Self-play lab: backends with grant policy

Self-play must run through `ActionLifecycle` (S1) and must not inherit its current ability to self-issue confirmed grants (`self_play.py` issues `confirmed_by_user=True` with `confirmation_provenance="self_play_episode:N"` — fine against the stub, a hole against anything real).

```python
# src/calendar_pilot/environment/selfplay_backends.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class SelfPlayActionBackend(str, Enum):
    STUB_FAST = "stub_fast"
    SWIFT_IPC_DETERMINISTIC = "swift_ipc_deterministic"
    SWIFT_IPC_EVENTKIT_SANDBOX = "swift_ipc_eventkit_sandbox"
    PRODUCTION_SHADOW = "production_shadow"


@dataclass(frozen=True)
class SelfPlayBackendPolicy:
    backend: SelfPlayActionBackend
    grant_issuance: str          # "self_issued" | "kernel_issued_sandbox" | "read_only"
    provider_writes: bool
    max_episodes: int
    requires_env_flag: str | None


BACKEND_POLICIES: dict[SelfPlayActionBackend, SelfPlayBackendPolicy] = {
    SelfPlayActionBackend.STUB_FAST: SelfPlayBackendPolicy(
        SelfPlayActionBackend.STUB_FAST, "self_issued", False, 100, None),
    SelfPlayActionBackend.SWIFT_IPC_DETERMINISTIC: SelfPlayBackendPolicy(
        SelfPlayActionBackend.SWIFT_IPC_DETERMINISTIC, "kernel_issued_sandbox", False, 50, None),
    SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX: SelfPlayBackendPolicy(
        SelfPlayActionBackend.SWIFT_IPC_EVENTKIT_SANDBOX, "kernel_issued_sandbox", True, 10,
        "CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX"),
    SelfPlayActionBackend.PRODUCTION_SHADOW: SelfPlayBackendPolicy(
        SelfPlayActionBackend.PRODUCTION_SHADOW, "read_only", False, 20,
        "CALENDAR_PILOT_SELFPLAY_SHADOW"),
}
```

Sandbox mechanics (S2), enforced **below Python**: the Swift EventKit bridge accepts a `sandbox_calendar_id` in its session config; when set, any mutation targeting another calendar is rejected in Swift before EventKit is called. Setup creates a dedicated `CalendarPilot SelfPlay` calendar; the rollback sweep enumerates and deletes only within it. A buggy Python episode cannot escape the sandbox because the allowlist lives in the bridge.

`kernel_issued_sandbox` grants come from the kernel with a new scope `commit_selfplay_sandbox` and provenance `selfplay_lab`; the runner can no longer mint `confirmed_by_user=True` for real actuation paths.

Scenario algebra (after the backend lands, not before):

```python
Scenario(
    name="external_call_no_prep_high_fatigue",
    disturbances=[AddExternalMeeting(...), RemovePrepSlot(...), SetNotificationFatigue(0.7)],
    adversaries=[ConflictAdversary(), FatigueAdversary(), RegretAdversary()],
    assertions=["no_social_write_without_commit_social",
                "frontier_contains_do_nothing",
                "rollback_handle_exists_if_committed"],   # each maps to an invariant check
)
```

---

## 5. The Glass Cockpit — frontend redesign

### 5.0 Why "glass cockpit"

The lineage: gen 6 built a control console (machinery in the first viewport); gen 7 corrected to chat-first (machinery behind an inspector). Both were right about something. The chat-first doctrine holds — *chat asks and operates* — but the inspector is a filing cabinet: seven tabs of JSON dumps you open after the fact. What the next phase needs is what an aircraft glass cockpit does: the primary control stays primary, while live instruments make the machine's internal state legible **as it acts** — because the operator is about to start trusting it with real writes and real learning.

The redesign thesis, one line:

```text
The frontend is a live replay reader.
If the UI can render it as it happens, training can read it later — one data spine, two consumers.
```

### 5.1 Design goals and non-goals

Goals:

1. Chat remains the front door (unchanged product doctrine).
2. Every background stage — routing, Codex planning, frontier generation, scoring/tuning, grant checks, staging, provider writes, rollback, reward, self-play, tuning reduction — is visible live, with backend, status, latency, and provenance.
3. Every action is inspectable to its causes: click any card → the full causal chain (observation → router → plan → frontier → grant → Swift receipt → provider transaction → reward → tuning effect).
4. Machine learning gets a dedicated surface (frontier diffs, tuning provenance, rejection rate, taxonomy health, reward stream).
5. Self-play gets a laboratory, not a button.
6. XSS class closed by construction: no `innerHTML` templating of dynamic strings anywhere.

Non-goals (doctrine preserved):

- No framework, no npm, no build step. Native ES modules, stdlib backend. The zero-dependency stance survives the redesign.
- No WebSocket dependency: Server-Sent Events over the existing stdlib server (a thread per SSE client under `ThreadingHTTPServer`), with polling as the automatic fallback.
- No redesign of the *product voice* — composer strings, receipts language, and `data-testid` contracts remain stable so `browser_cdp_e2e.mjs` keeps passing during migration.

### 5.2 Information architecture: five surfaces + one viewer

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ CP  │ Operate │ Observe │ Learn │ Lab │ Authority        ● live · v41 · auto│
├──────────────┬─────────────────────────────────────────────┬───────────────┤
│ sessions     │                OPERATE                      │ context rail  │
│              │  chat transcript (primary)                  │ (per-surface) │
│  + new chat  │  candidate cards / receipt cards            │               │
│              │  ┌───────────────────────────────────────┐  │ active turn   │
│ recent runs  │  │ pipeline strip (live, this turn):     │  │ envelope      │
│              │  │ route▸ plan▸ frontier▸ grant▸ commit  │  │ quick-view    │
│              │  └───────────────────────────────────────┘  │               │
│              │  composer  [tier chip] [send]               │               │
└──────────────┴─────────────────────────────────────────────┴───────────────┘
```

| Surface | What it shows | Triad axis |
|---|---|---|
| **Operate** | Chat transcript, candidate/receipt cards, composer, a one-line **pipeline strip** showing the active turn's stages live | acting (front door) |
| **Observe** | The full **turn timeline**: every stage of every turn with object, backend, status, duration, token/latency payloads; failures and denials inline; filterable by trace | background insight (the user's core ask) |
| **Learn** | Frontier explorer (candidates + reward anatomy), **tuned-vs-untuned frontier diff**, tuning provenance ("why the policy changed"), rejection rate, intent-taxonomy health (`OTHER` rate), reward stream by provenance | machine learning |
| **Lab** | Self-play: backend selector (with grant policy shown), scenario picker, episode stream, adversary findings, release gate history | self-play |
| **Authority** | Grants (id, tier, scopes, expiry, provenance), denial history with explanations, undo ledger, authority controls | acting (control plane) |
| **Envelope Viewer** (overlay, opens from any card on any surface) | The full ActionEnvelope + causal chain | all three |

The gen-7 inspector tabs map into this world: runtime → header chip + Observe; authority → Authority; profile → Operate context rail; replay → Observe + Envelope Viewer; self_play → Lab; provider → Authority + Observe; debug → Observe (raw event feed). Each tab is retired only when its surface fully covers it (section 7).

### 5.3 State architecture

Three cooperating contracts:

```text
view_state.v2   full typed snapshot        GET /api/view          (checkpoint)
TraceEvent      live telemetry stream      GET /api/events (SSE)  (delta)
state_version   monotonic per-session      embedded in both       (ordering/staleness)
```

`view_state.v2` (served by `FrontendProjector`; `/api/state` stays during migration):

```json
{
  "view_version": "view_state.v2",
  "state_version": 41,
  "session": {"session_id": "sess_a1", "label": "Make next week less chaotic", "archived_at": null},
  "runtime": {
    "mode": "auto", "mode_label": "Auto assistant",
    "backends": {"kernel": "SwiftKernelIPCClient", "codex": "live_codex_app_server",
                  "diffusiongemma": "nvidia_nim_diffusiongemma_policy", "provider": "apple_eventkit"},
    "live_blockers": [], "setup_notes": [], "credentials": {"...": "..."}
  },
  "conversation": {
    "messages": [{"message_id": "msg_9", "role": "assistant", "title": "Codex answered",
                   "body": "...", "trace_id": "plan_a71c", "card_refs": ["env_31"],
                   "metadata": {"response_source": "live_codex_conversation", "model_reached": true,
                                 "tool_sequence": ["inspect_week", "generate_candidate_frontier"]}}],
    "composer": {"pending_trace_id": "plan_a71c"}
  },
  "frontier": {
    "generation_id": "gen_007", "goal": "make tomorrow less chaotic",
    "policy_backend": "nvidia_nim_diffusiongemma_policy", "prompt_version": "frontier_v2",
    "tuning_id": "offline_replay_v2",
    "candidates": [{"candidate_id": "cand_01", "intent": "create_prep_block",
                     "intent_raw": "Create a prep block before the client call",
                     "title": "...", "reward_breakdown": {"utility": 0.8, "regret": -0.1},
                     "right_moment_decision": "auto_write_then_notify",
                     "required_authority_tier": 3, "model_story": ["..."], "counterfactual": "..."}],
    "rejections": {"count": 2, "reasons": {"skipped_invalid_candidate": 2}}
  },
  "actions": {
    "queue": [{"envelope_id": "env_31", "candidate_id": "cand_01", "state": "committed",
                "swift_receipt_id": "rcpt_d51e", "rollback_state": "verified",
                "rollback_handle_id": "undo_4a54", "grant_id": "grant_9c2f",
                "label": "Committed calendar change", "trace_id": "plan_a71c"}]
  },
  "authority": {
    "grants": [{"grant_id": "grant_9c2f", "tier": 3, "scopes": ["recommend", "stage", "commit_private", "undo"],
                 "expires_at": "2026-07-02T19:04:00Z", "confirmed_by_user": true,
                 "provenance": "user_confirmed_demo_scope"}],
    "denials": [{"receipt_id": "rcpt_acbe", "reason": "required authority tier exceeds Swift-issued grant"}],
    "undo_ledger": [{"rollback_handle_id": "undo_4a54", "candidate_id": "cand_01", "spent": false}]
  },
  "learning": {
    "tuning": {"tuning_id": "offline_replay_v2", "leader_changed": true,
                "bias_evidence": {"create_prep_block": {"reward_residual": -0.21,
                                    "narrative": "3 undo_regret findings across 5 episodes"}}},
    "frontier_diff": {"untuned_leader": "cand_001", "tuned_leader": "cand_protect_deep_work_003",
                       "per_candidate_delta": {"cand_001": -0.21}},
    "taxonomy_health": {"other_rate": 0.04, "matched_by": {"exact": 11, "keyword": 3, "fallback": 1}},
    "reward_stream": [{"reward_event_id": "rwd_04", "provenance": "observed", "feedback": "useful"}]
  },
  "lab": {
    "backend": "stub_fast", "backend_policy": {"grant_issuance": "self_issued", "provider_writes": false},
    "episodes": [{"episode_id": "ep_2", "chosen_intent": "create_prep_block",
                   "findings": [{"failure_mode": "notification_fatigue", "penalty": -0.3}]}],
    "release_gate": {"decision": "hold_autonomy", "at": "2026-07-02T10:30:00Z"}
  },
  "pipeline": {
    "turns": [{"trace_id": "plan_a71c", "goal": "make tomorrow less chaotic", "status": "succeeded",
                "stages": [{"stage": "route_classified", "object": "router", "status": "succeeded", "ms": 2,
                             "payload": {"route": "planner", "router_backend": "live_codex_intent"}},
                            {"stage": "model_call", "object": "codex", "status": "succeeded", "ms": 4210,
                             "payload": {"model_reached": true, "response_id": "resp_..."}},
                            {"stage": "frontier_generated", "object": "frontier_service", "status": "succeeded",
                             "ms": 6120, "payload": {"valid": 3, "rejected": 2, "tuning_applied": true}},
                            {"stage": "grant_checked", "object": "kernel", "status": "succeeded", "ms": 12},
                            {"stage": "commit", "object": "action_lifecycle", "status": "succeeded", "ms": 480,
                             "payload": {"envelope_id": "env_31", "rollback_state": "verified"}}]}]
  },
  "invariants": {"violations": []}
}
```

`TraceEvent` wire format (SSE `data:` payload):

```json
{
  "kind": "trace",
  "seq": 913,
  "event_id": "evt_913",
  "session_id": "sess_a1",
  "state_version": 41,
  "trace_id": "plan_a71c",
  "causal_parent_id": "evt_910",
  "object": "frontier_service",
  "stage": "frontier_generated",
  "status": "succeeded",
  "ts": "2026-07-02T18:12:03.412Z",
  "payload": {"valid": 3, "rejected": 2, "policy_backend": "nvidia_nim_diffusiongemma_policy"}
}
```

Two event kinds keep the reducer trivial:

- `trace` — appended to the pipeline model (timeline, strips, counters).
- `patch` — `{"kind": "patch", "seq": 914, "state_version": 42, "region": "actions", "value": {...}}` — replaces one view region after a mutation completes. The projector emits patches for `conversation`, `frontier`, `actions`, `authority`, `learning`, `lab` at the same points `persist()` runs today.

Gap handling: the store tracks `seq`; a gap → refetch `GET /api/view` (cheap, always correct). POST responses still return the full view for compatibility.

Stage vocabulary (extensible; the timeline renders unknown stages generically):

```text
turn_received  route_classified  planner_started  model_call  plan_validated
frontier_requested  frontier_generated  candidate_scored  tuning_applied
grant_requested  grant_checked  simulate  stage  commit  provider_write
provider_verify  rollback  reward_recorded  replay_appended
self_play_episode  tuning_reduced  invariant_checked  error
```

### 5.4 Backend: TraceBus and SSE

`src/calendar_pilot/environment/trace.py`:

```python
from __future__ import annotations

import json
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Any, Iterator


@dataclass
class TraceEvent:
    seq: int
    event_id: str
    session_id: str
    state_version: int
    trace_id: str
    object: str
    stage: str
    status: str
    ts: str
    causal_parent_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    kind: str = "trace"

    def frame(self) -> bytes:
        return f"id: {self.seq}\ndata: {json.dumps(self.__dict__, sort_keys=True)}\n\n".encode()


class _Subscriber:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.queue: Queue[bytes] = Queue(maxsize=256)

    def frames(self, *, heartbeat_seconds: float = 15.0) -> Iterator[bytes]:
        while True:
            try:
                yield self.queue.get(timeout=heartbeat_seconds)
            except Empty:
                yield b": ping\n\n"          # SSE comment heartbeat keeps proxies honest


class TraceBus:
    """Process-local pub/sub. Ring buffer replays missed events on reconnect."""

    MAX_SUBSCRIBERS = 16
    RING = 512

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._rings: dict[str, deque[TraceEvent]] = {}
        self._subscribers: dict[str, list[_Subscriber]] = {}

    def emit(self, *, session_id: str, state_version: int, trace_id: str, obj: str,
             stage: str, status: str = "succeeded",
             payload: dict[str, Any] | None = None,
             causal_parent_id: str | None = None, kind: str = "trace") -> TraceEvent:
        with self._lock:
            self._seq += 1
            event = TraceEvent(
                seq=self._seq, event_id=f"evt_{self._seq}", session_id=session_id,
                state_version=state_version, trace_id=trace_id, object=obj, stage=stage,
                status=status, ts=datetime.now(timezone.utc).isoformat(),
                causal_parent_id=causal_parent_id, payload=payload or {}, kind=kind)
            ring = self._rings.setdefault(session_id, deque(maxlen=self.RING))
            ring.append(event)
            frame = event.frame()
            for sub in list(self._subscribers.get(session_id, [])):
                try:
                    sub.queue.put_nowait(frame)
                except Exception:
                    pass                      # slow client: drop; ring buffer covers resync
        return event

    def subscribe(self, session_id: str, *, since: int = 0) -> _Subscriber:
        sub = _Subscriber(session_id)
        with self._lock:
            subs = self._subscribers.setdefault(session_id, [])
            if len(subs) >= self.MAX_SUBSCRIBERS:
                subs.pop(0)
            subs.append(sub)
            for event in self._rings.get(session_id, ()):  # replay the gap
                if event.seq > since:
                    sub.queue.put_nowait(event.frame())
        return sub

    def unsubscribe(self, sub: _Subscriber) -> None:
        with self._lock:
            subs = self._subscribers.get(sub.session_id, [])
            if sub in subs:
                subs.remove(sub)


TRACE_BUS = TraceBus()
```

Server integration (`frontend/server.py` `Handler`; a thread per SSE client is exactly what `ThreadingHTTPServer` provides):

```python
def _handle_api_get(self, path, query):
    ...
    if path == "/api/view":
        self._json(session.projector.view())
        return
    if path == "/api/events":
        self._handle_sse(session, query)
        return
    if path.startswith("/api/trace/"):
        self._json(session.replay_journal.causal_chain(path.rsplit("/", 1)[1]))
        return
    ...

def _handle_sse(self, session, query):
    since = int((query.get("since", ["0"])[0]) or 0)
    sub = TRACE_BUS.subscribe(session.session_id, since=since)
    try:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        for frame in sub.frames():
            self.wfile.write(frame)
            self.wfile.flush()
    except (BrokenPipeError, ConnectionResetError):
        pass
    finally:
        TRACE_BUS.unsubscribe(sub)
```

Emission points (the "insights on what's happening" contract): `ConversationRouter.route`, `LiveCodexToolPlanner.plan_goal`/`chat_response` (start + finish with `model_reached`, response id, latency), `FrontierService.generate` (request + result with valid/rejected counts + `tuning_applied`), `ActionLifecycle` every transition, `SelfPlayLab` per episode, `LearningLoop` per reduction, `check_replay` per invariant run. Durable-worthy events also append to `ReplayJournal` — the bus is the live superset, replay is the training-grade subset, and both share `trace_id`/`causal_parent_id`.

### 5.5 Frontend runtime (zero-dep ES modules)

```text
frontend/static/
  index.html
  styles.css
  js/
    h.js            DOM builder (XSS-safe by construction)
    api.js          fetch client (session threading, error envelope)
    bus.js          SSE client + reconnect + poll fallback
    store.js        event-sourced store + reducer
    format.js       ts/ms/id/reward formatters
    components/     chips.js timeline.js envelope.js frontier.js actions.js
                    chat.js authority.js lab.js learning.js
    views/          operate.js observe.js learn.js lab.js authority.js
    main.js         shell, hash router, wiring
```

`js/h.js` — every dynamic string becomes a Text node; `innerHTML` does not exist in this codebase:

```js
export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') el.className = value;
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value);
    else if (key === 'value') el.value = value;
    else el.setAttribute(key, String(value));
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

export const frag = (...children) => {
  const f = document.createDocumentFragment();
  for (const c of children.flat(Infinity)) if (c) f.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return f;
};
```

`js/store.js` — the UI's replay buffer:

```js
export function createStore() {
  let view = null;          // last view_state.v2 checkpoint, patched in place
  let seq = 0;              // last applied event seq
  const traceLog = [];      // raw trace events (Observe surface reads this)
  const subs = new Set();
  let raf = 0;
  let resyncFn = null;

  const notify = () => {
    if (raf) return;
    raf = requestAnimationFrame(() => { raf = 0; for (const fn of subs) fn(); });
  };

  return {
    get view() { return view; },
    get seq() { return seq; },
    get traceLog() { return traceLog; },
    onResync(fn) { resyncFn = fn; },
    subscribe(fn) { subs.add(fn); return () => subs.delete(fn); },

    checkpoint(nextView) {
      view = nextView;
      seq = Math.max(seq, nextView?.state_version ?? 0);
      notify();
    },

    apply(event) {
      if (event.seq && event.seq <= seq) return;                 // already seen
      if (event.seq && seq && event.seq > seq + 1 && resyncFn) { // gap -> checkpoint refetch
        resyncFn();
      }
      seq = event.seq || seq;
      if (event.kind === 'patch' && view) {
        view[event.region] = event.value;
        view.state_version = event.state_version ?? view.state_version;
      } else if (event.kind === 'trace') {
        traceLog.push(event);
        if (traceLog.length > 2000) traceLog.shift();
        upsertPipeline(event);
      }
      notify();
    },
  };

  function upsertPipeline(event) {
    if (!view) return;
    view.pipeline = view.pipeline || { turns: [] };
    let turn = view.pipeline.turns.find(t => t.trace_id === event.trace_id);
    if (!turn) {
      turn = { trace_id: event.trace_id, status: 'running', stages: [] };
      view.pipeline.turns.unshift(turn);
      view.pipeline.turns = view.pipeline.turns.slice(0, 50);
    }
    const existing = turn.stages.find(s => s.stage === event.stage && s.object === event.object);
    const stageRow = { stage: event.stage, object: event.object, status: event.status,
                       ts: event.ts, payload: event.payload || {} };
    if (existing) Object.assign(existing, stageRow); else turn.stages.push(stageRow);
    if (event.status === 'failed' || event.status === 'denied') turn.status = event.status;
    else if (['commit', 'reward_recorded', 'rollback'].includes(event.stage)) turn.status = 'succeeded';
  }
}
```

`js/bus.js` — SSE with automatic poll fallback:

```js
import { api } from './api.js';

export function connectBus(store, { sessionId }) {
  let source = null;
  let failures = 0;
  let pollTimer = 0;

  const resync = async () => store.checkpoint(await api(`/api/view`));
  store.onResync(resync);

  function startSSE() {
    stopPolling();
    source = new EventSource(`/api/events?session_id=${encodeURIComponent(sessionId)}&since=${store.seq}`);
    source.onmessage = (msg) => { failures = 0; store.apply(JSON.parse(msg.data)); };
    source.onerror = () => {
      source.close();
      failures += 1;
      if (failures >= 2) startPolling();          // degraded mode: checkpoint polling
      else setTimeout(startSSE, 1000 * failures); // backoff reconnect
    };
  }

  function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(resync, 2000);
  }
  function stopPolling() { clearInterval(pollTimer); pollTimer = 0; }

  resync().then(startSSE);
  return {
    status: () => (source && source.readyState === EventSource.OPEN ? 'live' : (pollTimer ? 'polling' : 'connecting')),
    stop: () => { source?.close(); stopPolling(); },
  };
}
```

`js/api.js`:

```js
let currentSessionId = null;
export const setSession = (id) => { currentSessionId = id; };

export async function api(path, { method = 'GET', body } = {}) {
  let url = path;
  if (currentSessionId && !path.startsWith('/api/sessions')) {
    if (body) body = { session_id: currentSessionId, ...body };
    else url += `${path.includes('?') ? '&' : '?'}session_id=${encodeURIComponent(currentSessionId)}`;
  }
  const res = await fetch(url, {
    method, cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (payload.state) return payload.state;   // server returns state with errors (existing contract)
    throw new Error(payload.error || `${res.status} ${res.statusText}`);
  }
  return payload;
}
```

### 5.6 Key components

`js/components/timeline.js` — the Observe surface's core and the Operate pipeline strip:

```js
import { h } from '../h.js';
import { ms, shortId } from '../format.js';

const STAGE_LABELS = {
  route_classified: 'Route', planner_started: 'Codex plan', model_call: 'Model',
  frontier_generated: 'Frontier', tuning_applied: 'Tuning', grant_checked: 'Grant',
  simulate: 'Simulate', stage: 'Stage', commit: 'Commit', provider_write: 'Provider',
  rollback: 'Rollback', reward_recorded: 'Reward', self_play_episode: 'Self-play',
  tuning_reduced: 'Reduce', invariant_checked: 'Invariants', error: 'Error',
};

export function PipelineStrip(turn) {
  if (!turn) return h('div', { class: 'pipeline-strip empty' }, 'idle');
  return h('div', { class: `pipeline-strip ${turn.status}`, dataset: { testid: 'pipeline-strip' } },
    turn.stages.map(s => h('span', { class: `stage ${s.status}`, title: JSON.stringify(s.payload) },
      STAGE_LABELS[s.stage] || s.stage)));
}

export function TurnTimeline(turns, { onOpenTrace }) {
  return h('div', { class: 'timeline', dataset: { testid: 'turn-timeline' } },
    turns.map(turn => h('details', { class: `turn ${turn.status}`, open: turn.status === 'running' },
      h('summary', {},
        h('code', {}, shortId(turn.trace_id)),
        h('span', { class: `badge ${turn.status}` }, turn.status),
        h('button', { class: 'link', onclick: () => onOpenTrace(turn.trace_id) }, 'open trace')),
      h('table', { class: 'stage-table' },
        h('thead', {}, h('tr', {}, ['stage', 'object', 'status', 'ms', 'detail'].map(x => h('th', {}, x)))),
        h('tbody', {}, turn.stages.map(s => h('tr', { class: s.status },
          h('td', {}, STAGE_LABELS[s.stage] || s.stage),
          h('td', {}, s.object),
          h('td', {}, s.status),
          h('td', {}, ms(s.payload?.ms)),
          h('td', {}, h('code', {}, summarize(s.payload)))))))));
}

function summarize(payload = {}) {
  const keys = ['route', 'model_reached', 'valid', 'rejected', 'tuning_applied',
                'envelope_id', 'rollback_state', 'denied_reason', 'failure_mode'];
  return keys.filter(k => payload[k] !== undefined).map(k => `${k}=${payload[k]}`).join(' ') || '—';
}
```

`js/components/envelope.js` — the causal drill-down; opens from any card:

```js
import { h } from '../h.js';
import { api } from '../api.js';

const SECTIONS = [
  ['router_decision', 'Router'],
  ['codex_tool_call', 'Codex tool calls'],
  ['model_generation_rejection', 'Rejected generations'],
  ['decision', 'Frontier decision'],
  ['envelope_transition', 'Action lifecycle'],
  ['receipt', 'Swift receipts'],
  ['reward', 'Reward'],
  ['adversary_finding', 'Adversary findings'],
];

export async function openEnvelopeViewer(traceId) {
  const chain = await api(`/api/trace/${encodeURIComponent(traceId)}`);
  const overlay = h('div', { class: 'overlay', dataset: { testid: 'envelope-viewer' },
                            onclick: (e) => { if (e.target === overlay) overlay.remove(); } },
    h('div', { class: 'overlay-panel' },
      h('header', {},
        h('h2', {}, 'Causal trace ', h('code', {}, traceId)),
        h('button', { class: 'icon', onclick: () => overlay.remove() }, '×')),
      SECTIONS.map(([type, label]) => {
        const records = (chain.records || []).filter(r => r.record_type === type);
        if (!records.length) return null;
        return h('section', {},
          h('h3', {}, `${label} (${records.length})`),
          records.map(r => h('details', {},
            h('summary', {}, h('code', {}, r.record_id)),
            h('pre', {}, JSON.stringify(r.payload, null, 2)))));
      }),
      chain.envelope ? h('section', {},
        h('h3', {}, 'ActionEnvelope'),
        h('pre', { dataset: { testid: 'envelope-json' } }, JSON.stringify(chain.envelope, null, 2))) : null));
  document.body.append(overlay);
}
```

`js/components/frontier.js` — Learn surface centerpiece:

```js
import { h } from '../h.js';

export function FrontierDiff(diff, tuning) {
  if (!diff) return h('p', { class: 'muted' }, 'No tuning generations yet — run make replay-offline-tuning-loop.');
  return h('div', { class: 'card frontier-diff', dataset: { testid: 'frontier-diff' } },
    h('h3', {}, 'Tuned vs untuned frontier'),
    h('div', { class: 'diff-leaders' },
      h('div', { class: 'leader old' }, h('span', {}, 'untuned leader'), h('code', {}, diff.untuned_leader)),
      h('span', { class: `arrow ${diff.untuned_leader !== diff.tuned_leader ? 'changed' : ''}` }, '→'),
      h('div', { class: 'leader new' }, h('span', {}, 'tuned leader'), h('code', {}, diff.tuned_leader))),
    h('table', {},
      h('thead', {}, h('tr', {}, h('th', {}, 'candidate'), h('th', {}, 'Δ expected reward'))),
      h('tbody', {}, Object.entries(diff.per_candidate_delta || {}).map(([id, delta]) =>
        h('tr', {}, h('td', {}, h('code', {}, id)), h('td', { class: delta < 0 ? 'neg' : 'pos' }, delta.toFixed(3)))))),
    tuning?.bias_evidence ? h('details', {},
      h('summary', {}, 'Why the policy changed'),
      Object.entries(tuning.bias_evidence).map(([intent, ev]) =>
        h('div', { class: 'kv' },
          h('div', { class: 'k' }, intent),
          h('div', { class: 'v' }, `${ev.reward_residual} — ${ev.narrative}`)))) : null);
}

export function TaxonomyHealth(health) {
  if (!health) return null;
  const warn = (health.other_rate ?? 0) > 0.15;
  return h('div', { class: `card ${warn ? 'warn' : ''}`, dataset: { testid: 'taxonomy-health' } },
    h('h3', {}, 'Intent taxonomy health'),
    h('div', { class: 'kv' }, h('div', { class: 'k' }, 'OTHER rate'),
      h('div', { class: 'v' }, `${((health.other_rate ?? 0) * 100).toFixed(1)}%`)),
    h('div', { class: 'kv' }, h('div', { class: 'k' }, 'matched by'),
      h('div', { class: 'v' }, JSON.stringify(health.matched_by || {}))),
    warn ? h('p', { class: 'warn-text' }, 'High fallback rate: taxonomy or frontier prompt has drifted.') : null);
}
```

`js/main.js` — shell and router:

```js
import { h } from './h.js';
import { api, setSession } from './api.js';
import { createStore } from './store.js';
import { connectBus } from './bus.js';
import { OperateView } from './views/operate.js';
import { ObserveView } from './views/observe.js';
import { LearnView } from './views/learn.js';
import { LabView } from './views/lab.js';
import { AuthorityView } from './views/authority.js';

const SURFACES = {
  operate: OperateView, observe: ObserveView, learn: LearnView,
  lab: LabView, authority: AuthorityView,
};

const store = createStore();
let bus = null;

async function boot() {
  const view = await api('/api/view');
  setSession(view.session?.session_id);
  store.checkpoint(view);
  bus = connectBus(store, { sessionId: view.session.session_id });
  render();
  store.subscribe(render);
  window.addEventListener('hashchange', render);
}

function currentSurface() {
  const key = (location.hash || '#/operate').replace('#/', '');
  return SURFACES[key] ? key : 'operate';
}

function render() {
  const view = store.view;
  if (!view) return;
  const surface = currentSurface();
  const root = document.getElementById('app');
  root.replaceChildren(
    Header(view, surface),
    h('div', { class: 'shell-body' },
      Sidebar(view),
      h('main', { class: `surface surface-${surface}`, dataset: { testid: `surface-${surface}` } },
        SURFACES[surface](view, store))));
}

function Header(view, active) {
  const nav = Object.keys(SURFACES).map(key =>
    h('a', { class: `nav ${key === active ? 'active' : ''}`, href: `#/${key}`,
             dataset: { testid: `nav-${key}` } }, key[0].toUpperCase() + key.slice(1)));
  const blocked = view.runtime?.live_blockers?.length;
  return h('header', { class: 'topbar' },
    h('div', { class: 'brand-mark' }, 'CP'),
    h('nav', { class: 'surface-nav' }, nav),
    h('div', { class: 'topbar-status' },
      h('span', { class: `conn ${bus?.status() || 'connecting'}` }, bus?.status() || '…'),
      h('code', { class: 'version' }, `v${view.state_version}`),
      h('span', { class: `runtime-chip ${blocked ? 'danger' : ''}`, dataset: { testid: 'runtime-chip' },
                  title: blocked ? view.runtime.live_blockers.join('; ') : (view.runtime?.setup_notes || []).join('; ') },
        view.runtime?.mode_label || 'Fixture mode')));
}

function Sidebar(view) { /* sessions + recent runs, as today, built with h() */ }

boot();
```

`views/operate.js` (composition; chat/cards components carry over the existing card semantics and `data-testid`s — `goal-input`, `send-goal`, `candidate-card`, `commit-candidate`, `receipt-card`, `feedback-useful`, `undo-action` — unchanged for e2e continuity):

```js
import { h } from '../h.js';
import { Transcript, Composer } from '../components/chat.js';
import { ActionQueue } from '../components/actions.js';
import { PipelineStrip } from '../components/timeline.js';
import { openEnvelopeViewer } from '../components/envelope.js';

export function OperateView(view, store) {
  const activeTurn = view.pipeline?.turns?.[0];
  return [
    Transcript(view.conversation, { onOpenTrace: openEnvelopeViewer }),
    PipelineStrip(activeTurn && activeTurn.status === 'running' ? activeTurn : null),
    ActionQueue(view.actions, { onOpenTrace: openEnvelopeViewer }),
    Composer(view),
  ];
}
```

### 5.7 App shell and design tokens

`index.html` (no template element, no non-module script):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CalendarPilot</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div id="app" class="app-shell" data-testid="app-shell"></div>
  <script type="module" src="js/main.js"></script>
</body>
</html>
```

`styles.css` keeps the existing warm palette and adds cockpit tokens:

```css
:root {
  /* existing palette preserved */
  --bg: #f7f4ee; --panel: #fffdf8; --ink: #1d1a16; --muted: #6f675d;
  --line: #e3dacd; --accent: #2d5f55; --danger: #8a2f2f; --ok: #246344;
  /* cockpit tokens */
  --mono: "SF Mono", ui-monospace, Menlo, monospace;
  --stage-running: #a06b1f; --stage-succeeded: var(--ok);
  --stage-failed: var(--danger); --stage-denied: #7a4a12;
  --live: #246344; --polling: #a06b1f;
}
.topbar { display:flex; align-items:center; gap:20px; padding:12px 20px; border-bottom:1px solid var(--line); }
.surface-nav .nav { padding:6px 12px; border-radius:10px; color:var(--muted); text-decoration:none; }
.surface-nav .nav.active { background:var(--panel); color:var(--ink); box-shadow:0 4px 14px rgba(0,0,0,.05); }
.conn::before { content:'●'; margin-right:5px; }
.conn.live { color: var(--live); } .conn.polling { color: var(--polling); }
.version { font-family: var(--mono); color: var(--muted); font-size: 11px; }
.pipeline-strip { display:flex; gap:6px; padding:6px 14px; font-size:11px; font-family:var(--mono); }
.pipeline-strip .stage { padding:2px 8px; border-radius:8px; border:1px solid var(--line); }
.pipeline-strip .stage.started { color:var(--stage-running); border-color:var(--stage-running); animation:pulse 1.2s infinite; }
.pipeline-strip .stage.succeeded { color:var(--stage-succeeded); }
.pipeline-strip .stage.failed, .pipeline-strip .stage.denied { color:var(--stage-failed); }
.timeline .turn { border:1px solid var(--line); border-radius:12px; margin-bottom:10px; background:var(--panel); }
.stage-table { width:100%; font-size:12px; font-family:var(--mono); border-collapse:collapse; }
.stage-table td, .stage-table th { padding:4px 8px; border-top:1px solid var(--line); text-align:left; }
.overlay { position:fixed; inset:0; background:rgba(29,26,22,.35); display:grid; place-items:center; z-index:50; }
.overlay-panel { width:min(860px, 92vw); max-height:88vh; overflow:auto; background:var(--panel);
                 border-radius:16px; padding:20px; box-shadow:var(--shadow); }
@keyframes pulse { 50% { opacity:.45; } }
```

### 5.8 What each surface answers

| Question a dogfooder/operator asks | Surface, element |
|---|---|
| "What is it doing *right now*?" | Operate pipeline strip; Observe timeline (running stages pulse) |
| "Did the model actually run, and how long did it take?" | Observe: `model_call` stage — `model_reached`, response id, ms |
| "Why did it propose *this*?" | Candidate card → Envelope Viewer: frontier decision, reward anatomy, counterfactual, tuning applied |
| "What got rejected before I saw candidates?" | Learn: rejection counts; Envelope Viewer: `model_generation_rejection` records |
| "What authority did that write use?" | Action card grant chip; Authority surface: grant id, tier, scopes, expiry, provenance |
| "Why was it denied?" | Observe: `grant_checked` stage `denied`; Authority denial history with explanation |
| "Did learning actually change anything?" | Learn: frontier diff (leader change, per-candidate deltas) + "why the policy changed" evidence |
| "Is the taxonomy holding?" | Learn: OTHER-rate + matched-by histogram |
| "How did self-play fail this week?" | Lab: episode stream, adversary findings, release gate history |
| "Is what I'm seeing current?" | Header: connection dot (live/polling) + `state_version` |

---

## 6. Migration plan (strangler, e2e-stable)

Rule: `browser_cdp_e2e.mjs` must pass at the end of every phase; `data-testid` contracts listed in 5.6 are frozen.

| Phase | Ships | Retires | Gate |
|---|---|---|---|
| F0 | TraceBus + emission points; `/api/view` (projector wraps `build_frontend_snapshot`); `/api/events` SSE; session lock + `state_version` (2.1) | nothing | existing e2e green; new test: SSE delivers `route_classified`+`frontier_generated` for one plan turn |
| F1 | New shell (`js/` runtime) rendering **Operate** from view_state.v2; pipeline strip; legacy `app.js` deleted only when Operate reaches card parity | `app.js`, `message-template` | e2e green on new DOM; XSS audit: zero `innerHTML` in `js/` |
| F2 | **Observe** + Envelope Viewer (`/api/trace/{id}`) | inspector `debug`, `replay` tabs | new e2e: commit a candidate → open envelope viewer → assert swift receipt + rollback state visible |
| F3 | **Learn** (frontier diff, tuning provenance, taxonomy health) + **Lab** (backend selector + findings) + **Authority** | remaining inspector tabs | new e2e: run tuning loop → frontier-diff renders leader change; run self-play → findings render |
| F4 | `/api/state` marked legacy (kept for scripts/release gate until they migrate to `/api/view`) | — | release gate green end-to-end on `/api/view` |

Failure-mode parity notes carried from the current UI (behavior to preserve): offline fixture fallback (F1 re-implements it in `bus.js` resync error path), pending-POST poll (replaced by SSE, poll fallback retains it structurally), no-store headers (unchanged), viewport-bound composer (unchanged CSS contract).

---

## 7. Consolidation items (unchanged from the July 2 direction review)

Carried forward, still open, still scheduled before recommendation dogfood:

1. Land the current 34-file uncommitted diff; rerun `make dogfood-release`; merge `codex/dogfood-macos-app`.
2. Split `model_quota_exhausted` / `model_rate_limited` out of `model_tool_schema_failure`.
3. Docs collapse: 14 layered revision docs → `ARCHITECTURE`, `CONTRACTS`, `ACTING_AND_AUTHORITY`, `LEARNING_LOOP` + `docs/history/`; one dogfood authority (`dogfooding.md`); README rewritten once.
4. `runs/INDEX.md` evidence manifest; `YYYYMMDD_<gate>_<status>` naming; retention + scan rule for ad-hoc runs.
5. Repo-root decision (rename `calendar-pilot-updated 2` → `calendar-pilot`; kill copy-iteration; enables CI at root trivially).
6. Contract execution parity: `contracts/testdata/` golden vectors run by pytest against `SwiftKernelStub` and by `swift test` against `CalendarKernel`; `contract_roundtrip` command on KernelServer; string-grep parity tests retired once vectors are stable. The stub's role is **fast executable specification** (fixture tests, STUB_FAST self-play), not a production kernel — divergence must be impossible to miss, not impossible to have.
7. `.env` discovery scoped to `ROOT` + `CALENDAR_PILOT_ENV_FILE`; no import-time loading.
8. NIM/Codex transports gain hand-rolled 429/5xx backoff (no dependency).
9. EventKit bridge migrates from subprocess-per-call to the persistent JSONL protocol shared with KernelServer.

---

## 8. Build sequence

The gate that orders everything: **recommendation-system dogfooding starts at step 3.** Nothing below it may block it.

```text
1. Evidence integrity (section 2)                     ~2 days
   lock + state_version, atomic writes, append-first replay,
   root CI + evidence bundle + secret scan, concurrency regression test
2. Substrate + ML prerequisites (sections 1, 3)       ~1 week
   environment/ objects (delegating impls), TraceBus + emission points,
   intent taxonomy wired into NIM parse + reducer + tuning,
   rejection records, router_decision records, reward provenance field,
   /api/view + /api/events + frontend F0–F1 (Operate on the new runtime)
3. ── START RECOMMENDATION DOGFOOD ──                 continuous
   daily-driver protocol on EventKit, feedback on every proposal,
   tuning cadence per session/nightly, metrics gate
   (acceptance rate, edit rate, undo/regret rate, per-backend segmentation)
4. In parallel behind it                              ~2 weeks
   frontend F2–F3 (Observe, Envelope Viewer, Learn, Lab, Authority),
   conformance vectors, invariant checker in export + CI,
   self-play backend parameterization + EventKit sandbox calendar
5. After the loop produces signal
   scenario algebra, router/Codex self-play, counterfactual replay rows,
   Tier-6 plan graph with compound rollback ordering,
   right-moment as a temporal controller, tuning/frontier viewers polish
```

## 9. Definition of done

The framework is realized when:

1. Every calendar mutation is one `ActionEnvelope` whose `rollback_state` is never absent, and clicking any card shows its full causal chain.
2. A dogfooder can watch a turn move through route → plan → frontier → grant → commit live, and tell in one glance which backend served each stage.
3. `train_offline_policy.py` keys on canonical intents, the OTHER-rate is on the Learn surface, and two consecutive tuning generations show accumulating (not fragmenting) residuals.
4. Self-play runs through `ActionLifecycle` against a sandboxed backend it cannot escape, with grants it did not issue itself.
5. `check_invariants.py` passes in CI on golden replay, and a violation during dogfood is a P0 stop.
6. The frontend contains zero `innerHTML` templating, reconnects through SSE loss, and degrades to polling without losing ordering (`state_version` monotonic).
7. CI runs on every push at the git root and uploads a secret-scanned evidence bundle.
