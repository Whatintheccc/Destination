import Foundation
import CalendarPilotKernel

struct KernelRPCRequest: Codable {
    var id: String
    var op: String
    var payload: [String: JSONValue]
}

struct KernelRPCResponse: Codable {
    var id: String
    var ok: Bool
    var payload: [String: JSONValue]
    var error: String?
}

struct IssueGrantPayload: Codable {
    var userScopeID: String
    var maxAuthorityTier: Int
    var scopes: [String]
    var confirmationProvenance: String
    var ttlSeconds: TimeInterval
    var confirmedByUser: Bool
    var issuedAt: Date

    enum CodingKeys: String, CodingKey {
        case userScopeID = "user_scope_id"
        case maxAuthorityTier = "max_authority_tier"
        case scopes
        case confirmationProvenance = "confirmation_provenance"
        case ttlSeconds = "ttl_seconds"
        case confirmedByUser = "confirmed_by_user"
        case issuedAt = "issued_at"
    }
}

struct ActuationPayload: Codable {
    var candidate: CandidateCalendarAction
    var observation: RawCalendarObservation
    var authorityGrantID: String?
    var requestedAuthorityTier: Int

    enum CodingKeys: String, CodingKey {
        case candidate
        case observation
        case authorityGrantID = "authority_grant_id"
        case requestedAuthorityTier = "requested_authority_tier"
    }
}

struct UndoPayload: Codable {
    var rollbackHandleID: String
    var authorityGrantID: String?
    var observedAt: Date
    var requestedAuthorityTier: Int?

    enum CodingKeys: String, CodingKey {
        case rollbackHandleID = "rollback_handle_id"
        case authorityGrantID = "authority_grant_id"
        case observedAt = "observed_at"
        case requestedAuthorityTier = "requested_authority_tier"
    }
}

final class KernelRPCServer {
    private let kernel = CalendarKernel()
    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()

    init() {
        decoder.dateDecodingStrategy = .iso8601
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
    }

    func run() {
        while let line = readLine() {
            guard !line.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { continue }
            let response: KernelRPCResponse
            do {
                let request = try decoder.decode(KernelRPCRequest.self, from: Data(line.utf8))
                response = try handle(request)
            } catch {
                response = KernelRPCResponse(id: "unknown", ok: false, payload: [:], error: String(describing: error))
            }
            if let data = try? encoder.encode(response), let text = String(data: data, encoding: .utf8) {
                FileHandle.standardOutput.write(Data((text + "\n").utf8))
            }
        }
    }

    private func handle(_ request: KernelRPCRequest) throws -> KernelRPCResponse {
        switch request.op {
        case "issue_authority_grant":
            let payload = try decode(IssueGrantPayload.self, from: request.payload)
            let grant = kernel.issueAuthorityGrant(
                userScopeID: payload.userScopeID,
                maxAuthorityTier: payload.maxAuthorityTier,
                scopes: payload.scopes,
                confirmationProvenance: payload.confirmationProvenance,
                ttlSeconds: payload.ttlSeconds,
                confirmedByUser: payload.confirmedByUser,
                issuedAt: payload.issuedAt
            )
            return try ok(request, ["authority_grant": toJSONValue(grant)])
        case "stage":
            let payload = try decode(ActuationPayload.self, from: request.payload)
            let receipt = kernel.stage(
                candidate: payload.candidate,
                observation: payload.observation,
                authorityGrant: payload.authorityGrantID.flatMap { kernel.resolveGrant($0) },
                requestedAuthorityTier: payload.requestedAuthorityTier
            )
            return try ok(request, ["receipt": toJSONValue(receipt)])
        case "preview":
            let payload = try decode(ActuationPayload.self, from: request.payload)
            let receipt = kernel.preview(
                candidate: payload.candidate,
                observation: payload.observation,
                authorityGrant: payload.authorityGrantID.flatMap { kernel.resolveGrant($0) },
                requestedAuthorityTier: payload.requestedAuthorityTier
            )
            return try ok(request, ["receipt": toJSONValue(receipt)])
        case "commit":
            let payload = try decode(ActuationPayload.self, from: request.payload)
            let (receipt, _) = kernel.authorizeAndMaterialize(
                candidate: payload.candidate,
                observation: payload.observation,
                authorityGrant: payload.authorityGrantID.flatMap { kernel.resolveGrant($0) },
                requestedAuthorityTier: payload.requestedAuthorityTier
            )
            return try ok(request, ["receipt": toJSONValue(receipt)])
        case "undo":
            let payload = try decode(UndoPayload.self, from: request.payload)
            let receipt = kernel.undo(
                rollbackHandleID: payload.rollbackHandleID,
                authorityGrant: payload.authorityGrantID.flatMap { kernel.resolveGrant($0) },
                observedAt: payload.observedAt,
                requestedAuthorityTier: payload.requestedAuthorityTier
            )
            return try ok(request, ["receipt": toJSONValue(receipt)])
        default:
            return KernelRPCResponse(id: request.id, ok: false, payload: [:], error: "unsupported op \(request.op)")
        }
    }

    private func ok(_ request: KernelRPCRequest, _ payload: [String: JSONValue]) -> KernelRPCResponse {
        KernelRPCResponse(id: request.id, ok: true, payload: payload, error: nil)
    }

    private func decode<T: Decodable>(_ type: T.Type, from value: [String: JSONValue]) throws -> T {
        let data = try encoder.encode(value)
        return try decoder.decode(T.self, from: data)
    }

    private func toJSONValue<T: Encodable>(_ value: T) throws -> JSONValue {
        let data = try encoder.encode(value)
        return try decoder.decode(JSONValue.self, from: data)
    }
}

KernelRPCServer().run()
