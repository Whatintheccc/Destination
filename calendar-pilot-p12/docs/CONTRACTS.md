# Contracts

CalendarPilot uses checked contracts, not generated contracts. JSON Schema files in `contracts/` are public truth; Python dataclasses and Swift Codable mirrors are checked by parity tests and golden vectors.

## Version policy

`contracts/VERSIONS.json` lists the current schema version for each contract. Additive fields may land under the same major contract version. Breaking changes require:

1. a version bump in `contracts/VERSIONS.json`;
2. a migration note in this document;
3. new golden vectors under `contracts/testdata/`;
4. parity updates for Python and Swift when the object crosses the runtime boundary.

Replay rows append `record_schema_version`; current runtime rows use `r1`. Missing or unsupported versions are counted as skipped by reducers and must not be silently lifted into current training evidence.

## Cross-runtime contracts

| Contract | Schema | Python owner | Swift mirror |
|---|---|---|---|
| RawCalendarObservation | `contracts/raw_calendar_observation.schema.json` | `types.RawCalendarObservation` | `CalendarContracts.swift` |
| CandidateCalendarAction | `contracts/candidate_calendar_action.schema.json` | `types.CandidateCalendarAction` | `CalendarContracts.swift` |
| CalendarActionReceipt | `contracts/calendar_action_receipt.schema.json` | `types.CalendarActionReceipt` | `CalendarContracts.swift` |
| AuthorityGrant | `contracts/authority_grant.schema.json` | `types.AuthorityGrant` | `WriteAuthorityBroker.swift` |
| RewardEvent | `contracts/reward_event.schema.json` | `types.RewardEvent` | `CalendarContracts.swift` |
| CodexToolCall / Receipt | `contracts/codex_tool_*.schema.json` | `types.CodexTool*` | `CodexToolContracts.swift` |
| ActionEnvelope | `contracts/action_envelope.schema.json` | `environment.envelope.ActionEnvelope` | checked at boundary; Swift receipts fill envelope fields |
| ReplayRecord | `contracts/replay_record.schema.json` | `replay.ReplayRecord` | JSONL boundary |
| PolicyTuning | `contracts/policy_tuning.schema.json` | `types.PolicyTuning` | read-only promotion artifact |

Lab-only schemas live under `contracts/lab/`; they are not Swift mirrored.

## Replay row types

Existing durable row types remain supported: `decision`, `receipt`, `reward`, `self_play_episode`, `adversary_finding`, `codex_tool_call`, `codex_tool_receipt`, `candidate_receipt`, `router_decision`, `model_generation_rejection`, and `envelope_transition`.

New row types:

| Type | Purpose |
|---|---|
| `frontier_generation` | One model/policy frontier attempt, including valid ids, rejection summary, taxonomy health, backend, and prompt/model provenance. |
| `provider_transaction` | Provider preview/commit/verify/rollback facts, external ids, idempotency key, rollback verification, and errors. |
| `tuning_reduction` | Reducer provenance: input replay, partitions, weights, skipped rows, output tuning id/path. |
| `artifact_ref` | Hash reference to large derived artifacts such as scorecards, frontier diffs, and promotion records. |

## Migration notes

- `RewardEvent.provenance` accepts legacy values (`observed`, `provider`, `adversarial`, `model`) and maps them in reducers to the training partitions `human_ui`, `self_play_simulator`, and `synthetic_demo`.
- `schema_version` on older ActionEnvelope payloads is kept for browser compatibility; `envelope_version` is the canonical envelope version.

## P12 signal contracts

P12 adds signal governance contracts:

| Contract | Schema | Python owner |
|---|---|---|
| SemanticSignal | `contracts/semantic_signal.schema.json` | `types.SemanticSignal` |
| SignalEstimatorReport | `contracts/signal_estimator_report.schema.json` | `types.SignalEstimatorReport` |
| LabelActivation | `contracts/label_activation.schema.json` | `types.LabelActivation` |
| BiographyDriftFinding | `contracts/biography_drift_finding.schema.json` | `types.BiographyDriftFinding` |
| MeasurementReport | `contracts/measurement_report.schema.json` | `scripts/make_measurement_report.py` |
| CalibrationReport | `contracts/calibration_report.schema.json` | `scripts/make_calibration_report.py` |
| ProviderCapabilityReport | `contracts/provider_capability_report.schema.json` | `scripts/make_provider_capability_report.py` |

Every `ReplayRecord` now carries `signal_stream: action | world | biography | derived | system`. Older rows are classified by `environment.signal_streams.infer_signal_stream` during load/checks.
