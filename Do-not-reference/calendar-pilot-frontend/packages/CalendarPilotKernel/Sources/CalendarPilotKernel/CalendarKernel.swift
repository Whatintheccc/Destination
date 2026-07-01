import Foundation

public final class CalendarKernel: @unchecked Sendable {
    private let authorityBroker: WriteAuthorityBroker
    private let materializer: ActionMaterializer
    private var undoLedger: [String: UndoRecord]
    private var grants: [String: AuthorityGrant]

    public init(authorityBroker: WriteAuthorityBroker = WriteAuthorityBroker(), materializer: ActionMaterializer = ActionMaterializer()) {
        self.authorityBroker = authorityBroker
        self.materializer = materializer
        self.undoLedger = [:]
        self.grants = [:]
    }

    public func issueAuthorityGrant(userScopeID: String, maxAuthorityTier: Int, scopes: [String] = ["recommend", "stage", "commit_private", "undo"], confirmationProvenance: String, ttlSeconds: TimeInterval = 1800, confirmedByUser: Bool = true, issuedAt: Date = Date()) -> AuthorityGrant {
        let raw = "\(userScopeID)|\(maxAuthorityTier)|\(confirmationProvenance)|\(issuedAt.timeIntervalSince1970)"
        let grant = AuthorityGrant(
            grantID: "grant_\(abs(raw.hashValue))",
            userScopeID: userScopeID,
            maxAuthorityTier: maxAuthorityTier,
            scopes: scopes,
            issuedAt: issuedAt,
            expiresAt: issuedAt.addingTimeInterval(ttlSeconds),
            confirmationProvenance: confirmationProvenance,
            issuedBy: "CalendarPilotKernel",
            confirmedByUser: confirmedByUser
        )
        grants[grant.grantID] = grant
        return grant
    }

    public func resolveGrant(_ grantID: String) -> AuthorityGrant? {
        grants[grantID]
    }

    public func authorizeAndMaterialize(candidate: CandidateCalendarAction, observation: RawCalendarObservation, authorityGrant: AuthorityGrant?, requestedAuthorityTier: Int) -> (CalendarActionReceipt, [RawCalendarEvent]) {
        let resolved = authorityGrant.flatMap { grants[$0.grantID] }
        let decision = authorityBroker.authorize(candidate: candidate, observation: observation, grant: resolved, desiredTier: requestedAuthorityTier, commit: true)
        let output = materializer.materialize(candidate: candidate, observation: observation, authority: decision)
        if let undo = output.undo {
            undoLedger[undo.rollbackHandleID] = undo
        }
        return (output.receipt, output.newEvents)
    }

    @available(*, deprecated, message: "Use Swift-issued AuthorityGrant. Caller-supplied authority tiers are denied by design.")
    public func authorizeAndMaterialize(candidate: CandidateCalendarAction, observation: RawCalendarObservation, grantedAuthorityTier: Int) -> (CalendarActionReceipt, [RawCalendarEvent]) {
        let decision = authorityBroker.authorize(candidate: candidate, observation: observation, grant: nil, desiredTier: grantedAuthorityTier, commit: true)
        let output = materializer.materialize(candidate: candidate, observation: observation, authority: decision)
        return (output.receipt, output.newEvents)
    }

    public func stage(candidate: CandidateCalendarAction, observation: RawCalendarObservation, authorityGrant: AuthorityGrant?, requestedAuthorityTier: Int) -> CalendarActionReceipt {
        let resolved = authorityGrant.flatMap { grants[$0.grantID] }
        let decision = authorityBroker.authorize(candidate: candidate, observation: observation, grant: resolved, desiredTier: requestedAuthorityTier, commit: false)
        let stagedIDs = decision.admitted ? candidate.actions.enumerated().map { idx, action in "stage_\(action.actionType.rawValue)_\(candidate.candidateID.suffix(8))_\(idx)" } : []
        let peopleConfirm = authorityBroker.isPeopleAffectingMutation(candidate: candidate)
        return CalendarActionReceipt(
            receiptID: "stage_rcpt_\(abs(candidate.candidateID.hashValue))",
            candidateID: candidate.candidateID,
            executedAt: observation.observedAt,
            executedBy: "CalendarPilotKernel.stage",
            authorityTierUsed: decision.tierUsed,
            syncStatus: decision.admitted ? .staged : .denied,
            rollbackHandleID: nil,
            conflictCheckPassed: decision.reason != "conflict_detected_before_stage",
            generatedEventIDs: [],
            stagedActionIDs: stagedIDs,
            rejectedActionTypes: decision.admitted ? [] : candidate.actions.map { $0.actionType.rawValue },
            providerID: "local_swift",
            actuationMode: decision.admitted ? .stagedDraft : .denied,
            deniedReason: decision.reason,
            authorityGrantID: decision.grantID,
            confirmationProvenance: decision.confirmationProvenance,
            stageState: decision.admitted ? (peopleConfirm ? .requiresConfirmation : .stageable) : .denied,
            correlationID: candidate.candidateID
        )
    }

