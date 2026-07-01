# Self-play

The self-play implementation lives in `src/calendar_pilot/diffusiongemma/self_play.py`.

It simulates:

- calendar state evolution;
- user acceptance/rejection/undo behavior;
- notification fatigue;
- social risk;
- regret after auto-write;
- adversarial scenarios.

The default adversaries are lightweight but intentionally shaped around control failures:

- `ConflictAdversary` injects overlapping events;
- `FatigueAdversary` penalizes notification-heavy policies;
- `RegretAdversary` punishes high-confidence low-reversibility writes;
- `EngagementAdversary` detects policies that get opens while increasing regret.

Self-play is not a production trainer by itself. It is the harness around which offline RL, DPO, or policy-gradient training can be added.
