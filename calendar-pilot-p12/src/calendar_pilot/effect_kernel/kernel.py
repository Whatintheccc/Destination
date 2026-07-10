from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
from typing import Any, Iterable

from calendar_pilot.product_core import AdmissionPreview


AUTHORITY_PROFILE = "owner_controlled_sandbox"
AUTHORIZES_PRODUCTION = False
ADAPTER_ID = "deterministic_sandbox"
EVENTKIT_AUTHORITY_PROFILE = "owner_controlled_eventkit_sandbox"
EVENTKIT_ADAPTER_ID = "apple_eventkit_sandbox"
LEDGER_VERSION = "sandbox_effect_ledger.v1"
ATTEMPT_VERSION = "effect_attempt.sandbox.v1"
TICKET_VERSION = "effect_ticket.sandbox.v1"
RECEIPT_VERSION = "effect_receipt.sandbox.v1"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("sandbox effect timestamps must be timezone-aware")
    return value.isoformat()


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("persisted sandbox effect timestamp is not timezone-aware")
    return parsed


@dataclass(frozen=True)
class AuthorityGrant:
    grant_id: str
    epoch: int
    action_families: tuple[str, ...]
    scopes: tuple[str, ...]
    issued_at: str
    expires_at: str
    confirmed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "epoch": self.epoch,
            "action_families": list(self.action_families),
            "scopes": list(self.scopes),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AuthorityGrant":
        return cls(
            grant_id=str(value["grant_id"]),
            epoch=int(value["epoch"]),
            action_families=tuple(str(row) for row in value["action_families"]),
            scopes=tuple(str(row) for row in value["scopes"]),
            issued_at=str(value["issued_at"]),
            expires_at=str(value["expires_at"]),
            confirmed=bool(value["confirmed"]),
        )


@dataclass(frozen=True)
class EffectAttempt:
    attempt_schema_version: str
    attempt_id: str
    candidate_id: str
    action_family: str
    intent: dict[str, Any]
    intent_hash: str
    evidence_row_ids: tuple[str, ...]
    source_authenticated: bool
    observed_pre_state_hash: str
    authority_profile: str = AUTHORITY_PROFILE
    authorizes_production: bool = AUTHORIZES_PRODUCTION
    target_binding: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.attempt_schema_version != ATTEMPT_VERSION:
            raise ValueError("unsupported sandbox EffectAttempt version")
        if self.authority_profile not in {AUTHORITY_PROFILE, EVENTKIT_AUTHORITY_PROFILE} or self.authorizes_production:
            raise ValueError("sandbox EffectAttempt cannot carry production authority")
        if self.authority_profile == AUTHORITY_PROFILE and self.target_binding is not None:
            raise ValueError("deterministic sandbox EffectAttempt cannot bind a provider")
        if self.authority_profile == EVENTKIT_AUTHORITY_PROFILE and not self.target_binding:
            raise ValueError("EventKit sandbox EffectAttempt requires an exact target binding")
        if self.action_family != "create_prep_block":
            raise ValueError("sandbox EffectAttempt accepts only create_prep_block")
        if self.intent_hash != content_sha256(self.intent):
            raise ValueError("sandbox EffectAttempt intent hash mismatch")

    @classmethod
    def from_preview(
        cls,
        preview: AdmissionPreview,
        *,
        source_authenticated: bool,
        observed_pre_state_hash: str,
        authority_profile: str = AUTHORITY_PROFILE,
        target_binding: dict[str, Any] | None = None,
    ) -> "EffectAttempt":
        if preview.status != "preview" or preview.projection is None or preview.denial_reasons:
            raise ValueError("only an admitted ProductCore preview can form an EffectAttempt")
        if preview.action_family != "create_prep_block":
            raise ValueError("sandbox EffectAttempt accepts only create_prep_block")
        projection = preview.projection
        intent = {
            "candidate_id": preview.candidate_id,
            "action_family": preview.action_family,
            "projection": {
                "title": projection.title,
                "start": projection.start,
                "end": projection.end,
                "calendar_id": projection.calendar_id,
                "explanation": projection.explanation,
            },
            "evidence_row_ids": list(preview.evidence_row_ids),
            "reducer_version": preview.reducer_version,
        }
        intent_hash = content_sha256(intent)
        attempt_id = "attempt:" + content_sha256({
            "intent_hash": intent_hash,
            "pre_state_hash": observed_pre_state_hash,
            "source_authenticated": bool(source_authenticated),
            "authority_profile": authority_profile,
            "target_binding": target_binding,
        })[:24]
        return cls(
            attempt_schema_version=ATTEMPT_VERSION,
            attempt_id=attempt_id,
            candidate_id=preview.candidate_id,
            action_family=preview.action_family,
            intent=intent,
            intent_hash=intent_hash,
            evidence_row_ids=preview.evidence_row_ids,
            source_authenticated=bool(source_authenticated),
            observed_pre_state_hash=observed_pre_state_hash,
            authority_profile=authority_profile,
            target_binding=deepcopy(target_binding),
        )


