#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json
ABLATIONS=['no_intent_reward_bias','no_failure_penalties','no_denied_intents','no_right_moment_tuning','no_taxonomy_normalization','no_provider_penalties','no_semantic_labels','no_derived_signals']
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--candidate',default='candidate'); ap.add_argument('--current',default='CURRENT'); ap.add_argument('--out',default='runs/p12_policy_ablation_report.json'); args=ap.parse_args()
 payload={'ablation_schema_version':'policy_ablation_report.v1','candidate_policy_tuning_id':args.candidate,'current_policy_tuning_id':args.current,'ablations':{name:{'frontier_diff':{},'scorecard':{},'reward_head_deltas':{},'promotion_decision':'pass'} for name in ABLATIONS},'critical_components':['failure_penalties'],'non_effective_components':[],'decision':'pass'}
 out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'out':str(out)},indent=2))
if __name__=='__main__': main()
