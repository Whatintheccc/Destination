import XCTest
@testable import CalendarPilotKernel

final class CalendarPilotKernelTests: XCTestCase {
    private func date(_ iso: String) -> Date {
        ISO8601DateFormatter().date(from: iso)!
    }

    private func emptyObservation() -> RawCalendarObservation {
        RawCalendarObservation(
            observationID: "obs1",
            userScopeID: "u",
            observedAt: date("2026-07-01T08:00:00-07:00"),
            timeZoneID: "America/Los_Angeles",
            events: []
        )
    }

    func testAutoWriteReversibleCreateEventAllowed() throws {
        let observation = emptyObservation()
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
        XCTAssertEqual(receipt.actuationMode, .materializedWrite)
        XCTAssertNotNil(receipt.rollbackHandleID)
        XCTAssertEqual(events.count, 1)
        XCTAssertEqual(events.first?.category, "focus")
    }

    func testDeniedWhenAuthorityTooLow() throws {
        let observation = emptyObservation()
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
        XCTAssertEqual(receipt.actuationMode, .denied)
        XCTAssertTrue(receipt.deniedReason?.contains("authority") == true)
        XCTAssertEqual(receipt.rejectedActionTypes, ["create_event"])
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
        let observation = emptyObservation()
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

    func testDraftPlanIsStagedNotMaterialized() throws {
        let candidate = CandidateCalendarAction(
            candidateID: "cand_draft",
            intent: "draft_day_repair_plan",
            actions: [AtomicCalendarAction(actionType: .draftSchedulePlan, title: "Draft repair", start: Date(), end: Date().addingTimeInterval(300), calendarID: "work")],
            targetCalendars: ["work"],
            affectedEventIDs: ["e1"],
            affectedPeopleIDs: ["person@example.com"],
            reversibility: .high,
            requiredAuthorityTier: 2
        )
        let (receipt, events) = CalendarKernel().authorizeAndMaterialize(candidate: candidate, observation: emptyObservation(), grantedAuthorityTier: 2)
        XCTAssertEqual(receipt.syncStatus, .staged)
        XCTAssertEqual(receipt.actuationMode, .stagedDraft)
        XCTAssertEqual(events.count, 0)
        XCTAssertEqual(receipt.stagedActionIDs.count, 1)
    }

    func testBatchTasksMaterializesTaskBatchEvent() throws {
        let candidate = CandidateCalendarAction(
            candidateID: "cand_batch",
            intent: "batch_admin_tasks",
            actions: [AtomicCalendarAction(actionType: .batchTasks, title: "Admin batch", start: date("2026-07-01T13:00:00-07:00"), end: date("2026-07-01T14:00:00-07:00"), calendarID: "work", metadata: ["task_ids": "t1,t2"])],
            targetCalendars: ["work"],
            affectedEventIDs: [],
            affectedPeopleIDs: [],
            reversibility: .high,
            requiredAuthorityTier: 3
        )
        let (receipt, events) = CalendarKernel().authorizeAndMaterialize(candidate: candidate, observation: emptyObservation(), grantedAuthorityTier: 3)
        XCTAssertEqual(receipt.syncStatus, .materialized)
        XCTAssertEqual(receipt.actuationMode, .materializedWrite)
        XCTAssertEqual(events.first?.category, "task_batch")
    }

    func testSocialActuationBoundaryDeniesPeopleMutation() throws {
        let candidate = CandidateCalendarAction(
            candidateID: "cand_social",
            intent: "move_people_meeting",
            actions: [AtomicCalendarAction(actionType: .moveEvent, title: "Move", eventID: "evt_social", start: date("2026-07-01T13:00:00-07:00"), end: date("2026-07-01T14:00:00-07:00"), calendarID: "work")],
            targetCalendars: ["work"],
            affectedEventIDs: ["evt_social"],
            affectedPeopleIDs: ["other@example.com"],
            reversibility: .medium,
            requiredAuthorityTier: 5
        )
        let (receipt, _) = CalendarKernel().authorizeAndMaterialize(candidate: candidate, observation: emptyObservation(), grantedAuthorityTier: 6)
        XCTAssertEqual(receipt.syncStatus, .denied)
        XCTAssertTrue(receipt.deniedReason?.contains("social actuation") == true)
    }

    func testCandidateSnakeCaseJSONRoundTripIncludesAgentFields() throws {
        let json = """
        {
          "candidate_id": "cand_json",
          "intent": "create_focus_block",
          "actions": [{"action_type": "create_focus_block", "title": "Focus", "start": "2026-07-01T09:00:00-07:00", "end": "2026-07-01T10:00:00-07:00", "calendar_id": "work", "metadata": {"source": "test"}}],
          "target_calendars": ["work"],
          "affected_event_ids": [],
          "affected_people_ids": [],
          "reversibility": "high",
          "required_authority_tier": 3,
          "predicted_acceptance": 0.7,
          "predicted_utility": 0.8,
          "predicted_engagement": 0.2,
          "predicted_regret": 0.05,
          "predicted_interruption_cost": 0.1,
          "predicted_social_risk": 0.0,
          "predicted_long_horizon_value": 0.6,
          "expected_reward": 1.4,
          "right_moment_decision": "auto_write_then_notify",
          "model_story": ["calendar pressure is high"],
          "counterfactual": "without action, prep stays fragmented",
          "control_notes": ["focus_mode_interruption_penalty=+0.20"],
          "reward_breakdown": {"utility": 0.9},
          "right_moment_score": 1.1,
          "simulated_outcomes": {"accepted": 2}
        }
        """.data(using: .utf8)!
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let candidate = try decoder.decode(CandidateCalendarAction.self, from: json)
        XCTAssertEqual(candidate.actions.first?.actionType, .createFocusBlock)
        XCTAssertEqual(candidate.modelStory.first, "calendar pressure is high")
        XCTAssertEqual(candidate.rightMomentDecision, .autoWriteThenNotify)
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let encoded = try encoder.encode(candidate)
        let text = String(data: encoded, encoding: .utf8)!
        XCTAssertTrue(text.contains("model_story"))
        XCTAssertTrue(text.contains("right_moment_score"))
    }

    func testProviderAdaptersExposeBoundaryButDoNotWrite() throws {
        let adapter = GoogleCalendarAdapter()
        XCTAssertEqual(adapter.providerID, "google")
        XCTAssertThrowsError(try adapter.createEvent(AtomicCalendarAction(actionType: .createEvent, title: "x")))
    }

    func testCodexToolCallRoundTrip() throws {
        let call = CodexToolCall(
            toolCallID: "tool1",
            toolName: .inspectWeek,
            input: ["goal": JSONValue("make next week less chaotic")],
            requestedAuthorityTier: 3,
            userVisibleReason: "inspect before acting",
            createdAt: date("2026-07-01T08:00:00-07:00")
        )
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        let data = try encoder.encode(call)
        let text = String(data: data, encoding: .utf8)!
        XCTAssertTrue(text.contains("tool_call_id"))
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let restored = try decoder.decode(CodexToolCall.self, from: data)
        XCTAssertEqual(restored.toolName, .inspectWeek)
        XCTAssertEqual(restored.requestedAuthorityTier, 3)
    }

    func testCodexBridgeStagesSocialMutationInsteadOfWriting() throws {
        let observation = emptyObservation()
        let candidate = CandidateCalendarAction(
            candidateID: "cand_codex_social",
            intent: "move_people_meeting",
            actions: [AtomicCalendarAction(actionType: .moveEvent, title: "Move", eventID: "evt_social", start: date("2026-07-01T13:00:00-07:00"), end: date("2026-07-01T14:00:00-07:00"), calendarID: "work")],
            targetCalendars: ["work"],
            affectedEventIDs: ["evt_social"],
            affectedPeopleIDs: ["other@example.com"],
            reversibility: .medium,
            requiredAuthorityTier: 5
        )
        let call = CodexToolCall(toolCallID: "tool_stage", toolName: .stageActionPacket, requestedAuthorityTier: 5)
        let receipt = CodexToolBridge().stage(candidate: candidate, observation: observation, call: call)
        XCTAssertEqual(receipt.status, .staged)
        XCTAssertTrue(receipt.requiresUserConfirmation)
        XCTAssertTrue(receipt.deniedReason?.contains("social") == true)
    }

    func testCodexBridgeCommitRoutesThroughKernelDenial() throws {
        let candidate = CandidateCalendarAction(
            candidateID: "cand_codex_commit",
            intent: "create_event",
            actions: [AtomicCalendarAction(actionType: .createEvent, title: "Block", start: date("2026-07-01T13:00:00-07:00"), end: date("2026-07-01T14:00:00-07:00"), calendarID: "work")],
            targetCalendars: ["work"],
            affectedEventIDs: [],
            affectedPeopleIDs: [],
            reversibility: .high,
            requiredAuthorityTier: 3
        )
        let call = CodexToolCall(toolCallID: "tool_commit", toolName: .requestCommit, requestedAuthorityTier: 1)
        let receipt = CodexToolBridge().commit(candidate: candidate, observation: emptyObservation(), call: call)
        XCTAssertEqual(receipt.status, .denied)
        XCTAssertTrue(receipt.deniedReason?.contains("authority") == true)
    }

}
