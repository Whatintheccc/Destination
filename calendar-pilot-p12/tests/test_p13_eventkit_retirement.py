from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from calendar_pilot.diffusiongemma import DiffusionGemmaPolicy
from calendar_pilot.codex.tools import CodexToolRuntime
from calendar_pilot.effect_kernel import (
    ManagedCalendarBinding,
    ManagedEventKitRetirementProvider,
    ManagedProcessLease,
    classify_managed_candidate,
    managed_commit_confirmation_provenance,
)
from calendar_pilot.providers.apple_eventkit import AppleEventKitManagedDriver, AppleEventKitProvider
from calendar_pilot.replay import ReplayBuffer
from calendar_pilot.swift_bridge.client import SwiftKernelStub
from calendar_pilot.types import CandidateCalendarAction, CodexToolCall, CodexToolName, RawCalendarObservation, UserBiography


ROOT = Path(__file__).resolve().parents[1]
BINDING_ID = "123e4567-e89b-42d3-a456-426614174000"


class FakeManagedDriver:
    provider_id = "apple_eventkit"

    def __init__(self, *, calendar_id: str = "calendar:managed", title: str = "CalendarPilot Managed") -> None:
        self.permission_status = "full_access"
        self.identity = {
            "permission_status": "full_access",
            "writable": True,
            "event_store_id": "store:test",
            "calendar_id": calendar_id,
            "source_id": "source:local",
            "source_type": "local",
            "title": title,
        }
        self.events: dict[str, dict] = {}
        self.create_count = 0
        self.remove_count = 0
        self.target_vector_hashes: list[str] = []
        self.crash_after_create_before_return = False
        self.ambiguous_idempotency_keys: set[str] = set()
        self.ambiguous_marker_event_ids: list[str] = []

    def binding_identity(self) -> dict:
        return dict(self.identity)

    def snapshot(self, calendar_id: str) -> dict:
        if calendar_id != self.identity["calendar_id"]:
            return {"events": {}, "binding_identity": self.binding_identity()}
        return {
            "events": dict(self.events),
            "binding_identity": self.binding_identity(),
            "ambiguous_idempotency_keys": sorted(self.ambiguous_idempotency_keys),
            "ambiguous_marker_event_ids": list(self.ambiguous_marker_event_ids),
        }

    def create(self, *, expected_binding: dict, target_vector: dict, idempotency_key: str, projection: dict) -> str:
        self._validate(expected_binding, target_vector)
        if projection["calendar_id"] != self.identity["calendar_id"]:
            raise ValueError("managed driver target escaped")
        external_id = "event:" + idempotency_key[-16:]
        self.events[idempotency_key] = {"external_id": external_id, **dict(projection)}
        self.target_vector_hashes.append(str(target_vector["sha256"]))
        self.create_count += 1
        if self.crash_after_create_before_return:
            self.crash_after_create_before_return = False
            raise RuntimeError("injected crash after remote create before local persistence")
        return external_id

    def remove(self, *, expected_binding: dict, target_vector: dict, idempotency_key: str, external_id: str) -> bool:
        self._validate(expected_binding, target_vector)
        row = self.events.get(idempotency_key)
        if row is None or row["external_id"] != external_id:
            return False
        self.events.pop(idempotency_key)
        self.remove_count += 1
        return True

    def _validate(self, expected: dict, vector: dict) -> None:
        fields = {
            "event_store_id": self.identity["event_store_id"],
            "calendar_id": self.identity["calendar_id"],
            "source_id": self.identity["source_id"],
            "source_type": self.identity["source_type"],
            "title_tripwire": self.identity["title"],
        }
        self.asserted_binding = expected
        if any(expected[key] != value for key, value in fields.items()):
            raise ValueError("managed driver binding mismatch")
        body = {key: value for key, value in vector.items() if key != "sha256"}
        from calendar_pilot.effect_kernel import content_sha256
        if vector.get("sha256") != content_sha256(body):
            raise ValueError("managed driver target vector mismatch")


