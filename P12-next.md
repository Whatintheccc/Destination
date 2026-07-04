According to a document from **July 3, 2026**, P12's target is not broad autonomy yet; it is a governed learning loop where ActionStream is reward truth, WorldStream is context, BiographyStream is a prior, derived signals are evidence-cited, and autonomy expands only one reversible action family at a time.

**Status input (from the completed `P12-test.md` run `20260703T224814Z-p12`):** overall decision **pass**. All deterministic, fixture, contract, invariant, browser, and release gates green (`make p12-release` → `ok: true`). Three explicit, correct holds: calibration (`matched_examples: 0` — cold start), live EventKit (macOS permission/environment), and `create_prep_block` autonomy promotion (insufficient human feedback + sim-real calibration). Two data-quality flags recorded in the fixture measurement snapshot that must be carried forward, not forgotten: `OTHER_intent_rate: 0.1429` (above the 0.10 gate at fixture scale) and `expected_intent_hit_rate: 0.0`.

# Verdict (revised)

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

`OTHER_intent_rate 0.1429` and `expected_intent_hit_rate 0.0` in the fixture measurement report predate any deletion. Step 1 freezes these as baseline numbers so deletion waves are judged against the true "before," and a follow-up owns them separately (§12).

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

Duplicate snapshots (`calendar-pilot-updated 2`, second `calendar-pilot-executive`, second `calendar-pilot-frontend`) are near-copies from the same phase: diff them against their siblings once, record the delta in the lineage manifest, and treat the pair as one phase thereafter.

## Rules that make the method safe

```text
L1. Snapshot diffing is scripted, not eyeballed (Step 5).
L2. Inline LINEAGE tags are scaffolding, not documentation: the phase ends with
    ZERO tags remaining in the tree. Every tag resolves to either a deletion
    or an entry in docs/LINEAGE.md. A lint counts tags; nonzero fails.
L3. Backwards tracing is mark-and-sweep with an explicit root set (Step 7),
    not judgment calls. Default verdict for unreached code is DELETE; the
    burden of proof is on KEEP.
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
```

---

# 0. Prime directive

```text
1. Keep make p12-release green after every wave. The gate is the freeze.
2. Keep the cold-start runway collecting; never touch its pipeline.
3. Reconstruct lineage before deleting: every cut names the phase it unwinds.
4. Default-DELETE for unreachable code; KEEP requires a manifest entry.
5. Hit ≤ 50% LOC or itemize every shortfall with a named reason.
6. End with zero LINEAGE tags, a current-truth LINEAGE.md, and the same
   product behavior the P12 evidence bundle proved.
```

---

# 1. Evidence bundle setup + frozen baseline

```bash
export RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-p12-next"

mkdir -p runs/p12_next_evidence/$RUN_ID/{\
regression,baseline,cold_start,feedback,calibration,legacy_deletion,\
lineage,reachability,waves,docs,release}

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
Duplicates resolved to one phase each. No phase has zero anchor documents.
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
            loc, verdict: null, verdict_reason: null, tombstone: null}
```

```bash
PYTHONPATH=src python3 scripts/build_lineage.py \
  --archive /Users/temp/Desktop/Destination/Do-not-reference \
  --timeline runs/p12_next_evidence/$RUN_ID/lineage/phase_timeline.md \
  --out runs/p12_next_evidence/$RUN_ID/lineage/lineage.json
```

`build_lineage.py` is itself scaffolding: it moves to the evidence bundle at phase end, not into the permanent tree (record in LINEAGE.md where it lives).

## Acceptance

