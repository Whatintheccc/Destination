# P12-P17 Compression Roadmap

Status: planning document  
Scope: CalendarPilot after P12, with P12-next as the proof chain and later phases as product simplification  
Primary target under discussion: reduce `calendar-pilot-p12/src/calendar_pilot` from about 13,949 LOC toward a 3,000 LOC core

## 1. Goal

The goal is not to make the current system smaller by quota pressure. The goal is to decide what CalendarPilot is becoming, then make the code match that product shape.

The 3,000 LOC target is theoretically possible, but not as a pure cleanup exercise. It requires retiring product commitments, compatibility promises, runtime modes, and UI surfaces. P12-next can make deletion safe. It cannot by itself make a 13,949 LOC system into a 3,000 LOC system.

Working target:

```text
current /src calendar_pilot LOC: ~13,949
target /src calendar_pilot LOC:  ~3,000
required reduction:              ~10,950 LOC (~78%)
```

That level of reduction means the later product is a smaller edition of CalendarPilot:

- one core trajectory engine,
- one primary frontend/control surface,
- one policy/live-model path or a very small backend adapter layer,
- one real provider path plus deterministic fixtures,
- one current simulator generation,
- one current replay/envelope schema,
- a smaller lab interface,
- no long-lived compatibility strata except where explicitly chosen.

## 2. Safety Definition

Safe compression means code can be removed, merged, or rebuilt without weakening the frozen product, the evidence trail, or the humane constraints of the system.

A safe destructive change has:

- accepted C1 verdict evidence,
- root and coverage evidence,
- exact line spans,
- dynamic dispatch and JS reachability audit,
- live-leg handling through run evidence or `DEFER`,
- no deletion of B-invariant or human-legibility walls,
- awareness of placebo gates,
- correct migration order,
- green release gates or named pre-existing holds,
- a tombstone/archive path for removed behavior.

Unsafe compression is any change justified only by grep, fixture tests, `p12-release` alone, old lineage, row counts, or a LOC target.

## 3. Current Read

P12 proved the governed learning loop:

- ActionStream is reward truth.
- WorldStream is calendar/provider context.
- BiographyStream is a user-owned prior.
- derived signals are evidence-cited and user-governed.
- labels cannot influence authority.
- reward purity is enforced at replay/training consumption.
- provider writes are bounded by the ActionLifecycle, Swift/kernel authority, and provider transaction truth.

P12-next is the retention phase. Stage C0 decided the unit of judgment should be flow-clusters, not 1,506 individual symbols. C1 must assign verdicts. Step D can only implement accepted verdicts.

The major C0 findings that govern the roadmap:

- `legacy_state` is still product surface through served JS.
- `app.js` is not loaded by `index.html`, but `dogfood-release` still checks `/app.js`.
- several release report legs are placeholder/thin and can only anchor KEEP-I.
- `sim_v1`, fatigue residue, and envelope v1/r0 are compatibility/product-policy decisions.
- `frontend/session.py` is the largest compressible source mass, but only after frontend weaning or replacement.
- the largest savings require strangler completion or product simplification, not simple dead-code deletion.

## 4. Phase Model

The old P13-P15 sequence can collapse into one phase if the current frontend is considered disposable.

Recommended phase model:

```text
P12-next  retention verdicts + safe cleanup
P13       collapsed rebuild: backend/ML core simplification + frontend reset
P16       feature/product commitment selection
P17       optimization and LOC harvest against the selected product
```

P14 and P15 are intentionally folded into P13 in this model. They remain conceptual substeps inside P13, not standalone phases.

## 5. P12-next: Proof Chain And Safe Retention Cleanup

Purpose: decide what can be removed or consolidated under the current P12 product freeze.

Required work:

- run C1,
- produce flow-cluster verdict rows,
- produce defer ledger,
- produce placebo gate inventory,
- produce consolidation order,
- run Step D only for accepted destructive/consolidating verdicts.

