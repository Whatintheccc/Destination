
#if canImport(EventKit)

import EventKit
import Foundation
import CalendarPilotKernel

private struct BridgeRequest: Codable {
    var command: String
    var payload: [String: JSONValue]
}

private struct BridgeResponse: Codable {
    var ok: Bool
    var result: [String: JSONValue]
    var error: String?
}

private struct EventKitAction: Codable {
    var actionType: AtomicActionType
    var title: String
    var eventID: String?
    var start: Date?
    var end: Date?
    var calendarID: String
    var attendees: [String]
    var metadata: [String: String]

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
}

private enum BridgeFailure: Error, CustomStringConvertible {
    case unsupportedCommand(String)
    case missingField(String)
    case notAuthorized(String)
    case eventNotFound(String)
    case noWritableCalendar
    case sandboxViolation(String)

    var description: String {
        switch self {
        case .unsupportedCommand(let command): return "unsupported EventKit bridge command: \(command)"
        case .missingField(let field): return "missing required EventKit payload field: \(field)"
        case .notAuthorized(let status): return "Apple Calendar permission is \(status)"
        case .eventNotFound(let eventID): return "Apple Calendar event not found: \(eventID)"
        case .noWritableCalendar: return "no writable Apple Calendar is available"
        case .sandboxViolation(let message): return "EventKit self-play sandbox violation: \(message)"
        }
    }
}

@main
private struct CalendarPilotEventKitBridge {
    static func main() async {
        let decoder = makeDecoder()
        let requestFile = argumentValue(after: "--request-file")
        let raw = requestFile.flatMap { try? Data(contentsOf: URL(fileURLWithPath: $0)) } ?? FileHandle.standardInput.readDataToEndOfFile()
        let resultFile = argumentValue(after: "--result-file")
        do {
            let request: BridgeRequest
            if CommandLine.arguments.contains("--request-access") {
                request = BridgeRequest(command: "request_access", payload: [:])
            } else if CommandLine.arguments.contains("--status") {
                request = BridgeRequest(command: "status", payload: [:])
            } else {
                request = try decoder.decode(BridgeRequest.self, from: raw.isEmpty ? Data(#"{"command":"status","payload":{}}"#.utf8) : raw)
            }
            let result = try await EventKitCommandHandler().handle(command: request.command, payload: request.payload)
            emit(BridgeResponse(ok: true, result: result, error: nil), resultFile: resultFile)
        } catch {
            emit(BridgeResponse(ok: false, result: [:], error: String(describing: error)), resultFile: resultFile)
        }
    }

    private static func emit(_ response: BridgeResponse, resultFile: String?) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        if let data = try? encoder.encode(response), let text = String(data: data, encoding: .utf8) {
            if let resultFile {
                try? data.write(to: URL(fileURLWithPath: resultFile), options: [.atomic])
                return
            }
            FileHandle.standardOutput.write(Data((text + "\n").utf8))
        }
    }
}

private final class EventKitCommandHandler {
    private let store = EKEventStore()
    private let decoder = makeDecoder()
    private let encoder = makeEncoder()
    private let envSandboxCalendarID = ProcessInfo.processInfo.environment["CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID"] ?? ProcessInfo.processInfo.environment["CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID"]

    func handle(command: String, payload: [String: JSONValue]) async throws -> [String: JSONValue] {
        switch command {
        case "status":
            return statusPayload()
        case "request_access":
            return try await requestAccess()
        case "read_events":
            return try readEvents(payload)
        case "commit":
            return try commit(payload)
        case "rollback":
            return try rollback(payload)
        default:
            throw BridgeFailure.unsupportedCommand(command)
        }
    }

