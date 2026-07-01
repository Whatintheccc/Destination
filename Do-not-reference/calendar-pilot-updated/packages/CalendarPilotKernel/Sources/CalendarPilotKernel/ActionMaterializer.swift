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
                    generatedEventIDs: [],
                    stagedActionIDs: [],
                    rejectedActionTypes: candidate.actions.map { $0.actionType.rawValue },
                    providerID: "local_swift",
                    actuationMode: .denied,
                    deniedReason: authority.reason
                ),
                observation.events,
                nil
            )
        }

        var events = observation.events
        var generatedIDs: [String] = []
        var stagedIDs: [String] = []
        var rejectedActionTypes: [String] = []
        var materializedWrite = false
        var stagedOnly = false

        for (idx, action) in candidate.actions.enumerated() {
            switch action.actionType {
            case .createEvent, .createFocusBlock, .addBuffer, .batchTasks:
                guard let start = action.start, let end = action.end else { continue }
                let id = "evt_generated_\(candidate.candidateID.suffix(8))_\(idx)"
                generatedIDs.append(id)
                materializedWrite = true
                let category: String
                switch action.actionType {
                case .createFocusBlock:
                    category = "focus"
                case .batchTasks:
                    category = "task_batch"
                case .addBuffer:
                    category = "buffer"
                default:
                    category = action.metadata["category"] ?? "generated"
                }
                events.append(RawCalendarEvent(
                    eventID: id,
                    title: action.title,
                    start: start,
                    end: end,
                    calendarID: action.calendarID,
                    attendees: action.attendees,
                    location: "",
                    notes: action.metadata["notes"] ?? "",
                    isUserOwned: true,
                    isFlexible: true,
                    category: category
                ))
            case .moveEvent, .resizeEvent:
                guard let eventID = action.eventID, let start = action.start, let end = action.end else { continue }
                materializedWrite = true
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
                    materializedWrite = true
                    events.removeAll { $0.eventID == eventID && $0.isUserOwned }
                }
            case .draftSchedulePlan, .notify, .askClarification:
                stagedOnly = true
                stagedIDs.append("stage_\(action.actionType.rawValue)_\(candidate.candidateID.suffix(8))_\(idx)")
            case .autoApplyPlan, .undo:
                rejectedActionTypes.append(action.actionType.rawValue)
            case .doNothing:
                continue
            }
        }

        let rollbackID = materializedWrite && candidate.reversibility != .none ? "undo_\(candidate.candidateID.suffix(10))" : nil
        let undo = rollbackID.map { UndoRecord(rollbackHandleID: $0, candidateID: candidate.candidateID, originalEvents: observation.events, generatedEventIDs: generatedIDs, createdAt: observation.observedAt) }
        let status: CalendarSyncStatus = stagedOnly && !materializedWrite ? .staged : .materialized
        let mode: ActuationMode
        if materializedWrite {
            mode = .materializedWrite
        } else if stagedOnly {
            mode = stagedIDs.contains(where: { $0.contains("notify") }) ? .stagedNotification : .stagedDraft
        } else {
            mode = .noOp
        }
        let receipt = CalendarActionReceipt(
            receiptID: Self.receiptID(candidate.candidateID),
            candidateID: candidate.candidateID,
            executedAt: observation.observedAt,
            executedBy: "CalendarPilotKernel",
            authorityTierUsed: authority.tierUsed,
            syncStatus: status,
            rollbackHandleID: rollbackID,
            conflictCheckPassed: true,
            generatedEventIDs: generatedIDs,
            stagedActionIDs: stagedIDs,
            rejectedActionTypes: rejectedActionTypes,
            providerID: "local_swift",
            actuationMode: mode
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
