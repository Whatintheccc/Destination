# plan-8-analysis.md — Why Plan 8 Reads Dry, and What Framework It Stopped Carrying

**Status:** review of `plan-8.md` against the framework documentation of the prior
iterations (`readme.md`, `plan-6-revised.md`, `plan-7-revised.md`) and the deleted
transformation files recovered from git (`plan-7.md`, `plan-7-controller-audit.md`,
`self-play.md`). It proposes no contract. It diagnoses a register break and a
corpus-integration failure, and recommends repairs.

**One-line verdict.** Plan 8's engineering core is sound and in one respect genuinely
advances the corpus — *minimize state, never monitors* is the right compression law.
But Plan 8 compressed the wrong layer to zero. It preserved every **sensor** and
discarded almost every **reason**, and in this corpus the reasons are partly
load-bearing. The result is an implementation manifest that has seceded from the
framework it claims to realize: the framework brief (`readme.md`) never references it,
the authority it cites (a "compression study") does not exist as a document, and the
one register the corpus exists to sustain — *every mechanism paired with the human
stake it protects* — is gone everywhere except the final eight lines.

---

## 1. What the corpus is, and where Plan 8 sits in it

Reconstructed from git history (`git log --all --diff-filter=A`), the lineage is:

```text
plan-4-revised(10)  ──▶  plan-5-revised  ──▶  plan-6 / plan-6-revised  ──▶  plan-7 / plan-7-revised  ──▶  plan-8
        │                     │                      ▲   │                       ▲   │
        │                     │            the-witness.md │            plan-7-controller-audit.md │
        │                game-engine.md   (counter-arg)   │                  self-play.md         │
     readme.md  ◀── rewritten per iteration ──────────────┴───────────── points at plan-7-revised ┘  (never updated for Plan 8)
```

The **transformation files** that produced each canonical step are mostly *adversarial
companions*, and most were deleted once folded in:

| Companion (deleted) | Persona / role | What it injected into the canon |
|---|---|---|
| `the-witness.md` | design counter-argument to Plan 5 | the witness reframe itself |
| `self-play.md` | RL researcher (Schulman persona) | E1–E4, "corrigible plant," the Witness Calculus |
| `plan-7-controller-audit.md` | hybrid-control theorist (Tomlin persona) | the seven controller repairs; the compress-order verdict |

This matters for the diagnosis: **the corpus advances by staging a thesis against a
capable adversary and folding the survivor into prose.** Plan 6-revised, Plan 7-revised,
and the readme all carry the marks of that dialectic. Plan 8 is the first canonical
artifact with no adversary in its bloodline — and it reads like it.

Recovered facts (all verifiable in git):

- Commit `8721d1e` added `plan-7.md`, `plan-7-revised.md`, `plan-7-controller-audit.md`, `self-play.md` together.
- Commit `83b63e7` ("Remove superseded plan documents") deleted `plan-7.md`, `plan-7-controller-audit.md`, `self-play.md`.
- Commit `0df7ef7` ("Add current plan state") added `plan-8.md`, re-added `plan-6-revised.md`, and **stripped the "Corpus status" table out of `readme.md`** (the table that used to tell a reader which file was canonical).

That last edit is the structural root of the problem and is treated in §4.

---

## 2. The register Plan 8 stopped carrying

"Framework documentation," in this corpus, has a precise and consistent signature
across the prior three documents. It is not decoration; it is a method. Three features
define it.

**(a) Every mechanism is introduced with the human stake it exists to protect.** The
machinery is never stated bare. It arrives married to a one-line moral consequence,
usually aphoristic:

- `plan-6-revised.md:706` — spendability, the mechanism, is justified in one breath: *"A true fact aimed at a self that can no longer act is not a witness. It is a sentence passed."*
- `plan-6-revised.md:494` — the calculus's expressive ceiling: *"The ceiling is the conscience. The same grammar that cannot say 'you are avoiding your sister' is the grammar forbidden by the privacy gene to know who the sister is."*
- `readme.md:24` — names its own limit before stating the law: *"What follows is the part no test holds…"*
- `plan-7-revised.md:2174` (Coda) — *"When the user becomes too predictable to the witness, the witness does not celebrate. It confesses that its own read is becoming self-confirming and asks again."*

