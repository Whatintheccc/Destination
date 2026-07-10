from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.plan_graph import actions_from_plan_metadata
from calendar_pilot.product_core import run_create_prep_block_vertical
from calendar_pilot.replay import ReplayBuffer, observation_fingerprint
from calendar_pilot.types import (
    ActuationMode,
    AtomicActionType,
    AuthorityGrant as RuntimeAuthorityGrant,
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarObservation,
    StageState,
)

from .kernel import (
    EVENTKIT_AUTHORITY_PROFILE,
    EVENTKIT_ADAPTER_ID,
    EventKitSandboxAdapter,
    EffectAttempt,
    EffectReceipt,
    EffectTicket,
    SandboxAuthorityGate,
    SandboxEffectGateway,
    SandboxEffectLedger,
    content_sha256,
)


MANAGED_AUTHORITY_PROFILE = "owner_controlled_eventkit_binding_retirement"
MANAGED_LEDGER_AUTHORITY_PROFILE = EVENTKIT_AUTHORITY_PROFILE
MANAGED_BACKEND = "apple_eventkit"
MANAGED_OWNER = "effect_kernel"
BINDING_VERSION = "managed_eventkit_binding.v1"
BINDING_REGISTRY_VERSION = "managed_eventkit_binding_registry.v1"
MANAGED_ADAPTER_ID = "apple_eventkit_managed_binding"
WRITE_ACTIONS = {
    AtomicActionType.CREATE_EVENT,
    AtomicActionType.CREATE_FOCUS_BLOCK,
    AtomicActionType.ADD_BUFFER,
    AtomicActionType.BATCH_TASKS,
    AtomicActionType.MOVE_EVENT,
    AtomicActionType.RESIZE_EVENT,
    AtomicActionType.DELETE_OWN_EVENT,
}


class ManagedEventKitDriver(Protocol):
    provider_id: str
    permission_status: str

    def binding_identity(self) -> dict[str, Any]: ...
    def snapshot(self, calendar_id: str) -> dict[str, Any]: ...
    def create(
        self,
        *,
        expected_binding: dict[str, Any],
        target_vector: dict[str, Any],
        idempotency_key: str,
        projection: dict[str, Any],
    ) -> str: ...
    def remove(
        self,
        *,
        expected_binding: dict[str, Any],
        target_vector: dict[str, Any],
        idempotency_key: str,
        external_id: str,
    ) -> bool: ...


