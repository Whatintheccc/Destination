# Lab

The lab is the operating system for CalendarPilot experiments. It makes model generation, acting, self-play, tuning, and promotion comparable rather than demo-driven.

## Experiment cells

| Cell | Runtime | Purpose |
|---|---|---|
| A | fixture heuristic | Baseline deterministic policy and Swift stub. |
| B | live DiffusionGemma/NIM | Typed model frontier quality under rejection tracking. |
| C | live Codex E2E | Tool-planning and explanation health outside the lab matrix. |
| D | provider sandbox | EventKit/deterministic provider transaction and rollback verification. |

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
