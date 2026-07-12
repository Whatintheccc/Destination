

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any, Protocol

from calendar_pilot.providers.base import CalendarProviderError, ProviderVerificationResult
from calendar_pilot.providers.deterministic import ProviderMutationResult, WRITE_ACTIONS
from calendar_pilot.environment.fsio import atomic_write_json
from calendar_pilot.environment.plan_graph import actions_from_plan_metadata, rollback_order_from_metadata
from calendar_pilot.types import (
    AtomicActionType,
    AtomicCalendarAction,
    CalendarActionReceipt,
    CandidateCalendarAction,
    RawCalendarEvent,
    RawCalendarObservation,
)


PROVIDER_ID = "apple_eventkit"


class EventKitBridge(Protocol):
    def call(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass
class SwiftEventKitBridge:
    executable: str = field(default_factory=lambda: os.environ.get("CALENDAR_PILOT_EVENTKIT_BRIDGE", ""))
    timeout_seconds: float = 30.0

    def call(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        executable = self.executable or _default_bridge_path()
        executable_path = _canonical_bridge_executable(Path(executable)) if executable else Path()
        if not executable or not executable_path.exists():
            raise CalendarProviderError("Apple Calendar EventKit bridge is not built or CALENDAR_PILOT_EVENTKIT_BRIDGE is not set")
        sandbox_calendar_id = os.environ.get("CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID") or os.environ.get("CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID")
        if sandbox_calendar_id:
            payload = dict(payload)
            payload.setdefault("sandbox_calendar_id", sandbox_calendar_id)
            payload.setdefault("self_play_sandbox", True)
        request = {"command": command, "payload": payload}
        app_result = self._call_app_bridge(executable_path, request)
        if app_result is not None:
            return app_result
        try:
            proc = subprocess.run(
                [str(executable_path)],
                input=json.dumps(request),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise CalendarProviderError(f"EventKit bridge failed: {exc}") from exc
        if proc.returncode != 0:
            raise CalendarProviderError(proc.stderr.strip() or f"EventKit bridge exited {proc.returncode}")
        return self._parse_response(proc.stdout)

    def _call_app_bridge(self, executable: Path, request: dict[str, Any]) -> dict[str, Any] | None:
        app_bundle = _app_bundle_for_executable(executable)
        if app_bundle is None:
            return None
        with tempfile.NamedTemporaryFile(prefix="calendarpilot-eventkit-request-", suffix=".json", delete=False, mode="w", encoding="utf-8") as request_file:
            json.dump(request, request_file)
            request_path = Path(request_file.name)
        with tempfile.NamedTemporaryFile(prefix="calendarpilot-eventkit-", suffix=".json", delete=False) as result_file:
            result_path = Path(result_file.name)
        try:
            try:
                proc = subprocess.run(
                    ["open", "-W", "-n", str(app_bundle), "--args", "--request-file", str(request_path), "--result-file", str(result_path)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                _terminate_app_bundle(app_bundle)
                raise CalendarProviderError(f"EventKit bridge app timed out: {exc}") from exc
            except (OSError, subprocess.SubprocessError) as exc:
                _terminate_app_bundle(app_bundle)
                raise CalendarProviderError(f"EventKit bridge app failed: {exc}") from exc
            output = self._wait_for_result_file(
                result_path,
                timeout_seconds=self.timeout_seconds if request.get("command") == "request_access" else min(5.0, self.timeout_seconds),
            )
            if output:
                return self._parse_response(output)
            if proc.returncode != 0:
                raise CalendarProviderError(proc.stderr.strip() or f"EventKit bridge app exited {proc.returncode}")
            return self._parse_response("")
        finally:
            try:
                request_path.unlink()
            except OSError:
                pass
            try:
                result_path.unlink()
            except OSError:
                pass

    def _parse_response(self, output: str) -> dict[str, Any]:
        try:
            response = json.loads(output or "{}")
        except json.JSONDecodeError as exc:
            raise CalendarProviderError(f"EventKit bridge returned non-JSON output: {exc}") from exc
        if not response.get("ok", False):
            raise CalendarProviderError(str(response.get("error", "EventKit bridge failed")))
        return dict(response.get("result", {}))

    @staticmethod
    def _wait_for_result_file(path: Path, *, timeout_seconds: float) -> str:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            try:
                if path.exists() and path.stat().st_size > 0:
                    return path.read_text(encoding="utf-8")
            except OSError:
                pass
            time.sleep(0.05)
        return ""


class AppleEventKitProvider:
    provider_id = PROVIDER_ID
    real_provider = True
    real_oauth = False
    observation_id = "obs_apple_eventkit"

    def __init__(self, *, state_path: str | Path | None = None, bridge: EventKitBridge | None = None, bridge_path: str | Path | None = None) -> None:
        self.state_path = Path(state_path) if state_path is not None else _default_state_path()
        if bridge is not None:
            self.bridge = bridge
        elif bridge_path is not None:
            self.bridge = SwiftEventKitBridge(executable=str(bridge_path))
        else:
            self.bridge = SwiftEventKitBridge()
        self.state = self._load_state()
        self.last_read_window: dict[str, str] | None = None

    def health_status(self, *, request_access: bool = False) -> dict[str, Any]:
        command = "request_access" if request_access else "status"
        try:
            result = self.bridge.call(command, {})
            status = str(result.get("authorization_status", "unknown"))
            configured = bool(result.get("authorized", False))
            return {
                "provider": self.provider_id,
                "status": "configured" if configured else status,
                "configured": configured,
                "real_provider": True,
                "real_oauth": False,
                "auth_method": "eventkit_os_calendar_permission",
                "authorization_status": status,
                "bridge": result.get("bridge", "CalendarPilotEventKitBridge"),
            }
        except (CalendarProviderError, OSError, subprocess.SubprocessError) as exc:
            return {
                "provider": self.provider_id,
                "status": "bridge_unavailable",
                "configured": False,
                "real_provider": True,
                "real_oauth": False,
                "auth_method": "eventkit_os_calendar_permission",
                "reason": str(exc),
            }

    def request_access(self) -> dict[str, Any]:
        return self.health_status(request_access=True)

    def read_observation(self, user_scope_id: str, *, observed_at: datetime | None = None, time_zone_id: str = "UTC") -> RawCalendarObservation:
        now = observed_at or datetime.now(timezone.utc)
        time_min = _read_window_bound("CALENDAR_PILOT_EVENTKIT_READ_TIME_MIN") or (now - timedelta(days=1))
        time_max = _read_window_bound("CALENDAR_PILOT_EVENTKIT_READ_TIME_MAX") or (now + timedelta(days=14))
        if time_max <= time_min:
            raise CalendarProviderError("EventKit read window must have time_max after time_min")
        self.last_read_window = {"time_min": time_min.isoformat(), "time_max": time_max.isoformat()}
        result = self.bridge.call("read_events", {
            **self.last_read_window,
        })
        return RawCalendarObservation(
            observation_id=self.observation_id,
            user_scope_id=user_scope_id,
            observed_at=now,
            time_zone_id=time_zone_id,
            events=[RawCalendarEvent.from_dict(row) for row in result.get("events", [])],
        )

    def conflict_truth(self, candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        if self.idempotency_key(candidate) in self.state.get("idempotency", {}):
            return []
        if not self.health_status().get("configured"):
            raise CalendarProviderError("Apple Calendar permission is not configured")
        observation = self.read_observation("apple_eventkit_user")
        conflicts: list[dict[str, Any]] = []
        for action in _expanded_actions(candidate):
            if action.action_type not in WRITE_ACTIONS or action.start is None or action.end is None:
                continue
            for event in observation.events:
                if action.event_id and event.event_id == action.event_id:
                    continue
                if action.start < event.end and action.end > event.start:
                    conflicts.append({
                        "provider": self.provider_id,
                        "event_id": event.event_id,
                        "start": event.start.isoformat(),
                        "end": event.end.isoformat(),
                        "action_type": action.action_type.value,
                    })
        return conflicts


    def preview(self, candidate: CandidateCalendarAction) -> list[dict[str, Any]]:
        return self.conflict_truth(candidate)

    def commit(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, observation: RawCalendarObservation) -> ProviderMutationResult:
        return self.commit_candidate(candidate, receipt, observation)

    def verify(self, transaction: Any, *, observation: RawCalendarObservation | None = None) -> ProviderVerificationResult:
        payload = transaction.to_dict() if hasattr(transaction, "to_dict") else dict(transaction or {})
        external_ids = [str(x) for x in payload.get("external_ids", [])]
        found: set[str] = set()
        local_time_echo_ok = None
        try:
            obs = self.read_observation("apple_eventkit_user")
            observed_ids = {event.event_id for event in obs.events}
            found = {external_id for external_id in external_ids if external_id in observed_ids}
            local_time_echo_ok = all(external_id in observed_ids for external_id in payload.get("created_external_ids", []) + payload.get("moved_external_ids", []))
        except Exception:
            # Keep verification as replay-visible instead of failing the acting path.
            found = set()
            local_time_echo_ok = False
        missing = [external_id for external_id in external_ids if external_id not in found and external_id not in payload.get("deleted_external_ids", [])]
        rollback_handle = payload.get("rollback_handle_id")
        record = self.state.get("rollback_records", {}).get(rollback_handle or "", {})
        return ProviderVerificationResult(
            provider_id=self.provider_id,
            status="verified" if not missing and local_time_echo_ok is not False else "unverified",
            verified_external_ids=sorted(found),
            missing_external_ids=missing,
            rollback_handle_id=rollback_handle,
            rollback_verified=bool(record.get("rollback_verified", False)) if rollback_handle else None,
            local_time_echo_ok=local_time_echo_ok,
        )

    def commit_candidate(self, candidate: CandidateCalendarAction, receipt: CalendarActionReceipt, observation: RawCalendarObservation) -> ProviderMutationResult:
        self._require_configured()
        idempotency_key = self.idempotency_key(candidate)
        existing = self.state.setdefault("idempotency", {}).get(idempotency_key)
        if existing and not existing.get("rollback_verified"):
            return ProviderMutationResult(
                provider_id=self.provider_id,
                status="idempotent_replay",
                idempotency_key=idempotency_key,
                external_ids=list(existing.get("external_ids", [])),
                created_external_ids=list(existing.get("created_external_ids", [])),
                moved_external_ids=list(existing.get("moved_external_ids", [])),
                deleted_external_ids=list(existing.get("deleted_external_ids", [])),
                rollback_handle_id=existing.get("rollback_handle_id"),
            )
        conflicts = self.conflict_truth(candidate)
        if conflicts:
            return ProviderMutationResult(provider_id=self.provider_id, status="conflict_denied", idempotency_key=idempotency_key, conflict_truth=conflicts)
        result = self.bridge.call("commit", {
            "idempotency_key": idempotency_key,
            "candidate_id": candidate.candidate_id,
            "rollback_handle_id": receipt.rollback_handle_id,
            "actions": [_jsonable_action(action) for action in _expanded_actions(candidate)],
        })
        status = "idempotent_replay" if result.get("idempotent_replay") else "materialized"
        record = {
            "idempotency_key": idempotency_key,
            "candidate_id": candidate.candidate_id,
            "rollback_handle_id": receipt.rollback_handle_id,
            "external_ids": list(result.get("external_ids", [])),
            "created_external_ids": list(result.get("created_external_ids", [])),
            "moved_external_ids": list(result.get("moved_external_ids", [])),
            "deleted_external_ids": list(result.get("deleted_external_ids", [])),
            "before_events": result.get("before_events", {}),
            "status": status,
        }
        self.state.setdefault("idempotency", {})[idempotency_key] = record
        if receipt.rollback_handle_id:
            self.state.setdefault("rollback_records", {})[receipt.rollback_handle_id] = record
        self._save_state()
        return ProviderMutationResult(
            provider_id=self.provider_id,
            status=status,
            idempotency_key=idempotency_key,
            external_ids=list(result.get("external_ids", [])),
            created_external_ids=list(result.get("created_external_ids", [])),
            moved_external_ids=list(result.get("moved_external_ids", [])),
            deleted_external_ids=list(result.get("deleted_external_ids", [])),
            rollback_handle_id=receipt.rollback_handle_id,
        )

    def rollback(self, rollback_handle_id: str) -> ProviderMutationResult:
        self._require_configured()
        record = self.state.setdefault("rollback_records", {}).get(rollback_handle_id)
        if not record:
            return ProviderMutationResult(provider_id=self.provider_id, status="rollback_missing", idempotency_key="", rollback_handle_id=rollback_handle_id, rollback_verified=False)
        result = self.bridge.call("rollback", {
            "rollback_handle_id": rollback_handle_id,
            "created_external_ids": record.get("created_external_ids", []),
            "moved_external_ids": record.get("moved_external_ids", []),
            "deleted_external_ids": record.get("deleted_external_ids", []),
            "before_events": record.get("before_events", {}),
        })
        verified = bool(result.get("rollback_verified", False))
        record["rollback_verified"] = verified
        self._save_state()
        return ProviderMutationResult(
            provider_id=self.provider_id,
            status="rollback_verified" if verified else "rollback_unverified",
            idempotency_key=str(record.get("idempotency_key", "")),
            rollback_handle_id=rollback_handle_id,
            rollback_verified=verified,
            created_external_ids=list(record.get("created_external_ids", [])),
            moved_external_ids=list(record.get("moved_external_ids", [])),
            deleted_external_ids=list(record.get("deleted_external_ids", [])),
        )

    def snapshot(self) -> dict[str, Any]:
        health = self.health_status()
        rollback_records = self.state.get("rollback_records", {})
        return {
            "provider": self.provider_id,
            "real_provider": True,
            "real_oauth": False,
            "permission_status": health.get("status"),
            "auth_method": "eventkit_os_calendar_permission",
            "event_count": "eventkit_remote" if health.get("configured") else "permission_required",
            "idempotency_keys": len(self.state.get("idempotency", {})),
            "rollback_records": len(rollback_records),
            "rollback_verified": sum(1 for row in rollback_records.values() if row.get("rollback_verified")),
            "recent_mutations": [_redacted_mutation(row) for row in list(self.state.get("idempotency", {}).values())[-8:]],
            "connect_enabled": True,
            "sandbox_calendar_id": os.environ.get("CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID") or os.environ.get("CALENDAR_PILOT_EVENTKIT_SANDBOX_CALENDAR_ID"),
        }

    @staticmethod
    def idempotency_key(candidate: CandidateCalendarAction) -> str:
        return "idem_eventkit_" + hashlib.sha1(json.dumps(candidate.to_dict(), sort_keys=True).encode()).hexdigest()[:16]

    def _require_configured(self) -> None:
        health = self.health_status()
        if not health.get("configured"):
            raise CalendarProviderError(f"Apple Calendar permission is not configured: {health.get('status')}")

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"idempotency": {}, "rollback_records": {}}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.state_path, self.state)
        try:
            os.chmod(self.state_path, 0o600)
        except OSError:
            pass


class AppleEventKitManagedDriver:
    """Strict identifier-only port used by the managed EventKit EffectKernel adapter."""

    provider_id = PROVIDER_ID

    def __init__(self, provider: AppleEventKitProvider, *, calendar_id: str, expected_binding: Any | None = None) -> None:
        self.provider = provider
        self.calendar_id = str(calendar_id)
        if not self.calendar_id or self.calendar_id == "default":
            raise ValueError("managed EventKit driver requires an exact non-default calendar id")
        self.identifier_only_validation_count = 0
        self.post_verify_count = 0
        self.last_pre_binding: dict[str, Any] | None = None
        self.last_post_binding: dict[str, Any] | None = None
        self.last_target_vector_sha256: str | None = None
        self.runtime_identity_bound = False
        if expected_binding is not None:
            self._bind_runtime_identity(expected_binding)

    def _bind_runtime_identity(self, binding: Any) -> None:
        if not isinstance(self.provider.bridge, SwiftEventKitBridge):
            raise CalendarProviderError("managed EventKit runtime requires the canonical Swift bridge")
        executable = self.provider.bridge.executable or _default_bridge_path()
        bridge_path = _canonical_bridge_executable(Path(executable)).resolve()
        app_path = _calendar_pilot_app(bridge_path)
        if app_path is None or not bridge_path.is_file():
            raise CalendarProviderError("managed EventKit runtime bridge is not inside CalendarPilot.app")
        expected_bridge = Path(str(binding.bridge_path)).resolve()
        expected_app = Path(str(binding.app_path)).resolve()
        if bridge_path != expected_bridge or app_path.resolve() != expected_app:
            raise CalendarProviderError("managed EventKit app or bridge path changed")
        if _file_sha256(bridge_path) != str(binding.bridge_sha256) or _tree_sha256(app_path) != str(binding.app_sha256):
            raise CalendarProviderError("managed EventKit app or bridge hash changed")
        self.runtime_identity_bound = True

    @property
    def permission_status(self) -> str:
        health = self.provider.health_status()
        return str(health.get("authorization_status") or health.get("status") or "unknown")

    def binding_identity(self) -> dict[str, Any]:
        result = self.provider.bridge.call("calendar_identity", {"calendar_id": self.calendar_id})
        result["permission_status"] = str(result.get("authorization_status", self.permission_status))
        return result

    def snapshot(self, calendar_id: str) -> dict[str, Any]:
        if calendar_id != self.calendar_id:
            raise CalendarProviderError("managed EventKit snapshot target changed")
        return self.provider.bridge.call("managed_snapshot", {"calendar_id": self.calendar_id})

    def create(
        self,
        *,
        expected_binding: dict[str, Any],
        target_vector: dict[str, Any],
        idempotency_key: str,
        projection: dict[str, Any],
    ) -> str:
        explanation = str(projection.get("explanation", ""))
        if any(line.startswith("CalendarPilot-Idempotency: ") for line in explanation.splitlines()):
            raise CalendarProviderError("managed EventKit notes use a reserved marker namespace")
        result = self.provider.bridge.call("managed_commit", {
            "expected_binding": dict(expected_binding),
            "target_vector": dict(target_vector),
            "idempotency_key": idempotency_key,
            "action": {
                "action_type": "create_focus_block",
                "title": projection["title"],
                "start": projection["start"],
                "end": projection["end"],
                "calendar_id": self.calendar_id,
                "attendees": [],
                "metadata": {
                    "notes": explanation,
                    "calendarpilot_binding_id": str(expected_binding["binding_id"]),
                    "calendarpilot_binding_epoch": str(expected_binding["binding_epoch"]),
                },
            },
        })
        self.identifier_only_validation_count += 1
        self.post_verify_count += 1
        self.last_pre_binding = dict(result.get("pre_binding", {}))
        self.last_post_binding = dict(result.get("post_binding", {}))
        self.last_target_vector_sha256 = str(result.get("target_vector_sha256", ""))
        external_ids = [str(value) for value in result.get("created_external_ids", [])]
        if len(external_ids) != 1 or result.get("verified") is not True:
            raise CalendarProviderError("managed EventKit create did not post-verify exactly one event")
        return external_ids[0]

    def remove(
        self,
        *,
        expected_binding: dict[str, Any],
        target_vector: dict[str, Any],
        idempotency_key: str,
        external_id: str,
    ) -> bool:
        result = self.provider.bridge.call("managed_remove", {
            "expected_binding": dict(expected_binding),
            "target_vector": dict(target_vector),
            "idempotency_key": idempotency_key,
            "external_id": external_id,
        })
        self.identifier_only_validation_count += 1
        self.post_verify_count += 1
        self.last_pre_binding = dict(result.get("pre_binding", {}))
        self.last_post_binding = dict(result.get("post_binding", {}))
        self.last_target_vector_sha256 = str(result.get("target_vector_sha256", ""))
        return bool(result.get("verified_absent", False))


def _jsonable_action(action: Any) -> dict[str, Any]:
    from calendar_pilot.types import to_jsonable

    return to_jsonable(action)


def _expanded_actions(candidate: CandidateCalendarAction) -> list[AtomicCalendarAction]:
    output: list[AtomicCalendarAction] = []
    for action in candidate.actions:
        if action.action_type == AtomicActionType.AUTO_APPLY_PLAN:
            nested = actions_from_plan_metadata(action.metadata)
            if nested:
                output.extend(nested)
                continue
        output.append(action)
    return output


def _default_state_path() -> Path:
    return Path(os.environ.get("CALENDAR_PILOT_EVENTKIT_STATE_FILE", str(Path.home() / "Library" / "Application Support" / "CalendarPilot" / "apple_eventkit_provider.json")))


def _calendar_pilot_app(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if parent.name == "CalendarPilot.app":
            return parent
    return None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(value for value in root.rglob("*") if value.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(_file_sha256(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _default_bridge_path() -> str:
    candidates = []
    env_bridge = os.environ.get("CALENDAR_PILOT_EVENTKIT_BRIDGE", "").strip()
    if env_bridge:
        candidates.append(_canonical_bridge_executable(Path(env_bridge)))
    candidates.extend([
        Path(sys.prefix) / "bin" / "CalendarPilotEventKitBridge.app" / "Contents" / "MacOS" / "CalendarPilotEventKitBridge",
        Path(sys.prefix) / "bin" / "CalendarPilotEventKitBridge",
        Path(__file__).resolve().parents[4] / "bin" / "CalendarPilotEventKitBridge.app" / "Contents" / "MacOS" / "CalendarPilotEventKitBridge",
        Path(__file__).resolve().parents[4] / "bin" / "CalendarPilotEventKitBridge",
        Path(__file__).resolve().parents[3] / "packages" / "CalendarPilotKernel" / ".build" / "release" / "CalendarPilotEventKitBridge",
        Path(__file__).resolve().parents[3] / "packages" / "CalendarPilotKernel" / ".build" / "debug" / "CalendarPilotEventKitBridge",
    ])
    for path in candidates:
        if str(path) and path.exists():
            return str(path)
    return ""


def _read_window_bound(name: str) -> datetime | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalendarProviderError(f"{name} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise CalendarProviderError(f"{name} must include a UTC offset")
    return parsed


def _canonical_bridge_executable(path: Path) -> Path:
    if path.name != "CalendarPilotEventKitBridge":
        return path
    if any(parent.name == "CalendarPilotEventKitBridge.app" for parent in path.parents):
        return path
    sibling_app_executable = path.parent / "CalendarPilotEventKitBridge.app" / "Contents" / "MacOS" / "CalendarPilotEventKitBridge"
    if sibling_app_executable.exists():
        return sibling_app_executable
    return path


def _app_bundle_for_executable(executable: Path) -> Path | None:
    for parent in [executable, *executable.parents]:
        if parent.suffix == ".app" and parent.name == "CalendarPilotEventKitBridge.app":
            return parent
    return None


def _terminate_app_bundle(app_bundle: Path) -> None:
    try:
        subprocess.run(["osascript", "-e", f'tell application "{app_bundle}" to quit'], text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, check=False)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        subprocess.run(["pkill", "-f", str(app_bundle)], text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def _redacted_mutation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "idempotency_key": row.get("idempotency_key"),
        "candidate_id": row.get("candidate_id"),
        "rollback_handle_id": row.get("rollback_handle_id"),
        "external_ids_count": len(row.get("external_ids", [])),
        "created_external_ids_count": len(row.get("created_external_ids", [])),
        "moved_external_ids_count": len(row.get("moved_external_ids", [])),
        "deleted_external_ids_count": len(row.get("deleted_external_ids", [])),
        "status": row.get("status"),
        "rollback_verified": row.get("rollback_verified", False),
    }
