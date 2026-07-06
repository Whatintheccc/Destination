#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def _load_decision(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        payload=json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    decision=payload.get('decision')
    return str(decision) if decision in {'pass','hold','fail'} else None

def run(name, cmd, *, artifact: Path | None = None):
    proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    artifact_decision=_load_decision(artifact)
    if proc.returncode != 0:
        status='fail'
    elif artifact_decision in {'pass','hold','fail'}:
        status=artifact_decision
    else:
        status='pass'
    return {
        'name':name,
        'cmd':' '.join(cmd),
        'returncode':proc.returncode,
        'status':status,
        'ok':status=='pass',
        'artifact':str(artifact) if artifact else None,
        'stdout':proc.stdout[-4000:],
        'stderr':proc.stderr[-4000:],
    }

def root_listed_leg(leg: str, reason: str, *, last_passing_artifact: str = "", signed: bool = False) -> dict:
    return {
        'leg':leg,
        'status':'signed-root-list' if signed else 'root-listed',
        'reason':reason,
        'last_passing_artifact':last_passing_artifact,
        'owner':'Step E instrument owner',
        'next_unblock_action':f'run `make {leg}` in the Step E evidence bundle or keep this root-list entry signed',
        'accepted_until':'Step E completion or next behavior-changing compression wave',
    }

def release_reach() -> list[dict]:
    return [
        {
            'leg':'p12-release',
            'status':'ran',
            'reason':'current release wrapper execution',
            'last_passing_artifact':'',
            'owner':'Step E instrument owner',
            'next_unblock_action':'none for this leg',
            'accepted_until':'this run',
        },
        root_listed_leg('swift-ipc-test','outside the deterministic p12-release subprocess set; required as a Step E protected leg',last_passing_artifact='calendar-pilot-p12/runs/p12_next_evidence/20260705T174108Z-p12-next-stage-d2-official-pipelines/', signed=True),
        root_listed_leg('browser-e2e','outside the deterministic p12-release subprocess set; required as a Step E protected leg',last_passing_artifact='calendar-pilot-p12/runs/p12_next_evidence/20260705T174108Z-p12-next-stage-d2-official-pipelines/', signed=True),
        root_listed_leg('dogfood-release','outside the deterministic p12-release subprocess set; required as a Step E protected leg',last_passing_artifact='calendar-pilot-p12/runs/p12_next_evidence/20260705T174108Z-p12-next-stage-d2-official-pipelines/', signed=True),
        root_listed_leg('live-codex-e2e','live credential/runtime leg must be run intentionally or root-listed',last_passing_artifact='calendar-pilot-p12/runs/p12_next_evidence/20260705T043439Z-p12-next-stage-d-blocker-fixes/', signed=True),
        root_listed_leg('live-diffusiongemma-e2e','live NIM credential/runtime leg must be run intentionally or root-listed',last_passing_artifact='calendar-pilot-p12/runs/p12_next_evidence/20260705T043439Z-p12-next-stage-d-blocker-fixes/', signed=True),
        root_listed_leg('live-eventkit-e2e','sandbox EventKit mutation must be run intentionally with CalendarPilot SelfPlay env or root-listed',last_passing_artifact='calendar-pilot-p12/runs/p12_next_evidence/20260706T215430Z-step-e-app-access/', signed=True),
    ]

def release_decision(checks: list[dict], reach: list[dict]) -> str:
    if any(c['status']=='fail' for c in checks):
        return 'fail'
    if any(c['status']=='hold' for c in checks):
        return 'hold'
    if any(leg.get('status')=='root-listed' for leg in reach):
        return 'hold'
    return 'pass'

def reward_replay_inputs() -> list[Path]:
    env=os.environ.get('CALENDAR_PILOT_REWARD_REPLAY','')
    if env:
        paths=[Path(p) for p in env.split(os.pathsep) if p]
    else:
        paths=[
            ROOT/'runs'/'browser_e2e'/'server_state'/'replay.jsonl',
            ROOT/'runs'/'dogfood'/'replay.jsonl',
            ROOT/'runs'/'release'/'mac_app_state_fixture'/'replay.jsonl',
            ROOT/'runs'/'release'/'mac_app_state_swift_ipc'/'replay.jsonl',
            ROOT/'runs'/'live_codex_e2e'/'server_state'/'replay.jsonl',
            ROOT/'runs'/'live_diffusiongemma_e2e'/'server_state'/'replay.jsonl',
        ]
    existing=[]
    seen=set()
    for path in paths:
        p=path if path.is_absolute() else ROOT/path
        if p.exists() and p not in seen:
            existing.append(p)
            seen.add(p)
    return existing or [ROOT/'tests'/'fixtures'/'replay_golden.jsonl']

def materialize_action_reward_replay(outdir: Path, inputs: list[Path]) -> tuple[Path, Path]:
    out=outdir/'action_reward_replay.jsonl'
    manifest=outdir/'action_reward_replay_manifest.json'
    rows=[]
    source_rows=[]
    excluded=[]
    malformed=[]
    for path in inputs:
        if not path.exists():
            continue
        for line_no,line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except json.JSONDecodeError as exc:
                malformed.append({'path':str(path),'line_no':line_no,'error':str(exc)})
                continue
            payload=row.get('payload') if isinstance(row.get('payload'), dict) else {}
            has_reward=isinstance(payload.get('reward'), dict) or row.get('record_type')=='reward'
            is_action=row.get('signal_stream')=='action'
            if row.get('record_type')=='reward' and is_action:
                rows.append(json.dumps(row, sort_keys=True))
                source_rows.append({'path':str(path),'line_no':line_no,'record_id':row.get('record_id')})
            elif has_reward and not is_action:
                excluded.append({'path':str(path),'line_no':line_no,'record_id':row.get('record_id'),'record_type':row.get('record_type'),'signal_stream':row.get('signal_stream')})
    out.write_text(('\n'.join(rows)+'\n') if rows else '', encoding='utf-8')
    manifest.write_text(json.dumps({
        'action_reward_replay':str(out),
        'source_replays':[str(p) for p in inputs],
        'included_action_reward_rows':source_rows,
        'excluded_non_action_reward_rows':excluded,
        'malformed_rows':malformed,
        'decision':'pass' if rows else 'hold',
    }, indent=2, sort_keys=True), encoding='utf-8')
    return out, manifest

