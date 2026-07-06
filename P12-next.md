According to a document from **July 3, 2026**, P12's target is not broad autonomy yet; it is a governed learning loop where ActionStream is reward truth, WorldStream is context, BiographyStream is a prior, derived signals are evidence-cited, and autonomy expands only one reversible action family at a time.

**Status input (from the completed `P12-test.md` run `20260703T224814Z-p12`, updated by Stage D2 and Step E evidence):** overall P12 baseline decision **pass**, and Step E is now **complete/pass** at run `20260706T220150Z-step-e-complete`. The release/testing instrument is pinned by that run bundle's `INSTRUMENT.sha`; `make p12-release` reports `decision: pass`; `reward_heads`, `policy_ablation`, calibration, Belief/object-level `explain()`, and explicit `CalendarPilot SelfPlay` EventKit mutation/rollback are all covered by evidence. The next behavior-changing wave is still blocked until C-VAR exists: every wave needs seed-bootstrap variance and borderline flip-rate comparison for the promote/hold decision before vs after the change. Two data-quality flags recorded in the fixture measurement snapshot must still be carried forward, not forgotten: `OTHER_intent_rate: 0.1429` (above the 0.10 gate at fixture scale) and `expected_intent_hit_rate: 0.0`.

# Working delegation layer

This document is now the team control surface for P12-next. The technical plan below stays intact; the tables in this section are the working ledgers engineers update as they annex archive repos, map source purpose, cut dead code, and keep the P12 gate green.

## Operating state

| field | value |
|---|---|
| phase | P12-next: cold-start runway + debt erasure |
| current checkpoint before this working-doc edit | `906cc68` (`chore: checkpoint p12 workspace`) |
| live product freeze | `make p12-release` from `P12-test.md` run `20260703T224814Z-p12` |
| archive root | `/Users/temp/Desktop/Destination/Do-not-reference` |
| current implementation root | `/Users/temp/Desktop/Destination/calendar-pilot-p12` |
| source purpose scope | structural rows for every file, class, function, method, nested definition, durable constant, CLI entrypoint, provider surface, frontend component, contract schema, and fixture that takes meaningful space |
| protected runway | Program A paths in §2; no deletion/consolidation/signature change without explicit promotion evidence |
| Stage A/B verdict state | **Stage C structural readiness ACHIEVED** (`20260704T041118Z-p12-next-stage-c-readiness`): archive-diff per-symbol resolution -> **54/54 files expansion-ready**, 1506 structural rows all settled + 119 waivers, 100% source-symbol coverage, 0 open blockers. **This is not line-level provenance.** `B-SA-001/002/003` resolved (duplicate folders proven P8-era; P8.5 folder is doc/runway). Retention verdicts still **deferred to Stage C** (not performed). Prior: Stage B acceptance `20260704T032235Z`; expansion `20260704T034739Z`. |

## Status vocabulary

Use exactly these statuses in the working tables so progress can be filtered without interpretation:

```text
not started        row exists, no engineer has accepted it
assigned           owner named, no durable artifact yet
inventorying       repo/file is being listed and counted
diffing            archive/current or duplicate diff is in progress
mapping            lineage or symbol-purpose rows are being filled
line-mapping       line spans are being mapped to structural rows and phases
review             artifact exists and needs peer review
annexed            archive repo is fully represented in phase_timeline.md, lineage.json, and tombstones
verified           gate/evidence checks prove the row's final verdict
blocked            blocked with a named reason, owner, and next unblock action
```

## Delegation board

| workstream | owner | status | required artifact | gate before merge | next action |
|---|---|---|---|---|---|
| Baseline freeze + LOC report | TBD | not started | `runs/p12_next_evidence/$RUN_ID/baseline/loc_report_before.json` | `make p12-release` green | implement `scripts/loc_report.py` and freeze numbers |
| Cold-start runway ops | TBD | not started | daily imported observation, shadow frontier, provider preview, calibration report | no autonomy matrix diff | write evidence target JSON and daily operator checklist |
| Archive repo annex | TBD | not started | `lineage/phase_timeline.md`, duplicate deltas, archive inventory | every repo row below has non-blank status | assign owners for all `/Do-not-reference` repos |
| Source purpose census | TBD | not started | `lineage/src_symbol_manifest.json` and file-level ledger | AST parse succeeds for all Python files | seed manifest from current `calendar-pilot-p12/src` |
| Line-level provenance | Codex | review | `runs/p12_next_evidence/20260704T060917Z-p12-next-line-provenance/lineage/line_span_manifest.jsonl`, coverage, gap report | every current line is assigned, waived, or blocked; blockers are isolated to scopes absent from accepted structural lineage | review `examples`/`tests`/`packages` blockers before Stage D |
| Reachability + root set | TBD | not started | `reachability/coverage.json`, root list, verdict coverage | deterministic + release + live-NIM + browser legs recorded; line spans available for verdicts | write root-set file after line-level pass |
| Step E instrument gate | Codex | verified | `calendar-pilot-p12/runs/p12_next_evidence/20260706T220150Z-step-e-complete/instrument/` | `make p12-release` pass plus protected Step E legs run or signed-root-listed | Step E complete; do not start destructive waves until the separate lineage/root-set and C-VAR prerequisites are ready |
| C-VAR variance gate | TBD | blocked | seed-bootstrap promote/hold variance report with borderline flip-rate before/after each behavior-changing wave | required before P13 or any compression wave that can change behavior | implement C-VAR and add it to the protected release evidence before starting the next wave |
| Legacy deletion wave | TBD | not started | tombstones for D1-D6, inverted quarantine tests | accepted Stage A/B lineage, line-level provenance for removed spans, plus Stage C verdicts for each item; `make p12-release` green after each deletion | wait for annex/source-purpose/lineage/root-set work, then start with `notification_fatigue` and `sim_v1` |
| Consolidation waves | TBD | not started | per-wave LOC delta, tombstones, survivor map | protected-path diff clean | plan ML -> backend -> frontend order |
| Current-truth docs | TBD | not started | `docs/LINEAGE.md`, README refresh, history archive pointer | `grep` finds no deleted-flow docs | draft docs index after Wave 1 |

## Blocker and decision log

| id | type | owner | status | affected rows | decision or unblock needed | next action |
|---|---|---|---|---|---|---|
| B-001 | environment | Codex Stage D2 | **resolved** (`20260705T174108Z`) | live EventKit + provider-backed self-play evidence | Resolved: `CalendarPilot SelfPlay` sandbox configured, EventKit probe targeted sandbox title, provider-backed `swift_ipc_eventkit_sandbox` self-play completed with verified readback/idempotency/rollback cleanup. This Mac used explicit `source_policy: default_if_no_local` because no local EventKit source was exposed. | none for D2; keep local-only sandbox as an environment note |
| B-002 | data | TBD | open | cold-start runway | matched examples and explicit feedback below threshold | continue daily Program A collection |
| B-003 | quality | TBD | open | frontier measurement | `OTHER_intent_rate` and `expected_intent_hit_rate` are baseline flags | freeze baseline; do not treat deletion waves as owner unless worsened |
| B-005 | instrument | TBD | open | C-VAR pre-wave certificate | Behavior-changing waves need seed-bootstrap variance and borderline flip-rate comparison for the promote/hold decision before vs after the wave; Step E does not yet provide this C-VAR certificate. | implement C-VAR, add a protected report artifact, and require it before P13/compression execution |
| B-SA-001 | lineage | Codex Stage A | **resolved** (`20260704T041118Z`) | P7 `calendar-pilot-updated 2` | Resolved: `updated 2` proven a **P8-era accumulated snapshot** (has P8 files, lacks P9 `environment/`); archive-diff shows 0 current symbols depend on it alone. Affected providers attributed P8-era first-sighting. Evidence: `blocker_resolution.md`. | none — resolved |
| B-SA-002 | lineage | Codex Stage A | **resolved** (`20260704T041118Z`) | P8 frontend duplicate pair | Resolved: `frontend 2` proven P8-era (same content test); 0 current symbols depend on it alone. `frontend/*`, `swift_bridge/*` attributed P8-era first-sighting. | none — resolved |
| B-SA-003 | lineage | Codex Stage A | **resolved** (`20260704T041118Z`) | P8.5 `calendar-pilot` dogfood/safety row | Resolved: **0 current symbols/carriers first-seen in the P8.5 folder** (no P8.5 in the first-sighting distribution); session/live/release originate P8. P8.5 confirmed doc/runway only. | none — resolved |
| B-004 | instrument | Codex | **resolved** (`20260706T220150Z`) | Step E final gate | Resolved: `p12-release` now reports `decision: pass`; `reward_heads` passes from real ActionStream reward rows, `policy_ablation` passes with per-ablation frontier/scorecard reruns, calibration passes from real `create_prep_block` human feedback rows, Belief/object-level `explain()` contract is implemented/tested, and explicit app-bundled `CalendarPilot SelfPlay` EventKit commit/verify/rollback reran with `authorization_status: full_access`. | none for Step E; keep collecting Program A feedback volume before autonomy promotion |

## Repo annex progress ledger

Every repository directory under `/Do-not-reference` gets one row. "Annexed" means the repo is no longer just an archive folder: it is represented in the phase timeline, duplicate status is known, current-path matches have been attempted, source-symbol lineage has been mined where applicable, and any deletion tombstones point back to it.

Current disposition (run `20260704T041118Z-p12-next-stage-c-readiness`): prior Stage B blockers `B-SA-001`, `B-SA-002`, and `B-SA-003` are **resolved** by archive-level per-symbol diff. `calendar-pilot-updated 2` and `calendar-pilot-frontend 2` are treated as P8-era accumulated snapshots for rows whose evidence supports that; P8.5 `calendar-pilot` is doc/runway only with 0 current symbols first-seen there. All repos remain lineage/review artifacts only; no repo reached retention judgment.

| phase | archive repo | duplicate group | owner | intake | duplicate diff | current path map | symbol/purpose map | tombstone index | status | next action |
|---|---|---|---|---|---|---|---|---|---|---|
| P6.5 | `Do-not-reference/calendar-pilot-revised` | unique | Codex Stage A | review | n/a | review | review | not started | review | Stage A early ML lineage captured in `SA-P6.5-001` through `SA-P6.5-006`; no retention judgment |
| P7 | `Do-not-reference/calendar-pilot-updated` | primary for updated pair | Codex Stage A | review | review | review | review | not started | review | Stage A P7 biography/provider/core-contract/package rows captured in `SA-P7-001` through `SA-P7-005`; duplicate delta in `SA-P7-DUP-001` |
| P7 | `Do-not-reference/calendar-pilot-updated 2` | P8-era accumulated snapshot in updated pair | Codex Stage A | review | review | review | review | not started | review | `B-SA-001` resolved in `20260704T041118Z`: 0 current symbols depend on this folder alone; row-level evidence only, no retention judgment |
| P7.5 | `Do-not-reference/calendar-pilot-executive` | primary for executive pair | Codex Stage A | review | review | review | review | not started | review | Stage A Codex planner/runtime/replay rows captured in `SA-P7.5-001` through `SA-P7.5-003`; duplicate delta in `SA-P7.5-DUP-001` |
| P7.5 | `Do-not-reference/calendar-pilot-executive 2` | duplicate of P7.5 executive | Codex Stage A | review | review | review | review | not started | review | Executive2 adds authority/safety contract deltas; row-level evidence captured with uncertainty in `SA-P7.5-DUP-001` |
| P8 | `Do-not-reference/calendar-pilot-frontend` | primary for frontend pair | Codex Stage A | review | review | review | review | not started | review | Stage A frontend/static/control-surface rows captured in `SA-P8-001` through `SA-P8-003`; duplicate delta in `SA-P8-DUP-001` |
| P8 | `Do-not-reference/calendar-pilot-frontend 2` | P8-era accumulated snapshot in frontend pair | Codex Stage A | review | review | review | review | not started | review | `B-SA-002` resolved in `20260704T041118Z`: 0 current symbols depend on this folder alone; row-level chat-first/live/runtime sightings retained |
| P8.5 | `Do-not-reference/calendar-pilot` | dogfood/safety repo | Codex Stage A | review | n/a | review | review | not started | review | `B-SA-003` resolved in `20260704T041118Z`: P8.5 folder has 0 current first-seen symbols; use as doc/runway evidence only |
| P9 | `Do-not-reference/calendar-pilot-system-framework` | unique | Codex Stage A | review | n/a | review | review | not started | review | Stage A environment substrate rows captured in `SA-P9-001` through `SA-P9-004`: trace, envelope, fsio, object protocols, router, taxonomy, invariants, selfplay backend policy |
| P10 | `Do-not-reference/calendar-pilot-deferred-pass` | unique | Codex Stage A | review | n/a | review | review | not started | review | Stage A deferred runtime rows captured in `SA-P10-001` through `SA-P10-007`: ActionLifecycle, SessionStore, plan graph, temporal controller, EventKit sandbox/bridge, ES-module frontend/runtime, live DiffusionGemma current-body expansion |
| P11 | `Do-not-reference/calendar-pilot-p11` | unique | Codex Stage A | review | n/a | review | review | not started | review | Stage A sim/autonomy/provider rows captured in `SA-P11-001` through `SA-P11-006`: FrontierService, sim_v2 self-play, provider transactions, autonomy/action lifecycle, replay/invariant hardening, DiffusionGemma package exports |

## Archive document intake ledger

The repo annex ledger handles directory snapshots. These loose documents provide phase anchors or test evidence and must be linked from `phase_timeline.md` before any repo is considered annexed.

| document group | files | purpose | owner | status | next action |
|---|---|---|---|---|---|
| Phase plans | `plan-6-revised.md`, `plan-7-revised.md`, `plan-8.md`, `plan-8-analysis.md`, `plan-9.md`, `readme.md` | P5-P9 timeline reconstruction | Codex Stage A | review | Phase anchors for `SA-P6.5-001`..`SA-P6.5-006`, `SA-P7-001`..`SA-P7-005`, `SA-P8-001`..`SA-P8-003`, and `SA-P9-001`..`SA-P9-004`; review as timeline evidence only |
| Dogfood and safety | `DOGFOODING_FRAMEWORK.md`, `dogfooding framework 2.md`, `dogfooding.md`, `thin-lab.md`, `thickening-the-lab.md` | dogfood/lab/runway lineage | Codex Stage A | review | Supports `SA-P8.5-000`..`SA-P8.5-004`, `SA-P10-004`, `SA-P10-005`, `SA-P11-002`, and `SA-P11-004` as doc/runway evidence; `B-SA-003` resolved in `20260704T041118Z`, so these docs remain timeline/runway evidence only |
| System and ML tests | `SYSTEM_FRAMEWORK.md`, `ML-E2E.md`, `ML-testing.md`, `P11-test.md` | framework gates, ML evidence, prior acceptance | Codex Stage A | review | Gate/test anchors for `SA-P9-001`..`SA-P9-004`, `SA-P10-001`..`SA-P10-007`, and `SA-P11-001`..`SA-P11-006`; do not use tests as retention or root proof |

