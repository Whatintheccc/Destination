import Foundation

public final class CalendarKernel: @unchecked Sendable {
    private let authorityBroker: WriteAuthorityBroker
    private let materializer: ActionMaterializer
    private var undoLedger: [String: UndoRecord]

    public init(authorityBroker: WriteAuthorityBroker = WriteAuthorityBroker(), materializer: ActionMaterializer = ActionMaterializer()) {
        self.authorityBroker = authorityBroker
        self.materializer = materializer
        self.undoLedger = [:]
    }

    public func authorizeAndMaterialize(candidate: CandidateCalendarAction, observation: RawCalendarObservation, grantedAuthorityTier: Int) -> (CalendarActionReceipt, [RawCalendarEvent]) {
        let decision = authorityBroker.authorize(candidate: candidate, observation: observation, grantedTier: grantedAuthorityTier)
        let output = materializer.materialize(candidate: candidate, observation: observation, authority: decision)
        if let undo = output.undo {
            undoLedger[undo.rollbackHandleID] = undo
        }
        return (output.receipt, output.newEvents)
    }

    public func undo(rollbackHandleID: String) -> [RawCalendarEvent]? {
        guard let undo = undoLedger.removeValue(forKey: rollbackHandleID) else { return nil }
        return materializer.revert(undo: undo)
    }
}