def reward_head_cmd(outdir: Path, replay_path: Path) -> list[str]:
    cmd=[sys.executable,'scripts/make_reward_head_report.py','--replay',str(replay_path)]
    cmd.extend(['--out',str(outdir/'reward_head_report.json')])
    return cmd

def main():
    outdir=ROOT/'runs'/'p12_release'; outdir.mkdir(parents=True,exist_ok=True)
    checks=[]
    reward_inputs=reward_replay_inputs()
    calibration_cmd=[sys.executable,'scripts/make_calibration_report.py','--family','create_prep_block','--out',str(outdir/'calibration_report.json')]
    for replay in reward_inputs:
        calibration_cmd.extend(['--replay',str(replay)])
    checks.append(run('check_invariants',[sys.executable,'scripts/check_invariants.py','--replay','tests/fixtures/replay_golden.jsonl','--out',str(outdir/'invariants.json')], artifact=outdir/'invariants.json'))
    checks.append(run('signal_estimators',[sys.executable,'scripts/run_signal_estimators.py','--out',str(outdir/'signal_estimator_report.json'),'--replay-out',str(outdir/'signal_estimator_replay.jsonl')], artifact=outdir/'signal_estimator_report.json'))
    checks.append(run('frontier_diff',[sys.executable,'scripts/run_frontier_diff.py','--out',str(outdir/'frontier_diff.json')], artifact=outdir/'frontier_diff.json'))
    checks.append(run('scorecard',[sys.executable,'scripts/make_scorecard.py','--replay','tests/fixtures/replay_golden.jsonl','--frontier-diff',str(outdir/'frontier_diff.json'),'--out',str(outdir/'ml_scorecard.json')], artifact=outdir/'ml_scorecard.json'))
    checks.append(run('measurement',[sys.executable,'scripts/make_measurement_report.py','--scorecard',str(outdir/'ml_scorecard.json'),'--frontier-diff',str(outdir/'frontier_diff.json'),'--out',str(outdir/'measurement_report.json')], artifact=outdir/'measurement_report.json'))
    checks.append(run('calibration',calibration_cmd, artifact=outdir/'calibration_report.json'))
    checks.append(run('provider_capability',[sys.executable,'scripts/make_provider_capability_report.py','--out',str(outdir/'provider_capability_report.json')], artifact=outdir/'provider_capability_report.json'))
    reward_replay, reward_manifest=materialize_action_reward_replay(outdir, reward_inputs)
    checks.append(run('reward_heads',reward_head_cmd(outdir, reward_replay), artifact=outdir/'reward_head_report.json'))
    checks.append(run('curriculum',[sys.executable,'scripts/run_self_play_curriculum.py','--curriculum','experiments/curricula/p12_base.json','--out',str(outdir/'curriculum_run.json')], artifact=outdir/'curriculum_run.json'))
    checks.append(run('policy_ablation',[sys.executable,'scripts/run_policy_ablation.py','--frontier-diff',str(outdir/'frontier_diff.json'),'--scorecard',str(outdir/'ml_scorecard.json'),'--reward-heads',str(outdir/'reward_head_report.json'),'--evidence-dir',str(outdir/'policy_ablation_evidence'),'--out',str(outdir/'policy_ablation_report.json')], artifact=outdir/'policy_ablation_report.json'))
    checks.append(run('belief_explain',[sys.executable,'scripts/make_belief_explain_report.py','--out',str(outdir/'belief_explain_report.json')], artifact=outdir/'belief_explain_report.json'))
    checks.append(run('cvar',[sys.executable,'scripts/run_cvar_report.py','--out',str(outdir/'cvar_report.json')], artifact=outdir/'cvar_report.json'))
    checks.append(run('b_migrate',[sys.executable,'scripts/run_b_migrate_dual_run.py','--artifacts-dir',str(outdir/'b_migrate_artifacts'),'--out',str(outdir/'b_migrate_report.json')], artifact=outdir/'b_migrate_report.json'))
    checks.append(run('secret_scan',[sys.executable,'scripts/run_secret_scan.py','--path',str(outdir)]))
    reach=release_reach()
    decision=release_decision(checks, reach)
    report={'p12_release_schema_version':'p12_release_report.v1','decision':decision,'ok':decision=='pass','checks':checks,'release_reach':reach,'reward_replay_inputs':[str(p) for p in reward_inputs],'reward_action_replay':str(reward_replay),'reward_action_replay_manifest':str(reward_manifest),'artifacts_dir':str(outdir)}
    (outdir/'p12_release_report.json').write_text(json.dumps(report,indent=2,sort_keys=True))
    print(json.dumps({'ok':report['ok'],'decision':decision,'out':str(outdir/'p12_release_report.json')},indent=2))
    raise SystemExit(1 if decision=='fail' else 0)
if __name__=='__main__': main()
