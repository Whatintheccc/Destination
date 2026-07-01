# API and Contract Sketch

## RawCalendarObservationV1

A raw observation is the bridge between Swift and the policy layer. The Python contract lives in `calendar_pilot.types.RawCalendarObservation`; the Swift mirror lives in `CalendarContracts.swift`.

## CandidateCalendarActionV1

A candidate contains:

- action program: one or more atomic calendar actions;
- required authority tier;
- affected events/people;
- reversibility;
- predicted reward heads;
- recommended execution/notification time;
- explanation plan.

## CalendarActionReceiptV1

A receipt is emitted when Swift stages or applies an action. It contains:

- action program digest;
- authority tier used;
- sync/materialization status;
- rollback handle if reversible;
- conflict check result;
- generated event IDs.

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