**(b) A standing distinction between law, guess, and the un-typeable floor.** The
theorem / rule / data taxonomy (`plan-6-revised.md §2`) and the "breakfast test" exist
precisely so that a future reader can tell a wall from a flag. The framework keeps
re-drawing the line between *what a type holds* and *what only you can hold*
(`readme.md` §A "three walls and a floor"; the membrane as "the boundary of
theorem-izability").

**(c) The conclusion is dramatized, not asserted.** Even `plan-7-revised.md` — by far
the most contract-dense predecessor, pages of Swift structs — keeps a doctrine spine
(§3 empty-maximize theorem, §4 the dynamism doctrine) and closes on a Coda that argues
(`:2172`): *"That loss is not patched by a metric. It is carried as a floor."*

This is the "framework documentation of prior iterations." It is the corpus's whole
reason for being readable: it is an argument about restraint, in which the contracts
are evidence, not the point.

---

## 3. How Plan 8 breaks from it

Plan 8 inverts the ratio. The contracts become the point; the argument becomes a
table cell. Six specific breaks:

### 3.1 The "why" layer is compressed to near-zero

Plan 8 tells you *what* is remembered (seven registers), *how* it is classified
(STATE / RING / SENSOR / PROJECTION / PROVENANCE), and *that* it is equivalent
(`ProjectionEquivalenceReceiptV1`). It almost never tells you *why a human is better off*
for any of it. Compare the same idea across iterations — the rule that a missing
measurement is treated as danger:

- Framework register, `plan-7-revised.md:2177`: *"A margin you cannot measure is negative."* (a sentence that teaches)
- Plan-8 register, `plan-8.md:1327`: `testMarginUnmeasuredRoutesNegative | margin | .notMeasured(M) ≡ M<0.` (a row that ships)

Both are correct. Only one carries the framework. Plan 8 is 1,521 lines and the
density of moral/rationale prose is a rounding error against the predecessors'.

### 3.2 It is monologic — the dialectic is gone

Every prior canonical step was forced through an adversary (§1). Plan 8's
self-examination is `§20`, a self-audit table whose every row already answers in its
own favor ("Did Plan 8 add a new primitive? **No**"). A table that interrogates
itself and is always satisfied is not the corpus's epistemic engine; it is its
opposite. The document asserts convergence (`§1`, "primitive-level fixpoint") rather
than surviving an attempt to break it.

### 3.3 It cites an authority that does not exist

Plan 8 grounds its central decision in a "compression study," repeatedly and as
settled canon:

- `:57` "Plan 8 accepts the compression study's verdict"
- `:260` "The compression study's closure result becomes Plan-8 doctrine"
- `:1130` "Plan 8 adopts the process lesson from the compression study"

**There is no compression study in the corpus** — not in the working tree, not anywhere
in git history (`git rev-list --all` + content grep returns nothing). The nearest real
artifact is `plan-7-controller-audit.md`, which argued the *opposite ordering*
("complete → re-verify → **then** compress") and was deleted in `83b63e7`. So Plan 8
leans its whole compression mandate on a document the reader cannot open, derived from
an audit the reader can no longer find. In a corpus whose entire discipline is
*provenance you can check* (evidence hashes, sealed forecasts, derivation reports), an
un-checkable citation is not a small stylistic lapse — it violates the corpus's own
first principle.

### 3.4 Its new process apparatus has no lineage

`§16` ("Design process as a plant") introduces `M_design`, the **two-distinct-lens
rule**, and `AuditLensRegisterV1` as adopted doctrine. The *idea* is genuinely
inherited — it is the controller audit's §7 warning, re-stated. But the specific
apparatus is novel to Plan 8: a content search across all of git history shows
`two-distinct-lens` / `distinct lens` / `AuditLens` appears in **`plan-8.md` only**.
The framework would have introduced a new primitive with its rationale and its
counter-argument; Plan 8 introduces it as a finished `struct` and a test row
(`testTwoDistinctLensRuleRequiredForConvergence`). The corpus's own rule —
*a new primitive is theorem-surface and earns prose; only data ships as a row* — is
applied to the runtime controller but not to Plan 8's own method.

### 3.5 It preserves sensors but not meaning — and treats the two asymmetrically

Plan 8's signature insight is a preservation doctrine: *"Minimize state, never
monitors"* (`:9`), with `§3.2` a "preservation test" — delete nothing whose absence
would make an off-nominal mode invisible. This is excellent, and correct. But it is
applied only to machine observability. The same document compresses the *rationale
layer* to zero on the implicit claim that nothing safety-relevant was lost — without
ever running its own preservation test on that layer. In this corpus the claim is
false: the "why" is exactly what lets a future owner distinguish a law from a guess
(`plan-6-revised §2`) and resist quiet widening. Note that Plan 8 itself lists
`ownerWideningPressure` as an off-nominal mode (`:572`) and `owner config row →
reference-cap increase` as a topology failure (`:498`). **A dry spec is precisely the
surface on which owner-widening pressure operates unseen** — because a reader who was
handed rows instead of reasons cannot feel which constant is sacred and which is a
dial. By its own preservation test, the rationale layer is a monitor, and Plan 8
deleted it.

### 3.6 It seceded from the framework document instead of updating it

This is the largest break and the subject of §4.

---

## 4. The corpus now has two heads, and the front door points at the wrong one

The readme is the framework documentation — it says so: *"Engineering **brief**, not
the record"* (`readme.md:2`). A reader enters the corpus there. And there, today:

- `readme.md:3-5` declares **"The canonical record is now `plan-7-revised.md`."**
- `readme.md` mentions Plan 8 **zero times** (grep confirms; the lone "compression" hit at `:233` is the word inside "pre-registered").
- `plan-8.md:2` simultaneously declares itself **"canonical Plan-8 target architecture."**

So the two canonical claims contradict, and the framework brief routes every new reader
*away* from Plan 8 and into Plan 7-revised — the very document Plan 8 says it
compresses and supersedes. Plan 8 did not earn its place in the framework; it parked
beside it.

Worse, the commit that introduced Plan 8 (`0df7ef7`) actively *removed* the map that
would have located it. The prior readme carried a **Corpus status table** routing the
reader across files (canonical / evidence / provenance). That table was deleted in the
same commit that added Plan 8:

```text
0df7ef7  readme.md
-  | `plan-7-revised.md`         | canonical target architecture | … |
-  | `plan-7-controller-audit.md`| temporary verification evidence | … |
-  | `plan-7.md`                 | superseded | … |
-  | `plan-6-revised.md`         | historical architecture/provenance | … |
-  | `self-play.md`              | historical dynamism analysis/provenance | … |
```

The net effect: at the moment Plan 8 arrived, the corpus lost the one surface that
tells a reader which document to trust and why. Plan 8 is dry *and* unmoored — and the
second is what makes the first dangerous rather than merely austere.

---

## 5. The irony: Plan 8 is the artifact the deleted audit warned about

`plan-7-controller-audit.md` — the Tomlin-persona verification, now deleted — closed on
exactly this failure mode, in plain words (`:402`):

> *"Compressing now would bake the gating repairs into prose that reads finished, and
> the next reader — having lost the seams — would inherit a controller that looks
> complete and is not. That is the meta-level version of the very failure §4.2 warns
> against: mistaking the appearance of convergence (a clean document) for its
> substance."*

Plan 8 then does two things at once. It **imports the lesson** — `§16`'s "premature
freeze," `M_design`, "a clean audit from a lens that cannot surprise the design is
`.notMeasured`" is that paragraph, re-typed. And it **enacts the failure** — it is the
clean document that reads finished, with the seams (the rationale, the dissent, the
personae) compressed out, citing a study no one can read. The corpus warned itself,
deleted the warning, and shipped the thing the warning described. A document that
preaches "the appearance of convergence is not its substance" while being the smoothest,
least-contestable surface in the corpus is not converged; by its own §16 rule it is
`.notMeasured`.

---

## 6. What Plan 8 gets right (so the fix doesn't throw it away)

The critique is about register and integration, not about the engineering. Preserve:

- **The compression law** — *minimize remembered state, preserve every monitor, freeze governance constants, materialize decisions on read* (`§3.1`). This is a real advance and the right instinct.
- **The seven-register realization and the sensor budget** (`§5`, `§7`). Naming the corrigibility minimum as *state + sealed ring + sensor budget* (`§4.1`) is a genuinely clarifying move that the predecessors lacked.
- **The equivalence gate** (`§1.2`, `ProjectionEquivalenceReceiptV1`) — making compression a migration gate rather than a documentation style is exactly right.
- **The state/projection topology lint** — "no projection receipt may become state" is a clean, checkable invariant.

None of this needs to be sacrificed to fix the register. The fix is additive.

---

## 7. Recommendations

Ordered by leverage.

1. **Reunify the head. Update `readme.md` first.** Restore a Corpus status table and
   make exactly one document canonical. If Plan 8 is the target, the readme must say so
   and must route Plan 7-revised → "provenance/contracts" and Plan 6-revised →
   "ancestry," the way it once routed the others. Today the framework brief contradicts
   Plan 8 to a new reader's face; nothing else matters until that is fixed.

2. **Pay the provenance debt.** Either (a) write the missing `compression-study.md`
   (it can be short, and `plan-7-controller-audit.md §7` is its real seed — consider
   un-deleting that audit as cited evidence), or (b) stop citing a "study" and attribute
   the verdict to the controller audit by name. An un-openable citation cannot stand in
   this corpus.

3. **Restore the pairing, not the page count.** Plan 8 does not need to become Plan
   6-revised. It needs each *section* to regain one or two framework sentences: the
   human stake beside the mechanism. The seven registers should each say what is lost
   to the user if they drift; the sensor budget should say, in a line, why an unseen
   off-nominal mode is a harm and not just a bug. This is small surgery — a sentence per
   subsection — and it is the entire difference between a manifest and the framework.

4. **Run Plan 8's own preservation test on the rationale layer.** Adopt the rule
   explicitly: *the "why" is a monitor.* A compression that removes a reason a future
   owner needs to resist widening pressure fails the §3.2 test exactly as deleting a
   sensor would. Make that symmetry a stated doctrine, since Plan 8 already lists owner
   widening as the thing to fear.

5. **Give §16 a lineage or a counter-argument.** The two-distinct-lens rule is good and
   should stay — but it should be introduced as the new primitive it is: with its
   rationale, and ideally with the adversary the corpus always supplies. Otherwise Plan
   8 exempts its own method from the discipline it imposes on the controller.

6. **Carry the Coda register up.** The single place Plan 8 reaches the framework is its
   Coda (`:1502`, *"Plan 7 made the witness controller verifiable. Plan 8 makes it
   small enough to implement without losing the instrument panel."*; `:1519`, *"When it
   cannot tell, it assumes it is falling."*). That voice should open the document, not
   only close it. The Coda proves Plan 8 *can* speak the framework; it simply chose to
   do so for eight lines out of fifteen hundred.

---

## Coda

Plan 8's thesis is that you can shrink the witness without blinding it — *small state,
preserved monitors.* The thesis is right, and the document is its own counterexample.
It shrank the controller and kept every machine sensor; it shrank the prose and kept
almost no human one. The instrument panel it was so careful to preserve is the panel the
*machine* reads. The panel the *next engineer* reads — the one that says which constant
is sacred, which silence is mercy, and why a margin you cannot measure is assumed to be
falling — is the one it compressed away.

The corpus has always held that the deepest harms are the ones no type can hold, and
that the only defense there is to keep saying, in plain language, what the wall cannot.
Plan 8 walled the state beautifully and stopped saying the rest. That is why it reads
dry, and that is the part no test will catch.