```text
Every tracked file has a first_seen_phase (unknowns explicitly "pre-P6.5").
Per-symbol rows exist for the ten largest Python files.
LOC by phase sums to the loc-report total (± generated files, listed).
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

Engineers apply tags while tracing **backwards from ML**: start at what learning consumes (replay record types, reward reduction, tuning, frontier provenance), walk into backend (lifecycle, kernel bridge, providers), then frontend (projector → surfaces). Tag as you go using `lineage.json` for the phase id.

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

## Acceptance

```text
100% of lineage.json rows have verdicts. Coverage union includes at least the
deterministic, release, live-NIM, and browser legs (EventKit noted if env-held).
Every env-gated live path is either covered or explicitly root-listed.
```

---

# 8. Deletion waves (reverse-lineage order, gate-green after each)

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
p12-release green. loc-report delta recorded. Zero new invariant violations.
Baseline data-quality flags (§1) unchanged or improved — never worsened.
Tombstones written. Protected paths untouched (diff-checked).
```

---

# 9. Docs current-truth pass

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

# 10. Final release + phase acceptance

```bash
make p12-release  | tee runs/p12_next_evidence/$RUN_ID/release/p12-release-final.log
make loc-report   | tee runs/p12_next_evidence/$RUN_ID/release/loc_report_after.json
make py-test swift-test check-invariants contract-vectors
```

```md
# P12-next Final Acceptance

## Freeze held
- [ ] p12-release green at baseline, after every wave, and at final.
- [ ] No P11/P12 invariant relaxed; B1–B6 intact; reward purity intact.
- [ ] Baseline data-quality flags not worsened by any wave.
- [ ] Protected runway paths byte-identical or additively extended.

## Program A — cold-start runway
- [ ] Evidence target file exists; counts increasing week over week.
- [ ] Calibration reports hold honestly (or pass, if thresholds met).
- [ ] Autonomy proposal re-run quantifies the remaining deficit.
- [ ] No autonomy matrix diff shipped without a promotion record.

## Program B — debt erasure
- [ ] phase_timeline.md + lineage.json complete; every row has a verdict.
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

# 11. Recommended PR sequence

```text
PR 1  p12-next-baseline        loc_report.py + make target, baseline freeze, evidence bundle
PR 2  p12-next-runway-ops      evidence-target file, daily-procedure doc, protected-path lint
PR 3  p12-next-legacy-delete   §3 D1–D6 (one PR per item is fine), inverted quarantine tests
PR 4  p12-next-lineage         phase_timeline.md, build_lineage.py, lineage.json
PR 5  p12-next-tagging         LINEAGE tag lint + tagging sweep + reachability/coverage union
PR 6  p12-next-wave-1          dead-by-reachability deletions + tombstones
PR 7  p12-next-wave-2          lineage-dead flow deletions (ML → backend → frontend order)
PR 8  p12-next-wave-3          lab.py CLI consolidation, shared report writer, session decomposition
PR 9  p12-next-docs            LINEAGE.md, history archive, README refresh, tag-lint removal
PR 10 p12-next-final           final release run, loc gate, acceptance ledger
```

---

# 12. Follow-ups this phase deliberately does not own

```text
OTHER_intent_rate 0.1429 and expected_intent_hit_rate 0.0 at fixture scale —
  owned by a frontier-quality follow-up after the deletion waves settle
  (baseline is frozen so regressions vs. flags are distinguishable).
Live EventKit permission/environment hold — operator task, unchanged from P12.
create_prep_block promotion — Program A decides it with data, not this phase.
Google/Microsoft sandbox providers — P13, against a half-sized repo.
```

---

# 13. Judgment standard

P12-next succeeds when:

```text
the same P12 evidence bundle can be regenerated from half the code,
every deleted line is attributable to the phase that added it and the
  snapshot that still contains it,
the cold-start runway accumulated real ActionStream evidence the whole time,
create_prep_block remains held for a quantified, shrinking reason,
no invariant, contract, or gate was weakened to get green,
and the next engineer reads docs/LINEAGE.md and understands in one sitting
  both what this system is and what it used to be.
```

Deletion with lineage is not losing history — it is finally putting history where it belongs: in the archive, out of the executable.