class FakeIncumbent:
    provider_id = "apple_eventkit"

    def __init__(self, observation: RawCalendarObservation) -> None:
        self.observation = observation
        self.commit_count = 0
        self.rollback_count = 0

    def read_observation(self, *_args, **_kwargs):
        return self.observation

    def preview(self, _candidate):
        return []

    def conflict_truth(self, _candidate):
        return []

    def commit_candidate(self, *_args, **_kwargs):
        self.commit_count += 1
        return {"owner": "incumbent"}

    def rollback(self, _handle):
        self.rollback_count += 1
        return {"owner": "incumbent"}


class MockManagedBridge:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call(self, command: str, payload: dict) -> dict:
        self.calls.append((command, dict(payload)))
        if command == "status":
            return {"authorization_status": "full_access", "authorized": True}
        if command == "calendar_identity":
            return {
                "authorization_status": "full_access",
                "writable": True,
                "event_store_id": "store:test",
                "calendar_id": "calendar:managed",
                "source_id": "source:local",
                "source_type": "local",
                "title": "CalendarPilot Managed",
            }
        if command == "managed_snapshot":
            return {"events": {}, "binding_identity": {"calendar_id": "calendar:managed"}}
        if command == "managed_commit":
            expected = payload["expected_binding"]
            return {
                "created_external_ids": ["event:managed"],
                "pre_binding": expected,
                "post_binding": expected,
                "target_vector_sha256": payload["target_vector"]["sha256"],
                "verified": True,
            }
        if command == "managed_remove":
            expected = payload["expected_binding"]
            return {
                "pre_binding": expected,
                "post_binding": expected,
                "target_vector_sha256": payload["target_vector"]["sha256"],
                "verified_absent": True,
            }
        raise ValueError(command)