## Source purpose census

The current Python source seed inventory is 54 files, 136 classes, 132 top-level functions, 532 methods, and 14 nested definitions, for 814 AST-level symbols before manual cleanup. That count is a starting point only: properties, dataclass fields, module constants, protocol fields, static JS components, contract schemas, fixtures, and scripts also need purpose rows when they materially shape behavior.

Important boundary: the accepted `20260704T041118Z-p12-next-stage-c-readiness`
run proves structural provenance coverage, not literal line-by-line provenance.
It is sufficient to start a retention/reachability pass, but not sufficient to
delete arbitrary line spans. Before Stage D edits, every removed or consolidated
line span must point back to a structural lineage row and either a phase-level
archive match, a current-only row, or an explicit waiver.

Required row schema for the source-purpose manifest:

During Stage A lineage discovery, fill only discovery fields. Leave
`root_reachability`, `verdict`, tombstone, deletion, and consolidation fields
blank until Stage C retention judgment.

| field | meaning |
|---|---|
| `path` | repo-relative file path |
| `symbol` | class/function/method/constant/component/schema name, or `__module__` for whole-file rows |
| `kind` | module, class, method, function, nested_def, constant, dataclass_field, provider_surface, cli_entrypoint, js_component, contract_schema, fixture |
| `line_start` / `line_end` | current location when mapped |
| `line_provenance_status` | line-level only: mapped, waived, generated, blank/comment-only, or blocked |
| `purpose` | one sentence naming the behavior this symbol exists to provide |
| `introduced_phase` | phase from archive annex, or `unknown` with reason |
| `root_reachability` | Stage C/final only: named root, coverage evidence, or `unreached` |
| `verdict` | Stage C/final only: KEEP, CONSOLIDATE, DELETE, ARCHIVE |
| `owner` | engineer accountable for the row |
| `evidence` | test, gate, trace, grep, diff, or tombstone path |

Stage A DoD for a source row:

```text
1. Every row has path.
2. Every row names the symbol or flow being discovered.
3. Every row states observed purpose.
4. Every row states introduced phase.
5. Every row points to archive evidence.
6. Every row states match type and confidence.
7. Every row records uncertainty and blockers.
8. Every row has owner/status.
9. Any row covering multiple files/classes/functions is marked as a flow-level
   discovery row with symbol_expansion_required=true in the run artifact or queue.
10. root_reachability, verdict, and tombstone fields stay blank.
```

Stage C/final DoD for a source row:

```text
1. Reachability/root evidence is filled from the explicit Stage C root set.
2. Retention verdict is assigned only after Stage A lineage and Stage B review.
3. KEEP/CONSOLIDATE/DELETE/ARCHIVE rows name their root, survivor, tombstone, or
   archive/deletion evidence as applicable.
4. No verdict is based only on tests, docs/history, examples, archive presence,
   parent-module import, or importing a parent module as proof for child symbols.
5. Any DELETE/CONSOLIDATE row names the exact current line spans it affects or
   records a blocker explaining why line-span provenance is incomplete.
6. Deletion/consolidation implementation belongs to Stage D, after Stage C
   verdicts and line-span provenance are accepted.
```

### File-level source assignment queue

Expansion disposition (run `20260704T041118Z-p12-next-stage-c-readiness`): every file below is **100% symbol-expanded with archive-diff-resolved per-symbol phases** — **all 54 files are structurally expansion-ready** (1506 rows all `stage_c_ready: true`, 0 open blockers; 119 class-attr waivers). Per-symbol introducing phases come from a cross-snapshot AST first-sighting; B-SA-001/002/003 resolved. Per-file status in `expanded_file_status.md`; per-symbol rows in `expanded_symbol_lineage.jsonl`; blocker evidence in `blocker_resolution.md`. No retention verdict assigned. This does **not** claim literal every-line provenance; that is the next required pass before Stage D edits. (Chain: Stage B `20260704T032235Z` insufficient -> expansion `20260704T034739Z` structural 100% coverage but 27 blocked -> this pass resolved blockers + mixed-phase.)

| src file | classes | top-level funcs | methods | nested defs | inventory status | purpose map | owner |
|---|---:|---:|---:|---:|---|---|---|
| `calendar-pilot-p12/src/calendar_pilot/__init__.py` | 0 | 0 | 0 | 0 | review: `SA-P7-005` | review: root package marker first appears P6.5; current version/export body exact from P7 onward | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/app.py` | 0 | 5 | 0 | 0 | review: `SA-P10-006` | review: current app/demo orchestration body exact by P10/P11; older load helper symbols predate P10 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/biography.py` | 1 | 0 | 8 | 0 | review: `SA-P7-001` | review: biography provenance and repair flow introduced P7 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/codex/__init__.py` | 0 | 0 | 0 | 0 | review: `SA-P7.5-003` | review: package export body first current match in ambiguous P7 updated2, exact by P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/codex/agent.py` | 1 | 0 | 8 | 0 | review: `SA-P7.5-003` | review: narrative Codex agent starts P6.5/P7, distinct from P7.5 tool runtime | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/codex/annotator.py` | 1 | 1 | 2 | 0 | review: `SA-P12-NF-001` | review: no archive source found; P12 signal annotator current-phase row | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/codex/live.py` | 12 | 13 | 34 | 0 | review: `SA-P8.5-003` | review: live Codex app-server path first row-level sighting in ambiguous updated2, dogfood docs trace live mode | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/codex/planner.py` | 2 | 0 | 7 | 0 | review: `SA-P7.5-001` | review: Codex tool planner introduced by P7.5 doc/source, current body later | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/codex/tools.py` | 1 | 0 | 26 | 0 | review: `SA-P7.5-001`, `SA-P11-004` | review: Codex tool runtime introduced by P7.5; autonomy matrix and FrontierService integration are P11 row-level additions | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/__init__.py` | 0 | 0 | 0 | 0 | review: `SA-P11-006` | review: diffusiongemma package starts P6.5; current exports closest to P11 after FrontierService/SelfPlayEpisode additions | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/frontier_service.py` | 2 | 0 | 4 | 0 | review: `SA-P11-001` | review: FrontierService facade introduced P11; byte-identical to current | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/live.py` | 10 | 5 | 28 | 0 | review: `SA-P10-007` | review: live DiffusionGemma/NIM client first row-level sighting in ambiguous updated2; current frontier-generation body closest to P10 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/policy.py` | 1 | 2 | 13 | 0 | review: `SA-P6.5-006`, `SA-P10-007` | review: deterministic DiffusionGemma policy core introduced P6.5; current tuning/temporal controller body closest to P10 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/reward.py` | 2 | 1 | 6 | 0 | review: `SA-P6.5-003` | review: reward anatomy introduced P6.5 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/right_moment.py` | 2 | 0 | 5 | 0 | review: `SA-P6.5-004` | review: right-moment timing model introduced P6.5 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/self_play.py` | 11 | 0 | 17 | 0 | review: `SA-P6.5-005`, `SA-P11-002` | review: self-play adversary substrate introduced P6.5; sim_v2/UserSimulator and current episode runner body closest to P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/signals.py` | 2 | 7 | 1 | 0 | review: `SA-P6.5-001` | review: raw context signal extraction introduced P6.5 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/temporal_controller.py` | 2 | 0 | 6 | 0 | review: `SA-P10-004` | review: right-moment temporal controller introduced P10 and remains exact | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/diffusiongemma/world_model.py` | 2 | 1 | 2 | 0 | review: `SA-P6.5-002` | review: candidate future sketch introduced P6.5 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/env.py` | 0 | 3 | 0 | 0 | review: `SA-P7-005` | review: local .env loader first row-level sighting in ambiguous updated2 and remains exact through P11/current | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/__init__.py` | 0 | 0 | 0 | 0 | review: `SA-P9-001` | review: environment package first appears P9; current exports exact by P10/P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/action_lifecycle.py` | 2 | 0 | 18 | 0 | review: `SA-P10-001`, `SA-P11-004` | review: ActionLifecycle extraction introduced P10; provider transaction/rate-cap/autonomy-adjacent current body closest to P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/envelope.py` | 1 | 2 | 4 | 0 | review: `SA-P9-001` | review: ActionEnvelope/rollback-state helper introduced P9 and remains exact through current body | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/fsio.py` | 0 | 3 | 0 | 0 | review: `SA-P9-001` | review: atomic JSON/text writes and append_jsonl introduced P9 and remain exact | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/invariants.py` | 1 | 18 | 1 | 0 | review: `SA-P9-003`, `SA-P11-005`, `SA-P12-NF-002` | review: initial executable invariant checker introduced P9; P11 adds I2a/I3/I5/I7 replay/provider hardening; P12 adds B-series signal-stream checks | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/label_registry.py` | 1 | 0 | 8 | 0 | review: `SA-P12-NF-002` | review: P12 signal label registry not found in archive; current docs specify governed label activation and B2 barrier | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/objects.py` | 6 | 0 | 14 | 0 | review: `SA-P9-002` | review: environment object protocol substrate introduced P9 and remains exact | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/plan_graph.py` | 2 | 3 | 4 | 0 | review: `SA-P10-003` | review: Tier-6 plan graph and rollback-order helpers introduced P10 and remain exact | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/router.py` | 3 | 0 | 4 | 0 | review: `SA-P9-002` | review: RoutedTurn/KeywordRouter/ModelIntentRouter introduced P9 and remain exact | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/selfplay_backends.py` | 2 | 0 | 0 | 0 | review: `SA-P9-004` | review: self-play backend enum and sandbox policy introduced P9 and remain exact | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/session_store.py` | 1 | 0 | 7 | 0 | review: `SA-P10-002` | review: SessionStore extraction introduced P10 and remains exact | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/signal_estimators.py` | 2 | 4 | 4 | 0 | review: `SA-P12-NF-002` | review: P12 interruption-tolerance estimator not found in archive; current docs specify derived signal estimator layer | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/signal_streams.py` | 1 | 3 | 0 | 0 | review: `SA-P12-NF-002` | review: P12 signal-stream classifier not found in archive; current docs specify action/world/biography/derived/system streams | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/taxonomy.py` | 1 | 2 | 0 | 0 | review: `SA-P9-002` | review: CanonicalIntent/normalize_intent/taxonomy health introduced P9; current near-exact with P11 formatting delta | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/environment/trace.py` | 3 | 0 | 8 | 0 | review: `SA-P9-001` | review: TraceEvent/TraceBus/SSE frame stream introduced P9 and remain exact | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/frontend/__init__.py` | 0 | 0 | 0 | 0 | review: `SA-P8-002` | review: frontend package starts in P8-era snapshots, exact by P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/frontend/launch.py` | 1 | 2 | 4 | 0 | review: `SA-P8-002` | review: launch surface starts P8-era, current body exact by P9/P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/frontend/projector.py` | 1 | 5 | 2 | 0 | review: `SA-P8-002`, `SA-P10-006`, `SA-P12-NF-002` | review: FrontendProjector first appears P9; P10 adds Glass Cockpit/lab view payload lineage; current body has P12 evidence/signal payload additions | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/frontend/runtime.py` | 2 | 13 | 2 | 0 | review: `SA-P8-002`, `SA-P10-006` | review: runtime first sighted in P8-era duplicate, current body exact by P10/P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/frontend/server.py` | 0 | 7 | 0 | 11 | review: `SA-P8-002`, `SA-P10-006` | review: server first sighted P8-era, current serve/api surface closest to P10/P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/frontend/session.py` | 1 | 3 | 93 | 3 | review: `SA-P8-002`, `SA-P8.5-001`, `SA-P10-002` | review: dogfood session state documented P8.5; P10 routes persist/restore through SessionStore and current body is closest to P10/P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/frontend/session_manager.py` | 1 | 0 | 21 | 0 | review: `SA-P8-002`, `SA-P8.5-001` | review: session manager first sighted P8-era, exact by P9/P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/frontend/surface.py` | 3 | 14 | 1 | 0 | review: `SA-P8-002` | review: surface/snapshot control surface first sighted P8-era, exact by P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/providers/__init__.py` | 0 | 0 | 0 | 0 | review: `SA-P7-003`, `SA-P11-003` | review: provider package export lineage starts P7; current transaction-boundary exports exact to P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/providers/apple_eventkit.py` | 3 | 8 | 20 | 0 | review: `SA-P7-004`, `SA-P10-005`, `SA-P11-003` | review: EventKit provider first found in P7 updated2; P10 adds sandbox/bridge shape; current provider transaction body closest to P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/providers/base.py` | 4 | 0 | 10 | 0 | review: `SA-P7-003`, `SA-P11-003` | review: provider adapter interface introduced P7; five-method transaction protocol and receipt/verification types introduced P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/providers/deterministic.py` | 2 | 0 | 17 | 0 | review: `SA-P7-004`, `SA-P11-003` | review: deterministic provider first found in P7 updated2; current transaction methods/body exact to P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/providers/stubs.py` | 4 | 0 | 11 | 0 | review: `SA-P7-003`, `SA-P11-003` | review: Google/Apple/Microsoft provider stubs introduced P7; current transaction-stub shape exact to P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/replay.py` | 3 | 2 | 37 | 0 | review: `SA-P7.5-002`, `SA-P11-005` | review: tool-call/tool-receipt replay rows introduced P7.5; P11 adds frontier/provider/tuning/artifact replay rows; P12 adds signal rows | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/swift_bridge/__init__.py` | 0 | 0 | 0 | 0 | review: `SA-P8-003` | review: Swift bridge exports refined in P8/P8 frontend2, exact by P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/swift_bridge/client.py` | 1 | 0 | 18 | 0 | review: `SA-P8-003` | review: Swift kernel client starts earlier, IPC/current body later P10/P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/swift_bridge/ipc.py` | 2 | 1 | 19 | 0 | review: `SA-P8-003` | review: Swift IPC first sighted in P8-era duplicate, exact by P10/P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/swift_bridge/protocol.py` | 1 | 0 | 8 | 0 | review: `SA-P8-003` | review: JSONL protocol first sighted in P8-era duplicate, exact by P11 | Codex Stage A |
| `calendar-pilot-p12/src/calendar_pilot/types.py` | 29 | 4 | 30 | 0 | review: `SA-P7-002`, `SA-P8.5-002`, `SA-P12-NF-002` | review: core contracts and biography types introduced P7; AuthorityGrant hardening documented P8.5/P8; P12 signal dataclasses not found in archive | Codex Stage A |

