# P10 — CalendarPilot Lab v0: Thin Lab + Seeded ML (implementation spec)

The core test spine is evidence-grade: every test path leaves replay JSONL, tuning output, frontier diff, invariant report, and session/runtime artifacts, and those paths pass across Python, Swift, Swift IPC, browser, SSE, ActionLifecycle, SessionStore, contract vectors, self-play, and invariants (see `calendar-pilot-deferred-pass/docs/DEFERRED_WORK_IMPLEMENTATION_PASS.md`). The repo is ready for **signal acquisition**.

**Decision (recorded, not open):** do not choose between "seed a calendar and go full throttle on ML" and "materialize a lab." Build a **one-week thin lab shell**, then run seeded/full-throttle ML inside it. Full-throttle-without-lab produces runs that are not comparable experiments; lab-without-signal produces a research cockpit with nothing in it. The lab is the smallest infrastructure layer that makes ML runs repeated, comparable, and scored.

This document is now a **spec, not a proposal**. Every previously open decision is locked in §1. An engineer implementing this should not need to invent formats, thresholds, names, or procedures — if you find yourself making a decision this document doesn't cover, that's a gap: record it in `experiments/DECISIONS.md` and pick the option that uses existing repo machinery.

All paths below are relative to `calendar-pilot-deferred-pass/` unless stated otherwise. Nothing in this plan references or depends on `Do-not-reference/`.

The target loop is unchanged:

```text
seeded calendar corpus
→ live/fixture policy frontier
→ Codex/tool path
→ ActionLifecycle/Swift/provider path
→ reward + self-play + human feedback
→ replay
→ tuning
→ next frontier
→ scorecard
```

The lab must produce **frontier deltas, reward deltas, rejection rates, OTHER intent rate, rollback coverage, provider mutation stats, and tuning effects** every day. Anything that does not feed one of those numbers is lab theater and is out of scope (§14).

---

## 1. Decisions locked for v0

Every row below was ambiguous or open-ended in the previous draft. These are now decided. Change them only via a recorded entry in `experiments/DECISIONS.md`.

| # | Question | Locked decision |
|---|---|---|
| D1 | Where does the lab live? | Inside `calendar-pilot-deferred-pass/`: new `experiments/` tree (§2) + four new scripts in the existing `scripts/`. No new repo, no databases, files only. |
| D2 | How many seeds? | Exactly **20**: 10 personas × 2 seeds each (one `_baseline`, one named pressure variant). Roster in §3.2. Days 1–2 use the 5-seed starter set named in §3.2. |
| D3 | "30 days of events"? | **One 7-day observation window per seed** (Mon 2026-07-06 → Sun 2026-07-12, `America/Los_Angeles`), plus ≥14 days of `notification_history`. Rationale: the pipeline consumes a single `RawCalendarObservation`, and the live NIM frontier prompt embeds the whole observation (`CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS` defaults to 4200). 30-day corpora and multi-day episode simulation are P11 (§15). |
| D4 | Seed file format? | One JSON file per seed embedding `observation` (must round-trip `RawCalendarObservation.from_dict`), `profile` (`UserBiography` shape), and an `expectations` block. Full schema in §3.1. |
| D5 | Intent label vocabulary? | Canonical taxonomy only: the 11 values of `CanonicalIntent` in `src/calendar_pilot/environment/taxonomy.py` (`protect_deep_work`, `create_prep_block`, `add_buffer`, `batch_admin`, `reschedule_conflict`, `move_meeting`, `decline_or_trim`, `notify_summary`, `ask_clarification`, `do_nothing`, `other`). Aliases like `move_flexible_hold` are not valid expectation labels (they normalize to `move_meeting`). |
| D6 | "Useful non-do-nothing candidate"? | Lint rule L7 (§3.3): the fixture (heuristic) policy on the seed must yield ≥1 candidate whose canonical intent is not `do_nothing`/`other` and whose `expected_reward > 0`. |
| D7 | "Adversarial variants"? | Exactly **5 generated perturbation variants per seed**, default set `[remove_prep_slot, increase_notification_fatigue, expire_authority_grant, compress_between_meetings, inject_flexible_hold]`; seed may override with justification in its `notes`. Catalog and machine-checked expected effects in §3.4. |
| D8 | Runtime matrix cells? | Mapped to real `CALENDAR_PILOT_RUNTIME_MODE` values (`fixture`, `live_diffusiongemma`) and real `--self-play-backend` choices (`stub_fast`, `swift_ipc_deterministic`, `swift_ipc_eventkit_sandbox`, `production_shadow`). Exact cells in §5. |
| D9 | Manifest `"..."` placeholders? | Every manifest field has a defined source (§4). One tiny code change required: add `PROMPT_VERSION = "frontier_v1"` to `src/calendar_pilot/diffusiongemma/live.py` (§8.5). |
| D10 | `valid_frontier_rate ≥ 0.95` vs `rejection_rate ≤ 0.15` contradiction? | They measure different levels. `valid_frontier_rate` is **run-level** (share of live runs producing ≥3 valid candidates). `model_generation_rejection_rate` is **item-level** (pooled rejected items / pooled generated items). Formulas in §6. |
| D11 | "Seeded failure cases" for the leader-change gate? | Seeds flagged `expects_tuning_leader_change: true` (4 seeds, §3.2). Gate: promotion-time frontier diff shows `leader_changed == true` on ≥3 of them. |
| D12 | "Self-play penalty changes later frontier behavior" — how measured? | Candidate tuning has non-empty `failure_penalties`, AND on ≥1 flagged seed some candidate whose canonical intent carries a failure penalty has `per_candidate_delta[...].delta < 0` in the promotion-time `frontier_diff.json`. |
| D13 | "Nearest synthetic seed" for dogfood shadow? | Static mapping file `experiments/configs/shadow_map.json` (`{"<user_scope_id>": "<seed_id>"}`), maintained by hand. No similarity metric in v0 (§15). |
| D14 | Experiment IDs, collisions, concurrency? | `lab_YYYYMMDD_NNN` (UTC date, NNN = next free 3-digit sequence). Existing run dir is never overwritten without `--force`. v0 runs experiments **serially**; `experiments/index.json` is **derived** (rebuildable via `compare_lab_runs.py --reindex`) — run dirs are the source of truth. |
| D15 | "Scorecards comparable" means? | Every run writes the same artifact set (§4.2) stamped `lab_schema_version: "lab_v0.1"`, keyed by `(seed_id, runtime_mode, policy_tuning_id)`, consumed by `compare_lab_runs.py`. |
| D16 | Which tuning gets promoted? | Per-run tunings are diagnostics only. The **candidate tuning** for promotion is trained on the pooled replay of a batch (§7.2). Promoted tunings are copied to `experiments/promoted/` and pointed at by `experiments/promoted/CURRENT.json`; lab runs default `--tuning` to CURRENT when it exists. |
| D17 | EventKit sandbox identity? | A local ("On My Mac") calendar named `CalendarPilot SelfPlay`. The Swift bridge matches `CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID` by calendar identifier **or title**, so the title string is a valid value. Runbook in §9. |
| D18 | Self-play episode count? | `--episodes 10` default (≤ every backend cap in `environment/selfplay_backends.py`: stub 100, swift_ipc 50, eventkit 10, shadow 20). Cell D (EventKit) uses 5. |
| D19 | Authority profile names? | `tier1_recommend` (max tier 1, commit forbidden) and `tier3_private` (max tier 3, safe private commits allowed under existing planner semantics — default). `tier5_social_sandbox` is P11; social actuation stays denied. |
| D20 | Do expectation failures fail the run? | No. Infrastructure errors exit nonzero; **expectation misses are data**, recorded in `lab_report.json` and enforced only by promotion gates and day exit criteria. A bad model must not crash the lab. |
| D21 | Feedback queue states? | Mapped onto existing `RewardEvent` kinds (§10.2): `accepted`, `undone`, `ignored`, `explicit_wrong` ("wrong"), `explicit_not_needed` ("not needed"), `notification_dismissed` ("too interruptive"). `needs_feedback` is a queue-only state meaning "receipt exists, no reward event yet." |
| D22 | Real-dogfood comparability? | `run_lab_experiment.py --from-replay <path>` imports an app dogfood replay and runs only the analysis steps (invariants → tuning → frontier diff → scorecard → lab report), producing a lab-shaped run dir comparable to the shadow seed run (§10.1). |
| D23 | Temperature/top_p ablations? | Deferred to P11. Live decoding is currently fixed in `NvidiaNIMPolicyClient` (attempt 1: `temperature=0.2, top_p=0.9`; retry: `0.0/1.0`); the manifest records those constants. Adding env knobs is a separate small change. |
| D24 | Seed dates drift? | Never. All seeds use the fixed week of D3 and deterministic content. Regenerating a seed with the same generator version must be byte-identical (sorted keys, no timestamps-of-generation inside seed files). |

