#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(name, cmd, *, allow_hold=False):
    proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    return {'name':name,'cmd':' '.join(cmd),'returncode':proc.returncode,'ok':proc.returncode==0 or allow_hold,'stdout':proc.stdout[-4000:],'stderr':proc.stderr[-4000:]}

def main():
    outdir=ROOT/'runs'/'p12_release'; outdir.mkdir(parents=True,exist_ok=True)
    checks=[]
    checks.append(run('check_invariants',[sys.executable,'scripts/check_invariants.py','--replay','tests/fixtures/replay_golden.jsonl','--out',str(outdir/'invariants.json')]))
    checks.append(run('signal_estimators',[sys.executable,'scripts/run_signal_estimators.py','--out',str(outdir/'signal_estimator_report.json'),'--replay-out',str(outdir/'signal_estimator_replay.jsonl')]))
    checks.append(run('measurement',[sys.executable,'scripts/make_measurement_report.py','--out',str(outdir/'measurement_report.json')]))
    checks.append(run('calibration',[sys.executable,'scripts/make_calibration_report.py','--out',str(outdir/'calibration_report.json')]))
    checks.append(run('provider_capability',[sys.executable,'scripts/make_provider_capability_report.py','--out',str(outdir/'provider_capability_report.json')]))
    checks.append(run('reward_heads',[sys.executable,'scripts/make_reward_head_report.py','--out',str(outdir/'reward_head_report.json')]))
    checks.append(run('curriculum',[sys.executable,'scripts/run_self_play_curriculum.py','--curriculum','experiments/curricula/p12_base.json','--out',str(outdir/'curriculum_run.json')]))
    checks.append(run('policy_ablation',[sys.executable,'scripts/run_policy_ablation.py','--out',str(outdir/'policy_ablation_report.json')]))
    checks.append(run('secret_scan',[sys.executable,'scripts/run_secret_scan.py','--path',str(outdir)]))
    report={'p12_release_schema_version':'p12_release_report.v1','ok':all(c['ok'] for c in checks),'checks':checks,'artifacts_dir':str(outdir)}
    (outdir/'p12_release_report.json').write_text(json.dumps(report,indent=2,sort_keys=True))
    print(json.dumps({'ok':report['ok'],'out':str(outdir/'p12_release_report.json')},indent=2))
    raise SystemExit(0 if report['ok'] else 1)
if __name__=='__main__': main()
