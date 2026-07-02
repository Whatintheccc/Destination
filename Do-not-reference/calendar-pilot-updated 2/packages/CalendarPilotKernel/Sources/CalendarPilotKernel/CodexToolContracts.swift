
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
    case validateModelPlan = "validate_model_plan"
}

public enum CodexToolStatus: String, Codable, Hashable, Sendable {
    case succeeded
    case simulated
    case stageable
    case staged
    case committed
    case reverted
    case denied
    case requiresConfirmation = "requires_confirmation"
    case failed
}

public enum StageState: String, Codable, Hashable, Sendable {
    case simulated
    case stageable
    case requiresConfirmation = "requires_confirmation"
    case denied
    case committed
    case noOp = "no_op"
}

public enum JSONValue: Codable, Hashable, Sendable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    public init(_ value: String) { self = .string(value) }
    public init(_ value: Int) { self = .int(value) }
    public init(_ value: Double) { self = .double(value) }
    public init(_ value: Bool) { self = .bool(value) }
    public init(_ value: [String: JSONValue]) { self = .object(value) }
    public init(_ value: [JSONValue]) { self = .array(value) }

    public init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null; return }
        if let b = try? c.decode(Bool.self) { self = .bool(b); return }
        if let i = try? c.decode(Int.self) { self = .int(i); return }
        if let d = try? c.decode(Double.self) { self = .double(d); return }
        if let s = try? c.decode(String.self) { self = .string(s); return }
        if let a = try? c.decode([JSONValue].self) { self = .array(a); return }
        if let o = try? c.decode([String: JSONValue].self) { self = .object(o); return }
        throw DecodingError.typeMismatch(JSONValue.self, .init(codingPath: decoder.codingPath, debugDescription: "Unsupported JSON value"))
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .string(let s): try c.encode(s)
        case .int(let i): try c.encode(i)
        case .double(let d): try c.encode(d)
        case .bool(let b): try c.encode(b)
        case .object(let o): try c.encode(o)
        case .array(let a): try c.encode(a)
        case .null: try c.encodeNil()
        }
    }

    public var stringValue: String? {
        if case .string(let s) = self { return s }
        return nil
    }

    public var objectValue: [String: JSONValue]? {
        if case .object(let o) = self { return o }
        return nil
    }
}

public struct CodexToolCall: Codable, Hashable, Sendable {
    public var toolCallID: String
    public var toolName: CodexToolName
    public var input: [String: JSONValue]
    public var requestedAuthorityTier: Int
    public var userVisibleReason: String
    public var authorityGrantID: String?
    public var correlationID: String?
    public var createdAt: Date

    enum CodingKeys: String, CodingKey {
        case toolCallID = "tool_call_id"
        case toolName = "tool_name"
        case input
        case requestedAuthorityTier = "requested_authority_tier"
        case userVisibleReason = "user_visible_reason"
        case authorityGrantID = "authority_grant_id"
        case correlationID = "correlation_id"
        case createdAt = "created_at"
    }

    public init(toolCallID: String, toolName: CodexToolName, input: [String: JSONValue] = [:], requestedAuthorityTier: Int = 0, userVisibleReason: String = "", authorityGrantID: String? = nil, correlationID: String? = nil, createdAt: Date = Date()) {
        self.toolCallID = toolCallID
        self.toolName = toolName
        self.input = input
        self.requestedAuthorityTier = requestedAuthorityTier
        self.userVisibleReason = userVisibleReason
        self.authorityGrantID = authorityGrantID
        self.correlationID = correlationID
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
    public var stageState: StageState
    public var authorityGrantID: String?
    public var correlationID: String?
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
        case stageState = "stage_state"
        case authorityGrantID = "authority_grant_id"
        case correlationID = "correlation_id"
        case createdAt = "created_at"
    }

    public init(toolCallID: String, toolName: CodexToolName, status: CodexToolStatus, output: [String: JSONValue] = [:], swiftReceiptID: String? = nil, replayRecordID: String? = nil, deniedReason: String? = nil, requiresUserConfirmation: Bool = false, stageState: StageState = .noOp, authorityGrantID: String? = nil, correlationID: String? = nil, createdAt: Date = Date()) {
        self.toolCallID = toolCallID
        self.toolName = toolName
        self.status = status
        self.output = output
        self.swiftReceiptID = swiftReceiptID
        self.replayRecordID = replayRecordID
        self.deniedReason = deniedReason
        self.requiresUserConfirmation = requiresUserConfirmation
        self.stageState = stageState
        self.authorityGrantID = authorityGrantID
        self.correlationID = correlationID
        self.createdAt = createdAt
    }
}
