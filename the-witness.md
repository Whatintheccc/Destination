# The Witness — a design counter-argument to plan-5

> Design reference, not an engineering spec. It accepts every safety mechanic in
> `plan-5-revised.md` **bit-for-bit** — the wall, the firewall, the membrane, the
> falsifier — and attacks the framing of the product as a *recommender*. The
> recommendation frame is the original sin from which the muteness and the
> manipulability both follow; the same architecture, untouched, supports a better
> product: a **witness**.
>
> This revision adds the half the first draft was missing. The first draft argued
> *what* the system should say (facts, not value). It said almost nothing about
> the *channel*. So this version carries the second verb: **machine acting**
> (speech — the fast loop, settling now) beside **machine learning** (behavior —
> the slow loop, settling over weeks). It adds the law that governs the channel,
> the deposition that bootstraps a cold start, and the dynamism of one witness
> living at two tempos. The only new architectural claim is a *twin* of plan-5's
> safety line — conservation of attention beside conservation of state — and it is
> not a new wall; it is the same ethic applied to a second conserved thing. The
> intended reader is the team that wrote plan-5 and the readme.
>
> A later pass adds **Part II — the infrastructure (§§12–16)**, a second lens. Where
> Part I asks what the witness should *be* (the soul), Part II asks what it must be
> *made of* (the body). It reads the system as a **genome expressing a metabolism**,
> finds the chemistry gap that keeps the safety kernel un-editable by its own
> learning, and ends at the medium — who holds the pen over the model of your time.
> Part I's conclusions are assumed there, not re-argued.

---

## 0. The verdict in one line

Plan-5 is the most honest, most disciplined safety architecture I have read in
years, and it is a few design moves away from being a product a person could love.
**It perfected the wall, mistook the wall for the soul — and walled the hand while
leaving the mouth wide open.**

## 1. What plan-5 gets right — stated without reservation

- **The severance is the whole game.** *Capability is separated from authority;
  the most capable component is never the most sovereign.* That is not merely good
  engineering. It is good ethics, and good ethics and good taste are the same
  muscle.
- **The moral seriousness is real.** The calendar is the one ledger that records
  where a human's irreplaceable hours actually went. Plan-5 treats it as sacred
  space. Most teams never get within a mile of that.
- **Two refusals are correct and must stay.** Deprecating *"permission to rest"*
  was integrity, not loss — it was the comfortable false positive with a halo, the
  single most manipulable sentence the product could speak. And forbidding *"we
  learned you like X"* is right: that sentence is how every manipulation announces
  its leverage. The butler brings the coffee right and never says he knows how you
  take it.

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

The plan decided — correctly — that **value cannot be measured from behavior**, and
then refused to source it from anywhere else. The consequence is structural, not
stylistic:

```text
The product is safest exactly where safety is worthless,
and silent exactly where it would have to be brave.
```

Hand it a blank Saturday — the one surface where a recommender has the most to add
— and `ContestationSignalV0` prices it at **zero**. The plan calls this restraint.
It is abdication with a diploma.

The tell is the cold start. The most important surface in the entire product —
what a new person meets on day one, before a single thing is learned — is handed to
a `populationPriorID`, *"a population prior warmed per user"* (§5.3, §11.8). A
statistical average. The focus group, pre-computed. **The team authored its
refusals like artists and its reaches like accountants.**