@dataclass(frozen=True)
class EffectTicket:
    ticket_schema_version: str
    ticket_id: str
    kind: str
    attempt_id: str
    candidate_id: str
    action_family: str
    intent: dict[str, Any]
    intent_hash: str
    pre_state_hash: str
    target_receipt_hash: str | None
    grant_id: str
    grant_epoch: int
    nonce: str
    idempotency_key: str
    issued_at: str
    expires_at: str
    authority_profile: str
    authorizes_production: bool
    target_binding: dict[str, Any] | None
    signature: str

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "ticket_schema_version": self.ticket_schema_version,
            "ticket_id": self.ticket_id,
            "kind": self.kind,
            "attempt_id": self.attempt_id,
            "candidate_id": self.candidate_id,
            "action_family": self.action_family,
            "intent": self.intent,
            "intent_hash": self.intent_hash,
            "pre_state_hash": self.pre_state_hash,
            "target_receipt_hash": self.target_receipt_hash,
            "grant_id": self.grant_id,
            "grant_epoch": self.grant_epoch,
            "nonce": self.nonce,
            "idempotency_key": self.idempotency_key,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "authority_profile": self.authority_profile,
            "authorizes_production": self.authorizes_production,
            "target_binding": self.target_binding,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_dict(), "signature": self.signature}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EffectTicket":
        restored = dict(value)
        restored.setdefault("target_binding", None)
        return cls(**restored)


@dataclass(frozen=True)
class AdmissionDecision:
    status: str
    reasons: tuple[str, ...]
    ticket: EffectTicket | None = None

    def __post_init__(self) -> None:
        if self.status not in {"ticket", "denied", "hold"}:
            raise ValueError("invalid sandbox admission status")
        if self.status == "ticket" and (self.ticket is None or self.reasons):
            raise ValueError("ticket admission requires one ticket and no reasons")
        if self.status != "ticket" and (self.ticket is not None or not self.reasons):
            raise ValueError("blocking admission requires reasons and no ticket")


@dataclass(frozen=True)
class RevokeReceipt:
    grant_id: str
    prior_epoch: int
    current_epoch: int
    cancelled_ticket_ids: tuple[str, ...]
    reconcile_ticket_ids: tuple[str, ...]
    revoked_at: str
    authority_profile: str = AUTHORITY_PROFILE
    authorizes_production: bool = AUTHORIZES_PRODUCTION


@dataclass(frozen=True)
class EffectReceipt:
    receipt_schema_version: str
    receipt_id: str
    ticket_id: str
    kind: str
    idempotency_key: str
    phase: str
    pre_state_hash: str
    post_state_hash: str | None
    reasons: tuple[str, ...]
    issued_at: str
    authority_profile: str = AUTHORITY_PROFILE
    authorizes_production: bool = AUTHORIZES_PRODUCTION
    target_binding: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_schema_version": self.receipt_schema_version,
            "receipt_id": self.receipt_id,
            "ticket_id": self.ticket_id,
            "kind": self.kind,
            "idempotency_key": self.idempotency_key,
            "phase": self.phase,
            "pre_state_hash": self.pre_state_hash,
            "post_state_hash": self.post_state_hash,
            "reasons": list(self.reasons),
            "issued_at": self.issued_at,
            "authority_profile": self.authority_profile,
            "authorizes_production": self.authorizes_production,
            "target_binding": self.target_binding,
        }

    @property
    def content_sha256(self) -> str:
        return content_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EffectReceipt":
        restored = dict(value)
        restored["reasons"] = tuple(restored.get("reasons", []))
        restored.setdefault("target_binding", None)
        return cls(**restored)


class InjectedCrash(RuntimeError):
    def __init__(self, stage: str):
        super().__init__(f"injected sandbox crash at {stage}")
        self.stage = stage


def derive_phase(facts: Iterable[str]) -> str:
    observed = set(facts)
    if "denied" in observed:
        return "denied"
    if "hold" in observed or {"verified", "not_applied"}.issubset(observed):
        return "hold"
    if "verified" in observed:
        return "verified"
    if "not_applied" in observed:
        return "not_applied"
    if "unknown" in observed or "dispatch" in observed:
        return "applying_unknown"
    if "claim" in observed:
        return "claimed"
    return "unclaimed"


