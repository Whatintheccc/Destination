# P11 Implementation Summary

This pass thickens the lab from a demo-friendly loop into a trajectory-grade substrate. It follows the direction in `docs/history/THICKENING_THE_LAB_P11.md`: treat `TraceEvent`, `ActionEnvelope`, `ReplayRecord`, and lab scorecards as the product spine; preserve Swift/provider authority; and make replay, provider verification, and self-play evaluation falsifiable.

## Implemented

- Refactored `/docs` into current-truth docs plus `docs/history/` archaeology.
- Added canonical contract/version files for replay records, action envelopes, policy tuning, lab reports, frontier diffs, and scorecards.
- Added `FrontierService` as a delegating wrapper around local/live policies with intent normalization, generation provenance, rejection capture, taxonomy health, and replay rows.
- Upgraded replay into a versioned trajectory journal with `frontier_generation`, `provider_transaction`, `tuning_reduction`, and `artifact_ref` records while retaining legacy-row compatibility.
- Added provider transaction semantics: `read_observation`, `preview`, `commit`, `verify`, and `rollback` across the base/provider adapters.
- Added commit/mutation rate-cap denial receipts in `ActionLifecycle`; cap failures are replay-visible denials, not exceptions.
- Added provider verification/readback rows for commit, verify, and rollback flows.
- Added `configs/autonomy_matrix.json` so Codex consults an action-family curriculum before private commits while leaving social mutations to Swift's social-actuation boundary.
- Added `sim_v2` self-play simulator that uses seed/profile/context truth instead of candidate-predicted acceptance/utility/regret heads.
- Updated offline tuning reduction to partition by runtime, backend, and reward provenance, plus marginal frontier diffs against promoted/current baselines.
- Strengthened replay invariants with causal-parent integrity, rollback support checks, artifact hash checks, and rate-cap denial visibility.

## Validation run in this snapshot

```bash
PYTHONPATH=src python -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl --out /tmp/calendarpilot_invariants.json
PYTHONPATH=src python scripts/run_contract_vectors.py --out /tmp/calendarpilot_contract_vectors.json
PYTHONPATH=src python scripts/run_frontier_diff.py --out /tmp/calendarpilot_frontier_diff.json
PYTHONPATH=src python scripts/train_offline_policy.py --replay tests/fixtures/replay_golden.jsonl --out /tmp/calendarpilot_offline_policy_report.json
```

Results:

- Python unit suite: 148 tests OK, 10 skipped.
- Swift unit suite: 17 tests OK.
- Golden replay invariant check: OK.
- Python contract vectors: OK.
- Frontier diff and offline policy report generated successfully.

## Notes

This is intentionally a strangler pass. Existing policy, Swift, frontend, and lab entry points remain callable; the new objects wrap and harden the seams before replacing behavior wholesale.
