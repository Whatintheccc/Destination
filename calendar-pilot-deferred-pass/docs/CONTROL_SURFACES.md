

# Control Surfaces

CalendarPilot acts. The control problem is therefore to bound bad action and make learning recoverable.

## Authority

Authority tiers are the primary blast-radius control. Tier 3 can create or move low-risk user-owned reversible blocks. Tier 5 is the first social-actuation tier.

## Reversibility

Auto-write requires a rollback handle or reversible action. Irreversible actions should be staged or require higher authority.

## Regret

Regret is a first-class predicted head and a measured reward penalty. The self-play `RegretAdversary` intentionally punishes high-confidence policies that get short-term acceptance but produce undo.

## Interruption

Right-moment prediction subtracts notification fatigue and bad response windows. The `FatigueAdversary` searches for policies that over-notify.

## Social risk

Affected people increase social risk. The Swift broker denies tier-5 social actuation unless explicitly granted.

## Replay

Every receipt/reward pair should enter replay for offline evaluation. Production versions should run candidate policies in shadow before changing authority tiers.