---

## 2. Lab layout (Track 1 shell)

New tree at repo root:

```text
experiments/
  seeds/                      # committed, hand-reviewed seed JSON (base + generated perturbation variants)
  configs/
    promotion_thresholds.json # the numbers in §7.1, as data
    shadow_map.json           # D13
    matrix_v0.json            # the cells in §5, as data
  runs/                       # generated run dirs — gitignored
  reports/                    # committed batch comparisons + promotion records
  promoted/                   # committed promoted tunings + CURRENT.json
  index.json                  # derived registry — rebuildable, committed after each batch
  DECISIONS.md                # append-only log of any deviation from this spec

scripts/
  seed_calendar_corpus.py     # new
  run_lab_experiment.py       # new
  compare_lab_runs.py         # new
  promote_policy.py           # new
```

Everything else is generated from artifacts the framework already emits: `replay.jsonl`, `policy_tuning.json`, `frontier_diff.json`, `scorecard.json`, `invariant_report.json`, session manifests.

Required hygiene changes (part of Track 1):

- `.gitignore`: add `experiments/runs/`.
- `Makefile`: add targets

```make
lab-validate-seeds:
	PYTHONPATH=src python3 scripts/seed_calendar_corpus.py --validate

lab-run:            # SEED and RUNTIME injected: make lab-run SEED=... RUNTIME=fixture
	PYTHONPATH=src python3 scripts/run_lab_experiment.py --seed $(SEED) --runtime $(RUNTIME)

lab-compare:
	PYTHONPATH=src python3 scripts/compare_lab_runs.py --reindex --out experiments/reports/comparison_latest.json

lab-promote:
	PYTHONPATH=src python3 scripts/promote_policy.py --batch $(BATCH)
```

Do not add databases. Files only.

---

## 3. Track 2 — Seed corpus

### 3.1 Seed file schema (`seed_schema_version: "1.0"`)

One file per seed at `experiments/seeds/<seed_id>.json`:

```json
{
  "seed_schema_version": "1.0",
  "seed_id": "seed_ae_renewal_week_high_pressure",
  "persona": "account_executive",
  "variant": "renewal_week_high_pressure",
  "description": "External renewal call with no prep block, flexible admin hold before it, high notification fatigue, evening suggestions historically dismissed.",
  "goal": "Protect the renewal call and reduce notification noise",
  "authority": { "profile": "tier3_private" },
  "expects_tuning_leader_change": false,
  "observation": {
    "observation_id": "obs_seed_ae_renewal_week_high_pressure",
    "user_scope_id": "seed_ae_renewal_week_high_pressure",
    "observed_at": "2026-07-06T08:00:00-07:00",
    "time_zone_id": "America/Los_Angeles",
    "events": [
      {
        "event_id": "evt_renewal_call",
        "title": "Acme renewal call",
        "start": "2026-07-08T15:00:00-07:00",
        "end": "2026-07-08T16:00:00-07:00",
        "calendar_id": "work",
        "attendees": ["client@acme.example", "me@seed.example"],
        "location": "Zoom",
        "notes": "Renewal pricing discussion.",
        "is_user_owned": false,
        "is_flexible": false,
        "category": "external_meeting"
      },
      {
        "event_id": "evt_admin_hold",
        "title": "Admin hold",
        "start": "2026-07-08T13:30:00-07:00",
        "end": "2026-07-08T14:30:00-07:00",
        "calendar_id": "work",
        "attendees": [],
        "location": "",
        "notes": "Flexible.",
        "is_user_owned": true,
        "is_flexible": true,
        "category": "admin"
      }
    ],
    "tasks": [
      {
        "task_id": "task_renewal_prep",
        "title": "Prepare renewal notes",
        "due": "2026-07-08T15:00:00-07:00",
        "estimated_minutes": 45,
        "category": "prep"
      }
    ],
    "device_context": { "local_hour": 8, "active_surface": "calendar_day_view", "is_focus_mode": false },
    "notification_history": [
      { "sent_at": "2026-07-01T20:15:00-07:00", "kind": "suggestion", "outcome": "dismissed" },
      { "sent_at": "2026-07-02T21:05:00-07:00", "kind": "suggestion", "outcome": "dismissed" },
      { "sent_at": "2026-07-03T09:00:00-07:00", "kind": "suggestion", "outcome": "accepted" }
    ],
    "prior_actions": []
  },
  "profile": {
    "user_scope_id": "seed_ae_renewal_week_high_pressure",
    "deep_work_windows": ["09:00-11:00"],
    "admin_windows": ["Friday 14:00-17:00"],
    "best_response_hours": [8, 13],
    "bad_response_hours": [20, 21, 22, 23],
    "auto_create_travel_buffers": true,
    "auto_move_flexible_holds": true,
    "ask_before_people_meetings": true,
    "notification_fatigue": 0.6,
    "preference_claims": [
      { "claim": "accepts prep blocks near external calls", "confidence": 0.82 },
      { "claim": "dismisses evening suggestions", "confidence": 0.77 }
    ]
  },
  "expectations": {
    "expected_good_intents": ["create_prep_block", "move_meeting", "add_buffer"],
    "expected_bad_intents": [
      { "intent": "notify_summary", "why": "high fatigue; evening suggestions historically dismissed" },
      { "intent": "decline_or_trim", "why": "external renewal call must not be touched" }
    ]
  },
  "perturbations": ["remove_prep_slot", "increase_notification_fatigue", "expire_authority_grant", "compress_between_meetings", "inject_flexible_hold"],
  "notes": "Example above truncated to 2 events for readability; the real seed carries the full week per the density band."
}
```