## Stage A lineage discovery log

Run reviewed: `20260704T015059Z-p12-next-stage-a`
Repair run: `20260704T024144Z-p12-next-stage-a-ledger-repair`
Evidence root: `calendar-pilot-p12/runs/p12_next_evidence/20260704T015059Z-p12-next-stage-a/lineage/`
Repair root: `calendar-pilot-p12/runs/p12_next_evidence/20260704T024144Z-p12-next-stage-a-ledger-repair/lineage/`

Scope rule: Stage A answers only "where did this come from?" Stage B answers only whether the discovery claim is defensible. No KEEP, CONSOLIDATE, DELETE, ARCHIVE, reachability, root, tombstone, deletion, or consolidation judgment is part of this log.

Detailed findings live in run-scoped JSONL, not in this control ledger.

| artifact | path |
|---|---|
| Stage A findings JSONL | `calendar-pilot-p12/runs/p12_next_evidence/20260704T015059Z-p12-next-stage-a/lineage/stage_a_findings.jsonl` |
| P7 duplicate delta | `calendar-pilot-p12/runs/p12_next_evidence/20260704T015059Z-p12-next-stage-a/lineage/updated_dup_delta_filtered.md` |
| P7.5 duplicate delta | `calendar-pilot-p12/runs/p12_next_evidence/20260704T015059Z-p12-next-stage-a/lineage/executive_dup_delta_filtered.md` |
| P8 duplicate delta | `calendar-pilot-p12/runs/p12_next_evidence/20260704T015059Z-p12-next-stage-a/lineage/frontend_dup_delta_filtered.md` |
| Stage A/B review summary | `calendar-pilot-p12/runs/p12_next_evidence/20260704T024144Z-p12-next-stage-a-ledger-repair/lineage/stage_a_review_summary.md` |
| Stage A/B review summary JSON | `calendar-pilot-p12/runs/p12_next_evidence/20260704T024144Z-p12-next-stage-a-ledger-repair/lineage/stage_a_review_summary.json` |
| Duplicate delta summary | `calendar-pilot-p12/runs/p12_next_evidence/20260704T024144Z-p12-next-stage-a-ledger-repair/lineage/duplicate_delta_summary.md` |
| Loose document intake review | `calendar-pilot-p12/runs/p12_next_evidence/20260704T024144Z-p12-next-stage-a-ledger-repair/lineage/loose_doc_intake_review.md` |
| Symbol expansion queue | `calendar-pilot-p12/runs/p12_next_evidence/20260704T024144Z-p12-next-stage-a-ledger-repair/lineage/symbol_expansion_queue.jsonl` |
| Ignored retention artifacts | `calendar-pilot-p12/runs/p12_next_evidence/20260704T024144Z-p12-next-stage-a-ledger-repair/lineage/ignored_retention_artifacts.md` |
| P12-next update note | `calendar-pilot-p12/runs/p12_next_evidence/20260704T024144Z-p12-next-stage-a-ledger-repair/lineage/p12_next_updates.md` |

Finding count: 44.

Phase summary: P6.5 6; P7 6; P7.5 3; P6.5/P7 overlap 1; P8 4; P8.5 doc/runway 5; P9 4; P10 7; P11 6; P12 current 2.

Blocker summary:

| id | status | affected discovery | unblock needed |
|---|---|---|---|
| B-SA-001 | resolved | P7 `calendar-pilot-updated 2` | Resolved `20260704T041118Z`: updated2 proven P8-era (P8 files present, P9 `environment/` absent); 0 symbols depend on it alone. |
| B-SA-002 | resolved | P8 frontend duplicate pair | Resolved `20260704T041118Z`: frontend2 proven P8-era (same test); 0 symbols depend on it alone. |
| B-SA-003 | resolved | P8.5 dogfood/session/live/release lineage | Resolved `20260704T041118Z`: 0 current symbols first-seen in the P8.5 folder; those files originate P8, P8.5 is doc/runway. |

Grouped finding rule: any Stage A row covering multiple files, classes, functions, contracts, scripts, or a named flow is a flow-level discovery row. It has `symbol_expansion_required: true` in `symbol_expansion_queue.jsonl`. Flow-level discovery is not enough for Stage C retention judgment; Stage C must expand to symbol/file rows before assigning any retention verdict.

Quarantine note: prior verdict/tombstone/deletion-candidate artifacts from `20260704T013457Z-p12-next-lineage` are ignored for this Stage A/B pass and are listed in `ignored_retention_artifacts.md`. They are not lineage evidence.

## Stage B acceptance ledger (historical; superseded for readiness)

Run reviewed: `20260704T032235Z-p12-next-stage-b-acceptance` (Git SHA `906cc68`).
Scope: accept/correct/block Stage A/B lineage and decide symbol/file expansion sufficiency. No retention verdicts, roots, tombstones, deletions, or consolidations. Detailed rows live in run-scoped JSONL, not inline here.

| artifact | path |
|---|---|
| Acceptance matrix (44 rows) | `calendar-pilot-p12/runs/p12_next_evidence/20260704T032235Z-p12-next-stage-b-acceptance/review/stage_b_acceptance_matrix.jsonl` |
| Acceptance summary | `calendar-pilot-p12/runs/p12_next_evidence/20260704T032235Z-p12-next-stage-b-acceptance/review/stage_b_acceptance_summary.md` |
| Symbol expansion manifest (54 files) | `calendar-pilot-p12/runs/p12_next_evidence/20260704T032235Z-p12-next-stage-b-acceptance/lineage/symbol_expansion_manifest.jsonl` |
| File expansion status | `calendar-pilot-p12/runs/p12_next_evidence/20260704T032235Z-p12-next-stage-b-acceptance/lineage/file_expansion_status.md` |
| Blockers remaining | `calendar-pilot-p12/runs/p12_next_evidence/20260704T032235Z-p12-next-stage-b-acceptance/lineage/blockers_remaining.md` |
| AST coverage evidence | `calendar-pilot-p12/runs/p12_next_evidence/20260704T032235Z-p12-next-stage-b-acceptance/lineage/ast_coverage_raw.json` |
| P12-next update note | `calendar-pilot-p12/runs/p12_next_evidence/20260704T032235Z-p12-next-stage-b-acceptance/docs/p12_next_updates.md` |

This section records the Stage B exit state from `20260704T032235Z-p12-next-stage-b-acceptance`. Its blocker and sufficiency state is historical: Stage C readiness was later achieved by `20260704T041118Z-p12-next-stage-c-readiness`, which resolved `B-SA-001`, `B-SA-002`, and `B-SA-003`.

Lineage acceptance at Stage B exit (44 findings): **39 accepted, 2 corrected, 3 blocked.**

- Blocked at Stage B exit (whole-folder duplicate collapse / archive-repo intake, reduced to row-level evidence): `SA-P7-DUP-001` (B-SA-001), `SA-P8-DUP-001` (B-SA-002), `SA-P8.5-000` (B-SA-003). These blockers were resolved by the later Stage C readiness run.
- Corrected (`source_archive_repo` normalized to explicit `P12 current / not found`; confirmed current-phase, not archive lineage): `SA-P12-NF-001`, `SA-P12-NF-002`.
- Accepted: all other source flow-rows plus phase-adjacent duplicate delta `SA-P7.5-DUP-001`. Row-level rows under then-open blockers were accepted with the blocker attached: `SA-P7-004` (B-SA-001); `SA-P8-001/002/003` (B-SA-002); `SA-P8.5-001/002/003/004` (B-SA-003).

Symbol/file expansion sufficiency at Stage B exit: **INSUFFICIENT.** All 40 source flow-rows remained `symbol_expansion_required: true`. Independently measured core-symbol coverage was **20.8% (169/813 AST symbols named)**; 0 of 62 module constants and 0 of 667 class-level/dataclass fields were represented or waived. Every file in the file-level source assignment queue was expansion-insufficient; per-file gaps and unnamed-symbol lists are in `symbol_expansion_manifest.jsonl`. This was superseded by the Stage C readiness run.

Blocker carry-forward at Stage B exit: B-SA-001, B-SA-002, B-SA-003 remained open; no blocker was resolved and none was newly opened in that pass. All three are now resolved in `20260704T041118Z-p12-next-stage-c-readiness`.

## Stage C readiness (structural symbol/file expansion)

Run: `20260704T034739Z-p12-next-symbol-expansion` (Git SHA `906cc68`).
Scope: expand flow-level lineage into symbol/file-level rows + waivers. No retention verdicts, roots, tombstones, deletions, or consolidations. Detail rows live in run-scoped JSONL, not inline here.

| artifact | path |
|---|---|
| Expanded symbol lineage (1493 rows) | `calendar-pilot-p12/runs/p12_next_evidence/20260704T034739Z-p12-next-symbol-expansion/lineage/expanded_symbol_lineage.jsonl` |
| Waivers (127) | `calendar-pilot-p12/runs/p12_next_evidence/20260704T034739Z-p12-next-symbol-expansion/lineage/waivers.jsonl` |
| Coverage report | `calendar-pilot-p12/runs/p12_next_evidence/20260704T034739Z-p12-next-symbol-expansion/lineage/coverage_report.json` |
| Expanded file status | `calendar-pilot-p12/runs/p12_next_evidence/20260704T034739Z-p12-next-symbol-expansion/lineage/expanded_file_status.md` |
| Stage C readiness summary | `calendar-pilot-p12/runs/p12_next_evidence/20260704T034739Z-p12-next-symbol-expansion/review/stage_c_readiness_summary.md` |
| P12-next update note | `calendar-pilot-p12/runs/p12_next_evidence/20260704T034739Z-p12-next-symbol-expansion/docs/p12_next_updates.md` |

Structural coverage: **100% of current `src/calendar_pilot` symbols/carriers** — 814 AST symbols + 69 module constants + 549 dataclass fields rowed; 119 non-dataclass class attributes waived. Non-src carriers: 21 contract schemas + 10 frontend carriers + 30 scripts rowed, 8 scripts waived. Every row carries `retention_verdict: null`; no root/reachability claim; no literal line-by-line provenance claim.

AST reconciliation: prior 813 vs ledger 814 = the nested class `frontend/server.py::Handler` (defined in `serve()`). Counting all ClassDefs → 137 classes / 541 methods / 4 nested = **814**; every definition is rowed, so the boundary no longer affects coverage.

Initial expansion-run status: **partial.** 27 of 54 files were **expansion-ready** (all symbols settled, no blocker). 27 were **expansion-blocked**: 16 by then-open blockers (`B-SA-001`: `providers/deterministic.py`, `apple_eventkit.py`; `B-SA-002`: `frontend/*`, `swift_bridge/*`; `B-SA-003`: `codex/live.py`, `types.py`, `frontend/session.py`, `session_manager.py`), and 11 mixed-phase files (`replay.py`, `self_play.py`, `codex/tools.py`, `action_lifecycle.py`, `providers/base.py`, `invariants.py`, `policy.py`, `providers/stubs.py`, `biography.py`, `signals.py`, `providers/__init__.py`) whose file-inherited symbols needed an archive-level per-symbol diff. This was superseded by the readiness-achieved update below.

### Update — Stage C readiness ACHIEVED (`20260704T041118Z-p12-next-stage-c-readiness`)

Both blocking causes were cleared by an archive-level per-symbol diff (`archive_index.py`) across all 11 snapshots. Result: **54/54 files structurally expansion-ready**, 1506 rows all `stage_c_ready: true`, 0 open blockers, 100% source-symbol coverage.

| artifact | path |
|---|---|
| Resolved symbol lineage (1506 rows) | `calendar-pilot-p12/runs/p12_next_evidence/20260704T041118Z-p12-next-stage-c-readiness/lineage/expanded_symbol_lineage.jsonl` |
| Waivers (119) | `…/20260704T041118Z-p12-next-stage-c-readiness/lineage/waivers.jsonl` |
| Blocker resolution evidence | `…/20260704T041118Z-p12-next-stage-c-readiness/lineage/blocker_resolution.md` |
| Coverage report | `…/20260704T041118Z-p12-next-stage-c-readiness/lineage/coverage_report.json` |
| Expanded file status (54/54 ready) | `…/20260704T041118Z-p12-next-stage-c-readiness/lineage/expanded_file_status.md` |
| Stage C readiness summary | `…/20260704T041118Z-p12-next-stage-c-readiness/review/stage_c_readiness_summary.md` |
| P12-next update note | `…/20260704T041118Z-p12-next-stage-c-readiness/docs/p12_next_updates.md` |

Method: cross-snapshot AST first-sighting; ambiguous duplicates positioned P8-era by content (P8 files present, P9 `environment/` absent). Each symbol's `introduced_phase` = earliest name-matching snapshot; body stabilization tracked separately. Blockers resolved: `updated 2`/`frontend 2` proven P8-era accumulated snapshots; **0 symbols depend on an ambiguous folder alone**, **0 first-seen in the P8.5 folder**. Refinements over the coarse flow rows include `BiographyStore`/`RawCalendarObservation` at P6.5 (not P7). Retention verdicts remain deferred — Stage C is now unblocked, not executed.

## Line-level provenance pass (required before Stage D edits)

The next implementation pass upgrades structural lineage into current-line
provenance. It does not redo Stage A/B lineage; it attaches exact line spans to
the accepted structural rows and records any lines that cannot be safely mapped.

Line-level provenance answers: "which accepted lineage row owns this current
line span, and can Stage C/Stage D cite that span directly?" It is stricter than
symbol readiness and narrower than retention judgment.

Required inputs:

