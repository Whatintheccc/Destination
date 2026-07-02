

# Safety and Contract Pass

This revision makes the Codex executive path structurally safer before adding more provider or model intelligence.

The central change is that authority is no longer a caller-supplied integer. Swift now issues `AuthorityGrant` objects, and the Python/Codex side can only carry those grants back to Swift.

```text
AuthorityGrant = max tier + scopes + expiry + confirmation provenance + issuing kernel
```

Codex can request. Swift grants or denies. Provider writes remain Swift-owned.

## P0 fixes landed

### Swift-issued authority grants

`AuthorityGrant` is now a canonical cross-runtime contract in Python, JSON Schema, and Swift. It includes:

```text
grant_id
user_scope_id
max_authority_tier
scopes
issued_at
expires_at
confirmation_provenance
issued_by
confirmed_by_user
```

Python/Codex can no longer pass `granted_authority_tier=3` and receive actuation authority. The Swift kernel stub and Swift package reject out-of-band authority before materialization.

### Lossless Swift JSON payloads

Swift `JSONValue` now supports recursive objects and arrays instead of preserving only scalar leaves. This lets Codex tool calls and receipts round-trip rich nested payloads such as candidates, grants, staged packets, denial receipts, and profile patches.

### Codex-first app flow

The demo path no longer uses the old direct path:

```text
policy.generate_candidates -> kernel.authorize_and_materialize -> codex.explain
```

The default path is now:

```text
Codex inspect_week
-> generate_candidate_frontier
-> compare_candidates
-> simulate_action_program
-> stage_action_packet
-> optional request_commit
-> replay causal trace
```

The direct kernel call still exists as a primitive and test surface, but not as the main app pathway.

### Staging semantics

Receipts now distinguish:

```text
simulated
stageable
requires_confirmation
denied
committed
no_op
```

A staged packet can no longer look successful when Swift denied it. Tool status, receipt `stage_state`, denial reason, and Swift receipt ID are explicit.

## P1 fixes landed

### Contract parity

Python dataclasses, JSON schemas, and Swift `Codable` contracts now cover the canonical fields for:

```text
AuthorityGrant
CandidateCalendarAction
CalendarActionReceipt
RawCalendarObservation
RewardEvent
CodexToolCall
CodexToolReceipt
```

Swift `RawCalendarObservation` now mirrors Python/schema fields such as tasks, device context, notification history, and prior actions. Swift `RewardEvent` now mirrors Python reward heads.

### Causal replay

Replay records now include:

```text
record_id
trace_id
causal_parent_id
```

The training loop can consume the deliberation path: tool calls, tool receipts, candidate decisions, Swift receipts, rewards, self-play episodes, denials, and adversary findings.

### Adversary finding double-count fix

Replay still stores full episode payloads and normalized `adversary_finding` rows, but summary counting uses only normalized rows. Embedded findings no longer double-count.

### Policy tuning order

Policy tuning is applied before right-moment decisions, so tuning changes affect both candidate ranking and timing decisions. The focus-mode interruption penalty no longer depends on a right-moment value that has not yet been computed.

### Interval union pressure

Occupied workday minutes now use interval unioning instead of summing event durations. Overlapping events no longer inflate schedule pressure and distort open-slot/right-moment behavior.

### Self-play authority boundary

Self-play no longer escalates tier `0` to tier `3`. If no grant exists, actuation is denied. When self-play needs write authority, it uses a Swift-issued grant with explicit provenance.

## Provider boundary

Provider interfaces remain explicit. Real OAuth/read/write/sync is intentionally not implemented in this pass.

```text
Python proposes.
Swift/provider adapters own real sync and writes.
Python never holds provider tokens.
```

The next provider milestone should add a fixture-backed Google or Apple adapter with external IDs, idempotency, conflict truth, retries, and rollback receipts before real OAuth.

## Control-theory posture

Privacy is not the main doctrine in this branch. The retained privacy-like boundaries exist because they are control surfaces:

```text
scoped grants limit blast radius;
expiry prevents stale authority;
confirmation provenance improves auditability;
undo ledger supports recovery;
provider-token separation prevents Codex/Python from bypassing Swift;
causal replay lets learning see why actions were denied or repaired.
```

## Validation

Expected checks:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
swift test --package-path packages/CalendarPilotKernel
PYTHONPATH=src python3 -m calendar_pilot.app demo --observation data/sample_calendar.json --self-play 2 --replay-out runs/replay.jsonl --commit
PYTHONPATH=src python3 scripts/train_offline_policy.py --replay runs/replay.jsonl --out runs/offline_policy_report.json --tuning-out runs/policy_tuning.json
```