Rules the example encodes:

- `observation` and `profile` are exactly the shapes of `data/sample_calendar.json` / `data/sample_profile.json` (`RawCalendarObservation` / `UserBiography`). No new observation fields — the lab adds metadata *around* the contract, never inside it.
- Expectation labels are canonical intents (D5). The earlier draft's `move_flexible_hold` becomes `move_meeting`; "notify_summary at 21:00" becomes `notify_summary` with the timing concern expressed in `why` (right-moment quality is measured separately, §6).
- `user_scope_id` equals `seed_id` so replay rows are attributable to a seed with no join table.

Persona density bands (lint L5): dense personas (`ea_dense`, `ae`, `consultant`, `founder`, `travel`) 35–60 events/week; medium (`em`, `parent`, `admin_frag`, `burnout`) 20–35; deep-work (`researcher`) 12–20.

### 3.2 The 20-seed roster

| persona | baseline seed | pressure variant | flagged (D11) |
|---|---|---|---|
| founder/operator | `seed_founder_baseline` | `seed_founder_board_week_crunch` | |
| sales/account executive | `seed_ae_baseline` | `seed_ae_renewal_week_high_pressure` | |
| engineering manager | `seed_em_baseline` | `seed_em_incident_review_overload` | |
| researcher/deep-work | `seed_researcher_baseline` | `seed_researcher_deadline_fatigue` | ✓ |
| consultant/client-heavy | `seed_consultant_baseline` | `seed_consultant_backtoback_clients` | |
| parent/caregiver | `seed_parent_baseline` | `seed_parent_school_pickup_conflicts` | |
| executive-assistant dense | `seed_ea_dense_baseline` | `seed_ea_dense_double_bookings` | ✓ |
| travel-heavy | `seed_travel_baseline` | `seed_travel_timezone_hop` | ✓ |
| burnout/high-fatigue | `seed_burnout_baseline` | `seed_burnout_notification_saturation` | ✓ |
| fragmented/admin-heavy | `seed_admin_frag_baseline` | `seed_admin_frag_context_thrash` | |

**Flagged seeds** (`expects_tuning_leader_change: true`) are constructed so the *untuned* fixture leader's intent appears in `expected_bad_intents` (lint L10 verifies this by running the fixture policy). They are the fixtures for the leader-change promotion gate.

**Days 1–2 starter set (5):** `seed_ae_renewal_week_high_pressure`, `seed_researcher_deadline_fatigue`, `seed_ea_dense_double_bookings`, `seed_burnout_notification_saturation`, `seed_parent_school_pickup_conflicts`.

**Cell D (EventKit sandbox) seeds (2):** `seed_ae_renewal_week_high_pressure`, `seed_researcher_deadline_fatigue`.

### 3.3 Seed validation (replaces "pass criteria")

`scripts/seed_calendar_corpus.py --validate` runs these lints over `experiments/seeds/*.json` and exits nonzero listing every violation:

```text
L1  seed_schema_version == "1.0"; filename == seed_id + ".json"; seed_id matches ^seed_[a-z0-9_]+$
L2  observation round-trips RawCalendarObservation.from_dict(...).to_dict() preserving required fields;
    profile round-trips UserBiography the same way
L3  expectation labels ∈ CanonicalIntent; expected_good ∩ expected_bad = ∅;
    do_nothing and other are not allowed in expected_good_intents
L4  all events within [2026-07-06, 2026-07-13); observed_at == 2026-07-06T08:00:00-07:00;
    time_zone_id == America/Los_Angeles
L5  event count within the persona density band (§3.1)
L6  notification_history ≥ 1 entry; if profile.notification_fatigue ≥ 0.5 then ≥ 5 entries spanning ≥ 7 days
L7  fixture policy on the seed yields ≥ 1 candidate with canonical intent ∉ {do_nothing, other}
    and expected_reward > 0            # "useful non-do-nothing candidate", D6
L8  authority.profile ∈ {tier1_recommend, tier3_private}
L9  perturbations list ⊆ catalog (§3.4); length == 5
L10 if expects_tuning_leader_change: fixture untuned leader intent ∈ expected_bad_intents
```

"Every seed has expected intent labels" = L3. "Every seed produces at least one useful candidate" = L7. "Every seed has adversarial variants" = L9 + generation below. "Every seed can run fixture, live NIM, self-play, and offline tuning" is proven by the day 3–4 matrix runs, not by lint.

### 3.4 Perturbation catalog

`seed_calendar_corpus.py --generate-variants` writes `experiments/seeds/<seed_id>__<perturbation>.json` (same schema; `variant_of: <seed_id>` added; expectations inherited then overridden per catalog). If a perturbation is not applicable to a seed (e.g. `remove_prep_slot` on a seed with no prep-dependent meeting), the generator must **fail loudly** so the seed author overrides the list — never emit a silent no-op variant.

| perturbation | transform (deterministic) | expected effect (encoded in variant) | machine-checked in v0 |
|---|---|---|---|
| `remove_prep_slot` | delete the open slot / flexible hold immediately before the highest-stakes external meeting | `{"check": "intent_in_top_k", "intent": "create_prep_block", "k": 3}` | ✓ |
| `increase_notification_fatigue` | set `profile.notification_fatigue = max(existing, 0.8)`; append 5 dismissed notifications | `{"check": "intent_not_top1", "intent": "notify_summary"}` | ✓ |
| `expire_authority_grant` | set `authority.profile = "tier1_recommend"` | `{"check": "failure_mode_present", "mode": "denied_actuation", "min": 1}` (self-play must surface denial) | ✓ |
| `compress_between_meetings` | remove gaps so ≥3 meetings are back-to-back | `{"check": "intent_in_top_k", "intent": "add_buffer", "k": 3}` | ✓ |
| `inject_flexible_hold` | add a user-owned `is_flexible: true` hold adjacent to the pressure point | `{"check": "intent_in_top_k", "intent": "move_meeting", "k": 3}` | ✓ |
| `add_external_meeting` | insert one external meeting into the densest day | `{"check": "note", "text": "pressure signals rise"}` | tracked only |
| `add_social_conflict` | add an overlapping meeting with attendees | `{"check": "note", "text": "social_conflict findings expected when social candidates previewed"}` | tracked only |
| `make_observation_stale` | set `observed_at` 26h before week start | `{"check": "note", "text": "temporal controller should mark staleness"}` | tracked only |