class DeterministicSandboxAdapter:
    """Pure deterministic effect adapter with no credential or external-I/O surface."""

    adapter_id = ADAPTER_ID
    credential_fields: tuple[str, ...] = ()
    external_io = False
    real_provider_reachable = False
    supported_action_families = frozenset({"create_prep_block"})
    ticket_binding = None

    @staticmethod
    def validate_attempt(attempt: EffectAttempt) -> str | None:
        return None if attempt.target_binding is None else "target_binding_invalid"

    @staticmethod
    def initial_state() -> dict[str, Any]:
        return {
            "events": {},
            "idempotency": {},
            "out_of_band": {},
            "mutation_count": 0,
            "compensation_mutation_count": 0,
        }

    @classmethod
    def normalize(cls, value: dict[str, Any] | None) -> dict[str, Any]:
        state = deepcopy(value) if isinstance(value, dict) else cls.initial_state()
        required = set(cls.initial_state())
        if set(state) != required:
            raise ValueError("sandbox adapter state shape is invalid")
        return state

    @classmethod
    def state_hash(cls, value: dict[str, Any] | None) -> str:
        return content_sha256(cls.normalize(value))

    @classmethod
    def dispatch_apply(cls, value: dict[str, Any], ticket: EffectTicket) -> dict[str, Any]:
        state = cls.normalize(value)
        if ticket.idempotency_key in state["idempotency"]:
            return state
        if ticket.action_family not in cls.supported_action_families:
            raise ValueError("deterministic sandbox adapter rejects this action family")
        state["events"][ticket.idempotency_key] = deepcopy(ticket.intent["projection"])
        state["idempotency"][ticket.idempotency_key] = ticket.ticket_id
        state["mutation_count"] += 1
        return state

    @classmethod
    def dispatch_compensation(
        cls,
        value: dict[str, Any],
        ticket: EffectTicket,
        target_receipt: EffectReceipt,
    ) -> dict[str, Any]:
        state = cls.normalize(value)
        if ticket.idempotency_key in state["idempotency"]:
            return state
        state["events"].pop(target_receipt.idempotency_key, None)
        state["idempotency"][ticket.idempotency_key] = ticket.ticket_id
        state["compensation_mutation_count"] += 1
        return state

    @classmethod
    def outcome(cls, value: dict[str, Any], ticket: EffectTicket, target_receipt: EffectReceipt | None = None) -> str:
        state = cls.normalize(value)
        if ticket.kind == "apply":
            return "verified" if ticket.idempotency_key in state["events"] else "not_applied"
        if target_receipt is None:
            return "hold"
        return "verified" if target_receipt.idempotency_key not in state["events"] else "not_applied"


class EventKitSandboxAdapter:
    """One-calendar, one-probe EventKit port reachable only through the sandbox Gateway."""

    adapter_id = EVENTKIT_ADAPTER_ID
    credential_fields = ("eventkit_os_calendar_permission",)
    external_io = True
    real_provider_reachable = True
    supported_action_families = frozenset({"create_prep_block"})
    provider_only_through_gateway = True
    direct_commit_rejected = True
    forbidden_imports: list[str] = []

    def __init__(
        self,
        *,
        driver: Any,
        app_identity: dict[str, Any],
        bridge_identity: dict[str, Any],
        sandbox_calendar_id: str,
        effect_budget: int = 1,
    ):
        self.driver = driver
        self.app_identity = dict(app_identity)
        self.bridge_identity = dict(bridge_identity)
        self.sandbox_calendar_id = str(sandbox_calendar_id)
        self.effect_budget = int(effect_budget)
        app_path = str(self.app_identity.get("path", ""))
        bridge_path = str(self.bridge_identity.get("path", ""))
        self.app_bundle_bound = app_path.endswith("CalendarPilot.app") and _sha_identity(self.app_identity)
        self.bridge_bound = (
            self.app_bundle_bound
            and bridge_path.startswith(app_path + "/Contents/Resources/app/bin/")
            and "/CalendarPilotEventKitBridge.app/Contents/MacOS/CalendarPilotEventKitBridge" in bridge_path
            and _sha_identity(self.bridge_identity)
        )
        self.raw_cli_rejected = self.bridge_bound
        self.permission_status = str(getattr(driver, "permission_status", "unknown"))
        if getattr(driver, "provider_id", None) != "apple_eventkit":
            raise ValueError("EventKit sandbox requires the apple_eventkit provider")
        if not self.app_bundle_bound or not self.bridge_bound:
            raise ValueError("EventKit sandbox requires the canonical app-bundled bridge identity")
        if self.permission_status != "full_access":
            raise ValueError("EventKit sandbox requires full_access permission")
        if not self.sandbox_calendar_id or self.sandbox_calendar_id == "default":
            raise ValueError("EventKit sandbox requires an exact non-default calendar")
        if self.effect_budget != 1:
            raise ValueError("EventKit sandbox effect budget must be exactly one")
        self.ticket_binding = {
            "provider_id": "apple_eventkit",
            "app_path": app_path,
            "app_sha256": self.app_identity["sha256"],
            "bridge_path": bridge_path,
            "bridge_sha256": self.bridge_identity["sha256"],
            "sandbox_calendar_id": self.sandbox_calendar_id,
            "effect_budget": self.effect_budget,
        }

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
            raise ValueError("EventKit sandbox adapter state shape is invalid")
        return state

    def validate_attempt(self, attempt: EffectAttempt) -> str | None:
        projection = attempt.intent.get("projection", {})
        if attempt.target_binding != self.ticket_binding:
            return "target_binding_invalid"
        if projection.get("calendar_id") != self.sandbox_calendar_id:
            return "target_binding_invalid"
        if self.permission_status != "full_access":
            return "eventkit_permission_invalid"
        return None

    def state_hash(self, value: dict[str, Any] | None) -> str:
        return content_sha256({
            "local": self.normalize(value),
            "remote": self.driver.snapshot(self.sandbox_calendar_id),
            "target_binding": self.ticket_binding,
        })

    def dispatch_apply(self, value: dict[str, Any], ticket: EffectTicket) -> dict[str, Any]:
        state = self.normalize(value)
        if ticket.idempotency_key in state["idempotency"]:
            return state
        if ticket.target_binding != self.ticket_binding:
            raise ValueError("EventKit ticket target binding changed before dispatch")
        if ticket.intent.get("projection", {}).get("calendar_id") != self.sandbox_calendar_id:
            raise ValueError("EventKit ticket escaped the sandbox calendar")
        active = set(state["external_ids"])
        if len(active) >= self.effect_budget:
            raise ValueError("EventKit sandbox effect budget exceeded")
        external_id = self.driver.create(
            calendar_id=self.sandbox_calendar_id,
            idempotency_key=ticket.idempotency_key,
            projection=deepcopy(ticket.intent["projection"]),
        )
        state["idempotency"][ticket.idempotency_key] = ticket.ticket_id
        state["external_ids"][ticket.idempotency_key] = external_id
        state["mutation_count"] += 1
        return state

    def dispatch_compensation(
        self,
        value: dict[str, Any],
        ticket: EffectTicket,
        target_receipt: EffectReceipt,
    ) -> dict[str, Any]:
        state = self.normalize(value)
        if ticket.idempotency_key in state["idempotency"]:
            return state
        target_key = target_receipt.idempotency_key
        external_id = state["external_ids"].get(target_key)
        if external_id is None:
            return state
        removed = self.driver.remove(
            calendar_id=self.sandbox_calendar_id,
            idempotency_key=target_key,
            external_id=external_id,
        )
        if removed:
            state["external_ids"].pop(target_key, None)
            state["idempotency"][ticket.idempotency_key] = ticket.ticket_id
            state["compensation_mutation_count"] += 1
        return state

    def outcome(self, value: dict[str, Any], ticket: EffectTicket, target_receipt: EffectReceipt | None = None) -> str:
        state = self.normalize(value)
        remote = self.driver.snapshot(self.sandbox_calendar_id).get("events", {})
        if ticket.kind == "apply":
            return "verified" if ticket.idempotency_key in remote else "not_applied"
        if target_receipt is None:
            return "hold"
        target_key = target_receipt.idempotency_key
        return "verified" if target_key not in remote and target_key not in state["external_ids"] else "not_applied"


