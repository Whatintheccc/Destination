import Foundation

public enum AtomicActionType: String, Codable, Hashable, Sendable {
    case doNothing
    case notify
    case askClarification
    case createEvent
    case moveEvent
    case resizeEvent
    case deleteOwnEvent
    case addBuffer
    case createFocusBlock
    case batchTasks
    case draftSchedulePlan
    case autoApplyPlan
    case undo
}

public enum ReversibilityBand: String, Codable, Hashable, Sendable {
    case none
    case low
    case medium
    case high
}

public enum CalendarSyncStatus: String, Codable, Hashable, Sendable {
    case staged
    case materialized
    case denied
    case reverted
}

public struct RawCalendarEvent: Codable, Hashable, Sendable {
    public var eventID: String
    public var title: String
    public var start: Date
    public var end: Date
    public var calendarID: String
    public var attendees: [String]
    public var location: String
    public var notes: String
    public var isUserOwned: Bool
    public var isFlexible: Bool
    public var category: String

    public init(eventID: String, title: String, start: Date, end: Date, calendarID: String, attendees: [String] = [], location: String = "", notes: String = "", isUserOwned: Bool = false, isFlexible: Bool = false, category: String = "unknown") {
        self.eventID = eventID
        self.title = title
        self.start = start
        self.end = end
        self.calendarID = calendarID
        self.attendees = attendees
        self.location = location
        self.notes = notes
        self.isUserOwned = isUserOwned
        self.isFlexible = isFlexible
        self.category = category
    }
}

public struct RawCalendarObservation: Codable, Hashable, Sendable {
    public var observationID: String
    public var userScopeID: String
    public var observedAt: Date
    public var timeZoneID: String
    public var events: [RawCalendarEvent]

    public init(observationID: String, userScopeID: String, observedAt: Date, timeZoneID: String, events: [RawCalendarEvent]) {
        self.observationID = observationID
        self.userScopeID = userScopeID
        self.observedAt = observedAt
        self.timeZoneID = timeZoneID
        self.events = events
    }
}

public struct AtomicCalendarAction: Codable, Hashable, Sendable {
    public var actionType: AtomicActionType
    public var title: String
    public var eventID: String?
    public var start: Date?
    public var end: Date?
    public var calendarID: String
    public var attendees: [String]
    public var metadata: [String: String]

    public init(actionType: AtomicActionType, title: String = "", eventID: String? = nil, start: Date? = nil, end: Date? = nil, calendarID: String = "default", attendees: [String] = [], metadata: [String: String] = [:]) {
        self.actionType = actionType
        self.title = title
        self.eventID = eventID
        self.start = start
        self.end = end
        self.calendarID = calendarID
        self.attendees = attendees
        self.metadata = metadata
    }
}

public struct CandidateCalendarAction: Codable, Hashable, Sendable {
    public var candidateID: String
    public var intent: String
    public var actions: [AtomicCalendarAction]
    public var targetCalendars: [String]
    public var affectedEventIDs: [String]
    public var affectedPeopleIDs: [String]
    public var reversibility: ReversibilityBand
    public var requiredAuthorityTier: Int
    public var predictedAcceptance: Double
    public var predictedUtility: Double
    public var predictedEngagement: Double
    public var predictedRegret: Double
    public var predictedInterruptionCost: Double
    public var predictedSocialRisk: Double
    public var expectedReward: Double
    public var explanation: String

    public init(candidateID: String, intent: String, actions: [AtomicCalendarAction], targetCalendars: [String], affectedEventIDs: [String], affectedPeopleIDs: [String], reversibility: ReversibilityBand, requiredAuthorityTier: Int, predictedAcceptance: Double = 0, predictedUtility: Double = 0, predictedEngagement: Double = 0, predictedRegret: Double = 0, predictedInterruptionCost: Double = 0, predictedSocialRisk: Double = 0, expectedReward: Double = 0, explanation: String = "") {
        self.candidateID = candidateID
        self.intent = intent
        self.actions = actions
        self.targetCalendars = targetCalendars
        self.affectedEventIDs = affectedEventIDs
        self.affectedPeopleIDs = affectedPeopleIDs
        self.reversibility = reversibility
        self.requiredAuthorityTier = requiredAuthorityTier
        self.predictedAcceptance = predictedAcceptance
        self.predictedUtility = predictedUtility
        self.predictedEngagement = predictedEngagement
        self.predictedRegret = predictedRegret
        self.predictedInterruptionCost = predictedInterruptionCost
        self.predictedSocialRisk = predictedSocialRisk
        self.expectedReward = expectedReward
        self.explanation = explanation
    }
}

public struct CalendarActionReceipt: Codable, Hashable, Sendable {
    public var receiptID: String
    public var candidateID: String
    public var executedAt: Date
    public var executedBy: String
    public var authorityTierUsed: Int
    public var syncStatus: CalendarSyncStatus
    public var rollbackHandleID: String?
    public var conflictCheckPassed: Bool
    public var generatedEventIDs: [String]
    public var deniedReason: String?

    public init(receiptID: String, candidateID: String, executedAt: Date, executedBy: String, authorityTierUsed: Int, syncStatus: CalendarSyncStatus, rollbackHandleID: String?, conflictCheckPassed: Bool, generatedEventIDs: [String] = [], deniedReason: String? = nil) {
        self.receiptID = receiptID
        self.candidateID = candidateID
        self.executedAt = executedAt
        self.executedBy = executedBy
        self.authorityTierUsed = authorityTierUsed
        self.syncStatus = syncStatus
        self.rollbackHandleID = rollbackHandleID
        self.conflictCheckPassed = conflictCheckPassed
        self.generatedEventIDs = generatedEventIDs
        self.deniedReason = deniedReason
    }
}

public struct RewardEvent: Codable, Hashable, Sendable {
    public var rewardEventID: String
    public var receiptID: String
    public var observedAt: Date
    public var accepted: Bool?
    public var edited: Bool?
    public var undone: Bool?
    public var ignored: Bool?
    public var totalReward: Double

    public init(rewardEventID: String, receiptID: String, observedAt: Date, accepted: Bool? = nil, edited: Bool? = nil, undone: Bool? = nil, ignored: Bool? = nil, totalReward: Double = 0) {
        self.rewardEventID = rewardEventID
        self.receiptID = receiptID
        self.observedAt = observedAt
        self.accepted = accepted
        self.edited = edited
        self.undone = undone
        self.ignored = ignored
        self.totalReward = totalReward
    }
}