The five check types (`intent_in_top_k`, `intent_not_top1`, `failure_mode_present`, `denial_present`, `note`) are the complete v0 evaluator vocabulary, implemented once inside `run_lab_experiment.py` and reported in `lab_report.json.expectation_results`. Effects marked "tracked only" are recorded, never gated.

---

## 4. Experiment manifests and run artifacts

### 4.1 `manifest.json` — every field has a source; no placeholders

```json
{
  "lab_schema_version": "lab_v0.1",
  "experiment_id": "lab_20260706_001",
  "batch_id": "batch_20260706_01",
  "seed_id": "seed_ae_renewal_week_high_pressure",
  "seed_path": "experiments/seeds/seed_ae_renewal_week_high_pressure.json",
  "seed_sha256": "…",
  "goal": "Protect the renewal call and reduce notification noise",
  "runtime_mode": "live_diffusiongemma",
  "policy_backend": "nvidia_nim_diffusiongemma_policy",
  "codex_backend": "deterministic_codex_tool_planner",
  "kernel_backend": "SwiftKernelIPCClient",
  "provider_backend": "deterministic",
  "model": "…",
  "prompt_version": "frontier_v1",
  "decoding": { "temperature": 0.2, "top_p": 0.9, "max_tokens": 4200 },
  "policy_tuning_id": "empty",
  "reward_weights_id": "…",
  "authority_profile": "tier3_private",
  "self_play_backend": "swift_ipc_deterministic",
  "episodes": 10,
  "git_sha": "…",
  "git_dirty": false,
  "started_at": "2026-07-06T17:00:00Z",
  "ended_at": "2026-07-06T17:04:12Z",
  "status": "completed",
  "skip_reason": null
}
```

| field | source |
|---|---|
| `experiment_id` | allocated `lab_YYYYMMDD_NNN` (UTC date; next free NNN under `experiments/runs/`) — D14 |
| `batch_id` | `--batch` flag; default `adhoc` |
| `seed_id` / `seed_path` / `seed_sha256` / `goal` | seed file (sha256 of its bytes) |
| `runtime_mode` | `--runtime` flag; v0 set: `fixture` \| `live_diffusiongemma` (both ∈ `KNOWN_MODES` in `frontend/runtime.py`) |
| `policy_backend` / `codex_backend` / `kernel_backend` | `runtime_report()["backends"]` for the chosen mode (e.g. fixture → `heuristic_diffusiongemma_policy` / `deterministic_codex_tool_planner` / `SwiftKernelStub`) |
| `provider_backend` | `CALENDAR_PILOT_PROVIDER_BACKEND` env, else `deterministic` |
| `model` | `CALENDAR_PILOT_NIM_MODEL` / `NIM_MODEL` env; `null` for fixture |
| `prompt_version` | `PROMPT_VERSION` constant in `diffusiongemma/live.py` (§8.5) |
| `decoding` | the client's attempt-1 constants + `CALENDAR_PILOT_NIM_FRONTIER_MAX_TOKENS` (D23) |
| `policy_tuning_id` | `tuning_id` of the `--tuning` file; `empty` if none; defaults to `experiments/promoted/CURRENT.json` target when present (D16) |
| `reward_weights_id` | `sha256(configs/reward_weights.json)[:12]` |
| `authority_profile` | seed `authority.profile` (D19) |
| `self_play_backend` / `episodes` | flags; defaults `stub_fast` / `10` |
| `git_sha` / `git_dirty` | `git rev-parse HEAD`; dirty flag if working tree modified |
| `started_at` / `ended_at` | UTC ISO-8601, written at start / finalize |
| `status` | `completed` \| `failed` \| `skipped` (+ `skip_reason`, e.g. `nim_credentials_missing`) |

### 4.2 Run artifact set (all always written; empty JSONL = zero-line file)

```text
experiments/runs/<experiment_id>/
  manifest.json                        §4.1
  replay.jsonl                         ReplayBuffer (decision / receipt / reward / self_play_episode /
                                       adversary_finding / codex_tool_call / codex_tool_receipt /
                                       router_decision / model_generation_rejection / envelope_transition)
  valid_candidates.jsonl               one row per accepted frontier candidate
  model_generation_rejections.jsonl    one row per NIM rejection (reasons: skipped_non_object_candidate,
                                       skipped_invalid_candidate, duplicate_candidate_id,
                                       skipped_candidate_without_actions, missing_target_calendars)
  invariant_report.json                check_invariants output over this run's replay (rules I2, I6)
  offline_policy_report.json           train_offline_policy output over this run's replay
  policy_tuning.json                   per-run tuning (diagnostic only — D16)
  frontier_diff.json                   run_frontier_diff.build_diff(observation, profile, this run's tuning, goal)
  scorecard.json                       make_scorecard.build_scorecard(replay, frontier_diff, offline_report)
  lab_report.json                      §4.3
```

### 4.3 `lab_report.json` — the row every comparison consumes

```json
{
  "lab_schema_version": "lab_v0.1",
  "experiment_id": "lab_20260706_001",
  "seed_id": "seed_ae_renewal_week_high_pressure",
  "runtime_mode": "live_diffusiongemma",
  "policy_tuning_id": "empty",
  "metrics": {
    "valid_candidates": 6,
    "valid_frontier": true,
    "generated_items": 7,
    "rejections": 1,
    "duplicate_rejections": 0,
    "other_intent_count": 0,
    "other_intent_rate": 0.0,
    "frontier_distinct_intents": 4,
    "top_candidate_intent": "create_prep_block",
    "top_candidate_expected_reward": 1.84,
    "top_candidate_predicted_regret": 0.08,
    "top_candidate_predicted_social_risk": 0.02,
    "top_candidate_right_moment_decision": "notify_now",
    "leader_changed_after_tuning": false,
    "avg_reward_delta_after_tuning": 0.0,
    "self_play_average_reward": 0.61,
    "failure_modes": { "notification_fatigue": 2 },
    "receipts": 12,
    "denials": 0,
    "invariant_violations": 0
  },
  "expectation_results": {
    "expected_intent_hit": true,
    "expected_intent_hit_detail": "create_prep_block at rank 1",
    "bad_intent_top1": false,
    "bad_intent_committed": false,
    "perturbation_checks": []
  },
  "scorecard_decision": "promote_candidate"
}
```

`experiments/index.json` is exactly the list of these rows plus `run_dir`, rebuilt by `compare_lab_runs.py --reindex` (D14) — this keeps the Glass Cockpit able to list past experiments without a database.

---

## 5. Runtime matrix v0 (`experiments/configs/matrix_v0.json`)

| cell | `--runtime` | `--self-play-backend` | commits | gating | meaning |
|---|---|---|---|---|---|
| A | `fixture` | `stub_fast` | staging only | none | heuristic policy + deterministic provider (baseline) |
| B | `live_diffusiongemma` | `stub_fast` | staging only | NIM credentials | live NIM frontier + deterministic provider |
| C | `live_diffusiongemma` | `swift_ipc_deterministic` | staging only | NIM credentials + Swift toolchain | live NIM + Swift IPC deterministic self-play (kernel-issued sandbox grants) |
| D | `live_diffusiongemma` | `swift_ipc_eventkit_sandbox` | sandbox writes | NIM + `CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1` + sandbox calendar id + macOS calendar access | EventKit sandbox (§9), episodes=5, the 2 designated seeds only |