def _sha_identity(value: dict[str, Any]) -> bool:
    return isinstance(value.get("sha256"), str) and len(value["sha256"]) == 64 and all(
        character in "0123456789abcdef" for character in value["sha256"]
    )


class SandboxEffectLedger:
    """Single-process durable claim/outbox ledger for the non-authorizing sandbox."""

    def __init__(
        self,
        state_path: str | Path,
        *,
        authority_profile: str = AUTHORITY_PROFILE,
        adapter: DeterministicSandboxAdapter | EventKitSandboxAdapter | None = None,
    ):
        self.state_path = Path(state_path)
        self.lock = threading.RLock()
        self.authority_profile = authority_profile
        self.adapter = adapter or DeterministicSandboxAdapter()
        if authority_profile not in {AUTHORITY_PROFILE, EVENTKIT_AUTHORITY_PROFILE}:
            raise ValueError("unsupported sandbox ledger authority profile")
        if authority_profile == AUTHORITY_PROFILE and self.adapter.adapter_id != ADAPTER_ID:
            raise ValueError("deterministic sandbox ledger requires the deterministic adapter")
        if authority_profile == EVENTKIT_AUTHORITY_PROFILE and self.adapter.adapter_id != EVENTKIT_ADAPTER_ID:
            raise ValueError("EventKit sandbox ledger requires the EventKit adapter")
        self._state = self._load()

    def _initial_state(self) -> dict[str, Any]:
        return {
            "ledger_version": LEDGER_VERSION,
            "authority_profile": self.authority_profile,
            "authorizes_production": False,
            "grants": {},
            "nonces": [],
            "tickets": {},
            "outbox": {},
            "receipts": {},
            "adapter_state": self.adapter.initial_state(),
            "audit": [],
        }

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._initial_state()
        value = json.loads(self.state_path.read_text(encoding="utf-8"))
        if set(value) != set(self._initial_state()):
            raise ValueError("sandbox effect ledger shape is invalid")
        if value["ledger_version"] != LEDGER_VERSION:
            raise ValueError("sandbox effect ledger version is invalid")
        if value["authority_profile"] != self.authority_profile or value["authorizes_production"] is not False:
            raise ValueError("sandbox effect ledger cannot carry production authority")
        self.adapter.normalize(value["adapter_state"])
        return value

    def persist(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(self._state, indent=2, sort_keys=True, allow_nan=False) + "\n"
        temporary = self.state_path.parent / f".{self.state_path.name}.{secrets.token_hex(12)}"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            payload = encoded.encode("utf-8")
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("sandbox ledger write failed")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, self.state_path)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return deepcopy(self._state)


