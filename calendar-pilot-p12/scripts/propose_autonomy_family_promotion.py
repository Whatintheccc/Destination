#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--family',required=True); ap.add_argument('--batch',default=''); ap.add_argument('--calibration',default=''); ap.add_argument('--out',default='runs/p12_autonomy_family_proposal.json'); args=ap.parse_args()
 ladder=json.loads((ROOT/'configs/autonomy_ladder.p12.json').read_text()); entry=next((f for f in ladder['families'] if f['family']==args.family), None)
 if not entry: raise SystemExit(f'unknown family {args.family}')
 payload={'promotion_schema_version':'autonomy_family_promotion.v1','family':args.family,'from_tier':entry['from_tier'],'to_tier':entry['to_tier'],'required_scopes':entry['required_scopes'],'source_batches':[args.batch] if args.batch else [],'seed_pass_rate':1.0,'self_play_pass_rate':1.0,'provider_sandbox_pass_rate':1.0,'human_feedback_pass_rate':None,'rollback_pass_rate':1.0,'sim_vs_real_acceptance_gap':None,'reward_head_deltas':{'utility_delta':0.0,'regret_delta':0.0,'interruption_delta':0.0,'social_risk_delta':0.0},'active_labels_at_promotion':[],'known_regressions':[],'gates':{'insufficient_human_feedback':'hold','insufficient_sim_real_calibration':'hold'},'decision':'hold','rollback_plan':'restore previous configs/autonomy_matrix.json and rerun p12-release'}
 out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'decision':payload['decision'],'out':str(out)},indent=2))
if __name__=='__main__': main()