    private func requestAccess() async throws -> [String: JSONValue] {
        let granted: Bool = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Bool, Error>) in
            if #available(macOS 14.0, *) {
                store.requestFullAccessToEvents { ok, error in
                    if let error {
                        continuation.resume(throwing: error)
                    } else {
                        continuation.resume(returning: ok)
                    }
                }
            } else {
                store.requestAccess(to: .event) { ok, error in
                    if let error {
                        continuation.resume(throwing: error)
                    } else {
                        continuation.resume(returning: ok)
                    }
                }
            }
        }
        var payload = statusPayload()
        payload["request_granted"] = JSONValue(granted)
        return payload
    }

    private func readEvents(_ payload: [String: JSONValue]) throws -> [String: JSONValue] {
        try requireAuthorized()
        let start = try dateField("time_min", in: payload)
        let end = try dateField("time_max", in: payload)
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: store.calendars(for: .event))
        let events = store.events(matching: predicate)
        return ["events": JSONValue(events.map { JSONValue(eventPayload($0)) })]
    }

    private func commit(_ payload: [String: JSONValue]) throws -> [String: JSONValue] {
        try requireAuthorized()
        let actions = try actionList(in: payload)
        let sandboxCalendarID = payload["sandbox_calendar_id"]?.stringValue ?? envSandboxCalendarID
        try enforceSandbox(actions: actions, sandboxCalendarID: sandboxCalendarID)
        let idempotencyKey = payload["idempotency_key"]?.stringValue ?? ""
        let writeActions = actions.filter { isWriteAction($0.actionType) }
        let createActions = writeActions.filter { isCreateAction($0.actionType) }
        if !idempotencyKey.isEmpty && !createActions.isEmpty && createActions.count == writeActions.count {
            let existing = existingEventIDs(for: idempotencyKey)
            if existing.count >= createActions.count {
                return [
                    "provider_id": JSONValue("apple_eventkit"),
                    "external_ids": JSONValue(existing.map(JSONValue.init)),
                    "created_external_ids": JSONValue(existing.map(JSONValue.init)),
                    "moved_external_ids": JSONValue([]),
                    "deleted_external_ids": JSONValue([]),
                    "before_events": JSONValue([:]),
                    "idempotent_replay": JSONValue(true),
                ]
            }
        }
        var created: [String] = []
        var moved: [String] = []
        var deleted: [String] = []
        var beforeEvents: [String: JSONValue] = [:]
        var pendingCreatedEvents: [EKEvent] = []

        for action in actions {
            switch action.actionType {
            case .createEvent, .createFocusBlock, .addBuffer, .batchTasks:
                let event = try eventFromAction(action, idempotencyKey: idempotencyKey, index: pendingCreatedEvents.count)
                try store.save(event, span: .thisEvent, commit: false)
                pendingCreatedEvents.append(event)
            case .moveEvent, .resizeEvent:
                let id = try action.eventID.orThrow("event_id")
                let event = try eventForIdentifier(id)
                beforeEvents[id] = JSONValue(eventPayload(event))
                if let start = action.start { event.startDate = start }
                if let end = action.end { event.endDate = end }
                if !action.title.isEmpty { event.title = action.title }
                try store.save(event, span: .thisEvent, commit: false)
                moved.append(currentIdentifier(for: event))
            case .deleteOwnEvent:
                let id = try action.eventID.orThrow("event_id")
                let event = try eventForIdentifier(id)
                beforeEvents[id] = JSONValue(eventPayload(event))
                try store.remove(event, span: .thisEvent, commit: false)
                deleted.append(id)
            case .doNothing, .notify, .askClarification, .draftSchedulePlan, .autoApplyPlan, .undo:
                continue
            }
        }
        try store.commit()
        created = pendingCreatedEvents.map { currentIdentifier(for: $0) }

        let external = created + moved + deleted
        return [
            "provider_id": JSONValue("apple_eventkit"),
            "external_ids": JSONValue(external.map(JSONValue.init)),
            "created_external_ids": JSONValue(created.map(JSONValue.init)),
            "moved_external_ids": JSONValue(moved.map(JSONValue.init)),
            "deleted_external_ids": JSONValue(deleted.map(JSONValue.init)),
            "before_events": JSONValue(beforeEvents),
        ]
    }

    private func rollback(_ payload: [String: JSONValue]) throws -> [String: JSONValue] {
        try requireAuthorized()
        if let sandboxCalendarID = payload["sandbox_calendar_id"]?.stringValue ?? envSandboxCalendarID {
            try assertRollbackSandbox(payload, sandboxCalendarID: sandboxCalendarID)
        }
        for eventID in stringArray(payload["created_external_ids"]) {
            if let event = store.event(withIdentifier: eventID) {
                try store.remove(event, span: .thisEvent, commit: false)
            }
        }
        for (_, value) in payload["before_events"]?.objectValue ?? [:] {
            guard let row = value.objectValue else { continue }
            try restoreEvent(from: row)
        }
        try store.commit()
        let createdGone = stringArray(payload["created_external_ids"]).allSatisfy { store.event(withIdentifier: $0) == nil }
        let restoredRows = payload["before_events"]?.objectValue?.values.compactMap(\.objectValue) ?? []
        let restored = restoredRows.allSatisfy { verifyRestoredEvent($0) }
        return [
            "provider_id": JSONValue("apple_eventkit"),
            "rollback_verified": JSONValue(createdGone && restored),
        ]
    }

    private func eventFromAction(_ action: EventKitAction, idempotencyKey: String, index: Int) throws -> EKEvent {
        let start = try action.start.orThrow("start")
        let end = try action.end.orThrow("end")
        let event = EKEvent(eventStore: store)
        event.title = action.title.isEmpty ? "CalendarPilot event" : action.title
        event.startDate = start
        event.endDate = end
        event.calendar = try calendar(id: action.calendarID)
        let marker = idempotencyKey.isEmpty ? "" : "\nCalendarPilot-Idempotency: \(idempotencyKey)#\(index)"
        if let notes = action.metadata["notes"], !notes.isEmpty {
            event.notes = notes + marker
        } else {
            event.notes = "Created by CalendarPilot" + marker
        }
        return event
    }

    private func restoreEvent(from row: [String: JSONValue]) throws {
        let eventID = row["event_id"]?.stringValue
        let event = eventID.flatMap { store.event(withIdentifier: $0) } ?? EKEvent(eventStore: store)
        event.title = row["title"]?.stringValue ?? event.title ?? "CalendarPilot restored event"
        event.startDate = try dateField("start", in: row)
        event.endDate = try dateField("end", in: row)
        event.location = row["location"]?.stringValue ?? ""
        event.notes = row["notes"]?.stringValue ?? ""
        event.calendar = try calendar(id: row["calendar_id"]?.stringValue ?? "default")
        try store.save(event, span: .thisEvent, commit: false)
    }

    private func eventPayload(_ event: EKEvent) -> [String: JSONValue] {
        let attendees = (event.attendees ?? []).compactMap { participant -> String? in
            let url = participant.url.absoluteString
            if !url.isEmpty { return url }
            if let name = participant.name, !name.isEmpty { return name }
            return nil
        }
        return [
            "event_id": JSONValue(currentIdentifier(for: event)),
            "title": JSONValue(event.title ?? ""),
            "start": JSONValue(formatDate(event.startDate)),
            "end": JSONValue(formatDate(event.endDate)),
            "calendar_id": JSONValue(event.calendar?.calendarIdentifier ?? "default"),
            "attendees": JSONValue(attendees.map(JSONValue.init)),
            "location": JSONValue(event.location ?? ""),
            "notes": JSONValue(event.notes ?? ""),
            "is_user_owned": JSONValue(event.calendar?.allowsContentModifications ?? false),
            "is_flexible": JSONValue(false),
            "category": JSONValue(event.calendar?.title ?? "calendar"),
        ]
    }

    private func requireAuthorized() throws {
        let status = EKEventStore.authorizationStatus(for: .event)
        if !isFullyAuthorized(status) {
            throw BridgeFailure.notAuthorized(statusName(status))
        }
    }

    private func statusPayload() -> [String: JSONValue] {
        let status = EKEventStore.authorizationStatus(for: .event)
        return [
            "provider": JSONValue("apple_eventkit"),
            "bridge": JSONValue("CalendarPilotEventKitBridge"),
            "authorization_status": JSONValue(statusName(status)),
            "authorized": JSONValue(isFullyAuthorized(status)),
            "bundle_id": JSONValue(Bundle.main.bundleIdentifier ?? "unbundled"),
            "sandbox_calendar_id": JSONValue(envSandboxCalendarID ?? ""),
            "sandbox_enforced": JSONValue(envSandboxCalendarID != nil),
        ]
    }

    private func statusName(_ status: EKAuthorizationStatus) -> String {
        if #available(macOS 14.0, *) {
            switch status {
            case .fullAccess: return "full_access"
            case .writeOnly: return "write_only"
            case .notDetermined: return "not_determined"
            case .restricted: return "restricted"
            case .denied: return "denied"
            case .authorized: return "authorized"
            @unknown default: return "unknown"
            }
        }
        switch status {
        case .notDetermined: return "not_determined"
        case .restricted: return "restricted"
        case .denied: return "denied"
        case .authorized: return "authorized"
        case .fullAccess: return "full_access"
        case .writeOnly: return "write_only"
        @unknown default: return "unknown"
        }
    }

    private func isFullyAuthorized(_ status: EKAuthorizationStatus) -> Bool {
        if #available(macOS 14.0, *) {
            return status == .fullAccess || status == .authorized
        }
        return status == .authorized
    }

    private func enforceSandbox(actions: [EventKitAction], sandboxCalendarID: String?) throws {
        guard let sandboxCalendarID, !sandboxCalendarID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        for action in actions where isWriteAction(action.actionType) {
            let target = action.calendarID.trimmingCharacters(in: .whitespacesAndNewlines)
            if target != sandboxCalendarID {
                throw BridgeFailure.sandboxViolation("action \(action.actionType.rawValue) targeted calendar '\(target.isEmpty ? "default" : target)' while sandbox is '\(sandboxCalendarID)'")
            }
        }
    }

    private func assertRollbackSandbox(_ payload: [String: JSONValue], sandboxCalendarID: String) throws {
        for (_, value) in payload["before_events"]?.objectValue ?? [:] {
            guard let row = value.objectValue else { continue }
            let calendarID = row["calendar_id"]?.stringValue ?? ""
            if calendarID != sandboxCalendarID {
                throw BridgeFailure.sandboxViolation("rollback attempted to restore non-sandbox calendar '\(calendarID)'")
            }
        }
        for eventID in stringArray(payload["created_external_ids"]) {
            if let event = store.event(withIdentifier: eventID), event.calendar?.calendarIdentifier != sandboxCalendarID && event.calendar?.title != sandboxCalendarID {
                throw BridgeFailure.sandboxViolation("rollback attempted to delete non-sandbox event '\(eventID)'")
            }
        }
    }

    private func calendar(id: String) throws -> EKCalendar {
        let calendars = store.calendars(for: .event)
        if id != "default", let match = calendars.first(where: { $0.calendarIdentifier == id || $0.title == id }) {
            return match
        }
        if let defaultCalendar = store.defaultCalendarForNewEvents, defaultCalendar.allowsContentModifications {
            return defaultCalendar
        }
        if let writable = calendars.first(where: { $0.allowsContentModifications }) {
            return writable
        }
        throw BridgeFailure.noWritableCalendar
    }

    private func eventForIdentifier(_ id: String) throws -> EKEvent {
        guard let event = store.event(withIdentifier: id) else {
            throw BridgeFailure.eventNotFound(id)
        }
        return event
    }

    private func currentIdentifier(for event: EKEvent) -> String {
        event.eventIdentifier ?? event.calendarItemIdentifier
    }

    private func isWriteAction(_ actionType: AtomicActionType) -> Bool {
        switch actionType {
        case .createEvent, .createFocusBlock, .addBuffer, .batchTasks, .moveEvent, .resizeEvent, .deleteOwnEvent:
            return true
        default:
            return false
        }
    }

    private func isCreateAction(_ actionType: AtomicActionType) -> Bool {
        switch actionType {
        case .createEvent, .createFocusBlock, .addBuffer, .batchTasks:
            return true
        default:
            return false
        }
    }

    private func existingEventIDs(for idempotencyKey: String) -> [String] {
        guard !idempotencyKey.isEmpty else { return [] }
        let end = Date().addingTimeInterval(366 * 24 * 60 * 60)
        let start = Date().addingTimeInterval(-30 * 24 * 60 * 60)
        let predicate = store.predicateForEvents(withStart: start, end: end, calendars: store.calendars(for: .event))
        return store.events(matching: predicate)
            .filter { ($0.notes ?? "").contains("CalendarPilot-Idempotency: \(idempotencyKey)#") }
            .map { currentIdentifier(for: $0) }
    }

    private func verifyRestoredEvent(_ row: [String: JSONValue]) -> Bool {
        guard
            let title = row["title"]?.stringValue,
            let start = try? dateField("start", in: row),
            let end = try? dateField("end", in: row)
        else { return false }
        if let id = row["event_id"]?.stringValue, let event = store.event(withIdentifier: id) {
            return event.title == title && abs(event.startDate.timeIntervalSince(start)) < 1 && abs(event.endDate.timeIntervalSince(end)) < 1
        }
        let predicate = store.predicateForEvents(withStart: start.addingTimeInterval(-1), end: end.addingTimeInterval(1), calendars: store.calendars(for: .event))
        return store.events(matching: predicate).contains { event in
            event.title == title && abs(event.startDate.timeIntervalSince(start)) < 1 && abs(event.endDate.timeIntervalSince(end)) < 1
        }
    }

    private func actionList(in payload: [String: JSONValue]) throws -> [EventKitAction] {
        guard case .array(let values)? = payload["actions"] else {
            return []
        }
        return try values.map { try decode(EventKitAction.self, from: $0) }
    }

    private func dateField(_ key: String, in payload: [String: JSONValue]) throws -> Date {
        guard let value = payload[key]?.stringValue else {
            throw BridgeFailure.missingField(key)
        }
        return try parseDate(value)
    }

    private func parseDate(_ value: String) throws -> Date {
        for formatter in makeISOFormatters() {
            if let date = formatter.date(from: value) {
                return date
            }
        }
        throw BridgeFailure.missingField("valid ISO-8601 date")
    }

    private func decode<T: Decodable>(_ type: T.Type, from value: JSONValue) throws -> T {
        let data = try encoder.encode(value)
        return try decoder.decode(type, from: data)
    }
}