Notes:

- "Heuristic policy" in the earlier draft = `fixture` mode (`heuristic_diffusiongemma_policy` backend). "Live NIM frontier" = `live_diffusiongemma`.
- Live preflight: `NvidiaNIMPolicyClient().health_status(validate_remote=True)`; not `configured` or not `ok` → run exits **2** with `status: "skipped"`, `skip_reason` recorded (same convention as `scripts/run_live_diffusiongemma_e2e.py`). Skips are visible in the index, never silent.
- `production_shadow` (read-only, gated by `CALENDAR_PILOT_SELFPLAY_SHADOW`) is used on days 5–6 on selected seeds; it is not a matrix cell.
- Credentials come from `.env` via `calendar_pilot.env.load_local_env` (`NVIDIA_API_KEY` / `NIM_API_KEY` / `CALENDAR_PILOT_NIM_API_KEY`, plus optional `CALENDAR_PILOT_NIM_BASE_URL`, `CALENDAR_PILOT_NIM_MODEL`, `CALENDAR_PILOT_NIM_TIMEOUT`).

---

## 6. First-order ML metrics — definitions

Track these before inventing more architecture. "Pooled" = summed counts across the live runs of a batch, then divided (not a mean of per-run rates).

| metric | level | formula | source | gate? |
|---|---|---|---|---|
| `valid_frontier_rate` | run→batch | share of live runs with `len(valid_candidates) ≥ 3` | `valid_candidates.jsonl` | **≥ 0.95** |
| `model_generation_rejection_rate` | item, pooled | Σ rejections / Σ (rejections + valid candidates) | `model_generation_rejections.jsonl` + `valid_candidates.jsonl` | **≤ 0.15** |
| `duplicate_candidate_rate` | item, pooled | Σ rejections with reason `duplicate_candidate_id` / Σ generated items | same | tracked |
| `OTHER_intent_rate` | item, pooled | Σ candidates with canonical intent `other` / Σ candidates, over tuned frontiers | `scorecard.frontier.taxonomy_health` counts | **≤ 0.10** |
| `top_candidate_expected_reward` | run | `tuned_frontier[0].expected_reward` | `frontier_diff.json` | tracked |
| `top_candidate_predicted_regret` | run | `tuned_frontier[0].predicted_regret` (raw head, not the weighted `reward_breakdown.regret`) | `frontier_diff.json` | tracked |
| `top_candidate_predicted_social_risk` | run | `tuned_frontier[0].predicted_social_risk` | `frontier_diff.json` | tracked |
| `frontier_diversity_by_intent` | run | count of distinct canonical intents (excluding `other`) in tuned frontier | `frontier_diff.json` | tracked, target ≥ 3 |
| `leader_changed_after_tuning` | run | `frontier_diff.leader_changed` | `frontier_diff.json` | **true on ≥ 3 flagged seeds** at promotion time (D11) |
| `average_reward_after_self_play` | run | `scorecard.self_play.average_reward` | `scorecard.json` | tracked |
| `undo_regret_findings` / `notification_fatigue_findings` / `denied_actuation_findings` | run | `scorecard.self_play.failure_modes[mode]` | `scorecard.json` | tracked |
| `invariant_violations` | run | `scorecard.invariants.violations` (I2 = committed/verify/undo transitions without acceptable `rollback_state` — this **is** "committed_actions_missing_rollback_state"; I6 = undo handle replay) | `scorecard.json` | **== 0** |
| `expected_intent_hit` | run | any of top-3 tuned candidates' canonical intent ∈ `expected_good_intents` | `lab_report.json` | day-exit criterion: ≥ 0.80 hit rate on fixture runs; tracked for live |
| `bad_intent_violation` | run | `bad_intent_committed` (any committed receipt whose intent ∈ expected_bad) — gated; `bad_intent_top1` — tracked | `lab_report.json` | committed: **== 0** |

Right-moment quality in v0 is `top_candidate_right_moment_decision` recorded per run and the `intent_not_top1(notify_summary)` perturbation check on high-fatigue variants; a dedicated right-moment metric is P11 (§15).

---

## 7. Promotion

### 7.1 Thresholds (`experiments/configs/promotion_thresholds.json`)

```json
{
  "valid_frontier_rate_min": 0.95,
  "other_intent_rate_max": 0.10,
  "model_generation_rejection_rate_max": 0.15,
  "invariant_violations_max": 0,
  "bad_intent_committed_max": 0,
  "flagged_seed_leader_changes_min": 3,
  "self_play_penalty_effect_required": true
}
```

`self_play_penalty_effect_required` is the D12 check: candidate tuning has non-empty `failure_penalties` AND ≥1 flagged seed shows a negative `per_candidate_delta` for a candidate whose intent carries a failure penalty.

### 7.2 Promotion flow (answers "which tuning is promoted?")

```text
1. Run a batch (matrix cells over a seed set, one git_sha, serial).
2. Pool the batch: concatenate experiments/runs/<id>/replay.jsonl for all completed runs.
3. Train the candidate tuning on the pooled replay:
   train_offline_policy.py --replay <pooled.jsonl> --tuning-out <candidate policy_tuning.json>
   (tuning_id := batch_id)
4. promote_policy.py --batch <batch_id>:
   a. for every batch seed, recompute frontier_diff with the candidate tuning
      (build_diff from scripts/run_frontier_diff.py — cheap, fixture scoring);
   b. evaluate every gate in §7.1 over the batch's lab_report rows + the recomputed diffs;
   c. write experiments/reports/promotion_<batch_id>.json (schema below);
   d. decision "promote": copy tuning to experiments/promoted/policy_tuning_<batch_id>.json
      and update experiments/promoted/CURRENT.json; otherwise decision "hold" and CURRENT is untouched.
5. Subsequent lab runs pick up CURRENT as their default --tuning (D16).
```

Promotion record — every promoted (or held) tuning gets one:

```json
{
  "policy_tuning_id": "batch_20260706_01",
  "source_batch": "batch_20260706_01",
  "source_runs": ["lab_20260706_001", "…"],
  "metrics_before": { "flagged_seed_leader_changes": 0, "other_intent_rate": 0.06, "rejection_rate": 0.09 },
  "metrics_after":  { "flagged_seed_leader_changes": 3, "other_intent_rate": 0.05, "rejection_rate": 0.09 },
  "frontier_diffs": ["experiments/reports/promotion_batch_20260706_01/<seed_id>.frontier_diff.json"],
  "known_regressions": [],
  "gates": { "valid_frontier_rate": "pass", "other_intent_rate": "pass", "…": "…" },
  "promotion_decision": "promote",
  "human_note": "",
  "decided_at": "2026-07-06T20:00:00Z",
  "git_sha": "…"
}
```