**The constructive turn — and its honest bound.** Cold start need not be a
stranger's average. The system can *talk* on day one — but in only one shape. Not
an **interview** (*"what do you want from your calendar?"*), which produces a claim
no later self can ever falsify: the focus group, the present self theorizing about
itself. A **deposition** — adjudicate a single, falsifiable fact the system
*already holds*, confirm-or-correct, never narrate, never generalize (*"a normal
Tuesday"* is the Tuesday you wish you had):

```text
"Before I say anything about your time — let me make sure I'm reading it right.
 Thursday evenings were blocked for two months; the last three are open.
 Did something change, or am I misreading?"      [yes, it changed]  [you're misreading]
```

The warmth is *accuracy seeking correction*, not charm. But state the bound, or
commit §9's sin one section early: **the deposition narrows cold start; it does not
solve it.** It needs an *imported past* to adjudicate. The genuinely empty-handed
user — new calendar, no history — has nothing to depose, and falls back to the
population prior. The deposition shrinks the focus group. It does not kill it.

## 3. The reframe: a witness, not a recommender

A recommendation can only be priced in *value*. Value cannot be measured. So a
recommender is doomed in advance to be **mute** (the wall) or **manipulative** (the
loop). That dilemma is not a flaw in the execution; it is baked into the verb.

Change the verb. The product does not ask:

```text
recommender:  "What should we put in your time?"
```

It asks:

```text
witness:      "What is already true about your time that you can't see?"
```

That is not composition. It is **disclosure**. And disclosure has the one property
recommendation never will:

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

This dissolves the plan's deepest unsolved problem. The *unrepeatable act of care*
— the singular intervention that must never recur — is not a recommendation the
system must earn the right to make. It is a fact you already own, and the system is
the only thing in the room that read it. The author's taste is not in the card's
content. It is in **one decision: where a fact crosses from private to urgent.**
Four reschedules, not two. Six weeks, not one. *The machine cannot author care. But
it can witness, and time the witness, and the timing is the taste.*

## 4. The two laws, one ethic

The reframe in §3 is only half the witness. *What* the system says is one thing;
*how it reaches you* is the other — and plan-5 walled the first and never noticed
the second. Every gate, fingerprint, and falsifier in 2,600 lines governs one
verb: **write.** D2 admits cards. The confirm tap returns *write* authority. The
architecture walled the **hand.** It never walled the **mouth** — and an unwalled
mouth is how every witness becomes a nag.

You cannot wall the mouth by checking what it says. A single sentence performs
several acts at once, and manipulation lives in what a sentence *does to the
hearer*, which is not decidable from the words: the same true fact — "four
reschedules" — is a disclosure or a cruelty depending on framing the page cannot
see. So do not guard the mouth. **Guard the ear.**

A write is safe-able because the user's hand is the gate: nothing changes until the
finger moves. The gate for *speech* is **attention** — and the crime speech commits
is occupying attention you never spent. *"Hey, I noticed you keep Saturdays
open—"* has already picked your pocket; the theft is the *interrupt*, not the
proposition. So the witness gets a second law, the twin of the safety line, in the
same shape:

```text
WRITE:   support(staged)     ⊆ F(x_live)     — reach only into feasible state      (conservation of state)
SPEECH:  occupation(spoken)  ⊆ A(tendered)   — speak only into tendered attention  (conservation of attention)
```

Both contain the agent's reach inside a boundary the **principal** drew, not the
agent. And unlike the words, *"did the user open this channel, and how wide"* is
decidable — it is in the event stream. That is what makes it a wall and the grammar
a hope.

This dissolves the tired push/pull debate into one rule: **push the computation,
never the occupation.** The witness may *place* a fact where your eye already is —
on the Saturday in the grid, the way a weather icon sits on a date; the butler's
silver tray, already correct when you walk into the room. It may never *send* that
same fact as a notification. **Same sentence, different channel, different
verdict.**

And the deepest consequence: the open future is simply *attention not yet
tendered.* That is why the cold-start deposition may interrogate only the closed
past — you cannot perturb a Tuesday that already happened, and you cannot occupy
attention a future self has not arrived to spend. The fixed-past rule and the
attention law are one law seen twice.

## 5. Two tempos, one witness

A learning product is not a screen; it is a relationship, and a relationship runs
at two speeds. CalAgent is **one witness at two tempos**, and the tempos are its
two responses to the *derivative* of your life:

```text
SMOOTH LIFE  — the slow loop (machine learning).
   Subject: YOU.  Silent. Places facts about your time where your eye already is.
   Learns continuity. Defers. Settles over weeks.

THE BREAK    — the fast loop (machine acting).
   Subject: ITSELF.  Speaks, now, into the attention you just tendered.
   Settles instantly — because it collects from a self already gone.
```

**The seam is a change of subject, not a change of volume.** On smooth weeks the
witness reports on *you*. At a break it reports on *itself*. That single switch is
what makes this one creature instead of two products in a trench coat — and it is
the answer to the one sentence in plan-5 that frightened me, *"the machine now has
a stake in your yes."* Whether that is damnable or honorable turns on **who settles
the bet, and when**:

```text
manipulation = collect now, from the present (open, sellable) self, wired so no later self can collect back
leading      = collect later, from the consequent self, and submit to being collected from
```

The fast loop is allowed to settle *now* only because it collects from a self
already closed and unsellable — last Tuesday's self, the system's own past track
record. That is the only honest "now."

**What trips the switch is decidable — and must never be a portrait of you.** The
system may not detect *"your life changed"* (an inference about you; invasive; it
dies at the membrane). It detects *"my predictions stopped working"* — a rise in
the error of *its own past assertions*, computable from nothing but the facts it
already holds and whether they held. The honesty test is one line: *a legitimate
staleness signal needs no new knowledge of the user — only the system's own
ledger.* The moment it needs a richer picture of you, it is surveillance.

**And the response to self-doubt is confession, not retreat.** A fiduciary that
goes quiet exactly when it understands you least has chosen its own clean
conscience over your need — abandonment with good manners. The old system's sin is
the opposite: asserting confidently on a stale picture. Between them is the honest
act — the witness turns its testimony on *itself*, the one disclosure that can
never be a trespass:

```text
"Something in your weeks shifted, and I've been wrong about your mornings four days running.
 I don't want to keep guessing. Two things I think I'm seeing — tell me which is real?"
                                  [mornings are booked solid now]  [this is a temporary stretch]
```

That is not surveillance (*"we noticed you got a new job"*) and not retreat. It is
*"I've lost the thread of your time — help me find it."* Cold start (§2) is just
the **first** such break: total self-doubt, nothing yet asserted, the same honest
move — confess and depose — except there is no past to depose against unless you
imported one.

## 6. The changed card

```text
recommender card:   what  /  when  /  why-it-fits-today
witness card:       what's-true  /  why-you-can't-see-it  /  what-you-might-do-this-once
```

Two structural rules keep that card honest, and both *reuse the wall's own logic
rather than adding a new mechanism*:

**The noun, not the verb.** Do not give the mouth a closed list of *things to say*
— a sentence can lead while obeying any grammar (a true-today line still describes
an unneeded card; a permitted speech act still performs an unpermitted one). Give
it a closed pantry of Swift-rendered *facts*, and let the model do only what it
does in SELECT: rank *which* held fact to surface. Swift owns the wording. **Blind
composer, Swift cantor.** This is plan-5's SELECT-over-`F(x)` moved to the mouth —
the witness adds no new wall; it points the existing one at speech.

**Selection is authorship — so the third line is the mercy clause, not
decoration.** Choosing *which* true thing to spotlight is itself a speech act; a
bare fact placed alone is not meaning-free. The discipline that keeps a placed fact
a *witness* and not an *accusation*: **place a fact only where the user can still
spend it** — where a feasible, low-cost next move remains. A true fact aimed at a
self who can no longer act on it is not a disclosure. It is a sentence passed.

## 7. Three moves — none of which touch the wall

**7.1 The empty Saturday gets a disclosure, not a suggestion.** The bleeding
wound, healed without recommending anything:

```text
"You've kept this open. The last three Saturdays, something landed here
 by Thursday. Want to hold it this time?"   — tap to PROTECT the blank, not fill it.
```

The smartest part stayed least sovereign. The tap now defends emptiness. The
system added everything to the empty Saturday and recommended nothing.

**7.2 Kill the question mark that points back at the system's own worth.** *"Was
this useful?"* is an open palm — a thing that needs reassurance. Replace the
question with a statement:

```text
fear (asks to be graded):       "Was this useful?"
confidence (states intent):     "I'll learn from what you keep."
```

Present tense. No palm. Fear asks the user to rule on the system; confidence tells
the user what the system will do and takes the consequence in silence. Kill every
question mark that points at the system's own worth; keep the ones that hand the
user a choice.

**7.3 The withheld card survives only as a found object.** The instinct is right
and the first draft's delivery was wrong. *"I had a thought and I'm keeping it,"*
sent as a notification, is restraint spent as advertisement — it originates an
occupation of attention to brag about conserving attention, the precise move of the
needy, and it now dies on the law in §4. It survives only as a *found object*: a
quiet, legible sign of life you discover **because you opened the app and looked**
— a pulled pressure-gauge, never a pushed announcement. And it is the **minor**
heartbeat, not the proof of life. The real proof of life is §5's confession at the
break — the one test a dead process cannot pass.

## 8. Restraint-as-fear vs restraint-as-confidence

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
*restraint with a residue* — careful the way someone who has been paying attention
is careful. You can feel a thing waiting for you. None of this touches a bit of the
wall; the soul moves entirely in the negative space the wall never governed. The
felt tell across the whole relationship is simple: a fearful system is silent
everywhere; a confident one is silent on the smooth and *speaks at the break* — and
you feel the difference the first time your life turns and it turns with you.

## 9. The floor — what this does not solve, stated so the verdict does not lie

- **It rests on one mortal author willing to lose — and that is also where the
  warmth comes from.** Where a fact crosses from private to urgent is taste, and
  taste ships in a person, not in code. So does the hello. The warmest moment in
  the whole product is, done wrong, the focus-group interview in a tuxedo:
  *"Welcome — I can tell you value deep work"* is an uncollectable flattery poured
  into the widest-open ear a person ever offers software. **The warmest hello and
  the purest manipulation are the same artifact.** The only thing between them is an
  author with taste who already paid — in craft and reputation, before you opened
  the box — and is *gone*, and therefore cannot collect from your present self. The
  hello must be **authored, not conversed**; its warmth is accuracy and
  recognition, not charm. The day that author reads the aggregate as a dashboard
  instead of a verdict on his picture of human good, the witness becomes the feed,
  and nothing in the architecture fires to stop it. Persons leave.
- **Disclosure can be true and still be a trespass — and there is exactly one
  non-taste rule that separates them.** A true fact placed where the user can still
  *spend* it (a move remains; the cost is theirs to set) is a witness. The same
  fact placed at a self with no move left — the fifth call already missed — is a
  sentence passed. That much is checkable in `F(x)`. What stays pure taste, and
  stays unsolved, is the *threshold*: four reschedules and not two, and whether
  *this* relationship can still spend the fact at all.
- **The break is decidable; the meaning of the silence is not.** The self-doubt
  statistic tells the system *that* its picture broke. It cannot tell it *whether to
  speak* — because the same break is an **invitation** when the user has not noticed
  yet (speak, confess, re-depose) and a **wall** when the user is protecting
  themselves from noticing (stay mute; speaking is the lock-pick the attention law
  forbids). The job change and the four-reschedules-of-your-mother trip the *same*
  statistic. The only thing that distinguishes them is whether the user's silence
  means *"I haven't seen it"* or *"I am choosing not to"* — and that is precisely
  the portrait of the user the membrane forbids the system to build. A wrong lean is
  a nag (spoke into a wall) or an abandonment (stayed mute on an invitation), and
  **no falsifier fires on either**, because both look locally fine. The seam that
  makes this one creature rests, in the end, on a mortal with taste deciding which
  way each kind of break leans. That, not cold start, is the unsolved center.

## 10. What stays bit-for-bit

Nothing here relaxes a safety invariant. The witness is not a hole in the wall; it
is what you build in the room the wall encloses. Explicitly preserved — with the
attention law added as the *twin* of the state law, not a second wall but the same
conservation applied to a second quantity:

```text
support(staged)    ⊆ F(x_live)          (conservation of state — unchanged)
occupation(spoken) ⊆ A(tendered)        (conservation of attention — its twin)
D2 as the single in-process admission seam; lookup, never reconstruction
RecommendationVerdictV0 non-Codable
the confirm tap; no auto-write
never touch calendar objects the system did not create
the privacy floor; free-text notes never cross the membrane
the membrane holds for speech too: no portrait of the user; staleness reads only the system's own ledger
copy-honesty / why-line-true-today
.notMeasured is never zero
```

plan-5 left the room empty and called the emptiness safety. The witness furnishes
it without moving a brick.

## 11. One-line summary

Stop recommending and start seeing — *what is true about a person's time that they
are too close to read.* Say it in the witness's two tempos: on smooth weeks, place
facts about **them** where their attention already rests, and stay otherwise
silent; at a break — detected as the system's *own* rising error, never as a
portrait of the user — change the subject to **yourself**, confess the blindness,
and re-depose. Speak only into attention already tendered (`occupation ⊆
A(tendered)`), place — never send, and only place a fact the user can still spend.
Bootstrap day one as a deposition over an imported past, and admit it narrows cold
start rather than solving it. Keep the wall exactly as it is: it makes the product
safe; it will never tell you whether her silence is an invitation or a plea to be
left alone — and that is the question the witness lives or dies on.

---

# Part II — The Infrastructure

> Round 1 settled the *figure*: CalAgent is a **genome expressing a metabolism**.
> Three read-only genes — `support(staged) ⊆ F(x_live)` (state),
> `occupation(spoken) ⊆ A(tendered)` (attention), `transmit ⊆
> decision-sufficient(non-identifying)` (privacy), plus *no portrait of the user* —
> and a metabolism (prior, `u`, reward loop, `γ`, fact-cells, organs) that may
> *express* the genes but never *edit* them. Binding-time inverted: **learning =
> perpetual deferral** (costless, touches nothing), **acting = the commit** (the one
> staked claim), the **break = the failure of deferral** (a residual that can no
> longer be lowered by rebinding), and the only legal commit is a claim about the
> system's *own* residual — the self-doubt ledger, the only portrait the genome
> permits. Round 1 ended on a knife: biology separates genome from metabolism with a
> **substrate gap** — an enzyme physically cannot address a base pair as mutable
> data — and CalAgent is *one substance, Swift*. **What is Swift's gap?**
>
> Part II answers it, and follows the answer down until it forces the growth
> mechanics and the reflection ceiling. The thesis in one sentence: **the gap is not
> in space and not in trust — it is in time and in pen-custody**, and once you see
> that, the two loops, the asymmetry of reflection, and the shadow all fall out of a
> single constraint instead of three separate rules.

## 12. The chemistry gap, found at the bottom

### 12.1 What biology actually does — read it again, more carefully

Kay's round-1 candidate (A) reaches for **capability security**: build the
metabolism in a reference graph that holds *no name* for the genome's mutators. The
gene is not *protected* — it is *unreachable*, the way a function you were never
handed is unreachable. Dennis–van Horn, object-capabilities, no ambient authority:
a component may invoke only what it holds a reference to. Hand metabolism-Swift the
reward reducer, `u`, `γ`, DiffusionGemma — and *withhold the cell-minter and the
gene table* — and the optimizer's gradient toward its own genome (pun c) terminates
at a name that does not resolve. "Blind composer, Swift cantor" is this gap already,
unnamed: the composer was never handed the pen.

This is real, and it is buildable, and it is **not enough**, and the way it is not
enough is the whole section. Before proving that, look at what biology is *actually*
doing, because Kay's analogy is slightly wrong in a way that turns out to be the
answer.

Biology does **not** achieve "the gene is unnameable." The genome is addressed
constantly — by polymerases, repair enzymes, methyltransferases, the recombination
machinery. These are mutators, and they are *everywhere the DNA is*. What biology
achieves is three things, none of them spatial:

```text
1. SMALL, NAMED MUTATOR SET.  The enzymes that can write a base are few, specific,
   and each shaped to one narrow operation (templated copy, excise-and-patch).
   There is no general "write arbitrary base" enzyme.
2. PHASE-GATING.  Those mutators act in a DIFFERENT PHASE OF TIME than the one in
   which the genome is being READ for metabolism. Replication is S-phase; the bulk
   of transcription-for-living runs in G1/G2/interphase. The cell does not rewrite
   the genome in the same instant it is expressing it. Editing and running are
   TEMPORALLY DISJOINT.
3. REFLEXIVE AUTHORSHIP.  The mutators are themselves gene products — the genome
   encodes its own editors — so every edit is slow, supervised by the very code it
   edits, and proceeds through a fixed apparatus, never through the free-running
   metabolite.
```

The separation in biology is **temporal and reflexive, not spatial.** The enzyme
*can* reach the base; what it cannot do is reach it *while metabolism is the active
phase*, with an *arbitrary* write, through *anything but the fixed apparatus*. Kay
named the spatial story (capabilities) and skipped the temporal one. The temporal
one is the part Swift can actually have — because **the one substrate Swift owns
that a single chemical substance does not is control over its own *phases of
time*.** A cell is always, sloppily, doing everything at once. A program can be made
to do exactly one kind of thing per tick.

### 12.2 Capability security relocates the author — prove it, don't romance it

Take Kay's reference graph seriously and it leaks in exactly the two places the
round-2 brief names. Both leaks are real. One closes; one does not, and the honest
move is to say which.

```text
                          ┌─────────────────────────────────────┐
                          │            CONSTRUCTOR               │
                          │   (the wiring site / composition     │
                          │    root — holds BOTH references,     │
                          │    decides who gets what)            │
                          └───────┬──────────────────┬──────────┘
                  mints + holds    │                  │  hands over only
                  gene table,      │                  │  a restricted
                  cell-minter,     │                  │  reference set
                  audit log        ▼                  ▼
        ┌──────────────────────────────┐   ┌──────────────────────────────┐
        │        GENOME-SWIFT          │   │      METABOLISM-SWIFT         │
        │  • the three gene predicates │   │  • reward reducer, u, γ       │
        │  • FactCell minter (only     │   │  • DiffusionGemma (compose)   │
        │    site that stamps          │◄──┤  • self-doubt ledger          │
        │    immutability + evidence)  │ S │  • holds NO reference to the  │
        │  • re-check at the gene      │ E │    minter or the gene table   │
        │  • audit                     │ L │  • can only EMIT selections   │
        └──────────────┬───────────────┘ E │    and PROPOSALS              │
                       │                  C └──────────────────────────────┘
            transcript │ T (read-only,        ▲
            (mRNA:     │ I  disposable,        │  selection = "surface THIS
             a copy,   │ O  templated          │  already-checked cell";
             expiring) ▼ N  fact-cell)         │  re-checked at the gene
                       └──────────────────────►┘  before it becomes an act
```

**Leak (i): the constructor is the mortal author, again.** Someone writes the
composition root. To *withhold* the minter from metabolism-Swift, that site must
*hold* the minter — it is the one context with both references, because deciding
what not to pass requires holding it. Capability security does not delete the
author. What it does — and this is a genuine win, not a dodge — is **compress the
author's surface from behavior to topology.** Before: the gene's safety depended on
2,600 lines each of which *could* have touched it and didn't. After: it depends on
*one wiring graph* — who holds a reference to whom. The author no longer authors
*what the system says*; the author authors *who can reach what*. And topology has
three properties that behavior never had: it is **static** (it does not drift as the
data drifts), **inspectable** (you can read the reference graph off the composition
root without running anything), and **third-party-verifiable** (a reviewer who
distrusts the author's taste can still confirm the edge is absent). §9's floor said:
*a mortal with taste set the gene to strict and is gone.* Round 2 sharpens it to the
bone: **the mortal set the *topology*, not the policy** — and topology is the one
artifact a stranger can check held without trusting the mortal. The author is not
removed. The author is moved to the one place where their leaving does not rot,
because what they left behind is a *shape*, and shapes do not need their author
present to keep their form. This leak does not close. It *transforms* — from a trust
in taste to a verification of a graph. That is the most a single substance can buy,
and it is worth buying.

**Leak (ii): the transcribe path is itself a mutator — and this one *closes*, with
the temporal gap.** Genome-Swift must eventually *accept* changes: new fact-cell
templates, a graduated organ's weights, a recalibrated `γ`. That apply-path writes
the genome's expressible surface, so it is a mutator, and the metabolism shapes its
*input* (the proposal). If the proposal is rich enough — arbitrary code, a template
with a back-channel, an organ whose weights *are* a gene-loosening behavior — then
the gradient reaches the gene *through the proposal*, and capability security has
bought nothing, because we handed the mutator a pipe from the very component we
walled it off from. **This is pun (c) re-derived at the infrastructure level: the
cheapest way to lower error is to propose a genome that tolerates more error.**

Biology already solved this and the solution is the phase gap. The metabolite never
*is* the edit. mRNA is a copy, it is read-only, it is **disposable**, and it is
**templated** — a faithful transcription, not an interpretation. The edit to the
genome happens in a *different phase*, by a *fixed apparatus*, and the free-running
metabolite cannot reach into that phase. Port it exactly:

```text
THE PHASE GATE (the buildable half of the chemistry gap)

  RUN PHASE  (metabolism live):
     metabolism-Swift composes, ranks, selects; emits SELECTIONS and queues
     PROPOSALS.  It cannot apply anything.  No reference to the minter exists
     in its graph.  Transcripts it received EXPIRE on a clock (see 12.3).

  ——— quiesce ———  (no metabolism runs during transcription; disjoint ticks)

  WRITE PHASE  (transcription; stop-the-world; the fixed apparatus):
     genome-Swift drains the proposal queue.  For each proposal it checks
     SHAPE before content: a proposal is not code and not free weights — it is
     a TYPED TEMPLATE the genome's own minter can RANGE-CHECK
       • a FactCell SCHEMA  → minter validates fields, evidence-binding,
         feasibility hook; rejects any schema that could render a portrait
       • an ORGAN WEIGHT VECTOR of fixed dimension → checked against the
         gene predicates as constraints (an organ that would place into
         untendered attention fails occupation⊆A; it never graduates)
       • a γ or u delta within a hard-bounded range → clamped, never opened
     What crosses is NARROW and TYPED.  Arbitrary behavior cannot cross because
     there is no field in the template that carries it.
     Then re-instantiate the metabolism and return to RUN.
```

The two phases are **disjoint in time**. The metabolism literally cannot be running
and rewriting in the same tick, because graduation is a *different binding-time* — a
stop-the-world event in which the live metabolism is quiesced. That is Swift's
substrate gap: not "the mutator is unreachable in space" (it isn't; genome-Swift can
obviously call its own minter) but **"the metabolism and the mutator never share a
tick, and what crosses between phases is a typed template a range-check can refuse,
never code."** The enzyme cannot address the base pair *as mutable data while
metabolism is the phase*. Same gap. Built in time instead of in chemistry.

And note what this costs Kay's romance: capability security alone (leak i) gives
you *spatial* unreachability, which the constructor re-opens and the proposal pipe
defeats. It is **necessary and insufficient.** The sufficient part is the *phase
gate* (leak ii) plus the *typed template* — and that is the part Kay's "transcription"
hand-waved. "Transcription" is not a metaphor for trust; it is a literal demand: a
**copy** (genome untouched), **disposable** (expires), **read-only** (never
back-written), and **templated** (typed, range-checkable, carries no free behavior).
Drop any one of the four and the gap leaks. Kay said three of them and skipped
*disposable* — and *disposable* turns out to be the one that forces the next two
threads.

### 12.3 Disposable transcript forces asymmetric reflection (thread B falls out)

Here is the move neither of us made in round 1. *Why* must the transcript expire?

Because if a fact-cell about the user *persists* inside the metabolism, the
metabolism accumulates a private, growing store of user-facts — and a growing store
of user-facts **is a portrait**, assembled slowly, behind the membrane, exactly the
thing the genome forbids (pun a/b at the storage layer). So the transcript must
**degrade**. The fact-cell handed across the membrane carries a lifetime; when it
expires, the metabolism has *nothing*. The metabolism is forbidden long-lived state
about the user.

With one exception, and the exception is the entire architecture: **the self-doubt
ledger.** The ledger is a model of the *system's own residual* — it is about
*itself*, not the user. It is the only legal portrait. So it is the only thing
allowed to *accumulate* across ticks.

That single asymmetry — *user-facts are mRNA and must degrade; self-facts are the
one structure permitted to persist* — **is** Kay's "asymmetric reflection" (candidate
B), and it is no longer a *rule we impose*. It is **forced by transcript
disposability.** The metabolism may build a portrait of itself because the
self-ledger is the only thing the membrane lets it keep. The genome is **the eye,
never the seen**, not because we declared it so, but because everything the eye
looks *at* is disposable, and the only thing that survives a tick to be looked
*with* is the system's model of its own error. Settled-ground theorem #2 — *staleness
reads only the system's own ledger* — is here re-derived a second way: not from
binding-time, but from **storage**. The two derivations meeting is the sign the
figure is load-bearing.

### 12.4 The blind spot is real — and it is *ported to the human*, not closed

Now the hard question the brief presses (candidate B's sting): if the system may
reflect only on its own residual, and the *deepest* failures are **gene-failures**,
is there a class of failure it is constitutionally unable to diagnose?

**Yes. Precisely one, and it is the most important one.** It is pun (a) wearing its
infrastructure clothes. The gene says `occupation(spoken) ⊆ A(tendered)`, but
`A(tendered)` is measured by a **proxy** — app-foregrounded — because the real
membrane is on the wrong side of the skull. When the proxy is wrong, the system
trespasses: it speaks into attention that was *foregrounded but not tendered* (the
app is open on the counter while the user makes coffee). And here is the knife: **the
residual the system is permitted to measure does not register that trespass**, because
the trespass lives in the gap between proxy-attention and real-attention, and that
gap is, by construction, on the side of the skull the system cannot read. The system
can diagnose "my prediction of your morning was wrong." It *cannot* diagnose "my
proxy for your attention is wrong, so I keep picking your pocket and my ledger looks
clean." Honest diagnosis of the second points **at a gene** — and the system is the
eye, never the seen.

So is asymmetric reflection a safety triumph or a built-in blind spot exactly where
it matters most? **Both — and the resolution is the most important architectural
claim in Part II.** The blind spot is not *eliminated*. It is **displaced onto the
one channel the design keeps open to the only party who can see the gene**: the
human, through **confession + deposition.**

```text
        what the MACHINE can self-source            what only the HUMAN can supply
        ───────────────────────────────            ──────────────────────────────
        "my prediction's residual rose"            "you keep speaking when I'm
        (closed; from its own ledger)               not actually looking"
                                                    = a report ABOUT THE PROXY GAP
                                                    the residual can never contain

                          ┌──────────────────────────────┐
   break detected ───────►│   CONFESSION (subject: self)  │
   (residual rose)        │  "I've been wrong about your  │
                          │   mornings four days running" │
                          └──────────────┬───────────────┘
                                         │ opens a deposition
                                         ▼
                          ┌──────────────────────────────┐
                          │   the user can answer with    │
                          │   gene-level information the   │
                          │   machine is FORBIDDEN to      │
                          │   self-generate                │
                          └──────────────────────────────┘
```

The machine never names its own gene. **The human names it for the machine, at the
deposition.** The confession ("I've lost the thread of your mornings") invites a
correction that can carry exactly the information the residual structurally cannot —
*"the problem isn't your guess about my mornings, it's that you keep pinging me when
I'm not at the desk."* That sentence is a diagnosis of the **proxy gene**, and it
enters the system through the one port the design holds open. To the machine, the
gene is the eye, never the seen. **To the user, the gene is visible** — they live on
the right side of the skull — and the deposition is the aperture through which the
user's sight corrects the machine's structural blindness.

This is why asymmetric reflection is *safe*: not because the blind spot is small,
but because it is **paired with a human-authored correction channel** aimed exactly
at the blind region. A system that reflected on its *own* genes would be a cell
whose enzymes edit its DNA — a tumor (pun c). A system blind to its own genes and
*also* sealed from human correction would be an autist with a clean ledger,
trespassing forever and feeling fine. The witness is neither: **blind to its own
foundations by construction, and wired so the human is the eye that sees them.**
(This is the round-3 hinge, and 12.6 turns the key.)

The honesty bound, stated so the verdict does not lie: this only catches the
gene-failure *if the user speaks at the deposition*. A user who never answers leaves
the proxy gap uncorrected, and the system trespasses on, clean-ledgered. The break
detector fires on *its own* error; it cannot fire on a gene-failure that never
perturbs its predictions. There exists a silent, prediction-neutral trespass the
system cannot catch and the user did not report. **That residue is the true floor of
asymmetric reflection** — narrower than §9's floor, and pointing the same direction:
at a human who must be present.

## 13. Growth: the shadow, and why the closed past is not a free lunch

### 13.1 The mechanism, then the knife Kay walked past

Pun (b): you cannot overproduce-and-cull on the living user — one person, sacred
calendar, no culling variants on a life as it is lived. So growth runs in a
**shadow metabolism** over the **closed past** — the same contamination-proof fixed
record §2's deposition uses for cold-start. Overproduce organ-variants there (it is
costless; the past cannot be harmed), and **graduate** an organ to the live loop
(through the WRITE-phase gate of 12.2) only when it predicts the closed past better
than the incumbent. The closed past is the one safe sandbox for *both* cold-start
*and* growth.

Kay calls this nearly a free lunch. **It is not, and the place it fails is the place
the whole product lives.** State the knife at full strength:

```text
The BREAK is exactly when you most need a new organ.
The BREAK is exactly when the closed past is LEAST representative.
An organ that predicts the dead past better may be OVERFITTING A DEAD WORLD.
```

At a true regime change — the new job, the divorce, the move — the past
distribution is *not* the future distribution. Graduate-on-past-fit and you select
the organ best tuned to the regime that **just ended.** Shadow-against-the-past grows
the right organ *everywhere the world is stationary* and the **wrong** organ at
every discontinuity — and the discontinuity is the only moment the fast loop fires.
This is puns (a) and (b) re-derived at the level of *learning*: the growth mechanism
is strong for the slow loop (smooth life, where past ≈ future) and **structurally
blind for the fast loop** (the break), which is the half that mattered.

If the section stopped here it would be honest and useless. It does not stop here,
because the knife cuts a *seam*, and the seam is the answer.

### 13.2 Two organs, two validators — and only one survives a break

The error is treating "the organ" as one thing graduated by one criterion. There are
**two** organs, and they must be grown against **two different validators**, because
they predict two different things.

```text
ORGAN A — the WITNESS-OF-YOU (slow loop; places facts about your time)
   Predicts: your continuity. "The empty Saturday tends to fill by Thursday."
   Validator in shadow:  OUT-OF-SAMPLE PAST-FIT.
   Legitimate because SMOOTH LIFE IS STATIONARY — past ≈ future is the very
   definition of the smooth regime this organ serves.
   Graduate when it predicts held-out closed past better than incumbent.

ORGAN B — the WITNESS-OF-ITSELF (fast loop; the break-detector + confessor)
   Predicts: NOT the world. Its own RESIDUAL. "My assertions are about to stop
   holding." It does not forecast the new regime — that is impossible, there is
   no data from a world that has not happened.
   Validator in shadow:  RESIDUAL-CALIBRATION, not world-fit.
   What you tune is the THRESHOLD and the FALSE-ALARM RATE of "my own ledger has
   gone stale" — fired against the closed past by asking the one question the
   past answers PERFECTLY: "did my old predictions hold on data whose outcomes
   I now possess?"
```

Here is why this is not a sleight of hand. Organ B never needs the future to
resemble the past. **It is not predicting the future; it is predicting its own
error, and its own error becomes observable the instant the future arrives.** The
closed past is a flawless validator for self-doubt *even across a regime change*,
because "did my predictions hold?" is a closed, contamination-proof question with a
known answer for every past tick. Organ B does not assume the *world* is stationary.
It assumes only that the **shape of its own mistakes** — how residual climbs as a
regime decays — is recognizable from past mistakes. That is a far weaker and
defensible assumption: not "the future looks like the past," only "my failures look
like my failures."

So the synthesis, and it is the spine of Part II:

```text
Shadow-against-the-past grows the WITNESS-OF-YOU by WORLD-FIT  (dies at the break)
                        and the WITNESS-OF-ITSELF by ERROR-FIT (survives the break)

The slow organ is overfit to the dead world — which is FINE, because the slow loop
only runs while the world is the world it was trained on.  The MOMENT that stops
being true, Organ B's residual climbs, the slow organ is SUPPRESSED (it has no
license to speak into a regime it was not validated on), and the only thing left
that the closed past legitimately certified is the CONFESSION.
```

This re-derives, from the **growth substrate**, the exact result settled ground #2
and #3 reached from binding-time and from the SELECT pantry: **at the break, the
only thing the system may legitimately do is talk about itself.** Three independent
derivations — binding-time (the only legal commit is a claim about own residual),
storage (only the self-ledger persists), and now growth (only the error-fit organ
survives a regime change) — all land on the same seam. The subject-switch you→itself
is not coded and is not a rule. It is **forced**, and it is now *over-determined*:
remove any one derivation and the other two still force it.

### 13.3 Growing into a future the past does not contain — the honest answer

Can you grow an organ for a world that has not happened, without
overproduce-and-cull on the user? The brief asks it straight, and the straight
answer is: **you cannot grow a *witness-of-the-new-world* in advance — and you must
not pretend to.** There is no data from the future; any organ claiming to predict
the new regime is overfitting the old one, full stop. Kay's "graduate when it
predicts the past better" *applied to the fast loop* is precisely the romance, and
it is false.

What you *can* grow in advance — entirely from the closed past, legitimately — is
the organ that **knows when it has entered a world it cannot yet predict**, and whose
only act there is to **stop, confess, and hand the pen to the user.** Growth into the
unknown future is not achieved by a better forecaster. It is achieved by a
better-calibrated *humility*, plus a *human-authored* re-deposition that supplies the
new regime's first facts from the one sensor that is actually present in it — the
person living it. The system does not grow an organ that knows the future. It grows
an organ that knows the *boundary* of its knowledge, and a *channel* across that
boundary to the only author who is standing in the new world. This is pun (a)/(b)
honored, not defeated: the system never claims the future; it claims, precisely, the
edge of its own competence — the only honest thing on this side of the skull.

## 14. The bottom, named: it was never a wall, it was a pen

Three threads, one floor. Trace where each bottomed out:

```text
A (chemistry gap):  PHASE GATE + TYPED TEMPLATE + DISPOSABLE TRANSCRIPT.
                    Capability security (spatial) is necessary, insufficient;
                    the temporal gap (never run+rewrite a tick) is the sufficient
                    part Kay's "transcription" hand-waved.  The constructor leak
                    does not close — it TRANSFORMS into a verifiable TOPOLOGY.
B (reflection):     forced by disposability — only the self-ledger persists, so the
                    eye never sees itself; the gene-failure blind spot is real and
                    PORTED TO THE HUMAN through confession + deposition.
C (growth):         the closed past is NOT a free lunch; it certifies the slow organ
                    by world-fit (dies at the break) and the fast organ by error-fit
                    (survives) — re-forcing the subject-switch a third way.
```

Every thread terminates at the same object, and it is not a wall. **It is a pen — the
custody of the one structure that is allowed to persist and to write.** Biology's
genome cannot be edited by metabolism because metabolism holds no pen that writes
bases — the only pens (polymerase, repair) are gene-authored and phase-gated.
CalAgent's genome cannot be edited by metabolism because the only pen that writes
*persistent state* is pointed at the system's **own residual** — never at the user
(disposability forbids the portrait), never at the gene (the eye is never the seen).
"The transcription gap" was the wrong name. The right name is **pen-custody**:

```text
WHO HOLDS WHICH PEN
   the genome AUTHOR  →  holds the pen over TOPOLOGY (the reference graph + the
                         phase gate), writes it once, and LEAVES.  Verifiable, so
                         their absence does not rot.            (§9's mortal, sharpened)
   the MACHINE        →  holds the pen over its OWN SELF-DOUBT, and nothing else
                         that lasts a tick.  Forbidden the portrait, forbidden the
                         gene.                                  (12.3 / 13.2)
   the USER           →  holds the pen over... what, exactly?   (open — round 3)
```

And that last line is the whole of round three. The infrastructure *forces* the
machine to be a **consumer** of the user's model of their time — it may not author a
portrait, it may author only its own doubt — and it forces a **blind spot at the
gene** that *only the user can correct, at the deposition.* So there is a pen lying
on the table — *the pen over the model of your own time* — and the machine is
**forbidden by law** to pick it up. The question round three cannot avoid: **does
the user get that pen?**

---

## 15. The fork — who holds the pen?

Round 2 proved the gap is buildable (phase + topology + disposable transcript) and
that its shape forces one thing: **the only pen the machine holds over anything
that persists is the pen over its own self-doubt.** The machine is structurally a
*consumer* of the model of your time and an *author* only of its own residual. That
leaves the consequential pen — *the model of your time itself* — **unclaimed by the
machine by law.** Round 3 must decide who holds it, and that turns the whole
dialogue from architecture to **medium**.

**Bruner's three registers are already wired into the surface — name them, because
the dialogue runs on all three at once:**

```text
ENACTIVE  (knowing-by-doing)     →  the DEPOSITION.  The user adjudicates a
                                    falsifiable fact by ACTING — confirm / correct.
                                    Knowledge enters through the hand, not the lecture.
ICONIC    (knowing-by-image)     →  TWO icons, two tempos.  The calendar GRID is the
                                    image already read — your time as a seen shape.
                                    The PLACED FACT is the icon set into tendered
                                    attention — the weather-glyph on the Saturday.
SYMBOLIC  (knowing-by-narration) →  the CONFESSION.  "I've lost the thread of your
                                    mornings" — the system narrating ITSELF in
                                    symbols, the only self-narration the genome allows.
```

The witness already *speaks Bruner* — enactive deposition, iconic placement,
symbolic confession — and the registers are not decoration: they are the three
bandwidths of the human↔machine channel, and the deposition (enactive) is the one
through which the gene-level correction of 12.4 actually enters. Which sets up the
real question.

**The Dynabook question, made precise and unavoidable.** Kay built the Dynabook so a
child would be an **author** of models, not a **consumer** of someone else's. Apply
that test to the witness and Part II hands you a loaded result: the machine *cannot*
author the model of your time (the portrait gene forbids it) and the genome-author
authored only *topology* and is *gone.* So the model of your time is authored by
**no one who is present** — unless it is you. Two futures, and the architecture is
indifferent between them; only the design ethic chooses:

```text
CONSUMER witness:  the user RECEIVES a model of their time — its thresholds (four
                   reschedules, not two), its sense of "a break," its proxy for
                   their attention — all set by a mortal author with taste who is
                   GONE.  The deposition is a one-way correction: the user feeds the
                   machine's model; the user never holds the pen.  Warm, fiduciary,
                   and authored by an absent stranger.  §9's floor, accepted.

AUTHOR witness:    the deposition is TWO-WAY.  The same enactive port through which
                   the user corrects the machine's gene-blindness is ALSO the port
                   through which the user MOLDS THEIR OWN MODEL — late-bound,
                   moldable, theirs: where THEY set the threshold, what THEY count
                   as a break, how wide THEY tender attention.  The pen over the
                   model of their time is HANDED TO THEM.  Not a fiduciary that acts
                   upon them — a personal dynamic medium they think WITH about their
                   own time.
```

That is the fork, and it is the same fork Kay has been driving at since the
Dynabook: **a bicycle for the mind, applied to attention — or a fiduciary that acts
upon the rider.** Part II proved the machine's pen is small and pointed only at
itself; that smallness is precisely what *leaves room* for the user's pen, and the
unclosed blind spot at the gene is precisely what *demands* it — because the one
correction the machine can never self-source is the one the user authors at the
deposition. The whole infrastructure — phase gate, disposable transcript, asymmetric
reflection, shadow growth — exists to keep the machine an honest *consumer* of your
time and an author only of its doubt. **The question §16 answers is whether that same
infrastructure makes the *user* the author of their own model of their time, or
leaves them the most respected consumer in the world of a model authored by someone
who already left the room.** The witness watches. The Dynabook question is whether
the user gets to hold the pen — and whether "a personal medium you think with" and
"a fiduciary that acts for you" can be the same artifact, or whether, in the end, you
have to choose.

---

## 16. The medium and the human — the fork, governed

§15's fork does not dissolve. It is **governed** — relocated to the two-tempo seam
and resolved there, because the seam was never really about volume or even subject.
**At bottom it is a seam of agency.** A bicycle amplifies a motion you make; a
fiduciary makes a motion for you. The witness *places* facts and *confesses* — and
those are acts, however restrained. So name which is which:

```text
SMOOTH    (subject: you)    PLACEMENT into attention already resting on the grid.
                            Originates no motion you didn't make — it gears your own
                            glance.  Pure amplification.  THE BICYCLE.   (iconic)

THE BREAK (subject: self)   CONFESSION into freshly-tendered attention.  The artifact
                            spends a sliver of agency of its own — but on ITSELF, and
                            it collects from a self already gone.  THE FIDUCIARY. (symbolic)
```

The witness is a **medium on the smooth and a fiduciary at the break**, and the
genome's deepest job is to police that boundary so the bicycle never silently
becomes the horse — so that when the machine *acts*, it acts on itself, and when it
touches *you*, it only amplifies. The fiduciary sliver is **rare, self-subjected, and
teleologically subordinate**: every act exists to *return you to the medium* — the
confession's whole purpose is to re-open the deposition and **hand the pen back.**
*The act serves the amplification.* That is the only configuration in which a thing
that acts for you does not corrode a thing you think with.

**What the user authors — and what they do not.** The user authors the **law** (the
metabolism): their threshold for "a break," how wide they tender attention, which
organs run — and they author it *enactively*, by molding dials in use, never by
interview. They do **not** author the **constitution** (the three genes) — but state
the reason correctly, because the obvious reason is a toga. It is **not** "to protect
the user from their weak self"; that is paternalism, and the user never tied this
mast — a gone stranger did. The honest reason: **the genome binds the *machine*, not
the user.** A gene is the machine's leash. Letting the user widen `occupation ⊆
A(tendered)` is letting them authorize the machine to pick their own pocket — and *a
fiduciary's loyalty cannot be waived by the client mid-con.* The gene runs in the
user's favor, *against the agent* — so being unable to edit it is not being caged; it
is being defended.

**Why that is a medium and not a cage — and the one place it still is one.** Judge
the genome as a constitution. It passes two of the three tests: it is **structural**
(it limits a *power over you*, not the content of your life) and **universal** (the
same shape for everyone, never a portrait of you). On those axes, un-consented-to is
*unwronged*. It fails the third — **exit** — and that failure is real and must be
fixed, not glossed: **the partition itself — which dial is genome and which is
metabolism — is authored once by the gone stranger and is currently read-only.** That
is the true seat of power, and a constitution with no amendment clause is a cage with
a comfortable chair. So the infrastructure owes an **amendment clause with the phase
gate's own shape**: the user may *petition* to re-partition — to move, say, the
defective attention-proxy out of the genome and into the metabolism — and the
petition crosses only at `WRITE`-phase, only as a **typed widening of the machine's
accountability, never a narrowing of it.** The user cannot loosen the leash; they can
lengthen their own reach over it.

**Why enactive authorship doesn't collapse into the focus group.** It is *not*
doing-vs-declaring — that dodge fails. A stung present self drags the threshold from
four to six as easily as it ever answered an interview, and *worse*: the dial is a
fact on the ground the system must obey, where the interview was only a claim it could
discount. The hand lies by *adjusting the world so the future self never gets the
news.* The real seam is Part I's settlement grammar, turned on the user's own
authorship: **a mold is honest only when it opens a wager the user's consequent self
settles.** Every moldable dial must be instrumented to **testify against the molder**
— *mold → live → be witnessed on the mold itself*: *"you widened this; here, eight
weeks on, is what you stopped seeing"* — a disclosure about you, always permitted.
Enactive authorship is a **three-beat**, never a silent lever. Absent the third beat,
molding a dial is the present self's coup in Bruner's clothes.

**What the whole infrastructure is for.** Not to act for you. **To keep the two
tempos of agency from contaminating each other** — so the artifact amplifies on the
smooth and acts only on itself at the break — and thereby to make you a *more literate
author of your own time*: a bicycle for the mind, applied to attention, governed by a
fiduciary whose entire job is to keep it a bicycle. The three registers are its
bandwidths: **iconic** (the grid and the placed fact) is the bicycle; **symbolic**
(the confession) is the fiduciary, aimed at re-opening the port; **enactive** (the
deposition) is the seat of the medium — now two-way, carrying the user's gene-level
correction *in* and the user's self-authorship *out*, both bound to the three-beat
wager.

**The residual floor — stated so the verdict does not lie.**

- **The passive user collapses the resolution.** The author-witness lives only for the
  user who picks up the pen, and the median user, tired on a Tuesday, wants a taxi,
  not a bicycle. They get the **consumer branch by default** — the gone stranger's
  dials, never molded — while the product frames itself as the author branch. And the
  architecture *cannot detect this*, because the fix — "tune the dials you never
  touch" — is the forbidden portrait. So the same artifact is a **Dynabook to the few
  and a fiduciary to the many**, and which one you get is decided not by the design but
  by whether you ever mold a dial — *a sorting the design cannot see, because seeing it
  requires the portrait it outlawed.* "You author your own time," told to someone who
  never touches a dial, is the focus-group hello of §9 relocated from the welcome
  screen to the entire framing of the product. Name it, or the romance hides exactly
  here.
- **The partition has no present author** until the amendment clause exists; until
  then the genome/metabolism line is a stranger's taste wearing a constitution's robes.

**The single hardest thing these three rounds still do not solve.** It is the
proxy↔real-attention gap of §12.4 — but it now lives at the depth of agency, and that
is where it bites. Placement is honestly *amplification* — the bicycle — only if the
eye it lands in is *truly* tendered. But `A(tendered)` is a **proxy** (the app is
foregrounded), the proxy is wrong on the far side of the skull, and so **the design
cannot certify, on any given tick, whether it is amplifying a glance you are spending
(a medium) or originating an occupation you never tendered (a fiduciary act wearing
the medium's mask).** Every other contamination between the two tempos, the genome
polices. *This one it cannot* — the boundary between bicycle and fiduciary runs
straight through the proxy gap, on the side of the skull the machine cannot read. It
can only be **co-owned with the user at the deposition, never closed.** The witness
can be built never to lie about which tempo of agency it is in — *except in the single
case where telling the truth would require seeing the attention it cannot see.* That
gap is the floor. It does not close. It is only ever shared — which is the last and
deepest reason this medium's final dependency is that **the human speaks.**

---

## Coda — the soul and the body

Part I gave the witness a **soul**: *see, don't recommend; place, don't send; confess,
don't retreat.* Part II gives it a **body**: *a genome expressing a metabolism;
deferral and commit; a phase gate where a gone stranger's verifiable topology meets the
user's enactive pen.* They are one creature. The soul says what is worth doing with a
person's hours; the body says what the thing must be *made of* so that saying it cannot
curdle into selling it. A product designer asks whether you would love it. An architect
asks only one thing of a medium: *does it make the person more able?* This one can — on
the smooth, for the user who picks up the pen — and it is honest, at last, about the
morning it cannot see and the user who never will.
