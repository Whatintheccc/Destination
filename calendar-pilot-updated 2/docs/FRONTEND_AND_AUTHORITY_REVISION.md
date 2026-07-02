
# Frontend and authority-boundary revision

This revision follows the product direction: machine learning, machine acting, and self-play should be visible product flows, not hidden chat transcript details.

## Frontend

Added `frontend/static` plus `calendar_pilot.frontend` snapshot generation.

The surface exposes:

- calendar pressure map;
- candidate futures and reward/right-moment anatomy;
- acting queue with stage/commit/denial/rollback state;
- Swift-issued authority grants;
- self-play findings;
- biography repair.

Chat remains useful for explanations, but the primary app pathway is now a structured control surface.

## Authority fixes

The app now treats grant objects as kernel state, not portable payload authority.

```text
CodexToolCall carries authority_grant_id.
Swift/Python resolve authority_grant_id inside a kernel registry.
Embedded AuthorityGrant objects are ignored.
confirmed_by_user is required for commit and undo.
Undo checks registry, liveness, confirmation, scope, and rollback ledger.
```

## Acting semantics

Safe private writes can commit through Codex when simulation says confirmation is not required. Real social mutations still do not silently commit. Mixed packets no longer lose rollback handles when a staged sidecar accompanies a write.

## Verification added

New tests cover:

- embedded grant payload rejection;
- unconfirmed commit denial;
- safe private commit through Codex planner;
- mixed write + staged sidecar receipt semantics;
- frontend snapshot surfaces;
- Swift embedded-grant rejection;
- Swift confirmation enforcement for commit and undo.


## Swift IPC boundary

Added `CalendarPilotKernelServer`, a JSONL Swift process that holds the grant registry and undo ledger while Python sends only grant IDs and candidate packets. `SwiftKernelIPCClient` can issue grants, stage, commit, and undo through that process.

This is a control boundary, not provider integration. Google/Apple/Microsoft adapters still remain stubs; provider OAuth, provider tokens, sync truth, idempotency, external IDs, and conflict reconciliation should live behind Swift/provider adapters.