Rollback = point `CURRENT.json` back at the previous promoted file and record a promotion record with `promotion_decision: "rollback"`. History is the `experiments/promoted/` directory plus records; nothing is deleted.

This turns the existing gate ladder into the lab board: Gate A (fixture ML) = cell A green; Gate B (live NIM ML) = cell B green; Gate C (live Codex executive) = `make live-codex-e2e`; Gate D (Swift IPC acting) = cell C green; Gate E (provider sandbox) = §9; Gate F (recommendation dogfood) = §10. Board colors: green = pass, yellow = pass with skips recorded, red = gate failure, gray = env-gated skip.

---

## 8. Script contracts

Shared conventions: stdlib only (argparse/json/pathlib — matching every existing script); atomic writes via `calendar_pilot.environment.fsio.atomic_write_json`; exit **0** = completed (expectation misses included — D20), **1** = infrastructure error, **2** = env-gated skip; `--force` required to reuse an existing run dir.

### 8.1 `scripts/seed_calendar_corpus.py`

```text
--validate                 run lints L1–L10 over experiments/seeds/, print violations, exit 1 on any
--generate-variants        write <seed_id>__<perturbation>.json per §3.4 (deterministic, byte-stable — D24)
--seed <path>              restrict either action to one seed
```

Base seeds are authored by hand (they are product judgments); the script validates and derives variants — it does not invent calendars in v0. A `Persona(...)`-template generator is P11.

### 8.2 `scripts/run_lab_experiment.py`

```bash
PYTHONPATH=src python3 scripts/run_lab_experiment.py \
  --seed experiments/seeds/seed_ae_renewal_week_high_pressure.json \
  --runtime live_diffusiongemma \
  --self-play-backend swift_ipc_deterministic \
  --episodes 10 \
  --batch batch_20260706_01 \
  [--tuning <path>] [--commit] [--out-root experiments/runs] [--force] \
  [--from-replay <path> --seed-id <label>]        # import mode, D22
```

Execution steps, each mapped to existing machinery:

```text
 1. load + lint seed (§3.3; L2 round-trip is the schema validation)
 2. allocate experiment_id, create run dir, write manifest (status: running)
 3. frontier:
      fixture → DiffusionGemmaPolicy(policy_tuning=--tuning).generate_candidates(...)
      live    → NvidiaNIMPolicyClient preflight (§5) then generate_candidate_frontier(...)
      write valid_candidates.jsonl + model_generation_rejections.jsonl;
      append decision + model_generation_rejection replay records
 4. Codex path (default on): CodexToolPlanner deterministic plan
      inspect → frontier → compare → simulate → stage; commit only with --commit AND
      simulation says confirmation not required AND authority profile allows (D19);
      every tool call/receipt lands in replay
 5. self-play: SelfPlayRunner(replay=...) with --self-play-backend, --episodes
      (backend grant policy from environment/selfplay_backends.py applies)
 6. invariants: check_replay over this run's replay → invariant_report.json
 7. tuning: train_offline_policy reduction → offline_policy_report.json + policy_tuning.json
 8. frontier diff: build_diff(seed observation, seed profile, this run's tuning, seed goal)
      → frontier_diff.json   # within-run learning-effect measurement
 9. scorecard: build_scorecard(replay, frontier_diff, offline_report) → scorecard.json
10. lab_report.json: metrics (§6) + expectation_results (§3.4 checks, good/bad intent checks)
11. finalize manifest (status, ended_at)
```

`--from-replay` runs only steps 6–11 over an existing replay file (used to import real dogfood days, §10.1); manifest records `runtime_mode` from the flag and `status: "completed"` with `imported: true`.

### 8.3 `scripts/compare_lab_runs.py`

```text
--runs <glob...> | --batch <batch_id> | --reindex
--out <path>            comparison JSON (default experiments/reports/comparison_latest.json)
--md <path>             optional markdown table for humans
```

Groups `lab_report.json` rows by `(seed_id, runtime_mode)`, emits per-group metric columns (§6) and pooled batch metrics, and answers the day 3–4 questions mechanically: which seeds miss `expected_intent_hit`, which runs' `leader_changed_after_tuning` is true, and per-config ranking by `valid_frontier_rate` / `other_intent_rate` / `rejection_rate`. `--reindex` rebuilds `experiments/index.json` from run dirs (D14). Always exit 0 unless IO error — comparison is descriptive; gates live in `promote_policy.py`.

### 8.4 `scripts/promote_policy.py`

```text
--batch <batch_id>                      required
--thresholds <path>                     default experiments/configs/promotion_thresholds.json
--candidate-tuning <path>               default: train on the batch's pooled replay (§7.2 step 3)
--decide promote|hold|rollback          optional human override; recorded with human_note
```

Implements §7.2. Exit 0 on `promote`, 3 on `hold` (distinct code so CI can gate), 1 on infrastructure error.

### 8.5 Required code change (one)

`src/calendar_pilot/diffusiongemma/live.py`: add module-level `PROMPT_VERSION = "frontier_v1"` next to the frontier prompt; bump it whenever `_frontier_prompt` or `_frontier_response_format` changes. The manifest and Track-3 comparisons read it. Without this, "prompt_version" is unrecordable and model comparisons become anecdotal.

### 8.6 Track 3 — model/prompt experiment matrix

For live runs, the manifest already captures `model`, `prompt_version`, `decoding`, `policy_tuning_id`, frontier size, and rejection reasons (§4). Comparing two configs = two batches differing only in `CALENDAR_PILOT_NIM_MODEL` (or a `PROMPT_VERSION` bump), then `compare_lab_runs.py --batch` on each. Score on: `valid_frontier_rate`, `frontier_diversity_by_intent`, `other_intent_rate`, `rejection_rate`, `top_candidate_expected_reward`, wall-clock per run (record `ended_at - started_at`). Temperature/top_p sweeps wait for env knobs (D23, P11).

---

## 9. Track 5 — EventKit sandbox runbook (Gate E, days 7–8)

Do not go from deterministic provider directly to a real work calendar. The bridge is a dedicated sandbox calendar; the denial path when the env flag is absent is already validated.

Setup (once, on the dogfood Mac):

```text
1. Calendar.app → File → New Calendar → "On My Mac" → name it exactly: CalendarPilot SelfPlay
   (local calendar, not iCloud/work — no sync side effects)
2. In .env (or the shell):
     CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"
       # the Swift bridge matches calendarIdentifier OR title, so the title string is valid
     CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1        # backend gate (selfplay_backends.py)
     CALENDAR_PILOT_EVENTKIT_MUTATION=1
     CALENDAR_PILOT_REQUEST_EVENTKIT_ACCESS=1
3. First run triggers the macOS calendar-access (TCC) prompt for the invoking terminal/app — grant it.
```

Sequence:

```text
make live-eventkit-e2e                      # existing Gate E harness first
run_lab_experiment.py --runtime live_diffusiongemma \
  --self-play-backend swift_ipc_eventkit_sandbox --episodes 5 \
  --seed <each of the 2 designated seeds (§3.2)>
```

