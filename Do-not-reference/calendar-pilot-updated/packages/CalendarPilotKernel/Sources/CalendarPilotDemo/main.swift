import Foundation
import CalendarPilotKernel

let now = ISO8601DateFormatter().date(from: "2026-07-01T08:00:00-07:00")!
let callStart = ISO8601DateFormatter().date(from: "2026-07-01T15:00:00-07:00")!
let callEnd = ISO8601DateFormatter().date(from: "2026-07-01T16:00:00-07:00")!
let prepStart = ISO8601DateFormatter().date(from: "2026-07-01T14:15:00-07:00")!
let prepEnd = ISO8601DateFormatter().date(from: "2026-07-01T14:45:00-07:00")!

let observation = RawCalendarObservation(
    observationID: "obs_swift_demo",
    userScopeID: "local_demo_user",
    observedAt: now,
    timeZoneID: "America/Los_Angeles",
    events: [
        RawCalendarEvent(eventID: "evt_client", title: "Client renewal call", start: callStart, end: callEnd, calendarID: "work", attendees: ["client@example.com"], isUserOwned: false, isFlexible: false, category: "external_meeting")
    ]
)

let candidate = CandidateCalendarAction(
    candidateID: "cand_swift_demo",
    intent: "create_prep_block",
    actions: [AtomicCalendarAction(actionType: .createEvent, title: "Prep for Client renewal call", start: prepStart, end: prepEnd, calendarID: "work", metadata: ["category": "prep"])],
    targetCalendars: ["work"],
    affectedEventIDs: ["evt_client"],
    affectedPeopleIDs: ["client@example.com"],
    reversibility: .high,
    requiredAuthorityTier: 3,
    predictedAcceptance: 0.8,
    predictedUtility: 0.8,
    predictedEngagement: 0.2,
    predictedRegret: 0.05,
    predictedInterruptionCost: 0.1,
    predictedSocialRisk: 0.02,
    expectedReward: 1.7,
    explanation: "Create prep before external meeting."
)

let kernel = CalendarKernel()
let (receipt, events) = kernel.authorizeAndMaterialize(candidate: candidate, observation: observation, grantedAuthorityTier: 3)
print("Receipt: \(receipt.syncStatus.rawValue), rollback=\(receipt.rollbackHandleID ?? "none"), generated=\(receipt.generatedEventIDs)")
print("Event count after materialization: \(events.count)")
