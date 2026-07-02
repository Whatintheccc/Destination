
# API and Contract Sketch

## RawCalendarObservationV1

A raw observation is the bridge between Swift and the policy layer. The Python contract lives in `calendar_pilot.types.RawCalendarObservation`; the Swift mirror lives in `CalendarContracts.swift`.

## CandidateCalendarActionV2

A candidate contains:

- action program: one or more atomic calendar actions;
- required authority tier;
- affected events/people;
- reversibility;
- predicted reward heads;
- recommended execution/notification time;
- explanation plan;
- `model_story`, `counterfactual`, `control_notes`, `reward_breakdown`, `right_moment_score`, and `simulated_outcomes` as canonical cross-runtime inspection fields.

## CalendarActionReceiptV2

A receipt is emitted when Swift stages or applies an action. It contains:

- action program digest;
- authority tier used;
- sync/materialization status;
- rollback handle if reversible;
- conflict check result;
- generated event IDs;
- staged action IDs for draft/notification/clarification actions;
- rejected action types for denial receipts;
- provider ID and actuation mode.

## RewardEventV1

A reward event is emitted later and can include:

- accepted;
- edited;
- undone;
- deleted later;
- ignored;
- explicit useful/wrong/not needed;
- notification dismissed;
- survived until event;
- downstream conflict;
- reengagement.


## Provider boundary

The provider boundary is declared but not implemented. Swift owns real OAuth, provider sync, conflict truth, and write execution through `CalendarProviderAdapter`; Python may only propose and simulate action programs. Stub adapters exist for Google, Apple, and Microsoft.