Pass checks (all from run artifacts, asserted by the day 7–8 exit criteria):

```text
create focus block → receipt has non-empty external_event_id
rollback           → event removed; rollback_state verified (no I2 violation)
idempotency        → re-run same idempotency key → no duplicate (receipt indicates no-op/duplicate-suppressed)
containment        → zero mutations outside the sandbox calendar (Swift-enforced below Python;
                     denial receipts appear in replay if anything tries)
provider errors    → become receipts/replay records, never silent
```

---

## 10. Real dogfood with seeded shadow (Gate F, days 9–10)

### 10.1 Daily procedure

```text
1. Real run: use the app normally for the day (make dogfood-release / app frontend;
   CALENDAR_PILOT_RUNTIME_MODE=live_diffusiongemma). Give feedback in the UI —
   feedback becomes RewardEvents in the session replay under the app run dir (default runs/dogfood).
2. Import the day:
     run_lab_experiment.py --from-replay <app run dir>/replay.jsonl \
       --seed-id real_<user_scope_id> --batch dogfood_YYYYMMDD
3. Shadow run: the seed mapped in experiments/configs/shadow_map.json (D13):
     run_lab_experiment.py --seed experiments/seeds/<mapped seed>.json \
       --runtime live_diffusiongemma --self-play-backend swift_ipc_deterministic \
       --batch dogfood_YYYYMMDD
4. Compare: compare_lab_runs.py --batch dogfood_YYYYMMDD
   → two lab-shaped rows (real + shadow) with identical metric columns.
5. Tuning trained on the real day's replay; next-day frontier diff comes from the import step's
   frontier_diff.json. The shadow seed answers: does this policy change generalize,
   or is it overfit to one real run?
```

Two signal streams, as intended: real-human signal and synthetic-controlled signal.

### 10.2 Human feedback queue (state mapping — D21)

Queue rows derive from replay: any staged/committed receipt without a later reward record is `needs_feedback`. UI feedback maps onto existing `RewardEvent` kinds — no new contract fields:

```text
needs_feedback     (queue-only: receipt exists, no reward event yet)
accepted           → accepted
undone             → undone
ignored            → ignored
wrong              → explicit_wrong
not_needed         → explicit_not_needed
too_interruptive   → notification_dismissed
```

This turns dogfood into labeled data collection with zero schema invention. A dedicated queue viewer is P11; the mapping above is binding now so the data is well-formed from day 1.

---

## 11. What "full throttle on ML" means (unchanged, now with auditable arithmetic)

Not "turn on live NIM and ask it to do everything." It means:

```text
1. Generate many typed frontiers.        5. Run self-play pressure.
2. Retain all invalid generations.       6. Apply policy tuning.
3. Canonicalize every intent.            7. Compare the next frontier.
4. Score reward/right-moment heads.      8. Record human feedback.
                                         9. Promote or hold with a scorecard.
```

A good full-throttle week, with the counting rule pinned — a **candidate-level observation = one `decision` replay record**:

```text
20 seeds × 6 files each (1 base + 5 variants) = 120 seed files
cells A, B, C over all 120                     = 360 runs
+ a second live config (model or prompt bump) on B and C = +240 runs → 600 runs
each run ≥ 3 frontier decisions + 10 self-play episodes  → ≥ 7,800 candidate/episode rows
                                                            (comfortably > the 6,000 target)
```

At ~1–2 minutes per live run this is a few machine-days — batches run serially (D14); split across evenings/overnight via `--batch`.

---

## 12. Suggested 10-day plan (exit criteria are now assertions)

### Days 1–2: Lab v0

Deliver: `experiments/` tree + 4 scripts + Makefile targets + `.gitignore` entry + `PROMPT_VERSION` constant; the 5 starter seeds (no variants yet).

Run: starter 5 × cell A, starter 5 × cell B (`--batch batch_d2`).

Exit criteria:

```text
□ seed_calendar_corpus.py --validate exits 0
□ all 10 runs status == completed (or skipped with recorded skip_reason if NIM creds absent —
  in that case cell B repeats on day 3)
□ every completed run dir contains all 10 artifacts of §4.2
□ jq '.invariants.violations' scorecard.json == 0 for every run
□ compare_lab_runs.py --batch batch_d2 exits 0; comparison has one row per (seed, mode);
  other_intent_rate and rejection-rate columns populated (nonzero denominator on live runs)
```

### Days 3–4: Seed corpus expansion

Deliver: all 20 base seeds + generated variants (120 files), lints green, flagged seeds verified by L10.

Run: 120 × cell A; 120 × cell B; cell C on the 20 base seeds (`--batch batch_d4`).

Exit criteria:

```text
□ "which seeds does the model fail" is a query, not a judgment:
  comparison lists every run with expected_intent_hit == false, grouped by seed/persona
□ fixture expected_intent_hit rate ≥ 0.80 (else fix seeds or file policy bugs — decide per seed, log in DECISIONS.md)
□ "does tuning change later frontiers" is a column: leader_changed_after_tuning per run;
  flagged seeds' promotion-time diff pending day 5–6 batch
□ "rank prompts/models" works: two live configs compared per §8.6 with the §6 metric columns
```

### Days 5–6: Self-play lab

Deliver: batch with `swift_ipc_deterministic` on all 120 files; `production_shadow` on 5 selected base seeds; first candidate tuning + promotion attempt.

Exit criteria:

```text
□ scorecard.self_play.failure_modes non-empty on the seeds built to provoke them
  (expire_authority_grant variants show denied_actuation ≥ 1 — the §3.4 gated check)
□ denied actions replay-visible: acting.denials > 0 somewhere and every denial has a receipt row
□ promote_policy.py --batch … runs end-to-end and writes a promotion record;
  candidate tuning flips the leader on ≥ 3 flagged seeds (gate D11) — if hold, the record says which gate failed
□ D12 self-play penalty effect check passes
```

### Days 7–8: EventKit sandbox

Deliver: §9 setup + `make live-eventkit-e2e` + cell D on the 2 designated seeds; sandbox report = those runs' lab reports + receipts.

Exit criteria: the five pass checks of §9, asserted from run artifacts; zero I2/I6 violations.

### Days 9–10: Real dogfood with seeded shadow

Deliver: two dogfood days via §10.1 — each day yields real import run + shadow run + comparison + promotion attempt on the pooled `dogfood_YYYYMMDD` batch.

Exit criteria:

```text
□ ≥ 1 explicit-kind reward event per day (accepted / explicit_wrong / explicit_not_needed / undone / notification_dismissed)
□ human feedback changes the next frontier: day-2 frontier_diff (tuned on day-1 real replay)
  shows leader_changed == true OR |avg_reward_delta| > 0 on the real observation
□ shadow confirms or challenges: same tuning applied to the shadow seed — direction of top-intent
  change recorded in the comparison (agreement is signal either way)
□ no evidence corruption: invariant_violations == 0; no missing rollback state (I2 == 0)
□ other_intent_rate not rising: day-2 pooled rate ≤ day-1 pooled rate + 0.02
```