Likely source reduction:

```text
conservative: 500-900 LOC
aggressive within freeze: 900-1,500 LOC
```

P12-next decisions:

| decision | options | likely recommendation |
|---|---|---|
| C1 unit | symbols vs flow-clusters | flow-clusters only |
| frontend legacy | preserve/wean/delete | wean or replace before session compression |
| `app.js` | delete now vs migrate release harness first | migrate dogfood-release check first |
| placebo gates | treat as pass vs KEEP-I | KEEP-I with owners |
| live/env-held paths | decide by fixture vs DEFER | DEFER unless run/root-listed |
| Program A runway | improve while consolidating vs protect | protect; report thinness only |
| tests/packages/examples | count toward quota vs out of runtime scope | out of runtime scope unless explicitly opened |

Exit gate:

- accepted C1 verdict artifacts,
- Step D readiness stated per cluster,
- no implementation change without verdict + spans + ordering,
- release pair remains green or has named pre-existing holds.

## 6. P13: Collapsed Rebuild And Frontend Reset

Purpose: make the product smaller by replacing the strangled surfaces instead of preserving them.

This is where the frontend-wholesale option belongs. If the current frontend is disposable, P13 can delete the careful P13/P14/P15 peel-apart sequence and replace it with a new contract-first product surface.

P13 thesis:

```text
frontend is disposable;
humane controls are not.
```

The old frontend/session machinery can be removed only after the new surface preserves:

- feedback capture as ActionStream rows,
- label activation/disable/correction,
- biography drift visibility,
- authority tier/scope visibility,
- grant/denial explanations,
- replay export or equivalent audit view,
- trace visibility,
- runtime blocker visibility,
- dogfood/cold-start evidence capture.

Likely source reduction:

```text
conservative net: 2,000-3,000 LOC
aggressive net:   3,000-4,500 LOC
```

The reduction is net of adding a smaller replacement frontend/control surface.

P13 decisions:

| decision | option A | option B | option C | impact |
|---|---|---|---|---|
| frontend strategy | preserve current app | wholesale rebuild | CLI/API-first temporary surface | biggest LOC lever |
| session state | keep `DogfoodSessionState` | split into small services | replace with stateless API + store | decides fate of `session.py` |
| `legacy_state` | migrate field by field | delete with new frontend | keep compatibility adapter | determines compression speed |
| control surface | browser app | local TUI/CLI + minimal web | Mac app only | product choice |
| lab panels | keep embedded in frontend | move to reports/artifacts | remove until needed | affects frontend and scripts |
| fixture conversation | preserve keyword UI | replace with scripted fixtures | share live conversation core | reduces `session.py` |
| static snapshot | keep sample/static fallback | remove | generate on demand | affects `frontend_state.sample.json` and app shell |
| dogfood release | preserve current harness | rebuild around new surface | split app release from ML release | affects `/app.js`, browser gates |

P13 exit gate:

- new control surface demonstrates all humane controls,
- browser/app/dogfood release gate updated to new surface,
- old frontend/session compatibility removed or explicitly retained,
- P12 B-invariants still pass,
- P12 feedback/replay/authority evidence remains visible.

## 7. P16: Feature And Product Commitment Selection

Purpose: choose what the small CalendarPilot product actually promises.

This is the phase that can make 3,000 LOC realistic. Without dropping commitments, the system remains large because it must support many modes, providers, compatibility paths, and lab surfaces.

Likely source reduction:

```text
conservative: 1,500-2,500 LOC
aggressive:   2,500-4,000 LOC
```

P16 decisions:

