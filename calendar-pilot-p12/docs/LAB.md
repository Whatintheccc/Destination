# Lab

The lab is the operating system for CalendarPilot experiments. It makes model generation, acting, self-play, tuning, and promotion comparable rather than demo-driven.

## Experiment cells

| Cell | Runtime | Purpose |
|---|---|---|
| A | fixture heuristic | Baseline deterministic policy and Swift stub. |
| B | live DiffusionGemma/NIM | Typed model frontier quality under rejection tracking. |
| C | live Codex E2E | Tool-planning and explanation health outside the lab matrix. |
| D | provider sandbox | EventKit/deterministic provider transaction and rollback verification. |

## EventKit sandbox setup

Cell D EventKit runs use a dedicated sandbox calendar title, normally:

```text
CalendarPilot SelfPlay
```

Set `CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1` and
`CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"`.
The EventKit bridge matches the configured value by calendar identifier or title
and rejects explicit unavailable calendar targets instead of falling back to the
default calendar.

For setup, the bridge command `ensure_calendar` creates or returns the named
calendar. It is local-only by default. If a dogfood Mac exposes no local
EventKit source, `source_policy: default_if_no_local` is an explicit test setup
override; reports must record that the sandbox calendar was not local-only.

A mutating EventKit result is accepted only from the user-visible app-bundled
bridge identity. Build and launch `dist/CalendarPilot.app`, set
`CALENDAR_PILOT_EVENTKIT_BRIDGE` to:

```text
dist/CalendarPilot.app/Contents/Resources/app/bin/
CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge
```

Then run `make live-eventkit-e2e` with
`CALENDAR_PILOT_REQUIRE_EVENTKIT=1`, `CALENDAR_PILOT_EVENTKIT_MUTATION=1`, and
the two sandbox variables above. A raw Swift binary or an IDE/terminal permission
surface is health evidence only. The canonical command and JSON assertions live in
[`../../compression-roadmap.md`](../../compression-roadmap.md), §4.9.

## Required artifacts per run

Every run directory should contain:

```text
manifest.json
observation.json
profile.json
valid_candidates.jsonl
model_generation_rejections.jsonl
replay.jsonl
invariant_report.json
offline_policy_report.json
policy_tuning.json
frontier_diff.json
scorecard.json
lab_report.json
```

Large artifacts are referenced from replay with `artifact_ref` rows instead of being embedded.

## Gates

Entry bars are lower data-hygiene bars used before tuning work; promotion gates are stricter release bars. Both live in `experiments/configs/promotion_thresholds.json`.

Core metrics:

```text
valid_frontier_rate
model_generation_rejection_rate
empty_frontier_rate
OTHER_intent_rate
expected_intent_hit_rate
hard_invariant_violations
candidate_vs_CURRENT marginal frontier delta
variance-adjusted self-play penalty effect
provider rollback verification rate
```

## Promotion rule

A tuning candidate is promotable only if it improves against `experiments/promoted/CURRENT.json` on the seed matrix, names all known regressions, avoids engagement gaming/social creep/regret regression, and writes a promotion record.

## Simulator versions

`sim_v2.1` is the default for new lab batches and is grounded in seed/profile truth, response windows, interruption-tolerance evidence, reversibility, and social friction. `sim_v2` remains available for continuity. Neither simulator may consume candidate `predicted_*` heads as simulator truth.
