import Foundation

public struct UndoRecord: Codable, Hashable, Sendable {
    public var rollbackHandleID: String
    public var candidateID: String
    public var originalEvents: [RawCalendarEvent]
    public var generatedEventIDs: [String]
    public var createdAt: Date
}

public struct ActionMaterializer: Sendable {
    public init() {}

    public func materialize(candidate: CandidateCalendarAction, observation: RawCalendarObservation, authority: AuthorityDecision) -> (receipt: CalendarActionReceipt, newEvents: [RawCalendarEvent], undo: UndoRecord?) {
        guard authority.admitted else {
            return (
                CalendarActionReceipt(
                    receiptID: Self.receiptID(candidate.candidateID),
                    candidateID: candidate.candidateID,
                    executedAt: observation.observedAt,
                    executedBy: "CalendarPilotKernel",
                    authorityTierUsed: authority.tierUsed,
                    syncStatus: .denied,
                    rollbackHandleID: nil,
                    conflictCheckPassed: authority.reason != "conflict_detected",
                    deniedReason: authority.reason
                ),
                observation.events,
                nil
            )
        }

        var events = observation.events
        var generatedIDs: [String] = []
        for (idx, action) in candidate.actions.enumerated() {
            switch action.actionType {
            case .createEvent, .createFocusBlock, .addBuffer:
                guard let start = action.start, let end = action.end else { continue }
                let id = "evt_generated_\(candidate.candidateID.suffix(8))_\(idx)"
                generatedIDs.append(id)
                events.append(RawCalendarEvent(
                    eventID: id,
                    title: action.title,
                    start: start,
                    end: end,
                    calendarID: action.calendarID,
                    attendees: action.attendees,
                    isUserOwned: true,
                    isFlexible: true,
                    category: action.metadata["category"] ?? "generated"
                ))
            case .moveEvent, .resizeEvent:
                guard let eventID = action.eventID, let start = action.start, let end = action.end else { continue }
                events = events.map { event in
                    if event.eventID == eventID {
                        var moved = event
                        moved.start = start
                        moved.end = end
                        return moved
                    }
                    return event
                }
            case .deleteOwnEvent:
                if let eventID = action.eventID {
                    events.removeAll { $0.eventID == eventID && $0.isUserOwned }
                }
            case .doNothing, .notify, .askClarification, .batchTasks, .draftSchedulePlan, .autoApplyPlan, .undo:
                continue
            }
        }

        let rollbackID = candidate.reversibility == .none ? nil : "undo_\(candidate.candidateID.suffix(10))"
        let undo = rollbackID.map { UndoRecord(rollbackHandleID: $0, candidateID: candidate.candidateID, originalEvents: observation.events, generatedEventIDs: generatedIDs, createdAt: observation.observedAt) }
        let receipt = CalendarActionReceipt(
            receiptID: Self.receiptID(candidate.candidateID),
            candidateID: candidate.candidateID,
            executedAt: observation.observedAt,
            executedBy: "CalendarPilotKernel",
            authorityTierUsed: authority.tierUsed,
            syncStatus: .materialized,
            rollbackHandleID: rollbackID,
            conflictCheckPassed: true,
            generatedEventIDs: generatedIDs
        )
        return (receipt, events, undo)
    }

    public func revert(undo: UndoRecord) -> [RawCalendarEvent] {
        return undo.originalEvents
    }

    private static func receiptID(_ candidateID: String) -> String {
        "rcpt_\(abs(candidateID.hashValue))"
    }
}