| area | keep-all option | small-product option | radical option |
|---|---|---|---|
| runtime modes | keep 7 modes | reduce to fixture, production, test | one runtime with injected backends |
| live model paths | keep Codex live + NIM live + deterministic | keep one live model path plus deterministic tests | externalize live model clients |
| Codex role | planner + conversation + annotator | annotator + bounded tool planner only | remove live conversation from core |
| DiffusionGemma role | deterministic + live NIM + tuning | one policy interface with pluggable adapter | external model service only |
| providers | EventKit + deterministic + stubs | EventKit + deterministic only | provider boundary as external service |
| Swift bridge | stub + IPC + mac app | one IPC-backed kernel plus fixture stub | Swift-only actuation, Python requests only |
| self-play | full curriculum/provider-backed | one simulator generation + small scenario set | external lab runner |
| replay compatibility | r0/r1/v1/v2 tolerated | current schema only after migration | migration tool outside runtime |
| lab scripts | many script entrypoints | one `calendar-pilot lab` CLI | lab outside core repo |
| dogfood app | full app release harness | smaller local dev harness | no app until productized |
| contracts | wide schema surface | current public contracts only | internal objects + generated boundary |

Feature commitments to decide explicitly:

- Is live Codex conversation a product feature or only a development aid?
- Is live NIM frontier generation part of core or an adapter?
- Is EventKit the only real provider for now?
- Are Google/Microsoft stubs useful or just declared future work?
- Is the Mac app a core product surface or a packaging experiment?
- Is provider-backed self-play core or lab-only?
- Are old replay/envelope schemas supported in runtime or only by migration tools?
- Is the lab embedded in the app or separate from the product?
- Is dogfood release the release gate, or does it become an optional operator gate?

P16 exit gate:

- signed feature matrix,
- code marked for removal by dropped commitment,
- replacement tests/gates aligned to smaller product,
- no dropped feature silently relied on by Program A or humane surfaces.

## 8. P17: Optimization And LOC Harvest

Purpose: after feature choices, remove structure that only existed to support discarded variation.

This phase should be mostly mechanical if P16 was explicit. It is where the 3,000 LOC target becomes an engineering target rather than a debate.

Likely source reduction:

```text
conservative: 1,000-1,500 LOC
aggressive:   1,500-3,000 LOC
```

P17 optimization targets:

- merge duplicated live-client scaffolding if both live stacks remain,
- collapse runtime configuration now that modes are fewer,
- shrink types around retained contracts only,
- delete compatibility shims after migration tools exist,
- merge or externalize scripts/lab entrypoints,
- remove unused provider stubs,
- simplify frontend/control API around the new surface,
- remove old session-persistence patterns after replacement,
- keep replay/invariants legible even if smaller.

P17 decisions:

| decision | conservative | aggressive |
|---|---|---|
| module boundaries | preserve organs | merge small modules around retained flows |
| type system | keep rich dataclasses | minimize runtime types, keep schemas at boundary |
| live clients | keep separate clients | common adapter/client substrate |
| invariants | keep broad checker | keep broad checker; never remove walls for LOC |
| lab | keep in repo | move lab runner outside core source |
| frontend | keep small web app | generate/static shell around API |

P17 exit gate:

- `/src/calendar_pilot` LOC measured,
- target delta explained,
- frozen smaller release gate passes,
- humane control audit passes,
- no compatibility promise remains undocumented.

## 9. Possible 3,000 LOC Architecture

A plausible 3,000 LOC edition might allocate roughly:

```text
core contracts/types:        350-450
replay + invariants:         450-600
policy/frontier/signals:     550-750
action lifecycle/provider:   450-650
authority/kernel bridge:     300-500
control API/frontend glue:   400-600
lab/simulator minimal:       300-500
package/app entrypoints:     100-200
```

This requires hard choices:

- no old frontend/session system,
- no broad compatibility runtime,
- no duplicated live-model stacks unless heavily shared,
- no large embedded dogfood release harness inside core source,
- no full lab cockpit inside the product app,
- no future-provider stubs that do not execute the transaction contract.

## 10. Decision Register

These are the major decisions that determine whether 3,000 LOC is reachable.

