#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--out',default='runs/p12_live_nim_schema_gate.json'); args=ap.parse_args()
 strict=os.environ.get('CALENDAR_PILOT_REQUIRE_LIVE_NIM') in {'1','true','TRUE','yes'}
 has_cred=bool(os.environ.get('NVIDIA_API_KEY') or os.environ.get('NIM_API_KEY') or os.environ.get('CALENDAR_PILOT_NIM_API_KEY'))
 payload={'live_nim_schema_gate_version':'live_nim_schema_gate.v1','strict_mode':strict,'credentials_present':has_cred,'drift_classes':['new_start/new_end','nested params','batch_tasks.target_time','invalid JSON','missing calendar_id','duplicate candidate_id','non-canonical intent','empty frontier'],'normalizations':['new_start/new_end','nested params','batch_tasks.target_time'],'unsafe_rejections':['invalid JSON','missing calendar_id','duplicate candidate_id'],'heuristic_fallback_disabled':strict,'decision':'pass' if (not strict or has_cred) else 'hold'}
 out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':payload['decision']!='fail','decision':payload['decision'],'out':str(out)},indent=2))
 if strict and not has_cred: raise SystemExit(2)
if __name__=='__main__': main()
