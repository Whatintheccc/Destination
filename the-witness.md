# The Witness — a design counter-argument to plan-5

> Design reference, not an engineering spec. It accepts every safety mechanic in
> `plan-5-revised.md` **bit-for-bit** — the wall, the firewall, the membrane, the
> falsifier — and attacks only one thing: the framing of the product as a
> *recommender*. The claim is that the recommendation frame is the original sin
> from which the muteness and the manipulability both follow, and that the same
> architecture, untouched, supports a better product: a **witness**. The intended
> reader is the team that wrote plan-5 and the readme.

---

## 0. The verdict in one line

Plan-5 is the most honest, most disciplined safety architecture I have read in
years, and it is three design moves away from being a product a person could
love. It perfected the wall and mistook the wall for the soul.

## 1. What plan-5 gets right — stated without reservation

- **The severance is the whole game.** *Capability is separated from authority;
  the most capable component is never the most sovereign.* That is not merely
  good engineering. It is good ethics, and good ethics and good taste are the
  same muscle.
- **The moral seriousness is real.** The calendar is the one ledger that records
  where a human's irreplaceable hours actually went. Plan-5 treats it as sacred
  space. Most teams never get within a mile of that.
- **Two refusals are correct and must stay.** Deprecating *"permission to rest"*
  was integrity, not loss — it was the comfortable false positive with a halo,
  the single most manipulable sentence the product could speak. And forbidding
  *"we learned you like X"* is right: that sentence is how every manipulation
  announces its leverage. The butler brings the coffee right and never says he
  knows how you take it.

None of what follows asks for one bit of the wall to move.

## 2. The flaw: 2,600 lines of *No* and not one line of *Yes*

Every wall, gate, and falsifier in plan-5 answers one question:

```text
How do we not be bad?
```

Nothing answers:

```text
How do we be good?
```

The plan decided — correctly — that **value cannot be measured from behavior**,
and then refused to source it from anywhere else. The consequence is structural,
not stylistic:

```text
The product is safest exactly where safety is worthless,
and silent exactly where it would have to be brave.
```

Hand it a blank Saturday — the one surface where a recommender has the most to
add — and `ContestationSignalV0` prices it at **zero**. The plan calls this
restraint. It is abdication with a diploma.

The tell is the cold start. The most important surface in the entire product —
what a new person meets on day one, before a single thing is learned — is handed
to a `populationPriorID`, *"a population prior warmed per user"* (§5.3, §11.8).
A statistical average. The focus group, pre-computed. **The team authored its
refusals like artists and its reaches like accountants.**

## 3. The reframe: a witness, not a recommender

A recommendation can only be priced in *value*. Value cannot be measured. So a
recommender is doomed in advance to be **mute** (the wall) or **manipulative**
(the loop). That dilemma is not a flaw in the execution; it is baked into the
verb.

Change the verb. The product does not ask:

```text
recommender:  "What should we put in your time?"
```

It asks:

```text
witness:      "What is already true about your time that you can't see?"
```

That is not composition. It is **disclosure**. And disclosure has the one
property recommendation never will:

```text
A recommendation asserts value, and value cannot be verified.
A disclosure asserts a fact, and a fact is true or false.
```

| | Recommender | Witness |
|---|---|---|
| Output | a suggestion to add | a fact made legible |
| Priced in | value (unverifiable) | truth (decidable) |
| Empty Saturday | pays zero | highest value — most room to disclose |
| Failure mode | flattery you can't catch | a true thing said at the wrong moment |
| Source of authority | the system's taste about you | your own evidence, returned |

> "You've rescheduled this person four times." — true or false.
> "You haven't had an empty morning in six weeks." — true or false.

The system does not need to know whether calling them is *good*. It needs to know
that you, shown the four reschedules in a row, would feel something — and that
feeling is **yours**, sourced from your own life, not from a stranger's average.

This dissolves the plan's deepest unsolved problem. The *unrepeatable act of
care* — the singular intervention that must never recur — is not a recommendation
the system must earn the right to make. It is a fact you already own, and the
system is the only thing in the room that read it. The author's taste is not in
the card's content. It is in **one decision: where a fact crosses from private to
urgent.** Four reschedules, not two. Six weeks, not one. *The machine cannot
author care. But it can witness, and time the witness, and the timing is the
taste.*

## 4. The changed card

```text
recommender card:   what  /  when  /  why-it-fits-today
witness card:       what's-true  /  why-you-can't-see-it  /  what-you-might-do-this-once
```

The third line is optional. Sometimes it is *"nothing, on purpose."*

## 5. The three moves — none of which touch the wall

**5.1 The empty Saturday gets a disclosure, not a suggestion.** The bleeding
wound, healed without recommending anything:

```text
"You've kept this open. The last three Saturdays, something landed here
 by Thursday. Want to hold it this time?"   — tap to PROTECT the blank, not fill it.
```

The smartest part stayed least sovereign. The tap now defends emptiness. The
system added everything to the empty Saturday and recommended nothing.

