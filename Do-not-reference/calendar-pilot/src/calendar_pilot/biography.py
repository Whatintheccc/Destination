from __future__ import annotations

from dataclasses import replace

from calendar_pilot.types import RewardEvent, UserBiography


class BiographyStore:
    """In-memory biography updater for the reference implementation."""

    def update_from_reward(self, biography: UserBiography, reward: RewardEvent) -> UserBiography:
        fatigue = biography.notification_fatigue
        if reward.notification_dismissed or reward.ignored:
            fatigue = min(1.0, fatigue + 0.05)
        if reward.accepted or reward.explicit_useful:
            fatigue = max(0.0, fatigue - 0.02)
        return replace(biography, notification_fatigue=round(fatigue, 3))

    def add_claim(self, biography: UserBiography, claim: str, confidence: float) -> UserBiography:
        claims = list(biography.preference_claims)
        claims.append({"claim": claim, "confidence": max(0.0, min(1.0, confidence))})
        return replace(biography, preference_claims=claims)
