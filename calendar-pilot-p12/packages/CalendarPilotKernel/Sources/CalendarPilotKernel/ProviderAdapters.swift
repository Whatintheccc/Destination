

import Foundation

public enum CalendarProviderError: Error, Equatable, Sendable {
    case notImplemented(providerID: String)
}

public struct CalendarProviderReceipt: Codable, Hashable, Sendable {
    public var providerID: String
    public var externalID: String?
    public var status: String
    public var message: String

    public init(providerID: String, externalID: String? = nil, status: String, message: String = "") {
        self.providerID = providerID
        self.externalID = externalID
        self.status = status
        self.message = message
    }
}

public protocol CalendarProviderAdapter: Sendable {
    var providerID: String { get }
    func readObservation(userScopeID: String) throws -> RawCalendarObservation
    func createEvent(_ action: AtomicCalendarAction) throws -> CalendarProviderReceipt
    func moveEvent(_ action: AtomicCalendarAction) throws -> CalendarProviderReceipt
    func deleteEvent(_ event: RawCalendarEvent) throws -> CalendarProviderReceipt
}

public struct GoogleCalendarAdapter: CalendarProviderAdapter {
    public let providerID = "google"
    public init() {}
    public func readObservation(userScopeID: String) throws -> RawCalendarObservation { RawCalendarObservation(observationID: "obs_google_stub", userScopeID: userScopeID, observedAt: Date(), timeZoneID: "UTC", events: []) }
    public func createEvent(_ action: AtomicCalendarAction) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
    public func moveEvent(_ action: AtomicCalendarAction) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
    public func deleteEvent(_ event: RawCalendarEvent) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
}

public struct AppleCalendarAdapter: CalendarProviderAdapter {
    public let providerID = "apple"
    public init() {}
    public func readObservation(userScopeID: String) throws -> RawCalendarObservation { RawCalendarObservation(observationID: "obs_apple_stub", userScopeID: userScopeID, observedAt: Date(), timeZoneID: "UTC", events: []) }
    public func createEvent(_ action: AtomicCalendarAction) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
    public func moveEvent(_ action: AtomicCalendarAction) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
    public func deleteEvent(_ event: RawCalendarEvent) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
}

public struct MicrosoftCalendarAdapter: CalendarProviderAdapter {
    public let providerID = "microsoft"
    public init() {}
    public func readObservation(userScopeID: String) throws -> RawCalendarObservation { RawCalendarObservation(observationID: "obs_microsoft_stub", userScopeID: userScopeID, observedAt: Date(), timeZoneID: "UTC", events: []) }
    public func createEvent(_ action: AtomicCalendarAction) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
    public func moveEvent(_ action: AtomicCalendarAction) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
    public func deleteEvent(_ event: RawCalendarEvent) throws -> CalendarProviderReceipt { throw CalendarProviderError.notImplemented(providerID: providerID) }
}