
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

    public func materialize(candidate: CandidateCalendarAction, observation: RawCalendarObservation, authority: AuthorityDecision, correlationID: String? = nil) -> (receipt: CalendarActionReceipt, newEvents: [RawCalendarEvent], undo: UndoRecord?) {
        guard authority.admitted else {
            return (
                CalendarActionReceipt(
                    receiptID: Self.receiptID(candidate: candidate, authority: authority, syncStatus: .denied, stageState: .denied, correlationID: correlationID),
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
                    deniedReason: authority.reason,
                    authorityGrantID: authority.grantID,
                    confirmationProvenance: authority.confirmationProvenance,
                    stageState: .denied,
                    correlationID: correlationID ?? candidate.candidateID
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
        let actions = Self.expandedActions(candidate.actions)

        for (idx, action) in actions.enumerated() {
            switch action.actionType {
            case .createEvent, .createFocusBlock, .addBuffer, .batchTasks, .autoApplyPlan:
                guard let start = action.start, let end = action.end else {
                    if action.actionType == .autoApplyPlan {
                        let id = "evt_generated_\(candidate.candidateID.suffix(8))_plan_\(idx)"
                        generatedIDs.append(id)
                        materializedWrite = true
                    }
                    continue
                }
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
                case .autoApplyPlan:
                    category = "auto_plan"
                default:
                    category = action.metadata["category"] ?? "generated"
                }
                events.append(RawCalendarEvent(
                    eventID: id,
                    title: action.title.isEmpty ? "CalendarPilot action" : action.title,
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
                        if !action.title.isEmpty { moved.title = action.title }
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
            case .undo:
                rejectedActionTypes.append(action.actionType.rawValue)
            case .doNothing:
                continue
            }
        }

        let rollbackID = materializedWrite && candidate.reversibility != .none ? StableID.make(prefix: "undo", parts: [candidate.candidateID, correlationID ?? ""]) : nil
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
        let stageState: StageState = materializedWrite ? .committed : (stagedOnly ? .requiresConfirmation : .noOp)
        let receipt = CalendarActionReceipt(
            receiptID: Self.receiptID(candidate: candidate, authority: authority, syncStatus: status, stageState: stageState, correlationID: correlationID),
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
            actuationMode: mode,
            deniedReason: nil,
            authorityGrantID: authority.grantID,
            confirmationProvenance: authority.confirmationProvenance,
            stageState: stageState,
            correlationID: correlationID ?? candidate.candidateID
        )
        return (receipt, events, undo)
    }

    public func revert(undo: UndoRecord) -> [RawCalendarEvent] {
        return undo.originalEvents
    }

    private static func receiptID(candidate: CandidateCalendarAction, authority: AuthorityDecision, syncStatus: CalendarSyncStatus, stageState: StageState, correlationID: String?) -> String {
        let actionSignature = expandedActions(candidate.actions)
            .map { action in action.actionType.rawValue }
            .joined(separator: ",")
        return StableID.make(prefix: "rcpt", parts: [
            candidate.candidateID,
            correlationID ?? "",
            syncStatus.rawValue,
            stageState.rawValue,
            authority.grantID ?? "no_grant",
            authority.reason ?? "",
            actionSignature,
        ])
    }

    private static func expandedActions(_ actions: [AtomicCalendarAction]) -> [AtomicCalendarAction] {
        var output: [AtomicCalendarAction] = []
        for action in actions {
            if action.actionType == .autoApplyPlan, let encoded = action.metadata["plan_actions"], let data = encoded.data(using: .utf8) {
                let decoder = JSONDecoder()
                decoder.dateDecodingStrategy = .iso8601
                if let nested = try? decoder.decode([AtomicCalendarAction].self, from: data), !nested.isEmpty {
                    output.append(contentsOf: nested)
                    continue
                }
            }
            output.append(action)
        }
        return output
    }
}