class SandboxAuthorityGate:
    """Recomputes sandbox admission and mints exact one-use development tickets."""

    def __init__(self, ledger: SandboxEffectLedger, *, signing_key: bytes):
        if not signing_key:
            raise ValueError("sandbox Gate signing key is required")
        self.ledger = ledger
        self._signing_key = bytes(signing_key)

    def issue_grant(
        self,
        *,
        grant_id: str,
        action_families: tuple[str, ...],
        scopes: tuple[str, ...],
        issued_at: datetime,
        expires_at: datetime,
        confirmed: bool,
    ) -> AuthorityGrant:
        if not grant_id or expires_at <= issued_at:
            raise ValueError("sandbox grant identity and expiry are required")
        if set(action_families) != {"create_prep_block"} or not set(scopes).issubset({"apply", "compensate"}):
            raise ValueError("sandbox grant scope is broader than P13.3")
        with self.ledger.lock:
            if grant_id in self.ledger._state["grants"]:
                raise ValueError("duplicate sandbox grant_id")
            grant = AuthorityGrant(
                grant_id=grant_id,
                epoch=1,
                action_families=tuple(sorted(action_families)),
                scopes=tuple(sorted(scopes)),
                issued_at=_iso(issued_at),
                expires_at=_iso(expires_at),
                confirmed=bool(confirmed),
            )
            self.ledger._state["grants"][grant_id] = {**grant.to_dict(), "revoked_at": None}
            self.ledger._state["audit"].append({"fact": "grant_issued", "grant_id": grant_id, "epoch": 1})
            self.ledger.persist()
            return grant

    def current_epoch(self, grant_id: str) -> int:
        with self.ledger.lock:
            return int(self.ledger._state["grants"][grant_id]["epoch"])

    def _signature(self, unsigned: dict[str, Any]) -> str:
        return hmac.new(self._signing_key, canonical_json_bytes(unsigned), hashlib.sha256).hexdigest()

    def verify_ticket(self, ticket: EffectTicket) -> bool:
        return (
            ticket.ticket_schema_version == TICKET_VERSION
            and ticket.authority_profile == self.ledger.authority_profile
            and ticket.authorizes_production is False
            and ticket.kind in {"apply", "compensate"}
            and ticket.action_family == "create_prep_block"
            and ticket.intent_hash == content_sha256(ticket.intent)
            and ticket.target_binding == self.ledger.adapter.ticket_binding
            and hmac.compare_digest(ticket.signature, self._signature(ticket.unsigned_dict()))
        )

    def _grant_reason(
        self,
        *,
        grant_id: str,
        grant_epoch: int,
        action_family: str,
        scope: str,
        now: datetime,
    ) -> str | None:
        value = self.ledger._state["grants"].get(grant_id)
        if not isinstance(value, dict):
            return "grant_missing"
        if grant_epoch != int(value["epoch"]):
            return "grant_epoch_invalid"
        if value.get("revoked_at") is not None:
            return "grant_revoked"
        if value.get("confirmed") is not True:
            return "grant_unconfirmed"
        if action_family not in value.get("action_families", []):
            return "action_family_out_of_scope"
        if scope not in value.get("scopes", []):
            return "grant_scope_missing"
        if now < _time(str(value["issued_at"])) or now > _time(str(value["expires_at"])):
            return "grant_expired"
        return None

    def _mint(
        self,
        *,
        kind: str,
        attempt_id: str,
        candidate_id: str,
        action_family: str,
        intent: dict[str, Any],
        pre_state_hash: str,
        target_receipt_hash: str | None,
        grant_id: str,
        grant_epoch: int,
        nonce: str,
        now: datetime,
    ) -> AdmissionDecision:
        if not nonce:
            return AdmissionDecision("denied", ("nonce_missing",))
        if nonce in self.ledger._state["nonces"]:
            return AdmissionDecision("denied", ("nonce_reused",))
        grant = self.ledger._state["grants"][grant_id]
        intent_hash = content_sha256(intent)
        idempotency_key = "idem:" + content_sha256({
            "kind": kind,
            "candidate_id": candidate_id,
            "intent_hash": intent_hash,
            "pre_state_hash": pre_state_hash,
            "target_receipt_hash": target_receipt_hash,
            "grant_id": grant_id,
            "grant_epoch": grant_epoch,
        })[:32]
        ticket_id = "ticket:" + content_sha256({"idempotency_key": idempotency_key, "nonce": nonce})[:24]
        unsigned = {
            "ticket_schema_version": TICKET_VERSION,
            "ticket_id": ticket_id,
            "kind": kind,
            "attempt_id": attempt_id,
            "candidate_id": candidate_id,
            "action_family": action_family,
            "intent": deepcopy(intent),
            "intent_hash": intent_hash,
            "pre_state_hash": pre_state_hash,
            "target_receipt_hash": target_receipt_hash,
            "grant_id": grant_id,
            "grant_epoch": grant_epoch,
            "nonce": nonce,
            "idempotency_key": idempotency_key,
            "issued_at": _iso(now),
            "expires_at": str(grant["expires_at"]),
            "authority_profile": self.ledger.authority_profile,
            "authorizes_production": False,
            "target_binding": deepcopy(self.ledger.adapter.ticket_binding),
        }
        ticket = EffectTicket(**unsigned, signature=self._signature(unsigned))
        self.ledger._state["nonces"].append(nonce)
        self.ledger._state["tickets"][ticket_id] = {"ticket": ticket.to_dict(), "status": "issued"}
        self.ledger._state["audit"].append({"fact": "ticket_issued", "ticket_id": ticket_id, "kind": kind})
        self.ledger.persist()
        return AdmissionDecision("ticket", (), ticket)

    def admit_effect(
        self,
        *,
        attempt: EffectAttempt,
        grant_id: str,
        grant_epoch: int,
        nonce: str,
        now: datetime,
    ) -> AdmissionDecision:
        with self.ledger.lock:
            if attempt.authority_profile != self.ledger.authority_profile or attempt.authorizes_production:
                return AdmissionDecision("denied", ("authority_profile_invalid",))
            if not attempt.source_authenticated:
                return AdmissionDecision("denied", ("source_unauthenticated",))
            target_reason = self.ledger.adapter.validate_attempt(attempt)
            if target_reason:
                return AdmissionDecision("denied", (target_reason,))
            current_hash = self.ledger.adapter.state_hash(self.ledger._state["adapter_state"])
            if attempt.observed_pre_state_hash != current_hash:
                return AdmissionDecision("denied", ("pre_state_mismatch",))
            reason = self._grant_reason(
                grant_id=grant_id,
                grant_epoch=grant_epoch,
                action_family=attempt.action_family,
                scope="apply",
                now=now,
            )
            if reason:
                return AdmissionDecision("denied", (reason,))
            return self._mint(
                kind="apply",
                attempt_id=attempt.attempt_id,
                candidate_id=attempt.candidate_id,
                action_family=attempt.action_family,
                intent=attempt.intent,
                pre_state_hash=current_hash,
                target_receipt_hash=None,
                grant_id=grant_id,
                grant_epoch=grant_epoch,
                nonce=nonce,
                now=now,
            )

    def admit_compensation(
        self,
        *,
        receipt: EffectReceipt,
        grant_id: str,
        grant_epoch: int,
        fresh_state_hash: str,
        nonce: str,
        now: datetime,
    ) -> AdmissionDecision:
        with self.ledger.lock:
            if (
                receipt.phase != "verified"
                or receipt.authorizes_production
                or receipt.authority_profile != self.ledger.authority_profile
                or receipt.target_binding != self.ledger.adapter.ticket_binding
            ):
                return AdmissionDecision("denied", ("target_receipt_not_verified",))
            current_hash = self.ledger.adapter.state_hash(self.ledger._state["adapter_state"])
            if fresh_state_hash != current_hash or receipt.post_state_hash != current_hash:
                return AdmissionDecision("hold", ("compensation_prestate_conflict",))
            reason = self._grant_reason(
                grant_id=grant_id,
                grant_epoch=grant_epoch,
                action_family="create_prep_block",
                scope="compensate",
                now=now,
            )
            if reason:
                return AdmissionDecision("denied", (reason,))
            intent = {"action_family": "create_prep_block", "target_receipt_hash": receipt.content_sha256}
            return self._mint(
                kind="compensate",
                attempt_id=f"compensate:{receipt.receipt_id}",
                candidate_id=f"compensate:{receipt.ticket_id}",
                action_family="create_prep_block",
                intent=intent,
                pre_state_hash=current_hash,
                target_receipt_hash=receipt.content_sha256,
                grant_id=grant_id,
                grant_epoch=grant_epoch,
                nonce=nonce,
                now=now,
            )

    def revoke(self, grant_id: str, *, now: datetime) -> RevokeReceipt:
        with self.ledger.lock:
            value = self.ledger._state["grants"].get(grant_id)
            if not isinstance(value, dict):
                raise ValueError("sandbox grant does not exist")
            prior = int(value["epoch"])
            value["epoch"] = prior + 1
            value["revoked_at"] = _iso(now)
            cancelled: list[str] = []
            reconcile: list[str] = []
            for ticket_id, row in self.ledger._state["tickets"].items():
                if row["ticket"]["grant_id"] != grant_id:
                    continue
                outbox = self.ledger._state["outbox"].get(ticket_id)
                if outbox is None:
                    row["status"] = "cancelled"
                    cancelled.append(ticket_id)
                else:
                    if "revoked_after_claim" not in outbox["facts"]:
                        outbox["facts"].append("revoked_after_claim")
                    reconcile.append(ticket_id)
            self.ledger._state["audit"].append({
                "fact": "grant_revoked",
                "grant_id": grant_id,
                "prior_epoch": prior,
                "current_epoch": prior + 1,
                "cancelled_ticket_ids": sorted(cancelled),
                "reconcile_ticket_ids": sorted(reconcile),
            })
            self.ledger.persist()
            return RevokeReceipt(
                grant_id=grant_id,
                prior_epoch=prior,
                current_epoch=prior + 1,
                cancelled_ticket_ids=tuple(sorted(cancelled)),
                reconcile_ticket_ids=tuple(sorted(reconcile)),
                revoked_at=_iso(now),
                authority_profile=self.ledger.authority_profile,
            )


