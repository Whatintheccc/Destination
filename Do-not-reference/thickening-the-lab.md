# Thickening the Lab — from thin shell to trajectory-grade system (P11 direction spec)

The repo's next architectural direction preserves the measured split already running in `calendar-pilot-deferred-pass/`: **DiffusionGemma/NIM generates typed candidate futures, Codex inspects/compares/repairs/operates typed tools, Swift owns calendar reality/grants/writes/rollback/audit, and replay/self-play/tuning close the loop.** Progress stays falsifiable on three axes: ML improves when tuning changes future frontiers under canonical intent keys; acting improves when every mutation has an ActionEnvelope with rollback state; self-play improves when episodes run through the production lifecycle against sandboxed providers.

This document is written from three lenses at once — a systems lens (what are the objects and messages, and how do we change them without a rewrite), a control lens (what are the states, inputs, disturbances, invariants, and reachable bad states), and an RL lens (what is the policy, the reward, the trajectory distribution, and which data do we trust). The shared answer: **the central object is not the model and not the UI. It is the trajectory** — `TraceEvent + ActionEnvelope + ReplayRecord + Scorecard`.

**Relationship to the thin-lab spec (P10):** the thin lab (`thin-lab.md`, decisions D1–D24) is the *operating system for experiments* — seeds, matrix, manifests, metrics, promotion. This document is the *plant, policy, and evaluator hardening* that makes those experiments trustworthy at scale. P10's scripts and gates are prerequisites for Phases 2–5 below. Where this document and the thin-lab spec touch the same number, §1 reconciles them explicitly.

**How to read this:** §1 locks every decision this phase needs (T1–T18). §2 lists the gaps we had not considered, now filled (G1–G12) — read it even if you skip everything else, because two of those gaps (G1, G2) silently corrupt learning if unaddressed. The numbered Steps keep the original 18-step structure; each now carries **Ground truth today → Delta → Verify** so the implementing engineer knows exactly what exists, what changes, and how to prove it. All paths are relative to `calendar-pilot-deferred-pass/`. Nothing here references or depends on `Do-not-reference/`.

---

## 1. Decisions locked for this phase (T1–T18)

Change these only via a recorded entry in `experiments/DECISIONS.md`.

