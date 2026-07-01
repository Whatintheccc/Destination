import Foundation

public enum AtomicActionType: String, Codable, Hashable, Sendable {
    case doNothing = "do_nothing"
    case notify = "notify"
    case askClarification = "ask_clarification"
    case createEvent = "create_event"
    case moveEvent = "move_event"
    case resizeEvent = "resize_event"
    case deleteOwnEvent = "delete_own_event"
    case addBuffer = "add_buffer"
    case createFocusBlock = "create_focus_block"
    case batchTasks = "batch_tasks"
    case draftSchedulePlan = "draft_schedule_plan"
    case autoApplyPlan = "auto_apply_plan"
    case undo = "undo"
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
    case simulated
}

public enum RightMomentDecision: String, Codable, Hashable, Sendable {
    case actNow = "act_now"
    case notifyNow = "notify_now"
    case wait
    case bundleIntoDigest = "bundle_into_digest"
    case silentlyDraft = "silently_draft"
    case autoWriteThenNotify = "auto_write_then_notify"
    case askClarification = "ask_clarification"
    case doNothing = "do_nothing"
}

public enum ActuationMode: String, Codable, Hashable, Sendable {
    case noOp = "no_op"
    case materializedWrite = "materialized_write"
    case stagedDraft = "staged_draft"
    case stagedNotification = "staged_notification"
    case denied
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

    enum CodingKeys: String, CodingKey {
        case eventID = "event_id"
        case title
        case start
        case end
        case calendarID = "calendar_id"
        case attendees
        case location
        case notes
        case isUserOwned = "is_user_owned"
        case isFlexible = "is_flexible"
        case category
    }

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

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.eventID = try c.decode(String.self, forKey: .eventID)
        self.title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        self.start = try c.decode(Date.self, forKey: .start)
        self.end = try c.decode(Date.self, forKey: .end)
        self.calendarID = try c.decodeIfPresent(String.self, forKey: .calendarID) ?? "default"
        self.attendees = try c.decodeIfPresent([String].self, forKey: .attendees) ?? []
        self.location = try c.decodeIfPresent(String.self, forKey: .location) ?? ""
        self.notes = try c.decodeIfPresent(String.self, forKey: .notes) ?? ""
        self.isUserOwned = try c.decodeIfPresent(Bool.self, forKey: .isUserOwned) ?? false
        self.isFlexible = try c.decodeIfPresent(Bool.self, forKey: .isFlexible) ?? false
        self.category = try c.decodeIfPresent(String.self, forKey: .category) ?? "unknown"
    }
}

public struct RawTask: Codable, Hashable, Sendable {
    public var taskID: String
    public var title: String
    public var due: Date?
    public var estimatedMinutes: Int
    public var category: String

    enum CodingKeys: String, CodingKey {
        case taskID = "task_id"
        case title
        case due
        case estimatedMinutes = "estimated_minutes"
        case category
    }

    public init(taskID: String, title: String = "", due: Date? = nil, estimatedMinutes: Int = 30, category: String = "unknown") {
        self.taskID = taskID
        self.title = title
        self.due = due
        self.estimatedMinutes = estimatedMinutes
        self.category = category
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.taskID = try c.decode(String.self, forKey: .taskID)
        self.title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        self.due = try c.decodeIfPresent(Date.self, forKey: .due)
        self.estimatedMinutes = try c.decodeIfPresent(Int.self, forKey: .estimatedMinutes) ?? 30
        self.category = try c.decodeIfPresent(String.self, forKey: .category) ?? "unknown"
    }
}

public struct DeviceContext: Codable, Hashable, Sendable {
    public var localHour: Int
    public var activeSurface: String
    public var isFocusMode: Bool

    enum CodingKeys: String, CodingKey {
        case localHour = "local_hour"
        case activeSurface = "active_surface"
        case isFocusMode = "is_focus_mode"
    }

    public init(localHour: Int = 9, activeSurface: String = "unknown", isFocusMode: Bool = false) {
        self.localHour = localHour
        self.activeSurface = activeSurface
        self.isFocusMode = isFocusMode
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.localHour = try c.decodeIfPresent(Int.self, forKey: .localHour) ?? 9
        self.activeSurface = try c.decodeIfPresent(String.self, forKey: .activeSurface) ?? "unknown"
        self.isFocusMode = try c.decodeIfPresent(Bool.self, forKey: .isFocusMode) ?? false
    }
}