@dataclass(frozen=True)
class ManagedCalendarBinding:
    binding_schema_version: str
    binding_id: str
    epoch: int
    event_store_id: str
    calendar_id: str
    source_id: str
    source_type: str
    title_tripwire: str
    app_path: str
    app_sha256: str
    bridge_path: str
    bridge_sha256: str
    confirmed_at: str

    def __post_init__(self) -> None:
        if self.binding_schema_version != BINDING_VERSION:
            raise ValueError("unsupported managed EventKit binding version")
        parsed = UUID(self.binding_id)
        if parsed.version != 4:
            raise ValueError("managed EventKit binding_id must be opaque UUIDv4")
        if self.epoch < 1:
            raise ValueError("managed EventKit binding epoch must be positive")
        required = {
            "event_store_id": self.event_store_id,
            "calendar_id": self.calendar_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title_tripwire": self.title_tripwire,
            "app_path": self.app_path,
            "app_sha256": self.app_sha256,
            "bridge_path": self.bridge_path,
            "bridge_sha256": self.bridge_sha256,
            "confirmed_at": self.confirmed_at,
        }
        if any(not str(value).strip() for value in required.values()):
            raise ValueError("managed EventKit binding fields must be nonempty")
        if len(self.app_sha256) != 64 or len(self.bridge_sha256) != 64:
            raise ValueError("managed EventKit app and bridge identities require SHA-256")
        if not self.app_path.endswith("CalendarPilot.app") or not self.bridge_path.startswith(self.app_path + "/Contents/Resources/app/bin/"):
            raise ValueError("managed EventKit binding requires the canonical app-bundled bridge path")

    @classmethod
    def from_confirmed_setup(
        cls,
        *,
        identity: dict[str, Any],
        app_identity: dict[str, Any],
        bridge_identity: dict[str, Any],
        confirmed_at: datetime,
        binding_id: str | None = None,
        epoch: int = 1,
    ) -> "ManagedCalendarBinding":
        if confirmed_at.tzinfo is None or confirmed_at.utcoffset() is None:
            raise ValueError("managed EventKit setup confirmation must be timezone-aware")
        if identity.get("permission_status") != "full_access" or identity.get("writable") is not True:
            raise ValueError("managed EventKit setup requires full access and a writable calendar")
        return cls(
            binding_schema_version=BINDING_VERSION,
            binding_id=binding_id or str(uuid4()),
            epoch=epoch,
            event_store_id=str(identity["event_store_id"]),
            calendar_id=str(identity["calendar_id"]),
            source_id=str(identity["source_id"]),
            source_type=str(identity["source_type"]),
            title_tripwire=str(identity["title"]),
            app_path=str(app_identity["path"]),
            app_sha256=str(app_identity["sha256"]),
            bridge_path=str(bridge_identity["path"]),
            bridge_sha256=str(bridge_identity["sha256"]),
            confirmed_at=confirmed_at.isoformat(),
        )

    @property
    def fingerprint_fields(self) -> dict[str, str]:
        return {
            "event_store_id": self.event_store_id,
            "calendar_id": self.calendar_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title_tripwire": self.title_tripwire,
        }

    @property
    def fingerprint_sha256(self) -> str:
        return content_sha256(self.fingerprint_fields)

    @property
    def target_binding(self) -> dict[str, Any]:
        return {
            "provider_id": MANAGED_BACKEND,
            "binding_id": self.binding_id,
            "binding_epoch": self.epoch,
            "binding_fingerprint_sha256": self.fingerprint_sha256,
            **self.fingerprint_fields,
            "app_path": self.app_path,
            "app_sha256": self.app_sha256,
            "bridge_path": self.bridge_path,
            "bridge_sha256": self.bridge_sha256,
        }

    def rebind(self, *, identity: dict[str, Any], confirmed_at: datetime) -> "ManagedCalendarBinding":
        return self.from_confirmed_setup(
            identity=identity,
            app_identity={"path": self.app_path, "sha256": self.app_sha256},
            bridge_identity={"path": self.bridge_path, "sha256": self.bridge_sha256},
            confirmed_at=confirmed_at,
            binding_id=self.binding_id,
            epoch=self.epoch + 1,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding_schema_version": self.binding_schema_version,
            "binding_id": self.binding_id,
            "epoch": self.epoch,
            "event_store_id": self.event_store_id,
            "calendar_id": self.calendar_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title_tripwire": self.title_tripwire,
            "app_path": self.app_path,
            "app_sha256": self.app_sha256,
            "bridge_path": self.bridge_path,
            "bridge_sha256": self.bridge_sha256,
            "confirmed_at": self.confirmed_at,
            "fingerprint_sha256": self.fingerprint_sha256,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ManagedCalendarBinding":
        restored = dict(value)
        fingerprint = restored.pop("fingerprint_sha256", None)
        binding = cls(**restored)
        if fingerprint is not None and fingerprint != binding.fingerprint_sha256:
            raise ValueError("managed EventKit binding fingerprint mismatch")
        return binding


@dataclass(frozen=True)
class ManagedOwnershipDecision:
    managed: bool
    owner: str
    status: str
    reason: str | None
    target_vector: dict[str, Any]


def _expanded_actions(candidate: CandidateCalendarAction) -> list[Any]:
    output: list[Any] = []
    for action in candidate.actions:
        if action.action_type == AtomicActionType.AUTO_APPLY_PLAN:
            nested = actions_from_plan_metadata(action.metadata)
            if nested:
                output.extend(nested)
                continue
        output.append(action)
    return output


def canonical_target_vector(candidate: CandidateCalendarAction) -> dict[str, Any]:
    rows = []
    for index, action in enumerate(_expanded_actions(candidate)):
        if action.action_type not in WRITE_ACTIONS:
            continue
        rows.append({
            "index": index,
            "action_type": action.action_type.value,
            "calendar_id": action.calendar_id,
            "binding_id": action.metadata.get("calendarpilot_binding_id", ""),
            "binding_epoch": action.metadata.get("calendarpilot_binding_epoch", ""),
        })
    payload = {
        "candidate_id": candidate.candidate_id,
        "intent": candidate.intent,
        "declared_target_calendars": sorted(candidate.target_calendars),
        "expanded_write_targets": rows,
    }
    return {**payload, "sha256": content_sha256(payload)}


def classify_managed_candidate(candidate: CandidateCalendarAction, binding: ManagedCalendarBinding) -> ManagedOwnershipDecision:
    vector = canonical_target_vector(candidate)
    rows = vector["expanded_write_targets"]
    named_ids = {str(row["binding_id"]) for row in rows if row["binding_id"]}
    targets = {str(row["calendar_id"]) for row in rows}
    declared = set(vector["declared_target_calendars"])
    managed = bool(named_ids or binding.calendar_id in targets or binding.calendar_id in declared)
    if not managed:
        return ManagedOwnershipDecision(False, "incumbent", "outside", None, vector)
    exact_epoch = str(binding.epoch)
    valid = bool(
        candidate.intent == "create_prep_block"
        and rows
        and targets == {binding.calendar_id}
        and declared == {binding.calendar_id}
        and named_ids == {binding.binding_id}
        and all(str(row["binding_epoch"]) == exact_epoch for row in rows)
    )
    if not valid:
        return ManagedOwnershipDecision(True, "effect_kernel", "hold", "managed_target_binding_invalid", vector)
    return ManagedOwnershipDecision(True, "effect_kernel", "managed", None, vector)


def managed_commit_confirmation_provenance(
    candidate: CandidateCalendarAction,
    binding: ManagedCalendarBinding,
) -> str:
    digest = content_sha256({"candidate": candidate.to_dict(), "target_binding": binding.target_binding})
    return f"user_confirmed_commit:{candidate.candidate_id}:{digest}"


class ManagedProcessLease:
    def __init__(self, path: str | Path, *, binding_id: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(self._fd)
            self._fd = -1
            raise RuntimeError("managed EventKit owner lease is already held") from exc
        payload = json.dumps({"pid": os.getpid(), "binding_id": binding_id}, sort_keys=True).encode()
        os.ftruncate(self._fd, 0)
        os.write(self._fd, payload)
        os.fsync(self._fd)

    def close(self) -> None:
        if self._fd >= 0:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = -1

    def __del__(self) -> None:
        self.close()


class ManagedEventKitAdapter(EventKitSandboxAdapter):
    adapter_id = EVENTKIT_ADAPTER_ID
    credential_fields = ("eventkit_os_calendar_permission",)
    external_io = True
    real_provider_reachable = True
    supported_action_families = frozenset({"create_prep_block"})
    provider_only_through_gateway = True

    def __init__(self, *, driver: ManagedEventKitDriver, binding: ManagedCalendarBinding):
        if getattr(driver, "provider_id", None) != MANAGED_BACKEND:
            raise ValueError("managed EventKit adapter requires apple_eventkit")
        self.driver = driver
        self.binding = binding
        self.ticket_binding = binding.target_binding
        self._ledger_tickets: list[EffectTicket] = []

    @staticmethod
    def initial_state() -> dict[str, Any]:
        return {
            "idempotency": {},
            "external_ids": {},
            "out_of_band": {},
            "mutation_count": 0,
            "compensation_mutation_count": 0,
        }

    @classmethod
    def normalize(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        state = deepcopy(value) if isinstance(value, dict) else cls.initial_state()
        if set(state) != set(cls.initial_state()):
            raise ValueError("managed EventKit adapter state shape is invalid")
        return state

    def identity_reason(self) -> str | None:
        if str(getattr(self.driver, "permission_status", "unknown")) != "full_access":
            return "eventkit_permission_suspended"
        observed = self.driver.binding_identity()
        expected = self.binding.fingerprint_fields
        actual = {
            "event_store_id": str(observed.get("event_store_id", "")),
            "calendar_id": str(observed.get("calendar_id", "")),
            "source_id": str(observed.get("source_id", "")),
            "source_type": str(observed.get("source_type", "")),
            "title_tripwire": str(observed.get("title", "")),
        }
        if observed.get("writable") is not True or actual != expected:
            return "eventkit_binding_rebind_required"
        return None

    def validate_attempt(self, attempt: EffectAttempt) -> str | None:
        if attempt.target_binding != self.ticket_binding:
            return "target_binding_invalid"
        projection = attempt.intent.get("projection", {})
        if projection.get("calendar_id") != self.binding.calendar_id:
            return "target_binding_invalid"
        vector = attempt.intent.get("canonical_target_vector")
        if not isinstance(vector, dict) or vector.get("sha256") != content_sha256({k: v for k, v in vector.items() if k != "sha256"}):
            return "canonical_target_vector_invalid"
        return self.identity_reason()

    def state_hash(self, value: dict[str, Any] | None) -> str:
        return content_sha256({
            "local": self.normalize(value),
            "remote": self.driver.snapshot(self.binding.calendar_id),
            "target_binding": self.ticket_binding,
        })

    @staticmethod
    def _remote_event_id(row: dict[str, Any]) -> str:
        return str(row.get("event_id") or row.get("external_id") or "")

    def _remote_projection_matches(self, ticket: EffectTicket, row: dict[str, Any]) -> bool:
        projection = ticket.intent.get("projection", {})
        if not isinstance(projection, dict):
            return False
        if (
            str(row.get("calendar_id", "")) != str(projection.get("calendar_id", ""))
            or str(row.get("title", "")) != str(projection.get("title", ""))
            or not self._remote_event_id(row)
        ):
            return False
        try:
            remote_start = datetime.fromisoformat(str(row["start"]).replace("Z", "+00:00"))
            remote_end = datetime.fromisoformat(str(row["end"]).replace("Z", "+00:00"))
            expected_start = datetime.fromisoformat(str(projection["start"]).replace("Z", "+00:00"))
            expected_end = datetime.fromisoformat(str(projection["end"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            return False
        return abs((remote_start - expected_start).total_seconds()) < 1 and abs((remote_end - expected_end).total_seconds()) < 1

    @staticmethod
    def _snapshot_is_ambiguous(snapshot: dict[str, Any], idempotency_key: str) -> bool:
        return bool(
            snapshot.get("ambiguous_marker_event_ids")
            or idempotency_key in set(str(value) for value in snapshot.get("ambiguous_idempotency_keys", []))
        )

    def dispatch_apply(self, value: dict[str, Any], ticket: EffectTicket) -> dict[str, Any]:
        state = self.normalize(value)
        if ticket.idempotency_key in state["idempotency"]:
            return state
        if ticket.target_binding != self.ticket_binding or self.identity_reason():
            raise ValueError("managed EventKit binding changed before dispatch")
        vector = dict(ticket.intent["canonical_target_vector"])
        external_id = self.driver.create(
            expected_binding=self.ticket_binding,
            target_vector=vector,
            idempotency_key=ticket.idempotency_key,
            projection=deepcopy(ticket.intent["projection"]),
        )
        state["idempotency"][ticket.idempotency_key] = ticket.ticket_id
        state["external_ids"][ticket.idempotency_key] = external_id
        state["mutation_count"] += 1
        return state

    def dispatch_compensation(self, value: dict[str, Any], ticket: EffectTicket, target_receipt: EffectReceipt) -> dict[str, Any]:
        state = self.normalize(value)
        if ticket.idempotency_key in state["idempotency"]:
            return state
        if ticket.target_binding != self.ticket_binding or self.identity_reason():
            raise ValueError("managed EventKit binding changed before compensation")
        target_key = target_receipt.idempotency_key
        external_id = state["external_ids"].get(target_key)
        if external_id is None:
            return state
        apply_ticket = None
        for row in self._ledger_tickets:
            if row.idempotency_key == target_key:
                apply_ticket = row
                break
        vector = dict(apply_ticket.intent["canonical_target_vector"]) if apply_ticket is not None else {}
        removed = self.driver.remove(
            expected_binding=self.ticket_binding,
            target_vector=vector,
            idempotency_key=target_key,
            external_id=external_id,
        )
        if removed:
            state["external_ids"].pop(target_key, None)
            state["idempotency"][ticket.idempotency_key] = ticket.ticket_id
            state["compensation_mutation_count"] += 1
        return state

    def outcome(self, value: dict[str, Any], ticket: EffectTicket, target_receipt: EffectReceipt | None = None) -> str:
        if self.identity_reason():
            return "hold"
        state = self.normalize(value)
        snapshot = self.driver.snapshot(self.binding.calendar_id)
        remote = snapshot.get("events", {})
        if ticket.kind == "apply":
            if self._snapshot_is_ambiguous(snapshot, ticket.idempotency_key):
                return "hold"
            row = remote.get(ticket.idempotency_key)
            if row is None:
                return "not_applied"
            if not isinstance(row, dict) or not self._remote_projection_matches(ticket, row):
                return "hold"
            actual_external_id = self._remote_event_id(row)
            local_external_id = state["external_ids"].get(ticket.idempotency_key)
            local_ticket_id = state["idempotency"].get(ticket.idempotency_key)
            if local_external_id is None and local_ticket_id is None:
                state["external_ids"][ticket.idempotency_key] = actual_external_id
                state["idempotency"][ticket.idempotency_key] = ticket.ticket_id
                state["mutation_count"] += 1
                value.clear()
                value.update(deepcopy(state))
            elif local_external_id != actual_external_id or local_ticket_id != ticket.ticket_id:
                return "hold"
            return "verified"
        if target_receipt is None:
            return "hold"
        target_key = target_receipt.idempotency_key
        if self._snapshot_is_ambiguous(snapshot, target_key):
            return "hold"
        return "verified" if target_key not in remote and target_key not in state["external_ids"] else "not_applied"


@dataclass
class _ManagedContext:
    binding: ManagedCalendarBinding
    adapter: ManagedEventKitAdapter
    ledger: SandboxEffectLedger
    gate: SandboxAuthorityGate
    gateway: SandboxEffectGateway


@dataclass(frozen=True)
class ManagedRetirementActionResult:
    calendar_receipt: CalendarActionReceipt
    provider_receipt: dict[str, Any]
    ticket: EffectTicket
    effect_receipt: EffectReceipt
    access_point: str
    binding: ManagedCalendarBinding

    @property
    def phase(self) -> str:
        return self.effect_receipt.phase

    @property
    def denied_reason(self) -> str | None:
        return self.effect_receipt.reasons[0] if self.effect_receipt.reasons else None

    def output_payload(self, candidate: CandidateCalendarAction | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "swift_receipt": self.calendar_receipt.to_dict(),
            "provider_receipt": dict(self.provider_receipt),
            "effect_ticket": self.ticket.to_dict(),
            "effect_receipt": self.effect_receipt.to_dict(),
            "stage_state": self.calendar_receipt.stage_state.value,
            "retirement": {
                "access_point": self.access_point,
                "retirement_profile": MANAGED_AUTHORITY_PROFILE,
                "owner": MANAGED_OWNER,
                "backend": MANAGED_BACKEND,
                "binding_id": self.binding.binding_id,
                "binding_epoch": self.binding.epoch,
                "phase": self.effect_receipt.phase,
                "effect_receipt_sha256": self.effect_receipt.content_sha256,
                "authorizes_production": False,
            },
        }
        if candidate is not None:
            payload["candidate"] = candidate.to_dict()
        if self.ticket.kind == "compensate":
            payload["provider_rollback"] = dict(self.provider_receipt)
            payload["rollback_verified"] = self.effect_receipt.phase == "verified"
        return payload


class ManagedEventKitRetirementProvider:
    provider_id = MANAGED_BACKEND
    real_provider = True
    real_oauth = False
    authorizes_production = False

    def __init__(
        self,
        *,
        incumbent: Any,
        driver: ManagedEventKitDriver,
        binding: ManagedCalendarBinding,
        state_root: str | Path,
        signing_key_path: str | Path,
        lease_path: str | Path,
        seed_observation: RawCalendarObservation,
        driver_factory: Callable[[ManagedCalendarBinding], ManagedEventKitDriver] | None = None,
        initialize: bool = False,
        acquire_lease: bool = True,
        reconcile_on_startup: bool = True,
    ) -> None:
        self.incumbent = incumbent
        self._initial_driver = driver
        self._initial_binding = binding
        self._driver_factory = driver_factory
        self.state_root = Path(state_root)
        self.signing_key_path = Path(signing_key_path)
        self.seed_observation = seed_observation
        self.direct_managed_commit_count = 0
        self.direct_managed_undo_count = 0
        self._lease = ManagedProcessLease(lease_path, binding_id=binding.binding_id) if acquire_lease else None
        if initialize:
            durable_paths = [
                self.state_root / "binding-registry.json",
                self.signing_key_path,
                *self.state_root.glob("epoch-*.json"),
            ]
            if any(path.exists() for path in durable_paths):
                self.close()
                raise ValueError("managed EventKit initialization requires empty durable state")
            self.state_root.mkdir(parents=True, exist_ok=True)
            self.signing_key_path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.signing_key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(secrets.token_bytes(32))
                handle.flush()
                os.fsync(handle.fileno())
        if not self.state_root.is_dir() or not self.signing_key_path.is_file():
            self.close()
            raise ValueError("managed EventKit durable ledger/signing state is missing")
        self.signing_key = self.signing_key_path.read_bytes()
        if len(self.signing_key) < 32:
            self.close()
            raise ValueError("managed EventKit signing state is corrupt")
        self.contexts: dict[int, _ManagedContext] = {}
        if initialize:
            self.current_epoch = binding.epoch
            self._add_context(binding)
            self._persist_registry()
        else:
            self._load_registry(binding)
        self.startup_reconciliation: list[EffectReceipt] = []
        if not initialize and reconcile_on_startup:
            try:
                self.startup_reconciliation = self.reconcile_pending()
            except Exception:
                self.close()
                raise

    @property
    def binding(self) -> ManagedCalendarBinding:
        return self.contexts[self.current_epoch].binding

    def close(self) -> None:
        lease = getattr(self, "_lease", None)
        if lease is not None:
            lease.close()
            self._lease = None

    def _context_path(self, binding: ManagedCalendarBinding) -> Path:
        return self.state_root / f"epoch-{binding.epoch}.json"

    def _add_context(self, binding: ManagedCalendarBinding) -> _ManagedContext:
        if self._driver_factory is not None:
            driver = self._driver_factory(binding)
        elif binding.fingerprint_fields == self._initial_binding.fingerprint_fields:
            driver = self._initial_driver
        else:
            raise ValueError("managed EventKit historical binding requires a per-binding driver factory")
        adapter = ManagedEventKitAdapter(driver=driver, binding=binding)
        context_path = self._context_path(binding)
        ledger = SandboxEffectLedger(context_path, authority_profile=MANAGED_LEDGER_AUTHORITY_PROFILE, adapter=adapter)
        if not context_path.exists():
            ledger.persist()
        gate = SandboxAuthorityGate(ledger, signing_key=self.signing_key)
        gateway = SandboxEffectGateway(ledger, signing_key=self.signing_key, adapter=adapter)
        context = _ManagedContext(binding, adapter, ledger, gate, gateway)
        self.contexts[binding.epoch] = context
        return context

    def _persist_registry(self) -> None:
        payload = {
            "binding_registry_schema_version": BINDING_REGISTRY_VERSION,
            "binding_id": self.binding.binding_id,
            "current_epoch": self.current_epoch,
            "bindings": [self.contexts[epoch].binding.to_dict() for epoch in sorted(self.contexts)],
        }
        atomic_write_json(self.state_root / "binding-registry.json", payload)

    def _load_registry(self, expected_current: ManagedCalendarBinding) -> None:
        path = self.state_root / "binding-registry.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("binding_registry_schema_version") != BINDING_REGISTRY_VERSION:
                raise ValueError("managed EventKit binding registry version is invalid")
            if payload.get("binding_id") != expected_current.binding_id:
                raise ValueError("managed EventKit binding registry lineage changed")
            bindings = [ManagedCalendarBinding.from_dict(row) for row in payload.get("bindings", [])]
            current_epoch = int(payload["current_epoch"])
            current = next(row for row in bindings if row.epoch == current_epoch)
            if current.to_dict() != expected_current.to_dict():
                raise ValueError("managed EventKit current binding does not match durable registry")
            for binding in bindings:
                if not self._context_path(binding).is_file():
                    raise ValueError("managed EventKit epoch ledger is missing")
            self.current_epoch = current_epoch
            for binding in bindings:
                self._add_context(binding)
        except (OSError, KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.close()
            raise ValueError("managed EventKit binding registry is missing or corrupt") from exc

    def health_status(self) -> dict[str, Any]:
        reason = self.contexts[self.current_epoch].adapter.identity_reason()
        return {
            "provider": self.provider_id,
            "configured": reason is None,
            "status": "configured" if reason is None else reason,
            "authority_profile": MANAGED_AUTHORITY_PROFILE,
            "authorizes_production": False,
            "binding_id": self.binding.binding_id,
            "binding_epoch": self.binding.epoch,
        }

    def read_observation(self, *args: Any, **kwargs: Any) -> RawCalendarObservation:
        return self.incumbent.read_observation(*args, **kwargs)

    def preview(self, candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        return self.incumbent.preview(candidate)

    def conflict_truth(self, candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        return self.incumbent.conflict_truth(candidate)

    def classify(self, candidate: CandidateCalendarAction) -> ManagedOwnershipDecision:
        return classify_managed_candidate(candidate, self.binding)

    def prepare_candidate(self, candidate: CandidateCalendarAction) -> CandidateCalendarAction:
        if candidate.intent != "create_prep_block":
            return candidate
        payload = candidate.to_dict()
        payload["target_calendars"] = [self.binding.calendar_id]
        for action in payload["actions"]:
            if action.get("action_type") not in {value.value for value in WRITE_ACTIONS}:
                continue
            action["calendar_id"] = self.binding.calendar_id
            metadata = action.setdefault("metadata", {})
            metadata["calendarpilot_binding_id"] = self.binding.binding_id
            metadata["calendarpilot_binding_epoch"] = str(self.binding.epoch)
        return CandidateCalendarAction.from_dict(payload)

    def owns_candidate(self, candidate: CandidateCalendarAction) -> bool:
        return self.classify(candidate).managed

    def commit_candidate(self, candidate: CandidateCalendarAction, *args: Any, **kwargs: Any) -> Any:
        decision = self.classify(candidate)
        if decision.managed:
            self.direct_managed_commit_count += 1
            raise RuntimeError("managed EventKit commit is disabled outside EffectKernel Gateway")
        return self.incumbent.commit_candidate(candidate, *args, **kwargs)

    def rollback(self, rollback_handle_id: str) -> Any:
        if self.owns_rollback_handle(rollback_handle_id):
            self.direct_managed_undo_count += 1
            raise RuntimeError("managed EventKit undo requires a CompensationTicket")
        return self.incumbent.rollback(rollback_handle_id)

    def _ensure_grant(self, context: _ManagedContext, authority: RuntimeAuthorityGrant) -> int:
        existing = context.ledger.snapshot()["grants"].get(authority.grant_id)
        if isinstance(existing, dict):
            return int(existing["epoch"])
        scopes = []
        if authority.allows_scope("commit_private"):
            scopes.append("apply")
        if authority.allows_scope("undo"):
            scopes.append("compensate")
        grant = context.gate.issue_grant(
            grant_id=authority.grant_id,
            action_families=("create_prep_block",),
            scopes=tuple(scopes),
            issued_at=authority.issued_at,
            expires_at=authority.expires_at,
            confirmed=authority.confirmed_by_user,
        )
        return grant.epoch

    def _receipt_by_hash(self, receipt_hash: str) -> tuple[_ManagedContext, EffectReceipt] | None:
        for context in self.contexts.values():
            for value in context.ledger.snapshot()["receipts"].values():
                receipt = EffectReceipt.from_dict(value)
                if receipt.content_sha256 == receipt_hash:
                    return context, receipt
        return None

    @staticmethod
    def _existing_apply_ticket(context: _ManagedContext, candidate_id: str) -> EffectTicket | None:
        for row in context.ledger.snapshot()["tickets"].values():
            ticket = EffectTicket.from_dict(row["ticket"])
            if ticket.kind == "apply" and ticket.candidate_id == candidate_id:
                return ticket
        return None

    def owns_rollback_handle(self, rollback_handle_id: str) -> bool:
        prefix = "eventkit-retirement:"
        return rollback_handle_id.startswith(prefix) and self._receipt_by_hash(rollback_handle_id.removeprefix(prefix)) is not None

    def commit_via_gateway(
        self,
        candidate: CandidateCalendarAction,
        observation: RawCalendarObservation,
        authority: RuntimeAuthorityGrant,
        *,
        replay: ReplayBuffer,
        trace_id: str,
        causal_parent_id: str | None,
        crash_at: str | None = None,
        now: datetime | None = None,
    ) -> ManagedRetirementActionResult:
        decision = self.classify(candidate)
        if decision.status != "managed":
            raise ValueError(decision.reason or "candidate is outside the managed EventKit binding")
        expected_confirmation = managed_commit_confirmation_provenance(candidate, self.binding)
        if not authority.confirmed_by_user or authority.confirmation_provenance != expected_confirmation:
            raise ValueError("managed EventKit commit requires exact candidate confirmation")
        now = now or datetime.now(timezone.utc)
        context = self.contexts[self.current_epoch]
        product = run_create_prep_block_vertical(
            observation,
            candidate,
            source_authenticated=True,
            received_at=observation.observed_at,
        )
        if product.preview.status != "preview":
            raise ValueError(f"managed EventKit ProductCore denied candidate: {product.preview.denial_reasons}")
        epoch = self._ensure_grant(context, authority)
        existing_ticket = self._existing_apply_ticket(context, candidate.candidate_id)
        if existing_ticket is not None:
            receipt = context.gateway.execute(existing_ticket, now=now, crash_at=crash_at)
            return self._action_result(
                context,
                existing_ticket,
                receipt,
                authority,
                replay=replay,
                trace_id=trace_id,
                causal_parent_id=causal_parent_id,
                candidate=candidate,
                access_point="CodexToolRuntime.REQUEST_COMMIT",
            )
        base_attempt = EffectAttempt.from_preview(
            product.preview,
            source_authenticated=True,
            observed_pre_state_hash=context.gateway.current_state_hash,
            authority_profile=MANAGED_LEDGER_AUTHORITY_PROFILE,
            target_binding=context.adapter.ticket_binding,
        )
        intent = deepcopy(base_attempt.intent)
        intent["canonical_target_vector"] = decision.target_vector
        attempt = replace(
            base_attempt,
            intent=intent,
            intent_hash=content_sha256(intent),
            attempt_id="attempt:" + content_sha256({
                "intent": intent,
                "pre_state": base_attempt.observed_pre_state_hash,
                "binding": context.adapter.ticket_binding,
            })[:24],
        )
        nonce = "nonce:" + hashlib.sha256(
            f"{authority.grant_id}|{candidate.candidate_id}|{self.binding.binding_id}|{self.binding.epoch}|{attempt.observed_pre_state_hash}".encode()
        ).hexdigest()[:24]
        admission = context.gate.admit_effect(
            attempt=attempt,
            grant_id=authority.grant_id,
            grant_epoch=epoch,
            nonce=nonce,
            now=now,
        )
        if admission.ticket is None:
            raise ValueError(f"managed EventKit admission blocked: {admission.reasons}")
        context.adapter._ledger_tickets = [
            EffectTicket.from_dict(row["ticket"]) for row in context.ledger.snapshot()["tickets"].values()
        ]
        receipt = context.gateway.execute(admission.ticket, now=now, crash_at=crash_at)
        return self._action_result(
            context,
            admission.ticket,
            receipt,
            authority,
            replay=replay,
            trace_id=trace_id,
            causal_parent_id=causal_parent_id,
            candidate=candidate,
            access_point="CodexToolRuntime.REQUEST_COMMIT",
        )

    def undo_via_gateway(
        self,
        rollback_handle_id: str,
        observation: RawCalendarObservation,
        authority: RuntimeAuthorityGrant,
        *,
        replay: ReplayBuffer,
        trace_id: str,
        causal_parent_id: str | None,
        now: datetime | None = None,
    ) -> ManagedRetirementActionResult:
        del observation
        found = self._receipt_by_hash(rollback_handle_id.removeprefix("eventkit-retirement:"))
        if found is None:
            raise ValueError("managed EventKit rollback handle is unknown")
        context, target = found
        if context.adapter.identity_reason():
            raise ValueError("managed EventKit historical binding drift requires manual reconciliation")
        expected_confirmation = f"user_confirmed_undo:{rollback_handle_id}"
        if not authority.confirmed_by_user or authority.confirmation_provenance != expected_confirmation:
            raise ValueError("managed EventKit undo requires exact receipt confirmation")
        now = now or datetime.now(timezone.utc)
        epoch = self._ensure_grant(context, authority)
        admission = context.gate.admit_compensation(
            receipt=target,
            grant_id=authority.grant_id,
            grant_epoch=epoch,
            fresh_state_hash=context.gateway.current_state_hash,
            nonce="nonce:" + hashlib.sha256(f"{authority.grant_id}|{target.content_sha256}".encode()).hexdigest()[:24],
            now=now,
        )
        if admission.ticket is None:
            raise ValueError(f"managed EventKit compensation blocked: {admission.reasons}")
        context.adapter._ledger_tickets = [
            EffectTicket.from_dict(row["ticket"]) for row in context.ledger.snapshot()["tickets"].values()
        ]
        receipt = context.gateway.execute(admission.ticket, now=now)
        return self._action_result(
            context,
            admission.ticket,
            receipt,
            authority,
            replay=replay,
            trace_id=trace_id,
            causal_parent_id=causal_parent_id,
            candidate=None,
            access_point="CodexToolRuntime.REQUEST_UNDO",
        )

    def _action_result(
        self,
        context: _ManagedContext,
        ticket: EffectTicket,
        receipt: EffectReceipt,
        authority: RuntimeAuthorityGrant,
        *,
        replay: ReplayBuffer,
        trace_id: str,
        causal_parent_id: str | None,
        candidate: CandidateCalendarAction | None,
        access_point: str,
    ) -> ManagedRetirementActionResult:
        verified = receipt.phase == "verified"
        rollback_handle = "eventkit-retirement:" + receipt.content_sha256 if ticket.kind == "apply" and verified else None
        external_id = None
        if ticket.kind == "apply" and verified:
            external_id = context.ledger.snapshot()["adapter_state"]["external_ids"].get(ticket.idempotency_key)
        calendar_receipt = CalendarActionReceipt(
            receipt_id=receipt.receipt_id,
            candidate_id=ticket.candidate_id,
            executed_at=datetime.fromisoformat(receipt.issued_at),
            executed_by="EffectKernel.Gateway",
            authority_tier_used=authority.max_authority_tier,
            sync_status="materialized" if ticket.kind == "apply" and verified else "reverted" if verified else receipt.phase,
            rollback_handle_id=rollback_handle,
            conflict_check_passed=receipt.phase not in {"hold", "denied"},
            generated_event_ids=[external_id] if external_id else [],
            provider_id=self.provider_id,
            actuation_mode=ActuationMode.MATERIALIZED_WRITE if verified else ActuationMode.DENIED,
            denied_reason=None if verified else (receipt.reasons[0] if receipt.reasons else receipt.phase),
            authority_grant_id=authority.grant_id,
            confirmation_provenance=authority.confirmation_provenance,
            stage_state=StageState.COMMITTED if ticket.kind == "apply" and verified else StageState.NO_OP,
            correlation_id=trace_id,
        )
        provider_receipt = {
            "provider_id": self.provider_id,
            "status": "materialized" if ticket.kind == "apply" and verified else "rollback_verified" if verified else receipt.phase,
            "idempotency_key": ticket.idempotency_key,
            "external_ids": [external_id] if external_id else [],
            "rollback_handle_id": rollback_handle,
            "rollback_verified": bool(ticket.kind == "compensate" and verified),
            "effect_receipt_sha256": receipt.content_sha256,
            "binding_id": context.binding.binding_id,
            "binding_epoch": context.binding.epoch,
            "authorizes_production": False,
        }
        replay.append_provider_transaction(
            operation="commit" if ticket.kind == "apply" else "rollback",
            transaction=provider_receipt,
            trace_id=trace_id,
            causal_parent_id=receipt.receipt_id,
        )
        replay.append_receipt(
            calendar_receipt,
            candidate,
            trace_id=trace_id,
            causal_parent_id=causal_parent_id,
            observation_id=self.seed_observation.observation_id,
            observation_fingerprint=observation_fingerprint(self.seed_observation),
            runtime_mode="codex_tool_runtime",
            policy_backend="effect_kernel_eventkit_retirement",
        )
        return ManagedRetirementActionResult(calendar_receipt, provider_receipt, ticket, receipt, access_point, context.binding)

    def rebind(self, *, identity: dict[str, Any], confirmed_at: datetime) -> ManagedCalendarBinding:
        for context in self.contexts.values():
            snapshot = context.ledger.snapshot()
            for ticket_id in snapshot["outbox"]:
                if context.gateway.phase(ticket_id) not in {"verified", "not_applied", "denied", "hold"}:
                    raise ValueError("managed EventKit rebind blocked by nonterminal work")
        binding = self.binding.rebind(identity=identity, confirmed_at=confirmed_at)
        self._add_context(binding)
        self.current_epoch = binding.epoch
        self._persist_registry()
        return binding

    def reconcile_pending(self, *, now: datetime | None = None) -> list[EffectReceipt]:
        now = now or datetime.now(timezone.utc)
        reconciled = []
        for context in self.contexts.values():
            state = context.ledger.snapshot()
            for ticket_id in sorted(state["outbox"]):
                if context.gateway.phase(ticket_id) in {"claimed", "applying_unknown"}:
                    reconciled.append(context.gateway.reconcile(ticket_id, now=now))
        return reconciled

    def retirement_snapshot(self) -> dict[str, Any]:
        ticket_count = claim_count = dispatch_count = mutation_count = compensation_count = 0
        active_count = 0
        audits = []
        for context in self.contexts.values():
            snapshot = context.gateway.snapshot()
            state = context.ledger.snapshot()
            ticket_count += snapshot["ticket_count"]
            claim_count += snapshot["claim_count"]
            dispatch_count += snapshot["dispatch_count"]
            mutation_count += snapshot["mutation_count"]
            compensation_count += int(state["adapter_state"]["compensation_mutation_count"])
            active_count += len(state["adapter_state"]["external_ids"])
            audits.extend(snapshot["audit"])
        return {
            "retirement_profile": MANAGED_AUTHORITY_PROFILE,
            "owner": MANAGED_OWNER,
            "backend": MANAGED_BACKEND,
            "binding_id": self.binding.binding_id,
            "binding_epoch": self.binding.epoch,
            "ticket_count": ticket_count,
            "claim_count": claim_count,
            "dispatch_count": dispatch_count,
            "mutation_count": mutation_count,
            "compensation_mutation_count": compensation_count,
            "active_event_count": active_count,
            "direct_commit_count": self.direct_managed_commit_count,
            "direct_undo_count": self.direct_managed_undo_count,
            "audit": audits,
        }
