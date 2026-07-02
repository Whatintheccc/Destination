
# Chat-first frontend redesign

The backend dogfood loop remains the product engine:

```text
goal -> inspect -> candidate frontier -> simulate -> stage/commit/deny -> undo -> feedback/reward -> replay -> policy tuning -> next run
```

The previous UI made that loop visible as a control console. That was useful for dogfood operators, but it put internal machinery in the first viewport. This redesign keeps every mechanism available while making the first screen feel like a calendar assistant with machine-acting powers.

## Layout regions

- **Left sidebar:** conversations, new chat, recent dogfood runs, replay export entry point.
- **Center:** ChatGPT-style transcript with user goals and assistant action messages.
- **Bottom composer:** goal/request input plus a Swift-authority indicator.
- **Right inspector drawer:** authority scopes, profile repair, replay/export, self-play release gate, fixture/provider state, and debug trace.

## State model

`GET /api/state` returns the legacy dogfood panels plus the new product IA:

```text
chat.messages[]
chat.candidate_cards[]
chat.receipt_cards[]
sidebar.sessions[]
sidebar.recent_runs[]
inspector.authority
inspector.profile
inspector.replay
inspector.self_play
inspector.provider
inspector.debug
```

The old panels remain for compatibility and tests. The frontend now treats them as inspector/debug source material, not as the primary surface.

## API-to-chat mapping

- `POST /api/plans` adds a user goal message and an assistant plan message with compact candidate cards.
- `POST /api/candidates/{id}/simulate` produces an assistant simulation receipt.
- `POST /api/candidates/{id}/stage` produces a staged action receipt.
- `POST /api/candidates/{id}/commit` produces a committed/denied Swift receipt and unlocks undo/feedback affordances.
- `POST /api/undo` produces an undo receipt.
- `POST /api/feedback` creates a reward event and an assistant confirmation message.
- `POST /api/denials/explain` turns Swift denial reasons into follow-up controls.
- `GET /api/replay/export` stays in the inspector so dogfood debugging remains available but secondary.

## User-facing machine learning and acting flows

The center chat exposes only what a user needs to decide or repair:

- candidate future;
- model story;
- expected reward/regret/right-moment anatomy;
- stage/commit controls;
- denial explanation;
- undo and feedback after action.

The inspector exposes deeper dogfood state:

- authority grants/scopes;
- learned profile claims and repair;
- replay records/export;
- self-play release gate;
- provider/debug trace.

## Design boundary

Codex remains the user-facing operator. DiffusionGemma proposes candidate futures. Swift validates, writes, denies, rolls back, and audits. The frontend should reinforce that product story: chat asks and operates, action cards show what may change, and the inspector keeps the machinery inspectable without making it the first impression.