| # | Question | Locked decision |
|---|---|---|
| T1 | Are Python/Swift contract types *generated* from JSON schemas or *checked* against them? | **Checked, not generated.** The repo is stdlib-only and already has parity tests plus golden vectors (`scripts/run_contract_vectors.py`); codegen adds a toolchain for no marginal safety. Schema remains public truth; drift is caught by vectors and `tests/test_contract_parity.py`. |
| T2 | Which contracts get new JSON schemas? | `contracts/` today has 7 schemas (observation, candidate, receipt, grant, reward event, tool call, tool receipt). Add **three cross-runtime schemas**: `action_envelope.schema.json`, `replay_record.schema.json`, `policy_tuning.schema.json`. Lab-only artifacts (`frontier_diff`, `lab_report`, `scorecard`) get lightweight schemas under `contracts/lab/` with **no Swift mirrors** — they never cross the boundary. |
| T3 | Contract versioning mechanism? | No retrofit of version fields into every contract in one pass (pure churn). Additive-only field changes are allowed; any breaking change requires: new golden vector files, a migration note in `docs/CONTRACTS.md`, and a bump in `contracts/VERSIONS.json` (new manifest file listing each schema's version). The envelope already carries `envelope_version: "calendar_action_envelope.v2"` — that pattern extends to replay rows (G6). |
| T4 | Canonical temporal-decision vocabulary? | The **temporal controller's existing 8 modes are canonical**: `act_now`, `expose_now`, `stage_now_commit_later`, `bundle_into_digest`, `ask_for_authority_or_context`, `wait_for_context_refresh`, `wait_for_response_window`, `do_nothing` (`diffusiongemma/temporal_controller.py`). The earlier draft's 6-value list was a third, nonexistent vocabulary — do not introduce it. `RightMomentDecision` (`act_now`, `notify_now`, `wait`, `bundle_into_digest`, `silently_draft`, `auto_write_then_notify`, `ask_clarification`, `do_nothing`) stays as the upstream *scoring* decision; the controller *plan* is the actuation-facing output. Mapping table in Step 11. |
| T5 | Provider transaction contract vs today's adapters? | Formalize what the EventKit adapter already de-facto implements. Mapping: `read_observation` (exists) / `preview` ≈ `conflict_truth` (exists) / `commit` ≈ `commit_candidate` with built-in idempotency (exists) / `rollback` (exists via state + bridge) / **`verify` is the only genuinely new method** (post-commit provider readback). The base `CalendarProviderAdapter` Protocol (`providers/base.py`) is narrower than reality — widen the Protocol to the five-method contract and make deterministic + EventKit adapters conform; Google/Microsoft stubs raise `NotImplementedError` per method, never invent their own semantics. |
| T6 | Which invariants exist vs which are new? | Today `environment/invariants.py` implements **only I2 and I6**. The full set I1–I8, M1–M5, S1–S4 (Step 10) is new code. Each new check lands **soft first** (report-only, counted in scorecards), then hardens at the phase named in the Step-10 table. A check may only harden after one full batch runs with zero soft violations. |
| T7 | Is I2 adequate as "committed actions missing rollback state"? | **No — known weakness, now fixed.** `ActionEnvelope.transition()` defaults `provider.rollback_state` to `"unsupported"`, and I2 accepts `"unsupported"`, so a committed materialized write with *no rollback handle* passes today. Add **I2′ (adequacy)**: an envelope whose lifecycle reaches `commit` with a materialized write must have `rollback_state ∈ {verified, pending}`, or `impossible` only when the candidate's `reversibility == "none"`. `unsupported` on a committed write is a violation. I2 (presence/validity) stays as-is for cheap early detection. |
| T8 | Where does per-family autonomy live (Step 13 mechanism)? | New file `configs/autonomy_matrix.json`: `{canonical_intent: {"max_auto_tier": int, "personas": [...] | "all"}}`. The **Codex planner consults it before `request_commit`** (it bounds what the executive *requests*); **Swift grant validation is unchanged** (it bounds what the plant *accepts*). Two independent layers — controller constraint plus safety envelope — so a bug in one does not open the other. Promotion by action family (Phase 6) edits this file via a promotion record, never by hand. |
| T9 | How do tunings get compared against the incumbent, not just against empty? | `run_frontier_diff.py` gains `--baseline-tuning` (default: `experiments/promoted/CURRENT.json` target if present, else empty). `promote_policy.py` computes **both** candidate-vs-empty (absolute effect) and candidate-vs-CURRENT (marginal effect); gates read the marginal diff. Without this, every promotion re-proves the first tuning's wins instead of the new one's (G3). |
| T10 | Reducer data partitioning? | `train_offline_policy.py` partitions replay rows by `(runtime_mode, policy_backend)` and by `RewardEvent.provenance`. Tunings are emitted **per partition**; promotion consumes the live-policy partition only. Reward provenance enum locked: `human_ui`, `self_play_simulator`, `synthetic_demo`. Mixing weights live in a new `configs/training_weights.json`: `{"human_ui": 1.0, "self_play_simulator": 0.3, "synthetic_demo": 0.0}` (G2). |
| T11 | Simulator versioning? | `UserSimulator` as-is becomes `sim_v1` (kept for regression continuity). `sim_v2` per G1 conditions **only on seed ground truth**, never on the candidate's own predicted heads. Every manifest and self-play episode row records `simulator_version` and `simulator_seed`. Lab batches from Phase 3 onward default to `sim_v2`. |
| T12 | New replay record types and their size discipline? | Four new types: `frontier_generation`, `provider_transaction`, `tuning_reduction`, `artifact_ref` (payload sketches in Step 9). Big derived artifacts (`frontier_diff.json`, `scorecard.json`, promotion records) are **not** embedded in replay — they get an `artifact_ref` row carrying `{artifact_type, path, sha256}`. Replay stays lean; integrity stays checkable. |
| T13 | Replay row versioning and compaction rules? | Every appended row gains `record_schema_version` (start `"r1"`; absent = legacy `"r0"`). Loaders tolerate unknown versions; the reducer skips them and **reports the skipped count** (silent skips are evidence corruption). Compaction (`SessionStore` / `ReplayBuffer.save_jsonl`) may deduplicate by `record_id` only; it must never drop `envelope_transition`, denial `receipt`, `model_generation_rejection`, `adversary_finding`, or `reward` rows (G6). |
| T14 | Rate limits on actuation? | `ActionLifecycle` enforces `max_commits_per_run` (default 20, manifest-recorded). EventKit sandbox runs inherit the backend episode cap (10) and add `max_mutations_per_run = 10`. Real private-write dogfood (provider level P2, Phase 4+) adds `max_mutations_per_day = 10` persisted in the provider state file. Exceeding a cap produces a **denial receipt** (replay-visible), not an exception. New invariant I7 (G5). |
| T15 | Phase-2 thresholds vs P10 promotion gates — contradiction? | Not a contradiction once labeled: Phase-2 numbers (`valid_frontier_rate ≥ 0.90`, `rejection_rate ≤ 0.20`) are **entry bars** — the data-hygiene floor below which tuning work is wasted. The P10 numbers (`≥ 0.95`, `≤ 0.15`) remain the **promotion gates**. Entry bar admits you to the casino; promotion gate pays out. Both now live in `experiments/configs/promotion_thresholds.json` under `entry_bars` and `promotion_gates` keys. |
| T16 | Does live Codex enter the lab matrix this phase? | **No.** `live_codex` stays exercised by `make live-codex-e2e` (Gate C) only. RL-lens discipline: change one live component at a time — while frontier quality (Phase 2) is moving, adding a second live model to the matrix confounds every metric. Router behavior is still tracked via `router_decision` rows. Revisit only after Phase 3 acceptance (G10). |
| T17 | Which docs are current truth vs history (Phase 0)? | Current truth after Phase 0: `docs/ARCHITECTURE.md` (rewritten), `docs/CONTRACTS.md` (new; absorbs `API.md`), `docs/LAB.md` (new; the P10 spec copied into the repo so it is self-contained), `docs/PROVIDER_BOUNDARY.md` (new), `docs/SELF_PLAY.md` (updated), `docs/IMPLEMENTATION_MAP.md` (updated). Moved to `docs/history/` with a one-line "historical record, superseded by …" banner: `AGENT_LOOP_REVISION.md`, `NEXT_FOCUS_REVISION.md`, `FRONTEND_AND_AUTHORITY_REVISION.md`, `SAFETY_CONTRACT_PASS.md`, `SYSTEM_FRAMEWORK_IMPLEMENTATION_PASS.md`, `DEFERRED_WORK_IMPLEMENTATION_PASS.md`, `CHAT_FIRST_FRONTEND_REDESIGN.md`, `CODEX_TOOL_EXECUTIVE.md`, `ML_ACTING_SELF_PLAY_LOOP.md`, `CONTROL_SURFACES.md`, `FRONTEND_SURFACES.md` (content folded into ARCHITECTURE/CONTRACTS first). |
| T18 | Failed/crashed lab runs? | A run that dies mid-way leaves `manifest.status: "failed"` (or a dir with no finalized manifest — `--reindex` records those as `status: "corrupt"`). Failed/corrupt runs are excluded from pooled metrics, counted in batch reports, and rerun with `--force`. No resume machinery in this phase. |

---

## 2. Gaps we had not considered — now filled (G1–G12)

These are the "rational possibilities" audit. Each entry: the gap, why it bites, the mechanism that closes it.

**G1 — The user simulator is circular: self-play currently pays the policy for being confident, not for being right.** `UserSimulator.respond()` computes `p_accept` from `candidate.predicted_acceptance`, `predicted_utility`, `predicted_regret`, `predicted_interruption_cost`, `predicted_social_risk` — i.e., from the **policy's own beliefs about itself**. A policy that inflates `predicted_acceptance` gets accepted more in simulation, gets more positive reward rows, and the reducer then biases toward whatever it was overconfident about. This is reward hacking built into the harness. **Fix (`sim_v2`, T11):** acceptance draws condition only on *seed ground truth*: `profile.notification_fatigue`, `bad_response_hours` vs the candidate's `recommended_execution_time`, `preference_claims` keyword match against the candidate intent/title, attendee count (social friction), reversibility, and the perturbation's intent (e.g., `increase_notification_fatigue` variants dampen acceptance of `notify_summary`). The candidate's `predicted_*` heads are **forbidden inputs**. Calibration check in Phase 5: `sim_vs_real_acceptance_gap = |sim acceptance rate − human acceptance rate on comparable intents|`, reported per dogfood day; target < 0.15 before simulator rewards get weight > 0.3 (T10).

**G2 — Off-policy contamination: the reducer trains on undifferentiated replay.** `train_offline_policy.py` today consumes every row in a replay file with no notion of *which policy generated the behavior* (fixture heuristic vs live NIM) or *which reward source judged it* (human vs simulator). Pooling a batch (P10 §7.2) makes this worse: fixture rows can dominate live rows and the "candidate tuning" ends up tuned to the heuristic. **Fix:** partition + provenance weights (T10). The RL-lens rule on the wall: *a training row without provenance is a corrupted row.* Invariant M2/M1 make this checkable.

**G3 — Promotion compares against the wrong baseline.** `build_diff` compares tuned vs **empty** tuning. Once anything is promoted, the question is "is the new tuning better than CURRENT," not "better than nothing." Without T9, the second promotion re-credits the first promotion's gains. **Fix:** `--baseline-tuning` + marginal-effect gating (T9).

**G4 — Evaluation noise has never been measured.** Live NIM generation runs at `temperature 0.2` (retry `0.0`) — run-to-run frontier variance is unknown, so "leader changed," "reward delta 0.05," or a 3-point rejection-rate move may be noise. **Fix:** a **variance probe** before Phase 3 conclusions: `run_lab_experiment.py --repeats 10` on one seed (locked: `seed_ae_renewal_week_high_pressure`, cell B), emitting per-metric run-to-run standard deviation into `experiments/reports/variance_probe.json`. Decision rule: a live-metric delta is treated as real only if it exceeds **2× the probed std** for that metric; deltas below that are reported as "within noise." Deterministic paths (fixture, frontier scoring, diffs) have zero variance and are exempt.

**G5 — No blast-radius bound on actuation.** Authority tiers bound *what kind* of action; nothing bounds *how many*. A pathological loop could legally commit hundreds of reversible writes. Control lens: bound the reachable set in the action-count dimension too. **Fix:** rate limits + denial receipts + invariant I7 (T14).

**G6 — Replay schema evolution and compaction can silently destroy training data.** Contracts will change; old replay files will be read by new reducers; compaction rewrites files. Without row versioning and a keep-list, a schema bump or an aggressive compaction quietly deletes the denials and rejections that Steps 6 and 9 promise to preserve. **Fix:** `record_schema_version`, counted skips, compaction keep-list (T13).

**G7 — Evidence *leakage* is distinct from evidence *corruption*.** `experiments/reports/` and `experiments/index.json` are committed; real-dogfood replay contains raw titles and attendees. An imported real run's lab report must not carry raw strings into git. **Fix:** `--from-replay` imports redact free text — lab reports and index rows for imported runs contain canonical intents, counts, and metrics only; `scripts/run_secret_scan.py` runs over `experiments/reports/` inside the `lab-compare` make target and fails the command on findings. Synthetic-seed artifacts are exempt (their titles are fiction by construction).

**G8 — Timezone/DST is the classic calendar failure and nothing tests it.** The locked lab week (2026-07-06 → 07-12, `America/Los_Angeles`) contains no DST transition, so the whole corpus is blind to the bug class. **Fix now:** a receipt-echo check inside `verify` — committed events' provider-readback local times must equal the candidate program's intended local times (this lands with T5's `verify`). **Fix later (P12):** one seed variant spanning the 2026-11-01 fall-back transition; do not silently widen the corpus this phase (D24 byte-stability holds).

**G9 — Vocabulary budget (systems lens).** The system's meaning lives in a handful of closed sets: replay `record_type`s, `CanonicalIntent`, temporal modes, lifecycle transitions, `ROLLBACK_STATES`, reward provenance, self-play backends. Each must be enumerated in **exactly one module** and imported everywhere else. Adding a member to any closed set requires a `DECISIONS.md` entry plus an answer to "which invariant now covers the new member?" An unguarded vocabulary grows into the untyped blob this architecture exists to prevent.

**G10 — One-live-component-at-a-time.** Already applied as T16 for live Codex; same discipline applies to simulator upgrades (`sim_v2` enters in its own batch with everything else held fixed) and prompt bumps (`frontier_v2` is its own A/B batch, Step 16 rung 8). The manifest already records enough provenance to enforce this in review: two batches differing in more than one live field cannot be compared for promotion.

**G11 — Lab crash semantics** — see T18. The reindex must never crash on a partial dir; a partial dir must never count as evidence.

**G12 — Cost/latency provenance.** Live runs currently record wall-clock only implicitly (`ended_at − started_at`). Frontier generation adds `latency_ms` and `nim_request_count` (attempts included) to the `frontier_generation` replay row and to `lab_report.metrics`. Not gated; tracked so that prompt/model comparisons (P10 §8.6) can trade quality against cost honestly.

---

# First-principles frame

CalendarPilot is not "a calendar app with a model." It is a **closed-loop decision system**:

```text
state estimate → policy proposal → executive deliberation → constrained actuation
→ observation/reward → replay → policy update → next state estimate
```

Four roles that must never collapse into one blob:

```text
1. Plant / reality boundary: Swift + provider adapters.
2. Policy / learning: DiffusionGemma/NIM + reward/right-moment models.
3. Executive / tool operator: Codex.
4. Observer / evaluator: replay, invariants, lab, self-play, scorecards.
```

The docs already encode this split (`docs/ARCHITECTURE.md`, `docs/CODEX_TOOL_EXECUTIVE.md`): Swift accepts or rejects typed candidate programs and never asks the model whether a write is valid; DiffusionGemma owns generation, right-moment, reward scoring, biography, counterfactuals, self-play; Codex explains, asks, negotiates, repairs.

Control-lens question: what are the states, control inputs, disturbances, invariants, and reachable bad states? RL-lens question: what is the policy, the reward, the trajectory distribution, and which data do we trust? Systems-lens question: what are the objects and messages, and can we change any of them late without a rewrite?

Shared answer: the trajectory is the product substrate, and this phase is about making the trajectory **trustworthy** — complete (Step 9), typed (Step 1), bounded (Step 10, T14), honestly rewarded (G1/G2), and honestly compared (G3/G4).

# The north-star architecture

```text
CalendarPilotEnvironment
├── RuntimeAssembly       chooses fixture/live/prod backends from RuntimeProfile
├── SessionStore          atomic state, manifest, replay, state_version
├── TraceBus              live event stream; also feeds replay
├── ConversationRouter    turn → route + intent + confidence
├── FrontierService       DiffusionGemma/NIM frontier + taxonomy + rejection capture
├── CodexExecutive        typed tool plans and repair
├── ActionLifecycle       prepare → simulate → stage → commit → verify → reward → undo
├── ProviderBoundary      deterministic/EventKit/Google/Microsoft adapters behind Swift
├── ReplayJournal         append-first trajectory store
├── LearningLoop          replay → tuning → frontier diff → promotion decision
├── SelfPlayLab           scenario/adversary/runtime backend lab
└── FrontendProjector     view_state.v2 / Glass Cockpit
```

**Ground truth today** (so the strangler has a map, not a slogan):

| North-star object | Exists today as | Delta this phase |
|---|---|---|
| RuntimeAssembly | `frontend/runtime.py` (`KNOWN_MODES`, `runtime_report`, backend selection in `session.py`) | none required; keep |
| SessionStore | `environment/session_store.py` (extracted, atomic writes, compaction) | compaction keep-list + row versioning (T13) |
| TraceBus | `environment/trace.py` + `/api/events` | emit new record types (Step 9) |
| ConversationRouter | `environment/router.py` + `router_decision` rows | none; tracked only (T16) |
| FrontierService | **split across** `diffusiongemma/policy.py` and `diffusiongemma/live.py` | new façade module (Step 4) with provenance stamping; strangler-wraps both |
| CodexExecutive | `codex/tools.py` + `codex/planner.py` | consult `autonomy_matrix.json` before commit requests (T8) |
| ActionLifecycle | `environment/action_lifecycle.py` (all 7 transitions live) | `verify` provider readback (T5), rate caps (T14) |
| ProviderBoundary | `providers/base.py` Protocol (narrow) + rich de-facto EventKit/deterministic adapters | widen Protocol to 5-method transaction contract (T5) |
| ReplayJournal | `replay.py` `ReplayBuffer` (11 record types) | +4 types, versioning (T12/T13) |
| LearningLoop | `scripts/train_offline_policy.py` + `run_frontier_diff.py` + P10 `promote_policy.py` (script-level only) | partitioning (T10), baseline diff (T9), `tuning_reduction` rows; a `LearningLoop` module may wrap these scripts but **scripts remain the entry points** |
| SelfPlayLab | `diffusiongemma/self_play.py` + `environment/selfplay_backends.py` | `sim_v2` (G1), scenario files (Step 7) |
| FrontendProjector | `frontend/projector.py` (emits `view_state.v2` marker already) | render new Learn/Lab fields; no new state |

The **strangler rule** remains binding: every new object ships as a delegating wrapper over the existing code before replacing behavior, proven by the golden replay fixture (`tests/fixtures/replay_golden.jsonl`) and fixture-seed `frontier_diff` equality before/after the refactor. Future-proofing that requires a rewrite is a rewrite sink, not future-proofing.

# Step-by-step framework

## Step 1 — Freeze the core contracts before adding intelligence

Long-term debt risk is not "too little ML." It is **contract drift** between model output, Codex tools, Swift receipts, provider writes, replay rows, and lab metrics.

Canonical, versioned contracts (existing seven schemas plus T2's additions):

```text
RawCalendarObservation      CandidateCalendarAction    CodexToolCall
CodexToolReceipt            AuthorityGrant             CalendarActionReceipt
RewardEvent                 ActionEnvelope*            ReplayRecord*
PolicyTuning*               FrontierDiff†              LabReport†               Scorecard†
   * new cross-runtime schema (T2)        † lab-only schema, no Swift mirror (T2)
```

Direction (unchanged, now with mechanism): JSON schema is public truth; Python/Swift are **checked** against it (T1); golden vectors cover Python stub, Swift kernel, Swift IPC (`contracts/testdata/kernel_vectors/`, extended for the new schemas); every schema change updates vectors + `contracts/VERSIONS.json` + a migration note (T3).

Architectural rule: **no model, tool, provider, or UI code may invent an unversioned shape.**

Verify: `make contract-vectors` green; `tests/test_contract_parity.py` extended to the three new schemas; a deliberately broken vector fails CI.

## Step 2 — Treat ActionEnvelope as the plant-transition record

Ground truth: `environment/envelope.py` already carries `envelope_id, trace_id, candidate_id, observation_fingerprint, runtime_mode, backends, authority, lifecycle[], provider{}, reward{}, replay_record_ids[]`, stamps `envelope_version: "calendar_action_envelope.v2"`, and derives `rollback_state` from receipts. The lifecycle spine (`prepare → simulate → stage → commit → verify → reward → undo`) is implemented in `action_lifecycle.py`, each transition appending a replay record.

Delta this phase:

- **I2′ adequacy** (T7): committed materialized writes may not sit at `rollback_state: "unsupported"`. This is the real "no committed action without rollback coverage" guarantee; today's I2 only checks the field is present and valid.
- `observation_fingerprint` gets one canonical constructor: `fingerprint = _digest(observation.to_dict(), "obsfp")` (reuse the envelope's `_digest` helper — sha1, 12 hex chars, prefixed). `FrontierService` computes it once per generation; lifecycle and training rows reference it (feeds M2).
- Rate caps enforced at `commit` (T14): the cap check emits a denial receipt and a `commit` transition with `status: "denied", detail: {"denied_reason": "mutation_cap_exceeded"}` — bounded and replay-visible, never an exception.

Debt-avoidance rule stands: **no acting path may return only a receipt; every acting path returns or references an ActionEnvelope.** That includes UI commits, Codex tool commits, self-play commits, EventKit sandbox commits, future Google/Microsoft commits, and replay rehydration.

Verify: golden replay still passes I2 and I6; a synthetic fixture with a committed-write envelope at `unsupported` fails I2′; cap-exceeded fixture produces the denial receipt row.

## Step 3 — Make Swift the deterministic plant and provider boundary

Control lens: Swift is the plant controller and safety envelope. It must not become a policy learner, and the model must not become the plant.

Invariant (unchanged): Python/Codex/DiffusionGemma propose and request; Swift decides whether calendar reality changes; provider tokens stay behind Swift/provider adapters.

Module split — ground truth is closer than the draft implied. The Swift package already separates contracts (`CalendarContracts.swift`), kernel (grant registry, broker, materializer, undo ledger), the JSONL server (`CalendarPilotKernelServer`), and the EventKit bridge (separate `CalendarPilotEventKitBridge` target). The delta is **naming and boundaries, not new code**: keep the four-module shape (`CalendarContracts` / `CalendarKernel` / `CalendarProviderBridge` / `CalendarKernelServer`) as target names when files move for other reasons; do not reorganize for its own sake.

Provider transaction contract (T5 — formalizing the de-facto EventKit surface):

```text
read_observation(window)                       -> provider truth
preview(action_packet, idempotency_key)        -> conflict/provider preview      (≈ conflict_truth today)
commit(prepared_action)                        -> external IDs + rollback handle (≈ commit_candidate today)
verify(receipt)                                -> provider readback              (NEW — includes G8 local-time echo)
rollback(rollback_handle)                      -> rollback receipt               (exists)
```

Debt-avoidance rule: **provider differences belong behind this one transaction interface.** Google/Microsoft adapters conform or raise; they never invent commit/rollback semantics.

Verify: deterministic + EventKit adapters pass a shared conformance test (`tests/test_deterministic_provider.py` / `test_apple_eventkit_provider.py` extended); `verify` readback asserted in the cell-D runbook checks (P10 §9).

## Step 4 — Split learning into policy, reward, timing, and update

"The ML system" is at least four policies/models:

```text
1. Frontier policy:            what futures to propose.
2. Reward/value model:         what tradeoffs matter.
3. Right-moment/temporal policy: when to expose, stage, or act.
4. Update rule:                how replay changes the next policy.
```

Ground truth: `reward.py`, `right_moment.py` + `temporal_controller.py` are already separate; generation is split across `policy.py` (heuristic) and `live.py` (NIM); the update rule lives in `train_offline_policy.py`.

Delta: a thin **`FrontierService`** façade (new module `diffusiongemma/frontier_service.py`) that owns: backend selection (fixture policy vs NIM client), intent normalization at parse time (Step 5), rejection capture, and **provenance stamping** — emitting one `frontier_generation` replay row per call with the minimum observable provenance:

```text
model, prompt_version, decoding parameters, runtime mode,
observation fingerprint, policy_tuning_id, valid/rejected counts,
canonical intent distribution, attempts, latency_ms (G12)
```

`DiffusionGemmaPolicy.generate_candidates` and `NvidiaNIMPolicyClient` keep their signatures; the façade wraps (strangler), and `run_lab_experiment.py` calls the façade.

Debt-avoidance rule: **a policy may use a model internally, but its observable output is a typed contract plus provenance.** M1/M2 make the absence of provenance a counted violation.

## Step 5 — Canonicalize intent and action semantics as early as possible

The lab already locks the 11-value canonical vocabulary and forbids expectation labels outside it (P10 D5). This is RL data hygiene, not bookkeeping: if model prose becomes the training key, residuals fragment forever (`"prepare for client call"` / `"create prep block"` / `"protect renewal call"` are one learning signal).

Delta: normalization moves to **frontier parse time** inside `FrontierService` — every candidate carries `intent` (canonical) + `intent_raw` + `intent_matched_by` from `taxonomy.normalize_intent` before it reaches scoring, replay, or the executive. `OTHER` rate remains the drift metric; promotion keeps its ≤ 0.10 gate.

Debt-avoidance rule: **free text can be evidence, never a primary training key.** (G9 applies: `CanonicalIntent` is a closed set with one home module.)

## Step 6 — Preserve invalid model output as learning data

A model-generated invalid action is a trajectory event, not trash. Ground truth: `live.py` already captures rejection reasons (`skipped_non_object_candidate`, `skipped_invalid_candidate`, `duplicate_candidate_id`, `skipped_candidate_without_actions`, `missing_target_calendars` — the last marked recoverable) and the lab retains `valid_candidates.jsonl` + `model_generation_rejections.jsonl`.

Two precise definitions the draft left open:

- **Retry ≠ repair.** The NIM client's second attempt (stricter decoding) is a *new generation attempt*, recorded via `attempt` index in the `frontier_generation` row and on each rejection row. **Item repair** (fixing a specific rejected item, e.g. backfilling `missing_target_calendars`) does not exist today; if implemented, it must emit a `repair` field on the rejection row and count separately. Never silently repair model output.
- `repair_salvage_rate = repaired-and-accepted items / recoverable rejections` — reported as `null` until an item-repair path exists (an honest null beats a fake zero). `empty_frontier_rate = live runs with 0 valid candidates / live runs`.

Metrics set: `valid_frontier_rate`, `model_generation_rejection_rate`, `duplicate_candidate_rate`, `repair_salvage_rate`, `OTHER_intent_rate`, `empty_frontier_rate` — formulas per P10 §6 conventions (run-level vs item-level pooling per D10).

## Step 7 — Treat self-play as a laboratory, not a side path

Ground truth: `SelfPlayRunner` already generates the frontier, previews adversarial penalties, chooses robust candidates, simulates responses, records named failure modes (`social_conflict`, `notification_fatigue`, `undo_regret`, `engagement_over_utility`, `denied_actuation`), and routes non-stub episodes through `ActionLifecycle` with backend grant policy (`environment/selfplay_backends.py`: `stub_fast → self_issued`, `swift_ipc_deterministic → kernel_issued_sandbox`, `swift_ipc_eventkit_sandbox → kernel_issued_sandbox`, `production_shadow → read_only`).

Debt-avoidance rule stands: **a self-play backend is not just an actuation target; it includes a grant-issuance policy.** That is what prevents a lab harness from self-issuing real write authority.

Deltas, in order:

1. **`sim_v2`** (G1/T11) — the highest-leverage change in this entire document. Self-play reward must come from seed ground truth, not the policy's self-assessment.
2. **Scenario files, not a DSL.** A scenario is a *composition*, not a new calendar format: `experiments/scenarios/<name>.json` = `{scenario_id, seed_id, disturbances: [perturbation names], adversaries: [...], simulator_version, invariant_assertions: [...]}` referencing existing seeds and the P10 perturbation catalog. The seven named scenarios (`external_call_no_prep_high_fatigue`, `dense_day_with_flexible_hold`, `social_conflict_move_meeting`, `stale_observation_after_provider_refresh`, `high_engagement_low_utility`, `undo_regret_after_auto_write`, `expired_authority_grant`) are compositions over the 20-seed corpus. A richer DSL waits until these files feel cramped (systems lens: simple things simple).
3. **Scenario invariant assertions map to the Step-10 set** — `no social write without scope` → I3; `do_nothing remains available` → new frontier check (the frontier must always contain a `do_nothing` candidate — add to L7's sibling checks); `rollback handle exists if committed` → I2′; `stale observation refreshed or denied` → I4; `denials enter replay` → I5.

## Step 8 — Use the lab as the experiment operating system

Unchanged from P10 and deliberately so: file-backed `experiments/` tree, matrix cells A–D, promotion thresholds, and the rule **expectation failures are data; infrastructure failures are failures** (D20). Additions from this document: entry bars vs promotion gates live side-by-side in the thresholds file (T15); variance probe before trusting live deltas (G4); failed/corrupt run semantics (T18); secret scan in `lab-compare` (G7).

## Step 9 — Make replay the single source of truth for learning and debugging

Replay is the trajectory distribution; if it is incomplete, training is contaminated.

Ground truth record types (11): `decision`, `receipt`, `candidate_receipt`, `reward`, `self_play_episode`, `adversary_finding`, `codex_tool_call`, `codex_tool_receipt`, `router_decision`, `model_generation_rejection`, `envelope_transition`.

New types (T12) with payload sketches and emitters:

```text
frontier_generation   emitter: FrontierService, one per generation call
  {observation_fingerprint, goal, backend, model, prompt_version, decoding,
   attempts, valid_count, rejection_count, intent_distribution, latency_ms, health_status}

provider_transaction  emitter: ActionLifecycle around provider calls
  {provider_id, op: preview|commit|verify|rollback, idempotency_key,
   external_event_id?, provider_transaction_id?, status, error?}

tuning_reduction      emitter: train_offline_policy at reduction time
  {tuning_id, source_replay_paths, partitions, row_counts, skipped_row_versions,
   mapped_findings, unmapped_findings, waived_findings}

artifact_ref          emitter: any script that writes a derived artifact
  {artifact_type: frontier_diff|scorecard|lab_report|promotion_record, path, sha256}
```

Debt-avoidance rule (two halves): **if it can change future policy, it must be in replay; if it is in replay, it must have `trace_id` and `causal_parent_id`** — and now also `record_schema_version` (T13). Big artifacts enter by reference, not by value (T12), so the journal stays appendable and diffable.

This keeps debugging, UI, training, and promotion as different views of one trajectory.

## Step 10 — Encode invariants as executable trace monitors

Ground truth: only I2 (presence) and I6 exist in `environment/invariants.py`. Everything else below is new code. Each check states its predicate, what it scans, its prerequisite, and when it hardens (T6). "Hard" = promotion-blocking; "soft" = counted in scorecards.

| id | predicate (scans) | prerequisite | hardens |
|---|---|---|---|
| I1 | every `provider_transaction` with `op: commit` has exactly one owning envelope (join on trace) | `provider_transaction` rows | Phase 4 |
| I2 | commit/verify/undo envelopes have `rollback_state ∈ ROLLBACK_STATES` (exists today) | — | hard now |
| I2′ | committed materialized writes: `rollback_state ∈ {verified, pending}` or `impossible` with `reversibility == "none"` (T7) | — | Phase 1 |
| I3 | social-scope mutations carry grant id whose scopes include the social scope (envelope `authority` vs receipt) | — | Phase 1 |
| I4 | commit transitions include provider-truth check detail (`provider_conflict_truth` present) or denial | `verify`/preview details | Phase 4 |
| I5 | every denial receipt has a replay row (exists structurally; check counts receipts vs rows) | — | Phase 1 |
| I6 | undo handle consumed at most once (exists today) | — | hard now |
| I7 | commits per run ≤ manifest cap; cap-exceeded produced denial receipts, not silence (G5/T14) | rate caps | Phase 4 |
| I8 | committed events' provider-readback local times match candidate intent (G8) | `verify` op | Phase 4 |
| M1 | every frontier candidate row carries `policy_backend + prompt_version + model` | FrontierService | Phase 2 |
| M2 | every training row carries `observation_fingerprint` | fingerprint constructor | Phase 2 |
| M3 | every tuning: each `intent_reward_bias` key has `bias_evidence` citing ≥1 replay record id; each `failure_penalties` key traces to `adversary_finding` ids | `tuning_reduction` rows | Phase 3 |
| M4 | every live run has one `frontier_generation` row with explicit `health_status` (NIM fallback never implicit) | FrontierService | Phase 2 |
| M5 | Σ rejection rows == Σ `rejection_count` in `frontier_generation` rows; skipped-version counts reported (T13) | — | Phase 2 |
| S1 | `self_play_episode` rows with backend ≠ `stub_fast` reference `envelope_transition` rows in-trace | — | Phase 3 |
| S2 | episodes with provider writes: backend policy sandbox + sandbox calendar id on every `provider_transaction` | `provider_transaction` rows | Phase 4 |
| S3 | every failure mode in replay is mapped in `failure_penalties` **or** listed in `waived_findings` with a reason (accounted-for, not force-penalized) | `tuning_reduction` rows | Phase 3 |
| S4 | every autonomy/tuning promotion record contains before/after frontier diffs (P10 §7.2 shape) | promote_policy | Phase 3 |

Run invariant checks at: replay export, lab run completion, promotion attempt, CI (golden fixture), dogfood release, provider sandbox run.

Debt-avoidance rule: **a new autonomy tier, provider, or vocabulary member cannot ship without naming its invariant** (G9).

## Step 11 — Design right-moment as a temporal control policy

Right-moment is a controller over exposure, staging, commit timing, and authority refresh — not a field on a candidate.

Ground truth and vocabulary reconciliation (T4): the controller exists (`RightMomentTemporalController.plan`) and its **8 modes are canonical**. The upstream scoring decision (`RightMomentDecision`) maps into plan modes:

```text
RightMomentDecision (scoring)      →  TemporalControlPlan.mode (actuation-facing)
act_now / auto_write_then_notify   →  act_now
notify_now                         →  expose_now
silently_draft                     →  stage_now_commit_later
bundle_into_digest                 →  bundle_into_digest
ask_clarification                  →  ask_for_authority_or_context
wait                               →  wait_for_response_window | wait_for_context_refresh (staleness ≥ 0.4)
do_nothing                         →  do_nothing
```

Inputs stay as implemented: candidate value, interruption cost, fatigue, response windows, focus mode, urgency, staleness risk, authority expiry, provider conflict risk, social risk.

Debt-avoidance rule: **separate "what to do" from "when/how to expose or execute it."** Otherwise the system learns "prep blocks are bad" when the truth was "the prep-block suggestion was delivered at 9 pm." Lab hook: `top_candidate_right_moment_decision` is already recorded per run (P10 §6); Phase 3 adds the plan mode alongside it so timing-vs-content failures are separable in the failure dashboard.

## Step 12 — Keep Codex as executive, not policy and not plant

Ground truth already enforces the boundary (Swift-issued `AuthorityGrant`, grant-id-only tool calls, embedded grants ignored, `confirmed_by_user` required for commit/undo). Codex owns: conversation, route interpretation, tool sequencing, candidate comparison, explanations, authority negotiation, profile repair proposals, denial repair, undo requests. Codex does not own: reward optimization, provider credentials, authority truth, rollback ledger, training updates, schema repair without replay.

Delta this phase: the planner consults `configs/autonomy_matrix.json` before `request_commit` (T8) — the executive's requests become curriculum-bounded per intent family while Swift's validation stays untouched underneath.

Debt-avoidance rule: **Codex can request, never confer, authority.**

## Step 13 — Stage autonomy as a curriculum, not a switch

Curriculum gates per tier stand as drafted (Tier 1 recommend → Tier 6 compound optimizer), with the mechanism now concrete: promotion happens **by canonical-intent family × persona family**, recorded in a promotion record, applied by editing `configs/autonomy_matrix.json` (T8). A policy may be ready for `create_prep_block` on account-executive seeds and not for `move_meeting` on executive-assistant-dense calendars — the matrix encodes exactly that, and S4 requires the before/after diffs.

Tier-5 social and Tier-6 compound (plan graph exists in `environment/plan_graph.py`; `auto_apply_plan` stays kernel-denied) remain out of scope for actuation this phase; shadow-scoring social candidates in self-play is allowed (findings only, no writes — S2 enforces).

## Step 14 — Build provider maturity in layers

```text
P0 deterministic provider          (done)
P1 EventKit sandbox                (this phase — P10 cell D + Phase 4)
P2 EventKit real private reversible writes (entry criteria below)
P3 Google/Microsoft sandbox
P4 multi-provider read truth
P5 multi-provider conflict resolution
P6 social actuation sandbox
```

Per-level evidence requirements stand: `external_event_id`, `idempotency_key`, `provider_transaction_id`, `rollback_handle`, `rollback_state`, `verify` result, `provider_error` replay row, sandbox containment evidence.

**P2 entry criteria (new — the scary level needs explicit guards):** P1 green on both designated seeds twice consecutively; writes restricted to an env-configured allowlist of calendar ids; `tier3_private` intents only per the autonomy matrix; `max_mutations_per_day = 10` (T14); undo verified in-session for the first 20 real writes; I7 + I8 hard.

Debt-avoidance rule: **no provider path is production-ready until rollback and idempotency are demonstrated** — and now also *bounded* (rate caps) and *verified* (readback).

## Step 15 — Make the Glass Cockpit a replay reader, not a second app state

Ground truth: `FrontendProjector` already emits `view_state.v2`; `/api/view`, `/api/events`, `/api/trace/{trace_id}` exist; the ES-module frontend renders Operate/Observe/Learn/Lab/Authority.

Delta: Learn surface renders `frontier_generation` provenance and taxonomy health; Lab surface renders scenario files and `simulator_version`; Envelope viewer follows `artifact_ref` rows to derived artifacts.

Debt-avoidance rule: **the UI must not derive hidden truth — it renders `view_state.v2` and TraceEvents.** Acceptance is mechanical: the frontend fetches nothing but `/api/view`, `/api/events`, `/api/trace/*`, and static assets.

## Step 16 — Formalize policy updates as conservative RL

CalendarPilot's learning problem is high-variance, delayed-feedback, partially observed, and action-constrained. Do not jump to opaque online RL. The ladder, with the previously missing rungs made operational:

```text
0. Heuristic policy baseline                      (cell A)
1. Live frontier generation w/ rejection tracking  (cell B, M4/M5)
2. Replay reducer → small PolicyTuning             (partitioned — T10/G2)
3. Tuning changes ranking/timing in frontier diffs (P10 D12)
4. Self-play adds adversarial penalties            (sim_v2 — G1; S3 accounting)
5. Human feedback adds observed rewards            (provenance human_ui, weight 1.0)
6. Shadow evaluation: candidate vs CURRENT         (T9/G3 — marginal diffs on the seed matrix)
7. Promotion only through scorecard gates          (P10 §7; variance rule G4)
8. Larger policy/model changes → A/B seeded batches (two batches, same sha, one changed field — G10)
```

`PolicyTuning` is a constrained policy-improvement layer, not policy-gradient training. That is a feature: it is legible, citable (M3), and reversible (CURRENT pointer). Keep it that way until the ladder's lower rungs are boringly green.

Debt-avoidance rule: **no policy update is accepted unless its marginal effect is visible in frontier_diff against the incumbent and its evidence is cited to replay.** "We trained something" is not "the policy improved on these trajectories."

## Step 17 — Define evaluation as multi-objective, not scalar reward worship

Reward heads stay decomposed (`configs/reward_weights.json`: acceptance, utility, engagement, long-horizon, regret, interruption, social risk, undo, ignored, explicit-wrong). Report scalar *and* heads, plus rollback coverage.

The three failure conditions become executable promotion checks in `promote_policy.py` (pooled, candidate-vs-CURRENT):

```text
engagement_gaming:  Δengagement > +0.05 AND Δutility < +0.01 AND (Δregret > 0 OR Δinterruption > 0)
social_creep:       Δsocial_risk > 0 without a new explicitly scoped social grant in the batch
regret_regression:  pooled undo_regret findings per episode rise > 20% after tuning
```

Any one ⇒ decision `hold` with the failing condition named in the promotion record.

Debt-avoidance rule: **engagement can be a feature, never the uninspected objective.**

## Step 18 — Use seeded lab results as regression tests, not demos

The regression pyramid for every future change, cheapest first:

```text
5-seed smoke matrix (cells A+B)      → every substantive PR
20-base-seed matrix (A/B/C)          → weekly + before any promotion
flagged-seed D12 matrix              → every tuning candidate
provider sandbox matrix (cell D)     → provider-touching changes
real dogfood import + shadow seed    → daily during dogfood phases
variance probe                        → after any live model/prompt/decoding change (G4)
```

Scored on the P10 §6 columns plus `sim_vs_real_acceptance_gap` (G1) and cost/latency (G12).

Debt-avoidance rule: **a seed failure is not a bug by default; a silent metric regression is.**

---

# Concrete next-phase roadmap

Dependencies: Phase 0 ∥ Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6. P10 (thin lab) scripts must exist before Phase 2; the variance probe (G4) runs at the start of Phase 3.

## Phase 0 — Architecture freeze and living docs

Deliver: `docs/ARCHITECTURE.md` rewritten as current truth; `docs/CONTRACTS.md` (schemas + vectors + migration policy + `contracts/VERSIONS.json`); `docs/LAB.md` (P10 spec copied in-repo); `docs/PROVIDER_BOUNDARY.md` (T5 contract); history moves per T17.

Acceptance (checkable): no doc outside `docs/history/` contradicts another on tier semantics, provider state, or frontend; every history doc carries its banner; `grep -r "Do-not-reference" docs/` is empty.

## Phase 1 — Stabilize the trajectory spine

Deliver: three new cross-runtime schemas + vectors (T2); I2′/I3/I5 implemented (I1/I4/I7/I8 stubs report-only); `record_schema_version` on append (T13); compaction keep-list test; `artifact_ref` emission from existing scripts.

Acceptance: golden replay green under old + new checks; synthetic violation fixtures fire each new check exactly once; a compaction round-trip preserves every keep-list row; `/api/trace/{trace_id}` shows a complete causal chain including `artifact_ref` rows for one demo run.

## Phase 2 — Frontier quality and ML data hygiene

Deliver: `FrontierService` façade with provenance + parse-time canonicalization (Steps 4–5); M1/M2/M4/M5 hardened; rejection taxonomy report; full 20-base-seed A/B matrix; reducer partitioning (T10) with `tuning_reduction` rows.

Acceptance (entry bars, T15): `valid_frontier_rate ≥ 0.90`, `model_generation_rejection_rate ≤ 0.20`, `OTHER_intent_rate ≤ 0.10`, `expected_intent_hit ≥ 0.80` on base seeds, zero hard-invariant violations, `empty_frontier_rate` reported. **Do not tune further until invalid output is below the entry bar** — tuning on garbage frontiers optimizes the garbage.

## Phase 3 — Self-play learning effect

Deliver: `sim_v2` behind `simulator_version` (T11, own batch per G10); variance probe report (G4); D12 diagnostic batch; S1/S3/S4 + M3 hardened; adversary-to-intent mapping with `waived_findings`.

Acceptance: `failure_penalties` non-empty; ≥1 flagged seed shows `per_candidate_delta < 0` on a penalized intent **beyond the variance rule**; promotion produces a promote-or-hold record with named gates; `sim_v1 → sim_v2` acceptance-rate shift documented in the batch report (expected: overconfident intents lose reward).

## Phase 4 — Provider sandbox and private-write curriculum

Deliver: `verify` readback (T5) incl. local-time echo (G8); rate caps + I7 (T14); I1/I2′/I4/I8/S2 hard; cell D green on both designated seeds twice; P2 entry checklist (Step 14) evaluated.

Acceptance: external IDs present; rollback verified; idempotency suppresses duplicates; zero outside-sandbox mutations; provider errors are replay rows; cap-exceeded test yields a denial receipt. Only after this does real private-calendar dogfood proceed.

## Phase 5 — Real dogfood with seeded shadow

Deliver daily (P10 §10 procedure): real replay import (redacted per G7) + mapped shadow seed run + feedback events + partitioned tuning + marginal frontier diff + scorecard + promotion attempt; `sim_vs_real_acceptance_gap` reported.

Acceptance: feedback maps to `RewardEvent` kinds; real + shadow rows comparable in one table; day-2 frontier change attributable to day-1 feedback in `bias_evidence` (M3); no secret-scan findings in committed reports; simulator gap < 0.15 or simulator weight stays ≤ 0.3.

## Phase 6 — Autonomy promotion by action family

Promote one family at a time via the autonomy matrix (T8): `create_prep_block` → `add_buffer` → `protect_deep_work` → `batch_admin` → `move_meeting` (private flexible only) → social shadow only → `auto_apply_plan` sandbox only. Each family promotion cites seed pass rate, self-play pass rate, provider sandbox pass rate, human feedback pass rate, rollback pass rate — and lands as a promotion record editing the matrix, with S4 diffs and a rollback plan (revert the matrix entry).

---

# Design rules to keep on the wall

```text
 1. The trajectory is the product substrate.
 2. Swift owns reality; models own proposals.
 3. Codex requests operations; it never mints authority.
 4. Every model output is typed, rejected, or repaired visibly.
 5. Every mutation has an ActionEnvelope — and a rollback state that means something (I2′).
 6. Every policy update cites replay, and beats the incumbent, not the empty baseline.
 7. Every autonomy increase has before/after frontier diffs, per intent family.
 8. Every provider write is idempotent, rollback-aware, verified, and rate-bounded.
 9. Every self-play backend declares grant policy; every simulator declares its version —
    and the simulator may never grade the policy on the policy's own beliefs.
10. Every UI surface reads the same trace the learner trains on.
11. Every closed vocabulary has one home module; growing it names its invariant. (G9)
12. Measure your noise before you believe your deltas. (G4)
13. A training row without provenance is a corrupted row. (G2)
```

# The shortest useful direction statement

Build CalendarPilot as a **controlled RL system over typed calendar actions**:

```text
DiffusionGemma proposes typed futures.
Codex operates the typed executive path.
Swift validates and materializes reality.
Trace/Envelope/Replay record the trajectory.
Self-play perturbs the trajectory distribution — graded by ground truth, not self-belief.
PolicyTuning updates the next frontier — judged against the incumbent.
The Lab proves whether the update helped — beyond measured noise.
```

This prevents the four debts (the draft named three; G1 adds the fourth):

```text
model debt:      untyped/free-text outputs becoming training truth
acting debt:     provider writes bypassing receipts/rollback/invariants/caps
experiment debt: runs that cannot be compared or reproduced
evaluator debt:  simulators and baselines that flatter the policy instead of testing it
```

The next build is not "more features." It is **trajectory integrity + frontier quality + honest evaluation + self-play effect + provider sandbox**, in that order.

---

# P11 blocker-fix progress — 2026-07-03

## P11 Step 13 — Dogfood Release

Progress:
- Fixed the macOS app build launcher so `scripts/build_macos_app.sh` is directly executable and its shebang is the first byte in the file.
- Verified `make mac-app-build` succeeds and creates `dist/CalendarPilot.app`.

Evidence:
- `scripts/build_macos_app.sh` now has executable mode in the working tree.
- `make mac-app-build` completed successfully on 2026-07-03.

Remaining:
- Rerun the full `make dogfood-release` gate after the other blockers are addressed, because that target also exercises browser, Swift IPC, LaunchServices, occupied-port, artifact validation, and release secret scans.

## P11 Steps 5/10 — Seed Corpus and Lab Matrix

Progress:
- Materialized the locked 20-seed corpus through `scripts/seed_calendar_corpus.py --write-base-seeds`.
- Verified `make lab-validate-seeds` now passes instead of returning `no seed files found`.
- Ran a five-seed fixture smoke matrix and a full 20-base-seed fixture matrix with `sim_v2`, `stub_fast`, and three episodes per seed.

Evidence:
- `experiments/seeds/*.json` now contains the 20 base seed files.
- `experiments/reports/p11_fix_smoke_20260703_comparison.json` has 5 completed rows.
- `experiments/reports/p11_fix_base20_20260703_comparison.json` has 20 completed rows.
- The 20-seed fixture matrix reported `valid_frontier_rate=1.0`, `model_generation_rejection_rate=0.0`, `expected_intent_hit_rate=0.85`, `invariant_violations_max=0`, and `bad_intent_committed=0`.

Remaining:
- `OTHER_intent_rate=0.1081` on the 20-seed fixture matrix, slightly above the 0.10 entry/promotion bar, so frontier taxonomy quality still needs tightening before promotion can be considered clean.

## P11 Steps 2/4/9 — Strict Replay, Schema, and Artifact References

Progress:
- Added a strict replay row-shape invariant (`R1`) that fails rows missing `record_schema_version`, `record_id`, `trace_id`, or `causal_parent_id`.
- Updated replay writing so new root rows use `causal_parent_id="ROOT"` instead of `null`.
- Updated `contracts/replay_record.schema.json` and the golden replay fixture to require an explicit causal parent and `record_schema_version="r1"`.
- Added provider preview replay logging as a `provider_transaction` in `ActionLifecycle`.
- Added lab postprocessing `artifact_ref` rows for invariant report, offline policy report, policy tuning, frontier diff, scorecard, and lab report.

Evidence:
- `make check-invariants` passes on `tests/fixtures/replay_golden.jsonl`.
- The previous missing-version negative fixture now fails with `R1`.
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_replay.py' -v` passes.
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_action_lifecycle_and_store.py' -v` passes and checks preview/commit/verify provider transaction rows.
- Fresh lab probe `experiments/runs/p11_replay_strict_probe/replay.jsonl` has 38 rows, 0 missing schema versions, 0 missing parents, 6 `artifact_ref` rows, and strict invariant status OK.

Remaining:
- Existing historical run artifacts generated before this fix may still contain legacy/root-null rows; rerun affected batches rather than treating old evidence as strict P11 evidence.

## P11 Step 11/16 — CURRENT Incumbent and Marginal Promotion

Progress:
- Added an explicit empty incumbent policy tuning at `experiments/promoted/policy_tuning_baseline_empty_v1.json`.
- Added `experiments/promoted/CURRENT.json` pointing to that incumbent so frontier diffs no longer fall back to an unnamed empty baseline.
- Updated `scripts/promote_policy.py` so flagged leader changes and self-play penalty effects use marginal diff fields against CURRENT when available.

Evidence:
- `make frontier-diff` now reports `baseline_tuning_id=baseline_empty_v1`.
- `scripts/promote_policy.py --batch p11_fix_base20_20260703` wrote `experiments/reports/promotion_p11_fix_base20_20260703.json` and held with exit code 3.
- The promotion record includes 20 source runs and 20 frontier diff artifacts under `experiments/reports/promotion_p11_fix_base20_20260703/`.

Remaining:
- Promotion still correctly holds: `OTHER_intent_rate=0.1081 > 0.10`, `flagged_seed_leader_changes=0 < 3`, and `self_play_penalty_effect` is absent.

## P11 Steps 7/8 — Self-play Scenarios, Variance, and Grant Policy

Progress:
- Added seven adversarial `sim_v2` scenario specs under `experiments/scenarios/`, covering external-call prep pressure, dense-day holds, social conflicts, stale provider observations, high-engagement/low-utility traps, undo regret, and expired authority grants.
- Added `scripts/validate_self_play_scenarios.py` and the `make lab-validate-scenarios` access point so the scenario corpus fails closed when a seed, disturbance, adversary, invariant assertion, or simulator version is missing.
- Added `scripts/run_variance_probe.py` and the `make variance-probe` access point to record repeated fixture frontier variance.
- Added self-play replay evidence for backend grant policy, including backend, grant issuance, provider-write permission, episode cap, and required environment flag.
- Exported `UserSimulator` from `calendar_pilot.diffusiongemma` so self-play callers and tests can use the package entrypoint.

Evidence:
- `make lab-validate-scenarios` passes with 7 scenario files.
- `make variance-probe` wrote `experiments/reports/variance_probe.json`.
- The fixture variance probe ran 10 repeats with `valid_candidates` mean 14.0/stddev 0.0, `top_expected_reward` mean 2.324/stddev 0.0, and `OTHER_intent_rate` mean 0.0714/stddev 0.0.
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_self_play.py' -v` passes and verifies replayed `simulator_version="sim_v2"` plus `backend_grant_policy.backend="stub_fast"` and `grant_issuance="self_issued"`.

Remaining:
- The UI Lab path still needs to be wired away from `sim_v1` and verified through the app surface.
- Promotion still needs self-play penalty-effect evidence across the promoted batch, not only one focused replay unit test.

## P11 Step 12 — Live NIM Replay-offline Tuning Loop

Progress:
- Hardened `scripts/run_replay_offline_tuning_loop.py` so live NIM schema failures in self-play, untuned frontier generation, or tuned frontier generation write controlled evidence instead of surfacing as raw tracebacks.
- The failure path now writes `nim_schema_failure.json` and a stage-specific `nim_schema_failure_<stage>.json`, appends a `model_generation_rejection` replay row with `causal_parent_id="ROOT"`, saves the replay, and exits with the named schema-failure code.
- Added a regression test for the failure artifact and strict replay row shape.

Evidence:
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_replay_offline_tuning_loop.py' -v` passes.
- `PYTHONPATH=src python3 -m py_compile scripts/run_replay_offline_tuning_loop.py` passes.
- `make replay-offline-tuning-loop` now passes live end-to-end and writes artifacts under `runs/replay_offline_tuning_loop/artifacts`.
- The live loop reported `tuning_had_effect=true`, `leader_changed=true`, untuned leader `cand_001_prep_focus`, tuned leader `cand_002`, and `tuning_control_notes_present=true`.

Remaining:
- None for the invalid-frontier-JSON blocker; the loop now has both controlled failure evidence and a passing live access-point run.

## P11 Step 6/14 — UI Lab Self-play Simulator Version

Progress:
- Updated the `run_self_play_probe` tool path so UI-triggered self-play explicitly defaults to `sim_v2` and passes a versioned `UserSimulator` into `SelfPlayRunner`.
- Threaded `simulator_version` through `/api/self-play`, frontend session history, composer-triggered self-play side effects, and response metadata.
- Updated `/api/view` and the Lab card so the visible Lab surface shows `simulator sim_v2` before and after a run.
- Updated the legacy static bundle to send `simulator_version="sim_v2"` for self-play release-gate runs.

Evidence:
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_frontend_server_api.py' -v` passes and asserts `/api/view["lab"]["simulator_version"] == "sim_v2"`.
- `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_frontend_session_persistence.py' -v` passes and asserts composer/session self-play history persists `sim_v2`.
- Computer Use UI verification opened `http://127.0.0.1:8791`, selected Lab, observed the visible `simulator sim_v2` row, clicked `Run self-play`, and confirmed the exported state recorded `simulator_version="sim_v2"` in the latest self-play history and each episode log.
- `PYTHONPATH=src python3 scripts/check_invariants.py --replay runs/ui_self_play_sim_v2/replay.jsonl` passes with 29 replay records and 0 violations.

Remaining:
- None for the UI `sim_v1` blocker.

## P11 Step 13 — Dogfood Release, Final Pass

Progress:
- Added `configs/` to the macOS app bundle so packaged app runs can load `configs/autonomy_matrix.json`; this fixed fixture packaged-app commits being denied with `max_auto_tier=0`.
- Added the bundled autonomy matrix to release artifact validation.
- Cleaned generated release run directories before packaged app sanity checks so stale failed sessions cannot poison subsequent release runs.
- Made the occupied-port launch gate wait for HTTP readiness after the launcher selects an alternate port.
- Fixed the strict invariant crash on commit envelopes with `swift_receipt=null`.

Evidence:
- `make mac-app-build` succeeds and `dist/CalendarPilot.app/Contents/Resources/app/configs/autonomy_matrix.json` is present.
- `make dogfood-release` now passes end to end.
- Final release report `runs/release/dogfood_release_report.json` has `ok=true`.
- Passing release checks include `python_tests`, `swift_tests`, `swift_ipc_tests`, `browser_e2e`, `mac_app_build`, `mac_app_sanity`, `mac_app_swift_ipc_sanity`, `launchservices_smoke`, `occupied_port_launch_gate`, `artifact_validation`, `secret_scan`, `release_report_validation`, and `release_report_secret_scan`.
- `mac_app_sanity` passed in fixture mode with `SwiftKernelStub`; `mac_app_swift_ipc_sanity` passed with `SwiftKernelIPCClient`; `launchservices_smoke` served `http://127.0.0.1:8787`; occupied-port launch selected alternate port `52025`.

Remaining:
- None for the dogfood release blocker.

## P11 Final Acceptance — Blocker-fix Run

Evidence:
- `make py-test` passes: 151 tests, 10 skipped.
- `make check-invariants contract-vectors lab-validate-seeds lab-validate-scenarios variance-probe` passes.
- `make browser-e2e` passes and writes artifacts under `runs/browser_e2e/artifacts`.
- `make replay-offline-tuning-loop` passes live end-to-end and proves tuning affected the next live NIM frontier.
- `make dogfood-release` passes with release report `ok=true`.

Remaining:
- The 20-seed fixture matrix still reports `OTHER_intent_rate=0.1081`, slightly above the 0.10 promotion bar, so promotion remains correctly held even though the blocker list is now addressed.
