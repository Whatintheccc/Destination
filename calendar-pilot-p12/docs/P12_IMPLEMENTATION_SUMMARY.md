# P12 Implementation Summary

This pass advances CalendarPilot from the P11 trajectory substrate into the P12 signal-plane direction: **Lab as Instrument, Policy as Product, Signals as Truth**.

## Implemented

- Added governed replay signal streams: `action`, `world`, `biography`, `derived`, and `system`.
- Added `signal_stream` to `ReplayRecord` with compatibility inference for legacy rows.
- Added P12 B-invariants to `environment.invariants`:
  - B0 stream validity
  - B1 evidence-cited derived signals
  - B2 labels never gate authority
  - B3 activation changes are audited
  - B4 reward purity: reward rows must be ActionStream
  - B5 biography drift findings are explicit
  - B6 estimator versioning
- Added `interruption_tolerance_v1`, a deterministic signal estimator over notification/action behavior.
- Updated pressure extraction and `sim_v2.1` to use behavioral estimator output rather than the legacy `UserBiography.notification_fatigue` scalar.
- Stopped `BiographyStore.update_from_reward` from mutating `notification_fatigue`; reward events now remain ActionStream evidence.
- Added `SemanticSignal`, `SignalEstimatorReport`, `LabelActivation`, and `BiographyDriftFinding` Python contracts.
- Added `CodexSemanticAnnotator` for evidence-cited semantic label proposals.
- Added `LabelRegistry` for user-governed activation/disable controls with an explicit authority barrier.
- Added P12 contracts for semantic signals, estimator reports, label activation, biography drift, measurement, calibration, provider capabilities, autonomy-family promotion, curriculum runs, and policy ablations.
- Added P12 scripts for signal estimation, measurement, calibration, dogfood shadow import/frontier/preview, provider capabilities, reward-head reports, self-play curriculum, autonomy-family promotion, live NIM schema gate, policy ablations, and P12 release.
- Added P12 docs: `p12-direction.md`, `docs/P12_TEST_FRAMEWORK.md`, and `docs/SIGNAL_STREAMS.md`.
- Added a frontend Signals surface scaffold that renders semantic signals, activation history, drift findings, and evidence coverage from the same replay-backed view state.

## Validation in this environment

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python3 scripts/check_invariants.py --replay tests/fixtures/replay_golden.jsonl --out /tmp/p12_invariants.json
PYTHONPATH=src python3 scripts/run_contract_vectors.py --out /tmp/p12_contract_vectors.json
PYTHONPATH=src python3 scripts/run_signal_estimators.py --out /tmp/p12_signal_estimator_report.json --replay-out /tmp/p12_signal_replay.jsonl
PYTHONPATH=src python3 scripts/make_measurement_report.py --out /tmp/p12_measurement_report.json
PYTHONPATH=src python3 scripts/make_calibration_report.py --out /tmp/p12_calibration_report.json
PYTHONPATH=src python3 scripts/make_provider_capability_report.py --out /tmp/p12_provider_capability_report.json
PYTHONPATH=src python3 scripts/run_p12_release.py
```

Results:

- Python tests: 158 tests OK, 10 skipped.
- Swift tests: 17 tests OK.
- Golden replay invariant check: OK.
- Contract vectors: OK.
- P12 signal estimator, measurement, calibration, provider capability, and release artifacts: generated successfully.

Browser E2E was attempted but could not launch because the local Playwright Chromium binary is not installed in this container.
