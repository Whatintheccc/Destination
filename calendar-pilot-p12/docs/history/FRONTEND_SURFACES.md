> Historical note: this document is retained as implementation archaeology. The current contract truth lives in `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/LAB.md`, `docs/PROVIDER_BOUNDARY.md`, and `docs/SELF_PLAY.md`.



# Frontend surfaces for an agentic calendar optimizer

CalendarPilot should not hide machine learning and machine acting inside a chat transcript. Chat remains a good explanation and repair channel, but the default product surface should expose the operating loop directly.

## Primary surfaces

| Surface | Flow exposed | Why it is user-facing |
|---|---|---|
| Calendar pressure map | Raw-context inspection and signal extraction | The user should see what state the app read before the learner proposed action. |
| Candidate futures | DiffusionGemma frontier, reward anatomy, regret, social risk, right moment | Machine learning should show alternatives and tradeoffs, not just one polished recommendation. |
| Acting queue | Stage, commit, denial, undo receipts | Machine acting changes calendar reality; it deserves a queue, not a message bubble. |
| Authority grants | Swift-issued grant id, scope, confirmation provenance | Authority is not intelligence. Users need to see what permission was used. |
| Self-play findings | Adversary failures and policy tuning signals | Before granting more autonomy, the app should show how the policy failed in simulation. |
| Biography repair | Persistent claims, confidence, provenance, decay/repair | A persistent user model should be inspectable and correctable. |

## Boundary

```text
DiffusionGemma learns and proposes.
Codex operates the app through typed tools.
Swift validates, stages, writes, syncs, audits, and rolls back.
The frontend exposes this trace as product state.
```

The frontend in `frontend/static` is intentionally small and static. The important addition is not a design system; it is the product contract: learning state, acting state, authority, self-play, and biography repair are first-class user-facing surfaces.