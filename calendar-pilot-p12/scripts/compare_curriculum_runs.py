#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--candidate',default=''); ap.add_argument('--runs',nargs='*',default=[]); ap.add_argument('--out',default='runs/p12_curriculum_comparison.json'); args=ap.parse_args(); rows=[]
 run_paths = ([args.candidate] if args.candidate else []) + list(args.runs)
 for r in run_paths:
  p=Path(r); p=p if p.is_absolute() else ROOT/p
  if p.exists(): rows.append(json.loads(p.read_text()))
 payload={'curriculum_comparison_schema_version':'curriculum_comparison.v1','runs':rows,'decision':'pass' if all(not r.get('promotion_blockers') for r in rows) else 'hold'}
 out=Path(args.out); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'out':str(out)},indent=2))
if __name__=='__main__': main()