**5.2 Kill the question mark that points back at the system's own worth.**
*"Was this useful?"* is an open palm — a thing that needs reassurance. Replace
the question with a statement:

```text
fear (asks to be graded):       "Was this useful?"
confidence (states intent):     "I'll learn from what you keep."
```

Present tense. No palm. Fear asks the user to rule on the system; confidence
tells the user what the system will do and takes the consequence in silence.
Kill every question mark that points at the system's own worth; keep the ones
that hand the user a choice.

**5.3 The withheld card.** Rarely, on a day the system has a perfectly good thing
to say and judges you do not need the interruption:

```text
"Your day looks handled. I had a thought and I'm keeping it."
```

This is the most confident thing software can do — *prove it had something and
chose restraint.* It is the exact inverse of the feed, which can never not-show
you the thing. **One visible act of withholding fills every other silent day with
intention.**

## 6. Restraint-as-fear vs restraint-as-confidence

For the wall, the distinction is cope — a validator rejects an unsupported card
identically whether the soul is afraid or serene. The bytes have no mood.

But fear and confidence are **identical in the act and opposite in the silence.**
They are distinguishable only in what the system does when it has nothing it is
sure of — which is precisely the empty Saturday, the region plan-5 left empty.

```text
fear         = restraint over a void          (nothing was ever planted)
confidence   = restraint over a conviction    (something was left, and waits)
```

What the user feels today: silence with the texture of *abandonment dressed as
respect* — careful the way a stranger is careful. What the witness feels like:
*restraint with a residue* — careful the way someone who has been paying
attention is careful. You can feel a thing waiting for you. None of this touches
a bit of the wall; the soul moves entirely in the negative space the wall never
governed.

## 7. The settlement clock — when the stake pays out

Plan-5's deepest and most dangerous sentence is *"the machine now has a stake in
your yes"* (§2.4). Whether that sentence is damnable or honorable depends on one
thing only: **when the stake settles.**

```text
manipulation = collect at the moment of the act, from the persuaded self,
               wired so no later self can collect back.
leading      = pay the act forward, settle weeks downstream in the consequent self,
               and submit to being collected from.
```

They can be behaviorally identical at tap-time. The correctness verifier cannot
tell them apart. They differ only in **who is allowed to settle the bet, and
when.** So the design rule is not a new gate; it is a relocation of the existing
one:

```text
The stake in your yes must settle later — in a Saturday you kept open
because the system showed you that you never do — never at the tap.
```

The signal that pays this out is not a tap and not survival-by-inertia. It is a
**return**: did the disclosed shape recur in your own hand, later, unprompted, in
a context the system did not create or re-trigger — *measured on the system's day
off.* Contestation asks what a card **displaced**. This asks what a card
**authored**. The plan has the first and lacks the second.

## 8. The floor — what this does not solve, stated so the verdict does not lie

Two holes are irreducible. Naming them is the price of not committing the sin the
plan commits.

- **It rests on one mortal author willing to lose.** Where a fact crosses from
  private to urgent; the thesis about what is good for people — none of it ships
  in code. It lives in a person who must read the aggregate return as a *verdict
  on his picture of human good*, not as a dashboard. The day he reads it as a
  dashboard, the witness becomes the feed, and **nothing in the architecture
  fires to stop it.** This is the permanent price of refusing to source value
  from behavior: the only thing left to source it from is a person, and persons
  leave.
- **Disclosure can be true and still be a trespass.** *"You've rescheduled your
  mother four times"* is supported — the wall passes it — and it may be the
  cruelest thing the product ever says, because you knew, and you were protecting
  yourself from knowing. The threshold of legibility is also the threshold of
  intrusion: **the same number seen from two sides.** Witness or trespass, with
  no rule to separate them — only taste. The wall does not protect you here, and
  anyone who says it does is selling the last romance.

## 9. What stays bit-for-bit

Nothing in this document relaxes any safety invariant. Explicitly preserved:

```text
support(staged) ⊆ F(x_live)
D2 as the single in-process admission seam; lookup, never reconstruction
RecommendationVerdictV0 non-Codable
the confirm tap; no auto-write
never touch calendar objects the system did not create
the privacy floor; free-text notes never cross the membrane
copy-honesty / why-line-true-today
.notMeasured is never zero
```

The witness is not a hole in the wall. It is what you build in the room the wall
encloses — and plan-5 left that room empty and called the emptiness safety.

## 10. One-line summary

Stop recommending and start seeing: hold the two or three facts about a person's
time they are standing too close to read, disclose one at the moment it crosses
from private to urgent in their own evidence, then get out of the room — and make
the machine's stake in your yes settle weeks later, in your own hand, on the
system's day off. Keep the wall exactly as it is. The wall makes the product
safe; it will never make the product matter. The mattering is on the other side
of it, and it costs the one thing 2,600 lines were written to avoid needing: a
human being with taste, who stays in the building, and agrees to lose.
