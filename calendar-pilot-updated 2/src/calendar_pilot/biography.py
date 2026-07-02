
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib

from calendar_pilot.types import (
    BiographyRepairPlan,
    CorrectionProvenance,
    ProfileUpdateEvent,
    RewardEvent,
    UserBiography,
)


class BiographyStore:
    """Inspectable biography updater for the reference implementation.

    The biography is intentionally agentic in this product direction, but it is
    now controlled through explicit update events, confidence deltas, provenance,
    and decay. A correction is recorded as a correction, not silently laundered
    into an opaque latent preference.
    """

    def update_from_reward(
        self,
        biography: UserBiography,
        reward: RewardEvent,
        *,
        source: str = "reward_event",
        observed_at: datetime | None = None,
    ) -> UserBiography:
        observed_at = observed_at or reward.observed_at
        fatigue = biography.notification_fatigue
        reason = "neutral"
        if reward.notification_dismissed or reward.ignored:
            fatigue = min(1.0, fatigue + 0.05)
            reason = "notification fatigue increased after dismissal/ignore"
        if reward.accepted or reward.explicit_useful:
            fatigue = max(0.0, fatigue - 0.02)
            reason = "fatigue decreased after accepted/useful action"
        updated = replace(biography, notification_fatigue=round(fatigue, 3), last_profile_update_at=observed_at)
        event = self._event(
            biography=biography,
            claim="notification_fatigue",
            prior=biography.notification_fatigue,
            next_value=updated.notification_fatigue,
            reason=reason,
            provenance=CorrectionProvenance(source=source, surface="reward_logger", created_at=observed_at, note=reward.reward_event_id),
        )
        return self._append_event(updated, event)

    def add_claim(
        self,
        biography: UserBiography,
        claim: str,
        confidence: float,
        *,
        provenance: CorrectionProvenance | None = None,
    ) -> UserBiography:
        provenance = provenance or CorrectionProvenance(
            source="manual",
            surface="profile_editor",
            created_at=datetime.now(timezone.utc),
            note="user/profile supplied claim",
        )
        bounded = max(0.0, min(1.0, confidence))
        prior = biography.confidence_for(claim)
        claims = [dict(c) for c in biography.preference_claims]
        claims.append({
            "claim": claim,
            "confidence": bounded,
            "source": provenance.source,
            "updated_at": provenance.created_at.isoformat(),
        })
        updated = replace(biography, preference_claims=claims, last_profile_update_at=provenance.created_at)
        event = self._event(biography, claim, prior, bounded, "explicit profile claim added", provenance)
        return self._append_event(updated, event)

    def apply_user_correction(
        self,
        biography: UserBiography,
        claim: str,
        correction: str,
        confidence_delta: float = -0.20,
        *,
        surface: str = "codex_profile_repair",
    ) -> UserBiography:
        now = datetime.now(timezone.utc)
        prior = biography.confidence_for(claim)
        next_conf = max(0.0, min(1.0, prior + confidence_delta))
        claims: list[dict] = []
        found = False
        for c in biography.preference_claims:
            item = dict(c)
            if claim.lower() in item.get("claim", "").lower():
                item["confidence"] = next_conf
                item["correction"] = correction
                item["updated_at"] = now.isoformat()
                found = True
            claims.append(item)
        if not found:
            claims.append({"claim": claim, "confidence": next_conf, "correction": correction, "updated_at": now.isoformat()})
        provenance = CorrectionProvenance(source="user_correction", surface=surface, created_at=now, note=correction)
        updated = replace(biography, preference_claims=claims, last_profile_update_at=now)
        event = self._event(updated, claim, prior, next_conf, "explicit user correction changed confidence", provenance)
        return self._append_event(updated, event)

    def decay_stale_claims(
        self,
        biography: UserBiography,
        *,
        now: datetime | None = None,
        half_life_days: int = 90,
    ) -> UserBiography:
        now = now or datetime.now(timezone.utc)
        claims = []
        events: list[dict] = []
        for claim in biography.preference_claims:
            item = dict(claim)
            updated_at_raw = item.get("updated_at")
            updated_at = None
            if updated_at_raw:
                try:
                    updated_at = datetime.fromisoformat(str(updated_at_raw).replace("Z", "+00:00"))
                except ValueError:
                    updated_at = None
            if not updated_at:
                claims.append(item)
                continue
            age_days = max(0, (now - updated_at).days)
            if age_days < half_life_days:
                claims.append(item)
                continue
            prior = float(item.get("confidence", 0.5))
            decay = min(0.35, 0.08 * (age_days // half_life_days))
            next_conf = max(0.0, round(prior - decay, 3))
            item["confidence"] = next_conf
            item["stale_at"] = now.isoformat()
            claims.append(item)
            event = self._event(
                biography,
                str(item.get("claim", "unknown")),
                prior,
                next_conf,
                "staleness decay applied",
                CorrectionProvenance(source="staleness_decay", surface="biography_store", created_at=now, note=f"age_days={age_days}"),
                decay_applied=decay,
            )
            events.append(event.to_dict())
        return replace(
            biography,
            preference_claims=claims,
            profile_update_events=list(biography.profile_update_events) + events,
            last_profile_update_at=now if events else biography.last_profile_update_at,
        )

    def propose_repair(self, biography: UserBiography, correction: str) -> BiographyRepairPlan:
        now = datetime.now(timezone.utc)
        claim = self._guess_claim(correction)
        prior = biography.confidence_for(claim)
        suggested = max(0.0, round(prior - 0.20, 3))
        provenance = CorrectionProvenance(source="codex", surface="profile_repair", created_at=now, note=correction)
        prompt = (
            f"Profile repair candidate: lower `{claim}` confidence from {prior:.2f} to {suggested:.2f}. "
            "Apply, edit, or discard?"
        )
        return BiographyRepairPlan(prompt=prompt, candidate_claim=claim, suggested_confidence=suggested, provenance=provenance)

    @staticmethod
    def _guess_claim(correction: str) -> str:
        text = correction.lower()
        if "evening" in text:
            return "dismisses evening suggestions"
        if "prep" in text:
            return "accepts prep blocks near external calls"
        if "focus" in text:
            return "deep work"
        return correction[:80]

    @staticmethod
    def _event(
        biography: UserBiography,
        claim: str,
        prior: float,
        next_value: float,
        reason: str,
        provenance: CorrectionProvenance,
        decay_applied: float = 0.0,
    ) -> ProfileUpdateEvent:
        digest = hashlib.sha1(f"{biography.user_scope_id}|{claim}|{provenance.created_at.isoformat()}".encode()).hexdigest()[:12]
        return ProfileUpdateEvent(
            update_id=f"prof_{digest}",
            user_scope_id=biography.user_scope_id,
            claim=claim,
            prior_confidence=round(float(prior), 3),
            next_confidence=round(float(next_value), 3),
            reason=reason,
            provenance=provenance,
            decay_applied=round(float(decay_applied), 3),
        )

    @staticmethod
    def _append_event(biography: UserBiography, event: ProfileUpdateEvent) -> UserBiography:
        return replace(biography, profile_update_events=list(biography.profile_update_events) + [event.to_dict()])