```text
accepted structural lineage:
  calendar-pilot-p12/runs/p12_next_evidence/20260704T041118Z-p12-next-stage-c-readiness/lineage/expanded_symbol_lineage.jsonl
accepted waivers:
  calendar-pilot-p12/runs/p12_next_evidence/20260704T041118Z-p12-next-stage-c-readiness/lineage/waivers.jsonl
current tree:
  calendar-pilot-p12/{src,scripts,contracts,frontend,examples,tests,packages}
archive root for escalation only:
  /Users/temp/Desktop/Destination/Do-not-reference
```

Line-level manifest schema:

```json
{
  "path": "",
  "line_start": 0,
  "line_end": 0,
  "line_kind": "",
  "owning_symbol": "",
  "owning_lineage_row_id": "",
  "introduced_phase": "",
  "source_archive_repo": "",
  "archive_evidence_path": "",
  "match_type": "",
  "match_confidence": "",
  "current_text_hash": "",
  "purpose_observed": "",
  "line_provenance_status": "",
  "waiver_reason": "",
  "uncertainty": "",
  "stage_c_use": ""
}
```

Line kinds:

```text
code                  executable or declarative behavior
import                import/export surface
constant              module/global/class constant line
schema                JSON schema line or key span
frontend              HTML/CSS/JS behavior line
script_entry          CLI/script command surface
test_fixture          test vector or fixture line
comment_docstring     human-facing implementation context
blank                 blank/format-only line
generated             generated or vendored line, if any
```

Line provenance statuses:

```text
mapped                assigned to an accepted structural lineage row
mapped_current_only   P12-current row, not found in archive, evidence cited
waived_blank          blank/format-only line
waived_comment        comment/docstring with no independent behavior
waived_generated      generated/vendored line, generator or source named
blocked              cannot map without archive reinspection or human decision
```

Acceptance:

```text
1. Every nonblank current line in src, scripts, contracts, frontend, examples,
   tests, and packages is mapped, waived, or blocked.
2. Every mapped line span names one accepted structural lineage row.
3. Every DELETE/CONSOLIDATE candidate has exact line spans before Stage D.
4. Blank/comment/docstring waivers are counted separately and cannot hide
   executable behavior.
5. Imported tests/docs/examples may be mapped as carriers, but they still do
   not prove KEEP unless tied to a frozen root in Stage C.
6. Output is run-scoped JSONL; do not paste line manifests inline in this file.
```

### Update — line provenance run `20260704T060917Z-p12-next-line-provenance`

Artifacts:

| artifact | path |
|---|---|
| Line inventory | `calendar-pilot-p12/runs/p12_next_evidence/20260704T060917Z-p12-next-line-provenance/lineage/line_inventory.jsonl` |
| Line span manifest | `calendar-pilot-p12/runs/p12_next_evidence/20260704T060917Z-p12-next-line-provenance/lineage/line_span_manifest.jsonl` |
| Line span coverage | `calendar-pilot-p12/runs/p12_next_evidence/20260704T060917Z-p12-next-line-provenance/lineage/line_span_coverage.json` |
| Line span gaps | `calendar-pilot-p12/runs/p12_next_evidence/20260704T060917Z-p12-next-line-provenance/lineage/line_span_gaps.md` |
| Line span waivers | `calendar-pilot-p12/runs/p12_next_evidence/20260704T060917Z-p12-next-line-provenance/lineage/line_span_waivers.jsonl` |
| Review summary | `calendar-pilot-p12/runs/p12_next_evidence/20260704T060917Z-p12-next-line-provenance/review/line_provenance_summary.md` |
| Update note | `calendar-pilot-p12/runs/p12_next_evidence/20260704T060917Z-p12-next-line-provenance/docs/p12_next_updates.md` |

Counts: 170 scoped files, 29,888 current lines, 20,279 mapped to accepted structural rows, 3,358 waived (3,001 blank; 357 comment/docstring; 0 generated), 6,251 blocked across 41 files. Blockers are confined to `examples`, `tests`, and `packages`, which were in current scope but absent from the accepted Stage C structural lineage artifact. No retention verdicts assigned.

## Stage C₀ — retention framework (instrument built; verdicts still deferred to C₁)

Run: `20260704T221313Z-p12-next-stage-c0-framework` (Git SHA `a058bb2`). Stage C is split: C₀ built the retention framework from direct code reading (~35 runtime files, `path:line`-cited); **no verdicts were assigned and no implementation code was touched.** Framework artifacts live under `calendar-pilot-p12/runs/p12_next_evidence/20260704T221313Z-p12-next-stage-c0-framework/`: `framework/organ_map.md`, `framework/root_model.md`, `framework/language_primitives.md`, `framework/invariant_map.md`, `framework/code_reading_notes.md`, `framework/complexity_duplication_map.md`, `framework/proposed_retention_taxonomy.md`, `framework/evidence_requirements.md`, `framework/prior_stage_c_risks.md`, `framework/candidate_pressure_map.md`, `framework/recommended_next_pass.md`, and `review/retention_framework_review.md` (one-sitting synthesis; compact note in `docs/p12_next_updates.md`).

Status: the framework supersedes parts of this ledger's cleanup intuitions and C₁ should run from it. Load-bearing findings: the served frontend still consumes the legacy snapshot via `view_state.v2.legacy_state` (`projector.py:60` → `frontend/static/js/main.js`), so the `session.py` quota is sequenced behind a JS weaning; three of nine `p12-release` legs are placebo emitters (policy-ablation, reward-heads, calibration — the protected calibration script also lacks the `--family` flag §2 documents), so they can anchor interface-keeps only; D1/D3 are largely done in behavior (naming + one contract field remain), D2 is a one-line default flip that contradicts `ARCHITECTURE.md`'s sim_v1 retention note, D5 is confirmed dead from the served entry; ~54 statically-dead provider-plumbing lines sit in `codex/tools.py:390-443`; several §6 consolidation hints do not survive reading (swift client+ipc "shared framing", right_moment→temporal-controller fold, "3 browser E2E implementations", per-script duplication estimates). C₁ verdicts ~26 flow-clusters (not 1,506 symbols) under the framework's taxonomy (KEEP-B/KEEP-I/CONSOLIDATE/DELETE/ARCHIVE/DEFER), its coverage-union + runtime-mode matrix (live legs run or DEFER — never default-delete; `run_live_nim_schema_gate.py` is not a make target and must be root-listed), and its humane exception (B-invariant/legibility surfaces may consolidate, never delete); it reads the line-provenance summaries by default and opens `line_span_manifest.jsonl` only per candidate span; `examples`/`tests`/`packages` blockers do not block runtime verdicts.

## Stage C₁ — retention verdicts assigned (flow-clusters; verdicts done, deletion still Stage D)

Run: `20260705T021039Z-p12-next-stage-c1-verdicts` (Git SHA `8cec9d4`; runtime source byte-identical to C₀ `a058bb2`). C₁ **applied** the C₀ framework and produced the accepted Stage-C verdict artifacts. **No implementation code was changed, moved, deleted, refactored, or tombstoned; this ledger is not rewritten.**

Method (binding C₀ decision honored): verdicted **flow-clusters, not 1,506 symbols** — 41 home clusters that **partition all 128 files / 1,506 accepted structural rows exactly once** (0 orphans/overlaps, verified) + 14 span-scoped carve-outs = **55 verdict rows** under `retention_verdict.v1`. Ran **6 real coverage legs** (py-test 159✓, check-invariants 0-violations, p12-release ok:true, swift-ipc-test 9✓, swift-test 17✓, browser-e2e✓) + static dispatch/JS audit; a prebuilt Swift kernel-server binary + Chrome were present, so swift-ipc-test and browser-e2e RAN — pulling the Swift IPC client and served JS app out of DEFER into KEEP-B. Swift logs are captured in the run as `reachability/leg_swift_ipc.log` and `reachability/leg_swift_test.log`.

Distribution (by cluster): **KEEP-B 36 · CONSOLIDATE 12 · DEFER 4 · KEEP-I 2 · DELETE 1 · ARCHIVE 0**; 18 humane clusters, **0 humane DELETE/ARCHIVE**. Load-bearing outcomes: (1) **one clean DELETE** — the dispatch-dead provider quartet `codex/tools.py:390-443` (survivor `action_lifecycle.py:456-489`); (2) `legacy_state` is **live product** (browser-E2E-proven) — `frontend.legacy_state_bridge` CONSOLIDATE is the root of the frontend order, `session.py` compression sequenced behind the JS weaning (2 genuine v2 gaps: `sidebar.sessions`/`recent_runs`); (3) `app.js` **not** deletion-ready — `run_dogfood_release.py:185-186` fetches `/app.js`, release-harness migration is a prerequisite; (4) `sim_v1` is **reached** (test_self_play.py:17) → CONSOLIDATE (flip default → `sim_v2.1`, pin fixtures, fix `ARCHITECTURE.md:62`/`SELF_PLAY.md:19-21`); (5) 4 placebo/thin gates → KEEP-I (calibration protected — thinness reported, not fixed, missing `--family`); (6) 4 DEFER verdicts plus one deferred live-NIM span inside a KEEP-B cluster. Quota (current `/src` 13,949): immediate ~low-single-digits, low-teens after the strangler — the ≥50% TOTAL-LOC target is a refactor-and-sequence problem, not deletion. **Step D readiness: Yes for Wave 1 only (quartet DELETE + formal independent structural folds: `codex.auth_state_dup`, `codex.redact_secret_dup`, `scripts.lab_hub_structure`, `scripts.browser_e2e_pipeline_fold`), with prerequisites for the CONSOLIDATE chains, No for the quota-bearing frontend work and the DEFERs.**

Artifacts under `calendar-pilot-p12/runs/p12_next_evidence/20260705T021039Z-p12-next-stage-c1-verdicts/`: `reachability/{root_set.md, coverage_union.json, dispatch_grep.txt, js_legacy_state_audit.md}`, `framework-verdicts/{cluster_inventory.jsonl, verdict_rows.jsonl, defer_ledger.md, placebo_gates.md}`, `review/{c1_verdict_review.md, consolidation_order.md, quota_honesty.md}`, `docs/p12_next_updates.md`.

## Stage D Wave 1 — narrow deletion/consolidation landed (dogfood bundle blocker remains)

Run: `calendar-pilot-p12/runs/p12_next_evidence/20260705T035713Z-p12-next-stage-d-wave1/`. Implemented only the accepted Wave 1 rows: `codex.provider_quartet_dead`, `codex.auth_state_dup`, `codex.redact_secret_dup`, `scripts.lab_hub_structure`, and `scripts.browser_e2e_pipeline_fold`. The dead Codex provider quartet was deleted from `CodexToolRuntime` with an inverted quarantine test; auth-state truth now lives in `frontend.runtime`; Codex/NIM secret redaction share a primitive while keeping distinct key sets; the lab hub imports through `scripts.lab_modules`; browser E2E implementation lives in `run_browser_e2e.py` with `run_external_browser_flow.py` kept as a compatibility shim. `scripts/browser_e2e.spec.mjs` was explicitly retained as optional Node-runner coverage. `scripts/build_macos_app.sh` gained executable mode only so the frozen `mac-app-build` target can run.

Validation: `make py-test` (160✓, 10 skipped), `make check-invariants` (0 violations), `make p12-release` (ok:true), `make browser-e2e` (CDP pass), `make swift-test` (17✓), and `make swift-ipc-test` (9✓) passed; logs are under the run's `logs/`. Fixture app access-point validation passed at `http://127.0.0.1:8787` via Chrome/CDP: shell loaded (sidebar/conversation/composer/inspector), fixture action path exercised goal→stage→commit→undo→feedback→replay export, 87 replay records, no live Codex/NIM/EventKit/provider writes. `make dogfood-release` was run and remains red outside Wave 1: bundled app sanity launches/plans/stages but does not reach commit/undo/feedback in CDP, occupied-port launch refuses connection, and artifact validation misses the dependent bundle-browser artifacts. Report: `step_d_wave1_report.md`.

## Stage D blocker-fix pass — dogfood/live gates green; EventKit mutation still gated

Run: `calendar-pilot-p12/runs/p12_next_evidence/20260705T043439Z-p12-next-stage-d-blocker-fixes/`. This pass fixed the dogfood app-bundle CDP blocker, the occupied-port launch race, and advanced the C1 non-Wave-1 chains that were safe to land now: `frontend.legacy_state_bridge`, `frontend.static_legacy`, `dg.self_play.sim_v1`, `dg.fatigue_field_residue`, `env.envelope_v1_flatten`, and `codex.plan_ordering_triplication`. The served JS no longer reads `legacy_state`; `app.js` and `frontend_state.sample.json` are deleted; runtime envelopes are v2/r1-only; `sim_v2.1` is the default; fatigue residue is replaced by interruption-tolerance vocabulary; plan ordering has one shared validator. Bulk `frontend.session_brain` compression is not landed; the prerequisite JS weaning is complete, so it is now a separate high-risk refactor rather than a dependency blocker.

Validation: `make py-test`, `make check-invariants`, `make p12-release`, `make browser-e2e`, `make dogfood-release`, `make swift-test`, `make swift-ipc-test`, `scripts/run_live_nim_schema_gate.py`, `make live-diffusiongemma-e2e`, and `make live-codex-e2e` passed with logs in the run directory. Fixture app access-point validation also passed at `http://127.0.0.1:8787` via Chrome/CDP. `make live-eventkit-e2e` was run only in non-mutating mode and recorded `authorization_status: write_only`, `mutation_enabled: false`; the real Apple Calendar write/rollback probe remains blocked until full Calendar access and explicit `CALENDAR_PILOT_EVENTKIT_MUTATION=1` authorization. Report: `step_d_blocker_fix_report.md`.

## Stage D2 — frontend fixture conversation/session-brain decomposition landed

Run: `calendar-pilot-p12/runs/p12_next_evidence/20260705T053214Z-p12-next-stage-d2-session-brain/`. Implemented only the now-unblocked frontend Chain F work: extracted the fixture/local conversation subsystem from `frontend/session.py` into `frontend/session_conversation.py`, and decomposed `DogfoodSessionState` through focused snapshot and persistence controllers while preserving `DogfoodSessionState` as the public composition root. `session.py` line count: **2222 → 1316**. This is decomposition, not global LOC deletion: moved code counts zero; the touched session modules total 2308 lines after seam overhead. `legacy_state` remains absent from product frontend reads.

