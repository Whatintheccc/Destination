import Foundation

public struct AuthorityGrant: Codable, Hashable, Sendable {
    public var grantID: String
    public var userScopeID: String
    public var maxAuthorityTier: Int
    public var scopes: [String]
    public var issuedAt: Date
    public var expiresAt: Date
    public var confirmationProvenance: String
    public var issuedBy: String
    public var confirmedByUser: Bool

    enum CodingKeys: String, CodingKey {
        case grantID = "grant_id"
        case userScopeID = "user_scope_id"
        case maxAuthorityTier = "max_authority_tier"
        case scopes
        case issuedAt = "issued_at"
        case expiresAt = "expires_at"
        case confirmationProvenance = "confirmation_provenance"
        case issuedBy = "issued_by"
        case confirmedByUser = "confirmed_by_user"
    }

    public init(grantID: String, userScopeID: String, maxAuthorityTier: Int, scopes: [String], issuedAt: Date, expiresAt: Date, confirmationProvenance: String, issuedBy: String = "CalendarPilotKernel", confirmedByUser: Bool = false) {
        self.grantID = grantID
        self.userScopeID = userScopeID
        self.maxAuthorityTier = maxAuthorityTier
        self.scopes = scopes
        self.issuedAt = issuedAt
        self.expiresAt = expiresAt
        self.confirmationProvenance = confirmationProvenance
        self.issuedBy = issuedBy
        self.confirmedByUser = confirmedByUser
    }

    public func isLive(at date: Date) -> Bool {
        issuedAt <= date && date <= expiresAt
    }

    public func allows(_ scope: String) -> Bool {
        scopes.contains("*") || scopes.contains(scope)
    }
}

public struct AuthorityDecision: Codable, Hashable, Sendable {
    public var admitted: Bool
    public var reason: String?
    public var tierUsed: Int
    public var grantID: String?
    public var confirmationProvenance: String?

    public init(admitted: Bool, reason: String? = nil, tierUsed: Int, grantID: String? = nil, confirmationProvenance: String? = nil) {
        self.admitted = admitted
        self.reason = reason
        self.tierUsed = tierUsed
        self.grantID = grantID
        self.confirmationProvenance = confirmationProvenance
    }
}

public struct WriteAuthorityBroker: Sendable {
    public init() {}

    public func authorize(candidate: CandidateCalendarAction, observation: RawCalendarObservation, grant: AuthorityGrant?, desiredTier: Int, commit: Bool = true) -> AuthorityDecision {
        guard let grant else {
            return AuthorityDecision(admitted: false, reason: "missing Swift-issued authority grant; caller-supplied tiers are rejected before materialization", tierUsed: 0)
        }
        if grant.userScopeID != observation.userScopeID {
            return AuthorityDecision(admitted: false, reason: "authority grant user scope mismatch", tierUsed: 0, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if !grant.isLive(at: observation.observedAt) {
            return AuthorityDecision(admitted: false, reason: "authority grant expired before materialization", tierUsed: 0, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if desiredTier > grant.maxAuthorityTier {
            return AuthorityDecision(admitted: false, reason: "out-of-band authority tier rejected before materialization", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if commit && candidate.requiredAuthorityTier > grant.maxAuthorityTier {
            return AuthorityDecision(admitted: false, reason: "required authority tier exceeds Swift-issued grant", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if commit && candidate.actions.contains(where: { isWriteAction($0.actionType) }) && !grant.confirmedByUser {
            return AuthorityDecision(admitted: false, reason: "authority grant lacks user confirmation provenance for commit", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if commit && candidate.actions.contains(where: { isWriteAction($0.actionType) }) && !grant.allows("commit_private") {
            return AuthorityDecision(admitted: false, reason: "authority grant scope does not include commit_private", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if !commit && !grant.allows("stage") {
            return AuthorityDecision(admitted: false, reason: "authority grant scope does not include stage", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if candidate.actions.contains(where: { $0.actionType == .autoApplyPlan }) {
            return AuthorityDecision(admitted: false, reason: "auto_apply_plan requires product-specific tier 6 policy and is not kernel-v1 materialized", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if commit && isPeopleAffectingMutation(candidate: candidate) {
            return AuthorityDecision(admitted: false, reason: "social actuation boundary: people-affecting calendar mutation must be explicitly confirmed outside kernel-v1", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if commit && candidate.requiredAuthorityTier >= 3 && candidate.reversibility == .none {
            return AuthorityDecision(admitted: false, reason: "auto-write requires reversible or rollbackable action", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        if hasHardConflict(candidate: candidate, observation: observation) {
            return AuthorityDecision(admitted: false, reason: commit ? "conflict_detected" : "conflict_detected_before_stage", tierUsed: grant.maxAuthorityTier, grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
        }
        return AuthorityDecision(admitted: true, tierUsed: min(desiredTier, candidate.requiredAuthorityTier, grant.maxAuthorityTier), grantID: grant.grantID, confirmationProvenance: grant.confirmationProvenance)
    }

    public func isPeopleAffectingMutation(candidate: CandidateCalendarAction) -> Bool {
        guard !candidate.affectedPeopleIDs.isEmpty else { return false }
        return candidate.actions.contains { action in
            switch action.actionType {
            case .moveEvent, .resizeEvent, .deleteOwnEvent, .autoApplyPlan:
                return true
            default:
                return false
            }
        }
    }

    public func isWriteAction(_ actionType: AtomicActionType) -> Bool {
        switch actionType {
        case .createEvent, .createFocusBlock, .addBuffer, .batchTasks, .moveEvent, .resizeEvent, .deleteOwnEvent:
            return true
        default:
            return false
        }
    }

    public func hasHardConflict(candidate: CandidateCalendarAction, observation: RawCalendarObservation) -> Bool {
        for action in candidate.actions {
            guard let start = action.start, let end = action.end else { continue }
            switch action.actionType {
            case .createEvent, .createFocusBlock, .addBuffer, .batchTasks:
                if observation.events.contains(where: { start < $0.end && end > $0.start }) { return true }
            case .moveEvent, .resizeEvent:
                if observation.events.contains(where: { event in
                    if event.eventID == action.eventID { return false }
                    return start < event.end && end > event.start
                }) { return true }
            default:
                continue
            }
        }
        return false
    }
}
