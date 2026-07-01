import Foundation

public enum CodexToolName: String, Codable, Hashable, Sendable {
    case inspectWeek = "inspect_week"
    case inspectEvent = "inspect_event"
    case inspectOpenSlots = "inspect_open_slots"
    case inspectAuthorityScope = "inspect_authority_scope"
    case generateCandidateFrontier = "generate_candidate_frontier"
    case simulateActionProgram = "simulate_action_program"
    case compareCandidates = "compare_candidates"
    case stageActionPacket = "stage_action_packet"
    case requestCommit = "request_commit"
    case requestUndo = "request_undo"
    case queryReplayTrace = "query_replay_trace"
    case inspectProfileClaims = "inspect_profile_claims"
    case proposeProfilePatch = "propose_profile_patch"
    case applyProfilePatch = "apply_profile_patch"
    case runSelfPlayProbe = "run_self_play_probe"
    case proposeAutonomyScope = "propose_autonomy_scope"
    case explainSwiftDenial = "explain_swift_denial"
}

public enum CodexToolStatus: String, Codable, Hashable, Sendable {
    case succeeded
    case staged
    case denied
    case requiresConfirmation = "requires_confirmation"
    case failed
}

public struct JSONValue: Codable, Hashable, Sendable {
    public var value: String
    public init(_ value: String) { self.value = value }
    public init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let string = try? c.decode(String.self) { value = string; return }
        if let bool = try? c.decode(Bool.self) { value = String(bool); return }
        if let int = try? c.decode(Int.self) { value = String(int); return }
        if let double = try? c.decode(Double.self) { value = String(double); return }
        value = ""
    }
    public func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        try c.encode(value)
    }
}

public struct CodexToolCall: Codable, Hashable, Sendable {
    public var toolCallID: String
    public var toolName: CodexToolName
    public var input: [String: JSONValue]
    public var requestedAuthorityTier: Int
    public var userVisibleReason: String
    public var createdAt: Date

    enum CodingKeys: String, CodingKey {
        case toolCallID = "tool_call_id"
        case toolName = "tool_name"
        case input
        case requestedAuthorityTier = "requested_authority_tier"
        case userVisibleReason = "user_visible_reason"
        case createdAt = "created_at"
    }

    public init(toolCallID: String, toolName: CodexToolName, input: [String: JSONValue] = [:], requestedAuthorityTier: Int = 0, userVisibleReason: String = "", createdAt: Date = Date()) {
        self.toolCallID = toolCallID
        self.toolName = toolName
        self.input = input
        self.requestedAuthorityTier = requestedAuthorityTier
        self.userVisibleReason = userVisibleReason
        self.createdAt = createdAt
    }
}

public struct CodexToolReceipt: Codable, Hashable, Sendable {
    public var toolCallID: String
    public var toolName: CodexToolName
    public var status: CodexToolStatus
    public var output: [String: JSONValue]
    public var swiftReceiptID: String?
    public var replayRecordID: String?
    public var deniedReason: String?
    public var requiresUserConfirmation: Bool
    public var createdAt: Date

    enum CodingKeys: String, CodingKey {
        case toolCallID = "tool_call_id"
        case toolName = "tool_name"
        case status
        case output
        case swiftReceiptID = "swift_receipt_id"
        case replayRecordID = "replay_record_id"
        case deniedReason = "denied_reason"
        case requiresUserConfirmation = "requires_user_confirmation"
        case createdAt = "created_at"
    }

    public init(toolCallID: String, toolName: CodexToolName, status: CodexToolStatus, output: [String: JSONValue] = [:], swiftReceiptID: String? = nil, replayRecordID: String? = nil, deniedReason: String? = nil, requiresUserConfirmation: Bool = false, createdAt: Date = Date()) {
        self.toolCallID = toolCallID
        self.toolName = toolName
        self.status = status
        self.output = output
        self.swiftReceiptID = swiftReceiptID
        self.replayRecordID = replayRecordID
        self.deniedReason = deniedReason
        self.requiresUserConfirmation = requiresUserConfirmation
        self.createdAt = createdAt
    }
}
