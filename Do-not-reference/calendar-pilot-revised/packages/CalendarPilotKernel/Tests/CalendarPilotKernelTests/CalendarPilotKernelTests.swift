import XCTest
@testable import CalendarPilotKernel

final class CalendarPilotKernelTests: XCTestCase {
    private func date(_ iso: String) -> Date {
        ISO8601DateFormatter().date(from: iso)!
    }

    func testAutoWriteReversibleCreateEventAllowed() throws {
        let observation = RawCalendarObservation(
            observationID: "obs1",
            userScopeID: "u",
            observedAt: date("2026-07-01T08:00:00-07:00"),
            timeZoneID: "America/Los_Angeles",
            events: []
        )
        let candidate = CandidateCalendarAction(
            candidateID: "cand1",
            intent: "create_focus_block",
            actions: [AtomicCalendarAction(actionType: .createFocusBlock, title: "Focus", start: date("2026-07-01T09:00:00-07:00"), end: date("2026-07-01T10:00:00-07:00"), calendarID: "work")],
            targetCalendars: ["work"],
            affectedEventIDs: [],
            affectedPeopleIDs: [],
            reversibility: .high,
            requiredAuthorityTier: 3
        )
        let kernel = CalendarKernel()
        let (receipt, events) = kernel.authorizeAndMaterialize(candidate: candidate, observation: observation, grantedAuthorityTier: 3)
        XCTAssertEqual(receipt.syncStatus, .materialized)
        XCTAssertNotNil(receipt.rollbackHandleID)
        XCTAssertEqual(events.count, 1)
    }

    func testDeniedWhenAuthorityTooLow() throws {
        let observation = RawCalendarObservation(observationID: "obs", userScopeID: "u", observedAt: Date(), timeZoneID: "UTC", events: [])
        let candidate = CandidateCalendarAction(
            candidateID: "cand2",
            intent: "create_prep_block",
            actions: [AtomicCalendarAction(actionType: .createEvent, title: "Prep", start: Date(), end: Date().addingTimeInterval(1800))],
            targetCalendars: ["work"],
            affectedEventIDs: [],
            affectedPeopleIDs: [],
            reversibility: .high,
            requiredAuthorityTier: 3
        )
        let kernel = CalendarKernel()
        let (receipt, _) = kernel.authorizeAndMaterialize(candidate: candidate, observation: observation, grantedAuthorityTier: 1)
        XCTAssertEqual(receipt.syncStatus, .denied)
        XCTAssertTrue(receipt.deniedReason?.contains("authority") == true)
    }

    func testConflictDetectionDeniesCreate() throws {
        let start = date("2026-07-01T09:00:00-07:00")
        let end = date("2026-07-01T10:00:00-07:00")
        let observation = RawCalendarObservation(
            observationID: "obs",
            userScopeID: "u",
            observedAt: date("2026-07-01T08:00:00-07:00"),
            timeZoneID: "America/Los_Angeles",
            events: [RawCalendarEvent(eventID: "busy", title: "Busy", start: start, end: end, calendarID: "work")]
        )
        let candidate = CandidateCalendarAction(
            candidateID: "cand3",
            intent: "create_conflicting_block",
            actions: [AtomicCalendarAction(actionType: .createEvent, title: "Overlap", start: start.addingTimeInterval(600), end: end.addingTimeInterval(600), calendarID: "work")],
            targetCalendars: ["work"],
            affectedEventIDs: [],
            affectedPeopleIDs: [],
            reversibility: .high,
            requiredAuthorityTier: 3
        )
        let kernel = CalendarKernel()
        let (receipt, events) = kernel.authorizeAndMaterialize(candidate: candidate, observation: observation, grantedAuthorityTier: 3)
        XCTAssertEqual(receipt.syncStatus, .denied)
        XCTAssertEqual(receipt.deniedReason, "conflict_detected")
        XCTAssertEqual(events.count, 1)
    }

    func testUndoRestoresOriginalEvents() throws {
        let observation = RawCalendarObservation(observationID: "obs", userScopeID: "u", observedAt: Date(), timeZoneID: "UTC", events: [])
        let candidate = CandidateCalendarAction(
            candidateID: "cand4",
            intent: "create_focus_block",
            actions: [AtomicCalendarAction(actionType: .createFocusBlock, title: "Focus", start: Date().addingTimeInterval(3600), end: Date().addingTimeInterval(7200), calendarID: "work")],
            targetCalendars: ["work"],
            affectedEventIDs: [],
            affectedPeopleIDs: [],
            reversibility: .high,
            requiredAuthorityTier: 3
        )
        let kernel = CalendarKernel()
        let (receipt, events) = kernel.authorizeAndMaterialize(candidate: candidate, observation: observation, grantedAuthorityTier: 3)
        XCTAssertEqual(events.count, 1)
        let restored = kernel.undo(rollbackHandleID: receipt.rollbackHandleID!)
        XCTAssertEqual(restored?.count, 0)
    }
}
