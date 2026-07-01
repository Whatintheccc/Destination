import Foundation

public struct CodexToolBridge: Sendable {
    public var kernel: CalendarKernel

    public init(kernel: CalendarKernel = CalendarKernel()) {
        self.kernel = kernel
    }

    public func stage(candidate: CandidateCalendarAction, observation: RawCalendarObservation, call: CodexToolCall) -> CodexToolReceipt {
        let stagedIDs = candidate.actions.enumerated().map { idx, action in
            "stage_\(action.actionType.rawValue)_\(candidate.candidateID.suffix(8))_\(idx)"
        }
        let requiresSocialConfirmation = !candidate.affectedPeopleIDs.isEmpty && candidate.actions.contains { action in
            switch action.actionType {
            case .moveEvent, .resizeEvent, .deleteOwnEvent, .autoApplyPlan:
                return true
            default:
                return false
            }
        }
        return CodexToolReceipt(
            toolCallID: call.toolCallID,
            toolName: .stageActionPacket,
            status: .staged,
            output: [
                "candidate_id": JSONValue(candidate.candidateID),
                "staged_action_ids": JSONValue(stagedIDs.joined(separator: ",")),
                "requires_social_confirmation": JSONValue(String(requiresSocialConfirmation))
            ],
            deniedReason: requiresSocialConfirmation ? "requires social actuation confirmation before commit" : nil,
            requiresUserConfirmation: true,
            createdAt: observation.observedAt
        )
    }

    public func commit(candidate: CandidateCalendarAction, observation: RawCalendarObservation, call: CodexToolCall) -> CodexToolReceipt {
        let (receipt, _) = kernel.authorizeAndMaterialize(candidate: candidate, observation: observation, grantedAuthorityTier: call.requestedAuthorityTier)
        return CodexToolReceipt(
            toolCallID: call.toolCallID,
            toolName: .requestCommit,
            status: receipt.deniedReason == nil ? .succeeded : .denied,
            output: [
                "candidate_id": JSONValue(candidate.candidateID),
                "sync_status": JSONValue(receipt.syncStatus.rawValue),
                "actuation_mode": JSONValue(receipt.actuationMode.rawValue)
            ],
            swiftReceiptID: receipt.receiptID,
            deniedReason: receipt.deniedReason,
            requiresUserConfirmation: false,
            createdAt: observation.observedAt
        )
    }

    public func undo(rollbackHandleID: String, call: CodexToolCall) -> CodexToolReceipt {
        let restored = kernel.undo(rollbackHandleID: rollbackHandleID)
        return CodexToolReceipt(
            toolCallID: call.toolCallID,
            toolName: .requestUndo,
            status: restored == nil ? .denied : .succeeded,
            output: ["rollback_handle_id": JSONValue(rollbackHandleID)],
            deniedReason: restored == nil ? "rollback handle not found" : nil,
            requiresUserConfirmation: false
        )
    }
}
