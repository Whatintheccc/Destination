import Foundation

public struct CodexToolBridge: Sendable {
    public var kernel: CalendarKernel

    public init(kernel: CalendarKernel = CalendarKernel()) {
        self.kernel = kernel
    }

    private func grant(from call: CodexToolCall) -> AuthorityGrant? {
        if let grant = call.authorityGrant { return grant }
        if let id = call.input["authority_grant_id"]?.stringValue { return kernel.resolveGrant(id) }
        return nil
    }

    public func stage(candidate: CandidateCalendarAction, observation: RawCalendarObservation, call: CodexToolCall) -> CodexToolReceipt {
        let grant = grant(from: call)
        let receipt = kernel.stage(candidate: candidate, observation: observation, authorityGrant: grant, requestedAuthorityTier: call.requestedAuthorityTier)
        return CodexToolReceipt(
            toolCallID: call.toolCallID,
            toolName: .stageActionPacket,
            status: receipt.deniedReason == nil ? .stageable : .denied,
            output: [
                "candidate_id": JSONValue(candidate.candidateID),
                "staged_action_ids": JSONValue(receipt.stagedActionIDs.map { JSONValue($0) }),
                "stage_state": JSONValue(receipt.stageState.rawValue),
                "swift_receipt": JSONValue.object([
                    "receipt_id": JSONValue(receipt.receiptID),
                    "sync_status": JSONValue(receipt.syncStatus.rawValue),
                    "actuation_mode": JSONValue(receipt.actuationMode.rawValue)
                ])
            ],
            swiftReceiptID: receipt.receiptID,
            deniedReason: receipt.deniedReason,
            requiresUserConfirmation: receipt.stageState == .requiresConfirmation || receipt.stageState == .stageable,
            stageState: receipt.stageState,
            authorityGrantID: receipt.authorityGrantID,
            correlationID: candidate.candidateID,
            createdAt: observation.observedAt
        )
    }

    public func commit(candidate: CandidateCalendarAction, observation: RawCalendarObservation, call: CodexToolCall) -> CodexToolReceipt {
        let grant = grant(from: call)
        let (receipt, _) = kernel.authorizeAndMaterialize(candidate: candidate, observation: observation, authorityGrant: grant, requestedAuthorityTier: call.requestedAuthorityTier)
        return CodexToolReceipt(
            toolCallID: call.toolCallID,
            toolName: .requestCommit,
            status: receipt.deniedReason == nil ? .committed : .denied,
            output: [
                "candidate_id": JSONValue(candidate.candidateID),
                "sync_status": JSONValue(receipt.syncStatus.rawValue),
                "actuation_mode": JSONValue(receipt.actuationMode.rawValue),
                "stage_state": JSONValue(receipt.stageState.rawValue)
            ],
            swiftReceiptID: receipt.receiptID,
            deniedReason: receipt.deniedReason,
            requiresUserConfirmation: false,
            stageState: receipt.stageState,
            authorityGrantID: receipt.authorityGrantID,
            correlationID: candidate.candidateID,
            createdAt: observation.observedAt
        )
    }

    public func undo(rollbackHandleID: String, call: CodexToolCall) -> CodexToolReceipt {
        let grant = grant(from: call)
        let receipt = kernel.undo(rollbackHandleID: rollbackHandleID, authorityGrant: grant)
        return CodexToolReceipt(
            toolCallID: call.toolCallID,
            toolName: .requestUndo,
            status: receipt.deniedReason == nil ? .committed : .denied,
            output: ["rollback_handle_id": JSONValue(rollbackHandleID), "stage_state": JSONValue(receipt.stageState.rawValue)],
            swiftReceiptID: receipt.receiptID,
            deniedReason: receipt.deniedReason,
            requiresUserConfirmation: false,
            stageState: receipt.stageState,
            authorityGrantID: receipt.authorityGrantID,
            correlationID: rollbackHandleID
        )
    }
}