private extension JSONValue {
    var arrayValue: [JSONValue]? {
        if case .array(let values) = self { return values }
        return nil
    }
}

private extension Optional where Wrapped == String {
    func orThrow(_ field: String) throws -> String {
        guard let value = self, !value.isEmpty else {
            throw BridgeFailure.missingField(field)
        }
        return value
    }
}

private extension Optional where Wrapped == Date {
    func orThrow(_ field: String) throws -> Date {
        guard let value = self else {
            throw BridgeFailure.missingField(field)
        }
        return value
    }
}

private func stringArray(_ value: JSONValue?) -> [String] {
    guard let values = value?.arrayValue else { return [] }
    return values.compactMap(\.stringValue)
}

private func argumentValue(after flag: String) -> String? {
    guard let index = CommandLine.arguments.firstIndex(of: flag) else { return nil }
    let valueIndex = CommandLine.arguments.index(after: index)
    guard valueIndex < CommandLine.arguments.endIndex else { return nil }
    return CommandLine.arguments[valueIndex]
}

private func makeISOFormatters() -> [ISO8601DateFormatter] {
    let fractional = ISO8601DateFormatter()
    fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    let standard = ISO8601DateFormatter()
    standard.formatOptions = [.withInternetDateTime]
    return [fractional, standard]
}