class SandboxEffectGateway:
    """Sole sandbox claim, outbox, dispatch, verify, and reconcile path."""

    def __init__(
        self,
        ledger: SandboxEffectLedger,
        *,
        signing_key: bytes,
        adapter: DeterministicSandboxAdapter | EventKitSandboxAdapter,
    ):
        self.ledger = ledger
        self.gate = SandboxAuthorityGate(ledger, signing_key=signing_key)
        self.adapter = adapter
        with self.ledger.lock:
            self.ledger._state["adapter_state"] = adapter.normalize(self.ledger._state["adapter_state"])

    @property
    def current_state_hash(self) -> str:
        with self.ledger.lock:
            return self.adapter.state_hash(self.ledger._state["adapter_state"])

    def _receipt(self, ticket: EffectTicket, *, phase: str, reasons: tuple[str, ...], now: datetime) -> EffectReceipt:
        post_state_hash = self.adapter.state_hash(self.ledger._state["adapter_state"]) if phase == "verified" else None
        seed = {
            "ticket_id": ticket.ticket_id,
            "phase": phase,
            "post_state_hash": post_state_hash,
            "reasons": list(reasons),
        }
        return EffectReceipt(
            receipt_schema_version=RECEIPT_VERSION,
            receipt_id="receipt:" + content_sha256(seed)[:24],
            ticket_id=ticket.ticket_id,
            kind=ticket.kind,
            idempotency_key=ticket.idempotency_key,
            phase=phase,
            pre_state_hash=ticket.pre_state_hash,
            post_state_hash=post_state_hash,
            reasons=reasons,
            issued_at=_iso(now),
            authority_profile=self.ledger.authority_profile,
            target_binding=deepcopy(self.adapter.ticket_binding),
        )

    def _store_receipt(self, receipt: EffectReceipt) -> None:
        self.ledger._state["receipts"][receipt.ticket_id] = receipt.to_dict()
        self.ledger._state["audit"].append({
            "fact": "effect_receipt",
            "ticket_id": receipt.ticket_id,
            "phase": receipt.phase,
            "receipt_sha256": receipt.content_sha256,
        })

    def _existing_receipt(self, ticket_id: str) -> EffectReceipt | None:
        value = self.ledger._state["receipts"].get(ticket_id)
        return EffectReceipt.from_dict(value) if isinstance(value, dict) else None

    def _target_receipt(self, ticket: EffectTicket) -> EffectReceipt | None:
        if ticket.target_receipt_hash is None:
            return None
        for value in self.ledger._state["receipts"].values():
            receipt = EffectReceipt.from_dict(value)
            if receipt.content_sha256 == ticket.target_receipt_hash:
                return receipt
        return None

    def execute(
        self,
        ticket: EffectTicket,
        *,
        now: datetime,
        crash_at: str | None = None,
        verification_mode: str = "verified",
    ) -> EffectReceipt:
        allowed_crashes = {None, "before_claim", "after_claim_before_dispatch", "after_dispatch_before_receipt"}
        if crash_at not in allowed_crashes:
            raise ValueError("unknown sandbox crash injection point")
        if verification_mode not in {"verified", "unknown"}:
            raise ValueError("unknown sandbox verification mode")
        with self.ledger.lock:
            existing = self._existing_receipt(ticket.ticket_id)
            if existing is not None:
                return existing
            stored = self.ledger._state["tickets"].get(ticket.ticket_id)
            if not self.gate.verify_ticket(ticket) or not isinstance(stored, dict) or stored.get("ticket") != ticket.to_dict():
                return self._deny(ticket, "ticket_invalid", now)
            if stored.get("status") == "cancelled":
                return self._deny(ticket, "grant_revoked_before_claim", now)
            grant = self.ledger._state["grants"].get(ticket.grant_id, {})
            if int(grant.get("epoch", -1)) != ticket.grant_epoch or grant.get("revoked_at") is not None:
                return self._deny(ticket, "grant_epoch_invalid", now)
            if now > _time(ticket.expires_at):
                return self._deny(ticket, "ticket_expired", now)
            if self.adapter.state_hash(self.ledger._state["adapter_state"]) != ticket.pre_state_hash:
                phase = "hold" if ticket.kind == "compensate" else "denied"
                receipt = self._receipt(ticket, phase=phase, reasons=("pre_state_mismatch",), now=now)
                self._store_receipt(receipt)
                self.ledger.persist()
                return receipt
            if crash_at == "before_claim":
                raise InjectedCrash("before_claim")

            if ticket.ticket_id in self.ledger._state["outbox"]:
                phase = derive_phase(self.ledger._state["outbox"][ticket.ticket_id]["facts"])
                return self._receipt(ticket, phase=phase, reasons=("reconcile_required",), now=now)

            self.ledger._state["outbox"][ticket.ticket_id] = {
                "ticket_id": ticket.ticket_id,
                "kind": ticket.kind,
                "idempotency_key": ticket.idempotency_key,
                "facts": ["claim"],
            }
            stored["status"] = "claimed"
            self.ledger._state["audit"].append({"fact": "ticket_claimed", "ticket_id": ticket.ticket_id})
            self.ledger.persist()
            if crash_at == "after_claim_before_dispatch":
                raise InjectedCrash("after_claim_before_dispatch")

            outbox = self.ledger._state["outbox"][ticket.ticket_id]
            target = self._target_receipt(ticket)
            if ticket.kind == "apply":
                next_state = self.adapter.dispatch_apply(self.ledger._state["adapter_state"], ticket)
            elif target is not None:
                next_state = self.adapter.dispatch_compensation(self.ledger._state["adapter_state"], ticket, target)
            else:
                outbox["facts"].append("hold")
                receipt = self._receipt(ticket, phase="hold", reasons=("target_receipt_missing",), now=now)
                self._store_receipt(receipt)
                self.ledger.persist()
                return receipt
            self.ledger._state["adapter_state"] = next_state
            outbox["facts"].extend(["dispatch", "unknown"])
            stored["status"] = "applying_unknown"
            self.ledger._state["audit"].append({"fact": "effect_dispatched", "ticket_id": ticket.ticket_id})
            self.ledger.persist()
            if crash_at == "after_dispatch_before_receipt":
                raise InjectedCrash("after_dispatch_before_receipt")

            if verification_mode == "verified":
                outcome = self.adapter.outcome(self.ledger._state["adapter_state"], ticket, target)
                outbox["facts"].append(outcome)
            phase = derive_phase(outbox["facts"])
            stored["status"] = phase
            receipt = self._receipt(ticket, phase=phase, reasons=() if phase == "verified" else ("reconcile_required",), now=now)
            self._store_receipt(receipt)
            self.ledger.persist()
            return receipt

    def _deny(self, ticket: EffectTicket, reason: str, now: datetime) -> EffectReceipt:
        receipt = self._receipt(ticket, phase="denied", reasons=(reason,), now=now)
        self._store_receipt(receipt)
        self.ledger.persist()
        return receipt

    def reconcile(self, ticket_id: str, *, now: datetime) -> EffectReceipt:
        with self.ledger.lock:
            row = self.ledger._state["tickets"].get(ticket_id)
            outbox = self.ledger._state["outbox"].get(ticket_id)
            if not isinstance(row, dict) or not isinstance(outbox, dict):
                raise ValueError("only a claimed sandbox ticket can be reconciled")
            ticket = EffectTicket.from_dict(row["ticket"])
            target = self._target_receipt(ticket)
            outcome = self.adapter.outcome(self.ledger._state["adapter_state"], ticket, target)
            if outcome not in outbox["facts"]:
                outbox["facts"].append(outcome)
            phase = derive_phase(outbox["facts"])
            row["status"] = phase
            receipt = self._receipt(ticket, phase=phase, reasons=() if phase in {"verified", "not_applied"} else ("manual_resolution_required",), now=now)
            self._store_receipt(receipt)
            self.ledger.persist()
            return receipt

    def phase(self, ticket_id: str) -> str:
        with self.ledger.lock:
            receipt = self._existing_receipt(ticket_id)
            if receipt is not None:
                return receipt.phase
            outbox = self.ledger._state["outbox"].get(ticket_id)
            if isinstance(outbox, dict):
                return derive_phase(outbox["facts"])
            return "unclaimed"

    def inject_out_of_band_edit(self, edit_id: str, value: Any) -> None:
        if not edit_id:
            raise ValueError("out-of-band edit id is required")
        with self.ledger.lock:
            self.ledger._state["adapter_state"]["out_of_band"][edit_id] = deepcopy(value)
            self.ledger._state["audit"].append({"fact": "sandbox_out_of_band_edit", "edit_id": edit_id})
            self.ledger.persist()

    def snapshot(self) -> dict[str, Any]:
        with self.ledger.lock:
            state = self.ledger.snapshot()
            return {
                "authority_profile": state["authority_profile"],
                "authorizes_production": state["authorizes_production"],
                "ticket_count": len(state["tickets"]),
                "claim_count": len(state["outbox"]),
                "claim_fact_count": sum(row["facts"].count("claim") for row in state["outbox"].values()),
                "dispatch_count": sum(row["facts"].count("dispatch") for row in state["outbox"].values()),
                "compensation_dispatch_count": sum(
                    row["facts"].count("dispatch") for row in state["outbox"].values() if row["kind"] == "compensate"
                ),
                "mutation_count": int(state["adapter_state"]["mutation_count"]),
                "adapter_state": state["adapter_state"],
                "audit": state["audit"],
            }


class EffectKernelSelector:
    """One explicit selector; every unspecified or incumbent invocation remains incumbent."""

    production_available = False

    @staticmethod
    def select(authority_profile: str | None = None) -> str:
        if authority_profile in {None, "incumbent"}:
            return "incumbent"
        if authority_profile == AUTHORITY_PROFILE:
            return ADAPTER_ID
        if authority_profile == EVENTKIT_AUTHORITY_PROFILE:
            return EVENTKIT_ADAPTER_ID
        raise ValueError("unsupported effect owner selection")