public struct RawCalendarObservation: Codable, Hashable, Sendable {
    public var observationID: String
    public var userScopeID: String
    public var observedAt: Date
    public var timeZoneID: String
    public var events: [RawCalendarEvent]
    public var tasks: [RawTask]
    public var deviceContext: DeviceContext
    public var notificationHistory: [[String: JSONValue]]
    public var priorActions: [[String: JSONValue]]

    enum CodingKeys: String, CodingKey {
        case observationID = "observation_id"
        case userScopeID = "user_scope_id"
        case observedAt = "observed_at"
        case timeZoneID = "time_zone_id"
        case events
        case tasks
        case deviceContext = "device_context"
        case notificationHistory = "notification_history"
        case priorActions = "prior_actions"
    }

    public init(observationID: String, userScopeID: String, observedAt: Date, timeZoneID: String, events: [RawCalendarEvent], tasks: [RawTask] = [], deviceContext: DeviceContext = DeviceContext(), notificationHistory: [[String: JSONValue]] = [], priorActions: [[String: JSONValue]] = []) {
        self.observationID = observationID
        self.userScopeID = userScopeID
        self.observedAt = observedAt
        self.timeZoneID = timeZoneID
        self.events = events
        self.tasks = tasks
        self.deviceContext = deviceContext
        self.notificationHistory = notificationHistory
        self.priorActions = priorActions
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.observationID = try c.decode(String.self, forKey: .observationID)
        self.userScopeID = try c.decodeIfPresent(String.self, forKey: .userScopeID) ?? "default_user"
        self.observedAt = try c.decode(Date.self, forKey: .observedAt)
        self.timeZoneID = try c.decodeIfPresent(String.self, forKey: .timeZoneID) ?? "UTC"
        self.events = try c.decodeIfPresent([RawCalendarEvent].self, forKey: .events) ?? []
        self.tasks = try c.decodeIfPresent([RawTask].self, forKey: .tasks) ?? []
        self.deviceContext = try c.decodeIfPresent(DeviceContext.self, forKey: .deviceContext) ?? DeviceContext()
        self.notificationHistory = try c.decodeIfPresent([[String: JSONValue]].self, forKey: .notificationHistory) ?? []
        self.priorActions = try c.decodeIfPresent([[String: JSONValue]].self, forKey: .priorActions) ?? []
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

    enum CodingKeys: String, CodingKey {
        case actionType = "action_type"
        case title
        case eventID = "event_id"
        case start
        case end
        case calendarID = "calendar_id"
        case attendees
        case metadata
    }

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

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.actionType = try c.decode(AtomicActionType.self, forKey: .actionType)
        self.title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        self.eventID = try c.decodeIfPresent(String.self, forKey: .eventID)
        self.start = try c.decodeIfPresent(Date.self, forKey: .start)
        self.end = try c.decodeIfPresent(Date.self, forKey: .end)
        self.calendarID = try c.decodeIfPresent(String.self, forKey: .calendarID) ?? "default"
        self.attendees = try c.decodeIfPresent([String].self, forKey: .attendees) ?? []
        self.metadata = try c.decodeIfPresent([String: String].self, forKey: .metadata) ?? [:]
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
    public var predictedLongHorizonValue: Double
    public var expectedReward: Double
    public var recommendedExecutionTime: Date?
    public var rightMomentDecision: RightMomentDecision
    public var explanation: String
    public var modelStory: [String]
    public var counterfactual: String
    public var controlNotes: [String]
    public var rewardBreakdown: [String: Double]
    public var rightMomentScore: Double
    public var simulatedOutcomes: [String: Double]

    enum CodingKeys: String, CodingKey {
        case candidateID = "candidate_id"
        case intent
        case actions
        case targetCalendars = "target_calendars"
        case affectedEventIDs = "affected_event_ids"
        case affectedPeopleIDs = "affected_people_ids"
        case reversibility
        case requiredAuthorityTier = "required_authority_tier"
        case predictedAcceptance = "predicted_acceptance"
        case predictedUtility = "predicted_utility"
        case predictedEngagement = "predicted_engagement"
        case predictedRegret = "predicted_regret"
        case predictedInterruptionCost = "predicted_interruption_cost"
        case predictedSocialRisk = "predicted_social_risk"
        case predictedLongHorizonValue = "predicted_long_horizon_value"
        case expectedReward = "expected_reward"
        case recommendedExecutionTime = "recommended_execution_time"
        case rightMomentDecision = "right_moment_decision"
        case explanation
        case modelStory = "model_story"
        case counterfactual
        case controlNotes = "control_notes"
        case rewardBreakdown = "reward_breakdown"
        case rightMomentScore = "right_moment_score"
        case simulatedOutcomes = "simulated_outcomes"
    }

    public init(candidateID: String, intent: String, actions: [AtomicCalendarAction], targetCalendars: [String], affectedEventIDs: [String], affectedPeopleIDs: [String], reversibility: ReversibilityBand, requiredAuthorityTier: Int, predictedAcceptance: Double = 0, predictedUtility: Double = 0, predictedEngagement: Double = 0, predictedRegret: Double = 0, predictedInterruptionCost: Double = 0, predictedSocialRisk: Double = 0, predictedLongHorizonValue: Double = 0, expectedReward: Double = 0, recommendedExecutionTime: Date? = nil, rightMomentDecision: RightMomentDecision = .doNothing, explanation: String = "", modelStory: [String] = [], counterfactual: String = "", controlNotes: [String] = [], rewardBreakdown: [String: Double] = [:], rightMomentScore: Double = 0, simulatedOutcomes: [String: Double] = [:]) {
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
        self.predictedLongHorizonValue = predictedLongHorizonValue
        self.expectedReward = expectedReward
        self.recommendedExecutionTime = recommendedExecutionTime
        self.rightMomentDecision = rightMomentDecision
        self.explanation = explanation
        self.modelStory = modelStory
        self.counterfactual = counterfactual
        self.controlNotes = controlNotes
        self.rewardBreakdown = rewardBreakdown
        self.rightMomentScore = rightMomentScore
        self.simulatedOutcomes = simulatedOutcomes
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.candidateID = try c.decode(String.self, forKey: .candidateID)
        self.intent = try c.decodeIfPresent(String.self, forKey: .intent) ?? "unknown"
        self.actions = try c.decodeIfPresent([AtomicCalendarAction].self, forKey: .actions) ?? []
        self.targetCalendars = try c.decodeIfPresent([String].self, forKey: .targetCalendars) ?? []
        self.affectedEventIDs = try c.decodeIfPresent([String].self, forKey: .affectedEventIDs) ?? []
        self.affectedPeopleIDs = try c.decodeIfPresent([String].self, forKey: .affectedPeopleIDs) ?? []
        self.reversibility = try c.decodeIfPresent(ReversibilityBand.self, forKey: .reversibility) ?? .none
        self.requiredAuthorityTier = try c.decodeIfPresent(Int.self, forKey: .requiredAuthorityTier) ?? 0
        self.predictedAcceptance = try c.decodeIfPresent(Double.self, forKey: .predictedAcceptance) ?? 0
        self.predictedUtility = try c.decodeIfPresent(Double.self, forKey: .predictedUtility) ?? 0
        self.predictedEngagement = try c.decodeIfPresent(Double.self, forKey: .predictedEngagement) ?? 0
        self.predictedRegret = try c.decodeIfPresent(Double.self, forKey: .predictedRegret) ?? 0
        self.predictedInterruptionCost = try c.decodeIfPresent(Double.self, forKey: .predictedInterruptionCost) ?? 0
        self.predictedSocialRisk = try c.decodeIfPresent(Double.self, forKey: .predictedSocialRisk) ?? 0
        self.predictedLongHorizonValue = try c.decodeIfPresent(Double.self, forKey: .predictedLongHorizonValue) ?? 0
        self.expectedReward = try c.decodeIfPresent(Double.self, forKey: .expectedReward) ?? 0
        self.recommendedExecutionTime = try c.decodeIfPresent(Date.self, forKey: .recommendedExecutionTime)
        self.rightMomentDecision = try c.decodeIfPresent(RightMomentDecision.self, forKey: .rightMomentDecision) ?? .doNothing
        self.explanation = try c.decodeIfPresent(String.self, forKey: .explanation) ?? ""
        self.modelStory = try c.decodeIfPresent([String].self, forKey: .modelStory) ?? []
        self.counterfactual = try c.decodeIfPresent(String.self, forKey: .counterfactual) ?? ""
        self.controlNotes = try c.decodeIfPresent([String].self, forKey: .controlNotes) ?? []
        self.rewardBreakdown = try c.decodeIfPresent([String: Double].self, forKey: .rewardBreakdown) ?? [:]
        self.rightMomentScore = try c.decodeIfPresent(Double.self, forKey: .rightMomentScore) ?? 0
        self.simulatedOutcomes = try c.decodeIfPresent([String: Double].self, forKey: .simulatedOutcomes) ?? [:]
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
    public var stagedActionIDs: [String]
    public var rejectedActionTypes: [String]
    public var providerID: String
    public var actuationMode: ActuationMode
    public var deniedReason: String?
    public var authorityGrantID: String?
    public var confirmationProvenance: String?
    public var stageState: StageState
    public var correlationID: String?

    enum CodingKeys: String, CodingKey {
        case receiptID = "receipt_id"
        case candidateID = "candidate_id"
        case executedAt = "executed_at"
        case executedBy = "executed_by"
        case authorityTierUsed = "authority_tier_used"
        case syncStatus = "sync_status"
        case rollbackHandleID = "rollback_handle_id"
        case conflictCheckPassed = "conflict_check_passed"
        case generatedEventIDs = "generated_event_ids"
        case stagedActionIDs = "staged_action_ids"
        case rejectedActionTypes = "rejected_action_types"
        case providerID = "provider_id"
        case actuationMode = "actuation_mode"
        case deniedReason = "denied_reason"
        case authorityGrantID = "authority_grant_id"
        case confirmationProvenance = "confirmation_provenance"
        case stageState = "stage_state"
        case correlationID = "correlation_id"
    }

    public init(receiptID: String, candidateID: String, executedAt: Date, executedBy: String, authorityTierUsed: Int, syncStatus: CalendarSyncStatus, rollbackHandleID: String?, conflictCheckPassed: Bool, generatedEventIDs: [String] = [], stagedActionIDs: [String] = [], rejectedActionTypes: [String] = [], providerID: String = "local_swift", actuationMode: ActuationMode = .noOp, deniedReason: String? = nil, authorityGrantID: String? = nil, confirmationProvenance: String? = nil, stageState: StageState = .noOp, correlationID: String? = nil) {
        self.receiptID = receiptID
        self.candidateID = candidateID
        self.executedAt = executedAt
        self.executedBy = executedBy
        self.authorityTierUsed = authorityTierUsed
        self.syncStatus = syncStatus
        self.rollbackHandleID = rollbackHandleID
        self.conflictCheckPassed = conflictCheckPassed
        self.generatedEventIDs = generatedEventIDs
        self.stagedActionIDs = stagedActionIDs
        self.rejectedActionTypes = rejectedActionTypes
        self.providerID = providerID
        self.actuationMode = actuationMode
        self.deniedReason = deniedReason
        self.authorityGrantID = authorityGrantID
        self.confirmationProvenance = confirmationProvenance
        self.stageState = stageState
        self.correlationID = correlationID
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.receiptID = try c.decode(String.self, forKey: .receiptID)
        self.candidateID = try c.decode(String.self, forKey: .candidateID)
        self.executedAt = try c.decode(Date.self, forKey: .executedAt)
        self.executedBy = try c.decodeIfPresent(String.self, forKey: .executedBy) ?? "CalendarPilotKernel"
        self.authorityTierUsed = try c.decodeIfPresent(Int.self, forKey: .authorityTierUsed) ?? 0
        self.syncStatus = try c.decodeIfPresent(CalendarSyncStatus.self, forKey: .syncStatus) ?? .denied
        self.rollbackHandleID = try c.decodeIfPresent(String.self, forKey: .rollbackHandleID)
        self.conflictCheckPassed = try c.decodeIfPresent(Bool.self, forKey: .conflictCheckPassed) ?? false
        self.generatedEventIDs = try c.decodeIfPresent([String].self, forKey: .generatedEventIDs) ?? []
        self.stagedActionIDs = try c.decodeIfPresent([String].self, forKey: .stagedActionIDs) ?? []
        self.rejectedActionTypes = try c.decodeIfPresent([String].self, forKey: .rejectedActionTypes) ?? []
        self.providerID = try c.decodeIfPresent(String.self, forKey: .providerID) ?? "local_swift"
        self.actuationMode = try c.decodeIfPresent(ActuationMode.self, forKey: .actuationMode) ?? .noOp
        self.deniedReason = try c.decodeIfPresent(String.self, forKey: .deniedReason)
        self.authorityGrantID = try c.decodeIfPresent(String.self, forKey: .authorityGrantID)
        self.confirmationProvenance = try c.decodeIfPresent(String.self, forKey: .confirmationProvenance)
        self.stageState = try c.decodeIfPresent(StageState.self, forKey: .stageState) ?? .noOp
        self.correlationID = try c.decodeIfPresent(String.self, forKey: .correlationID)
    }
}

public struct RewardEvent: Codable, Hashable, Sendable {
    public var rewardEventID: String
    public var receiptID: String
    public var observedAt: Date
    public var accepted: Bool?
    public var edited: Bool?
    public var undone: Bool?
    public var deletedLater: Bool?
    public var ignored: Bool?
    public var explicitUseful: Bool?
    public var explicitWrong: Bool?
    public var explicitNotNeeded: Bool?
    public var notificationDismissed: Bool?
    public var survivedUntilEvent: Bool?
    public var downstreamConflict: Bool?
    public var reengaged: Bool?
    public var utilityReward: Double
    public var acceptanceReward: Double
    public var engagementReward: Double
    public var regretPenalty: Double
    public var interruptionPenalty: Double
    public var socialRiskPenalty: Double
    public var totalReward: Double

    enum CodingKeys: String, CodingKey {
        case rewardEventID = "reward_event_id"
        case receiptID = "receipt_id"
        case observedAt = "observed_at"
        case accepted
        case edited
        case undone
        case deletedLater = "deleted_later"
        case ignored
        case explicitUseful = "explicit_useful"
        case explicitWrong = "explicit_wrong"
        case explicitNotNeeded = "explicit_not_needed"
        case notificationDismissed = "notification_dismissed"
        case survivedUntilEvent = "survived_until_event"
        case downstreamConflict = "downstream_conflict"
        case reengaged
        case utilityReward = "utility_reward"
        case acceptanceReward = "acceptance_reward"
        case engagementReward = "engagement_reward"
        case regretPenalty = "regret_penalty"
        case interruptionPenalty = "interruption_penalty"
        case socialRiskPenalty = "social_risk_penalty"
        case totalReward = "total_reward"
    }

    public init(rewardEventID: String, receiptID: String, observedAt: Date, accepted: Bool? = nil, edited: Bool? = nil, undone: Bool? = nil, deletedLater: Bool? = nil, ignored: Bool? = nil, explicitUseful: Bool? = nil, explicitWrong: Bool? = nil, explicitNotNeeded: Bool? = nil, notificationDismissed: Bool? = nil, survivedUntilEvent: Bool? = nil, downstreamConflict: Bool? = nil, reengaged: Bool? = nil, utilityReward: Double = 0, acceptanceReward: Double = 0, engagementReward: Double = 0, regretPenalty: Double = 0, interruptionPenalty: Double = 0, socialRiskPenalty: Double = 0, totalReward: Double = 0) {
        self.rewardEventID = rewardEventID
        self.receiptID = receiptID
        self.observedAt = observedAt
        self.accepted = accepted
        self.edited = edited
        self.undone = undone
        self.deletedLater = deletedLater
        self.ignored = ignored
        self.explicitUseful = explicitUseful
        self.explicitWrong = explicitWrong
        self.explicitNotNeeded = explicitNotNeeded
        self.notificationDismissed = notificationDismissed
        self.survivedUntilEvent = survivedUntilEvent
        self.downstreamConflict = downstreamConflict
        self.reengaged = reengaged
        self.utilityReward = utilityReward
        self.acceptanceReward = acceptanceReward
        self.engagementReward = engagementReward
        self.regretPenalty = regretPenalty
        self.interruptionPenalty = interruptionPenalty
        self.socialRiskPenalty = socialRiskPenalty
        self.totalReward = totalReward
    }
}
