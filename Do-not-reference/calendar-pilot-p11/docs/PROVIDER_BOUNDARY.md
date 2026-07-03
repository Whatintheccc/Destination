# Provider Boundary

Provider adapters are transaction boundaries behind Swift. Python and Codex can request operations and inspect receipts; provider credentials and authoritative write truth stay behind the provider adapter.

## Five-method contract

```python
read_observation(user_scope_id, ...) -> RawCalendarObservation
preview(candidate) -> list[ProviderConflict]
commit(candidate, receipt, observation) -> ProviderMutationResult
verify(transaction, observation=None) -> ProviderVerificationResult
rollback(rollback_handle_id) -> ProviderMutationResult
```

`preview` is the provider's conflict truth. `commit` must be idempotent. `verify` is post-write readback: external ids exist or expected deletions are gone, times echo in local calendar truth, and rollback state is meaningful. `rollback` restores the provider state and must itself be verified.

## Required transaction facts

Provider transaction replay rows should include:

```text
provider_id
operation
status
idempotency_key
external_ids
created/moved/deleted_external_ids
rollback_handle_id
rollback_verified
local_time_echo_ok
errors
```

## Sandbox curriculum

Provider-backed self-play uses sandbox calendars and rate caps. Outside-sandbox writes are denial receipts, not exceptions. Real private-calendar dogfood begins only after:

```text
external ids present
rollback verified
idempotency suppresses duplicates
zero outside-sandbox mutations
provider errors are replay rows
cap-exceeded produces denial receipt
```

Google and Microsoft adapters remain explicit stubs until they can implement this full transaction contract.
