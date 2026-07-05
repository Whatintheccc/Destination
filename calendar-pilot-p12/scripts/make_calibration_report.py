#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--sim-batch',default=''); ap.add_argument('--dogfood-shadow',default=''); ap.add_argument('--family',default=''); ap.add_argument('--out',default='runs/p12_calibration_report.json'); args=ap.parse_args()
    family=args.family.strip()
    family_metrics={family:{'matched_examples':0,'acceptance_gap':None,'undo_gap':None,'decision':'hold'}} if family else {}
    payload={'calibration_schema_version':'calibration_report.v1','run_id':args.sim_batch or 'p12_calibration','policy_tuning_id':'CURRENT','simulator_version':'sim_v2.1','estimator_versions':['interruption_tolerance_v1'],'real_source':'dogfood_shadow' if args.dogfood_shadow else 'fixture','matched_examples':0,'action_family_metrics':family_metrics,'overall_acceptance_gap':None,'overall_undo_gap':None,'estimator_calibration_gap':None,'known_biases':['insufficient matched real examples'],'decision':'hold'}
    out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'decision':'hold','out':str(out)},indent=2))
if __name__=='__main__': main()
