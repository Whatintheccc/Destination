#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--curriculum',required=True); ap.add_argument('--provider',default='stub'); ap.add_argument('--sandbox-calendar',default=''); ap.add_argument('--families',default=''); ap.add_argument('--episodes',type=int,default=10); ap.add_argument('--out',default='runs/p12_curriculum_run.json'); args=ap.parse_args()
 cpath=Path(args.curriculum); cpath=cpath if cpath.is_absolute() else ROOT/cpath; cur=json.loads(cpath.read_text())
 scenarios=cur.get('scenarios',[]); blockers=[]
 for sc in scenarios:
  if any(k in sc for k in ['fatigue','energy','mood']): blockers.append(f"scenario {sc.get('scenario_id')} declares internal state")
 payload={'curriculum_schema_version':'curriculum_run.v1','curriculum_id':cur.get('curriculum_id',cpath.stem),'simulator_version':'sim_v2.1','estimator_versions':['interruption_tolerance_v1'],'policy_tuning_id':'CURRENT','scenario_count':len(scenarios),'episode_count':args.episodes,'failure_modes':{},'mapped_findings':{},'unmapped_findings':{},'waived_findings':{},'average_reward':0.0,'reward_head_deltas':{},'promotion_blockers':blockers,'provider':args.provider,'families':[x for x in args.families.split(',') if x],'sandbox_calendar':args.sandbox_calendar}
 out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':not blockers,'out':str(out),'promotion_blockers':blockers},indent=2))
 if blockers: raise SystemExit(1)
if __name__=='__main__': main()
