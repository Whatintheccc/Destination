import Foundation

public struct AuthorityDecision: Codable, Hashable, Sendable {
    public var admitted: Bool
    public var reason: String?
    public var tierUsed: Int

    public init(admitted: Bool, reason: String? = nil, tierUsed: Int) {
        self.admitted = admitted
        self.reason = reason
        self.tierUsed = tierUsed
    }
}

public struct WriteAuthorityBroker: Sendable {
    public init() {}

    public func authorize(candidate: CandidateCalendarAction, observation: RawCalendarObservation, grantedTier: Int) -> AuthorityDecision {
        if candidate.requiredAuthorityTier > grantedTier {
            return AuthorityDecision(admitted: false, reason: "required authority tier exceeds granted tier", tierUsed: grantedTier)
        }
        if candidate.actions.contains(where: { $0.actionType == .autoApplyPlan }) {
            return AuthorityDecision(admitted: false, reason: "auto_apply_plan requires product-specific tier 6 policy and is not kernel-v1 materialized", tierUsed: grantedTier)
        }
        if isPeopleAffectingMutation(candidate: candidate) {
            return AuthorityDecision(admitted: false, reason: "social actuation boundary: people-affecting calendar mutation must be explicitly confirmed outside kernel-v1", tierUsed: grantedTier)
        }
        if candidate.requiredAuthorityTier >= 3 && candidate.reversibility == .none {
            return AuthorityDecision(admitted: false, reason: "auto-write requires reversible or rollbackable action", tierUsed: grantedTier)
        }
        if hasHardConflict(candidate: candidate, observation: observation) {
            return AuthorityDecision(admitted: false, reason: "conflict_detected", tierUsed: grantedTier)
        }
        return AuthorityDecision(admitted: true, tierUsed: min(grantedTier, candidate.requiredAuthorityTier))
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

    public func hasHardConflict(candidate: CandidateCalendarAction, observation: RawCalendarObservation) -> Bool {
        for action in candidate.actions {
            guard let start = action.start, let end = action.end else { continue }
            switch action.actionType {
            case .createEvent, .createFocusBlock, .addBuffer, .batchTasks:
                if observation.events.contains(where: { start < $0.end && end > $0.start }) {
                    return true
                }
            case .moveEvent, .resizeEvent:
                if observation.events.contains(where: { event in
                    if event.eventID == action.eventID { return false }
                    return start < event.end && end > event.start
                }) {
                    return true
                }
            default:
                continue
            }
        }
        return false
    }
}