---

## 13. Infrastructure locked into v0 vs deferred

Locked in v0 (already specified above): the derived experiment registry (`index.json`, §4.3/D14), the promotion record (§7.2), the feedback-state mapping (§10.2), the gate board mapping (§7.2).

Deferred to P11 — pinned enough that building them later requires no new decisions:

- **Frontier leaderboard**: rank candidates/tunings by `expected_reward`, post-tuning delta, self-play robust reward, regret-adjusted and social-risk-adjusted reward. All columns already exist in `frontier_diff.json`/`lab_report.json`; the leaderboard is a view over `index.json`. Canonical question: *which candidate would have won before tuning, and which wins now* → `per_candidate_delta` ranks.
- **Seed failure dashboard**: group `expected_intent_hit == false` and `failure_modes` by intent / persona / perturbation / denial / rejection reason / `right_moment_decision` — again a view over the index (example finding it should surface: "create_prep_block works on AE seeds but over-notifies on high-fatigue researcher seeds").
- **Feedback queue viewer** over the §10.2 derivation.

---

## 14. Non-goals for v0

Databases; dashboards beyond `compare_lab_runs.py` output; automatic seed-similarity for shadow mapping (D13); multi-day episode simulation (D3); a `Persona(...)` synthetic-calendar generator (§8.1); provider OAuth or any non-sandbox provider writes; parallel experiment execution (D14); temperature/top_p sweeps (D23); tier-5 social actuation (D19); merging tunings across batches automatically (D16). Each has a pinned v0 substitute above.

---

## 15. Research ideas once the lab exists (P11+, unchanged in intent)

1. **Counterfactual frontier training** — keep top rejected alternatives per chosen candidate, self-play their outcomes, train on deltas, not just winners. The lab prerequisite (full frontiers + `per_candidate_delta` retained per run) ships in v0.
2. **Right-moment as a separate policy** — split *what to do* from *when to expose/commit/batch/ask*; the temporal controller (`diffusiongemma/temporal_controller.py`) already records act/stage/wait/digest/refresh modes, and v0 records `top_candidate_right_moment_decision` per run, so "good action, bad time" becomes measurable before it becomes learnable.
3. **Autonomy curriculum** — promote autonomy by seed family: recommend-only everywhere → stage private reversible on low-regret seeds → auto-write private reversible on repeatedly passing seeds → social only in sandbox with explicit `commit_social`. Gate on the same promotion machinery (§7) applied per seed family.
4. **Prompt/model ablations** — `prompt_v1` vs `prompt_v2` (via `PROMPT_VERSION`), with/without tuning, with/without seed metadata, with/without self-play findings; scored on the §6 columns plus human preference.
5. **Biography learning tests** — seed `preference_claims` (e.g. "dismisses evening suggestions"), then test: does the model learn the claim, overgeneralize it, respond to profile repair, and decay stale claims? Seeds already carry claims with confidences, so these become perturbation-style variants.

---

## 16. P10 acceptance criteria (all machine-checkable)

```text
□ 120 seed files (20 base + 100 variants) pass seed_calendar_corpus.py --validate
□ ≥ 100 runs with status == completed in experiments/index.json after --reindex
□ 0 invariant violations across all completed runs (max over index == 0)
□ frontier_diff.json and scorecard.json present in every completed run dir
□ human feedback captured on each dogfood day (≥ 1 explicit-kind reward event per day)
□ ≥ 1 promotion record exists; its candidate tuning changes the leader on ≥ 3 flagged seeds
□ D12 self-play penalty effect check passes on the promoted (or best held) tuning
□ EventKit sandbox: cell D runs on both designated seeds pass all five §9 checks
```

---

## 17. Bottom line

Stop proving the skeleton. The next move is measured aggression:

```text
Seed calendars.            Use self-play as pressure.
Run lots of frontiers.     Use human feedback as truth.
Keep every rejection.      Promote policies only through scorecards.
Train from replay.
Compare the next frontier.
```

Build only as much lab as makes the ML signal repeatable — the four scripts, the seed corpus, and the gates above — then go full throttle. Milestone name: **P10 — Seeded ML Lab and Recommendation Dogfood**.

---

# Codex implementation run log

## thin_lab_codex_20260703

Started: 2026-07-03 PDT

Checkpoint:

```text
dc6c498 Add thin lab implementation spec
```

Progress:

```text
[2026-07-03 PDT] Read thin-lab.md end to end and read the Computer Use policy before UI testing.
[2026-07-03 PDT] Committed the current non-Do-not-reference checkpoint before implementation. The checkpoint intentionally captured the current ML-testing.md deletion and new thin-lab.md file.
[2026-07-03 PDT] Started Track 1 implementation: experiments tree, four lab scripts, Makefile/.gitignore changes, prompt-version constant, and Lab surface routing.
[2026-07-03 PDT] Materialized the full deterministic seed corpus: 20 base seeds plus 100 generated perturbation variants. `seed_calendar_corpus.py --write-base-seeds --generate-variants --validate` passed across all 120 seed files.
[2026-07-03 PDT] Added and smoke-tested the lab execution loop. `run_lab_experiment.py` completed a fixture run for `seed_ae_renewal_week_high_pressure`, wrote the full artifact set, `compare_lab_runs.py --reindex` rebuilt `experiments/index.json`, and `promote_policy.py --batch thin_lab_smoke` wrote a hold record with explicit failed gates for missing flagged-seed/D12 evidence.
[2026-07-03 PDT] Ran the days-1/2 starter matrix locally: 5 fixture runs completed and 5 live DiffusionGemma runs skipped with `nim_missing_credential`. Fixture metrics: valid_frontier_rate=1.00, other_intent_rate=0.082, invariant_violations_max=0, bad_intent_committed=0, expected_intent_hit_rate=0.60. `promote_policy.py --batch thin_lab_starter_fixture` wrote a hold record because D11/D12 evidence is not present.
[2026-07-03 PDT] Tested app routing through `/api/view` and Chrome/Computer Use. The Lab tab showed `Seeded ML experiments` with index loaded and 11 rows; clicking `Run self-play` originally exposed a legacy-state refresh bug, then the frontend was patched to refetch `/api/view` after POSTs. Retest confirmed Lab and the legacy inspector `Self-play` tab keep the seeded experiment panel loaded after self-play.
[2026-07-03 PDT] Probed the two EventKit-designated seeds through cell D; both wrote skipped lab rows with `nim_missing_credential` before EventKit preflight. Final `make lab-compare` rebuilt `experiments/index.json` with 13 rows: 6 completed and 7 skipped.
[2026-07-03 PDT] Verification passed: script py_compile, `make lab-validate-seeds`, targeted frontend tests, full Python unittest discovery (147 tests, 10 skipped), Swift package tests (17 tests), and `scripts/run_browser_e2e.py`.
[2026-07-03 PDT] Exercised dogfood import mode with `run_lab_experiment.py --from-replay` against the smoke replay. `comparison_latest` was rebuilt with 14 indexed rows.
```
