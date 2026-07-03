#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from calendar_pilot.diffusiongemma.policy import DiffusionGemmaPolicy
from calendar_pilot.environment.taxonomy import CanonicalIntent, normalize_intent
from calendar_pilot.types import RawCalendarObservation, UserBiography, to_jsonable


SEEDS_DIR = ROOT / "experiments" / "seeds"
OBSERVED_AT = "2026-07-06T08:00:00-07:00"
TZ = "America/Los_Angeles"
WEEK_START = datetime.fromisoformat("2026-07-06T00:00:00-07:00")
WEEK_END = datetime.fromisoformat("2026-07-13T00:00:00-07:00")
DEFAULT_PERTURBATIONS = [
    "remove_prep_slot",
    "increase_notification_fatigue",
    "expire_authority_grant",
    "compress_between_meetings",
    "inject_flexible_hold",
]
PERTURBATION_CATALOG = {
    "remove_prep_slot",
    "increase_notification_fatigue",
    "expire_authority_grant",
    "compress_between_meetings",
    "inject_flexible_hold",
    "add_external_meeting",
    "add_social_conflict",
    "make_observation_stale",
}
DENSITY_BANDS = {
    "dense": (35, 60),
    "medium": (20, 35),
    "deep": (12, 20),
}


ROSTER: list[dict[str, Any]] = [
    {"persona": "founder_operator", "density": "medium", "base": "seed_founder_baseline", "variant": "seed_founder_board_week_crunch", "variant_name": "board_week_crunch"},
    {"persona": "sales_account_executive", "density": "dense", "base": "seed_ae_baseline", "variant": "seed_ae_renewal_week_high_pressure", "variant_name": "renewal_week_high_pressure"},
    {"persona": "engineering_manager", "density": "medium", "base": "seed_em_baseline", "variant": "seed_em_incident_review_overload", "variant_name": "incident_review_overload"},
    {"persona": "researcher_deep_work", "density": "deep", "base": "seed_researcher_baseline", "variant": "seed_researcher_deadline_fatigue", "variant_name": "deadline_fatigue", "flagged": True},
    {"persona": "consultant_client_heavy", "density": "dense", "base": "seed_consultant_baseline", "variant": "seed_consultant_backtoback_clients", "variant_name": "backtoback_clients"},
    {"persona": "parent_caregiver", "density": "medium", "base": "seed_parent_baseline", "variant": "seed_parent_school_pickup_conflicts", "variant_name": "school_pickup_conflicts"},
    {"persona": "executive_assistant_dense", "density": "dense", "base": "seed_ea_dense_baseline", "variant": "seed_ea_dense_double_bookings", "variant_name": "double_bookings", "flagged": True},
    {"persona": "travel_heavy", "density": "dense", "base": "seed_travel_baseline", "variant": "seed_travel_timezone_hop", "variant_name": "timezone_hop", "flagged": True},
    {"persona": "burnout_high_fatigue", "density": "medium", "base": "seed_burnout_baseline", "variant": "seed_burnout_notification_saturation", "variant_name": "notification_saturation", "flagged": True},
    {"persona": "fragmented_admin_heavy", "density": "medium", "base": "seed_admin_frag_baseline", "variant": "seed_admin_frag_context_thrash", "variant_name": "context_thrash"},
]


