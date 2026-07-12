#!/usr/bin/env python3
"""Derive D1 evidence envelopes from retained browser/API/replay records."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any
from html.parser import HTMLParser


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evals.dogfood.capture.browser_capture import extract_semantic_dom, write_capture_manifest, write_capture_row


ZERO_FIELDS = ("provider_mutations", "effect_attempts", "stage_actions", "claims", "outbox_dispatches")
ACTION_TESTIDS = {
    "local_date": "candidate-local-date",
    "timezone": "candidate-timezone",
    "start": "candidate-start",
    "end": "candidate-end",
    "duration_minutes": "candidate-duration-minutes",
    "calendar_id": "candidate-calendar-id",
    "title": "candidate-title",
    "attendees": "candidate-attendees",
    "affected_ids": "candidate-affected-ids",
    "conflicts": "candidate-conflicts",
    "reversibility": "candidate-reversibility",
    "authority_need": "candidate-authority-need",
}
JSON_ACTION_FIELDS = {"attendees", "affected_ids", "conflicts"}
INT_ACTION_FIELDS = {"duration_minutes", "authority_need"}


class _CandidateDOMParser(HTMLParser):
    VOID_ELEMENTS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.candidates: list[dict[str, Any]] = []
        self._stack: list[tuple[int | None, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value for name, value in attrs}
        testid = attributes.get("data-testid")
        candidate_index = self._stack[-1][0] if self._stack else None
        if testid == "candidate-card":
            candidate_index = len(self.candidates)
            self.candidates.append({"candidate_id": attributes.get("data-candidate-id"), "fields": {}})
        if candidate_index is not None and testid:
            self.candidates[candidate_index]["fields"].setdefault(testid, [])
        if tag.lower() not in self.VOID_ELEMENTS:
            self._stack.append((candidate_index, testid))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() not in self.VOID_ELEMENTS and self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if not self._stack:
            return
        candidate_index, testid = self._stack[-1]
        if candidate_index is not None and testid:
            self.candidates[candidate_index]["fields"][testid].append(data)


def extract_candidate_dom(dom: str) -> list[dict[str, Any]]:
    parser = _CandidateDOMParser()
    parser.feed(dom)
    return [
        {
            "candidate_id": row["candidate_id"],
            "fields": {key: " ".join(" ".join(parts).split()) for key, parts in row["fields"].items()},
        }
        for row in parser.candidates
    ]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def replay_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = raw.get("replay_export", {}).get("records", [])
    return [row for row in rows if isinstance(row, dict)]


def latest_record(raw: dict[str, Any], record_type: str) -> dict[str, Any]:
    return next((row for row in reversed(replay_rows(raw)) if row.get("record_type") == record_type), {})


def selected_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    payload = latest_record(raw, "learning_decision").get("payload", {})
    candidate = payload.get("selected_behavior_payload", {}) if isinstance(payload, dict) else {}
    return dict(candidate) if isinstance(candidate, dict) else {}


def internal_action(raw: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    return candidate_action(selected_candidate(raw), timezone_name)


def candidate_action(candidate: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    actions = candidate.get("actions", [])
    action = dict(actions[0]) if isinstance(actions, list) and actions and isinstance(actions[0], dict) else {}
    if not action:
        return {}
    start = str(action.get("start") or "")
    end = str(action.get("end") or "")
    duration = None
    try:
        duration = int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() // 60)
    except (TypeError, ValueError):
        pass
    return {
        "local_date": start[:10] or None,
        "timezone": timezone_name,
        "start": start,
        "end": end,
        "duration_minutes": duration,
        "calendar_id": action.get("calendar_id"),
        "title": action.get("title"),
        "attendees": list(action.get("attendees") or []),
        "affected_ids": sorted({str(value) for value in [*(candidate.get("affected_event_ids") or []), *(candidate.get("affected_people_ids") or [])]}),
        "conflicts": list(action.get("conflicts") or []),
        "reversibility": candidate.get("reversibility"),
        "authority_need": candidate.get("required_authority_tier"),
    }


def d7_committed_action(raw: dict[str, Any], timezone_name: str) -> dict[str, Any]:
    receipt = latest_tool_receipt(raw, "request_commit", "committed")
    candidate = receipt.get("output", {}).get("candidate", {})
    return candidate_action(candidate if isinstance(candidate, dict) else {}, timezone_name)


def visible_action(semantic: dict[str, str]) -> dict[str, Any]:
    action: dict[str, Any] = {}
    for field, testid in ACTION_TESTIDS.items():
        if testid not in semantic:
            continue
        value: Any = semantic[testid]
        if field in JSON_ACTION_FIELDS:
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = [item.strip() for item in value.split(",") if item.strip()]
        elif field in INT_ACTION_FIELDS:
            try:
                value = int(value)
            except ValueError:
                pass
        action[field] = value
    return action


def visible_fact_ids(dom_html: str) -> list[str]:
    fact_ids = set(ids_from_dom(dom_html, "data-fact-id"))
    for candidate in extract_candidate_dom(dom_html):
        encoded = candidate.get("fields", {}).get("candidate-affected-ids")
        if not encoded:
            continue
        try:
            values = json.loads(encoded)
        except json.JSONDecodeError:
            values = []
        if isinstance(values, list):
            fact_ids.update(str(value) for value in values if value)
    return sorted(fact_ids)


def effect_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {field: 0 for field in ZERO_FIELDS}
    for row in rows:
        record_type = str(row.get("record_type") or "")
        payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        call = payload.get("call", {}) if isinstance(payload.get("call"), dict) else {}
        if record_type == "codex_tool_call" and call.get("tool_name") == "stage_action_packet":
            counts["stage_actions"] += 1
        if record_type == "effect_attempt":
            counts["effect_attempts"] += 1
        if record_type in {"provider_mutation", "provider_write"}:
            counts["provider_mutations"] += 1
        if record_type in {"effect_claim", "claim"}:
            counts["claims"] += 1
        if record_type in {"outbox_dispatch", "dispatch"}:
            counts["outbox_dispatches"] += 1
    return counts


def count_delta(current: dict[str, int], previous: dict[str, int]) -> dict[str, int]:
    return {field: max(0, current[field] - previous[field]) for field in ZERO_FIELDS}


def fact_ids_from_provider(raw: dict[str, Any]) -> list[str]:
    observation = latest_record(raw, "calendar_observation").get("payload", {})
    if isinstance(observation, dict) and isinstance(observation.get("fact_ids"), list):
        return sorted(str(value) for value in observation["fact_ids"])
    for row in reversed(replay_rows(raw)):
        if row.get("record_type") != "codex_tool_receipt":
            continue
        receipt = row.get("payload", {}).get("receipt", {})
        if receipt.get("tool_name") != "inspect_week":
            continue
        events = receipt.get("output", {}).get("raw_events", [])
        return sorted(str(event.get("event_id")) for event in events if isinstance(event, dict) and event.get("event_id"))
    return []


def provider_observation_payload(raw: dict[str, Any]) -> dict[str, Any]:
    payload = latest_record(raw, "calendar_observation").get("payload", {})
    return dict(payload) if isinstance(payload, dict) else {}


def ids_from_dom(dom: str, attribute: str) -> list[str]:
    return list(dict.fromkeys(re.findall(rf'{re.escape(attribute)}=["\']([^"\']+)["\']', dom)))


def latest_payload(rows: list[dict[str, Any]], record_type: str) -> dict[str, Any]:
    row = next((item for item in reversed(rows) if item.get("record_type") == record_type), {})
    payload = row.get("payload", {})
    return dict(payload) if isinstance(payload, dict) else {}


def latest_tool_receipt(raw: dict[str, Any], tool_name: str, status: str | None = None) -> dict[str, Any]:
    for row in reversed(replay_rows(raw)):
        if row.get("record_type") != "codex_tool_receipt":
            continue
        receipt = row.get("payload", {}).get("receipt", {})
        if receipt.get("tool_name") == tool_name and (status is None or receipt.get("status") == status):
            return dict(receipt)
    return {}


def latest_provider_transaction(raw: dict[str, Any], operation: str) -> dict[str, Any]:
    for row in reversed(replay_rows(raw)):
        if row.get("record_type") != "provider_transaction":
            continue
        payload = row.get("payload", {})
        if payload.get("operation") == operation and isinstance(payload.get("transaction"), dict):
            return dict(payload["transaction"])
    return {}


def d7_ledger(run_dir: Path, filename: str = "ledger.after_restart.raw.json") -> dict[str, Any]:
    return json.loads((run_dir / "ruler_capture" / filename).read_text(encoding="utf-8"))


def d7_provider_snapshot(run_dir: Path, name: str) -> dict[str, Any]:
    return json.loads((run_dir / "ruler_capture" / f"provider.{name}.raw.json").read_text(encoding="utf-8"))


def d7_provider_read_evidence(run_dir: Path) -> dict[str, Any]:
    snapshot = d7_provider_snapshot(run_dir, "before")
    return {
        "fact_ids": sorted(str(row.get("event_id")) for row in snapshot.get("events", []) if row.get("event_id")),
        "provider_identity": str(snapshot.get("provider_identity") or "unknown_provider"),
        "uses_sample_fixtures": False,
        "fixture_rows": [],
        "permission_owner": "app" if snapshot.get("permission_status") == "full_access" else "unknown",
        "read_window": snapshot.get("read_window"),
    }


def d7_effect_evidence(run_dir: Path, raw: dict[str, Any]) -> dict[str, Any]:
    ledger = d7_ledger(run_dir, "ledger.after_commit.raw.json")
    apply_rows = [row["ticket"] for row in ledger.get("tickets", {}).values() if row.get("ticket", {}).get("kind") == "apply"]
    apply_ticket = apply_rows[0] if len(apply_rows) == 1 else {}
    outbox = ledger.get("outbox", {}).get(apply_ticket.get("ticket_id"), {})
    effect_receipt = ledger.get("receipts", {}).get(apply_ticket.get("ticket_id"), {})
    commit_receipt = latest_tool_receipt(raw, "request_commit", "committed")
    provider_receipt = commit_receipt.get("output", {}).get("provider_receipt", {})
    external_ids = list(provider_receipt.get("external_ids") or [])
    external_id = str(external_ids[0]) if len(external_ids) == 1 else ""
    provider_ids = {str(row.get("event_id")) for row in d7_provider_snapshot(run_dir, "after").get("events", [])}
    swift = commit_receipt.get("output", {}).get("swift_receipt", {})
    ticket_binding = apply_ticket.get("target_binding", {})
    binding = json.loads((run_dir / "managed-binding.json").read_text(encoding="utf-8"))
    candidate = json.loads((run_dir / "d7_candidate.json").read_text(encoding="utf-8")).get("candidate", {})
    return {
        "tickets": len(apply_rows),
        "claims": list(outbox.get("facts") or []).count("claim"),
        "dispatches": list(outbox.get("facts") or []).count("dispatch"),
        "provider_mutations": int(ledger.get("adapter_state", {}).get("mutation_count", 0)),
        "verify_count": int(effect_receipt.get("phase") == "verified" and external_id in provider_ids),
        "ticket_external_id": external_id,
        "provider_external_id": external_id,
        "verify_external_id": external_id if external_id in provider_ids else None,
        "receipt_external_id": (swift.get("generated_event_ids") or [None])[0],
        "target_binding": f"{ticket_binding.get('binding_id')}@{ticket_binding.get('binding_epoch')}",
        "expected_binding": f"{binding.get('binding_id')}@{binding.get('epoch')}",
        "receipt_status": commit_receipt.get("status"),
        "has_attendees": bool(candidate.get("action", {}).get("attendees")),
        "action_family": apply_ticket.get("action_family"),
        "legacy_owner_mutations": int(not (commit_receipt.get("output", {}).get("retirement", {}).get("owner") == "effect_kernel")),
    }


def d7_undo_evidence(run_dir: Path, raw: dict[str, Any]) -> dict[str, Any]:
    ledger = d7_ledger(run_dir)
    before_restart_ledger = d7_ledger(run_dir, "ledger.after_undo.raw.json")
    tickets = [row["ticket"] for row in ledger.get("tickets", {}).values()]
    apply_ticket = next((row for row in tickets if row.get("kind") == "apply"), {})
    compensation = next((row for row in tickets if row.get("kind") == "compensate"), {})
    apply_receipt = ledger.get("receipts", {}).get(apply_ticket.get("ticket_id"), {})
    compensation_receipt = ledger.get("receipts", {}).get(compensation.get("ticket_id"), {})
    commit_receipt = latest_tool_receipt(raw, "request_commit", "committed")
    undo_receipt = latest_tool_receipt(raw, "request_undo", "reverted")
    commit_provider = commit_receipt.get("output", {}).get("provider_receipt", {})
    committed_ids = list(commit_provider.get("external_ids") or [])
    committed_id = str(committed_ids[0]) if len(committed_ids) == 1 else ""
    remaining = {str(row.get("event_id")) for row in d7_provider_snapshot(run_dir, "after_undo").get("events", [])}
    before_dispatches = sum(list(row.get("facts") or []).count("dispatch") for row in before_restart_ledger.get("outbox", {}).values())
    after_dispatches = sum(list(row.get("facts") or []).count("dispatch") for row in ledger.get("outbox", {}).values())
    linked = compensation.get("target_receipt_hash") == commit_provider.get("effect_receipt_sha256")
    rollback_verified = undo_receipt.get("output", {}).get("rollback_verified") is True
    return {
        "separate_compensation_authority": bool(compensation.get("grant_id") and compensation.get("grant_id") != apply_ticket.get("grant_id")),
        "remove_count": int(ledger.get("adapter_state", {}).get("compensation_mutation_count", 0)),
        "committed_external_id": committed_id,
        "remove_external_id": committed_id if linked and compensation_receipt.get("phase") == "verified" and rollback_verified else None,
        "absence_external_id": committed_id if committed_id not in remaining else None,
        "verified_absent": bool(committed_id and committed_id not in remaining and linked and rollback_verified),
        "audit_retained": bool(apply_ticket and apply_receipt and compensation),
        "restart_redispatch_count": max(0, after_dispatches - before_dispatches),
    }


def restart_digest(raw: dict[str, Any], label: str) -> dict[str, str]:
    view = raw.get("view", {})
    replay = replay_rows(raw)
    components = {
        "conversation": view.get("conversation"),
        "plan": active_plan_identity(raw),
        "candidate": view.get("frontier", {}).get("candidates"),
        "receipt": view.get("conversation", {}).get("receipt_cards"),
        "outcome": [row for row in replay if row.get("record_type") == "learning_outcome"],
        "runtime": stable_runtime_identity(raw),
        "replay": replay,
    }
    return {f"{label}_{key}_digest": digest(value) for key, value in components.items()}


def active_plan_identity(raw: dict[str, Any]) -> dict[str, Any]:
    frontier = raw.get("view", {}).get("frontier", {})
    return {
        "generation_id": frontier.get("generation_id"),
        "goal": frontier.get("goal"),
    }


def stable_runtime_identity(raw: dict[str, Any]) -> dict[str, Any]:
    runtime = raw.get("view", {}).get("runtime", {})
    fixture_paths = runtime.get("fixture_paths", {})
    return {
        "build_id": runtime.get("build_id"),
        "runtime_mode": runtime.get("runtime_mode"),
        "requested_runtime_mode": runtime.get("requested_runtime_mode"),
        "backends": runtime.get("backends"),
        "fixture_mode": runtime.get("fixture_mode"),
        "active_observation_id": fixture_paths.get("active_observation_id"),
        "uses_sample_fixtures": fixture_paths.get("uses_sample_fixtures"),
        "provider_observation_loaded": fixture_paths.get("provider_observation_loaded"),
        "live_target": runtime.get("live_target"),
        "production_target": runtime.get("production_target"),
        "valid_runtime_mode": runtime.get("valid_runtime_mode"),
    }


def envelope(run_id: str, scenario_id: str, source: str, payload: dict[str, Any], raw_artifact: str, raw_sha: str, record_id: str) -> dict[str, Any]:
    return {
        "dogfood_evidence_schema_version": "dogfood_evidence.v1",
        "run_id": run_id,
        "scenario_id": scenario_id,
        "source": source,
        "payload": payload,
        "raw_refs": [{
            "artifact": raw_artifact,
            "artifact_sha256": raw_sha,
            "record_id": record_id,
            "scenario_id": scenario_id,
            "fields": sorted(payload),
        }],
    }


def normalize(run_dir: Path) -> None:
    run_dir = run_dir.resolve()
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    truth = json.loads((run_dir / "operator_truth.json").read_text(encoding="utf-8"))
    if manifest.get("cell") not in {"D1", "D2", "D3", "D4", "D5", "D6", "D7"}:
        raise ValueError("D1-D7 normalizer cannot process another cell")
    browser_path = run_dir / "ruler_capture/browser_records.jsonl"
    browser_rows = load_jsonl(browser_path)
    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for row in browser_rows:
        if row.get("run_id") != manifest["run_id"]:
            raise ValueError("browser record crosses run boundary")
        by_scenario.setdefault(str(row["scenario_id"]), []).append(row)
    expected = set(manifest["scenario_ids"]) - {"P-IDENTITY"}
    if set(by_scenario) != expected:
        raise ValueError(f"browser capture coverage mismatch: expected {sorted(expected)}, got {sorted(by_scenario)}")

    derived: list[dict[str, Any]] = []
    rendered: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    replay_evidence: list[tuple[str, dict[str, Any]]] = []
    ui_evidence: list[tuple[str, dict[str, Any]]] = []
    previous_counts = {field: 0 for field in ZERO_FIELDS}
    chronological = [row for row in browser_rows if not (row["scenario_id"] == "P-RESTART" and row["phase"] == "before_restart")]
    deltas: dict[str, dict[str, int]] = {}
    for raw in chronological:
        current = effect_counts(replay_rows(raw))
        deltas[raw["record_id"]] = count_delta(current, previous_counts)
        previous_counts = current

    for scenario_id in sorted(expected, key=lambda value: manifest["scenario_ids"].index(value)):
        raw = by_scenario[scenario_id][-1]
        semantic = extract_semantic_dom(str(raw["dom_html"]))
        visible = semantic
        counts = deltas.get(raw["record_id"], {field: 0 for field in ZERO_FIELDS})
        replay_payload: dict[str, Any] = dict(counts)
        rendered_payload: dict[str, Any] = {
            "visible": visible,
            "driver_interaction": raw.get("driver_interaction"),
        }

        if scenario_id == "P-OBSERVE":
            rendered_payload.update({
                "fact_ids": ids_from_dom(raw["dom_html"], "data-fact-id"),
                "citation_ids": ids_from_dom(raw["dom_html"], "data-citation-id"),
                "candidate_ids": ids_from_dom(raw["dom_html"], "data-candidate-id"),
            })
        elif scenario_id == "P-LIVE-READ":
            rendered_payload.update({
                "fact_ids": visible_fact_ids(raw["dom_html"]),
                "citation_ids": ids_from_dom(raw["dom_html"], "data-citation-id"),
                "captured_from_ui": True,
            })
        elif scenario_id == "P-RECOMMEND":
            candidate = selected_candidate(raw)
            replay_payload["candidate_id"] = candidate.get("candidate_id")
            rendered_candidates = extract_candidate_dom(raw["dom_html"])
            rendered_ids = [str(row["candidate_id"]) for row in rendered_candidates if row.get("candidate_id")]
            leading_fields = rendered_candidates[0]["fields"] if rendered_candidates else {}
            rendered_payload.update({
                "candidate_id": rendered_ids[0] if rendered_ids else None,
                "addresses_goal": leading_fields.get("candidate-addresses-goal") == "true",
                "rationale_compares_noop": leading_fields.get("candidate-compares-noop") == "true",
            })
        elif scenario_id == "P-ACTION-VISIBLE":
            replay_payload["action"] = (
                d7_committed_action(by_scenario["P-EFFECT"][-1], truth["timezone"])
                if manifest.get("cell") == "D7"
                else internal_action(raw, truth["timezone"])
            )
            rendered_candidates = extract_candidate_dom(raw["dom_html"])
            leading_fields = rendered_candidates[0]["fields"] if rendered_candidates else {}
            rendered_payload.update({"action": visible_action(leading_fields), "captured_from_ui": True})
        elif scenario_id == "P-TIMEZONE":
            rendered_candidates = extract_candidate_dom(raw["dom_html"])
            leading_fields = rendered_candidates[0]["fields"] if rendered_candidates else {}
            rendered_payload["timezone_check"] = {
                key: leading_fields.get(f"timezone-{key.replace('_', '-')}") == "true"
                for key in ("local_day_matches", "offset_roundtrip", "duration_preserved", "tomorrow_uses_bound_timezone", "dst_case_resolved")
            }
        elif scenario_id == "P-FOLLOWUP":
            before = by_scenario["P-ACTION-VISIBLE"][-1]
            before_action = internal_action(before, truth["timezone"])
            after_action = internal_action(raw, truth["timezone"])
            before_candidate = selected_candidate(before)
            after_candidate = selected_candidate(raw)
            replay_payload["continuity"] = {
                "before_plan_digest": digest(active_plan_identity(before)),
                "after_plan_digest": digest(active_plan_identity(raw)),
                "before_candidate_digest": digest(before_candidate),
                "after_candidate_digest": digest(after_candidate),
                "before_action_digest": digest(before_action),
                "after_action_digest": digest(after_action),
                "frontier_generations": max(0, sum(row.get("record_type") == "frontier_generation" for row in replay_rows(raw)) - sum(row.get("record_type") == "frontier_generation" for row in replay_rows(before))),
                "resolved_from_existing_evidence": semantic.get("followup-resolved-from-existing-evidence") == "true",
            }
        elif scenario_id == "P-CORRECTION":
            replay_payload["correction"] = {
                "command_id": semantic.get("correction-command-id"),
                "citation_ids": ids_from_dom(raw["dom_html"], "data-correction-citation-id"),
                "old_belief_active": semantic.get("correction-old-belief-active") != "false",
                "new_plan_uses_correction": semantic.get("correction-new-plan-uses-correction") == "true",
                "before_authority_digest": semantic.get("correction-before-authority-digest"),
                "after_authority_digest": semantic.get("correction-after-authority-digest"),
            }
            if (raw.get("driver_interaction") or {}).get("succeeded"):
                ui_evidence.append((scenario_id, {"action": "candidate_corrected_then_reasked"}))
        elif scenario_id == "P-SIMULATE":
            preview: dict[str, Any] = {}
            for field in ("action", "provider_result", "conflict_result", "uncertainty", "denial_or_hold_reason"):
                value = semantic.get(f"simulation-{field.replace('_', '-')}")
                if value is not None:
                    try:
                        preview[field] = json.loads(value)
                    except json.JSONDecodeError:
                        preview[field] = value
            rendered_payload["preview"] = preview
            if (raw.get("driver_interaction") or {}).get("succeeded"):
                ui_evidence.append((scenario_id, {"action": "simulate"}))
        elif scenario_id == "P-DENIAL":
            rendered_payload["denial"] = {
                "owner": semantic.get("denial-owner"),
                "reason": semantic.get("denial-reason"),
                "repair": semantic.get("denial-repair"),
                "specific": semantic.get("denial-specific") == "true",
            }
        elif scenario_id == "P-NOOP":
            candidate = selected_candidate(raw)
            rendered_payload.update({
                "winner": "no_op" if candidate.get("intent") in {"no_op", "do_nothing"} else candidate.get("intent"),
                "binding_constraint": semantic.get("noop-binding-constraint"),
                "write_controls_visible": any(
                    f'data-testid="{testid}"' in raw["dom_html"]
                    for testid in ("simulate-candidate", "stage-candidate", "commit-candidate")
                ),
            })
        elif scenario_id == "P-FEEDBACK":
            exposure = latest_payload(replay_rows(raw), "learning_exposure")
            outcome = latest_payload(replay_rows(raw), "learning_outcome")
            rendered_payload["exposure"] = {
                "exposure_id": exposure.get("exposure_id") or exposure.get("event_id"),
                "decision_id": exposure.get("decision_id"),
                "candidate_id": (exposure.get("rendered_candidate_ids") or [None])[0],
            }
            same_outcomes = [row for row in replay_rows(raw) if row.get("record_type") == "learning_outcome" and row.get("payload", {}).get("exposure_id") == outcome.get("exposure_id") and row.get("payload", {}).get("candidate_id") == outcome.get("candidate_id")]
            replay_payload["outcome"] = {
                "exposure_id": outcome.get("exposure_id"),
                "decision_id": outcome.get("decision_id"),
                "candidate_id": outcome.get("candidate_id"),
                "terminal_count": len(same_outcomes),
            }
            if (raw.get("driver_interaction") or {}).get("succeeded"):
                ui_evidence.append((scenario_id, {"action": "dismissed"}))
        elif scenario_id == "P-RESTART":
            before = next(row for row in by_scenario[scenario_id] if row["phase"] == "before_restart")
            after = next(row for row in by_scenario[scenario_id] if row["phase"] == "after_restart")
            before_ids = [row.get("record_id") for row in replay_rows(before)]
            after_ids = [row.get("record_id") for row in replay_rows(after)]
            replay_payload["restart"] = {
                **restart_digest(before, "before"),
                **restart_digest(after, "after"),
                "duplicate_tool_calls": max(0, len(after_ids) - len(set(after_ids))),
                "duplicate_effects": 0,
            }
        elif scenario_id == "P-EFFECT":
            candidate = json.loads((run_dir / "d7_candidate.json").read_text(encoding="utf-8")).get("candidate", {})
            replay_payload["effect"] = d7_effect_evidence(run_dir, raw)
            ui_evidence.append((scenario_id, {"action": "confirmed_private_create", "candidate_id": candidate.get("candidate_id")}))
        elif scenario_id == "P-UNDO":
            replay_payload["undo"] = d7_undo_evidence(run_dir, raw)
            ui_evidence.append((scenario_id, {"action": "separately_confirmed_compensation"}))

        rendered.append((scenario_id, rendered_payload, raw))
        replay_evidence.append((scenario_id, replay_payload))

    provider_raw = by_scenario.get("P-OBSERVE", by_scenario.get("P-LIVE-READ", []))[-1]
    observation_payload = provider_observation_payload(provider_raw)
    raw_health = provider_raw.get("health", {}) if isinstance(provider_raw.get("health"), dict) else {}
    health_backends = raw_health.get("backends", {}) if isinstance(raw_health.get("backends"), dict) else {}
    fixture_paths = raw_health.get("fixture_paths", {}) if isinstance(raw_health.get("fixture_paths"), dict) else {}
    provider_health = raw_health.get("provider_health", {}) if isinstance(raw_health.get("provider_health"), dict) else {}
    provider_identity = str(health_backends.get("provider") or "unknown_provider")
    live_provider = provider_identity == "apple_eventkit"
    provider_payload = {
        "fact_ids": fact_ids_from_provider(provider_raw),
        "provider_identity": provider_identity,
        "uses_sample_fixtures": bool(fixture_paths.get("uses_sample_fixtures")),
        "fixture_rows": [],
        "permission_owner": "app" if provider_health.get("auth_method") == "eventkit_os_calendar_permission" else "fixture",
        "read_window": observation_payload.get("read_window"),
    }
    if manifest.get("cell") == "D7":
        provider_payload = d7_provider_read_evidence(run_dir)
    provider_rows = [("P-LIVE-READ" if manifest.get("cell") == "D7" else "P-OBSERVE", provider_payload)]
    if manifest.get("cell") in {"D5", "D6", "D7"}:
        if provider_rows[0][0] != "P-LIVE-READ":
            provider_rows.append(("P-LIVE-READ", provider_payload))

    provider_checkpoint_rows: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    if manifest.get("cell") == "D7":
        provider_checkpoint_rows = {
            "provider_after": [("P-EFFECT", {"events": d7_provider_snapshot(run_dir, "after").get("events", []), "provider_identity": "apple_eventkit", "verified": True})],
            "provider_after_undo": [("P-UNDO", {"events": d7_provider_snapshot(run_dir, "after_undo").get("events", []), "provider_identity": "apple_eventkit", "verified": True})],
        }

    sources = [("rendered_view", [(scenario, payload) for scenario, payload, _ in rendered]), ("replay", replay_evidence), ("ui_action", ui_evidence), ("provider_read", provider_rows), *provider_checkpoint_rows.items()]
    for source, rows in sources:
        for index, (scenario_id, payload) in enumerate(rows, 1):
            derived.append({"record_id": f"derived:{source}:{scenario_id}:{index}", "scenario_id": scenario_id, "source": source, **payload})
    derived_path = run_dir / "ruler_capture/derived_records.jsonl"
    derived_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in derived), encoding="utf-8")
    derived_sha = sha256_file(derived_path)
    raw_artifact = str(derived_path.relative_to(run_dir))
    derived_by_key = {(row["source"], row["scenario_id"]): row for row in derived}

    def envelopes_for(source: str, rows: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
        return [envelope(manifest["run_id"], scenario_id, source, payload, raw_artifact, derived_sha, derived_by_key[(source, scenario_id)]["record_id"]) for scenario_id, payload in rows]

    (run_dir / "rendered_views.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in envelopes_for("rendered_view", [(scenario, payload) for scenario, payload, _ in rendered])), encoding="utf-8")
    (run_dir / "ui_actions.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in envelopes_for("ui_action", ui_evidence)), encoding="utf-8")

    replay_path = run_dir / "replay.jsonl"
    raw_replay_path = run_dir / "ruler_capture/replay.raw.jsonl"
    shutil.copy2(replay_path, raw_replay_path)
    with replay_path.open("a", encoding="utf-8") as handle:
        for row in envelopes_for("replay", replay_evidence):
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    provider_document = {
        "run_id": manifest["run_id"],
        "provider_identity": provider_payload["provider_identity"],
        "dogfood_evidence": envelopes_for("provider_read", provider_rows),
    }
    (run_dir / "provider.before.json").write_text(json.dumps(provider_document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if manifest.get("cell") == "D7":
        for checkpoint, source in (("after", "provider_after"), ("after_undo", "provider_after_undo")):
            document = {
                "run_id": manifest["run_id"],
                "provider_identity": "apple_eventkit",
                "dogfood_evidence": envelopes_for(source, provider_checkpoint_rows[source]),
            }
            (run_dir / f"provider.{checkpoint}.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    final_raw = by_scenario["P-RESTART"][-1]
    (run_dir / "replay_export.json").write_text(json.dumps(final_raw["replay_export"], indent=2, sort_keys=True) + "\n", encoding="utf-8")

    capture_rows_path = run_dir / "ruler_capture/semantic_dom.jsonl"
    capture_rows_path.unlink(missing_ok=True)
    write_capture_manifest(run_dir, run_id=manifest["run_id"], browser="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", available=True)
    stimulus_hashes = {row["scenario_id"]: row["utf8_sha256"] for row in manifest["stimuli"]}
    for scenario_id, _, raw in rendered:
        write_capture_row(run_dir, run_id=manifest["run_id"], scenario_id=scenario_id, stimulus_utf8_sha256=stimulus_hashes[scenario_id], url=str(raw["url"]), dom_html=str(raw["dom_html"]))

    screenshot_rows = []
    for scenario_id, records in by_scenario.items():
        raw = records[-1]
        screenshot_path = run_dir / raw["screenshot"]
        screenshot_rows.append({"scenario_id": scenario_id, "path": str(screenshot_path.relative_to(run_dir)), "sha256": sha256_file(screenshot_path)})
    (run_dir / "screenshots/manifest.json").write_text(json.dumps({"run_id": manifest["run_id"], "screenshots": screenshot_rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: normalize_d1.py <run-dir>")
    normalize(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