private func formatDate(_ date: Date) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return formatter.string(from: date)
}

private func makeDecoder() -> JSONDecoder {
    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .custom { decoder in
        let container = try decoder.singleValueContainer()
        let raw = try container.decode(String.self)
        for formatter in makeISOFormatters() {
            if let date = formatter.date(from: raw) {
                return date
            }
        }
        throw DecodingError.dataCorruptedError(in: container, debugDescription: "Expected ISO-8601 date")
    }
    return decoder
}

private func makeEncoder() -> JSONEncoder {
    let encoder = JSONEncoder()
    encoder.dateEncodingStrategy = .custom { date, encoder in
        var container = encoder.singleValueContainer()
        try container.encode(formatDate(date))
    }
    encoder.outputFormatting = [.sortedKeys]
    return encoder
}

#else
import Foundation

@main
private struct CalendarPilotEventKitBridge {
    static func main() {
        let response = [
            "ok": false,
            "result": [
                "provider": "apple_eventkit",
                "bridge": "CalendarPilotEventKitBridge",
                "authorization_status": "unsupported_platform",
                "authorized": false,
            ] as [String : Any],
            "error": "EventKit is only available on macOS"
        ] as [String : Any]
        if let data = try? JSONSerialization.data(withJSONObject: response, options: [.sortedKeys]), let text = String(data: data, encoding: .utf8) {
            FileHandle.standardOutput.write(Data((text + "\n").utf8))
        }
    }
}
#endif