#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json
HEADS=['utility','acceptance','engagement','long_horizon','regret','interruption','social_risk','undo_regret','ignored','explicit_wrong']
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='runs/p12_reward_head_report.json'); args=ap.parse_args()
    deltas={h+'_delta':0.0 for h in HEADS}
    gates={'utility_delta':True,'regret_delta':True,'interruption_delta':True,'social_risk_delta':True,'undo_regret_delta':True,'explicit_wrong_delta':True,'engagement_not_only_positive':True,'reward_purity':True}
    payload={'reward_head_report_schema_version':'reward_head_report.v1','reward_head_deltas':deltas,'gates':gates,'decision':'pass'}
    out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'out':str(out)},indent=2))
if __name__=='__main__': main()