Validation: `make py-test`, `make check-invariants`, `make p12-release`, `make browser-e2e`, `make dogfood-release`, `make swift-test`, and `make swift-ipc-test` passed with logs in the D2 run directory. Fixture app access-point validation passed at `http://127.0.0.1:8787`: browser/CDP exercised shell load, plan→stage→commit→undo→feedback, authority/self-play/replay export; an additional local composer tool path routed `show replay trace` to `query_replay_trace` without live Codex. Report: `step_d2_session_brain_report.md`.

## Stage D EventKit blocker fix — live write/rollback probe unblocked

Run: `calendar-pilot-p12/runs/p12_next_evidence/20260705T055514Z-p12-next-eventkit-blocker-fix/`. With operator-granted Apple Calendar full access, the app-bundled EventKit bridge passed the live materialization probe: commit `committed`/`materialized`, undo `reverted`, provider rollback `rollback_verified`, 14 replay records. The dogfood release harness now scopes `CALENDAR_PILOT_EVENTKIT_RELEASE_BRIDGE` to the live EventKit sub-gate and sets `CALENDAR_PILOT_REQUIRE_EVENTKIT=1`, so the opt-in release gate performs a real write/rollback probe without poisoning fixture runtime-mode tests. Validation: focused release-gate unit test, `make live-eventkit-e2e` with mutation, and `CALENDAR_PILOT_RUN_LIVE_EVENTKIT_RELEASE=1 CALENDAR_PILOT_EVENTKIT_RELEASE_BRIDGE=… make dogfood-release` all passed. EventKit permission/environment hold is resolved for this machine. Remaining blockers are the protected Program A cold-start runway / `create_prep_block` evidence hold and the already-documented placebo/thin gate follow-ups; no live EventKit mutation blocker remains. Report: `eventkit_blocker_fix_report.md`.

## Stage D2 official pipeline follow-up — seeds/lab/runway exercised

Run: `calendar-pilot-p12/runs/p12_next_evidence/20260705T174108Z-p12-next-stage-d2-official-pipelines/`. Reviewed current and historical docs for the official seed/EventKit/test pipelines. Found `scripts/seed_calendar_corpus.py`, generated and validated the locked 120-file seed corpus, ran `make lab-validate-seeds`, and completed `make lab-run SEED=experiments/seeds/seed_founder_baseline.json RUNTIME=fixture`. The documented Program A command line was ahead of the scripts (`--family create_prep_block` was documented but unparsed), so `run_shadow_frontier.py` and `make_calibration_report.py` now accept additive `--family` and record family-scoped shadow/calibration output without changing authority or write behavior. The Program A shadow path now runs end-to-end: imported fixture/local observation tagged `apple_eventkit`, 1 `create_prep_block` shadow candidate, 1 provider preview, 0 commits, calibration still `hold` with 0 matched examples. Root `/Do-not-reference` docs identify the recent sandbox setup: a calendar titled `CalendarPilot SelfPlay` plus `CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1` and `CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay"`; P11 used a similar `CalendarPilot Sandbox` unblock. Current `run_live_eventkit_e2e.py` had regressed to targeting `default`; restored P11 env-targeting behavior, made the Swift bridge fail closed for unavailable explicit calendar ids/titles, added an explicit `ensure_calendar` setup command, and fixed EventKit verification to use fresh provider readback with stable created IDs. This machine exposed no local EventKit source, so `CalendarPilot SelfPlay` was created with explicit `source_policy: default_if_no_local`; all writes still targeted only that sandbox title. Provider-backed EventKit self-play completed: 5 `swift_ipc_eventkit_sandbox` episodes on a run-local `CalendarPilot SelfPlay` seed, all `create_prep_block`, 0 denials, first commit `materialized`, verify `verified` with `local_time_echo_ok: true`, later write idempotent, replay invariants `ok: true`, rollback cleanup `rollback_verified: true` and 0 unverified rollback records. Final gates passed: focused script/provider tests, `make py-test`, `make check-invariants`, `make p12-release`, `make browser-e2e`, `make dogfood-release`, `make swift-test`, `make swift-ipc-test`, `make mac-app-build`, sandboxed mutating EventKit probe, and sandboxed live-EventKit-enabled `make dogfood-release`. Stage D2 is complete. Remaining holds are evidence-only: `create_prep_block` promotion still lacks matched examples/explicit feedback volume, and the broader placebo/thin gate follow-ups remain tracked. Report: `stage_d2_official_pipelines_report.md`.

## Step E instrument gate — complete before further destructive compression

Original review after the P12-P17 architecture pass: Stage D2 proved the EventKit/provider-backed runway on this machine, but it did not make `make p12-release` a sufficient ruler for compression. The release target exercised the deterministic spine while live Codex, live DiffusionGemma/NIM, live EventKit, Swift IPC, browser E2E, and dogfood release evidence lived beside it. Three release legs were too thin to certify behavioral deletion: `reward_heads` reported constant zero purity violations, `policy_ablation` returned pass-shaped ablations without re-grading candidate behavior, and `calibration` emitted insufficient-data `hold` while the release wrapper still counted it as green. Section 8 became the binding Step E instrument gate: make the ruler truthful, pin it, record known-red flags, and only then continue destructive waves.

Update — Step E run `20260706T191434Z-step-e-instrument` (instrument SHA `84fd6bd0da17f0f1aed4d6222f56373732757caf`; evidence `calendar-pilot-p12/runs/p12_next_evidence/20260706T191434Z-step-e-instrument/instrument/`) landed as **hold**, not pass. Local gates passed: focused Step E tests, `make py-test`, `make check-invariants`, `make contract-vectors`, `make swift-ipc-test`, `make browser-e2e`, and `make dogfood-release`. Live legs: `make live-codex-e2e` and `make live-diffusiongemma-e2e` ran and passed; explicit `CalendarPilot SelfPlay` `make live-eventkit-e2e` was root-listed because the probe reported `authorization_status: write_only`, `configured: false`, and `mutation_enabled: false`. `reward_heads` now scans replay rows and holds on `consumed_action_rows: 0`; synthetic non-ActionStream reward evidence fails with row ids. `policy_ablation` now reuses named `frontier_diff` + `scorecard` + reward-head inputs and holds when reward evidence holds or inputs are empty/malformed. `calibration` preserves `matched_examples: 0`, family `create_prep_block`, and `decision: hold`. Known-red flags are pinned in `known_red_flags.json`: `OTHER_intent_rate: 0.1429`, `expected_intent_hit_rate: 0.0`, `matched_examples: 0`, `create_prep_block_promotion: hold`, `calibration_decision: hold`. Belief/object-level `explain()` is explicitly held in `belief_explain_report.md`. No deletion/compression work landed.

Update — Step E blocker-fix run `20260706T193733Z-step-e-blocker-fix` (instrument SHA `84fd6bd0da17f0f1aed4d6222f56373732757caf`; evidence `calendar-pilot-p12/runs/p12_next_evidence/20260706T193733Z-step-e-blocker-fix/instrument/`) remains **hold**. `reward_heads` now passes from a derived real ActionStream reward replay with 12 included action reward rows and 5 excluded non-ActionStream reward payload rows recorded in the manifest; `policy_ablation` now passes with 8 per-ablation frontier/scorecard reruns. Calibration remains hold with `matched_examples: 0`; `live-eventkit-e2e` was invoked with `CalendarPilot SelfPlay` sandbox mutation env but remains root-listed on `authorization_status: write_only`, `configured: false`, `mutation_enabled: true`; Belief/object-level `explain()` remains held. Required local gates passed except `p12-release`, which correctly exits as `decision: hold`. No deletion/compression work landed.

Update — Step E current-blockers run `20260706T211543Z-step-e-current-blockers` (instrument SHA `84fd6bd0da17f0f1aed4d6222f56373732757caf`; evidence `calendar-pilot-p12/runs/p12_next_evidence/20260706T211543Z-step-e-current-blockers/instrument/`) remains **hold**. Explicit `CalendarPilot SelfPlay` EventKit probe was rerun with mutation env enabled and is still root-listed on `authorization_status: write_only`, `configured: false`, `mutation_enabled: true`, `materialization.status: blocked`; no calendar mutation materialized. `p12-release` was rerun and preserved the fixed state: `reward_heads` passes with 12 ActionStream reward rows and `policy_ablation` passes with 8 per-ablation reruns. Calibration remains hold for `create_prep_block` with `matched_examples: 0`; a replay scan found 12 create-prep reward rows but 0 action/create-prep feedback rows, so no calibration pass was claimed. Belief/object-level `explain()` remains the prior object-contract hold. No code, deletion, or compression work landed.

Update — Step E finish run `20260706T212343Z-step-e-finish` (instrument SHA `84fd6bd0da17f0f1aed4d6222f56373732757caf`; evidence `calendar-pilot-p12/runs/p12_next_evidence/20260706T212343Z-step-e-finish/instrument/`) remains **hold**. A narrow EventKit instrument fix now overwrites stale `eventkit_materialization.json` on blocked/skipped probes; the rerun still root-lists explicit `CalendarPilot SelfPlay` EventKit on `authorization_status: write_only`, `configured: false`, `mutation_enabled: true`, `materialization.status: blocked`, so no calendar mutation materialized. `p12-release` remains `decision: hold`; `reward_heads` stays pass with 12 ActionStream reward rows and `policy_ablation` stays pass with 8 per-ablation reruns. Calibration remains hold for `create_prep_block` with `matched_examples: 0`; refreshed scan found 12 create-prep reward rows but 0 ActionStream/create-prep feedback rows. Belief/object-level `explain()` remains the prior object-contract hold. Required code-change gates passed: `make py-test`, `make check-invariants`, `make contract-vectors`, `make p12-release` (hold), `make swift-ipc-test`, `make browser-e2e`, and `make dogfood-release`.

Update — Step E retry run `20260706T214346Z-step-e-retry` (instrument SHA `84fd6bd0da17f0f1aed4d6222f56373732757caf`; evidence `calendar-pilot-p12/runs/p12_next_evidence/20260706T214346Z-step-e-retry/instrument/`) remains **hold**. Explicit `CalendarPilot SelfPlay` EventKit was retried with mutation env and still reports `authorization_status: write_only`, `configured: false`, `mutation_enabled: true`, `materialization.status: blocked`; no calendar mutation materialized. `p12-release` reran as `decision: hold`; `reward_heads` remains pass with 12 ActionStream reward rows and `policy_ablation` remains pass with 8 per-ablation reruns. Calibration still has `matched_examples: 0`; the retry scan again found 12 create-prep reward rows but 0 ActionStream/create-prep feedback rows. Belief/object-level `explain()` remains the prior object-contract hold.

Operator observation — the repeated EventKit retries may not be exercising the user-visible app access point. No CalendarPilot app or macOS permission prompt/settings surface was observed opening; the visible app path appeared to land in VS Code on `sample_profile.json`. Treat current EventKit evidence as a CLI bridge health/root-list only, not proof that the app permission request or app-bundled bridge access path was reached. Before claiming EventKit unblock, Step E must record an app-access preflight artifact that names the launched app/bundle or permission surface, shows the Calendar access state for `CalendarPilotEventKitBridge` or the bundled CalendarPilot app, and only then reruns the explicit `CalendarPilot SelfPlay` mutation probe. If the app access path cannot be reached in this environment, keep EventKit root-listed with owner `local macOS app permission/access-point owner` and next unblock action `open the correct CalendarPilot app/bundle permission surface, grant full Calendar access, then rerun the SelfPlay mutation probe`.

Update — Step E app-access run `20260706T215430Z-step-e-app-access` (instrument SHA `84fd6bd0da17f0f1aed4d6222f56373732757caf`; evidence `calendar-pilot-p12/runs/p12_next_evidence/20260706T215430Z-step-e-app-access/instrument/`) remains **hold** overall, but clears the EventKit blocker through the app access point. Preflight first confirmed VS Code was frontmost on `sample_profile.json`, then launched `dist/CalendarPilot.app` and a short-lived `live_provider` app instance using the packaged `CalendarPilotEventKitBridge.app`; that path reported `provider=apple_eventkit`, `authorization_status: full_access`, and `configured: true`. The rerun of explicit `CalendarPilot SelfPlay` `make live-eventkit-e2e` with `CALENDAR_PILOT_EVENTKIT_BRIDGE` pointed at the packaged bridge and mutation env enabled materialized, verified, and rolled back the probe event (`materialization.status: passed`, commit `committed`, undo `reverted`). `p12-release` still returns `decision: hold`; `reward_heads` remains pass, `policy_ablation` remains pass, calibration remains hold for `create_prep_block` with zero feedback matched examples, and Belief/object-level `explain()` remains the prior object-contract hold. No code, deletion, or compression work landed in this run.