def _json_dump(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime.fromisoformat(f"2026-07-{day:02d}T{hour:02d}:{minute:02d}:00-07:00")


def _event(event_id: str, title: str, start: datetime, minutes: int, *, category: str, attendees: list[str] | None = None, owned: bool = False, flexible: bool = False, location: str = "Zoom") -> dict[str, Any]:
    return {
        "attendees": attendees or [],
        "calendar_id": "work",
        "category": category,
        "end": (start + timedelta(minutes=minutes)).isoformat(),
        "event_id": event_id,
        "is_flexible": flexible,
        "is_user_owned": owned,
        "location": location,
        "notes": "",
        "start": start.isoformat(),
        "title": title,
    }


def _task(task_id: str, title: str, due: datetime, minutes: int, category: str) -> dict[str, Any]:
    return {"task_id": task_id, "title": title, "due": due.isoformat(), "estimated_minutes": minutes, "category": category}


def _notification_history(fatigue: float) -> list[dict[str, str]]:
    start = datetime.fromisoformat("2026-06-22T08:30:00-07:00")
    rows = []
    for idx in range(14):
        hour = 20 if idx % 3 else 9
        rows.append({
            "sent_at": (start + timedelta(days=idx, hours=hour - 8)).isoformat(),
            "kind": "suggestion",
            "outcome": "dismissed" if fatigue >= 0.5 or idx % 2 else "accepted",
        })
    return rows


def _target_count(density: str, pressure: bool) -> int:
    if density == "dense":
        return 42 if pressure else 36
    if density == "deep":
        return 16 if pressure else 13
    return 28 if pressure else 22


def _base_events(seed_id: str, persona: str, density: str, pressure: bool) -> list[dict[str, Any]]:
    events = [
        _event("evt_pressure_external", f"{persona.replace('_', ' ').title()} external review", _dt(8, 15), 60, category="external_meeting", attendees=["client@example.com", "me@seed.example"], owned=False, flexible=False),
        _event("evt_admin_hold", "Flexible admin hold", _dt(8, 13, 30), 60, category="admin", owned=True, flexible=True, location=""),
        _event("evt_team_sync", "Team sync", _dt(7, 11), 30, category="internal_meeting", attendees=["team@example.com"], owned=False, flexible=True),
    ]
    count = _target_count(density, pressure)
    day_cycle = [6, 7, 8, 9, 10, 11, 12]
    hour_cycle = [9, 10, 11, 12, 16, 17]
    idx = 0
    while len(events) < count:
        day = day_cycle[idx % len(day_cycle)]
        hour = hour_cycle[(idx // len(day_cycle)) % len(hour_cycle)]
        minute = 0 if idx % 2 == 0 else 30
        start = _dt(day, hour, minute)
        if day == 8 and hour in {13, 14, 15}:
            idx += 1
            continue
        category = "admin" if idx % 5 == 0 else ("external_meeting" if pressure and idx % 7 == 0 else "internal_meeting")
        attendees = ["peer@example.com"] if category != "admin" else []
        events.append(_event(f"evt_{seed_id}_{idx:02d}", f"{category.replace('_', ' ').title()} {idx + 1}", start, 30, category=category, attendees=attendees, owned=category == "admin", flexible=category == "admin", location="" if category == "admin" else "Zoom"))
        idx += 1
    return sorted(events, key=lambda row: (row["start"], row["event_id"]))


def build_base_seed(seed_id: str, persona: str, variant: str, *, density: str, pressure: bool, flagged: bool = False) -> dict[str, Any]:
    fatigue = 0.72 if ("burnout" in seed_id or "fatigue" in seed_id or pressure) else 0.35
    expected_good = ["create_prep_block", "move_meeting", "add_buffer"]
    expected_bad = [
        {"intent": "notify_summary", "why": "notification fatigue makes notification-only suggestions risky"},
        {"intent": "decline_or_trim", "why": "the high-stakes external meeting should not be touched"},
    ]
    if flagged:
        expected_good = ["add_buffer", "move_meeting", "protect_deep_work"]
        expected_bad.insert(0, {"intent": "create_prep_block", "why": "flagged seed expects tuning to demote the untuned prep-block leader"})
    return {
        "authority": {"profile": "tier3_private"},
        "description": f"{persona.replace('_', ' ')} {variant.replace('_', ' ')} seeded week with external pressure, flexible holds, and notification history.",
        "expectations": {
            "expected_bad_intents": expected_bad,
            "expected_good_intents": expected_good,
        },
        "expects_tuning_leader_change": bool(flagged),
        "goal": "Protect the renewal call and reduce notification noise",
        "notes": "Deterministic P10 seed materialized from the locked roster.",
        "observation": {
            "device_context": {"active_surface": "calendar_week_view", "is_focus_mode": False, "local_hour": 8},
            "events": _base_events(seed_id, persona, density, pressure),
            "notification_history": _notification_history(fatigue),
            "observation_id": f"obs_{seed_id}",
            "observed_at": OBSERVED_AT,
            "prior_actions": [],
            "tasks": [
                _task("task_pressure_prep", "Prepare notes for external review", _dt(8, 15), 45, "prep"),
                _task("task_admin_cleanup", "Clear admin backlog", _dt(10, 17), 40, "admin"),
            ],
            "time_zone_id": TZ,
            "user_scope_id": seed_id,
        },
        "persona": persona,
        "perturbations": list(DEFAULT_PERTURBATIONS),
        "profile": {
            "admin_windows": ["Friday 14:00-17:00"],
            "ask_before_people_meetings": True,
            "auto_create_travel_buffers": True,
            "auto_move_flexible_holds": True,
            "bad_response_hours": [20, 21, 22, 23],
            "best_response_hours": [8, 13],
            "deep_work_windows": ["09:00-11:00"],
            "notification_fatigue": fatigue,
            "preference_claims": [
                {"claim": "accepts prep blocks near external calls", "confidence": 0.82},
                {"claim": "dismisses evening suggestions", "confidence": 0.77 if fatigue >= 0.5 else 0.55},
            ],
            "user_scope_id": seed_id,
        },
        "seed_id": seed_id,
        "seed_schema_version": "1.0",
        "variant": variant,
    }


def base_seed_payloads() -> list[dict[str, Any]]:
    out = []
    for row in ROSTER:
        out.append(build_base_seed(row["base"], row["persona"], "baseline", density=row["density"], pressure=False, flagged=False))
        out.append(build_base_seed(row["variant"], row["persona"], row["variant_name"], density=row["density"], pressure=True, flagged=bool(row.get("flagged"))))
    return out


def write_base_seeds(seed_dir: Path = SEEDS_DIR) -> None:
    for seed in base_seed_payloads():
        _json_dump(seed_dir / f"{seed['seed_id']}.json", seed)


def load_seed(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_paths(seed: str | None = None, seed_dir: Path = SEEDS_DIR) -> list[Path]:
    if seed:
        p = Path(seed)
        return [p if p.is_absolute() else ROOT / p]
    return sorted(p for p in seed_dir.glob("*.json") if p.is_file())


def _canonical_intent(value: str) -> str:
    return normalize_intent(value)["intent"]


def _fixture_frontier(seed: dict[str, Any]) -> list[Any]:
    obs = RawCalendarObservation.from_dict(seed["observation"])
    bio = UserBiography.from_dict(seed["profile"])
    return DiffusionGemmaPolicy().generate_candidates(obs, bio, goal=seed.get("goal"))


def lint_seed(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        seed = load_seed(path)
    except Exception as exc:
        return [f"{path}: invalid JSON: {exc}"]
    seed_id = str(seed.get("seed_id", ""))
    if seed.get("seed_schema_version") != "1.0":
        errors.append("L1 seed_schema_version must be 1.0")
    if path.name != f"{seed_id}.json" or not re.match(r"^seed_[a-z0-9_]+(?:__[a-z0-9_]+)?$", seed_id):
        errors.append("L1 filename/seed_id mismatch or invalid seed_id")
    try:
        obs = RawCalendarObservation.from_dict(seed["observation"])
        bio = UserBiography.from_dict(seed["profile"])
        if to_jsonable(obs)["observation_id"] != seed["observation"]["observation_id"] or bio.to_dict()["user_scope_id"] != seed["profile"]["user_scope_id"]:
            errors.append("L2 round-trip lost required ids")
    except Exception as exc:
        errors.append(f"L2 observation/profile did not round-trip: {exc}")
        return errors
    labels = {intent.value for intent in CanonicalIntent}
    good = set(seed.get("expectations", {}).get("expected_good_intents", []))
    bad = {row.get("intent") for row in seed.get("expectations", {}).get("expected_bad_intents", []) if isinstance(row, dict)}
    if not good or any(item not in labels for item in good | bad) or good & bad or {"do_nothing", "other"} & good:
        errors.append("L3 expectation labels must be canonical, disjoint, and useful")
    if obs.observed_at.isoformat() != OBSERVED_AT or obs.time_zone_id != TZ:
        errors.append("L4 observed_at/time_zone_id mismatch")
    for event in obs.events:
        if event.start < WEEK_START or event.end > WEEK_END:
            errors.append(f"L4 event outside fixed week: {event.event_id}")
            break
    density = next((row["density"] for row in ROSTER if row["persona"] == seed.get("persona")), None)
    if density:
        lo, hi = DENSITY_BANDS[density]
        if not (lo <= len(obs.events) <= hi):
            errors.append(f"L5 event count {len(obs.events)} outside {density} band {lo}-{hi}")
    else:
        errors.append("L5 unknown persona")
    history = obs.notification_history
    if len(history) < 1:
        errors.append("L6 notification_history must have at least one row")
    if bio.notification_fatigue >= 0.5:
        try:
            sent = [datetime.fromisoformat(str(row["sent_at"])) for row in history]
            if len(history) < 5 or max(sent) - min(sent) < timedelta(days=7):
                errors.append("L6 high fatigue seeds need at least 5 notifications spanning 7 days")
        except Exception as exc:
            errors.append(f"L6 invalid notification history: {exc}")
    frontier = _fixture_frontier(seed)
    useful = [c for c in frontier if _canonical_intent(c.intent) not in {"do_nothing", "other"} and c.expected_reward > 0]
    if not useful:
        errors.append("L7 fixture policy produced no useful non-do-nothing candidate")
    if seed.get("authority", {}).get("profile") not in {"tier1_recommend", "tier3_private"}:
        errors.append("L8 authority.profile is not a known v0 profile")
    perturbations = seed.get("perturbations", [])
    if len(perturbations) != 5 or any(p not in PERTURBATION_CATALOG for p in perturbations):
        errors.append("L9 perturbations must be exactly 5 catalog entries")
    if seed.get("expects_tuning_leader_change"):
        leader = _canonical_intent(frontier[0].intent) if frontier else ""
        if leader not in bad:
            errors.append(f"L10 flagged seed leader {leader!r} is not expected_bad")
    return errors


def validate(seed: str | None = None) -> list[str]:
    paths = seed_paths(seed)
    if not paths:
        return ["no seed files found"]
    violations: list[str] = []
    for path in paths:
        for error in lint_seed(path):
            violations.append(f"{path.relative_to(ROOT)}: {error}")
    return violations


def _retarget_ids(seed: dict[str, Any], seed_id: str) -> None:
    seed["seed_id"] = seed_id
    seed["observation"]["observation_id"] = f"obs_{seed_id}"
    seed["observation"]["user_scope_id"] = seed_id
    seed["profile"]["user_scope_id"] = seed_id
    for idx, event in enumerate(seed["observation"]["events"]):
        event["event_id"] = f"{event['event_id']}__{seed_id}" if not str(event["event_id"]).endswith(seed_id) else event["event_id"]


def _highest_external(seed: dict[str, Any]) -> dict[str, Any] | None:
    externals = [e for e in seed["observation"]["events"] if e.get("category") == "external_meeting"]
    return sorted(externals, key=lambda e: e["start"])[0] if externals else None


def apply_perturbation(seed: dict[str, Any], perturbation: str) -> dict[str, Any]:
    out = copy.deepcopy(seed)
    external = _highest_external(out)
    if perturbation == "remove_prep_slot":
        if external is None:
            raise ValueError("remove_prep_slot requires an external meeting")
        start = datetime.fromisoformat(external["start"])
        before = len(out["observation"]["events"])
        out["observation"]["events"] = [
            e for e in out["observation"]["events"]
            if not (e.get("is_flexible") and datetime.fromisoformat(e["end"]) <= start and start - datetime.fromisoformat(e["end"]) <= timedelta(hours=2))
        ]
        if len(out["observation"]["events"]) == before:
            raise ValueError("remove_prep_slot found no flexible hold before the pressure meeting")
        out.setdefault("expectations", {}).setdefault("perturbation_checks", []).append({"check": "intent_in_top_k", "intent": "create_prep_block", "k": 3})
    elif perturbation == "increase_notification_fatigue":
        out["profile"]["notification_fatigue"] = max(float(out["profile"].get("notification_fatigue", 0)), 0.8)
        base = datetime.fromisoformat("2026-06-29T20:00:00-07:00")
        out["observation"].setdefault("notification_history", []).extend({"sent_at": (base + timedelta(days=i)).isoformat(), "kind": "suggestion", "outcome": "dismissed"} for i in range(5))
        out.setdefault("expectations", {}).setdefault("perturbation_checks", []).append({"check": "intent_not_top1", "intent": "notify_summary"})
    elif perturbation == "expire_authority_grant":
        out["authority"]["profile"] = "tier1_recommend"
        out.setdefault("expectations", {}).setdefault("perturbation_checks", []).append({"check": "failure_mode_present", "mode": "denied_actuation", "min": 1})
    elif perturbation == "compress_between_meetings":
        for idx, hour in enumerate([9, 9, 10]):
            minute = 0 if idx != 1 else 30
            out["observation"]["events"].append(_event(f"evt_compress_{idx}", f"Compressed meeting {idx + 1}", _dt(9, hour, minute), 30, category="internal_meeting", attendees=["peer@example.com"]))
        out.setdefault("expectations", {}).setdefault("perturbation_checks", []).append({"check": "intent_in_top_k", "intent": "add_buffer", "k": 3})
    elif perturbation == "inject_flexible_hold":
        out["observation"]["events"].append(_event("evt_injected_flexible_hold", "Injected flexible hold", _dt(8, 12, 30), 30, category="admin", owned=True, flexible=True, location=""))
        out.setdefault("expectations", {}).setdefault("perturbation_checks", []).append({"check": "intent_in_top_k", "intent": "move_meeting", "k": 3})
    else:
        raise ValueError(f"{perturbation} is tracked-only or unsupported in v0 generation")
    return out


def generate_variants(seed: str | None = None) -> None:
    for path in seed_paths(seed):
        base = load_seed(path)
        if base.get("variant_of"):
            continue
        for perturbation in base.get("perturbations", []):
            if perturbation not in DEFAULT_PERTURBATIONS:
                continue
            variant = apply_perturbation(base, perturbation)
            variant_id = f"{base['seed_id']}__{perturbation}"
            _retarget_ids(variant, variant_id)
            variant["variant_of"] = base["seed_id"]
            variant["variant"] = f"{base.get('variant', 'base')}__{perturbation}"
            variant["description"] = f"{base.get('description', '')} Perturbation: {perturbation}."
            _json_dump(path.parent / f"{variant_id}.json", variant)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--generate-variants", action="store_true")
    parser.add_argument("--write-base-seeds", action="store_true", help="materialize the locked 20-seed roster")
    parser.add_argument("--seed", default="")
    args = parser.parse_args()
    if args.write_base_seeds:
        write_base_seeds()
    if args.generate_variants:
        generate_variants(args.seed or None)
    if args.validate:
        violations = validate(args.seed or None)
        if violations:
            print("\n".join(violations))
            raise SystemExit(1)
        print("seed validation passed")
    if not (args.write_base_seeds or args.generate_variants or args.validate):
        parser.print_help()


if __name__ == "__main__":
    main()