| id | decision | if yes | if no |
|---|---|---|---|
| D-01 | Is 3,000 LOC a `/src` target or whole-repo target? | source architecture must change | broader cleanup can count scripts/docs/tests |
| D-02 | Is current frontend disposable? | P13 can collapse strangler work | frontend must be weaned carefully |
| D-03 | Are humane controls mandatory in replacement? | safe rebuild path | P12's moral contract breaks |
| D-04 | Keep live Codex conversation? | larger Codex organ | smaller annotator/tool planner |
| D-05 | Keep live NIM in core? | larger DiffusionGemma organ | external adapter or deterministic-only core |
| D-06 | Keep seven runtime modes? | large runtime/session surface | smaller config and tests |
| D-07 | Keep dogfood-release as product gate? | larger scripts/app harness | smaller core release, optional operator gate |
| D-08 | Keep EventKit live path in core? | provider/Swift path stays | provider becomes external service |
| D-09 | Keep old replay/envelope compatibility? | compatibility shims stay | migration tool + current runtime only |
| D-10 | Keep self-play provider-backed lab in core? | lab code stays | external lab runner |
| D-11 | Keep Google/Microsoft stubs? | future promise stays | remove until real provider exists |
| D-12 | Keep Mac app packaging in core phase? | build harness stays | app packaging outside core source |
| D-13 | Keep rich explanatory fields in candidate contracts? | larger contracts/reward wiring | smaller contract, possible product loss |
| D-14 | Open tests/packages for cleanup? | repo-wide reduction possible | `/src` target remains harder |
| D-15 | Accept product break from P12? | faster shrink | must define new P13 freeze |

## 11. Recommended Path

Recommended path if the 3,000 LOC target is serious:

1. Finish P12-next C1 and Step D.
   - Do not skip this. It creates the proof chain and protects humane walls.

2. Declare P13 a rebuild phase, not a cleanup phase.
   - Current frontend is disposable.
   - Replacement humane controls are mandatory.
   - Old frontend/session code can be removed only after replacement gates pass.

3. Use P16 to choose features.
   - Reduce runtime modes.
   - Choose one real provider.
   - Choose one live model architecture.
   - Move lab/dogfood complexity out of core where possible.

4. Use P17 to optimize.
   - Merge modules around the selected product.
   - Delete compatibility.
   - Keep invariants, replay, authority, and humane controls legible.

## 12. Expected LOC Trajectory

This is a planning estimate, not a promise.

| point | expected `/src` LOC |
|---|---:|
| now | ~13,949 |
| after P12-next | ~12,500-13,400 |
| after P13 collapsed rebuild | ~8,000-10,500 |
| after P16 feature selection | ~5,000-7,500 |
| after P17 optimization | ~3,000-5,000 |

The low end requires aggressive product narrowing. If most current product commitments remain, expect the floor to be closer to 5,000-7,000 LOC.

## 13. Non-Negotiables

Do not cut these for LOC:

- reward purity at replay/training consumption,
- ActionStream/WorldStream/BiographyStream separation,
- no labels/signals in authority,
- user-controlled label activation/disable,
- biography drift visibility,
- authority grant/denial auditability,
- replay rows and causal chains,
- trace or equivalent inspectability,
- redaction at live egress points,
- provider write/verify/rollback truth,
- cold-start holds that honestly require real data.

These can be redesigned or consolidated. They cannot disappear.

## 14. Bottom Line

P12-next makes cleanup safe. It will not deliver 3,000 LOC.

The 3,000 LOC target becomes plausible only if later phases change the product shape:

- P13 replaces the frontend/session organism rather than preserving it,
- P16 chooses fewer features and runtime commitments,
- P17 optimizes the chosen smaller product.

The strategic choice is whether CalendarPilot remains a broad dogfood lab cockpit or becomes a small governed calendar autonomy core with a thinner control surface. The first wants evidence and flexibility. The second can approach 3,000 LOC.