Update — Step E complete run `20260706T220150Z-step-e-complete` (instrument SHA pinned in that run bundle's `INSTRUMENT.sha`; evidence `calendar-pilot-p12/runs/p12_next_evidence/20260706T220150Z-step-e-complete/instrument/`) moves Step E to **pass**. The final `make p12-release` reports `decision: pass`; all release checks pass, including calibration and `belief_explain`. Calibration now consumes real ActionStream UI feedback for `create_prep_block` (`matched_examples: 1`, `real_source: human_feedback`) and keeps the low-volume bias pinned so it is not treated as autonomy-promotion volume. Belief/object-level `explain()` now has a versioned object contract and tests/report coverage for Belief, Authority denial/revocation, Candidate, Provider, and Trajectory explanations. `reward_heads` remains pass with 13 ActionStream reward rows; `policy_ablation` remains pass with 8 per-ablation reruns. Explicit app-bundled `CalendarPilot SelfPlay` EventKit mutation reran with `authorization_status: full_access`, `configured: true`, `mutation_enabled: true`, materialization `passed`, commit `committed`, undo `reverted`, and rollback verified. Required gates passed: `make py-test`, `make check-invariants`, `make contract-vectors`, `make p12-release`, `make swift-ipc-test`, `make browser-e2e`, `make dogfood-release`, plus the explicit sandboxed `make live-eventkit-e2e`. No deletion/compression work landed.

## Hygiene rules for delegated work

```text
H1. One owner per row. A row with no owner is not delegated.
H2. One durable artifact per claim. "Looked at it" does not count.
H3. Every PR touches one workstream unless release gates require a paired fix.
H4. Every deletion records a tombstone before merge.
H5. Every KEEP verdict names a root and evidence. No "still useful" keeps.
H6. Blocked rows name the blocking command, missing permission, or unresolved decision.
H7. Engineers update tables in the same PR as the work, not in a later cleanup PR.
H8. Reference archive paths are pointers, not runtime dependencies.
```

## Handoff note template

Use this template in PR descriptions and in the working notes appended to the evidence bundle:

```text
Owner:
Rows touched:
Archive repos consulted:
Current files/symbols mapped:
Verdicts changed:
Evidence written:
Gates run:
Tombstones added:
Open blockers:
Next owner/action:
```

# Verdict (revised)

Stage A/B repair note: the cleanup posture below is retained as future Stage C/D
context only. The `20260704T024144Z-p12-next-stage-a-ledger-repair` pass did not
assign or update retention verdicts.

The previous version of this document said: *do not do broad cleanup yet; do minimal reconsolidation only.* That posture is now wrong, for one decisive reason:

> **The gates are green. This is the safest moment this repo will ever have for aggressive deletion — and the cold-start hold hands us the time to do it.**

The cold-start blocker is resolved by **calendar time** (real dogfood days producing ActionStream evidence), not by engineering hours. Engineers waiting on matched examples are free. So P12-next is two programs running in the same window:

```text
Program A — Cold-start runway (background, calendar-time-bound):
  collect create_prep_block shadow examples + explicit feedback until the
  evidence targets are met; keep the hold honest and quantified.

Program B — Debt erasure (foreground, aggressive):
  freeze current capabilities behind the P12 release gate, reconstruct the
  repo's phase lineage from /Do-not-reference, label every flow with the
  phase that introduced it, trace backwards from ML through backend to
  frontend, and delete or consolidate until calendar-pilot-p12 is at or
  below HALF its current size.
```

The freeze is what makes aggression safe: `make p12-release` already encodes every invariant, gate, and surface we care about. Any deletion that keeps it green preserved the product. Anything deleted lives on in `/Do-not-reference` — the archive means **deletion is reversible by construction**.

Hard target, measured and enforced (§6):

```text
Baseline (2026-07-03):  ~31,259 tracked LOC
Target:                 ≤ 15,700 tracked LOC   (≥ 50% cut)
Floor for acceptance:   ≥ 50% or every shortfall line itemized with a named
                        blocking reason in LINEAGE.md and user sign-off
```

# What the P12 results mean for this pass

## 1. The cold-start hold is the system working

P12's calibration gate requires real matched examples; `matched_examples: 0` correctly produced `hold`. The lab is asking for reality before it grants autonomy. Program A below keeps that runway running and quantified. Nothing in Program B may touch the collection pipeline.

## 2. Deprecated code graduates from "quarantine" to "delete"

The prior draft quarantined legacy paths (fatigue scalar, sim_v1, envelope v1 markers) so they could not contaminate reward/sim/authority. Quarantine was the right move while gates were unproven. Gates are now proven — quarantined code has no remaining purpose. **Quarantine is a waypoint, not a destination.** P12-next deletes it.

## 3. The two data-quality flags are pre-existing, not cleanup regressions

`OTHER_intent_rate 0.1429` and `expected_intent_hit_rate 0.0` in the fixture measurement report predate any deletion. Step 1 freezes these as baseline numbers so deletion waves are judged against the true "before," and a follow-up owns them separately (§13).

---

# The lineage method

This is the heart of Program B. The repo has no continuous git history across phases — each phase was delivered as a snapshot folder, and those snapshots now sit in `/Do-not-reference`. That archive is our `git blame`. The method:

```text
1. Sort the snapshot repos and implementation documents by date → phase timeline.
2. Diff successive snapshots → attribute every file/flow in calendar-pilot-p12
   to the phase that introduced it and the phases that modified it.
3. Label flows in calendar-pilot-p12 with inline LINEAGE tags naming the phase.
4. Trace backwards from ML (what the learning loop actually consumes) through
   backend to frontend; every flow not reachable from a frozen root is a
   deletion candidate by default.
5. Delete or consolidate lineage-by-lineage, re-running the frozen gate after
   each wave.
```

## The phase timeline (reconstructed from /Do-not-reference)

Dated by folder/document mtimes, **anchored by the pass documents now in `docs/history/`** (mtimes alone lie — folders get touched when moved; where mtime and pass-doc content disagree, the pass doc wins):

| phase | snapshot repo in /Do-not-reference | anchor document | what it introduced (flows to look for) |
|---|---|---|---|
| P5–P6 (Jun 29) | — (plans only) | `plan-6-revised.md` … `plan-9.md`, `readme.md` | original concept: kernel/policy/executive split, demo loop |
| P6.5 (Jun 30) | `calendar-pilot-revised` | `AGENT_LOOP_REVISION.md` | signals.py pressure read, world model, reward anatomy, right-moment, first self-play adversaries |
| P7 (Jun 30) | `calendar-pilot-updated` (+ `…updated 2` dup) | `NEXT_FOCUS_REVISION.md` | contract reconciliation, snake_case CodingKeys, staging depth, biography provenance, provider stubs |
| P7.5 (Jun 30) | `calendar-pilot-executive` (+ dup) | `CODEX_TOOL_EXECUTIVE.md` | CodexToolRuntime/Planner, tool contracts, deliberation replay |
| P8 (Jul 1) | `calendar-pilot-frontend` (×2) | `FRONTEND_AND_AUTHORITY_REVISION.md`, `FRONTEND_SURFACES.md`, `CHAT_FIRST_FRONTEND_REDESIGN.md` | static frontend, snapshot surfaces, grant registry, Swift IPC server, chat-first panels |
| P8.5 (Jul 1) | `dogfooding`, `calendar-pilot` | `DOGFOODING_FRAMEWORK.md`, `SAFETY_CONTRACT_PASS.md` | dogfood session state, AuthorityGrant hardening, live Codex path, release script |
| P9 (Jul 2) | `calendar-pilot-system-framework` | `SYSTEM_FRAMEWORK.md`, `SYSTEM_FRAMEWORK_IMPLEMENTATION_PASS.md` | environment/ substrate: trace, envelope, router, taxonomy, invariants, fsio, session locking |
| P10 (Jul 2–3) | `calendar-pilot-deferred-pass` | `DEFERRED_WORK_IMPLEMENTATION_PASS.md`, `thin-lab.md` | ActionLifecycle/SessionStore extraction, ES-module frontend, EventKit sandbox, plan graph, temporal controller, lab shell + seeds |
| P11 (Jul 3) | `calendar-pilot-p11` | `thickening-the-lab.md`, `P11-test.md` | FrontierService provenance, sim_v2, autonomy matrix, marginal promotion, provider transactions, B-precursors |
| P12 (current) | `calendar-pilot-p12` | `P12-direction.md`, `P12-test.md` | three streams, estimators, semantic labels/registry, calibration, measurement, curricula, capability reports |

Duplicate folders (`calendar-pilot-updated 2`, second `calendar-pilot-executive`, second `calendar-pilot-frontend`) are phase-adjacent snapshots with row-level deltas. Treat a duplicate pair as one phase only for rows whose evidence supports that. The former duplicate/source-mismatch blockers `B-SA-001`, `B-SA-002`, and `B-SA-003` are resolved by `20260704T041118Z-p12-next-stage-c-readiness`; continue to use row-level evidence rather than whole-folder phase collapse.

## Rules that make the method safe

```text
L1. Snapshot diffing is scripted, not eyeballed (Step 5).
L2. Inline LINEAGE tags are scaffolding, not documentation: the phase ends with
    ZERO tags remaining in the tree. Every tag resolves to either a deletion
    or an entry in docs/LINEAGE.md. A lint counts tags; nonzero fails.
L3. Stage C backwards tracing is mark-and-sweep with an explicit root set
    (Step 7), not judgment calls. Stage A/B discovery assigns no verdicts.
    Stage C retention defaults are not active until lineage review and root-set
    definition are complete.
L4. Coverage runs must include the env-gated live paths (live NIM schema gate,
    EventKit opt-in, browser E2E, Swift IPC) or those paths must be protected
    by explicit root listing. A deterministic-only coverage run WILL mark live
    code as dead — this is the method's biggest trap.
L5. Every deletion PR records a tombstone: what died, which phase built it,
    which snapshot repo still contains it. /Do-not-reference is the archive;
    nothing is lost, so nothing needs to be kept "just in case."
L6. Tests die only with their feature. A test deletion never counts toward the
    LOC quota unless it rides a feature-deletion PR. Deleting tests to hit
    numbers is gaming, and the anti-gaming rules (§6) make it visible.
L7. Lineage discovery and retention judgment are separate phases. Discovery
    may record first_seen_phase, source_archive_repo, modified phases, path
    matches, symbol matches, and uncertainty. It may NOT emit KEEP,
    CONSOLIDATE, DELETE, or ARCHIVE verdicts. Retention verdicts are assigned
    only after the discovery ledger is reviewed and the frozen root set is
    explicitly named.
L8. Static references are not roots. Tests, docs/history, examples, deleted
    frontend scaffolding, and parent-module imports may support investigation,
    but they never prove KEEP by themselves. KEEP requires a current frozen
    product root or protected runway root.
```

---

## Discovery-to-judgment review loop

Every finding updates this document or a run-scoped ledger before the next file
is reviewed. The team does not batch discoveries into an opaque final summary.

```text
Stage A — lineage discovery:
  question: where did this file/symbol/flow come from?
  outputs: phase, archive repo, evidence path, match type, confidence,
           uncertainty, and notes.
  forbidden output: KEEP/CONSOLIDATE/DELETE/ARCHIVE.

Stage B — discovery review:
  question: is the lineage claim defensible?
  outputs: accepted lineage, corrected lineage, or blocker.
  required update: mark the repo annex row and source-purpose row immediately.

Stage C — retention judgment:
  question: does this current behavior still belong in calendar-pilot-p12?
  outputs: KEEP/CONSOLIDATE/DELETE/ARCHIVE, root evidence, tombstone pointer.
  required order: trace ML roots → backend producers → frontend consumers.

Stage D — deletion/consolidation:
  question: can this verdict land while keeping the freeze green?
  outputs: PR-sized wave, tombstone, loc delta, p12-release evidence.
```

If a tool produces retention verdicts during Stage A, discard that artifact and
rerun discovery without verdict assignment.

# 0. Prime directive

```text
1. Keep make p12-release green after every wave, but do not treat it as a
   complete safety claim until the Step E instrument gate passes or root-lists
   every live exception.
2. Keep the cold-start runway collecting; never touch its pipeline.
3. Reconstruct lineage before deleting: every cut names the phase it unwinds.
4. Stage A/B assigns no retention verdicts; Stage C may do that only after
   reviewed lineage and an explicit root set.
5. Hit ≤ 50% LOC or itemize every shortfall with a named reason.
6. End with zero LINEAGE tags, a current-truth LINEAGE.md, and the same
   product behavior the P12 evidence bundle proved.
```

---

# 1. Evidence bundle setup + frozen baseline

All operational command blocks below assume the repo root:
`/Users/temp/Desktop/Destination/calendar-pilot-p12`. This avoids accidentally
using the workspace-level `Makefile`, which targets an older archive repo.

```bash
cd /Users/temp/Desktop/Destination/calendar-pilot-p12
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-p12-next"

mkdir -p runs/p12_next_evidence/$RUN_ID/{\
regression,baseline,cold_start,feedback,calibration,legacy_deletion,\
lineage,reachability,instrument,waves,docs,release}

git rev-parse HEAD > runs/p12_next_evidence/$RUN_ID/git_sha.txt
git status --short > runs/p12_next_evidence/$RUN_ID/git_status.txt
```

## Freeze the "before" (this is what every wave is judged against)

```bash
make py-test          | tee runs/p12_next_evidence/$RUN_ID/regression/py-test.log
make swift-test       | tee runs/p12_next_evidence/$RUN_ID/regression/swift-test.log
make check-invariants | tee runs/p12_next_evidence/$RUN_ID/regression/check-invariants.log
make contract-vectors | tee runs/p12_next_evidence/$RUN_ID/regression/contract-vectors.log
make p12-release      | tee runs/p12_next_evidence/$RUN_ID/regression/p12-release.log
```

Add a LOC report target so the number is measured one way forever:

```make
loc-report:
	@python3 scripts/loc_report.py   # counts src/tests/scripts/packages/frontend/contracts/docs, excludes runs/ experiments/ data/ __pycache__ .build
```

`scripts/loc_report.py` (new, ~60 lines) writes `loc_report.json` with per-area and total counts. Run it now:

```bash
make loc-report | tee runs/p12_next_evidence/$RUN_ID/baseline/loc_report_before.json
```

Baseline as measured 2026-07-03 (verify, then freeze in the ledger):

```text
src (Python)      13,949      frontend (js/html/css)  1,041
tests              4,025      contracts (json)        1,999
scripts            5,257      docs (md, incl. history) 1,329
Swift              3,659      TOTAL                  ~31,259
```

Also snapshot the pre-existing data-quality flags so waves are not blamed for them: copy the current `measurement/measurement_report.json` (with `OTHER_intent_rate: 0.1429`, `expected_intent_hit_rate: 0.0`) into `baseline/`.

## Acceptance

```text
All gates green at baseline. loc_report_before.json exists. Baseline
measurement snapshot recorded. No P11/P12 invariant relaxed.
```

---

# 2. Program A — the cold-start runway (background, protected)

The machinery already exists and passed its tests (`import_dogfood_observation.py`, `run_shadow_frontier.py`, `run_shadow_provider_preview.py`, `make_calibration_report.py`). This step is an **operating procedure**, not construction.

## Evidence target for `create_prep_block` (unchanged)

```text
matched_examples >= 20          explicit_feedback_events >= 10
provider_preview_examples >= 10 rollback_pass_rate = 1.0 (any committed reversible writes)
hard_invariant_violations = 0   reward_purity_violations = 0
labels_in_authority_path = 0    sim_vs_real acceptance/undo gaps measured or held
```

Write it once as `runs/p12_next_evidence/$RUN_ID/cold_start/create_prep_block_evidence_target.json` (schema from the prior draft, unchanged).

## Daily procedure (dogfood operator)

```bash
PYTHONPATH=src python3 scripts/import_dogfood_observation.py --provider apple_eventkit \
  --out runs/p12_next_evidence/$RUN_ID/cold_start/imported_observation_$(date +%Y%m%d).json
PYTHONPATH=src python3 scripts/run_shadow_frontier.py \
  --observation runs/p12_next_evidence/$RUN_ID/cold_start/imported_observation_$(date +%Y%m%d).json \
  --family create_prep_block \
  --out runs/p12_next_evidence/$RUN_ID/cold_start/shadow_frontier_$(date +%Y%m%d).json
PYTHONPATH=src python3 scripts/run_shadow_provider_preview.py ... # as in P12 Step 4
# review candidates; record feedback (ActionStream rows) via the app feedback path
PYTHONPATH=src python3 scripts/make_calibration_report.py --family create_prep_block ... \
  --out runs/p12_next_evidence/$RUN_ID/calibration/create_prep_block_calibration_$(date +%Y%m%d).json
```

## Protected-path rule (binding on Program B)

```text
PROTECTED (no deletion, no consolidation, no signature change this phase):
  scripts/import_dogfood_observation.py     scripts/run_shadow_frontier.py
  scripts/run_shadow_provider_preview.py    scripts/make_calibration_report.py
  scripts/propose_autonomy_family_promotion.py  scripts/promote_autonomy_family.py
  the feedback capture path, the ActionStream reward path, all B-invariants
```

## Acceptance (per week, and at phase end)

```text
Matched-example and feedback counts monotonically increasing and reported.
Calibration report continues to hold honestly until thresholds are met.
Autonomy proposal re-run names the remaining evidence deficit numerically.
No autonomy matrix diff ships. create_prep_block stays recommend/stage/confirm.
```

---

# 3. Legacy deletion (upgraded from quarantine)

The prior draft's grep-audit and quarantine tests ran and passed. Now finish the job — these are the first, easiest LOC:

Prerequisite: none of D1-D6 may land until its accepted Stage A/B lineage row is
named, its structural symbol/file expansion is complete, its exact current
line spans are mapped in `line_span_manifest.jsonl`, and a Stage C retention
verdict exists with root evidence or an explicit unreachable finding. This
section lists intended deletion candidates; it is not permission to delete
during Stage A/B or before line-level provenance.

```text
D1. UserBiography.notification_fatigue: delete field, parsers, and the
    update_from_reward nudge. Bump the observation/biography contract per
    VERSIONS.json migration rules; update golden vectors; seeds already
    author behavior (P12 Step 5 migration completed the consumers).
D2. sim_v1: delete the branch AND flip the default — self_play.py currently
    defaults simulator_version="sim_v1". Default becomes sim_v2.1; the
    version knob stays (future sim_v3), the v1 body goes. Regression
    continuity now comes from pinned replay fixtures, not from keeping v1
    executable.
D3. FatigueAdversary naming: rename to the behavioral finding it actually
    probes (notification_fatigue stays as a canonical failure-mode KEY in
    taxonomy/tuning — keys are vocabulary, not psychology — but no code path
    reads a fatigue scalar).
D4. envelope v1 marker + record_schema_version "r0" tolerance: one migration
    script over retained fixtures, then loaders drop the legacy branches.
D5. frontend/static/app.js (486 lines, unloaded since P10) + frontend_state.sample.json.
D6. examples/ (5 lines, superseded by make demo).
```

Each item lands as its own small PR with the quarantine tests inverted: the test that proved "no live reader" becomes "symbol does not exist."

## Acceptance

```text
grep -RIn "notification_fatigue" src scripts frontend --include="*.py" --include="*.js"
  → only the canonical failure-mode key in taxonomy/tuning contexts, or nothing.
sim_v1 absent; default simulator is sim_v2.1; self-play tests green on fixtures.
app.js gone; browser E2E green. Contract vectors green after migration.
```

---

# 4. Lineage archaeology — inventory and timeline

This section feeds the "Repo annex progress ledger" above. An archive repo is not annexed until its row has an owner, intake artifact, duplicate classification, current-path map, and tombstone pointer policy.

## Commands

```bash
ls -la /Users/temp/Desktop/Destination/Do-not-reference/ \
  > runs/p12_next_evidence/$RUN_ID/lineage/archive_inventory.txt
```

Record the phase timeline table (§ "The lineage method") as `lineage/phase_timeline.md`, correcting any mtime-vs-passdoc conflicts by reading the pass docs in `docs/history/`. Diff duplicate snapshots against their siblings once and note the delta:

```bash
diff -rq "/Users/temp/Desktop/Destination/Do-not-reference/calendar-pilot-updated" \
         "/Users/temp/Desktop/Destination/Do-not-reference/calendar-pilot-updated 2" \
  > runs/p12_next_evidence/$RUN_ID/lineage/updated_dup_delta.txt || true
```

## Acceptance

```text
phase_timeline.md lists every snapshot repo and anchor doc with a phase id.
Duplicate deltas recorded; duplicate folders are treated as one phase only for
rows whose evidence supports that. No phase has zero anchor documents.
Every repo row in the annex ledger is assigned or explicitly blocked.
Every loose archive document group has an owner and phase-timeline disposition.
```

---

# 5. Lineage extraction — build `lineage.json` by snapshot diffing

## New script (this phase's main new code, budgeted ~250 lines)

```text
scripts/build_lineage.py
  inputs:  ordered snapshot list from phase_timeline.md + current repo
  method:  for each current file (src/tests/scripts/packages/frontend/contracts):
             - find first snapshot containing the same path (or best content
               match ≥ 0.7 similarity for renames)
             - record first_seen_phase, modified_in_phases (content-hash per
               snapshot), current_loc
           for Python files additionally: per top-level function/class via ast,
             first_seen_phase by matching name+body fuzz across snapshots
  output:  lineage.json rows:
           {path, symbol|null, first_seen_phase, modified_in_phases,
            source_archive_repo, loc, purpose: null, owner: null,
            discovery_status: "not started", match_type, match_confidence,
            discovery_evidence, uncertainty: null}

scripts/build_src_purpose_manifest.py
  inputs:  current calendar-pilot-p12/src tree
  method:  parse Python with ast; list module rows, classes, methods,
           functions, nested definitions; add manual slots for constants,
           dataclass fields, provider surfaces, and behavior-carrying module
           globals that AST symbol counts miss
  output:  src_symbol_manifest.json rows matching the schema in the working
           delegation layer. During Stage A, retention fields stay null; this
           manifest is the assignment sheet for file-level lineage discovery.

scripts/build_line_provenance.py
  inputs:  accepted expanded_symbol_lineage.jsonl + waivers.jsonl + current
           tree under src, scripts, contracts, frontend, examples, tests,
           packages
  method:  build a current line inventory, assign line spans to accepted
           structural lineage rows by AST spans, JSON key spans, frontend
           parser spans, script/CLI carrier rows, and explicit blank/comment
           waivers. Escalate to archive reinspection only when a line span
           cannot be assigned to an accepted structural row.
  output:  line_span_manifest.jsonl rows matching the "Line-level provenance
           pass" schema, plus line_span_coverage.json and line_span_gaps.md.
```

```bash
PYTHONPATH=src python3 scripts/build_lineage.py \
  --archive /Users/temp/Desktop/Destination/Do-not-reference \
  --timeline runs/p12_next_evidence/$RUN_ID/lineage/phase_timeline.md \
  --out runs/p12_next_evidence/$RUN_ID/lineage/lineage.json

PYTHONPATH=src python3 scripts/build_src_purpose_manifest.py \
  --src src/calendar_pilot \
  --out runs/p12_next_evidence/$RUN_ID/lineage/src_symbol_manifest.json

PYTHONPATH=src python3 scripts/build_line_provenance.py \
  --lineage runs/p12_next_evidence/20260704T041118Z-p12-next-stage-c-readiness/lineage/expanded_symbol_lineage.jsonl \
  --waivers runs/p12_next_evidence/20260704T041118Z-p12-next-stage-c-readiness/lineage/waivers.jsonl \
  --root . \
  --out runs/p12_next_evidence/$RUN_ID/lineage/line_span_manifest.jsonl \
  --coverage runs/p12_next_evidence/$RUN_ID/lineage/line_span_coverage.json \
  --gaps runs/p12_next_evidence/$RUN_ID/lineage/line_span_gaps.md
```

`build_lineage.py` is itself scaffolding: it moves to the evidence bundle at phase end, not into the permanent tree (record in LINEAGE.md where it lives).

## Acceptance

```text
Every tracked file has a first_seen_phase (unknowns explicitly "pre-P6.5").
Per-symbol rows exist for the ten largest Python files.
LOC by phase sums to the loc-report total (± generated files, listed).
src_symbol_manifest.json exists and covers all 54 current Python source files.
Every file in the source assignment queue has an owner or a blocking reason.
No KEEP/CONSOLIDATE/DELETE/ARCHIVE verdicts appear in lineage discovery output.
Every discovered row has phase, archive evidence, match type, confidence, and
an uncertainty note when evidence is weak or conflicting.
line_span_manifest.jsonl exists and every current line is mapped, waived, or
blocked. line_span_coverage.json separates executable, schema, frontend,
script, blank, comment, generated, and blocked counts by path.
No Stage D deletion/consolidation candidate lacks line-span provenance.
```

---

# 6. LOC budget and the kill list

Quotas are budgets that sum to the target; each wave re-measures via `make loc-report`. **Anti-gaming rules:** (a) a test or doc deletion counts toward quota only when it rides the feature deletion that orphaned it; (b) gate scripts, invariants, contracts+vectors, and the protected runway never count; (c) code moved to the archive counts, code moved *within* the repo does not.

| area | baseline | quota | how (named candidates, grounded) |
|---|---:|---:|---|
| src/frontend (py) | ~4,180 | ≤ 2,100 | `session.py` 2,222 → ≤ 900: delete chat-first legacy panels and pre-projector state paths (P8 lineage; projector/`view_state.v2` is the survivor), fold `surface.py` (460) into projector, merge `session_manager.py` (294) session-launch duplication |
| src/codex | ~2,400 | ≤ 1,600 | dedupe deterministic planner vs `codex/live.py` (1,135) shared tool plumbing; delete explanation paths superseded by receipts (P6.5 lineage) |
| src/diffusiongemma | ~3,300 | ≤ 2,400 | sim_v1 (§3); collapse `right_moment.py` scoring into temporal controller mapping (P11 T4 made controller canonical); world_model counterfactual prose trims |
| src other | ~4,070 | ≤ 3,300 | fatigue field + parsers (§3); `providers/stubs.py` → capability declarations (Step 8 of P12 made "unsupported" explicit — stubs that pretend methods are dead weight); merge `swift_bridge/client.py` (450) + `ipc.py` (303) shared framing |
| scripts | 5,257 | ≤ 1,800 | 38 scripts → ~14: one `scripts/lab.py` CLI absorbs the make_*/compare_*/run_* families behind subcommands sharing argparse/IO/report-writer plumbing (~150–250 duplicated lines each); Make targets keep their names and delegate — **the Makefile interface is frozen, its implementations are not**; 3 browser E2E implementations (`browser_cdp_e2e.mjs`, `browser_e2e.spec.mjs`, `run_browser_e2e.py` + `run_external_browser_flow.py`) → 1; `run_dogfood_release.py` 877 → ~350 by calling the same shared runner |
| tests | 4,025 | ≤ 2,700 | tests of deleted features die with them (L6); merge per-phase test helpers; keep every gate/invariant/contract test |
| Swift | 3,659 | ≤ 3,300 | demo target trim, dead Codable mirrors for deleted legacy fields; kernel/authority/rollback untouched |
| frontend static | 1,041 | ≤ 500 | app.js + sample state (§3); component dedup in `js/components/` |
| contracts | 1,999 | ≤ 1,700 | legacy markers via versioned migration only (v1 envelope, r0) |
| docs | 1,329 | ≤ 600 | `docs/history/` (12 pass docs) moves to /Do-not-reference — the archive is where history lives; current-truth set stays: ARCHITECTURE, CONTRACTS, LAB, PROVIDER_BOUNDARY, SELF_PLAY, SIGNAL_STREAMS, IMPLEMENTATION_MAP, + new LINEAGE.md |
| **total** | **~31,259** | **≤ 15,700** | **≥ 50%** |

Every quota miss at phase end requires a per-file KEEP justification in LINEAGE.md and user sign-off on the shortfall.

---

# 7. Inline LINEAGE tagging + reachability (the tracing pass)

## Tag format (the user-proposed inline labels, with a hard half-life)

```text
# LINEAGE[P8][candidate]: chat-first panel state; superseded by view_state.v2 — verify no test reads it
# LINEAGE[P7.5][keep]: tool receipt path consumed by replay reducer (root: p12-release)
```

Engineers apply tags while tracing **backwards from ML**: start at what learning consumes (replay record types, reward reduction, tuning, frontier provenance), walk into backend (lifecycle, kernel bridge, providers), then frontend (projector -> surfaces). Tag as you go using `lineage.json` for the phase id and `line_span_manifest.jsonl` for the exact line spans. A tag may cover a symbol or flow while investigating, but the final evidence for a deletion/consolidation must cite line spans.

```text
Tag lint (added to p12-release for this phase only):
  zero LINEAGE tags may remain at phase end — each resolves to a deletion PR
  or a docs/LINEAGE.md entry. Tags are working scaffolding; a lineage comment
  that outlives the phase is itself tech debt.
```

## Root set (mark-and-sweep roots — the freeze, enumerated)

```text
make targets (all 30 — the frozen interface), contracts/ + vectors,
environment/invariants.py checks, the B-series tests, the protected runway
(§2), app entry (calendar_pilot.app), frontend served entry (index.html + js/main.js),
Swift package products, .github workflows.
```

## Reachability + coverage union (L4 — do not skip the live legs)

```bash
# static reachability: imports from roots (script or grep-based, recorded)
# dynamic coverage — UNION of:
coverage run -m unittest discover -s tests          # deterministic
make p12-release                                     # gate path (under coverage)
CALENDAR_PILOT_REQUIRE_LIVE_NIM=1 scripts/run_live_nim_schema_gate.py   # live NIM leg
make live-eventkit-e2e                               # when environment permits
make browser-e2e                                     # browser leg
coverage json -o runs/p12_next_evidence/$RUN_ID/reachability/coverage.json
```

## Verdict taxonomy (recorded per lineage.json row)

```text
KEEP        root-reachable and gate-covered (reason = which root)
CONSOLIDATE reachable but duplicates a kept flow (names the survivor)
DELETE      unreachable from roots, or reachable only from legacy roots
ARCHIVE     docs/history and scaffolding → /Do-not-reference
DEFAULT is DELETE. KEEP without a named root is not a verdict, it is a feeling.
```

Retention verdicts are appended only after Stage A discovery and Stage B
discovery review are complete for the relevant repo/file slice. A verifier must
be able to point to the accepted lineage row and the frozen root before a KEEP
or CONSOLIDATE verdict is accepted.

DELETE and ARCHIVE verdicts must additionally point to line-span evidence before
implementation begins. A symbol-level DELETE is not enough if the containing
file also has KEEP lines; Stage D removes only the mapped spans or records why
whole-file deletion is safe.

## Acceptance

```text
100% of lineage.json rows have verdicts. Coverage union includes at least the
deterministic, release, live-NIM, and browser legs (EventKit noted if env-held).
Every env-gated live path is either covered or explicitly root-listed.
100% of src_symbol_manifest.json rows have purpose, owner, reachability, verdict,
and evidence fields filled before final wave acceptance.
Every verdict references an accepted Stage A lineage row; no verdict is based
only on docs/history, examples, tests, parent-module import, or archive presence.
100% of DELETE/CONSOLIDATE/ARCHIVE verdicts cite exact line spans or carry a
Stage C blocker. Mixed files name both the survivor spans and the removed spans.
```

---

# 8. Step E instrument gate — make the ruler truthful before more cuts

Step E is the lettered continuation after Stage D, before destructive
compression resumes. It is not a deletion wave. It is the gate that proves the
release instrument can detect the failures a deletion wave might introduce. It
may add code. That is acceptable: Step E lowers false confidence before P12-next
lowers LOC.

## Pin the instrument

```bash
git rev-parse HEAD > runs/p12_next_evidence/$RUN_ID/instrument/INSTRUMENT.sha
git status --short > runs/p12_next_evidence/$RUN_ID/instrument/instrument_git_status.txt

make p12-release \
  | tee runs/p12_next_evidence/$RUN_ID/instrument/p12-release-instrument.log

make swift-ipc-test \
  | tee runs/p12_next_evidence/$RUN_ID/instrument/swift-ipc-test.log

make browser-e2e \
  | tee runs/p12_next_evidence/$RUN_ID/instrument/browser-e2e.log

make dogfood-release \
  | tee runs/p12_next_evidence/$RUN_ID/instrument/dogfood-release.log
```

Live legs are run when credentials and OS permission are intentionally present.
If a leg cannot run, root-list it in the same bundle with a named owner and the
next unblock action. A skipped live leg with no root-list entry is a failed
instrument gate.

```bash
make live-codex-e2e \
  | tee runs/p12_next_evidence/$RUN_ID/instrument/live-codex-e2e.log

make live-diffusiongemma-e2e \
  | tee runs/p12_next_evidence/$RUN_ID/instrument/live-diffusiongemma-e2e.log

CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX=1 \
CALENDAR_PILOT_SELFPLAY_EVENTKIT_SANDBOX_CALENDAR_ID="CalendarPilot SelfPlay" \
make live-eventkit-e2e \
  | tee runs/p12_next_evidence/$RUN_ID/instrument/live-eventkit-e2e.log
```

Root-list schema:

```text
leg:
status: ran | root-listed
reason:
last_passing_artifact:
owner:
next_unblock_action:
accepted_until:
```

## De-placebo release legs

`reward_heads`, `policy_ablation`, and `calibration` are protected instrument
surfaces. They can be thin only if they say they are thin, and they must fail or
hold for real reasons.

Required outputs:

```text
reward_heads:
  consumed_action_rows > 0, or explicit no-data hold
  non_action_stream_rows counted
  reward_purity_violations list carries row ids
  synthetic non-ActionStream reward fixture fails

policy_ablation:
  every ablation re-runs or reuses a named frontier_diff + scorecard input
  promotion_decision comes from re-graded deltas, not constants
  no_semantic_labels and no_derived_signals state whether signals are load-bearing
  empty ablation inputs hold, not pass

calibration:
  matched_examples, family metrics, gaps, and known_biases are always emitted
  insufficient-data is a release-level hold with `decision: hold`
  hold exits are represented separately from pass in the release report
  `--family create_prep_block` output is carried into Program A
```

Acceptance is adversarial: each leg gets one negative fixture proving the gate
turns red or hold-shaped when the protected condition is violated. A green report
with no consumed evidence is not a pass.

## Known-red baseline flags

Write the known-red flags at the same `INSTRUMENT@sha` so future waves can be
judged against the real before-state, not against a cleaned-up memory.

```json
{
  "OTHER_intent_rate": 0.1429,
  "expected_intent_hit_rate": 0.0,
  "matched_examples": 0,
  "create_prep_block_promotion": "hold",
  "calibration_decision": "hold"
}
```

These flags are not owned by deletion waves unless a wave worsens them. They are
owned by frontier quality, Program A evidence collection, and the Step E
instrument report.

## Belief and explain gate

Step E must make derived human state an object, not a scalar convention.

```text
Belief:
  constructible only with evidence row ids, confidence, version, and controls
  SemanticSignal may back a Belief, but uncited labels cannot
  active/correct/disable history is replay-visible

explain():
  answers include claim, evidence row ids, confidence, controls, and version
  at minimum covers Belief, Authority denial/revocation, Candidate, Provider,
  and Trajectory trace answers
```

If `Belief` or `explain()` is not implemented, P12-next final acceptance is
`hold`, not `pass`. A hold may be accepted only with `belief_explain_report.md`
listing the missing object messages, owner, target phase, and the compression
work that is blocked until the gap closes.

## Acceptance

```text
INSTRUMENT@sha pinned with clean or intentionally dirty status recorded.
Every live leg ran or has a signed root-list entry.
reward_heads, policy_ablation, and calibration can fail or hold for real inputs.
Known-red flags are recorded at pin time and not worsened by later waves.
Belief and explain are implemented, or final acceptance is explicitly hold.
No destructive wave lands after the pin without rerunning affected instrument legs.
```

---

# 9. Deletion waves (reverse-lineage order, gate-green after each)

Each wave: one PR series → `make p12-release` + `make loc-report` → tombstones appended to LINEAGE.md (`what died, phase that built it, snapshot repo that still has it`).

```text
Wave 1 — dead by reachability (target ~ −4,500 LOC):
  §3 items (fatigue, sim_v1, app.js, envelope v1/r0, examples), unreferenced
  scripts, docs/history → archive, orphaned fixtures.

Wave 2 — lineage-dead flows (target ~ −6,000 LOC):
  P8 chat-first panels + pre-projector session state (session.py, surface.py),
  P6.5 explanation paths superseded by receipts, provider stubs → capability
  declarations, browser E2E consolidation to one implementation,
  right_moment scoring fold-in, swift_bridge merge.

Wave 3 — consolidation (target ~ −5,000 LOC):
  scripts → lab.py CLI (Make targets stable, delegating), shared report
  writer for measurement/calibration/reward-head/capability, dogfood_release
  on the shared runner, test-helper merges, session.py decomposition per the
  P9 object map (RuntimeAssembly/SessionStore/Projector already extracted —
  finish the strangler and delete the wrapped bodies).
```

Ordering rule within every wave, exactly as proposed: **trace ML → backend → frontend.** Cutting a consumer before its producer leaves the producer visibly unreachable in the next reachability run; cutting producer-first hides breakage in review.

## Acceptance per wave

```text
p12-release green. Step E affected instrument legs rerun or explicitly unchanged.
loc-report delta recorded. Zero new invariant violations.
Baseline data-quality flags (§1) unchanged or improved — never worsened.
Tombstones written. Protected paths untouched (diff-checked).
```

---

# 10. Docs current-truth pass

```text
docs/LINEAGE.md (new, permanent): phase timeline, verdict summary, tombstone
  index, where build_lineage.py and lineage.json live in the evidence bundle.
docs/history/ → /Do-not-reference/calendar-pilot-docs-history/ (archive).
README.md: refresh tree listing and quickstart against the post-wave repo
  (the current README already drifts — it says "calendar-pilot/" and lists
  examples/; both wrong after Wave 1).
docs/DEPRECATED_FIELDS.md: entries flip from "quarantined" to "removed in
  P12-next, survives in <snapshot>".
```

Acceptance: a new engineer finds current truth in ≤ 60 seconds; no doc references a deleted flow; `grep -r "Do-not-reference" docs/` returns only LINEAGE.md archive pointers.

---

# 11. Final release + phase acceptance

```bash
make p12-release  | tee runs/p12_next_evidence/$RUN_ID/release/p12-release-final.log
make loc-report   | tee runs/p12_next_evidence/$RUN_ID/release/loc_report_after.json
make py-test swift-test swift-ipc-test check-invariants contract-vectors
make browser-e2e dogfood-release
```

```md
# P12-next Final Acceptance

## Freeze held
- [ ] p12-release green at baseline, after every wave, and at final.
- [x] Step E instrument gate passed, or final decision is explicitly hold.
- [ ] No P11/P12 invariant relaxed; B1–B6 intact; reward purity intact.
- [ ] Baseline data-quality flags not worsened by any wave.
- [ ] Protected runway paths byte-identical or additively extended.

## Step E — instrument truth
- [x] `INSTRUMENT@sha` is pinned and final release names the pinned instrument.
- [x] Live Codex, live DiffusionGemma/NIM, live EventKit, Swift IPC, browser E2E,
      and dogfood release legs ran or are root-listed with owner/sign-off.
- [x] `reward_heads` scans consumed rows and has a negative fixture that fails.
- [x] `policy_ablation` re-grades real frontier/scorecard inputs; no constant pass.
- [x] `calibration` distinguishes pass from insufficient-data hold in release output.
- [x] Known-red flags are recorded at pin time and remain unchanged or improved.
- [x] Belief/explain object contract shipped, or final acceptance is hold with
      `belief_explain_report.md`.

## Program A — cold-start runway
- [ ] Evidence target file exists; counts increasing week over week.
- [ ] Calibration reports hold honestly (or pass, if thresholds met).
- [ ] Autonomy proposal re-run quantifies the remaining deficit.
- [ ] No autonomy matrix diff shipped without a promotion record.

## Program B — debt erasure
- [ ] phase_timeline.md + lineage.json complete; every row has a verdict.
- [ ] Repo annex ledger has every `/Do-not-reference` repo marked annexed, verified, or blocked with user sign-off.
- [ ] src_symbol_manifest.json covers every class/function/method/nested def and every waived non-AST behavior carrier.
- [ ] line_span_manifest.jsonl covers every current nonblank line as mapped, waived, or blocked.
- [ ] Every source-purpose row has purpose, owner, phase, reachability, verdict, and evidence.
- [ ] Every DELETE/CONSOLIDATE/ARCHIVE verdict names exact current line spans or an accepted whole-file deletion reason.
- [ ] Coverage union included live legs or explicit root-listing (L4).
- [ ] Zero LINEAGE tags remain (lint enforced).
- [ ] loc_report_after ≤ 15,700 tracked LOC, OR every shortfall itemized
      in LINEAGE.md with named reasons and user sign-off.
- [ ] Every deletion has a tombstone naming its archive location.
- [ ] Tests deleted only alongside their features (audit of test-deletion PRs).
- [ ] docs/LINEAGE.md exists; docs/history archived; README current.

## Legacy graduation
- [ ] notification_fatigue removed (field, parsers, nudge) with contract migration.
- [ ] sim_v1 removed; default simulator sim_v2.1.
- [ ] app.js, examples/, envelope v1/r0 branches removed.
```

---

# 12. Recommended PR sequence

```text
PR 1  p12-next-baseline        loc_report.py + make target, baseline freeze, evidence bundle
PR 2  p12-next-runway-ops      evidence-target file, daily-procedure doc, protected-path lint
PR 3  p12-next-annex           repo annex ledger assignments, phase_timeline.md, duplicate deltas
PR 4  p12-next-source-purpose  build_src_purpose_manifest.py, source owners, initial purpose rows
PR 5  p12-next-lineage         build_lineage.py, lineage.json, source_archive_repo mapping
PR 6  p12-next-line-spans      build_line_provenance.py, line_span_manifest.jsonl, line-span gap review
PR 7  p12-next-root-verdicts   LINEAGE tag lint + tagging sweep + reachability/coverage union + Stage C verdict gate
PR 8  p12-next-step-e          Step E instrument pin, live-leg/root-list ledger, de-placebo gates, Belief/explain decision
PR 9  p12-next-legacy-delete   §3 D1–D6 after accepted lineage/line spans/Stage C verdicts, inverted quarantine tests
PR 10 p12-next-wave-1          remaining dead-by-reachability deletions + tombstones
PR 11 p12-next-wave-2          lineage-dead flow deletions (ML -> backend -> frontend order)
PR 12 p12-next-wave-3          lab.py CLI consolidation, shared report writer, session decomposition
PR 13 p12-next-docs            LINEAGE.md, history archive, README refresh, tag-lint removal
PR 14 p12-next-final           final release run, loc gate, Step E acceptance ledger
```

---

# 13. Follow-ups this phase deliberately does not own

```text
Frontier-quality remediation for OTHER_intent_rate 0.1429 and
  expected_intent_hit_rate 0.0 at fixture scale — owned by a frontier-quality
  follow-up after the deletion waves settle. Step E owns pinning these flags and
  proving waves did not worsen them.
Live EventKit permission/environment hold — resolved in Stage D2 for this machine; keep the `CalendarPilot SelfPlay` sandbox setup documented, including the `default_if_no_local` caveat when no local EventKit source exists.
create_prep_block promotion — Program A decides it with data, not this phase.
Google/Microsoft sandbox providers — P13, against a half-sized repo.
```

---

# 14. Judgment standard

P12-next succeeds when:

```text
the same P12 evidence bundle can be regenerated from half the code,
every deleted line is attributable to the phase that added it and the
  snapshot that still contains it,
the cold-start runway accumulated real ActionStream evidence the whole time,
create_prep_block remains held for a quantified, shrinking reason,
no invariant, contract, or gate was weakened to get green,
the Step E instrument can fail truthfully and names every live exception,
and the next engineer reads docs/LINEAGE.md and understands in one sitting
  both what this system is and what it used to be.
```

Deletion with lineage is not losing history — it is finally putting history where it belongs: in the archive, out of the executable.
