#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from calendar_pilot.environment.fsio import atomic_write_json

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--proposal',required=True); ap.add_argument('--human-note',default=''); ap.add_argument('--out',default=''); args=ap.parse_args()
 p=Path(args.proposal); p=p if p.is_absolute() else ROOT/p; payload=json.loads(p.read_text()); payload['human_note']=args.human_note; payload.setdefault('decision','hold')
 out=Path(args.out) if args.out else p.with_name(p.stem+'_decision.json'); out=out if out.is_absolute() else ROOT/out; atomic_write_json(out,payload); print(json.dumps({'ok':True,'decision':payload['decision'],'out':str(out)},indent=2))
if __name__=='__main__': main()
