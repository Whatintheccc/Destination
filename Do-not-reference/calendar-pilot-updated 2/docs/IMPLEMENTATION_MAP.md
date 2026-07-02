
# Implementation Map

This map shows where the requested framework lands in the repository.

| Framework requirement | Repo location |
|---|---|
| Agentic calendar optimizer | `README.md`, `calendar_pilot.app`, Swift demo |
| Raw-context modeling | `RawCalendarObservation`, sample fixtures, policy inputs |
| Persistent user biography | `UserBiography`, `BiographyStore` |
| Proactive intervention | `RightMomentModel`, Codex explanations |
| Calendar write authority | `WriteAuthorityBroker`, `ActionMaterializer`, `CalendarKernel` |
| Right-moment prediction | `diffusiongemma/right_moment.py` |
| Reward-driven recommendation | `diffusiongemma/reward.py`, candidate expected reward heads |
| Self-play | `diffusiongemma/self_play.py` |
| Codex layer | `codex/agent.py` |
| DiffusionGemma layer | `diffusiongemma/policy.py` |
| Swift kernel | `packages/CalendarPilotKernel` |
| Replay/offline learning | `replay.py`, `scripts/train_offline_policy.py` |
| JSON contracts | `contracts/*.schema.json` |
