# P12 Signal Streams

P12 separates human evidence into governed streams so the learner does not treat an invented human state as truth.

## Streams

| Stream | Contents | Role |
|---|---|---|
| `action` | accept, undo, dismiss, ignore, edit, explicit wrong/not needed, label disabled, feedback | The only reward truth and the measurement stream for estimators. |
| `world` | calendar observations, provider transactions, provider truth, preview/verify/rollback facts | State and context for generation/ranking. |
| `biography` | declared profile settings, conversational claims, corrections, drift findings | User-owned prior; capped, editable, never reward. |
| `derived` | `SemanticSignal`, `SignalEstimatorReport` | Estimated human patterns with evidence, confidence, half-life, and user control. |
| `system` | decisions, receipts, tool calls, frontier generations, tuning reductions, artifact refs | Execution and lab metadata. |

## B-invariants

- **B1** every derived `SemanticSignal` cites at least one action/world evidence row.
- **B2** no signal or label can influence authority tier, scope, grants, or grant issuance.
- **B3** every label activation change is a user-attributed replay row.
- **B4** reward reduction consumes `action` stream rows only.
- **B5** declared-vs-derived conflicts emit `BiographyDriftFinding`; they are never silently overwritten.
- **B6** estimator outputs carry `estimator_version`, and the same version runs on synthetic and real streams.

## Interruption-Tolerance Policy

The old `UserBiography.notification_fatigue` scalar is no longer part of the runtime biography. Stale inputs carrying that key are tolerated at parse time but ignored. The replacement is `interruption_tolerance_v1`, a derived signal over observable behavior such as dismissal streaks, hourly dismissal rates, response-latency trends, and undo-after-accept events.