    public func preview(candidate: CandidateCalendarAction, observation: RawCalendarObservation, authorityGrant: AuthorityGrant?, requestedAuthorityTier: Int) -> CalendarActionReceipt {
        let resolved = authorityGrant.flatMap { grants[$0.grantID] }
        let decision = authorityBroker.authorize(candidate: candidate, observation: observation, grant: resolved, desiredTier: requestedAuthorityTier, commit: false)
        return CalendarActionReceipt(
            receiptID: "preview_rcpt_\(abs(candidate.candidateID.hashValue))",
            candidateID: candidate.candidateID,
            executedAt: observation.observedAt,
            executedBy: "CalendarPilotKernel.preview",
            authorityTierUsed: decision.tierUsed,
            syncStatus: decision.admitted ? .simulated : .denied,
            rollbackHandleID: nil,
            conflictCheckPassed: decision.reason != "conflict_detected_before_stage",
            generatedEventIDs: [],
            stagedActionIDs: [],
            rejectedActionTypes: decision.admitted ? [] : candidate.actions.map { $0.actionType.rawValue },
            providerID: "local_swift",
            actuationMode: decision.admitted ? .noOp : .denied,
            deniedReason: decision.reason,
            authorityGrantID: decision.grantID,
            confirmationProvenance: decision.confirmationProvenance,
            stageState: decision.admitted ? .simulated : .denied,
            correlationID: candidate.candidateID
        )
    }

    public func undo(rollbackHandleID: String, authorityGrant: AuthorityGrant?, observedAt: Date = Date(), requestedAuthorityTier: Int? = nil) -> CalendarActionReceipt {
        let resolved = authorityGrant.flatMap { grants[$0.grantID] }
        let desiredTier = requestedAuthorityTier ?? resolved?.maxAuthorityTier ?? 0
        let denied: String?
        if resolved == nil {
            denied = "missing Swift-issued authority grant for undo"
        } else if !resolved!.isLive(at: observedAt) {
            denied = "authority grant expired before undo"
        } else if !resolved!.confirmedByUser {
            denied = "authority grant lacks user confirmation provenance for undo"
        } else if desiredTier > resolved!.maxAuthorityTier {
            denied = "out-of-band authority tier rejected before undo"
        } else if !resolved!.allows("undo") {
            denied = "authority grant scope does not include undo"
        } else if undoLedger.removeValue(forKey: rollbackHandleID) == nil {
            denied = "rollback handle not found"
        } else {
            denied = nil
        }
        return CalendarActionReceipt(
            receiptID: "undo_rcpt_\(abs(rollbackHandleID.hashValue))",
            candidateID: rollbackHandleID,
            executedAt: observedAt,
            executedBy: "CalendarPilotKernel.undo",
            authorityTierUsed: resolved?.maxAuthorityTier ?? 0,
            syncStatus: denied == nil ? .reverted : .denied,
            rollbackHandleID: rollbackHandleID,
            conflictCheckPassed: true,
            providerID: "local_swift",
            actuationMode: denied == nil ? .noOp : .denied,
            deniedReason: denied,
            authorityGrantID: resolved?.grantID,
            confirmationProvenance: resolved?.confirmationProvenance,
            stageState: denied == nil ? .committed : .denied,
            correlationID: rollbackHandleID
        )
    }
}