class ManagedEventKitRetirementTests(unittest.TestCase):
    def setUp(self) -> None:
        raw = json.loads((ROOT / "data/sample_calendar.json").read_text(encoding="utf-8"))
        raw["observed_at"] = datetime.now(timezone.utc).isoformat()
        self.observation = RawCalendarObservation.from_dict(raw)
        self.biography = UserBiography.from_dict(json.loads((ROOT / "data/sample_profile.json").read_text(encoding="utf-8")))
        self.driver = FakeManagedDriver()
        self.app_identity = {"path": "/Applications/CalendarPilot.app", "sha256": "a" * 64}
        self.bridge_identity = {
            "path": "/Applications/CalendarPilot.app/Contents/Resources/app/bin/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge",
            "sha256": "b" * 64,
        }
        self.binding = ManagedCalendarBinding.from_confirmed_setup(
            identity=self.driver.binding_identity(),
            app_identity=self.app_identity,
            bridge_identity=self.bridge_identity,
            confirmed_at=self.observation.observed_at,
            binding_id=BINDING_ID,
        )
        base = next(
            row for row in DiffusionGemmaPolicy().generate_candidates(self.observation, self.biography)
            if row.intent == "create_prep_block"
        )
        self.candidate = self._bound_candidate(base, candidate_id="candidate:managed:one")

    def _bound_candidate(self, candidate: CandidateCalendarAction, *, candidate_id: str) -> CandidateCalendarAction:
        payload = candidate.to_dict()
        payload["candidate_id"] = candidate_id
        payload["target_calendars"] = [self.binding.calendar_id]
        for action in payload["actions"]:
            action["calendar_id"] = self.binding.calendar_id
            action.setdefault("metadata", {})["calendarpilot_binding_id"] = self.binding.binding_id
            action["metadata"]["calendarpilot_binding_epoch"] = str(self.binding.epoch)
        return CandidateCalendarAction.from_dict(payload)

    def _provider(self, root: Path, *, acquire_lease: bool = False) -> ManagedEventKitRetirementProvider:
        return ManagedEventKitRetirementProvider(
            incumbent=FakeIncumbent(self.observation),
            driver=self.driver,
            binding=self.binding,
            state_root=root / "state",
            signing_key_path=root / "signing.key",
            lease_path=root / "owner.lock",
            seed_observation=self.observation,
            initialize=True,
            acquire_lease=acquire_lease,
        )

    def _grant(self, *, provenance: str, scopes=("recommend", "stage", "commit_private", "undo")):
        kernel = SwiftKernelStub()
        return kernel.issue_authority_grant(
            user_scope_id=self.observation.user_scope_id,
            max_authority_tier=3,
            scopes=scopes,
            confirmation_provenance=provenance,
            confirmed_by_user=True,
            issued_at=datetime.now(timezone.utc),
        )

    def test_binding_and_total_classifier_fail_closed(self):
        decision = classify_managed_candidate(self.candidate, self.binding)
        self.assertEqual((decision.managed, decision.owner, decision.status), (True, "effect_kernel", "managed"))

        missing = self.candidate.to_dict()
        for action in missing["actions"]:
            action["metadata"].pop("calendarpilot_binding_id", None)
            action["metadata"].pop("calendarpilot_binding_epoch", None)
        held = classify_managed_candidate(CandidateCalendarAction.from_dict(missing), self.binding)
        self.assertEqual((held.managed, held.owner, held.status), (True, "effect_kernel", "hold"))

        outside = self.candidate.to_dict()
        outside["target_calendars"] = ["calendar:other"]
        for action in outside["actions"]:
            action["calendar_id"] = "calendar:other"
            action["metadata"].pop("calendarpilot_binding_id", None)
            action["metadata"].pop("calendarpilot_binding_epoch", None)
        incumbent = classify_managed_candidate(CandidateCalendarAction.from_dict(outside), self.binding)
        self.assertEqual((incumbent.managed, incumbent.owner), (False, "incumbent"))

    def test_normal_frontier_prepares_prep_blocks_for_the_managed_binding(self):
        with tempfile.TemporaryDirectory() as td:
            provider = self._provider(Path(td))
            runtime = CodexToolRuntime(kernel=SwiftKernelStub(), replay=ReplayBuffer(), provider=provider)
            receipt = runtime.execute(
                CodexToolCall(
                    tool_call_id="tool:managed:frontier",
                    tool_name=CodexToolName.GENERATE_CANDIDATE_FRONTIER,
                    input={"limit": 8, "goal": "Make next week less chaotic"},
                    requested_authority_tier=3,
                    user_visible_reason="Generate managed candidates.",
                ),
                self.observation,
                self.biography,
            )
            prep = next(row for row in receipt.output["candidates"] if row["intent"] == "create_prep_block")
            self.assertTrue(all(action["action_type"] == "create_focus_block" for action in prep["actions"]))
            self.assertEqual(prep["target_calendars"], [self.binding.calendar_id])
            self.assertTrue(all(action["calendar_id"] == self.binding.calendar_id for action in prep["actions"]))
            self.assertTrue(all(action["metadata"]["calendarpilot_binding_id"] == self.binding.binding_id for action in prep["actions"]))

    def test_gateway_supports_two_events_replay_and_receipt_owned_undo(self):
        with tempfile.TemporaryDirectory() as td:
            provider = self._provider(Path(td))
            replay = ReplayBuffer()
            first_grant = self._grant(provenance=managed_commit_confirmation_provenance(self.candidate, self.binding))
            first = provider.commit_via_gateway(
                self.candidate,
                self.observation,
                first_grant,
                replay=replay,
                trace_id="trace:first",
                causal_parent_id=None,
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(first.phase, "verified")

            second_candidate = self._bound_candidate(self.candidate, candidate_id="candidate:managed:two")
            second_grant = self._grant(provenance=managed_commit_confirmation_provenance(second_candidate, self.binding))
            second = provider.commit_via_gateway(
                second_candidate,
                self.observation,
                second_grant,
                replay=replay,
                trace_id="trace:second",
                causal_parent_id=None,
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(second.phase, "verified")
            self.assertEqual(provider.retirement_snapshot()["active_event_count"], 2)

            replayed = provider.commit_via_gateway(
                self.candidate,
                self.observation,
                first_grant,
                replay=replay,
                trace_id="trace:replay",
                causal_parent_id=None,
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(replayed.ticket.ticket_id, first.ticket.ticket_id)
            self.assertEqual(self.driver.create_count, 2)

            handle = second.calendar_receipt.rollback_handle_id or ""
            undo_grant = self._grant(provenance=f"user_confirmed_undo:{handle}", scopes=("undo",))
            undone = provider.undo_via_gateway(
                handle,
                self.observation,
                undo_grant,
                replay=replay,
                trace_id="trace:undo",
                causal_parent_id=None,
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(undone.phase, "verified")
            self.assertEqual(provider.retirement_snapshot()["active_event_count"], 1)

    def test_exact_confirmation_and_identity_drift_block_before_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            provider = self._provider(Path(td))
            wrong = self._grant(provenance="dogfood_session_boot")
            with self.assertRaisesRegex(ValueError, "exact candidate confirmation"):
                provider.commit_via_gateway(
                    self.candidate,
                    self.observation,
                    wrong,
                    replay=ReplayBuffer(),
                    trace_id="trace:wrong",
                    causal_parent_id=None,
                )
            substituted_payload = self.candidate.to_dict()
            substituted_payload["actions"][0]["title"] = "Substituted after confirmation"
            substituted = CandidateCalendarAction.from_dict(substituted_payload)
            original_confirmation = self._grant(
                provenance=managed_commit_confirmation_provenance(self.candidate, self.binding)
            )
            with self.assertRaisesRegex(ValueError, "exact candidate confirmation"):
                provider.commit_via_gateway(
                    substituted,
                    self.observation,
                    original_confirmation,
                    replay=ReplayBuffer(),
                    trace_id="trace:substituted",
                    causal_parent_id=None,
                )
            self.driver.identity["title"] = "Renamed"
            exact = self._grant(provenance=managed_commit_confirmation_provenance(self.candidate, self.binding))
            with self.assertRaisesRegex(ValueError, "admission blocked"):
                provider.commit_via_gateway(
                    self.candidate,
                    self.observation,
                    exact,
                    replay=ReplayBuffer(),
                    trace_id="trace:drift",
                    causal_parent_id=None,
                )
            self.assertEqual(self.driver.create_count, 0)

    def test_startup_recovers_actual_external_id_after_remote_save_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            provider = self._provider(root)
            grant = self._grant(provenance=managed_commit_confirmation_provenance(self.candidate, self.binding))
            self.driver.crash_after_create_before_return = True
            with self.assertRaisesRegex(RuntimeError, "after remote create"):
                provider.commit_via_gateway(
                    self.candidate,
                    self.observation,
                    grant,
                    replay=ReplayBuffer(),
                    trace_id="trace:save-gap",
                    causal_parent_id=None,
                )
            context = provider.contexts[1]
            ticket_id = next(iter(context.ledger.snapshot()["outbox"]))
            idempotency_key = context.ledger.snapshot()["tickets"][ticket_id]["ticket"]["idempotency_key"]
            self.assertEqual(context.gateway.phase(ticket_id), "applying_unknown")
            self.assertNotIn(idempotency_key, context.ledger.snapshot()["adapter_state"]["external_ids"])
            actual_external_id = self.driver.events[idempotency_key]["external_id"]
            provider.close()

            restarted = ManagedEventKitRetirementProvider(
                incumbent=FakeIncumbent(self.observation),
                driver=self.driver,
                binding=self.binding,
                state_root=root / "state",
                signing_key_path=root / "signing.key",
                lease_path=root / "owner.lock",
                seed_observation=self.observation,
                initialize=False,
                acquire_lease=False,
            )
            self.assertEqual([row.phase for row in restarted.startup_reconciliation], ["verified"])
            recovered = restarted.contexts[1].ledger.snapshot()["adapter_state"]
            self.assertEqual(recovered["external_ids"][idempotency_key], actual_external_id)
            self.assertEqual(recovered["idempotency"][idempotency_key], ticket_id)

            replayed = restarted.commit_via_gateway(
                self.candidate,
                self.observation,
                grant,
                replay=ReplayBuffer(),
                trace_id="trace:save-gap:replay",
                causal_parent_id=None,
            )
            self.assertEqual(replayed.calendar_receipt.generated_event_ids, [actual_external_id])
            self.assertEqual(replayed.provider_receipt["external_ids"], [actual_external_id])
            self.assertEqual(self.driver.create_count, 1)
            handle = replayed.calendar_receipt.rollback_handle_id or ""
            undone = restarted.undo_via_gateway(
                handle,
                self.observation,
                self._grant(provenance=f"user_confirmed_undo:{handle}", scopes=("undo",)),
                replay=ReplayBuffer(),
                trace_id="trace:save-gap:undo",
                causal_parent_id=None,
            )
            self.assertEqual(undone.phase, "verified")
            self.assertFalse(self.driver.events)

    def test_recovery_holds_on_duplicate_marker_or_projection_mismatch(self):
        for fault in ("duplicate", "content"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self.driver = FakeManagedDriver()
                provider = self._provider(root)
                grant = self._grant(provenance=managed_commit_confirmation_provenance(self.candidate, self.binding))
                self.driver.crash_after_create_before_return = True
                with self.assertRaises(RuntimeError):
                    provider.commit_via_gateway(
                        self.candidate,
                        self.observation,
                        grant,
                        replay=ReplayBuffer(),
                        trace_id=f"trace:{fault}",
                        causal_parent_id=None,
                    )
                context = provider.contexts[1]
                ticket_id = next(iter(context.ledger.snapshot()["outbox"]))
                idempotency_key = context.ledger.snapshot()["tickets"][ticket_id]["ticket"]["idempotency_key"]
                if fault == "duplicate":
                    self.driver.ambiguous_idempotency_keys.add(idempotency_key)
                else:
                    self.driver.events[idempotency_key]["title"] = "Changed after save"
                provider.close()
                restarted = ManagedEventKitRetirementProvider(
                    incumbent=FakeIncumbent(self.observation),
                    driver=self.driver,
                    binding=self.binding,
                    state_root=root / "state",
                    signing_key_path=root / "signing.key",
                    lease_path=root / "owner.lock",
                    seed_observation=self.observation,
                    initialize=False,
                    acquire_lease=False,
                )
                self.assertEqual([row.phase for row in restarted.startup_reconciliation], ["hold"])
                state = restarted.contexts[1].ledger.snapshot()["adapter_state"]
                self.assertNotIn(idempotency_key, state["external_ids"])
                self.assertEqual(self.driver.remove_count, 0)

    def test_initialize_is_create_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            provider = self._provider(root)
            registry = (root / "state/binding-registry.json").read_bytes()
            provider.close()
            with self.assertRaisesRegex(ValueError, "empty durable state"):
                self._provider(root)
            self.assertEqual((root / "state/binding-registry.json").read_bytes(), registry)

    def test_rebind_restart_uses_exact_driver_for_historical_undo(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old_driver = self.driver
            new_driver = FakeManagedDriver(calendar_id="calendar:rebound", title="CalendarPilot Rebound")
            drivers = {old_driver.identity["calendar_id"]: old_driver, new_driver.identity["calendar_id"]: new_driver}
            factory = lambda row: drivers[row.calendar_id]
            provider = ManagedEventKitRetirementProvider(
                incumbent=FakeIncumbent(self.observation),
                driver=old_driver,
                driver_factory=factory,
                binding=self.binding,
                state_root=root / "state",
                signing_key_path=root / "signing.key",
                lease_path=root / "owner.lock",
                seed_observation=self.observation,
                initialize=True,
                acquire_lease=False,
            )
            applied = provider.commit_via_gateway(
                self.candidate,
                self.observation,
                self._grant(provenance=managed_commit_confirmation_provenance(self.candidate, self.binding)),
                replay=ReplayBuffer(),
                trace_id="trace:rebind:apply",
                causal_parent_id=None,
            )
            handle = applied.calendar_receipt.rollback_handle_id or ""
            rebound = provider.rebind(identity=new_driver.binding_identity(), confirmed_at=datetime.now(timezone.utc))
            provider.close()
            restarted = ManagedEventKitRetirementProvider(
                incumbent=FakeIncumbent(self.observation),
                driver=new_driver,
                driver_factory=factory,
                binding=rebound,
                state_root=root / "state",
                signing_key_path=root / "signing.key",
                lease_path=root / "owner.lock",
                seed_observation=self.observation,
                initialize=False,
                acquire_lease=False,
            )
            undone = restarted.undo_via_gateway(
                handle,
                self.observation,
                self._grant(provenance=f"user_confirmed_undo:{handle}", scopes=("undo",)),
                replay=ReplayBuffer(),
                trace_id="trace:rebind:undo",
                causal_parent_id=None,
            )
            self.assertEqual((undone.phase, undone.binding.epoch), ("verified", 1))
            self.assertEqual((old_driver.remove_count, new_driver.remove_count), (1, 0))
            self.assertFalse(old_driver.events)

    def test_normal_runtime_commit_and_undo_use_managed_gateway(self):
        with tempfile.TemporaryDirectory() as td:
            provider = self._provider(Path(td))
            kernel = SwiftKernelStub()
            replay = ReplayBuffer()
            runtime = CodexToolRuntime(kernel=kernel, replay=replay, provider=provider)
            runtime.frontier[self.candidate.candidate_id] = self.candidate
            grant = kernel.issue_authority_grant(
                user_scope_id=self.observation.user_scope_id,
                max_authority_tier=3,
                scopes=("recommend", "stage", "commit_private", "undo"),
                confirmation_provenance=managed_commit_confirmation_provenance(self.candidate, self.binding),
                confirmed_by_user=True,
                issued_at=datetime.now(timezone.utc),
            )
            commit = runtime.execute(
                CodexToolCall(
                    tool_call_id="tool:managed:commit",
                    tool_name=CodexToolName.REQUEST_COMMIT,
                    input={"candidate_id": self.candidate.candidate_id},
                    requested_authority_tier=3,
                    user_visible_reason="Confirm exact managed EventKit event.",
                    authority_grant_id=grant.grant_id,
                    correlation_id="trace:managed:runtime",
                ),
                self.observation,
                self.biography,
            )
            self.assertEqual(commit.status.value, "committed")
            handle = str(commit.output["swift_receipt"]["rollback_handle_id"])
            undo_grant = kernel.issue_authority_grant(
                user_scope_id=self.observation.user_scope_id,
                max_authority_tier=3,
                scopes=("undo",),
                confirmation_provenance=f"user_confirmed_undo:{handle}",
                confirmed_by_user=True,
                issued_at=datetime.now(timezone.utc),
            )
            undo = runtime.execute(
                CodexToolCall(
                    tool_call_id="tool:managed:undo",
                    tool_name=CodexToolName.REQUEST_UNDO,
                    input={"rollback_handle_id": handle},
                    requested_authority_tier=3,
                    user_visible_reason="Confirm exact managed EventKit undo.",
                    authority_grant_id=undo_grant.grant_id,
                    correlation_id="trace:managed:runtime",
                ),
                self.observation,
                self.biography,
            )
            self.assertEqual(undo.status.value, "reverted")
            self.assertEqual(provider.retirement_snapshot()["direct_commit_count"], 0)
            self.assertEqual(provider.retirement_snapshot()["direct_undo_count"], 0)

    def test_old_epoch_undo_keeps_its_owner_and_holds_on_identity_drift(self):
        with tempfile.TemporaryDirectory() as td:
            provider = self._provider(Path(td))
            replay = ReplayBuffer()
            apply_grant = self._grant(provenance=managed_commit_confirmation_provenance(self.candidate, self.binding))
            applied = provider.commit_via_gateway(
                self.candidate,
                self.observation,
                apply_grant,
                replay=replay,
                trace_id="trace:old-epoch",
                causal_parent_id=None,
            )
            handle = applied.calendar_receipt.rollback_handle_id or ""
            rebound = provider.rebind(identity=self.driver.binding_identity(), confirmed_at=datetime.now(timezone.utc))
            self.assertEqual(rebound.epoch, 2)
            undo_grant = self._grant(provenance=f"user_confirmed_undo:{handle}", scopes=("undo",))
            undone = provider.undo_via_gateway(
                handle,
                self.observation,
                undo_grant,
                replay=replay,
                trace_id="trace:old-epoch:undo",
                causal_parent_id=None,
            )
            self.assertEqual((undone.phase, undone.binding.epoch), ("verified", 1))

        with tempfile.TemporaryDirectory() as td:
            self.driver = FakeManagedDriver()
            provider = self._provider(Path(td))
            replay = ReplayBuffer()
            apply_grant = self._grant(provenance=managed_commit_confirmation_provenance(self.candidate, self.binding))
            applied = provider.commit_via_gateway(
                self.candidate,
                self.observation,
                apply_grant,
                replay=replay,
                trace_id="trace:drifted-old-epoch",
                causal_parent_id=None,
            )
            handle = applied.calendar_receipt.rollback_handle_id or ""
            self.driver.identity["title"] = "Renamed externally"
            undo_grant = self._grant(provenance=f"user_confirmed_undo:{handle}", scopes=("undo",))
            with self.assertRaisesRegex(ValueError, "drift requires manual reconciliation"):
                provider.undo_via_gateway(
                    handle,
                    self.observation,
                    undo_grant,
                    replay=replay,
                    trace_id="trace:drifted-old-epoch:undo",
                    causal_parent_id=None,
                )

    def test_os_lease_and_missing_durable_state_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lease = ManagedProcessLease(root / "owner.lock", binding_id=self.binding.binding_id)
            try:
                with self.assertRaisesRegex(RuntimeError, "already held"):
                    ManagedProcessLease(root / "owner.lock", binding_id=self.binding.binding_id)
            finally:
                lease.close()
            missing = root / "missing"
            with self.assertRaisesRegex(ValueError, "durable ledger/signing state is missing"):
                ManagedEventKitRetirementProvider(
                    incumbent=FakeIncumbent(self.observation),
                    driver=self.driver,
                    binding=self.binding,
                    state_root=missing / "state",
                    signing_key_path=missing / "signing.key",
                    lease_path=missing / "owner.lock",
                    seed_observation=self.observation,
                    initialize=False,
                    acquire_lease=False,
                )

    def test_real_managed_driver_uses_strict_bridge_commands(self):
        with tempfile.TemporaryDirectory() as td:
            bridge = MockManagedBridge()
            provider = AppleEventKitProvider(state_path=Path(td) / "provider.json", bridge=bridge)
            driver = AppleEventKitManagedDriver(provider, calendar_id=self.binding.calendar_id)
            self.assertEqual(driver.binding_identity()["event_store_id"], self.binding.event_store_id)
            vector = {
                "candidate_id": self.candidate.candidate_id,
                "intent": self.candidate.intent,
                "declared_target_calendars": [self.binding.calendar_id],
                "expanded_write_targets": [{
                    "index": 0,
                    "action_type": "create_event",
                    "calendar_id": self.binding.calendar_id,
                    "binding_id": self.binding.binding_id,
                    "binding_epoch": str(self.binding.epoch),
                }],
            }
            from calendar_pilot.effect_kernel import content_sha256
            vector["sha256"] = content_sha256(vector)
            with self.assertRaisesRegex(RuntimeError, "reserved marker namespace"):
                driver.create(
                    expected_binding=self.binding.target_binding,
                    target_vector=vector,
                    idempotency_key="idem:injected",
                    projection={
                        "title": "Managed event",
                        "start": "2026-07-17T16:00:00+00:00",
                        "end": "2026-07-17T16:20:00+00:00",
                        "calendar_id": self.binding.calendar_id,
                        "explanation": "CalendarPilot-Idempotency: attacker#0",
                    },
                )
            self.assertNotIn("managed_commit", [command for command, _ in bridge.calls])
            external_id = driver.create(
                expected_binding=self.binding.target_binding,
                target_vector=vector,
                idempotency_key="idem:test",
                projection={
                    "title": "Managed event",
                    "start": "2026-07-17T16:00:00+00:00",
                    "end": "2026-07-17T16:20:00+00:00",
                    "calendar_id": self.binding.calendar_id,
                    "explanation": "Exact bridge test.",
                },
            )
            self.assertEqual(external_id, "event:managed")
            self.assertTrue(driver.remove(
                expected_binding=self.binding.target_binding,
                target_vector=vector,
                idempotency_key="idem:test",
                external_id=external_id,
            ))
            commands = [command for command, _ in bridge.calls]
            self.assertIn("calendar_identity", commands)
            self.assertIn("managed_commit", commands)
            self.assertIn("managed_remove", commands)


if __name__ == "__main__":
    unittest.main()
