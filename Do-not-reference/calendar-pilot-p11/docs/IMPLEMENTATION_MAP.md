# Implementation Map

| Direction requirement | Repo location |
|---|---|
| Trajectory substrate | `environment/trace.py`, `environment/envelope.py`, `replay.py` |
| Frontier façade and rejection capture | `diffusiongemma/frontier_service.py`, `codex/tools.py` |
| Canonical intent taxonomy | `environment/taxonomy.py` |
| Action lifecycle | `environment/action_lifecycle.py` |
| Rate-limited mutation path | `environment/action_lifecycle.py` |
| Provider transaction contract | `providers/base.py`, `providers/deterministic.py`, `providers/apple_eventkit.py`, `docs/PROVIDER_BOUNDARY.md` |
| Swift authority and rollback | `swift_bridge/*`, `packages/CalendarPilotKernel` |
| Replay record versions/new row types | `replay.py`, `contracts/replay_record.schema.json` |
| Invariants | `environment/invariants.py`, `scripts/check_invariants.py` |
| Simulator-versioned self-play | `diffusiongemma/self_play.py` |
| Offline reduction / tuning | `scripts/train_offline_policy.py`, `types.PolicyTuning`, `contracts/policy_tuning.schema.json` |
| Incumbent frontier comparison | `scripts/run_frontier_diff.py`, `experiments/promoted/CURRENT.json` |
| Autonomy matrix | `configs/autonomy_matrix.json`, `codex/planner.py` |
| Lab artifacts and gates | `scripts/run_lab_experiment.py`, `scripts/compare_lab_runs.py`, `scripts/promote_policy.py`, `experiments/configs/promotion_thresholds.json` |
| Current docs | `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/LAB.md`, `docs/SELF_PLAY.md`, `docs/PROVIDER_BOUNDARY.md` |
| Historical docs | `docs/history/` |
