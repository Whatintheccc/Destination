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
        if candidate.requiredAuthorityTier >= 5 && !candidate.affectedPeopleIDs.isEmpty {
            return AuthorityDecision(admitted: false, reason: "social actuation requires explicit tier 5+ confirmation", tierUsed: grantedTier)
        }
        if candidate.requiredAuthorityTier >= 3 && candidate.reversibility == .none {
            return AuthorityDecision(admitted: false, reason: "auto-write requires reversible or rollbackable action", tierUsed: grantedTier)
        }
        if hasHardConflict(candidate: candidate, observation: observation) {
            return AuthorityDecision(admitted: false, reason: "conflict_detected", tierUsed: grantedTier)
        }
        return AuthorityDecision(admitted: true, tierUsed: min(grantedTier, candidate.requiredAuthorityTier))
    }

    public func hasHardConflict(candidate: CandidateCalendarAction, observation: RawCalendarObservation) -> Bool {
        for action in candidate.actions {
            guard let start = action.start, let end = action.end else { continue }
            switch action.actionType {
            case .createEvent, .createFocusBlock, .addBuffer:
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
